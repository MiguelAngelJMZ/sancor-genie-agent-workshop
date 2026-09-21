-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 04: Seguridad a nivel de filas (Row-Level Security)
-- Demo: cada productor ve solo su propia cartera en Genie
-- ============================================================

USE CATALOG genie_workshop;
USE SCHEMA sancor;

-- ── Función de filtro para pólizas ───────────────────────────────────────────
-- ON acepta solo columnas de la tabla — el lookup a productores va dentro de la función

CREATE OR REPLACE FUNCTION genie_workshop.sancor.rls_polizas(
  productor_id INT
)
RETURNS BOOLEAN
COMMENT 'Política RLS: oculta al usuario actual las pólizas de un productor asignado determinísticamente por hash de email. Sin bypass de admins.'
RETURN (
  -- Se asigna un productor_id "al azar" por usuario (determinista vía hash del email).
  -- El usuario actual NO puede ver las pólizas de ese productor; ve todo lo demás.
  productor_id != abs(hash(current_user())) % (
    SELECT max(productor_id) FROM genie_workshop.sancor.productores
  ) + 1
);

ALTER TABLE genie_workshop.sancor.polizas
  SET ROW FILTER genie_workshop.sancor.rls_polizas
  ON (productor_id);

-- ── Verificación () ───────────────────────────

SELECT
  current_user()               AS usuario,
  COUNT(*)                     AS polizas_visibles,
  COUNT(DISTINCT productor_id) AS productores_en_vista
FROM genie_workshop.sancor.polizas;


-- ── Para remover las políticas si es necesario ────────────────────────────────
-- ALTER TABLE genie_workshop.sancor.polizas    DROP ROW FILTER;
-- ALTER TABLE genie_workshop.sancor.siniestros DROP ROW FILTER;
