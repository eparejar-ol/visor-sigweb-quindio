const API_BASE_URL = "http://localhost:8000";
let map;
let layerMunicipios = null;
let layerEstaciones = null;
let layerBusquedaEspacial = null;
let markerCentroRadio = null;
let circleRadio = null;
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    checkApiConnection();
    cargarMunicipios();
    cargarEstaciones();
    setupEventListeners();
});
function initMap() {
    map = L.map("map").setView([4.5539, -75.6603], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors | UQ SIG Web"
    }).addTo(map);
    map.on("click", (e) => {
        document.getElementById("inputLat").value = e.latlng.lat.toFixed(4);
        document.getElementById("inputLon").value = e.latlng.lng.toFixed(4);
    });
}
async function checkApiConnection() {
    const statusCard = document.getElementById("apiStatusCard");
    const statusText = document.getElementById("apiStatusText");
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            const data = await response.json();
            statusCard.classList.add("active");
            statusText.innerHTML = `<i class="fa-solid fa-circle-check"></i> API Activa: ${data.proyecto}`;
        }
    } catch (error) {
        statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> API PostGIS en local (Uvicorn:8000)`;
    }
}
async function cargarMunicipios() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/capas/municipios`);
        const geojsonData = await response.json();
        if (layerMunicipios) map.removeLayer(layerMunicipios);
        layerMunicipios = L.geoJSON(geojsonData, {
            style: { color: "#2563eb", weight: 2, fillColor: "#3b82f6", fillOpacity: 0.15 },
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(`<strong>${p.nombre}</strong><br>DANE: ${p.codigo_dane}<br>Área: ${p.area_km2} km²<br>Población: ${p.poblacion.toLocaleString()} hab.`);
            }
        }).addTo(map);
    } catch (e) { console.error("Error capa municipios", e); }
}
async function cargarEstaciones(tipoFiltro = "") {
    try {
        let url = `${API_BASE_URL}/api/v1/capas/estaciones`;
        if (tipoFiltro) url += `?tipo=${encodeURIComponent(tipoFiltro)}`;
        const response = await fetch(url);
        const geojsonData = await response.json();
        if (layerEstaciones) map.removeLayer(layerEstaciones);
        layerEstaciones = L.geoJSON(geojsonData, {
            pointToLayer: (feature, latlng) => {
                return L.circleMarker(latlng, { radius: 8, fillColor: "#ef4444", color: "#ffffff", weight: 2, fillOpacity: 0.9 });
            },
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(`<strong>${p.nombre}</strong> (${p.codigo})<br>Tipo: ${p.tipo_estacion}<br>Municipio: ${p.municipio}`);
                layer.on("click", () => cargarDetalleEstacion(p.id));
            }
        }).addTo(map);
    } catch (e) { console.error("Error capa estaciones", e); }
}
async function cargarDetalleEstacion(estacionId) {
    const panel = document.getElementById("panelDetalle");
    panel.innerHTML = "<p>Cargando información desde PostGIS...</p>";
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/estaciones/${estacionId}`);
        const data = await response.json();
        const est = data.estacion;
        const lecturas = data.lecturas_historicas;
        let html = `<div><h3>${est.nombre}</h3><small>${est.codigo} | ${est.tipo_estacion}</small></div>`;
        html += `<p><b>Municipio:</b> ${est.municipio_nombre}</p>`;
        html += `<p><b>Altitud:</b> ${est.altitud_mabsl} m s.n.m.</p>`;
        html += `<h4>Historial de Sensores:</h4>`;
        if (lecturas.length === 0) {
            html += "<p>Sin registros lecturas.</p>";
        } else {
            html += '<table class="data-table"><thead><tr><th>Fecha</th><th>Temp (°C)</th><th>Precip (mm)</th><th>Alerta</th></tr></thead><tbody>';
            lecturas.forEach(l => {
                html += `<tr><td>${l.fecha_hora ? l.fecha_hora.substring(0,16) : ""}</td><td>${l.temperatura_c} °C</td><td>${l.precipitacion_mm} mm</td><td><b>${l.nivel_alerta}</b></td></tr>`;
            });
            html += "tbody></table>";
        }
        panel.innerHTML = html;
    } catch (e) { panel.innerHTML = "<p>Error al cargar detalle.</p>"; }
}
async function ejecutarConsultaEspacial() {
    const lat = parseFloat(document.getElementById("inputLat").value);
    const lon = parseFloat(document.getElementById("inputLon").value);
    const radioKm = parseFloat(document.getElementById("inputRadio").value);
    if (isNaN(lat) || isNaN(lon) || isNaN(radioKm)) return;
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/estaciones/busqueda-espacial?latitud=${lat}&longitud=${lon}&radio_km=${radioKm}`);
        const data = await response.json();
        limpiarBusquedaEspacial();
        markerCentroRadio = L.marker([lat, lon]).addTo(map).bindPopup(`Centro de Búsqueda ST_DWithin`).openPopup();
        circleRadio = L.circle([lat, lon], { radius: radioKm * 1000, color: "#8b5cf6", fillColor: "#a855f7", fillOpacity: 0.15 }).addTo(map);
        layerBusquedaEspacial = L.geoJSON(data.resultado_geojson, {
            pointToLayer: (feature, latlng) => L.circleMarker(latlng, { radius: 10, fillColor: "#fbbf24", color: "#7c3aed", weight: 3, fillOpacity: 0.95 }),
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindPopup(`<strong>${p.nombre}</strong><br>Distancia PostGIS ST_DWithin: ${p.distancia_km} km`);
            }
        }).addTo(map);
        map.fitBounds(circleRadio.getBounds());
    } catch (e) { console.error("Error consulta espacial", e); }
}
function limpiarBusquedaEspacial() {
    if (markerCentroRadio) map.removeLayer(markerCentroRadio);
    if (circleRadio) map.removeLayer(circleRadio);
    if (layerBusquedaEspacial) map.removeLayer(layerBusquedaEspacial);
}
async function cargarResumenMunicipal() {
    const contenedor = document.getElementById("contenedorResumen");
    const alerta = document.getElementById("selectAlerta").value;
    contenedor.innerHTML = "<p>Cargando resumen...</p>";
    try {
        let url = `${API_BASE_URL}/api/v1/analisis/alertas-municipio`;
        if (alerta) url += `?nivel_alerta=${encodeURIComponent(alerta)}`;
        const response = await fetch(url);
        const data = await response.json();
        let html = '<table class="data-table"><thead><tr><th>Municipio</th><th>Estaciones</th><th>Temp Prom</th><th>Críticas</th></tr></thead><tbody>';
        data.resumen_municipal.forEach(item => {
            html += `<tr><td><b>${item.municipio}</b></td><td>${item.total_estaciones}</td><td>${item.temp_promedio_c || "N/D"} °C</td><td>${item.alertas_criticas}</td></tr>`;
        });
        html += "</tbody></table>";
        contenedor.innerHTML = html;
    } catch (e) { contenedor.innerHTML = "<p>Error al cargar resumen.</p>"; }
}
function setupEventListeners() {
    document.getElementById("chkMunicipios").addEventListener("change", (e) => {
        if (e.target.checked) map.addLayer(layerMunicipios);
        else map.removeLayer(layerMunicipios);
    });
    document.getElementById("chkEstaciones").addEventListener("change", (e) => {
        if (e.target.checked) map.addLayer(layerEstaciones);
        else map.removeLayer(layerEstaciones);
    });
    document.getElementById("selectTipoEstacion").addEventListener("change", (e) => cargarEstaciones(e.target.value));
    document.getElementById("btnConsultaEspacial").addEventListener("click", ejecutarConsultaEspacial);
    document.getElementById("btnLimpiarEspacial").addEventListener("click", () => {
        limpiarBusquedaEspacial();
        map.setView([4.5539, -75.6603], 11);
    });
    document.getElementById("btnCargarResumen").addEventListener("click", cargarResumenMunicipal);
}