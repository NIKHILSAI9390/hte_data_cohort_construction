#inspects the meds data properly
import json
import os 
import glob
import pandas as pd 
import pyarrow.parquet as pq
#find all shards across BOTH download folders
SHARDS=glob.glob("data/**/data_*.parquet", recursive=True)
META=glob.glob("data/**/metadata.json", recursive=True)
print(f"Found {len(SHARDS)} parquet shards, {len(META)} metadata file(s)\n")
#read metadata.json
if META:
    with open(META[0]) as f:
        meta = json.load(f)
    print("METADATA keys:", list(meta.keys()))
#MEDS metadata usually has a 'codes' or dataset description
    for k, v in meta.items():
        if isinstance(v, (str, int, float)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: dict with {len(v)} entries, sample keys: {list(v.keys())[:5]}")
        elif isinstance(v, list):
            print(f"  {k}: list of {len(v)}, sample: {v[:3]}")
    print()
#load one shard to see data schema
shard=  SHARDS[0]
print(f"Loading one shard: {os.path.basename(shard)}")
df=pd.read_parquet(shard)
print(f"  shape: {df.shape}")
print(f"  columns: {list(df.columns)}")
print(f"\n  dtypes:\n{df.dtypes}")
print(f"\n  first 10 rows:")
print(df.head(10).to_string())
print()

#meds is evenet stream to understad the strcuture 
# Standard MEDS columns: subject_id, time, code, numeric_value
if "subject_id" in df.columns:
    print(f"  unique patients IN THIS SHARD: {df['subject_id'].nunique()}")
    print(f"  events in this shard: {len(df)}")
if "code" in df.columns:
    print(f"\n  most common event codes (types of medical events):")
    print(df['code'].value_counts().head(20).to_string())
#any free notes ?

print("\n" + "="*50)
print("CHECKING FOR NOTES / TEXT DATA:")
text_cols = [c for c in df.columns if df[c].dtype == object]
print(f"  object/string columns: {text_cols}")
for c in text_cols:
    sample = df[c].dropna().astype(str)
    if len(sample) > 0:
        avg_len = sample.str.len().mean()
        maxlen = sample.str.len().max()
        print(f"    '{c}': avg length {avg_len:.0f} chars, max {maxlen}")
        if maxlen > 200:
            print(f"       ^^ LONG TEXT — possible clinical notes! sample:")
            longest = sample.loc[sample.str.len().idxmax()]
            print(f"       '{longest[:300]}...'")
# Also check if any code values mention notes/text
if "code" in df.columns:
    note_codes = df['code'].astype(str).str.contains("note|text|NOTE|TEXT|discharge|radiology",
                                                       case=False, na=False)
    print(f"\n  event codes mentioning note/text/discharge: {note_codes.sum()}")
    if note_codes.sum() > 0:
        print("   ", df.loc[note_codes, 'code'].unique()[:10])