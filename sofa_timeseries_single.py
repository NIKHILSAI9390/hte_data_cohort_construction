"""Time-series SOFA for ONE patient — conference-fidelity verification."""
import glob
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards
from sofa import (gcs_points, s_coag, s_liver, s_renal, s_cns, s_resp, s_cardio)

def load_patient_events(shard_path, subject_id):
    ev = extract_shard(shard_path)
    ev = ev[ev["subject_id"] == subject_id].copy()
    ev["val"] = ev["numeric_value"]
    gm = ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])
    ev.loc[gm,"val"] = [gcs_points(v,t) for v,t in zip(ev.loc[gm,"variable"], ev.loc[gm,"text_value"])]
    ev = ev.dropna(subset=["val"])
    ev["time"] = pd.to_datetime(ev["time"])
    return ev.sort_values("time")

def sofa_at(ev, t, lookback_h=24):
    w = ev[(ev["time"] > t - pd.Timedelta(hours=lookback_h)) & (ev["time"] <= t)]
    if len(w)==0: return np.nan, {}
    def worst(var, how):
        s = w[w["variable"]==var]["val"]
        if len(s)==0: return np.nan
        return s.min() if how=="min" else s.max()
    plt=worst("platelets","min"); bili=worst("bilirubin_total","max")
    crea=worst("creatinine","max")
    mapv=worst("map_arterial","min")
    if pd.isna(mapv): mapv=worst("map_noninvasive","min")
    pao2=worst("pao2","min"); fio2=worst("fio2","max")
    fio2n=(fio2*100 if pd.notna(fio2) and fio2<=1 else fio2)
    ratio=(pao2/(fio2n/100.0)) if (pd.notna(pao2) and pd.notna(fio2n) and fio2n>0) else np.nan
    gw={v:worst(v,"min") for v in ["gcs_eye","gcs_verbal","gcs_motor"]}
    gtot=(sum(gw.values()) if all(pd.notna(x) for x in gw.values()) else np.nan)
    vlist=[worst(x,"max") for x in ["norepinephrine","epinephrine","dopamine","vasopressin","phenylephrine"]]
    vlist=[x for x in vlist if pd.notna(x)]
    vmax=max(vlist) if vlist else np.nan
    comps={"coag":s_coag(plt),"liver":s_liver(bili),"renal":s_renal(crea),
           "cns":s_cns(gtot),"resp":s_resp(ratio,False),
           "cardio":s_cardio(mapv, vmax if pd.notna(vmax) else None)}
    total=np.nansum([v for v in comps.values()])
    return total, comps

if __name__ == "__main__":
    shard = find_shards()[0]
    from suspicion_of_infection import get_cultures_from_shard, suspicion_per_patient
    cx = get_cultures_from_shard(shard)
    abx = pd.read_parquet("data/antibiotics_filtered.parquet")
    abx["starttime"]=pd.to_datetime(abx["starttime"])
    abx=abx[abx["subject_id"].isin(cx["subject_id"].unique())]
    abx_by=abx.groupby("subject_id")["starttime"].apply(lambda s:sorted(s.tolist()))
    cx_by=cx.groupby("subject_id")["culture_time"].apply(lambda s:sorted(s.tolist()))
    both=set(abx_by.index)&set(cx_by.index)
    pid=None; si_time=None
    for p in both:
        t=suspicion_per_patient(abx_by[p],cx_by[p])
        if t is not None:
            ev=load_patient_events(shard,p)
            if ev["time"].nunique()>40:
                pid=p; si_time=t; break

    print(f"Patient {pid}, suspected infection at {si_time}\n")
    ev=load_patient_events(shard,pid)
    print(f"  total measurements: {len(ev)}, distinct times: {ev['time'].nunique()}")
    print(f"  time span: {ev['time'].min()} -> {ev['time'].max()}")

    times=sorted(ev["time"].unique())
    traj=[]
    for t in times:
        tot,comps=sofa_at(ev,pd.Timestamp(t))
        traj.append((pd.Timestamp(t),tot))
    tr=pd.DataFrame(traj,columns=["time","sofa"])

    print(f"\n  SOFA trajectory (every ~10th timepoint):")
    print(tr.iloc[::max(1,len(tr)//20)].to_string(index=False))

    lo,hi=si_time-pd.Timedelta(hours=48), si_time+pd.Timedelta(hours=24)
    win=tr[(tr["time"]>=lo)&(tr["time"]<=hi)]
    if len(win):
        baseline=win["sofa"].iloc[0]; peak=win["sofa"].max()
        print(f"\n  SUSPICION WINDOW [si-48h, si+24h]:")
        print(f"    SOFA at window start: {baseline:.0f}")
        print(f"    SOFA peak in window:  {peak:.0f}")
        print(f"    RISE: {peak-baseline:.0f}  -> {'SEPSIS (>=2)' if peak-baseline>=2 else 'not sepsis'}")