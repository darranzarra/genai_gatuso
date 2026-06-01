import os
import unicodedata
from typing import Optional
import pandas as pd
from langchain.tools import tool

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "market_values.csv")


def _normalizar_texto(valor) -> str:
    """Normaliza texto para búsquedas tolerantes a mayúsculas y acentos."""
    texto = str(valor or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _buscar_columna(df: pd.DataFrame, claves: list[str]) -> Optional[str]:
    """Devuelve la primera columna cuyo nombre contiene alguna clave."""
    for columna in df.columns:
        columna_norm = _normalizar_texto(columna)
        if any(clave in columna_norm for clave in claves):
            return columna
    return None


def _normalizar_posicion(posicion: str) -> str:
    posicion_norm = _normalizar_texto(posicion)
    equivalencias = {
        "delantero": ["delantero", "forward", "attacker", "striker", "ataque"],
        "centrocampista": ["centrocampista", "mediocampista", "midfielder", "midfield"],
        "defensa": ["defensa", "defender", "defence", "defense"],
        "portero": ["portero", "goalkeeper", "keeper"],
    }

    for canonica, opciones in equivalencias.items():
        if any(opcion in posicion_norm for opcion in opciones):
            return canonica
    return posicion_norm


def _serie_numerica(serie: pd.Series) -> pd.Series:
    limpia = (
        serie.astype(str)
        .str.replace("€", "", regex=False)
        .str.replace("M", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    return pd.to_numeric(limpia, errors="coerce")


def _cargar_dataset() -> pd.DataFrame:
    """Carga el dataset de valores de mercado."""
    try:
        df = pd.read_csv(DATA_PATH)
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    except FileNotFoundError:
        return pd.DataFrame()


def _columnas_dataset(df: pd.DataFrame) -> dict[str, Optional[str]]:
    return {
        "nombre": _buscar_columna(df, ["name", "nombre", "player", "jugador"]),
        "valor": _buscar_columna(df, ["market_value", "value", "valor", "market"]),
        "equipo": _buscar_columna(df, ["club", "team", "equipo"]),
        "posicion": _buscar_columna(df, ["position", "posicion", "pos"]),
        "liga": _buscar_columna(df, ["league", "liga", "competition"]),
        "edad": _buscar_columna(df, ["age", "edad"]),
        "goles": _buscar_columna(df, ["goals", "goles"]),
        "asistencias": _buscar_columna(df, ["assists", "asistencias"]),
    }


def _filtrar_dataset_local(
    posicion: Optional[str] = None,
    liga: Optional[str] = None,
    presupuesto_max: Optional[float] = None,
) -> tuple[pd.DataFrame, dict[str, Optional[str]]]:
    """Filtra el CSV local con criterios de scouting básicos."""
    df = _cargar_dataset()
    columnas = _columnas_dataset(df)

    if df.empty:
        return df, columnas

    filtrado = df.copy()
    col_valor = columnas["valor"]
    col_posicion = columnas["posicion"]
    col_liga = columnas["liga"]

    if col_valor:
        filtrado[col_valor] = _serie_numerica(filtrado[col_valor])
        if presupuesto_max is not None:
            filtrado = filtrado[filtrado[col_valor] <= float(presupuesto_max)]

    if posicion and col_posicion:
        posicion_objetivo = _normalizar_posicion(posicion)
        filtrado = filtrado[
            filtrado[col_posicion].apply(
                lambda valor: _normalizar_posicion(valor) == posicion_objetivo
            )
        ]

    if liga and _normalizar_texto(liga) != "todas" and col_liga:
        liga_objetivo = _normalizar_texto(liga)
        filtrado = filtrado[
            filtrado[col_liga].apply(lambda valor: liga_objetivo in _normalizar_texto(valor))
        ]

    return filtrado.copy(), columnas


@tool
def obtener_valor_mercado(nombre_jugador: str) -> str:
    """
    Consulta el valor de mercado de un jugador desde el dataset local.
    Devuelve el valor en millones de euros y su equipo actual.
    
    Args:
        nombre_jugador: Nombre del jugador a consultar
    """
    df = _cargar_dataset()

    if df.empty:
        return (
            "Dataset de valores de mercado no encontrado. "
            "Coloca el archivo 'market_values.csv' en la carpeta /data/."
        )

    columnas = _columnas_dataset(df)
    col_nombre = columnas["nombre"]
    col_valor = columnas["valor"]
    col_equipo = columnas["equipo"]

    if not col_nombre or not col_valor:
        return "El dataset no tiene el formato esperado. Revisa que tenga columnas de nombre y valor."

    nombre_norm = _normalizar_texto(nombre_jugador)
    mask = df[col_nombre].apply(lambda valor: nombre_norm in _normalizar_texto(valor))
    resultados = df[mask]

    if resultados.empty:
        return f"No se encontró '{nombre_jugador}' en el dataset de valores de mercado."

    fila = resultados.iloc[0]
    valor = fila.get(col_valor, "N/A")
    equipo = fila.get(col_equipo, "N/A") if col_equipo else "N/A"

    return (
        f"Jugador: {fila[col_nombre]}\n"
        f"Equipo: {equipo}\n"
        f"Valor de mercado: {valor} M€"
    )


@tool
def filtrar_por_presupuesto(posicion: str, presupuesto_max: float, liga: str = "todas") -> str:
    """
    Filtra jugadores del dataset cuyo valor de mercado no supere el presupuesto indicado.
    
    Args:
        posicion: Posición del jugador (Forward, Midfielder, Defender, Goalkeeper)
        presupuesto_max: Presupuesto máximo en millones de euros
        liga: Liga a filtrar (opcional, 'todas' para no filtrar por liga)
    """
    filtrado, columnas = _filtrar_dataset_local(posicion, liga, presupuesto_max)

    if filtrado.empty:
        return (
            f"No se encontraron jugadores de posición '{posicion}' "
            f"con valor <= {presupuesto_max}M€ en {liga}."
        )

    col_nombre = columnas["nombre"]
    col_valor = columnas["valor"]
    col_equipo = columnas["equipo"]

    if not col_nombre or not col_valor:
        return "Formato del dataset incorrecto."

    filtrado = filtrado.sort_values(col_valor, ascending=False).head(10)

    lineas = [f"Top jugadores asequibles (posición: {posicion}, presupuesto: {presupuesto_max}M€):"]
    for _, fila in filtrado.iterrows():
        nombre = fila.get(col_nombre, "N/A")
        valor = fila.get(col_valor, "N/A")
        equipo = fila.get(col_equipo, "N/A") if col_equipo else "N/A"
        lineas.append(f"- {nombre} ({equipo}): {valor} M€")

    return "\n".join(lineas)
