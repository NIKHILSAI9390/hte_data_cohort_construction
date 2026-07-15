"""Find itemids for SAPS-II variables not yet in our codebook."""
import glob
import pandas as pd

d_lab = pd.read_csv(glob.glob("data/**/d_labitems.csv", recursive=True)[0])
d_item = pd.read_csv(glob.glob("data/**/d_items.csv", recursive=True)[0])

def show(df, term, prefix):
    hits = df[df["label"].str.contains(term, case=False, na=False)]
    print(f"\n=== '{term}' in {prefix}: {len(hits)} ===")
    for _, r in hits.head(8).iterrows():
        extra = r.get("fluid","") if "fluid" in df.columns else r.get("category","")
        print(f"  {prefix}/{r['itemid']:>7}  {r['label']}   [{extra}]")

print("###### SAPS-II labs needed ######")
show(d_lab, "bicarbonate", "MIMIC_IV_LABITEM")
show(d_lab, "sodium", "MIMIC_IV_LABITEM")
show(d_lab, "potassium", "MIMIC_IV_LABITEM")
show(d_lab, "urea nitrogen", "MIMIC_IV_LABITEM")