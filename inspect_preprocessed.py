"""Read the .arrow Preprocessed files properly (HuggingFace datasets format)."""
import glob, os
import pyarrow as pa

# Find one arrow shard
shards = glob.glob("data/**/*.arrow", recursive=True)
print(f"Found {len(shards)} .arrow shards. Reading the first one:\n")
shard = shards[0]
print(f"  {shard}\n")

# .arrow files from HF datasets are Arrow IPC streams — read with pyarrow
try:
    with pa.memory_map(shard, "r") as source:
        table = pa.ipc.open_stream(source).read_all()
except Exception:
    # some are random-access format, not stream
    with pa.memory_map(shard, "r") as source:
        table = pa.ipc.open_file(source).read_all()

print(f"  rows in this shard: {table.num_rows}")
print(f"  columns: {table.column_names}\n")
print("  schema:")
print(table.schema)

# show the first row's content (truncated) to understand what each row IS
print("\n  FIRST ROW (truncated):")
row = table.slice(0, 1).to_pylist()[0]
for k, v in row.items():
    s = str(v)
    print(f"    {k}: {s[:200]}{'...' if len(s)>200 else ''}")