#!/usr/bin/env python3
"""Audit hedonic/valence data coverage across YAML materials and ingredient_intelligence profiles."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(r"D:\chatbots\perfume-chem")
YAML_DIR = ROOT / "data" / "materials"
II_FILE = ROOT / "engine" / "ingredient_intelligence.py"
OUT_CSV = ROOT / ".omo" / "evidence" / "hedonic_audit.csv"
OUT_TRUTHS = ROOT / ".omo" / "evidence" / "truths.jsonl"

# ── Parse YAML files ──────────────────────────────────────────────────────────
yaml_materials: dict[str, dict] = {}


def parse_yaml_file(filepath: Path) -> list[dict]:
    """Manually parse the YAML list-of-dicts files (simple structure, no full YAML parser needed)."""
    entries = []
    current = None
    in_block = False
    block_key = None
    block_lines = []

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue

        # Detect start of new entry: "- canonical_name:"
        m_new = re.match(r"^- canonical_name:\s*(.+)$", stripped)
        if m_new:
            if current is not None and not in_block:
                entries.append(current)
            current = {"canonical_name": m_new.group(1).strip()}
            in_block = False
            block_key = None
            block_lines = []
            continue

        if current is None:
            continue

        # Handle block scalar indicator (e.g., "  notes: |")
        m_block = re.match(r"^  (\w+):\s*\|$", stripped)
        if m_block:
            in_block = True
            block_key = m_block.group(1)
            block_lines = []
            continue

        if in_block:
            # End of block: next key at indent level 2
            m_next = re.match(r"^  (\w+):", stripped)
            if m_next and block_lines:
                current[block_key] = "\n".join(line.strip() for line in block_lines)
                in_block = False
                block_key = None
                block_lines = []
            else:
                block_lines.append(stripped)
                continue

        if in_block:
            continue  # still collecting block

        # Parse scalar fields
        m_kv = re.match(r"^  (\w+(?:_\w+)*):\s*(.*)", stripped)
        if m_kv:
            key = m_kv.group(1)
            value = m_kv.group(2).strip()
            if value == "null":
                current[key] = None
            elif value == "":
                current[key] = None
            elif value.startswith('"') and value.endswith('"'):
                current[key] = value[1:-1]
            elif value == "true":
                current[key] = True
            elif value == "false":
                current[key] = False
            else:
                # Try numeric
                try:
                    current[key] = (
                        float(value) if "." in value or "e" in value.lower() else int(value)
                    )
                except (ValueError, TypeError):
                    current[key] = value

    # Don't forget the last entry
    if current is not None:
        if in_block and block_key and block_lines:
            current[block_key] = "\n".join(line.strip() for line in block_lines)
        entries.append(current)

    return entries


# Parse all YAML files
for yaml_file in sorted(YAML_DIR.glob("[A-Z].yaml")):
    entries = parse_yaml_file(yaml_file)
    for entry in entries:
        name = entry.get("canonical_name", "UNKNOWN")
        yaml_materials[name] = entry

print(
    f"YAML: {len(yaml_materials)} materials parsed from {len(list(YAML_DIR.glob('[A-Z].yaml')))} files"
)

# ── Parse ingredient_intelligence.py _PROFILES and _HEDONIC_OVERRIDES ──────────
ii_content = II_FILE.read_text(encoding="utf-8")

# Extract _HEDONIC_OVERRIDES
hedonic_overrides: dict[str, float] = {}
ho_match = re.search(r"_HEDONIC_OVERRIDES\s*=\s*\{([^}]+)\}", ii_content, re.DOTALL)
if ho_match:
    ho_block = ho_match.group(1)
    for pair in re.finditer(r'"([^"]+)"\s*:\s*([-\d.]+)', ho_block):
        hedonic_overrides[pair.group(1)] = float(pair.group(2))

print(f"_HEDONIC_OVERRIDES: {len(hedonic_overrides)} entries")

# Extract _PROFILES hedonic fields
# Find the _PROFILES dict
profiles_match = re.search(r"_PROFILES\s*=\s*\{", ii_content)
profiles_start = profiles_match.start() if profiles_match else None

# Find all "hedonic": value entries in _PROFILES
profiles_hedonic: dict[str, float] = {}
# Use regex to find each profile name and its hedonic value
# Pattern: "Name": { ... "hedonic": value, ...  }
# Strategy: find all "hedonic" that appear within the _PROFILES block
if profiles_start:
    profiles_end = ii_content.find("\n#", profiles_start)
    if profiles_end == -1:
        profiles_end = len(ii_content)
    profiles_block = ii_content[profiles_start:profiles_end]

    # Find each profile entry: the key before hedonic
    # We look for: "ProfileName": { ... "hedonic": value }
    # Walk backward from each hedonic occurrence to find the profile name
    hedonic_positions = [m.start() for m in re.finditer(r'"hedonic":\s*([-\d.]+)', profiles_block)]

    for hpos in hedonic_positions:
        hv_match = re.match(r'"hedonic":\s*([-\d.]+)', profiles_block[hpos:])
        if hv_match:
            hv = float(hv_match.group(1))
            # Walk backwards to find the profile name
            # Profile name is the last "Something": { before this hedonic
            before = profiles_block[:hpos]
            # Find all "key": { patterns before this position
            key_matches = list(re.finditer(r'"([^"]+)"\s*:\s*\{', before))
            if key_matches:
                pname = key_matches[-1].group(1)
                profiles_hedonic[pname] = hv

print(f"_PROFILES explicit hedonic: {len(profiles_hedonic)} entries")

# Also capture all profile names (even without hedonic)
all_profile_names = set()
key_matches = re.finditer(r'"([^"]+)"\s*:\s*\{', profiles_match.group(0) if profiles_match else "")
for km in key_matches:
    all_profile_names.add(km.group(1))

print(f"_PROFILES total entries: {len(all_profile_names)}")

# ── Build the audit dataset ────────────────────────────────────────────────────
audit_rows = []

for name, entry in yaml_materials.items():
    hv_raw = entry.get("hedonic_valence")

    # Classify the YAML hedonic_valence
    hv_numeric = None
    hv_status = "unknown"
    hv_source = ""

    if hv_raw is None:
        hv_status = "null_or_empty"
    elif isinstance(hv_raw, (int, float)):
        hv_numeric = float(hv_raw)
        hv_status = "numeric"
        hv_source = "yaml_explicit"
    elif isinstance(hv_raw, str):
        if hv_raw == "engine.hedonic_model":
            hv_status = "model_computed"
            hv_source = "engine.hedonic_model"
        elif hv_raw.startswith("manual:"):
            hv_status = "manual_annotation"
            hv_source = hv_raw
            # Try to extract a numeric value from preceding line?
        else:
            hv_status = "string_other"
            hv_source = hv_raw

    # Look up in ingredient_intelligence
    ii_hedonic = None
    ii_source = ""

    # Try canonical name in profiles_hedonic
    if name in profiles_hedonic:
        ii_hedonic = profiles_hedonic[name]
        ii_source = "ii_profile_explicit"
    elif name in hedonic_overrides:
        ii_hedonic = hedonic_overrides[name]
        ii_source = "ii_hedonic_overrides"

    # Try alias matching
    if ii_hedonic is None:
        # Check aliases in YAML
        aliases = entry.get("aliases", [])
        if aliases:
            for alias in aliases:
                if alias in profiles_hedonic:
                    ii_hedonic = profiles_hedonic[alias]
                    ii_source = f"ii_profile_via_alias({alias})"
                    break
                if alias in hedonic_overrides:
                    ii_hedonic = hedonic_overrides[alias]
                    ii_source = f"ii_overrides_via_alias({alias})"
                    break

    # Determine best hedonic value and its provenance
    best_val = hv_numeric
    best_source = hv_source

    if best_val is None and ii_hedonic is not None:
        best_val = ii_hedonic
        best_source = ii_source
    elif best_val is not None and ii_hedonic is not None:
        if abs(best_val - ii_hedonic) < 0.001:
            best_source = f"{hv_source} + {ii_source} (consistent)"
        else:
            best_source = f"{hv_source} (YAML={best_val}, II={ii_hedonic})"

    # Literature found status
    literature_found = "none"
    if hv_numeric is not None:
        literature_found = "yaml_hardcoded"
    elif ii_hedonic is not None:
        literature_found = "ii_profile"
    elif hv_raw == "engine.hedonic_model":
        literature_found = "model_inferred"
    elif hv_raw and str(hv_raw).startswith("manual:"):
        literature_found = "manual_estimate"

    inventory_status = "in_inventory" if entry.get("user_in_inventory") else "not_in_inventory"

    audit_rows.append(
        {
            "material": name,
            "yaml_hedonic_valence_raw": str(hv_raw) if hv_raw is not None else "null",
            "yaml_hedonic_numeric": hv_numeric,
            "ii_profile_hedonic": ii_hedonic,
            "best_hedonic_valence": best_val,
            "literature_found": literature_found,
            "source": best_source,
            "inventory_status": inventory_status,
        }
    )

# Also add materials only in II profiles, not in YAML
for pname in all_profile_names:
    if pname not in yaml_materials:
        pv = profiles_hedonic.get(pname)
        ho = hedonic_overrides.get(pname)
        best = pv if pv is not None else ho
        source = (
            "ii_profile_explicit"
            if pv is not None
            else ("ii_hedonic_overrides" if ho is not None else "none")
        )
        lit = "ii_profile" if best is not None else "none"

        audit_rows.append(
            {
                "material": pname,
                "yaml_hedonic_valence_raw": "NO_YAML_ENTRY",
                "yaml_hedonic_numeric": None,
                "ii_profile_hedonic": best,
                "best_hedonic_valence": best,
                "literature_found": lit,
                "source": source,
                "inventory_status": "no_yaml_entry",
            }
        )

# ── Statistics ─────────────────────────────────────────────────────────────────
total = len(audit_rows)
with_hedonic = sum(1 for r in audit_rows if r["best_hedonic_valence"] is not None)
without_hedonic = total - with_hedonic
yaml_populated = sum(1 for r in audit_rows if r["yaml_hedonic_numeric"] is not None)
yaml_model = sum(1 for r in audit_rows if r["yaml_hedonic_valence_raw"] == "engine.hedonic_model")
yaml_manual = sum(1 for r in audit_rows if r["yaml_hedonic_valence_raw"].startswith("manual:"))
yaml_null = sum(1 for r in audit_rows if r["yaml_hedonic_valence_raw"] in ("null", "NO_YAML_ENTRY"))
ii_populated = sum(1 for r in audit_rows if r["ii_profile_hedonic"] is not None)
in_inventory = sum(1 for r in audit_rows if r["inventory_status"] == "in_inventory")

coverage_pct = (with_hedonic / total * 100) if total > 0 else 0

print(f"\n{'=' * 60}")
print("HEDONIC AUDIT RESULTS")
print(f"{'=' * 60}")
print(f"Total materials audited:        {total}")
print(f"  With any hedonic value:       {with_hedonic}  ({coverage_pct:.1f}%)")
print(f"  Without hedonic value:        {without_hedonic}  ({100 - coverage_pct:.1f}%)")
print("")
print("YAML data:")
print(f"  Explicit numeric (YAML):      {yaml_populated}")
print(f"  Model-computed (YAML):        {yaml_model}")
print(f"  Manual annotation (YAML):     {yaml_manual}")
print(f"  Null/empty (YAML):            {yaml_null}")
print("")
print("Ingredient Intelligence:")
print(f"  _PROFILES explicit hedonic:   {len(profiles_hedonic)}")
print(f"  _HEDONIC_OVERRIDES entries:   {len(hedonic_overrides)}")
print(f"  Total profiles:               {len(all_profile_names)}")
print("")
print("Inventory status:")
print(f"  In inventory:                 {in_inventory}")
print("")

# ── Write CSV ──────────────────────────────────────────────────────────────────
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=audit_rows[0].keys())
    writer.writeheader()
    writer.writerows(audit_rows)

print(f"CSV written: {OUT_CSV}")

# ── Write truths.jsonl ─────────────────────────────────────────────────────────
truths_written = 0
with open(OUT_TRUTHS, "w", encoding="utf-8") as f:
    for row in audit_rows:
        if row["best_hedonic_valence"] is not None:
            # Determine evidence class
            evidence_class = "HEURISTIC"
            if row["literature_found"] in ("yaml_hardcoded", "ii_profile"):
                evidence_class = "LITERATURE_DERIVED"
            elif row["literature_found"] == "model_inferred":
                evidence_class = "HEURISTIC"
            elif row["literature_found"] == "manual_estimate":
                evidence_class = "EMPIRICALLY_CALIBRATED"

            truth = {
                "material": row["material"],
                "property": "hedonic_valence",
                "value": row["best_hedonic_valence"],
                "source": row["source"],
                "evidence_class": evidence_class,
                "scope": "repository_canonical",
            }
            f.write(json.dumps(truth) + "\n")
            truths_written += 1

print(f"Truths written: {truths_written} entries in {OUT_TRUTHS}")

# ── Print gap materials (in inventory but no hedonic) ──────────────────────────
print(f"\n{'=' * 60}")
print("GAPS: In-inventory materials WITHOUT hedonic data")
print(f"{'=' * 60}")
gap_count = 0
for row in audit_rows:
    if row["inventory_status"] == "in_inventory" and row["best_hedonic_valence"] is None:
        print(f"  - {row['material']}")
        gap_count += 1

print(f"\nTotal in-inventory gaps: {gap_count}")

# ── Coverage summary to JSON for downstream ────────────────────────────────────
summary = {
    "audit_date": "2026-07-21",
    "total_materials": total,
    "with_hedonic": with_hedonic,
    "without_hedonic": without_hedonic,
    "coverage_percent": round(coverage_pct, 1),
    "yaml_explicit_numeric": yaml_populated,
    "yaml_model_computed": yaml_model,
    "yaml_manual": yaml_manual,
    "yaml_null": yaml_null,
    "ii_profiles_explicit_hedonic": len(profiles_hedonic),
    "ii_hedonic_overrides": len(hedonic_overrides),
    "ii_total_profiles": len(all_profile_names),
    "in_inventory_count": in_inventory,
    "in_inventory_gaps": gap_count,
    "truths_written": truths_written,
}

summary_path = ROOT / ".omo" / "evidence" / "hedonic_audit_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"\nSummary written: {summary_path}")
print("\nDone.")
