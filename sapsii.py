"""sapsii.py — FULL SAPS-II (Le Gall 1993), first-24h ICU."""
import glob
import pandas as pd
import numpy as np
from sofa import gcs_points

SAPS_CODES = {
    "MIMIC_IV_LABITEM/50882":"bicarbonate", "MIMIC_IV_LABITEM/50983":"sodium",
    "MIMIC_IV_LABITEM/50971":"potassium", "MIMIC_IV_LABITEM/51006":"bun",
    "MIMIC_IV_ITEM/220050":"sbp_arterial", "MIMIC_IV_ITEM/220179":"sbp_noninvasive",
    "MIMIC_IV_ITEM/226559":"urine","MIMIC_IV_ITEM/226560":"urine",
    "MIMIC_IV_ITEM/226566":"urine","MIMIC_IV_ITEM/226627":"urine",
    "MIMIC_IV_ITEM/226631":"urine","MIMIC_IV_ITEM/227489":"urine",
    "MIMIC_IV_ITEM/226564":"urine","MIMIC_IV_ITEM/226565":"urine",
    "MIMIC_IV_ITEM/225792":"vent","MIMIC_IV_ITEM/220339":"vent",
    "MIMIC_IV_ITEM/224685":"vent",
}

def extract_saps_extra(shard_path):
    from extract_sofa_values import extract_shard
    ev = extract_shard(shard_path)
    df = pd.read_parquet(shard_path)
    idc = "subject_id" if "subject_id" in df.columns else "patient_id"
    rows=[]
    for _, r in df.iterrows():
        pid=r[idc]
        for e in r["events"]:
            code=e.get("code","")
            base="/".join(code.split("/")[:2])
            name=SAPS_CODES.get(code) or SAPS_CODES.get(base)
            if name:
                rows.append((pid,e.get("time"),name,e.get("numeric_value"),e.get("text_value")))
    extra=pd.DataFrame(rows,columns=["subject_id","time","variable","numeric_value","text_value"])
    return pd.concat([ev,extra],ignore_index=True)

def p_age(a):
    return 0 if a<40 else 7 if a<60 else 12 if a<70 else 15 if a<75 else 16 if a<80 else 18
def p_hr(x):
    if pd.isna(x):return None
    return 11 if x<40 else 2 if x<70 else 0 if x<120 else 4 if x<160 else 7
def p_sbp(x):
    if pd.isna(x):return None
    return 13 if x<70 else 5 if x<100 else 0 if x<200 else 2
def p_temp(x): return None if pd.isna(x) else (0 if x<39 else 3)
def p_gcs(x):
    if pd.isna(x):return None
    return 26 if x<6 else 13 if x<9 else 7 if x<11 else 5 if x<14 else 0
def p_bun(x):
    if pd.isna(x):return None
    return 0 if x<28 else 6 if x<84 else 10
def p_wbc(x):
    if pd.isna(x):return None
    return 12 if x<1 else 0 if x<20 else 3
def p_k(x):
    if pd.isna(x):return None
    return 3 if x<3 else 0 if x<5 else 3
def p_na(x):
    if pd.isna(x):return None
    return 5 if x<125 else 0 if x<145 else 1
def p_hco3(x):
    if pd.isna(x):return None
    return 6 if x<15 else 3 if x<20 else 0
def p_bili(x):
    if pd.isna(x):return None
    return 0 if x<4 else 4 if x<6 else 9
def p_pf(ratio,vent):
    if not vent: return 0
    if pd.isna(ratio): return 0
    return 11 if ratio<100 else 9 if ratio<200 else 6
def p_urine(ml):
    if pd.isna(ml): return None
    return 11 if ml<500 else 4 if ml<1000 else 0

def compute_sapsii(shard_path, cohort, icu, diag, adm):
    ev=extract_saps_extra(shard_path)
    ev["val"]=ev["numeric_value"]
    gm=ev["variable"].isin(["gcs_eye","gcs_verbal","gcs_motor"])
    ev.loc[gm,"val"]=[gcs_points(v,t) for v,t in zip(ev.loc[gm,"variable"],ev.loc[gm,"text_value"])]
    ev_vent=ev[ev["variable"]=="vent"].copy()
    ev=ev.dropna(subset=["val"]); ev["time"]=pd.to_datetime(ev["time"])
    ev_vent["time"]=pd.to_datetime(ev_vent["time"])

    intime_by=dict(zip(icu["subject_id"],pd.to_datetime(icu["intime"])))
    sids=list(cohort["subject_id"].unique())
    def in24(d):
        d=d[d["subject_id"].isin(sids)].copy()
        d["intime"]=d["subject_id"].map(intime_by)
        return d[(d["time"]>=d["intime"])&(d["time"]<=d["intime"]+pd.Timedelta(hours=24))]
    ev=in24(ev); ev_vent=in24(ev_vent)

    RANGES={"heart_rate":(20,250),"sbp_arterial":(20,300),"sbp_noninvasive":(20,300),
            "temp_c":(25,45),"temp_f":(77,113),"bun":(0,300),"wbc":(0,200),
            "potassium":(1,15),"sodium":(80,200),"bicarbonate":(0,60),
            "bilirubin_total":(0,80),"pao2":(0,700),"fio2":(0,100),"urine":(0,5000)}
    keep=pd.Series(True,index=ev.index)
    for var,(lo,hi) in RANGES.items():
        m=ev["variable"]==var
        keep &= ~(m&((ev["val"]<lo)|(ev["val"]>hi)))
    ev=ev[keep]

    vent_pts=set(ev_vent["subject_id"].unique())
    urine_sum=ev[ev["variable"]=="urine"].groupby("subject_id")["val"].sum()

    d=diag[diag["subject_id"].isin(sids)].copy()
    d["c"]=d["icd_code"].astype(str).str.replace(".","",regex=False).str.upper()
    def has(sid,i9,i10):
        cc=d[d["subject_id"]==sid]
        return any(any(x.startswith(p) for p in (i9 if v==9 else i10))
                   for x,v in zip(cc["c"],cc["icd_version"]))
    adm_type=dict(zip(adm["subject_id"],adm["admission_type"]))

    ages=dict(zip(cohort["subject_id"],cohort["age"]))
    scores={}
    for sid in sids:
        def w(var,how):
            s=ev[(ev["subject_id"]==sid)&(ev["variable"]==var)]["val"]
            return (np.nan if len(s)==0 else (s.min() if how=="min" else s.max()))
        hr=w("heart_rate","max"); sbp=w("sbp_arterial","min")
        if pd.isna(sbp): sbp=w("sbp_noninvasive","min")
        temp=w("temp_c","max")
        if pd.isna(temp):
            tf=w("temp_f","max"); temp=(tf-32)*5/9 if pd.notna(tf) else np.nan
        gc=[w(g,"min") for g in ["gcs_eye","gcs_verbal","gcs_motor"]]
        gtot=sum(gc) if all(pd.notna(x) for x in gc) else np.nan
        vent=sid in vent_pts
        pao2=w("pao2","min"); fio2=w("fio2","max")
        fio2n=(fio2*100 if pd.notna(fio2) and fio2<=1 else fio2)
        pf=(pao2/(fio2n/100.0)) if (pd.notna(pao2) and pd.notna(fio2n) and fio2n>0) else np.nan
        urine=urine_sum.get(sid,np.nan)
        cd=0
        if has(sid,["042","043","044"],["B20","B21","B22","B24"]): cd=17
        elif has(sid,["200","201","202","203","204","205","206","207","208"],
                     ["C81","C82","C83","C84","C85","C88","C90","C91","C92","C93","C94","C95","C96"]): cd=10
        elif has(sid,["196","197","198","199"],["C77","C78","C79","C80"]): cd=9
        at=str(adm_type.get(sid,"")).upper()
        if "ELECTIVE" in at or "SURG" in at: adm_pts=0
        elif "URGENT" in at or "EMER" in at: adm_pts=8
        else: adm_pts=6
        pts=[p_age(ages.get(sid,60)),p_hr(hr),p_sbp(sbp),p_temp(temp),p_gcs(gtot),
             p_bun(w("bun","max")),p_wbc(w("wbc","max")),p_k(w("potassium","max")),
             p_na(w("sodium","max")),p_hco3(w("bicarbonate","min")),
             p_bili(w("bilirubin_total","max")),p_pf(pf,vent),p_urine(urine)]
        total=np.nansum([p for p in pts if p is not None])+cd+adm_pts
        scores[sid]=total
    return pd.Series(scores,name="sapsii")

if __name__=="__main__":
    from extract_sofa_values import find_shards
    shard=find_shards()[0]
    cohort=pd.read_parquet("results/covariates_data_0.parquet")
    icu=pd.read_csv(glob.glob("data/**/icustays.csv",recursive=True)[0])
    diag=pd.read_csv(glob.glob("data/**/diagnoses_icd.csv",recursive=True)[0])
    adm=pd.read_csv(glob.glob("data/**/admissions.csv",recursive=True)[0])
    saps=compute_sapsii(shard,cohort,icu,diag,adm)
    saps.to_frame().to_parquet("results/sapsii_data_0.parquet")
    print(f"FULL SAPS-II for {len(saps)} patients")
    print(saps.describe().to_string())
    print(f"  coverage(>0): {(saps>0).mean():.1%}")