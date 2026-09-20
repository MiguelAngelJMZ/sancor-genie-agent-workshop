# Databricks notebook source
# DBTITLE 1,Workshop MLOps End-to-End
# MAGIC %md
# MAGIC # Workshop: MLOps End-to-End en Databricks
# MAGIC ### Industria de Seguros — Sancor Seguros
# MAGIC
# MAGIC En este workshop recorreremos el **ciclo completo de MLOps** en Databricks, desde la exploración de datos hasta el monitoreo en producción.
# MAGIC
# MAGIC **Caso de uso:** Predecir si un siniestro (reclamo) será **rechazado** para priorizar la revisión de reclamos.
# MAGIC
# MAGIC | Paso | Tema | Herramienta Databricks |
# MAGIC | --- | --- | --- |
# MAGIC | 0 | Setup | `%pip install` |
# MAGIC | 1 | Exploración de Datos (EDA) | Spark SQL, PySpark |
# MAGIC | 2 | Feature Engineering | PySpark joins + transformaciones |
# MAGIC | 3 | Entrenamiento del Modelo | sklearn + MLflow Tracking |
# MAGIC | 4 | Evaluación del Modelo | Métricas, curvas ROC/PR |
# MAGIC | 5 | Registro en Unity Catalog | MLflow Model Registry |
# MAGIC | 6 | Despliegue en Model Serving | REST API endpoint |
# MAGIC | 7 | Feature Store | Feature Tables reutilizables |
# MAGIC | 8 | Batch Inference | `fe.score_batch` |
# MAGIC | 9 | Monitoreo | Inference Tables |
# MAGIC
# MAGIC **Schema:** `genie_workshop.sancor` — 5 tablas transaccionales (clientes, pólizas, siniestros, productores, ramos)

# COMMAND ----------

# DBTITLE 1,Configuración (widgets)
# Parámetros configurables — modificar sin tocar el código
dbutils.widgets.text("catalog", "genie_workshop", "Catalog")
dbutils.widgets.text("schema",  "sancor",          "Schema")
dbutils.widgets.text("endpoint_name", "rechazo-siniestros", "Endpoint Name")
dbutils.widgets.text("model_name", "rechazo_siniestros", "Model Name")

CATALOG        = dbutils.widgets.get("catalog")
SCHEMA         = dbutils.widgets.get("schema")
ENDPOINT_NAME  = dbutils.widgets.get("endpoint_name")
MODEL_NAME     = dbutils.widgets.get("model_name")

REGISTERED_MODEL = f"{CATALOG}.{SCHEMA}.{MODEL_NAME}"
FEATURE_TABLE    = f"{CATALOG}.{SCHEMA}.features_poliza"

print(f"Catalog:  {CATALOG}")
print(f"Schema:   {SCHEMA}")
print(f"Modelo:   {REGISTERED_MODEL}")
print(f"Endpoint: {ENDPOINT_NAME}")

# COMMAND ----------

# DBTITLE 1,Paso 0: Setup
# MAGIC %md
# MAGIC ## Paso 0: Setup
# MAGIC
# MAGIC Instalamos las dependencias necesarias. `databricks-feature-engineering` es requerido para trabajar con Feature Store en los pasos posteriores.
# MAGIC
# MAGIC > **Nota:** `dbutils.library.restartPython()` reinicia el kernel de Python. Todas las variables previas se pierden, por eso lo hacemos al inicio del notebook.

# COMMAND ----------

# DBTITLE 1,Instalar dependencias
# MAGIC %pip install databricks-feature-engineering --quiet

# COMMAND ----------

# DBTITLE 1,Reiniciar kernel de Python
# Necesario después de %pip install para que las nuevas librerías estén disponibles.
# Todas las variables previas se pierden — por eso ejecutamos esto al inicio.
dbutils.library.restartPython()

# COMMAND ----------

# Parámetros configurables — modificar sin tocar el código
dbutils.widgets.text("catalog", "genie_workshop", "Catalog")
dbutils.widgets.text("schema",  "sancor",          "Schema")
dbutils.widgets.text("endpoint_name", "rechazo-siniestros", "Endpoint Name")
dbutils.widgets.text("model_name", "rechazo_siniestros", "Model Name")

CATALOG        = dbutils.widgets.get("catalog")
SCHEMA         = dbutils.widgets.get("schema")
ENDPOINT_NAME  = dbutils.widgets.get("endpoint_name")
MODEL_NAME     = dbutils.widgets.get("model_name")

REGISTERED_MODEL = f"{CATALOG}.{SCHEMA}.{MODEL_NAME}"
FEATURE_TABLE    = f"{CATALOG}.{SCHEMA}.features_poliza"

print(f"Catalog:  {CATALOG}")
print(f"Schema:   {SCHEMA}")
print(f"Modelo:   {REGISTERED_MODEL}")
print(f"Endpoint: {ENDPOINT_NAME}")

# COMMAND ----------

# DBTITLE 1,Paso 1: Exploración de Datos (EDA)
# MAGIC %md
# MAGIC ## Paso 1: Exploración de Datos (EDA)
# MAGIC
# MAGIC Antes de construir cualquier modelo, necesitamos entender los datos disponibles:
# MAGIC * **Volumen** — ¿tenemos suficientes datos para entrenar un modelo?
# MAGIC * **Distribuciones** — ¿cómo se distribuyen las variables numéricas y categóricas?
# MAGIC * **Target** — ¿existe una variable objetivo natural? ¿Está balanceada?
# MAGIC * **Relaciones** — ¿cómo se conectan las tablas entre sí?
# MAGIC
# MAGIC > **Buena práctica:** Invertir tiempo en EDA evita sorpresas durante el entrenamiento (nulls, outliers, clases desbalanceadas).

# COMMAND ----------

# DBTITLE 1,Exploración del schema y volúmenes de datos
# Exploración del schema genie_workshop.sancor
tables = ["clientes", "polizas", "siniestros", "productores", "ramos", "conocimiento_cobertura"]

print("=" * 60)
print("RESUMEN DEL SCHEMA genie_workshop.sancor")
print("=" * 60)

for t in tables:
    df = spark.table(f"genie_workshop.sancor.{t}")
    count = df.count()
    cols = len(df.columns)
    print(f"\n📋 {t}: {count:,} filas | {cols} columnas")
    print(f"   Columnas: {', '.join(df.columns)}")

# COMMAND ----------

# DBTITLE 1,Distribuciones clave para ML
# MAGIC %sql
# MAGIC -- Distribución de estados de pólizas y siniestros
# MAGIC SELECT 'Pólizas' AS tabla, estado, COUNT(*) AS cantidad
# MAGIC FROM genie_workshop.sancor.polizas
# MAGIC GROUP BY estado
# MAGIC UNION ALL
# MAGIC SELECT 'Siniestros' AS tabla, estado, COUNT(*) AS cantidad
# MAGIC FROM genie_workshop.sancor.siniestros
# MAGIC GROUP BY estado
# MAGIC ORDER BY tabla, cantidad DESC

# COMMAND ----------

# DBTITLE 1,Perfil de clientes y features numéricas
import pyspark.sql.functions as F

# Perfil de clientes: edad, antigüedad, score crediticio
clientes = spark.table("genie_workshop.sancor.clientes")

clientes_profile = clientes.select(
    F.round(F.datediff(F.current_date(), F.col("fecha_nacimiento")) / 365.25, 1).alias("edad"),
    F.round(F.datediff(F.current_date(), F.col("fecha_alta")) / 365.25, 1).alias("antiguedad_anos"),
    F.col("score_crediticio"),
    F.col("provincia"),
    F.col("canal_captacion")
)

print("📊 Estadísticas descriptivas de clientes:")
clientes_profile.select("edad", "antiguedad_anos", "score_crediticio").summary().display()

print("\n📊 Distribución por canal de captación:")
clientes_profile.groupBy("canal_captacion").count().orderBy(F.desc("count")).display()

print("\n📊 Top 10 provincias:")
clientes_profile.groupBy("provincia").count().orderBy(F.desc("count")).limit(10).display()

# COMMAND ----------

# DBTITLE 1,Paso 2: Feature Engineering
# MAGIC %md
# MAGIC ## Paso 2: Feature Engineering
# MAGIC
# MAGIC **Hallazgos del EDA:**
# MAGIC * 4,000 clientes, 8,000 pólizas, 3,500 siniestros — volumen suficiente para modelos clásicos
# MAGIC * Target natural: `estado` del siniestro (rechazado=250 vs resuelto=2,038)
# MAGIC * Variables numéricas con buena dispersión + categóricas útiles
# MAGIC * Relaciones claras entre tablas vía FK
# MAGIC
# MAGIC En este paso:
# MAGIC 1. **Unimos las 5 tablas** usando las FK (siniestro → póliza → cliente, ramo, productor)
# MAGIC 2. **Creamos features derivadas**: edad, antigüedad, ratios (prima/suma, monto/suma)
# MAGIC 3. **Generamos un dataset plano** listo para entrenar
# MAGIC
# MAGIC > **Concepto clave:** En ML, el dataset de entrenamiento debe ser una **tabla plana** (filas=observaciones, columnas=features). Los joins multi-tabla convierten un modelo relacional en features individuales que un algoritmo puede procesar.

# COMMAND ----------

# DBTITLE 1,Construcción del dataset de features para ML
import pyspark.sql.functions as F

# Cargar tablas
clientes = spark.table("genie_workshop.sancor.clientes")
polizas = spark.table("genie_workshop.sancor.polizas")
siniestros = spark.table("genie_workshop.sancor.siniestros")
productores = spark.table("genie_workshop.sancor.productores")
ramos = spark.table("genie_workshop.sancor.ramos")

# Filtrar solo siniestros con resolución definitiva (resuelto o rechazado)
siniestros_resueltos = siniestros.filter(F.col("estado").isin("resuelto", "rechazado"))

# Join completo: siniestros + pólizas + clientes + ramos + productores
ml_dataset = (
    siniestros_resueltos
    .join(polizas, "poliza_id")
    .join(clientes, "cliente_id")
    .join(ramos, "ramo_id")
    .join(productores, "productor_id")
    .select(
        # Target
        F.when(siniestros_resueltos["estado"] == "rechazado", 1).otherwise(0).alias("target_rechazado"),
        # Features del cliente
        F.round(F.datediff(F.current_date(), clientes["fecha_nacimiento"]) / 365.25, 1).alias("edad_cliente"),
        F.round(F.datediff(F.current_date(), clientes["fecha_alta"]) / 365.25, 1).alias("antiguedad_cliente"),
        clientes["score_crediticio"],
        clientes["provincia"].alias("provincia_cliente"),
        clientes["canal_captacion"],
        # Features de la póliza
        polizas["prima_anual"],
        polizas["suma_asegurada"],
        polizas["canal_venta"],
        polizas["estado"].alias("estado_poliza"),
        # Features del ramo
        ramos["nombre_ramo"],
        # Features del siniestro
        siniestros_resueltos["tipo_siniestro"],
        siniestros_resueltos["monto_siniestro"],
        F.datediff(siniestros_resueltos["fecha_denuncia"], siniestros_resueltos["fecha_siniestro"]).alias("dias_hasta_denuncia"),
        # Features del productor
        productores["zona"],
        productores["tasa_retencion"],
        productores["anos_experiencia"],
        # Features derivadas
        F.round(polizas["prima_anual"] / polizas["suma_asegurada"], 6).alias("ratio_prima_suma"),
        F.round(siniestros_resueltos["monto_siniestro"] / polizas["suma_asegurada"], 4).alias("ratio_monto_suma"),
    )
)

print(f"Dataset ML: {ml_dataset.count():,} filas | {len(ml_dataset.columns)} columnas")
print(f"\nDistribución del target:")
ml_dataset.groupBy("target_rechazado").count().display()

print(f"\nMuestra del dataset:")
ml_dataset.limit(5).display()

# COMMAND ----------

# DBTITLE 1,Paso 3: Entrenamiento del Modelo
# MAGIC %md
# MAGIC ## Paso 3: Entrenamiento del Modelo con MLflow
# MAGIC
# MAGIC Entrenamos un modelo de clasificación binaria para predecir rechazo de siniestros.
# MAGIC
# MAGIC **Stack técnico:**
# MAGIC * `sklearn.pipeline.Pipeline` — encapsula preprocesamiento + modelo en un solo artefacto
# MAGIC * `ColumnTransformer` — transformaciones distintas para features numéricas vs categóricas
# MAGIC * `RandomForestClassifier` con `class_weight="balanced"` — compensa el desbalance de clases
# MAGIC * **MLflow Tracking** — registra parámetros, métricas y el modelo automáticamente
# MAGIC
# MAGIC > **¿Por qué Pipeline?** Encapsular el preprocesamiento dentro del modelo es una best practice de MLOps. Cuando el modelo se mueve a producción, el preprocesamiento viaja con él — evitando discrepancias entre entrenamiento y scoring (*train/serve skew*).

# COMMAND ----------

# DBTITLE 1,Paso 4: Evaluación del Modelo
# MAGIC %md
# MAGIC ## Paso 4: Evaluación del Modelo
# MAGIC
# MAGIC Evaluamos el modelo con múltiples métricas complementarias:
# MAGIC * **Feature Importance** — ¿qué variables aportan más al modelo?
# MAGIC * **Curva ROC** — sensibilidad del modelo ante diferentes thresholds
# MAGIC * **Curva Precision-Recall** — más informativa que ROC con clases desbalanceadas
# MAGIC * **Ajuste de threshold** — el threshold default (0.50) no siempre es óptimo
# MAGIC
# MAGIC > **Concepto clave:** Con clases desbalanceadas (11% rechazados), la **accuracy** es engañosa — un modelo que siempre predice "resuelto" tiene 89% accuracy. Las métricas de la clase minoritaria (precision, recall, F1 de "rechazado") son las que realmente importan.

# COMMAND ----------

# DBTITLE 1,Entrenamiento del modelo con MLflow
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import pandas as pd
import numpy as np

# Convertir a pandas
pdf = ml_dataset.toPandas()

# Definir features y target
target = "target_rechazado"

numeric_features = [
    "edad_cliente", "antiguedad_cliente", "score_crediticio",
    "prima_anual", "suma_asegurada", "monto_siniestro",
    "dias_hasta_denuncia", "tasa_retencion", "anos_experiencia",
    "ratio_prima_suma", "ratio_monto_suma"
]

categorical_features = [
    "provincia_cliente", "canal_captacion", "canal_venta",
    "estado_poliza", "nombre_ramo", "tipo_siniestro", "zona"
]

X = pdf[numeric_features + categorical_features]
y = pdf[target]

# Split temporal no aplica aquí (no hay orden temporal claro en el target)
# Usamos split aleatorio estratificado
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Pipeline de preprocesamiento + modelo
numeric_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="constant", fill_value="desconocido")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

preprocessor = ColumnTransformer(transformers=[
    ("num", numeric_transformer, numeric_features),
    ("cat", categorical_transformer, categorical_features)
])

model_pipeline = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        class_weight="balanced",  # Compensar desbalance de clases
        random_state=42,
        n_jobs=-1
    ))
])

# Entrenar con MLflow tracking
mlflow.set_experiment(f"/Users/{spark.sql('SELECT current_user()').collect()[0][0]}/sancor_siniestros_ml")

with mlflow.start_run(run_name="rf_rechazo_siniestros") as run:
    # Entrenar
    model_pipeline.fit(X_train, y_train)
    
    # Predecir
    y_pred = model_pipeline.predict(X_test)
    y_prob = model_pipeline.predict_proba(X_test)[:, 1]
    
    # Métricas
    auc = roc_auc_score(y_test, y_prob)
    report = classification_report(y_test, y_pred, target_names=["resuelto", "rechazado"], output_dict=True)
    
    # Loggear parámetros
    mlflow.log_param("model_type", "RandomForestClassifier")
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("n_features_numeric", len(numeric_features))
    mlflow.log_param("n_features_categorical", len(categorical_features))
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("test_size", len(X_test))
    
    # Loggear métricas
    mlflow.log_metric("auc_roc", auc)
    mlflow.log_metric("precision_rechazado", report["rechazado"]["precision"])
    mlflow.log_metric("recall_rechazado", report["rechazado"]["recall"])
    mlflow.log_metric("f1_rechazado", report["rechazado"]["f1-score"])
    mlflow.log_metric("accuracy", report["accuracy"])
    
    # Loggear modelo con signature
    signature = infer_signature(X_train.head(100), model_pipeline.predict(X_train.head(100)))
    model_info = mlflow.sklearn.log_model(
        model_pipeline,
        name="model",
        signature=signature,
        input_example=X_train.head(3)
    )
    
    print(f"\n{'='*60}")
    print(f"RESULTADOS DEL MODELO")
    print(f"{'='*60}")
    print(f"\nAUC-ROC: {auc:.4f}")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["resuelto", "rechazado"]))
    print(f"\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  Predicho:     resuelto  rechazado")
    print(f"  Real resuelto:  {cm[0][0]:>6}    {cm[0][1]:>6}")
    print(f"  Real rechazado: {cm[1][0]:>6}    {cm[1][1]:>6}")
    print(f"\nMLflow Run ID: {run.info.run_id}")
    print(f"Model URI: {model_info.model_uri}")

# COMMAND ----------

# DBTITLE 1,Feature importance del modelo
import matplotlib.pyplot as plt

# Extraer feature importance
rf_model = model_pipeline.named_steps["classifier"]
preproc = model_pipeline.named_steps["preprocessor"]

# Obtener nombres de features transformadas
num_names = numeric_features
cat_names = preproc.named_transformers_["cat"].named_steps["onehot"].get_feature_names_out(categorical_features).tolist()
all_feature_names = num_names + cat_names

importances = rf_model.feature_importances_
feature_imp = pd.DataFrame({
    "feature": all_feature_names,
    "importance": importances
}).sort_values("importance", ascending=False)

# Top 15 features
top_features = feature_imp.head(15)

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(range(len(top_features)), top_features["importance"].values, color="#1B6B93")
ax.set_yticks(range(len(top_features)))
ax.set_yticklabels(top_features["feature"].values)
ax.invert_yaxis()
ax.set_xlabel("Importancia")
ax.set_title("Top 15 Features Más Importantes - Predicción de Rechazo de Siniestros")
plt.tight_layout()
plt.show()

print("\nTop 10 features:")
display(feature_imp.head(10))

# COMMAND ----------

# DBTITLE 1,Ajuste de threshold y curva ROC
from sklearn.metrics import roc_curve, precision_recall_curve
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Curva ROC
fpr, tpr, thresholds_roc = roc_curve(y_test, y_prob)
axes[0].plot(fpr, tpr, color="#1B6B93", lw=2, label=f"AUC = {auc:.3f}")
axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
axes[0].set_xlabel("False Positive Rate")
axes[0].set_ylabel("True Positive Rate")
axes[0].set_title("Curva ROC")
axes[0].legend()
axes[0].grid(alpha=0.3)

# Curva Precision-Recall
precision_curve, recall_curve, thresholds_pr = precision_recall_curve(y_test, y_prob)
axes[1].plot(recall_curve, precision_curve, color="#E74C3C", lw=2)
prevalence = y_test.sum() / len(y_test)
axes[1].axhline(y=prevalence, color="gray", linestyle="--", alpha=0.5, label=f"Baseline (prevalencia={prevalence:.2%})")
axes[1].set_xlabel("Recall")
axes[1].set_ylabel("Precision")
axes[1].set_title("Curva Precision-Recall")
axes[1].legend()
axes[1].grid(alpha=0.3)

plt.suptitle("Evaluación del Modelo de Predicción de Rechazo de Siniestros", fontsize=13, y=1.02)
plt.tight_layout()
plt.show()

# Threshold óptimo (maximizar F1 para clase rechazado)
from sklearn.metrics import f1_score
best_threshold = 0.5
best_f1 = 0
for t in np.arange(0.1, 0.9, 0.01):
    y_pred_t = (y_prob >= t).astype(int)
    f1 = f1_score(y_test, y_pred_t)
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = t

y_pred_opt = (y_prob >= best_threshold).astype(int)
print(f"Threshold óptimo: {best_threshold:.2f}")
print(f"\nClassification Report con threshold ajustado:")
print(classification_report(y_test, y_pred_opt, target_names=["resuelto", "rechazado"]))

# COMMAND ----------

# DBTITLE 1,Paso 5: Registro en Unity Catalog
# MAGIC %md
# MAGIC ## Paso 5: Registro del Modelo en Unity Catalog
# MAGIC
# MAGIC Una vez satisfechos con el modelo, lo registramos en **Unity Catalog** para:
# MAGIC * **Versionamiento** — cada entrenamiento crea una versión inmutable
# MAGIC * **Gobernanza** — permisos heredados del catálogo (quién puede leer, servir, modificar)
# MAGIC * **Trazabilidad** — link directo al run de MLflow que lo generó
# MAGIC * **Aliases** — etiquetas mutables (ej: `champion`) que apuntan a una versión específica
# MAGIC
# MAGIC > **Flujo:** MLflow Artifact → Validación (signature + input\_example) → `mlflow.register_model()` → Alias `champion`

# COMMAND ----------

# DBTITLE 1,Paso 6: Despliegue en Model Serving
# MAGIC %md
# MAGIC ## Paso 6: Despliegue en Model Serving
# MAGIC
# MAGIC Con el modelo registrado, lo desplegamos como un **endpoint REST API** para inferencia en tiempo real.
# MAGIC
# MAGIC **Configuración elegida:**
# MAGIC * **Workload:** CPU Small (suficiente para sklearn RandomForest)
# MAGIC * **Scale-to-zero:** Habilitado (ahorro de costo cuando no hay tráfico)
# MAGIC * **SDK:** `databricks.sdk.WorkspaceClient` para crear y gestionar endpoints
# MAGIC
# MAGIC > **¿Cuándo usar GPU?** Solo si el modelo requiere CUDA (PyTorch, Transformers). Para sklearn, XGBoost y LightGBM, CPU siempre es suficiente. El endpoint toma \~15 minutos en estar listo.

# COMMAND ----------

# DBTITLE 1,Registro del modelo en Unity Catalog
import mlflow

# ── 1. Validar el artefacto antes de registrar ──────────────────────────
print("Validando artefacto MLflow...")
pyfunc_model = mlflow.pyfunc.load_model(model_info.model_uri)

if pyfunc_model.metadata.signature is None:
    raise ValueError("El modelo no tiene signature. Corregir antes de registrar.")
print(f"  ✅ Signature presente: {pyfunc_model.metadata.signature}")

representative_input = pyfunc_model.input_example
if representative_input is None:
    raise ValueError("El modelo no tiene input_example. Corregir antes de registrar.")
print(f"  ✅ Input example presente ({type(representative_input).__name__})")

# Verificar que predice correctamente
test_prediction = mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data=representative_input,
)
print(f"  ✅ Predicción de prueba exitosa: {test_prediction}")

# ── 2. Registrar en Unity Catalog ───────────────────────────────────────
registered_model_name = REGISTERED_MODEL

mlflow.set_registry_uri("databricks-uc")
registered_version = mlflow.register_model(
    model_uri=model_info.model_uri,
    name=registered_model_name,
    await_registration_for=300,
)
model_version = registered_version.version

print(f"\n{'='*60}")
print(f"MODELO REGISTRADO EN UNITY CATALOG")
print(f"{'='*60}")
print(f"  Nombre: {registered_model_name}")
print(f"  Versión: {model_version}")
print(f"  URI: models:/{registered_model_name}/{model_version}")

# ── 3. Asignar alias 'champion' ─────────────────────────────────────────
from mlflow import MlflowClient

registry_client = MlflowClient(registry_uri="databricks-uc")
registry_client.set_registered_model_alias(
    name=registered_model_name,
    alias="champion",
    version=model_version,
)
print(f"  Alias: champion → versión {model_version}")

# COMMAND ----------

# DBTITLE 1,Despliegue en Model Serving
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    ServedEntityInput,
    ServingModelWorkloadType,
)

w = WorkspaceClient()

# ── 1. Tamaños de workload disponibles (referencia) ─────────────────────
# CPU  → Small | Medium | Large           (sklearn, XGBoost, LightGBM)
# GPU  → Small | Medium | Large | XLarge  (PyTorch, Transformers, LLMs)
# Para RandomForest sklearn → CPU Small es suficiente.
print("Workload seleccionado: CPU / Small (suficiente para sklearn)")
print("  CPU  Small/Medium/Large  — modelos tabulares clásicos")
print("  GPU  Small/Large/XLarge  — solo si el modelo usa CUDA")

# ── 2. Configurar endpoint (CPU Small, scale-to-zero habilitado) ────────
endpoint_name = ENDPOINT_NAME
workload_type = "CPU"
workload_size = "Small"

served_entity = ServedEntityInput(
    entity_name=REGISTERED_MODEL,
    entity_version=str(model_version),
    workload_type=ServingModelWorkloadType(workload_type),
    workload_size=workload_size,
    scale_to_zero_enabled=True,
)
endpoint_config = EndpointCoreConfigInput(name=endpoint_name, served_entities=[served_entity])

# ── 3. Crear o actualizar endpoint ──────────────────────────────────────
try:
    existing_endpoint = w.serving_endpoints.get(endpoint_name)
except NotFound:
    existing_endpoint = None

if existing_endpoint is not None:
    current_entities = list(
        existing_endpoint.config.served_entities
        if existing_endpoint.config and existing_endpoint.config.served_entities
        else []
    )
    current_entity_names = [entity.entity_name for entity in current_entities]
    if len(current_entities) != 1 or current_entity_names[0] != registered_model_name:
        raise ValueError(
            f"El endpoint '{endpoint_name}' sirve {current_entity_names}. "
            f"Elija otro nombre o confirme el reemplazo."
        )
    print(f"\nActualizando endpoint existente '{endpoint_name}'...")
    w.serving_endpoints.update_config(
        name=endpoint_name,
        served_entities=[served_entity],
    )
else:
    print(f"\nCreando nuevo endpoint '{endpoint_name}'...")
    w.serving_endpoints.create(
        name=endpoint_name,
        config=endpoint_config,
    )

print(f"\n{'='*60}")
print(f"ENDPOINT DE MODEL SERVING")
print(f"{'='*60}")
print(f"  Endpoint: {endpoint_name}")
print(f"  Modelo: {registered_model_name} v{model_version}")
print(f"  Workload: {workload_type} / {workload_size}")
print(f"  Scale-to-zero: Habilitado")
print(f"\n⏳ El despliegue toma ~15 minutos. Ejecutar la siguiente celda para esperar...")

# COMMAND ----------

# DBTITLE 1,Esperar readiness y probar endpoint
import time
from databricks.sdk.service.serving import EndpointStateConfigUpdate, EndpointStateReady

# ── 1. Esperar a que el endpoint esté listo ─────────────────────────────
def wait_for_endpoint_ready(name, timeout_s=900, poll_s=15):
    deadline = time.time() + timeout_s
    failure_states = {
        EndpointStateConfigUpdate.UPDATE_FAILED,
        EndpointStateConfigUpdate.UPDATE_CANCELED,
    }
    while time.time() < deadline:
        state = w.serving_endpoints.get(name).state
        if (
            state.ready == EndpointStateReady.READY
            and state.config_update == EndpointStateConfigUpdate.NOT_UPDATING
        ):
            return
        if state.config_update in failure_states:
            raise RuntimeError(
                f"{name} falló con estado: {state.config_update.value}"
            )
        elapsed = int(time.time() - (deadline - timeout_s))
        print(f"  ⏳ Esperando... ({elapsed}s transcurridos)", end="\r")
        time.sleep(poll_s)
    raise TimeoutError(f"{name} no listo después de {timeout_s}s")

print("Esperando a que el endpoint esté listo...")
wait_for_endpoint_ready(endpoint_name)
print(f"\n✅ Endpoint '{endpoint_name}' está LISTO")

# ── 2. Enviar request de prueba ─────────────────────────────────────────
import json

# Tomar una muestra real del dataset de test
sample_row = X_test.head(1).to_dict(orient="records")
print(f"\nDatos de entrada (1 registro):")
print(json.dumps(sample_row, indent=2, default=str))

response = w.serving_endpoints.query(
    name=endpoint_name,
    dataframe_records=sample_row,
)

print(f"\n{'='*60}")
print(f"RESPUESTA DEL ENDPOINT")
print(f"{'='*60}")
print(f"  Predicción: {response.predictions}")
print(f"  (0 = resuelto, 1 = rechazado)")
print(f"\n✅ Flujo completo: Datos → Feature Engineering → Modelo → Unity Catalog → Model Serving")

# COMMAND ----------

# DBTITLE 1,Paso 7: Feature Store
# MAGIC %md
# MAGIC ## Paso 7: Feature Store — Features Reutilizables
# MAGIC
# MAGIC Hasta ahora construimos features manualmente con joins. En producción, esto causa problemas:
# MAGIC * Cada modelo recalcula los mismos joins → **duplicación de lógica**
# MAGIC * Entrenamiento y scoring pueden usar features distintas → **train/serve skew**
# MAGIC * No hay visibilidad de qué features existen → **difícil descubrimiento**
# MAGIC
# MAGIC **Feature Store** resuelve esto registrando features como tablas con **clave primaria** en Unity Catalog:
# MAGIC
# MAGIC | API | Propósito |
# MAGIC | --- | --- |
# MAGIC | `fe.create_table()` | Registra la Feature Table con PK |
# MAGIC | `FeatureLookup` | Declara qué features necesita el modelo |
# MAGIC | `fe.log_model()` | El artefacto incluye metadata de dónde buscar features |
# MAGIC | `fe.score_batch()` | Las features se resuelven automáticamente al scorear |
# MAGIC
# MAGIC > **Ventaja clave:** Con Feature Store, el scoring solo necesita la **lookup key** (`poliza_id`) + datos específicos del siniestro. Las 14 features de póliza se buscan automáticamente.

# COMMAND ----------

# DBTITLE 1,Crear Feature Table de pólizas enriquecidas
from databricks.feature_engineering import FeatureEngineeringClient
import pyspark.sql.functions as F

fe = FeatureEngineeringClient()

# Cargar tablas base
clientes = spark.table("genie_workshop.sancor.clientes")
polizas = spark.table("genie_workshop.sancor.polizas")
ramos = spark.table("genie_workshop.sancor.ramos")
productores = spark.table("genie_workshop.sancor.productores")

# Construir features enriquecidas a nivel póliza
poliza_features = (
    polizas
    .join(clientes, "cliente_id")
    .join(ramos, "ramo_id")
    .join(productores, "productor_id")
    .select(
        polizas["poliza_id"],
        # Demográficas del cliente
        F.round(F.datediff(F.current_date(), clientes["fecha_nacimiento"]) / 365.25, 1).alias("edad_cliente"),
        F.round(F.datediff(F.current_date(), clientes["fecha_alta"]) / 365.25, 1).alias("antiguedad_cliente"),
        clientes["score_crediticio"],
        clientes["provincia"].alias("provincia_cliente"),
        clientes["canal_captacion"],
        # Características de la póliza
        polizas["prima_anual"],
        polizas["suma_asegurada"],
        polizas["canal_venta"],
        polizas["estado"].alias("estado_poliza"),
        # Ramo
        ramos["nombre_ramo"],
        # Productor
        productores["zona"],
        productores["tasa_retencion"],
        productores["anos_experiencia"],
        # Derivadas
        F.round(polizas["prima_anual"] / polizas["suma_asegurada"], 6).alias("ratio_prima_suma"),
    )
)

# Crear feature table en Unity Catalog
table_name = "genie_workshop.sancor.features_poliza"

try:
    fe.create_table(
        name=table_name,
        primary_keys=["poliza_id"],
        df=poliza_features,
        schema=poliza_features.schema,
        description="Features enriquecidas a nivel de póliza: datos demográficos del cliente, características de póliza, ramo y productor. PK: poliza_id.",
    )
    print("Feature table CREADA.")
except Exception as e:
    if "already exists" in str(e):
        print("Feature table ya existe, reutilizando.")
    else:
        raise

print(f"✅ Feature Table creada: genie_workshop.sancor.features_poliza")
print(f"   Primary key: poliza_id")
print(f"   Filas: {poliza_features.count():,} | Columnas: {len(poliza_features.columns)}")
print(f"\nPreview:")
display(spark.table("genie_workshop.sancor.features_poliza").limit(5))

# COMMAND ----------

# DBTITLE 1,Entrenar modelo con Feature Store
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
import pyspark.sql.functions as F
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import mlflow
import mlflow.sklearn
from mlflow import MlflowClient

fe = FeatureEngineeringClient()
registered_model_name = REGISTERED_MODEL

# Labels df: solo datos del siniestro + lookup key
siniestros = spark.table("genie_workshop.sancor.siniestros")
labels_df = (
    siniestros
    .filter(F.col("estado").isin("resuelto", "rechazado"))
    .select(
        F.col("poliza_id"),
        F.col("tipo_siniestro"),
        F.col("monto_siniestro"),
        F.datediff(F.col("fecha_denuncia"), F.col("fecha_siniestro")).alias("dias_hasta_denuncia"),
        F.when(F.col("estado") == "rechazado", 1).otherwise(0).alias("target_rechazado"),
    )
)

# Feature lookup: las features de póliza se buscan automáticamente por poliza_id
feature_lookups = [
    FeatureLookup(
        table_name="genie_workshop.sancor.features_poliza",
        lookup_key="poliza_id",
    )
]

# Training set con Feature Store
training_set = fe.create_training_set(
    df=labels_df,
    feature_lookups=feature_lookups,
    label="target_rechazado",
    exclude_columns=["poliza_id"],  # PK no es feature predictiva
)


training_pdf = training_set.load_df().toPandas()
print(f"Training set: {len(training_pdf):,} filas | {len(training_pdf.columns)} columnas")

# Definir features (mismas que antes, sin ratio_monto_suma que depende del siniestro)
numeric_features_fs = [
    "edad_cliente", "antiguedad_cliente", "score_crediticio",
    "prima_anual", "suma_asegurada", "monto_siniestro",
    "dias_hasta_denuncia", "tasa_retencion", "anos_experiencia",
    "ratio_prima_suma"
]
categorical_features_fs = [
    "provincia_cliente", "canal_captacion", "canal_venta",
    "estado_poliza", "nombre_ramo", "tipo_siniestro", "zona"
]

feature_cols = numeric_features_fs + categorical_features_fs
X_fs = training_pdf[feature_cols]
y_fs = training_pdf["target_rechazado"]

X_train_fs, X_test_fs, y_train_fs, y_test_fs = train_test_split(
    X_fs, y_fs, test_size=0.2, random_state=42, stratify=y_fs
)

# Pipeline sklearn
preprocessor_fs = ColumnTransformer(transformers=[
    ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric_features_fs),
    ("cat", Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value="desconocido")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical_features_fs),
])

model_pipeline_fs = Pipeline([
    ("preprocessor", preprocessor_fs),
    ("classifier", RandomForestClassifier(n_estimators=100, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1))
])

# Entrenar y loggear con Feature Store
mlflow.set_experiment(f"/Users/{spark.sql('SELECT current_user()').collect()[0][0]}/sancor_siniestros_ml")

with mlflow.start_run(run_name="rf_feature_store") as run:
    model_pipeline_fs.fit(X_train_fs, y_train_fs)
    y_pred_fs = model_pipeline_fs.predict(X_test_fs)
    y_prob_fs = model_pipeline_fs.predict_proba(X_test_fs)[:, 1]
    auc_fs = roc_auc_score(y_test_fs, y_prob_fs)
    report_fs = classification_report(y_test_fs, y_pred_fs, target_names=["resuelto", "rechazado"], output_dict=True)

    mlflow.log_param("model_type", "RandomForestClassifier")
    mlflow.log_param("training_method", "Feature Store")
    mlflow.log_metric("auc_roc", auc_fs)
    mlflow.log_metric("f1_rechazado", report_fs["rechazado"]["f1-score"])
    mlflow.log_metric("accuracy", report_fs["accuracy"])

    # Log modelo CON metadata de Feature Store
    fe_model_info = fe.log_model(
        model=model_pipeline_fs,
        artifact_path="fs_model",
        flavor=mlflow.sklearn,
        training_set=training_set,
    )

# Registrar nueva versión en Unity Catalog
mlflow.set_registry_uri("databricks-uc")
fs_registered = mlflow.register_model(
    model_uri=fe_model_info.model_uri,
    name=registered_model_name,
    await_registration_for=300,
)
fs_model_version = fs_registered.version

registry_client = MlflowClient(registry_uri="databricks-uc")
registry_client.set_registered_model_alias(
    name=registered_model_name, alias="feature_store", version=fs_model_version,
)

print(f"\n{'='*60}")
print(f"MODELO CON FEATURE STORE")
print(f"{'='*60}")
print(f"  AUC-ROC: {auc_fs:.4f}")
print(f"  Registrado: {registered_model_name} v{fs_model_version}")
print(f"  Alias: feature_store → v{fs_model_version}")
print(f"\n  ✨ Ventaja: el modelo sabe automáticamente dónde buscar")
print(f"  las features. Para scoring solo necesita poliza_id +")
print(f"  datos del siniestro.")

# COMMAND ----------

# DBTITLE 1,Comparar versiones de modelos en MLflow
# ── Comparación de runs: versión sin Feature Store vs con Feature Store ──
import mlflow
from mlflow import MlflowClient

client_cmp = MlflowClient()
current_user = spark.sql("SELECT current_user()").collect()[0][0]
experiment_name_cmp = f"/Users/{current_user}/sancor_siniestros_ml"
experiment_cmp = client_cmp.get_experiment_by_name(experiment_name_cmp)

if experiment_cmp:
    runs = client_cmp.search_runs(
        experiment_ids=[experiment_cmp.experiment_id],
        order_by=["metrics.auc_roc DESC"],
        max_results=5,
    )
    print(f"{'Run':<30} {'AUC-ROC':>8} {'F1-Rechazo':>12} {'Método':<20}")
    print("-" * 74)
    for r in runs:
        auc    = r.data.metrics.get("auc_roc", 0)
        f1     = r.data.metrics.get("f1_rechazado", 0)
        method = r.data.params.get("training_method", "Manual join")
        print(f"{r.info.run_name:<30} {auc:>8.4f} {f1:>12.4f} {method:<20}")
    print(f"\n→ Tip: En la UI de MLflow podés comparar visualmente los runs:")
    print(f"  Experiments → sancor_siniestros_ml → seleccioná ambos runs → Compare")
else:
    print("Experimento no encontrado. Ejecutá primero los pasos 3 y 7.")

# COMMAND ----------

# DBTITLE 1,Paso 8: Batch Inference
# MAGIC %md
# MAGIC ## Paso 8: Batch Inference — Scoring Masivo
# MAGIC
# MAGIC La inferencia en batch es el caso de uso más común en seguros: scorear toda la cartera de siniestros pendientes (ej: cada noche).
# MAGIC
# MAGIC Con Feature Store, el scoring es limpio:
# MAGIC 1. El DataFrame de entrada solo necesita la **lookup key** (`poliza_id`) + features del siniestro
# MAGIC 2. Las 14 features de la póliza se buscan **automáticamente** desde la Feature Table
# MAGIC 3. No hay joins manuales — el modelo "sabe" dónde buscar
# MAGIC
# MAGIC > **Comparación:** Sin Feature Store, `scoring_df` necesita 19 columnas (todas las features). Con Feature Store, solo necesita 5 columnas (key + datos del siniestro).

# COMMAND ----------

# DBTITLE 1,Paso 9: Monitoreo con Inference Tables
# MAGIC %md
# MAGIC ## Paso 9: Monitoreo con Inference Tables
# MAGIC
# MAGIC El último paso del ciclo MLOps es monitorear el modelo en producción.
# MAGIC
# MAGIC **Inference Tables** capturan automáticamente cada request y response del endpoint:
# MAGIC * **Auditoría** — quién consultó qué, cuándo
# MAGIC * **Data drift** — ¿las features de producción se están alejando del training?
# MAGIC * **Model quality** — si llegan labels reales, se puede medir la degradación
# MAGIC
# MAGIC Los datos se guardan en una tabla Delta en Unity Catalog, consultable con SQL estándar.

# COMMAND ----------

# DBTITLE 1,Batch Inference — Scoring masivo de siniestros pendientes
# ── Batch Inference: scorear siniestros pendientes de resolución ──────
# Solo necesitamos poliza_id + datos del siniestro.
# Las features de póliza se buscan AUTOMÁTICAMENTE desde la Feature Table.

from databricks.feature_engineering import FeatureEngineeringClient
import pyspark.sql.functions as F

fe = FeatureEngineeringClient()

siniestros = spark.table(f"{CATALOG}.{SCHEMA}.siniestros")

scoring_df = (
    siniestros
    .filter(F.col("estado").isin("pendiente", "en_proceso"))
    .select(
        F.col("siniestro_id"),
        F.col("poliza_id"),
        F.col("tipo_siniestro"),
        F.col("monto_siniestro"),
        F.datediff(F.col("fecha_denuncia"), F.col("fecha_siniestro")).alias("dias_hasta_denuncia"),
    )
)

print(f"Siniestros pendientes a scorear: {scoring_df.count():,}")
print(f"Columnas en scoring_df: {scoring_df.columns}")
print(f"\n→ Las 14 features de póliza se buscan automáticamente de la Feature Table\n")

# Batch scoring con Feature Store
predictions = fe.score_batch(
    model_uri=f"models:/{REGISTERED_MODEL}@feature_store",  # Usa el alias asignado
    df=scoring_df,
)

# Resultados
predictions_display = predictions.withColumn(
    "prediccion", F.when(F.col("prediction") == 1, "🟡 RECHAZADO").otherwise("🟢 RESUELTO")
)

print("Distribución de predicciones:")
predictions_display.groupBy("prediccion").count().orderBy(F.desc("count")).display()

print("\nTop 10 siniestros con predicción de RECHAZO (priorización):")
predictions_display.filter(F.col("prediction") == 1).select(
    "siniestro_id", "poliza_id", "tipo_siniestro", "monto_siniestro", "prediccion"
).limit(10).display()

# COMMAND ----------

# DBTITLE 1,Inference Table — Logging de requests del endpoint
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    AiGatewayInferenceTableConfig,
    AiGatewayUsageTrackingConfig,
)

w = WorkspaceClient()
table_name_prefix = ENDPOINT_NAME.replace("-", "_")

print(f"Habilitando inference table en endpoint '{ENDPOINT_NAME}'...")
print(f"  Destino: {CATALOG}.{SCHEMA}.{table_name_prefix}_payload")

try:
    # Preservar configuración existente del gateway si la hay
    existing_ep = w.serving_endpoints.get(ENDPOINT_NAME)
    existing_gw = existing_ep.ai_gateway if existing_ep else None

    w.serving_endpoints.put_ai_gateway(
        name=ENDPOINT_NAME,
        fallback_config=existing_gw.fallback_config if existing_gw else None,
        guardrails=existing_gw.guardrails if existing_gw else None,
        rate_limits=existing_gw.rate_limits if existing_gw else None,
        inference_table_config=AiGatewayInferenceTableConfig(
            catalog_name=CATALOG,
            schema_name=SCHEMA,
            table_name_prefix=table_name_prefix,
            enabled=True,
        ),
        usage_tracking_config=AiGatewayUsageTrackingConfig(enabled=True),
    )

    # Verificar
    deployed = w.serving_endpoints.get(ENDPOINT_NAME)
    tc = deployed.ai_gateway.inference_table_config if deployed.ai_gateway else None

    if tc and tc.enabled:
        print(f"\n✅ Inference table habilitada exitosamente")
        print(f"   Tabla: {tc.catalog_name}.{tc.schema_name}.{tc.table_name_prefix}_payload")
        print(f"   Usage tracking: habilitado")
        print(f"\n   Cada request/response al endpoint se loguea")
        print(f"   automáticamente para auditoría y monitoreo de drift.")
    else:
        print("\n⚠️ La inference table no se activó correctamente.")

except Exception as e:
    print(f"\n⚠️ No se pudo habilitar la inference table: {e}")
    print(f"   Nota: requiere un catálogo con external storage.")
    print(f"   En producción, usar un catálogo dedicado para monitoreo.")

# COMMAND ----------

# DBTITLE 1,Resumen del Workshop
# MAGIC %md
# MAGIC ## Resumen del Workshop
# MAGIC
# MAGIC Recorrimos el **ciclo completo de MLOps** en Databricks, desde datos crudos hasta un modelo monitoreado en producción:
# MAGIC
# MAGIC | Paso | Qué hicimos | Herramienta |
# MAGIC | --- | --- | --- |
# MAGIC | 1 | Exploramos 5 tablas de Sancor Seguros | Spark SQL + PySpark |
# MAGIC | 2 | Construimos 19 features con joins multi-tabla | PySpark |
# MAGIC | 3 | Entrenamos Random Forest con pipeline encapsulado | sklearn + MLflow |
# MAGIC | 4 | Evaluamos con ROC, PR y ajuste de threshold | sklearn + matplotlib |
# MAGIC | 5 | Registramos el modelo v1 con alias `champion` | MLflow + Unity Catalog |
# MAGIC | 6 | Desplegamos endpoint REST API con scale-to-zero | Model Serving SDK |
# MAGIC | 7 | Registramos features reutilizables + modelo v2 | Feature Store |
# MAGIC | 8 | Scoreamos 1,212 siniestros pendientes | `fe.score_batch` |
# MAGIC | 9 | Habilitamos logging de requests/responses | Inference Tables |
# MAGIC
# MAGIC **Nota sobre el AUC \~0.60:** La señal débil es esperable en datos sintéticos. El objetivo del workshop es demostrar el **flujo MLOps**, no optimizar el modelo.
# MAGIC
# MAGIC **Próximos pasos sugeridos:**
# MAGIC * Configurar Lakehouse Monitoring sobre la inference table para detectar data drift
# MAGIC * Optimizar hiperparámetros con Optuna o GridSearchCV
# MAGIC * Probar otros targets: predicción de cancelación de pólizas
# MAGIC
# MAGIC **Recursos:**
# MAGIC * [MLflow en Databricks](https://docs.databricks.com/mlflow/index.html)
# MAGIC * [Feature Engineering](https://docs.databricks.com/machine-learning/feature-store/index.html)
# MAGIC * [Model Serving](https://docs.databricks.com/machine-learning/model-serving/index.html)