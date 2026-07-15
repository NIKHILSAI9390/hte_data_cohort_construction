"""Finish the codebook: find MAP (mean arterial pressure) and SpO2 codes
that the first search missed due to MIMIC's label wording."""
import glob
import pandas as pd

d_item = pd.read_csv(glob.glob("data/**/d_items.csv", recursive=True)[0])

def show(term):
    hits = d_item[d_item["label"].str.contains(term, case=False, na=False)]
    print(f"\n=== '{term}' : {len(hits)} matches ===")
    for _, r in hits.head(12).iterrows():
        print(f"  MIMIC_IV_ITEM/{r['itemid']:>7}  ->  {r['label']}   "
              f"[{r.get('category','')}, {r.get('unitname','')}]")

show("blood pressure mean")
show("arterial pressure mean")
show("ABPm")
show("O2 saturation")
show("SpO2")
show("pulseoxymetry")