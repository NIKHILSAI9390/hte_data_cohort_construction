"""sofa.py — First-24h ICU SOFA, all six organ systems, windowed to icustays.intime."""
import glob
import pandas as pd
import numpy as np
from extract_sofa_values import extract_shard, find_shards

EYE = {"Spontaneously":4,"To Speech":3,"To Pain":2,"None":1}
VERBAL = {"Oriented":5,"Confused":4,"Inappropriate Words":3,
          "Incomprehensible sounds":2,"No Response":1,"No Response-ETT":1}
MOTOR = {"Obeys Commands":6,"Localizes Pain":5,"Flex-withdraws":4,
         "Abnormal Flexion":3,"Abnormal extension":2,"No response":1,"No Response":1}
def gcs_points(var, txt):
    if txt is None: return np.nan
    return {"gcs_eye":EYE,"gcs_verbal":VERBAL,"gcs_motor":MOTOR}[var].get(txt, np.nan)

def s_coag(p):  return np.nan if pd.isna(p) else (4 if p<20 else 3 if p<50 else 2 if p<100 else 1 if p<150 else 0)
def s_liver(b): return np.nan if pd.isna(b) else (4 if b>=12 else 3 if b>=6 else 2 if b>=2 else 1 if b>=1.2 else 0)
def s_renal(c): return np.nan if pd.isna(c) else (4 if c>=5 else 3 if c>=3.5 else 2 if c>=2 else 1 if c>=1.2 else 0)
def s_cns(g):   return np.nan if pd.isna(g) else (4 if g<6 else 3 if g<10 else 2 if g<13 else 1 if g<15 else 0)
def s_resp(ratio, vent):
    if pd.isna(ratio): return np.nan
    if ratio < 100 and vent: return 4
    if ratio < 200 and vent: return 3
    if ratio < 300: return 2
    if ratio < 400: return 1
    return 0
def s_cardio(map_val, vaso_max):
    if vaso_max is not None and vaso_max > 0:
        return 3
    if pd.isna(map_val): return np.nan
    return 1 if map_val < 70 else 0

def compute_sofa_for_shard(shard_path, icu):
    ev = extract_shard(shard_path)
    ev["val"] = ev["numeric_value"]
    gcs_mask = ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])
    ev.loc[gcs_mask, "val"] = [gcs_points(v,t) for v,t in
                               zip(ev.loc[gcs_mask,"variable"], ev.loc[gcs_mask,"text_value"])]
    ev = ev.dropna(subset=["val"])

    ev = ev.merge(icu[["subject_id","stay_id","intime"]], on="subject_id", how="inner")
    ev["intime"] = pd.to_datetime(ev["intime"])
    ev["time"] = pd.to_datetime(ev["time"])
    win = (ev["time"] >= ev["intime"]) & (ev["time"] <= ev["intime"] + pd.Timedelta(hours=24))
    ev = ev[win]

    def worst(var, how):
        s = ev[ev["variable"]==var].groupby("stay_id")["val"]
        return s.min() if how=="min" else s.max()

    plt   = worst("platelets","min")
    bili  = worst("bilirubin_total","max")
    crea  = worst("creatinine","max")
    mapv  = worst("map_arterial","min").combine_first(worst("map_noninvasive","min"))
    pao2  = worst("pao2","min")
    fio2  = worst("fio2","max")
    fio2n = fio2.apply(lambda x: x*100 if pd.notna(x) and x<=1 else x)
    ratio = (pao2 / (fio2n/100.0))
    vent  = pd.Series(False, index=ratio.index)

    gwide = (ev[ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])]
             .pivot_table(index="stay_id", columns="variable", values="val", aggfunc="min"))
    gtot = gwide.reindex(columns=["gcs_eye","gcs_verbal","gcs_motor"]).sum(axis=1, min_count=3)

    vaso = ev[ev["variable"].isin(["norepinephrine","epinephrine","dopamine",
                                    "vasopressin","phenylephrine"])]
    vmax = vaso.groupby("stay_id")["val"].max()

    stays = icu["stay_id"]
    out = pd.DataFrame(index=stays.values)
    out["coag"]  = plt.map(s_coag)
    out["liver"] = bili.map(s_liver)
    out["renal"] = crea.map(s_renal)
    out["cns"]   = gtot.map(s_cns)
    out["resp"]  = [s_resp(r, v) for r,v in zip(ratio.reindex(out.index),
                                                vent.reindex(out.index).fillna(False))]
    out["cardio"]= [s_cardio(m, vmax.get(sid)) for sid,m in
                    zip(out.index, mapv.reindex(out.index))]
    out["sofa_total"] = out[["coag","liver","renal","cns","resp","cardio"]].sum(axis=1, min_count=1)
    return out

if __name__ == "__main__":
    icu = pd.read_csv(glob.glob("data/**/icustays.csv", recursive=True)[0])
    shard = find_shards()[0]
    print("Computing first-24h SOFA on one shard...\n")
    sofa = compute_sofa_for_shard(shard, icu)
    print(f"stays with a SOFA total: {sofa['sofa_total'].notna().sum()}")
    print(f"\nper-component coverage & mean score:")
    for c in ["coag","liver","renal","cns","resp","cardio"]:
        s = sofa[c]
        print(f"  {c:7s}: {s.notna().sum():5d} stays, mean {s.mean():.2f}, "
              f"dist {s.value_counts().sort_index().to_dict()}")
    print(f"\nTOTAL SOFA distribution:")
    print(sofa['sofa_total'].describe().to_string())
    print(f"\n  histogram:")
    print(sofa['sofa_total'].value_counts().sort_index().to_string())