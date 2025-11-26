import sys, math, time
from dataclasses import dataclass
from typing import Optional, Tuple
from time import time

import glfw
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

PALETTE = {
    "R": (0.90, 0.30, 0.30),
    "G": (0.30, 0.90, 0.30),
    "B": (0.30, 0.60, 0.95),
    "Y": (0.95, 0.80, 0.25),
    "C": (0.20, 0.85, 0.85),
    "M": (0.85, 0.40, 0.85),
    "O": (0.95, 0.60, 0.25),
    "P": (0.70, 0.55, 0.95),
}

ALPHA_OUTER =1.0
ALPHA_INNER =1.0

#É aqui que é construído o labirinto como um conjunto de paredes
def make_maze():
    H, T, R = 2.5, 0.15, 4.0
    a_outer = ALPHA_OUTER
    a_inner = ALPHA_INNER
    walls = []
    # Outer rectangle
    walls += [
        make_wall("Outer_North", (-R, -R), ( R, -R), "R", a_outer),
        make_wall("Outer_South", (-R,  R), ( R,  R), "R", a_outer),
        make_wall("Outer_West",  (-R, -R), (-R,  R), "G", a_outer),
        make_wall("Outer_East",  ( R, -R), ( R,  R), "G", a_outer),
    ]
    # corredores
    walls += [
        make_wall("A", (-3.0, -3.0), ( 1.0, -3.0), "B", a_inner),
        make_wall("B", ( 1.0, -3.0), ( 1.0, -1.0), "O", a_inner),
        make_wall("C", (-3.0, -1.0), ( 1.0, -1.0), "G", a_inner),
        make_wall("D", (-3.0,  1.0), (-1.0,  1.0), "M", a_inner),
        make_wall("E", (-1.0,  1.0), (-1.0,  3.0), "C", a_inner),
        make_wall("F", (-1.0,  3.0), ( 3.0,  3.0), "Y", a_inner),
        make_wall("G", ( 3.0, -1.5), ( 3.0,  3.0), "O", a_inner),
        make_wall("H", ( 1.0, -1.5), ( 3.0, -1.5), "P", a_inner),
    ]
    return walls



#funções auxiliares <- normais em 2D para a BSP e 
def norm2(a):
    L = np.linalg.norm(a)
    return a / L if L > 1e-8 else np.zeros_like(a)

def perp_right(n):
    return np.array([n[1], -n[0]], dtype=np.float32)

#paredes como data classes do Python
@dataclass
class Wall:
    name: str
    p1: np.ndarray
    p2: np.ndarray
    height: float = 2.5
    thickness: float = 0.15
    color: Tuple[float, float, float, float] = (0.8, 0.2, 0.2, 1.0)  # RGBA
    color_abbr: str = "?"
    
    def center_len_angle(self):
        # vector direccional da parede em XZ
        d = self.p2 - self.p1
        # comprimento da parede
        length = float(np.linalg.norm(d))
        # centro do segmento
        c = 0.5 * (self.p1 + self.p2)
        # ângulo da parede em torno de Y (no plano XZ)
        angle = float(np.arctan2(d[1], d[0]))  # yaw around Y
        return (float(c[0]), float(c[1])), length, angle

    def plane(self):
        # direcção da parede
        d = self.p2 - self.p1
        # normal 2D (no plano XZ), obtida por rotação de 90º
        n = norm2(perp_right(d))
        # ponto de referência do "plano" (na prática, recta em XZ)
        p = 0.5 * (self.p1 + self.p2)  # midpoint
        return p, n

@dataclass
class BSPNode:
    wall: Wall
    back: Optional['BSPNode']
    front: Optional['BSPNode']
    

# Classifica um ponto 2D (x,z) em relação a um plano (recta) definido por um ponto na recta e a normal 2D dessa recta
# se o resultado for >0  o ponto está de um lado da frente na normal, caso contrário está atrás (0, está na recta!)
def classify_point_to_plane(pt_xz, plane_point, plane_normal):
    # Vector do ponto de referência do plano até ao ponto que queremos classificar
    v = pt_xz - plane_point
    # Produto escalar com a normal: o sinal indica em que lado estamos
    return float(np.dot(v, plane_normal))


#esta é parte importante! É aqui que se define a BSP
def build_bsp(walls):
    if not walls:
        return None
    splitter = walls[0]
    p, n = splitter.plane()
    back_list, front_list = [], []
    for w in walls[1:]:
        mid = 0.5 * (w.p1 + w.p2)
        s = classify_point_to_plane(mid, p, n)
        (back_list if s < 0 else front_list).append(w)
    return BSPNode(
        wall=splitter,
        back=build_bsp(back_list),
        front=build_bsp(front_list)
    )


class Camera:
    def __init__(self, eye=(0.5, 0.1, 0.5), yaw=0.0, pitch=1.0):
        self.eye = np.array(eye, dtype=np.float32)  # [x, y, z]
        self.yaw = float(yaw)   # rot no eixo dos y
        self.pitch = float(pitch)  # rot no eixo dos x
        self.speed = 2.0
        self.turn_speed = math.radians(90)

    def forward_dir(self):
        #define a matriz de deslocação para a frente sabendo os ângulos para onde a câmara está a andar, em X e Z
        return np.array([math.cos(self.yaw), 0.0, math.sin(self.yaw)], dtype=np.float32)

    def move_forward(self, amount):
        # desloca a câmara para a frente/atrás ao longo da direcção de "forward"
        self.eye += self.forward_dir() * amount

    def yaw_left(self, amount_rad):
        # ângulo no eixo dos y (para onde se olha (esq/dir))
        self.yaw += amount_rad


def draw_floor(size=10, step=1.0):
    glDisable(GL_LIGHTING)
    glColor3f(0.15, 0.15, 0.18)
    glBegin(GL_QUADS)
    glVertex3f(-size, 0.0, -size)
    glVertex3f( size, 0.0, -size)
    glVertex3f( size, 0.0,  size)
    glVertex3f(-size, 0.0,  size)
    glEnd()

def draw_box(length=1.0, width=0.1, height=2.0):
    lx, wy, lz = length*0.5, height*0.5, width*0.5
    glBegin(GL_QUADS)
    # +X
    glNormal3f(1,0,0)
    glVertex3f( lx,-wy,-lz); glVertex3f( lx,-wy, lz); glVertex3f( lx, wy, lz); glVertex3f( lx, wy,-lz)
    # -X
    glNormal3f(-1,0,0)
    glVertex3f(-lx,-wy, lz); glVertex3f(-lx,-wy,-lz); glVertex3f(-lx, wy,-lz); glVertex3f(-lx, wy, lz)
    # +Y
    glNormal3f(0,1,0)
    glVertex3f(-lx, wy,-lz); glVertex3f( lx, wy,-lz); glVertex3f( lx, wy, lz); glVertex3f(-lx, wy, lz)
    # -Y
    glNormal3f(0,-1,0)
    glVertex3f(-lx,-wy, lz); glVertex3f( lx,-wy, lz); glVertex3f( lx,-wy,-lz); glVertex3f(-lx,-wy,-lz)
    # +Z
    glNormal3f(0,0,1)
    glVertex3f(-lx,-wy, lz); glVertex3f(-lx, wy, lz); glVertex3f( lx, wy, lz); glVertex3f( lx,-wy, lz)
    # -Z
    glNormal3f(0,0,-1)
    glVertex3f( lx,-wy,-lz); glVertex3f( lx, wy,-lz); glVertex3f(-lx, wy,-lz); glVertex3f(-lx,-wy,-lz)
    glEnd()

def draw_wall(wall):
    (cx, cz), length, angle = wall.center_len_angle()
    glPushMatrix()
    glTranslatef(cx, wall.height * 0.5, cz)
    glRotatef(np.degrees(angle), 0, 1, 0)
    r, g, b, a = wall.color
    glColor4f(r, g, b, a)
    glEnable(GL_LIGHTING)
    draw_box(length=length, width=wall.thickness, height=wall.height)
    glPopMatrix()

    
# Ordem de desenho da BSP
draw_order = []

#de trás para a frente
def traverse_and_draw(node, cam_xz):
    global draw_order
    if node is None:
        return
    p, n = node.wall.plane()
    side = classify_point_to_plane(cam_xz, p, n)
    ident = f"{node.wall.name}[{node.wall.color_abbr}]"
    if side > 0:
        traverse_and_draw(node.back, cam_xz)
        draw_wall(node.wall)
        draw_order.append(ident)
        traverse_and_draw(node.front, cam_xz)
    else:
        traverse_and_draw(node.front, cam_xz)
        draw_wall(node.wall)
        draw_order.append(ident)
        traverse_and_draw(node.back, cam_xz)

#da frente para trás
def traverse_and_draw_front_to_back(node, cam_xz):
    if node is None:
        return
    p, n = node.wall.plane()
    side = float(np.dot(cam_xz - p, n))
    if side > 0:          # camera na frente
        near, far = node.front, node.back
    else:                  # camera atrás
        near, far = node.front, node.back  # (esta versão está "simétrica")

    # Recursar 1
    traverse_and_draw_front_to_back(near, cam_xz)
    # Desenha parede e actualiza a lista
    draw_wall(node.wall)
    draw_order.append(f"{node.wall.name}[{node.wall.color_abbr}]")
    # Recursa 2
    traverse_and_draw_front_to_back(far, cam_xz)



def make_wall(name, p1, p2, abbr, alpha, h=2.5, t=0.15):
    rgb = PALETTE[abbr]
    return Wall(
        name=name, 
        p1=np.array(p1, dtype=np.float32),
        p2=np.array(p2, dtype=np.float32),
        height=h, 
        thickness=t,
        color=(rgb[0], rgb[1], rgb[2], float(alpha)),
        color_abbr=abbr
    )


#input
keys_down = set()

def key_callback(window, key, scancode, action, mods):
    global keys_down
    if action == glfw.PRESS:
        keys_down.add(key)
    elif action == glfw.RELEASE:
        keys_down.discard(key)
    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)

#setup do OpenGL
def init_gl(w, h):
    glViewport(0, 0, w, h)
    glEnable(GL_DEPTH_TEST)
    #glEnable(GL_CULL_FACE)
    #glCullFace(GL_BACK)
    glShadeModel(GL_SMOOTH)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 1.0, 0.6, 0.0))  # directional
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.18, 0.18, 0.22, 1.0))
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.08, 0.08, 0.1, 1.0))
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Translucency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def set_projection(w, h):
    aspect = max(1.0, float(w)/float(max(h,1)))
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, aspect, 0.05, 100.0)
    glMatrixMode(GL_MODELVIEW)

def set_camera(cam):
    glLoadIdentity()
    f = cam.forward_dir()
    center = cam.eye + f
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    gluLookAt(cam.eye[0], cam.eye[1], cam.eye[2],
              center[0],  center[1],  center[2],
              up[0], up[1], up[2])

def main():
    if not glfw.init():
        print("Failed to initialize GLFW"); return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_FALSE)

    w, h = 800, 600
    window = glfw.create_window(w, h, "Labirinto OpenGL", None, None)
    if not window:
        glfw.terminate(); print("Failed to create GLFW window"); return
    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)

    init_gl(w, h)
    set_projection(w, h)

    # Cena
    walls = make_maze()
    bsp_root = build_bsp(walls)
    cam = Camera(eye=(-3.5, 0.15, -3.5), yaw=math.radians(45))

    last_time = time()
    draw_order_older = []

    print("\nControls: Up/Down = frente/trás  |  Esq/Dir = rodar a vista  |  Esc = Sair\n")
    while not glfw.window_should_close(window):
        now = time()
        dt = now - last_time
        last_time = now

        # Input <- isto não devia estar aqui - Código podia estar melhor
        if glfw.KEY_UP in keys_down:    cam.move_forward(cam.speed * dt)
        if glfw.KEY_DOWN in keys_down:  cam.move_forward(-cam.speed * dt)
        if glfw.KEY_LEFT in keys_down:  cam.yaw_left(-cam.turn_speed * dt)
        if glfw.KEY_RIGHT in keys_down: cam.yaw_left( cam.turn_speed * dt)

        # Render
        glClearColor(0.05, 0.06, 0.12, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        #por a câmara e o chão
        set_camera(cam)
        draw_floor(10, 1)

        # ir buscar a ordem de desenho
        global draw_order
        
        #glDepthMask(GL_FALSE)     #<-----ALTERAR AQUI
        draw_order = []
        traverse_and_draw(bsp_root, cam_xz=np.array([cam.eye[0], cam.eye[2]], dtype=np.float32))
        
        glDepthMask(GL_TRUE) #<---------------ESTE DEIXAR ESTAR - Não Mexer
        # mostrar a ordem de desenho só quando muda 
        if draw_order != draw_order_older:
            print("#### Ordem de desenho das paredes #####")
            for wname in draw_order:
                print("Desenhar:", wname)
            draw_order_older = draw_order[:]  # copy

        glfw.swap_buffers(window)
        glfw.poll_events()

        # resizes
        fbw, fbh = glfw.get_framebuffer_size(window)
        set_projection(fbw, fbh)

    glfw.terminate()

if __name__ == "__main__":
    main()
