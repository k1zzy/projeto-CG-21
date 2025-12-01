
import sys
import math
import glfw
import numpy as np
from OpenGL.GL import *

from shader import ShaderProgram
from scene import Node, create_grid_mesh, create_cube_mesh, load_texture
from camera import Camera
from transform import translate, rotate, scale, perspective
from obj_loader import OBJModel

# Constants
WIN_WIDTH = 1280
WIN_HEIGHT = 720
TITLE = "Projecto CG - Grupo 21"

class CarController:
    def __init__(self, root_node, chassis, front_axle, rear_axle, front_pivot, rear_pivot, steering_wheel, doors):
        self.root = root_node
        self.chassis = chassis
        self.front_axle = front_axle
        self.rear_axle = rear_axle
        self.front_pivot = front_pivot
        self.rear_pivot = rear_pivot
        self.steering_wheel = steering_wheel
        self.doors = doors # [Left, Right]
        
        self.position = np.array([0.0, 1.2, 0.0], dtype=np.float32)
        self.yaw = 0.0
        self.speed = 0.0
        self.steering_angle = 0.0
        
        self.door_open = False
        self.door_angle = 0.0
        
        # Config
        self.max_speed = 10.0
        self.acceleration = 5.0
        self.friction = 2.0
        self.turn_speed = 2.0
        self.max_steer = 30.0

    def update(self, dt, inputs):
        # Acceleration
        if inputs['w']: self.speed += self.acceleration * dt
        elif inputs['s']: self.speed -= self.acceleration * dt
        else:
            # Friction
            if abs(self.speed) < 0.1: self.speed = 0
            else: self.speed -= math.copysign(self.friction * dt, self.speed)
            
        # Clamp speed
        self.speed = max(-5.0, min(self.speed, self.max_speed))
        
        # Steering
        target_steer = 0.0
        if inputs['a']: target_steer = self.max_steer
        elif inputs['d']: target_steer = -self.max_steer
        
        # Smooth steering
        self.steering_angle += (target_steer - self.steering_angle) * 5.0 * dt
        
        # Movement
        if abs(self.speed) > 0.1:
            turn = math.radians(self.steering_angle) * (self.speed / self.max_speed) * self.turn_speed * dt
            self.yaw += turn
            
            dx = math.sin(self.yaw) * self.speed * dt
            dz = math.cos(self.yaw) * self.speed * dt
            self.position[0] += dx
            self.position[2] += dz
            
        # Update Car Root Transform
        self.root.local = translate(self.position[0], self.position[1], self.position[2]) @ \
                          rotate(self.yaw, (0, 1, 0))
                          
        # Rotate Wheels (visual)
        wheel_rot_speed = self.speed * 2.0 
        
        # Helper for pivot rotation: T(P) * R * T(-P)
        def get_pivot_transform(pivot, rotation_matrix):
            # We want to rotate around the pivot point (center of axle)
            # The node is already at (0,0,0) with vertices offset.
            # So we translate to pivot (which is where the vertices "are"), rotate, then translate back?
            # No, the vertices are at 'pivot' relative to (0,0,0).
            # To rotate around 'pivot', we need: T(pivot) * R * T(-pivot)
            # But wait, the node's local transform applies to the vertices.
            # If vertices are at V, and we want to rotate around P.
            # NewV = T(P) * R * T(-P) * V
            return translate(pivot[0], pivot[1], pivot[2]) @ \
                   rotation_matrix @ \
                   translate(-pivot[0], -pivot[1], -pivot[2])

        # Front Axle (Steer + Roll)
        if not hasattr(self.front_axle, 'roll_angle'): self.front_axle.roll_angle = 0.0
        self.front_axle.roll_angle += wheel_rot_speed * dt * 10.0
        
        front_rot = rotate(math.radians(self.steering_angle), (0, 1, 0)) @ \
                    rotate(self.front_axle.roll_angle, (1, 0, 0))
        
        self.front_axle.local = get_pivot_transform(self.front_pivot, front_rot)

        # Rear Axle (Roll only)
        if not hasattr(self.rear_axle, 'roll_angle'): self.rear_axle.roll_angle = 0.0
        self.rear_axle.roll_angle += wheel_rot_speed * 0.66 * dt * 10.0 # Larger wheels
        
        rear_rot = rotate(self.rear_axle.roll_angle, (1, 0, 0))
        self.rear_axle.local = get_pivot_transform(self.rear_pivot, rear_rot)

        # Update Steering Wheel
        if self.steering_wheel:
            # Adjust rotation axis/direction as needed for the model
            self.steering_wheel.local = rotate(math.radians(self.steering_angle * 3), (0, 0, 1))

        # Doors
        target_door = 45.0 if self.door_open else 0.0
        self.door_angle += (target_door - self.door_angle) * 2.0 * dt
        for door in self.doors:
            door.local = rotate(math.radians(self.door_angle), (0, 1, 0))

    def toggle_door(self):
        self.door_open = not self.door_open

class GarageController:
    def __init__(self, door_node):
        self.door = door_node
        self.is_open = False
        self.open_height = 0.0
        self.max_height = 2.5
        
    def update(self, dt):
        target = self.max_height if self.is_open else 0.0
        self.open_height += (target - self.open_height) * 2.0 * dt
        self.door.local = translate(0, self.open_height, 0)
        
    def toggle(self):
        self.is_open = not self.is_open

def load_obj_node(path, name, color=None, alpha=1.0, specular=(1,1,1), shininess=32.0, center=False):
    try:
        model = OBJModel(path)
        c = (0,0,0)
        if center: c = model.get_center()
        model.build()
        node = model.to_node(name)
        
        # Override material properties recursively
        def set_props(n):
            if color: n.mat_diffuse = color
            n.mat_alpha = alpha
            n.mat_specular = specular
            n.mat_shininess = shininess
            for c in n.children: set_props(c)
            
        set_props(node)
        return node, c
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return Node(name), (0,0,0)

def main():
    if not glfw.init():
        sys.exit(1)
        
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    
    window = glfw.create_window(WIN_WIDTH, WIN_HEIGHT, TITLE, None, None)
    if not window:
        glfw.terminate()
        sys.exit(1)
        
    glfw.make_context_current(window)
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED) # Capture mouse
    
    # Init Shader
    try:
        shader = ShaderProgram()
    except Exception as e:
        print(e)
        sys.exit(1)
        
    # Camera
    camera = Camera(radius=15.0, height=8.0)
    
    # Scene Construction
    cube_mesh = create_cube_mesh(1.0)
    grid_mesh = create_grid_mesh(100, 20)
    
    root = Node("Root")
    
    # Floor
    floor = Node("Floor", mesh=grid_mesh, material_diffuse=(0.8, 0.8, 0.8))
    tex_id = load_texture("floor.jpg")
    if tex_id: floor.mesh.texture_id = tex_id
    root.add(floor)
    
    # --- Car Construction ---
    car_root = Node("CarRoot")
    
    # Rotator node to fix orientation (180 degrees)
    # If the car faces backwards, rotating 180 around Y should fix it.
    car_orient = Node("CarOrient", local=rotate(math.radians(180), (0, 1, 0)))
    car_root.add(car_orient)

    # Chassis (Red Paint)
    # Chassis (Red Paint)
    chassis, _ = load_obj_node("../models/carrocaria.obj", "ChassisModel", 
                            color=(0.8, 0.0, 0.0), specular=(1.0, 1.0, 1.0), shininess=64.0, center=False)
    car_orient.add(chassis)
    
    # Lights
    luz_frente, _ = load_obj_node("../models/luz_frente.obj", "LuzFrente", color=(1.0, 1.0, 0.9))
    luz_tras, _ = load_obj_node("../models/luz_tras.obj", "LuzTras", color=(0.8, 0.0, 0.0))
    car_orient.add(luz_frente, luz_tras)
    
    # Mirrors
    retrovisores, _ = load_obj_node("../models/retrovisores_fora.obj", "Retrovisores", color=(0.1, 0.1, 0.1))
    car_orient.add(retrovisores)
    
    # Wheels (Black Metallic) - Using Axle approach
    # Wheels (Black Metallic) - Axles
    # Load Front Axle
    front_axle, front_center = load_obj_node("../models/rodas_frente.obj", "FrontAxle", 
                                             color=(0.1, 0.1, 0.1), specular=(0.8, 0.8, 0.8), shininess=32.0, center=True)
    car_orient.add(front_axle)
    
    # Load Rear Axle
    rear_axle, rear_center = load_obj_node("../models/rodas_tras.obj", "RearAxle", 
                                           color=(0.1, 0.1, 0.1), specular=(0.8, 0.8, 0.8), shininess=32.0, center=True)
    car_orient.add(rear_axle)

    # Glass (Transparent) - Moved to end for correct blending
    parabrisas, _ = load_obj_node("../models/parabrisas.obj", "Parabrisas", 
                               color=(0.2, 0.3, 0.4), alpha=0.4, specular=(1,1,1), shininess=128)
    vidros_resto, _ = load_obj_node("../models/vidros_resto.obj", "VidrosResto", 
                                 color=(0.2, 0.3, 0.4), alpha=0.4, specular=(1,1,1), shininess=128)
    car_orient.add(parabrisas, vidros_resto)
    
    root.add(car_root)
    
    car_ctrl = CarController(car_root, chassis, front_axle, rear_axle, front_center, rear_center, None, [])
    
    # --- Garage Construction ---
    garage_root = Node("Garage", local=translate(10, 0, 10))
    g_walls = Node("GWalls", local=scale(6.0, 3.0, 6.0), mesh=cube_mesh, material_diffuse=(0.6, 0.6, 0.6))
    garage_root.add(g_walls)
    
    g_door_mount = Node("GDoorMount", local=translate(0, 0, 3.0))
    g_door = Node("GDoor", local=scale(4.0, 2.5, 0.2), mesh=cube_mesh, material_diffuse=(0.4, 0.2, 0.0))
    g_door_mount.add(g_door)
    garage_root.add(g_door_mount)
    
    root.add(garage_root)
    garage_ctrl = GarageController(g_door)
    
    # Input State
    inputs = {'w': False, 's': False, 'a': False, 'd': False, 'q': False, 'e': False}
    mouse_dx, mouse_dy = 0, 0
    
    def key_callback(window, key, scancode, action, mods):
        if action == glfw.PRESS:
            if key == glfw.KEY_ESCAPE: glfw.set_window_should_close(window, True)
            if key == glfw.KEY_W: inputs['w'] = True
            if key == glfw.KEY_S: inputs['s'] = True
            if key == glfw.KEY_A: inputs['a'] = True
            if key == glfw.KEY_D: inputs['d'] = True
            if key == glfw.KEY_Q: inputs['q'] = True
            if key == glfw.KEY_E: inputs['e'] = True
            
            if key == glfw.KEY_O: garage_ctrl.toggle()
            if key == glfw.KEY_P: car_ctrl.toggle_door()
            if key == glfw.KEY_C: camera.toggle_mode()
            
        elif action == glfw.RELEASE:
            if key == glfw.KEY_W: inputs['w'] = False
            if key == glfw.KEY_S: inputs['s'] = False
            if key == glfw.KEY_A: inputs['a'] = False
            if key == glfw.KEY_D: inputs['d'] = False
            if key == glfw.KEY_Q: inputs['q'] = False
            if key == glfw.KEY_E: inputs['e'] = False

    def mouse_callback(window, xpos, ypos):
        nonlocal mouse_dx, mouse_dy
        # Simple delta calculation
        # In a real app we'd center the mouse, but for now just use delta from previous frame
        # We need a global or static variable for last pos, but here we can just use a simple approach
        # or rely on glfw's cursor disabled mode which gives unbounded coordinates
        pass 

    # Better mouse handling
    last_x, last_y = 0, 0
    first_mouse = True
    def mouse_callback_impl(window, xpos, ypos):
        nonlocal last_x, last_y, first_mouse, mouse_dx, mouse_dy
        if first_mouse:
            last_x, last_y = xpos, ypos
            first_mouse = False
        
        mouse_dx = xpos - last_x
        mouse_dy = ypos - last_y
        last_x, last_y = xpos, ypos

    def scroll_callback(window, xoffset, yoffset):
        if yoffset > 0:
            camera.zoom(0.9) # Zoom in
        elif yoffset < 0:
            camera.zoom(1.1) # Zoom out

    glfw.set_key_callback(window, key_callback)
    glfw.set_cursor_pos_callback(window, mouse_callback_impl)
    glfw.set_scroll_callback(window, scroll_callback)
    
    # Loop
    last_time = glfw.get_time()
    
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE) # Fix for invisible inner parts
    
    # Alpha Blending
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    while not glfw.window_should_close(window):
        t = glfw.get_time()
        dt = t - last_time
        last_time = t
        
        glfw.poll_events()
        
        # Update
        # Update
        if camera.mode == "FREE":
            camera.update_free_cam(dt, inputs, (mouse_dx, mouse_dy))
        else:
            car_ctrl.update(dt, inputs)
            
            # Smart Follow Camera
            # Base angle is car's yaw (plus 180 since car model was rotated 180)
            base_angle = math.degrees(car_ctrl.yaw) + 180
            
            # Mouse input adds to an offset angle
            if mouse_dx != 0:
                camera.angle_offset = getattr(camera, 'angle_offset', 0.0) - mouse_dx * 0.2
                camera.last_mouse_time = t
            
            # Auto-align if no input for 2 seconds
            if t - getattr(camera, 'last_mouse_time', 0.0) > 2.0:
                # Decay offset to 0
                offset = getattr(camera, 'angle_offset', 0.0)
                camera.angle_offset = offset * (1.0 - 5.0 * dt) # Smooth decay
                if abs(camera.angle_offset) < 0.1: camera.angle_offset = 0.0
            
            camera.angle = base_angle + getattr(camera, 'angle_offset', 0.0)
            camera.center = car_ctrl.position
            
        mouse_dx, mouse_dy = 0, 0 # Reset delta
        
        garage_ctrl.update(dt)
        
        # Render
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        width, height = glfw.get_framebuffer_size(window)
        glViewport(0, 0, width, height)
        
        P = perspective(60.0, width/height, 0.1, 1000.0)
        V, eye_pos = camera.get_view_matrix()
        VP = P @ V
        
        shader.use()
        shader.set_view_pos(eye_pos)
        
        # Lights
        shader.set_light(0, (10, 20, 10), (0.2, 0.2, 0.2), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0))
        shader.set_light(1, (-10, 10, -10), (0.1, 0.1, 0.1), (0.5, 0.5, 0.8), (0.5, 0.5, 0.5))
        
        root.draw(shader, np.eye(4, dtype=np.float32), VP)
        
        glfw.swap_buffers(window)
        
    glfw.terminate()

if __name__ == "__main__":
    main()
