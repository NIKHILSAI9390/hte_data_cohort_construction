"""Definitive check: scan ALL event codes in one shard for note/text data."""
import pandas as pd, glob, ast
from collections import Counter

shard = glob.glob("data/**/data_*.parquet", recursive=True)[0]
df = pd.read_parquet(shard)
print(f"patients in shard: {len(df)}")

# The 'events' column holds a list of event-dicts per patient.
# Collect the "table" each event came from, and the code prefixes.
tables = Counter()
code_prefixes = Counter()
sample_checked = 0

for events in df["events"].head(200):        # check 200 patients
    # events may be a list already, or a string repr
    if isinstance(events, str):
        try: events = ast.literal_eval(events)
        except: continue
    for e in events:
        props = e.get("properties", {}) or {}
        tbl = props.get("table")
        if tbl: tables[tbl] += 1
        code = str(e.get("code", ""))
        prefix = code.split("/")[0] if "/" in code else code
        code_prefixes[prefix] += 1
    sample_checked += 1

print(f"\nchecked {sample_checked} patients")
print("\nSOURCE TABLES present (this tells us what data types exist):")
for t, c in tables.most_common():
    print(f"  {t:35s} {c}")
print("\nCODE PREFIXES (event types):")
for p, c in code_prefixes.most_common(25):
    print(f"  {p:35s} {c}")

# Explicit note hunt
note_tables = [t for t in tables if any(k in t.lower() for k in ["note","text","discharge","radiology","report"])]
print(f"\nNOTE-related source tables found: {note_tables if note_tables else 'NONE'}")