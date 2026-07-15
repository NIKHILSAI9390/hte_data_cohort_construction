"""Why do 345 infection-suspected patients drop to 155 at SOFA>=2?
Show the SOFA baseline/peak/rise distribution to see if the rise criterion is too strict."""
import glob, os, pandas as pd, numpy as np
from extract_sofa_values import extract_shard, find_shards
from sofa import gcs_points, s_coag, s_liver, s_renal, s_cns, s_resp, s_cardio
from suspicion_of_infection import suspicion_per_patient
from sepsis_cohort import sofa_components_in_window, VASO

icu=pd.read_csv(glob.glob("data/**/icustays.csv",recursive=True)[0])
pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
age=dict(zip(pts["subject_id"],pts["anchor_age"]))
abx=pd.read_parquet("data/antibiotics_filtered.parquet"); abx["starttime"]=pd.to_datetime(abx["starttime"])
abx_by=abx.groupby("subject_id")["starttime"].apply(lambda s:sorted(s.tolist()))

shard=find_shards()[0]
ev=extract_shard(shard)
ev["val"]=ev["numeric_value"]
gm=ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])
ev.loc[gm,"val"]=[gcs_points(v,t) for v,t in zip(ev.loc[gm,"variable"],ev.loc[gm,"text_value"])]
ev=ev.dropna(subset=["val"]); ev["time"]=pd.to_datetime(ev["time"])

dfm=pd.read_parquet(shard); idc="subject_id" if "subject_id" in dfm.columns else "patient_id"
cx_rows=[]
for _,r in dfm.iterrows():
    for e in r["events"]:
        if str(e.get("code","")).startswith("MIMIC_IV_MicrobiologyTest"):
            cx_rows.append((r[idc],pd.to_datetime(e.get("time"))))
cx=pd.DataFrame(cx_rows,columns=["subject_id","culture_time"])
cx_by=cx.groupby("subject_id")["culture_time"].apply(lambda s:sorted(s.tolist()))

rows=[]
icu_shard=icu[icu["subject_id"].isin(ev["subject_id"].unique())]
for sid,stay in icu_shard.groupby("subject_id"):
    if age.get(sid,0)<18 or sid not in abx_by.index or sid not in cx_by.index: continue
    si=suspicion_per_patient(abx_by[sid],cx_by[sid])
    if si is None: continue
    pev=ev[ev["subject_id"]==sid]; stay=stay.sort_values("intime")
    for _,s in stay.iterrows():
        intime=pd.to_datetime(s["intime"]); outtime=pd.to_datetime(s["outtime"])
        if not (intime-pd.Timedelta(days=1)<=si<=outtime+pd.Timedelta(days=1)): continue
        lo=max(intime,si-pd.Timedelta(hours=48)); hi=min(outtime,si+pd.Timedelta(hours=24))
        stay_ev=pev[(pev["time"]>=intime-pd.Timedelta(hours=24))&(pev["time"]<=hi)]
        tps=sorted(stay_ev[(stay_ev["time"]>=lo)&(stay_ev["time"]<=hi)]["time"].unique())
        if not tps: continue
        sofas=np.array([sofa_components_in_window(
            stay_ev[(stay_ev["time"]>t-pd.Timedelta(hours=24))&(stay_ev["time"]<=t)]) for t in tps])
        baseline=np.nanmin(sofas[:max(1,len(sofas)//4)])
        rows.append({"peak":np.nanmax(sofas),"baseline":baseline,
                     "rise":np.nanmax(sofas)-baseline,"n_timepoints":len(tps)})
        break

d=pd.DataFrame(rows)
print(f"infection-suspected stays analyzed: {len(d)}")
print(f"\nSOFA PEAK distribution (max SOFA reached):")
print(d["peak"].describe().to_string())
print(f"\n  peak >= 2 (would qualify under 'SOFA>=2' rule): {(d['peak']>=2).sum()} ({(d['peak']>=2).mean():.1%})")
print(f"  rise >= 2 (current 'rise above baseline' rule): {(d['rise']>=2).sum()} ({(d['rise']>=2).mean():.1%})")
print(f"\nBASELINE distribution (are patients already sick at window start?):")
print(d["baseline"].describe().to_string())
print(f"\n  n_timepoints distribution (enough data to see a rise?):")
print(d["n_timepoints"].describe().to_string())