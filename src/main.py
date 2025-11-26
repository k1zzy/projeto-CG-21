
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
TITLE = "Projecto CG - Carro e Garagem"

class CarController:
    def __init__(self, root_node, chassis, wheels, steering_wheel, doors):
        self.root = root_node
        self.chassis = chassis
        self.wheels = wheels # [FL, FR, RL, RR]
        self.steering_wheel = steering_wheel
        self.doors = doors # [Left, Right]
        
        self.position = np.array([0.0, 0.5, 0.0], dtype=np.float32)
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
        wheel_rot_speed = self.speed * 2.0 # simplified
        for i, w in enumerate(self.wheels):
            # Rotate around X axis (rolling)
            # We need to accumulate rotation or just use time-based if constant speed, 
            # but for variable speed we should integrate. 
            # For simplicity, let's just rotate based on distance traveled if we tracked it, 
            # or just spin them based on current speed for effect.
            # A better way: keep a current angle for each wheel
            if not hasattr(w, 'roll_angle'): w.roll_angle = 0.0
            
            # Rear wheels (2, 3) are larger, so they rotate slower?
            # Let's say rear radius is 1.5x front.
            radius_factor = 1.0 if i < 2 else 0.66
            w.roll_angle += wheel_rot_speed * radius_factor * dt * 10.0
            
            # Front wheels (0, 1) also steer
            steer_mat = np.eye(4, dtype=np.float32)
            if i < 2:
                steer_mat = rotate(math.radians(self.steering_angle), (0, 1, 0))
                
            # Apply transforms: Steer -> Roll -> Scale/Pos (handled by parent)
            # Since we are modifying 'local', we need to be careful not to overwrite the initial offset.
            # We assume the wheel nodes have an initial offset in their parent.
            # Actually, Node.local is the full transform. 
            # To make this easy, we should have a "WheelHolder" node for offset/steering, and "WheelGeo" for rolling.
            # But for this base code, let's just assume the wheel node is at (0,0,0) relative to a parent "WheelMount".
            # Let's assume the passed 'wheels' are the geometry nodes.
            
            w.local = steer_mat @ rotate(w.roll_angle, (1, 0, 0))

        # Update Steering Wheel
        if self.steering_wheel:
            self.steering_wheel.local = rotate(math.radians(self.steering_angle * 3), (0, 0, 1))

        # Doors
        target_door = 45.0 if self.door_open else 0.0
        self.door_angle += (target_door - self.door_angle) * 2.0 * dt
        for door in self.doors:
            # Assume door pivot is correctly set up (e.g. at the hinge)
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
    # Try to load texture
    tex_id = load_texture("floor.jpg")
    if tex_id:
        floor.mesh.texture_id = tex_id
    root.add(floor)
    
    # --- Car Construction (Placeholder) ---
    car_root = Node("CarRoot")
    
    # Chassis
    chassis = Node("Chassis", local=scale(2.0, 0.5, 4.0), mesh=cube_mesh, material_diffuse=(0.8, 0.2, 0.2))
    car_root.add(chassis)
    
    # Cabin
    cabin = Node("Cabin", local=translate(0, 0.5, -0.5) @ scale(1.8, 0.6, 2.0), mesh=cube_mesh, material_diffuse=(0.2, 0.2, 0.8))
    car_root.add(cabin)
    
    # Wheels (using helper nodes for offsets)
    wheels = []
    
    # Front Left
    fl_mount = Node("FL_Mount", local=translate(1.1, 0.0, 1.5))
    fl_wheel = Node("FL_Wheel", local=scale(0.4, 0.8, 0.8), mesh=cube_mesh, material_diffuse=(0.1, 0.1, 0.1))
    fl_mount.add(fl_wheel)
    car_root.add(fl_mount)
    wheels.append(fl_wheel)
    
    # Front Right
    fr_mount = Node("FR_Mount", local=translate(-1.1, 0.0, 1.5))
    fr_wheel = Node("FR_Wheel", local=scale(0.4, 0.8, 0.8), mesh=cube_mesh, material_diffuse=(0.1, 0.1, 0.1))
    fr_mount.add(fr_wheel)
    car_root.add(fr_mount)
    wheels.append(fr_wheel)
    
    # Rear Left (Larger)
    rl_mount = Node("RL_Mount", local=translate(1.1, 0.2, -1.5))
    rl_wheel = Node("RL_Wheel", local=scale(0.5, 1.2, 1.2), mesh=cube_mesh, material_diffuse=(0.1, 0.1, 0.1))
    rl_mount.add(rl_wheel)
    car_root.add(rl_mount)
    wheels.append(rl_wheel)
    
    # Rear Right (Larger)
    rr_mount = Node("RR_Mount", local=translate(-1.1, 0.2, -1.5))
    rr_wheel = Node("RR_Wheel", local=scale(0.5, 1.2, 1.2), mesh=cube_mesh, material_diffuse=(0.1, 0.1, 0.1))
    rr_mount.add(rr_wheel)
    car_root.add(rr_mount)
    wheels.append(rr_wheel)
    
    # Steering Wheel (Visual)
    sw_mount = Node("SW_Mount", local=translate(-0.5, 0.6, 0.0)) # Inside cabin
    sw_geo = Node("SteeringWheel", local=scale(0.3, 0.3, 0.05), mesh=cube_mesh, material_diffuse=(0.3, 0.3, 0.3))
    sw_mount.add(sw_geo)
    car_root.add(sw_mount)
    
    # Doors (Visual - Simple pivot)
    # Left Door
    ld_mount = Node("LD_Mount", local=translate(1.0, 0.5, 0.0))
    ld_geo = Node("LeftDoor", local=translate(0, 0, 0.5) @ scale(0.1, 0.5, 1.0), mesh=cube_mesh, material_diffuse=(0.8, 0.25, 0.25))
    ld_mount.add(ld_geo)
    car_root.add(ld_mount)
    
    root.add(car_root)
    
    car_ctrl = CarController(car_root, chassis, wheels, sw_geo, [ld_mount])
    
    # --- Garage Construction ---
    garage_root = Node("Garage", local=translate(10, 0, 10))
    
    # Walls
    g_walls = Node("GWalls", local=scale(6.0, 3.0, 6.0), mesh=cube_mesh, material_diffuse=(0.6, 0.6, 0.6))
    # Note: Cube is solid, so we'd be inside it. For a real garage, model it in Blender with inverted normals or separate walls.
    # For now, just a block representing the garage.
    garage_root.add(g_walls)
    
    # Door
    g_door_mount = Node("GDoorMount", local=translate(0, 0, 3.0))
    g_door = Node("GDoor", local=scale(4.0, 2.5, 0.2), mesh=cube_mesh, material_diffuse=(0.4, 0.2, 0.0))
    g_door_mount.add(g_door)
    garage_root.add(g_door_mount)
    
    root.add(garage_root)
    
    garage_ctrl = GarageController(g_door)
    
    # Input State
    inputs = {'w': False, 's': False, 'a': False, 'd': False}
    
    def key_callback(window, key, scancode, action, mods):
        if action == glfw.PRESS:
            if key == glfw.KEY_ESCAPE: glfw.set_window_should_close(window, True)
            if key == glfw.KEY_W: inputs['w'] = True
            if key == glfw.KEY_S: inputs['s'] = True
            if key == glfw.KEY_A: inputs['a'] = True
            if key == glfw.KEY_D: inputs['d'] = True
            if key == glfw.KEY_O: garage_ctrl.toggle()
            if key == glfw.KEY_P: car_ctrl.toggle_door()
            
            # Camera
            if key == glfw.KEY_UP: camera.zoom(0.9)
            if key == glfw.KEY_DOWN: camera.zoom(1.1)
            if key == glfw.KEY_LEFT: camera.rotate(-5)
            if key == glfw.KEY_RIGHT: camera.rotate(5)
            
        elif action == glfw.RELEASE:
            if key == glfw.KEY_W: inputs['w'] = False
            if key == glfw.KEY_S: inputs['s'] = False
            if key == glfw.KEY_A: inputs['a'] = False
            if key == glfw.KEY_D: inputs['d'] = False

    glfw.set_key_callback(window, key_callback)
    
    # Loop
    last_time = glfw.get_time()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    
    while not glfw.window_should_close(window):
        t = glfw.get_time()
        dt = t - last_time
        last_time = t
        
        glfw.poll_events()
        
        # Update
        car_ctrl.update(dt, inputs)
        garage_ctrl.update(dt)
        
        # Camera follows car
        camera.center = car_ctrl.position
        
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
