"""treatment.py — Treatment definition on the sepsis cohort."""
import glob, os
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

VASO = ["norepinephrine","epinephrine","dopamine","vasopressin","phenylephrine"]

def get_vaso_events(shard_path):
    ev = extract_shard(shard_path)
    v = ev[ev["variable"].isin(VASO)].copy()
    v["time"] = pd.to_datetime(v["time"])
    return v.groupby("subject_id")["time"].apply(lambda s: sorted(s.tolist()))

if __name__ == "__main__":
    shard = find_shards()[0]
    sepsis = pd.read_parquet("results/sepsis_data_0.parquet")
    sepsis["sepsis_onset"] = pd.to_datetime(sepsis["sepsis_onset"])
    print(f"sepsis patients in shard 0: {len(sepsis)}")

    vaso_by_pt = get_vaso_events(shard)

    rows=[]
    for _, r in sepsis.iterrows():
        sid=r["subject_id"]; onset=r["sepsis_onset"]
        vtimes = vaso_by_pt.get(sid, [])
        first_vaso = min(vtimes) if len(vtimes) else None
        pre_onset = any(t < onset for t in vtimes) if vtimes else False
        treated = False
        if first_vaso is not None:
            early = [t for t in vtimes if onset <= t <= onset + pd.Timedelta(hours=4)]
            treated = len(early) > 0
        rows.append({"subject_id":sid,"sepsis_onset":onset,
                     "first_vaso":first_vaso,"any_vaso":len(vtimes)>0,
                     "pre_onset_vaso":pre_onset,"treated":treated})

    t=pd.DataFrame(rows)
    t.to_parquet("results/treatment_data_0.parquet", index=False)

    n=len(t)
    print(f"\nTREATMENT SUMMARY (shard 0, {n} sepsis patients):")
    print(f"  received ANY vasopressor:        {t['any_vaso'].sum()} ({t['any_vaso'].mean():.1%})")
    print(f"  pre-onset vasopressor (exclude): {t['pre_onset_vaso'].sum()} ({t['pre_onset_vaso'].mean():.1%})")
    print(f"  TREATED (vaso within 4h onset):  {t['treated'].sum()} ({t['treated'].mean():.1%})")
    print(f"\n  paper reference: ~10% treated (2,184 / 21,859)")

    keep = t[~t["pre_onset_vaso"]]
    print(f"\n  After pre-onset exclusion: {len(keep)} patients, "
          f"treated {keep['treated'].sum()} ({keep['treated'].mean():.1%})")