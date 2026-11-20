import json

notebook_path = r"notebooks/01_EDA_and_Preprocessing.ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Insert a new markdown cell and code cell after Cell 3 (which lists the files)
# to analyze the 10 patients cohort before diving into the primary patient.

cohort_md = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "### 1.1 Multi-Patient Cohort Exploration & Stay Duration Analysis\n",
        "\n",
        "Before selecting a primary patient for in-depth time-series modeling, we analyze the **entire cohort of 10 real ICU patients** from `mimic4wdb`.\n",
        "We compute:\n",
        "1. **Total observations recorded** per patient.\n",
        "2. **Continuous ICU monitoring duration** (hours and days).\n",
        "3. **Completeness across channels**: valid counts for Heart Rate (`HR`), Blood Pressure (`NBPs/NBPd`), Oxygen Saturation (`SpO2`), and Respiratory Rate (`RR`).\n",
        "\n",
        "This comparative analysis allows us to select the patient with the highest temporal density and longest stay as our primary subject for time-series modeling, reserving the remaining patients for generalizability testing."
    ]
}

cohort_code = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# Cohort-wide comparative statistical analysis across all 10 real patients\n",
        "cohort_stats = []\n",
        "\n",
        "for fpath in wdb_files:\n",
        "    pid = os.path.basename(fpath).split('_')[0]\n",
        "    with gzip.open(fpath, 'rt') as fp:\n",
        "        df_p = pd.read_csv(fp)\n",
        "    \n",
        "    dt_hours = (df_p['time'].max() - df_p['time'].min()) / (1000.0 * 3600.0)\n",
        "    cohort_stats.append({\n",
        "        'patient_id': pid,\n",
        "        'filename': os.path.basename(fpath),\n",
        "        'total_rows': len(df_p),\n",
        "        'duration_hours': round(dt_hours, 1),\n",
        "        'duration_days': round(dt_hours / 24.0, 2),\n",
        "        'valid_hr': int(df_p['HR [bpm]'].notnull().sum()) if 'HR [bpm]' in df_p else 0,\n",
        "        'valid_bp': int(df_p['NBPs [mmHg]'].notnull().sum()) if 'NBPs [mmHg]' in df_p else 0,\n",
        "        'valid_spo2': int(df_p['SpO2 [%]'].notnull().sum()) if 'SpO2 [%]' in df_p else 0,\n",
        "        'valid_rr': int(df_p['RR [rpm]'].notnull().sum()) if 'RR [rpm]' in df_p else 0\n",
        "    })\n",
        "\n",
        "df_cohort = pd.DataFrame(cohort_stats).sort_values('total_rows', ascending=False).reset_index(drop=True)\n",
        "\n",
        "# Visualization of monitoring duration across the 10 patients\n",
        "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))\n",
        "\n",
        "sns.barplot(data=df_cohort, x='patient_id', y='duration_days', palette='Blues_r', ax=ax1)\n",
        "ax1.set_title(\"ICU Monitoring Duration per Patient (Days)\", fontsize=12, fontweight='bold')\n",
        "ax1.set_ylabel(\"Days in ICU\", fontsize=11)\n",
        "ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45)\n",
        "ax1.grid(True, linestyle=':', alpha=0.6)\n",
        "\n",
        "sns.barplot(data=df_cohort, x='patient_id', y='total_rows', palette='viridis', ax=ax2)\n",
        "ax2.set_title(\"Total Real Vital Sign Observations Recorded\", fontsize=12, fontweight='bold')\n",
        "ax2.set_ylabel(\"Number of Observations\", fontsize=11)\n",
        "ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45)\n",
        "ax2.grid(True, linestyle=':', alpha=0.6)\n",
        "\n",
        "plt.tight_layout()\n",
        "plt.show()\n",
        "\n",
        "# Display cohort summary table\n",
        "print(\"=== Cohort Summary (10 Real Patients) ===\")\n",
        "display(df_cohort[['patient_id', 'total_rows', 'duration_hours', 'duration_days', 'valid_hr', 'valid_bp', 'valid_spo2', 'valid_rr']])"
    ]
}

# Insert after cell 3
nb["cells"].insert(4, cohort_md)
nb["cells"].insert(5, cohort_code)

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("SUCCESS: Notebook updated with cohort analysis section!")
