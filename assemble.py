"""assemble.py — merge all pieces into ONE analysis-ready patient-level table."""
import glob, os, sys
import pandas as pd
import numpy as np

def assemble_shard(shard_tag):
    R=f"results"
    def load(name):
        p=f"{R}/{name}_{shard_tag}.parquet"
        return pd.read_parquet(p) if os.path.exists(p) else None

    sepsis=load("sepsis"); treat=load("treatment"); out=load("outcome")
    cov=load("covariates"); ch=load("charlson"); saps=load("sapsii")
    if any(x is None for x in [sepsis,treat,out,cov,ch,saps]):
        print(f"  {shard_tag}: missing a piece, skipping"); return None

    df = sepsis[["subject_id","stay_id","sepsis_onset","sofa_peak"]].copy()
    df = df.merge(out[["subject_id","treated","pre_onset_vaso","mortality_28d",
                       "los_days","icu_short"]], on="subject_id", how="left")
    df = df.merge(cov.drop(columns=[c for c in ["age"] if c in cov.columns and c in df.columns],
                           errors="ignore"), on="subject_id", how="left")
    ch=ch.reset_index().rename(columns={"index":"subject_id"})
    saps=saps.reset_index().rename(columns={"index":"subject_id"})
    df=df.merge(ch, on="subject_id", how="left").merge(saps, on="subject_id", how="left")
    return df

def apply_funnel(df):
    n0=len(df); print(f"  start (Sepsis-3):                 {n0}")
    df=df[~df["icu_short"].fillna(False)]
    print(f"  after ICU>=6h:                    {len(df)}  (-{n0-len(df)})")
    n1=len(df); df=df[~df["pre_onset_vaso"].fillna(False)]
    print(f"  after no pre-onset vasopressor:   {len(df)}  (-{n1-len(df)})")
    n2=len(df); df=df[df["mortality_28d"].notna()]
    print(f"  after valid outcome:              {len(df)}  (-{n2-len(df)})")
    return df

if __name__=="__main__":
    tag = sys.argv[1] if len(sys.argv)>1 else "data_0"
    df = assemble_shard(tag)
    if df is None: raise SystemExit

    print(f"\nASSEMBLED cohort for {tag}: {len(df)} patients, {df.shape[1]} columns")
    print(f"columns: {list(df.columns)}\n")
    print("EXCLUSION FUNNEL:")
    final = apply_funnel(df)
    final.to_parquet(f"results/cohort_{tag}.parquet", index=False)

    print(f"\nFINAL analysis cohort: {len(final)} patients")
    print(f"  treated: {final['treated'].mean():.1%}")
    print(f"  28-day mortality: {final['mortality_28d'].mean():.1%}")

    print(f"\nCOVARIATE MEANS (validate vs paper Table 3), treated vs control:")
    covs=["age","male","sofa_peak","sapsii","charlson","map","heart_rate",
          "resp_rate","temperature","spo2","creatinine","wbc","platelets",
          "bilirubin_total","lactate"]
    t=final[final["treated"]]; c=final[~final["treated"]]
    print(f"  {'covariate':16s} {'treated':>10s} {'control':>10s}")
    for cv in covs:
        if cv in final.columns:
            print(f"  {cv:16s} {t[cv].mean():>10.2f} {c[cv].mean():>10.2f}")