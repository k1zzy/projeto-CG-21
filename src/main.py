
import sys, os, math
import glfw
import numpy as np
from OpenGL.GL import *

from shader import ShaderProgram
from scene import Node, create_grid_mesh, create_cube_mesh, load_texture, create_sphere_mesh
from camera import Camera
from transform import translate, rotate, scale, perspective
from obj_loader import OBJModel

# constantes
WIN_WIDTH = 1280
WIN_HEIGHT = 720
TITLE = "Projecto CG - Grupo 21"

# auxiliar pra rotacao de pivo tipo T(P) * R * T(-P)
def get_pivot_transform(pivot, rotation_matrix):
    return translate(pivot[0], pivot[1], pivot[2]) @ \
           rotation_matrix @ \
           translate(-pivot[0], -pivot[1], -pivot[2])

class CarController:
    def __init__(self, root_node, chassis, wheels_dict, doors_dict, steering_wheel):
        self.root = root_node
        self.chassis = chassis
        self.wheels = wheels_dict # tipo fl fr etc
        self.doors = doors_dict   # mesma coisa
        self.steering_wheel = steering_wheel
        
        self.position = np.array([0.0, 0.65, 0.0], dtype=np.float32)
        self.yaw = 0.0
        self.speed = 0.0
        self.steering_angle = 0.0
        
        # estados das portas todas independentes
        self.door_states = {
            'frente_esquerda': {'open': False, 'angle': 0.0},
            'frente_direita': {'open': False, 'angle': 0.0},
            'tras_esquerda': {'open': False, 'angle': 0.0},
            'tras_direita': {'open': False, 'angle': 0.0}
        }
        
        # configuracao do carro
        self.max_speed = 10.0
        self.acceleration = 5.0
        self.friction = 2.0
        self.turn_speed = 2.0
        self.max_steer = 30.0

    def update(self, dt, inputs):
        # aceleracao
        if inputs['w']: self.speed += self.acceleration * dt
        elif inputs['s']: self.speed -= self.acceleration * dt
        else:
            # atrito
            if abs(self.speed) < 0.1: self.speed = 0
            else: self.speed -= math.copysign(self.friction * dt, self.speed)
            
        # limitar velocidade
        self.speed = max(-5.0, min(self.speed, self.max_speed))
        
        # direcao do volante
        target_steer = 0.0
        if inputs['a']: target_steer = self.max_steer
        elif inputs['d']: target_steer = -self.max_steer
        
        # suavizar direcao
        self.steering_angle += (target_steer - self.steering_angle) * 5.0 * dt
        
        # movimento
        if abs(self.speed) > 0.1:
            turn = math.radians(self.steering_angle) * (self.speed / self.max_speed) * self.turn_speed * dt
            self.yaw += turn
            
            dx = math.sin(self.yaw) * self.speed * dt
            dz = math.cos(self.yaw) * self.speed * dt
            self.position[0] += dx
            self.position[2] += dz
            
        # atualizar transformacao da raiz do carro
        self.root.local = translate(self.position[0], self.position[1], self.position[2]) @ \
                          rotate(self.yaw, (0, 1, 0))
                          
        # rodar rodas so visual
        wheel_rot_speed = self.speed * 2.0 
        

        for key, (node, center) in self.wheels.items():
            if not hasattr(node, 'roll_angle'): node.roll_angle = 0.0
            
            # rodas de tras sao maiores tipo 30 porcento
            radius_factor = 1.0/1.3 if 'tras' in key else 1.0 # compensar velocidade de rotacao
            scale_factor = 1.3 if 'tras' in key else 1.0
            
            node.roll_angle += wheel_rot_speed * radius_factor * dt * 10.0
            
            steer = 0.0
            if 'frente' in key:
                steer = self.steering_angle
                
            rot_mat = rotate(math.radians(steer), (0, 1, 0)) @ \
                      rotate(node.roll_angle, (1, 0, 0)) @ \
                      scale(scale_factor, scale_factor, scale_factor)
            
            node.local = get_pivot_transform(center, rot_mat)

        # atualizar volante
        if self.steering_wheel:
            self.steering_wheel.local = rotate(math.radians(self.steering_angle * 3), (0, 0, 1))

        # logica das portas todas independentes
        for key, (node, center) in self.doors.items():
            if key in self.door_states:
                state = self.door_states[key]
                target = 45.0 if state['open'] else 0.0
                state['angle'] += (target - state['angle']) * 2.0 * dt
                
                if 'esquerda' in key:
                    final_angle = -state['angle'] # negativo pra esquerda abrir pra fora
                elif 'direita' in key:
                    final_angle = state['angle'] # positivo pra direita abrir pra fora
                
                rot_mat = rotate(math.radians(final_angle), (0, 1, 0))
                node.local = get_pivot_transform(center, rot_mat)

    def toggle_door(self, door_key):
        if door_key in self.door_states:
            self.door_states[door_key]['open'] = not self.door_states[door_key]['open']

class GarageController:
    def __init__(self, left_gate, right_gate, left_pivot, right_pivot):
        self.left_gate = left_gate
        self.right_gate = right_gate
        self.left_pivot = left_pivot
        self.right_pivot = right_pivot
        
        self.is_open = False
        self.angle = 0.0
        self.max_angle = 90.0 # graus
        
    def update(self, dt):
        target = self.max_angle if self.is_open else 0.0
        self.angle += (target - self.angle) * 2.0 * dt
        
        # rotacao em torno do eixo x pra abrir pra cima
        # dobradica ta no topo
        # pra abrir pra fora e pra cima a rotacao tem que ser negativa tipo regra da mao direita
        # z positivo e pra tras ou pra frente sei la opengl e confuso
        # carro olha pra menos z e garagem abre pra z
        # vamo tentar angulo negativo
        
        rot = rotate(math.radians(-self.angle), (1, 0, 0))
        
        self.left_gate.local = get_pivot_transform(self.left_pivot, rot)
        self.right_gate.local = get_pivot_transform(self.right_pivot, rot)
        
    def toggle(self):
        self.is_open = not self.is_open

def load_obj_node(path, name, color=None, alpha=1.0, specular=(1,1,1), shininess=32.0, center=False):
    try:
        model = OBJModel(path)
        c = (0,0,0)
        if center: c = model.get_center()
        model.build()
        node = model.to_node(name)
        
        # substituir propriedades do material recursivamente
        def set_props(n):
            if color: n.mat_diffuse = color
            n.mat_alpha = alpha
            n.mat_specular = specular
            n.mat_shininess = shininess
            for c in n.children: set_props(c)
            
        set_props(node)
        return node, model

    except Exception as e:
        print(f"Falha ao carregar {path}: {e}")
        return Node(name), None

def apply_texture_recursive(node, texture_id):
    if node.mesh:
        node.mesh.texture_id = texture_id
    for c in node.children:
        apply_texture_recursive(c, texture_id)

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
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED) # capturar rato
    
    # inicializar shader
    try:
        shader = ShaderProgram()
    except Exception as e:
        print(e)
        sys.exit(1)
        
    # camara
    camera = Camera(radius=15.0, height=8.0)
    
    # construcao da cena
    cube_mesh = create_cube_mesh(1.0)
    # chao
    # aumentar tamanho pra 150 e repeticao pra 30
    grid_mesh = create_grid_mesh(150, 30) 
    
    root = Node("Root")

    floor = Node("Floor", mesh=grid_mesh, 
                 material_diffuse=(0.8, 0.8, 0.8),
                 material_specular=(0.0, 0.0, 0.0),  # sem reflexao especular
                 material_shininess=1.0)  # superficie mate
    tex_id = load_texture("../models/grass.jpg")
    if tex_id: floor.mesh.texture_id = tex_id
    root.add(floor)

    # skybox esfera com textura panoramica
    sky_tex = load_texture("../models/sky_panoramic.jpg")
    if sky_tex:
        sky_mesh = create_sphere_mesh(500.0, 64, 64) # esfera grande
        # material emissivo 1 1 1 multiplicado pela textura diffuse e spec a 0 pra nao ter luz
        skybox = Node("Skybox", mesh=sky_mesh, 
                      material_emission=(1.0, 1.0, 1.0), 
                      material_diffuse=(0.0, 0.0, 0.0),
                      material_specular=(0.0, 0.0, 0.0)) 
        skybox.mesh.texture_id = sky_tex
        root.add(skybox)
    
    # sol esfera brilhante como fonte de luz
    sun_pos = np.array([200.0, 150.0, 200.0], dtype=np.float32)  # posicao do sol
    sun_mesh = create_sphere_mesh(20.0, 32, 32)  # esfera de raio 20
    sun = Node("Sun", mesh=sun_mesh,
               local=translate(sun_pos[0], sun_pos[1], sun_pos[2]),
               material_emission=(3.0, 2.5, 1.5),  # amarelo laranja brilhante
               material_diffuse=(0.0, 0.0, 0.0),
               material_specular=(0.0, 0.0, 0.0))
    root.add(sun)
    
    # construcao do carro
    car_root = Node("CarRoot")
    
    # no rotador pra corrigir orientacao tipo 180 graus
    # se o carro tiver virado pra tras rodar 180 em y deve corrigir
    car_orient = Node("CarOrient", local=rotate(math.radians(180), (0, 1, 0)))
    car_root.add(car_orient)

    # chassis pintura azul
    chassis, _ = load_obj_node("../models/carrocaria.obj", "ChassisModel", 
                            color=(0.0, 0.3, 0.9), specular=(1.0, 1.0, 1.0), shininess=64.0, center=False)
    car_orient.add(chassis)
    
    # luzes
    luz_frente, _ = load_obj_node("../models/luz_frente.obj", "LuzFrente", color=(1.0, 1.0, 0.9))
    luz_tras, _ = load_obj_node("../models/luz_tras.obj", "LuzTras", color=(0.8, 0.0, 0.0))
    luz_tras, _ = load_obj_node("../models/luz_tras.obj", "LuzTras", color=(0.8, 0.0, 0.0))
    car_orient.add(luz_frente, luz_tras)

    # configuracao do interior ajuste aqui
    
    # 1 banco racing seat
    # posicao x y z tipo x lateral y altura z frente tras
    seat_pos = (-0.30, -0.25, -0.2) 
    
    # escala tamanho do banco
    seat_scale = 0.075 # reduzido pra um quarto de 015
    
    # rotacao ajuste se o banco tiver virado pro lado errado
    seat_rot_y = 90.0 # graus rodar 90 pra esquerda

    seat_mount = Node("SeatMount", local=translate(seat_pos[0], seat_pos[1], seat_pos[2]) @ \
                                         rotate(math.radians(seat_rot_y), (0, 1, 0)) @ \
                                         scale(seat_scale, seat_scale, seat_scale))
    seat_node, seat_model = load_obj_node("../models/racing_seat_completed.obj", "RacingSeat", 
                                          color=(0.2, 0.2, 0.2), specular=(0.5, 0.5, 0.5), shininess=16.0, center=True)
    seat_mount.add(seat_node)
    car_orient.add(seat_mount)

    # 2 volante
    volante_node, volante_model = load_obj_node("../models/volante.obj", "Volante", 
                                                color=(0.1, 0.1, 0.1), specular=(0.8, 0.8, 0.8), shininess=64.0, center=True)
    
    # posicao x y z
    vol_pos = (-0.30, 0.25, -0.6) 
    
    # escala
    vol_scale = 0.65 
    
    # inclinacao graus ajustar angulo da coluna de direcao
    vol_tilt = 20.0
    
    volante_mount = Node("VolanteMount", local=translate(vol_pos[0], vol_pos[1], vol_pos[2]) @ \
                                               rotate(math.radians(vol_tilt), (1, 0, 0)) @ \
                                               scale(vol_scale, vol_scale, vol_scale))
    
    volante_mount.add(volante_node)
    car_orient.add(volante_mount)
    
    # rodas separadas
    wheels = {}
    wheel_files = {
        'frente_esquerda': 'roda_frente_esquerda',
        'frente_direita': 'roda_frente_direita',
        'tras_esquerda': 'roda_tras_esquerda',
        'tras_direita': 'roda_tras_direita'
    }
    
    for key, name in wheel_files.items():
        # carregar e centrar logicamente
        node, model = load_obj_node(f"../models/{name}.obj", name, 
                                     color=(0.1, 0.1, 0.1), specular=(0.8, 0.8, 0.8), shininess=32.0, center=True)
        
        # pivot da roda e o centro geometrico
        center = model.get_center()

        # mount identity assumindo vertices globais
        mount = Node(name + "_Mount") 
        mount.add(node)
        car_orient.add(mount)
        
        wheels[key] = (mount, center)

    # portas separadas
    doors = {}
    door_files = {
        'frente_esquerda': 'porta_frente_esquerda',
        'frente_direita': 'porta_frente_direita',
        'tras_esquerda': 'porta_tras_esquerda',
        'tras_direita': 'porta_tras_direita'
    }
    
    # mapeamento de vidros e retrovisores pra cada porta
    glass_files = {
        'frente_esquerda': 'vidro_porta_frente_esquerdo',
        'frente_direita': 'vidro_porta_frente_direito',
        'tras_esquerda': 'vidro_porta_tras_esquerdo',
        'tras_direita': 'vidro_porta_tras_direito'
    }
    
    mirror_files = {
        'frente_esquerda': 'retrovisor_fora_esquerda',
        'frente_direita': 'retrovisor_fora_direita'
    }

    for key, name in door_files.items():
        # carregar porta
        door_node, door_model = load_obj_node(f"../models/{name}.obj", name, 
                                               color=(0.0, 0.3, 0.9), specular=(1.0, 1.0, 1.0), shininess=64.0, center=True)
        
        # calcular pivot baseado nos limites tipo bounding box
        # esquerda min x direita max x
        # dobradica provavelmente na frente do carro tipo min z ou max z
        # assumindo min z como frente baseado em opengl padrao
        # experimentar min z pro pivot z
        min_v, max_v = door_model.get_bounds()
        center = door_model.get_center()
        
        pivot_x = center[0]
        if 'esquerda' in key: pivot_x = min_v[0]
        elif 'direita' in key: pivot_x = max_v[0]
        
        # ajustar z pra ponta da porta assumindo que a porta e comprida em z
        # se as portas abrem normalmente a dobradica e na frente
        # vamo tentar min z tipo frente se for portas de tras talvez max z
        # por agora min z pra todas
        pivot_z = min_v[2] # tentativa de dobradica na frente
            
        pivot = (pivot_x, center[1], pivot_z)
        
        
        mount = Node(name + "_Mount") # identity transform
        mount.add(door_node)
        car_orient.add(mount)
        
        doors[key] = (mount, pivot)
        
        # carregar vidro e ligar a porta
        if key in glass_files:
            g_name = glass_files[key]
            glass, _ = load_obj_node(f"../models/{g_name}.obj", g_name,
                                     color=(0.2, 0.3, 0.4), alpha=0.4, specular=(1,1,1), shininess=128)
            door_node.add(glass)
            
        # carregar retrovisor e ligar a porta
        if key in mirror_files:
            m_name = mirror_files[key]
            mirror, _ = load_obj_node(f"../models/{m_name}.obj", m_name, color=(0.1, 0.1, 0.1))
            door_node.add(mirror)

    # outros vidros parabrisas e atras estaticos
    parabrisas, _ = load_obj_node("../models/parabrisas.obj", "Parabrisas", 
                               color=(0.2, 0.3, 0.4), alpha=0.4, specular=(1,1,1), shininess=128)
    vidro_atras, _ = load_obj_node("../models/vidro_atras.obj", "VidroAtras", 
                               color=(0.2, 0.3, 0.4), alpha=0.4, specular=(1,1,1), shininess=128)
    car_orient.add(parabrisas, vidro_atras)
    
    # interior
    # banco racing seat
    # posicionar no lado do condutor esquerda
    seat_node, seat_model = load_obj_node("../models/racing_seat_completed.obj", "RacingSeat", 
                                          color=(0.2, 0.2, 0.2), specular=(0.5, 0.5, 0.5), shininess=16.0, center=True)
    
    # ajustar posicao tentativa inicial
    root.add(car_root)
    
    car_ctrl = CarController(car_root, chassis, wheels, doors, volante_node)
    
    # construcao da garagem modelos novos
    garage_root = Node("Garage", local=translate(0, 0, 0)) # assumindo origem centrada no blend
    
    # 1 estrutura fora
    # 1 estrutura fora
    struct_node, struct_model = load_obj_node("../models/garagem_parte_fora_paredes.obj", "GarageStruct", 
                                              color=(0.7, 0.7, 0.7), specular=(0.2, 0.2, 0.2), center=False)
    
    # aplicar textura de parede
    wall_tex = load_texture("../models/wall.jpg")
    if wall_tex: apply_texture_recursive(struct_node, wall_tex)
    
    garage_root.add(struct_node)
    
    # 2 estrutura dentro
    struct_node, struct_model = load_obj_node("../models/garagem_parte_dentro_luzes.obj", "GarageLights", 
                                              color=(0.7, 0.7, 0.7), specular=(0.2, 0.2, 0.2), center=False)
    garage_root.add(struct_node)

    # 3 piso
    struct_node, floor_model = load_obj_node("../models/garagem_parte_dentro_pilares.obj", "GaragePillars", 
                                            color=(0.7, 0.7, 0.7), specular=(0.2, 0.2, 0.2), center=False)
    garage_root.add(struct_node)
    
    # 4 portoes
    # textura do portao
    gate_tex = load_texture("../models/garage_door.jpg")

    # esquerda
    gate_l_node, gate_l_model = load_obj_node("../models/garagem_portao.obj", "GateLeft", 
                                              color=(0.8, 0.8, 0.8), center=False)
    if gate_tex: apply_texture_recursive(gate_l_node, gate_tex)
    
    # pivot em cima max y
    gl_min, gl_max = gate_l_model.get_bounds()
    # centro x pra simetria
    center_x = (gl_min[0] + gl_max[0]) / 2.0
    
    # pivot centro x do portao topo y frente z
    # usando min z como frente da folha do portao
    gate_pivot = (center_x, gl_max[1], gl_min[2]) 
    
    gate_l_mount = Node("GateL_Mount") 
    gate_l_mount.add(gate_l_node)
    garage_root.add(gate_l_mount)

    # direita
    # o modelo e o mesmo se tiver centrado na origem temos que mover pros lados
    # se tiver na esquerda global temos que mover pra direita
    # ajuste manual do offset
    
    gate_r_node, _ = load_obj_node("../models/garagem_portao.obj", "GateRight", 
                                   color=(0.8, 0.8, 0.8), center=False)
    if gate_tex: apply_texture_recursive(gate_r_node, gate_tex)
    
    gate_r_mount = Node("GateR_Mount")
    gate_r_mount.add(gate_r_node)
    
    # ajuste aqui offset pra separar os portoes
    # se tao sobrepostos tenta valores tipo 5 6 10 ou negativos
    # se center x for a posicao original tipo menos 3 entao menos 2 vezes menos 3 da mais 6 move pra mais 3
    # se tiverem a sobrepor talvez o offset automatico tenha sido 0
    
    gate_r_offset_val = 28.3 # tenta mudar isto tipo 5 6 menos 6
    
    gate_r_offset = Node("GateR_Offset", local=translate(gate_r_offset_val, 0, 0))
    gate_r_offset.add(gate_r_mount)
    garage_root.add(gate_r_offset)
    
    root.add(garage_root)
    
    # controlador
    # nota passamos gate r mount que roda no sitio errado mas como ta dentro do gate r offset
    # visualmente aparece no sitio certo a rodar sobre o proprio eixo que e igual ao da esquerda
    garage_ctrl = GarageController(gate_l_mount, gate_r_mount, gate_pivot, gate_pivot)
    
    # estado de input
    inputs = {'w': False, 's': False, 'a': False, 'd': False, 'q': False, 'e': False, '1': False}
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
            # removido pra usar 3 4 5 6
            
            if key == glfw.KEY_3: car_ctrl.toggle_door('frente_direita')
            if key == glfw.KEY_4: car_ctrl.toggle_door('frente_esquerda')
            if key == glfw.KEY_5: car_ctrl.toggle_door('tras_direita')
            if key == glfw.KEY_6: car_ctrl.toggle_door('tras_esquerda')
            if key == glfw.KEY_7: 
                camera.mode = "FREE" if camera.mode != "FREE" else "ORBIT"
            
            if key == glfw.KEY_1: inputs['1'] = not inputs['1'] # toggle ao pressionar
            if key == glfw.KEY_2:
                if camera.mode == "FIRST_PERSON":
                    camera.mode = "ORBIT"
                else:
                    camera.mode = "FIRST_PERSON"
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
        # calculo delta simples
        pass 

    # melhor manuseamento do rato
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
            camera.zoom(0.9) # zoom in
        elif yoffset < 0:
            camera.zoom(1.1) # zoom out

    glfw.set_key_callback(window, key_callback)
    glfw.set_cursor_pos_callback(window, mouse_callback_impl)
    glfw.set_scroll_callback(window, scroll_callback)
    
    # loop
    last_time = glfw.get_time()
    
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE) # correcao pra partes internas invisiveis
    
    # alpha blending
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    while not glfw.window_should_close(window):
        t = glfw.get_time()
        dt = t - last_time
        last_time = t
        
        glfw.poll_events()
        
        # atualizar
        if camera.mode == "FREE":
            camera.update_free_cam(dt, inputs, (mouse_dx, mouse_dy))
        else:
            car_ctrl.update(dt, inputs)
            
            if camera.mode == "FIRST_PERSON":
                # posicao da cabeca tipo driver head
                # offset relativo ao car orient que ta rodado 180
                # seat menos 030 menos 025 menos 02 volante z menos 06
                # cabeca anterior menos 025
                # ajuste mover pra tras direcao mais z local do car orient pois menos z e frente world
                # tentativa 01 mais pra tras que menos 025
                head_local = np.array([-0.30, 0.40, 0.1, 1.0], dtype=np.float32)
                
                # transformacao pra world
                # 1 car orient rotate 180 y
                # 2 car root translate pos mais rotate yaw
                
                car_rot = rotate(car_ctrl.yaw, (0, 1, 0))
                mesh_orient = rotate(math.radians(180), (0, 1, 0))
                
                total_rot = car_rot @ mesh_orient
                
                head_pos_rel = total_rot @ head_local
                head_world = car_ctrl.position + head_pos_rel[:3]
                
                camera.position = head_world
                
                # forward vector alinhado com o carro
                cy = car_ctrl.yaw
                camera.front = np.array([math.sin(cy), 0, math.cos(cy)], dtype=np.float32)
                camera.up = np.array([0, 1, 0], dtype=np.float32)
                
            else:
                # camara inteligente tipo smart follow camera
                # angulo base e o yaw do carro mais 180 pois o modelo foi rodado
                base_angle = math.degrees(car_ctrl.yaw) + 180
                
                # input do rato adiciona a um angulo offset
                if mouse_dx != 0:
                    camera.angle_offset = getattr(camera, 'angle_offset', 0.0) - mouse_dx * 0.2
                    camera.last_mouse_time = t
                
                # auto alinhar se sem input por 2 segundos
                if t - getattr(camera, 'last_mouse_time', 0.0) > 2.0:
                    # decair offset pra 0
                    offset = getattr(camera, 'angle_offset', 0.0)
                    camera.angle_offset = offset * (1.0 - 5.0 * dt) # decaimento suave
                    if abs(camera.angle_offset) < 0.1: camera.angle_offset = 0.0
                
                camera.angle = base_angle + getattr(camera, 'angle_offset', 0.0)
                camera.center = car_ctrl.position
            
        mouse_dx, mouse_dy = 0, 0 # reset delta
        
        garage_ctrl.update(dt)
        
        # renderizar
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        width, height = glfw.get_framebuffer_size(window)
        glViewport(0, 0, width, height)
        
        # fov dinamico
        current_fov = 90.0 if camera.mode == "FIRST_PERSON" else 60.0
        
        P = perspective(current_fov, width/height, 0.1, 1000.0)
        V, eye_pos = camera.get_view_matrix()
        VP = P @ V
        
        shader.use()
        shader.set_view_pos(eye_pos)
        
        # luzes
        # sol como fonte de luz principal
        shader.set_light(0, sun_pos, (0.3, 0.3, 0.2), (1.0, 0.95, 0.8), (1.0, 1.0, 0.9), cutoff=-1.0)
        # luz ambiente suave
        shader.set_light(1, (0, 50, 0), (0.2, 0.2, 0.25), (0.3, 0.3, 0.4), (0.2, 0.2, 0.2), cutoff=-1.0)
        
        # logica dos farois
        headlights_on = inputs['1']
        
        # calcular vetores forward e right do carro
        # yaw do carro e car ctrl yaw
        # forward e sin yaw 0 cos yaw
        cy = car_ctrl.yaw
        fwd = np.array([math.sin(cy), 0, math.cos(cy)])
        right = np.array([math.cos(cy), 0, -math.sin(cy)])
        up = np.array([0, 1, 0])
        
        # posicao do carro
        car_pos = car_ctrl.position
        
        # posicoes dos farois
        hl_intensity = (0,0,0)
        
        # auxiliar pra definir emissao recursivamente
        def set_emission_recursive(node, emission):
            node.mat_emission = emission
            for c in node.children:
                set_emission_recursive(c, emission)
        
        if headlights_on:
            hl_intensity = (1.0, 1.0, 0.9) # brilhante levemente amarelo
            set_emission_recursive(luz_frente, (1.0, 1.0, 0.8)) # brilho do mesh
        else:
            set_emission_recursive(luz_frente, (0.0, 0.0, 0.0)) # sem brilho
            
        # direcao do spotlight ligeiramente pra baixo
        spot_dir = fwd - up * 0.2
        # cutoff do spotlight cosseno do angulo 20 graus tipo 094
        spot_cutoff = math.cos(math.radians(20))
            
        # farol esquerdo
        l_pos = car_pos + fwd * 1.2 - right * 0.6 + up * 0.5
        shader.set_light(2, l_pos, (0,0,0), hl_intensity, hl_intensity, direction=spot_dir, cutoff=spot_cutoff)
        
        # farol direito
        r_pos = car_pos + fwd * 1.2 + right * 0.6 + up * 0.5
        shader.set_light(3, r_pos, (0,0,0), hl_intensity, hl_intensity, direction=spot_dir, cutoff=spot_cutoff)
        
        # logica das luzes de marcha atras
        # se mover pra tras velocidade menor que menos 01 ou pressionar s
        reversing = inputs['s'] or car_ctrl.speed < -0.1
        if reversing:
            set_emission_recursive(luz_tras, (2.0, 0.0, 0.0)) # vermelho muito brilhante
        else:
            set_emission_recursive(luz_tras, (0.3, 0.0, 0.0)) # vermelho escuro luzes traseiras sempre ligadas
        
        root.draw(shader, np.eye(4, dtype=np.float32), VP)
        
        glfw.swap_buffers(window)
        
    glfw.terminate()

if __name__ == "__main__":
    main()
