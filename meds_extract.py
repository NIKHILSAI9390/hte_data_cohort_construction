import glob
import pandas as pd
import numpy as np
# from pathlib  import path 
def find_shards():
    return sorted(glob.glob("data/**/MEDS/data/data_*.parquet",recursive=True))

def flatten_shard(path ,code_prefixes=None):
    # read one med  parquet shard and flatten
    df=pd.read_parquet(path)
    id_col="subject_id" if "subject_id " in df.columns else "patient_id"
    rows=[]
    for _, r in df.iterrows():
        pid = r[id_col]
        events = r["events"]              # numpy array of dicts
        for e in events:
            code = e.get("code", "")
            if code_prefixes and not any(code.startswith(p) for p in code_prefixes):
                continue
            rows.append((pid, e.get("time"), code,
                         e.get("numeric_value"), e.get("text_value")))
    return pd.DataFrame(rows, columns=["subject_id","time","code","numeric_value","text_value"])
if __name__ == "__main__":
    shards = find_shards()
    print(f"Found {len(shards)} MEDS shards")
    if not shards:
        print("No shards found under data/**/MEDS/data/ — check path.")
        raise SystemExit

    test = shards[0]
    print(f"\nFlattening one shard (all events): {test}")
    flat = flatten_shard(test)
    print(f"  flattened rows (events): {len(flat)}")
    print(f"  unique patients: {flat['subject_id'].nunique()}")
    print(f"\n  sample rows:")
    print(flat.head(10).to_string())

    prefixes = flat["code"].str.split("/").str[0].value_counts()
    print(f"\n  code prefixes present (top 20):")
    print(prefixes.head(20).to_string())    