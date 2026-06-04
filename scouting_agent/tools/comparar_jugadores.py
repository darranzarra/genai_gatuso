import os
from typing import Optional
import requests
import pandas as pd
from langchain.tools import tool
from tools.valor_mercado import (
    _columnas_dataset,
    _cargar_dataset,
    _normalizar_texto,
    _serie_numerica,
)

BASE_URL = "https://v3.football.api-sports.io"

LIGAS = {
    "La Liga": 140,
    "Premier League": 39,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
}

LIGAS_ALIASES = {
    "la liga": "La Liga",
    "liga espanola": "La Liga",
    "liga española": "La Liga",
    "espana": "La Liga",
    "españa": "La Liga",
    "spain": "La Liga",
    "spanish": "La Liga",
    "premier": "Premier League",
    "liga inglesa": "Premier League",
    "inglaterra": "Premier League",
    "england": "Premier League",
    "serie a": "Serie A",
    "liga italiana": "Serie A",
    "italia": "Serie A",
    "italy": "Serie A",
    "bundesliga": "Bundesliga",
    "liga alemana": "Bundesliga",
    "alemania": "Bundesliga",
    "germany": "Bundesliga",
    "ligue 1": "Ligue 1",
    "liga francesa": "Ligue 1",
    "francesa": "Ligue 1",
    "francia": "Ligue 1",
    "france": "Ligue 1",
    "french": "Ligue 1",
}


def _api_headers() -> dict:
    return {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "").strip()}


def _normalizar_liga(liga: str) -> str:
    liga_norm = _normalizar_texto(liga)
    for alias, canonica in LIGAS_ALIASES.items():
        if alias in liga_norm:
            return canonica
    return liga


def _valor_numerico_fila(fila, columna: Optional[str]) -> int:
    if not columna:
        return 0
    valor = _serie_numerica(fila.to_frame().T[columna]).iloc[0]
    return 0 if pd.isna(valor) else int(valor)


def _get_stats_jugador_local(nombre: str) -> dict:
    df = _cargar_dataset()
    columnas = _columnas_dataset(df)

    if df.empty or not columnas["nombre"]:
        return {}

    nombre_norm = _normalizar_texto(nombre)
    resultados = df[df[columnas["nombre"]].apply(lambda valor: nombre_norm in _normalizar_texto(valor))]
    if resultados.empty:
        return {}

    fila = resultados.iloc[0]
    col_valor = columnas["valor"]
    col_goles = columnas["goles"]
    col_asistencias = columnas["asistencias"]

    valor = fila.get(col_valor, "N/A") if col_valor else "N/A"
    goles = _valor_numerico_fila(fila, col_goles)
    asistencias = _valor_numerico_fila(fila, col_asistencias)

    return {
        "nombre": fila.get(columnas["nombre"], nombre),
        "liga": fila.get(columnas["liga"], "N/A") if columnas["liga"] else "N/A",
        "equipo": fila.get(columnas["equipo"], "N/A") if columnas["equipo"] else "N/A",
        "edad": fila.get(columnas["edad"], "N/A") if columnas["edad"] else "N/A",
        "posicion": fila.get(columnas["posicion"], "N/A") if columnas["posicion"] else "N/A",
        "partidos": "N/A",
        "goles": goles,
        "asistencias": asistencias,
        "pases_clave": "N/A",
        "duelos_ganados": "N/A",
        "valor_mercado": valor,
    }


def _stats_desde_fila_local(fila, columnas: dict, liga: str) -> dict:
    col_valor = columnas["valor"]
    col_goles = columnas["goles"]
    col_asistencias = columnas["asistencias"]

    return {
        "nombre": fila.get(columnas["nombre"], "N/A") if columnas["nombre"] else "N/A",
        "liga": fila.get(columnas["liga"], liga) if columnas["liga"] else liga,
        "equipo": fila.get(columnas["equipo"], "N/A") if columnas["equipo"] else "N/A",
        "edad": fila.get(columnas["edad"], "N/A") if columnas["edad"] else "N/A",
        "posicion": fila.get(columnas["posicion"], "N/A") if columnas["posicion"] else "N/A",
        "partidos": "N/A",
        "goles": _valor_numerico_fila(fila, col_goles),
        "asistencias": _valor_numerico_fila(fila, col_asistencias),
        "pases_clave": "N/A",
        "duelos_ganados": "N/A",
        "valor_mercado": fila.get(col_valor, "N/A") if col_valor else "N/A",
    }


def _maximo_goleador_local(liga: str) -> dict:
    df = _cargar_dataset()
    columnas = _columnas_dataset(df)

    if df.empty or not columnas["nombre"] or not columnas["goles"]:
        return {}

    liga_canonica = _normalizar_liga(liga)
    filtrado = df.copy()

    if columnas["liga"]:
        liga_norm = _normalizar_texto(liga_canonica)
        filtrado = filtrado[
            filtrado[columnas["liga"]].apply(lambda valor: liga_norm in _normalizar_texto(valor))
        ]

    if filtrado.empty:
        return {}

    filtrado[columnas["goles"]] = _serie_numerica(filtrado[columnas["goles"]]).fillna(0)
    orden = [columnas["goles"]]
    ascendente = [False]

    if columnas["asistencias"]:
        filtrado[columnas["asistencias"]] = _serie_numerica(filtrado[columnas["asistencias"]]).fillna(0)
        orden.append(columnas["asistencias"])
        ascendente.append(False)

    fila = filtrado.sort_values(orden, ascending=ascendente).iloc[0]
    return _stats_desde_fila_local(fila, columnas, liga_canonica)


def _get_stats_jugador(nombre: str, temporada: str) -> dict:
    """Función auxiliar: obtiene stats de un jugador por nombre."""
    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        return _get_stats_jugador_local(nombre)

    response = requests.get(
        f"{BASE_URL}/players",
        headers=_api_headers(),
        params={"search": nombre, "season": temporada}
    )

    if response.status_code >= 400:
        return _get_stats_jugador_local(nombre)

    data = response.json()
    jugadores = data.get("response", [])
    if not jugadores:
        return _get_stats_jugador_local(nombre)

    j = jugadores[0]
    info = j.get("player", {})
    stats = j.get("statistics", [{}])[0]

    return {
        "nombre": info.get("name", nombre),
        "liga": "N/A",
        "equipo": stats.get("team", {}).get("name", "N/A"),
        "edad": info.get("age", "N/A"),
        "posicion": stats.get("games", {}).get("position", "N/A"),
        "partidos": stats.get("games", {}).get("appearences") or 0,
        "goles": stats.get("goals", {}).get("total") or 0,
        "asistencias": stats.get("goals", {}).get("assists") or 0,
        "pases_clave": stats.get("passes", {}).get("key") or 0,
        "duelos_ganados": stats.get("duels", {}).get("won") or 0,
    }


def _maximo_goleador(liga: str, temporada: str) -> dict:
    liga_canonica = _normalizar_liga(liga)

    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        return _maximo_goleador_local(liga_canonica)

    liga_id = LIGAS.get(liga_canonica)
    if not liga_id:
        return _maximo_goleador_local(liga_canonica)

    try:
        response = requests.get(
            f"{BASE_URL}/players/topscorers",
            headers=_api_headers(),
            params={"league": liga_id, "season": temporada},
        )

        if response.status_code >= 400:
            return _maximo_goleador_local(liga_canonica)

        jugadores = response.json().get("response", [])
        if not jugadores:
            return _maximo_goleador_local(liga_canonica)

        jugador = jugadores[0]
        info = jugador.get("player", {})
        stats = jugador.get("statistics", [{}])[0]
        nombre = info.get("name", "N/A")
        stats_locales = _get_stats_jugador_local(nombre)

        return {
            "nombre": nombre,
            "liga": liga_canonica,
            "equipo": stats.get("team", {}).get("name", "N/A"),
            "edad": info.get("age", "N/A"),
            "posicion": stats.get("games", {}).get("position", "N/A"),
            "partidos": stats.get("games", {}).get("appearences") or 0,
            "goles": stats.get("goals", {}).get("total") or 0,
            "asistencias": stats.get("goals", {}).get("assists") or 0,
            "pases_clave": stats.get("passes", {}).get("key") or 0,
            "duelos_ganados": stats.get("duels", {}).get("won") or 0,
            "valor_mercado": stats_locales.get("valor_mercado", "N/A"),
        }
    except Exception:
        return _maximo_goleador_local(liga_canonica)


def _formatear_comparacion(stats1: dict, stats2: dict, titulo: str) -> str:
    metricas = [
        ("Liga", "liga"),
        ("Equipo", "equipo"),
        ("Edad", "edad"),
        ("Posicion", "posicion"),
        ("Partidos", "partidos"),
        ("Goles", "goles"),
        ("Asistencias", "asistencias"),
        ("G+A", "g_a"),
        ("Valor mercado", "valor_mercado"),
    ]

    stats1 = stats1.copy()
    stats2 = stats2.copy()
    stats1["g_a"] = int(stats1.get("goles", 0) or 0) + int(stats1.get("asistencias", 0) or 0)
    stats2["g_a"] = int(stats2.get("goles", 0) or 0) + int(stats2.get("asistencias", 0) or 0)

    lineas = [
        titulo,
        "",
        f"| Metrica | {stats1['nombre']} | {stats2['nombre']} |",
        "|---|---:|---:|",
    ]

    for etiqueta, clave in metricas:
        valor1 = stats1.get(clave, "N/A")
        valor2 = stats2.get(clave, "N/A")
        if valor1 != "N/A" or valor2 != "N/A":
            lineas.append(f"| {etiqueta} | {valor1} | {valor2} |")

    if stats1["goles"] > stats2["goles"]:
        conclusion = f"{stats1['nombre']} es el maximo goleador mas productivo en goles ({stats1['goles']} vs {stats2['goles']})."
    elif stats2["goles"] > stats1["goles"]:
        conclusion = f"{stats2['nombre']} es el maximo goleador mas productivo en goles ({stats2['goles']} vs {stats1['goles']})."
    elif stats1["g_a"] > stats2["g_a"]:
        conclusion = f"Empatan en goles, pero {stats1['nombre']} aporta mas G+A ({stats1['g_a']} vs {stats2['g_a']})."
    elif stats2["g_a"] > stats1["g_a"]:
        conclusion = f"Empatan en goles, pero {stats2['nombre']} aporta mas G+A ({stats2['g_a']} vs {stats1['g_a']})."
    else:
        conclusion = f"Ambos tienen un rendimiento ofensivo muy similar (G+A: {stats1['g_a']} cada uno)."

    lineas.extend(["", f"Conclusion: {conclusion}"])
    return "\n".join(lineas)


@tool
def comparar_jugadores(jugador1: str, jugador2: str, temporada: str = "2023") -> str:
    """
    Compara estadísticas entre dos jugadores de fútbol.
    Muestra una tabla comparativa con sus métricas principales.
    
    Args:
        jugador1: Nombre del primer jugador
        jugador2: Nombre del segundo jugador
        temporada: Año de la temporada (ej: 2023)
    """
    try:
        stats1 = _get_stats_jugador(jugador1, temporada)
        stats2 = _get_stats_jugador(jugador2, temporada)

        if not stats1:
            return f"No se encontraron datos para '{jugador1}'."
        if not stats2:
            return f"No se encontraron datos para '{jugador2}'."

        metricas = ["equipo", "edad", "posicion", "partidos", "goles", "asistencias", "pases_clave"]

        lineas = [
            f"{'Métrica':<20} {'':>20} {'':>20}",
            f"{'':=<60}",
            f"{'Jugador':<20} {stats1['nombre']:>20} {stats2['nombre']:>20}",
        ]

        for m in metricas:
            lineas.append(f"{m.capitalize():<20} {str(stats1.get(m, 'N/A')):>20} {str(stats2.get(m, 'N/A')):>20}")

        # Determinar quién tiene mejor rendimiento ofensivo
        score1 = stats1.get("goles", 0) + stats1.get("asistencias", 0)
        score2 = stats2.get("goles", 0) + stats2.get("asistencias", 0)

        if score1 > score2:
            conclusion = f"\nConclusión: {stats1['nombre']} tiene mejor rendimiento ofensivo (G+A: {score1} vs {score2})."
        elif score2 > score1:
            conclusion = f"\nConclusión: {stats2['nombre']} tiene mejor rendimiento ofensivo (G+A: {score2} vs {score1})."
        else:
            conclusion = f"\nConclusión: Rendimiento ofensivo similar (G+A: {score1} cada uno)."

        return "\n".join(lineas) + conclusion

    except Exception as e:
        return f"Error al comparar jugadores: {str(e)}"


@tool
def comparar_maximos_goleadores(liga1: str, liga2: str, temporada: str = "2023") -> str:
    """
    Compara al maximo goleador de dos ligas.
    Usa esta herramienta cuando el usuario pida comparar maximos goleadores,
    pichichis o top scorers de ligas, aunque no mencione nombres de jugadores.

    Args:
        liga1: Primera liga a comparar. Acepta alias como liga espanola o La Liga.
        liga2: Segunda liga a comparar. Acepta alias como liga francesa o Ligue 1.
        temporada: Ano de la temporada (ej: 2023)
    """
    stats1 = _maximo_goleador(liga1, temporada)
    stats2 = _maximo_goleador(liga2, temporada)

    if not stats1:
        return f"No se pudo identificar el maximo goleador de {liga1}."
    if not stats2:
        return f"No se pudo identificar el maximo goleador de {liga2}."

    liga1_canonica = _normalizar_liga(liga1)
    liga2_canonica = _normalizar_liga(liga2)
    titulo = f"Comparativa de maximos goleadores: {liga1_canonica} vs {liga2_canonica}"
    return _formatear_comparacion(stats1, stats2, titulo)
