"""Check for immortal-time bias: do control patients die very early (before they
could have been treated), inflating control mortality and making treated look protective?"""
import pandas as pd, numpy as np
c=pd.read_parquet("results/master_cohort.parquet")
c["sepsis_onset"]=pd.to_datetime(c["sepsis_onset"])

# need time from onset to death. reload dod
import glob
pts=pd.read_csv(glob.glob("data/**/patients.csv",recursive=True)[0])
pts["dod"]=pd.to_datetime(pts["dod"])
dod=dict(zip(pts["subject_id"],pts["dod"]))
c["dod"]=c["subject_id"].map(dod)
c["hrs_onset_to_death"]=(c["dod"]-c["sepsis_onset"]).dt.total_seconds()/3600

died=c[c["mortality_28d"]==1]
t=died[died["treated"]]; ct=died[~died["treated"]]
print("Among patients who died within 28d — hours from onset to death:")
print(f"  treated: median {t['hrs_onset_to_death'].median():.0f}h, "
      f"within 24h of onset: {(t['hrs_onset_to_death']<24).mean():.1%}")
print(f"  control: median {ct['hrs_onset_to_death'].median():.0f}h, "
      f"within 24h of onset: {(ct['hrs_onset_to_death']<24).mean():.1%}")
print(f"\n  control deaths within 4h of onset (couldn't be 'treated in 4h'): "
      f"{(ct['hrs_onset_to_death']<4).sum()} ({(ct['hrs_onset_to_death']<4).mean():.1%} of control deaths)")
print(f"  treated deaths within 4h: {(t['hrs_onset_to_death']<4).sum()}")
print(f"\nIf control patients die much earlier than treated, that's immortal-time bias:")
print(f"  treated who die do so later because they SURVIVED to be treated.")