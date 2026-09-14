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
├── resources/
│   ├── knowledge_store_snippets.md  # Guía completa de curación del Knowledge Store
│   └── benchmark_questions.md       # 7 preguntas benchmark con SQL de referencia
├── agent/                         # Agente conversacional (componente separado)
└── agent-app/                     # Aplicación Databricks Apps (componente separado)
```

---

## Descripción de los scripts

### `00_setup.sql` — Configuración inicial
Crea el catálogo `genie_workshop`, el schema `sancor` y otorga los permisos
necesarios a todos los participantes del workspace.
**Ejecutar una vez como administrador antes del taller.**

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
00_setup.sql              → crear catálogo y permisos
01_data_generation.py     → generar las 5 tablas
02_metadata.sql           → aplicar comentarios y tags PII
03_uc_functions.sql       → crear las 5 funciones UC
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

## Componentes adicionales

Las carpetas `agent/` y `agent-app/` contienen componentes avanzados del taller
que se presentan en una etapa posterior, independiente de la configuración del
Genie Agent descrita en este README.
