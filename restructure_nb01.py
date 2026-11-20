"""
Restructures notebook 01_EDA_and_Preprocessing.ipynb:
1. Updates Cell 0 (title/objectives) to reflect real mimic4wdb dataset
2. Inserts cohort analysis markdown + code after Cell 3 (the file-scanning cell)
3. Validates JSON parsability
Preserves all existing user-written cells unchanged.
"""
import json, re

NB_PATH = r"notebooks/01_EDA_and_Preprocessing.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]
print(f"[INFO] Starting with {len(cells)} cells")

# --- 1. Update Cell 0 (title) to reflect mimic4wdb real data ---
# Replace the objectives list which still mentions the old demo CSV structure
OLD_OBJ = [
    "# AI in Industry - Final Project: ICU Vital Signs Anomaly Detection\n",
    "## 01. Exploratory Data Analysis (EDA) & Preprocessing\n",
    "\n",
    "### Notebook Objectives:\n",
    "1. **Data Ingestion & Verification**: Inspect the availability of MIMIC-IV Clinical Database Demo v2.2 tables (`chartevents.csv.gz`, `d_items.csv.gz`, `icustays.csv.gz`).\n",
    "2. **Clinical Feature Selection**: Extract continuous core physiological time series in the ICU:\n",
    "   - Heart Rate (HR): `itemid = 220045` (bpm)\n",
    "   - Respiratory Rate (RR): `itemid = 220210` (insp/min)\n",
    "   - O2 Saturation Pulseoxymetry (SpO2): `itemid = 220277` (%)\n",
    "   - Non-Invasive Blood Pressure Systolic (NIBP SBP): `itemid = 220179` (mmHg)\n",
    "   - Non-Invasive Blood Pressure Diastolic (NIBP DBP): `itemid = 220180` (mmHg)\n",
    "3. **Sampling Irregularity & Missing Data Exploration**: Visually expose the raw sampling intervals (scatter plot of true observation timestamps and distribution of $Delta_t$), showing that measurements are taken irregularly (e.g. 3 measurements in 5 minutes followed by a 40-minute gap).\n",
    "4. **Temporal Alignment & Uniform Resampling**: Construct an equidistant time grid (`15min` / `1H`) resolving timestamp collisions and duplicates.\n",
    "5. **Clinical Ground Truth Anomaly Labeling**: Establish binary labels based on critical physiological deterioration thresholds:\n",
    "   - Severe Tachycardia / Critical Bradycardia ($HR > 120$ or $HR < 45$ bpm)\n",
    "   - Hypoxemia / Arterial Desaturation ($SpO_2 < 90\\%$)\n",
    "   - Acute Hypotension ($SBP < 90$ mmHg) or Hypertensive Crisis ($SBP > 180$ mmHg)\n",
    "   - Severe Tachypnea ($RR > 30$) or Critical Bradypnea ($RR < 8$)\n",
    "6. **Chronological Splitting (Train / Val / Test) & Standardization**: Compute means (`trmean`) and standard deviations (`trstd`) strictly on the training partition to prevent data leakage.\n",
    "7. **Dataset Export**: Save structured and standardized data for downstream models (Gaussian Processes, KDE, Autoencoders, and Hospital Cost Optimization)."
]

NEW_OBJ = [
    "# AI in Industry - Final Project: ICU Vital Signs Anomaly Detection\n",
    "## 01. Exploratory Data Analysis (EDA) & Preprocessing\n",
    "\n",
    "**Dataset:** MIMIC-IV Waveform Database (`mimic4wdb v0.1.0`) — 10 real ICU patients with continuous vital signs numerics.\n",
    "\n",
    "### Notebook Objectives:\n",
    "1. **Cohort Survey**: Load all 10 real patient files and compare monitoring duration, total observations, and per-channel completeness to select the best primary subject.\n",
    "2. **Primary Patient Deep-Dive**: Inspect raw irregular sampling structure of the selected patient (scatter plot of observation times, inter-measurement gap distribution).\n",
    "3. **Uniform Resampling**: Construct a 15-minute equidistant time grid; expose and quantify missing data after resampling.\n",
    "4. **Clinical Ground Truth Anomaly Labeling**: Binary labels based on critical physiological thresholds:\n",
    "   - Severe Tachycardia (HR > 120 bpm) or Critical Bradycardia (HR < 45 bpm)\n",
    "   - Hypoxemia / Arterial Desaturation (SpO2 < 90 %)\n",
    "   - Acute Hypotension (SBP < 90 mmHg) or Hypertensive Crisis (SBP > 180 mmHg)\n",
    "   - Severe Tachypnea (RR > 30) or Critical Bradypnea (RR < 8)\n",
    "5. **Multivariate Visualization**: 5-panel time-series plot with anomaly spans highlighted in red.\n",
    "6. **Chronological Partitioning**: Strict 60/20/20 train/val/test split to prevent data leakage. Train-only standardization (trmean, trstd).\n",
    "7. **Dataset Export**: Save parquet files and normalization statistics for downstream notebooks (GP Imputation, KDE, Autoencoder, Cost Optimization)."
]

if "".join(cells[0]["source"]).startswith("# AI in Industry"):
    cells[0]["source"] = NEW_OBJ
    print("[INFO] Cell 0 (title/objectives) updated to reflect real mimic4wdb dataset.")
else:
    print("[WARN] Cell 0 did not match expected pattern — skipping update.")

# --- 2. Insert Cohort Analysis cells after Cell 3 (the file-scanning code cell) ---
# Cell 3 is the code cell that scans for wdb_files. Insert cohort md + code AFTER it.

# Check cell 3 is indeed the file-scanning cell
cell3_src = "".join(cells[3]["source"])
if "wdb_files" not in cell3_src:
    print(f"[WARN] Cell 3 does not contain 'wdb_files' — content: {repr(cell3_src[:80])}")
    print("       Searching for the right insert point...")
    for idx, c in enumerate(cells):
        if "wdb_files" in "".join(c["source"]) and c["cell_type"] == "code":
            insert_after = idx
            print(f"       Found wdb_files code cell at index {idx}")
            break
    else:
        insert_after = 3
        print("       Could not find wdb_files cell, defaulting to insert after index 3")
else:
    insert_after = 3
    print("[INFO] Cell 3 confirmed as wdb_files scanning cell.")

# Check if cohort cells already exist (don't double-insert)
already_has_cohort = any(
    "Cohort" in "".join(c["source"]) or "cohort_stats" in "".join(c["source"])
    for c in cells
)

if already_has_cohort:
    print("[INFO] Cohort analysis cells already present — skipping insert.")
else:
    cohort_md = {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### 1.1 Multi-Patient Cohort Overview — All 10 Real ICU Patients\n",
            "\n",
            "Before selecting a primary patient for in-depth time-series modeling, we survey the **entire cohort of 10 real ICU patients** from `mimic4wdb v0.1.0`.\n",
            "\n",
            "For each patient we compute:\n",
            "1. **Total observations** recorded during the ICU stay.\n",
            "2. **Continuous monitoring duration** in hours and days.\n",
            "3. **Per-channel completeness**: valid non-null readings for HR, NBPs, NBPd, SpO2, and RR.\n",
            "\n",
            "This survey guides us to select the patient with the richest temporal coverage as our **primary modeling subject**, while the remaining patients serve as an **external test cohort** to validate generalizability."
        ]
    }

    cohort_code = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Survey all 10 patients: duration, observations, per-channel completeness\n",
            "cohort_stats = []\n",
            "\n",
            "for fpath in wdb_files:\n",
            "    pid = os.path.basename(fpath).split('_')[0]\n",
            "    with gzip.open(fpath, 'rt') as fp:\n",
            "        df_p = pd.read_csv(fp)\n",
            "\n",
            "    dt_hours = (df_p['time'].max() - df_p['time'].min()) / (1000.0 * 3600.0)\n",
            "    cohort_stats.append({\n",
            "        'patient_id': pid,\n",
            "        'filename': os.path.basename(fpath),\n",
            "        'total_rows': len(df_p),\n",
            "        'duration_hours': round(dt_hours, 1),\n",
            "        'duration_days': round(dt_hours / 24.0, 2),\n",
            "        'valid_hr':   int(df_p['HR [bpm]'].notnull().sum())   if 'HR [bpm]'   in df_p.columns else 0,\n",
            "        'valid_sbp':  int(df_p['NBPs [mmHg]'].notnull().sum()) if 'NBPs [mmHg]' in df_p.columns else 0,\n",
            "        'valid_dbp':  int(df_p['NBPd [mmHg]'].notnull().sum()) if 'NBPd [mmHg]' in df_p.columns else 0,\n",
            "        'valid_spo2': int(df_p['SpO2 [%]'].notnull().sum())   if 'SpO2 [%]'   in df_p.columns else 0,\n",
            "        'valid_rr':   int(df_p['RR [rpm]'].notnull().sum())    if 'RR [rpm]'    in df_p.columns else 0,\n",
            "    })\n",
            "\n",
            "df_cohort = pd.DataFrame(cohort_stats).sort_values('total_rows', ascending=False).reset_index(drop=True)\n",
            "\n",
            "# --- Visualization ---\n",
            "fig, axes = plt.subplots(1, 3, figsize=(18, 5))\n",
            "\n",
            "# Panel 1: ICU Stay Duration (days)\n",
            "sns.barplot(data=df_cohort, x='patient_id', y='duration_days',\n",
            "            palette='Blues_r', ax=axes[0])\n",
            "axes[0].set_title('ICU Monitoring Duration (Days)', fontsize=12, fontweight='bold')\n",
            "axes[0].set_ylabel('Days in ICU')\n",
            "axes[0].set_xlabel('')\n",
            "axes[0].tick_params(axis='x', rotation=45)\n",
            "axes[0].grid(True, linestyle=':', alpha=0.6)\n",
            "\n",
            "# Panel 2: Total recorded observations\n",
            "sns.barplot(data=df_cohort, x='patient_id', y='total_rows',\n",
            "            palette='viridis', ax=axes[1])\n",
            "axes[1].set_title('Total Observations Recorded', fontsize=12, fontweight='bold')\n",
            "axes[1].set_ylabel('Number of Rows')\n",
            "axes[1].set_xlabel('')\n",
            "axes[1].tick_params(axis='x', rotation=45)\n",
            "axes[1].grid(True, linestyle=':', alpha=0.6)\n",
            "\n",
            "# Panel 3: Per-channel valid readings (stacked bar)\n",
            "ch_df = df_cohort.set_index('patient_id')[['valid_hr','valid_sbp','valid_dbp','valid_spo2','valid_rr']]\n",
            "ch_df.plot(kind='bar', stacked=True, ax=axes[2],\n",
            "           color=['#2196F3','#F44336','#FF9800','#4CAF50','#9C27B0'])\n",
            "axes[2].set_title('Per-Channel Valid Observations', fontsize=12, fontweight='bold')\n",
            "axes[2].set_ylabel('Valid Readings')\n",
            "axes[2].set_xlabel('')\n",
            "axes[2].tick_params(axis='x', rotation=45)\n",
            "axes[2].legend(['HR','SBP','DBP','SpO2','RR'], loc='upper right', fontsize=9)\n",
            "axes[2].grid(True, linestyle=':', alpha=0.6)\n",
            "\n",
            "plt.suptitle('MIMIC-IV Waveform DB — 10-Patient ICU Cohort Overview', fontsize=14, fontweight='bold', y=1.02)\n",
            "plt.tight_layout()\n",
            "plt.show()\n",
            "\n",
            "# Summary table\n",
            "print('\\n=== Cohort Summary Table (sorted by total observations) ===')\n",
            "display(df_cohort[['patient_id','total_rows','duration_hours','duration_days',\n",
            "                    'valid_hr','valid_sbp','valid_dbp','valid_spo2','valid_rr']])\n",
            "\n",
            "# Flag short stays\n",
            "short_stays = df_cohort[df_cohort['duration_hours'] < 10]\n",
            "if len(short_stays):\n",
            "    print(f'\\n[WARNING] {len(short_stays)} patient(s) with <10h monitoring — may be excluded from generalization tests:')\n",
            "    print(short_stays[['patient_id','duration_hours']].to_string(index=False))\n",
            "\n",
            "# Identify primary patient (longest stay = most temporal richness)\n",
            "primary_row = df_cohort.iloc[0]\n",
            "print(f'\\n[SELECTION] Primary patient: {primary_row[\"patient_id\"]} '\n",
            "      f'({primary_row[\"duration_days\"]} days, {primary_row[\"total_rows\"]:,} observations)')"
        ]
    }

    cells.insert(insert_after + 1, cohort_md)
    cells.insert(insert_after + 2, cohort_code)
    print(f"[INFO] Cohort analysis cells inserted at positions {insert_after+1} and {insert_after+2}.")

# --- 3. Validate JSON ---
nb["cells"] = cells
output_str = json.dumps(nb, indent=1, ensure_ascii=False)

# Sanity-check: re-parse
try:
    json.loads(output_str)
    print("[OK] JSON validation passed.")
except json.JSONDecodeError as e:
    print(f"[ERROR] JSON validation failed: {e}")
    raise

with open(NB_PATH, "w", encoding="utf-8") as f:
    f.write(output_str)

print(f"[DONE] Notebook saved. Total cells: {len(cells)}")
