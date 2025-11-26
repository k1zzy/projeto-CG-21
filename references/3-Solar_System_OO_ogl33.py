# OpenGL com Shaders (>3.3)
# Sistema solar simples : 2 planetas + 1 lua

import sys, math, ctypes
import numpy as np
import glfw
from OpenGL.GL import *


# Transformações matemáticas! Teêm que ser todas explicitadas
def perspective(fovy_deg, aspect, znear, zfar):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    M = np.zeros((4,4), dtype=np.float32)
    M[0,0] = f/aspect; M[1,1] = f
    M[2,2] = (zfar + znear) / (znear - zfar)
    M[2,3] = (2.0 * zfar * znear) / (znear - zfar)
    M[3,2] = -1.0
    return M

#Nem existe uma função de LookAt. Tem que ser construída de raíz
def lookAt(eye, center, up):
    eye = np.array(eye, dtype=np.float32)
    center = np.array(center, dtype=np.float32)
    up = np.array(up, dtype=np.float32)
    f = center - eye; f = f / np.linalg.norm(f)
    u = up / np.linalg.norm(up)
    s = np.cross(f, u); s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4, dtype=np.float32)
    M[0,0:3] = s; M[1,0:3] = u; M[2,0:3] = -f
    T = np.eye(4, dtype=np.float32)
    T[0,3] = -eye[0]; T[1,3] = -eye[1]; T[2,3] = -eye[2]
    return M @ T

#funções de transformaçãp
def translate(x, y, z):
    M = np.eye(4, dtype=np.float32) 
    M[0,3]=x; M[1,3]=y; M[2,3]=z 
    return M

def scale(sx, sy=None, sz=None):
    if sy is None: sy = sx
    if sz is None: sz = sx
    M = np.eye(4, dtype=np.float32)
    M[0,0]=sx; M[1,1]=sy; M[2,2]=sz; 
    return M

#para a rotação usamos a forma de Rodrigues e temos um "rodador" compatível com
# as versões anteriores do OpenGL

def rotate(angle_rad, axis):
    
    axis = np.array(axis, dtype=np.float32)
    n = np.linalg.norm(axis)
    if n == 0: return np.eye(4, dtype=np.float32)
    x, y, z = axis / n
    c = math.cos(angle_rad); s = math.sin(angle_rad); C = 1.0 - c
    R3 = np.array([
        [x*x*C + c,     x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s,   y*y*C + c,   y*z*C - x*s],
        [z*x*C - y*s,   z*y*C + x*s, z*z*C + c  ],], dtype=np.float32)
    M = np.eye(4, dtype=np.float32)
    M[:3,:3] = R3
    return M

#Cria a matriz normal como inversa da transposta da matriz do modelo
def normal_matrix(M):
    N = M[:3,:3]
    return np.linalg.inv(N).T.astype(np.float32)



# Vertex Shader (GLSL 330 core) — Flat shading 
VS = r"""
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal; 

uniform mat4 uM;
uniform mat4 uVP;
uniform mat3 uN;

flat out vec3 fN;    // sem interpolações
out vec3  fPosW;

void main(){
    vec4 posW = uM * vec4(aPos, 1.0);
    fPosW = posW.xyz;
    fN = normalize(uN * aNormal);
    gl_Position = uVP * posW;
}
"""

#fragment shader <- aqui colocamos a cor de cada fragmento
FS = r"""
#version 330 core
flat in vec3 fN;
in vec3  fPosW;
out vec4 fragColor;

uniform vec3 uLightDir;   // iluminação para a cena
uniform vec3 uLightDiffuse;
uniform vec3 uViewPos;    // posição da camara (world coords)
uniform vec3 uAlbedo;     // ambiente
uniform vec3 uAmbient;    // cor base

void main(){
    vec3 N = normalize(fN);
    vec3 L = normalize(-uLightDir);
    float diff = max(dot(N, L), 0.0);

    // opcional: componente Blinn-Phong  para melhorar a visualisação
    //vec3 V = normalize(uViewPos - fPosW);
    //vec3 H = normalize(L + V);
    //float spec = pow(max(dot(N, H), 0.0), 64.0);

    //vec3 color = uAmbient * uAlbedo + diff * uAlbedo + 0.15 * spec * vec3(1.0);
    // se se usar o codigo acima, comentar a linha em baixo
    vec3 color = (uAmbient * uAlbedo) + (diff * uLightDiffuse * uAlbedo);
    // se ignorarmos a luz direccional
    //vec3 color = uAmbient * uAlbedo + diff * uAlbedo + 0.15;
    fragColor = vec4(color, 1.0);
}
"""



class ShaderProgram:
    def __init__(self, vs_src, fs_src):
        self.prog = glCreateProgram()
        vs = self._compile(vs_src, GL_VERTEX_SHADER)
        fs = self._compile(fs_src, GL_FRAGMENT_SHADER)
        glAttachShader(self.prog, vs); glAttachShader(self.prog, fs); glLinkProgram(self.prog)
        glDeleteShader(vs); glDeleteShader(fs)
        if not glGetProgramiv(self.prog, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(self.prog).decode())
        # Cache dos locations dos uniforms para acesso fácil
        self.loc_uM   = glGetUniformLocation(self.prog, "uM")
        self.loc_uVP  = glGetUniformLocation(self.prog, "uVP")
        self.loc_uN   = glGetUniformLocation(self.prog, "uN")
        self.loc_uAlb = glGetUniformLocation(self.prog, "uAlbedo")
        self.loc_uAmb = glGetUniformLocation(self.prog, "uAmbient")
        self.loc_uLD  = glGetUniformLocation(self.prog, "uLightDir")
        self.loc_uVPs = glGetUniformLocation(self.prog, "uViewPos")
        self.loc_uLDiff = glGetUniformLocation(self.prog, "uLightDiffuse")

    #compilador
    def _compile(self, src, kind):
        sh = glCreateShader(kind); glShaderSource(sh, src); glCompileShader(sh)
        if not glGetShaderiv(sh, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(sh).decode())
        return sh

    def use(self):
        glUseProgram(self.prog)

    def set_common(self, VP, view_pos, light_dir, ambient, light_diffuse):
        #colocação das componentes da geometria e iluminação da cena nos shaders
        glUniformMatrix4fv(self.loc_uVP, 1, GL_TRUE, VP)
        glUniform3fv(self.loc_uVPs, 1, np.array(view_pos, dtype=np.float32))
        glUniform3fv(self.loc_uLD,  1, np.array(light_dir, dtype=np.float32))
        glUniform3fv(self.loc_uAmb, 1, np.array(ambient,   dtype=np.float32))
        glUniform3fv(self.loc_uLDiff, 1, np.array(light_diffuse, dtype=np.float32))

    def set_per_object(self, M, albedo):
        glUniformMatrix4fv(self.loc_uM, 1, GL_TRUE, M)
        glUniformMatrix3fv(self.loc_uN, 1, GL_TRUE, normal_matrix(M))
        glUniform3fv(self.loc_uAlb, 1, np.array(albedo, dtype=np.float32))

    def destroy(self):
        glDeleteProgram(self.prog)


# criação da geometria
class Mesh:
    #Interleaved [pos3, normal3] with indices. 
    def __init__(self, interleaved: np.ndarray, indices: np.ndarray):
        self.count = indices.size
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, interleaved.nbytes, interleaved, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        #dimensão de cada elemento (3 posição+3normais) x 4 bytes
        stride = 6 * 4
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        #2 elemento - Normais
        glEnableVertexAttribArray(1); 
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glBindVertexArray(0)

    def draw(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, ctypes.c_void_p(0))

    def destroy(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(1, [self.ebo])


# nos do Grafo de cena
class Node:
    def __init__(self, name="Node", local=None, mesh: Mesh=None, albedo=(1,1,1), animator=None):
        self.name = name
        #Aqui coloca-se a matriz de transformação local
        self.local = np.array(local if local is not None else np.eye(4, dtype=np.float32), dtype=np.float32)
        self.children = []
        self.mesh = mesh
        self.albedo = np.array(albedo, dtype=np.float32)
        self.animator = animator  # função de animação

    def add(self, *children):
        for c in children: self.children.append(c)
        return self

    def update(self, dt):
        if self.animator: self.animator(self, dt)
        for c in self.children: c.update(dt)

    def draw(self, shader: ShaderProgram, parent_world, VP, view_pos, light_dir, ambient):
        #parent_world é a matriz anterior existente
        world = parent_world @ self.local  
        if self.mesh is not None:
            shader.set_per_object(world, self.albedo)
            self.mesh.draw()
        for c in self.children:
            c.draw(shader, world, VP, view_pos, light_dir, ambient)


#Construção da geometria
def gen_uv_sphere_flat(radius=1.0, stacks=24, slices=48):
    #construção da Esfera com normais
    # tem que ser construída explicitamente para cada corte e fatia 
    # grelha de posições <- Nao podemos usar o glutSolidSphere
    P = np.zeros(((stacks+1)*(slices+1), 3), dtype=np.float32)
    for i in range(stacks+1):
        v = i / stacks
        theta = v * math.pi
        st, ct = math.sin(theta), math.cos(theta)
        for j in range(slices+1):
            u = j / slices
            phi = u * 2.0 * math.pi
            sp, cp = math.sin(phi), math.cos(phi)
            x = cp * st; y = ct; z = sp * st
            P[i*(slices+1)+j] = [radius*x, radius*y, radius*z]

    #
    tri_pos = []; tri_nrm = []
    for i in range(stacks):
        for j in range(slices):
            #Cada elemento dá um QUAD, que tem que ser dividido em triangulos
            a = i*(slices+1)+j; b = a+1; c = a+(slices+1); d = c+1
            # tri1: a,c,b
            p0, p1, p2 = P[a], P[c], P[b]
            #normal <- veja-se o produto externo
            n = np.cross(p1-p0, p2-p0); ln = np.linalg.norm(n); n = n/ln if ln>0 else np.array([0,1,0], dtype=np.float32)
            tri_pos.extend([p0, p1, p2]); tri_nrm.extend([n, n, n])
            # tri2: b,c,d
            p0, p1, p2 = P[b], P[c], P[d]
            #normal <- veja-se o produto externo
            n = np.cross(p1-p0, p2-p0); ln = np.linalg.norm(n); n = n/ln if ln>0 else np.array([0,1,0], dtype=np.float32)
            tri_pos.extend([p0, p1, p2]); tri_nrm.extend([n, n, n])

    tri_pos = np.array(tri_pos, dtype=np.float32).reshape(-1,3)
    tri_nrm = np.array(tri_nrm, dtype=np.float32).reshape(-1,3)
    inter = np.empty((tri_pos.shape[0], 6), dtype=np.float32)
    inter[:,0:3] = tri_pos; inter[:,3:6] = tri_nrm
    inter = inter.reshape(-1)
    indices = np.arange(tri_pos.shape[0], dtype=np.uint32)
    return inter, indices


# iniciar o OpenGL e Janela usando o GLFW
def setup_window(w=1200, h=800, title="Solar System — Grafo de cena com Flat Shading (OpenGL 3.3)"):
    if not glfw.init():
        print("Failed to initialize GLFW", file=sys.stderr); sys.exit(1)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    win = glfw.create_window(w, h, title, None, None)
    if not win:
        glfw.terminate(); print("Failed to create window", file=sys.stderr); sys.exit(1)
    glfw.make_context_current(win)
    return win

def setup_gl_state():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glFrontFace(GL_CCW)


# Forma extensivel de construir a cena
def build_scene(sphere_mesh):
    # materiais
    COL_STAR   = (1.00, 0.95, 0.40)
    COL_P1     = (0.60, 0.60, 1.00)
    COL_P2     = (0.45, 0.25, 0.45)
    COL_MOON   = (0.80, 0.80, 0.90)

    # Animators <- modificam o atributo local
    def rotator(axis, deg_per_sec):
        axis = np.array(axis, dtype=np.float32)
        def _fn(node, dt):
            node.local = rotate(math.radians(deg_per_sec) * dt, axis) @ node.local
        return _fn
    # Definição dos planetas e orbitas (nós do grafo)
    #note-se que as orbitas são unidades do grafo de cena que não têm geometria (mesh)
    star      = Node("Star",      local=scale(1.8), mesh=sphere_mesh, albedo=COL_STAR, animator=rotator((0,1,0), 12.0))
    p1_orbit  = Node("Planet1Orbit", animator=rotator((0,1,0), 28.0))
    p1        = Node("Planet1",   local=translate(8.0,0,0) @ scale(0.8), mesh=sphere_mesh, albedo=COL_P1, animator=rotator((0,1,0), 80.0))

    moon_orb  = Node("MoonOrbit", animator=rotator((0,1,0), 180.0))
    moon      = Node("Moon", local=translate(2.5,0,0) @ scale(0.3),
                     mesh=sphere_mesh, albedo=COL_MOON, animator=rotator((0,1,0), 140.0))

    p2_orbit  = Node("Planet2Orbit", animator=rotator((0,1,0), 18.0))
    p2        = Node("Planet2",   local=translate(-20,0,0) @ scale(1.1), mesh=sphere_mesh, albedo=COL_P2, animator=rotator((0,1,0), 60.0))


    # Construção da Hierarquia (aqui de baixo para cima)
    moon_orb.add(moon)
    p1.add(moon_orb)            
    p1_orbit.add(p1)            

    p2_orbit.add(p2)
    root = Node("Root")
    root.add(star, p1_orbit, p2_orbit)
    return root



def main():
    win = setup_window()
    setup_gl_state()

    #aqui só teremos um shader
    shader = ShaderProgram(VS, FS)

    # para a geometria vai ser sempre a mesma (uma só esfera 
    inter, idx = gen_uv_sphere_flat(radius=1.0, stacks=24, slices=48)
    sphere = Mesh(inter, idx)

    # criar a geometria
    root = build_scene(sphere)

    # dados globais da cena, camara e luz
    eye = np.array([20.0, 12.0, 22.0], dtype=np.float32)
    up  = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    ambient       = np.array([0.38, 0.38, 0.32], dtype=np.float32)    # GL_AMBIENT
    light_diffuse = np.array([1.0, 1.0, 1.0], dtype=np.float32)    # GL_DIFFUSE

    # Equivalente a  glLightfv(GL_POSITION, (0, 2, 1, 0))  -> luz direccional
    light_dir = np.array([0.45, 0.9, 0.35], dtype=np.float32)
    light_dir /= np.linalg.norm(light_dir)



    #controlo (com glfw)
    def on_key(win, key, sc, action, mods):
        if action in (glfw.PRESS, glfw.REPEAT):
            if key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(win, True)

    glfw.set_key_callback(win, on_key) #definir o call back do teclado
    t_prev = glfw.get_time()

    while not glfw.window_should_close(win):
        glfw.poll_events()

        # tempos
        t_now = glfw.get_time()
        dt = max(1e-6, t_now - t_prev); t_prev = t_now

        # actualização do grafo de cena
        root.update(dt)


        #definição das transformações até ao viewport (perspectivca e vista)
        fbw, fbh = glfw.get_framebuffer_size(win)
        glViewport(0,0,fbw,fbh)
        P  = perspective(35.0, max(fbw,1) / float(max(fbh,1)), 0.1, 1000.0)

        I = np.eye(4, dtype=np.float32)
        eye_rot = (I @ np.array([eye[0], eye[1], eye[2], 1.0], dtype=np.float32))[:3]
        V  = lookAt(eye_rot, np.array([0,0,0], dtype=np.float32), up)
        VP = P @ V

        glClearColor(0.05, 0.05, 0.25, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        shader.use()
        #shader.set_common(VP, eye_rot, light_dir, ambient)
        shader.set_common(VP, eye_rot, light_dir, ambient, light_diffuse)

        # Desenhar tudo
        root.draw(shader, np.eye(4, dtype=np.float32), VP, eye_rot, light_dir, ambient)

        glfw.swap_buffers(win)

    # saída e limpeza
    sphere.destroy()
    shader.destroy()
    glfw.terminate()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERRO:", e); sys.exit(1)
