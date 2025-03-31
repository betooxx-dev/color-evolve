import re
from bs4 import BeautifulSoup
import requests
from collections import Counter
import numpy as np
from sklearn.cluster import KMeans
import colorsys
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color

class ColorExtractor:
    """Clase para extraer los tres colores principales de HTML"""
    
    def __init__(self):
        # Patrones regex para diferentes formatos de color
        self.hex_pattern = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')
        self.rgb_pattern = re.compile(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')
        self.rgba_pattern = re.compile(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*((0|1)?.?\d+)\s*\)')
        
        # Lista de elementos prominentes para buscar en orden de prioridad
        self.prominent_selectors = [
            ".logo", "#logo", ".brand-logo", "#brand-logo",   # Logos
            "header", ".header", "#header", "#main-header",    # Cabeceras
            ".brand", "#brand", ".navbar-brand",              # Elementos de marca
            ".btn-primary", ".primary-button", ".cta",        # Botones CTA
            ".main-color", "#primary-color"                   # Elementos con nombres sugestivos
        ]
        
        # Selectores para colores de fondo
        self.background_selectors = [
            "body", ".bg", "#background", ".background",
            ".container", "main", "#main", ".main-content"
        ]
        
        # Selectores para colores de acento
        self.accent_selectors = [
            ".accent", "#accent", ".secondary", "#secondary",
            ".btn-secondary", ".accent-color", ".highlight"
        ]
        
    def extract_from_url(self, url):
        """Extrae tres colores principales desde una URL"""
        try:
            response = requests.get(url)
            html_content = response.text
            return self.extract_from_html(html_content)
        except Exception as e:
            raise Exception(f"Error al obtener HTML desde URL: {str(e)}")
    
    def extract_from_html(self, html_content):
        """Método principal para extraer tres colores de HTML"""
        # Extraer todos los colores del HTML
        all_colors = self._extract_all_colors(html_content)
        
        if not all_colors or len(all_colors) < 3:
            # Si no hay suficientes colores, usamos valores por defecto
            return ["#3A5FCD", "#FFFFFF", "#F08080"]
        
        # 1. Intentar encontrar colores por roles específicos
        primary = self._extract_by_prominence(html_content, self.prominent_selectors)
        background = self._extract_by_prominence(html_content, self.background_selectors)
        accent = self._extract_by_prominence(html_content, self.accent_selectors)
        
        # 2. Si no se encuentran por roles, usar clustering
        if len(all_colors) >= 5:
            clustered_colors = self._analyze_by_clustering(all_colors, n_clusters=5)
            
            # Rellenar los que faltan con colores del clustering
            if not primary and clustered_colors:
                primary = clustered_colors[0]
            
            if not background and len(clustered_colors) > 1:
                # Para fondo, buscar el color más claro
                background = self._find_lightest_color(clustered_colors)
            
            if not accent and len(clustered_colors) > 2:
                # Para acento, buscar un color que contraste con el fondo
                accent = self._find_contrasting_color(background or "#FFFFFF", clustered_colors)
        
        # 3. Rellenar con análisis por frecuencia si es necesario
        if not primary:
            primary = self._analyze_by_frequency(all_colors) or "#3A5FCD"
        
        if not background:
            # Buscar un color claro para el fondo
            light_colors = [c for c in all_colors if self._is_light_color(c)]
            if light_colors:
                background = Counter(light_colors).most_common(1)[0][0]
            else:
                background = "#FFFFFF"  # Por defecto, fondo blanco
        
        if not accent:
            # Excluir los colores ya seleccionados
            remaining = [c for c in all_colors if c != primary and c != background]
            if remaining:
                accent = self._analyze_by_frequency(remaining) or "#F08080"
            else:
                accent = "#F08080"  # Por defecto, un rojo suave
        
        return [primary, background, accent]
    
    def _extract_all_colors(self, html_content):
        """Extrae todos los colores del documento HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Obtener todo el CSS inline y en etiquetas <style>
        styles = []
        
        # CSS inline en atributos style
        for tag in soup.find_all(style=True):
            styles.append(tag['style'])
        
        # CSS en etiquetas <style>
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                styles.append(style_tag.string)
        
        # Atributos de color específicos
        color_attrs = ['color', 'background-color', 'background', 'border-color']
        for tag in soup.find_all():
            for attr in color_attrs:
                if attr in tag.attrs:
                    styles.append(f"{attr}: {tag[attr]}")
        
        # Extraer colores de todos los estilos
        colors = []
        
        for style in styles:
            if not style:
                continue
                
            # Buscar colores hexadecimales
            for match in self.hex_pattern.finditer(style):
                hex_color = match.group(0)
                # Normalizar hex shorthand (#ABC -> #AABBCC)
                if len(hex_color) == 4:
                    hex_color = '#' + ''.join([c*2 for c in hex_color[1:]])
                colors.append(hex_color.upper())
            
            # Buscar colores RGB
            for match in self.rgb_pattern.finditer(style):
                r, g, b = map(int, match.groups())
                hex_color = f'#{r:02x}{g:02x}{b:02x}'.upper()
                colors.append(hex_color)
            
            # Buscar colores RGBA (ignorando alpha)
            for match in self.rgba_pattern.finditer(style):
                r, g, b = map(int, match.groups()[:3])
                hex_color = f'#{r:02x}{g:02x}{b:02x}'.upper()
                colors.append(hex_color)
        
        return colors
    
    def _extract_by_prominence(self, html_content, selectors):
        """Extrae colores de elementos prominentes según los selectores proporcionados"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for selector in selectors:
            elements = soup.select(selector)
            if not elements:
                continue
                
            for element in elements:
                # Extraer colores directos
                if element.has_attr('style'):
                    style = element['style']
                    # Buscar background-color o color
                    bg_match = re.search(r'background(-color)?:\s*([^;]+)', style)
                    color_match = re.search(r'color:\s*([^;]+)', style)
                    
                    # Priorizar background-color si estamos buscando fondos
                    if selectors == self.background_selectors and bg_match:
                        value = bg_match.group(2).strip()
                    # Priorizar color para primario y acento
                    elif color_match:
                        value = color_match.group(1).strip()
                    # Usar background como respaldo
                    elif bg_match:
                        value = bg_match.group(2).strip()
                    else:
                        continue
                    
                    hex_matches = self.hex_pattern.search(value)
                    rgb_matches = self.rgb_pattern.search(value)
                    
                    if hex_matches:
                        color = hex_matches.group(0).upper()
                        if len(color) == 4:  # Convertir #ABC a #AABBCC
                            color = '#' + ''.join([c*2 for c in color[1:]])
                        
                        # Para color primario y acento, evitar colores neutros
                        if selectors != self.background_selectors and self._is_neutral_color(color):
                            continue
                            
                        # Para fondo, evitar colores muy oscuros
                        if selectors == self.background_selectors and self._is_too_dark(color):
                            continue
                            
                        return color
                    elif rgb_matches:
                        r, g, b = map(int, rgb_matches.groups())
                        color = f'#{r:02x}{g:02x}{b:02x}'.upper()
                        
                        # Filtros similares para RGB
                        if selectors != self.background_selectors and self._is_neutral_color(color):
                            continue
                            
                        if selectors == self.background_selectors and self._is_too_dark(color):
                            continue
                            
                        return color
        
        return None  # No se encontró color en elementos prominentes
    
    def _analyze_by_frequency(self, colors):
        """Analiza los colores por frecuencia de aparición"""
        if not colors:
            return None
            
        # Contar ocurrencias
        color_counts = Counter(colors)
        
        # Filtrar colores neutros
        non_neutral_colors = {color: count for color, count in color_counts.items() 
                             if not self._is_neutral_color(color)}
        
        if non_neutral_colors:
            # Devolver el color no neutro más frecuente
            return max(non_neutral_colors, key=non_neutral_colors.get)
        else:
            # Si solo hay colores neutros, devolver el más común
            return color_counts.most_common(1)[0][0]
    
    def _analyze_by_clustering(self, colors, n_clusters=5):
        """Utiliza K-means para encontrar los colores principales"""
        if len(colors) < n_clusters:
            return None
        
        # Convertir colores hex a RGB normalizados (0-1)
        rgb_colors = []
        original_colors = []  # Para mantener la correspondencia con los colores originales
        
        for hex_color in colors:
            hex_color = hex_color.lstrip('#')
            try:
                rgb = tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))
                # Verificar que es un color válido
                if all(0 <= c <= 1 for c in rgb):
                    rgb_colors.append(rgb)
                    original_colors.append(f'#{hex_color}'.upper())
            except (ValueError, IndexError):
                continue  # Ignorar colores inválidos
        
        if len(rgb_colors) < n_clusters:
            return None
            
        # Convertir a array numpy
        rgb_array = np.array(rgb_colors)
        
        # Aplicar K-means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(rgb_array)
        
        # Obtener los centroides (colores representativos)
        centroids = kmeans.cluster_centers_
        
        # Contar puntos en cada cluster
        counts = np.bincount(labels, minlength=n_clusters)
        
        # Calcular saturación y valor (HSV) para cada centroide
        centroid_features = []
        for i, rgb in enumerate(centroids):
            hsv = colorsys.rgb_to_hsv(*rgb)
            # Calculamos un score que favorece colores saturados
            # pero no demasiado oscuros ni demasiado claros
            saturation = hsv[1]
            value = hsv[2]
            
            # Convertir a Lab para mejor evaluación perceptual
            rgb_obj = sRGBColor(rgb[0], rgb[1], rgb[2])
            lab_obj = convert_color(rgb_obj, LabColor)
            
            # Penalizar colores muy oscuros o muy claros
            l_penalty = 1.0 - abs(lab_obj.lab_l - 50) / 50
            
            # Calcular score considerando saturación y cluster size
            score = (saturation * 0.6 + l_penalty * 0.4) * counts[i]
            
            # Convertir centroide a hex
            hex_color = f'#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}'.upper()
            
            centroid_features.append((hex_color, score))
        
        # Ordenar por score
        centroid_features.sort(key=lambda x: x[1], reverse=True)
        
        # Devolver los colores hex de los centroides
        return [color for color, _ in centroid_features]
    
    def _find_lightest_color(self, colors):
        """Encuentra el color más claro de la lista"""
        lightest = None
        max_l = -1
        
        for color in colors:
            try:
                hex_color = color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))
                rgb_obj = sRGBColor(r, g, b)
                lab_obj = convert_color(rgb_obj, LabColor)
                
                if lab_obj.lab_l > max_l:
                    max_l = lab_obj.lab_l
                    lightest = color
            except:
                continue
        
        return lightest or "#FFFFFF"
    
    def _find_contrasting_color(self, bg_color, colors, min_contrast=4.5):
        """Encuentra un color que contraste bien con el fondo"""
        from models.accessibility import contrast_ratio
        
        bg_rgb = hex_to_rgb(bg_color)
        
        best_contrast = 0
        best_color = None
        
        for color in colors:
            if color == bg_color:
                continue
                
            try:
                color_rgb = hex_to_rgb(color)
                contrast = contrast_ratio(bg_rgb, color_rgb)
                
                if contrast > best_contrast:
                    best_contrast = contrast
                    best_color = color
            except:
                continue
        
        # Si encontramos uno con buen contraste, lo devolvemos
        if best_contrast >= min_contrast:
            return best_color
        
        # Si no, devolvemos el mejor que hayamos encontrado
        return best_color
    
    def _is_neutral_color(self, hex_color):
        """Determina si un color es neutro (blanco, negro, gris)"""
        try:
            # Convertir a RGB
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Si R, G y B son casi iguales, es un tono de gris
            max_diff = max(abs(r-g), abs(r-b), abs(g-b))
            
            # Margen de tolerancia para considerar un color como gris
            tolerance = 15
            
            # Es muy claro (casi blanco) o muy oscuro (casi negro)
            is_too_light = r > 240 and g > 240 and b > 240
            is_too_dark = r < 15 and g < 15 and b < 15
            
            # Es blanco, negro o gris?
            if max_diff <= tolerance or is_too_light or is_too_dark:
                return True
            
            return False
        except:
            # En caso de error, consideramos que no es neutro
            return False
    
    def _is_light_color(self, hex_color):
        """Determina si un color es claro (para fondos)"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Fórmula de luminosidad perceptual
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            
            # Consideramos claro si luminancia > 70% (de 255)
            return luminance > 180
        except:
            return False
    
    def _is_too_dark(self, hex_color):
        """Determina si un color es demasiado oscuro para ser fondo"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Fórmula de luminosidad perceptual
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            
            # Consideramos demasiado oscuro si luminancia < 25% (de 255)
            return luminance < 64
        except:
            return True

# Función auxiliar para conversión
def hex_to_rgb(hex_color):
    """Convierte color hexadecimal a RGB (0-1)"""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))