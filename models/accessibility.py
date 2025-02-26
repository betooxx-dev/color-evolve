import numpy as np
from colormath.color_objects import sRGBColor

def relative_luminance(rgb):
    """Calcula luminancia relativa según WCAG 2.1"""
    r, g, b = rgb
    
    # Conversión gamma
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(color1, color2):
    """Calcula ratio de contraste según WCAG 2.1"""
    lum1 = relative_luminance(color1)
    lum2 = relative_luminance(color2)
    
    # El más brillante primero
    if lum1 < lum2:
        lum1, lum2 = lum2, lum1
        
    return (lum1 + 0.05) / (lum2 + 0.05)

def simulate_protanopia(rgb):
    """Simula protanopia (dificultad para ver rojo)"""
    # Matriz de conversión basada en modelo Machado et al. 2009
    matrix = np.array([
        [0.152, 1.052, -0.204],
        [0.114, 0.786, 0.100],
        [0.004, -0.048, 1.044]
    ])
    return np.clip(np.dot(matrix, rgb), 0, 1)

def simulate_deuteranopia(rgb):
    """Simula deuteranopia (dificultad para ver verde)"""
    matrix = np.array([
        [0.367, 0.861, -0.228],
        [0.280, 0.673, 0.047],
        [-0.011, 0.043, 0.968]
    ])
    return np.clip(np.dot(matrix, rgb), 0, 1)

def simulate_tritanopia(rgb):
    """Simula tritanopia (dificultad para ver azul)"""
    matrix = np.array([
        [1.255, -0.077, -0.178],
        [0.078, 0.930, -0.008],
        [-0.026, 0.263, 0.763]
    ])
    return np.clip(np.dot(matrix, rgb), 0, 1)

def evaluate_color_blindness(color1, color2):
    """Evalúa legibilidad con diferentes tipos de daltonismo"""
    types = {
        'protanopia': simulate_protanopia,
        'deuteranopia': simulate_deuteranopia,
        'tritanopia': simulate_tritanopia
    }
    
    results = {}
    for name, simulator in types.items():
        c1_sim = simulator(color1)
        c2_sim = simulator(color2)
        results[name] = contrast_ratio(c1_sim, c2_sim)
    
    return results