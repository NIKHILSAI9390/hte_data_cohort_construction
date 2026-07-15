"""covariates_vitals_labs.py — first-day vitals/labs covariates at/before onset,
with physiological range filtering (discard impossible values before aggregating)."""
import glob
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

VITALS = ["heart_rate","resp_rate","spo2","temp_c","temp_f",
          "map_arterial","map_noninvasive"]
LABS   = ["creatinine","wbc","platelets","bilirubin_total","lactate"]

# physiological valid ranges — values outside are discarded (sentinels/errors)
RANGES = {
    "heart_rate":(20,250), "resp_rate":(4,60), "spo2":(50,100),
    "temp_c":(25,45), "temp_f":(77,113),
    "map_arterial":(20,200), "map_noninvasive":(20,200),
    "creatinine":(0.1,20), "wbc":(0,200), "platelets":(0,2000),
    "bilirubin_total":(0,80), "lactate":(0,40),
}

def build_covariates(shard_path, sepsis):
    ev = extract_shard(shard_path)
    ev["val"]=ev["numeric_value"]
    ev["time"]=pd.to_datetime(ev["time"])
    ev = ev.dropna(subset=["val"])

    # PHYSIOLOGICAL RANGE FILTER: drop impossible values per variable
    keep_mask = pd.Series(True, index=ev.index)
    for var,(lo,hi) in RANGES.items():
        m = ev["variable"]==var
        keep_mask &= ~(m & ((ev["val"]<lo) | (ev["val"]>hi)))
    ev = ev[keep_mask]

    onset_by = dict(zip(sepsis["subject_id"], pd.to_datetime(sepsis["sepsis_onset"])))
    ev = ev[ev["subject_id"].isin(onset_by.keys())].copy()
    ev["onset"] = ev["subject_id"].map(onset_by)
    win = (ev["time"] >= ev["onset"] - pd.Timedelta(hours=24)) & (ev["time"] <= ev["onset"])
    ev = ev[win]

    rows={sid:{"subject_id":sid} for sid in onset_by}
    for v in VITALS:
        m = ev[ev["variable"]==v].groupby("subject_id")["val"].mean()
        for sid,val in m.items(): rows[sid][v]=val
    for lab in LABS:
        how = "min" if lab=="platelets" else "max"
        g = ev[ev["variable"]==lab].groupby("subject_id")["val"]
        m = g.min() if how=="min" else g.max()
        for sid,val in m.items(): rows[sid][lab]=val

    cov = pd.DataFrame(rows.values())
    cov["map"] = cov["map_arterial"].combine_first(cov["map_noninvasive"])
    cov["temperature"] = cov["temp_c"].combine_first(
        cov["temp_f"].apply(lambda f: (f-32)*5/9 if pd.notna(f) else np.nan))
    cov = cov.drop(columns=["map_arterial","map_noninvasive","temp_c","temp_f"])
    return cov

if __name__ == "__main__":
    shard = find_shards()[0]
    sepsis = pd.read_parquet("results/sepsis_data_0.parquet")
    cov = build_covariates(shard, sepsis)

    pts = pd.read_csv(glob.glob("data/**/patients.csv", recursive=True)[0])
    cov = cov.merge(pts[["subject_id","gender","anchor_age"]], on="subject_id", how="left")
    cov = cov.rename(columns={"anchor_age":"age"})
    cov["male"] = (cov["gender"]=="M").astype(int)
    cov = cov.drop(columns=["gender"])
    cov.to_parquet("results/covariates_data_0.parquet", index=False)

    print(f"Covariate table: {len(cov)} patients x {cov.shape[1]} columns")
    print(f"columns: {list(cov.columns)}\n")
    print("Coverage (non-null %) and mean per covariate:")
    for c in cov.columns:
        if c=="subject_id": continue
        cov_pct = cov[c].notna().mean()
        mean = cov[c].mean() if cov[c].dtype!=object else np.nan
        print(f"  {c:16s} coverage {cov_pct:5.1%}  mean {mean:.2f}")