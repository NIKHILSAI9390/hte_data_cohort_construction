"""Find antibiotic and culture/microbiology codes for Sepsis-3 suspected-infection.
Antibiotics: in prescriptions (NDC/Drug) or inputevents.
Cultures: MIMIC_IV_MicrobiologyTest prefix (seen in first inspection)."""
import glob
import pandas as pd
from collections import Counter

shard = sorted(glob.glob("data/**/MEDS/data/data_*.parquet", recursive=True))[0]
df = pd.read_parquet(shard)

# 1. Find microbiology/culture codes
micro_codes = Counter()
abx_codes = Counter()
ABX_NAMES = ["vancomycin","piperacillin","cefepime","ceftriaxone","meropenem",
             "metronidazole","levofloxacin","ciprofloxacin","azithromycin",
             "ampicillin","gentamicin","zosyn","tazobactam","linezolid",
             "aztreonam","cefazolin","clindamycin","doxycycline","penicillin"]

for _, r in df.head(800).iterrows():
    for e in r["events"]:
        code = str(e.get("code",""))
        low = code.lower()
        if "microbiolog" in low or "culture" in low:
            micro_codes[code.split("/")[0]] += 1
        if any(a in low for a in ABX_NAMES):
            abx_codes[code] += 1

print("=== MICROBIOLOGY / CULTURE code prefixes ===")
for c, n in micro_codes.most_common(10):
    print(f"  {n:6d}  {c}")

print("\n=== ANTIBIOTIC codes (by drug name) ===")
for c, n in abx_codes.most_common(30):
    print(f"  {n:6d}  {c}")

# Also show a sample microbiology event's full structure
print("\n=== Sample microbiology event structure ===")
for _, r in df.head(200).iterrows():
    for e in r["events"]:
        if "microbiolog" in str(e.get("code","")).lower():
            print(" ", {k: e.get(k) for k in ['code','time','numeric_value','text_value']})
            break
    else:
        continue
    break