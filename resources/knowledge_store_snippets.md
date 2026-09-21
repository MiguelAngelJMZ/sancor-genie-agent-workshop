# Knowledge Store Snippets — Taller Genie Agents
## Sancor Seguros Argentina

Contenido listo para pegar en el **Genie Agent** durante el taller.

Este archivo está organizado según la **jerarquía de curación de Databricks**, de mayor a
menor impacto en la calidad de las respuestas. Cada capa se agrega en un lugar distinto de la
UI de Genie. Trabajar en este orden es, en sí mismo, el mensaje pedagógico del taller.

| # | Capa de curación | Dónde se configura en Genie | Impacto |
|---|------------------|-----------------------------|---------|
| 0 | **Metadatos** (comentarios de tablas y columnas) | Unity Catalog → ya aplicado en `02_metadata.sql` | ★★★★★ |
| 1 | **SQL expressions** (medidas, filtros, dimensiones) | Genie → *Instructions* → *SQL expressions* | ★★★★☆ |
| 2 | **Join relationships** (relaciones con cardinalidad) | Genie → *Instructions* → *Joins* | ★★★★☆ |
| 3 | **Example SQL queries** (pregunta + SQL validado + intención) | Genie → *Instructions* → *Example queries* | ★★★★☆ |
| 4 | **SQL functions** (funciones UC de negocio) | Genie → *Instructions* → *SQL functions* | ★★★★☆ |
| 5 | **General instructions** (texto libre — último recurso) | Genie → *Instructions* → *General instructions* | ★★☆☆☆ |

> **Regla de oro (docs de Databricks):** si puedes expresar la lógica como una SQL expression,
> un example query o una función UC, **no la escribas como instrucción de texto**. El texto es el
> último recurso, solo para vacíos conceptuales que las otras capas no cubren.

**Límites a tener presentes (para no saturar el taller):**
- Máximo **200 snippets** de knowledge store (descripciones + joins + SQL expressions comparten el cupo).
- Máximo **100 instrucciones**: cada example query, cada SQL function y **todo** el bloque de general
  instructions cuentan como **1** instrucción cada uno.
- Recomendado **≤ 5–7 tablas** por espacio (aquí usamos 5: `ramos`, `productores`, `clientes`, `polizas`, `siniestros`).

---

# 0 · Metadatos (recordatorio)

Ya aplicados en `02_metadata.sql` (comentarios de tabla + columna, tags de PII). **No es necesario
repetirlos aquí**, pero recuerda durante el taller que este es el paso de mayor impacto: sin buenos
comentarios, todo lo demás rinde menos. Regla mental: *Genie traduce palabras a SQL; si las columnas
no tienen palabras, adivina.*

---

# 1 · SQL Expressions (medidas, filtros y dimensiones)

Pegar cada una en **Instructions → SQL expressions**. Una SQL expression es una porción de SQL
reutilizable que Genie aplica **exactamente como está escrita** cuando el usuario menciona el
concepto. Cada expression lleva tres partes: la **expresión**, los **sinónimos** que la disparan y
una **instrucción** breve que explica cuándo usarla.

> Nota técnica: las SQL expressions operan sobre **una tabla** dentro de la consulta que Genie arma.
> Las razones/ratios que cruzan tablas (ej. índice de siniestralidad = siniestros/primas) se resuelven
> mejor con un **example query** (§3) o una **función UC** (§4), no como SQL expression.
>
> ⚠️ **Califica SIEMPRE las columnas con el nombre de la tabla** (`polizas.prima_anual`, no
> `prima_anual`). Como Genie arma joins entre varias tablas, una columna sin calificar es ambigua y
> falla con el error *"Table name or alias is required for column ..."*. Todas las expresiones de
> abajo ya vienen calificadas con su tabla.

## 1A · Medidas (measures)

**Prima total (primaje)** — tabla `polizas`
```sql
SUM(polizas.prima_anual)
```
- **Sinónimos:** primaje, cartera en pesos, prima emitida, volumen de primas, ingresos por primas
- **Instrucción:** Suma de primas anuales en ARS. Es la métrica principal de tamaño de cartera. Filtrar por `polizas.estado = 'vigente'` si el usuario pide "cartera activa".

**Cantidad de pólizas** — tabla `polizas`
```sql
COUNT(DISTINCT polizas.poliza_id)
```
- **Sinónimos:** número de pólizas, cantidad de coberturas, total de contratos, pólizas emitidas
- **Instrucción:** Conteo de pólizas. Usar DISTINCT porque una póliza puede aparecer repetida al unir con `siniestros`.

**Suma asegurada total (exposición)** — tabla `polizas`
```sql
SUM(polizas.suma_asegurada)
```
- **Sinónimos:** exposición, capital asegurado, monto expuesto, exposición total
- **Instrucción:** Capital máximo a indemnizar en ARS. Es la exposición de riesgo, distinta de la prima (lo que cobra Sancor).

**Monto total de siniestros** — tabla `siniestros`
```sql
SUM(siniestros.monto_siniestro)
```
- **Sinónimos:** siniestros pagados, monto indemnizado, costo de siniestros, egresos por siniestros
- **Instrucción:** Suma de indemnizaciones en ARS. Para el costo real de siniestros liquidados, combinar con el filtro `siniestros resueltos`. Excluir `siniestros.estado = 'rechazado'` salvo que el usuario pida rechazados explícitamente.

**Ticket promedio de siniestro** — tabla `siniestros`
```sql
AVG(siniestros.monto_siniestro)
```
- **Sinónimos:** siniestro promedio, monto promedio de siniestro, ticket medio, severidad
- **Instrucción:** Costo medio por siniestro (severidad). Excluir `rechazado`.

**Tiempo promedio de resolución** — tabla `siniestros`
```sql
AVG(CASE WHEN siniestros.estado = 'resuelto' THEN siniestros.dias_resolucion END)
```
- **Sinónimos:** días promedio de resolución, tiempo de atención, demora media, tiempo de liquidación
- **Instrucción:** Días promedio entre denuncia y resolución, sólo sobre siniestros resueltos. SLA objetivo: 15 días (simples) / 30 días (complejos). Valores > 30 indican incumplimiento.

**Cumplimiento de SLA (%)** — tabla `siniestros`
```sql
AVG(CASE WHEN siniestros.estado = 'resuelto' AND siniestros.dias_resolucion <= 30 THEN 1.0
         WHEN siniestros.estado = 'resuelto' THEN 0.0 END)
```
- **Sinónimos:** % dentro de SLA, cumplimiento de SLA, tasa de cumplimiento, siniestros a tiempo
- **Instrucción:** Fracción de siniestros resueltos dentro de los 30 días. Resultado entre 0 y 1; multiplicar por 100 para mostrar como porcentaje.

**Tasa de retención promedio** — tabla `productores`
```sql
AVG(productores.tasa_retencion)
```
- **Sinónimos:** retención media, tasa de renovación promedio, retención de cartera
- **Instrucción:** Promedio de la proporción de clientes que renuevan (0 a 1). Multiplicar por 100 para porcentaje. < 0.50 crítico, 0.50–0.65 en riesgo, > 0.80 saludable.

### 🧪 Pruébalo en Genie (después de agregar las medidas)
- *"¿Cuál es el primaje total de la cartera vigente?"* → ejercita la medida **prima total**.
- *"¿Cuál es el ticket promedio de siniestro por ramo?"* → ejercita la medida **ticket promedio de siniestro**.

## 1B · Filtros (filters)

**Pólizas activas / vigentes** — tabla `polizas`
```sql
polizas.estado = 'vigente'
```
- **Sinónimos:** pólizas activas, coberturas vigentes, contratos en vigor, pólizas al día
- **Instrucción:** Aplicar cuando el usuario habla de cartera "activa", "vigente" o "al día".

**Renovaciones pendientes** — tabla `polizas`
```sql
polizas.estado = 'pendiente_renovacion'
```
- **Sinónimos:** por renovar, próximas a vencer, pendientes de renovación, renovaciones del mes
- **Instrucción:** Pólizas que vencen en menos de 30 días y aún no se renovaron.

**Cartera vencida (sin renovar)** — tabla `polizas`
```sql
polizas.estado = 'vencida'
```
- **Sinónimos:** pólizas vencidas, caídas, no renovadas, cartera perdida, bajas por vencimiento
- **Instrucción:** Pólizas expiradas que el cliente no renovó. Métrica clave de fuga de cartera.

**Siniestros abiertos (en trámite)** — tabla `siniestros`
```sql
siniestros.estado IN ('pendiente', 'en_proceso')
```
- **Sinónimos:** siniestros abiertos, en trámite, sin resolver, expedientes activos, reclamos abiertos
- **Instrucción:** Siniestros que todavía no fueron liquidados ni rechazados.

**Siniestros demorados (fuera de SLA)** — tabla `siniestros`
```sql
siniestros.estado IN ('pendiente', 'en_proceso')
  AND DATEDIFF(CURRENT_DATE(), siniestros.fecha_denuncia) > 30
```
- **Sinónimos:** siniestros demorados, atrasados, fuera de SLA, expedientes vencidos, reclamos estancados
- **Instrucción:** Siniestros abiertos con más de 30 días desde la denuncia. Incumplen el SLA objetivo.

**Zona interior** — tabla `productores`
```sql
productores.zona <> 'Zona GBA'
```
- **Sinónimos:** interior, zona interior, fuera de GBA, provincias del interior
- **Instrucción:** Todo lo que no sea Zona GBA (Buenos Aires + CABA). Aplica sobre `productores.zona`.

**Interior del país** — tabla `clientes` (o `productores`)
```sql
clientes.provincia NOT IN ('Buenos Aires', 'CABA')
```
- **Sinónimos:** interior del país, fuera de Buenos Aires, provincias del interior
- **Instrucción:** Cuando el filtro geográfico se pide a nivel provincia (no hay columna `zona` en `clientes`). Si el análisis es sobre productores, usar `productores.provincia`.

**Productores activos** — tabla `productores`
```sql
productores.activo = true
```
- **Sinónimos:** productores activos, agentes habilitados, asesores vigentes, red activa
- **Instrucción:** Excluir productores dados de baja salvo que se pida el histórico completo.

### 🧪 Pruébalo en Genie (después de agregar los filtros)
- *"¿Cuántos siniestros están fuera de SLA hoy?"* → ejercita el filtro **siniestros demorados**.
- *"¿Cuántas pólizas hay por renovar este mes?"* → ejercita el filtro **renovaciones pendientes**.

## 1C · Dimensiones / campos calculados (fields)

**Estado de cartera del productor** — tabla `productores`
```sql
CASE
  WHEN productores.tasa_retencion < 0.50 THEN 'Crítico'
  WHEN productores.tasa_retencion < 0.65 THEN 'En riesgo'
  WHEN productores.tasa_retencion < 0.80 THEN 'En seguimiento'
  ELSE 'Saludable'
END
```
- **Sinónimos:** salud de cartera, semáforo del productor, clasificación de cartera, estado del productor
- **Instrucción:** Clasificación rápida por tasa de retención. Para la clasificación **completa** (que también pesa pólizas vencidas y prima), usar la función UC `clasificar_estado_cartera` (§4).

**Rango etario del cliente** — tabla `clientes`
```sql
CASE
  WHEN DATEDIFF(CURRENT_DATE(), clientes.fecha_nacimiento) / 365 < 30 THEN '18-29'
  WHEN DATEDIFF(CURRENT_DATE(), clientes.fecha_nacimiento) / 365 < 45 THEN '30-44'
  WHEN DATEDIFF(CURRENT_DATE(), clientes.fecha_nacimiento) / 365 < 60 THEN '45-59'
  ELSE '60+'
END
```
- **Sinónimos:** grupo etario, franja de edad, segmento de edad, rango de edad
- **Instrucción:** Agrupa clientes por edad para análisis actuarial y segmentación.

**Segmento de score crediticio** — tabla `clientes`
```sql
CASE
  WHEN clientes.score_crediticio >= 750 THEN 'Bajo riesgo'
  WHEN clientes.score_crediticio >= 550 THEN 'Riesgo medio'
  ELSE 'Alto riesgo'
END
```
- **Sinónimos:** segmento crediticio, nivel de riesgo crediticio, score segmentado
- **Instrucción:** Segmenta por score (350–950). Mayor score = menor riesgo. Usado en suscripción.

### 🧪 Pruébalo en Genie (después de agregar las dimensiones)
- *"¿Cómo se reparten los productores según el estado de su cartera?"* → ejercita el campo **estado de cartera**.
- *"Muestra la cantidad de clientes por rango etario"* → ejercita el campo **rango etario del cliente**.

---

# 2 · Join Relationships

Pegar en **Instructions → Joins**. Definir cada relación con su **cardinalidad** y una nota de
*cuándo usarla* ayuda a Genie a elegir el join correcto y evitar duplicados por fan-out.

| Tabla izquierda | Tabla derecha | Condición de join | Cardinalidad | Cuándo usar |
|-----------------|---------------|-------------------|--------------|-------------|
| `polizas` | `clientes` | `polizas.cliente_id = clientes.cliente_id` | Many-to-One | Análisis de cartera por atributos del cliente (provincia, edad, canal, score). |
| `polizas` | `productores` | `polizas.productor_id = productores.productor_id` | Many-to-One | Cartera por productor/zona; alertas de red comercial; retención. |
| `polizas` | `ramos` | `polizas.ramo_id = ramos.ramo_id` | Many-to-One | Análisis por línea de negocio (Automotores, Hogar, Agrícola, etc.). |
| `siniestros` | `polizas` | `siniestros.poliza_id = polizas.poliza_id` | Many-to-One | Cualquier análisis de siniestros por ramo, productor, cliente o zona. **Este join también hereda el filtro RLS de `polizas`.** |

> **Cuidado con el fan-out:** al unir `polizas` con `siniestros` (1→N), sumar `prima_anual` duplica
> primas si una póliza tiene varios siniestros. Regla: agregar primas y siniestros por separado
> (subconsultas o `COUNT(DISTINCT poliza_id)`), como en el example query §3.1.

### 🧪 Pruébalo en Genie (después de definir los joins)
- *"¿Cuál es la prima total por zona comercial?"* → fuerza el join **polizas → productores** (la zona está en `productores`).
- *"¿Qué ramo concentra la mayor cantidad de siniestros?"* → fuerza la cadena **siniestros → polizas → ramos**.

---

# 3 · Example SQL Queries

Pegar en **Instructions → Example queries**. Cada ejemplo lleva la **pregunta**, una **guía de
intención (user guidance)** — qué le enseña a Genie y cuándo debe reutilizar el patrón — y el **SQL
validado**. Los ejemplos son la mejor herramienta para preguntas ambiguas, multi-parte o con lógica
derivada. Genie generaliza el patrón a preguntas parecidas.

> **Consistencia:** las reglas de estos ejemplos deben coincidir con las SQL expressions y las
> funciones UC. Ej.: siniestralidad siempre excluye `rechazado` y toma `polizas` en `('vigente','vencida')`.

## 3.1 · Índice de siniestralidad por ramo (parametrizado — trusted asset)

**Pregunta:** ¿Cuál es el índice de siniestralidad del ramo :nombre_ramo en los últimos :meses_atras meses?

**Parámetros:**
- `:nombre_ramo` (String) — Nombre del ramo. Ej: `Automotores`, `Hogar`, `Agrícola`. Dejar vacío o `null` para todos los ramos.
- `:meses_atras` (Integer) — Ventana de tiempo en meses hacia atrás. Ej: `12` = último año, `3` = último trimestre.

**Guía de intención (user guidance):**
> Usar para cualquier pregunta de rentabilidad/siniestralidad por ramo (*loss ratio*, "ramo más
> rentable", "dónde hay pérdidas", "siniestralidad de Agrícola este año"). Al tener parámetros,
> Genie solicita el ramo y la ventana de tiempo al usuario antes de ejecutar, convirtiéndolo en un
> **trusted asset** con resultado verificado. Enseña el patrón correcto anti fan-out: primas y
> siniestros en el mismo join plano con LEFT JOIN. Excluye siniestros `rechazado` y toma pólizas
> `vigente`/`vencida`. El semáforo replica el criterio de negocio de Sancor.

```sql
SELECT
    r.nombre_ramo,
    COUNT(DISTINCT p.poliza_id)                                    AS total_polizas,
    SUM(p.prima_anual)                                             AS total_primas_ars,
    COALESCE(SUM(s.monto_siniestro), 0)                            AS total_siniestros_ars,
    ROUND(COALESCE(SUM(s.monto_siniestro), 0)
          / NULLIF(SUM(p.prima_anual), 0), 4)                      AS indice_siniestralidad,
    CASE
        WHEN COALESCE(SUM(s.monto_siniestro), 0)
             / NULLIF(SUM(p.prima_anual), 0) > 0.9  THEN 'Crítico'
        WHEN COALESCE(SUM(s.monto_siniestro), 0)
             / NULLIF(SUM(p.prima_anual), 0) > 0.7  THEN 'En riesgo'
        ELSE 'Normal'
    END                                                            AS semaforo
FROM genie_workshop.sancor.polizas p
JOIN genie_workshop.sancor.ramos r ON p.ramo_id = r.ramo_id
LEFT JOIN genie_workshop.sancor.siniestros s
    ON p.poliza_id = s.poliza_id
   AND s.fecha_siniestro >= ADD_MONTHS(CURRENT_DATE(), -:meses_atras)
   AND s.estado != 'rechazado'
WHERE p.estado IN ('vigente', 'vencida')
  AND (:nombre_ramo IS NULL OR r.nombre_ramo = :nombre_ramo)
GROUP BY r.nombre_ramo
ORDER BY indice_siniestralidad DESC NULLS LAST;
```

## 3.2 · Productores con cartera vencida

**Pregunta:** ¿Qué productores tienen más pólizas vencidas sin renovar?

**Guía de intención (user guidance):**
> Usar para preguntas de gestión de la red comercial: productores con fuga de cartera, alertas de
> retención, prioridades de visita comercial. Enseña a cruzar `productores` con sus `polizas`
> vencidas y a clasificar por `tasa_retencion` (criterio Crítico/En riesgo/Normal de Sancor). El
> `HAVING >= 3` filtra ruido: sólo casos accionables. Generalizar a "productores en riesgo" o
> "cartera crítica en el interior" agregando el filtro `zona <> 'Zona GBA'`.

```sql
SELECT
    pr.nombre || ' ' || pr.apellido    AS productor,
    pr.provincia,
    pr.zona,
    ROUND(pr.tasa_retencion * 100, 1)  AS retencion_pct,
    COUNT(p.poliza_id)                 AS polizas_vencidas,
    CASE
        WHEN pr.tasa_retencion < 0.50  THEN 'Crítico'
        WHEN pr.tasa_retencion < 0.65  THEN 'En riesgo'
        ELSE 'Normal'
    END                                AS estado_cartera
FROM genie_workshop.sancor.productores pr
JOIN genie_workshop.sancor.polizas p
    ON pr.productor_id = p.productor_id
   AND p.estado = 'vencida'
GROUP BY pr.productor_id, pr.nombre, pr.apellido,
         pr.provincia, pr.zona, pr.tasa_retencion
HAVING COUNT(p.poliza_id) >= 3
ORDER BY polizas_vencidas DESC
LIMIT 15;
```

## 3.3 · Siniestros demorados (incumplimiento de SLA)

**Pregunta:** ¿Cuántos siniestros llevan más de 30 días sin resolverse?

**Guía de intención (user guidance):**
> Usar para eficiencia operativa y SLA: expedientes estancados, backlog, cuellos de botella por ramo
> o tipo. Enseña que "demorado" = abierto (`pendiente`/`en_proceso`) **y** > 30 días desde la
> **denuncia** (no desde el siniestro). Muestra días promedio, máximo y monto expuesto. Generalizar a
> "por liquidador" agregando `s.liquidador_id` al GROUP BY.

```sql
SELECT
    r.nombre_ramo,
    s.tipo_siniestro,
    COUNT(*)                                                       AS cantidad,
    ROUND(AVG(DATEDIFF(CURRENT_DATE(), s.fecha_denuncia)))         AS dias_prom_espera,
    MAX(DATEDIFF(CURRENT_DATE(), s.fecha_denuncia))                AS max_dias,
    SUM(s.monto_siniestro)                                         AS monto_expuesto_ars
FROM genie_workshop.sancor.siniestros s
JOIN genie_workshop.sancor.polizas p ON s.poliza_id = p.poliza_id
JOIN genie_workshop.sancor.ramos r   ON p.ramo_id   = r.ramo_id
WHERE s.estado IN ('pendiente', 'en_proceso')
  AND DATEDIFF(CURRENT_DATE(), s.fecha_denuncia) > 30
GROUP BY r.nombre_ramo, s.tipo_siniestro
ORDER BY cantidad DESC;
```

## 3.4 · Clientes sin siniestros (oportunidad de cross-sell)

**Pregunta:** ¿Qué clientes nunca tuvieron un siniestro y tienen pólizas vigentes?

**Guía de intención (user guidance):**
> Usar para oportunidades comerciales: cross-sell, up-sell, clientes de bajo riesgo, campañas de
> fidelización. Enseña el patrón **anti-join** (`LEFT JOIN ... WHERE s.siniestro_id IS NULL`) para
> "nunca tuvo X". Ordena por prima total para priorizar a los clientes de mayor valor. Generalizar a
> "clientes de bajo riesgo con score alto" agregando `c.score_crediticio >= 750`.

```sql
SELECT
    c.nombre || ' ' || c.apellido   AS cliente,
    c.provincia,
    c.canal_captacion,
    COUNT(DISTINCT p.poliza_id)     AS polizas_activas,
    SUM(p.prima_anual)              AS prima_total_ars
FROM genie_workshop.sancor.clientes c
JOIN genie_workshop.sancor.polizas p
    ON c.cliente_id = p.cliente_id
   AND p.estado = 'vigente'
LEFT JOIN genie_workshop.sancor.siniestros s ON p.poliza_id = s.poliza_id
WHERE s.siniestro_id IS NULL
GROUP BY c.cliente_id, c.nombre, c.apellido, c.provincia, c.canal_captacion
ORDER BY prima_total_ars DESC
LIMIT 30;
```

## 3.5 · Resumen ejecutivo de cartera (pregunta WOW / P12)

**Pregunta:** Dame un resumen del estado de la cartera: pólizas vigentes, prima total, ramo con mayor siniestralidad y productores en riesgo.

**Guía de intención (user guidance):**
> Es la pregunta multi-parte de cierre. Enseña a Genie que puede componer varias métricas en una sola
> respuesta ejecutiva. No es necesario que replique este SQL exacto: sirve como patrón de "vista 360"
> que combina las medidas y filtros ya definidos. Si Genie descompone la pregunta en varias consultas,
> también es correcto — mostrarlo como fortaleza frente a un dashboard estático.

```sql
SELECT
    (SELECT COUNT(*)  FROM genie_workshop.sancor.polizas WHERE estado = 'vigente')          AS polizas_vigentes,
    (SELECT SUM(prima_anual) FROM genie_workshop.sancor.polizas WHERE estado = 'vigente')   AS prima_vigente_ars,
    (SELECT COUNT(*)  FROM genie_workshop.sancor.polizas WHERE estado = 'vencida')          AS polizas_vencidas,
    (SELECT COUNT(*)  FROM genie_workshop.sancor.siniestros
       WHERE estado IN ('pendiente','en_proceso')
         AND DATEDIFF(CURRENT_DATE(), fecha_denuncia) > 30)                                 AS siniestros_fuera_sla,
    (SELECT COUNT(*)  FROM genie_workshop.sancor.productores WHERE tasa_retencion < 0.50)   AS productores_criticos;
```

### 🧪 Pruébalo en Genie (después de agregar los example queries)
- *"¿Qué ramos superan el 70% de siniestralidad en los últimos 12 meses?"* → reutiliza el patrón de §3.1 (esperado: Incendio y Agrícola).
- *"Muestra los productores con cartera crítica que operan en el interior"* → generaliza §3.2 sumando el filtro de zona interior.

---

# 4 · SQL Functions (funciones UC de negocio — trusted assets)

Las 5 funciones de `03_uc_functions.sql` deben **agregarse al espacio** en
**Instructions → SQL functions**. Genie las invoca automáticamente con los parámetros que el usuario
provee, devolviendo respuestas **verificadas** para lógica de negocio crítica (no la improvisa).

> ⚠️ **Requisito de Genie:** las funciones UC deben declararse con `RETURNS TABLE(...)`.
> Las funciones escalares (que retornan `DOUBLE`, `INT`, `STRING`, etc.) generan el error
> *"You must select a function that returns a table"* y no pueden agregarse a Genie.
> Las funciones de `03_uc_functions.sql` ya están actualizadas como TVF.

| Función UC | Qué calcula | Ejemplos de prompt que la disparan |
|------------|-------------|------------------------------------|
| `calcular_indice_siniestralidad(p_nombre_ramo, p_meses_atras)` | Ratio siniestros/primas + nivel de riesgo por ramo | "siniestralidad de Automotores en 12 meses", "loss ratio de Hogar" |
| `calcular_score_riesgo_cliente(p_cliente_id)` | Score de riesgo 0–100 + nivel del cliente | "riesgo del cliente 123", "¿es un cliente de alto riesgo?" |
| `clasificar_estado_cartera(p_productor_id)` | Saludable / En seguimiento / En riesgo / Crítico + detalle de pólizas | "estado de cartera del productor 5", "¿está en riesgo su cartera?" |
| `proyectar_renovaciones(p_productor_id, p_meses)` | Renovaciones probables a N meses con tasa de retención | "renovaciones proyectadas de la red a 3 meses", "forecast de cartera" |
| `get_tiempo_promedio_resolucion(p_tipo_siniestro, p_ramo_nombre)` | Días promedio de resolución + estado vs SLA | "tiempo promedio de resolución de robos en Automotores", "demora de siniestros de Hogar" |

> **Cómo agregarlas:** en la UI del Genie Agent, *Instructions → SQL functions → Add* y seleccionar
> cada función del schema `genie_workshop.sancor`. Verifica que aparezcan las 5 antes del taller.

### 🧪 Pruébalo en Genie (después de agregar las funciones UC)
- *"¿Cuál es el índice de siniestralidad de Hogar en los últimos 6 meses?"* → invoca `calcular_indice_siniestralidad('Hogar', 6)`.
- *"¿En qué estado está la cartera del productor 5?"* → invoca `clasificar_estado_cartera(5)`.

---

# 5 · General Instructions (texto — último recurso)

Pegar en **Instructions → General instructions**. Todo este bloque cuenta como **1** instrucción.
Mantenerlo **corto y específico**: sólo jerga de negocio y comportamientos por defecto que **no**
estén ya cubiertos por metadatos, SQL expressions, joins o funciones.

```
CONTEXTO DEL NEGOCIO
Eres el asistente de datos de Sancor Seguros Argentina. El dominio es seguros patrimoniales y de
personas comercializados por una red de productores asesores. Todos los montos están en pesos
argentinos (ARS).

VOCABULARIO (sinónimos que no están en los comentarios de columnas)
- "asegurado", "asegurados", "tomador", "titular" = tabla clientes
- "productor", "agente", "asesor", "intermediario" = tabla productores
- "cartera" = conjunto de pólizas (de un productor, ramo o cliente, según el contexto)
- "ramo", "línea de negocio", "producto" = tabla ramos
- "cobertura", "contrato" = póliza
- "siniestro", "reclamo", "denuncia", "expediente", "claim" = tabla siniestros
- "índice de siniestralidad", "loss ratio", "tasa de siniestralidad" → usar función calcular_indice_siniestralidad o el example query de siniestralidad por ramo

REGLAS DE INTERPRETACIÓN
- SLA de resolución de siniestros: 15 días para siniestros simples, 30 días para complejos; más de 30 días es incumplimiento.
- Siniestralidad y montos de siniestros excluyen registros con estado 'rechazado', salvo que el usuario lo pida explícitamente.
- Al unir polizas con siniestros, no sumar prima_anual en el mismo join plano (fan-out): usar COUNT(DISTINCT poliza_id) o subconsultas separadas.

COMPORTAMIENTO POR DEFECTO
- Formato de dinero: pesos argentinos con separador de miles (ej: $1.250.000).
- Las tasas y ratios se muestran como porcentaje con 1 decimal (ej: 72,5%).
- Si una pregunta sobre siniestralidad o rentabilidad no especifica ventana de tiempo, asumir los últimos 12 meses y aclararlo en la respuesta.
- Si el usuario pide "top" o "principales" sin número, devolver el top 10.
- No exponer DNI ni email de clientes en las respuestas salvo pedido explícito y justificado.
- Al consultar productores, excluir siempre los dados de baja (activo = false), salvo que el usuario pida explícitamente el histórico completo.
- "Prima total de un cliente" se calcula sobre pólizas vigentes (estado = 'vigente'), no sobre el historial acumulado de todas las pólizas.
```

> Nota que este bloque **no** define estados de póliza, zonas ni filtros de negocio: esos ya viven como
> SQL expressions en §1B con sus sinónimos correspondientes — repetirlos aquí es redundante y genera
> conflictos. El texto solo aporta vocabulario de tabla, reglas de cálculo no expresables en SQL y
> comportamientos por defecto. Ese es el patrón correcto.

### 🧪 Pruébalo en Genie (después de agregar las instrucciones)
- *"¿Cuántos asegurados renovaron su póliza este año?"* → prueba el sinónimo **asegurados → clientes** (es la trampa B5: falla antes de agregar el sinónimo, funciona después).
- *"¿Cuánto suman las primas de la cartera activa?"* → prueba que "cartera activa" se interprete como `estado = 'vigente'` y que el monto se muestre en ARS con separador de miles.

---

# 6 · Base de Conocimiento en Unity Catalog Volume (RAG via Volumes)

Creada en `06_rag_knowledge_base.py`. Permite a Genie responder preguntas sobre coberturas,
exclusiones y procedimientos leyendo directamente documentos internos de Sancor almacenados
en un Volume, con búsqueda semántica nativa — sin necesidad de funciones SQL ni tablas Delta.

**Volume:** `genie_workshop.sancor.base_conocimiento`

| Archivo | Contenido |
|---------|-----------|
| `sancor_coberturas_automotores.md` | Coberturas todo riesgo, exclusiones, primas por perfil |
| `sancor_coberturas_hogar.md` | Cobertura de inmueble y contenido, inhabilitación, exclusiones |
| `sancor_coberturas_agricola_y_comerciales.md` | Agrícola, RC, Transporte, Vida, Salud, Movilidad |
| `sancor_procedimientos_denuncia_siniestros.md` | Plazos, canales, documentación, rol del liquidador |
| `sancor_sla_tiempos_resolucion.md` | SLA por ramo, escalada, tiempos promedio 2026 |
| `sancor_renovacion_primas_tarifas.md` | Renovación automática, cancelación, cálculo de prima |

> **Cómo registrar el Volume en el Genie Agent (UI):**
> 1. Abrir el Genie Agent → pestaña **Sources** → **Add**
> 2. Seleccionar el Volume `genie_workshop.sancor.base_conocimiento`
> 3. Agregar descripción: *"Manual interno de Sancor Seguros: coberturas, exclusiones, procedimientos de denuncia, SLA, renovación y tarifas."*
> 4. Guardar

> **Límites del producto:** hasta 10 Volumes por agente; el agente recupera hasta 5 archivos
> por pregunta; máx. 500 archivos de 10 MB cada uno sin content search indexing.

### 🧪 Pruébalo en Genie (después de registrar el Volume)
- *"¿Qué no cubre el seguro de Automotores?"* → Genie lee `sancor_coberturas_automotores.md` → respuesta verificada.
- *"¿Cómo denuncio una granizada?"* → Genie lee `sancor_procedimientos_denuncia_siniestros.md` → procedimiento paso a paso.
- *"¿Cuánto tarda Sancor en resolver un siniestro?"* → Genie lee `sancor_sla_tiempos_resolucion.md` → tiempos oficiales por ramo.

---
