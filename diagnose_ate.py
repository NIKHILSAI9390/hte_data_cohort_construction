"""Diagnose why crude ATE is ~0 despite treated being much sicker."""
import pandas as pd, numpy as np
c=pd.read_parquet("results/master_cohort.parquet")
c["sepsis_onset"]=pd.to_datetime(c["sepsis_onset"])

t=c[c["treated"]]; ct=c[~c["treated"]]
print("Mortality by group:", f"treated {t['mortality_28d'].mean():.1%}, control {ct['mortality_28d'].mean():.1%}")

# Is mortality monotonic in severity? bin by SOFA and check mortality
print("\nMortality by SOFA bin (should rise with SOFA):")
c["sofa_bin"]=pd.cut(c["sofa_peak"],[0,4,8,12,25])
print(c.groupby("sofa_bin")["mortality_28d"].agg(["mean","count"]).to_string())

# within same SOFA bin, treated vs control mortality (severity-matched)
print("\nMortality treated vs control WITHIN SOFA bins (crude confounding check):")
for b,g in c.groupby("sofa_bin"):
    tt=g[g["treated"]]; cc=g[~g["treated"]]
    if len(tt)>5 and len(cc)>5:
        print(f"  SOFA {b}: treated {tt['mortality_28d'].mean():.1%} (n={len(tt)}) "
              f"vs control {cc['mortality_28d'].mean():.1%} (n={len(cc)})")

# check: do treated patients have plausible time-to-death?
print("\nAmong treated who died: are deaths within window sensible?")
print(f"  treated mortality {t['mortality_28d'].mean():.1%}, control {ct['mortality_28d'].mean():.1%}")
print(f"  treated SOFA {t['sofa_peak'].mean():.1f}, control {ct['sofa_peak'].mean():.1f}")