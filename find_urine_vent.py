"""Find urine-output itemids (summed for 24h total) and ventilation indicators."""
import glob
import pandas as pd

d_item = pd.read_csv(glob.glob("data/**/d_items.csv", recursive=True)[0])

def show(term):
    hits=d_item[d_item["label"].str.contains(term,case=False,na=False)]
    print(f"\n=== '{term}': {len(hits)} ===")
    for _,r in hits.head(15).iterrows():
        print(f"  {r['itemid']:>7}  {r['label']}   [{r.get('category','')}, {r.get('unitname','')}]")

print("###### URINE OUTPUT ######")
show("urine")
show("void")
show("foley")
show("nephrostomy")
print("\n###### VENTILATION ######")
show("ventilation")
show("tidal volume")
show("PEEP")
show("O2 Delivery")