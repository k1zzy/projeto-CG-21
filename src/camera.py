
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

    def rotate(self, delta_deg):
        self.angle += delta_deg

    def zoom(self, factor):
        self.radius *= factor
        if self.radius < 1.0: self.radius = 1.0
        if self.radius > 100.0: self.radius = 100.0

    def get_view_matrix(self):
        rad = math.radians(self.angle)
        eye_x = self.center[0] + self.radius * math.sin(rad)
        eye_z = self.center[2] + self.radius * math.cos(rad)
        eye_y = self.center[1] + self.height
        
        eye = np.array([eye_x, eye_y, eye_z], dtype=np.float32)
        return lookAt(eye, self.center, self.up), eye
