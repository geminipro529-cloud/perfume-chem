import csv
import json

truths = []
with open(".omo/evidence/odt_source_audit.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        truths.append(
            json.dumps(
                {
                    "id": f"odt_{i + 1:04d}",
                    "description": f"ODT of {row['material']} is {row['odt_air']} ppb air / {row['odt_eth']} ppm EtOH per {row['source_cited']}",
                    "literature_source": row["source_cited"],
                    "codebase_evidence": f"engine/odor_thresholds.py:ODT_DATA[{row['material']}]",
                    "crosscheck_sources": ["ODT_DATA", "ODT_VERIFICATION", "perfume_kb.jsonl"],
                    "vfy_status": row["vfy"],
                    "source_plausibility": row["source_verified"],
                    "verified_at": "2026-07-21",
                }
            )
        )
with open(".omo/evidence/truths.jsonl", "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")
print(f"Recovered {len(truths)} ODT truths")
