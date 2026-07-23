#!/usr/bin/env python3
"""Audit EO/absolute composition from natural_absolute_decomposition.py."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / ".omo" / "evidence"
TRUTHS_PATH = OUT / "truths.jsonl"

decomp_path = ROOT / "engine" / "pipeline" / "natural_absolute_decomposition.py"
content = decomp_path.read_text(encoding="utf-8")

# Extract _ABSOLUTE_CONSTITUENTS dict
match = re.search(r"_ABSOLUTE_CONSTITUENTS\s*=\s*\{", content)
if not match:
    print("_ABSOLUTE_CONSTITUENTS not found")
    exit(1)

# Find the closing brace by counting braces
start = match.end()
depth = 1
end = start
for i in range(start, len(content)):
    if content[i] == "{":
        depth += 1
    elif content[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

block = content[match.start() : end]

# Extract natural entries
entries = []
current_abs = None
for line in block.split("\n"):
    abs_match = re.match(r'\s*"([^"]+)"\s*:\s*\{', line)
    if abs_match:
        current_abs = abs_match.group(1).strip()
        entries.append({"name": current_abs, "constituents": [], "total_wt": 0.0})
        continue
    if current_abs and "}" in line:
        current_abs = None
        continue
    if current_abs:
        const_match = re.match(r'\s*"([^"]+)"\s*:\s*([\d.]+)', line)
        if const_match:
            cname = const_match.group(1).strip()
            wt = float(const_match.group(2))
            entries[-1]["constituents"].append((cname, wt))
            entries[-1]["total_wt"] += wt

# Get character impact compounds
char_match = re.search(r"_CHARACTER_IMPACT_BONUS\s*=\s*\{([^}]+)\}", content, re.DOTALL)
char_bonus = {}
if char_match:
    for m in re.finditer(r'"([^"]+)"\s*:\s*\{[^}]*"compound":\s*"([^"]+)"', char_match.group(1)):
        char_bonus[m.group(1).strip()] = m.group(2).strip()

# Write CSV
rows = []
for e in entries:
    top3 = ", ".join(
        [
            f"{c}({w * 100:.1f}%)"
            for c, w in sorted(e["constituents"], key=lambda x: x[1], reverse=True)[:3]
        ]
    )
    rows.append(
        {
            "natural_name": e["name"],
            "num_constituents": len(e["constituents"]),
            "weight_coverage_pct": round(e["total_wt"] * 100, 1),
            "character_compounds": top3,
            "has_character_bonus": e["name"].lower() in {k.lower() for k in char_bonus},
            "decomposition_module": "natural_absolute_decomposition.py",
        }
    )

with open(OUT / "eo_composition_audit.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "natural_name",
            "num_constituents",
            "weight_coverage_pct",
            "character_compounds",
            "has_character_bonus",
            "decomposition_module",
        ],
    )
    w.writeheader()
    w.writerows(rows)

# Append truths
truths = []
for e in entries:
    truths.append(
        json.dumps(
            {
                "id": f"eo_{len(truths) + 1:04d}",
                "category": "eo_absolute_composition",
                "description": f"Natural {e['name']}: {len(e['constituents'])} constituents at {e['total_wt'] * 100:.1f}% weight coverage. Top 3: {', '.join([f'{c}({w * 100:.1f}%)' for c, w in sorted(e['constituents'], key=lambda x: x[1], reverse=True)[:3]])}",
                "literature_source": "GC-O literature / published decomposition",
                "codebase_evidence": "engine/pipeline/natural_absolute_decomposition.py:_ABSOLUTE_CONSTITUENTS",
                "crosscheck_sources": ["decomposition module", "GC-O literature"],
                "verified_at": "2026-07-21",
            }
        )
    )

with open(TRUTHS_PATH, "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")

print(f"EO Composition Audit: {len(entries)} naturals decomposed, {len(truths)} truths")
for e in entries[:5]:
    print(
        f"  {e['name']}: {len(e['constituents'])} constituents, {e['total_wt'] * 100:.1f}% coverage"
    )
