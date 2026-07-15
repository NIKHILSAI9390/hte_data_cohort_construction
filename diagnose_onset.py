"""Check if sepsis onset is being detected too early (causing high treated rate).
Compare onset time vs ICU admission and vs suspicion time."""
import pandas as pd, numpy as np

sepsis = pd.read_parquet("results/sepsis_data_0.parquet")
for c in ["intime","suspected_infection","sepsis_onset"]:
    sepsis[c]=pd.to_datetime(sepsis[c])

sepsis["onset_after_intime_h"]=(sepsis["sepsis_onset"]-sepsis["intime"]).dt.total_seconds()/3600
sepsis["onset_vs_suspicion_h"]=(sepsis["sepsis_onset"]-sepsis["suspected_infection"]).dt.total_seconds()/3600

print("Onset timing diagnostics:")
print(f"\n  hours from ICU admission to detected onset:")
print(sepsis["onset_after_intime_h"].describe().to_string())
print(f"\n  hours from suspicion time to detected onset:")
print(sepsis["onset_vs_suspicion_h"].describe().to_string())
print(f"\n  onset within first 6h of ICU admission: "
      f"{(sepsis['onset_after_intime_h']<=6).mean():.1%}")
print(f"  (if most onsets are right at admission, onset is firing too early)")