"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Monitor Analítico de Movilidad y Clima - CABA 2024                         ║
║  Dashboard Streamlit + Plotly                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

DATASET_PATH = Path("dataset_maestro_FINAL_2024.csv")

# Orden canónico de categorías de lluvia (de menor a mayor intensidad)
LLUVIA_ORDER = ["Sin lluvia", "Lluvia leve", "Lluvia moderada", "Lluvia intensa"]

# Paleta de colores del dashboard
COLOR_COLECTIVO = "#3B82F6"   # azul
COLOR_SUBTE     = "#EAB308"   # amarillo
COLOR_AUTO      = "#6B7280"   # gris

CARD_CSS = """
<style>
  /* ── Fondo general ── */
  .stApp { background-color: #0F172A; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
      border-right: 1px solid #334155;
  }

  /* ── Métricas / KPIs ── */
  [data-testid="stMetric"] {
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 1rem 1.5rem;
      box-shadow: 0 4px 24px rgba(0,0,0,.35);
  }
  [data-testid="stMetricLabel"]  { color: #94A3B8 !important; font-size: .85rem !important; }
  [data-testid="stMetricValue"]  { color: #F1F5F9 !important; font-size: 1.9rem !important; font-weight: 700 !important; }
  [data-testid="stMetricDelta"]  { color: #38BDF8 !important; }

  /* ── Títulos de sección ── */
  .section-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: #94A3B8;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin: 2rem 0 .5rem;
      padding-bottom: .4rem;
      border-bottom: 1px solid #334155;
  }

  /* ── Divider ── */
  hr { border-color: #334155 !important; }
</style>
"""

PLOTLY_THEME = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#1E293B",
    font=dict(color="#CBD5E1", family="Inter, system-ui, sans-serif"),
    xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
    legend=dict(bgcolor="#1E293B", bordercolor="#334155", borderwidth=1),
    margin=dict(l=20, r=20, t=50, b=20),
)


# ══════════════════════════════════════════════════════════════════════════════
# CARGA Y VALIDACIÓN DEL DATASET
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Cargando dataset…")
def cargar_datos() -> pd.DataFrame:
    """Carga el CSV y aplica tipos de datos básicos."""
    df = pd.read_csv(DATASET_PATH, parse_dates=["fecha"])

    # Asegurar que las columnas booleanas sean bool
    bool_cols = [
        "es_fin_de_semana", "es_feriado",
        "es_anomalia_operativa", "es_vacaciones_invierno",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    # Orden categórico para lluvia
    if "intensidad_lluvia" in df.columns:
        df["intensidad_lluvia"] = pd.Categorical(
            df["intensidad_lluvia"], categories=LLUVIA_ORDER, ordered=True
        )

    return df


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Monitor Movilidad CABA 2024",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CARD_CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE EXISTENCIA DEL DATASET
# ══════════════════════════════════════════════════════════════════════════════

if not DATASET_PATH.exists():
    st.error(
        "⚠️ **Dataset no encontrado.** "
        "Asegurate de que `dataset_maestro_FINAL_2024.csv` esté en el mismo directorio que `app.py`. "
        "Podés generarlo ejecutando: `python generate_dataset.py`"
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

try:
    df_raw = cargar_datos()
except Exception as e:
    st.error(f"❌ Error al leer el dataset: `{e}`")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — FILTROS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎛️ Filtros de Análisis")
    st.markdown("---")

    st.markdown("#### Segmentos a incluir")

    incluir_finde = st.toggle("Fines de semana", value=True)
    incluir_feriado = st.toggle("Feriados", value=True)

    st.markdown("---")
    st.markdown("#### Eventos atípicos")
    st.caption("Por defecto desactivados para analizar el comportamiento basal.")

    incluir_anomalia  = st.toggle("Anomalías operativas (paros/fallas)", value=False)
    incluir_vacaciones = st.toggle("Vacaciones de invierno", value=False)

    st.markdown("---")
    st.markdown("#### Rango temporal")
    fecha_min = df_raw["fecha"].min().date()
    fecha_max = df_raw["fecha"].max().date()
    rango_fechas = st.date_input(
        "Período",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#475569'>Datos sintéticos representativos · CABA 2024</small>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# APLICACIÓN DE FILTROS
# ══════════════════════════════════════════════════════════════════════════════

def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra el DataFrame según los toggles del sidebar."""
    mask = pd.Series(True, index=df.index)

    if not incluir_finde:
        mask &= ~df["es_fin_de_semana"]
    if not incluir_feriado:
        mask &= ~df["es_feriado"]
    if not incluir_anomalia:
        mask &= ~df["es_anomalia_operativa"]
    if not incluir_vacaciones:
        mask &= ~df["es_vacaciones_invierno"]

    # Rango de fechas
    if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
        f_ini, f_fin = pd.Timestamp(rango_fechas[0]), pd.Timestamp(rango_fechas[1])
        mask &= df["fecha"].between(f_ini, f_fin)

    return df[mask].copy()


df = aplicar_filtros(df_raw)

if df.empty:
    st.warning("⚠️ No hay datos con los filtros actuales. Ajustá los toggles del sidebar.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    "<h1 style='color:#F1F5F9; font-size:2rem; font-weight:800; margin-bottom:.2rem;'>"
    "🚇 Monitor Analítico de Movilidad y Clima — CABA 2024"
    "</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:#64748B; font-size:.9rem; margin-bottom:1.5rem;'>"
    f"Mostrando <b style='color:#38BDF8'>{len(df):,}</b> días · "
    f"Período: <b style='color:#38BDF8'>{df['fecha'].min().strftime('%d %b')}</b> → "
    f"<b style='color:#38BDF8'>{df['fecha'].max().strftime('%d %b %Y')}</b>"
    f"</p>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# KPIs — TARJETAS DE MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════

def formato_millones(valor: float) -> str:
    """Formatea un número como 'X.XX M' o 'XXX K'."""
    if valor >= 1_000_000:
        return f"{valor / 1_000_000:.2f} M"
    if valor >= 1_000:
        return f"{valor / 1_000:.1f} K"
    return f"{valor:,.0f}"


avg_col   = df["pax_colectivo"].mean()
avg_sub   = df["pax_subte_puro_bajo_tierra"].mean()
avg_auto  = df["autos_total"].mean()

# Comparar con el total del dataset sin filtros para el delta
base_col  = df_raw["pax_colectivo"].mean()
base_sub  = df_raw["pax_subte_puro_bajo_tierra"].mean()
base_auto = df_raw["autos_total"].mean()

kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.metric(
        label="🚌 Pasajeros Colectivo / día",
        value=formato_millones(avg_col),
        delta=f"{(avg_col/base_col - 1)*100:+.1f}% vs. total",
    )
with kpi2:
    st.metric(
        label="🚇 Pasajeros Subte / día",
        value=formato_millones(avg_sub),
        delta=f"{(avg_sub/base_sub - 1)*100:+.1f}% vs. total",
    )
with kpi3:
    st.metric(
        label="🚗 Autos en circulación / día",
        value=formato_millones(avg_auto),
        delta=f"{(avg_auto/base_auto - 1)*100:+.1f}% vs. total",
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 1 — IMPACTO DE LA LLUVIA (barras agrupadas)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">☔ El Impacto de la Lluvia sobre la Demanda</p>', unsafe_allow_html=True)

# Agrupar por intensidad de lluvia
lluvia_agg = (
    df.groupby("intensidad_lluvia", observed=True)[
        ["pax_colectivo", "pax_subte_puro_bajo_tierra", "autos_total"]
    ]
    .mean()
    .reset_index()
)

# Reshape a formato largo para px.bar agrupado
lluvia_long = lluvia_agg.melt(
    id_vars="intensidad_lluvia",
    value_vars=["pax_colectivo", "pax_subte_puro_bajo_tierra", "autos_total"],
    var_name="Modo",
    value_name="Promedio diario",
)
lluvia_long["Modo"] = lluvia_long["Modo"].map({
    "pax_colectivo": "Colectivo",
    "pax_subte_puro_bajo_tierra": "Subte Puro",
    "autos_total": "Autos",
})

fig1 = px.bar(
    lluvia_long,
    x="intensidad_lluvia",
    y="Promedio diario",
    color="Modo",
    barmode="group",
    category_orders={"intensidad_lluvia": LLUVIA_ORDER},
    color_discrete_map={
        "Colectivo":  COLOR_COLECTIVO,
        "Subte Puro": COLOR_SUBTE,
        "Autos":      COLOR_AUTO,
    },
    labels={"intensidad_lluvia": "Intensidad de Lluvia", "Promedio diario": "Promedio diario de pasajeros / autos"},
    title="Demanda promedio por intensidad de lluvia",
    text_auto=".3s",
)
fig1.update_traces(textposition="outside", textfont_size=11)
fig1.update_layout(**PLOTLY_THEME, title_font_size=16, bargap=0.25, bargroupgap=0.06)
fig1.update_yaxes(tickformat=".2s")

st.plotly_chart(fig1, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 2 — TEMPERATURA vs DEMANDA (scatter con tendencia)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">🌡️ Temperatura vs. Demanda de Subte (sin Línea D)</p>', unsafe_allow_html=True)

# Mapeamos intensidad_lluvia a un entero para el tamaño del punto
size_map = {"Sin lluvia": 5, "Lluvia leve": 9, "Lluvia moderada": 14, "Lluvia intensa": 20}
df_scatter = df.copy()
df_scatter["punto_tamaño"] = df_scatter["intensidad_lluvia"].map(size_map).fillna(5)

fig2 = px.scatter(
    df_scatter,
    x="temp_promedio",
    y="pax_subte_sin_linea_d",
    color="intensidad_lluvia",
    size="punto_tamaño",
    size_max=20,
    trendline="ols",
    trendline_scope="overall",
    trendline_color_override="#F43F5E",
    category_orders={"intensidad_lluvia": LLUVIA_ORDER},
    color_discrete_sequence=["#22D3EE", "#38BDF8", "#818CF8", "#A78BFA"],
    labels={
        "temp_promedio": "Temperatura Promedio (°C)",
        "pax_subte_sin_linea_d": "Pasajeros Subte sin Línea D",
        "intensidad_lluvia": "Lluvia",
    },
    title="Temperatura vs. Pasajeros de Subte · cada punto = 1 día",
    hover_data={"fecha": True, "lluvia_mm": ":.1f", "punto_tamaño": False},
)
fig2.update_layout(**PLOTLY_THEME, title_font_size=16)
fig2.update_yaxes(tickformat=".2s")

# Anotación sobre la línea de tendencia
fig2.add_annotation(
    xref="paper", yref="paper", x=0.98, y=0.05,
    text="<b>— Tendencia OLS</b>",
    showarrow=False,
    font=dict(color="#F43F5E", size=12),
    align="right",
)

st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 3 — EL LATIDO DE LA CIUDAD (líneas temporales, doble eje Y)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">📈 El Latido de la Ciudad — Evolución Temporal 2024</p>', unsafe_allow_html=True)

df_sorted = df.sort_values("fecha")

fig3 = go.Figure()

# Serie 1: Colectivos (eje Y izquierdo)
fig3.add_trace(go.Scatter(
    x=df_sorted["fecha"],
    y=df_sorted["pax_colectivo"],
    name="Colectivo",
    mode="lines",
    line=dict(color=COLOR_COLECTIVO, width=2),
    yaxis="y1",
    hovertemplate="<b>%{x|%d %b}</b><br>Colectivo: %{y:,.0f}<extra></extra>",
))

# Serie 2: Autos (eje Y derecho)
fig3.add_trace(go.Scatter(
    x=df_sorted["fecha"],
    y=df_sorted["autos_total"],
    name="Autos",
    mode="lines",
    line=dict(color=COLOR_AUTO, width=2, dash="dot"),
    yaxis="y2",
    hovertemplate="<b>%{x|%d %b}</b><br>Autos: %{y:,.0f}<extra></extra>",
))

fig3.update_layout(
    **PLOTLY_THEME,
    title=dict(text="Pasajeros de Colectivo y Flujo de Autos · Evolución diaria 2024", font_size=16),
    yaxis=dict(
        title="Pasajeros Colectivo",
        tickformat=".2s",
        gridcolor="#334155",
        color=COLOR_COLECTIVO,
        zerolinecolor="#334155",
    ),
    yaxis2=dict(
        title="Autos en circulación",
        tickformat=".2s",
        overlaying="y",
        side="right",
        color=COLOR_AUTO,
        gridcolor="rgba(0,0,0,0)",
        showgrid=False,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(
        gridcolor="#334155",
        zerolinecolor="#334155",
        # Range slider para zoom temporal
        rangeslider=dict(visible=True, bgcolor="#0F172A", bordercolor="#334155", thickness=0.06),
        rangeselector=dict(
            bgcolor="#1E293B",
            bordercolor="#334155",
            font=dict(color="#94A3B8"),
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all", label="Todo"),
            ],
        ),
    ),
    hovermode="x unified",
)

st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:.8rem;'>"
    "Monitor Analítico de Movilidad y Clima · CABA 2024 · "
    "Construido con Streamlit & Plotly"
    "</p>",
    unsafe_allow_html=True,
)
