-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 04: Seguridad a nivel de filas (Row-Level Security)
-- Demo: cada productor ve solo su propia cartera en Genie
-- ============================================================
-- IMPORTANTE — ORDEN DE EJECUCIÓN:
--   Ejecutar DESPUÉS de 01_data_generation.py. Además, regenerar los
--   datos con saveAsTable(mode="overwrite") puede quitar el row filter,
--   por lo que es necesario VOLVER A EJECUTAR este script cada vez que se
--   regeneren los datos para reactivar la seguridad.
-- ============================================================
-- ANTES DE EJECUTAR:
--   Actualizar el email de 1-2 productores para que coincidan
--   con los emails de los participantes del taller:
--
--   UPDATE genie_workshop.sancor.productores
--   SET email = 'participante@empresa.com'
--   WHERE productor_id = 1;
--
--   El facilitador (admin del workspace) verá todo gracias al bypass
--   is_member('admins') / is_account_group_member('admins').
-- ============================================================

USE CATALOG genie_workshop;
USE SCHEMA sancor;

-- ── Función de filtro para pólizas ───────────────────────────────────────────
-- ON acepta solo columnas de la tabla — el lookup a productores va dentro de la función

CREATE OR REPLACE FUNCTION genie_workshop.sancor.rls_polizas(
  productor_id INT
)
RETURNS BOOLEAN
COMMENT 'Política RLS: un productor solo ve las pólizas que él gestionó. Admins ven todo.'
RETURN (
  -- Bypass para admins: se contemplan grupos de CUENTA y de WORKSPACE.
  -- El facilitador suele ser admin de workspace (is_member) y NO de un grupo
  -- de cuenta llamado 'admins' (is_account_group_member), por eso se chequean ambos.
  is_account_group_member('admins')
  OR is_member('admins')
  OR EXISTS (
    SELECT 1 FROM genie_workshop.sancor.productores
    WHERE productores.productor_id = rls_polizas.productor_id
      AND productores.email        = current_user()
  )
);

ALTER TABLE genie_workshop.sancor.polizas
  SET ROW FILTER genie_workshop.sancor.rls_polizas
  ON (productor_id);

-- ── Nota sobre siniestros ─────────────────────────────────────────────────────
-- Databricks no permite row filters encadenados (siniestros → polizas → productores
-- cuando polizas ya tiene RLS aplicado). No es necesario: cualquier consulta que
-- una siniestros con polizas hereda automáticamente el filtro de polizas.
-- Genie siempre hace el join, por lo que la seguridad es efectiva end-to-end.

-- ── Verificación (ejecutar como facilitador/admin) ───────────────────────────

SELECT
  current_user()               AS usuario,
  COUNT(*)                     AS polizas_visibles,
  COUNT(DISTINCT productor_id) AS productores_en_vista
FROM genie_workshop.sancor.polizas;

-- ── Instrucciones para el demo en el taller ──────────────────────────────────
-- 1. Facilitador ejecuta la query de arriba → ve todas las pólizas
-- 2. Participante (con email en tabla productores) ejecuta la misma query
--    → ve solo su cartera
-- 3. Ambos hacen la misma pregunta en Genie → respuestas distintas
--    Pregunta sugerida: "¿Cuántas pólizas vigentes tengo?"

-- ── Para remover las políticas si es necesario ────────────────────────────────
-- ALTER TABLE genie_workshop.sancor.polizas    DROP ROW FILTER;
-- ALTER TABLE genie_workshop.sancor.siniestros DROP ROW FILTER;
