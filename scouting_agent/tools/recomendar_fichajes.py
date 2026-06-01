import os
import requests
import pandas as pd
from langchain.tools import tool
from tools.valor_mercado import (
    _buscar_columna,
    _columnas_dataset,
    _filtrar_dataset_local,
    _normalizar_texto,
    _serie_numerica,
)

BASE_URL = "https://v3.football.api-sports.io"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "market_values.csv")

LIGAS = {
    "La Liga": 140,
    "Premier League": 39,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61
}

POSICIONES_MAP = {
    "delantero": "Attacker",
    "forward": "Attacker",
    "centrocampista": "Midfielder",
    "mediocampista": "Midfielder",
    "midfielder": "Midfielder",
    "defensa": "Defender",
    "defender": "Defender",
    "portero": "Goalkeeper",
    "goalkeeper": "Goalkeeper",
}


def _api_headers() -> dict:
    return {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "").strip()}


def recomendar_fichajes_local(
    posicion: str,
    presupuesto_max: float,
    liga: str = "La Liga",
    limite: int = 5,
) -> tuple[str, pd.DataFrame]:
    """Recomienda fichajes usando solo el CSV local."""
    filtrado, columnas = _filtrar_dataset_local(posicion, liga, presupuesto_max)

    if filtrado.empty:
        return (
            f"No hay candidatos en el CSV para {posicion} en {liga} "
            f"con presupuesto <= {presupuesto_max}M€.",
            pd.DataFrame(),
        )

    col_nombre = columnas["nombre"]
    col_valor = columnas["valor"]
    col_equipo = columnas["equipo"]
    col_liga = columnas["liga"]
    col_posicion = columnas["posicion"]
    col_edad = columnas["edad"]
    col_goles = columnas["goles"]
    col_asistencias = columnas["asistencias"]

    if not col_nombre or not col_valor:
        return "El CSV demo no tiene columnas de jugador y valor de mercado.", pd.DataFrame()

    ranking = filtrado.copy()
    ranking[col_valor] = _serie_numerica(ranking[col_valor])
    ranking["_score"] = 0.0

    if col_goles:
        ranking["_score"] += _serie_numerica(ranking[col_goles]).fillna(0) * 1.5
    if col_asistencias:
        ranking["_score"] += _serie_numerica(ranking[col_asistencias]).fillna(0)

    orden = ["_score", col_valor]
    ascendente = [False, True]
    top = ranking.sort_values(orden, ascending=ascendente).head(limite)

    columnas_salida = [
        col_nombre,
        col_equipo,
        col_liga,
        col_posicion,
        col_edad,
        col_valor,
        col_goles,
        col_asistencias,
    ]
    columnas_salida = [col for col in columnas_salida if col and col in top.columns]

    tabla = top[columnas_salida].copy()
    tabla = tabla.rename(
        columns={
            col_nombre: "Jugador",
            col_equipo: "Equipo" if col_equipo else col_equipo,
            col_liga: "Liga" if col_liga else col_liga,
            col_posicion: "Posición" if col_posicion else col_posicion,
            col_edad: "Edad" if col_edad else col_edad,
            col_valor: "Valor (M€)",
            col_goles: "Goles" if col_goles else col_goles,
            col_asistencias: "Asistencias" if col_asistencias else col_asistencias,
        }
    )

    lineas = [
        f"Recomendaciones demo — {posicion} | {liga} | Presupuesto máximo: {presupuesto_max}M€"
    ]
    for i, (_, fila) in enumerate(tabla.iterrows(), 1):
        nombre = fila.get("Jugador", "N/A")
        equipo = fila.get("Equipo", "N/A")
        valor = fila.get("Valor (M€)", "N/A")
        goles = fila.get("Goles", 0)
        asistencias = fila.get("Asistencias", 0)
        lineas.append(
            f"{i}. {nombre} ({equipo}) — {valor}M€ | Goles: {goles} | Asistencias: {asistencias}"
        )

    return "\n".join(lineas), tabla.reset_index(drop=True)


@tool
def recomendar_fichajes(
    posicion: str,
    presupuesto_max: float,
    liga: str = "La Liga",
    temporada: str = "2023",
    min_goles: int = 0
) -> str:
    """
    Recomienda los mejores fichajes posibles para una posición dada,
    filtrando por presupuesto máximo y rendimiento mínimo.
    Combina estadísticas de la API con valores de mercado del dataset.
    
    Args:
        posicion: Posición buscada (delantero, centrocampista, defensa, portero)
        presupuesto_max: Presupuesto máximo en millones de euros
        liga: Liga donde buscar (La Liga, Premier League, Serie A, Bundesliga, Ligue 1)
        temporada: Año de la temporada (ej: 2023)
        min_goles: Mínimo de goles requeridos (útil para atacantes)
    """
    posicion_api = POSICIONES_MAP.get(posicion.lower(), "Attacker")
    liga_id = LIGAS.get(liga, 140)

    if not os.getenv("API_FOOTBALL_KEY", "").strip():
        texto, _ = recomendar_fichajes_local(posicion, presupuesto_max, liga)
        return texto

    try:
        # 1. Obtener jugadores de la API
        response = requests.get(
            f"{BASE_URL}/players",
            headers=_api_headers(),
            params={
                "league": liga_id,
                "season": temporada,
                "position": posicion_api,
                "page": 1
            }
        )

        if response.status_code >= 400:
            texto, _ = recomendar_fichajes_local(posicion, presupuesto_max, liga)
            return (
                f"API-Football devolvió estado {response.status_code}. "
                f"Uso fallback local.\n\n{texto}"
            )

        data = response.json()
        jugadores_api = data.get("response", [])

        if not jugadores_api:
            texto, _ = recomendar_fichajes_local(posicion, presupuesto_max, liga)
            return (
                f"No se encontraron jugadores de tipo '{posicion}' en API-Football. "
                f"Uso fallback local.\n\n{texto}"
            )

        # 2. Cargar dataset de valores de mercado
        candidatos = []
        try:
            df = pd.read_csv(DATA_PATH)
            df.columns = [c.lower().strip() for c in df.columns]
            columnas = _columnas_dataset(df)
            col_nombre = columnas["nombre"]
            col_valor = columnas["valor"]
            if col_valor:
                df[col_valor] = _serie_numerica(df[col_valor])
        except Exception:
            df = pd.DataFrame()
            col_nombre = None
            col_valor = None

        # 3. Cruzar datos y filtrar
        for j in jugadores_api:
            info = j.get("player", {})
            stats = j.get("statistics", [{}])[0]
            nombre = info.get("name", "")
            goles = stats.get("goals", {}).get("total") or 0
            asistencias = stats.get("goals", {}).get("assists") or 0
            equipo = stats.get("team", {}).get("name", "N/A")

            if goles < min_goles:
                continue

            # Buscar valor de mercado en el dataset
            valor = None
            if not df.empty and col_nombre and col_valor:
                apellido = nombre.split()[-1] if nombre else ""
                mask = df[col_nombre].apply(
                    lambda valor_nombre: _normalizar_texto(apellido) in _normalizar_texto(valor_nombre)
                )
                match = df[mask]
                if not match.empty:
                    valor = match.iloc[0][col_valor]

            # Filtrar por presupuesto si tenemos el valor
            if valor is not None and valor > presupuesto_max:
                continue

            candidatos.append({
                "nombre": nombre,
                "equipo": equipo,
                "goles": goles,
                "asistencias": asistencias,
                "g_a": goles + asistencias,
                "valor": valor if valor is not None else "N/D"
            })

        if not candidatos:
            return (
                f"No se encontraron candidatos para '{posicion}' en {liga} "
                f"con presupuesto <= {presupuesto_max}M€ y >= {min_goles} goles."
            )

        # 4. Ordenar por G+A y mostrar top 5
        candidatos.sort(key=lambda x: x["g_a"], reverse=True)
        top = candidatos[:5]

        lineas = [
            f"Top fichajes recomendados — {posicion} | {liga} | Presupuesto: {presupuesto_max}M€\n"
        ]
        for i, c in enumerate(top, 1):
            valor_str = f"{c['valor']}M€" if c["valor"] != "N/D" else "valor N/D"
            lineas.append(
                f"{i}. {c['nombre']} ({c['equipo']})\n"
                f"   Goles: {c['goles']} | Asistencias: {c['asistencias']} | G+A: {c['g_a']} | {valor_str}"
            )

        return "\n".join(lineas)

    except Exception as e:
        texto, _ = recomendar_fichajes_local(posicion, presupuesto_max, liga)
        return f"No se pudo consultar API-Football ({str(e)}). Uso fallback local.\n\n{texto}"
