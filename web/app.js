// Comportamiento del frontend para el planificador de rutas.
// Este archivo centraliza la lógica del navegador: selección de estaciones,
// llamadas a la API, tratamiento de errores y renderizado del resultado.
const form = document.querySelector("#route-form");
const origin = document.querySelector("#origin");
const destination = document.querySelector("#destination");
const accessible = document.querySelector("#accessible");
const result = document.querySelector("#result");
const errorBox = document.querySelector("#error");

function normalizeErrorMessage(error) {
  if (error instanceof Error && error.message && error.message.trim()) {
    return error.message.trim();
  }
  return "Ha ocurrido un error inesperado. Inténtalo de nuevo.";
}

function showValidationError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  result.className = "result empty";
  result.innerHTML = '<div class="empty-icon">↯</div><p>Elige un origen y un destino para consultar la mejor ruta disponible.</p>';
}

function validateSelection() {
  const selectedOrigin = origin.value.trim();
  const selectedDestination = destination.value.trim();

  if (selectedOrigin && selectedDestination && selectedOrigin === selectedDestination) {
    showValidationError("Origen y destino son iguales. Verifica la selección antes de continuar.");
    return false;
  }

  errorBox.hidden = true;
  return true;
}

// Rellena los selectores del formulario con las estaciones disponibles en la red.
// Este proceso se hace al cargar la página para que el usuario pueda elegir origen y destino.
function fillStations(stations) {
  for (const select of [origin, destination]) {
    select.replaceChildren(...stations.map((station) => new Option(station, station)));
  }
  if (stations.length > 1) destination.value = stations[stations.length - 1];
}

// Construye la vista visual de la ruta elegida a partir de la respuesta del backend.
// La función genera una línea de paradas y la lista de segmentos que componen el recorrido.
function renderRoute(data) {
  const stops = data.stops.map((stop, index) => {
    const segment = data.segments[index] ? `${data.segments[index].line} · ${data.segments[index].minutes} min` : "Destino final";
    return `<div class="stop"><span class="stop-name">${stop}</span><span class="segment">${segment}</span></div>`;
  }).join("");

  // Se utiliza la ruta más lenta como referencia para escalar la barra visual de cada alternativa.
  const longest = Math.max(...data.alternatives.map((alternative) => alternative.total_minutes), 1);
  const routeColors = ["#ef765d", "#49b6a8", "#e5b85c", "#7f9fe8", "#c183b9"];

  const comparisons = data.alternatives.map((alternative, index) => {
    const width = Math.max(8, Math.round((alternative.total_minutes / longest) * 100));
    const selected = index === 0 ? " best" : "";
    const label = index === 0 ? "Ruta más rápida" : "Ruta más lenta";
    const color = routeColors[index % routeColors.length];

    const alternativeStops = alternative.stops.map((stop, stopIndex) => {
      const segment = alternative.segments[stopIndex];
      const detail = segment ? `${segment.line} · ${segment.minutes} min` : "Destino final";
      return `<li><strong>${stop}</strong><span>${detail}</span></li>`;
    }).join("");

    return `<article class="comparison-card${selected}" style="--route-color: ${color}"><div class="comparison-top"><strong><i class="route-color" aria-hidden="true"></i>${label}</strong><span>${alternative.total_minutes} min</span></div><ol class="alternative-timeline">${alternativeStops}</ol><div class="comparison-bar"><i style="width: ${width}%"></i></div></article>`;
  }).join("");

  const comparisonNote = data.alternatives.length === 1
    ? "No hay rutas alternativas disponibles en la red configurada."
    : `${data.alternatives.length} rutas comparadas en total.`;

  result.className = "result route-result";
  result.innerHTML = `<h3>${data.origin} <span>→</span> ${data.destination}</h3><p class="total">${data.total_minutes} minutos de viaje</p><div class="timeline">${stops}</div><div class="comparison"><h4>Comparación por tiempo</h4><p class="comparison-note">${comparisonNote}</p>${comparisons}</div>`;
}

// Carga la lista de estaciones desde la API del backend cuando se inicia la interfaz.
async function loadStations() {
  const response = await fetch("/api/stations");
  if (!response.ok) throw new Error("No se pudo cargar la red de transporte.");
  fillStations((await response.json()).stations);
}

// Gestiona el envío del formulario sin recargar la página.
// Envía la solicitud al backend y procesa la respuesta para mostrar la ruta calculada.
origin.addEventListener("change", validateSelection);
destination.addEventListener("change", validateSelection);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  try {
    const selectedOrigin = origin.value.trim();
    const selectedDestination = destination.value.trim();

    if (!validateSelection()) {
      throw new Error("Origen y destino son iguales. Verifica la selección antes de continuar.");
    }

    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origin: selectedOrigin,
        destination: selectedDestination,
        accessible_only: accessible.checked,
      }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "La solicitud no se pudo procesar.");
    renderRoute(data);
  } catch (error) {
    errorBox.textContent = normalizeErrorMessage(error);
    errorBox.hidden = false;
  }
});

// Arranque inicial de la aplicación: se cargan las estaciones y, si hay un error,
// se muestra un mensaje claro al usuario en la parte superior de la pantalla.
loadStations().catch((error) => {
  errorBox.textContent = normalizeErrorMessage(error);
  errorBox.hidden = false;
});