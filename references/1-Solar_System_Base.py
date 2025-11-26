# OpenGL clássico 
# Sistema solar simples : 2 planetas + 1 lua


import sys, math
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

#Funções de Geometria
def draw_sphere(color=(0.8, 0.85, 0.95)):
    # Função por omissão para criação de esfera com  normais
    glColor3f(*color)
    glutSolidSphere(1,24,24)

def create_star_geometry():
    return lambda: draw_sphere((1.0, 0.75, 0.5))   # cor quente

def create_planetA_geometry():
    return lambda: draw_sphere((0.6, 0.8, 1.0)) 

def create_planetB_geometry():
    return lambda: draw_sphere((0.45, 0.25, 0.45)) #arroxeado

def create_moon_geometry():
    return lambda: draw_sphere((0.8, 0.8, 0.9)) #branco azulado

# criação da Geometria da cena <-funções separadas para maior flexibilidade
draw_star   = create_star_geometry()
draw_planetA = create_planetA_geometry()
draw_planetB = create_planetB_geometry()
draw_moon   = create_moon_geometry()


# Variáves globais
WIN_W, WIN_H = 800, 600

#angulos das orbitas
thetaA = 0.0   
thetaB = 0.0   
thetaM = 0.0   

#velocidades
SPEED_A = 360.0 / 10.0   # uma volta em 10 segundos
SPEED_B = 360.0 / 20.0   # uma volta em 20 segs
SPEED_M = 360.0 /  2.0   

last_time = 0.0


# Raios e escalas
R_A = 8.0      
R_B = 20.0     
R_M = 2.5      # distancia ao planeta A

S_SUN    = (3.0, 3.0, 3.0)
S_PLANETA = (1.0, 1.0, 1.0)
S_PLANETB = (2.0, 2.0, 2.0)
S_MOON   = (0.5, 0.5, 0.5)


# Setup do OpenGL
def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)

    # Iluminação
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0.45, 0.9, 0.35, 0.0)) 
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 2, 1, 0.0))  # direccional

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


#IMPORTANTE <- ver o stack de matrizes aqui
def display():
    glClearColor(0.05, 0.05, 0.25, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Camera
    gluLookAt(20.0, 12.0, 22.0,   0.0, 0.0, 0.0,   0.0, 1.0, 0.0)
    # Inclinação em X e Y para ver melhor
    glRotatef(18.0, 1,0,0)
    glRotatef(28.0, 0,1,0)

    # desenhar MUNDO (stack level 0) 
    glPushMatrix()

    # Desenhar o SOL --------------------------------------------------
    glPushMatrix()
    # Não há translação!
    glScalef(*S_SUN)
    draw_star()
    glPopMatrix()
    # --- fim do SOL-----------------------------------------------------

    # --- PLANETA A e Lua ------------------------------------------------
    # MUNDO-> OrbitA Rotação em volta do yy
    glPushMatrix()
    glRotatef(thetaA, 0 , 1, 0)      # 2. Rotaçaõ à volta do Sol (theta)
    glTranslatef(R_A, 0, 0)          # 1. Deslocação para o raio da órbita

    # Desenhar Planeta A
    glPushMatrix()
    glScalef(*S_PLANETA)
    draw_planetA()
    glPopMatrix()

    # Mundo -> OrbitA -> LuaOrbitA (Lua à volta do Planeta A)
    glPushMatrix()
    glRotatef(thetaM, 0, 1, 0)      # 1. Orbita Lunar à volta do Planeta A
    glTranslatef(R_M, 0, 0)         # 2. Translacção para a orbita

    # Desenha Lua
    glPushMatrix()
    glScalef(*S_MOON)
    draw_moon()
    glPopMatrix()

    glPopMatrix()  # pop MoonOrbitA
    glPopMatrix()  # pop OrbitA
    # --- FIM PLANETA A & Lua ----------------------------------------

    # --- PLANETA B ----------------------------------------------------
    # MUNDO -> OrbitB 
    glPushMatrix()
    glRotatef(thetaB, 0, 1, 0)      # 1. Rotação à volta do Sol
    glTranslatef(R_B, 0, 0)         # 2. Coloca o planeta na órbita

    # Desenha Planeta B
    glPushMatrix()
    glScalef(*S_PLANETB)
    draw_planetB()
    glPopMatrix()

    glPopMatrix()  # pop OrbitB
    # --- fim PLANETA B ------------------------------------------------

    glPopMatrix() 

    glutSwapBuffers()

#Animação <- aqui são alteradas as variáveis globais com os ângulos
def idle():
    global last_time, thetaA, thetaB, thetaM
    t_ms = glutGet(GLUT_ELAPSED_TIME) #isto vai ser feito em função do tempo decorrido
    t = t_ms * 0.001
    if last_time == 0.0: last_time = t
    dt = t - last_time #calcular o Delta_t
    last_time = t

    # muda os ângulos (deg)
    thetaA = (thetaA + SPEED_A * dt) % 360.0
    thetaB = (thetaB + SPEED_B * dt) % 360.0
    thetaM = (thetaM + SPEED_M * dt) % 360.0

    glutPostRedisplay()

def keyboard(key, x, y):
    if key == b'\x1b':  # ESC sai
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit(0)

def main():
    glutInit(sys.argv)

    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Classic OpenGL - Stack de matrizes explicito (Esc - sai)")

    init_gl()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutMainLoop()

if __name__ == "__main__":
    main()
