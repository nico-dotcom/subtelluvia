"""
Script auxiliar: genera un dataset sintético representativo de CABA 2024
respetando el esquema y la metodología del Dataset Maestro oficial.

Ejecutar una sola vez si el archivo CSV no existe:
    python generate_dataset.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

OUTPUT = Path("dataset_maestro_FINAL_2024.csv")

np.random.seed(42)

# ── Fechas ────────────────────────────────────────────────────────────────────
fechas = pd.date_range("2024-01-01", "2024-12-31", freq="D")
n = len(fechas)

df = pd.DataFrame({"fecha": fechas})
df["mes"] = df["fecha"].dt.month
dow = df["fecha"].dt.dayofweek  # 0=Lun … 6=Dom

# ── dia_semana (String) ───────────────────────────────────────────────────────
nombres_dia = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
df["dia_semana"] = df["fecha"].dt.dayofweek.map(dict(enumerate(nombres_dia)))

# ── Flags booleanos ───────────────────────────────────────────────────────────
df["es_fin_de_semana"] = dow.isin([5, 6])

feriados_fechas = {
    "2024-01-01", "2024-02-12", "2024-02-13",
    "2024-03-24", "2024-03-28", "2024-03-29",
    "2024-04-02", "2024-05-01", "2024-05-25",
    "2024-06-17", "2024-06-20", "2024-07-09",
    "2024-08-17", "2024-10-12", "2024-11-18",
    "2024-12-08", "2024-12-25",
}
df["es_feriado"] = df["fecha"].dt.strftime("%Y-%m-%d").isin(feriados_fechas)

# Días puente / Jueves Santo
puentes = {"2024-03-28", "2024-06-21", "2024-10-11"}
df["es_dia_puente"] = df["fecha"].dt.strftime("%Y-%m-%d").isin(puentes)

# Vacaciones de invierno: 15-26 de julio
df["es_vacaciones_invierno"] = (df["mes"] == 7) & df["fecha"].dt.day.between(15, 26)

# Anomalías operativas (~12 días: paros + 1 día con falla de sensor el 31/12)
anomalias_idx = np.random.choice(np.where(~df["es_fin_de_semana"])[0], size=11, replace=False)
df["es_anomalia_operativa"] = False
df.loc[anomalias_idx, "es_anomalia_operativa"] = True
# 31/12 siempre es anomalía (falla de sensores documentada)
df.loc[df["fecha"] == "2024-12-31", "es_anomalia_operativa"] = True

# ── Clima (franja operativa del Subte: 05:30–23:50) ──────────────────────────
temp_media = 18 - 10 * np.cos(2 * np.pi * (df["mes"] - 1) / 12)
df["temp_promedio"] = np.round(temp_media + np.random.normal(0, 3, n), 1)

# Lluvia: categorías con prefijo numérico (facilitan el ordenamiento automático)
prob_lluvia = np.random.rand(n)
condiciones = [
    prob_lluvia < 0.50,
    (prob_lluvia >= 0.50) & (prob_lluvia < 0.70),
    (prob_lluvia >= 0.70) & (prob_lluvia < 0.85),
    prob_lluvia >= 0.85,
]
categorias = ["0. Sin Lluvia", "1. Lluvia Leve", "2. Moderada", "3. Temporal Fuerte"]
df["intensidad_lluvia"] = np.select(condiciones, categorias, default="0. Sin Lluvia")

mm_base = {"0. Sin Lluvia": 0, "1. Lluvia Leve": 2.5, "2. Moderada": 12, "3. Temporal Fuerte": 38}
ruido_mm = {"0. Sin Lluvia": 0, "1. Lluvia Leve": 2, "2. Moderada": 6, "3. Temporal Fuerte": 18}
df["lluvia_total_mm"] = df["intensidad_lluvia"].apply(
    lambda x: max(0, mm_base[x] + np.random.normal(0, ruido_mm[x]))
)
df["lluvia_total_mm"] = np.round(df["lluvia_total_mm"], 1)

# ── Hora operativa (aprox.) ───────────────────────────────────────────────────
# Viernes y sábado el servicio termina pasada la medianoche
hora_inicio_base = "05:30:00"
df["hora_inicio"] = hora_inicio_base

hora_fin_mapa = {
    "Lunes": "23:10:00", "Martes": "23:10:00", "Miércoles": "23:10:00",
    "Jueves": "23:10:00", "Viernes": "01:00:00", "Sábado": "01:00:00",
    "Domingo": "22:00:00",
}
df["hora_fin"] = df["dia_semana"].map(hora_fin_mapa)

# ── Demanda de transporte ─────────────────────────────────────────────────────
# Base: laboral vs fin de semana / feriado
es_no_laboral = df["es_fin_de_semana"] | df["es_feriado"] | df["es_dia_puente"]

base_colectivo = np.where(es_no_laboral, 2_800_000, 5_200_000)
base_subte     = np.where(es_no_laboral,   550_000, 1_250_000)
base_autos_c   = np.where(es_no_laboral,   180_000,   410_000)  # hacia centro
base_autos_p   = np.where(es_no_laboral,   200_000,   310_000)  # hacia provincia

# Factor lluvia (metodología: destrucción de demanda en Temporal Fuerte)
fac_lluv_col  = {"0. Sin Lluvia": 1.00, "1. Lluvia Leve": 1.03, "2. Moderada": 1.08, "3. Temporal Fuerte": 0.73}
fac_lluv_sub  = {"0. Sin Lluvia": 1.00, "1. Lluvia Leve": 1.04, "2. Moderada": 1.10, "3. Temporal Fuerte": 0.75}
fac_lluv_auto = {"0. Sin Lluvia": 1.00, "1. Lluvia Leve": 0.97, "2. Moderada": 0.92, "3. Temporal Fuerte": 0.70}

f_col  = df["intensidad_lluvia"].map(fac_lluv_col)
f_sub  = df["intensidad_lluvia"].map(fac_lluv_sub)
f_auto = df["intensidad_lluvia"].map(fac_lluv_auto)

# Factor temperatura (calor extremo reduce subte)
factor_temp = np.where(df["temp_promedio"] > 28, 0.93, 1.0)

# Factor vacaciones invierno (–25%)
factor_vac = np.where(df["es_vacaciones_invierno"], 0.75, 1.0)

# Factor anomalías (–40% transporte público, +25% autos por sustitución parcial)
factor_anom_pub  = np.where(df["es_anomalia_operativa"], 0.60, 1.0)
factor_anom_auto = np.where(df["es_anomalia_operativa"], 1.25, 1.0)

# Tendencia anual leve (+3%)
tendencia = 1 + (df["fecha"].dt.dayofyear - 1) / 365 * 0.03

# Factor sesgo Línea D: cerrada enero–principios de marzo por obras
# La Línea D aporta ~22% del total del subte
factor_cierre_linea_d = np.where(
    (df["mes"] == 1) | (df["mes"] == 2) | ((df["mes"] == 3) & (df["fecha"].dt.day <= 10)),
    0.78, 1.0
)

noise = lambda s: np.random.normal(1, s, n)

df["pax_colectivo"] = np.round(
    base_colectivo * f_col * factor_vac * factor_anom_pub * tendencia * noise(0.04)
).astype(int)

pax_sub_full = np.round(
    base_subte * f_sub * factor_temp * factor_vac * factor_anom_pub * tendencia * noise(0.05)
).astype(int)

# pax_subte_puro_bajo_tierra: excluye Premetro (~5% del total)
df["pax_subte_puro_bajo_tierra"] = np.round(pax_sub_full * 0.95 * noise(0.01)).astype(int)

# pax_subte_sin_linea_d: excluye Línea D siempre + cierre de obra en verano
# Línea D = ~22% del total, pero 0% cuando está cerrada (ya descontado en base)
linea_d_proporcion = np.where(factor_cierre_linea_d < 1, 0, 0.22)
df["pax_subte_sin_linea_d"] = np.round(
    pax_sub_full * (1 - linea_d_proporcion) * noise(0.02)
).astype(int)

# pax_subte_total: red completa (incluye Premetro y Línea D con sesgo de obra)
df["pax_subte_total"] = np.round(
    pax_sub_full * factor_cierre_linea_d * noise(0.01)
).astype(int)

# Autos (con decimales por coeficiente de ajuste de sensores)
autos_c = base_autos_c * f_auto * factor_anom_auto * tendencia * noise(0.05)
autos_p = base_autos_p * f_auto * factor_anom_auto * tendencia * noise(0.05)
df["autos_hacia_centro"]   = np.round(autos_c, 1)
df["autos_hacia_provincia"] = np.round(autos_p, 1)
df["autos_total"]           = np.round(autos_c + autos_p, 1)

# ── Guardar ───────────────────────────────────────────────────────────────────
col_order = [
    "fecha", "temp_promedio", "lluvia_total_mm", "hora_inicio", "hora_fin",
    "dia_semana", "es_feriado", "es_dia_puente", "es_fin_de_semana",
    "es_vacaciones_invierno", "es_anomalia_operativa", "intensidad_lluvia",
    "pax_colectivo", "pax_subte_total", "pax_subte_sin_linea_d",
    "pax_subte_puro_bajo_tierra", "autos_hacia_centro", "autos_hacia_provincia",
    "autos_total",
]
df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
df[col_order].to_csv(OUTPUT, index=False)
print(f"Dataset generado: {OUTPUT} ({len(df)} filas, {len(col_order)} columnas)")
print(df[col_order].head(3).to_string())
