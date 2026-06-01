# ⚽ Agente de Scouting de Fútbol

Sistema agéntico de análisis y recomendación de fichajes construido con LangChain + GPT-4o + Streamlit.

## Estructura del proyecto

```
scouting_agent/
├── app.py                  # Interfaz principal (Streamlit)
├── agent.py                # Núcleo del agente LangChain
├── requirements.txt        # Dependencias
├── .env.example            # Plantilla de variables de entorno
├── data/
│   └── market_values.csv   # Dataset de valores de mercado (descargar de Kaggle)
└── tools/
    ├── buscar_jugadores.py     # Tool: búsqueda por posición y nombre
    ├── comparar_jugadores.py   # Tool: comparativa de estadísticas
    ├── valor_mercado.py        # Tool: consulta de valores de mercado
    └── recomendar_fichajes.py  # Tool: recomendación combinada
```

## Instalación

### 1. Clonar e instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env con tus claves API
```

Necesitas:
- **OpenAI API Key**: https://platform.openai.com/api-keys
- **API-Football Key**: https://www.api-football.com (plan gratuito disponible)

### 3. Descargar dataset de valores de mercado
- Ve a Kaggle y busca: `football players market value transfermarkt`
- Descarga el CSV y colócalo en `data/market_values.csv`
- Dataset recomendado: https://www.kaggle.com/datasets/davidcariboo/player-scores

### 4. Ejecutar la aplicación
```bash
streamlit run app.py
```

## Uso

Una vez arrancada la app, puedes hacer consultas como:

- *"Recomienda un delantero para el Real Madrid con máximo 80M€ en La Liga"*
- *"Compara a Lewandowski y Benzema"*
- *"¿Cuánto vale Pedri en el mercado?"*
- *"¿Quién es el mejor centrocampista de la Premier League esta temporada?"*

## Tools del agente

| Tool | Descripción |
|------|-------------|
| `buscar_jugadores` | Busca jugadores por posición y liga |
| `buscar_jugador_por_nombre` | Obtiene stats detalladas de un jugador |
| `comparar_jugadores` | Compara estadísticas entre dos jugadores |
| `obtener_valor_mercado` | Consulta el valor de mercado de un jugador |
| `filtrar_por_presupuesto` | Filtra jugadores asequibles por posición y presupuesto |
| `recomendar_fichajes` | Recomendación completa combinando stats + valor de mercado |

## Stack tecnológico

- **LLM**: GPT-4o (OpenAI)
- **Framework agéntico**: LangChain
- **Datos en tiempo real**: API-Football
- **Valores de mercado**: Dataset Kaggle (Transfermarkt)
- **Interfaz**: Streamlit
