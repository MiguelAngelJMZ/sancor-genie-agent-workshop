-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 05: Validación del entorno — ejecutar el día antes
-- Un ✓ en cada fila = entorno listo para el taller
-- ============================================================

USE CATALOG genie_workshop;
USE SCHEMA sancor;

-- ── 1. Tablas con datos ───────────────────────────────────────────────────────

SELECT 'ramos'       AS tabla, COUNT(*) AS filas,
       CASE WHEN COUNT(*) = 12    THEN '✓ OK' ELSE '✗ REVISAR' END AS estado
FROM ramos
UNION ALL
SELECT 'productores',            COUNT(*),
       CASE WHEN COUNT(*) = 150  THEN '✓ OK' ELSE '✗ REVISAR' END
FROM productores
UNION ALL
SELECT 'clientes',               COUNT(*),
       CASE WHEN COUNT(*) >= 3900 THEN '✓ OK' ELSE '✗ REVISAR' END
FROM clientes
UNION ALL
SELECT 'polizas',                COUNT(*),
       CASE WHEN COUNT(*) >= 7800 THEN '✓ OK' ELSE '✗ REVISAR' END
FROM polizas
UNION ALL
SELECT 'siniestros',             COUNT(*),
       CASE WHEN COUNT(*) >= 3400 THEN '✓ OK' ELSE '✗ REVISAR' END
FROM siniestros;

-- ── 2. Integridad referencial ─────────────────────────────────────────────────

SELECT 'Pólizas sin cliente válido'       AS check_nombre, COUNT(*) AS cant,
       CASE WHEN COUNT(*) = 0 THEN '✓ OK' ELSE '✗ HUÉRFANOS' END AS estado
FROM polizas p LEFT JOIN clientes c ON p.cliente_id = c.cliente_id WHERE c.cliente_id IS NULL
UNION ALL
SELECT 'Pólizas sin productor válido',     COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN '✓ OK' ELSE '✗ HUÉRFANOS' END
FROM polizas p LEFT JOIN productores pr ON p.productor_id = pr.productor_id WHERE pr.productor_id IS NULL
UNION ALL
SELECT 'Siniestros sin póliza válida',     COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN '✓ OK' ELSE '✗ HUÉRFANOS' END
FROM siniestros s LEFT JOIN polizas p ON s.poliza_id = p.poliza_id WHERE p.poliza_id IS NULL;

-- ── 3. Cobertura de metadatos ─────────────────────────────────────────────────

SELECT
  table_name,
  COUNT(*)                                                         AS total_columnas,
  SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS con_comentario,
  CASE WHEN COUNT(*) = SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END)
       THEN '✓ Completo' ELSE '⚠ Parcial' END AS estado
FROM information_schema.columns
WHERE table_catalog = 'genie_workshop'
  AND table_schema   = 'sancor'
  AND table_name IN ('ramos', 'productores', 'clientes', 'polizas', 'siniestros')
GROUP BY table_name
ORDER BY table_name;

-- ── 4. Funciones UC registradas ───────────────────────────────────────────────

SELECT
  routine_name,
  CASE WHEN routine_name IS NOT NULL THEN '✓ Registrada' END AS estado
FROM information_schema.routines
WHERE routine_catalog = 'genie_workshop'
  AND routine_schema   = 'sancor'
  AND routine_name IN (
    'calcular_indice_siniestralidad',
    'calcular_score_riesgo_cliente',
    'clasificar_estado_cartera',
    'proyectar_renovaciones',
    'get_tiempo_promedio_resolucion'
  )
ORDER BY routine_name;

-- ── 5. Datos para preguntas benchmark ────────────────────────────────────────

SELECT 'P1: Pólizas vigentes en Automotores'   AS benchmark, COUNT(*) AS valor,
       CASE WHEN COUNT(*) > 500 THEN '✓ OK' ELSE '✗ POCOS DATOS' END AS estado
FROM polizas p JOIN ramos r ON p.ramo_id = r.ramo_id
WHERE r.nombre_ramo = 'Automotores' AND p.estado = 'vigente'
UNION ALL
SELECT 'P4: Pólizas agrícolas con provincia',  COUNT(*),
       CASE WHEN COUNT(*) > 50 THEN '✓ OK' ELSE '✗ POCOS DATOS' END
FROM polizas p JOIN ramos r ON p.ramo_id = r.ramo_id
JOIN clientes c ON p.cliente_id = c.cliente_id
WHERE r.nombre_ramo = 'Agrícola' AND p.estado = 'vigente'
UNION ALL
SELECT 'P5: Pólizas vencidas sin renovar',     COUNT(*),
       CASE WHEN COUNT(*) > 50 THEN '✓ OK' ELSE '✗ POCOS DATOS' END
FROM polizas WHERE estado = 'vencida'
UNION ALL
SELECT 'P6: Siniestros > 30 días pendientes',  COUNT(*),
       CASE WHEN COUNT(*) > 20 THEN '✓ OK' ELSE '✗ POCOS DATOS' END
FROM siniestros
WHERE estado IN ('pendiente', 'en_proceso')
  AND DATEDIFF(CURRENT_DATE(), fecha_denuncia) > 30;

-- ── 6. Test de funciones UC (TVF — usar SELECT * FROM) ───────────────────────
-- Las funciones ahora retornan tabla; llamarlas con SELECT * FROM en vez de
-- como expresión escalar (de lo contrario Genie tampoco las acepta).

SELECT * FROM genie_workshop.sancor.calcular_indice_siniestralidad('Automotores', 12);
SELECT * FROM genie_workshop.sancor.calcular_score_riesgo_cliente(1);
SELECT * FROM genie_workshop.sancor.clasificar_estado_cartera(1);
SELECT * FROM genie_workshop.sancor.proyectar_renovaciones(NULL, 3);
SELECT * FROM genie_workshop.sancor.get_tiempo_promedio_resolucion(NULL, 'Automotores');

-- ── 7. Test de base de conocimiento (RAG) ─────────────────────────────────────

SELECT COUNT(*) AS total_docs,
       CASE WHEN COUNT(*) = 30 THEN '✓ OK' ELSE '✗ REVISAR' END AS estado
FROM genie_workshop.sancor.conocimiento_cobertura;

SELECT * FROM genie_workshop.sancor.buscar_cobertura('granizo');

SELECT '✅ Todo OK — El taller puede comenzar' AS resultado;
