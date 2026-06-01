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


def _api_headers() -> dict:
    return {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "").strip()}


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
        "equipo": stats.get("team", {}).get("name", "N/A"),
        "edad": info.get("age", "N/A"),
        "posicion": stats.get("games", {}).get("position", "N/A"),
        "partidos": stats.get("games", {}).get("appearences") or 0,
        "goles": stats.get("goals", {}).get("total") or 0,
        "asistencias": stats.get("goals", {}).get("assists") or 0,
        "pases_clave": stats.get("passes", {}).get("key") or 0,
        "duelos_ganados": stats.get("duels", {}).get("won") or 0,
    }


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
