import os
import re
import unicodedata
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

PROJECT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(PROJECT_DIR, ".env"), override=True)

from agent import crear_agente, convertir_historial
from tools.recomendar_fichajes import recomendar_fichajes_local

st.set_page_config(
    page_title="Scouting Agent",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .main-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.8rem;
        letter-spacing: 2px;
        color: #00C853;
        line-height: 1;
        margin-bottom: 0.2rem;
    }

    .main-subtitle {
        font-size: 0.95rem;
        color: #888;
        margin-bottom: 1.5rem;
        font-weight: 300;
    }

    .stChatMessage {
        border-radius: 12px;
    }

    .sidebar-section {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #2a2a4a;
    }

    .sidebar-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #00C853;
        margin-bottom: 6px;
        font-weight: 500;
    }

    .quick-btn {
        font-size: 0.8rem;
        margin-bottom: 4px;
    }

    .tool-badge {
        display: inline-block;
        background: #0d3b1e;
        color: #00C853;
        border: 1px solid #00C853;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.72rem;
        margin: 2px;
    }

    [data-testid="stSidebar"] {
        background-color: #0f0f1a;
    }

    .stTextInput > div > div > input {
        border-radius: 10px;
    }

    .stButton > button {
        border-radius: 10px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


def clave_configurada(nombre: str) -> bool:
    return bool(os.getenv(nombre, "").strip())


<<<<<<< HEAD
GROQ_CONFIGURADA = clave_configurada("GROQ_API_KEY")
=======
def normalizar_texto(valor: str) -> str:
    texto = str(valor or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def extraer_filtros_consulta(
    consulta: str,
    posicion_sidebar: str,
    liga_sidebar: str,
    presupuesto_sidebar: float,
    usar_presupuesto_sidebar: bool,
) -> tuple[Optional[str], float, str]:
    """Combina filtros del chat con los del sidebar, priorizando el texto escrito."""
    texto = normalizar_texto(consulta)

    posicion_detectada = None
    posiciones = {
        "Delantero": ["delantero", "atacante", "forward", "striker"],
        "Centrocampista": ["centrocampista", "mediocampista", "midfielder", "medio"],
        "Defensa": ["defensa", "defender", "central", "lateral"],
        "Portero": ["portero", "goalkeeper", "keeper", "arquero"],
    }
    for posicion_objetivo, claves in posiciones.items():
        if any(clave in texto for clave in claves):
            posicion_detectada = posicion_objetivo
            break

    presupuesto_detectado = None
    patrones_presupuesto = [
        r"(?:maximo|max|hasta|presupuesto|menos de|por debajo de)\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(?:m|millones|m€)?",
        r"(\d+(?:[.,]\d+)?)\s*(?:m€|m|millones)",
    ]
    for patron in patrones_presupuesto:
        match = re.search(patron, texto)
        if match:
            presupuesto_detectado = float(match.group(1).replace(",", "."))
            break

    liga_detectada = None
    ligas = {
        "La Liga": ["la liga", "laliga", "espana", "barcelona", "barca", "real madrid", "atletico"],
        "Premier League": ["premier", "inglaterra", "arsenal", "chelsea", "liverpool", "city", "united", "newcastle"],
        "Serie A": ["serie a", "italia", "inter", "milan", "juventus", "napoli"],
        "Bundesliga": ["bundesliga", "alemania", "bayern", "dortmund", "leverkusen"],
        "Ligue 1": ["ligue 1", "francia", "psg", "lille", "monaco", "marseille"],
    }
    for liga_objetivo, claves in ligas.items():
        if any(clave in texto for clave in claves):
            liga_detectada = liga_objetivo
            break

    posicion_filtro = posicion_detectada or (
        None if posicion_sidebar == "Cualquiera" else posicion_sidebar
    )
    liga_filtro = liga_detectada or (
        "todas" if liga_sidebar == "Todas las ligas" else liga_sidebar
    )
    presupuesto_filtro = (
        presupuesto_detectado
        if presupuesto_detectado is not None
        else presupuesto_sidebar if usar_presupuesto_sidebar else 9999
    )

    return posicion_filtro, presupuesto_filtro, liga_filtro


OPENAI_CONFIGURADA = clave_configurada("OPENAI_API_KEY") or clave_configurada("GROQ_API_KEY")
>>>>>>> 4d64ae6e6fbe2dd7210cc47e0536bb63191affb5
API_FOOTBALL_CONFIGURADA = clave_configurada("API_FOOTBALL_KEY")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">⚽ SCOUT<br>AGENT</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">Powered by LLaMA 3.3 (Groq) + LangChain</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="sidebar-label">Contexto del equipo (opcional)</div>', unsafe_allow_html=True)
    equipo = st.text_input("Equipo", placeholder="Ej: Real Madrid", label_visibility="collapsed")
    posicion = st.selectbox(
        "Posición buscada",
        ["Cualquiera", "Delantero", "Centrocampista", "Defensa", "Portero"],
        label_visibility="collapsed"
    )
    usar_presupuesto = st.checkbox("Limitar presupuesto", value=False)
    presupuesto = st.number_input(
        "Presupuesto máximo (M€)",
        min_value=0,
        max_value=300,
        value=80,
        step=5,
        label_visibility="collapsed",
        disabled=not usar_presupuesto
    )
    liga = st.selectbox(
        "Liga",
        ["Todas las ligas", "La Liga", "Premier League", "Serie A", "Bundesliga", "Ligue 1"],
        label_visibility="collapsed"
    )

    _pos_btn = posicion if posicion != "Cualquiera" else "jugador"
    _liga_btn = liga if liga != "Todas las ligas" else "cualquier liga"
    _presupuesto_btn = f" con máximo {presupuesto}M€" if usar_presupuesto else ""
    _equipo_btn = f" para {equipo}" if equipo else ""
    if st.button("🔍 Buscar con estos filtros", use_container_width=True, type="primary"):
        st.session_state.consulta_rapida = (
            f"Recomienda un {_pos_btn.lower()}{_equipo_btn}{_presupuesto_btn} en {_liga_btn}"
        )

    st.markdown("---")

    st.markdown('<div class="sidebar-label">Modo</div>', unsafe_allow_html=True)
    if GROQ_CONFIGURADA:
        usar_agente = st.toggle(
            "Usar agente LangChain",
            value=True,
            help="Requiere GROQ_API_KEY. Si falta API_FOOTBALL_KEY, las tools usan el CSV local.",
        )
    else:
        usar_agente = False

    if usar_agente and API_FOOTBALL_CONFIGURADA:
        st.caption("Agente avanzado con Groq y API-Football.")
    elif usar_agente:
        st.caption("Agente LangChain (Groq) con datos del CSV local.")
    else:
        st.caption("Demo local con data/market_values.csv.")

    st.markdown("---")

    st.markdown('<div class="sidebar-label">Consultas rápidas</div>', unsafe_allow_html=True)

    _pos = posicion if posicion != "Cualquiera" else "jugador"
    _liga = liga if liga != "Todas las ligas" else "Europa"
    _presupuesto_txt = f"con máximo {presupuesto}M€ " if usar_presupuesto else ""
    consultas = [
        f"Recomienda un {_pos.lower()} para {equipo or 'mi equipo'} {_presupuesto_txt}en {_liga}",
        f"¿Quién es el mejor {_pos.lower()} de {_liga} esta temporada?",
        "Compara a Lewandowski y Benzema",
        "¿Cuánto vale Pedri en el mercado?",
    ]

    for consulta in consultas:
        if st.button(consulta[:55] + "..." if len(consulta) > 55 else consulta, use_container_width=True):
            st.session_state.consulta_rapida = consulta

    st.markdown("---")

    st.markdown('<div class="sidebar-label">Tools disponibles</div>', unsafe_allow_html=True)
    badges = ["buscar_jugadores", "comparar_stats", "max_goleadores", "valor_mercado", "filtrar_presupuesto", "recomendar_fichajes"]
    badges_html = "".join([f'<span class="tool-badge">{b}</span>' for b in badges])
    st.markdown(badges_html, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Estado de la sesión ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if usar_agente and st.session_state.get("agente") is None:
    try:
        st.session_state.agente = crear_agente()
        st.session_state.agent_error = None
    except Exception as e:
        st.session_state.agente = None
        st.session_state.agent_error = str(e)
        usar_agente = False


# ── Área principal ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">Agente de Scouting</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Busca jugadores, compara estadísticas y descubre los mejores fichajes para tu equipo</div>', unsafe_allow_html=True)

if st.session_state.get("agent_error"):
    st.warning(st.session_state.agent_error)

if not usar_agente:
    _pos_filtro = None if posicion == "Cualquiera" else posicion
    _liga_filtro = "todas" if liga == "Todas las ligas" else liga
    _presupuesto_filtro = presupuesto if usar_presupuesto else 9999
    texto_demo, tabla_demo = recomendar_fichajes_local(_pos_filtro, _presupuesto_filtro, _liga_filtro, limite=10)
    st.markdown("### Recomendaciones demo")
    if tabla_demo.empty:
        st.info(texto_demo)
    else:
        st.dataframe(tabla_demo, use_container_width=True, hide_index=True)

if not st.session_state.messages:
    st.info("👋 Empieza preguntando algo como: *\"Recomienda un delantero para el Barcelona con máximo 60M€\"*")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="⚽" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Detectar consulta rápida del sidebar
if "consulta_rapida" in st.session_state and st.session_state.consulta_rapida:
    prompt = st.session_state.consulta_rapida
    st.session_state.consulta_rapida = None
else:
    prompt = st.chat_input("Escribe tu consulta de scouting...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⚽"):
        with st.spinner("Analizando datos de scouting..."):
            if usar_agente and st.session_state.get("agente"):
                try:
                    historial = convertir_historial(st.session_state.messages[:-1])
                    respuesta = st.session_state.agente.invoke({
                        "input": prompt,
                        "chat_history": historial
                    })
                    contenido = respuesta.get("output", "No se pudo generar una respuesta.")
                except Exception as e:
                    _pos_filtro, _presupuesto_filtro, _liga_filtro = extraer_filtros_consulta(
                        prompt,
                        posicion,
                        liga,
                        presupuesto,
                        usar_presupuesto,
                    )
                    contenido = (
                        "No se pudo usar el agente avanzado. "
                        f"Uso el modo demo local.\n\n{recomendar_fichajes_local(_pos_filtro, _presupuesto_filtro, _liga_filtro)[0]}\n\n"
                        f"Detalle técnico: {str(e)}"
                    )
            else:
                _pos_filtro, _presupuesto_filtro, _liga_filtro = extraer_filtros_consulta(
                    prompt,
                    posicion,
                    liga,
                    presupuesto,
                    usar_presupuesto,
                )
                contenido = recomendar_fichajes_local(_pos_filtro, _presupuesto_filtro, _liga_filtro)[0]

        st.markdown(contenido)

    st.session_state.messages.append({"role": "assistant", "content": contenido})
    st.rerun()
