# Decision log

Each decision: what we chose, why, and what we give up.
🟡: need to decide together
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

## D4 – Selection criteria: duration and coverage 🟡
**Decision:** A stay is eligible if (1) it lasts at least **X hours** and (2) **each** of the 5 vital signs is measured in at least **Y%** of its hours (`min_coverage` ≥ Y).

**Why:**
- ICU data has gaps; a long stay is not automatically complete (p10020306: 76.3 h, but cuff coverage only 23.4%).
- Our models need all 5 signals together, so the weakest signal decides (almost always the cuff).
- Coverage per hour catches both missing signals and long interruptions; short gaps are handled by gap filling (notebook 02).

**Options considered (notebook 00, section 8):**
| | ≥ 70% | ≥ 80% | ≥ 90% |
|---|---|---|---|
| ≥ 12 h | 97 | 89 | 81 |
| ≥ 24 h | 75 | 70 | 63 |

These numbers count cuff copies as measurements (see D7), so they may be slightly optimistic. To check: recompute coverage with real cuff measurements only.

**To decide:** X and Y, and why.

**Possible bias:** the cuff is almost always the weakest signal, and it is often missing in patients with an arterial line, who tend to be the sickest. This coverage rule may therefore exclude more severely ill patients, so our results may not hold for them. We check this by comparing included and excluded stays.

---

## D5 – How many eligible stays do we use? 🟡
**Options:**
| Option | For | Against |
|---|---|---|
| **All eligible stays** (63–97, depending on D4) | more training data; larger, more reliable test set; no extra selection step (less selection bias) | more computing time (still small on a 15-min grid); more data to inspect |
| **A fixed number (30), randomly drawn** from the eligible stays | smaller and easier to inspect by hand; faster to run | throws away usable data; smaller test set (~9 patients) → less reliable score |

**Never:** choosing the *longest* stays, because that favours particular patients (selection bias), and the longest stay is not the most complete one (p10020306: 76.3 h, cuff coverage 23.4%).

**Limitation (both options):** results only describe stays that meet our criteria (D4), not all ICU patients.

**To decide together:** all eligible stays, or a random 30?

---

## D6 – Train/test split per patient (70/30)
**Decision:** 70% of the patients train the model, 30% test it. Patients are assigned randomly (fixed seed). We tune settings on a few training patients (validation) and use the test set only once, at the end. Mean and standard deviation for scaling come from the training patients only.

**Why:**
- **Per patient:** a monitor must work for *new* patients. Splitting one patient's timeline would let the model "recognize" that patient → misleadingly good score (data leakage).
- **Random, fixed seed:** no cherry-picking of "easy" test patients; same split on every laptop.
- **Test once, scaling on training only:** nothing from the test patients may influence training, otherwise the test score is no longer honest.

---

## D7 – Time grid 🟡
**What:** our models need a table with one row per fixed time block (e.g. every 15 minutes). We average each signal within each block. The block size is "the grid".

**Finding:** ~85% of cuff (NBP) rows are copies; the monitor re-writes the last value every ~2 min. Real new cuff measurements happen about every 20 minutes (median).

**Grid check (real cuff measurements, median stay):**
| Grid | 15 min | 30 min | 60 min |
|---|---|---|---|
| Blocks with a real cuff measurement | 38% | 62% | 96% |

**Trade-off:** small blocks give more detail but more missing blood pressure values to fill in; big blocks have fewer gaps but average away short events (e.g. a short SpO2 dip).

**To decide together:** which grid size, and how we handle the missing cuff values.

---

## D8 – What we predict 🟡
**Problem:** ICU patients are often already "abnormal", so fixed thresholds would raise alarms all the time (alarm fatigue).

**Proposal:**
- **Event:** the *start* of a clinically defined deterioration, e.g. low blood pressure (hypotension) or low oxygen (SpO2 < 90%), lasting at least a minimum time.
- **Detection:** an anomaly score that compares each patient with **their own** earlier data (personal baseline), not with healthy people.
- **Evaluation:** does the score rise **before** an event, and how many minutes before? A simple threshold rule is the baseline to compare with.

**To decide together:** which events and their thresholds, the minimum duration, and the length of the personal baseline. Check with the professor?

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