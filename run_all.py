"""run_all.py — orchestrate the full cohort pipeline across all 100 shards."""
import glob, os, sys, time
import pandas as pd
import numpy as np

from extract_sofa_values import find_shards
from sepsis_cohort import process_shard as run_sepsis
from covariates_vitals_labs import build_covariates
from charlson import charlson_for_patients
from sapsii import compute_sapsii
from assemble import assemble_shard, apply_funnel

def tag_of(shard_path):
    return os.path.basename(shard_path).replace(".parquet","")

def run_treatment(shard_path, tag):
    from treatment import get_vaso_events
    sepsis=pd.read_parquet(f"results/sepsis_{tag}.parquet")
    sepsis["sepsis_onset"]=pd.to_datetime(sepsis["sepsis_onset"])
    vaso_by=get_vaso_events(shard_path)
    rows=[]
    for _,r in sepsis.iterrows():
        sid=r["subject_id"]; onset=r["sepsis_onset"]; vt=vaso_by.get(sid,[])
        fv=min(vt) if len(vt) else None
        pre=any(t<onset for t in vt) if vt else False
        treated=any(onset<=t<=onset+pd.Timedelta(hours=4) for t in vt) if vt else False
        rows.append({"subject_id":sid,"sepsis_onset":onset,"first_vaso":fv,
                     "any_vaso":len(vt)>0,"pre_onset_vaso":pre,"treated":treated})
    pd.DataFrame(rows).to_parquet(f"results/treatment_{tag}.parquet",index=False)

def run_outcome(tag, dod_by, los_by):
    sepsis=pd.read_parquet(f"results/sepsis_{tag}.parquet")
    sepsis["sepsis_onset"]=pd.to_datetime(sepsis["sepsis_onset"])
    treat=pd.read_parquet(f"results/treatment_{tag}.parquet")
    df=sepsis.merge(treat[["subject_id","treated","pre_onset_vaso"]],on="subject_id",how="left")
    rows=[]
    for _,r in df.iterrows():
        sid=r["subject_id"]; onset=r["sepsis_onset"]; stay=r["stay_id"]
        dod=dod_by.get(sid); mort=0
        if pd.notna(dod):
            days=(dod-onset).days
            mort=1 if 0<=days<=28 else (np.nan if days<0 else 0)
        los=los_by.get(stay,np.nan)
        rows.append({"subject_id":sid,"treated":r["treated"],"pre_onset_vaso":r["pre_onset_vaso"],
                     "mortality_28d":mort,"los_days":los,
                     "icu_short":(los<0.25) if pd.notna(los) else False})
    pd.DataFrame(rows).to_parquet(f"results/outcome_{tag}.parquet",index=False)

def run_covariates(shard_path, tag, pts):
    sepsis=pd.read_parquet(f"results/sepsis_{tag}.parquet")
    cov=build_covariates(shard_path,sepsis)
    cov=cov.merge(pts[["subject_id","gender","anchor_age"]],on="subject_id",how="left")
    cov=cov.rename(columns={"anchor_age":"age"}); cov["male"]=(cov["gender"]=="M").astype(int)
    cov.drop(columns=["gender"]).to_parquet(f"results/covariates_{tag}.parquet",index=False)

def run_charlson(tag, diag):
    sepsis=pd.read_parquet(f"results/sepsis_{tag}.parquet")
    ch=charlson_for_patients(diag, list(sepsis["subject_id"].unique()))
    ch.to_frame().to_parquet(f"results/charlson_{tag}.parquet")

def run_sapsii(shard_path, tag, icu, diag, adm):
    cov=pd.read_parquet(f"results/covariates_{tag}.parquet")
    saps=compute_sapsii(shard_path,cov,icu,diag,adm)
    saps.to_frame().to_parquet(f"results/sapsii_{tag}.parquet")

if __name__=="__main__":
    shards=find_shards()
    start=int(sys.argv[1]) if len(sys.argv)>1 else 0
    end=int(sys.argv[2]) if len(sys.argv)>2 else len(shards)

    print("Loading shared reference tables once...")
    icu=pd.read_csv(glob.glob("data/**/icustays.csv",recursive=True)[0])
    pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
    pts["dod"]=pd.to_datetime(pts["dod"])
    adm=pd.read_csv(glob.glob("data/**/admissions.csv",recursive=True)[0])
    diag=pd.read_csv(glob.glob("data/**/diagnoses_icd.csv",recursive=True)[0])
    abx=pd.read_parquet("data/antibiotics_filtered.parquet"); abx["starttime"]=pd.to_datetime(abx["starttime"])
    abx_by=abx.groupby("subject_id")["starttime"].apply(lambda s:sorted(s.tolist()))
    age_by=dict(zip(pts["subject_id"],pts["anchor_age"]))
    dod_by=dict(zip(pts["subject_id"],pts["dod"]))
    los_by=dict(zip(icu["stay_id"],icu["los"]))

    for i in range(start,end):
        sp=shards[i]; tag=tag_of(sp)
        if os.path.exists(f"results/cohort_{tag}.parquet"):
            print(f"[{i}] {tag}: done, skip"); continue
        t0=time.time()
        try:
            if not os.path.exists(f"results/sepsis_{tag}.parquet"):
                run_sepsis(sp, icu, abx_by, age_by)
            run_treatment(sp, tag)
            run_outcome(tag, dod_by, los_by)
            run_covariates(sp, tag, pts)
            run_charlson(tag, diag)
            run_sapsii(sp, tag, icu, diag, adm)
            df=assemble_shard(tag)
            final=apply_funnel(df) if df is not None else None
            if final is not None:
                final.to_parquet(f"results/cohort_{tag}.parquet",index=False)
            print(f"[{i}] {tag}: {len(final) if final is not None else 0} patients ({time.time()-t0:.0f}s)")
        except Exception as e:
            print(f"[{i}] {tag}: ERROR {e}")

    cohorts=glob.glob("results/cohort_*.parquet")
    if cohorts:
        allc=pd.concat([pd.read_parquet(f) for f in cohorts],ignore_index=True)
        print(f"\n=== CUMULATIVE: {len(cohorts)} shards, {len(allc)} patients ===")
        print(f"  treated: {allc['treated'].mean():.1%}, mortality: {allc['mortality_28d'].mean():.1%}")