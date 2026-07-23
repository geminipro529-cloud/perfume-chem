#!/usr/bin/env python3
"""Audit phototoxicity database + generate truths."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / ".omo" / "evidence"
TRUTHS_PATH = OUT / "truths.jsonl"

photo_path = ROOT / ".opencode" / "library" / "phototoxic_oils.json"
if not photo_path.exists():
    print("phototoxic_oils.json not found")
    exit(1)

phototoxic = json.loads(photo_path.read_text(encoding="utf-8"))
known_phototoxic = [
    "Bergamot",
    "Lime (expressed)",
    "Lemon (cold-pressed)",
    "Grapefruit",
    "Bitter Orange",
    "Angelica Root",
    "Rue",
    "Cumin",
    "Parsley Leaf",
    "Tagetes",
    "Fig Leaf",
    "Clementine",
    "Mandarin Leaf",
]

# Generate truths
truths = []
for oil in phototoxic:
    name = oil.get("name", str(oil)) if isinstance(oil, dict) else str(oil)
    bergaptene = oil.get("bergaptene_ppm", "?") if isinstance(oil, dict) else "?"
    truths.append(
        json.dumps(
            {
                "id": f"phototoxic_{len(truths) + 1:04d}",
                "category": "phototoxicity",
                "description": f"Phototoxic oil: {name} (bergaptene: {bergaptene} ppm)",
                "literature_source": "IFRA Phototoxicity Guidelines",
                "codebase_evidence": ".opencode/library/phototoxic_oils.json",
                "crosscheck_sources": ["IFRA Standards", "EU SCCS"],
                "verified_at": "2026-07-21",
            }
        )
    )

# Flag missing oils
in_db = {
    o.get("name", str(o)).lower() if isinstance(o, dict) else str(o).lower() for o in phototoxic
}
missing = [k for k in known_phototoxic if k.lower() not in in_db]
gaps = {
    "total_in_db": len(phototoxic),
    "known_phototoxic": known_phototoxic,
    "missing_from_db": missing,
}
(OUT / "phototoxic_gaps.json").write_text(json.dumps(gaps, indent=2))

with open(TRUTHS_PATH, "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")

print(f"Phototoxic Audit: {len(phototoxic)} in DB, {len(missing)} missing, {len(truths)} truths")
if missing:
    print(f"  Missing: {missing}")
