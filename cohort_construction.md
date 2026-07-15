# MIMIC-IV Sepsis Cohort Construction — Methods & Validation

Replication of the early-vasopressor → 28-day mortality sepsis cohort
(paper arXiv 2604.16763) built **from raw MEDS event-stream data** (no derived tables).

---

## 1. Data sources

| Source | Used for |
|---|---|
| MEDS parquet shards (100, ~2.6 GB) | labs, vitals, vasopressors, cultures, GCS |
| `prescriptions.csv` (2.46 GB) | antibiotics (MEDS codes drugs as bare NDC, unusable) |
| `patients.csv` | age, sex, date of death |
| `admissions.csv` | admission type, death timing |
| `icustays.csv` | ICU intime/outtime, length of stay |
| `diagnoses_icd.csv` | Charlson comorbidities, SAPS-II chronic disease |
| `d_labitems.csv`, `d_items.csv` | code → concept dictionaries |

MEDS event structure: one row per patient, `events` = array of dicts
(`code`, `time`, `numeric_value`, `text_value`).

### Key MEDS coding quirks discovered
- **Vasopressors** coded `MIMIC_IV_ITEM/<id>/Continuous Med` (suffix) — needs prefix match.
- **GCS** stored as **text** in `text_value` ("Spontaneously", "Oriented"…), not numeric — mapped to points.
- **Antibiotics** in MEDS are bare NDC numbers (no names) — pulled from raw `prescriptions.csv` instead.
- **Sentinel/outlier values** (e.g. MAP = 3,333,330) — physiological range filters applied.

---

## 2. Codebook (confirmed itemids)

**Labs** (`MIMIC_IV_LABITEM/`): creatinine 50912, bilirubin_total 50885,
platelets 51265, wbc 51301, lactate 50813, pao2 50821, bicarbonate 50882,
sodium 50983, potassium 50971, BUN 51006.

**Vitals** (`MIMIC_IV_ITEM/`): heart_rate 220045, resp_rate 220210,
temp_C 223762 / temp_F 223761, spo2 220277, MAP arterial 220052 / noninvasive 220181,
fio2 223835, sbp arterial 220050 / noninvasive 220179.

**GCS** (text): eye 220739, verbal 223900, motor 223901.

**Vasopressors** (treatment): norepinephrine 221906, epinephrine 221289,
dopamine 221662, vasopressin 222315, phenylephrine 221749.

**Cultures**: `MIMIC_IV_MicrobiologyTest/` prefix.
**Urine** (summed): Foley 226559, Void 226560, + nephrostomy/OR/PACU/irrigant.
**Ventilation** (presence): Invasive Vent 225792, PEEP 220339, Tidal Vol 224685.

---

## 3. Derivations

### SOFA (six organ systems, first-24h ICU and time-series)
Standard mimic-code thresholds. Components: respiration (PaO2/FiO2, vent-gated),
coagulation (platelets), liver (bilirubin), cardiovascular (MAP + vasopressors),
CNS (GCS text→points), renal (creatinine, urine).
- **Simplifications (stated):** respiration scores 0 if PaO2/FiO2 missing;
  cardio simplified (any vasopressor → ≥3, not dose-banded).

### Suspicion of infection
Antibiotic–culture pairing near the ICU stay: culture within [abx, abx+24h]
OR antibiotic within [culture, culture+72h]. Suspicion time = earlier of pair.

### Sepsis-3 (onset)
Suspected infection + peak SOFA ≥ 2 in window [suspicion−48h, suspicion+24h]
(baseline-0 convention). **Onset = suspicion time** (mimic-code convention).
First qualifying ICU stay per patient. Age ≥ 18.

### Treatment
First vasopressor within 4h of onset = treated. Pre-onset vasopressor → excluded.

### Outcome
28-day all-cause mortality (death within 0–28 days of onset).

### Severity scores
- **Charlson**: Quan 2005 ICD-9/10 mappings, 17 weighted categories.
- **SAPS-II**: full Le Gall 1993 — physiological (first-24h worst) + PaO2/FiO2
  (vent-gated) + 24h urine + chronic disease (ICD) + admission type.

### Exclusion funnel
Sepsis-3 → ICU ≥ 6h → no pre-onset vasopressor → valid outcome
→ (missing discharge notes: DEFERRED pending PhysioNet notes access).

---

## 4. Validation vs paper

| Quantity | This cohort | Paper |
|---|---|---|
| Sepsis-3 patients | 18,312 | 21,859 (84%) |
| Treated rate | 10.5% | 10.0% |
| 28-day mortality | 17.3% | 17.3% |
| Confounding (SOFA treated/control) | 9.8 / 5.9 | (treated sicker ✓) |
| SAPS-II treated/control | 55 / 44 | (treated sicker ✓) |

Cohort structure validates well. **Cohort count gap (84%)** attributable to
MEDS-vs-derived-table reconstruction + deferred missing-notes exclusion.

## 5. OPEN ISSUE — ATE sign differs from paper
Crude unadjusted ATE ≈ **−0.008** (treated 16.6% vs control 17.4%), vs paper's
structured-only PSM **+0.055**. Divergence **survives adjustment**:

| Estimator | ATE |
|---|---|
| Crude | −0.008 |
| IPW (stabilized, trimmed) | +0.012 |
| PS matching (1:1, caliper .05) | −0.059 |
| Regression adjustment | −0.057 |

Diagnostics performed:
- Persists under SAPS-II stratification (not a SOFA-cardio-inflation artifact).
- Not simple immortal-time bias (only 0.9% of control deaths within 4h of onset).
- Onset-definition sensitivity (suspicion / ICU-admit / suspicion+6h): ATE moves
  −0.008 → +0.001 → +0.019, none reach +0.055 — onset alone not the cause.
- **PSM (paper's own baseline) gives −0.057, not +0.055** — sign difference
  survives the paper's adjustment method.
- Propensity overlap is poor (treated mean PS 0.29 vs control 0.08), making
  matching/regression estimates unstable — a real limitation.

**Leading remaining suspect:** the missing-discharge-notes exclusion (deferred
until PhysioNet notes access). If excluded patients are disproportionately
early-death controls, including them inflates control mortality and flips the sign.
Cannot be tested until notes access granted. **Raised with advisor.**

**Onset-definition sensitivity test** (crude ATE under 3 onset anchors):
| Onset definition | n | treated% | ATE |
|---|---|---|---|
| A: suspicion time (current) | 18,312 | 10.5% | −0.008 |
| B: ICU admission | 18,281 | 12.7% | +0.001 |
| C: suspicion + 6h | 15,809 | 4.2% | +0.019 |

→ Onset anchor moves ATE toward positive but does NOT reach paper's +0.055.
Onset is a **partial** factor. Largest untested factor: **missing-notes
exclusion** (pending PhysioNet notes access) — plausibly correlated with early
death and treatment. Treated-group composition is highly sensitive to onset anchor.


