
# Scene graph em OpenGL clássico (GLUT/GLU) com classe Node.
# Cada Node sabe aplicar a sua transformação local, desenhar a sua geometria
# e desenhar recursivamente os filhos. Animação por "updaters" por nó.

import sys, math
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# Helpers de geometria (cores e esferas)
def draw_sphere(color=(0.8, 0.85, 0.95)):
    glColor3f(*color)
    glutSolidSphere(1.0, 24, 24)

def geo_star():
    draw_sphere((0.95, 0.75, 0.35))  # estrela quente

def geo_planet_a():
    draw_sphere((0.6, 0.8, 1.0))

def geo_planet_b():
    draw_sphere((0.45, 0.25, 0.55))

def geo_moon():
    draw_sphere((0.82, 0.82, 0.9))

# Classe Node - Base do grafo de cena
#Parametros
#  geom(node): função que desenha a geometria (opcional)
#  transform(node): função que aplica as transformações locais (opcional)
#  updater(node, dt): avança o estado (opcional)
#  state: dicionário com parâmetros arbitrários do nó (ex.: ângulos, escalas)
#         que poderão ser alterados pelos vários eventos da aplicação    

class Node:
    def __init__(self, name, geom=None, transform=None, updater=None, state=None):
        self.name = name
        self.geom = geom
        self.transform = transform  #função de transformação
        self.updater = updater      #será uma função (actualiza o state)
        self.state = state or {}    #parametros da função de update e transform
        self.children = []

    #aqui acrescentam-se os filhos de cada nó
    def add(self, *kids):
        for k in kids:
            self.children.append(k)
        return self

    #aqui faz-se a actualização da geometria
    def update(self, dt):
        if self.updater:
            self.updater(self, dt)
        for c in self.children:
            c.update(dt)

    #é aqui que tudo é desenhado
    def draw(self):
        glPushMatrix()
        if self.transform:
            self.transform(self)
        if self.geom:
            self.geom()
        for c in self.children:
            c.draw()
        glPopMatrix()

# -------------------------------
# Parâmetros globais / animação
# -------------------------------
WIN_W, WIN_H = 800, 600
last_time = 0.0

# Escalas e raios
S_SUN     = (3.0, 3.0, 3.0)
S_PLANET_A= (1.0, 1.0, 1.0)
S_PLANET_B= (2.0, 2.0, 2.0)
S_MOON    = (0.5, 0.5, 0.5)

R_A = 8.0
R_B = 20.0
R_M = 2.5

# Velocidades (graus/seg)
SPEED_A = 360.0 / 10.0
SPEED_B = 360.0 / 20.0
SPEED_M = 360.0 /  2.0

# Funções de Transform  (usam state do Node)
def tf_scale(sx, sy, sz):
    def _tf(node):
        glScalef(sx, sy, sz)
    return _tf

def tf_orbit(radius, angle_key="theta"):
    # Roda em torno de Y e depois translacciona para o raio.
    def _tf(node):
        glRotatef(node.state.get(angle_key, 0.0), 0, 1, 0)
        glTranslatef(radius, 0.0, 0.0)
    return _tf

#função de actualização
def updater_spin(speed_key="speed", angle_key="theta"):
    #Avança ângulo = (ângulo + speed*dt) % 360"""
    def _upd(node, dt):
        th = node.state.get(angle_key, 0.0)
        sp = node.state.get(speed_key, 0.0)
        node.state[angle_key] = (th + sp * dt) % 360.0
    return _upd

# aqui é construído o grafo de cena
def build_scene():
    # Nó raiz (mundo) - apenas um contentor
    world = Node("World")

    # Sol
    sun = Node("Sun", geom=geo_star, transform=tf_scale(*S_SUN))

    # Órbita do Planeta A (nó transform com updater)
    orbitA = Node(
        "OrbitA",
        transform=tf_orbit(R_A, "theta"),
        updater=updater_spin(speed_key="speed", angle_key="theta"),
        state={"theta": 0.0, "speed": SPEED_A}
    )
    planetA = Node("PlanetA", geom=geo_planet_a, transform=tf_scale(*S_PLANET_A))

    # Órbita da Lua (filha de OrbitA)
    orbitM = Node(
        "OrbitMoon",
        transform=tf_orbit(R_M, "theta"),
        updater=updater_spin(speed_key="speed", angle_key="theta"),
        state={"theta": 0.0, "speed": SPEED_M}
    )
    moon = Node("Moon", geom=geo_moon, transform=tf_scale(*S_MOON))

    # Órbita do Planeta B
    orbitB = Node(
        "OrbitB",
        transform=tf_orbit(R_B, "theta"),
        updater=updater_spin(speed_key="speed", angle_key="theta"),
        state={"theta": 0.0, "speed": SPEED_B}
    )
    planetB = Node("PlanetB", geom=geo_planet_b, transform=tf_scale(*S_PLANET_B))

    # Ligações (hierarquia)
    world.add(
        sun,
        orbitA.add(
            planetA,
            orbitM.add(moon)
        ),
        orbitB.add(planetB)
    )

    return world

SCENE = None  # será criado no main()

# setup
def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)

    # Lighting (fixed-function)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    # direccional
    glLightfv(GL_LIGHT0, GL_POSITION, (0.45, 0.9, 0.35, 0.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.18, 0.18, 0.22, 1.0))

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

def reshape(w, h):
    global WIN_W, WIN_H
    WIN_W, WIN_H = max(1, w), max(1, h)
    glViewport(0, 0, WIN_W, WIN_H)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, WIN_W/float(WIN_H), 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def display():
    glClearColor(0.05, 0.05, 0.25, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Câmara
    gluLookAt(20.0, 12.0, 22.0,   0.0, 0.0, 0.0,   0.0, 1.0, 0.0)
    # Inclinação para melhor percepção de profundidade
    glRotatef(18.0, 1, 0, 0)
    glRotatef(28.0, 0, 1, 0)

    # Desenhar a cena inteira
    SCENE.draw()

    glutSwapBuffers()


# Animação

def idle():
    global last_time
    t_ms = glutGet(GLUT_ELAPSED_TIME)
    t = t_ms * 0.001
    if last_time == 0.0:
        last_time = t
    dt = t - last_time
    last_time = t

    # Actualiza toda a árvore (ângulos/estados)
    SCENE.update(dt)

    glutPostRedisplay()

def keyboard(key, x, y):
    if key == b'\x1b':  # ESC
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit(0)
    if key in (b'c', b'C'):
        if glIsEnabled(GL_CULL_FACE):
            glDisable(GL_CULL_FACE); print("Back-face culling DISABLED")
        else:
            glEnable(GL_CULL_FACE); print("Back-face culling ENABLED")

# -------------------------------
# Main
# -------------------------------
def main():
    global SCENE
    glutInit(sys.argv)

    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Grafo de Cena OO - Classic OpenGL")

    init_gl()
    SCENE = build_scene()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutMainLoop()

if __name__ == "__main__":
    main()
