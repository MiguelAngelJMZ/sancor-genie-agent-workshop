-- ============================================================
-- Workshop Genie Agents — Sancor Seguros Argentina
-- Script 02: Metadatos y comentarios en tablas y columnas
-- Ejecutar después de 01_data_generation.py
-- IMPORTANTE: Buenos metadatos = 50% de la calidad de Genie
-- ============================================================

USE CATALOG genie_workshop;
USE SCHEMA sancor;

-- ── TABLA: ramos ──────────────────────────────────────────────────────────────

COMMENT ON TABLE ramos IS
  'Catálogo de ramos (líneas de negocio) de Sancor Seguros. '
  'Un ramo define el tipo de cobertura ofrecida. '
  'Ejemplos: Automotores, Hogar, Agrícola, Responsabilidad Civil. '
  'También llamados "líneas de negocio" o "productos".';

ALTER TABLE ramos ALTER COLUMN ramo_id       COMMENT 'Identificador único del ramo';
ALTER TABLE ramos ALTER COLUMN nombre_ramo   COMMENT 'Nombre comercial del ramo (ej: Automotores, Hogar, Agrícola). Sinónimos: línea de negocio, producto.';
ALTER TABLE ramos ALTER COLUMN codigo_ramo   COMMENT 'Código corto del ramo usado en sistemas internos (ej: AUT, HOG, AGR)';
ALTER TABLE ramos ALTER COLUMN descripcion   COMMENT 'Descripción de la cobertura que ofrece el ramo';
ALTER TABLE ramos ALTER COLUMN prima_min_ars COMMENT 'Prima mínima anual en pesos argentinos (ARS) para este ramo';
ALTER TABLE ramos ALTER COLUMN prima_max_ars COMMENT 'Prima máxima anual en pesos argentinos (ARS) para este ramo';

-- ── TABLA: productores ───────────────────────────────────────────────────────

COMMENT ON TABLE productores IS
  'Red de Productores Asesores de Sancor Seguros. '
  'Los productores son intermediarios habilitados por la SSN (Superintendencia de Seguros de la Nación) '
  'que comercializan y gestionan pólizas. '
  'También llamados "agentes", "asesores de seguros" o "intermediarios".';

ALTER TABLE productores ALTER COLUMN productor_id     COMMENT 'Identificador único del productor asesor';
ALTER TABLE productores ALTER COLUMN nombre           COMMENT 'Nombre del productor asesor';
ALTER TABLE productores ALTER COLUMN apellido         COMMENT 'Apellido del productor asesor';
ALTER TABLE productores ALTER COLUMN email            COMMENT 'Email corporativo del productor. Usado para autenticación y seguridad a nivel de filas (RLS).';
ALTER TABLE productores ALTER COLUMN provincia        COMMENT 'Provincia argentina donde opera el productor';
ALTER TABLE productores ALTER COLUMN zona             COMMENT 'Zona comercial de Sancor: Zona GBA, Zona Centro, Zona NOA, Zona NEA, Zona Cuyo, Zona Patagonia. La "zona interior" excluye Zona GBA.';
ALTER TABLE productores ALTER COLUMN tasa_retencion   COMMENT 'Proporción de clientes que renuevan su póliza (valor entre 0 y 1). '
                                                              'Menor a 0.50: cartera crítica. Entre 0.50 y 0.65: en riesgo. '
                                                              'Entre 0.65 y 0.80: en seguimiento. Mayor o igual a 0.80: saludable. '
                                                              'También llamada tasa de renovación.';
ALTER TABLE productores ALTER COLUMN anos_experiencia COMMENT 'Años de experiencia como productor asesor de seguros';
ALTER TABLE productores ALTER COLUMN activo           COMMENT 'Indica si el productor está activo (true) o dado de baja (false)';

-- ── TABLA: clientes ───────────────────────────────────────────────────────────

COMMENT ON TABLE clientes IS
  'Registro de asegurados de Sancor Seguros. '
  'Contiene todos los tomadores de pólizas. '
  'También llamados "asegurados", "tomadores" o "titulares de póliza". '
  'Un cliente puede tener múltiples pólizas activas en distintos ramos.';

ALTER TABLE clientes ALTER COLUMN cliente_id       COMMENT 'Identificador único del cliente asegurado';
ALTER TABLE clientes ALTER COLUMN nombre           COMMENT 'Nombre del cliente (asegurado)';
ALTER TABLE clientes ALTER COLUMN apellido         COMMENT 'Apellido del cliente (asegurado)';
ALTER TABLE clientes ALTER COLUMN dni              COMMENT 'Documento Nacional de Identidad del cliente. Identificador personal único en Argentina.';
ALTER TABLE clientes ALTER COLUMN email            COMMENT 'Email de contacto del cliente';
ALTER TABLE clientes ALTER COLUMN provincia        COMMENT 'Provincia argentina de residencia del cliente. Usar para análisis geográficos y exposición regional.';
ALTER TABLE clientes ALTER COLUMN fecha_nacimiento COMMENT 'Fecha de nacimiento del cliente. Usada para calcular edad y segmentación actuarial.';
ALTER TABLE clientes ALTER COLUMN fecha_alta       COMMENT 'Fecha de primer registro del cliente en Sancor. Usada para calcular antigüedad.';
ALTER TABLE clientes ALTER COLUMN canal_captacion  COMMENT 'Canal por el que el cliente fue captado: Online, Productor, Autogestión, WhatsApp, Telefónico.';
ALTER TABLE clientes ALTER COLUMN score_crediticio COMMENT 'Score crediticio del cliente (350-950). Mayor score indica menor riesgo crediticio. Usado en suscripción.';

ALTER TABLE clientes ALTER COLUMN nombre           SET TAGS ('pii' = 'NAME');
ALTER TABLE clientes ALTER COLUMN apellido         SET TAGS ('pii' = 'NAME');
ALTER TABLE clientes ALTER COLUMN dni              SET TAGS ('pii' = 'SSN');
ALTER TABLE clientes ALTER COLUMN email            SET TAGS ('pii' = 'EMAIL');

-- ── TABLA: polizas ────────────────────────────────────────────────────────────

COMMENT ON TABLE polizas IS
  'Registro central de pólizas de seguros de Sancor Seguros Argentina. '
  'Una póliza es un contrato de seguro entre Sancor y un cliente, '
  'comercializado por un productor asesor, para un ramo específico. '
  'También llamadas "coberturas" o "contratos". '
  'Estados: vigente, pendiente_renovacion (vence en < 30 días), '
  'vencida (expirada sin renovar), cancelada (dada de baja), suspendida.';

ALTER TABLE polizas ALTER COLUMN poliza_id         COMMENT 'Número de póliza. Identificador único del contrato de seguro.';
ALTER TABLE polizas ALTER COLUMN cliente_id        COMMENT 'Cliente asegurado titular de la póliza (FK → clientes)';
ALTER TABLE polizas ALTER COLUMN productor_id      COMMENT 'Productor asesor que gestionó la póliza (FK → productores)';
ALTER TABLE polizas ALTER COLUMN ramo_id           COMMENT 'Ramo o línea de negocio de la póliza (FK → ramos). Ej: 1=Automotores, 2=Hogar, 3=Agrícola.';
ALTER TABLE polizas ALTER COLUMN fecha_inicio      COMMENT 'Fecha de inicio de vigencia de la póliza';
ALTER TABLE polizas ALTER COLUMN fecha_vencimiento COMMENT 'Fecha de vencimiento de la póliza. Si está vencida y no renovada, el estado es "vencida".';
ALTER TABLE polizas ALTER COLUMN estado            COMMENT 'Estado actual: vigente, pendiente_renovacion, vencida, cancelada, suspendida. '
                                                           '"Pólizas activas" = estado vigente. "Renovaciones pendientes" = pendiente_renovacion.';
ALTER TABLE polizas ALTER COLUMN prima_anual       COMMENT 'Prima anual en pesos argentinos (ARS). Precio que paga el cliente por la cobertura. Sinónimo: precio de la póliza.';
ALTER TABLE polizas ALTER COLUMN suma_asegurada    COMMENT 'Monto máximo a indemnizar en caso de siniestro (ARS). Capital asegurado.';
ALTER TABLE polizas ALTER COLUMN canal_venta       COMMENT 'Canal por el que se contrató la póliza: Online, Productor, Autogestión, WhatsApp, Telefónico.';

-- ── TABLA: siniestros ─────────────────────────────────────────────────────────

COMMENT ON TABLE siniestros IS
  'Registro de siniestros (reclamos) de Sancor Seguros. '
  'Un siniestro es un evento cubierto por una póliza que genera una denuncia y potencial indemnización. '
  'También llamados "reclamos", "denuncias", "expedientes" o "claims". '
  'SLA objetivo de resolución: 15 días para siniestros simples, 30 días para complejos. '
  'Estados: pendiente (sin asignar), en_proceso (en análisis), resuelto (liquidado), rechazado (sin cobertura).';

ALTER TABLE siniestros ALTER COLUMN siniestro_id    COMMENT 'Número de expediente del siniestro. Identificador único.';
ALTER TABLE siniestros ALTER COLUMN poliza_id       COMMENT 'Póliza bajo la cual se denuncia el siniestro (FK → polizas)';
ALTER TABLE siniestros ALTER COLUMN fecha_siniestro COMMENT 'Fecha en que ocurrió el evento siniestral (el accidente, robo, granizo, etc.)';
ALTER TABLE siniestros ALTER COLUMN tipo_siniestro  COMMENT 'Tipo de evento: robo_total, robo_parcial, daño_propio, granizo, incendio, inundacion, accidente_personal, etc.';
ALTER TABLE siniestros ALTER COLUMN monto_siniestro COMMENT 'Monto de la indemnización en pesos argentinos (ARS). Para siniestros no resueltos, es el monto reclamado.';
ALTER TABLE siniestros ALTER COLUMN estado          COMMENT 'Estado del siniestro: pendiente (sin asignar), en_proceso (en análisis por liquidador), '
                                                            'resuelto (pago efectuado o cerrado), rechazado (evento sin cobertura).';
ALTER TABLE siniestros ALTER COLUMN fecha_denuncia  COMMENT 'Fecha en que el asegurado realizó la denuncia formal del siniestro a Sancor.';
ALTER TABLE siniestros ALTER COLUMN fecha_resolucion COMMENT 'Fecha de liquidación o rechazo del siniestro. NULL si está pendiente o en proceso.';
ALTER TABLE siniestros ALTER COLUMN dias_resolucion COMMENT 'Días entre la denuncia y la resolución. NULL si no está resuelto. SLA objetivo: 15 días.';
ALTER TABLE siniestros ALTER COLUMN liquidador_id   COMMENT 'Código del liquidador (perito) asignado al siniestro. Formato: LIQ001 a LIQ040.';

SELECT 'Metadatos aplicados a las 5 tablas correctamente' AS estado;
