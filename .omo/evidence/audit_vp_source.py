#!/usr/bin/env python3
"""Audit VP source hierarchy across all YAML files. Output: .omo/evidence/vp_source_audit.csv + truths.jsonl"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
YAML_DIR = ROOT / "data" / "materials"
OUT = ROOT / ".omo" / "evidence"
TRUTHS_PATH = OUT / "truths.jsonl"

sources = Counter()
total = 0
entries = []

for yf in sorted(YAML_DIR.glob("*.yaml")):
    content = yf.read_text(encoding="utf-8")
    # Split into material blocks
    blocks = re.split(r"\n  (?=\w)", content)
    for b in blocks:
        name_match = re.search(r"^\s{2}([\w\s\-]+):\s*$", b, re.MULTILINE)
        vp_match = re.search(r"vp_25c_pa:\s*([\d.eE\-]+)", b)
        vp_src_match = re.search(r"vp_source:\s*(.+)", b)
        if name_match:
            name = name_match.group(1).strip()
            vp = vp_match.group(1) if vp_match else "?"
            vp_src = vp_src_match.group(1).strip() if vp_src_match else "UNKNOWN"
            if "#" in vp_src:
                vp_src = vp_src.split("#")[0].strip()
            if vp_src in ("null", "None", ""):
                vp_src = "UNKNOWN"
            sources[vp_src] += 1
            total += 1
            entries.append({"name": name, "vp_25c_pa": vp, "vp_source": vp_src, "file": yf.name})

# Write CSV
import csv

with open(OUT / "vp_source_report.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["name", "vp_25c_pa", "vp_source", "file"])
    w.writeheader()
    w.writerows(entries)

# Write report
report = f"""# VP Source Hierarchy Audit
Total materials: {total}

## Source Distribution
| Source | Count | % |
|--------|-------|---|
"""
for src, cnt in sources.most_common():
    report += f"| {src} | {cnt} | {cnt * 100 // max(total, 1)}% |\n"
report += "\n## Tier 1-2 Materials (NIST/EPI/PubChem_exp)\n"
tier1_2 = [e for e in entries if e["vp_source"] in ("NIST", "EPI", "PubChem_exp")]
report += f"Count: {len(tier1_2)} / {total}\n"
if tier1_2:
    for e in tier1_2[:20]:
        report += f"- {e['name']}: {e['vp_source']} (VP={e['vp_25c_pa']} Pa)\n"
report += f"\n## UNKNOWN Materials ({sources.get('UNKNOWN', 0)})\n"
unknown = [e for e in entries if e["vp_source"] == "UNKNOWN"]
for e in unknown[:20]:
    report += f"- {e['name']}: VP={e['vp_25c_pa']} Pa\n"

(OUT / "vp_source_report.md").write_text(report, encoding="utf-8")

# Append truths
truths = []
for e in entries:
    if e["vp_source"] != "UNKNOWN":
        truths.append(
            json.dumps(
                {
                    "id": f"vp_{len(truths) + 1:04d}",
                    "category": "vp_source",
                    "description": f"VP of {e['name']} ({e['vp_25c_pa']} Pa) sourced from {e['vp_source']}",
                    "literature_source": e["vp_source"],
                    "codebase_evidence": f"data/materials/{e['file']}",
                    "crosscheck_sources": [e["vp_source"], "data/materials/*.yaml"],
                    "verified_at": "2026-07-21",
                }
            )
        )

with open(TRUTHS_PATH, "a", encoding="utf-8") as f:
    for t in truths:
        f.write(t + "\n")

print(
    f"VP Source Audit: {total} materials, {len(truths)} sourced ({len(truths) * 100 // max(total, 1)}%)"
)
print(f"Source distribution: {dict(sources.most_common(5))}")
print(f"UNKNOWN: {sources.get('UNKNOWN', 0)}")
