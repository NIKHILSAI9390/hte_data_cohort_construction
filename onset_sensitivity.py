"""onset_sensitivity.py — test how treated/control split and crude ATE change
under different sepsis-onset definitions."""
import glob, os
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

VASO=["norepinephrine","epinephrine","dopamine","vasopressin","phenylephrine"]

def all_vaso_times():
    cache="results/_vaso_times.parquet"
    if os.path.exists(cache):
        v=pd.read_parquet(cache)
        v["time"]=pd.to_datetime(v["time"])
        return v.groupby("subject_id")["time"].apply(list)
    rows=[]
    for sp in find_shards():
        ev=extract_shard(sp)
        vv=ev[ev["variable"].isin(VASO)][["subject_id","time"]]
        rows.append(vv)
    allv=pd.concat(rows,ignore_index=True)
    allv["time"]=pd.to_datetime(allv["time"])
    allv.to_parquet(cache,index=False)
    return allv.groupby("subject_id")["time"].apply(list)

def treated_under(onset_series, vaso_by, dod_by, cohort):
    rows=[]
    for sid,onset in onset_series.items():
        if pd.isna(onset): continue
        vt=vaso_by.get(sid,[])
        treated=any(onset<=t<=onset+pd.Timedelta(hours=4) for t in vt) if len(vt) else False
        pre=any(t<onset for t in vt) if len(vt) else False
        dod=dod_by.get(sid)
        mort=np.nan
        if pd.isna(dod): mort=0
        else:
            d=(dod-onset).days
            mort = 1 if 0<=d<=28 else (np.nan if d<0 else 0)
        rows.append({"subject_id":sid,"treated":treated,"pre_onset_vaso":pre,"mortality_28d":mort})
    d=pd.DataFrame(rows)
    d=d[(~d["pre_onset_vaso"]) & (d["mortality_28d"].notna())]
    t=d[d["treated"]]; c=d[~d["treated"]]
    return {"n":len(d),"treated_rate":d["treated"].mean(),
            "mort_treated":t["mortality_28d"].mean(),"mort_control":c["mortality_28d"].mean(),
            "crude_ate":t["mortality_28d"].mean()-c["mortality_28d"].mean()}

if __name__=="__main__":
    cohort=pd.read_parquet("results/master_cohort.parquet")
    for col in ["sepsis_onset","intime"]:
        if col in cohort: cohort[col]=pd.to_datetime(cohort[col])
    sic=pd.concat([pd.read_parquet(f)[["subject_id","suspected_infection","intime"]]
                   for f in glob.glob("results/sepsis_*.parquet")],ignore_index=True)
    sic["suspected_infection"]=pd.to_datetime(sic["suspected_infection"])
    sic["intime"]=pd.to_datetime(sic["intime"])
    sic=sic.drop_duplicates("subject_id")

    pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
    pts["dod"]=pd.to_datetime(pts["dod"]); dod_by=dict(zip(pts["subject_id"],pts["dod"]))

    print("Building vasopressor time cache (one pass over shards, then cached)...")
    vaso_by=all_vaso_times()

    m=cohort.merge(sic,on="subject_id",how="left",suffixes=("","_s"))
    susp=dict(zip(m["subject_id"],m["suspected_infection"]))
    intime=dict(zip(m["subject_id"],m["intime"]))

    print("\nCrude ATE under different ONSET definitions:\n")
    variants={
      "A: suspicion time (current)": pd.Series(susp),
      "B: ICU admission (intime)":   pd.Series(intime),
      "C: suspicion + 6h":           pd.Series({k:(v+pd.Timedelta(hours=6) if pd.notna(v) else v) for k,v in susp.items()}),
    }
    print(f"  {'onset def':32s} {'n':>6s} {'trt%':>6s} {'mTrt':>6s} {'mCtl':>6s} {'ATE':>7s}")
    for name,os_ in variants.items():
        r=treated_under(os_,vaso_by,dod_by,cohort)
        print(f"  {name:32s} {r['n']:>6d} {r['treated_rate']:>6.1%} "
              f"{r['mort_treated']:>6.1%} {r['mort_control']:>6.1%} {r['crude_ate']:>+7.3f}")