
import sys
import glfw
from OpenGL.GL import *

# Estado global simples para alternar o sombreamento
shade_smooth = False  # False => GL_FLAT (default), True => GL_SMOOTH

def key_callback(window, key, scancode, action, mods):
    global shade_smooth
    if action == glfw.PRESS:
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_C:
            shade_smooth = not shade_smooth
            glShadeModel(GL_SMOOTH if shade_smooth else GL_FLAT)
            mode = "GL_SMOOTH" if shade_smooth else "GL_FLAT"
            print(f"[INFO] Sombreamento: {mode}")

def init_gl():
    # Cor de fundo e estado inicial
    #glClearColor(0.08, 0.08, 0.10, 1.0)
    glClearColor(0.53, 0.81, 0.92, 1.0)  # sky blue

    glDisable(GL_DEPTH_TEST)  # não precisamos de profundidade para 2D simples
    glShadeModel(GL_FLAT)     # começa em FLAT, como pedido

def draw_triangle():
    # Triângulo em coordenadas NDC (-1..1) com cores por vértice
    # IMPORTANTE: o ÚLTIMO vértice enviado será o "provoking" em GL_FLAT
    # (no OpenGL 2.1 o provoking vertex por omissão é o último).
    glBegin(GL_TRIANGLES)

    glColor3f(0.1, 0.9, 0.2)
    glVertex2f(-0.6, -0.4)

    glColor3f(0.2, 0.4, 1.0)
    glVertex2f(0.6, -0.4)

    glColor3f(1.0, 0.1, 0.1)
    glVertex2f(0.0, 0.6)

    glEnd()

def main():
    if not glfw.init():
        print("Falha ao inicializar o GLFW.")
        sys.exit(1)

    # Contexto OpenGL 2.1
    #O GLFW necessita de "saber" que versão do OpenGL estamos a usar. Aqui é OpenGL 2.1
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_FALSE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    window = glfw.create_window(800, 600, "Triângulo: FLAT <-> SMOOTH (C) | ESC sai", None, None)
    if not window:
        glfw.terminate()
        print("Falha ao criar janela.")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)
    glfw.swap_interval(1)  # vsync

    init_gl()
    print("[INFO] Controles: 'C' alterna GL_FLAT/GL_SMOOTH, ESC sai.")
    print("[INFO] Começa em GL_FLAT. O último vértice é vermelho (provoking).")

    while not glfw.window_should_close(window):
        glViewport(0, 0, *glfw.get_framebuffer_size(window))
        glClear(GL_COLOR_BUFFER_BIT)

        # Desenho
        draw_triangle()

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
