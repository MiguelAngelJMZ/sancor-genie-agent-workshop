# ============================================================
# Workshop Genie Agents — Sancor Seguros Argentina
# Script 01: Generación de datos de muestra
# Ejecutar en un Databricks notebook (Python)
# Tiempo estimado: 2-3 minutos
# Prerequisito: haber ejecutado 00_setup.sql
# ============================================================

import random
from datetime import date, timedelta

random.seed(42)

CATALOG = "genie_workshop"
SCHEMA  = "sancor"
spark.sql(f"USE {CATALOG}.{SCHEMA}")

# ── Datos de referencia ────────────────────────────────────────────────────────

PROVINCIAS = [
    "Buenos Aires", "CABA", "Córdoba", "Santa Fe", "Mendoza",
    "Tucumán", "Entre Ríos", "Salta", "Misiones", "Chaco",
    "Corrientes", "Santiago del Estero", "San Juan", "Jujuy",
    "Río Negro", "Neuquén", "Formosa", "Chubut", "San Luis",
    "Catamarca", "La Rioja", "Santa Cruz", "Tierra del Fuego", "La Pampa",
]

# Pesos poblacionales aproximados para distribución realista
PROV_W = [28, 10, 12, 8, 5, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 2]

ZONAS = {
    "Buenos Aires": "Zona GBA",    "CABA": "Zona GBA",
    "Córdoba": "Zona Centro",      "Santa Fe": "Zona Centro",    "La Pampa": "Zona Centro",
    "Mendoza": "Zona Cuyo",        "San Juan": "Zona Cuyo",      "San Luis": "Zona Cuyo",
    "Tucumán": "Zona NOA",         "Salta": "Zona NOA",          "Jujuy": "Zona NOA",
    "Catamarca": "Zona NOA",       "La Rioja": "Zona NOA",       "Santiago del Estero": "Zona NOA",
    "Misiones": "Zona NEA",        "Chaco": "Zona NEA",          "Corrientes": "Zona NEA",
    "Formosa": "Zona NEA",         "Entre Ríos": "Zona NEA",
    "Neuquén": "Zona Patagonia",   "Río Negro": "Zona Patagonia","Chubut": "Zona Patagonia",
    "Santa Cruz": "Zona Patagonia","Tierra del Fuego": "Zona Patagonia",
}

NOMBRES_M = [
    "Juan", "Carlos", "Luis", "Miguel", "Roberto", "Diego", "Marcelo", "Pablo",
    "Alejandro", "Fernando", "Eduardo", "Jorge", "Gustavo", "Ricardo", "Daniel",
    "Sebastián", "Matías", "Nicolás", "Andrés", "Hernán", "Claudio", "Oscar",
    "Ramón", "Néstor", "Mario", "Sergio", "Raúl", "Hugo", "Alberto", "César",
]
NOMBRES_F = [
    "María", "Ana", "Laura", "Carolina", "Verónica", "Claudia", "Patricia", "Sandra",
    "Gabriela", "Silvina", "Natalia", "Valeria", "Florencia", "Romina", "Mariela",
    "Cecilia", "Lorena", "Alejandra", "Marcela", "Cristina", "Rosa", "Beatriz",
    "Mónica", "Liliana", "Susana", "Elena", "Isabel", "Graciela", "Nora", "Viviana",
]
APELLIDOS = [
    "García", "González", "Rodríguez", "Fernández", "López", "Martínez", "Pérez",
    "Sánchez", "Romero", "Torres", "Díaz", "Ramírez", "Morales", "Álvarez",
    "Gutiérrez", "Ruiz", "Herrera", "Medina", "Vega", "Castro", "Vargas",
    "Flores", "Reyes", "Cruz", "Ortega", "Molina", "Moreno", "Suárez",
    "Ramos", "Benítez", "Acosta", "Silva", "Rojas", "Núñez", "Ríos",
]

def gen_nombre():
    if random.random() < 0.55:
        return random.choice(NOMBRES_M), random.choice(APELLIDOS)
    return random.choice(NOMBRES_F), random.choice(APELLIDOS)

def slug(s):
    return (s.lower()
             .replace(" ", "").replace("á","a").replace("é","e")
             .replace("í","i").replace("ó","o").replace("ú","u")
             .replace("ñ","n"))

# ── Tabla: ramos ──────────────────────────────────────────────────────────────

print("Generando ramos...")
ramos = [
    (1,  "Automotores",        "AUT", "Cobertura de vehículos particulares y comerciales livianos",            200_000,  1_200_000),
    (2,  "Hogar",              "HOG", "Cobertura de vivienda y contenido contra incendio, robo e inundación",   80_000,    400_000),
    (3,  "Agrícola",           "AGR", "Cobertura de cultivos y maquinaria agrícola contra granizo y helada",   150_000,    800_000),
    (4,  "Accidentes Personales","ACP","Cobertura por accidentes que causan muerte o incapacidad",              50_000,    200_000),
    (5,  "Responsabilidad Civil","RC", "Cobertura frente a reclamos de terceros por daños materiales",         100_000,    500_000),
    (6,  "Embarcaciones",      "EMB", "Cobertura de embarcaciones deportivas y de trabajo",                    120_000,    600_000),
    (7,  "Garantías",          "GAR", "Garantías para obras públicas, privadas y aduaneras",                    80_000,    350_000),
    (8,  "Salud",              "SAL", "Cobertura de gastos médicos y hospitalización",                         150_000,    600_000),
    (9,  "Incendio",           "INC", "Cobertura contra incendio para establecimientos comerciales",           100_000,    700_000),
    (10, "Transporte",         "TRA", "Cobertura de mercaderías en tránsito",                                   90_000,    450_000),
    (11, "Vida",               "VID", "Seguro de vida individual y colectivo",                                  60_000,    300_000),
    (12, "Movilidad Urbana",   "MOV", "Cobertura para bicicletas y monopatines eléctricos",                    30_000,    120_000),
]

df_ramos = spark.createDataFrame(
    ramos,
    "ramo_id INT, nombre_ramo STRING, codigo_ramo STRING, descripcion STRING, prima_min_ars LONG, prima_max_ars LONG"
)
df_ramos.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.ramos")
print(f"  ✓ ramos: {df_ramos.count()} registros")

# ── Tabla: productores ────────────────────────────────────────────────────────

print("Generando productores...")
prod_prov = random.choices(PROVINCIAS, weights=PROV_W, k=150)
productores = []
for i in range(1, 151):
    nombre, apellido = gen_nombre()
    prov   = prod_prov[i - 1]
    zona   = ZONAS[prov]
    ret    = round(max(0.30, min(0.98, random.gauss(0.72, 0.15))), 3)
    anos   = random.randint(1, 25)
    email  = f"{slug(nombre)}.{slug(apellido)}{i}@productores.sancor.test"
    activo = random.random() < 0.92
    productores.append((i, nombre, apellido, email, prov, zona, ret, anos, activo))

df_prod = spark.createDataFrame(
    productores,
    "productor_id INT, nombre STRING, apellido STRING, email STRING, "
    "provincia STRING, zona STRING, tasa_retencion DOUBLE, anos_experiencia INT, activo BOOLEAN"
)
df_prod.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.productores")
print(f"  ✓ productores: {df_prod.count()} registros")

# ── Tabla: clientes ───────────────────────────────────────────────────────────

print("Generando clientes...")
cli_prov    = random.choices(PROVINCIAS, weights=PROV_W, k=4000)
CANALES     = ["Online", "Productor", "Autogestión", "WhatsApp", "Telefónico"]
CANAL_W     = [20, 45, 15, 12, 8]
base_nac    = date(1955, 1, 1)
base_alta   = date(2018, 1, 1)

clientes = []
for i in range(1, 4001):
    nombre, apellido = gen_nombre()
    prov  = cli_prov[i - 1]
    dni   = random.randint(20_000_000, 45_000_000)
    nac   = base_nac  + timedelta(days=random.randint(0, 365 * 50))
    alta  = base_alta + timedelta(days=random.randint(0, 365 * 7))
    canal = random.choices(CANALES, weights=CANAL_W)[0]
    score = random.randint(350, 950)
    clientes.append((i, nombre, apellido, dni, f"cli{i}@mail.test", prov,
                     nac, alta, canal, score))

df_cli = spark.createDataFrame(
    clientes,
    "cliente_id INT, nombre STRING, apellido STRING, dni LONG, email STRING, "
    "provincia STRING, fecha_nacimiento DATE, fecha_alta DATE, "
    "canal_captacion STRING, score_crediticio INT"
)
df_cli.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.clientes")
print(f"  ✓ clientes: {df_cli.count()} registros")

# ── Tabla: polizas ────────────────────────────────────────────────────────────

print("Generando polizas...")

# Distribución de ramos: Automotores domina (35%), luego Hogar (20%)
RAMO_DIST = (
    [1]*35 + [2]*20 + [3]*10 + [4]*10 + [5]*8 +
    [6]*3  + [7]*2  + [8]*4  + [9]*3  + [10]*2 + [11]*2 + [12]*1
)
ESTADOS_POL = ["vigente", "pendiente_renovacion", "vencida", "cancelada", "suspendida"]
ESTADO_W    = [65, 12, 13, 7, 3]
CANALES_V   = ["Online", "Productor", "Autogestión", "WhatsApp", "Telefónico"]
CANAL_V_W   = [20, 50, 15, 10, 5]

hoy       = date.today()
ramos_map = {r[0]: r for r in ramos}

polizas = []
for i in range(1, 8001):
    cli_id  = random.randint(1, 4000)
    prod_id = random.randint(1, 150)
    ramo_id = random.choice(RAMO_DIST)
    estado  = random.choices(ESTADOS_POL, weights=ESTADO_W)[0]
    duracion = 365 if random.random() < 0.85 else 730

    # Fechas ANCLADAS A HOY: el vencimiento se deriva del estado para que la
    # cartera sea coherente sin importar cuándo se ejecute el script. Esto evita
    # que todas las pólizas "venzan" con el paso del tiempo (antes se anclaban a
    # 2022 y hoy quedaban casi todas vencidas → sólo ~1% vigentes).
    if estado == "vigente":
        vencimiento = hoy + timedelta(days=random.randint(31, 365))
    elif estado == "pendiente_renovacion":
        vencimiento = hoy + timedelta(days=random.randint(1, 30))
    elif estado == "vencida":
        vencimiento = hoy - timedelta(days=random.randint(1, 300))
    else:  # cancelada / suspendida: el vencimiento puede ser pasado o futuro
        vencimiento = hoy + timedelta(days=random.randint(-300, 120))

    inicio = vencimiento - timedelta(days=duracion)

    ramo_row   = ramos_map[ramo_id]
    prima      = random.randint(ramo_row[4], ramo_row[5])
    suma_aseg  = prima * random.randint(8, 25)
    canal      = random.choices(CANALES_V, weights=CANAL_V_W)[0]

    polizas.append((i, cli_id, prod_id, ramo_id,
                    inicio, vencimiento,
                    estado, prima, suma_aseg, canal))

df_pol = spark.createDataFrame(
    polizas,
    "poliza_id INT, cliente_id INT, productor_id INT, ramo_id INT, "
    "fecha_inicio DATE, fecha_vencimiento DATE, estado STRING, "
    "prima_anual LONG, suma_asegurada LONG, canal_venta STRING"
)
df_pol.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.polizas")
print(f"  ✓ polizas: {df_pol.count()} registros")

# ── Tabla: siniestros ─────────────────────────────────────────────────────────

print("Generando siniestros...")

TIPOS_POR_RAMO = {
    1:  ["robo_total", "robo_parcial", "daño_propio", "responsabilidad_civil", "incendio"],
    2:  ["incendio", "robo", "inundacion", "daño_por_agua", "rotura_vidrios"],
    3:  ["granizo", "helada", "incendio", "inundacion", "viento"],
    4:  ["accidente_personal", "invalidez_parcial", "invalidez_total"],
    5:  ["daño_a_terceros", "lesiones_a_terceros"],
    6:  ["naufragio", "robo", "incendio", "colision"],
    7:  ["incumplimiento_contrato"],
    8:  ["hospitalizacion", "cirugia", "urgencia"],
    9:  ["incendio", "explosion", "daño_por_agua"],
    10: ["perdida_total", "daño_parcial", "robo"],
    11: ["fallecimiento", "invalidez_total"],
    12: ["robo", "daño_propio", "accidente"],
}
# Severidad del siniestro expresada como MÚLTIPLO de la prima anual de la póliza.
# Vincular el monto a la prima (en vez de rangos absolutos) mantiene el índice de
# siniestralidad (SUM siniestros / SUM primas) en rangos creíbles (~0.4 a ~1.1 por
# ramo) y realistas: las indemnizaciones escalan con el valor de la cobertura.
SEVERIDAD_POR_RAMO = {
    1:  (0.6, 4.5),   # Automotores
    2:  (0.5, 4.0),   # Hogar
    3:  (1.0, 6.0),   # Agrícola (siniestros grandes: granizo, helada)
    4:  (0.5, 3.5),   # Accidentes Personales
    5:  (0.6, 4.0),   # Responsabilidad Civil
    6:  (0.8, 5.0),   # Embarcaciones
    7:  (0.5, 3.5),   # Garantías
    8:  (0.4, 3.0),   # Salud
    9:  (0.8, 5.0),   # Incendio
    10: (0.6, 4.0),   # Transporte
    11: (1.0, 5.0),   # Vida
    12: (0.4, 3.0),   # Movilidad Urbana
}

ESTADOS_SIN = ["pendiente", "en_proceso", "resuelto", "rechazado"]
ESTADO_SIN_W = [12, 18, 62, 8]

# Solo pólizas históricamente activas pueden tener siniestros
ids_con_sin = [p[0] for p in polizas if p[6] in ("vigente", "vencida", "cancelada", "suspendida")]
random.shuffle(ids_con_sin)
ids_con_sin = ids_con_sin[:3200]

pol_map  = {p[0]: p for p in polizas}
sin_base = hoy - timedelta(days=730)   # siniestros de los últimos 24 meses

siniestros = []
sid = 1

for pol_id in ids_con_sin:
    if sid > 3400:
        break
    pol    = pol_map[pol_id]
    ramo_id = pol[3]
    n_sin  = random.choices([1, 2, 3], weights=[82, 14, 4])[0]

    for _ in range(n_sin):
        if sid > 3400:
            break
        tipo        = random.choice(TIPOS_POR_RAMO[ramo_id])
        sev_min, sev_max = SEVERIDAD_POR_RAMO[ramo_id]
        monto       = int(pol[7] * random.uniform(sev_min, sev_max))  # pol[7] = prima_anual
        estado      = random.choices(ESTADOS_SIN, weights=ESTADO_SIN_W)[0]
        fecha_sin   = sin_base + timedelta(days=random.randint(0, (hoy - sin_base).days))
        fecha_den   = fecha_sin + timedelta(days=random.randint(0, 3))

        fecha_res = None
        dias_res  = None

        if estado == "resuelto":
            dias_r = max(1, min(180, int(abs(random.gauss(16, 10)))))
            fr     = fecha_den + timedelta(days=dias_r)
            if fr <= hoy:
                fecha_res = fr
                dias_res  = dias_r
            else:
                estado = "en_proceso"
        elif estado == "rechazado":
            dias_r = random.randint(5, 25)
            fr     = fecha_den + timedelta(days=dias_r)
            if fr <= hoy:
                fecha_res = fr
                dias_res  = dias_r

        liq = f"LIQ{random.randint(1, 40):03d}"
        siniestros.append((sid, pol_id, fecha_sin, tipo, monto,
                           estado, fecha_den, fecha_res, dias_res, liq))
        sid += 1

# Agregar siniestros pendientes > 30 días (necesarios para benchmark P6)
for _ in range(100):
    pol_id  = random.choice(ids_con_sin)
    pol     = pol_map[pol_id]
    ramo_id = pol[3]
    tipo    = random.choice(TIPOS_POR_RAMO[ramo_id])
    sev_min, sev_max = SEVERIDAD_POR_RAMO[ramo_id]
    monto   = int(pol[7] * random.uniform(sev_min, sev_max))  # pol[7] = prima_anual
    fecha_den = hoy - timedelta(days=random.randint(31, 120))
    siniestros.append((sid, pol_id, fecha_den - timedelta(days=1),
                       tipo, monto,
                       "pendiente", fecha_den, None, None,
                       f"LIQ{random.randint(1, 40):03d}"))
    sid += 1

df_sin = spark.createDataFrame(
    siniestros,
    "siniestro_id INT, poliza_id INT, fecha_siniestro DATE, "
    "tipo_siniestro STRING, monto_siniestro LONG, estado STRING, "
    "fecha_denuncia DATE, fecha_resolucion DATE, "
    "dias_resolucion INT, liquidador_id STRING"
)
df_sin.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.siniestros")
print(f"  ✓ siniestros: {df_sin.count()} registros")

print("\n✅ Dataset Sancor Seguros generado exitosamente.")
print(f"   Catálogo: {CATALOG}.{SCHEMA}")
print("   Próximo paso: ejecutar 02_metadata.sql")
