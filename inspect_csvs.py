"""Peek at the column structure of the raw CSV files (just headers + 3 rows each)
to see which hold named antibiotics, diagnoses, procedures — without loading full files."""
import glob
import pandas as pd

FILES = ["prescriptions.csv", "diagnoses_icd.csv", "procedures_icd.csv",
         "procedureevents.csv", "drgcodes.csv", "d_icd_diagnoses.csv",
         "admissions.csv", "patients.csv"]

for fname in FILES:
    hits = glob.glob(f"data/**/{fname}", recursive=True)
    if not hits:
        print(f"\n### {fname}: NOT downloaded / not found")
        continue
    try:
        df = pd.read_csv(hits[0], nrows=3)
        print(f"\n### {fname}")
        print(f"  columns: {list(df.columns)}")
        # show the first row transposed so long text is readable
        print(f"  first row sample:")
        for col in df.columns:
            val = str(df.iloc[0][col])
            print(f"    {col}: {val[:60]}")
    except Exception as e:
        print(f"\n### {fname}: error reading ({e})")