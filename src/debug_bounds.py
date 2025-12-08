import sys
import numpy as np

def get_bounds(filename):
    min_v = [float('inf')]*3
    max_v = [float('-inf')]*3
    count = 0
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('v '):
                v = list(map(float, line.split()[1:4]))
                for i in range(3):
                    if v[i] < min_v[i]: min_v[i] = v[i]
                    if v[i] > max_v[i]: max_v[i] = v[i]
                count += 1
    if count == 0: return None
    return min_v, max_v

gate_min, gate_max = get_bounds("../models/garagem_portao.obj")
wall_min, wall_max = get_bounds("../models/garagem_parte_fora_paredes.obj")

print(f"Gate Bounds: Min={gate_min}, Max={gate_max}")
print(f"Gate Center X: {(gate_min[0] + gate_max[0])/2}")
print(f"Wall Bounds: Min={wall_min}, Max={wall_max}")
