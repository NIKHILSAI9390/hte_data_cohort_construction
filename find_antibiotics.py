"""Find how antibiotics are coded — they didn't show by name search.
Look at ALL drug codes (NDC + MIMIC_IV_Drug) and their text_values."""
import glob
import pandas as pd
from collections import Counter

shard = sorted(glob.glob("data/**/MEDS/data/data_*.parquet", recursive=True))[0]
df = pd.read_parquet(shard)

drug_prefixes = Counter()
drug_samples = []
mimic_drug_names = Counter()

for _, r in df.head(800).iterrows():
    for e in r["events"]:
        code = str(e.get("code",""))
        if code.startswith("NDC") or code.startswith("MIMIC_IV_Drug"):
            drug_prefixes[code.split("/")[0]] += 1
            if code.startswith("MIMIC_IV_Drug"):
                # the drug name is after the slash
                mimic_drug_names[code] += 1
            if len(drug_samples) < 15:
                drug_samples.append({k: e.get(k) for k in
                                    ['code','time','numeric_value','text_value']})

print("Drug code prefixes:")
for c, n in drug_prefixes.most_common():
    print(f"  {n:6d}  {c}")

print("\nSample drug events (to see where the drug NAME lives):")
for s in drug_samples:
    print(" ", s)

print(f"\nMost common MIMIC_IV_Drug codes (these have names):")
for c, n in mimic_drug_names.most_common(40):
    print(f"  {n:5d}  {c}")