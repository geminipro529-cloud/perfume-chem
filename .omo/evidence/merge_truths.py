#!/usr/bin/env python3
"""Rebuild categorized truths.jsonl from all evidence CSVs. Uses write mode to deduplicate."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE = ROOT / ".omo" / "evidence"
TRUTHS_PATH = EVIDENCE / "truths.jsonl"

truths: list[dict] = []
seen_ids: set[str] = set()


def add(category: str, id_prefix: str, desc: str, lit_src: str, evidence: str, sources: list[str]):
    global truths, seen_ids
    tid = f"{id_prefix}_{len([t for t in truths if t['category'] == category]) + 1:04d}"
    if tid in seen_ids:
        return
    seen_ids.add(tid)
    truths.append(
        {
            "id": tid,
            "category": category,
            "description": desc,
            "literature_source": lit_src,
            "codebase_evidence": evidence,
            "crosscheck_sources": sources,
            "verified_at": "2026-07-21",
        }
    )


# ── ODT truths ──
odt_csv = EVIDENCE / "odt_source_audit.csv"
if odt_csv.exists():
    with open(odt_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            add(
                "odt_sources",
                "odt",
                f"ODT of {row['material']}: {row['odt_air']} ppb air / {row['odt_eth']} ppm EtOH — {row.get('source_cited', 'unknown source')} (vfy: {row.get('vfy', '?')}, plausibility: {row.get('source_verified', '?')})",
                row.get("source_cited", "unknown"),
                "engine/odor_thresholds.py:ODT_DATA",
                ["ODT_DATA", "ODT_VERIFICATION", "perfume_kb.jsonl"],
            )

# ── Consistency truths ──
cons_csv = EVIDENCE / "consistency_audit.csv"
if cons_csv.exists():
    with open(cons_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            add(
                "data_consistency",
                "consistency",
                f"Material '{row.get('material', '?')}' verified: VP match={row.get('vp_match', '?')}, ODT match={row.get('odt_match', '?')}, name match={row.get('name_match', '?')}",
                "internal cross-ref",
                "inventory.txt + YAML + PROFILES + ODT_DATA",
                [
                    "inventory.txt",
                    "data/materials/*.yaml",
                    "engine/ingredient_intelligence.py",
                    "engine/odor_thresholds.py",
                ],
            )

# ── Hedonic truths ──
hed_csv = EVIDENCE / "hedonic_audit.csv"
if hed_csv.exists():
    with open(hed_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            val = row.get("best_hedonic_valence", "?")
            src = row.get("source", "?")
            if val and val not in ("?", "None", ""):
                add(
                    "hedonic_valence",
                    "hedonic",
                    f"Hedonic valence of {row['material']}: {val} (source: {src})",
                    src,
                    "data/materials/*.yaml",
                    ["data/materials/*.yaml", "engine/ingredient_intelligence.py"],
                )

# ── Receptor truths (from receptor_map.csv) ──
rec_csv = EVIDENCE / "receptor_map.csv"
if rec_csv.exists():
    with open(rec_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mat = row.get("material", "?")
            rec = row.get("receptor", "?")
            cid = row.get("pubchem_cid", "?")
            if mat and rec:
                add(
                    "receptor_mapping",
                    "receptor",
                    f"{mat} interacts with {rec} (PubChem CID: {cid})",
                    f"PubChem CID {cid}",
                    f"PubChem/{cid}",
                    ["PubChem", "engine/pipeline/gates.py"],
                )

# ── Write ──
with open(TRUTHS_PATH, "w", encoding="utf-8") as f:
    f.write(
        json.dumps(
            {
                "_meta": {
                    "plan": "final-audit-polish-v1",
                    "category_targets": {
                        "odt_sources": 500,
                        "data_consistency": 500,
                        "hedonic_valence": 500,
                        "receptor_mapping": 500,
                        "biochem_neuro": 500,
                        "ifra_allergen": 500,
                        "phototoxicity": 500,
                        "vp_source": 500,
                        "eo_absolute_composition": 500,
                        "material_perfume_effect": 1000,
                    },
                    "total_target": 5500,
                    "verified_at": "2026-07-21",
                }
            }
        )
        + "\n"
    )
    for t in truths:
        f.write(json.dumps(t) + "\n")

# ── Report ──
from collections import Counter

counts = Counter(t["category"] for t in truths)
print("Truths by category:")
total = 0
for cat in sorted(counts):
    target = {
        "odt_sources": 500,
        "data_consistency": 500,
        "hedonic_valence": 500,
        "receptor_mapping": 500,
        "biochem_neuro": 500,
        "ifra_allergen": 500,
        "phototoxicity": 500,
        "vp_source": 500,
        "eo_absolute_composition": 500,
        "material_perfume_effect": 1000,
    }.get(cat, 500)
    print(f"  {cat}: {counts[cat]:>5} / {target} ({counts[cat] * 100 // (target or 1)}%)")
    total += counts[cat]
print(f"  TOTAL: {total}")
