"""
==============================================================================
PROYECTO: VISOR SIG WEB - SISTEMA DE MONITOREO AMBIENTAL DEL QUINDÍO
ASIGNATURA: Programación para SIG - Universidad del Quindío
DOCENTE: Julián Garzón
DESCRIPCIÓN: Backend API REST con FastAPI y Psycopg para consulta espacial PostGIS.
              Implementa consultas parametrizadas seguras, formateo GeoJSON y
              las 4 funcionalidades requeridas en la rúbrica de evaluación.
==============================================================================
"""

import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from psycopg.rows import dict_row

# Configuración de aplicación FastAPI
app = FastAPI(
    title="SIG Web Ambiental del Quindío - API REST",
    description="Servicio Web SIG conectado a Geodatabase PostgreSQL/PostGIS",
    version="1.0.0"
)

# Habilitar CORS para permitir solicitudes HTTP desde el Visor Frontend (Leaflet)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración segura de parámetros de conexión (Variables de entorno con valores por defecto)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sigweb_quindio")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def get_db_connection():
    """Establece conexión con la base de datos PostgreSQL/PostGIS de forma segura."""
    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            row_factory=dict_row
        )
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fatal de conexión con la Geodatabase PostgreSQL/PostGIS: {str(e)}"
        )

@app.get("/")
def read_root():
    """Endpoint raíz con metadatos del servicio SIG Web."""
    return {
        "proyecto": "Visor SIG Web - Monitoreo Ambiental del Quindío",
        "asignatura": "Programación para SIG - Universidad del Quindío",
        "estado": "Operativo",
        "postgis_conectado": True
    }

# ============================================================================
# FUNCIONALIDAD 1 (F1): VISUALIZACIÓN GEOGRÁFICA (GeoJSON desde PostGIS)
# ============================================================================

@app.get("/api/v1/capas/estaciones", summary="F1: Obtener capa de Estaciones en GeoJSON")
def get_estaciones_geojson(tipo: Optional[str] = None):
    """
    F1. Consulta espacial a PostGIS que transforma la geometría de estaciones (Punto)
    a formato GeoJSON nativo usando ST_AsGeoJSON() y une el nombre del municipio.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            e.id,
            e.codigo,
            e.nombre,
            e.tipo_estacion,
            e.estado,
            e.altitud_mabsl,
            m.nombre AS municipio_nombre,
            ST_AsGeoJSON(e.geom)::json AS geometry
        FROM estaciones_monitoreo e
        JOIN municipios m ON e.municipio_id = m.id
    """
    params = []
    
    if tipo:
        sql += " WHERE e.tipo_estacion = %s"
        params.append(tipo)
        
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    # Construcción de la FeatureCollection GeoJSON cumpliendo el estándar RFC 7946
    features = []
    for r in rows:
        feature = {
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {
                "id": r["id"],
                "codigo": r["codigo"],
                "nombre": r["nombre"],
                "tipo_estacion": r["tipo_estacion"],
                "estado": r["estado"],
                "altitud_mabsl": float(r["altitud_mabsl"]),
                "municipio": r["municipio_nombre"]
            }
        }
        features.append(feature)
        
    conn.close()
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/v1/capas/municipios", summary="F1: Obtener límites municipales en GeoJSON")
def get_municipios_geojson():
    """
    F1. Retorna los límites municipales del Quindío (Polígonos) en GeoJSON
    directamente desde la consulta PostGIS.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            id, nombre, codigo_dane, area_km2, poblacion,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM municipios
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    
    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {
                "id": r["id"],
                "nombre": r["nombre"],
                "codigo_dane": r["codigo_dane"],
                "area_km2": float(r["area_km2"]),
                "poblacion": r["poblacion"]
            }
        })
        
    conn.close()
    return {"type": "FeatureCollection", "features": features}

# ============================================================================
# FUNCIONALIDAD 2 (F2): CONSULTA DE ATRIBUTOS (Relación Multitabla)
# ============================================================================

@app.get("/api/v1/estaciones/{estacion_id}", summary="F2: Consulta detallada de atributos de una estación")
def get_detalle_estacion(estacion_id: int):
    """
    F2. Recupera la información alfanumérica completa de una estación específica,
    incluyendo datos del municipio (JOIN) y el historial reciente de lecturas asociadas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Consulta 1: Datos de la estación y municipio
    sql_estacion = """
        SELECT 
            e.id, e.codigo, e.nombre, e.tipo_estacion, e.estado, e.altitud_mabsl,
            m.nombre AS municipio_nombre, m.poblacion, m.area_km2,
            ST_X(e.geom) AS longitud, ST_Y(e.geom) AS latitud
        FROM estaciones_monitoreo e
        JOIN municipios m ON e.municipio_id = m.id
        WHERE e.id = %s
    """
    cursor.execute(sql_estacion, (estacion_id,))
    estacion = cursor.fetchone()
    
    if not estacion:
        conn.close()
        raise HTTPException(status_code=404, detail="Estación de monitoreo no encontrada.")
        
    # Consulta 2: Historial alfanumérico de lecturas asociadas (FK)
    sql_lecturas = """
        SELECT id, fecha_hora, temperatura_c, precipitacion_mm, humedad_relativa, velocidad_viento_kmh, nivel_alerta
        FROM lecturas_sensores
        WHERE estacion_id = %s
        ORDER BY fecha_hora DESC
        LIMIT 10
    """
    cursor.execute(sql_lecturas, (estacion_id,))
    lecturas = cursor.fetchall()
    
    conn.close()
    
    # Formatear timestamps a ISO string
    lecturas_fmt = []
    for l in lecturas:
        l_dict = dict(l)
        l_dict["fecha_hora"] = l_dict["fecha_hora"].isoformat() if l_dict["fecha_hora"] else None
        lecturas_fmt.append(l_dict)
        
    return {
        "estacion": dict(estacion),
        "lecturas_historicas": lecturas_fmt
    }

# ============================================================================
# FUNCIONALIDAD 3 (F3): CONSULTA ESPACIAL POSTGIS (ST_DWithin)
# ============================================================================

@app.get("/api/v1/estaciones/busqueda-espacial", summary="F3: Consulta Espacial PostGIS (ST_DWithin)")
def busqueda_espacial_estaciones(
    latitud: float = Query(..., description="Latitud WGS84 del punto de origen"),
    longitud: float = Query(..., description="Longitud WGS84 del punto de origen"),
    radio_km: float = Query(10.0, description="Radio de búsqueda espacial en kilómetros")
):
    """
    F3. Ejecuta una operación espacial en PostGIS mediante ST_DWithin()
    para encontrar las estaciones de monitoreo dentro de un radio de influencia X km
    respecto a un punto geográfico seleccionado en el visor. Usa ST_DistanceSphere()
    para calcular la distancia exacta en metros.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Consulta Espacial usando ST_DWithin sobre tipos geography (EPSG:4326)
    sql_espacial = """
        SELECT 
            e.id, e.codigo, e.nombre, e.tipo_estacion, e.estado,
            m.nombre AS municipio_nombre,
            ST_Distance(
                e.geom::geography, 
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            ) / 1000.0 AS distancia_km,
            ST_AsGeoJSON(e.geom)::json AS geometry
        FROM estaciones_monitoreo e
        JOIN municipios m ON e.municipio_id = m.id
        WHERE ST_DWithin(
            e.geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s * 1000.0
        )
        ORDER BY distancia_km ASC;
    """
    # Parámetros seguros: longitud, latitud, longitud, latitud, radio_km
    cursor.execute(sql_espacial, (longitud, latitud, longitud, latitud, radio_km))
    rows = cursor.fetchall()
    
    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {
                "id": r["id"],
                "codigo": r["codigo"],
                "nombre": r["nombre"],
                "tipo_estacion": r["tipo_estacion"],
                "municipio": r["municipio_nombre"],
                "distancia_km": round(float(r["distancia_km"]), 2)
            }
        })
        
    conn.close()
    return {
        "criterio_busqueda": {
            "centro": {"latitud": latitud, "longitud": longitud},
            "radio_km": radio_km,
            "total_encontradas": len(features)
        },
        "resultado_geojson": {
            "type": "FeatureCollection",
            "features": features
        }
    }

# ============================================================================
# FUNCIONALIDAD 4 (F4): FUNCIONALIDAD GEOGRÁFICA COMPLEMENTARIA (Resumen y Filtros)
# ============================================================================

@app.get("/api/v1/analisis/alertas-municipio", summary="F4: Análisis Estadístico y Alertas por Municipio")
def resumen_alertas_municipio(nivel_alerta: Optional[str] = Query(None, description="Filtro opcional: Normal, Preventivo, Crítico")):
    """
    F4. Consulta temática y analítica agregada que combina GROUP BY entre municipios,
    estaciones y lecturas de sensores para calcular promedios de temperatura, precipitación
    y conteo de eventos de alertas ambientales.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT 
            m.nombre AS municipio,
            COUNT(DISTINCT e.id) AS total_estaciones,
            COUNT(l.id) AS total_lecturas,
            ROUND(AVG(l.temperatura_c), 1) AS temp_promedio_c,
            ROUND(AVG(l.precipitacion_mm), 1) AS precip_promedio_mm,
            COUNT(CASE WHEN l.nivel_alerta = 'Crítico' THEN 1 END) AS alertas_criticas,
            COUNT(CASE WHEN l.nivel_alerta = 'Preventivo' THEN 1 END) AS alertas_preventivas
        FROM municipios m
        LEFT JOIN estaciones_monitoreo e ON m.id = e.municipio_id
        LEFT JOIN lecturas_sensores l ON e.id = l.estacion_id
    """
    params = []
    
    if nivel_alerta:
        sql += " WHERE l.nivel_alerta = %s"
        params.append(nivel_alerta)
        
    sql += " GROUP BY m.id, m.nombre ORDER BY m.nombre ASC;"
    
    cursor.execute(sql, params)
    resumen = cursor.fetchall()
    
    conn.close()
    return {
        "filtro_aplicado": nivel_alerta if nivel_alerta else "Todos los niveles",
        "resumen_municipal": [dict(row) for row in resumen]
    }
