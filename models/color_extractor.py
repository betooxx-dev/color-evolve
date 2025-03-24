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
    """Clase para extraer el color principal de HTML"""
    
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
        
    def extract_from_url(self, url):
        """Extrae el color principal desde una URL"""
        try:
            response = requests.get(url)
            html_content = response.text
            return self.extract_from_html(html_content)
        except Exception as e:
            raise Exception(f"Error al obtener HTML desde URL: {str(e)}")
    
    def extract_from_html(self, html_content):
        """Método principal para extraer color de HTML"""
        # 1. Intenta encontrar color en elementos prominentes
        prominence_color = self._extract_by_prominence(html_content)
        if prominence_color:
            return prominence_color
            
        # 2. Extrae todos los colores y analiza por frecuencia y clustering
        all_colors = self._extract_all_colors(html_content)
        
        if not all_colors:
            return "#3A5FCD"  # Color por defecto si no se encuentra ninguno
            
        # 3. Intenta clustering para encontrar colores dominantes
        if len(all_colors) > 5:
            cluster_color = self._analyze_by_clustering(all_colors)
            if cluster_color:
                return cluster_color
                
        # 4. Recurre a análisis por frecuencia
        frequency_color = self._analyze_by_frequency(all_colors)
        return frequency_color or "#3A5FCD"  # Color por defecto
    
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
    
    def _extract_by_prominence(self, html_content):
        """Extrae colores de elementos prominentes"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for selector in self.prominent_selectors:
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
                    
                    if bg_match:
                        value = bg_match.group(2).strip()
                        hex_matches = self.hex_pattern.search(value)
                        rgb_matches = self.rgb_pattern.search(value)
                        
                        if hex_matches:
                            color = hex_matches.group(0).upper()
                            if len(color) == 4:  # Convertir #ABC a #AABBCC
                                color = '#' + ''.join([c*2 for c in color[1:]])
                            if not self._is_neutral_color(color):
                                return color
                        elif rgb_matches:
                            r, g, b = map(int, rgb_matches.groups())
                            color = f'#{r:02x}{g:02x}{b:02x}'.upper()
                            if not self._is_neutral_color(color):
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
        for hex_color in colors:
            hex_color = hex_color.lstrip('#')
            try:
                rgb = tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))
                # Verificar que es un color válido
                if all(0 <= c <= 1 for c in rgb):
                    rgb_colors.append(rgb)
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
            
            # No considerar colores neutros
            if not self._is_neutral_color(hex_color):
                centroid_features.append((hex_color, score))
        
        if not centroid_features:
            return None
            
        # Ordenar por score y devolver el mejor
        centroid_features.sort(key=lambda x: x[1], reverse=True)
        return centroid_features[0][0]
    
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