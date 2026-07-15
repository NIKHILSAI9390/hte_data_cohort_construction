"""Find where GCS values actually live — they vanished after dropna(numeric_value),
so the value is in text_value or elsewhere."""
import pandas as pd
from extract_sofa_values import extract_shard, find_shards

df = extract_shard(find_shards()[0])   # full extract, NO dropna
g = df[df["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])]

print(f"GCS rows (before any dropna): {len(g)}")
print(f"\nvalue field population for GCS:")
print(f"  numeric_value non-null: {g['numeric_value'].notna().sum()}")
print(f"  text_value non-null:    {g['text_value'].notna().sum()}")

print(f"\nsample GCS rows (all fields):")
print(g.head(15).to_string())

print(f"\nunique text_values for gcs_verbal (if text-coded):")
tv = g[g['variable']=='gcs_verbal']['text_value'].dropna().unique()
print(tv[:20])

print(f"\nunique numeric_values for gcs_eye (if numeric):")
nv = g[g['variable']=='gcs_eye']['numeric_value'].dropna().unique()
print(sorted(nv)[:20] if len(nv) else "none")