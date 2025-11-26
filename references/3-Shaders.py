import sys, math
import glfw
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram

# Modos de iluminação
LIGHTING_FLAT = 0
LIGHTING_GOURAUD = 1
LIGHTING_PHONG = 2
LIGHTING_BLINN_PHONG = 3

# Modo de iluminação atual
current_lighting_mode = LIGHTING_FLAT

# Programas de shader
shader_programs = {}

# Estado mínimo
angle_y = 0.0

# Câmara e luz
CAM_POS = (0.0, 2.0, 6.0)
LOOK_AT = (0.0, 0.0, 0.0)
UP      = (0.0, 1.0, 0.0)

LIGHT_RADIUS   = 3.0
LIGHT_Y_OFFSET = -2.0

# Dados da esfera - criamos dados separados para flat shading
sphere_vertices = None
sphere_normals = None  
sphere_indices = None
sphere_vao = None
sphere_vbo = None
sphere_ebo = None
sphere_normal_vbo = None

# Para flat shading: precisamos de vértices duplicados com normais de face
flat_sphere_vertices = None
flat_sphere_normals = None
flat_sphere_indices = None
flat_sphere_vao = None
flat_sphere_vbo = None
flat_sphere_ebo = None
flat_sphere_normal_vbo = None

# Dados do chão
floor_vao = None
floor_vbo = None

def on_key(win, key, sc, action, mods):
    global current_lighting_mode
    if action != glfw.PRESS: 
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(win, True)
    elif key == glfw.KEY_1:
        current_lighting_mode = LIGHTING_FLAT
        print("Modo de iluminação: FLAT")
    elif key == glfw.KEY_2:
        current_lighting_mode = LIGHTING_GOURAUD
        print("Modo de iluminação: GOURAUD")
    elif key == glfw.KEY_3:
        current_lighting_mode = LIGHTING_PHONG
        print("Modo de iluminação: PHONG")
    elif key == glfw.KEY_4:
        current_lighting_mode = LIGHTING_BLINN_PHONG
        print("Modo de iluminação: BLINN-PHONG")

def perspective(fov, aspect, near, far):
    # Cria uma matriz de projeção em perspetiva
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    return np.array([
        [f / aspect, 0, 0, 0],
        [0, f, 0, 0],
        [0, 0, (far + near) / (near - far), -1],
        [0, 0, (2 * far * near) / (near - far), 0]
    ], dtype=np.float32)

def lookAt(eye, target, up):
    # Cria uma matriz de visualização usando parâmetros look-at
    forward = np.array(target) - np.array(eye)
    forward = forward / np.linalg.norm(forward)
    
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    
    new_up = np.cross(right, forward)
    new_up = new_up / np.linalg.norm(new_up)
    
    return np.array([
        [right[0], new_up[0], -forward[0], 0],
        [right[1], new_up[1], -forward[1], 0],
        [right[2], new_up[2], -forward[2], 0],
        [-np.dot(right, eye), -np.dot(new_up, eye), np.dot(forward, eye), 1]
    ], dtype=np.float32)

def rotation_matrix(angle_degrees, axis):
    # Cria uma matriz de rotação em torno de um eixo
    angle = math.radians(angle_degrees)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1 - c
    
    return np.array([
        [t*x*x + c,   t*x*y - s*z, t*x*z + s*y, 0],
        [t*x*y + s*z, t*y*y + c,   t*y*z - s*x, 0],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0],
        [0, 0, 0, 1]
    ], dtype=np.float32)

# Vertex Shader comum para Gouraud, Phong, Blinn-Phong
vertex_shader_source = """
#version 330 core

//layout (location = 0) 
in vec3 aPos;
//layout (location = 1) 
in vec3 aNormal;

out vec3 FragPos;
out vec3 Normal;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main()
{
    FragPos = vec3(model * vec4(aPos, 1.0));
    Normal = mat3(transpose(inverse(model))) * aNormal;
    gl_Position = projection * view * vec4(FragPos, 1.0);
}
"""

# Vertex Shader para TRUE Gouraud
gouraud_vertex_shader_source = """
#version 330 core

//layout (location = 0) 
in vec3 aPos;
//layout (location = 1) 
in vec3 aNormal;

out vec3 Color;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 objectColor;

void main()
{
    vec3 FragPos = vec3(model * vec4(aPos, 1.0));
    vec3 Normal = mat3(transpose(inverse(model))) * aNormal;
    Normal = normalize(Normal);
    
    // Calcula iluminação no VÉRTICE
    float ambientStrength = 0.2;
    vec3 ambient = ambientStrength * lightColor;
    
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(Normal, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    Color = (ambient + diffuse) * objectColor;
    
    gl_Position = projection * view * vec4(FragPos, 1.0);
}
"""

# Vertex Shader para TRUE Flat shading - usa normais de face pré-calculadas
flat_vertex_shader_source = """
#version 330 core

//layout (location = 0) 
in vec3 aPos;         // per-vertex position
//layout (location = 1) 
in vec3 aFaceNormal;  // same normal for the 3 verts of the face

flat out vec3 FaceColor;                    // Cor da Face <- FLAT - sem intepolação

uniform mat4 model, view, projection;
uniform vec3 lightPos;
uniform vec3 lightColor;
uniform vec3 objectColor;


void main()
{
    // Posição da face
    float ambientStrength = 0.2;
    vec3 P = vec3(model * vec4(aPos, 1.0));
    vec3 N = normalize(mat3(transpose(inverse(model))) * aFaceNormal);

    // Ambiente + difusea
    vec3 ambient = ambientStrength * lightColor;
    vec3 L = normalize(lightPos - P);
    float diff = max(dot(N, L), 0.0);
    vec3 diffuse = diff * lightColor;

    // Cor final tirada do Provoking vertex
    FaceColor = (ambient + diffuse) * objectColor;

    gl_Position = projection * view * vec4(P, 1.0);
}
"""


# Fragment Shader para TRUE Flat lighting - minimalista porque não há nada a fazer
#semelhante ao Gouraud mas o qualificativo flat elimina as intepolações na FaceColor

flat_fragment_shader_source = """
#version 330 core
flat in vec3 FaceColor;
out vec4 FragColor;
void main() { 
   FragColor = vec4(FaceColor, 1.0); 
}
"""

# Fragment Shader para TRUE Gouraud lighting
gouraud_fragment_shader_source = """
#version 330 core

in vec3 Color;   //aqui permite interpolações (sem FLAT)
out vec4 FragColor;
void main()
{
    // Apenas usa a cor interpolada dos vértices
    FragColor = vec4(Color, 1.0);
}
"""

# Fragment Shader para PHONG lighting
phong_fragment_shader_source = """
#version 330 core

in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 objectColor;

void main()
{
    // Iluminação ambiente
    float ambientStrength = 0.2;
    vec3 ambient = ambientStrength * lightColor;
    
    // Iluminação difusa
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // Especular (Phong)
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
    vec3 specular = 0.5 * spec * lightColor;
    
    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, 1.0);
}
"""

# Fragment Shader para BLINN-PHONG lighting
blinn_phong_fragment_shader_source = """
#version 330 core

in vec3 FragPos;
in vec3 Normal;

out vec4 FragColor;

uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 objectColor;

void main()
{
    // Iluminação ambiente
    float ambientStrength = 0.2;
    vec3 ambient = ambientStrength * lightColor;
    
    // Iluminação difusa
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // Especular (Blinn-Phong)
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(norm, halfwayDir), 0.0), 32.0);
    vec3 specular = 0.5 * spec * lightColor;
    
    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, 1.0);
}
"""

def link_program_with_bindings(vs_src, fs_src, bindings=None):
    vs = compileShader(vs_src, GL_VERTEX_SHADER)
    fs = compileShader(fs_src, GL_FRAGMENT_SHADER)
    prog = glCreateProgram()
    glAttachShader(prog, vs)
    glAttachShader(prog, fs)
    # força os locais ANTES do link:
    if bindings is not None:
        for loc, name in bindings.items():
            glBindAttribLocation(prog, loc, name.encode('utf-8'))
    glLinkProgram(prog)
    # validação opcional
    if glGetProgramiv(prog, GL_LINK_STATUS) != GL_TRUE:
        raise RuntimeError(glGetProgramInfoLog(prog).decode())
    glDeleteShader(vs); glDeleteShader(fs)
    return prog



def compile_shaders():
    global shader_programs
    bindings= {0: "aPos", 1: "aNormal"}
    
    print("###################GO################################")
    shader_programs[LIGHTING_FLAT] = link_program_with_bindings(flat_vertex_shader_source, 
                                                                flat_fragment_shader_source, bindings)
    print(1)
    shader_programs[LIGHTING_GOURAUD] = link_program_with_bindings(gouraud_vertex_shader_source, 
                                                                   gouraud_fragment_shader_source, bindings)
    print(2)
    shader_programs[LIGHTING_PHONG] = link_program_with_bindings(vertex_shader_source, 
                                                                 phong_fragment_shader_source, bindings)
    shader_programs[LIGHTING_BLINN_PHONG] = link_program_with_bindings(vertex_shader_source, 
                                                                       blinn_phong_fragment_shader_source, bindings)



def calculate_face_normal(v1, v2, v3):
    #Calcula o vetor normal para uma face triangular
    edge1 = np.array(v2) - np.array(v1)
    edge2 = np.array(v3) - np.array(v1)
    normal = np.cross(edge1, edge2)
    return normal / np.linalg.norm(normal)

def create_sphere(radius=1.0, sectors=36, stacks=18):
    global sphere_vertices, sphere_normals, sphere_indices
    global flat_sphere_vertices, flat_sphere_normals, flat_sphere_indices
    
    # Dados regulares da esfera (para Gouraud, Phong, Blinn-Phong)
    vertices = []
    normals = []
    indices = []
    
    # Dados da esfera flat - precisamos duplicar vértices para cada face
    flat_vertices = []
    flat_normals = []
    flat_indices = []
    
    sector_step = 2 * math.pi / sectors
    stack_step = math.pi / stacks
    
    # Gera vértices para esfera regular
    for i in range(stacks + 1):
        stack_angle = math.pi / 2 - i * stack_step
        xy = radius * math.cos(stack_angle)
        z = radius * math.sin(stack_angle)
        
        for j in range(sectors + 1):
            sector_angle = j * sector_step
            x = xy * math.cos(sector_angle)
            y = xy * math.sin(sector_angle)
            
            vertices.append([x, z, y])
            normals.append([x/radius, z/radius, y/radius])
    
    # Gera índices e cria dados para flat shading
    index_counter = 0
    for i in range(stacks):
        k1 = i * (sectors + 1)
        k2 = k1 + sectors + 1
        
        for j in range(sectors):
            if i != 0:
                # Obtém os três vértices deste triângulo
                v1 = vertices[k1]
                v2 = vertices[k2] 
                v3 = vertices[k1 + 1]
                
                # Calcula a normal da FACE para este triângulo
                face_normal = calculate_face_normal(v1, v2, v3)
                
                # Duplica vértices com a MESMA normal de face
                flat_vertices.extend([v1, v2, v3])
                flat_normals.extend([face_normal, face_normal, face_normal])
                flat_indices.extend([index_counter, index_counter + 1, index_counter + 2])
                index_counter += 3
                
                indices.extend([k1, k2, k1 + 1])
            
            if i != (stacks - 1):
                # Segundo triângulo do quad
                v1 = vertices[k1 + 1]
                v2 = vertices[k2]
                v3 = vertices[k2 + 1]
                
                face_normal = calculate_face_normal(v1, v2, v3)
                
                flat_vertices.extend([v1, v2, v3])
                flat_normals.extend([face_normal, face_normal, face_normal])
                flat_indices.extend([index_counter, index_counter + 1, index_counter + 2])
                index_counter += 3
                
                indices.extend([k1 + 1, k2, k2 + 1])
            
            k1 += 1
            k2 += 1
    
    sphere_vertices = np.array(vertices, dtype=np.float32)
    sphere_normals = np.array(normals, dtype=np.float32)
    sphere_indices = np.array(indices, dtype=np.uint32)
    
    flat_sphere_vertices = np.array(flat_vertices, dtype=np.float32)
    flat_sphere_normals = np.array(flat_normals, dtype=np.float32)
    flat_sphere_indices = np.array(flat_indices, dtype=np.uint32)

def setup_sphere():
    global sphere_vao, sphere_vbo, sphere_ebo, sphere_normal_vbo
    global flat_sphere_vao, flat_sphere_vbo, flat_sphere_ebo, flat_sphere_normal_vbo
    
    # Configura esfera regular (para Gouraud, Phong, Blinn-Phong)
    sphere_vao = glGenVertexArrays(1)
    sphere_vbo = glGenBuffers(1)
    sphere_normal_vbo = glGenBuffers(1)
    sphere_ebo = glGenBuffers(1)
    
    glBindVertexArray(sphere_vao)
    
    glBindBuffer(GL_ARRAY_BUFFER, sphere_vbo)
    glBufferData(GL_ARRAY_BUFFER, sphere_vertices.nbytes, sphere_vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    
    glBindBuffer(GL_ARRAY_BUFFER, sphere_normal_vbo)
    glBufferData(GL_ARRAY_BUFFER, sphere_normals.nbytes, sphere_normals, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, sphere_ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sphere_indices.nbytes, sphere_indices, GL_STATIC_DRAW)
    
    glBindVertexArray(0)
    
    # Configura esfera flat (VAO separado com normais de face) !!! para não termos que as calcular em runtime
    flat_sphere_vao = glGenVertexArrays(1)
    flat_sphere_vbo = glGenBuffers(1)
    flat_sphere_normal_vbo = glGenBuffers(1)
    flat_sphere_ebo = glGenBuffers(1)
    
    glBindVertexArray(flat_sphere_vao)
    
    glBindBuffer(GL_ARRAY_BUFFER, flat_sphere_vbo)
    glBufferData(GL_ARRAY_BUFFER, flat_sphere_vertices.nbytes, flat_sphere_vertices, GL_STATIC_DRAW)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    
    glBindBuffer(GL_ARRAY_BUFFER, flat_sphere_normal_vbo)
    glBufferData(GL_ARRAY_BUFFER, flat_sphere_normals.nbytes, flat_sphere_normals, GL_STATIC_DRAW)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, flat_sphere_ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, flat_sphere_indices.nbytes, flat_sphere_indices, GL_STATIC_DRAW)
    
    glBindVertexArray(0)

def setup_floor():
    global floor_vao, floor_vbo
    
    floor_vertices = np.array([
        -8.0, -1.2, -8.0,   0.0, 1.0, 0.0,
         8.0, -1.2, -8.0,   0.0, 1.0, 0.0,
         8.0, -1.2,  8.0,   0.0, 1.0, 0.0,
        -8.0, -1.2,  8.0,   0.0, 1.0, 0.0,
    ], dtype=np.float32)
    
    floor_vao = glGenVertexArrays(1)
    floor_vbo = glGenBuffers(1)
    
    glBindVertexArray(floor_vao)
    glBindBuffer(GL_ARRAY_BUFFER, floor_vbo)
    glBufferData(GL_ARRAY_BUFFER, floor_vertices.nbytes, floor_vertices, GL_STATIC_DRAW)
    
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(GLfloat), ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(GLfloat), ctypes.c_void_p(3 * sizeof(GLfloat)))
    glEnableVertexAttribArray(1)
    
    glBindVertexArray(0)

def init_gl():
    glClearColor(0.53, 0.81, 0.92, 1.0)  # azul céu
    glEnable(GL_DEPTH_TEST)
    
    create_sphere()
    setup_sphere()
    setup_floor()
    compile_shaders()

def set_camera_and_proj(w, h):
    # Matriz de projeção
    aspect = (w if w>0 else 1) / float(h if h>0 else 1)
    projection = perspective(45.0, aspect, 0.1, 100.0)
    
    # Matriz de visualização (câmara)
    view = lookAt(CAM_POS, LOOK_AT, UP)
    
    return projection, view

def update_spot(angle):
    # posição percorre círculo em XZ; fica acima da câmara
    lx = LIGHT_RADIUS * math.cos(angle)
    lz = LIGHT_RADIUS * math.sin(angle)
    ly = CAM_POS[1] + LIGHT_Y_OFFSET
    
    return (lx, ly, lz)

def draw_floor(model, view, projection, light_pos):
    # Usa o programa de shader atual
    program = shader_programs[current_lighting_mode]
    glUseProgram(program)
    
    # Define uniforms <- entradas no shader
    glUniformMatrix4fv(glGetUniformLocation(program, "model"), 1, GL_FALSE, model)
    glUniformMatrix4fv(glGetUniformLocation(program, "view"), 1, GL_FALSE, view)
    glUniformMatrix4fv(glGetUniformLocation(program, "projection"), 1, GL_FALSE, projection)
    glUniform3f(glGetUniformLocation(program, "lightPos"), light_pos[0], light_pos[1], light_pos[2])
    glUniform3f(glGetUniformLocation(program, "viewPos"), CAM_POS[0], CAM_POS[1], CAM_POS[2])
    glUniform3f(glGetUniformLocation(program, "lightColor"), 1.0, 0.95, 0.9)
    glUniform3f(glGetUniformLocation(program, "objectColor"), 0.5, 0.52, 0.56)
    
    # Desenha o chão
    glBindVertexArray(floor_vao)
    glDrawArrays(GL_TRIANGLE_FAN, 0, 4)
    glBindVertexArray(0)

def draw_sphere(model, view, projection, light_pos):
    # Usa o programa de shader atual
    program = shader_programs[current_lighting_mode]
    glUseProgram(program)
    
    # Define uniforms
    glUniformMatrix4fv(glGetUniformLocation(program, "model"), 1, GL_FALSE, model)
    glUniformMatrix4fv(glGetUniformLocation(program, "view"), 1, GL_FALSE, view)
    glUniformMatrix4fv(glGetUniformLocation(program, "projection"), 1, GL_FALSE, projection)
    glUniform3f(glGetUniformLocation(program, "lightPos"), light_pos[0], light_pos[1], light_pos[2])
    glUniform3f(glGetUniformLocation(program, "viewPos"), CAM_POS[0], CAM_POS[1], CAM_POS[2])
    glUniform3f(glGetUniformLocation(program, "lightColor"), 1.0, 0.95, 0.9)
    glUniform3f(glGetUniformLocation(program, "objectColor"), 0.85, 0.65, 0.35)
    
    if current_lighting_mode == LIGHTING_FLAT:
        # Usa o VAO da esfera flat com normais de face #!!!!
        glBindVertexArray(flat_sphere_vao)
        glDrawElements(GL_TRIANGLES, len(flat_sphere_indices), GL_UNSIGNED_INT, None)
    else:
        # Usa o VAO da esfera regular com normais de vértice
        glBindVertexArray(sphere_vao)
        glDrawElements(GL_TRIANGLES, len(sphere_indices), GL_UNSIGNED_INT, None)
    
    glBindVertexArray(0)

def main():
    global angle_y
    
    if not glfw.init(): 
        sys.exit("Falha ao inicializar GLFW")
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)
    win = glfw.create_window(900, 650, "Modelos de Shading (1:FLAT, 2:GOURAUD, 3:PHONG, 4:BLINN-PHONG, ESC: sair)", None, None)
    if not win:
        glfw.terminate()
        sys.exit("Falha ao criar janela")
    
    glfw.make_context_current(win)
    glfw.set_key_callback(win, on_key)
    glfw.swap_interval(1)
    
    init_gl()
    
    last_t = glfw.get_time()
    while not glfw.window_should_close(win):
        w, h = glfw.get_framebuffer_size(win)
        glViewport(0, 0, w, h)
        
        projection, view = set_camera_and_proj(w, h)
        
        # animação
        t = glfw.get_time()
        angle_y += math.radians(30.0) * max(0.0, t - last_t)
        last_t = t
        
        light_pos = update_spot(angle_y)
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Desenha o chão
        floor_model = np.identity(4, dtype=np.float32)
        draw_floor(floor_model, view, projection, light_pos)
        
        # Desenha a esfera
        sphere_model = np.identity(4, dtype=np.float32)
        # Roda a esfera para corresponder à orientação original
        # EDIT: na verdade a esfera foi definida de baixo para cima, pelo que a rotação não mantem a consistência
        # com o exercício anterior e podemos comnetar sem problema esta transformação seguinte
        #sphere_model = np.dot(sphere_model, rotation_matrix(90, [1, 0, 0]))
        draw_sphere(sphere_model, view, projection, light_pos)
        
        glfw.swap_buffers(win)
        glfw.poll_events()
    
    # Limpeza
    for program in shader_programs.values():
        glDeleteProgram(program)
    
    if sphere_vao: glDeleteVertexArrays(1, [sphere_vao])
    if sphere_vbo: glDeleteBuffers(1, [sphere_vbo])
    if sphere_normal_vbo: glDeleteBuffers(1, [sphere_normal_vbo])
    if sphere_ebo: glDeleteBuffers(1, [sphere_ebo])
    if flat_sphere_vao: glDeleteVertexArrays(1, [flat_sphere_vao])
    if flat_sphere_vbo: glDeleteBuffers(1, [flat_sphere_vbo])
    if flat_sphere_normal_vbo: glDeleteBuffers(1, [flat_sphere_normal_vbo])
    if flat_sphere_ebo: glDeleteBuffers(1, [flat_sphere_ebo])
    if floor_vao: glDeleteVertexArrays(1, [floor_vao])
    if floor_vbo: glDeleteBuffers(1, [floor_vbo])
    
    glfw.terminate()

if __name__ == "__main__":
    main()