import os

from pathlib import Path
DATA_DIR="data"
print(f"Exploring: {os.path.abspath(DATA_DIR)}\n")
ext_counts={}
total_size=0
file_list=[]
for root,dirs,files in os.walk(DATA_DIR):
    depth=root.replace(DATA_DIR, "").count(os.sep)
    indent=" "*depth
    print(f"{indent}{os.path.basename(root)}/")
    for f in files :
        path = os.path.join(root, f)
        size = os.path.getsize(path)
        total_size += size
        ext = Path(f).suffix.lower()
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        file_list.append((path, size))
    for f in files[:8]:
        path = os.path.join(root, f)
        size_mb = os.path.getsize(path) / 1e6
        print(f"{indent}  {f}  ({size_mb:.2f} MB)")
    if len(files) > 8:
        print(f"{indent}  ... and {len(files)-8} more files")

print("\n" + "="*50)
print("SUMMARY")
print(f"  total files: {sum(ext_counts.values())}")
print(f"  total size:  {total_size/1e9:.2f} GB")
print(f"  file types (extension -> count):")
for ext, cnt in sorted(ext_counts.items(), key=lambda x: -x[1]):
    print(f"    {ext or '(no ext)':12s} {cnt}")

# Flag the likely data format
print("\n  Likely format:")
if ".parquet" in ext_counts:
    print("    -> Parquet shards (standard MEDS). We'll use pyarrow/pandas to load.")
if ".json" in ext_counts:
    print("    -> JSON present (possibly MEDS metadata/schema).")
if ".csv" in ext_counts:
    print("    -> CSV present.")
if ".pkl" in ext_counts:
    print("    -> Pickle files present.")