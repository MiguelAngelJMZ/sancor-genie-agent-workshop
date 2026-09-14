-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 03: Funciones de Unity Catalog para Genie Agent
-- Ejecutar después de 01_data_generation.py
-- ⚠️  TODAS las funciones usan RETURNS TABLE porque Genie
--     solo acepta TVF (table-valued functions). Las funciones
--     escalares (RETURNS DOUBLE/INT/STRING) generan el error:
--     "You must select a function that returns a table".
-- ============================================================

USE CATALOG genie_workshop;
USE SCHEMA sancor;

-- ── FUNCIÓN 1: Índice de siniestralidad ───────────────────────────────────────

CREATE OR REPLACE FUNCTION genie_workshop.sancor.calcular_indice_siniestralidad(
  p_nombre_ramo  STRING  DEFAULT NULL  COMMENT 'Nombre del ramo (ej: Automotores, Hogar, Agrícola). NULL/omitido = todos los ramos.',
  p_meses_atras  INT     DEFAULT 12    COMMENT 'Ventana de tiempo en meses (ej: 12 = último año, 3 = último trimestre). Omitido = 12.'
)
RETURNS TABLE(
  nombre_ramo           STRING,
  indice_siniestralidad DOUBLE,
  nivel_riesgo          STRING,
  total_primas_ars      LONG,
  total_siniestros_ars  LONG
)
COMMENT 'Calcula el índice de siniestralidad de un ramo: suma de siniestros / suma de primas. '
        'Valores > 0.70 (70%) indican riesgo. Valores > 1.0 indican pérdida neta. '
        'Excluye siniestros rechazados. '
        'Invocar para: rentabilidad de ramos, siniestralidad, pérdidas, combined ratio, estado financiero.'
RETURN
  SELECT
    r.nombre_ramo,
    ROUND(
      COALESCE(SUM(s.monto_siniestro), 0.0) / NULLIF(SUM(p.prima_anual), 0),
      4
    )                                                             AS indice_siniestralidad,
    CASE
      WHEN COALESCE(SUM(s.monto_siniestro), 0.0)
           / NULLIF(SUM(p.prima_anual), 0) > 0.9  THEN 'Crítico (>90%)'
      WHEN COALESCE(SUM(s.monto_siniestro), 0.0)
           / NULLIF(SUM(p.prima_anual), 0) > 0.7  THEN 'En riesgo (70-90%)'
      ELSE 'Normal (<70%)'
    END                                                           AS nivel_riesgo,
    SUM(p.prima_anual)                                            AS total_primas_ars,
    COALESCE(SUM(s.monto_siniestro), 0)                           AS total_siniestros_ars
  FROM genie_workshop.sancor.polizas p
  JOIN genie_workshop.sancor.ramos r  ON p.ramo_id = r.ramo_id
  LEFT JOIN genie_workshop.sancor.siniestros s
         ON p.poliza_id = s.poliza_id
        AND s.fecha_siniestro >= ADD_MONTHS(CURRENT_DATE(), -p_meses_atras)
        AND s.estado != 'rechazado'
  WHERE (p_nombre_ramo IS NULL OR r.nombre_ramo = p_nombre_ramo)
    AND p.estado IN ('vigente', 'vencida')
  GROUP BY r.nombre_ramo;

-- ── FUNCIÓN 2: Score de riesgo del cliente ────────────────────────────────────

CREATE OR REPLACE FUNCTION genie_workshop.sancor.calcular_score_riesgo_cliente(
  p_cliente_id  INT  COMMENT 'ID del cliente a evaluar'
)
RETURNS TABLE(
  cliente_id      INT,
  nombre_completo STRING,
  score_riesgo    INT,
  nivel_riesgo    STRING
)
COMMENT 'Calcula un score de riesgo para un cliente basado en historial de siniestros (0-100). '
        '0-30: riesgo bajo. 31-60: riesgo medio. 61-80: riesgo alto. 81-100: riesgo muy alto. '
        'Considera: frecuencia de siniestros en 12 meses, monto promedio, historial total. '
        'Invocar para: clientes de alto riesgo, segmentación de cartera, política de renovación, detección de fraude.'
RETURN
  SELECT
    sc.cliente_id,
    sc.nombre_completo,
    sc.score_riesgo,
    CASE
      WHEN sc.score_riesgo > 80 THEN 'Muy alto (81-100)'
      WHEN sc.score_riesgo > 60 THEN 'Alto (61-80)'
      WHEN sc.score_riesgo > 30 THEN 'Medio (31-60)'
      ELSE 'Bajo (0-30)'
    END AS nivel_riesgo
  FROM (
    SELECT
      c.cliente_id,
      c.nombre || ' ' || c.apellido                              AS nombre_completo,
      LEAST(100, GREATEST(0, CAST(
          (COUNT(CASE WHEN s.fecha_siniestro >= ADD_MONTHS(CURRENT_DATE(), -12) THEN 1 END) * 20)
        + CASE
            WHEN AVG(s.monto_siniestro) > 3000000 THEN 30
            WHEN AVG(s.monto_siniestro) > 1000000 THEN 20
            WHEN AVG(s.monto_siniestro) >  500000 THEN 10
            ELSE 5
          END
        + LEAST(30, COUNT(s.siniestro_id) * 5)
      AS INT)))                                                   AS score_riesgo
    FROM genie_workshop.sancor.clientes c
    LEFT JOIN genie_workshop.sancor.polizas pol  ON c.cliente_id  = pol.cliente_id
    LEFT JOIN genie_workshop.sancor.siniestros s
           ON pol.poliza_id = s.poliza_id
          AND s.estado != 'rechazado'
    WHERE c.cliente_id = p_cliente_id
    GROUP BY c.cliente_id, c.nombre, c.apellido
  ) sc;

-- ── FUNCIÓN 3: Estado de cartera del productor ────────────────────────────────

CREATE OR REPLACE FUNCTION genie_workshop.sancor.clasificar_estado_cartera(
  p_productor_id  INT  DEFAULT NULL
  COMMENT 'ID del productor a evaluar. NULL u omitido = clasifica TODOS los productores activos.'
)
RETURNS TABLE(
  productor_id     INT,
  nombre_productor STRING,
  provincia        STRING,
  zona             STRING,
  estado_cartera   STRING,
  tasa_retencion   DOUBLE,
  polizas_vigentes INT,
  polizas_vencidas INT,
  prima_vigente_ars LONG
)
COMMENT 'Clasifica la cartera de productores: Saludable, En seguimiento, En riesgo o Crítico. '
        'Considera: tasa de retención y cantidad de pólizas vencidas sin renovar. '
        'Pasar NULL (o llamar sin argumentos) para obtener TODOS los productores activos clasificados. '
        'Pasar un productor_id específico para evaluar uno solo. '
        'Invocar para: productores en riesgo, alertas de cartera, gestión de la red, '
        'visitas comerciales, filtrar por estado_cartera = ''Crítico'' o ''En riesgo''.'
RETURN
  SELECT
    prod.productor_id,
    prod.nombre || ' ' || prod.apellido                                  AS nombre_productor,
    prod.provincia,
    prod.zona,
    CASE
      WHEN prod.tasa_retencion >= 0.80
       AND SUM(CASE WHEN pol.estado = 'vencida' THEN 1 ELSE 0 END) <= 3
        THEN 'Saludable'
      WHEN prod.tasa_retencion >= 0.65
        THEN 'En seguimiento'
      WHEN prod.tasa_retencion >= 0.50
        OR  SUM(CASE WHEN pol.estado = 'vencida' THEN 1 ELSE 0 END) > 10
        THEN 'En riesgo'
      ELSE 'Crítico'
    END                                                                  AS estado_cartera,
    prod.tasa_retencion,
    SUM(CASE WHEN pol.estado = 'vigente' THEN 1 ELSE 0 END)              AS polizas_vigentes,
    SUM(CASE WHEN pol.estado = 'vencida' THEN 1 ELSE 0 END)              AS polizas_vencidas,
    SUM(CASE WHEN pol.estado = 'vigente' THEN pol.prima_anual ELSE 0 END) AS prima_vigente_ars
  FROM genie_workshop.sancor.productores prod
  LEFT JOIN genie_workshop.sancor.polizas pol ON prod.productor_id = pol.productor_id
  WHERE prod.activo = true
    AND (p_productor_id IS NULL OR prod.productor_id = p_productor_id)
  GROUP BY prod.productor_id, prod.nombre, prod.apellido,
           prod.provincia, prod.zona, prod.tasa_retencion;

-- ── FUNCIÓN 4: Proyección de renovaciones ─────────────────────────────────────

CREATE OR REPLACE FUNCTION genie_workshop.sancor.proyectar_renovaciones(
  p_productor_id  INT  DEFAULT NULL  COMMENT 'ID del productor. NULL/omitido = proyección de toda la red.',
  p_meses         INT  DEFAULT 12    COMMENT 'Horizonte de proyección en meses (1-12). Omitido = 12.'
)
RETURNS TABLE(
  renovaciones_proyectadas BIGINT,
  polizas_base             BIGINT,
  tasa_retencion_promedio  DOUBLE,
  horizonte_meses          INT
)
COMMENT 'Proyecta la cantidad de renovaciones probables en los próximos N meses, '
        'basado en la tasa de retención histórica del productor. '
        'Invocar para: forecast de cartera, planning comercial, metas de renovación, pipeline.'
RETURN
  SELECT
    CAST(COUNT(pol.poliza_id) * COALESCE(AVG(prod.tasa_retencion), 0.72) AS BIGINT)
                                                                 AS renovaciones_proyectadas,
    COUNT(pol.poliza_id)                                         AS polizas_base,
    ROUND(COALESCE(AVG(prod.tasa_retencion), 0.72), 3)           AS tasa_retencion_promedio,
    p_meses                                                      AS horizonte_meses
  FROM genie_workshop.sancor.polizas pol
  JOIN genie_workshop.sancor.productores prod ON pol.productor_id = prod.productor_id
  WHERE pol.fecha_vencimiento BETWEEN CURRENT_DATE() AND ADD_MONTHS(CURRENT_DATE(), p_meses)
    AND pol.estado IN ('vigente', 'pendiente_renovacion')
    AND (p_productor_id IS NULL OR pol.productor_id = p_productor_id);

-- ── FUNCIÓN 5: Tiempo promedio de resolución ──────────────────────────────────

CREATE OR REPLACE FUNCTION genie_workshop.sancor.get_tiempo_promedio_resolucion(
  p_tipo_siniestro  STRING  DEFAULT NULL  COMMENT 'Tipo de siniestro (ej: robo_total, granizo). NULL/omitido = todos los tipos.',
  p_ramo_nombre     STRING  DEFAULT NULL  COMMENT 'Nombre del ramo (ej: Automotores, Hogar). NULL/omitido = todos los ramos.'
)
RETURNS TABLE(
  filtro_tipo              STRING,
  filtro_ramo              STRING,
  dias_promedio_resolucion DOUBLE,
  cumple_sla               STRING,
  total_siniestros         BIGINT
)
COMMENT 'Retorna el tiempo promedio de resolución en días, filtrado por tipo y/o ramo. '
        'SLA objetivo de Sancor: 15 días para siniestros simples, 30 para complejos. '
        'Valores > 30 días indican incumplimiento de SLA. '
        'Invocar para: eficiencia operativa, SLA, tiempos de atención, performance de liquidadores, KPIs de operaciones.'
RETURN
  SELECT
    COALESCE(p_tipo_siniestro, 'Todos')   AS filtro_tipo,
    COALESCE(p_ramo_nombre,    'Todos')   AS filtro_ramo,
    ROUND(AVG(s.dias_resolucion), 1)      AS dias_promedio_resolucion,
    CASE
      WHEN AVG(s.dias_resolucion) <= 15 THEN 'Cumple SLA simple (≤15 días)'
      WHEN AVG(s.dias_resolucion) <= 30 THEN 'Cumple SLA complejo (≤30 días)'
      ELSE 'Incumple SLA (>30 días)'
    END                                   AS cumple_sla,
    COUNT(*)                              AS total_siniestros
  FROM genie_workshop.sancor.siniestros s
  JOIN genie_workshop.sancor.polizas p  ON s.poliza_id = p.poliza_id
  JOIN genie_workshop.sancor.ramos   r  ON p.ramo_id   = r.ramo_id
  WHERE s.estado           = 'resuelto'
    AND s.dias_resolucion IS NOT NULL
    AND (p_tipo_siniestro IS NULL OR s.tipo_siniestro = p_tipo_siniestro)
    AND (p_ramo_nombre    IS NULL OR r.nombre_ramo    = p_ramo_nombre);

-- ── Verificación ──────────────────────────────────────────────────────────────

SELECT routine_name, routine_type
FROM information_schema.routines
WHERE routine_catalog = 'genie_workshop'
  AND routine_schema   = 'sancor'
ORDER BY routine_name;

SELECT '5 funciones UC (TVF) creadas y listas para Genie Agent' AS estado;
