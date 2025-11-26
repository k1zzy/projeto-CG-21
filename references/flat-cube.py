
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys


win_w, win_h = 800, 600

def draw_cube(size=1.0):
    s = size * 0.5
    glBegin(GL_QUADS)

    # +Z (frente) — azul
    glColor3f(0.0, 0.3, 0.7)
    glVertex3f(-s, -s, +s)
    glVertex3f(+s, -s, +s)
    glVertex3f(+s, +s, +s)
    glVertex3f(-s, +s, +s)

    # -Z (trás) — laranja
    glColor3f(1.0, 0.5, 0.0)
    glVertex3f(+s, -s, -s)
    glVertex3f(-s, -s, -s)
    glVertex3f(-s, +s, -s)
    glVertex3f(+s, +s, -s)

    # +X (direita) — verde
    glColor3f(0.0, 0.8, 0.0)
    glVertex3f(+s, -s, +s)
    glVertex3f(+s, -s, -s)
    glVertex3f(+s, +s, -s)
    glVertex3f(+s, +s, +s)

    
    # +Y (esquerdo) — amarelo
    glColor3f(1.0, 1.0, 0.0)
    glVertex3f(-s, -s, -s)
    glVertex3f(-s, -s, +s)
    glVertex3f(-s, +s, +s)
    glVertex3f(-s, +s, -s)

    # -X (topo) — vermelho
    glColor3f(1.0, 0.0, 0.0)
    glVertex3f(-s, +s, +s)
    glVertex3f(+s, +s, +s)
    glVertex3f(+s, +s, -s)
    glVertex3f(-s, +s, -s)

    # -Y (base) — magenta
    glColor3f(0.9, 0.0, 0.9)
    glVertex3f(-s, -s, -s)
    glVertex3f(+s, -s, -s)
    glVertex3f(+s, -s, +s)
    glVertex3f(-s, -s, +s)

    glEnd()


# Callbacks para GLUT

# o que acontece quando desenhamos a janela
#é aqui que quase todo o trabalho se foca
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Matriz de modelview
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Câmara: Eye, Center, Up
    gluLookAt(2.5, 2.0, 6.0,   0.0, 0.0, 0.0,   0.0, 1.0, 0.0)

    #  uma ligeira rotação só para ver melhor a forma
    glRotatef(20.0, 1.0, 0.0, 0.0)
    glRotatef(-15.0, 0.0, 1.0, 0.0)

    # Desenha cubo <- é aqui que tudo acontece. Par já só um cubo
    draw_cube(size=1.5)

    #depois de desenhar trocamos os buffers
    glutSwapBuffers()

#o que acontece quando a janela é modificada  e logo a seguir à inicialização
def reshape(w, h):
    global win_w, win_h
    win_w, win_h = max(1, w), max(1, h)

    glViewport(0, 0, win_w, win_h)

    # Projeção em perspectiva
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = float(win_w) / float(win_h)
    gluPerspective(60.0, aspect, 0.1, 100.0)

# este é o procedimento para lidar eventos do teclado
def keyboard(key, x, y):
    # 'X' para sair
    if key == b'x':  #X (escape= b'\x1b')
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit(0)



# Inicialização - define os atributos dos recursos que se utilizarão e aspectos globais
# não é callback!
def init_gl():
    # Cor de fundo
    glClearColor(0.1, 0.1, 0.1, 1.0) #- cor de fundo (RGBA)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    #vamos usar Flat Shading
    glShadeModel(GL_FLAT)

    # Normais: para escalamentos não uniformes
    glEnable(GL_NORMALIZE)

def main():
    glutInit(sys.argv)
    # Janela double-buffered + RGBA + depth buffer
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(win_w, win_h)
    glutCreateWindow(b"Cubo com FLAT Shading (X para sair)")

    init_gl()

    # Callbacks do GLUT
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)

    glutMainLoop()

if __name__ == "__main__":
    main()
