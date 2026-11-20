-- ============================================================================
-- PROYECTO: VISOR SIG WEB - SISTEMA DE MONITOREO AMBIENTAL DEL QUINDÍO
-- ASIGNATURA: Programación para SIG - Universidad del Quindío
-- DESCRIPCIÓN: Script de creación de extensión PostGIS, 4 tablas relacionadas,
--              restricciones de integridad referencial, índices espaciales y
--              datos geográficos reales/representativos del Departamento del Quindío.
-- SRID UTILIZADO: EPSG:4326 (WGS84 - Coordenadas Geográficas Latitud/Longitud)
-- ============================================================================

-- Habilitar extensión espacial PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- ----------------------------------------------------------------------------
-- LIMPIEZA DE TABLAS PREVIAS (Para ejecuciones idénticas y limpias)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS lecturas_sensores CASCADE;
DROP TABLE IF EXISTS estaciones_monitoreo CASCADE;
DROP TABLE IF EXISTS vias_acceso CASCADE;
DROP TABLE IF EXISTS municipios CASCADE;

-- ----------------------------------------------------------------------------
-- TABLA 1: municipios (Entidad Polígono Espacial)
-- ----------------------------------------------------------------------------
CREATE TABLE municipios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    codigo_dane VARCHAR(10) NOT NULL,
    area_km2 NUMERIC(10, 2) NOT NULL,
    poblacion INTEGER NOT NULL,
    geom GEOMETRY(Polygon, 4326) NOT NULL
);

-- ----------------------------------------------------------------------------
-- TABLA 2: estaciones_monitoreo (Entidad Punto Espacial - Relación FK con Municipios)
-- ----------------------------------------------------------------------------
CREATE TABLE estaciones_monitoreo (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    tipo_estacion VARCHAR(50) CHECK (tipo_estacion IN ('Meteorológica', 'Hidrométrica', 'Calidad del Aire', 'Agrometeorológica')),
    estado VARCHAR(20) DEFAULT 'Activa' CHECK (estado IN ('Activa', 'Mantenimiento', 'Inactiva')),
    altitud_mabsl NUMERIC(8, 2) NOT NULL,
    municipio_id INTEGER NOT NULL REFERENCES municipios(id) ON DELETE CASCADE,
    geom GEOMETRY(Point, 4326) NOT NULL
);

-- ----------------------------------------------------------------------------
-- TABLA 3: vias_acceso (Entidad Lineal Espacial - Relación FK con Municipios)
-- ----------------------------------------------------------------------------
CREATE TABLE vias_acceso (
    id SERIAL PRIMARY KEY,
    codigo_via VARCHAR(30) NOT NULL,
    nombre_via VARCHAR(150) NOT NULL,
    tipo_superficie VARCHAR(40) CHECK (tipo_superficie IN ('Pavimentada', 'Afirmado', 'Trocha')),
    estado_via VARCHAR(30) CHECK (estado_via IN ('Bueno', 'Regular', 'Crítico')),
    longitud_km NUMERIC(8, 2) NOT NULL,
    municipio_id INTEGER NOT NULL REFERENCES municipios(id) ON DELETE CASCADE,
    geom GEOMETRY(LineString, 4326) NOT NULL
);

-- ----------------------------------------------------------------------------
-- TABLA 4: lecturas_sensores (Tabla Alfanumérica Histórica - Relación FK con Estaciones)
-- ----------------------------------------------------------------------------
CREATE TABLE lecturas_sensores (
    id SERIAL PRIMARY KEY,
    estacion_id INTEGER NOT NULL REFERENCES estaciones_monitoreo(id) ON DELETE CASCADE,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    temperatura_c NUMERIC(5, 2),
    precipitacion_mm NUMERIC(6, 2),
    humedad_relativa NUMERIC(5, 2),
    velocidad_viento_kmh NUMERIC(5, 2),
    nivel_alerta VARCHAR(20) DEFAULT 'Normal' CHECK (nivel_alerta IN ('Normal', 'Preventivo', 'Crítico'))
);

-- ----------------------------------------------------------------------------
-- ÍNDICES ESPACIALES (GIST) PARA OPTIMIZACIÓN DE CONSULTAS POSTGIS
-- ----------------------------------------------------------------------------
CREATE INDEX idx_municipios_geom ON municipios USING GIST (geom);
CREATE INDEX idx_estaciones_geom ON estaciones_monitoreo USING GIST (geom);
CREATE INDEX idx_vias_geom ON vias_acceso USING GIST (geom);
CREATE INDEX idx_lecturas_estacion_id ON lecturas_sensores(estacion_id);

-- ============================================================================
-- POBLADO DE DATOS (DML) - DEPARTAMENTO DEL QUINDÍO, COLOMBIA
-- ============================================================================

-- 1. Inserción de Municipios (Geometrías Simplificadas Polígono)
INSERT INTO municipios (nombre, codigo_dane, area_km2, poblacion, geom) VALUES
('Armenia', '63001', 115.00, 300000, ST_GeomFromText('POLYGON((-75.72 4.51, -75.64 4.51, -75.64 4.57, -75.72 4.57, -75.72 4.51))', 4326)),
('Salento', '63690', 377.00, 9000, ST_GeomFromText('POLYGON((-75.65 4.58, -75.48 4.58, -75.48 4.72, -75.65 4.72, -75.65 4.58))', 4326)),
('Calarcá', '63130', 219.00, 80000, ST_GeomFromText('POLYGON((-75.68 4.45, -75.55 4.45, -75.55 4.54, -75.68 4.54, -75.68 4.45))', 4326)),
('Circasia', '63190', 91.00, 30000, ST_GeomFromText('POLYGON((-75.73 4.58, -75.62 4.58, -75.62 4.65, -75.73 4.65, -75.73 4.58))', 4326));

-- 2. Inserción de Estaciones de Monitoreo (Puntos Espaciales en el Quindío)
INSERT INTO estaciones_monitoreo (codigo, nombre, tipo_estacion, estado, altitud_mabsl, municipio_id, geom) VALUES
('EST-ARM-01', 'Estación Central Uniquindío', 'Meteorológica', 'Activa', 1480.00, 1, ST_GeomFromText('POINT(-75.6603 4.5539)', 4326)),
('EST-ARM-02', 'Estación Parque De la Vida', 'Calidad del Aire', 'Activa', 1510.00, 1, ST_GeomFromText('POINT(-75.6550 4.5450)', 4326)),
('EST-SAL-01', 'Estación Valle de Cocora', 'Agrometeorológica', 'Activa', 2250.00, 2, ST_GeomFromText('POINT(-75.5320 4.6380)', 4326)),
('EST-SAL-02', 'Estación Mirador Salento', 'Meteorológica', 'Mantenimiento', 1920.00, 2, ST_GeomFromText('POINT(-75.5700 4.6370)', 4326)),
('EST-CAL-01', 'Estación Río Quindío - Calarcá', 'Hidrométrica', 'Activa', 1550.00, 3, ST_GeomFromText('POINT(-75.6450 4.5200)', 4326)),
('EST-CIR-01', 'Estación Alto de la Cruz Circasia', 'Meteorológica', 'Activa', 1770.00, 4, ST_GeomFromText('POINT(-75.6350 4.6180)', 4326));

-- 3. Inserción de Vías de Acceso (Vías Principales en LineString)
INSERT INTO vias_acceso (codigo_via, nombre_via, tipo_superficie, estado_via, longitud_km, municipio_id, geom) VALUES
('VIA-ARM-SAL', 'Autopista del Café (Armenia - Salento)', 'Pavimentada', 'Bueno', 24.50, 2, ST_GeomFromText('LINESTRING(-75.6603 4.5539, -75.6350 4.6180, -75.5700 4.6370)', 4326)),
('VIA-ARM-CAL', 'Variante Armenia - Calarcá', 'Pavimentada', 'Bueno', 8.20, 3, ST_GeomFromText('LINESTRING(-75.6603 4.5539, -75.6500 4.5300, -75.6450 4.5200)', 4326)),
('VIA-COC-SAL', 'Carreteable Salento - Cocora', 'Afirmado', 'Regular', 11.40, 2, ST_GeomFromText('LINESTRING(-75.5700 4.6370, -75.5500 4.6350, -75.5320 4.6380)', 4326));

-- 4. Inserción de Lecturas Históricas de Sensores (Datos Alfanuméricos)
INSERT INTO lecturas_sensores (estacion_id, fecha_hora, temperatura_c, precipitacion_mm, humedad_relativa, velocidad_viento_kmh, nivel_alerta) VALUES
(1, CURRENT_TIMESTAMP - INTERVAL '2 hours', 21.5, 0.0, 75.0, 12.4, 'Normal'),
(1, CURRENT_TIMESTAMP - INTERVAL '1 hour', 22.1, 0.0, 72.0, 14.1, 'Normal'),
(2, CURRENT_TIMESTAMP - INTERVAL '1 hour', 23.4, 1.2, 80.0, 8.5, 'Normal'),
(3, CURRENT_TIMESTAMP - INTERVAL '3 hours', 15.2, 45.8, 92.0, 22.0, 'Preventivo'),
(3, CURRENT_TIMESTAMP - INTERVAL '1 hour', 14.8, 68.4, 96.0, 31.5, 'Crítico'),
(4, CURRENT_TIMESTAMP - INTERVAL '5 hours', 17.0, 5.0, 85.0, 10.0, 'Normal'),
(5, CURRENT_TIMESTAMP - INTERVAL '1 hour', 19.8, 32.1, 88.0, 18.2, 'Preventivo'),
(6, CURRENT_TIMESTAMP - INTERVAL '2 hours', 18.5, 12.0, 79.0, 15.0, 'Normal');
