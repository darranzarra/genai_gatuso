# Agente de Scouting de Fútbol

Sistema agéntico de análisis y recomendación de fichajes construido con LangChain + Groq + Streamlit.
La app puede arrancar sin claves usando un modo demo local basado en `data/market_values.csv`.

## Estructura del proyecto

```
scouting_agent/
├── app.py                  # Interfaz principal (Streamlit)
├── agent.py                # Núcleo del agente LangChain
├── requirements.txt        # Dependencias
├── .env.example            # Plantilla de variables de entorno
├── data/
│   └── market_values.csv   # Dataset demo de valores de mercado
└── tools/
    ├── buscar_jugadores.py     # Tool: búsqueda por posición y nombre
    ├── comparar_jugadores.py   # Tool: comparativa de estadísticas
    ├── valor_mercado.py        # Tool: consulta de valores de mercado
    └── recomendar_fichajes.py  # Tool: recomendación combinada
```

## Instalación

### 1. Clonar e instalar dependencias
```bash
cd scouting_agent
pip install -r requirements.txt
```

### 2. Configurar variables de entorno opcionales
```bash
cp .env.example .env
# Edita .env si quieres usar el modo avanzado
```

Variables disponibles:
- `GROQ_API_KEY`: activa el agente LangChain con LLaMA 3.3 en Groq.
- `API_FOOTBALL_KEY`: permite que las tools consulten API-Football.

Si no configuras claves, Streamlit usa el modo demo local con el CSV incluido.
Si configuras `GROQ_API_KEY` pero no `API_FOOTBALL_KEY`, el agente sigue funcionando y las tools usan el CSV como fallback.

### 3. Ejecutar la aplicación
```bash
streamlit run app.py
```

## Uso

Una vez arrancada la app, puedes hacer consultas como:

- *"Recomienda un delantero para el Real Madrid con máximo 80M€ en La Liga"*
- *"Compara a Lewandowski y Benzema"*
- *"¿Cuánto vale Pedri en el mercado?"*
- *"¿Quién es el mejor centrocampista de la Premier League esta temporada?"*

En modo demo, los filtros de la barra lateral (`posición`, `liga` y `presupuesto máximo`) generan recomendaciones desde `data/market_values.csv`.

## Tools del agente

| Tool | Descripción |
|------|-------------|
| `buscar_jugadores` | Busca jugadores por posición y liga |
| `buscar_jugador_por_nombre` | Obtiene stats detalladas de un jugador |
| `comparar_jugadores` | Compara estadísticas entre dos jugadores |
| `comparar_maximos_goleadores` | Compara al máximo goleador de dos ligas |
| `obtener_valor_mercado` | Consulta el valor de mercado de un jugador |
| `filtrar_por_presupuesto` | Filtra jugadores asequibles por posición y presupuesto |
| `recomendar_fichajes` | Recomendación completa combinando stats + valor de mercado |

## Stack tecnológico

- **LLM**: LLaMA 3.3 en Groq
- **Framework agéntico**: LangChain
- **Datos avanzados**: API-Football
- **Demo local**: CSV de valores de mercado de ejemplo
- **Interfaz**: Streamlit
