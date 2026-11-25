import os, gzip
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel, Matern

# Style configuration
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_dir = os.path.abspath(os.path.join("notebooks", "figures"))
os.makedirs(fig_dir, exist_ok=True)

DATA_DIR = os.path.join("dataset", "mimic4wdb")
files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("n.csv.gz")])

TICKS_PER_SECOND = 999.56
NBP_COLS = ["NBPs [mmHg]", "NBPd [mmHg]"]
ABP_COLS = ["ABPs [mmHg]", "ABPd [mmHg]"]
CORE_SIGNALS = ["HR [bpm]", "RR [rpm]", "SpO2 [%]", "NBPs [mmHg]", "NBPd [mmHg]"]

print("1. Computing stats across stays...")
patient_rows = []
all_gaps_min = []

for f in files:
    fpath = os.path.join(DATA_DIR, f)
    cols = pd.read_csv(fpath, nrows=1).columns.tolist()
    use_cols = [c for c in cols if c == "time" or c in CORE_SIGNALS or c in ABP_COLS]
    df = pd.read_csv(fpath, usecols=use_cols)
    
    dur_h = (df["time"].max() - df["time"].min()) / TICKS_PER_SECOND / 3600
    hour_blocks = ((df["time"] - df["time"].min()) / TICKS_PER_SECOND / 3600).astype(int)
    n_blocks = hour_blocks.max() + 1
    
    has_nbp = "NBPs [mmHg]" in df.columns and df["NBPs [mmHg]"].notna().sum() > 0
    cuff_rows = df["NBPs [mmHg]"].notna().sum() if has_nbp else 0
    has_abp = "ABPs [mmHg]" in df.columns and df["ABPs [mmHg]"].notna().sum() > 0
    abp_rows = df["ABPs [mmHg]"].notna().sum() if has_abp else 0
    
    cov_with_copies = round(100 * hour_blocks[df["NBPs [mmHg]"].notna()].nunique() / n_blocks, 1) if has_nbp else 0.0
    
    if has_nbp:
        cuff = df.dropna(subset=["NBPs [mmHg]"]).sort_values("time")
        vals = cuff[[c for c in NBP_COLS if c in cuff.columns]].fillna(-1)
        changed = vals.ne(vals.shift()).any(axis=1)
        real_cuff = cuff.loc[changed]
        n_real = len(real_cuff)
        
        real_hour_blocks = ((real_cuff["time"] - df["time"].min()) / TICKS_PER_SECOND / 3600).astype(int)
        cov_real = round(100 * real_hour_blocks.nunique() / n_blocks, 1)
        
        real_m = real_cuff["time"] / TICKS_PER_SECOND / 60
        gaps = real_m.diff().dropna().values
        all_gaps_min.extend(gaps[gaps > 0])
        med_gap = np.median(gaps) if len(gaps) > 0 else 0
    else:
        n_real = 0
        cov_real = 0.0
        med_gap = 0
        
    patient_rows.append({
        "file": f,
        "patient": f.split("_")[0],
        "duration_h": dur_h,
        "cov_with_copies": cov_with_copies,
        "cov_real": cov_real,
        "cuff_rows": cuff_rows,
        "n_real": n_real,
        "repeats_pct": 100 * (1 - n_real / cuff_rows) if cuff_rows > 0 else 0,
        "has_abp": has_abp,
        "abp_rows": abp_rows,
        "med_gap": med_gap,
        "included_d4": (dur_h >= 12.0) and (cov_real >= 80.0)
    })

p_df = pd.DataFrame(patient_rows)
all_gaps = np.array(all_gaps_min)

# ==============================================================================
# PLOT 1: COBERTURA REAL DE NBP Y SESGO DE LÍNEA ARTERIAL (ABP)
# ==============================================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

# 1A: With copies vs Real NBP coverage
p_df_sorted = p_df.sort_values("duration_h", ascending=False).reset_index(drop=True)
x = np.arange(len(p_df_sorted))
width = 0.38

axes[0].bar(x - width/2, p_df_sorted["cov_with_copies"], width, label="Con copias del monitor", color="#90CAF9", edgecolor="#1565C0")
axes[0].bar(x + width/2, p_df_sorted["cov_real"], width, label="Mediciones reales (sin copias)", color="#1976D2", edgecolor="#0D47A1")
axes[0].axhline(80, color="#D32F2F", linestyle="--", linewidth=1.5, label="Umbral D4 (≥ 80%)")
axes[0].set_xticks(x)
axes[0].set_xticklabels(p_df_sorted["patient"], rotation=45, ha='right', fontsize=9)
axes[0].set_ylabel("Cobertura por hora (%)", fontsize=11, fontweight='bold')
axes[0].set_title("(1A) Cobertura NBP: Copias vs. Reales", fontsize=12, fontweight='bold')
axes[0].legend(loc="lower left", fontsize=9)
axes[0].set_ylim(0, 110)

# 1B: Sensitivity of stays passing D4 (>=12h) at different coverage thresholds
thresholds = [70, 80, 85, 90]
pass_copies = [( (p_df["duration_h"] >= 12) & (p_df["cov_with_copies"] >= t) ).sum() for t in thresholds]
pass_real = [( (p_df["duration_h"] >= 12) & (p_df["cov_real"] >= t) ).sum() for t in thresholds]

x_t = np.arange(len(thresholds))
axes[1].bar(x_t - width/2, pass_copies, width, label="Con copias", color="#A5D6A7", edgecolor="#2E7D32")
axes[1].bar(x_t + width/2, pass_real, width, label="Mediciones reales", color="#388E3C", edgecolor="#1B5E20")
for i in range(len(thresholds)):
    axes[1].text(x_t[i] - width/2, pass_copies[i] + 0.1, str(pass_copies[i]), ha='center', va='bottom', fontweight='bold')
    axes[1].text(x_t[i] + width/2, pass_real[i] + 0.1, str(pass_real[i]), ha='center', va='bottom', fontweight='bold')
axes[1].set_xticks(x_t)
axes[1].set_xticklabels([f"≥ {t}%" for t in thresholds])
axes[1].set_ylabel("Pacientes elegibles (de 10)", fontsize=11, fontweight='bold')
axes[1].set_title("(1B) Impacto del Filtro D4 (≥12h) en Cohorte", fontsize=12, fontweight='bold')
axes[1].legend(loc="upper right", fontsize=9)
axes[1].set_ylim(0, max(pass_copies) + 1.5)

# 1C: Clinical Bias: Included vs Excluded by D4 -> Arterial Line Presence!
# Patients with duration >= 12h: included vs excluded
d12_pts = p_df[p_df["duration_h"] >= 12.0].copy()
d12_pts["grupo"] = np.where(d12_pts["cov_real"] >= 80.0, "Incluidos (D4 >= 80%)", "Excluidos (D4 < 80%)")
bias_agg = d12_pts.groupby("grupo").agg(
    total=("patient", "count"),
    con_abp=("has_abp", "sum"),
    abp_pct=("has_abp", lambda s: 100 * s.mean()),
    abp_filas_media=("abp_rows", "mean")
).reset_index()

colors_bias = ["#2E7D32" if "Incluidos" in g else "#C62828" for g in bias_agg["grupo"]]
bars = axes[2].bar(bias_agg["grupo"], bias_agg["abp_pct"], color=colors_bias, width=0.5, edgecolor="black")
for bar, total, count in zip(bars, bias_agg["total"], bias_agg["con_abp"]):
    yval = bar.get_height()
    axes[2].text(bar.get_x() + bar.get_width()/2, yval + 2, f"{yval:.0f}% ({count}/{total} pacientes)", ha='center', va='bottom', fontweight='bold', fontsize=10)
axes[2].set_ylabel("% Pacientes con Línea Arterial (ABP)", fontsize=11, fontweight='bold')
axes[2].set_title("(1C) Sesgo Clínico: Línea Arterial en Excluidos", fontsize=12, fontweight='bold')
axes[2].set_ylim(0, 115)

plt.suptitle("Verificación D4: Cobertura Real NBP y Documentación de Sesgo Clínico", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig1_path = os.path.join(fig_dir, "01_nbp_real_coverage_and_bias.png")
plt.savefig(fig1_path, dpi=200, bbox_inches='tight')
plt.close()
print(f"Saved: {fig1_path}")

# ==============================================================================
# PLOT 2: DISTRIBUCIÓN DE GAPS DE PRESIÓN NBP
# ==============================================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Filter gaps < 180 min for readable histogram (focus on operational ICU intervals)
normal_gaps = all_gaps[all_gaps <= 120]
med = np.median(all_gaps)
p75 = np.percentile(all_gaps, 75)
p90 = np.percentile(all_gaps, 90)

sns.histplot(normal_gaps, bins=30, kde=True, color="#455A64", edgecolor="black", ax=axes[0])
axes[0].axvline(med, color="#E65100", linestyle="--", linewidth=2, label=f"Mediana: {med:.1f} min")
axes[0].axvline(p75, color="#F57C00", linestyle=":", linewidth=2, label=f"P75: {p75:.1f} min")
axes[0].axvline(p90, color="#D32F2F", linestyle="-.", linewidth=2, label=f"P90: {p90:.1f} min")
axes[0].axvline(15, color="#1976D2", linestyle="-", linewidth=1.5, alpha=0.8, label="Grilla 15 min")
axes[0].axvline(30, color="#388E3C", linestyle="-", linewidth=1.5, alpha=0.8, label="Grilla 30 min")
axes[0].set_title("(2A) Distribución de Intervalos (Gaps) entre Mediciones Reales", fontsize=12, fontweight='bold')
axes[0].set_xlabel("Minutos entre mediciones consecutivas de NBP", fontsize=11)
axes[0].set_ylabel("Frecuencia (número de intervalos)", fontsize=11)
axes[0].legend(fontsize=9)

# CDF of gaps
sorted_gaps = np.sort(all_gaps)
cdf = np.arange(1, len(sorted_gaps) + 1) / len(sorted_gaps)
axes[1].plot(sorted_gaps, cdf * 100, color="#1565C0", linewidth=2.5)
axes[1].axvline(15, color="#1976D2", linestyle="--", label=f"< 15 min: {100*np.mean(all_gaps <= 15):.1f}%")
axes[1].axvline(30, color="#388E3C", linestyle="--", label=f"< 30 min: {100*np.mean(all_gaps <= 30):.1f}%")
axes[1].axvline(60, color="#F57C00", linestyle="--", label=f"< 60 min: {100*np.mean(all_gaps <= 60):.1f}%")
axes[1].set_xlim(0, 120)
axes[1].set_ylim(0, 105)
axes[1].set_title("(2B) Función Acumulada (CDF) de Intervalos de Muestreo", fontsize=12, fontweight='bold')
axes[1].set_xlabel("Minutos entre mediciones", fontsize=11)
axes[1].set_ylabel("% Acumulado de mediciones", fontsize=11)
axes[1].legend(loc="lower right", fontsize=10)

plt.suptitle("Verificación D7: Caracterización Temporal de Gaps de Presión No Invasiva", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig2_path = os.path.join(fig_dir, "02_nbp_gaps_distribution.png")
plt.savefig(fig2_path, dpi=200, bbox_inches='tight')
plt.close()
print(f"Saved: {fig2_path}")

# ==============================================================================
# PLOT 3: PRUEBA GP EN GRILLA DE 15 MIN VS 30 MIN (PATIENT p10019003)
# ==============================================================================
# Load p10019003 window 24h
f_rep = os.path.join(DATA_DIR, "p10019003_87033314n.csv.gz")
df_rep = pd.read_csv(f_rep, usecols=["time", "NBPs [mmHg]", "NBPd [mmHg]"])
cuff_rep = df_rep.dropna(subset=["NBPs [mmHg]"]).sort_values("time")
vals_rep = cuff_rep[["NBPs [mmHg]", "NBPd [mmHg]"]].fillna(-1)
changed_rep = vals_rep.ne(vals_rep.shift()).any(axis=1)
real_rep = cuff_rep.loc[changed_rep].copy()
real_rep["hours"] = (real_rep["time"] - df_rep["time"].min()) / TICKS_PER_SECOND / 3600
real_rep = real_rep[real_rep["hours"] <= 20.0].copy() # 20 hour window for clear visual comparison

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True)

def fit_and_plot_gp(ax, grid_min, title_str, color_line, color_fill):
    bins = np.arange(0, 20.0 + grid_min/60.0, grid_min/60.0)
    real_rep["bin"] = np.digitize(real_rep["hours"], bins) - 1
    agg = real_rep.groupby("bin")["NBPs [mmHg]"].mean().reset_index()
    
    grid_centers = (bins[:-1] + bins[1:]) / 2
    grid_df = pd.DataFrame({"bin": range(len(bins)-1), "t_h": grid_centers})
    merged = pd.merge(grid_df, agg, on="bin", how="left")
    
    obs = merged.dropna(subset=["NBPs [mmHg]"])
    X_train = obs["t_h"].values.reshape(-1, 1)
    y_train = obs["NBPs [mmHg]"].values
    X_all = merged["t_h"].values.reshape(-1, 1)
    
    # Kernel: Matern + WhiteNoise
    kernel = C(50.0, (1.0, 500.0)) * Matern(length_scale=2.5, length_scale_bounds=(0.8, 8.0), nu=1.5) + WhiteKernel(noise_level=16.0, noise_level_bounds=(1.0, 64.0))
    gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, random_state=42)
    gp.fit(X_train, y_train)
    y_pred, y_std = gp.predict(X_all, return_std=True)
    
    # Plot observations
    ax.scatter(obs["t_h"], obs["NBPs [mmHg]"], color="black", s=30, zorder=4, label=f"Observaciones reales ({len(obs)}/{len(merged)} bloques)")
    # Mark missing blocks with vertical faint dashed ticks
    missing = merged[merged["NBPs [mmHg]"].isna()]
    ax.scatter(missing["t_h"], [100]*len(missing), marker="|", color="red", s=40, alpha=0.5, label=f"Gaps a imputar ({len(missing)} bloques)")
    
    # Plot GP prediction and 95% CI
    ax.plot(merged["t_h"], y_pred, color=color_line, linewidth=2, label="Media predictiva GP (μ)")
    ax.fill_between(merged["t_h"], y_pred - 1.96 * y_std, y_pred + 1.96 * y_std, color=color_fill, alpha=0.25, label="Intervalo de confianza 95% (μ ± 1.96σ)")
    
    ax.set_ylabel("NBPs [mmHg]", fontsize=11, fontweight='bold')
    ax.set_title(title_str, fontsize=12, fontweight='bold')
    ax.legend(loc="upper right", fontsize=9, ncol=2)
    ax.set_ylim(85, 145)

fit_and_plot_gp(ax1, 15, "(3A) Grilla de 15 minutos: Resolución temporal fina para detección temprana (D8)", "#1976D2", "#2196F3")
fit_and_plot_gp(ax2, 30, "(3B) Grilla de 30 minutos: Menor proporción de huecos pero menor sensibilidad a alertas tempranas", "#2E7D32", "#4CAF50")

ax2.set_xlabel("Tiempo transcurrido en UCI (Horas)", fontsize=11, fontweight='bold')
plt.suptitle("Verificación D7: Comparación de Imputación por Gaussian Process en Grilla de 15m vs 30m", fontsize=14, fontweight='bold', y=1.01)
plt.tight_layout()
fig3_path = os.path.join(fig_dir, "03_gp_imputation_15m_vs_30m.png")
plt.savefig(fig3_path, dpi=200, bbox_inches='tight')
plt.close()
print(f"Saved: {fig3_path}")
