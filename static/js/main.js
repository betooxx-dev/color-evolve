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

  // Sincronizar selector de color con input de texto
  const baseColorInput = document.getElementById("base-color");
  const hexInput = document.getElementById("hex-value");

  baseColorInput.addEventListener("input", function () {
    hexInput.value = baseColorInput.value;
  });

  hexInput.addEventListener("input", function () {
    // Validar formato hexadecimal
    if (/^#[0-9A-F]{6}$/i.test(hexInput.value)) {
      baseColorInput.value = hexInput.value;
    }
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
        displayPalettes(data.palettes);

        // Mostrar gráficos
        convergenceChart.src = `data:image/png;base64,${data.convergence_chart}`;

        // Seleccionar primera paleta por defecto
        if (data.palettes.length > 0) {
          displayPreview(data.palettes[0].colors);
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
  function displayPalettes(palettes) {
    // Limpiar tabla existente
    palettesTable.innerHTML = "";

    // Añadir cada paleta a la tabla
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
        displayPreview(palette.colors);
      });

      palettesTable.appendChild(row);
    });
  }

  // Función para mostrar previsualización de paleta
  function displayPreview(colors) {
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

    // Mostrar códigos hexadecimales
    const colorsInfo = document.createElement("div");
    colorsInfo.className = "colors-info";

    colors.forEach((color, index) => {
      const colorInfo = document.createElement("div");
      colorInfo.className = "color-info";

      const colorSwatch = document.createElement("div");
      colorSwatch.className = "color-info-swatch";
      colorSwatch.style.backgroundColor = color;

      const colorLabel = document.createElement("div");
      colorLabel.className = "color-info-label";
      colorLabel.textContent = ["Primario", "Fondo", "Acento"][index];

      const colorHex = document.createElement("div");
      colorHex.className = "color-info-hex";
      colorHex.textContent = color;

      colorInfo.appendChild(colorSwatch);
      colorInfo.appendChild(colorLabel);
      colorInfo.appendChild(colorHex);

      colorsInfo.appendChild(colorInfo);
    });

    palettePreview.appendChild(colorsInfo);
  }

  // Funcionalidad para extraer color de URL
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
            // Actualizar el selector de color y el campo de texto
            document.getElementById("base-color").value = data.color;
            document.getElementById("hex-value").value = data.color;

            // Mostrar una previsualización
            const preview = document.getElementById("url-result-preview");
            preview.innerHTML = `
        <div class="d-flex align-items-center">
          <div style="width: 24px; height: 24px; background-color: ${data.color}; border-radius: 4px; border: 1px solid #dee2e6;"></div>
          <span class="ms-2">${data.color}</span>
        </div>
      `;
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

  // Funcionalidad para extraer color de HTML
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
            // Actualizar el selector de color y el campo de texto
            document.getElementById("base-color").value = data.color;
            document.getElementById("hex-value").value = data.color;

            // Mostrar una previsualización
            const preview = document.getElementById("html-result-preview");
            preview.innerHTML = `
        <div class="d-flex align-items-center">
          <div style="width: 24px; height: 24px; background-color: ${data.color}; border-radius: 4px; border: 1px solid #dee2e6;"></div>
          <span class="ms-2">${data.color}</span>
        </div>
      `;
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

  // Asegurar que el color seleccionado se mantiene al cambiar de tab
  document.querySelectorAll("#colorSourceTabs button").forEach((button) => {
    button.addEventListener("shown.bs.tab", function (e) {
      // Al cambiar de tab, asegurar que el valor del color base se mantiene sincronizado
      const currentColor = document.getElementById("hex-value").value;
      document.getElementById("base-color").value = currentColor;
    });
  });
});
