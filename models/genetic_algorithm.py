import random
import numpy as np
from deap import base, creator, tools, algorithms

from models.color_utils import hex_to_rgb, rgb_to_lab, lab_to_rgb, rgb_to_hex, get_delta_e
from models.accessibility import contrast_ratio, evaluate_color_blindness

class ColorPaletteGA:
    def __init__(self, base_color, wcag_level="AA", population_size=50, generations=30, 
                 mutation_prob=0.15, accessibility_weight=0.7):
        """
        Inicialización del algoritmo genético para paletas de colores
        
        Args:
            base_color: Color primario de la marca (hex)
            wcag_level: Nivel de accesibilidad 'AA' o 'AAA'
            population_size: Tamaño de la población
            generations: Número de generaciones
            mutation_prob: Probabilidad de mutación
            accessibility_weight: Peso relativo accesibilidad vs estética (0-1)
        """
        self.base_color = base_color
        self.base_rgb = hex_to_rgb(base_color)
        self.base_lab = rgb_to_lab(self.base_rgb)
        self.wcag_level = wcag_level
        self.min_contrast = 7.0 if wcag_level == "AAA" else 4.5
        self.population_size = population_size
        self.generations = generations
        self.mutation_prob = mutation_prob
        self.accessibility_weight = accessibility_weight
        
        # Configurar DEAP
        self._setup_ga()
        
        # Resultados
        self.hall_of_fame = None
        self.logbook = None
        
    def _setup_ga(self):
        """Configura componentes del algoritmo genético"""
        if hasattr(creator, "FitnessMax"):
            del creator.FitnessMax
        if hasattr(creator, "Individual"):
            del creator.Individual
            
        # Definir problema de maximización
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        
        # Definir individuo (una paleta de colores)
        # Cada individuo será [bg_L, bg_a, bg_b, accent_L, accent_a, accent_b]
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        self.toolbox = base.Toolbox()
        
        # Generadores para componentes L*a*b*
        self.toolbox.register("L_value", random.uniform, 50, 100)  # Luminosidad alta para fondos
        self.toolbox.register("a_value", random.uniform, -128, 128)
        self.toolbox.register("b_value", random.uniform, -128, 128)
        
        # Para colores de acento, permitimos más saturación
        self.toolbox.register("accent_L", random.uniform, 20, 80)
        self.toolbox.register("accent_a", random.uniform, -128, 128)
        self.toolbox.register("accent_b", random.uniform, -128, 128)
        
        # Crear un individuo
        self.toolbox.register("individual", tools.initCycle, creator.Individual,
                             (self.toolbox.L_value, self.toolbox.a_value, self.toolbox.b_value,
                              self.toolbox.accent_L, self.toolbox.accent_a, self.toolbox.accent_b), n=1)
        
        # Crear población
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Función de evaluación
        self.toolbox.register("evaluate", self._evaluate_palette)
        
        # Operadores genéticos
        self.toolbox.register("mate", tools.cxBlend, alpha=0.5)
        self.toolbox.register("mutate", self._mutate_color_palette, indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)
    
    def _evaluate_palette(self, individual):
        """Evalúa una paleta de colores según múltiples criterios"""
        # Extraer componentes LAB
        bg_lab = tuple(individual[0:3])
        accent_lab = tuple(individual[3:6])
        
        # Convertir a RGB para cálculos de contraste
        try:
            bg_rgb = lab_to_rgb(bg_lab)
            accent_rgb = lab_to_rgb(accent_lab)
        except:
            # Si la conversión falla (fuera de gamut), penalizar
            return (0.0,)
        
        # 1. Evaluar contraste WCAG
        contrast = contrast_ratio(bg_rgb, accent_rgb)
        contrast_score = min(contrast / self.min_contrast, 1.0)
        
        if contrast < self.min_contrast:
            contrast_penalty = (contrast / self.min_contrast) ** 2
        else:
            contrast_penalty = 1.0
        
        # 2. Evaluar fidelidad al color de marca
        delta_e = get_delta_e(accent_lab, self.base_lab)
        fidelity_score = max(0, 1.0 - (delta_e / 30.0))
        
        # 3. Evaluar legibilidad con daltonismo
        cb_results = evaluate_color_blindness(bg_rgb, accent_rgb)
        cb_scores = []
        
        for cb_type, cb_contrast in cb_results.items():
            cb_scores.append(min(cb_contrast / self.min_contrast, 1.0))
        
        cb_score = sum(cb_scores) / len(cb_scores)
        
        # 4. Penalizar colores muy saturados para fondos
        saturation_penalty = 1.0
        bg_saturation = np.sqrt(bg_lab[1]**2 + bg_lab[2]**2)
        if bg_saturation > 25:
            saturation_penalty = max(0.5, 1.0 - (bg_saturation - 25) / 75)
        
        # Puntuación final
        accessibility_score = (contrast_score * 0.7 + cb_score * 0.3) * contrast_penalty * saturation_penalty
        aesthetic_score = fidelity_score
        
        final_score = (accessibility_score * self.accessibility_weight + 
                      aesthetic_score * (1 - self.accessibility_weight))
        
        return (final_score,)
    
    def _mutate_color_palette(self, individual, indpb):
        """Operador de mutación personalizado"""
        for i in range(len(individual)):
            if random.random() < indpb:
                if i % 3 == 0:  # Componente L
                    if i == 0:  # Fondo: más claro
                        individual[i] += random.gauss(0, 5)
                        individual[i] = max(50, min(100, individual[i]))
                    else:  # Acento: cualquier luminosidad
                        individual[i] += random.gauss(0, 10)
                        individual[i] = max(20, min(80, individual[i]))
                else:  # Componentes a y b
                    individual[i] += random.gauss(0, 8)
                    individual[i] = max(-128, min(128, individual[i]))
        
        return individual,
    
    def run(self):
        """Ejecuta el algoritmo genético"""
        # Población inicial
        pop = self.toolbox.population(n=self.population_size)
        
        # Hall of Fame para guardar mejores individuos
        hof = tools.HallOfFame(10)
        
        # Estadísticas
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        # Ejecutar algoritmo
        pop, logbook = algorithms.eaSimple(
            pop, self.toolbox, 
            cxpb=0.7,  # Probabilidad de cruce
            mutpb=self.mutation_prob, 
            ngen=self.generations, 
            stats=stats, 
            halloffame=hof, 
            verbose=True
        )
        
        self.hall_of_fame = hof
        self.logbook = logbook
        
        return hof, logbook
    
    def get_best_palettes(self, num=3):
        """Devuelve las mejores paletas encontradas"""
        if not self.hall_of_fame:
            return []
        
        palettes = []
        for i, ind in enumerate(self.hall_of_fame[:num]):
            # Convertir a formatos utilizables
            bg_lab = tuple(ind[0:3])
            accent_lab = tuple(ind[3:6])
            
            bg_rgb = lab_to_rgb(bg_lab)
            accent_rgb = lab_to_rgb(accent_lab)
            
            bg_hex = rgb_to_hex(bg_rgb)
            accent_hex = rgb_to_hex(accent_rgb)
            
            # Calcular métricas
            contrast = contrast_ratio(bg_rgb, accent_rgb)
            delta_e = get_delta_e(accent_lab, self.base_lab)
            
            # Evaluar con daltonismo
            cb_results = evaluate_color_blindness(bg_rgb, accent_rgb)
            cb_valid = sum(1 for c in cb_results.values() if c >= self.min_contrast)
            cb_percent = (cb_valid / len(cb_results)) * 100
            
            palettes.append({
                "colors": [self.base_color, bg_hex, accent_hex],
                "contrast": f"{contrast:.1f}:1",
                "delta_e": f"{delta_e:.1f}",
                "daltonism": f"{cb_percent:.0f}% válido"
            })
        
        return palettes