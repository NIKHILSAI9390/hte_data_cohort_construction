"""GCS component fixed — map text descriptions to GCS point values, sum, score CNS."""
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

df = extract_shard(find_shards()[0])   # keep text_value, no dropna yet
g = df[df["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])].copy()

# ---- Standard Glasgow Coma Scale text -> points mappings ----
EYE = {
    "Spontaneously": 4,
    "To Speech": 3,
    "To Pain": 2,
    "None": 1,
}
VERBAL = {
    "Oriented": 5,
    "Confused": 4,
    "Inappropriate Words": 3,
    "Incomprehensible sounds": 2,
    "No Response": 1,
    "No Response-ETT": 1,   # intubated — scored as 1 (worst) by convention
}
MOTOR = {
    "Obeys Commands": 6,
    "Localizes Pain": 5,
    "Flex-withdraws": 4,
    "Abnormal Flexion": 3,
    "Abnormal extension": 2,
    "No response": 1,
    "No Response": 1,
}

def map_gcs(row):
    v, txt = row["variable"], row["text_value"]
    if txt is None: return np.nan
    if v == "gcs_eye":    return EYE.get(txt, np.nan)
    if v == "gcs_verbal": return VERBAL.get(txt, np.nan)
    if v == "gcs_motor":  return MOTOR.get(txt, np.nan)
    return np.nan

g["gcs_points"] = g.apply(map_gcs, axis=1)

# Check for any unmapped text (would be NaN) so we don't silently lose data
unmapped = g[g["gcs_points"].isna()]["text_value"].value_counts()
print("Unmapped GCS text values (should be empty or rare):")
print(unmapped.head(20).to_string() if len(unmapped) else "  none — all mapped!")

# Per patient: worst (min) points per component, then sum the three
gcs_wide = g.dropna(subset=["gcs_points"]).pivot_table(
    index="subject_id", columns="variable", values="gcs_points", aggfunc="min")

needed = ["gcs_eye","gcs_verbal","gcs_motor"]
have = [c for c in needed if c in gcs_wide.columns]
print(f"\ncomponents present: {have}")
gcs_total = gcs_wide[needed].sum(axis=1, min_count=3)

print(f"\nGCS total: {gcs_total.notna().sum()} patients")
print("GCS total distribution (should peak at 15 = normal):")
print(gcs_total.value_counts().sort_index().to_string())

def score_cns(v):
    if pd.isna(v): return np.nan
    if v < 6: return 4
    if v < 10: return 3
    if v < 13: return 2
    if v < 15: return 1
    return 0

cns = gcs_total.map(score_cns)
print("\nCNS score distribution (should peak at 0 = most alert):")
print(cns.value_counts().sort_index().to_dict())