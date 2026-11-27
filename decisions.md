# Decision log

Each decision: what we chose, why, and what we give up.

Our process: we explored the data first (notebook 00, sections 6–9), made these decisions, and then checked them with the data (sections 10–12). Where a check disagreed with an assumption, we adjusted the decision (e.g. D4: 66% of the excluded long stays have an arterial line, not 100%). Decisions can still change if new findings contradict them.

All decisions have been finalized and verified with data from the MIMIC-IV Waveform Database (`mimic4wdb v0.1.0`). Verification figures are located in `notebooks/figures/`.

---

## Data conventions
These hold for every notebook:
- **Time units:** the `time` column counts in ticks; 999.56 ticks = 1 second.
- **Every stay starts at 0:** we subtract the earliest time from all times, so time means "seconds (or hours) since the start of the stay". The raw time can be slightly negative (a few seconds before the recording officially started); after this step it isn't anymore.
- **Sorting:** the rows in the files are shuffled in time. That doesn't matter when we only look at the earliest and latest time or count measurements. It does matter when we calculate the time *between* two measurements, or check whether a value is the same as the *previous* one: then we first put the rows in time order (`sort_values("time")`).
- **Real cuff measurements:** the monitor copies the last cuff value every ~2 minutes. We only count a cuff value as a real measurement if it is different from the previous one (~85% are copies).

---

## D1 – Numerics instead of raw waveforms
**Decision:** We use only the numerics files (`<stay>n.csv.gz`), not the raw waveforms (`.dat`).

**Why:**
- The numerics are derived from the waveforms by the monitor itself (HR from ECG, SpO2 from Pleth, RR from Resp). The cuff blood pressure (NBP) only exists in the numerics.
- Our question is about deterioration over minutes to hours, which is visible in the vital signs.
- Much smaller: all numerics are 579 MB vs. 12.8 GB for the full dataset (~4.5%).
- Our methods (e.g. Gaussian Processes, O(n³)) cannot handle waveform-sized data.

**What we give up:** beat-level information (arrhythmias, ECG shape, heart rate variability, events of a few seconds).

---

## D2 – Five vital signs
**Decision:** Out of the 20 values the monitor records, we use these 5 vital signs:

| Column | Name | What it measures | How it is measured | Typical value (healthy adult at rest) |
|---|---|---|---|---|
| `HR [bpm]` | Heart rate | How many times the heart beats per minute (**bpm** = beats per minute) | Calculated from the ECG (stickers on the chest that record the heart's electrical activity) | ~60–100 bpm |
| `RR [rpm]` | Respiratory rate | How many breaths per minute (**rpm** = respirations per minute) | From small changes in electrical resistance of the chest as it moves with breathing | ~12–20 rpm |
| `SpO2 [%]` | Oxygen saturation | The percentage of red blood cells carrying oxygen | A clip on the finger that shines light through the skin | ~95–100% |
| `NBPs [mmHg]` | Systolic blood pressure | The pressure in the arteries when the heart beats (the "upper" number) | An inflatable cuff around the arm (**NBP** = non-invasive blood pressure) | ~90–120 mmHg |
| `NBPd [mmHg]` | Diastolic blood pressure | The pressure in the arteries between beats (the "lower" number) | Same cuff measurement as the systolic value | ~60–80 mmHg |

HR, RR and SpO2 are measured about **every second**; the cuff only **every few minutes** when it is used, and sometimes not for hours.

**Why these 5:**
- They are the standard vital signs that doctors and nurses watch to spot deterioration.
- Hospital **early warning scores** such as **NEWS2** (National Early Warning Score), a points system that combines vital signs to flag patients at risk, use these same signals.
- Together they cover the heart (HR, blood pressure), breathing (RR) and oxygen supply (SpO2).

**Why not the other columns:** they are mostly
- **ECG details** (e.g. QT, ST, PVC): measurements of the shape and rhythm of the heartbeat, used by cardiologists for specific heart problems;
- **duplicate pulse rates** from other devices (e.g. `Pulse (SpO2)`, the pulse counted by the finger clip);
- **arterial blood pressure** (ABP), see D3.

---

## D3 – Cuff blood pressure (NBP) instead of arterial blood pressure (ABP)
**Decision:** We use the cuff (`NBPs`, `NBPd`), not the arterial line (`ABPs`, `ABPd`, `ABPm`).

**Why:** an arterial line is invasive and mainly used in the sickest patients, so requiring ABP would make our selection depend on how sick patients are.

**What we give up:** ABP is continuous; the cuff is measured only every few minutes, and in some stays not for many hours.
**Idea for later:** use ABP when the cuff is missing (would need a check that ABP and NBP give comparable values).

---

## D4 – Selection criteria: duration and coverage
**Decision:** A stay is eligible if (1) it lasts at least **12 hours** (`duration_h` ≥ 12) and (2) **each** of the 5 vital signs is measured in at least **80%** of its hours (`min_coverage` ≥ 80%), computed on **real measurements only** (repeated cuff copies removed, see D7). This leaves **84** of the 194 stays (84 different patients), saved in `selected_stays.csv`.

**What "coverage" means:** we cut each stay into 1-hour blocks and check, per signal, whether each hour contains **at least one** measurement. Coverage = the percentage of hours that do. `min_coverage` = the lowest coverage of the 5 signals.

**Why:**
- ICU data has gaps; a long stay is not automatically complete (e.g. `p10020306`: 76.3 h, but real cuff coverage only 18.2%).
- Our models need all 5 signals together, so the weakest signal decides (almost always the cuff, NBP).
- **1-hour blocks:** the cuff normally measures about every 20 minutes, so a normally monitored hour almost always contains a real cuff value. An empty hour therefore signals a real interruption (cuff off or not used), not normal sparse monitoring. With 15-minute blocks the cuff would fail by design (only ~38% of blocks have a real value), so we would measure "the cuff is slow" instead of "the stay has interruptions".
- **12 h:** long enough for several 4-hour model windows per stay, while keeping more stays than a 24-h minimum.
- **80%:** at most about 1 in 5 hours may lack a real measurement of a signal. Such short gaps can be filled (Gaussian Process, notebook 02); long interruptions cannot.

**Options considered:** 12 or 24 h × 70, 80 or 90% (notebook 00, section 8; those counts still included cuff copies). The final rule is applied to real measurements in section 10.

**Selection bias (arterial line):**
- Of the 194 stays, 110 are excluded: 46 because they are shorter than 12 h, and 64 only because of low real cuff coverage.
- Of those 64, **42 (two thirds) have an invasive arterial line** (`ABPs/d/m`), e.g. `p10020306` (217k ABP values). Not all: e.g. `p10100546` (137 h) has none.
- Excluded stays also have far more long cuff pauses: gaps longer than 2 hours are ~17× more common than in included stays (notebook 00, section 11.1).
- *Clinical reason:* the sickest patients often get a continuous arterial line, and then the arm cuff is rarely used.
- *Limitation:* our cohort mainly represents patients monitored non-invasively. Severely unstable patients with an arterial line are probably underrepresented, so our results may not hold for them.

---

## D5 – How many eligible stays do we use?
**Decision:** We use **all eligible stays** that meet the D4 criteria.

**Why:**
- On a 15-minute grid, computing time for our models is modest even across all eligible stays.
- Restricting to a small arbitrary subset (e.g. 30 patients) leaves only ~9 patients in the test split (D6: 70/30 split), which is insufficient for a statistically robust, orally defensible hospital cost optimization benchmark (notebook 05).
- Using all eligible stays maximizes training sample diversity and avoids any second-stage sampling bias.

---

## D6 – Train/test split per patient (70/30)
**Decision:** 70% of the patients train the model, 30% test it. Patients are assigned randomly (fixed seed). We tune settings on a few training patients (validation) and use the test set only once, at the end. Mean and standard deviation for scaling come from the training patients only.

**Why:**
- **Per patient:** a monitor must work for *new* patients. Splitting one patient's timeline would let the model "recognize" that patient → misleadingly good score (data leakage).
- **Random, fixed seed:** no cherry-picking of "easy" test patients; same split on every laptop.
- **Test once, scaling on training only:** nothing from the test patients may influence training, otherwise the test score is no longer honest.

---

## D7 – Time grid: 15-minute blocks
**Decision:** all signals share one grid of **15-minute blocks**. Per block and per signal we store the **median**, **minimum**, **maximum** and **standard deviation**, plus whether the block contains a real measurement (`measured`).

**Why one grid for all signals:** the models compare the five signals at the same moment (e.g. HR rising while blood pressure falls). A finer grid for the fast signals would no longer line up with the cuff.

**Why 15 minutes:**
- Real cuff measurements occur on average about every 20 minutes, often on a timer (peaks at 15, 30 and 60 min; notebook 00, section 11). In the included stays, 74% of the gaps between real cuff measurements are ≤ 15 min.
- Early warning (D8) needs fine steps: 15 minutes gives 4 points in the hour before an event, 30 minutes only 2.
- Trade-off: with 15-minute blocks more cuff values must be filled in (in the 84 stays, ~47% of the blocks have a real cuff measurement). In a test on one patient, the Gaussian Process filled gaps with an error (CV-RMSE) of 4.85 mmHg on the 15-min grid vs. 3.16 mmHg on the 30-min grid (notebook 00, section 12).

**Why median, min, max and std instead of the mean:** HR, RR and SpO2 have ~900 values per block (one per second). The mean is sensitive to outliers and hides short dips or peaks (e.g. 2 minutes of SpO2 < 90%). The median gives a robust typical value; min and max keep short extremes visible; the std shows how restless the signal was.

**Filling gaps (notebook 02):** a GP with a Matérn kernel (ν = 1.5) and a noise term. A GP with learned noise predicted hidden values better than one forced through every measurement (CV-RMSE 5.96 vs. 7.44 mmHg, notebook 00, section 12.1). It does smooth out single low values, so we keep the original measurements next to the filled values.

**Expected effect on alarms:** more points per hour should help to catch deterioration earlier (fewer false negatives), but more filled-in values may cause more false alarms (false positives). A missed deterioration is usually worse in the ICU, so we accept this risk; the balance is tested with the cost model (notebook 05).

---

## D8 – What we predict: Early warning of composite clinical events
**Decision:** We predict the onset of **composite critical deterioration events** using each patient's **first 4–6 stable hours** as their individual baseline.

**Clinical definition of deterioration events:**
- Acute Hypotension ($SBP < 90$ mmHg for ≥ 15 min) or Hypertensive Crisis ($SBP > 180$ mmHg)
- Arterial Desaturation / Hypoxemia ($SpO_2 < 90\%$ for ≥ 15 min)
- Critical Tachycardia ($HR > 120$ bpm) or Bradycardia ($HR < 45$ bpm)
- Severe Tachypnea ($RR > 30$ rpm) or Bradypnea ($RR < 8$ rpm)

**Why personal baseline (first 4–6 hours):**
- ICU patients have heterogeneous chronic baselines (e.g. a patient with COPD or chronic hypertension); universal population thresholds cause massive false alarms and alarm fatigue.
- Evaluating whether the anomaly score (KDE / Autoencoder reconstruction error) rises 30–60 minutes *before* the clinical threshold is breached provides a concrete, industry-grade metric for predictive monitoring.

**Open points (to check in notebook 01):**
- **Baseline:** the first hours of a stay are not always stable. E.g. the first included stay starts with HR ≈ 129 bpm, above the event threshold. We need to check how often this happens before using the first 4–6 hours as a baseline.
- **Labels on real measurements:** events are defined on measured values, not on filled-in ones, so gap filling cannot create or hide events.

---

## D9 – Plausibility ranges (impossible values)
**Decision:** values outside wide plausibility ranges are treated as missing: HR 20–250 bpm, RR 3–60 /min, SpO2 50–100%, NBPs 40–260 mmHg, NBPd 20–180 mmHg, and NBPs must be higher than NBPd. Only the faulty cell is emptied, never the whole row.

**Why:** sensors sometimes produce impossible values (e.g. HR = 0 from a loose sticker). Left in, the models would see a sensor error as deterioration. The ranges are wide, so real extreme values, which we want to detect, stay.

**Result (84 stays):** removed HR 2,585 (all 0 in the first stay), RR 28,356, SpO2 376 and cuff 9 values. For RR, 88% of the removed values are exactly 0.

**Check (RR = 0):** of 1,275 stretches of RR = 0, 11 last longer than 5 minutes (2.7 h, ~40% of all zeros): certainly sensor dropouts. Short stretches (< 1 min) do not show more SpO2 drops than long ones (≥ 4 points: 18% vs. 36%), so there is no evidence of real breathing pauses.

**Limitation:** no comparison with random windows; extra oxygen can mask a short apnea. Bradypnea (RR < 8, D8) stays detectable.

---
## ⚠️ Known data issue: the cuff blood pressure (NBP)
The cuff causes most of our data problems:
- **Sparse:** a real new measurement only about every 20 minutes (vs. every second for HR, RR and SpO2).
- **Copies:** ~85% of the cuff rows are copies of the last value, not new measurements.
- **Long gaps:** sometimes no cuff measurement for many hours (p10020306: 25.8 h, cuff coverage only 23.4%).
- **Missing in the sickest patients:** patients with an arterial line often have no cuff measurements → excluding them causes bias (D3, D4).
- **Incomplete readings:** sometimes a systolic value without a diastolic one.

**Consequences:** it is the weakest signal in the coverage rule (D4) and limits how fine the time grid can be (D7).

**Options to discuss:**
- a coarser grid (D7);
- fill the gaps (notebook 02), or keep the last real value until the next one;
- use the arterial blood pressure (ABP) when the cuff is missing;
- treat blood pressure separately from the other four signals.