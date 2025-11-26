

import sys, math
import glfw
from OpenGL.GL import *
from OpenGL.GLU import *

# Estado mínimo
smooth = False
angle_y = 0.0
quadric = None

# Câmara e luz
CAM_POS = (0.0, 2.0, 6.0)
LOOK_AT = (0.0, 0.0, 0.0)
UP      = (0.0, 1.0, 0.0)

LIGHT_RADIUS   = 3.0
LIGHT_Y_OFFSET = -2.0      # abaixo do chão
LIGHT_CUTOFF   = 20.0     # cone um pouco largo
LIGHT_EXPONENT = 20.0

def on_key(win, key, sc, action, mods):
    global smooth
    if action != glfw.PRESS: return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(win, True)
    elif key == glfw.KEY_C:
        smooth = not smooth
        glShadeModel(GL_SMOOTH if smooth else GL_FLAT)
        print("Sombreamento:", "GL_SMOOTH" if smooth else "GL_FLAT")

def init_gl():
    glClearColor(0.53, 0.81, 0.92, 1.0)  # sky blue
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE);
    glFrontFace(GL_CCW);
    glCullFace(GL_BACK)

    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
    # Um pouco de ambiente global para evitar “preto total”
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.20, 0.20, 0.25, 1.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.08, 0.08, 0.09, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.00, 0.95, 0.90, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.00, 1.00, 1.00, 1.0))
    glLightf(GL_LIGHT0, GL_SPOT_EXPONENT, LIGHT_EXPONENT)
    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF,   LIGHT_CUTOFF)

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.85, 0.85, 0.95, 1.0))
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 64.0)

    glEnable(GL_NORMALIZE)
    glShadeModel(GL_FLAT)  # default pedido

def set_camera_and_proj(w, h):
    # Projecção
    aspect = (w if w>0 else 1) / float(h if h>0 else 1)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45.0, aspect, 0.1, 100.0)
    # ModelView (câmara)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    gluLookAt(*CAM_POS, *LOOK_AT, *UP)

def update_spot(angle):
    # posição percorre círculo em XZ; fica acima da câmara
    lx = LIGHT_RADIUS * math.cos(angle)
    lz = LIGHT_RADIUS * math.sin(angle)
    ly = CAM_POS[1] + LIGHT_Y_OFFSET
    # aponta ao (0,0,0)
    dx, dy, dz = -lx, -ly, -lz
    inv = 1.0 / (math.sqrt(dx*dx + dy*dy + dz*dz) or 1.0)
    glLightfv(GL_LIGHT0, GL_POSITION,       (lx, ly, lz, 1.0))
    glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, (dx*inv, dy*inv, dz*inv))

def draw_floor(size=8.0, y=-1.2):
    # Chão simples, claro, normal para cima
    glPushAttrib(GL_ENABLE_BIT)
    glDisable(GL_CULL_FACE)
    glColor3f(0.50, 0.52, 0.56)
    glNormal3f(0,1,0)
    s = size
    glBegin(GL_QUADS)
    glVertex3f(-s, y, -s); glVertex3f( s, y, -s)
    glVertex3f( s, y,  s); glVertex3f(-s, y,  s)
    glEnd()
    glPopAttrib()

def draw_sphere():
    glPushMatrix()
    glColor3f(0.85, 0.65, 0.35)
    glRotatef(90, 1, 0, 0)      # rodar 90° em X
    gluSphere(quadric, 1.0, 48, 32)
    glPopMatrix()

def main():
    global quadric, angle_y
    if not glfw.init(): sys.exit("Falha ao inicializar GLFW")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)

    win = glfw.create_window(900, 650, "Esfera + Spotlight (C: FLAT/SMOOTH, ESC: sair)", None, None)
    if not win:
        glfw.terminate(); sys.exit("Falha ao criar janela")

    glfw.make_context_current(win)
    glfw.set_key_callback(win, on_key)
    glfw.swap_interval(1)

    init_gl()
    quadric = gluNewQuadric(); gluQuadricNormals(quadric, GLU_SMOOTH)

    last_t = glfw.get_time()
    while not glfw.window_should_close(win):
        w, h = glfw.get_framebuffer_size(win)
        set_camera_and_proj(w, h)

        # animação
        t = glfw.get_time()
        angle_y += math.radians(30.0) * max(0.0, t - last_t); last_t = t

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        update_spot(angle_y)
        draw_floor()
        draw_sphere()

        glfw.swap_buffers(win)
        glfw.poll_events()

    if quadric: gluDeleteQuadric(quadric)
    glfw.terminate()

if __name__ == "__main__":
    main()
