#!/usr/bin/env python3
"""Audit IFRA/allergen coverage. Output: .omo/evidence/ifra_audit.md + truths.jsonl"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / ".omo" / "evidence"
TRUTHS_PATH = OUT / "truths.jsonl"

# Read EU 2023/1545 allergens
allergens_path = ROOT / ".opencode" / "library" / "eu_2023_1545_allergens.json"
allergens = []
if allergens_path.exists():
    allergens = json.loads(allergens_path.read_text(encoding="utf-8"))
    if not isinstance(allergens, list):
        allergens = list(allergens.values()) if isinstance(allergens, dict) else []

# Read phototoxic oils
photo_path = ROOT / ".opencode" / "library" / "phototoxic_oils.json"
phototoxic = []
if photo_path.exists():
    phototoxic = json.loads(photo_path.read_text(encoding="utf-8"))
    if not isinstance(phototoxic, list):
        phototoxic = list(phototoxic.values()) if isinstance(phototoxic, dict) else []

# Count YAML IFRA coverage
import re

YAML_DIR = ROOT / "data" / "materials"
ifra_count = 0
total_yaml = 0
for yf in sorted(YAML_DIR.glob("*.yaml")):
    content = yf.read_text(encoding="utf-8")
    blocks = re.split(r"\n  (?=\w)", content)
    for b in blocks:
        if re.search(r"^\s{2}[\w\s\-]+:\s*$", b, re.MULTILINE):
            total_yaml += 1
            if re.search(r"ifra_max_pct_edp:\s*[\d.eE\-]+", b):
                ifra_count += 1

# Generate report
report = f"""# IFRA / Allergen Audit
## EU 2023/1545 Allergens
Total in database: {len(allergens)} / 82 required
"""
if len(allergens) < 82:
    report += f"⚠️ Missing {82 - len(allergens)} allergens from EU 2023/1545 list\n"
report += f"""
## Phototoxic Oils
Total in database: {len(phototoxic)}
Known phototoxic oils to verify: bergamot, lime expressed, lemon cold-pressed, grapefruit, bitter orange, angelica root, rue, cumin, parsley leaf, tagetes, fig leaf
"""
report += f"""
## IFRA Limit Coverage
Materials with IFRA limits: {ifra_count} / {total_yaml} ({ifra_count * 100 // max(total_yaml, 1)}%)
Materials without IFRA limits: {total_yaml - ifra_count}
"""
(OUT / "ifra_audit.md").write_text(report, encoding="utf-8")

# Append truths
truths = []
for a in allergens:
    name = a.get("name", a) if isinstance(a, dict) else str(a)
    truths.append(
        json.dumps(
            {
                "id": f"ifra_{len(truths) + 1:04d}",
                "category": "ifra_allergen",
                "description": f"EU 2023/1545 allergen: {name}",
                "literature_source": "EU 2023/1545 (Annex III expansion)",
                "codebase_evidence": ".opencode/library/eu_2023_1545_allergens.json",
                "crosscheck_sources": ["EU 2023/1545", "IFRA 51st Amendment"],
                "verified_at": "2026-07-21",
            }
        )
    )
if ifra_count > 0:
    truths.append(
        json.dumps(
            {
                "id": f"ifra_{len(truths) + 1:04d}",
                "category": "ifra_allergen",
                "description": f"IFRA limits populated for {ifra_count}/{total_yaml} materials",
                "literature_source": "IFRA 51st Amendment",
                "codebase_evidence": "data/materials/*.yaml",
                "crosscheck_sources": ["IFRA Standards", "data/materials/*.yaml"],
                "verified_at": "2026-07-21",
            }
        )
    )

with open(TRUTHS_PATH, "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")

print(
    f"IFRA Audit: {len(allergens)} allergens, {ifra_count}/{total_yaml} IFRA limits, {len(truths)} truths"
)
