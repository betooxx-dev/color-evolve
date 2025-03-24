import random
import numpy as np
from models.color_utils import hex_to_rgb, rgb_to_lab, lab_to_rgb, rgb_to_hex, get_delta_e
from models.accessibility import contrast_ratio, evaluate_color_blindness

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
        self.min_population = max(5, population_size // 5)  # Al menos 5 o 20% del tamaño máximo
        self.max_population = population_size
        self.population_size = population_size
        self.generations = generations
        self.mutation_prob = mutation_prob
        self.bit_mutation_prob = 0.2  # Probabilidad de mutación por componente
        self.accessibility_weight = accessibility_weight
        
        # Definimos límites para los valores LAB
        self.bg_L_range = (50, 100)  # Luminosidad alta para fondos
        self.accent_L_range = (20, 80)  # Para acentos, más rango de luminosidad
        self.a_b_range = (-128, 128)  # Rango completo para a y b
        
        # Resultados
        self.hall_of_fame = []
        self.logbook = SimpleLogbook()
        
    def initialize_population(self):
        """Inicializa la población con valores aleatorios en espacios LAB apropiados"""
        population = []
        
        for _ in range(self.population_size):
            # Generamos componentes LAB para fondo
            bg_L = random.uniform(*self.bg_L_range)
            bg_a = random.uniform(*self.a_b_range)
            bg_b = random.uniform(*self.a_b_range)
            
            # Generamos componentes LAB para acento
            accent_L = random.uniform(*self.accent_L_range)
            accent_a = random.uniform(*self.a_b_range)
            accent_b = random.uniform(*self.a_b_range)
            
            # Creamos el individuo
            individual = [bg_L, bg_a, bg_b, accent_L, accent_a, accent_b]
            population.append(individual)
            
        return population
    
    def fitness(self, individual):
        """Evalúa un individuo según criterios de accesibilidad y estética"""
        # Extraer componentes LAB
        bg_lab = tuple(individual[0:3])
        accent_lab = tuple(individual[3:6])
        
        # Convertir a RGB para cálculos de contraste
        try:
            bg_rgb = lab_to_rgb(bg_lab)
            accent_rgb = lab_to_rgb(accent_lab)
        except:
            # Si la conversión falla (fuera de gamut), penalizar
            return 0.0
        
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
                    # Cruce blend: mezcla usando alpha
                    gamma = (1.0 + 2.0 * alpha) * random.random() - alpha
                    
                    # Crear hijos como mezcla de padres
                    value1 = (1.0 - gamma) * parent1[i] + gamma * parent2[i]
                    value2 = gamma * parent1[i] + (1.0 - gamma) * parent2[i]
                    
                    # Asegurar que están dentro de los límites
                    if i == 0:  # bg_L
                        value1 = max(self.bg_L_range[0], min(self.bg_L_range[1], value1))
                        value2 = max(self.bg_L_range[0], min(self.bg_L_range[1], value2))
                    elif i == 3:  # accent_L
                        value1 = max(self.accent_L_range[0], min(self.accent_L_range[1], value1))
                        value2 = max(self.accent_L_range[0], min(self.accent_L_range[1], value2))
                    else:  # a y b
                        value1 = max(self.a_b_range[0], min(self.a_b_range[1], value1))
                        value2 = max(self.a_b_range[0], min(self.a_b_range[1], value2))
                    
                    child1.append(value1)
                    child2.append(value2)
                
                new_population.extend([child1, child2])
            else:
                # Si no hay cruce, los padres pasan directamente
                new_population.extend([parent1[:], parent2[:]])
        
        return new_population, len(pairs)
    
    def _mutate_color_palette(self, individual, indpb):
        """Operador de mutación personalizado, compatible con la interfaz original"""
        mutated = individual[:]
        individual_mutated = False
        
        for i in range(len(individual)):
            if random.random() < indpb:
                if i % 3 == 0:  # Componente L
                    if i == 0:  # Fondo: más claro
                        mutated[i] += random.gauss(0, 5)
                        mutated[i] = max(self.bg_L_range[0], min(self.bg_L_range[1], mutated[i]))
                    else:  # Acento: cualquier luminosidad
                        mutated[i] += random.gauss(0, 10)
                        mutated[i] = max(self.accent_L_range[0], min(self.accent_L_range[1], mutated[i]))
                else:  # Componentes a y b
                    mutated[i] += random.gauss(0, 8)
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
                    mutated = self._mutate_color_palette(ind, 0.2)[0]
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
            # Convertir a formatos utilizables
            bg_lab = tuple(ind[0:3])
            accent_lab = tuple(ind[3:6])
            
            try:
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
            except:
                # Si hay error en la conversión, omitir esta paleta
                continue
        
        return palettes