MIMIC-IV Sepsis Cohort Reconstruction

Replication of the early-vasopressor → 28-day mortality sepsis cohort
(paper arXiv 2604.16763), built from raw MEDS event-stream data (no derived tables).

Full methods, codebook, and validation: see cohort_construction.md.


Pipeline — run order

The pipeline turns raw MEDS shards + reference CSVs into one analysis-ready
patient-level cohort, then estimates the treatment effect.

One-time setup


extract_antibiotics.py — scans the 2.46 GB prescriptions.csv once,
filters to antibiotics, saves data/antibiotics_filtered.parquet.
(MEDS codes drugs as bare NDC numbers, so antibiotics come from raw CSV.)


Build the cohort (per shard, orchestrated)


run_all.py — runs the full per-shard pipeline across all 100 shards,
resumable. For each shard it calls, in order:

sepsis_cohort.py — Sepsis-3 identification (SOFA + suspicion of infection)
treatment.py — first vasopressor within 4h of onset
outcome.py — 28-day mortality + ICU<6h exclusion
covariates_vitals_labs.py — first-day vitals/labs + demographics
charlson.py — Charlson comorbidity index (ICD)
sapsii.py — full SAPS-II severity score
assemble.py — merge + apply exclusion funnel → results/cohort_<shard>.parquet


Run: python run_all.py (or in batches: python run_all.py 0 25)


Consolidate + analyze


consolidate.py — merges 100 shard cohorts → results/master_cohort.parquet,
prints Table 3 (treated vs control means), missingness, crude ATE.
psm_baseline.py — MICE-style imputation → propensity model →
ATE via IPW, PS matching, and regression adjustment.


Supporting modules (imported, not run directly)


extract_sofa_values.py — MEDS event extraction + codebook (itemid → concept)
sofa.py — SOFA scoring (6 organs, GCS text-mapping, thresholds)
suspicion_of_infection.py — antibiotic–culture pairing logic


Diagnostics (ATE investigation)


diagnose_ate.py, diagnose_ate2.py — mortality by severity bin (SOFA / SAPS-II)
diagnose_immortal.py — immortal-time bias check
onset_sensitivity.py — ATE under alternative onset definitions



Current status

Cohort validates well against the paper on structure:

QuantityThis cohortPaperSepsis-3 patients18,31221,859Treated rate10.5%10.0%28-day mortality17.3%17.3%

Open issue: crude ATE ≈ −0.008 and PS-adjusted estimates disagree
(IPW +0.012, matching −0.059, regression −0.057) vs the paper's structured-only
PSM ATE ~+0.055. Suspected causes: poor propensity overlap (treated PS 0.29 vs
control 0.08), deferred missing-notes exclusion (pending PhysioNet notes access),
high imputation load (lactate/bilirubin ~50% missing). 
