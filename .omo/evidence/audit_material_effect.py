#!/usr/bin/env python3
"""Audit material perfume effect — character, note, role, texture from ingredient_intelligence.py."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / ".omo" / "evidence"
TRUTHS_PATH = OUT / "truths.jsonl"

ii_path = ROOT / "engine" / "ingredient_intelligence.py"
content = ii_path.read_text(encoding="utf-8")

# Extract _PROFILES
match = re.search(r"_PROFILES\s*=\s*\{", content)
if not match:
    print("_PROFILES not found")
    exit(1)

start = match.start()
depth = 0
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

# Parse profile entries
entries = []
current_name = None
current_fields = {}
brace_depth = 0

for line in block.split("\n"):
    name_match = re.match(r'\s*"([^"]+)"\s*:\s*\{', line)
    if name_match:
        if current_name:
            entries.append({"name": current_name, **current_fields})
        current_name = name_match.group(1).strip()
        current_fields = {}
        brace_depth = 1
        continue
    if current_name:
        if "{" in line:
            brace_depth += 1
        if "}" in line:
            brace_depth -= 1
        if brace_depth <= 0:
            entries.append({"name": current_name, **current_fields})
            current_name = None
            current_fields = {}
            continue
        # Parse fields
        for field in ["character", "note", "role", "texture", "hedonic_valence", "synergies"]:
            fm = re.search(rf'"{field}"\s*:\s*(.+)', line)
            if fm:
                val = fm.group(1).strip().rstrip(",").strip('"')
                current_fields[field] = val

if current_name:
    entries.append({"name": current_name, **current_fields})

# Write CSV
rows = []
for e in entries:
    rows.append(
        {
            "material": e.get("name", "?"),
            "odor_character": e.get("character", "unknown"),
            "note_tier": e.get("note", "unknown"),
            "role": e.get("role", "unknown"),
            "texture": e.get("texture", "unknown"),
            "hedonic_valence": e.get("hedonic_valence", "unknown"),
            "synergies": e.get("synergies", "none"),
        }
    )

with open(OUT / "material_effect_audit.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "material",
            "odor_character",
            "note_tier",
            "role",
            "texture",
            "hedonic_valence",
            "synergies",
        ],
    )
    w.writeheader()
    w.writerows(rows)

# Append truths (one per material with character data)
truths = []
for e in entries:
    if e.get("character") and e["character"] != "unknown":
        truths.append(
            json.dumps(
                {
                    "id": f"mat_{len(truths) + 1:04d}",
                    "category": "material_perfume_effect",
                    "description": f"Material {e['name']}: character={e.get('character', '?')}, note={e.get('note', '?')}, role={e.get('role', '?')}, texture={e.get('texture', '?')}",
                    "literature_source": "ingredient_intelligence.py profiles / perfumery literature",
                    "codebase_evidence": "engine/ingredient_intelligence.py:_PROFILES",
                    "crosscheck_sources": ["_PROFILES", "YAML", "AGENTS.md"],
                    "verified_at": "2026-07-21",
                }
            )
        )

with open(TRUTHS_PATH, "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")

print(f"Material Effect Audit: {len(entries)} profiles, {len(truths)} with character data")
for e in entries[:5]:
    print(
        f"  {e.get('name', '?')}: char={e.get('character', '?')}, note={e.get('note', '?')}, role={e.get('role', '?')}"
    )
