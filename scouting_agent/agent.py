import os
from dotenv import load_dotenv

PROJECT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

from tools.buscar_jugadores import buscar_jugadores, buscar_jugador_por_nombre
from tools.comparar_jugadores import comparar_jugadores
from tools.valor_mercado import obtener_valor_mercado, filtrar_por_presupuesto
from tools.recomendar_fichajes import recomendar_fichajes

SYSTEM_PROMPT = """Eres un experto agente de scouting de fútbol con acceso a datos estadísticos 
y valores de mercado de jugadores. Tu misión es ayudar a los equipos a encontrar los mejores 
fichajes posibles según sus necesidades y presupuesto.

Cuando el usuario te pida jugadores o fichajes, SIEMPRE:
1. Usa las herramientas disponibles para obtener datos reales
2. Filtra por presupuesto si se especifica
3. Presenta los resultados de forma clara y ordenada
4. Justifica tus recomendaciones con datos concretos (goles, asistencias, valor de mercado)
5. Si el usuario no especifica liga, busca en La Liga por defecto

Responde siempre en español y con un tono profesional pero accesible."""


def llm_configurado() -> bool:
    """Indica si se puede inicializar el agente LangChain."""
    return bool(os.getenv("GROQ_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip())


def crear_agente():
    """Inicializa y devuelve el agente con todas las tools registradas."""
    if not llm_configurado():
        raise RuntimeError(
            "No hay API key configurada. Añade GROQ_API_KEY o OPENAI_API_KEY al .env."
        )

    if os.getenv("GROQ_API_KEY", "").strip():
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            api_key=os.getenv("GROQ_API_KEY")
        )
    else:
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    tools = [
        buscar_jugadores,
        buscar_jugador_por_nombre,
        comparar_jugadores,
        obtener_valor_mercado,
        filtrar_por_presupuesto,
        recomendar_fichajes,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )

    return executor


def convertir_historial(mensajes: list) -> list:
    """Convierte el historial de Streamlit al formato de LangChain."""
    historial = []
    for msg in mensajes:
        if msg["role"] == "user":
            historial.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            historial.append(AIMessage(content=msg["content"]))
    return historial
