# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Title
# MAGIC %md
# MAGIC # Evaluación Remota del Agente Sancor
# MAGIC
# MAGIC Evalúa el agente desplegado en Databricks Apps invocando su endpoint HTTP, sin necesidad de entorno local.

# COMMAND ----------

# DBTITLE 1,Instalar dependencias
# MAGIC %pip install mlflow>=3.10.0 openai-agents>=0.4.1 databricks-openai>=0.13.0 --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Configurar MLflow experiment
import mlflow

# Apuntar al experiment vinculado a la app agent-sancor-test-agent
EXPERIMENT_ID = "4467560868402375"
mlflow.set_experiment(experiment_id=EXPERIMENT_ID)
print(f"Experiment configurado: {EXPERIMENT_ID}")

# COMMAND ----------

# DBTITLE 1,Definir agente y predict_fn directamente
# Replicar la lógica del agente directamente (misma config que agent.py)
import asyncio
import nest_asyncio
nest_asyncio.apply()

import mlflow
from agents import Agent, Runner, set_default_openai_api, set_default_openai_client
from agents.mcp import MCPServer, MCPServerManager
from agents.tracing import set_trace_processors
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import McpServer
from databricks.sdk import WorkspaceClient
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

mlflow.openai.autolog()
set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])

# Config extraída de agent.py
NAME = "agent-sancor-test-agent"
MODEL = "databricks-claude-opus-4-7"
SYSTEM_PROMPT = """Eres el asistente analítico de Sancor Seguros Argentina. Respondes
preguntas de negocio SOBRE DATOS consultando exclusivamente las herramientas disponibles;
nunca inventas cifras. Si una pregunta no se puede responder con las herramientas, dilo con
claridad en lugar de estimar.

Reglas de uso:
- Elige la herramienta adecuada según la intención: siniestralidad/rentabilidad de ramos,
  score de riesgo de un cliente, estado de cartera de un productor, proyección de
  renovaciones, o tiempos de resolución/SLA de siniestros.
- Para preguntas CONCEPTUALES sobre coberturas, exclusiones, procedimientos de denuncia,
  SLA o renovación (no cifras), usa la búsqueda en la base de conocimiento verificada.
  Esta búsqueda hace coincidencia por substring: consulta con UNA palabra clave corta
  (ej: "granizo", "exclusiones", "denuncia"), no con frases largas.
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
  de responder."""

MCP_SERVERS = [
    ("genie_workshop.sancor.calcular_indice_siniestralidad", "/api/2.0/mcp/functions/genie_workshop/sancor/calcular_indice_siniestralidad"),
    ("genie_workshop.sancor.calcular_score_riesgo_cliente", "/api/2.0/mcp/functions/genie_workshop/sancor/calcular_score_riesgo_cliente"),
    ("genie_workshop.sancor.clasificar_estado_cartera", "/api/2.0/mcp/functions/genie_workshop/sancor/clasificar_estado_cartera"),
    ("genie_workshop.sancor.proyectar_renovaciones", "/api/2.0/mcp/functions/genie_workshop/sancor/proyectar_renovaciones"),
    ("genie_workshop.sancor.get_tiempo_promedio_resolucion", "/api/2.0/mcp/functions/genie_workshop/sancor/get_tiempo_promedio_resolucion"),
]

w = WorkspaceClient()
host = w.config.host

def build_mcp_url(path: str) -> str:
    return f"{host}{path}"

def init_mcp_servers():
    return [
        McpServer(name=name, url=build_mcp_url(url), workspace_client=None)
        for (name, url) in MCP_SERVERS
    ]

def predict_fn(input: list[dict], **kwargs) -> dict:
    """Invoca el agente directamente (misma lógica que el app desplegado)."""
    async def _run():
        mcp_servers = init_mcp_servers()
        async with MCPServerManager(servers=mcp_servers, connect_in_parallel=True) as manager:
            agent = Agent(
                name=NAME,
                instructions=SYSTEM_PROMPT,
                model=MODEL,
                mcp_servers=manager.active_servers,
            )
            messages = input if isinstance(input, list) else [input]
            result = await Runner.run(agent, messages)
            resp = ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])
            return resp.model_dump()
    
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run())

print("Agente configurado con 5 herramientas MCP. predict_fn lista.")

# COMMAND ----------

# DBTITLE 1,Definir test cases y simulador
from mlflow.genai.scorers import (
    Completeness,
    ConversationalSafety,
    ConversationCompleteness,
    Fluency,
    KnowledgeRetention,
    RelevanceToQuery,
    Safety,
    ToolCallCorrectness,
    UserFrustration,
)
from mlflow.genai.simulators import ConversationSimulator

test_cases = [
    {
        "goal": "Conocer el índice de siniestralidad del ramo Automotores",
        "persona": "Un productor de seguros que quiere entender la rentabilidad de su cartera.",
        "simulation_guidelines": [
            "Pregunta primero qué es el índice de siniestralidad antes de pedir datos concretos.",
        ],
    },
    {
        "goal": "Consultar el estado de cartera de un productor específico",
        "persona": "Un gerente regional que necesita un resumen ejecutivo rápido.",
        "simulation_guidelines": [
            "Preferir mensajes cortos y directos.",
        ],
    },
]

simulator = ConversationSimulator(
    test_cases=test_cases,
    max_turns=5,
    user_model="databricks:/databricks-claude-opus-4-7",
)

print(f"{len(test_cases)} test cases configurados, max_turns=5")

# COMMAND ----------

# DBTITLE 1,Ejecutar evaluación
results = mlflow.genai.evaluate(
    data=simulator,
    predict_fn=predict_fn,
    scorers=[
        Completeness(),
        ConversationCompleteness(),
        ConversationalSafety(),
        KnowledgeRetention(),
        UserFrustration(),
        Fluency(),
        RelevanceToQuery(),
        Safety(),
        ToolCallCorrectness(),
    ],
)

display(results.tables["eval_results"])