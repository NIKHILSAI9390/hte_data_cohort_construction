"""suspicion_of_infection.py — Sepsis-3 suspected-infection timing.
Rule: infection suspected when antibiotic + culture occur close in time.
If culture first: antibiotic within +72h. If antibiotic first: culture within +24h.
Suspected-infection time = EARLIER of the pair."""
import glob
import pandas as pd
import numpy as np

def find_shards():
    return sorted(glob.glob("data/**/MEDS/data/data_*.parquet", recursive=True))

def get_cultures_from_shard(shard_path):
    df = pd.read_parquet(shard_path)
    id_col = "subject_id" if "subject_id" in df.columns else "patient_id"
    rows = []
    for _, r in df.iterrows():
        pid = r[id_col]
        for e in r["events"]:
            code = str(e.get("code",""))
            if code.startswith("MIMIC_IV_MicrobiologyTest"):
                rows.append((pid, e.get("time")))
    c = pd.DataFrame(rows, columns=["subject_id","culture_time"])
    c["culture_time"] = pd.to_datetime(c["culture_time"])
    return c

def suspicion_per_patient(abx_times, cx_times, abx_then_cx_h=24, cx_then_abx_h=72):
    best = None
    for a in abx_times:
        for c in cx_times:
            if a <= c <= a + pd.Timedelta(hours=abx_then_cx_h):
                t = min(a, c)
                if best is None or t < best: best = t
    for c in cx_times:
        for a in abx_times:
            if c <= a <= c + pd.Timedelta(hours=cx_then_abx_h):
                t = min(a, c)
                if best is None or t < best: best = t
    return best

if __name__ == "__main__":
    shard = find_shards()[0]
    print("Loading cultures from MEDS shard...")
    cx = get_cultures_from_shard(shard)
    print(f"  culture events: {len(cx):,}, patients with cultures: {cx['subject_id'].nunique():,}")

    print("Loading filtered antibiotics...")
    abx = pd.read_parquet("data/antibiotics_filtered.parquet")
    abx["starttime"] = pd.to_datetime(abx["starttime"])
    print(f"  antibiotic rows: {len(abx):,}")

    shard_patients = set(cx["subject_id"].unique())
    abx_s = abx[abx["subject_id"].isin(shard_patients)]
    print(f"  antibiotics for shard patients: {len(abx_s):,}, "
          f"patients: {abx_s['subject_id'].nunique():,}")

    abx_by_pt = abx_s.groupby("subject_id")["starttime"].apply(lambda s: sorted(s.tolist()))
    cx_by_pt  = cx.groupby("subject_id")["culture_time"].apply(lambda s: sorted(s.tolist()))

    both = set(abx_by_pt.index) & set(cx_by_pt.index)
    print(f"\n  patients with BOTH antibiotics and cultures: {len(both):,}")

    results = {}
    for pid in both:
        t = suspicion_per_patient(abx_by_pt[pid], cx_by_pt[pid])
        if t is not None:
            results[pid] = t

    si = pd.Series(results, name="suspected_infection_time")
    print(f"  patients with SUSPECTED INFECTION (valid abx-culture pair): {len(si):,}")
    print(f"\n  sample suspected-infection times:")
    print(si.head(10).to_string())