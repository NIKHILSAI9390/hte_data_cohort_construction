"""Diagnose the MAP outlier problem — mean of 1565 is impossible."""
import pandas as pd, numpy as np, glob
from extract_sofa_values import extract_shard, find_shards

ev = extract_shard(find_shards()[0])
mapv = ev[ev["variable"].isin(["map_arterial","map_noninvasive"])].copy()
mapv["val"]=mapv["numeric_value"]
mapv=mapv.dropna(subset=["val"])

print("MAP value distribution (both itemids):")
print(mapv["val"].describe().to_string())
print(f"\n  values > 200 (physiologically impossible for MAP): {(mapv['val']>200).sum()}")
print(f"  values > 300: {(mapv['val']>300).sum()}")
print(f"  max value: {mapv['val'].max()}")
print(f"\n  sample of extreme values (>200):")
print(mapv[mapv['val']>200][['variable','val']].head(15).to_string())
print(f"\n  distribution of PLAUSIBLE MAP (20-200):")
print(mapv[(mapv['val']>=20)&(mapv['val']<=200)]['val'].describe().to_string())