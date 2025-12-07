
import os
import sys
import math
import numpy as np
from PIL import Image
from OpenGL.GL import *
from scene import Mesh, Node

class OBJModel:
    def __init__(self, filename):
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []
        self.materials = {}
        self.batches = []
        
        self._load_obj(filename)
        # self._build_meshes() # Adiar construcao de malhas ate depois da centralizacao opcional

    def get_center(self):
        if not self.vertices: return (0,0,0)
        # Calcular centro
        min_v = np.min(self.vertices, axis=0)
        max_v = np.max(self.vertices, axis=0)
        center = (min_v + max_v) / 2.0
        return center

    def get_bounds(self):
        if not self.vertices: return (0,0,0), (0,0,0)
        min_v = np.min(self.vertices, axis=0)
        max_v = np.max(self.vertices, axis=0)
        return min_v, max_v

    def build(self):
        self._build_meshes()

    def _load_obj(self, filename):
        base_dir = os.path.dirname(filename)
        if base_dir == "": base_dir = "."
        
        current_material = None
        
        def resolve_index(idx_str, current_len):
            if not idx_str: return -1
            idx = int(idx_str)
            if idx > 0: return idx - 1
            elif idx < 0: return current_len + idx
            else: return -1

        try:
            with open(filename, "r", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    
                    if line.startswith("v "):
                        self.vertices.append(list(map(float, line.split()[1:4])))
                    elif line.startswith("vt "):
                        self.texcoords.append(list(map(float, line.split()[1:3])))
                    elif line.startswith("vn "):
                        self.normals.append(list(map(float, line.split()[1:4])))
                    elif line.startswith("mtllib"):
                        self._load_mtl(os.path.join(base_dir, line.split(None, 1)[1].strip()))
                    elif line.startswith("usemtl"):
                        current_material = line.split(None, 1)[1].strip()
                    elif line.startswith("f "):
                        parts = line.split()[1:]
                        face_verts = []
                        for p in parts:
                            tokens = p.split("/")
                            v_idx = resolve_index(tokens[0], len(self.vertices))
                            vt_idx = resolve_index(tokens[1], len(self.texcoords)) if len(tokens) > 1 else -1
                            vn_idx = resolve_index(tokens[2], len(self.normals)) if len(tokens) > 2 else -1
                            face_verts.append((v_idx, vt_idx, vn_idx))
                        
                        # Triangular
                        for i in range(1, len(face_verts) - 1):
                            self.faces.append({
                                "material": current_material,
                                "verts": [face_verts[0], face_verts[i], face_verts[i+1]]
                            })
                            
        except OSError as e:
            print(f"Error loading OBJ: {e}")

    def _load_mtl(self, filename):
        base_dir = os.path.dirname(filename)
        current = None
        try:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("newmtl"):
                        name = line.split(None, 1)[1].strip()
                        current = {"name": name, "diffuse": (0.8, 0.8, 0.8), "texture": None}
                        self.materials[name] = current
                    elif line.startswith("Kd ") and current:
                        current["diffuse"] = tuple(map(float, line.split()[1:4]))
                    elif line.startswith("map_Kd") and current:
                        tex_path = os.path.join(base_dir, line.split(None, 1)[1].strip())
                        current["texture"] = self._load_texture(tex_path)
        except OSError:
            pass

    def _load_texture(self, path):
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
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            glGenerateMipmap(GL_TEXTURE_2D)
            return tex_id
        except Exception as e:
            print(f"Texture error {path}: {e}")
            return None

    def _build_meshes(self):
        temp_batches = {}
        
        for face in self.faces:
            mat = face["material"]
            if mat not in temp_batches: temp_batches[mat] = []
            
            verts = face["verts"]
            # Calcular normal flat se em falta
            if all(v[2] < 0 for v in verts): # verificacao simplificada
                # ... (calculo de normais omitido por brevidade, assumindo normais existentes ou 0,1,0)
                fn = (0, 1, 0)
            else: fn = (0, 1, 0)

            for v_idx, vt_idx, vn_idx in verts:
                px, py, pz = self.vertices[v_idx]
                nx, ny, nz = self.normals[vn_idx] if vn_idx >= 0 else fn
                u, v = self.texcoords[vt_idx] if vt_idx >= 0 else (0, 0)
                temp_batches[mat].extend([px, py, pz, nx, ny, nz, u, v])

        for mat_name, data in temp_batches.items():
            arr = np.array(data, dtype=np.float32)
            indices = np.arange(len(data)//8, dtype=np.uint32)
            
            mat_data = self.materials.get(mat_name, {"diffuse": (0.8, 0.8, 0.8), "texture": None})
            
            mesh = Mesh(arr, indices, texture_id=mat_data["texture"])
            self.batches.append({
                "mesh": mesh,
                "material": mat_data
            })

    def to_node(self, name="OBJRoot"):
        root = Node(name)
        for batch in self.batches:
            mat = batch["material"]
            # Create a child node for each material batch
            child = Node(name + "_Mesh", mesh=batch["mesh"], 
                         material_diffuse=mat["diffuse"])
            root.add(child)
        return root
