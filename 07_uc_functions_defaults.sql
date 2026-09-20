-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 07: Parámetros con DEFAULT en las funciones UC
-- ------------------------------------------------------------
-- Motivo: para el agente custom (ResponsesAgent) las funciones se invocan vía
-- el ejecutor de unitycatalog-ai, que NO admite None en un parámetro requerido.
-- Declarar DEFAULT NULL (y DEFAULT 12 en las ventanas de meses) vuelve opcionales
-- los parámetros documentados como "NULL = todos", de modo que el modelo pueda
-- omitirlos al pedir agregados de toda la cartera/ramos.
-- Cambio retrocompatible: Genie y las llamadas existentes siguen funcionando igual.
-- Solo recrea las 3 funciones con parámetros nullable; el cuerpo no cambia.
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

SELECT 'Funciones 1, 4 y 5 recreadas con parámetros DEFAULT (nullable)' AS estado;
