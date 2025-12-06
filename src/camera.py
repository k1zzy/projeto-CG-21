
import math
import numpy as np
from transform import lookAt

class Camera:
    def __init__(self, radius=10.0, height=5.0):
        self.radius = radius
        self.height = height
        self.angle = 0.0
        self.center = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        
        # Camara Livre
        self.mode = "ORBIT" # ORBIT ou FREE
        self.position = np.array([0.0, 5.0, 10.0], dtype=np.float32)
        self.yaw = -90.0
        self.pitch = 0.0
        self.front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.speed = 10.0
        self.sensitivity = 0.1

    def rotate(self, delta_deg):
        if self.mode == "ORBIT":
            self.angle += delta_deg

    def zoom(self, factor):
        if self.mode == "ORBIT":
            # Escalar raio e altura para manter o angulo
            new_radius = self.radius * factor
            new_height = self.height * factor
            
            # Limitar baseado no raio
            if new_radius < 2.0: 
                new_radius = 2.0
                new_height = 2.0 * (self.height / self.radius) # Manter racio no limite
            if new_radius > 100.0: 
                new_radius = 100.0
                new_height = 100.0 * (self.height / self.radius)

            self.radius = new_radius
            self.height = new_height

    def toggle_mode(self):
        if self.mode == "ORBIT":
            self.mode = "FREE"
            # Definir pos da camara livre para a pos orbital atual
            view, eye = self.get_view_matrix()
            self.position = eye
            # Resetar orientacao para olhar para o centro (aprox)
            direction = self.center - self.position
            direction /= np.linalg.norm(direction)
            self.pitch = math.degrees(math.asin(direction[1]))
            self.yaw = math.degrees(math.atan2(direction[2], direction[0]))
        else:
            self.mode = "ORBIT"

    def update_free_cam(self, dt, inputs, d_mouse):
        if self.mode != "FREE": return

        # Visao com Rato
        dx, dy = d_mouse
        self.yaw += dx * self.sensitivity
        self.pitch -= dy * self.sensitivity
        
        if self.pitch > 89.0: self.pitch = 89.0
        if self.pitch < -89.0: self.pitch = -89.0
        
        # Atualizar vetores
        front = np.array([
            math.cos(math.radians(self.yaw)) * math.cos(math.radians(self.pitch)),
            math.sin(math.radians(self.pitch)),
            math.sin(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))
        ], dtype=np.float32)
        self.front = front / np.linalg.norm(front)
        self.right = np.cross(self.front, self.world_up)
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.front)
        self.up /= np.linalg.norm(self.up)
        
        # Movimento
        velocity = self.speed * dt
        if inputs['w']: self.position += self.front * velocity
        if inputs['s']: self.position -= self.front * velocity
        if inputs['a']: self.position -= self.right * velocity
        if inputs['d']: self.position += self.right * velocity
        if inputs.get('q'): self.position -= self.world_up * velocity # Baixo
        if inputs.get('e'): self.position += self.world_up * velocity # Cima

    def get_view_matrix(self):
        if self.mode == "ORBIT":
            rad = math.radians(self.angle)
            eye_x = self.center[0] + self.radius * math.sin(rad)
            eye_z = self.center[2] + self.radius * math.cos(rad)
            eye_y = self.center[1] + self.height
            
            eye = np.array([eye_x, eye_y, eye_z], dtype=np.float32)
            return lookAt(eye, self.center, self.up), eye
        else:
            return lookAt(self.position, self.position + self.front, self.up), self.position
