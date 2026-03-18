"""
Script auxiliar para generar un dataset sintético representativo de CABA 2024.
Se ejecuta una sola vez si el archivo CSV no existe.
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
df["dia_semana"] = df["fecha"].dt.dayofweek          # 0=Lun … 6=Dom
df["mes"] = df["fecha"].dt.month

# ── Flags booleanos ───────────────────────────────────────────────────────────
df["es_fin_de_semana"] = df["dia_semana"].isin([5, 6])

feriados = [
    "2024-01-01", "2024-02-12", "2024-02-13",
    "2024-03-24", "2024-03-28", "2024-03-29",
    "2024-04-02", "2024-05-01", "2024-05-25",
    "2024-06-17", "2024-06-20", "2024-07-09",
    "2024-08-17", "2024-10-12", "2024-11-18",
    "2024-12-08", "2024-12-25",
]
df["es_feriado"] = df["fecha"].dt.strftime("%Y-%m-%d").isin(feriados)

# Vacaciones de invierno: semana del 15 al 26 de julio
df["es_vacaciones_invierno"] = (df["mes"] == 7) & df["fecha"].dt.day.between(15, 26)

# Anomalías operativas (paros/fallas): ~12 días aleatorios
anomalias_idx = np.random.choice(n, size=12, replace=False)
df["es_anomalia_operativa"] = False
df.loc[anomalias_idx, "es_anomalia_operativa"] = True

# ── Clima ─────────────────────────────────────────────────────────────────────
# Temperatura con estacionalidad (hemisferio sur)
temp_media = 18 - 10 * np.cos(2 * np.pi * (df["mes"] - 1) / 12)
df["temp_promedio"] = np.round(temp_media + np.random.normal(0, 3, n), 1)
df["temp_max"] = np.round(df["temp_promedio"] + np.random.uniform(3, 7, n), 1)
df["temp_min"] = np.round(df["temp_promedio"] - np.random.uniform(3, 7, n), 1)
df["humedad_media"] = np.round(np.clip(60 + np.random.normal(0, 12, n), 30, 100), 1)

# Lluvia: categorías
prob_lluvia = np.random.rand(n)
condiciones = [
    prob_lluvia < 0.50,
    (prob_lluvia >= 0.50) & (prob_lluvia < 0.70),
    (prob_lluvia >= 0.70) & (prob_lluvia < 0.85),
    prob_lluvia >= 0.85,
]
categorias = ["Sin lluvia", "Lluvia leve", "Lluvia moderada", "Lluvia intensa"]
df["intensidad_lluvia"] = np.select(condiciones, categorias, default="Sin lluvia")

lluvia_mm = {
    "Sin lluvia": 0,
    "Lluvia leve": lambda: np.random.uniform(0.1, 5, 1)[0],
    "Lluvia moderada": lambda: np.random.uniform(5, 20, 1)[0],
    "Lluvia intensa": lambda: np.random.uniform(20, 60, 1)[0],
}
df["lluvia_mm"] = df["intensidad_lluvia"].apply(
    lambda x: 0 if x == "Sin lluvia" else lluvia_mm[x]()
)
df["lluvia_mm"] = np.round(df["lluvia_mm"], 1)

# ── Demanda de transporte ─────────────────────────────────────────────────────
# Base: laboral vs fin de semana / feriado
base_colectivo = np.where(df["es_fin_de_semana"] | df["es_feriado"], 2_800_000, 5_200_000)
base_subte     = np.where(df["es_fin_de_semana"] | df["es_feriado"], 550_000,  1_250_000)
base_autos     = np.where(df["es_fin_de_semana"] | df["es_feriado"], 380_000,   720_000)

# Efecto lluvia sobre colectivos (+) y subte (+) y autos (-)
factor_lluvia_col  = {"Sin lluvia": 1.00, "Lluvia leve": 1.03, "Lluvia moderada": 1.08, "Lluvia intensa": 1.14}
factor_lluvia_sub  = {"Sin lluvia": 1.00, "Lluvia leve": 1.04, "Lluvia moderada": 1.10, "Lluvia intensa": 1.18}
factor_lluvia_auto = {"Sin lluvia": 1.00, "Lluvia leve": 0.97, "Lluvia moderada": 0.91, "Lluvia intensa": 0.82}

f_col  = df["intensidad_lluvia"].map(factor_lluvia_col)
f_sub  = df["intensidad_lluvia"].map(factor_lluvia_sub)
f_auto = df["intensidad_lluvia"].map(factor_lluvia_auto)

# Efecto temperatura sobre subte (baja en calor extremo por la Línea D en obras)
factor_temp = np.where(df["temp_promedio"] > 28, 0.93, 1.0)

# Efecto vacaciones invierno (–25 %)
factor_vac = np.where(df["es_vacaciones_invierno"], 0.75, 1.0)

# Efecto anomalías (–40 % transporte público)
factor_anom_pub  = np.where(df["es_anomalia_operativa"], 0.60, 1.0)
factor_anom_auto = np.where(df["es_anomalia_operativa"], 1.25, 1.0)  # se van al auto

# Tendencia mensual leve (crecimiento anual ~3 %)
tendencia = 1 + (df["fecha"].dt.dayofyear - 1) / 365 * 0.03

# Columna pax_subte_sin_linea_d (excluye la Línea D para evitar sesgo de obra)
# La Línea D aporta ~22% del total; en verano baja extra por la obra
factor_linea_d = np.where(
    df["mes"].isin([1, 2, 12]),
    0.78 * 0.85,   # sin línea D + obra en verano
    0.78           # sin línea D
)

# Construcción final con ruido
noise = lambda s: np.random.normal(1, s, n)

df["pax_colectivo"] = np.round(
    base_colectivo * f_col * factor_vac * factor_anom_pub * tendencia * noise(0.04)
).astype(int)

df["pax_subte_puro_bajo_tierra"] = np.round(
    base_subte * f_sub * factor_temp * factor_vac * factor_anom_pub * tendencia * noise(0.05)
).astype(int)

df["pax_subte_sin_linea_d"] = np.round(
    df["pax_subte_puro_bajo_tierra"] * factor_linea_d * noise(0.02)
).astype(int)

df["autos_total"] = np.round(
    base_autos * f_auto * factor_anom_auto * tendencia * noise(0.05)
).astype(int)

# ── Guardar ───────────────────────────────────────────────────────────────────
df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
df.to_csv(OUTPUT, index=False)
print(f"Dataset generado: {OUTPUT} ({len(df)} filas, {len(df.columns)} columnas)")
print(df.head(3).to_string())
