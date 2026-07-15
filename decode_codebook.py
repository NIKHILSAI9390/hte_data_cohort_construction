"""Decode raw MEDS codes -> human-readable names using MIMIC dictionaries.
Maps the specific codes needed for the paper's cohort: SOFA components,
covariates, vasopressors. Download d_labitems.csv and d_items.csv first."""
import glob
import pandas as pd

# --- Load the MIMIC dictionaries ---
d_lab = pd.read_csv(glob.glob("data/**/d_labitems.csv", recursive=True)[0])
d_item = pd.read_csv(glob.glob("data/**/d_items.csv", recursive=True)[0])
print(f"d_labitems: {len(d_lab)} lab definitions, columns: {list(d_lab.columns)}")
print(f"d_items: {len(d_item)} item definitions, columns: {list(d_item.columns)}\n")

# --- The labs/vitals the PAPER needs (SOFA components + covariates) ---
# We search the dictionaries by name to find the itemid/labitem codes.
LAB_TARGETS = ["creatinine", "bilirubin", "platelet", "white blood",
               "lactate", "wbc"]
VITAL_TARGETS = ["heart rate", "arterial pressure", "respiratory rate",
                 "temperature", "spo2", "oxygen saturation"]

def search(dictdf, name_col, targets, code_prefix):
    print(f"\n=== Searching for: {targets} ===")
    for t in targets:
        hits = dictdf[dictdf[name_col].str.contains(t, case=False, na=False)]
        print(f"\n  '{t}': {len(hits)} matches")
        for _, row in hits.head(6).iterrows():
            # find the id column (itemid or similar)
            idcol = [c for c in dictdf.columns if "id" in c.lower()][0]
            label = row[name_col]
            print(f"    {code_prefix}/{row[idcol]}  ->  {label}")

# labs use 'label' column typically
lab_name_col = "label" if "label" in d_lab.columns else d_lab.columns[1]
item_name_col = "label" if "label" in d_item.columns else d_item.columns[1]

search(d_lab, lab_name_col, LAB_TARGETS, "MIMIC_IV_LABITEM")
search(d_item, item_name_col, VITAL_TARGETS, "MIMIC_IV_ITEM")

print("\n\nNEXT: we'll match these codes back against the flattened events "
      "to confirm they actually appear in the data.")

