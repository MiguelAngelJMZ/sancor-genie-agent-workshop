# Taller Genie Agent — Sancor Seguros Argentina

Workshop práctico para aprender a configurar y optimizar **Databricks Genie Agent**
usando un dataset sintético del sector seguros. El taller usa datos ficticios de
Sancor Seguros Argentina como dominio de negocio.

---

## Objetivo del taller

El taller sigue una metodología de mejora iterativa en dos etapas:

1. **Baseline:** conectar solo las 5 tablas al Genie Agent y ejecutar los 7
   benchmarks. Se observa qué preguntas Genie responde correctamente y cuáles no.

2. **Optimización por capas:** agregar el Knowledge Store capa por capa
   (SQL expressions → joins → example queries → UC functions → instrucciones →
   Volume de documentos) y volver a ejecutar los benchmarks después de cada capa
   para medir el impacto de cada mejora.

El mensaje central: **la calidad de Genie se construye por capas estructuradas,
no con instrucciones de texto libre**.

---

## Prerequisitos

- Acceso a un workspace de Databricks con Unity Catalog habilitado
- Permisos para crear catálogos, schemas y funciones UC
- SQL Warehouse disponible (Serverless recomendado)

---

## Estructura del repositorio

```
sancor-genie-workshop/
├── 00_setup.sql                   # Paso 1: configuración del entorno
├── 01_data_generation.py          # Paso 2: generación del dataset sintético ⭐
├── 02_metadata.sql                # Paso 3: comentarios y tags de PII en UC
├── 03_uc_functions.sql            # Paso 4: funciones de Unity Catalog (TVF)
├── 04_rls_policy.sql              # Paso 5: seguridad a nivel de filas (RLS)
├── 05_validation.sql              # Paso 6: validación del entorno antes del taller
├── 06_rag_knowledge_base.py       # Paso 7: base de conocimiento en UC Volume
├── 07_uc_functions_defaults.sql   # Paso 8: funciones UC con parámetros DEFAULT (agente custom)
└── resources/
    ├── knowledge_store_snippets.md  # Guía completa de curación del Knowledge Store
    └── benchmark_questions.md       # 7 preguntas benchmark con SQL de referencia
```

---

## Descripción de los scripts

### `00_setup.sql` — Configuración inicial
Crea el catálogo `genie_workshop` y el schema `sancor` en tu workspace.
**Ejecutar una vez antes de comenzar.**

### `01_data_generation.py` — Generación de datos ⭐
Genera el dataset sintético completo de Sancor Seguros con `random.seed(42)`
para resultados reproducibles:

| Tabla | Registros | Descripción |
|-------|-----------|-------------|
| `ramos` | 12 | Líneas de negocio (Automotores, Hogar, Agrícola, etc.) |
| `productores` | 150 | Red de productores asesores con zona y tasa de retención |
| `clientes` | 4.000 | Asegurados con provincia, score crediticio y canal de captación |
| `polizas` | 8.000 | Contratos de seguro con estado, prima y suma asegurada |
| `siniestros` | ~3.500 | Reclamos con SLA y liquidador asignado |

**Este es el único script que los participantes pueden ejecutar por su cuenta**
desde un notebook de Databricks antes o durante el taller.

### `02_metadata.sql` — Metadatos y comentarios
Agrega descripciones a todas las tablas y columnas en Unity Catalog, incluyendo
tags de PII (`NAME`, `SSN`, `EMAIL`) en la tabla `clientes`.
Esta es la capa de mayor impacto para la calidad de Genie.

### `03_uc_functions.sql` — Funciones UC (TVF)
Crea 5 funciones de Unity Catalog que encapsulan lógica de negocio compleja.
Todas usan `RETURNS TABLE` (TVF) porque Genie Agent solo acepta funciones
que retornan tabla — las funciones escalares generan el error
*"You must select a function that returns a table"*.

| Función | Qué calcula |
|---------|-------------|
| `calcular_indice_siniestralidad` | Ratio siniestros/primas por ramo y ventana temporal |
| `calcular_score_riesgo_cliente` | Score de riesgo 0–100 basado en historial de siniestros |
| `clasificar_estado_cartera` | Estado de cartera de productores (Saludable → Crítico) |
| `proyectar_renovaciones` | Forecast de renovaciones a N meses |
| `get_tiempo_promedio_resolucion` | Tiempo promedio de resolución de siniestros vs SLA |

### `04_rls_policy.sql` — Seguridad a nivel de filas
Configura Row-Level Security en la tabla `polizas` para que cada productor
vea únicamente su propia cartera al consultar Genie. Los administradores
del workspace ven toda la información.
**Nota:** volver a ejecutar este script cada vez que se regeneren los datos.

### `05_validation.sql` — Validación pre-taller
Script de verificación para ejecutar el día anterior al taller. Valida
conteos de tablas, integridad referencial, cobertura de metadatos,
funciones UC registradas y datos suficientes para cada benchmark.
Un ✓ en cada fila indica que el entorno está listo.

### `06_rag_knowledge_base.py` — Base de conocimiento en Volume
Crea el UC Volume `genie_workshop.sancor.base_conocimiento` y escribe
6 archivos Markdown con el manual interno de Sancor Seguros (coberturas,
exclusiones, procedimientos, SLA, renovación y tarifas).

El Volume se registra luego en el Genie Agent como **Source** desde la UI:
*Sources → Add → seleccionar el Volume → agregar descripción*.
Genie usa búsqueda semántica sobre estos documentos para responder
preguntas cualitativas sobre productos y procedimientos.

### `07_uc_functions_defaults.sql` — Funciones UC con parámetros DEFAULT
Recrea las funciones `calcular_indice_siniestralidad`, `proyectar_renovaciones` y
`get_tiempo_promedio_resolucion` declarando `DEFAULT NULL`/`DEFAULT 12` en sus parámetros.
Necesario para el **agente custom** (Parte 2): su ejecutor no admite `None` en un parámetro
requerido, así que los DEFAULT vuelven opcionales los filtros y el modelo puede omitirlos al
pedir agregados. Cambio retrocompatible: Genie y las llamadas existentes siguen igual.

---

## Recursos del taller

### `resources/knowledge_store_snippets.md`
Guía completa de curación del Knowledge Store, organizada por capas:
SQL expressions (medidas, filtros, dimensiones), join relationships,
example queries, UC functions e instrucciones de texto.
**Contiene el contenido listo para copiar y pegar en la UI de Genie.**

### `resources/benchmark_questions.md`
7 preguntas benchmark con su SQL de referencia verificado y el resultado
exacto esperado. Se usan para medir la calidad de Genie antes y después
de cada capa de curación.

| Benchmark | Capa que desbloquea |
|-----------|---------------------|
| B1 — Siniestros pendientes | Metadatos (baseline) |
| B2 — Siniestros fuera de SLA por tipo | SQL expressions |
| B3 — Top 5 provincias pólizas agrícolas | Join relationships |
| B4 — Ramos con siniestralidad > 70% | Example queries / UC functions |
| B5 — Top 10 productores con más vencidas | Example query §3.2 |
| B6 — Top clientes por prima (sin PII) | Gobernanza / PII tags |
| B7 — Tiempo promedio de resolución por ramo | Medidas + joins |

---

## Flujo de ejecución

### Preparación (instructor — antes del taller)

```
00_setup.sql              → crear catálogo y schema
01_data_generation.py     → generar las 5 tablas
02_metadata.sql           → aplicar comentarios y tags PII
03_uc_functions.sql       → crear las 5 funciones UC
07_uc_functions_defaults.sql → parámetros DEFAULT (necesario para el agente custom)
04_rls_policy.sql         → activar RLS en polizas
06_rag_knowledge_base.py  → crear Volume con documentos
05_validation.sql         → verificar que todo esté listo ✓
```

### Durante el taller

1. Conectar las 5 tablas al Genie Agent (sin Knowledge Store)
2. Ejecutar los 7 benchmarks → anotar cuáles pasan
3. Agregar el Knowledge Store capa por capa siguiendo `knowledge_store_snippets.md`
4. Después de cada capa, volver a ejecutar los benchmarks relevantes
5. Comparar resultados antes vs. después

---

## Parte 2 — Del Genie al Agente Custom

En la segunda parte del taller pasamos de **Genie** (agente de datos gestionado) a un
**agente custom** (`ResponsesAgent`) desplegado en **Databricks Apps**. El objetivo es
mostrar cómo las mismas funciones UC que curamos para Genie se reutilizan como
**herramientas (tools)** de un agente, y cómo se extiende el agente con lógica que Genie
no puede hacer.

### Flujo general

```
AI Playground                     Databricks Apps                Código del agente
─────────────                     ───────────────                ─────────────────
Adjuntar las 5 funciones UC  ──►  Deploy del agente         ──►  Repo con agent_server/
como tools (solo lectura)         (botón "Deploy")               (lo que editamos a mano)
```

1. **En el Playground** se adjuntan las **5 funciones UC** como herramientas del agente.
2. Se hace **Deploy a Databricks Apps** desde el Playground.
3. Databricks genera el **código del agente** (estructura `agent_server/`), que es el que
   editamos para añadir capacidades que el Playground no ofrece.

### Paso 1 — Añadir las 5 herramientas + el prompt en el AI Playground

Las 5 funciones UC del script `03_uc_functions.sql` (con los DEFAULT del `07_...`) se
adjuntan como tools directamente desde la UI, **sin escribir código**:

1. Abrir **AI Playground** en el workspace.
2. Elegir un modelo con soporte de tool calling (p. ej. *Claude Opus*).
3. En **Tools → Add tool → Unity Catalog function**, buscar y agregar cada una:
   - `genie_workshop.sancor.calcular_indice_siniestralidad`
   - `genie_workshop.sancor.calcular_score_riesgo_cliente`
   - `genie_workshop.sancor.clasificar_estado_cartera`
   - `genie_workshop.sancor.proyectar_renovaciones`
   - `genie_workshop.sancor.get_tiempo_promedio_resolucion`
4. Pegar el **system prompt inicial** (solo lectura) en el campo de instrucciones del
   agente. Este es el prompt de la primera etapa; en el Paso 2 lo ampliaremos:

   ```text
   Eres el asistente analítico de Sancor Seguros Argentina. Respondes preguntas de negocio
   SOBRE DATOS consultando exclusivamente las herramientas disponibles; nunca inventas cifras.
   Si una pregunta no se puede responder con las herramientas, dilo con claridad en lugar de
   estimar.

   Reglas de uso:
   - Elige la herramienta adecuada según la intención: siniestralidad/rentabilidad de ramos,
     score de riesgo de un cliente, estado de cartera de un productor, proyección de
     renovaciones, o tiempos de resolución/SLA de siniestros.
   - Para un agregado de TODOS los ramos/tipos, invoca la herramienta UNA sola vez omitiendo
     ese parámetro (devuelve una fila por categoría). No repitas la misma llamada.
   - Responde en español, claro y ejecutivo. Cuando la herramienta devuelva números, cítalos
     con su unidad (ARS, %, días) y añade una breve interpretación.

   Gobernanza:
   - No expongas datos personales (DNI, email) de clientes salvo que sea imprescindible y esté
     justificado; prioriza rankings y agregados.
   - La seguridad a nivel de filas (RLS) del workspace se aplica automáticamente: un productor
     solo ve su propia cartera. No intentes eludirla.
   - Ante preguntas ambiguas (p. ej. "el mejor productor"), pide que se aclare la métrica antes
     de responder.
   ```
5. Probar el agente en el chat del Playground (p. ej. *"¿siniestralidad por ramo?"*).
6. **Deploy → Databricks Apps.** Esto genera el código del agente y la app.

> Las 5 son funciones `RETURNS TABLE` de **solo lectura**, por eso el Playground las puede
> adjuntar tal cual. Todo el trabajo vive en Unity Catalog; el agente solo las invoca.
>
> **Escala del taller:** en esta etapa el agente **solo consulta**. En el Paso 2 le añadimos
> una herramienta de **escritura** (ingesta de siniestros) y **ampliamos este mismo prompt**
> con las reglas para usarla.

### Paso 2 — Añadir una herramienta de ESCRITURA (por código)

Ahora agregamos una herramienta que **registra (ingesta) un nuevo siniestro** —
`registrar_siniestro`. Esta **no se puede añadir por el Playground**:

> ⚠️ **Las funciones UC de SQL son de solo lectura: no pueden hacer `INSERT`/`UPDATE`.**
> Por eso una operación de **escritura** no puede ser una función UC ni adjuntarse desde el
> Playground. Se implementa como **tool local en Python** dentro del código del agente, que
> ejecuta el `INSERT` contra un **SQL warehouse** vía la *Statement Execution API*.

Sobre el código generado (estructura `agent_server/`) hay que tocar **4 lugares**:

| # | Archivo | Cambio |
|---|---------|--------|
| 1 | `agent_server/tools.py` *(nuevo)* | Definir la tool `registrar_siniestro` |
| 2 | `agent_server/agent.py` | Importar la tool, registrarla en el `Agent` y ampliar el system prompt |
| 3 | `app.yaml` *(deploy)* | Env var `SQL_WAREHOUSE_ID` + adjuntar el SQL warehouse (`CAN_USE`) |
| 4 | `.env` *(local)* | `SQL_WAREHOUSE_ID` para desarrollo local |

#### 2.1 — Crear `agent_server/tools.py`

```python
"""Herramientas locales (client-side function tools) del agente.

A diferencia de las funciones UC de solo lectura expuestas por MCP, aquí viven
las operaciones de ESCRITURA. Las funciones UC de SQL no pueden hacer INSERT, así
que la ingesta de un siniestro se implementa como una tool local que ejecuta la
sentencia contra un SQL warehouse vía la Statement Execution API del SDK.
"""

import asyncio
import os
import time
from typing import Optional

from agents import function_tool
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

CATALOG = "genie_workshop"
SCHEMA = "sancor"
TABLE_SINIESTROS = f"{CATALOG}.{SCHEMA}.siniestros"
TABLE_POLIZAS = f"{CATALOG}.{SCHEMA}.polizas"

_PENDING = (StatementState.PENDING, StatementState.RUNNING)


def _execute(statement: str, parameters: Optional[list] = None):
    """Ejecuta una sentencia SQL y espera a que termine. Lanza en caso de error."""
    warehouse_id = os.environ.get("SQL_WAREHOUSE_ID")
    if not warehouse_id:
        raise RuntimeError(
            "SQL_WAREHOUSE_ID no está configurado. Define el warehouse en .env "
            "(local) o en databricks.yml (deploy) para poder escribir siniestros."
        )
    w = WorkspaceClient()
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        parameters=parameters,
        wait_timeout="50s",
    )
    # Si el warehouse estaba frío puede seguir corriendo tras el wait_timeout: sondear.
    while resp.status and resp.status.state in _PENDING:
        time.sleep(1)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if not resp.status or resp.status.state != StatementState.SUCCEEDED:
        detail = (
            resp.status.error.message
            if resp.status and resp.status.error
            else "estado desconocido"
        )
        raise RuntimeError(f"La sentencia SQL no se completó: {detail}")
    return resp


def _scalar(resp) -> Optional[str]:
    if resp.result and resp.result.data_array:
        return resp.result.data_array[0][0]
    return None


def _registrar_siniestro_sync(poliza_id, tipo_siniestro, fecha_siniestro, monto_siniestro):
    # 1. Validar que la póliza exista antes de escribir.
    check = _execute(
        f"SELECT COUNT(*) FROM {TABLE_POLIZAS} WHERE poliza_id = :poliza_id",
        [StatementParameterListItem(name="poliza_id", value=str(poliza_id), type="INT")],
    )
    if (_scalar(check) or "0") == "0":
        return (
            f"No se registró ningún siniestro: la póliza {poliza_id} no existe en el "
            f"sistema. Verificá el número de póliza con el usuario."
        )

    # 2. Asignar el próximo siniestro_id (la tabla no es auto-incremental).
    nxt = _execute(f"SELECT COALESCE(MAX(siniestro_id), 0) + 1 FROM {TABLE_SINIESTROS}")
    new_id = int(_scalar(nxt))

    # 3. Insertar la denuncia en estado 'pendiente', con fecha de denuncia = hoy.
    params = [
        StatementParameterListItem(name="sid", value=str(new_id), type="INT"),
        StatementParameterListItem(name="pid", value=str(poliza_id), type="INT"),
        StatementParameterListItem(name="fecha", value=fecha_siniestro, type="DATE"),
        StatementParameterListItem(name="tipo", value=tipo_siniestro, type="STRING"),
    ]
    if monto_siniestro is None:
        monto_sql = "NULL"
    else:
        monto_sql = ":monto"
        params.append(
            StatementParameterListItem(name="monto", value=str(monto_siniestro), type="BIGINT")
        )

    _execute(
        f"""INSERT INTO {TABLE_SINIESTROS}
                (siniestro_id, poliza_id, fecha_siniestro, tipo_siniestro, monto_siniestro,
                 estado, fecha_denuncia, fecha_resolucion, dias_resolucion, liquidador_id)
            VALUES
                (:sid, :pid, :fecha, :tipo, {monto_sql},
                 'pendiente', CURRENT_DATE(), NULL, NULL, NULL)""",
        params,
    )

    monto_txt = f"{monto_siniestro:,} ARS" if monto_siniestro is not None else "sin monto informado"
    return (
        f"Siniestro registrado con éxito. Nº de expediente (siniestro_id): {new_id}. "
        f"Póliza {poliza_id}, tipo '{tipo_siniestro}', fecha del evento {fecha_siniestro}, "
        f"monto {monto_txt}. Estado inicial: pendiente; fecha de denuncia: hoy."
    )


@function_tool
async def registrar_siniestro(
    poliza_id: int,
    tipo_siniestro: str,
    fecha_siniestro: str,
    monto_siniestro: Optional[int] = None,
) -> str:
    """Registra (ingesta) la denuncia de un nuevo siniestro en la base de datos.

    IMPORTANTE: invoca esta herramienta SOLO después de haber recopilado y CONFIRMADO
    los datos con el usuario. La denuncia se crea en estado 'pendiente', con la fecha
    de denuncia = hoy y sin resolución todavía. El número de expediente (siniestro_id)
    se asigna automáticamente. La herramienta valida que la póliza exista antes de
    escribir; si no existe, no inserta nada.

    Args:
        poliza_id: ID de la póliza bajo la cual se denuncia el siniestro (debe existir).
        tipo_siniestro: Tipo de evento, p. ej. 'granizo', 'robo_total', 'colision'.
        fecha_siniestro: Fecha en que ocurrió el evento, en formato 'YYYY-MM-DD'.
        monto_siniestro: Monto estimado del siniestro en ARS. Opcional.

    Returns:
        Un mensaje con el siniestro_id asignado y el resumen, o un error si la póliza no existe.
    """
    return await asyncio.to_thread(
        _registrar_siniestro_sync, poliza_id, tipo_siniestro, fecha_siniestro, monto_siniestro
    )
```

> **¿Por qué `asyncio.to_thread`?** El agente corre en un loop asíncrono (`Runner.run`), pero
> las llamadas del SDK de Databricks son bloqueantes. Ejecutarlas en un thread evita frenar
> el loop.

#### 2.2 — Registrar la tool en `agent_server/agent.py`

Tres cambios pequeños:

```python
# (a) importar la tool, junto a los demás imports
from agent_server.tools import registrar_siniestro

# (b) registrarla en el Agent, junto a los mcp_servers de las 5 funciones UC
def create_agent(mcp_servers):
    return Agent(
        name=NAME,
        instructions=SYSTEM_PROMPT,
        model=MODEL,
        mcp_servers=mcp_servers,
        tools=[registrar_siniestro],   # ← herramienta local de escritura
    )
```

Y **(c)** ampliar el `SYSTEM_PROMPT` del Paso 1 **añadiendo** este bloque, para que el agente
sepa cuándo y cómo usar la nueva herramienta. Lo más importante es la **confirmación antes de
escribir**:

```text
Registro de siniestros (ESCRITURA con `registrar_siniestro`):
- Además de consultar, puedes REGISTRAR la denuncia de un nuevo siniestro.
- Antes de registrar, recopila y CONFIRMA con el usuario: poliza_id (obligatorio),
  tipo_siniestro (obligatorio), fecha del siniestro en formato AAAA-MM-DD (obligatorio)
  y monto en ARS (opcional).
- Muestra un resumen de lo que vas a registrar y espera una confirmación EXPLÍCITA
  ("sí", "confirmo") ANTES de llamar a la herramienta. Nunca inventes datos.
- La herramienta valida que la póliza exista, asigna el siniestro_id automáticamente y
  crea la denuncia en estado "pendiente". Tras registrar, informa el siniestro_id asignado.
```

#### 2.3 — Configurar el SQL warehouse en la app

Hacen falta **dos cosas**: (1) que el código conozca el warehouse vía la variable de entorno
`SQL_WAREHOUSE_ID`, y (2) que el *service principal* de la app tenga permiso para usarlo.

> ⚠️ **Gotcha clave (dónde va la variable de entorno).** Databricks Apps lee las env vars de
> **`app.yaml`**. Si desplegaste desde el **AI Playground** o con `databricks apps deploy` —el
> flujo de este taller—, **`app.yaml` es el archivo que se usa**, NO `databricks.yml`. Si solo
> agregas la variable a `databricks.yml` (que únicamente aplica cuando despliegas con
> `databricks bundle deploy`), la app arrancará **sin** `SQL_WAREHOUSE_ID` y la tool fallará con
> *"SQL_WAREHOUSE_ID no está configurado"*.

**a) Agregar la variable en `app.yaml`** (bajo `env:`), y **redeploy** la app:

```yaml
env:
  # ...las demás variables...
  - name: SQL_WAREHOUSE_ID
    value: "<tu_warehouse_id>"
```

**b) Adjuntar el SQL warehouse como recurso de la app** (para que el SP tenga `CAN_USE`).
Desde la UI de la app: *Edit → Resources → Add resource → SQL warehouse → CAN_USE*. Si usas
DABs, el equivalente en `databricks.yml` bajo `resources.apps.<app>.resources` es:

```yaml
        - name: 'sql-warehouse'
          sql_warehouse:
            id: '<tu_warehouse_id>'
            permission: 'CAN_USE'
```

> Si además despliegas con DABs, replica la variable en `databricks.yml` bajo
> `config.env` (mismo `name`/`value`). Adjuntar el recurso da el permiso; la env var le dice
> al código **cuál** warehouse usar — se necesitan **ambas**.

#### 2.4 — Variable local en `.env`

Para probar el agente localmente:

```bash
SQL_WAREHOUSE_ID=<tu_warehouse_id>
```

### Permisos de tabla para el deploy (importante)

En local funciona con tus credenciales (dueño del schema). Pero al desplegar, el *service
principal* de la app necesita permisos de Unity Catalog sobre las tablas — que **no** se
otorgan al adjuntar el warehouse. El *application ID* del SP aparece en la app:
*Overview → Service principal*. Ejecutar una vez tras el primer deploy (reemplazando
`<app-sp-application-id>`):

```sql
GRANT USE CATALOG ON CATALOG genie_workshop                    TO `<app-sp-application-id>`;
GRANT USE SCHEMA  ON SCHEMA  genie_workshop.sancor             TO `<app-sp-application-id>`;
GRANT SELECT          ON TABLE genie_workshop.sancor.polizas    TO `<app-sp-application-id>`;
GRANT SELECT, MODIFY  ON TABLE genie_workshop.sancor.siniestros TO `<app-sp-application-id>`;
```

> Sin estos grants, tras arreglar `SQL_WAREHOUSE_ID` el siguiente error sería de permisos
> (`PERMISSION_DENIED` al hacer el SELECT/INSERT). `MODIFY` es lo que habilita el `INSERT`.

### Probar la herramienta

```bash
# Levantar el agente localmente
uv run start-app

# Denuncia con confirmación explícita
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","content":"Registrá un siniestro para la póliza 1: granizo, 2026-09-10, monto 500000 ARS. Confirmo, procedé."}]}'
```

El agente debe llamar a `registrar_siniestro`, insertar la fila (estado `pendiente`,
`fecha_denuncia` = hoy) y responder con el `siniestro_id` asignado. Si la póliza no existe,
responde que no registró nada.

### Resumen didáctico: dos tipos de herramienta

| | Herramientas de LECTURA (las 5) | Herramienta de ESCRITURA (`registrar_siniestro`) |
|---|---|---|
| Implementación | Función UC (SQL `RETURNS TABLE`) | Tool local en Python (`@function_tool`) |
| Cómo se añade | **AI Playground** (sin código) | **Editando el código** del agente |
| Gobernanza | Unity Catalog (EXECUTE) | Warehouse `CAN_USE` + grants de tabla |
| Puede hacer `INSERT` | ❌ No | ✅ Sí (vía Statement Execution API) |

