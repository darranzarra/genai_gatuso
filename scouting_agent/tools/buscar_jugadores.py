import os
import requests
from langchain.tools import tool
from tools.valor_mercado import (
    _columnas_dataset,
    _cargar_dataset,
    _filtrar_dataset_local,
    _normalizar_texto,
    _serie_numerica,
)

BASE_URL = "https://v3.football.api-sports.io"


def _api_headers() -> dict:
    return {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "").strip()}


def _buscar_jugadores_local(posicion: str, liga: str, limite: int = 10) -> str:
    filtrado, columnas = _filtrar_dataset_local(posicion=posicion, liga=liga)

    if filtrado.empty:
        return f"No hay jugadores locales para la posición {posicion} en {liga}."

    col_nombre = columnas["nombre"]
    col_equipo = columnas["equipo"]
    col_valor = columnas["valor"]
    col_goles = columnas["goles"]
    col_asistencias = columnas["asistencias"]

    if not col_nombre:
        return "El CSV local no tiene columna de nombre de jugador."

    if col_valor:
        filtrado[col_valor] = _serie_numerica(filtrado[col_valor])
        filtrado = filtrado.sort_values(col_valor, ascending=False)

    lineas = [f"Jugadores encontrados en modo demo ({liga}, {posicion}):"]
    for _, fila in filtrado.head(limite).iterrows():
        nombre = fila.get(col_nombre, "N/A")
        equipo = fila.get(col_equipo, "N/A") if col_equipo else "N/A"
        goles = fila.get(col_goles, 0) if col_goles else 0
        asistencias = fila.get(col_asistencias, 0) if col_asistencias else 0
        valor = fila.get(col_valor, "N/D") if col_valor else "N/D"
        lineas.append(
            f"- {nombre} ({equipo}): {goles} goles, {asistencias} asistencias, {valor}M€"
        )

    return "\n".join(lineas)


def _buscar_jugador_local(nombre: str) -> str:
    df = _cargar_dataset()
    columnas = _columnas_dataset(df)

    if df.empty:
        return "Dataset local no encontrado. Coloca data/market_values.csv."

    col_nombre = columnas["nombre"]
    if not col_nombre:
        return "El CSV local no tiene columna de nombre de jugador."

    nombre_norm = _normalizar_texto(nombre)
    resultados = df[df[col_nombre].apply(lambda valor: nombre_norm in _normalizar_texto(valor))]

    if resultados.empty:
        return f"No se encontró ningún jugador local con el nombre '{nombre}'."

    fila = resultados.iloc[0]
    col_equipo = columnas["equipo"]
    col_posicion = columnas["posicion"]
    col_liga = columnas["liga"]
    col_edad = columnas["edad"]
    col_valor = columnas["valor"]
    col_goles = columnas["goles"]
    col_asistencias = columnas["asistencias"]

    return (
        f"Jugador: {fila.get(col_nombre, 'N/A')}\n"
        f"Edad: {fila.get(col_edad, 'N/A') if col_edad else 'N/A'} | "
        f"Liga: {fila.get(col_liga, 'N/A') if col_liga else 'N/A'}\n"
        f"Equipo actual: {fila.get(col_equipo, 'N/A') if col_equipo else 'N/A'} | "
        f"Posición: {fila.get(col_posicion, 'N/A') if col_posicion else 'N/A'}\n"
        f"Valor: {fila.get(col_valor, 'N/A') if col_valor else 'N/A'}M€ | "
        f"Goles: {fila.get(col_goles, 0) if col_goles else 0} | "
        f"Asistencias: {fila.get(col_asistencias, 0) if col_asistencias else 0}"
    )


@tool
def buscar_jugadores(posicion: str, liga: str = "La Liga", temporada: str = "2023") -> str:
    """
    Busca jugadores por posición y liga usando la API de fútbol.
    Devuelve una lista con nombre, equipo, goles y asistencias.
    
    Args:
        posicion: Posición del jugador (Attacker, Midfielder, Defender, Goalkeeper)
        liga: Nombre de la liga (La Liga, Premier League, Serie A, Bundesliga, Ligue 1)
        temporada: Año de la temporada (ej: 2023)
    """
    LIGAS = {
        "La Liga": 140,
        "Premier League": 39,
        "Serie A": 135,
        "Bundesliga": 78,
        "Ligue 1": 61
    }

    liga_id = LIGAS.get(liga, 140)

    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        return _buscar_jugadores_local(posicion, liga)

    try:
        response = requests.get(
            f"{BASE_URL}/players",
            headers=_api_headers(),
            params={
                "league": liga_id,
                "season": temporada,
                "position": posicion,
                "page": 1
            }
        )

        if response.status_code >= 400:
            return _buscar_jugadores_local(posicion, liga)

        data = response.json()
        jugadores = data.get("response", [])

        if not jugadores:
            return _buscar_jugadores_local(posicion, liga)

        resultado = []
        for j in jugadores[:10]:
            info = j.get("player", {})
            stats = j.get("statistics", [{}])[0]
            goles = stats.get("goals", {}).get("total") or 0
            asistencias = stats.get("goals", {}).get("assists") or 0
            equipo = stats.get("team", {}).get("name", "Desconocido")
            resultado.append(
                f"- {info.get('name')} ({equipo}): {goles} goles, {asistencias} asistencias"
            )

        return f"Jugadores encontrados en {liga} ({posicion}):\n" + "\n".join(resultado)

    except Exception as e:
        return f"No se pudo consultar API-Football ({str(e)}). Uso fallback local.\n\n{_buscar_jugadores_local(posicion, liga)}"


@tool
def buscar_jugador_por_nombre(nombre: str, temporada: str = "2023") -> str:
    """
    Busca información detallada de un jugador concreto por su nombre.
    
    Args:
        nombre: Nombre del jugador a buscar
        temporada: Año de la temporada (ej: 2023)
    """
    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        return _buscar_jugador_local(nombre)

    try:
        response = requests.get(
            f"{BASE_URL}/players",
            headers=_api_headers(),
            params={
                "search": nombre,
                "season": temporada
            }
        )

        if response.status_code >= 400:
            return _buscar_jugador_local(nombre)

        data = response.json()
        jugadores = data.get("response", [])

        if not jugadores:
            return _buscar_jugador_local(nombre)

        j = jugadores[0]
        info = j.get("player", {})
        stats = j.get("statistics", [{}])[0]

        nombre_completo = info.get("name", "Desconocido")
        edad = info.get("age", "N/A")
        nacionalidad = info.get("nationality", "N/A")
        equipo = stats.get("team", {}).get("name", "Desconocido")
        posicion = stats.get("games", {}).get("position", "N/A")
        goles = stats.get("goals", {}).get("total") or 0
        asistencias = stats.get("goals", {}).get("assists") or 0
        partidos = stats.get("games", {}).get("appearences") or 0

        return (
            f"Jugador: {nombre_completo}\n"
            f"Edad: {edad} | Nacionalidad: {nacionalidad}\n"
            f"Equipo actual: {equipo} | Posición: {posicion}\n"
            f"Temporada {temporada}: {partidos} partidos, {goles} goles, {asistencias} asistencias"
        )

    except Exception as e:
        return f"No se pudo consultar API-Football ({str(e)}). Uso fallback local.\n\n{_buscar_jugador_local(nombre)}"
