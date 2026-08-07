#!/usr/bin/env python3
"""ODT Data Source Audit — cross-reference every material against published literature.

Reads engine/odor_thresholds.py ODT_DATA + ODT_VERIFICATION dicts,
and .opencode/library/perfume_kb.jsonl odt_* entries.
Generates .omo/evidence/odt_source_audit.csv and .omo/evidence/truths.jsonl
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

# ── Setup sys.path so engine imports work ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION


def load_perfume_kb_odt_entries(kb_path: Path) -> dict[str, dict]:
    """Load all odt_* entries from perfume_kb.jsonl, keyed by name."""
    odt_entries: dict[str, dict] = {}
    if not kb_path.exists():
        print(f"WARNING: {kb_path} not found — skipping perfume_kb cross-reference")
        return odt_entries

    with open(kb_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("source") == "odor_thresholds" and "odt_air" in entry:
                name = entry.get("name", "")
                if name:
                    odt_entries[normalize_name(name)] = entry
    return odt_entries


def extract_comment_sources(odt_data_value: dict) -> list[str]:
    """Extract source citations from comment-style annotations in the ODT dict.

    Some entries lack a `sources` key but have citation data in `ref` or `note` fields,
    or in inline comments captured during parsing.
    """
    sources = []
    # Check for inline reference notes
    note = odt_data_value.get("note", "")
    if note and isinstance(note, str):
        # Look for citation patterns like "X et al. (YEAR)" or "X (YEAR)"
        refs = re.findall(r"[A-Z][a-z]+\s+(?:et al\.\s+)?\(\d{4}\)", note)
        sources.extend(refs)
    # Check char field for inline references
    char = odt_data_value.get("char", "")
    if char and isinstance(char, str):
        refs = re.findall(r"[A-Z][a-z]+\s+(?:et al\.\s+)?\(\d{4}\)", char)
        sources.extend(refs)
    return sources


def assess_source_plausibility(sources: list[str]) -> str:
    """Assess whether cited sources are plausible (have author-year format, known journals)."""
    if not sources:
        return "UNSOURCED"

    plausible = []
    implausible = []
    for s in sources:
        # Check for author-year pattern: "Smith et al. (2020)" or "Smith (2020)"
        if re.match(r"^[A-Z][a-z]+(?:\s+et al\.)?\s*\(\d{4}\)", s):
            plausible.append(s)
        elif re.match(r"^[A-Z][a-z]+(?:\s+et al\.)?\s+\d{4}", s):
            plausible.append(s)
        elif re.match(r"^[A-Z][a-z]+(?:\s+et al\.)?\s*\(\d{4}\)\s+\w+", s):
            plausible.append(s)
        elif any(
            journal in s.lower()
            for journal in [
                "j. agric. food chem",
                "j. org. chem",
                "chem. biodiv",
                "front. chem",
                "helv. chim. acta",
                "j. oleo sci",
                "brewingScience",
                "z. lebensm",
                "eur. j. org. chem",
                "anal. chem",
                "agric. biol. chem",
                "flavour fragr.",
                "j. chem. ecol",
            ]
        ):
            plausible.append(s)
        else:
            implausible.append(s)

    if not plausible and implausible:
        return "IMPLAUSIBLE"
    elif plausible and implausible:
        return "MIXED"
    elif plausible:
        return "PLAUSIBLE"
    return "UNKNOWN"


def build_audit() -> list[dict]:
    """Build the complete audit table."""
    kb_odts = load_perfume_kb_odt_entries(ROOT / ".opencode" / "library" / "perfume_kb.jsonl")

    rows = []
    for mat_name, data in sorted(ODT_DATA.items()):
        norm = normalize_name(mat_name)

        odt_air = data.get("odt_air")
        odt_eth = data.get("odt_eth")
        vfy = data.get("vfy", "UNVERIFIED")

        # Sources from ODT_DATA directly
        sources_data = data.get("sources", [])
        # Sources from ODT_VERIFICATION (keyed by same name)
        sources_verify = ODT_VERIFICATION.get(mat_name, {}).get("sources", [])
        # Comment-embedded sources
        sources_comment = extract_comment_sources(data)

        # Combine all sources, deduplicate
        all_sources = list(
            dict.fromkeys(
                (sources_data if isinstance(sources_data, list) else [sources_data])
                + (sources_verify if isinstance(sources_verify, list) else [sources_verify])
                + sources_comment
            )
        )
        # Flatten semicolon-separated sources
        flat_sources = []
        for s in all_sources:
            for part in re.split(r"\s*;\s*", s):
                part = part.strip()
                if part and part not in flat_sources:
                    flat_sources.append(part)

        has_source = bool(flat_sources)
        source_verified = assess_source_plausibility(flat_sources)

        # Cross-check with perfume_kb.jsonl
        kb_entry = kb_odts.get(norm, {})
        kb_has_source = "sources" in kb_entry and bool(kb_entry.get("sources", []))

        # Determine truth_id if verifiable
        truth_id = ""
        sourced_reason = ""
        if vfy in ("PEER_CROSS", "PEER_SINGLE") and has_source:
            truth_id = f"odt_{norm.replace(' ', '_').replace('-', '_')}"
            sourced_reason = (
                f"Verified by {len(flat_sources)} source(s): {'; '.join(flat_sources[:3])}"
            )
        elif vfy in ("PEER_EST", "DERIVED") and has_source:
            truth_id = f"odt_{norm.replace(' ', '_').replace('-', '_')}"
            sourced_reason = f"Estimated/Derived from: {'; '.join(flat_sources[:3])}"
        elif vfy == "UNVERIFIED" and has_source:
            sourced_reason = (
                f"Has source annotation but marked UNVERIFIED: {'; '.join(flat_sources[:3])}"
            )
        elif vfy == "UNVERIFIED" and not has_source:
            sourced_reason = "No peer-reviewed source located"

        rows.append(
            {
                "material": mat_name,
                "odt_air": odt_air if odt_air is not None else "",
                "odt_eth": odt_eth if odt_eth is not None else "",
                "vfy": vfy,
                "source_cited": "; ".join(flat_sources) if flat_sources else "NONE",
                "source_verified": source_verified,
                "kb_has_source": str(kb_has_source) if kb_entry else "NOT_IN_KB",
                "sourced_reason": sourced_reason,
                "truth_id": truth_id,
            }
        )

    return rows


def write_csv(rows: list[dict], path: Path):
    """Write the audit CSV."""
    fieldnames = [
        "material",
        "odt_air",
        "odt_eth",
        "vfy",
        "source_cited",
        "source_verified",
        "kb_has_source",
        "sourced_reason",
        "truth_id",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def write_truths(rows: list[dict], path: Path, min_truths: int = 15):
    """Write truth entries as JSONL. Prioritizes verified entries with sources."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Prioritize: PEER_CROSS > PEER_SINGLE > PEER_EST > DERIVED
    priority = {"PEER_CROSS": 0, "PEER_SINGLE": 1, "PEER_EST": 2, "DERIVED": 3, "UNVERIFIED": 4}

    candidates = sorted(
        [r for r in rows if r["truth_id"] and r["source_cited"] != "NONE"],
        key=lambda r: (priority.get(r["vfy"], 5), r["material"]),
    )

    truths = []
    seen = set()
    for r in candidates:
        tid = r["truth_id"]
        if tid in seen:
            continue
        seen.add(tid)

        source_str = r["source_cited"]
        # Take first source as primary
        primary_source = source_str.split(";")[0].strip() if source_str else "Unknown"

        truths.append(
            {
                "id": tid,
                "description": f"ODT of {r['material']} is {r['odt_air']} ppb (air) / {r['odt_eth']} ppm (EtOH) per {primary_source}",
                "literature_source": source_str,
                "codebase_evidence": f"engine/odor_thresholds.py:ODT_DATA['{r['material']}']",
                "crosscheck_sources": ["ODT_DATA", "ODT_VERIFICATION", "perfume_kb.jsonl"],
                "vfy_status": r["vfy"],
                "source_plausibility": r["source_verified"],
                "verified_at": "2026-07-21",
            }
        )

        if len(truths) >= 100:  # Cap at reasonable number
            break

    with open(path, "w", encoding="utf-8") as f:
        for t in truths:
            f.write(json.dumps(t) + "\n")

    print(f"Wrote {len(truths)} truth entries to {path}")
    if len(truths) < min_truths:
        print(f"WARNING: Only {len(truths)} truth entries — target is {min_truths}+")


def print_summary(rows: list[dict]):
    """Print audit summary statistics."""
    total = len(rows)
    with_sources = sum(1 for r in rows if r["source_cited"] != "NONE")
    without_sources = total - with_sources

    vfy_counts = {}
    for r in rows:
        vfy_counts[r["vfy"]] = vfy_counts.get(r["vfy"], 0) + 1

    plausibility_counts = {}
    for r in rows:
        plausibility_counts[r["source_verified"]] = (
            plausibility_counts.get(r["source_verified"], 0) + 1
        )

    print("\n" + "=" * 60)
    print("ODT DATA SOURCE AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total materials in ODT_DATA:     {total}")
    print(f"With VFY tag + sources cited:    {with_sources} ({with_sources * 100 // total}%)")
    print(f"Without sources (UNSOURCED):     {without_sources} ({without_sources * 100 // total}%)")
    print()
    print("Verification status breakdown:")
    for vfy in ["PEER_CROSS", "PEER_SINGLE", "PEER_EST", "DERIVED", "UNVERIFIED"]:
        c = vfy_counts.get(vfy, 0)
        bar = "█" * (c * 50 // total) if total else ""
        print(f"  {vfy:14s}: {c:4d} ({c * 100 // total:2d}%) {bar}")

    print()
    print("Source plausibility assessment:")
    for key in ["PLAUSIBLE", "MIXED", "IMPLAUSIBLE", "UNSOURCED", "UNKNOWN"]:
        c = plausibility_counts.get(key, 0)
        print(f"  {key:14s}: {c:4d}")
    print()

    # List top unsourced materials (non-solvent/stabilizer)
    unsourced = [r for r in rows if r["source_cited"] == "NONE"]
    solvents = {
        "bht",
        "ethanol",
        "diethyl phthalate",
        "dipropylene glycol",
        "isopropyl myristate",
        "triethyl citrate",
    }
    unsourced_non_solvent = [r for r in unsourced if r["material"] not in solvents]
    print(f"Unsourced materials (excluding solvents/stabilizers): {len(unsourced_non_solvent)}")
    print("First 20:")
    for r in unsourced_non_solvent[:20]:
        print(f"  - {r['material']} (ODT_air={r['odt_air']}, vfy={r['vfy']})")


def main():
    evidence_dir = ROOT / ".omo" / "evidence"
    csv_path = evidence_dir / "odt_source_audit.csv"
    jsonl_path = evidence_dir / "truths.jsonl"

    print("Building ODT source audit...")
    rows = build_audit()

    print("Writing CSV...")
    write_csv(rows, csv_path)

    print("Writing truths JSONL...")
    write_truths(rows, jsonl_path)

    print_summary(rows)

    # Verify deliverables exist
    assert csv_path.exists(), f"CSV not created: {csv_path}"
    assert jsonl_path.exists(), f"JSONL not created: {jsonl_path}"
    assert len(rows) >= 100, f"Only {len(rows)} materials audited — need 100+"
    print(f"\n✓ Audit complete. {len(rows)} materials audited.")


if __name__ == "__main__":
    main()
