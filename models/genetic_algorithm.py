import random
import numpy as np
from models.color_utils import hex_to_rgb, rgb_to_lab, lab_to_rgb, rgb_to_hex, get_delta_e
from models.accessibility import contrast_ratio, evaluate_color_blindness
import logging

cssutils_logger = logging.getLogger('cssutils')

class SimpleLogbook:
    """Clase simple para emular el comportamiento de DEAP Logbook"""
    def __init__(self):
        self.data = {}
        
    def record(self, gen, **kwargs):
        """Registra datos para una generación"""
        for key, value in kwargs.items():
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)
        if 'gen' not in self.data:
            self.data['gen'] = []
        self.data['gen'].append(gen)
    
    def select(self, key):
        """Selecciona columna de datos"""
        return self.data.get(key, [])

class ColorPaletteGA:
    def __init__(self, initial_colors, wcag_level="AA", population_size=50, generations=30, 
                 mutation_prob=0.15, accessibility_weight=0.7, initial_weight=0.3):
        """
        Inicialización del algoritmo genético para paletas de colores
        
        Args:
            initial_colors: Lista de tres colores iniciales [primario, fondo, acento] en formato hex
            wcag_level: Nivel de accesibilidad 'AA' o 'AAA'
            population_size: Tamaño de la población
            generations: Número de generaciones
            mutation_prob: Probabilidad de mutación
            accessibility_weight: Peso relativo accesibilidad vs estética (0-1)
            initial_weight: Peso para preservar similitud con colores iniciales (0-1)
        """
        self.initial_colors = initial_colors
        self.initial_rgbs = [hex_to_rgb(color) for color in initial_colors]
        self.initial_labs = [rgb_to_lab(rgb) for rgb in self.initial_rgbs]
        
        self.wcag_level = wcag_level
        self.min_contrast = 7.0 if wcag_level == "AAA" else 4.5
        self.min_population = max(5, population_size // 5)  # Al menos 5 o 20% del tamaño máximo
        self.max_population = population_size
        self.population_size = population_size
        self.generations = generations
        self.mutation_prob = mutation_prob
        self.bit_mutation_prob = 0.2  # Probabilidad de mutación por componente
        self.accessibility_weight = accessibility_weight
        self.initial_weight = initial_weight
        
        # Definimos límites para los valores LAB
        self.L_ranges = [
            (20, 80),  # Rango para primario
            (50, 100), # Luminosidad alta para fondos
            (20, 80)   # Para acentos, más rango de luminosidad
        ]
        self.a_b_range = (-128, 128)  # Rango completo para a y b
        
        # Resultados
        self.hall_of_fame = []
        self.logbook = SimpleLogbook()
        
    def initialize_population(self):
        """Inicializa la población de paletas basadas en los colores iniciales"""
        population = []
        
        # Incluir la paleta original como parte de la población inicial
        initial_palette = []
        for lab in self.initial_labs:
            initial_palette.extend([lab[0], lab[1], lab[2]])
        population.append(initial_palette)
        
        # Generar el resto de la población con variaciones de los colores iniciales
        for _ in range(self.population_size - 1):
            palette = []
            for i, initial_lab in enumerate(self.initial_labs):
                # Variación aleatoria basada en el color inicial
                L_range = self.L_ranges[i]
                
                # Variación de L con sesgo hacia el valor original
                L = initial_lab[0] + random.gauss(0, 10)
                L = max(L_range[0], min(L_range[1], L))
                
                # Variación de a y b
                a = initial_lab[1] + random.gauss(0, 15)
                a = max(self.a_b_range[0], min(self.a_b_range[1], a))
                
                b = initial_lab[2] + random.gauss(0, 15)
                b = max(self.a_b_range[0], min(self.a_b_range[1], b))
                
                palette.extend([L, a, b])
            
            population.append(palette)
            
        return population
    
    def fitness(self, individual):
        """Evalúa la aptitud de una paleta completa"""
        # Extraer componentes LAB de los tres colores
        primary_lab = tuple(individual[0:3])
        bg_lab = tuple(individual[3:6])
        accent_lab = tuple(individual[6:9])
        
        # Convertir a RGB para cálculos de contraste
        try:
            primary_rgb = lab_to_rgb(primary_lab)
            bg_rgb = lab_to_rgb(bg_lab)
            accent_rgb = lab_to_rgb(accent_lab)
        except:
            # Si la conversión falla (fuera de gamut), penalizar
            return 0.0
        
        # 1. Evaluar contraste entre colores
        contrasts = [
            contrast_ratio(primary_rgb, bg_rgb),
            contrast_ratio(primary_rgb, accent_rgb),
            contrast_ratio(bg_rgb, accent_rgb)
        ]
        
        # Necesitamos que al menos dos contrastes cumplan con el mínimo
        contrast_scores = [min(c / self.min_contrast, 1.0) for c in contrasts]
        avg_contrast_score = sum(contrast_scores) / len(contrast_scores)
        
        # Contar cuántos pares tienen buen contraste
        good_contrasts = sum(1 for c in contrasts if c >= self.min_contrast)
        
        # Fuerte penalización si no hay al menos dos buenos contrastes
        if good_contrasts < 2:
            contrast_penalty = 0.5
        else:
            contrast_penalty = 1.0
        
        # 2. Evaluar fidelidad a los colores iniciales
        fidelity_scores = []
        for i, color_lab in enumerate([primary_lab, bg_lab, accent_lab]):
            initial_lab = self.initial_labs[i]
            delta_e = get_delta_e(color_lab, initial_lab)
            fidelity_score = max(0, 1.0 - (delta_e / 30.0))
            fidelity_scores.append(fidelity_score)
        
        avg_fidelity_score = sum(fidelity_scores) / len(fidelity_scores)
        
        # 3. Evaluar legibilidad con daltonismo
        cb_scores = []
        for i in range(len(contrasts)):
            rgb1, rgb2 = [(primary_rgb, bg_rgb), (primary_rgb, accent_rgb), (bg_rgb, accent_rgb)][i]
            cb_results = evaluate_color_blindness(rgb1, rgb2)
            
            for cb_type, cb_contrast in cb_results.items():
                cb_scores.append(min(cb_contrast / self.min_contrast, 1.0))
        
        avg_cb_score = sum(cb_scores) / len(cb_scores)
        
        # 4. Evaluar armonía de colores (distancia perceptual balanceada)
        harmony_score = 1.0
        
        # Queremos que los colores tengan buena separación pero no excesiva
        for i in range(len(contrasts)):
            color1_lab, color2_lab = [(primary_lab, bg_lab), (primary_lab, accent_lab), (bg_lab, accent_lab)][i]
            delta_e = get_delta_e(color1_lab, color2_lab)
            
            # Penalizar colores muy cercanos o extremadamente distantes
            # Ideal: entre 25 y 80
            if delta_e < 15:
                harmony_factor = delta_e / 15
            elif delta_e > 100:
                harmony_factor = max(0, 1 - (delta_e - 100) / 50)
            else:
                harmony_factor = 1.0
            
            harmony_score *= harmony_factor
        
        # Puntuación final
        accessibility_score = (avg_contrast_score * 0.6 + avg_cb_score * 0.4) * contrast_penalty
        aesthetic_score = (avg_fidelity_score * 0.7 + harmony_score * 0.3)
        
        aesthetic_score = (avg_fidelity_score * 0.7 + harmony_score * 0.3) * (1 + self.initial_weight)
        
        final_score = (accessibility_score * self.accessibility_weight + 
               aesthetic_score * (1 - self.accessibility_weight))
        
        return final_score
    
    def select_best(self, population, num_selected=None):
        """Selecciona los mejores individuos de la población"""
        if num_selected is None:
            num_selected = max(self.min_population, len(population) // 2)
            
        # Calcular fitness para toda la población
        fitness_values = [(individual, self.fitness(individual)) for individual in population]
        
        # Ordenar por fitness (mayor a menor)
        sorted_population = sorted(fitness_values, key=lambda x: x[1], reverse=True)
        
        # Seleccionar los mejores
        selected = [ind for ind, _ in sorted_population[:num_selected]]
        
        return selected
    
    def select_for_mating(self, population):
        """Selección por torneo para reproducción"""
        tournament_size = 3
        selected_pairs = []
        
        # Determinar cuántos pares necesitamos para mantener el tamaño de población
        num_pairs = max(self.min_population, len(population) // 2)
        
        for _ in range(num_pairs):
            # Seleccionar individuos para el torneo
            tournament1 = random.sample(population, tournament_size)
            tournament2 = random.sample(population, tournament_size)
            
            # Seleccionar ganadores del torneo
            winner1 = max(tournament1, key=self.fitness)
            winner2 = max(tournament2, key=self.fitness)
            
            # Añadir par para cruce
            selected_pairs.append((winner1, winner2))
            
        return selected_pairs
    
    def crossover(self, population):
        """Realiza cruce entre pares seleccionados"""
        # Seleccionar pares para cruce
        pairs = self.select_for_mating(population)
        
        # Nueva población después del cruce
        new_population = []
        
        # Realizar cruce blend
        for parent1, parent2 in pairs:
            # Verificar probabilidad de cruce
            if random.random() <= 0.7:  # Probabilidad de cruce
                alpha = 0.5  # Parámetro de mezcla para cruce blend
                
                child1 = []
                child2 = []
                
                # Para cada componente
                for i in range(len(parent1)):
                    # Determinar el rango apropiado para este componente
                    if i % 3 == 0:  # Componente L
                        color_idx = i // 3
                        value_range = self.L_ranges[color_idx]
                    else:  # Componentes a y b
                        value_range = self.a_b_range
                    
                    # Cruce blend: mezcla usando alpha
                    gamma = (1.0 + 2.0 * alpha) * random.random() - alpha
                    
                    # Crear hijos como mezcla de padres
                    value1 = (1.0 - gamma) * parent1[i] + gamma * parent2[i]
                    value2 = gamma * parent1[i] + (1.0 - gamma) * parent2[i]
                    
                    # Asegurar que están dentro de los límites
                    value1 = max(value_range[0], min(value_range[1], value1))
                    value2 = max(value_range[0], min(value_range[1], value2))
                    
                    child1.append(value1)
                    child2.append(value2)
                
                new_population.extend([child1, child2])
            else:
                # Si no hay cruce, los padres pasan directamente
                new_population.extend([parent1[:], parent2[:]])
        
        return new_population, len(pairs)
    
    def _mutate_palette(self, individual, indpb):
        """Operador de mutación para paleta completa"""
        mutated = individual[:]
        individual_mutated = False
        
        for i in range(len(individual)):
            if random.random() < indpb:
                # Determinar el rango apropiado para este componente
                if i % 3 == 0:  # Componente L
                    color_idx = i // 3
                    value_range = self.L_ranges[color_idx]
                    # Mutación gaussiana con desviación estándar basada en el rango
                    std_dev = (value_range[1] - value_range[0]) / 10
                    mutated[i] += random.gauss(0, std_dev)
                    mutated[i] = max(value_range[0], min(value_range[1], mutated[i]))
                else:  # Componentes a y b
                    mutated[i] += random.gauss(0, 10)  # Mayor variación en color
                    mutated[i] = max(self.a_b_range[0], min(self.a_b_range[1], mutated[i]))
                
                individual_mutated = True
        
        return (mutated,)
    
    def prune_population(self, population):
        """Reduce la población al tamaño máximo permitido"""
        if len(population) <= self.max_population:
            return population
        
        # Eliminar duplicados si hubiera
        population_tuples = [tuple(ind) for ind in population]
        unique_indices = []
        seen = set()
        
        for i, tup in enumerate(population_tuples):
            if tup not in seen:
                seen.add(tup)
                unique_indices.append(i)
        
        population = [population[i] for i in unique_indices]
        
        if len(population) <= self.max_population:
            return population
        
        # Calcular fitness para cada individuo
        fitness_values = [(individual, self.fitness(individual)) for individual in population]
        
        # Ordenar por fitness (mayor a menor)
        sorted_population = sorted(fitness_values, key=lambda x: x[1], reverse=True)
        
        # Asegurar que el mejor individuo siempre está presente
        best_individual = sorted_population[0][0]
        
        # Seleccionar aleatoriamente del resto para mantener diversidad
        remaining = [ind for ind, _ in sorted_population[1:]]
        
        if len(remaining) + 1 > self.max_population:
            # Usar numpy para selección aleatoria eficiente
            indices = np.random.choice(
                len(remaining),
                size=self.max_population - 1,
                replace=False
            )
            remaining = [remaining[i] for i in indices]
        
        # Población final: mejor individuo + selección aleatoria del resto
        final_population = [best_individual] + remaining
        
        return final_population
    
    def run(self):
        """Ejecuta el algoritmo genético"""
        # Inicializar población
        pop = self.initialize_population()
        
        # Para almacenar el mejor individuo global
        self.hall_of_fame = []
        
        # Registro para estadísticas
        logbook = SimpleLogbook()
        
        # Ejecutar generaciones
        for gen in range(self.generations):
            # Calcular fitness de la población actual
            fitness_values = [self.fitness(ind) for ind in pop]
            avg_fitness = np.mean(fitness_values)
            min_fitness = np.min(fitness_values)
            max_fitness = np.max(fitness_values)
            
            # Registrar estadísticas con nombres compatibles con DEAP
            logbook.record(gen, avg=avg_fitness, max=max_fitness, min=min_fitness)
            
            # Imprimir progreso
            print(f"Gen {gen}: Avg={avg_fitness:.4f}, Max={max_fitness:.4f}, Min={min_fitness:.4f}")
            
            # Actualizar hall of fame con el mejor individuo
            best_idx = np.argmax(fitness_values)
            best_ind = pop[best_idx]
            
            # Añadir a hall of fame si es bueno
            if not self.hall_of_fame or self.fitness(best_ind) > self.fitness(self.hall_of_fame[0]):
                if len(self.hall_of_fame) >= 10:
                    self.hall_of_fame.pop()  # Eliminar el peor
                self.hall_of_fame.insert(0, best_ind)  # Insertar al principio
            
            # Selección
            selected = self.select_best(pop)
            
            # Cruce
            offspring, _ = self.crossover(selected)
            
            # Mutación - aplicar a cada individuo
            mutated_offspring = []
            for ind in offspring:
                if random.random() <= self.mutation_prob:
                    mutated = self._mutate_palette(ind, 0.4)[0]
                    mutated_offspring.append(mutated)
                else:
                    mutated_offspring.append(ind)
            
            # Combinar con la población anterior para mantener elitismo
            combined = pop + mutated_offspring
            
            # Podar para volver al tamaño máximo
            pop = self.prune_population(combined)
        
        # Guardar registro final
        self.logbook = logbook
        
        return self.hall_of_fame, self.logbook
    
    def get_best_palettes(self, num=3):
        """Devuelve las mejores paletas encontradas"""
        if not self.hall_of_fame:
            return []
        
        # Calcular fitness para todos los individuos en el hall of fame
        hall_fitness = [(ind, self.fitness(ind)) for ind in self.hall_of_fame]
        
        # Ordenar por fitness (mayor a menor)
        sorted_hall = sorted(hall_fitness, key=lambda x: x[1], reverse=True)
        
        # Limitar al número solicitado
        top_individuals = [ind for ind, _ in sorted_hall[:num]]
        
        palettes = []
        for ind in top_individuals:
            # Extraer los tres colores
            colors_lab = [
                tuple(ind[0:3]),    # Color primario
                tuple(ind[3:6]),    # Color de fondo
                tuple(ind[6:9])     # Color de acento
            ]
            
            try:
                # Convertir a RGB y HEX
                colors_rgb = [lab_to_rgb(lab) for lab in colors_lab]
                colors_hex = [rgb_to_hex(rgb) for rgb in colors_rgb]
                
                # Calcular métricas
                contrasts = [
                    contrast_ratio(colors_rgb[0], colors_rgb[1]),  # Primario vs Fondo
                    contrast_ratio(colors_rgb[0], colors_rgb[2]),  # Primario vs Acento
                    contrast_ratio(colors_rgb[1], colors_rgb[2])   # Fondo vs Acento
                ]
                
                # Promedio de contraste
                avg_contrast = sum(contrasts) / len(contrasts)
                
                # Delta-E respecto a colores originales (promedio)
                delta_es = [get_delta_e(colors_lab[i], self.initial_labs[i]) for i in range(3)]
                avg_delta_e = sum(delta_es) / len(delta_es)
                
                # Evaluación con daltonismo (promedio)
                cb_results = {}
                for i in range(len(contrasts)):
                    rgb1, rgb2 = [(colors_rgb[0], colors_rgb[1]), 
                                  (colors_rgb[0], colors_rgb[2]), 
                                  (colors_rgb[1], colors_rgb[2])][i]
                    cb = evaluate_color_blindness(rgb1, rgb2)
                    
                    for cb_type, cb_contrast in cb.items():
                        if cb_type not in cb_results:
                            cb_results[cb_type] = []
                        cb_results[cb_type].append(cb_contrast)
                
                # Porcentaje de combinaciones que cumplen con el contraste mínimo para daltónicos
                cb_valid_count = 0
                cb_total = 0
                
                for cb_type, cb_contrasts in cb_results.items():
                    for contrast in cb_contrasts:
                        cb_total += 1
                        if contrast >= self.min_contrast:
                            cb_valid_count += 1
                
                cb_percent = (cb_valid_count / cb_total * 100) if cb_total > 0 else 0
                
                palettes.append({
                    "colors": colors_hex,
                    "contrast": f"{avg_contrast:.2f}:1",
                    "delta_e": f"{avg_delta_e:.2f}",
                    "daltonism": f"{cb_percent:.0f}% válido"
                })
            except:
                # Si hay error en la conversión, omitir esta paleta
                continue
        
        return palettes