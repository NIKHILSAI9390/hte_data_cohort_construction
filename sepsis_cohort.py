"""sepsis_cohort.py — Sepsis-3 detection, ICU-stay-anchored (v2)."""
import glob, os, sys
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards
from sofa import gcs_points, s_coag, s_liver, s_renal, s_cns, s_resp, s_cardio

os.makedirs("results", exist_ok=True)
VASO = ["norepinephrine","epinephrine","dopamine","vasopressin","phenylephrine"]

def sofa_components_in_window(w):
    def worst(var, how):
        s = w[w["variable"]==var]["val"]
        if len(s)==0: return np.nan
        return s.min() if how=="min" else s.max()
    plt=worst("platelets","min"); bili=worst("bilirubin_total","max"); crea=worst("creatinine","max")
    mapv=worst("map_arterial","min")
    if pd.isna(mapv): mapv=worst("map_noninvasive","min")
    pao2=worst("pao2","min"); fio2=worst("fio2","max")
    fio2n=(fio2*100 if pd.notna(fio2) and fio2<=1 else fio2)
    ratio=(pao2/(fio2n/100.0)) if (pd.notna(pao2) and pd.notna(fio2n) and fio2n>0) else np.nan
    gw=[worst(v,"min") for v in ["gcs_eye","gcs_verbal","gcs_motor"]]
    gtot=(sum(gw) if all(pd.notna(x) for x in gw) else np.nan)
    vl=[worst(x,"max") for x in VASO]; vl=[x for x in vl if pd.notna(x)]
    vmax=max(vl) if vl else None
    return np.nansum([s_coag(plt),s_liver(bili),s_renal(crea),
                      s_cns(gtot),s_resp(ratio,False),s_cardio(mapv,vmax)])

def suspicion_near_stay(abx_times, cx_times, intime, outtime,
                        abx_then_cx_h=24, cx_then_abx_h=72):
    lo = intime - pd.Timedelta(days=1); hi = outtime + pd.Timedelta(days=1)
    a_near = [a for a in abx_times if lo <= a <= hi]
    c_near = [c for c in cx_times if lo <= c <= hi]
    best=None
    for a in a_near:
        for c in c_near:
            if a <= c <= a + pd.Timedelta(hours=abx_then_cx_h):
                t=min(a,c); best=t if best is None or t<best else best
    for c in c_near:
        for a in a_near:
            if c <= a <= c + pd.Timedelta(hours=cx_then_abx_h):
                t=min(a,c); best=t if best is None or t<best else best
    return best

def process_shard(shard_path, icu, abx_by_pt, patients_age):
    shard_id = os.path.basename(shard_path).replace(".parquet","")
    out_path = f"results/sepsis_{shard_id}.parquet"
    if os.path.exists(out_path):
        print(f"  {shard_id}: already done, skipping"); return

    ev = extract_shard(shard_path)
    ev["val"]=ev["numeric_value"]
    gm=ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])
    ev.loc[gm,"val"]=[gcs_points(v,t) for v,t in zip(ev.loc[gm,"variable"],ev.loc[gm,"text_value"])]
    ev=ev.dropna(subset=["val"]); ev["time"]=pd.to_datetime(ev["time"])

    dfm=pd.read_parquet(shard_path)
    idc="subject_id" if "subject_id" in dfm.columns else "patient_id"
    cx_rows=[]
    for _,r in dfm.iterrows():
        for e in r["events"]:
            if str(e.get("code","")).startswith("MIMIC_IV_MicrobiologyTest"):
                cx_rows.append((r[idc], pd.to_datetime(e.get("time"))))
    cx=pd.DataFrame(cx_rows,columns=["subject_id","culture_time"])
    cx_by=cx.groupby("subject_id")["culture_time"].apply(lambda s:sorted(s.tolist())) if len(cx) else pd.Series(dtype=object)

    results=[]
    icu_shard = icu[icu["subject_id"].isin(ev["subject_id"].unique())]
    for sid, stays in icu_shard.groupby("subject_id"):
        age = patients_age.get(sid)
        if age is None or age < 18: continue
        if sid not in abx_by_pt.index or sid not in cx_by.index: continue
        pev = ev[ev["subject_id"]==sid]
        atimes = abx_by_pt[sid]; ctimes = cx_by[sid]
        for _, s in stays.sort_values("intime").iterrows():
            intime=pd.to_datetime(s["intime"]); outtime=pd.to_datetime(s["outtime"])
            si = suspicion_near_stay(atimes, ctimes, intime, outtime)
            if si is None: continue
            lo=max(intime, si-pd.Timedelta(hours=48)); hi=min(outtime, si+pd.Timedelta(hours=24))
            stay_ev=pev[(pev["time"]>=intime-pd.Timedelta(hours=24)) & (pev["time"]<=hi)]
            tps=sorted(stay_ev[(stay_ev["time"]>=lo)&(stay_ev["time"]<=hi)]["time"].unique())
            if not tps: continue
            sofas=np.array([sofa_components_in_window(
                stay_ev[(stay_ev["time"]>t-pd.Timedelta(hours=24))&(stay_ev["time"]<=t)]) for t in tps])
            peak=np.nanmax(sofas)
            if peak >= 2:
                
                results.append({"subject_id":sid,"stay_id":s["stay_id"],
                                "intime":intime,"suspected_infection":si,
                                "sepsis_onset":si,
                                "sofa_peak":peak,"age":age})
                break
    res=pd.DataFrame(results)
    res.to_parquet(out_path,index=False)
    print(f"  {shard_id}: {len(res)} sepsis patients -> {out_path}")

if __name__=="__main__":
    icu=pd.read_csv(glob.glob("data/**/icustays.csv",recursive=True)[0])
    pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
    patients_age=dict(zip(pts["subject_id"], pts["anchor_age"]))
    abx=pd.read_parquet("data/antibiotics_filtered.parquet")
    abx["starttime"]=pd.to_datetime(abx["starttime"])
    abx_by=abx.groupby("subject_id")["starttime"].apply(lambda s:sorted(s.tolist()))

    shards=find_shards()
    start=int(sys.argv[1]) if len(sys.argv)>1 else 0
    end=int(sys.argv[2]) if len(sys.argv)>2 else 1
    print(f"Processing shards {start}..{end-1} of {len(shards)}")
    for sp in shards[start:end]:
        process_shard(sp, icu, abx_by, patients_age)
    done=glob.glob("results/sepsis_*.parquet")
    tot=sum(len(pd.read_parquet(f)) for f in done)
    print(f"\nShards done: {len(done)}/{len(shards)}, cumulative sepsis patients: {tot}")
    print(f"(paper reference across ALL shards: ~32,899)")