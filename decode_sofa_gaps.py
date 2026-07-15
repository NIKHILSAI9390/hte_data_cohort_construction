"""Close the remaining SOFA codebook gaps:
 - Respiration: PaO2 (blood gas), FiO2
 - CNS: Glasgow Coma Scale (GCS)
 - Cardiovascular: vasopressors (also = the TREATMENT)
 - Renal: urine output"""
import glob
import pandas as pd

d_item = pd.read_csv(glob.glob("data/**/d_items.csv", recursive=True)[0])
d_lab  = pd.read_csv(glob.glob("data/**/d_labitems.csv", recursive=True)[0])

def show(df, term, prefix, extra_cols=("category","unitname")):
    hits = df[df["label"].str.contains(term, case=False, na=False)]
    print(f"\n=== '{term}' in {prefix}: {len(hits)} matches ===")
    for _, r in hits.head(12).iterrows():
        extras = "  ".join(str(r.get(c,"")) for c in extra_cols if c in df.columns)
        print(f"  {prefix}/{r['itemid']:>7}  ->  {r['label']}   [{extras}]")

print("########## RESPIRATION (PaO2/FiO2 + ventilation) ##########")
show(d_lab,  "po2", "MIMIC_IV_LABITEM")
show(d_item, "FiO2", "MIMIC_IV_ITEM")
show(d_item, "inspired o2", "MIMIC_IV_ITEM")
show(d_item, "ventilator", "MIMIC_IV_ITEM")

print("\n########## CNS (Glasgow Coma Scale) ##########")
show(d_item, "GCS", "MIMIC_IV_ITEM")
show(d_item, "Glasgow", "MIMIC_IV_ITEM")

print("\n########## RENAL (urine output) ##########")
show(d_item, "urine out", "MIMIC_IV_ITEM")
show(d_item, "foley", "MIMIC_IV_ITEM")

print("\n########## CARDIOVASCULAR = VASOPRESSORS (also the TREATMENT) ##########")
for vp in ["norepinephrine","epinephrine","dopamine","dobutamine",
           "vasopressin","phenylephrine"]:
    show(d_item, vp, "MIMIC_IV_ITEM")