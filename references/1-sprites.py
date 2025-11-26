import sys
import math
import time

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

# -------------------------
# Configuration
# -------------------------
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

SPRITE_SHEET_PATH = "scottpilgrim_1row.png"
NUM_FRAMES = 8              # quantos frames na imagem
FRAME_DURATION = 0.08       # segundos por frame

GROUND_Y = 0.0
MOVE_SPEED = 2.5            # unidades de deslocação no x
LEFT_LIMIT = -4.0
RIGHT_LIMIT = 4.0

JUMP_VELOCITY = 5.0         # velocidade de salto inicial
GRAVITY = -12.0             # aceleração

sprite_height = 1.5


# -------------------------
# OpenGL helpers
# -------------------------

def load_texture(path):
    #carrega a textura e retorna o text id
    image = Image.open(path).convert("RGBA")
    width, height = image.size

    # Flip vertical - necessário para fazer (0,0) no canto inferior esquerdo
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = image.tobytes()

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA,
        width, height, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, img_data
    )

    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id, width, height


def setup_opengl(width, height):
    glViewport(0, 0, width, height)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, width / float(height), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)

    glClearColor(0.5, 0.8, 1.0, 1.0)  # sky blue


def draw_floor():
    # Desenha  o chão com um rectângulo
    glDisable(GL_TEXTURE_2D)
    glColor3f(0.1, 0.1, 0.6)

    glBegin(GL_QUADS)
    glVertex3f(-10.0, GROUND_Y, -10.0)
    glVertex3f( 10.0, GROUND_Y, -10.0)
    glVertex3f( 10.0, GROUND_Y,   0.0)
    glVertex3f(-10.0, GROUND_Y,   0.0)
    glEnd()

    glEnable(GL_TEXTURE_2D)


def draw_sprite(tex_id, frame_idx, num_frames, tex_w, tex_h,
                x, y, z, facing):
    #facing controla direita e esq (+1/-1)

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor3f(1.0, 1.0, 1.0)

    frame_w_px = tex_w / float(num_frames)
    frame_h_px = tex_h

    sprite_width = sprite_height * (frame_w_px / frame_h_px)

    half_w = sprite_width / 2.0
    bottom = y
    top = y + sprite_height

    # as coordenadas da textura dependem do frame em que estamos
    u0 = (frame_idx * frame_w_px) / tex_w
    u1 = ((frame_idx + 1) * frame_w_px) / tex_w
    v0 = 0.0
    v1 = 1.0

    if facing < 0:
        u0, u1 = u1, u0

    glBegin(GL_QUADS)
    glTexCoord2f(u0, v0)
    glVertex3f(x - half_w, bottom, z)

    glTexCoord2f(u1, v0)
    glVertex3f(x + half_w, bottom, z)

    glTexCoord2f(u1, v1)
    glVertex3f(x + half_w, top, z)
    
    glTexCoord2f(u0, v1)
    glVertex3f(x - half_w, top, z)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)


# -------------------------
# Main
# -------------------------

def main():
    if not glfw.init():
        print("impossivel inicializar o glfw")
        sys.exit(1)

    # OpenGL 2.1 context
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    window = glfw.create_window(
        WINDOW_WIDTH, WINDOW_HEIGHT, "Scroller (Espaço - salta)", None, None
    )
    if not window:
        glfw.terminate()
        print("oops. Não consegui criar a janela")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # vsync

    setup_opengl(WINDOW_WIDTH, WINDOW_HEIGHT)

    # carregar sprite
    texture_id, tex_w, tex_h = load_texture(SPRITE_SHEET_PATH)

    # estado
    sprite_x = 0.0
    sprite_y = GROUND_Y
    sprite_z = -2.0

    sprite_vy = 0.0
    on_ground = True
    direction = 1           # +1  dir -1 esq


    current_frame = 0
    frame_timer = 0.0

    last_time = time.time()

    while not glfw.window_should_close(window):
        # --- Time step ---
        now = time.time()
        dt = now - last_time
        last_time = now

        glfw.poll_events()

        # input: Salta com espaço!
        if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and on_ground:
            sprite_vy = JUMP_VELOCITY
            on_ground = False

        #posição horzontal <- depende da velocidade e do tempo que passou
        sprite_x += direction * MOVE_SPEED * dt

        # Volta para trás no limite do ecrâ [atenção que não lida bem com redefinições da janela
        #se chega ao fundo muda a direcção
        if sprite_x > RIGHT_LIMIT:
            sprite_x = RIGHT_LIMIT
            direction = -1
        elif sprite_x < LEFT_LIMIT:
            sprite_x = LEFT_LIMIT
            direction = 1

        # Salta! - modifica-se a velocidade
        if not on_ground:
            sprite_vy += GRAVITY * dt   
            sprite_y += sprite_vy * dt  

            if sprite_y <= GROUND_Y:
                sprite_y = GROUND_Y
                sprite_vy = 0.0
                on_ground = True

        # parte da animação
        frame_timer += dt
        if frame_timer >= FRAME_DURATION:
            frame_timer -= FRAME_DURATION
            current_frame = (current_frame + 1) % NUM_FRAMES

        # --- Render ---
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # Simple side view camera
        gluLookAt(0.0, 1.5, 5.0,   # eye
                  0.0, 1.0, 0.0,   # center
                  0.0, 1.0, 0.0)   # up

        draw_floor()
        draw_sprite(texture_id, current_frame, NUM_FRAMES,
                    tex_w, tex_h, sprite_x, sprite_y, sprite_z, direction)

        glfw.swap_buffers(window)

    glfw.terminate()


if __name__ == "__main__":
    main()
