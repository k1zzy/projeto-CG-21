
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys

win_w, win_h = 800, 600

#Posição da câmara (para ver depois)
eye_x, eye_y, eye_z = 0.0, 1.0, 5.0

def setup():
    glEnable(GL_DEPTH_TEST)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    # Luz simples <- componentes RGB iguais - luz branca (cinzenta) - Não altera cor dos objectos
    glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 10.0, 5.0, 1.0))  #Posição <- Alta e para tras da câmara
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))   # Luz difusa
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.5, 0.5, 0.5, 1.0))   # Luz ambiente

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glShadeModel(GL_FLAT)
    glClearColor(0.75, 0.75, 1.0, 1.0)

def draw_floor():
    #o chão de -100 a 100 <- um simples quadrado
    S = 100.0
    glColor3f(0.7, 0.8, 0.7)
    glNormal3f(0.0, 1.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(-S, 0.0,  S) # y =0
    glVertex3f( S, 0.0,  S)
    glVertex3f( S, 0.0, -S)
    glVertex3f(-S, 0.0, -S)
    glEnd()

def draw_cube():
    #NOTA: o glPushhMatrix() e o glPopMatrix() não são estritamente necessários aqui,
    #      mas são uma boa prática. Veremos este aspecto na próxima aula
    
    glPushMatrix() 
    glTranslatef(2.0, 1.0, -1.0)  # centro em (2,1,-1)
    glColor3f(0.7, 0.2, 0.2)
    glutSolidCube(1.0)  # :-) Assim é mais fácil
    glPopMatrix()

def display():
    global eye_x, eye_y, eye_z

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    gluLookAt(eye_x, eye_y, eye_z,   # Notar que o eye é variável global!
              0.0, 0.0, 0.0,         
              0.0, 1.0, 0.0)         

    glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 10.0, 5.0, 1.0))

    draw_floor()
    draw_cube()

    glutSwapBuffers()

def reshape(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, float(w)/float(h), 0.1, 1000.0)

def keyboard(key, x, y):
    if key in (b'\x1b', b'q'):  # ESC ou q para sair
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit(0)

    glutPostRedisplay()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(win_w, win_h)
    glutCreateWindow(b"Pipeline fixo (Flat) com iluminacao")

    setup()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutIdleFunc(display)
    glutMainLoop()

if __name__ == "__main__":
    main()
