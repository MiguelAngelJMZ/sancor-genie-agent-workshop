# ============================================================
# Workshop Genie Agents — Sancor Seguros Argentina
# Script 06: Base de Conocimiento en Unity Catalog Volume
# Ejecutar en un Databricks notebook (Python)
# Prerequisito: haber ejecutado 00_setup.sql
#
# Implementa el patrón RAG via Volumes:
#   1. Crea un UC Volume en genie_workshop.sancor
#   2. Escribe los archivos de conocimiento (.md) en el Volume
#   3. El Volume se registra en el Genie Agent como "Source"
#      desde la UI: Sources → Add → seleccionar el Volume
#
# Fuente del contenido: resources/base_conocimiento_seguros.md
# Documentación: docs.databricks.com/aws/en/genie-agents/volumes
# ============================================================

CATALOG = "genie_workshop"
SCHEMA  = "sancor"
VOLUME  = "base_conocimiento"
BASE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

# ── 1. Crear el Volume ────────────────────────────────────────────────────────

spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
print(f"✓ Volume: {CATALOG}.{SCHEMA}.{VOLUME}")
print(f"  Ruta:    {BASE_PATH}")

# ── 2. Contenido por archivo ──────────────────────────────────────────────────
# Cada archivo tiene un nombre descriptivo para que Genie identifique
# su contenido sin leerlo completo. Se recuperan hasta 5 archivos por pregunta.

archivos = {}

# ── Archivo 1: Coberturas Automotores ─────────────────────────────────────────
archivos["sancor_coberturas_automotores.md"] = """
# Coberturas — Ramo Automotores
## Sancor Seguros Argentina

### ¿Qué cubre la cobertura todo riesgo en Automotores?
La cobertura todo riesgo cubre daño propio (colisiones, vuelco, incendio), robo total
y parcial del vehículo, y Responsabilidad Civil Obligatoria (RCO) hacia terceros.
Incluye asistencia mecánica en ruta las 24 hs y auto de reemplazo por hasta 10 días
hábiles en caso de siniestro cubierto.

### ¿Qué diferencia hay entre cobertura básica, media y todo riesgo?
- **Cobertura básica (RC):** cubre únicamente daños a terceros.
- **Cobertura media:** suma robo total del vehículo.
- **Cobertura todo riesgo:** agrega daño propio y robo parcial.
Las primas aumentan progresivamente según la amplitud de la cobertura elegida.

### ¿Qué no cubre el seguro de Automotores?
Quedan excluidos: conducción bajo efecto de alcohol (>0,5 g/l) o estupefacientes;
daños intencionales; uso del vehículo fuera de la categoría declarada (ej. uso
comercial en póliza de uso particular); participación en competencias deportivas;
desgaste mecánico por uso normal; pérdida de valor por antigüedad del vehículo.

### Factores que aumentan la prima de Automotores
Mayor valor del vehículo, zonas de alta siniestralidad (CABA, GBA, Rosario,
Córdoba capital), vehículos de alta gama o alta demanda por robo, conductores
menores de 25 años o mayores de 70, historial con siniestros en los últimos
3 años, uso comercial del vehículo.

### ¿Puedo cambiar la cobertura al renovar?
Sí. En cada renovación el asegurado puede ampliar o reducir la cobertura,
actualizar la suma asegurada por inflación, agregar coberturas complementarias
o modificar datos del riesgo (domicilio, uso, conductores). Los cambios deben
solicitarse antes del vencimiento.
""".strip()

# ── Archivo 2: Coberturas Hogar ───────────────────────────────────────────────
archivos["sancor_coberturas_hogar.md"] = """
# Coberturas — Ramo Hogar
## Sancor Seguros Argentina

### ¿Qué bienes cubre el seguro de Hogar?
El seguro de Hogar cubre la estructura del inmueble y, opcionalmente, su contenido
(electrodomésticos, electrónica, mobiliario) contra incendio, robo con violencia,
daño por agua proveniente de cañerías internas, rotura de vidrios y daños por
granizo o tormenta. El contenido se asegura con suma asegurada independiente.

### ¿El seguro de Hogar cubre alquiler si la vivienda queda inhabitable?
Sí. Si la vivienda queda inhabitable como consecuencia directa de un siniestro
cubierto (incendio, inundación por cañería), Sancor reembolsa el gasto de
alquiler temporario por hasta 90 días corridos, con un límite equivalente al
10% de la suma asegurada del inmueble. Aplica exclusivamente para la vivienda
principal declarada en la póliza.

### Exclusiones del seguro de Hogar
No se cubren: desgaste natural o falta de mantenimiento del inmueble; robo sin
signos de violencia o fractura; inundaciones por desborde de ríos o canales
(salvo cobertura especial contratada); daños durante obras de refacción o
ampliación; daños causados por animales domésticos del asegurado.
""".strip()

# ── Archivo 3: Coberturas Agrícola y Ramos Comerciales ────────────────────────
archivos["sancor_coberturas_agricola_y_comerciales.md"] = """
# Coberturas — Ramos Agrícola, Responsabilidad Civil, Transporte y Otros
## Sancor Seguros Argentina

## Agrícola

### ¿Qué cultivos cubre el seguro Agrícola de Sancor?
Soja, maíz, girasol, trigo, sorgo, arroz, cebada y avena. Los cultivos intensivos
(frutales, hortalizas, viñedos) tienen coberturas específicas con tarifario
diferenciado. Consultar el tarifario vigente antes de emitir.

### ¿Qué riesgos cubre el seguro Agrícola?
La cobertura básica cubre granizo. Como coberturas complementarias opcionales:
helada, incendio e inundación. La suma asegurada se define en pesos por hectárea
según cultivo, zona agroclimática y rendimiento histórico del establecimiento.

### Exclusiones Agrícola
Negligencia en labores culturales, enfermedades fúngicas o plagas, sequía (salvo
cobertura complementaria contratada), siniestros fuera del período de cobertura
declarado, helada en cultivos no incluidos en la póliza.

### Prima del seguro Agrícola
La prima se calcula por hectárea según: cultivo, zona agroclimática por índice
histórico de granizo (mapa actualizado anualmente), suma asegurada por hectárea
y coberturas complementarias. Zonas del NOA y NEA presentan primas menores.

## Responsabilidad Civil
Cubre la obligación legal de indemnizar a terceros por daños materiales o lesiones
causados en el ejercicio de la actividad o uso de bienes del asegurado.
Incluye costos de defensa jurídica hasta el límite de suma asegurada.

## Transporte de Mercaderías
Cubre mercaderías en tránsito contra pérdida total, daño parcial por accidente
del transporte, robo con violencia, volcamiento y daños climáticos dentro de
Argentina. Puede extenderse a importaciones y exportaciones.

## Vida y Accidentes Personales
- **Vida:** abona el capital asegurado al beneficiario ante el fallecimiento por
  cualquier causa (enfermedad o accidente), salvo exclusiones expresas.
- **Accidentes Personales:** cubre solo muerte o invalidez permanente como
  consecuencia directa de un accidente externo, súbito y violento. Primas menores.

## Salud
Cubre internación, cirugías, estudios diagnósticos, medicación hospitalaria y
honorarios médicos. Complementa la obra social o prepaga del asegurado.

## Movilidad Urbana
Cubre bicicletas y monopatines eléctricos contra robo total, daño propio por
accidente y Responsabilidad Civil hacia terceros.
""".strip()

# ── Archivo 4: Procedimientos de Denuncia ─────────────────────────────────────
archivos["sancor_procedimientos_denuncia_siniestros.md"] = """
# Procedimientos de Denuncia de Siniestros
## Sancor Seguros Argentina

### ¿Cómo y en qué plazo hay que denunciar un siniestro?
La denuncia debe realizarse dentro de los **3 días hábiles** desde el momento
en que el asegurado tomó conocimiento del siniestro. Canales disponibles:
- Línea gratuita 0800-333-SANCOR (disponible 24/7 los 365 días)
- Portal web: sancor.com.ar/siniestros
- Aplicación móvil Sancor Seguros (iOS y Android)
- A través del productor asesor

La denuncia extemporánea no invalida la cobertura si se acredita causa justificada.

### Siniestros de Automotores — Documentación requerida
Cédula verde, DNI del asegurado y todos los conductores, licencia de conducir
vigente. En choque con terceros: datos del otro vehículo (nombre, DNI, patente,
seguro). En robo: denuncia policial obligatoria dentro de las 24 horas del hecho.

### Siniestros Agrícolas — Denuncia de granizada
Dentro de las **48 horas** de ocurrida la tormenta, comunicarse al 0800 o portal
web. Un perito agrícola visitará el campo en un plazo de 5 días hábiles.
**Importante:** no iniciar cosecha ni resiembra hasta que el perito haya realizado
la inspección y emitido el acta de daños.

### Siniestros de Hogar — Robo en vivienda
1. Realizar denuncia policial de inmediato (911 o comisaría del área).
2. Comunicar a Sancor dentro de las 24 horas.
3. Preparar inventario detallado de bienes robados con facturas de compra.
4. No alterar el lugar del siniestro hasta la visita del liquidador.
5. Conservar toda evidencia (fotografías, videos, cerraduras forzadas).

### ¿Qué es un liquidador y cuál es su rol?
El liquidador (o perito) es el profesional designado por Sancor para evaluar el
daño, verificar la cobertura y determinar el monto de la indemnización. Su informe
técnico es la base para la resolución del siniestro. Sancor cuenta con una red de
40 liquidadores (LIQ001 a LIQ040) distribuidos en todo el país.
""".strip()

# ── Archivo 5: SLA y Tiempos de Resolución ────────────────────────────────────
archivos["sancor_sla_tiempos_resolucion.md"] = """
# SLA y Tiempos de Resolución de Siniestros
## Sancor Seguros Argentina

### ¿Cuánto tarda Sancor en resolver un siniestro?
El objetivo de nivel de servicio (SLA) de Sancor es:
- **15 días hábiles** para siniestros simples (daños parciales menores, RC de
  bajo monto, robo de contenido hogareño).
- **30 días hábiles** para siniestros complejos (pérdidas totales, incendios
  estructurales, granizo agrícola de gran superficie, siniestros con litigios).

Los plazos se computan desde la recepción de la documentación completa,
no desde la denuncia inicial. Documentación incompleta suspende el SLA.

### Tiempos promedio por ramo (referencia 2026)

| Ramo | SLA estándar | Tiempo promedio |
|------|-------------|----------------|
| Vida | 30 días | ~22 días |
| Garantías | 30 días | ~17 días |
| Agrícola | 30 días | ~16 días |
| Hogar | 15 días | ~15 días |
| Automotores | 15 días | ~15 días |
| Responsabilidad Civil | 30 días | ~15 días |
| Accidentes Personales | 15 días | ~15 días |
| Incendio | 15 días | ~14 días |
| Embarcaciones | 15 días | ~14 días |

### ¿Qué pasa si Sancor no resuelve en el plazo prometido?
Los siniestros con más de 30 días sin resolución son escalados automáticamente
a la Gerencia de Siniestros. El productor asesor puede gestionar la escalada
desde el portal de productores. El asegurado puede exigir actualización formal
del estado del expediente.
""".strip()

# ── Archivo 6: Renovación, Cancelación, Primas y Tarifas ─────────────────────
archivos["sancor_renovacion_primas_tarifas.md"] = """
# Renovación, Cancelación, Primas y Tarifas
## Sancor Seguros Argentina

## Renovación de Pólizas

### ¿Cómo funciona la renovación automática?
Las pólizas anuales se renuevan automáticamente al vencimiento con la prima
actualizada. El asegurado recibe notificación por email 30 días antes.
Para cancelar la renovación, debe avisar con al menos **30 días de anticipación**.
Sin aviso previo, la póliza se considera tácitamente renovada.

### ¿Qué pasa si no se paga la prima en la renovación?
- A los **15 días** del vencimiento: póliza pasa a "suspendida" (sin cobertura).
- A los **30 días**: póliza cancelada definitivamente.
Para rehabilitar una póliza cancelada se debe emitir una nueva con evaluación
de riesgo actualizada.

## Primas y Tarifas

### ¿Cómo se calcula la prima de un seguro?
La prima surge de aplicar una tasa actuarial sobre la suma asegurada, ajustada
por factores de riesgo del bien, zona geográfica y perfil del asegurado. Los
productores acceden al cotizador online en el portal de productores.

### Exclusiones generales (todos los ramos)
Las siguientes causas quedan excluidas en todos los productos salvo pacto expreso:
- Hechos de guerra, conflicto armado o actos de terrorismo.
- Daños causados intencionalmente por el asegurado.
- Reacciones nucleares o contaminación radioactiva.
- Sismos y erupciones volcánicas (excepto en pólizas con cobertura especial).
""".strip()

# ── 3. Escribir archivos en el Volume ─────────────────────────────────────────

print(f"\nEscribiendo archivos en {BASE_PATH}...")
for nombre, contenido in archivos.items():
    ruta = f"{BASE_PATH}/{nombre}"
    dbutils.fs.put(ruta, contenido, overwrite=True)
    print(f"  ✓ {nombre}  ({len(contenido):,} bytes)")

# ── 4. Verificación ───────────────────────────────────────────────────────────

print(f"\nContenido del Volume:")
for f in dbutils.fs.ls(BASE_PATH):
    print(f"  {f.name:<55} {f.size:>8,} bytes")

print(f"""
✅ Volume listo: {CATALOG}.{SCHEMA}.{VOLUME}

PRÓXIMO PASO — Registrar el Volume en el Genie Agent (UI):
  1. Abrir el Genie Agent en el workspace
  2. Ir a la pestaña Sources → Add
  3. Seleccionar el Volume: {CATALOG}.{SCHEMA}.{VOLUME}
  4. Agregar descripción:
     "Manual interno de Sancor Seguros: coberturas por ramo, exclusiones,
      procedimientos de denuncia de siniestros, SLA, renovación y tarifas."
  5. Guardar

El agente recuperará hasta 5 archivos por pregunta usando búsqueda semántica.
""")
