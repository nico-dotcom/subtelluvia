"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Monitor Analítico de Movilidad y Clima - CABA 2024                         ║
║  Dashboard Streamlit + Plotly                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

DATASET_PATH = Path("dataset_maestro_FINAL_2024.csv")

# Orden canónico de intensidad (prefijo numérico → orden automático)
LLUVIA_ORDER = ["0. Sin Lluvia", "1. Lluvia Leve", "2. Moderada", "3. Temporal Fuerte"]
LLUVIA_LABELS = {
    "0. Sin Lluvia":      "Sin Lluvia",
    "1. Lluvia Leve":     "Lluvia Leve",
    "2. Moderada":        "Moderada",
    "3. Temporal Fuerte": "Temporal Fuerte",
}

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
  [data-testid="stMetricLabel"] { color: #94A3B8 !important; font-size: .85rem !important; }
  [data-testid="stMetricValue"] { color: #F1F5F9 !important; font-size: 1.9rem !important; font-weight: 700 !important; }
  [data-testid="stMetricDelta"] { color: #38BDF8 !important; }

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

  /* ── Pill informativa ── */
  .info-pill {
      display: inline-block;
      background: #1E3A5F;
      color: #7DD3FC;
      border: 1px solid #1D4ED8;
      border-radius: 999px;
      padding: .15rem .7rem;
      font-size: .75rem;
      font-weight: 600;
  }

  hr { border-color: #334155 !important; }
</style>
"""

# Layout base para todos los gráficos Plotly
PLOTLY_BASE = dict(
    paper_bgcolor="#1E293B",
    plot_bgcolor="#1E293B",
    font=dict(color="#CBD5E1", family="Inter, system-ui, sans-serif"),
    legend=dict(bgcolor="#1E293B", bordercolor="#334155", borderwidth=1),
    margin=dict(l=20, r=20, t=55, b=20),
)

AXIS_STYLE = dict(gridcolor="#334155", zerolinecolor="#334155")


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DEL DATASET
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Cargando dataset…")
def cargar_datos() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH, parse_dates=["fecha"])

    # Tipos booleanos robustos (el CSV puede traer strings "True"/"False")
    bool_cols = [
        "es_fin_de_semana", "es_feriado", "es_dia_puente",
        "es_anomalia_operativa", "es_vacaciones_invierno",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower() == "true"

    # Orden categórico para intensidad de lluvia
    if "intensidad_lluvia" in df.columns:
        df["intensidad_lluvia"] = pd.Categorical(
            df["intensidad_lluvia"],
            categories=[c for c in LLUVIA_ORDER if c in df["intensidad_lluvia"].unique()],
            ordered=True,
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
# VERIFICACIÓN DEL DATASET
# ══════════════════════════════════════════════════════════════════════════════

if not DATASET_PATH.exists():
    st.error(
        "⚠️ **Dataset no encontrado.**  \n"
        "Asegurate de que `dataset_maestro_FINAL_2024.csv` esté en el mismo directorio que `app.py`.  \n"
        "Podés generar un dataset de prueba ejecutando: `python generate_dataset.py`"
    )
    st.stop()

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

    st.markdown("#### ✅ Segmentos a incluir")
    incluir_finde    = st.toggle("Fines de semana",  value=True)
    incluir_feriado  = st.toggle("Feriados",          value=True)
    incluir_puente   = st.toggle("Días puente",       value=True)

    st.markdown("---")
    st.markdown("#### ⚠️ Eventos atípicos")
    st.caption("Desactivados por defecto — para medir el comportamiento basal.")
    incluir_anomalia   = st.toggle("Anomalías operativas (paros / fallas)", value=False)
    incluir_vacaciones = st.toggle("Vacaciones de invierno",                 value=False)

    st.markdown("---")
    st.markdown("#### 📅 Rango temporal")
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
        "<small style='color:#475569'>"
        "Dataset Maestro de Movilidad y Clima · CABA 2024  \n"
        "Franja operativa: 05:30 – 23:50 hs"
        "</small>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# APLICACIÓN DE FILTROS
# ══════════════════════════════════════════════════════════════════════════════

def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)

    if not incluir_finde:
        mask &= ~df["es_fin_de_semana"]
    if not incluir_feriado:
        mask &= ~df["es_feriado"]
    if "es_dia_puente" in df.columns and not incluir_puente:
        mask &= ~df["es_dia_puente"]
    if not incluir_anomalia:
        mask &= ~df["es_anomalia_operativa"]
    if not incluir_vacaciones:
        mask &= ~df["es_vacaciones_invierno"]

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

n_dias = len(df)
pct_habiles = (~df["es_fin_de_semana"] & ~df["es_feriado"]).mean() * 100

st.markdown(
    "<h1 style='color:#F1F5F9; font-size:2rem; font-weight:800; margin-bottom:.2rem;'>"
    "🚇 Monitor Analítico de Movilidad y Clima — CABA 2024"
    "</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:#64748B; font-size:.9rem; margin-bottom:.3rem;'>"
    f"<span class='info-pill'>{n_dias} días</span>&nbsp; "
    f"<span class='info-pill'>{pct_habiles:.0f}% hábiles</span>&nbsp; "
    f"Período: <b style='color:#38BDF8'>{df['fecha'].min().strftime('%d %b')}</b>"
    f" → <b style='color:#38BDF8'>{df['fecha'].max().strftime('%d %b %Y')}</b>"
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KPIs — TARJETAS DE MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════

def fmt_m(v: float) -> str:
    """Formatea un número como '5.12 M' o '890 K'."""
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} M"
    if v >= 1_000:
        return f"{v / 1_000:.1f} K"
    return f"{v:,.0f}"


avg_col  = df["pax_colectivo"].mean()
avg_sub  = df["pax_subte_puro_bajo_tierra"].mean()
avg_auto = df["autos_total"].mean()

# Delta respecto al promedio del dataset completo (sin filtros)
base_col  = df_raw["pax_colectivo"].mean()
base_sub  = df_raw["pax_subte_puro_bajo_tierra"].mean()
base_auto = df_raw["autos_total"].mean()

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(
        label="🚌 Pasajeros Colectivo / día",
        value=fmt_m(avg_col),
        delta=f"{(avg_col / base_col - 1) * 100:+.1f}% vs. promedio anual",
    )
with kpi2:
    st.metric(
        label="🚇 Pasajeros Subte (bajo tierra) / día",
        value=fmt_m(avg_sub),
        delta=f"{(avg_sub / base_sub - 1) * 100:+.1f}% vs. promedio anual",
    )
with kpi3:
    st.metric(
        label="🚗 Flujo de Autos / día",
        value=fmt_m(avg_auto),
        delta=f"{(avg_auto / base_auto - 1) * 100:+.1f}% vs. promedio anual",
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 1 — IMPACTO DE LA LLUVIA (barras agrupadas)
# ══════════════════════════════════════════════════════════════════════════════
# Pregunta central: ¿la lluvia traslada demanda o la destruye?
# En Temporal Fuerte, los tres modos caen ~25-35% (destrucción, no traslado).
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">☔ El Impacto de la Lluvia sobre la Demanda</p>', unsafe_allow_html=True)

lluvia_agg = (
    df.groupby("intensidad_lluvia", observed=True)[
        ["pax_colectivo", "pax_subte_puro_bajo_tierra", "autos_total"]
    ]
    .mean()
    .reset_index()
)

# Etiquetas cortas para el eje X
lluvia_agg["lluvia_label"] = lluvia_agg["intensidad_lluvia"].map(LLUVIA_LABELS)

lluvia_long = lluvia_agg.melt(
    id_vars=["intensidad_lluvia", "lluvia_label"],
    value_vars=["pax_colectivo", "pax_subte_puro_bajo_tierra", "autos_total"],
    var_name="Modo",
    value_name="Promedio diario",
)
lluvia_long["Modo"] = lluvia_long["Modo"].map({
    "pax_colectivo":               "Colectivo",
    "pax_subte_puro_bajo_tierra":  "Subte (bajo tierra)",
    "autos_total":                 "Autos",
})

# Mantener el orden correcto en X
label_order = [LLUVIA_LABELS[c] for c in LLUVIA_ORDER if c in lluvia_agg["intensidad_lluvia"].values]

fig1 = px.bar(
    lluvia_long,
    x="lluvia_label",
    y="Promedio diario",
    color="Modo",
    barmode="group",
    category_orders={"lluvia_label": label_order},
    color_discrete_map={
        "Colectivo":            COLOR_COLECTIVO,
        "Subte (bajo tierra)":  COLOR_SUBTE,
        "Autos":                COLOR_AUTO,
    },
    labels={"lluvia_label": "Intensidad de Lluvia", "Promedio diario": "Promedio diario"},
    title="Demanda promedio por categoría de lluvia — ¿Traslado o Destrucción?",
    text_auto=".3s",
)
fig1.update_traces(textposition="outside", textfont_size=11)
fig1.update_layout(
    **PLOTLY_BASE,
    title_font_size=15,
    bargap=0.25,
    bargroupgap=0.06,
    xaxis=AXIS_STYLE,
    yaxis={**AXIS_STYLE, "tickformat": ".2s"},
)

st.plotly_chart(fig1, use_container_width=True)

# Insight automático
if len(lluvia_agg) >= 2:
    sin_lluvia = lluvia_agg[lluvia_agg["intensidad_lluvia"] == "0. Sin Lluvia"]
    temporal   = lluvia_agg[lluvia_agg["intensidad_lluvia"] == "3. Temporal Fuerte"]
    if not sin_lluvia.empty and not temporal.empty:
        delta_col  = (temporal["pax_colectivo"].values[0] / sin_lluvia["pax_colectivo"].values[0] - 1) * 100
        delta_auto = (temporal["autos_total"].values[0] / sin_lluvia["autos_total"].values[0] - 1) * 100
        veredicto  = "🔴 Destrucción de demanda" if delta_auto < -10 else "🟡 Cambio modal parcial"
        st.info(
            f"**{veredicto}** · En Temporal Fuerte: Colectivo {delta_col:+.1f}% · "
            f"Autos {delta_auto:+.1f}% respecto a días sin lluvia."
        )

st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 2 — TEMPERATURA vs DEMANDA DE SUBTE (scatter con OLS)
# ══════════════════════════════════════════════════════════════════════════════
# Usamos pax_subte_sin_linea_d para evitar el sesgo de la obra en ene-mar.
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">🌡️ Temperatura vs. Demanda de Subte (sin Línea D)</p>', unsafe_allow_html=True)

# Tamaño del punto según intensidad de lluvia (escala visual)
size_map = {"0. Sin Lluvia": 5, "1. Lluvia Leve": 9, "2. Moderada": 14, "3. Temporal Fuerte": 20}
df_sc = df.copy()
df_sc["tamaño"] = df_sc["intensidad_lluvia"].map(size_map).fillna(5)
df_sc["lluvia_label"] = df_sc["intensidad_lluvia"].map(LLUVIA_LABELS).fillna(df_sc["intensidad_lluvia"].astype(str))

fig2 = px.scatter(
    df_sc,
    x="temp_promedio",
    y="pax_subte_sin_linea_d",
    color="lluvia_label",
    size="tamaño",
    size_max=22,
    trendline="ols",
    trendline_scope="overall",
    trendline_color_override="#F43F5E",
    category_orders={"lluvia_label": [LLUVIA_LABELS[c] for c in LLUVIA_ORDER]},
    color_discrete_sequence=["#22D3EE", "#38BDF8", "#818CF8", "#A78BFA"],
    labels={
        "temp_promedio":           "Temperatura Promedio (°C)",
        "pax_subte_sin_linea_d":   "Pasajeros Subte sin Línea D",
        "lluvia_label":            "Lluvia",
    },
    title="Temperatura vs. Pasajeros de Subte · cada punto = 1 día · sin Línea D (evita sesgo de obra)",
    hover_data={"fecha": True, "lluvia_total_mm": ":.1f", "tamaño": False},
)
fig2.update_layout(
    **PLOTLY_BASE,
    title_font_size=15,
    xaxis=AXIS_STYLE,
    yaxis={**AXIS_STYLE, "tickformat": ".2s"},
)
fig2.add_annotation(
    xref="paper", yref="paper", x=0.98, y=0.05,
    text="<b>— Tendencia OLS</b>",
    showarrow=False,
    font=dict(color="#F43F5E", size=12),
    align="right",
)

st.plotly_chart(fig2, use_container_width=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO 3 — EL LATIDO DE LA CIUDAD (serie temporal dual-axis)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-title">📈 El Latido de la Ciudad — Evolución Temporal 2024</p>', unsafe_allow_html=True)

df_sorted = df.sort_values("fecha")

fig3 = go.Figure()

# Serie 1: Colectivos → eje Y izquierdo
fig3.add_trace(go.Scatter(
    x=df_sorted["fecha"],
    y=df_sorted["pax_colectivo"],
    name="Colectivo",
    mode="lines",
    line=dict(color=COLOR_COLECTIVO, width=2),
    yaxis="y1",
    hovertemplate="<b>%{x|%d %b}</b><br>Colectivo: %{y:,.0f}<extra></extra>",
))

# Serie 2: Autos → eje Y derecho
fig3.add_trace(go.Scatter(
    x=df_sorted["fecha"],
    y=df_sorted["autos_total"],
    name="Autos (total)",
    mode="lines",
    line=dict(color=COLOR_AUTO, width=2, dash="dot"),
    yaxis="y2",
    hovertemplate="<b>%{x|%d %b}</b><br>Autos: %{y:,.0f}<extra></extra>",
))

fig3.update_layout(
    **PLOTLY_BASE,
    title=dict(
        text="Pasajeros Colectivo y Flujo de Autos · Evolución diaria 2024",
        font_size=15,
    ),
    yaxis=dict(
        title="Pasajeros Colectivo",
        tickformat=".2s",
        gridcolor="#334155",
        zerolinecolor="#334155",
        color=COLOR_COLECTIVO,
    ),
    yaxis2=dict(
        title="Autos en circulación",
        tickformat=".2s",
        overlaying="y",
        side="right",
        color=COLOR_AUTO,
        showgrid=False,
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="right",  x=1,
        bgcolor="#1E293B", bordercolor="#334155", borderwidth=1,
    ),
    xaxis=dict(
        gridcolor="#334155",
        zerolinecolor="#334155",
        rangeslider=dict(
            visible=True,
            bgcolor="#0F172A",
            bordercolor="#334155",
            thickness=0.06,
        ),
        rangeselector=dict(
            bgcolor="#1E293B",
            bordercolor="#334155",
            font=dict(color="#94A3B8"),
            buttons=[
                dict(count=1,  label="1M",  step="month", stepmode="backward"),
                dict(count=3,  label="3M",  step="month", stepmode="backward"),
                dict(count=6,  label="6M",  step="month", stepmode="backward"),
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
    "Construido con Streamlit &amp; Plotly · "
    "Franja operativa: 05:30–23:50 hs"
    "</p>",
    unsafe_allow_html=True,
)
