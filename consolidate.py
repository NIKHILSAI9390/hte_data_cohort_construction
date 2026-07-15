"""consolidate.py — merge all 100 per-shard cohort files into ONE master table."""
import glob
import pandas as pd
import numpy as np

files = sorted(glob.glob("results/cohort_*.parquet"))
print(f"Merging {len(files)} shard cohort files...")
cohort = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

before=len(cohort)
cohort = cohort.drop_duplicates(subset=["subject_id"], keep="first")
print(f"  merged: {before} rows -> {len(cohort)} unique patients "
      f"({before-len(cohort)} cross-shard dups removed)")

cohort.to_parquet("results/master_cohort.parquet", index=False)
print(f"  saved -> results/master_cohort.parquet\n")

covs = ["age","male","sofa_peak","sapsii","charlson","map","heart_rate",
        "resp_rate","temperature","spo2","creatinine","wbc","platelets",
        "bilirubin_total","lactate"]
t=cohort[cohort["treated"]]; c=cohort[~cohort["treated"]]
print(f"COHORT: {len(cohort)} patients | treated {len(t)} ({cohort['treated'].mean():.1%}) "
      f"| control {len(c)}")
print(f"28-day mortality: {cohort['mortality_28d'].mean():.1%} "
      f"(treated {t['mortality_28d'].mean():.1%}, control {c['mortality_28d'].mean():.1%})\n")

print(f"TABLE 3 — covariate means (treated vs control), with missing %:")
print(f"  {'covariate':16s} {'treated':>9s} {'control':>9s} {'missing%':>9s}")
for cv in covs:
    if cv in cohort.columns:
        miss = cohort[cv].isna().mean()
        print(f"  {cv:16s} {t[cv].mean():>9.2f} {c[cv].mean():>9.2f} {miss:>8.1%}")

print(f"\nMissingness per covariate (paper imputes these with MICE):")
miss=cohort[covs].isna().mean().sort_values(ascending=False)
for k,v in miss.items():
    if v>0: print(f"  {k:16s} {v:.1%}")

ate_crude = t["mortality_28d"].mean() - c["mortality_28d"].mean()
print(f"\nCRUDE unadjusted ATE (treated - control mortality): {ate_crude:+.3f}")