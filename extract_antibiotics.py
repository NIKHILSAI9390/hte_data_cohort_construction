"""Extract antibiotics from the 2.46GB prescriptions.csv WITHOUT loading it whole.
Read in chunks, keep only antibiotic rows + needed columns, save a small file."""
import glob
import pandas as pd

PRESCRIPTIONS = glob.glob("data/**/prescriptions.csv", recursive=True)[0]

ANTIBIOTICS = [
    "adoxa","ala-tet","alodox","amikacin","amikin","amoxicillin","clavulanate",
    "ampicillin","sulbactam","augmentin","avelox","avidoxy","azactam","azithromycin",
    "aztreonam","axetil","bactocill","bactrim","bethkis","biaxin","bicillin l-a",
    "cayston","cefazolin","cedax","cefoxitin","ceftazidime","cefaclor","cefadroxil",
    "cefdinir","cefditoren","cefepime","cefotan","cefotetan","cefotaxime","ceftaroline",
    "cefpodoxime","cefpirome","cefprozil","ceftibuten","ceftin","ceftriaxone","cefuroxime",
    "cephalexin","cephalothin","cephapirin","chloramphenicol","cipro","ciprofloxacin",
    "claforan","clarithromycin","cleocin","clindamycin","cubicin","dicloxacillin",
    "doryx","doxycycline","duricef","dynacin","ery-tab","eryped","eryc","erythrocin",
    "erythromycin","factive","flagyl","fortaz","furadantin","garamycin","gentamicin",
    "kanamycin","keflex","ketek","levaquin","levofloxacin","lincocin","macrobid",
    "macrodantin","maxipime","mefoxin","metronidazole","minocin","minocycline",
    "moxifloxacin","myrac","nafcillin","neomycin","nitrofurantoin","norfloxacin",
    "noroxin","ocudox","ofloxacin","omnicef","oracea","oxacillin","pc pen vk",
    "pce dispertab","panixine","pediazole","penicillin","periostat","pfizerpen",
    "piperacillin","tazobactam","primsol","proquin","raniclor","rifadin","rifampin",
    "rocephin","smz-tmp","septra","septra ds","solodyn","spectracef",
    "streptomycin","sulfadiazine","sulfamethoxazole","trimethoprim","sulfatrim",
    "sulfisoxazole","suprax","synercid","tazicef","tetracycline","timentin","tobi",
    "tobramycin","unasyn","vancocin","vancomycin","vantin","vibativ",
    "vibra-tabs","vibramycin","zinacef","zithromax","zosyn","zyvox",
]

def is_antibiotic(drug):
    if not isinstance(drug, str): return False
    d = drug.lower()
    return any(a in d for a in ANTIBIOTICS)

USECOLS = ["subject_id","hadm_id","starttime","stoptime","drug","route"]

print(f"Reading {PRESCRIPTIONS} in chunks (only needed columns)...")
kept = []
total = 0
for i, chunk in enumerate(pd.read_csv(PRESCRIPTIONS, usecols=USECOLS,
                                      chunksize=500_000, low_memory=False)):
    total += len(chunk)
    abx = chunk[chunk["drug"].apply(is_antibiotic)]
    if len(abx): kept.append(abx)
    if i % 5 == 0:
        print(f"  processed {total:,} rows, kept {sum(len(k) for k in kept):,} antibiotic rows")

abx_all = pd.concat(kept, ignore_index=True)
print(f"\nDONE. Total rows scanned: {total:,}")
print(f"Antibiotic administrations kept: {len(abx_all):,}")
print(f"Unique patients with antibiotics: {abx_all['subject_id'].nunique():,}")
print(f"\nTop antibiotics found:")
print(abx_all['drug'].value_counts().head(20).to_string())

out = "data/antibiotics_filtered.parquet"
abx_all.to_parquet(out, index=False)
print(f"\nSaved filtered antibiotics -> {out}")