import numpy as np
import colorsys
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
# Importar nuestra versión modificada en lugar de la original
from models.color_patch import delta_e_cie2000

def hex_to_rgb(hex_color):
    """Convierte color hexadecimal a RGB (0-1)"""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

def rgb_to_hex(rgb_color):
    """Convierte RGB (0-1) a hexadecimal"""
    return '#{:02x}{:02x}{:02x}'.format(
        int(rgb_color[0]*255), 
        int(rgb_color[1]*255), 
        int(rgb_color[2]*255)
    )

def rgb_to_lab(rgb_color):
    """Convierte RGB a LAB para cálculos perceptuales"""
    rgb_obj = sRGBColor(rgb_color[0], rgb_color[1], rgb_color[2])
    lab_obj = convert_color(rgb_obj, LabColor)
    return (lab_obj.lab_l, lab_obj.lab_a, lab_obj.lab_b)

def lab_to_rgb(lab_color):
    """Convierte LAB a RGB"""
    lab_obj = LabColor(lab_color[0], lab_color[1], lab_color[2])
    rgb_obj = convert_color(lab_obj, sRGBColor)
    return (rgb_obj.rgb_r, rgb_obj.rgb_g, rgb_obj.rgb_b)

def get_delta_e(color1, color2):
    """Calcula la distancia perceptual entre dos colores en LAB"""
    lab1 = LabColor(color1[0], color1[1], color1[2])
    lab2 = LabColor(color2[0], color2[1], color2[2])
    return delta_e_cie2000(lab1, lab2)