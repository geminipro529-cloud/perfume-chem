import csv
from pathlib import Path

EVIDENCE = Path(".omo/evidence")

# Check each CSV
for csv_name in ["odt_source_audit.csv", "consistency_audit.csv", "hedonic_audit.csv"]:
    csv_path = EVIDENCE / csv_name
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"{csv_name}: {len(rows)} rows, columns: {list(rows[0].keys()) if rows else 'EMPTY'}")
    else:
        print(f"{csv_name}: NOT FOUND")

# Check truths file
truths_path = EVIDENCE / "truths.jsonl"
with open(truths_path, encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()]
print(f"\ntruths.jsonl: {len(lines)} lines")
for l in lines[:3]:
    print(f"  {l[:120]}")
