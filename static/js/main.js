document.addEventListener("DOMContentLoaded", function () {
  // Referencias a elementos del DOM
  const form = document.getElementById("generate-form");
  const loadingIndicator = document.getElementById("loading");
  const resultsContainer = document.getElementById("results-container");
  const palettesTable = document
    .getElementById("palettes-table")
    .querySelector("tbody");
  const palettePreview = document.getElementById("palette-preview");
  const convergenceChart = document.getElementById("convergence-chart");

  // Sincronizar selectores de color con inputs de texto
  const colorInputs = [
    { color: document.getElementById("primary-color"), hex: document.getElementById("primary-hex-value") },
    { color: document.getElementById("bg-color"), hex: document.getElementById("bg-hex-value") },
    { color: document.getElementById("accent-color"), hex: document.getElementById("accent-hex-value") }
  ];
  
  // Configurar eventos para todos los selectores de color
  colorInputs.forEach(input => {
    input.color.addEventListener("input", function() {
      input.hex.value = input.color.value;
    });
    
    input.hex.addEventListener("input", function() {
      // Validar formato hexadecimal
      if (/^#[0-9A-F]{6}$/i.test(input.hex.value)) {
        input.color.value = input.hex.value;
      }
    });
  });

  // Actualizar valores de los sliders
  const populationSlider = document.getElementById("population-size");
  const populationValue = document.getElementById("population-value");
  populationSlider.addEventListener("input", function () {
    populationValue.textContent = populationSlider.value;
  });

  const generationsSlider = document.getElementById("generations");
  const generationsValue = document.getElementById("generations-value");
  generationsSlider.addEventListener("input", function () {
    generationsValue.textContent = generationsSlider.value;
  });

  const mutationSlider = document.getElementById("mutation-prob");
  const mutationValue = document.getElementById("mutation-value");
  mutationSlider.addEventListener("input", function () {
    mutationValue.textContent = mutationSlider.value;
  });

  const accessibilitySlider = document.getElementById("accessibility-weight");
  const accessValue = document.getElementById("access-value");
  const aestheticValue = document.getElementById("aesthetic-value");
  accessibilitySlider.addEventListener("input", function () {
    accessValue.textContent = accessibilitySlider.value;
    aestheticValue.textContent = 100 - accessibilitySlider.value;
  });
  
  const initialWeightSlider = document.getElementById("initial-weight");
  const initialWeightValue = document.getElementById("initial-weight-value");
  initialWeightSlider.addEventListener("input", function () {
    initialWeightValue.textContent = initialWeightSlider.value;
  });

  // Manejar envío del formulario
  form.addEventListener("submit", function (e) {
    e.preventDefault();

    // Mostrar indicador de carga
    loadingIndicator.style.display = "block";
    resultsContainer.style.display = "none";
    document.getElementById("generate-btn").disabled = true;

    // Obtener datos del formulario
    const formData = new FormData(form);

    // Enviar solicitud al servidor
    fetch("/generate", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        // Ocultar indicador de carga
        loadingIndicator.style.display = "none";
        resultsContainer.style.display = "block";
        document.getElementById("generate-btn").disabled = false;

        // Mostrar resultados
        displayPalettes(data.palettes, data.initial_colors);

        // Mostrar gráficos
        convergenceChart.src = `data:image/png;base64,${data.convergence_chart}`;

        // Seleccionar primera paleta por defecto
        if (data.palettes.length > 0) {
          displayPreview(data.palettes[0].colors, data.initial_colors);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        loadingIndicator.style.display = "none";
        document.getElementById("generate-btn").disabled = false;
        alert(
          "Ocurrió un error al generar las paletas. Por favor, intenta de nuevo."
        );
      });
  });

  // Función para mostrar paletas en la tabla
  function displayPalettes(palettes, initialColors) {
    // Limpiar tabla existente
    palettesTable.innerHTML = "";
    
    // Añadir la paleta inicial en la primera fila
    const initialRow = document.createElement("tr");
    initialRow.className = "table-light";
    
    // Columna de colores
    const initialColorsCell = document.createElement("td");
    const initialColorsDiv = document.createElement("div");
    initialColorsDiv.className = "palette-colors";
    
    initialColors.forEach((color) => {
      const colorSwatch = document.createElement("div");
      colorSwatch.className = "color-swatch";
      colorSwatch.style.backgroundColor = color;
      colorSwatch.title = color;
      initialColorsDiv.appendChild(colorSwatch);
    });
    
    initialColorsCell.appendChild(initialColorsDiv);
    initialRow.appendChild(initialColorsCell);
    
    // Columnas informativas
    const initialLabel = document.createElement("td");
    initialLabel.colSpan = 3;
    initialLabel.textContent = "Paleta inicial (sin optimizar)";
    initialLabel.className = "text-muted";
    initialRow.appendChild(initialLabel);
    
    initialRow.addEventListener("click", function() {
      const selected = palettesTable.querySelector(".table-active");
      if (selected) {
        selected.classList.remove("table-active");
      }
      initialRow.classList.add("table-active");
      displayPreview(initialColors, initialColors);
    });
    
    palettesTable.appendChild(initialRow);
    
    // Añadir cada paleta optimizada a la tabla
    palettes.forEach((palette, index) => {
      const row = document.createElement("tr");

      // Columna de colores
      const colorsCell = document.createElement("td");
      const colorsDiv = document.createElement("div");
      colorsDiv.className = "palette-colors";

      palette.colors.forEach((color) => {
        const colorSwatch = document.createElement("div");
        colorSwatch.className = "color-swatch";
        colorSwatch.style.backgroundColor = color;
        colorSwatch.title = color;
        colorsDiv.appendChild(colorSwatch);
      });

      colorsCell.appendChild(colorsDiv);
      row.appendChild(colorsCell);

      // Otras columnas
      const contrastCell = document.createElement("td");
      contrastCell.textContent = palette.contrast;
      row.appendChild(contrastCell);

      const deltaECell = document.createElement("td");
      deltaECell.textContent = palette.delta_e;
      row.appendChild(deltaECell);

      const daltonismCell = document.createElement("td");
      daltonismCell.textContent = palette.daltonism;
      row.appendChild(daltonismCell);

      // Añadir evento de clic para previsualizar
      row.addEventListener("click", function () {
        const selected = palettesTable.querySelector(".table-active");
        if (selected) {
          selected.classList.remove("table-active");
        }
        row.classList.add("table-active");
        displayPreview(palette.colors, initialColors);
      });

      palettesTable.appendChild(row);
    });
    
    // Seleccionar la primera paleta optimizada por defecto
    if (palettes.length > 0) {
      palettesTable.querySelectorAll("tr")[1].click();
    }
  }

  // Función para mostrar previsualización de paleta
  function displayPreview(colors, initialColors) {
    palettePreview.innerHTML = "";

    // Crear modelo de interfaz de ejemplo
    const mockup = document.createElement("div");
    mockup.className = "interface-mockup";

    // Aplicar colores a la interfaz
    mockup.innerHTML = `
            <div class="mockup-header" style="background-color: ${colors[0]}">
                <div class="mockup-logo">ColorEvolve</div>
                <div class="mockup-nav">
                    <span>Inicio</span>
                    <span>Galería</span>
                    <span>Contacto</span>
                </div>
            </div>
            <div class="mockup-content" style="background-color: ${colors[1]}">
                <div class="mockup-title" style="color: ${colors[2]}">Diseño Accesible</div>
                <div class="mockup-text">Texto de ejemplo en el color primario de fondo.</div>
                <button class="mockup-button" style="background-color: ${colors[2]}; color: ${colors[1]}">
                    Botón de acción
                </button>
            </div>
        `;

    palettePreview.appendChild(mockup);

    // Mostrar códigos hexadecimales y comparación
    const colorsInfo = document.createElement("div");
    colorsInfo.className = "colors-info";

    const labels = ["Primario", "Fondo", "Acento"];
    
    colors.forEach((color, index) => {
      const colorInfo = document.createElement("div");
      colorInfo.className = "color-info";

      const colorSwatch = document.createElement("div");
      colorSwatch.className = "color-info-swatch";
      colorSwatch.style.backgroundColor = color;

      const colorLabel = document.createElement("div");
      colorLabel.className = "color-info-label";
      colorLabel.textContent = labels[index];

      const colorHex = document.createElement("div");
      colorHex.className = "color-info-hex";
      colorHex.textContent = color;
      
      // Si es diferente del color inicial, mostrar comparación
      if (color !== initialColors[index]) {
        const comparisonDiv = document.createElement("div");
        comparisonDiv.className = "color-comparison";
        comparisonDiv.style.display = "flex";
        comparisonDiv.style.alignItems = "center";
        comparisonDiv.style.marginTop = "4px";
        
        const initialSwatch = document.createElement("div");
        initialSwatch.style.width = "12px";
        initialSwatch.style.height = "12px";
        initialSwatch.style.backgroundColor = initialColors[index];
        initialSwatch.style.border = "1px solid #dee2e6";
        initialSwatch.style.borderRadius = "50%";
        
        const arrow = document.createElement("span");
        arrow.textContent = " → ";
        arrow.style.fontSize = "0.8rem";
        arrow.style.color = "#666";
        
        const optimizedSwatch = document.createElement("div");
        optimizedSwatch.style.width = "12px";
        optimizedSwatch.style.height = "12px";
        optimizedSwatch.style.backgroundColor = color;
        optimizedSwatch.style.border = "1px solid #dee2e6";
        optimizedSwatch.style.borderRadius = "50%";
        
        comparisonDiv.appendChild(initialSwatch);
        comparisonDiv.appendChild(arrow);
        comparisonDiv.appendChild(optimizedSwatch);
        
        colorInfo.appendChild(comparisonDiv);
      }

      colorInfo.appendChild(colorSwatch);
      colorInfo.appendChild(colorLabel);
      colorInfo.appendChild(colorHex);

      colorsInfo.appendChild(colorInfo);
    });

    palettePreview.appendChild(colorsInfo);
  }

  // Funcionalidad para extraer colores de URL o HTML
  document
    .getElementById("extract-from-url")
    .addEventListener("click", function () {
      const url = document.getElementById("site-url").value;
      if (!url) {
        alert("Por favor, introduce una URL válida");
        return;
      }

      // Mostrar indicador de carga
      const spinner = document.getElementById("url-spinner");
      const button = this;

      spinner.classList.remove("d-none");
      button.disabled = true;

      fetch("/extract-color", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          url: url,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            alert("Error: " + data.error);
          } else {
            // Mostrar los colores extraídos
            displayExtractedColors(data);
            
            // Habilitar el botón para aplicar los colores
            document.getElementById("apply-extracted-colors").disabled = false;
          }
        })
        .catch((error) => {
          alert("Error: " + error.message);
        })
        .finally(() => {
          // Restaurar botón
          spinner.classList.add("d-none");
          button.disabled = false;
        });
    });

  document
    .getElementById("extract-from-html")
    .addEventListener("click", function () {
      const html = document.getElementById("html-code").value;
      if (!html) {
        alert("Por favor, introduce código HTML");
        return;
      }

      // Mostrar indicador de carga
      const spinner = document.getElementById("html-spinner");
      const button = this;

      spinner.classList.remove("d-none");
      button.disabled = true;

      fetch("/extract-color", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          html: html,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            alert("Error: " + data.error);
          } else {
            // Mostrar los colores extraídos
            displayExtractedColors(data);
            
            // Habilitar el botón para aplicar los colores
            document.getElementById("apply-extracted-colors").disabled = false;
          }
        })
        .catch((error) => {
          alert("Error: " + error.message);
        })
        .finally(() => {
          // Restaurar botón
          spinner.classList.add("d-none");
          button.disabled = false;
        });
    });
    
  // Función para mostrar los colores extraídos
  function displayExtractedColors(data) {
    const container = document.getElementById("extracted-colors-container");
    const preview = document.getElementById("extracted-colors-preview");
    
    preview.innerHTML = "";
    
    // Crear visualización para los tres colores
    const colors = [
      { name: "Primario", color: data.primary_color },
      { name: "Fondo", color: data.bg_color },
      { name: "Acento", color: data.accent_color }
    ];
    
    colors.forEach(colorInfo => {
      const colorDiv = document.createElement("div");
      colorDiv.className = "extracted-color";
      colorDiv.style.textAlign = "center";
      
      const swatch = document.createElement("div");
      swatch.style.width = "50px";
      swatch.style.height = "50px";
      swatch.style.backgroundColor = colorInfo.color;
      swatch.style.border = "1px solid #dee2e6";
      swatch.style.borderRadius = "4px";
      swatch.style.margin = "0 auto 5px auto";
      
      const label = document.createElement("div");
      label.textContent = colorInfo.name;
      label.style.fontWeight = "500";
      
      const hexValue = document.createElement("div");
      hexValue.textContent = colorInfo.color;
      hexValue.style.fontFamily = "monospace";
      hexValue.style.fontSize = "0.9rem";
      
      colorDiv.appendChild(swatch);
      colorDiv.appendChild(label);
      colorDiv.appendChild(hexValue);
      
      preview.appendChild(colorDiv);
    });
    
    container.style.display = "block";
    
    // Guardar los colores extraídos en un objeto global para usarlos después
    window.extractedColors = {
      primary: data.primary_color,
      background: data.bg_color,
      accent: data.accent_color
    };
  }
  
  // Aplicar colores extraídos a los inputs del formulario
  document.getElementById("apply-extracted-colors").addEventListener("click", function() {
    if (window.extractedColors) {
      // Actualizar selectores de color
      document.getElementById("primary-color").value = window.extractedColors.primary;
      document.getElementById("primary-hex-value").value = window.extractedColors.primary;
      
      document.getElementById("bg-color").value = window.extractedColors.background;
      document.getElementById("bg-hex-value").value = window.extractedColors.background;
      
      document.getElementById("accent-color").value = window.extractedColors.accent;
      document.getElementById("accent-hex-value").value = window.extractedColors.accent;
      
      // Cerrar modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('extractColorsModal'));
      modal.hide();
    }
  });
});