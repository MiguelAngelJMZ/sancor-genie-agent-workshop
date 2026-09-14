-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 00: Configuración inicial del entorno
-- Ejecutar una vez en tu workspace antes de comenzar
-- ============================================================

CREATE CATALOG IF NOT EXISTS genie_workshop;

USE CATALOG genie_workshop;

CREATE SCHEMA IF NOT EXISTS sancor;

SELECT 'Entorno listo: genie_workshop.sancor' AS estado;
