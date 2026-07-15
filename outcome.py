"""outcome.py — 28-day all-cause mortality outcome."""
import glob
import pandas as pd
import numpy as np

pts = pd.read_csv(glob.glob("data/**/patients.csv", recursive=True)[0])
adm = pd.read_csv(glob.glob("data/**/admissions.csv", recursive=True)[0])
icu = pd.read_csv(glob.glob("data/**/icustays.csv", recursive=True)[0])

pts["dod"] = pd.to_datetime(pts["dod"])
dod_by_pt = dict(zip(pts["subject_id"], pts["dod"]))
los_by_stay = dict(zip(icu["stay_id"], icu["los"]))

sepsis = pd.read_parquet("results/sepsis_data_0.parquet")
sepsis["sepsis_onset"] = pd.to_datetime(sepsis["sepsis_onset"])
treat = pd.read_parquet("results/treatment_data_0.parquet")

df = sepsis.merge(treat[["subject_id","treated","pre_onset_vaso"]], on="subject_id", how="left")

rows=[]
for _, r in df.iterrows():
    sid=r["subject_id"]; onset=r["sepsis_onset"]; stay_id=r["stay_id"]
    dod = dod_by_pt.get(sid)
    mortality = 0
    if pd.notna(dod):
        days = (dod - onset).days
        if 0 <= days <= 28:
            mortality = 1
        elif days < 0:
            mortality = np.nan
    los_days = los_by_stay.get(stay_id, np.nan)
    icu_short = (los_days < 0.25) if pd.notna(los_days) else False
    rows.append({"subject_id":sid,"treated":r["treated"],
                 "pre_onset_vaso":r["pre_onset_vaso"],
                 "mortality_28d":mortality,"los_days":los_days,"icu_short":icu_short})

o=pd.DataFrame(rows)
o.to_parquet("results/outcome_data_0.parquet", index=False)

n=len(o)
print(f"OUTCOME SUMMARY (shard 0, {n} sepsis patients):")
print(f"  deaths before onset (data issue): {o['mortality_28d'].isna().sum()}")
print(f"  28-day mortality (all):           {o['mortality_28d'].mean():.1%}")
print(f"  ICU <6h (exclude):                {o['icu_short'].sum()} ({o['icu_short'].mean():.1%})")
print(f"\n  paper reference: 28-day mortality 17.3%, ICU<6h drops only 38/32899 (~0.1%)")

final = o[(~o["pre_onset_vaso"]) & (~o["icu_short"]) & (o["mortality_28d"].notna())]
print(f"\n  AFTER exclusions (pre-onset vaso + ICU<6h): {len(final)} patients")
print(f"    28-day mortality: {final['mortality_28d'].mean():.1%}  (paper: 17.3%)")
print(f"    treated:          {final['treated'].mean():.1%}  (paper: 10.0%)")
print(f"\n  mortality by treatment group:")
print(f"    treated:  {final[final['treated']]['mortality_28d'].mean():.1%} "
      f"(n={final['treated'].sum()})")
print(f"    control:  {final[~final['treated']]['mortality_28d'].mean():.1%} "
      f"(n={(~final['treated']).sum()})")
print(f"  (paper: treated 26.2%, control 16.3%)")