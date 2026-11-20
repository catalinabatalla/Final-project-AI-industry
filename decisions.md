# Decision log

## D1 – Numerics instead of raw waveforms
**Decision:** We use only the numerics files (`<stay>n.csv.gz`), not the raw waveforms (`.dat`).

**Why:**
- The numerics are derived from the waveforms by the monitor itself (HR from ECG, SpO2 from Pleth, RR from Resp). NIBP only exists in the numerics.
- Our question is about deterioration over minutes to hours. That is visible in the vital signs; beat-level detail is not needed.
- We resample to 15 minutes anyway, so waveform detail would be averaged away.
- Our methods (e.g. Gaussian Processes, O(n³)) cannot handle waveform-sized data.
- Clinicians and early warning scores (e.g. NEWS2) use these same vital signs.
- Much smaller download: for stay 83404654, 7.2 MB numerics vs. ~143 MB waveforms.

**What we give up:** beat-level information such as arrhythmias, ECG shape changes, heart rate variability, and events shorter than a few seconds.

**Future work:** add waveform features (e.g. heart rate variability) to see whether they give earlier warnings.