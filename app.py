from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')  # No usar interfaz gráfica
import matplotlib.pyplot as plt
import numpy as np
import base64
from io import BytesIO
import json
from models.color_extractor import ColorExtractor

from models.genetic_algorithm import ColorPaletteGA

app = Flask(__name__)

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Genera paletas de colores basadas en parámetros"""
    # Obtener colores iniciales del formulario
    primary_color = request.form.get('primary_color', '#3A5FCD')
    bg_color = request.form.get('bg_color', '#FFFFFF')
    accent_color = request.form.get('accent_color', '#F08080')
    
    # Parámetros adicionales
    wcag_level = request.form.get('wcag_level', 'AA')
    population_size = int(request.form.get('population_size', 50))
    generations = int(request.form.get('generations', 20))
    mutation_prob = float(request.form.get('mutation_prob', 15)) / 100
    accessibility_weight = float(request.form.get('accessibility_weight', 70)) / 100
    initial_weight = float(request.form.get('initial_weight', 30)) / 100
    
    # Crear y ejecutar algoritmo genético con los tres colores
    initial_colors = [primary_color, bg_color, accent_color]
    ga = ColorPaletteGA(
        initial_colors=initial_colors,
        wcag_level=wcag_level,
        population_size=population_size,
        generations=generations,
        mutation_prob=mutation_prob,
        accessibility_weight=accessibility_weight,
        initial_weight=initial_weight
    )
    
    hof, log = ga.run()
    
    # Obtener las mejores paletas
    best_palettes = ga.get_best_palettes(3)
    
    # Generar gráficos de evolución
    # 1. Curva de convergencia
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    gen = log.select("gen")
    fit_avg = log.select("avg")
    fit_max = log.select("max")
    
    ax1.plot(gen, fit_avg, "r-", label="Aptitud promedio")
    ax1.plot(gen, fit_max, "b-", label="Mejor aptitud")
    ax1.set_xlabel("Generación")
    ax1.set_ylabel("Aptitud")
    ax1.set_title("Evolución de la aptitud")
    ax1.grid(True)
    ax1.legend()
    
    # Convertir a base64 para enviar al cliente
    buffer1 = BytesIO()
    fig1.savefig(buffer1, format='png')
    buffer1.seek(0)
    convergence_img = base64.b64encode(buffer1.getvalue()).decode()
    plt.close(fig1)
    
    # También podemos enviar los colores iniciales para compararlos
    return jsonify({
        'palettes': best_palettes,
        'convergence_chart': convergence_img,
        'initial_colors': initial_colors
    })

@app.route('/extract-color', methods=['POST'])
def extract_color():
    """Extrae los colores principales de un HTML o URL"""
    extractor = ColorExtractor()
    
    try:
        if 'html' in request.form and request.form['html'].strip():
            html_content = request.form['html']
            colors = extractor.extract_from_html(html_content)
        elif 'url' in request.form and request.form['url'].strip():
            url = request.form['url']
            colors = extractor.extract_from_url(url)
        else:
            return jsonify({'error': 'Se requiere HTML o URL válida'}), 400
        
        # Devolvemos los tres colores
        return jsonify({
            'primary_color': colors[0],
            'bg_color': colors[1],
            'accent_color': colors[2]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)