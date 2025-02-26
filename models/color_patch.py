import numpy as np

def delta_e_cie2000(color1, color2, Kl=1, Kc=1, Kh=1):
    """
    Implementación simplificada de delta_e_cie2000 que trabaja directamente con objetos LabColor
    """
    # Extraer valores L*a*b*
    L1, a1, b1 = color1.lab_l, color1.lab_a, color1.lab_b
    L2, a2, b2 = color2.lab_l, color2.lab_a, color2.lab_b
    
    # Calculate Cprime1, Cprime2, Cabbar
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    Cab = (C1 + C2) / 2.0
    
    # Calculate G
    G = 0.5 * (1 - np.sqrt(Cab**7 / (Cab**7 + 25**7)))
    
    # Calculate a'1, a'2, C'1, C'2
    ap1 = (1 + G) * a1
    ap2 = (1 + G) * a2
    Cp1 = np.sqrt(ap1**2 + b1**2)
    Cp2 = np.sqrt(ap2**2 + b2**2)
    
    # Calculate h'1, h'2
    hp1 = np.arctan2(b1, ap1)
    if hp1 < 0:
        hp1 += 2 * np.pi
    hp2 = np.arctan2(b2, ap2)
    if hp2 < 0:
        hp2 += 2 * np.pi
    
    # Calculate dL', dC', dH'
    dL = L2 - L1
    dC = Cp2 - Cp1
    
    # Calculate dhp
    dhp = hp2 - hp1
    if dhp > np.pi:
        dhp -= 2 * np.pi
    elif dhp < -np.pi:
        dhp += 2 * np.pi
    
    dH = 2 * np.sqrt(Cp1 * Cp2) * np.sin(dhp / 2.0)
    
    # Calculate Lp, Cp
    Lp = (L1 + L2) / 2.0
    Cp = (Cp1 + Cp2) / 2.0
    
    # Calculate hp
    hp = (hp1 + hp2) / 2.0
    if np.abs(hp1 - hp2) > np.pi:
        hp += np.pi
    
    # Calculate T
    T = 1 - 0.17 * np.cos(hp - np.pi/6) + 0.24 * np.cos(2*hp) + 0.32 * np.cos(3*hp + np.pi/30) - 0.2 * np.cos(4*hp - 21*np.pi/60)
    
    # Calculate dTheta
    dTheta = 30 * np.exp(-((hp - 275*np.pi/180) / (25*np.pi/180))**2)
    
    # Calculate Rc
    Rc = 2 * np.sqrt(Cp**7 / (Cp**7 + 25**7))
    
    # Calculate Sl, Sc, Sh
    Sl = 1 + (0.015 * (Lp - 50)**2) / np.sqrt(20 + (Lp - 50)**2)
    Sc = 1 + 0.045 * Cp
    Sh = 1 + 0.015 * Cp * T
    
    # Calculate Rt
    Rt = -np.sin(2 * dTheta * np.pi / 180) * Rc
    
    # Calculate dE00
    dE00 = np.sqrt((dL / (Kl * Sl))**2 + (dC / (Kc * Sc))**2 + (dH / (Kh * Sh))**2 + Rt * (dC / (Kc * Sc)) * (dH / (Kh * Sh)))
    
    # Devolvemos el valor como un flotante Python estándar
    return float(dE00)