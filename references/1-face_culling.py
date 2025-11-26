import math
import time

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *


def on_key(win, key, sc, action, mods):
    global smooth
    if action != glfw.PRESS: return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(win, True)

def framebuffer_size_callback(window, width, height):
    if height == 0:
        height = 1
    aspect = width / float(height)

    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, aspect, 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)


# ------------- OpenGL setup -------------

def init_opengl(width, height):
    # Sky blue background
    glClearColor(0.5, 0.7, 1.0, 1.0)

    glEnable(GL_DEPTH_TEST)

    # Face culling <-insert here
    #glEnable(GL_CULL_FACE)
    #glCullFace(GL_BACK)
    #glFrontFace(GL_CCW)

    

    # Smooth shading
    glShadeModel(GL_SMOOTH)

    # Lighting
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    # Light properties
    light_ambient = (0.2, 0.2, 0.2, 1.0)
    light_diffuse = (0.9, 0.9, 0.9, 1.0)
    light_specular = (1.0, 1.0, 1.0, 1.0)

    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)

    # Use glColor* as material
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Some specular highlight for the triangle
    material_specular = (1.0, 1.0, 1.0, 1.0)
    glMaterialfv(GL_FRONT, GL_SPECULAR, material_specular)
    glMaterialf(GL_FRONT, GL_SHININESS, 32.0)

    framebuffer_size_callback(None, width, height)


# ------------- Drawing functions -------------

def draw_floor():
    """Draw a simple gray floor (a large quad)."""
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6)  # gray
    glNormal3f(0.0, 1.0, 0.0)  # up

    size = 10.0
    y = -1.0   

    glBegin(GL_QUADS)
    glVertex3f(-size, y, -size)
    glVertex3f(size, y, -size)
    glVertex3f(size, y, size)
    glVertex3f(-size, y, size)
    glEnd()

    glPopMatrix()


def draw_floor_new():
    """Gray floor, front face pointing up, CCW winding."""
    glPushMatrix()

    glColor3f(0.6, 0.6, 0.6)      # gray
    glNormal3f(0.0, 1.0, 0.0)     # up

    size = 10.0
    y = 0.0   # or -1.0 if you prefer it lower

    glBegin(GL_TRIANGLES)
    # Triangle 1 (v0, v1, v2) – CCW, normal up
    glVertex3f(-size, y, -size)  # v0
    glVertex3f( size, y,  size)  # v2
    glVertex3f( size, y, -size)  # v1

    # Triangle 2 (v0, v2, v3) – CCW, normal up
    glVertex3f(-size, y, -size)  # v0
    glVertex3f(-size, y,  size)  # v3
    glVertex3f( size, y,  size)  # v2
    glEnd()

    glPopMatrix()

def draw_rotating_triangle(angle_deg):
    """Draw a single triangle rotating around the Y axis."""
    glPushMatrix()

    # Raise the triangle a bit so it's above the floor
    glTranslatef(0.0, 1.0, 0.0)
    glRotatef(angle_deg, 0.0, 1.0, 0.0)

    
    glBegin(GL_TRIANGLES)
    glColor3f(1.0, 0.3, 0.3)  # vermelho
    glNormal3f(0.0, 0.0, 1.0)
    glVertex3f(-1.0, 0.0, 0.0)
    glNormal3f(0.0, 0.0, 1.0)
    glVertex3f(1.0, 0.0, 0.0)
    glNormal3f(0.0, 0.0, 1.0)
    glVertex3f(0.0, 2.0, 0.0)

    glEnd()

    glPopMatrix()


# ------------- Main -------------

def main():
    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")

    # Request an OpenGL 2.1 context
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)

    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    width, height = 800, 600
    window = glfw.create_window(width, height, "Rotating Triangle - OpenGL 2.1", None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create GLFW window")

    glfw.make_context_current(window)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)

    glfw.set_key_callback(window, on_key)
    #glfw.swap_interval(1)

    init_opengl(width, height)

    last_time = time.time()
    angle = 0.0

    while not glfw.window_should_close(window):
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Rotate ~50 degrees per second
        angle += 50.0 * dt
        angle = angle % 360.0

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set up the camera
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0, 3.0, 8.0,   # eye
                  0.0, 0.0, 0.0,   # center
                  0.0, 1.0, 0.0)   # up

        light_pos = (4.0, 5.0, 2.0, 1.0)  # w=1 => positional light
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)

        # Desenha chão e triângulo
        draw_floor()
        draw_rotating_triangle(angle)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
