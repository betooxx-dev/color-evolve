import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
import numpy as np
from sklearn.cluster import KMeans
import colorsys
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from urllib.parse import urljoin, urlparse
import cssutils # Necesitas instalar: pip install cssutils
import logging
import math

# Configura el logging (opcional, pero útil para depurar)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
# Silenciar warnings de cssutils sobre propiedades desconocidas
cssutils.log.setLevel(logging.CRITICAL)

# --- Constantes y Helpers ---

# Diccionario de nombres de colores CSS comunes a HEX
# (Puedes expandir esta lista si es necesario)
CSS_COLOR_NAMES = {
    "aliceblue": "#F0F8FF", "antiquewhite": "#FAEBD7", "aqua": "#00FFFF", "aquamarine": "#7FFFD4",
    "azure": "#F0FFFF", "beige": "#F5F5DC", "bisque": "#FFE4C4", "black": "#000000",
    "blanchedalmond": "#FFEBCD", "blue": "#0000FF", "blueviolet": "#8A2BE2", "brown": "#A52A2A",
    "burlywood": "#DEB887", "cadetblue": "#5F9EA0", "chartreuse": "#7FFF00", "chocolate": "#D2691E",
    "coral": "#FF7F50", "cornflowerblue": "#6495ED", "cornsilk": "#FFF8DC", "crimson": "#DC143C",
    "cyan": "#00FFFF", "darkblue": "#00008B", "darkcyan": "#008B8B", "darkgoldenrod": "#B8860B",
    "darkgray": "#A9A9A9", "darkgrey": "#A9A9A9", "darkgreen": "#006400", "darkkhaki": "#BDB76B",
    "darkmagenta": "#8B008B", "darkolivegreen": "#556B2F", "darkorange": "#FF8C00", "darkorchid": "#9932CC",
    "darkred": "#8B0000", "darksalmon": "#E9967A", "darkseagreen": "#8FBC8F", "darkslateblue": "#483D8B",
    "darkslategray": "#2F4F4F", "darkslategrey": "#2F4F4F", "darkturquoise": "#00CED1",
    "darkviolet": "#9400D3", "deeppink": "#FF1493", "deepskyblue": "#00BFFF", "dimgray": "#696969",
    "dimgrey": "#696969", "dodgerblue": "#1E90FF", "firebrick": "#B22222", "floralwhite": "#FFFAF0",
    "forestgreen": "#228B22", "fuchsia": "#FF00FF", "gainsboro": "#DCDCDC", "ghostwhite": "#F8F8FF",
    "gold": "#FFD700", "goldenrod": "#DAA520", "gray": "#808080", "grey": "#808080",
    "green": "#008000", "greenyellow": "#ADFF2F", "honeydew": "#F0FFF0", "hotpink": "#FF69B4",
    "indianred": "#CD5C5C", "indigo": "#4B0082", "ivory": "#FFFFF0", "khaki": "#F0E68C",
    "lavender": "#E6E6FA", "lavenderblush": "#FFF0F5", "lawngreen": "#7CFC00", "lemonchiffon": "#FFFACD",
    "lightblue": "#ADD8E6", "lightcoral": "#F08080", "lightcyan": "#E0FFFF", "lightgoldenrodyellow": "#FAFAD2",
    "lightgray": "#D3D3D3", "lightgrey": "#D3D3D3", "lightgreen": "#90EE90", "lightpink": "#FFB6C1",
    "lightsalmon": "#FFA07A", "lightseagreen": "#20B2AA", "lightskyblue": "#87CEFA", "lightslategray": "#778899",
    "lightslategrey": "#778899", "lightsteelblue": "#B0C4DE", "lightyellow": "#FFFFE0", "lime": "#00FF00",
    "limegreen": "#32CD32", "linen": "#FAF0E6", "magenta": "#FF00FF", "maroon": "#800000",
    "mediumaquamarine": "#66CDAA", "mediumblue": "#0000CD", "mediumorchid": "#BA55D3",
    "mediumpurple": "#9370DB", "mediumseagreen": "#3CB371", "mediumslateblue": "#7B68EE",
    "mediumspringgreen": "#00FA9A", "mediumturquoise": "#48D1CC", "mediumvioletred": "#C71585",
    "midnightblue": "#191970", "mintcream": "#F5FFFA", "mistyrose": "#FFE4E1", "moccasin": "#FFE4B5",
    "navajowhite": "#FFDEAD", "navy": "#000080", "oldlace": "#FDF5E6", "olive": "#808000",
    "olivedrab": "#6B8E23", "orange": "#FFA500", "orangered": "#FF4500", "orchid": "#DA70D6",
    "palegoldenrod": "#EEE8AA", "palegreen": "#98FB98", "paleturquoise": "#AFEEEE",
    "palevioletred": "#DB7093", "papayawhip": "#FFEFD5", "peachpuff": "#FFDAB9", "peru": "#CD853F",
    "pink": "#FFC0CB", "plum": "#DDA0DD", "powderblue": "#B0E0E6", "purple": "#800080",
    "rebeccapurple": "#663399", "red": "#FF0000", "rosybrown": "#BC8F8F", "royalblue": "#4169E1",
    "saddlebrown": "#8B4513", "salmon": "#FA8072", "sandybrown": "#F4A460", "seagreen": "#2E8B57",
    "seashell": "#FFF5EE", "sienna": "#A0522D", "silver": "#C0C0C0", "skyblue": "#87CEEB",
    "slateblue": "#6A5ACD", "slategray": "#708090", "slategrey": "#708090", "snow": "#FFFAFA",
    "springgreen": "#00FF7F", "steelblue": "#4682B4", "tan": "#D2B48C", "teal": "#008080",
    "thistle": "#D8BFD8", "tomato": "#FF6347", "turquoise": "#40E0D0", "violet": "#EE82EE",
    "wheat": "#F5DEB3", "white": "#FFFFFF", "whitesmoke": "#F5F5F5", "yellow": "#FFFF00",
    "yellowgreen": "#9ACD32",
}

def _normalize_hex(hex_color):
    """Normaliza un color hexadecimal a formato #RRGGBB."""
    if not hex_color or not hex_color.startswith('#'):
        return None
    hex_color = hex_color.lstrip('#').upper()
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) == 6:
        # Validar caracteres hexadecimales
        if all(c in '0123456789ABCDEF' for c in hex_color):
            return f"#{hex_color}"
    return None

def _rgb_to_hex(r, g, b):
    """Convierte RGB (0-255) a hexadecimal #RRGGBB."""
    return f'#{r:02x}{g:02x}{b:02x}'.upper()

def _parse_color_value(color_str):
    """Intenta parsear un valor de color (hex, rgb, rgba, nombre) a HEX."""
    if not color_str:
        return None
    color_str = color_str.strip().lower()

    # Nombre de color
    if color_str in CSS_COLOR_NAMES:
        return CSS_COLOR_NAMES[color_str]

    # Hexadecimal
    if color_str.startswith('#'):
        return _normalize_hex(color_str)

    # RGB
    match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
    if match:
        r, g, b = map(int, match.groups())
        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return _rgb_to_hex(r, g, b)

    # RGBA (ignoramos alfa)
    match = re.match(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)', color_str)
    if match:
        r, g, b = map(int, match.groups())
        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            return _rgb_to_hex(r, g, b)

    # Podríamos añadir hsl, hsla si fuera necesario
    return None

def _hex_to_rgb_normalized(hex_color):
    """Convierte color hexadecimal a RGB normalizado (0-1)."""
    if not hex_color: return (0, 0, 0) # Default a negro si es inválido
    h = hex_color.lstrip('#')
    try:
        # Asegura que la longitud sea 6 antes de la conversión
        if len(h) == 3:
             h = ''.join([c*2 for c in h])
        if len(h) != 6:
            raise ValueError("Invalid hex color length")
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
         logging.warning(f"Error convirtiendo hex a RGB: {hex_color}")
         return (0, 0, 0) # Fallback

def _get_relative_luminance(rgb_normalized):
    """Calcula la luminancia relativa según WCAG."""
    rgb = []
    for val in rgb_normalized:
        if val <= 0.03928:
            rgb.append(val / 12.92)
        else:
            rgb.append(((val + 0.055) / 1.055) ** 2.4)
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

def _calculate_contrast_ratio(hex_color1, hex_color2):
    """Calcula el ratio de contraste WCAG entre dos colores HEX."""
    try:
        rgb1 = _hex_to_rgb_normalized(hex_color1)
        rgb2 = _hex_to_rgb_normalized(hex_color2)

        lum1 = _get_relative_luminance(rgb1)
        lum2 = _get_relative_luminance(rgb2)

        if lum1 > lum2:
            return (lum1 + 0.05) / (lum2 + 0.05)
        else:
            return (lum2 + 0.05) / (lum1 + 0.05)
    except Exception as e:
        logging.warning(f"Error calculando contraste entre {hex_color1} y {hex_color2}: {e}")
        return 1.0 # Ratio mínimo si hay error

# --- Clase Principal ---

class ColorExtractor:
    """Clase mejorada para extraer colores primarios, de fondo y de acento de páginas web."""

    def __init__(self, default_primary="#3A5FCD", default_background="#FFFFFF", default_accent="#F08080"):
        self.default_primary = default_primary
        self.default_background = default_background
        self.default_accent = default_accent

        # Selectores priorizados (puedes ajustarlos)
        self.primary_selectors = [
            ".btn-primary", ".button-primary", ".cta", "[role=button].primary",
            ".navbar", "nav", ".header", "#header", "header",
            ".logo", "#logo", ".brand"
        ]
        self.accent_selectors = [
             ".btn-secondary", ".button-secondary", "a:hover", ".highlight",
             ".accent", "#accent", ".text-accent", "mark"
        ]
        # Propiedades de color relevantes
        self.color_properties = ['color', 'background-color', 'background', 'border-color', 'fill', 'stroke']

    def extract_from_url(self, url, timeout=10):
        """Extrae colores principales desde una URL."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status() # Lanza excepción para códigos de error HTTP
            content_type = response.headers.get('content-type', '').lower()

            if 'text/html' in content_type:
                html_content = response.text
                # Usar la URL base para resolver URLs relativas de CSS
                base_url = response.url
                return self.extract_from_html(html_content, base_url=base_url)
            else:
                raise ValueError(f"La URL no devolvió HTML. Content-Type: {content_type}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener URL {url}: {e}")
            raise Exception(f"Error de red al acceder a {url}: {e}") from e
        except Exception as e:
            logging.error(f"Error procesando URL {url}: {e}")
            raise Exception(f"Error inesperado al procesar {url}: {e}") from e

    def extract_from_html(self, html_content, base_url=None):
        """Método principal para extraer colores primarios, de fondo y de acento."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Extraer TODOS los colores (inline, <style>, CSS externo)
        all_colors_data = self._extract_all_colors_with_context(soup, base_url)

        if not all_colors_data:
            logging.warning("No se encontraron colores. Usando defaults.")
            return [self.default_primary, self.default_background, self.default_accent]

        # 2. Determinar el Color de Fondo
        background_color = self._find_background_color(soup, all_colors_data)

        # Lista plana de todos los colores encontrados para clustering y frecuencia
        all_colors_flat = [item['color'] for item in all_colors_data]
        if not all_colors_flat: # Doble check
             return [self.default_primary, background_color, self.default_accent]

        # Filtrar colores muy similares al fondo para primario/acento
        potential_foreground_colors = [
            c for c in all_colors_flat
            if c != background_color and _calculate_contrast_ratio(c, background_color) > 1.5 # Umbral bajo para incluir opciones
        ]

        if not potential_foreground_colors:
             # Si todo es muy similar al fondo, buscar algo distinto o usar default
             other_options = [c for c in all_colors_flat if c != background_color]
             if other_options:
                 potential_foreground_colors = other_options
             else: # Solo queda el color de fondo
                 logging.warning("Solo se encontró el color de fondo. Usando defaults para primario/acento.")
                 # Intentar generar un acento que contraste
                 accent = self._find_contrasting_fallback(background_color, [self.default_accent, "#FF0000", "#0000FF"])
                 return [self.default_primary, background_color, accent]


        # 3. Determinar Color Primario
        primary_color = self._find_primary_color(soup, all_colors_data, potential_foreground_colors, background_color)

        # 4. Determinar Color de Acento
        accent_color = self._find_accent_color(soup, all_colors_data, potential_foreground_colors, background_color, primary_color)

        # Asegurarse de que los tres colores sean distintos si es posible
        final_colors = [primary_color, background_color, accent_color]
        if len(set(final_colors)) < 3:
            logging.debug("Colores duplicados detectados, intentando ajustar...")
            remaining_colors = [
                c for c in potential_foreground_colors
                if c not in final_colors and _calculate_contrast_ratio(c, background_color) >= 3.0 # Mayor contraste para reemplazo
            ]
            if primary_color == background_color:
                 if remaining_colors: primary_color = remaining_colors[0]
                 else: primary_color = self.default_primary # Reset a default
                 final_colors = [primary_color, background_color, accent_color] # Reconstruir
                 if len(set(final_colors)) < 3 and accent_color == primary_color : # Si acento ahora es igual
                     if len(remaining_colors) > 1: accent_color = remaining_colors[1]
                     else: accent_color = self._find_contrasting_fallback(background_color, [self.default_accent, "#FF8C00"])


            if accent_color == background_color or accent_color == primary_color:
                 if remaining_colors and remaining_colors[0] != primary_color: accent_color = remaining_colors[0]
                 elif len(remaining_colors) > 1 and remaining_colors[1] != primary_color: accent_color = remaining_colors[1]
                 else: # Buscar un fallback que contraste
                     accent_color = self._find_contrasting_fallback(background_color, [self.default_accent, "#FF4500", "#20B2AA"])


            final_colors = [primary_color, background_color, accent_color]
            # Asegurar que no sean el mismo de nuevo tras los ajustes
            if len(set(final_colors)) < 3:
                 logging.warning("No se pudieron encontrar 3 colores distintos. Puede haber duplicados.")
                 # Lógica de último recurso si aún hay duplicados (ej. asignar defaults si es necesario)
                 final_colors = list(dict.fromkeys(final_colors)) # Elimina duplicados manteniendo orden
                 while len(final_colors) < 3:
                      defaults_to_try = [self.default_primary, self.default_background, self.default_accent, "#FFA500", "#008080"]
                      found_default = False
                      for d in defaults_to_try:
                          if d not in final_colors:
                              final_colors.append(d)
                              found_default = True
                              break
                      if not found_default: # Si todos los defaults ya están, algo raro pasa
                          final_colors.append("#808080") # Añadir gris como último recurso


        return final_colors[:3] # Devolver siempre 3 colores

    def _fetch_and_parse_css(self, url, base_url, timeout=5):
        """Descarga y parsea un archivo CSS."""
        full_url = url
        if base_url and not urlparse(url).scheme:
            full_url = urljoin(base_url, url)

        try:
            headers = {'User-Agent': 'Mozilla/5.0'} # Ser un buen ciudadano web
            response = requests.get(full_url, timeout=timeout, headers=headers)
            response.raise_for_status()
            # Intentar decodificar con la codificación detectada o UTF-8
            response.encoding = response.apparent_encoding or 'utf-8'
            css_text = response.text
            # Parsear CSS - ignorar errores de propiedades específicas
            parser = cssutils.CSSParser(log=logging.getLogger('cssutils'), fetcher=lambda u: ('utf-8', b'')) # Evitar fetching recursivo
            sheet = parser.parseString(css_text, href=full_url)
            return sheet
        except requests.exceptions.RequestException as e:
            logging.warning(f"No se pudo descargar CSS desde {full_url}: {e}")
            return None
        except Exception as e:
            logging.warning(f"Error al parsear CSS desde {full_url}: {e}")
            return None

    def _extract_all_colors_with_context(self, soup, base_url):
        """Extrae todos los colores del HTML y CSS asociado, guardando contexto."""
        colors_data = [] # Lista de diccionarios {'color': hex, 'property': prop, 'is_background': bool}

        # 1. Estilos inline
        for tag in soup.find_all(style=True):
            try:
                # Usar cssutils para parsear estilos inline
                style_declaration = cssutils.parseStyle(tag['style'])
                for prop in style_declaration:
                    if prop.name in self.color_properties:
                        color = _parse_color_value(prop.value)
                        if color:
                            is_bg = 'background' in prop.name
                            colors_data.append({'color': color, 'property': prop.name, 'is_background': is_bg})
            except Exception as e:
                 logging.debug(f"Error parseando estilo inline: {tag.get('style', '')} - {e}")


        # 2. Etiquetas <style>
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                try:
                    parser = cssutils.CSSParser(log=logging.getLogger('cssutils'))
                    sheet = parser.parseString(style_tag.string)
                    for rule in sheet:
                        if rule.type == rule.STYLE_RULE:
                            for prop in rule.style:
                                if prop.name in self.color_properties:
                                    color = _parse_color_value(prop.value)
                                    if color:
                                        is_bg = 'background' in prop.name
                                        colors_data.append({'color': color, 'property': prop.name, 'is_background': is_bg})
                except Exception as e:
                    logging.debug(f"Error parseando <style> tag: {e}")


        # 3. CSS Externo (<link rel="stylesheet">)
        for link_tag in soup.find_all('link', rel='stylesheet', href=True):
            css_url = link_tag['href']
            sheet = self._fetch_and_parse_css(css_url, base_url)
            if sheet:
                for rule in sheet:
                    if rule.type == rule.STYLE_RULE:
                         # Guardar también el selector para posible análisis futuro
                         selector = rule.selectorText
                         for prop in rule.style:
                             if prop.name in self.color_properties:
                                 color = _parse_color_value(prop.value)
                                 if color:
                                     is_bg = 'background' in prop.name
                                     colors_data.append({
                                         'color': color,
                                         'property': prop.name,
                                         'is_background': is_bg,
                                         'selector': selector # Contexto adicional
                                         })

        # 4. Atributos HTML específicos (menos común hoy en día, pero por si acaso)
        # Ejemplo: <font color="...">, <body bgcolor="...">
        for tag in soup.find_all(attrs={'color': True}):
            color = _parse_color_value(tag['color'])
            if color: colors_data.append({'color': color, 'property': 'attr_color', 'is_background': False})
        for tag in soup.find_all(attrs={'bgcolor': True}):
             color = _parse_color_value(tag['bgcolor'])
             if color: colors_data.append({'color': color, 'property': 'attr_bgcolor', 'is_background': True})


        logging.info(f"Extraídos {len(colors_data)} colores con contexto.")
        return colors_data

    def _get_element_styles(self, element, all_colors_data):
         """Intenta obtener los colores aplicados a un elemento específico (heurística)."""
         # Esto es una simplificación, no calcula la cascada CSS completa.
         colors = []
         # Estilo inline
         if element.has_attr('style'):
             try:
                 style_declaration = cssutils.parseStyle(element['style'])
                 for prop in style_declaration:
                     if prop.name in self.color_properties:
                         color = _parse_color_value(prop.value)
                         if color:
                             is_bg = 'background' in prop.name
                             colors.append({'color': color, 'property': prop.name, 'is_background': is_bg})
             except Exception:
                 pass # Ignorar errores de parseo inline

         # Buscar en reglas CSS (simplificado: ¿alguna regla coincide?)
         # Una comprobación más robusta requeriría parsear selectores complejos
         # y entender la especificidad, lo cual está fuera del alcance aquí.
         # Por ahora, nos basamos en los colores generales extraídos.
         return colors


    def _find_background_color(self, soup, all_colors_data):
        """Intenta determinar el color de fondo principal."""
        # Prioridad 1: Estilo directo en <html> o <body>
        for tag_name in ['html', 'body']:
            element = soup.find(tag_name)
            if element:
                inline_styles = self._get_element_styles(element, all_colors_data)
                for style in inline_styles:
                     if style['is_background']:
                         logging.debug(f"Fondo encontrado en estilo inline de <{tag_name}>: {style['color']}")
                         # Asegurarse de que no sea transparente
                         if style['color'].upper() != "#TRANSPARENT": # Asumiendo que _parse_color_value no lo devuelve
                            if not self._is_transparent(style['color']): # Doble check por si acaso
                                return style['color']

                # Buscar en reglas CSS que apunten específicamente a html o body
                for data in all_colors_data:
                     if data.get('selector') in [tag_name, f'html > {tag_name}'] and data['is_background']:
                         if not self._is_transparent(data['color']):
                            logging.debug(f"Fondo encontrado en regla CSS para <{tag_name}>: {data['color']}")
                            return data['color']


        # Prioridad 2: El color de fondo más frecuente
        bg_colors = [d['color'] for d in all_colors_data if d['is_background'] and not self._is_transparent(d['color'])]
        if bg_colors:
            most_common_bg = Counter(bg_colors).most_common(1)[0][0]
            logging.debug(f"Fondo determinado por frecuencia de 'background': {most_common_bg}")
            return most_common_bg

        # Prioridad 3: El color más claro encontrado (si no se encontró fondo explícito)
        all_colors_flat = [d['color'] for d in all_colors_data if not self._is_transparent(d['color'])]
        if all_colors_flat:
             lightest = self._find_lightest_color(all_colors_flat)
             if lightest:
                 logging.debug(f"Fondo determinado como el color más claro: {lightest}")
                 return lightest

        logging.warning("No se pudo determinar el color de fondo. Usando default.")
        return self.default_background

    def _is_transparent(self, color_value):
        # Simple check for 'transparent' keyword or RGBA with zero alpha
        # (Aunque _parse_color_value actualmente ignora alpha)
        if not color_value: return False
        val = color_value.strip().lower()
        if val == 'transparent': return True
        # Podríamos añadir parseo RGBA aquí si fuera necesario
        return False


    def _find_primary_color(self, soup, all_colors_data, potential_colors, bg_color):
        """Encuentra el color primario."""
        if not potential_colors: return self.default_primary

        # 1. Buscar en elementos prominentes (botones primarios, header, nav)
        for selector in self.primary_selectors:
            elements = soup.select(selector)
            for element in elements:
                 # Revisar estilos directos o reglas asociadas (heurística)
                 # Por simplicidad, buscamos colores en all_colors_data asociados a estos selectores si es posible
                 # O simplemente vemos si algún color prominente aparece en este elemento
                 inline_styles = self._get_element_styles(element, all_colors_data)
                 for style in inline_styles:
                      color = style['color']
                      if color in potential_colors and not self._is_neutral_color(color, threshold=30) and _calculate_contrast_ratio(color, bg_color) >= 3.0: # Contraste AA para texto grande
                           logging.debug(f"Primario encontrado en selector '{selector}': {color}")
                           return color

                 # Check general potential colors if found within the element's text or applied nearby
                 # This part is tricky without full rendering. Let's rely more on frequency/clustering.


        # 2. Usar Clustering (KMeans) sobre los colores potenciales
        clustered_colors = self._analyze_by_clustering(potential_colors, n_clusters=min(5, len(potential_colors)))
        if clustered_colors:
            for color in clustered_colors:
                if not self._is_neutral_color(color, threshold=30) and _calculate_contrast_ratio(color, bg_color) >= 3.0:
                    logging.debug(f"Primario encontrado por clustering: {color}")
                    return color

        # 3. Usar Frecuencia (excluyendo neutros si es posible)
        non_neutral = [c for c in potential_colors if not self._is_neutral_color(c, threshold=30) and _calculate_contrast_ratio(c, bg_color) >= 2.0] # Baja un poco el contraste si no hay opciones
        if non_neutral:
             freq_color = Counter(non_neutral).most_common(1)[0][0]
             logging.debug(f"Primario encontrado por frecuencia (no neutro): {freq_color}")
             return freq_color
        else: # Si solo hay neutros, tomar el más frecuente que contraste mínimamente
            contrast_colors = [c for c in potential_colors if _calculate_contrast_ratio(c, bg_color) >= 2.0]
            if contrast_colors:
                freq_color = Counter(contrast_colors).most_common(1)[0][0]
                logging.debug(f"Primario encontrado por frecuencia (neutro con contraste): {freq_color}")
                return freq_color


        # 4. Fallback al color más frecuente de los potenciales
        if potential_colors:
             fallback_color = Counter(potential_colors).most_common(1)[0][0]
             logging.debug(f"Primario encontrado por frecuencia (fallback): {fallback_color}")
             return fallback_color


        logging.warning("No se pudo determinar color primario. Usando default.")
        return self.default_primary


    def _find_accent_color(self, soup, all_colors_data, potential_colors, bg_color, primary_color):
        """Encuentra el color de acento."""
        candidates = [
            c for c in potential_colors
            if c != primary_color and not self._is_neutral_color(c, threshold=25) # Más estricto con neutros para acento
               and _calculate_contrast_ratio(c, bg_color) >= 3.0 # Contraste mínimo
        ]

        if not candidates:
             # Si no hay candidatos no neutros, buscar alguno que contraste y sea diferente
             candidates = [c for c in potential_colors if c != primary_color and _calculate_contrast_ratio(c, bg_color) >= 2.5]
             if not candidates:
                  logging.warning("No hay candidatos para color de acento. Usando default o fallback.")
                  return self._find_contrasting_fallback(bg_color, [self.default_accent, primary_color])


        # 1. Buscar en selectores de acento
        for selector in self.accent_selectors:
             elements = soup.select(selector)
             for element in elements:
                 inline_styles = self._get_element_styles(element, all_colors_data)
                 for style in inline_styles:
                      color = style['color']
                      if color in candidates:
                           logging.debug(f"Acento encontrado en selector '{selector}': {color}")
                           return color

        # 2. Usar Clustering
        clustered_colors = self._analyze_by_clustering(candidates, n_clusters=min(5, len(candidates)))
        if clustered_colors:
            for color in clustered_colors:
                if color != primary_color: # Asegurar que sea distinto del primario también
                     logging.debug(f"Acento encontrado por clustering: {color}")
                     return color

        # 3. Usar Frecuencia de los candidatos
        if candidates:
             freq_color = Counter(candidates).most_common(1)[0][0]
             logging.debug(f"Acento encontrado por frecuencia: {freq_color}")
             return freq_color

        # 4. Fallback: Tomar el primer candidato disponible
        if candidates:
             logging.debug(f"Acento encontrado como primer candidato: {candidates[0]}")
             return candidates[0]

        logging.warning("No se pudo determinar color de acento. Usando default o fallback.")
        return self._find_contrasting_fallback(bg_color, [self.default_accent, primary_color])

    def _find_contrasting_fallback(self, bg_color, colors_to_avoid):
        """Encuentra un color de fallback que contraste con el fondo, evitando ciertos colores."""
        defaults = [self.default_accent, "#FF4500", "#008B8B", "#FFD700", self.default_primary, "#D2691E"]
        for color in defaults:
            if color not in colors_to_avoid and _calculate_contrast_ratio(color, bg_color) >= 3.0:
                return color
        # Último recurso: invertir o complementar el fondo (muy básico)
        try:
            r, g, b = _hex_to_rgb_normalized(bg_color)
            inv_r, inv_g, inv_b = int((1-r)*255), int((1-g)*255), int((1-b)*255)
            inv_hex = _rgb_to_hex(inv_r, inv_g, inv_b)
            if inv_hex not in colors_to_avoid:
                 return inv_hex
        except:
            pass
        # Si todo falla, devolver el default accent original
        return self.default_accent


    def _analyze_by_clustering(self, hex_colors, n_clusters=5):
        """Utiliza K-means para encontrar colores representativos."""
        if not hex_colors or len(hex_colors) < n_clusters:
            # Devolver colores ordenados por frecuencia si no hay suficientes para clusterizar
            if hex_colors:
                return [c for c, _ in Counter(hex_colors).most_common(n_clusters)]
            return []

        valid_rgb_colors = []
        original_hex_map = {} # Mapea RGB tuple -> lista de HEX originales

        for hex_color in hex_colors:
            try:
                rgb_norm = _hex_to_rgb_normalized(hex_color)
                # Asegurar que la tupla RGB es válida antes de usarla
                if rgb_norm is not None and len(rgb_norm) == 3:
                     valid_rgb_colors.append(rgb_norm)
                     if rgb_norm not in original_hex_map:
                          original_hex_map[rgb_norm] = []
                     original_hex_map[rgb_norm].append(hex_color)
                else:
                     logging.debug(f"Color inválido o error de conversión ignorado para clustering: {hex_color}")
            except Exception as e:
                logging.debug(f"Excepción procesando color para clustering {hex_color}: {e}")
                continue

        if len(valid_rgb_colors) < n_clusters:
             logging.debug(f"No hay suficientes colores válidos ({len(valid_rgb_colors)}) para {n_clusters} clusters.")
             # Devolver los hex originales más frecuentes si no se puede clusterizar
             return [c for c, _ in Counter(hex_colors).most_common(n_clusters)]


        try:
            rgb_array = np.array(valid_rgb_colors)
            # n_init='auto' es la opción recomendada en versiones recientes de sklearn
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto', max_iter=100) # max_iter bajo para velocidad
            kmeans.fit(rgb_array)
            centroids_rgb_norm = kmeans.cluster_centers_
            labels = kmeans.labels_
            counts = np.bincount(labels, minlength=n_clusters)

            centroid_features = []
            for i, rgb_norm in enumerate(centroids_rgb_norm):
                 # Convertir centroide a Lab para evaluar luminosidad perceptual
                 try:
                      rgb_obj = sRGBColor(rgb_norm[0], rgb_norm[1], rgb_norm[2], is_upscaled=True) # is_upscaled si son 0-1
                      lab_obj = convert_color(rgb_obj, LabColor)
                      lightness = lab_obj.lab_l # 0 (negro) a 100 (blanco)
                      # Calcular saturación (aproximada desde Lab o convertir a HSL/HSV)
                      # Usaremos una aproximación con a* y b* (distancia desde el eje gris)
                      chroma = math.sqrt(lab_obj.lab_a**2 + lab_obj.lab_b**2)
                 except Exception as conv_err:
                      logging.debug(f"Error en conversión de color para centroide {rgb_norm}: {conv_err}")
                      lightness = 50 # Valor neutro
                      chroma = 0 # Sin color

                 # Score: favorece colores con croma (colorfulness), tamaño de cluster,
                 # y penaliza los extremos de luminosidad (muy negros/blancos)
                 l_penalty = 1.0 - abs(lightness - 50) / 50 # 1 si L=50, 0 si L=0 o L=100
                 # Ponderar más el croma y el tamaño del cluster
                 score = (chroma * 0.5 + l_penalty * 0.2) * (counts[i] ** 0.5) # Raíz cuadrada para no sobredimensionar clusters grandes

                 # Convertir centroide a HEX para devolverlo
                 r, g, b = [max(0, min(255, int(c * 255))) for c in rgb_norm]
                 hex_color = _rgb_to_hex(r, g, b)

                 centroid_features.append({'hex': hex_color, 'score': score, 'cluster_index': i})

            # Ordenar por score descendente
            centroid_features.sort(key=lambda x: x['score'], reverse=True)

            # Devolver los HEX de los centroides ordenados
            return [feature['hex'] for feature in centroid_features]

        except Exception as e:
            logging.error(f"Error durante clustering K-Means: {e}")
            # Fallback: devolver los más frecuentes
            return [c for c, _ in Counter(hex_colors).most_common(n_clusters)]


    def _find_lightest_color(self, colors):
        """Encuentra el color más claro (mayor L*) de la lista."""
        lightest_color = None
        max_l = -1

        for hex_color in colors:
            try:
                rgb_norm = _hex_to_rgb_normalized(hex_color)
                if rgb_norm is None: continue

                rgb_obj = sRGBColor(rgb_norm[0], rgb_norm[1], rgb_norm[2], is_upscaled=True)
                lab_obj = convert_color(rgb_obj, LabColor)

                if lab_obj.lab_l > max_l:
                    max_l = lab_obj.lab_l
                    lightest_color = hex_color
            except Exception as e:
                logging.debug(f"Error al calcular L* para {hex_color}: {e}")
                continue

        return lightest_color

    def _is_neutral_color(self, hex_color, threshold=15):
        """Determina si un color es casi neutro (blanco, negro, gris) basado en Lab."""
        try:
            rgb_norm = _hex_to_rgb_normalized(hex_color)
            if rgb_norm is None: return False # No se pudo convertir

            # Blancos y negros puros
            if hex_color in ["#FFFFFF", "#000000"]: return True

            rgb_obj = sRGBColor(rgb_norm[0], rgb_norm[1], rgb_norm[2], is_upscaled=True)
            lab_obj = convert_color(rgb_obj, LabColor)

            # Comprobar si está cerca del eje acromático (a* y b* cerca de 0)
            # y no es extremadamente claro u oscuro (esos son blanco/negro)
            chroma = math.sqrt(lab_obj.lab_a**2 + lab_obj.lab_b**2)

            # Es gris si tiene baja cromaticidad
            # Aumentamos el umbral de 'threshold' para considerar más colores como neutros
            # si su luminosidad es muy alta o muy baja.
            l = lab_obj.lab_l
            adjusted_threshold = threshold
            if l > 90 or l < 10: # Si es casi blanco o casi negro
                 adjusted_threshold = threshold * 1.8 # Permitir más desviación a/b

            # print(f"Color: {hex_color}, L*: {l:.1f}, a*: {lab_obj.lab_a:.1f}, b*: {lab_obj.lab_b:.1f}, Chroma: {chroma:.1f}, Threshold: {adjusted_threshold:.1f}")

            return chroma < adjusted_threshold

        except Exception as e:
            logging.debug(f"Error al verificar neutralidad de {hex_color}: {e}")
            return False # Asumir no neutro en caso de error

# --- Ejemplo de uso ---
if __name__ == '__main__':
    extractor = ColorExtractor()

    # Ejemplo con URL
    # url = "https://stripe.com/" # Ejemplo de web con esquema claro
    url = "https://github.com/" # Ejemplo con modo oscuro/claro (depende de tu sistema/navegador)
    # url = "https://vibertiol.com" # Ejemplo con colores vibrantes
    # url = "https://www.mozilla.org/es-ES/" # Ejemplo con varios colores
    # url = "https://tailwindcss.com/"

    print(f"Extrayendo colores de: {url}")
    try:
        colors = extractor.extract_from_url(url)
        print("\nColores extraídos:")
        print(f"  Primario:  {colors[0]}")
        print(f"  Fondo:     {colors[1]}")
        print(f"  Acento:    {colors[2]}")

        # Visualización simple en HTML (opcional)
        html_output = f"""
        <html><head><title>Colores Extraídos de {url}</title></head>
        <body style="background-color: {colors[1]}; color: {colors[0]}; font-family: sans-serif; padding: 20px;">
            <h1>Colores Extraídos de {url}</h1>
            <div style="display: flex; gap: 20px; margin-top: 20px;">
                <div style="text-align: center;">
                    <div style="width: 100px; height: 100px; background-color: {colors[0]}; border: 1px solid #ccc;"></div>
                    <p>Primario<br>{colors[0]}</p>
                </div>
                <div style="text-align: center;">
                    <div style="width: 100px; height: 100px; background-color: {colors[1]}; border: 1px solid #ccc;"></div>
                    <p style="color: {'#000' if _get_relative_luminance(_hex_to_rgb_normalized(colors[1])) > 0.5 else '#FFF'};">Fondo<br>{colors[1]}</p>
                </div>
                <div style="text-align: center;">
                    <div style="width: 100px; height: 100px; background-color: {colors[2]}; border: 1px solid #ccc;"></div>
                    <p>Acento<br>{colors[2]}</p>
                </div>
            </div>
            <p style="margin-top: 30px;">Ratio de Contraste (Primario/Fondo): {_calculate_contrast_ratio(colors[0], colors[1]):.2f}:1</p>
            <p>Ratio de Contraste (Acento/Fondo): {_calculate_contrast_ratio(colors[2], colors[1]):.2f}:1</p>
        </body></html>
        """
        with open("color_preview.html", "w", encoding='utf-8') as f:
            f.write(html_output)
        print("\nVista previa guardada en 'color_preview.html'")

    except Exception as e:
        print(f"\nError al extraer colores: {e}")

    print("-" * 30)

    # Ejemplo con HTML directo (sin base_url, no podrá resolver CSS externos relativos)
    # sample_html = """
    # <!DOCTYPE html><html><head><title>Test</title>
    # <style>
    #   body { background-color: #f0f0f0; color: #333; }
    #   .container { background: white; padding: 1em; }
    #   h1 { color: darkblue; }
    #   .btn-primary { background-color: cornflowerblue; color: white; padding: 10px; border: none; }
    #   .highlight { color: #FF6347; /* Tomato */ }
    # </style>
    # </head><body>
    # <div class="container">
    #   <h1>Título Principal</h1><p>Texto de ejemplo.</p>
    #   <button class="btn-primary">Botón Primario</button>
    #   <p>Otro texto con <span class="highlight">algo resaltado</span>.</p>
    # </div></body></html>
    # """
    # print("\nExtrayendo colores de HTML de ejemplo:")
    # try:
    #     colors_html = extractor.extract_from_html(sample_html)
    #     print("\nColores extraídos:")
    #     print(f"  Primario:  {colors_html[0]}")
    #     print(f"  Fondo:     {colors_html[1]}")
    #     print(f"  Acento:    {colors_html[2]}")
    # except Exception as e:
    #     print(f"\nError al extraer colores del HTML: {e}")