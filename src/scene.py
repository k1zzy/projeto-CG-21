
import ctypes
import os
import numpy as np
from PIL import Image
from OpenGL.GL import *

class Mesh:
    def __init__(self, vertices, indices, texture_id=None):
        """
        vertices: numpy array of float32, interleaved [x,y,z, nx,ny,nz, u,v]
        indices: numpy array of uint32
        """
        self.count = indices.size
        self.texture_id = texture_id
        
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)
        
        glBindVertexArray(self.vao)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        # Stride: 3 pos + 3 norm + 2 uv = 8 floats * 4 bytes = 32 bytes
        stride = 8 * 4
        
        # Posicao (loc 0)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        
        # Normal (loc 1)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        
        # TexCoord (loc 2)
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24))
        
        glBindVertexArray(0)

    def draw(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, ctypes.c_void_p(0))
        glBindVertexArray(0)

    def destroy(self):
        glDeleteVertexArrays(1, [self.vao])
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(1, [self.ebo])

class Node:
    def __init__(self, name="Node", local=None, mesh=None, 
                 material_ambient=(0.2, 0.2, 0.2),
                 material_diffuse=(0.8, 0.8, 0.8),
                 material_specular=(1.0, 1.0, 1.0),
                 material_emission=(0.0, 0.0, 0.0),
                 material_shininess=32.0,
                 material_alpha=1.0):
        self.name = name
        self.local = np.array(local if local is not None else np.eye(4, dtype=np.float32), dtype=np.float32)
        self.children = []
        self.mesh = mesh
        
        # Propriedades do material
        self.mat_ambient = material_ambient
        self.mat_diffuse = material_diffuse
        self.mat_specular = material_specular
        self.mat_emission = material_emission
        self.mat_shininess = material_shininess
        self.mat_alpha = material_alpha

    def add(self, *children):
        for c in children: self.children.append(c)
        return self

    def draw(self, shader, parent_world, VP):
        world = parent_world @ self.local
        
        if self.mesh is not None:
            shader.set_transform_uniforms(world, VP)
            shader.set_material(self.mat_ambient, self.mat_diffuse, 
                              self.mat_specular, self.mat_shininess, 
                              self.mat_alpha,
                              self.mesh.texture_id,
                              self.mat_emission)
            self.mesh.draw()
            
        for c in self.children:
            c.draw(shader, world, VP)

def create_grid_mesh(size=100, tiles=20):
    # Criar uma grelha de chao
    # vertices: x, y, z, nx, ny, nz, u, v
    verts = []
    step = size / tiles
    
    # Vamos criar quads para cada tile
    for i in range(tiles):
        for j in range(tiles):
            x0 = -size/2 + i*step
            z0 = -size/2 + j*step
            x1 = x0 + step
            z1 = z0 + step
            
            u0 = i
            v0 = j
            u1 = i+1
            v1 = j+1
            
            # Normal e sempre para cima (0, 1, 0)
            # Quad vertices (2 triangulos)
            
            # Triangulo 1
            verts.extend([x0, 0, z0, 0, 1, 0, 0, 0])
            verts.extend([x0, 0, z1, 0, 1, 0, 0, 1])
            verts.extend([x1, 0, z0, 0, 1, 0, 1, 0])
            
            # Triangulo 2
            verts.extend([x1, 0, z0, 0, 1, 0, 1, 0])
            verts.extend([x0, 0, z1, 0, 1, 0, 0, 1])
            verts.extend([x1, 0, z1, 0, 1, 0, 1, 1])

    vertices = np.array(verts, dtype=np.float32)
    indices = np.arange(len(verts)//8, dtype=np.uint32)
    
    return Mesh(vertices, indices)

def create_cube_mesh(size=1.0):
    s = size * 0.5
    # vertices: x,y,z, nx,ny,nz, u,v
    # 6 faces * 4 verts = 24 verts
    verts = [
        # Front
        -s, -s,  s,  0, 0, 1,  0, 0,
         s, -s,  s,  0, 0, 1,  1, 0,
         s,  s,  s,  0, 0, 1,  1, 1,
        -s,  s,  s,  0, 0, 1,  0, 1,
        # Back
         s, -s, -s,  0, 0,-1,  0, 0,
        -s, -s, -s,  0, 0,-1,  1, 0,
        -s,  s, -s,  0, 0,-1,  1, 1,
         s,  s, -s,  0, 0,-1,  0, 1,
        # Top
        -s,  s,  s,  0, 1, 0,  0, 0,
         s,  s,  s,  0, 1, 0,  1, 0,
         s,  s, -s,  0, 1, 0,  1, 1,
        -s,  s, -s,  0, 1, 0,  0, 1,
        # Bottom
        -s, -s, -s,  0,-1, 0,  0, 0,
         s, -s, -s,  0,-1, 0,  1, 0,
         s, -s,  s,  0,-1, 0,  1, 1,
        -s, -s,  s,  0,-1, 0,  0, 1,
        # Right
         s, -s,  s,  1, 0, 0,  0, 0,
         s, -s, -s,  1, 0, 0,  1, 0,
         s,  s, -s,  1, 0, 0,  1, 1,
         s,  s,  s,  1, 0, 0,  0, 1,
        # Left
        -s, -s, -s, -1, 0, 0,  0, 0,
        -s, -s,  s, -1, 0, 0,  1, 0,
        -s,  s,  s, -1, 0, 0,  1, 1,
        -s,  s, -s, -1, 0, 0,  0, 1,
    ]
    
    indices = [
        0,1,2, 0,2,3,       # Front
        4,5,6, 4,6,7,       # Back
        8,9,10, 8,10,11,    # Top
        12,13,14, 12,14,15, # Bottom
        16,17,18, 16,18,19, # Right
        20,21,22, 20,22,23  # Left
    ]
    
    return Mesh(np.array(verts, dtype=np.float32), np.array(indices, dtype=np.uint32))

def load_texture(path):
    if not os.path.isfile(path): return None
    try:
        img = Image.open(path)
        img = img.transpose(Image.FLIP_TOP_BOTTOM).convert("RGBA")
        data = img.tobytes()
        w, h = img.size
        
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        return tex_id
    except Exception as e:
        print(f"Texture error {path}: {e}")
        return None
