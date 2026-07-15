"""SOFA computation — STEP 1: get the per-organ SCORING LOGIC right on one shard.
SIMPLIFICATION (temporary): score each patient by their WORST value per component
over their whole record. NOT the final time-windowed SOFA — this verifies the
scoring thresholds produce sensible 0-4 scores. Time-windowing comes later."""
import glob
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

shard = find_shards()[0]
print(f"Loading extracted values from one shard...\n")
df = extract_shard(shard)
df = df[["subject_id","time","variable","numeric_value"]].dropna(subset=["numeric_value"])

def worst_per_patient(var, how):
    sub = df[df["variable"]==var].groupby("subject_id")["numeric_value"]
    return (sub.min() if how=="min" else sub.max())

# COAGULATION (platelets, lower=worse)
plt = worst_per_patient("platelets","min")
def score_coag(p):
    if pd.isna(p): return np.nan
    if p < 20:  return 4
    if p < 50:  return 3
    if p < 100: return 2
    if p < 150: return 1
    return 0

# LIVER (bilirubin, higher=worse)
bili = worst_per_patient("bilirubin_total","max")
def score_liver(b):
    if pd.isna(b): return np.nan
    if b >= 12.0: return 4
    if b >= 6.0:  return 3
    if b >= 2.0:  return 2
    if b >= 1.2:  return 1
    return 0

# RENAL (creatinine, higher=worse)
crea = worst_per_patient("creatinine","max")
def score_renal(c):
    if pd.isna(c): return np.nan
    if c >= 5.0: return 4
    if c >= 3.5: return 3
    if c >= 2.0: return 2
    if c >= 1.2: return 1
    return 0

# CNS (GCS = eye+verbal+motor, lower=worse)
gcs = (df[df["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])]
       .groupby(["subject_id","variable"])["numeric_value"].min()
       .unstack())
gcs_total = gcs.sum(axis=1, min_count=3)
def score_cns(g):
    if pd.isna(g): return np.nan
    if g < 6:   return 4
    if g < 10:  return 3
    if g < 13:  return 2
    if g < 15:  return 1
    return 0

sofa = pd.DataFrame({
    "platelets_min": plt, "coag": plt.map(score_coag),
    "bilirubin_max": bili, "liver": bili.map(score_liver),
    "creatinine_max": crea, "renal": crea.map(score_renal),
    "gcs_total": gcs_total, "cns": gcs_total.map(score_cns),
})

print("SOFA components computed so far (coag, liver, renal, cns):")
for c in ["coag","liver","renal","cns"]:
    print(f"    {c}: {sofa[c].notna().sum()} patients, "
          f"scores: {sofa[c].value_counts().sort_index().to_dict()}")
print(f"\n  sample patients:")
print(sofa.dropna(subset=['coag','renal']).head(10).to_string())