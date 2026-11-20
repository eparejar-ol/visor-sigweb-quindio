# Guía Completa de Entrega y Sustentación Técnica: Visor SIG Web Ambiental del Quindío

## 1. Contexto y Cumplimiento de la Rúbrica de Evaluación

La Tarea 3 de la asignatura **Programación para SIG** (Universidad del Quindío) evalúa la capacidad de integrar una base de datos espacial PostgreSQL/PostGIS con un backend de servicios web en Python FastAPI y un frontend interactivo en Leaflet.js.

A continuación se detalla cómo la solución desarrollada responde a cada uno de los criterios de calificación de la guía:

| Criterio de Evaluación | Ponderación | Estado de Cumplimiento |
| :--- | :---: | :--- |
| **Geodatabase:** Mínimo 4 tablas relacionadas, datos e integridad básica | **15 %** | **Cumplido:** 4 tablas relacionales (`municipios`, `estaciones_monitoreo`, `vias_acceso`, `lecturas_sensores`), con PK, FK `ON DELETE CASCADE` y 3 tipos de geometría PostGIS (`Polygon`, `Point`, `LineString`). |
| **Integración Frontend–Backend–PostGIS** | **25 %** | **Cumplido:** Arquitectura cliente-servidor desacoplada. Leaflet consume endpoints REST de FastAPI, que a su vez ejecuta SQL parametrizado con `psycopg` sobre PostgreSQL. |
| **Implementación y pertinencia de las funcionalidades** | **25 %** | **Cumplido:** Se implementan las 4 funcionalidades exigidas (F1 GeoJSON, F2 Atributos multitabla, F3 Consulta espacial `ST_DWithin`, F4 Resumen temático ambiental). |
| **Verificación técnica de consultas y resultados** | **15 %** | **Cumplido:** El documento y el `README.md` incluyen las sentencias SQL reales contrastadas con las estructuras JSON/GeoJSON devueltas por la API. |
| **Organización del código y reproducibilidad** | **10 %** | **Cumplido:** Estructura limpia de repositorios (`database/`, `backend/`, `frontend/`), script SQL reproducible y dependencias en `requirements.txt`. |
| **Demostración y explicación técnica** | **10 %** | **Cumplido:** Diagrama y descripción detallada del flujo end-to-end (Interacción -> API -> PostGIS -> GeoJSON -> Leaflet). |

---

## 2. Estructura de Archivos para tu Repositorio en GitHub

Para realizar la entrega, debes crear un repositorio público en GitHub y organizar tus archivos con la siguiente estructura:

```
visor-sigweb-quindio/
├── database/
│   └── schema_and_data.sql    # Script SQL de creación de PostGIS y datos
├── backend/
│   ├── main.py                # Aplicación API REST en FastAPI
│   └── requirements.txt       # Dependencias de Python (FastAPI, psycopg, uvicorn)
├── frontend/
│   ├── index.html             # Interfaz de usuario HTML5
│   ├── styles.css             # Hojas de estilo CSS3
│   └── app.js                 # Lógica cliente JavaScript + Leaflet.js
└── README.md                  # Documentación técnica requerida
```

---

## 3. Matriz de Funcionalidades y Consultas SQL PostGIS

### F1. Visualización Geográfica Dinámica (GeoJSON)
- **Propósito:** Cargar los límites de los municipios y la ubicación de las estaciones directamente desde la base de datos a la capa cartográfica Leaflet.
- **SQL Ejecutado en PostGIS:**
  ```sql
  SELECT e.id, e.codigo, e.nombre, e.tipo_estacion, e.estado, e.altitud_mabsl,
         m.nombre AS municipio_nombre,
         ST_AsGeoJSON(e.geom)::json AS geometry
  FROM estaciones_monitoreo e
  JOIN municipios m ON e.municipio_id = m.id;
  ```

### F2. Consulta Alfanumérica de Atributos e Historial
- **Propósito:** Recuperar los detalles alfanuméricos completos de una estación al hacer clic en el mapa, incluyendo las lecturas registradas por sus sensores.
- **SQL Ejecutado en PostgreSQL:**
  ```sql
  SELECT id, fecha_hora, temperatura_c, precipitacion_mm, humedad_relativa, nivel_alerta
  FROM lecturas_sensores
  WHERE estacion_id = %s
  ORDER BY fecha_hora DESC LIMIT 10;
  ```

### F3. Consulta Espacial PostGIS (Proximidad con ST_DWithin)
- **Propósito:** Evaluar la influencia geográfica buscando qué estaciones se encuentran a un radio menor o igual a X km de un punto dado.
- **SQL Ejecutado en PostGIS:**
  ```sql
  SELECT e.id, e.codigo, e.nombre, m.nombre AS municipio_nombre,
         ST_Distance(e.geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000.0 AS distancia_km,
         ST_AsGeoJSON(e.geom)::json AS geometry
  FROM estaciones_monitoreo e
  JOIN municipios m ON e.municipio_id = m.id
  WHERE ST_DWithin(
      e.geom::geography,
      ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
      %s * 1000.0
  )
  ORDER BY distancia_km ASC;
  ```

### F4. Funcionalidad Geográfica Complementaria (Análisis Agregado Municipal)
- **Propósito:** Generar métricas territoriales de alerta ambiental agrupadas por municipio.
- **SQL Ejecutado en PostgreSQL:**
  ```sql
  SELECT m.nombre AS municipio,
         COUNT(DISTINCT e.id) AS total_estaciones,
         ROUND(AVG(l.temperatura_c), 1) AS temp_promedio_c,
         COUNT(CASE WHEN l.nivel_alerta = 'Crítico' THEN 1 END) AS alertas_criticas
  FROM municipios m
  LEFT JOIN estaciones_monitoreo e ON m.id = e.municipio_id
  LEFT JOIN lecturas_sensores l ON e.id = l.estacion_id
  GROUP BY m.id, m.nombre
  ORDER BY m.nombre ASC;
  ```

---

## 4. Instrucciones para la Entrega Final

1. Sube todos los archivos a tu repositorio público de GitHub.
2. Copia la URL pública de tu repositorio.
3. Envía un correo electrónico al profesor Julián Garzón antes de las 11:59 p. m. con el asunto: `Programación para SIG — Tarea integradora — [Tu Nombre Completo]` e incluye el enlace público a tu repositorio.