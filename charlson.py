"""charlson.py — Charlson Comorbidity Index from diagnoses_icd.csv."""
import glob
import pandas as pd
import numpy as np

CHARLSON = {
    "mi":            (1, ["410","412"], ["I21","I22","I252"]),
    "chf":           (1, ["428"], ["I50","I110","I130","I132","I255","I420","I425","I426","I427","I428","I429","P290"]),
    "pvd":           (1, ["440","441","443","4471","5571","5579","V434"], ["I70","I71","I731","I738","I739","I771","I790","I792","K551","K558","K559","Z958","Z959"]),
    "cvd":           (1, ["430","431","432","433","434","435","436","437","438"], ["G45","G46","I60","I61","I62","I63","I64","I65","I66","I67","I68","I69","H340"]),
    "dementia":      (1, ["290"], ["F00","F01","F02","F03","F051","G30","G311"]),
    "copd":          (1, ["490","491","492","493","494","495","496","500","501","502","503","504","505"], ["J40","J41","J42","J43","J44","J45","J46","J47","J60","J61","J62","J63","J64","J65","J66","J67"]),
    "rheumatic":     (1, ["7100","7101","7104","7140","7141","7142","7148","725"], ["M05","M06","M32","M33","M34","M315"]),
    "peptic_ulcer":  (1, ["531","532","533","534"], ["K25","K26","K27","K28"]),
    "mild_liver":    (1, ["5712","5714","5715","5716","5733"], ["B18","K700","K701","K702","K703","K709","K713","K717","K73","K74","K760"]),
    "diabetes":      (1, ["2500","2501","2502","2503","2508","2509"], ["E100","E101","E106","E108","E109","E110","E111","E116","E118","E119","E120","E130","E140"]),
    "diabetes_comp": (2, ["2504","2505","2506","2507"], ["E102","E103","E104","E105","E107","E112","E113","E114","E115","E132","E133","E134","E135","E142","E143","E144","E145"]),
    "paraplegia":    (2, ["3341","342","343","344"], ["G041","G114","G80","G81","G82","G83"]),
    "renal":         (2, ["582","583","585","586","588","5830","5831"], ["I120","I131","N032","N052","N18","N19","N250","Z490","Z491","Z492","Z940","Z992"]),
    "cancer":        (2, ["140","141","142","143","144","145","146","147","148","149","150","151","152","153","154","155","156","157","158","159","160","161","162","163","164","165","170","171","172","174","175","176","179","180","181","182","183","184","185","186","187","188","189","190","191","192","193","194","195","200","201","202","203","204","205","206","207","208"], ["C0","C1","C2","C3","C43","C45","C46","C47","C48","C49","C5","C6","C7","C81","C82","C83","C84","C85","C88","C9"]),
    "mod_severe_liver":(3, ["4560","4561","4562","5722","5723","5724","5728"], ["I850","I859","I864","I982","K704","K711","K721","K729","K765","K766","K767"]),
    "metastatic":    (6, ["196","197","198","199"], ["C77","C78","C79","C80"]),
    "hiv":           (6, ["042","043","044"], ["B20","B21","B22","B24"]),
}

def clean_icd(code):
    return str(code).replace(".","").strip().upper()

def charlson_for_patients(diag, subject_ids):
    d = diag[diag["subject_id"].isin(subject_ids)].copy()
    d["code"] = d["icd_code"].apply(clean_icd)
    scores = {sid:0 for sid in subject_ids}
    flags = {sid:set() for sid in subject_ids}
    for _, r in d.iterrows():
        sid=r["subject_id"]; code=r["code"]; ver=r["icd_version"]
        for cat,(w,i9,i10) in CHARLSON.items():
            prefixes = i9 if ver==9 else i10
            if any(code.startswith(p) for p in prefixes):
                if cat not in flags[sid]:
                    flags[sid].add(cat); scores[sid]+=w
    return pd.Series(scores, name="charlson")

if __name__ == "__main__":
    diag = pd.read_csv(glob.glob("data/**/diagnoses_icd.csv", recursive=True)[0])
    print(f"diagnoses rows: {len(diag):,}, columns: {list(diag.columns)}")

    sepsis = pd.read_parquet("results/sepsis_data_0.parquet")
    sids = list(sepsis["subject_id"].unique())

    ch = charlson_for_patients(diag, sids)
    ch.to_frame().to_parquet("results/charlson_data_0.parquet")

    print(f"\nCharlson computed for {len(ch)} patients")
    print(f"  coverage (has >=1 diagnosis): {(ch>0).mean():.1%}")
    print(f"  distribution:")
    print(ch.describe().to_string())
    print(f"\n  histogram:")
    print(ch.value_counts().sort_index().head(20).to_string())