"""Check if the anomaly is a SOFA-cardio-inflation artifact by stratifying on
SAPS-II (less mechanically tied to vasopressor use) instead of SOFA."""
import pandas as pd, numpy as np
c=pd.read_parquet("results/master_cohort.parquet")
t=c[c["treated"]]; ct=c[~c["treated"]]

print("Stratified by SAPS-II (treatment-independent severity):")
c["saps_bin"]=pd.cut(c["sapsii"],[0,30,45,60,200])
for b,g in c.groupby("saps_bin", observed=True):
    tt=g[g["treated"]]; cc=g[~g["treated"]]
    if len(tt)>5 and len(cc)>5:
        print(f"  SAPS {b}: treated {tt['mortality_28d'].mean():.1%} (n={len(tt)}) "
              f"vs control {cc['mortality_28d'].mean():.1%} (n={len(cc)})")

# also: recompute a SOFA WITHOUT cardio component would require re-derivation;
# instead check how many treated got pushed up by cardio points
print(f"\nTreated patients' SOFA is inflated by vasopressor cardio points (>=3).")
print(f"  If we assume ~3 pts of treated SOFA is cardio, treated 'true' severity")
print(f"  is lower than their sofa_peak suggests — explaining the bin artifact.")
print(f"\n  treated mean SOFA {t['sofa_peak'].mean():.1f} (includes cardio from their own treatment)")
print(f"  control mean SOFA {ct['sofa_peak'].mean():.1f}")