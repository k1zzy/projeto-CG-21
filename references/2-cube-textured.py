

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image
import sys, os

win_w, win_h = 900, 600
tex_cube = None
tex_floor = None

WALL_PATH   = "wall.jpg"
GRUNGE_PATH = "Texturelabs_Grunge_197M.jpg"

def load_texture(path, repeat=True):
    if not os.path.isfile(path):
        print("Texture not found:", path); sys.exit(1)

    img = Image.open(path).convert("RGBA")
    w, h = img.size
    data = img.tobytes("raw", "RGBA", 0, -1)

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    # filtros  e  mipmaps (veremos esta parte mais tarde )
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT if repeat else GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT if repeat else GL_CLAMP_TO_EDGE)

    # Criação de mipmaps com o GLU
    gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGBA, w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)

    #devolve o ID de cada textura carregada que será usado quando os objectos forem desenhados
    return tex_id

def setup():
    global tex_cube, tex_floor
    glEnable(GL_DEPTH_TEST)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    # Luz simples <- componentes RGB iguais - luz branca (cinzenta) - Não altera cor dos objectos
    glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 10.0, 5.0, 1.0))  #Posição <- Alta e para tras da câmara
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))   # Luz difusa
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.5, 0.5, 0.5, 1.0))   # Luz ambiente

    # Vamos permitir que as texturas sejam ilumnadas por multiplicação com a luz
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
    glEnable(GL_TEXTURE_2D)

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glShadeModel(GL_FLAT)
    glClearColor(0.75, 0.75, 1.0, 1.0)

    
    # Carregar as texturas 
    tex_cube  = load_texture(WALL_PATH,   repeat=False)   # walls no cubo
    tex_floor = load_texture(GRUNGE_PATH, repeat=True)    # grunge no floor Atenção ao repeat!!

def draw_floor():
    S = 100.0                 
    T = 50.0                  # Quantas vezes multiplicaremos a textura original no chão
    glBindTexture(GL_TEXTURE_2D, tex_floor)
    glColor3f(1, 1, 1)        # Não mexer na cor
    glNormal3f(0, 1, 0)

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex3f(-S, 0.0,  S)
    glTexCoord2f(T,   0.0); glVertex3f( S, 0.0,  S)
    glTexCoord2f(T,    T ); glVertex3f( S, 0.0, -S)
    glTexCoord2f(0.0,  T ); glVertex3f(-S, 0.0, -S)
    glEnd()

def draw_textured_cube():
    # Aqui vamos ter que usar o cubo procedural porque glutSolidCube não tem coordenadas de texturas
    glBindTexture(GL_TEXTURE_2D, tex_cube)
    glColor3f(1, 1, 1)

    s = 0.5 
    glBegin(GL_QUADS)
    glNormal3f(1,0,0)
    glTexCoord2f(0,0); glVertex3f( s,-s,-s)
    glTexCoord2f(1,0); glVertex3f( s,-s, s)
    glTexCoord2f(1,1); glVertex3f( s, s, s)
    glTexCoord2f(0,1); glVertex3f( s, s,-s)

    glNormal3f(-1,0,0)
    glTexCoord2f(0,0); glVertex3f(-s,-s, s)
    glTexCoord2f(1,0); glVertex3f(-s,-s,-s)
    glTexCoord2f(1,1); glVertex3f(-s, s,-s)
    glTexCoord2f(0,1); glVertex3f(-s, s, s)

    glNormal3f(0,1,0)
    glTexCoord2f(0,0); glVertex3f(-s, s,-s)
    glTexCoord2f(1,0); glVertex3f( s, s,-s)
    glTexCoord2f(1,1); glVertex3f( s, s, s)
    glTexCoord2f(0,1); glVertex3f(-s, s, s)

    glNormal3f(0,-1,0)
    glTexCoord2f(0,0); glVertex3f(-s,-s, s)
    glTexCoord2f(1,0); glVertex3f( s,-s, s)
    glTexCoord2f(1,1); glVertex3f( s,-s,-s)
    glTexCoord2f(0,1); glVertex3f(-s,-s,-s)

    glNormal3f(0,0,1)
    glTexCoord2f(0,0); glVertex3f(-s,-s, s)
    glTexCoord2f(1,0); glVertex3f( s,-s, s)
    glTexCoord2f(1,1); glVertex3f( s, s, s)
    glTexCoord2f(0,1); glVertex3f(-s, s, s)
    # -Z
    glNormal3f(0,0,-1)
    glTexCoord2f(0,0); glVertex3f( s,-s,-s)
    glTexCoord2f(1,0); glVertex3f(-s,-s,-s)
    glTexCoord2f(1,1); glVertex3f(-s, s,-s)
    glTexCoord2f(0,1); glVertex3f( s, s,-s)
    glEnd()

def draw_cube():
    glPushMatrix()
    glTranslatef(2.0, 1.0, -1.0)  # center at (2,1,-1)
    draw_textured_cube()
    glPopMatrix()

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0.0, 1.0, 5.0,   # eye
              0.0, 0.0, 0.0,   # center
              0.0, 1.0, 0.0)   # up

    # recolocar a posição da luz a cada frame
    glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 10.0, 5.0, 1.0))

    draw_floor()
    draw_cube()

    glutSwapBuffers()

def reshape(w, h):
    if h == 0: h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, float(w)/float(h), 0.1, 1000.0)

def keyboard(key, x, y):
    if key in (b'\x1b', b'q'):
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit(0)

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(win_w, win_h)
    glutCreateWindow(b"Pipeline Fixo (Flat) : Cubo e Chao texturados")
    setup()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutIdleFunc(display)
    glutMainLoop()

if __name__ == "__main__":
    main()
