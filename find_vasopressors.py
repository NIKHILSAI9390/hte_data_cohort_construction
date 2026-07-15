"""Find how vasopressors are ACTUALLY coded in the MEDS events.
The MIMIC_IV_ITEM/221906 code returned nothing, so infusions are coded
differently. Search all codes for anything vasopressor-related."""
import glob
import pandas as pd
from collections import Counter

shard = sorted(glob.glob("data/**/MEDS/data/data_*.parquet", recursive=True))[0]
df = pd.read_parquet(shard)
id_col = "subject_id" if "subject_id" in df.columns else "patient_id"

# Collect ALL codes containing any vasopressor itemid number, OR the drug name
VP_ITEMIDS = ["221906","221289","221662","222315","221749","221653"]
VP_NAMES = ["norepi","epinephr","dopamine","vasopressin","phenylephr","levophed","dobutamine"]

code_counter = Counter()
sample_events = []
for _, r in df.head(500).iterrows():   # 500 patients is enough to find the pattern
    for e in r["events"]:
        code = str(e.get("code",""))
        low = code.lower()
        if any(iid in code for iid in VP_ITEMIDS) or any(n in low for n in VP_NAMES):
            code_counter[code] += 1
            if len(sample_events) < 10:
                sample_events.append(e)

print("Codes matching vasopressor itemids or names:")
if code_counter:
    for code, cnt in code_counter.most_common(30):
        print(f"  {cnt:6d}  {code}")
else:
    print("  NONE found by itemid or name.")

print("\nSample full events (to see the structure):")
for e in sample_events[:5]:
    print(" ", {k: e.get(k) for k in ['code','time','numeric_value','text_value']})

# Also: what code PREFIXES exist that we haven't seen? Look for input/infusion
print("\nAll code prefixes containing 'input','ingredient','infus','med','drug':")
prefixes = Counter()
for _, r in df.head(500).iterrows():
    for e in r["events"]:
        code = str(e.get("code",""))
        low = code.lower()
        if any(k in low for k in ["input","ingredient","infus"]):
            prefixes[code.split("/")[0] if "/" in code else code] += 1
for p, c in prefixes.most_common(20):
    print(f"  {c:6d}  {p}")