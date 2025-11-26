import sys
import time
import math

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

# O mundo <- viewport
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

SPRITE_SHEET_PATH = "scottpilgrim_1row.png"
NUM_FRAMES = 8
FRAME_DURATION = 0.08

#Classe base <- tudo herda daqui. Há um método de update e outro de desenhar
class GameObject:
    def update(self, dt):
        pass

    def draw(self):
        pass


# Os objectos 
class Floor(GameObject):
    def __init__(self, y=0.0, length=20.0, depth=10.0, color=(0.1, 0.1, 0.6)):
        self.y = y
        self.length = length
        self.depth = depth
        self.color = color

    def draw(self):
        glDisable(GL_TEXTURE_2D)
        glColor3f(*self.color)

        half_len = self.length / 2.0
        depth = self.depth

        glBegin(GL_QUADS)
        # Rectangulo noplano XZ 
        glVertex3f(-half_len, self.y, -depth)
        glVertex3f( half_len, self.y, -depth)
        glVertex3f( half_len, self.y,  0.0)
        glVertex3f(-half_len, self.y,  0.0)
        glEnd()


class Sprite(GameObject):
    def __init__(self, tex_id, tex_w, tex_h,
                 num_frames, frame_duration,
                 x=0.0, y=0.0, z=-2.0,
                 sprite_height=1.5,
                 move_speed=2.5,
                 left_limit=-4.0, right_limit=4.0,
                 jump_velocity=5.0,
                 gravity=-12.0,
                 auto_move=True,
                 tint=(1.0, 1.0, 1.0)):
        self.tex_id = tex_id
        self.tex_w = tex_w
        self.tex_h = tex_h

        self.num_frames = num_frames
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.frame_timer = 0.0

        self.x = x
        self.y = y
        self.z = z

        self.sprite_height = sprite_height

        self.vx = move_speed
        self.vy = 0.0
        self.move_speed = move_speed
        self.left_limit = left_limit
        self.right_limit = right_limit
        self.ground_y = y  # starting y is ground
        self.jump_velocity = jump_velocity
        self.gravity = gravity
        self.on_ground = True
        self.direction = 1     # +1 right, -1 left

        self.auto_move = auto_move
        self.tint = tint

    def jump(self):
        if self.on_ground:
            self.vy = self.jump_velocity
            self.on_ground = False

    def update(self, dt):
        # Horizontal auto-movement (side-scrolling style)
        if self.auto_move:
            self.x += self.direction * self.move_speed * dt

            if self.x > self.right_limit:
                self.x = self.right_limit
                self.direction = -1
            elif self.x < self.left_limit:
                self.x = self.left_limit
                self.direction = 1

        # Vertical motion (jump)
        if not self.on_ground:
            self.vy += self.gravity * dt
            self.y += self.vy * dt
            if self.y <= self.ground_y:
                self.y = self.ground_y
                self.vy = 0.0
                self.on_ground = True

        # Animation
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_timer -= self.frame_duration
            self.current_frame = (self.current_frame + 1) % self.num_frames

    def draw(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glColor3f(*self.tint)

        frame_w_px = self.tex_w / float(self.num_frames)
        frame_h_px = self.tex_h

        sprite_height = self.sprite_height
        sprite_width = sprite_height * (frame_w_px / frame_h_px)

        half_w = sprite_width / 2.0
        bottom = self.y
        top = self.y + sprite_height

        # UVs for the current frame (single row)
        u0 = (self.current_frame * frame_w_px) / self.tex_w
        u1 = ((self.current_frame + 1) * frame_w_px) / self.tex_w
        v0 = 0.0
        v1 = 1.0

        # Fazer o flip horizontal se estamos a ir para esquerda <<- trocam-se as coordenadas horizontais (u)
        if self.direction < 0:
            u0, u1 = u1, u0

        glBegin(GL_QUADS)
        glTexCoord2f(u0, v0)
        glVertex3f(self.x - half_w, bottom, self.z)
        glTexCoord2f(u1, v0)
        glVertex3f(self.x + half_w, bottom, self.z)
        glTexCoord2f(u1, v1)
        glVertex3f(self.x + half_w, top, self.z)
        glTexCoord2f(u0, v1)
        glVertex3f(self.x - half_w, top, self.z)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)


#A textura é lida
def load_texture(path):
    image = Image.open(path).convert("RGBA") #vamos ter uma transparência <-crítico para sprites
    width, height = image.size
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = image.tobytes()

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                 width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id, width, height


def setup_opengl(width, height):
    glViewport(0, 0, width, height)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, width / float(height), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glClearColor(0.5, 0.8, 1.0, 1.0)  # azul céu
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)

 



# rendering do OpenGL
def render(objects, window):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    gluLookAt(0.0, 1.5, 5.0,
              0.0, 1.0, 0.0,
              0.0, 1.0, 0.0)

    #desenha todos os objectos da cena
    for obj in objects: objects[obj].draw()

    glfw.swap_buffers(window)


#define a propriedades do Vieiwport com o GLFW    
def init_device():
    if not glfw.init():
        print("Failed to initialize GLFW")
        sys.exit(1)

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_ANY_PROFILE)

    window = glfw.create_window(
        WINDOW_WIDTH, WINDOW_HEIGHT,"Motor de Sprites", None, None
    )
    if not window:
        glfw.terminate()
        print("Ooops, não foi possível criar a janela")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # vsync
    return window


# aqui criamos todos os objectos da cena
def create_scene():
    texture_id, tex_w, tex_h = load_texture(SPRITE_SHEET_PATH)

    #vamos guradar toda a cena num dicionário
    objects = {}

    floor = Floor(y=0.0, length=20.0, depth=10.0)
    objects["floor"] = floor

    # Main Scott (closer, bigger, slower)
    front_scott = Sprite(
        texture_id, tex_w, tex_h,
        NUM_FRAMES, FRAME_DURATION,
        x=0.0, y=0.0, z=-2.0,
        sprite_height=1.5,
        move_speed=2.5,
        left_limit=-4.0, right_limit=4.0,
        jump_velocity=5.0,
        gravity=-12.0,
        auto_move=True,
        tint=(1.0, 1.0, 1.0)
    )
    objects["front_scott"]=front_scott

    # Second Scott (farther, smaller, faster)
    back_scott = Sprite(
        texture_id, tex_w, tex_h,
        NUM_FRAMES, FRAME_DURATION,
        x=-2.0, y=0.0, z=-4.0,
        sprite_height=1.1,
        move_speed=4.0,           # faster
        left_limit=-6.0, right_limit=6.0,
        jump_velocity=5.0,
        gravity=-12.0,
        auto_move=True,
        tint=(0.85, 0.85, 0.85)   # slightly dimmer (farther feel)
    )
    objects["back_scott"]=back_scott
    
    return objects


def main():
    window=init_device()
    setup_opengl(WINDOW_WIDTH, WINDOW_HEIGHT)

    scene= create_scene()
    
    last_time = time.time()

    while not glfw.window_should_close(window):
        now = time.time()
        dt = now - last_time
        last_time = now
        
        # controles do utilizador
        glfw.poll_events()
        if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
            scene["front_scott"].jump()

        # actualiza cena: é aqui que se usa o delta do tempo para cada objecto
        for obj in scene:
            scene[obj].update(dt)

        # Render da cena
        render(scene, window)

    glfw.terminate()


if __name__ == "__main__":
    main()
