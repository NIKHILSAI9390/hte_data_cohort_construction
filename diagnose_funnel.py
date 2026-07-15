"""Diagnose WHERE patients are lost in sepsis detection on one shard,
to understand the ~half-of-paper shortfall."""
import glob, pandas as pd, numpy as np
from extract_sofa_values import extract_shard, find_shards
from suspicion_of_infection import suspicion_per_patient

icu=pd.read_csv(glob.glob("data/**/icustays.csv",recursive=True)[0])
pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
patients_age=dict(zip(pts["subject_id"], pts["anchor_age"]))
abx=pd.read_parquet("data/antibiotics_filtered.parquet")
abx["starttime"]=pd.to_datetime(abx["starttime"])
abx_by=abx.groupby("subject_id")["starttime"].apply(lambda s:sorted(s.tolist()))

shard=find_shards()[0]
ev=extract_shard(shard)
shard_patients=set(ev["subject_id"].unique())

# cultures
dfm=pd.read_parquet(shard)
idc="subject_id" if "subject_id" in dfm.columns else "patient_id"
cx_rows=[]
for _,r in dfm.iterrows():
    for e in r["events"]:
        if str(e.get("code","")).startswith("MIMIC_IV_MicrobiologyTest"):
            cx_rows.append((r[idc], pd.to_datetime(e.get("time"))))
cx=pd.DataFrame(cx_rows,columns=["subject_id","culture_time"])
cx_by=cx.groupby("subject_id")["culture_time"].apply(lambda s:sorted(s.tolist()))

# ICU patients in this shard
icu_pts = set(icu[icu["subject_id"].isin(shard_patients)]["subject_id"].unique())

print(f"FUNNEL for shard 0:")
print(f"  total patients in shard:        {len(shard_patients)}")
print(f"  ... with an ICU stay:           {len(icu_pts)}")
age_ok = {s for s in icu_pts if patients_age.get(s,0) and patients_age.get(s,0)>=18}
print(f"  ... age >= 18:                  {len(age_ok)}")
have_abx = {s for s in age_ok if s in abx_by.index}
print(f"  ... with antibiotics:           {len(have_abx)}")
have_cx = {s for s in have_abx if s in cx_by.index}
print(f"  ... with cultures too:          {len(have_cx)}")
have_si = {s for s in have_cx if suspicion_per_patient(abx_by[s], cx_by[s]) is not None}
print(f"  ... with valid infection pair:  {len(have_si)}")
print(f"\n  (final sepsis after SOFA>=2 rise was 155)")
print(f"\n  Antibiotic coverage: {len(have_abx)}/{len(age_ok)} = "
      f"{len(have_abx)/max(1,len(age_ok)):.1%} of ICU adults have antibiotics")