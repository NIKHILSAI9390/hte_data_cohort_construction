"""Extract the SOFA/treatment/covariate itemid VALUES from MEDS events into a
clean per-patient long table. Verifies WHERE the numeric value lives."""
import glob
import pandas as pd
import numpy as np

CODEBOOK = {
    "MIMIC_IV_LABITEM/50912": "creatinine",
    "MIMIC_IV_LABITEM/50885": "bilirubin_total",
    "MIMIC_IV_LABITEM/51265": "platelets",
    "MIMIC_IV_LABITEM/51301": "wbc",
    "MIMIC_IV_LABITEM/50813": "lactate",
    "MIMIC_IV_LABITEM/50821": "pao2",
    "MIMIC_IV_ITEM/220045": "heart_rate",
    "MIMIC_IV_ITEM/220210": "resp_rate",
    "MIMIC_IV_ITEM/223762": "temp_c",
    "MIMIC_IV_ITEM/223761": "temp_f",
    "MIMIC_IV_ITEM/220277": "spo2",
    "MIMIC_IV_ITEM/220052": "map_arterial",
    "MIMIC_IV_ITEM/220181": "map_noninvasive",
    "MIMIC_IV_ITEM/223835": "fio2",
    "MIMIC_IV_ITEM/220739": "gcs_eye",
    "MIMIC_IV_ITEM/223900": "gcs_verbal",
    "MIMIC_IV_ITEM/223901": "gcs_motor",
    "MIMIC_IV_ITEM/226559": "urine_foley",
    "MIMIC_IV_ITEM/221906": "norepinephrine",
    "MIMIC_IV_ITEM/221289": "epinephrine",
    "MIMIC_IV_ITEM/221662": "dopamine",
    "MIMIC_IV_ITEM/222315": "vasopressin",
    "MIMIC_IV_ITEM/221749": "phenylephrine",
}
WANTED = set(CODEBOOK.keys())

def find_shards():
    return sorted(glob.glob("data/**/MEDS/data/data_*.parquet", recursive=True))

def extract_shard(path):
    df = pd.read_parquet(path)
    id_col = "subject_id" if "subject_id" in df.columns else "patient_id"
    rows = []
    for _, r in df.iterrows():
        pid = r[id_col]
        for e in r["events"]:
            code = e.get("code", "")
             
            name = None
            if code in CODEBOOK:                    # exact match (labs, vitals)
                name = CODEBOOK[code]
            else:                                   # prefix match (vasopressors: ".../Continuous Med")
                base = "/".join(code.split("/")[:2])  # e.g. "MIMIC_IV_ITEM/221749"
                if base in CODEBOOK:
                    name = CODEBOOK[base]
            if name is not None:
                rows.append((pid, e.get("time"), name,
                             e.get("numeric_value"), e.get("text_value"), None))
    return pd.DataFrame(rows, columns=["subject_id","time","variable",
                                       "numeric_value","text_value","prop_value"])

if __name__ == "__main__":
    shard = find_shards()[0]
    print(f"Extracting from one shard: {shard}\n")
    out = extract_shard(shard)
    print(f"  extracted rows: {len(out)}")
    print(f"  patients: {out['subject_id'].nunique()}")
    print(f"\n  rows per variable:")
    print(out['variable'].value_counts().to_string())

    print(f"\n  VALUE LOCATION CHECK:")
    print(f"    numeric_value non-null: {out['numeric_value'].notna().sum()} / {len(out)}")
    print(f"    text_value non-null:    {out['text_value'].notna().sum()} / {len(out)}")
    print(f"    prop_value non-null:    {out['prop_value'].notna().sum()} / {len(out)}")

    print(f"\n  sample creatinine rows:")
    print(out[out['variable']=='creatinine'].head(8).to_string())
    print(f"\n  sample norepinephrine rows (treatment):")
    print(out[out['variable']=='norepinephrine'].head(5).to_string())