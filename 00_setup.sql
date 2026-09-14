-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 00: Configuración inicial del entorno
-- Ejecutar como admin del workspace antes del taller
-- ============================================================

CREATE CATALOG IF NOT EXISTS genie_workshop;

USE CATALOG genie_workshop;

CREATE SCHEMA IF NOT EXISTS sancor;

USE SCHEMA genie_workshop.sancor;

-- Permisos para todos los participantes del taller
GRANT USE CATALOG ON CATALOG genie_workshop TO `account users`;
GRANT USE SCHEMA ON SCHEMA genie_workshop.sancor TO `account users`;
GRANT SELECT ON SCHEMA genie_workshop.sancor TO `account users`;
GRANT EXECUTE ON SCHEMA genie_workshop.sancor TO `account users`;

SELECT 'Entorno listo: genie_workshop.sancor' AS estado;
