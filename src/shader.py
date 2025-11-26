
from OpenGL.GL import *
import numpy as np
from transform import normal_matrix

# Vertex Shader
VS = r"""
#version 330 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aTexCoord;

uniform mat4 uM;
uniform mat4 uVP;
uniform mat3 uN;

out vec3 fN;
out vec3 fPosW;
out vec2 fTexCoord;

void main(){
    vec4 posW = uM * vec4(aPos, 1.0);
    fPosW = posW.xyz;
    fN = normalize(uN * aNormal);
    fTexCoord = aTexCoord;
    gl_Position = uVP * posW;
}
"""

# Fragment Shader
FS = r"""
#version 330 core
in vec3 fN;
in vec3 fPosW;
in vec2 fTexCoord;

out vec4 fragColor;

struct Light {
    vec3 position;
    vec3 ambient;
    vec3 diffuse;
    vec3 specular;
};

#define NR_LIGHTS 2
uniform Light lights[NR_LIGHTS];

uniform vec3 uViewPos;
uniform vec3 uMaterialAmbient;
uniform vec3 uMaterialDiffuse;
uniform vec3 uMaterialSpecular;
uniform float uMaterialShininess;

uniform sampler2D uTexture;
uniform bool uHasTexture;

vec3 CalcLight(Light light, vec3 normal, vec3 viewDir, vec3 albedo) {
    vec3 lightDir = normalize(light.position - fPosW);
    
    // Diffuse
    float diff = max(dot(normal, lightDir), 0.0);
    
    // Specular
    vec3 reflectDir = reflect(-lightDir, normal);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), uMaterialShininess);
    
    vec3 ambient  = light.ambient  * albedo;
    vec3 diffuse  = light.diffuse  * diff * albedo;
    vec3 specular = light.specular * spec * uMaterialSpecular;
    
    return (ambient + diffuse + specular);
}

void main(){
    vec3 norm = normalize(fN);
    vec3 viewDir = normalize(uViewPos - fPosW);
    
    vec3 albedo = uMaterialDiffuse;
    if (uHasTexture) {
        vec4 texColor = texture(uTexture, fTexCoord);
        albedo = texColor.rgb;
    }
    
    vec3 result = vec3(0.0);
    for(int i = 0; i < NR_LIGHTS; i++)
        result += CalcLight(lights[i], norm, viewDir, albedo);
        
    fragColor = vec4(result, 1.0);
}
"""

class ShaderProgram:
    def __init__(self):
        self.prog = glCreateProgram()
        vs = self._compile(VS, GL_VERTEX_SHADER)
        fs = self._compile(FS, GL_FRAGMENT_SHADER)
        glAttachShader(self.prog, vs)
        glAttachShader(self.prog, fs)
        glLinkProgram(self.prog)
        glDeleteShader(vs)
        glDeleteShader(fs)
        
        if not glGetProgramiv(self.prog, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(self.prog).decode())
            
        # Cache uniform locations
        self.loc_uM = glGetUniformLocation(self.prog, "uM")
        self.loc_uVP = glGetUniformLocation(self.prog, "uVP")
        self.loc_uN = glGetUniformLocation(self.prog, "uN")
        self.loc_uViewPos = glGetUniformLocation(self.prog, "uViewPos")
        
        self.loc_mat_amb = glGetUniformLocation(self.prog, "uMaterialAmbient")
        self.loc_mat_diff = glGetUniformLocation(self.prog, "uMaterialDiffuse")
        self.loc_mat_spec = glGetUniformLocation(self.prog, "uMaterialSpecular")
        self.loc_mat_shiny = glGetUniformLocation(self.prog, "uMaterialShininess")
        
        self.loc_has_tex = glGetUniformLocation(self.prog, "uHasTexture")
        self.loc_tex = glGetUniformLocation(self.prog, "uTexture")
        
        # Light locations
        self.light_locs = []
        for i in range(2):
            self.light_locs.append({
                'pos': glGetUniformLocation(self.prog, f"lights[{i}].position"),
                'amb': glGetUniformLocation(self.prog, f"lights[{i}].ambient"),
                'diff': glGetUniformLocation(self.prog, f"lights[{i}].diffuse"),
                'spec': glGetUniformLocation(self.prog, f"lights[{i}].specular")
            })

    def _compile(self, src, kind):
        sh = glCreateShader(kind)
        glShaderSource(sh, src)
        glCompileShader(sh)
        if not glGetShaderiv(sh, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(sh).decode())
        return sh

    def use(self):
        glUseProgram(self.prog)

    def set_transform_uniforms(self, M, VP):
        glUniformMatrix4fv(self.loc_uM, 1, GL_TRUE, M)
        glUniformMatrix4fv(self.loc_uVP, 1, GL_TRUE, VP)
        glUniformMatrix3fv(self.loc_uN, 1, GL_TRUE, normal_matrix(M))

    def set_view_pos(self, pos):
        glUniform3fv(self.loc_uViewPos, 1, np.array(pos, dtype=np.float32))

    def set_material(self, ambient, diffuse, specular, shininess, texture_id=None):
        glUniform3fv(self.loc_mat_amb, 1, np.array(ambient, dtype=np.float32))
        glUniform3fv(self.loc_mat_diff, 1, np.array(diffuse, dtype=np.float32))
        glUniform3fv(self.loc_mat_spec, 1, np.array(specular, dtype=np.float32))
        glUniform1f(self.loc_mat_shiny, shininess)
        
        if texture_id is not None:
            glUniform1i(self.loc_has_tex, 1)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glUniform1i(self.loc_tex, 0)
        else:
            glUniform1i(self.loc_has_tex, 0)

    def set_light(self, index, position, ambient, diffuse, specular):
        if 0 <= index < len(self.light_locs):
            locs = self.light_locs[index]
            glUniform3fv(locs['pos'], 1, np.array(position, dtype=np.float32))
            glUniform3fv(locs['amb'], 1, np.array(ambient, dtype=np.float32))
            glUniform3fv(locs['diff'], 1, np.array(diffuse, dtype=np.float32))
            glUniform3fv(locs['spec'], 1, np.array(specular, dtype=np.float32))

    def destroy(self):
        glDeleteProgram(self.prog)
