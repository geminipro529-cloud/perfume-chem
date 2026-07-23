"""
Cross-reference audit: inventory.txt vs YAML vs PROFILES vs ODT_DATA.
Output: .omo/evidence/consistency_audit.csv + .omo/evidence/truths.jsonl
"""

import csv
import glob as glob_mod
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path("D:/chatbots/perfume-chem")
sys.path.insert(0, str(ROOT))


# ── 1. Parse inventory.txt ──
def parse_inventory():
    """Parse inventory.txt, return list of {name, raw_name, dilution, category, depleted}"""
    materials = []
    current_category = "Unknown"
    with open(ROOT / "inventory.txt", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            # Category headers
            if line.startswith("--- ") and line.endswith(" ---"):
                current_category = line.strip("- ").strip()
                continue
            if line.startswith("---") and line.endswith("---"):
                continue
            # Material entries: "- Name (dilution%)  # optional comment"
            if line.startswith("- ") or line.startswith(" - "):
                # Strip leading bullet
                entry = line.lstrip("- ").strip()
                # Remove trailing comments
                if "  #" in entry:
                    entry = entry.split("  #")[0].strip()
                if "#" in entry and "(" not in entry.split("#")[0]:
                    entry = entry.split("#")[0].strip()

                # Detect DEPLETED
                depleted = "DEPLETED" in line.upper()

                # Parse dilution from parenthetical
                dilution = "neat"
                name = entry
                m = re.match(r"^(.+?)\s*\(([\d.%\s]+(?:(?:w/w|w/v|in)\s*.+?)?)\)$", entry)
                if m:
                    name = m.group(1).strip()
                    dil_str = m.group(2).strip()
                    dilution = dil_str

                # Skip TOTALS section
                if current_category.startswith("TOTALS"):
                    continue
                if "TOTALS" in line:
                    continue

                # Skip empty lines after stripping
                if not name:
                    continue

                materials.append(
                    {
                        "raw_name": name,
                        "inventory_name": name,
                        "dilution": dilution,
                        "category": current_category,
                        "depleted": depleted,
                    }
                )
    return materials


# ── 2. Build YAML lookup ──
def build_yaml_lookup():
    """Read all YAML files, build {canonical_name: {entry}} and {alias: canonical_name}"""
    yaml_entries = {}  # canonical_name -> entry
    alias_map = {}  # alias -> canonical_name

    for yaml_file in sorted(glob_mod.glob(str(ROOT / "data/materials/*.yaml"))):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        for entry in data:
            cn = entry.get("canonical_name", "")
            if cn:
                cn_lower = cn.strip().lower()
                yaml_entries[cn_lower] = entry
                for alias in entry.get("aliases", []):
                    alias_map[alias.strip().lower()] = cn_lower

    return yaml_entries, alias_map


# ── 3. Build PROFILES lookup ──
# We'll use exec to extract _PROFILES safely
def build_profiles_lookup():
    """Extract _PROFILES dict from ingredient_intelligence.py"""
    from engine.ingredient_intelligence import _PROFILES

    return _PROFILES


# ── 4. Build ODT_DATA lookup ──
def build_odt_lookup():
    """Extract ODT_DATA dict from odor_thresholds.py"""
    from engine.odor_thresholds import ODT_DATA

    return ODT_DATA


# ── Name normalization using engine utilities ──
from engine.name_utils import normalize_name


def find_in_source(name, source_dict, source_name):
    """Try to find a material name in a source dict.
    Returns (matched_key, match_type) or (None, None).
    match_type: 'exact', 'normalized', 'partial'
    """
    if not name:
        return None, None

    name_lower = name.lower().strip()

    # Exact match
    if name_lower in source_dict:
        return name_lower, "exact"

    # Match using normalize_name
    norm = normalize_name(name)
    if norm in source_dict:
        return norm, "normalized"

    # Try partial/alias match
    for key in source_dict:
        key_norm = normalize_name(key)
        if key_norm == norm:
            return key, "normalized"

    # Try to match first word or common substring
    # (material names like "Bergamot EO" might be "bergamot eo" in ODT)
    return None, None


def find_in_yaml(name, yaml_entries, alias_map):
    """Try to find a material in YAML entries."""
    if not name:
        return None, None

    name_lower = name.lower().strip()

    # Exact canonical match
    if name_lower in yaml_entries:
        return name_lower, "exact"

    # Alias match
    if name_lower in alias_map:
        canonical = alias_map[name_lower]
        return canonical, "alias"

    # Normalize and try
    norm = normalize_name(name)
    if norm in yaml_entries:
        return norm, "normalized"
    if norm in alias_map:
        return alias_map[norm], "normalized_alias"

    # Try partial
    for cn, entry in yaml_entries.items():
        if entry.get("user_in_inventory"):
            # Check aliases for this entry
            for alias in entry.get("aliases", []):
                if normalize_name(alias) == norm:
                    return cn, "found_via_alias"

    return None, None


def find_in_profiles(name, profiles):
    """Try to find material in PROFILES dict."""
    if not name:
        return None, None

    name_lower = name.lower().strip()

    # Exact match
    if name_lower in profiles:
        return name_lower, "exact"

    # Case-insensitive match
    for key in profiles:
        if key.lower() == name_lower:
            return key, "case_insensitive"

    # Normalize
    norm = normalize_name(name)
    if norm in profiles:
        return norm, "normalized"
    for key in profiles:
        if key.lower() == norm:
            return key, "normalized_case"

    # Try partial
    for key in profiles:
        if normalize_name(key) == norm:
            return key, "normalized_key"

    return None, None


def find_in_odt(name, odt_data):
    """Try to find material in ODT_DATA dict (all lowercase keys)."""
    if not name:
        return None, None

    name_lower = name.lower().strip()

    # Exact match
    if name_lower in odt_data:
        return name_lower, "exact"

    # Normalize
    norm = normalize_name(name)
    if norm in odt_data:
        return norm, "normalized"

    # Try variations
    for key in odt_data:
        if normalize_name(key) == norm:
            return key, "normalized_key"

    return None, None


# ── VP comparison ──
def get_vp_yaml(yaml_entries, matched_key):
    """Get VP from YAML entry."""
    if matched_key and matched_key in yaml_entries:
        vp = yaml_entries[matched_key].get("vp_25c_pa")
        if vp is not None:
            return float(vp)
    return None


def get_vp_profiles(profiles, matched_key):
    """Get VP from PROFILES entry."""
    if matched_key and matched_key in profiles:
        vp = profiles[matched_key].get("vp")
        if vp is not None:
            return float(vp)
    return None


def get_odt_air_yaml(yaml_entries, matched_key):
    """Get ODT air from YAML."""
    if matched_key and matched_key in yaml_entries:
        odt = yaml_entries[matched_key].get("odt_air_ppb")
        if odt is not None:
            return float(odt)
    return None


def get_odt_air_profiles(profiles, matched_key):
    """Get ODT from PROFILES (odt field or odt_air_ppb)."""
    if matched_key and matched_key in profiles:
        odt = profiles[matched_key].get("odt_air_ppb") or profiles[matched_key].get("odt")
        if odt is not None:
            return float(odt)
    return None


def get_odt_air_odtdata(odt_data, matched_key):
    """Get ODT air from ODT_DATA."""
    if matched_key and matched_key in odt_data:
        odt = odt_data[matched_key].get("odt_air")
        if odt is not None:
            return float(odt)
    return None


def get_odt_eth_yaml(yaml_entries, matched_key):
    if matched_key and matched_key in yaml_entries:
        odt = yaml_entries[matched_key].get("odt_eth_ppm")
        if odt is not None:
            return float(odt)
    return None


def get_odt_eth_profiles(profiles, matched_key):
    """ODT ethanol from profiles."""
    if matched_key and matched_key in profiles:
        p = profiles[matched_key]
        odt = p.get("odt_eth_ppm") or p.get("odt_ppm")
        if odt is not None:
            return float(odt)
    return None


def get_odt_eth_odtdata(odt_data, matched_key):
    if matched_key and matched_key in odt_data:
        odt = odt_data[matched_key].get("odt_eth")
        if odt is not None:
            return float(odt)
    return None


def vp_diff_pct(v1, v2):
    """Return absolute percentage difference between two VP values.
    Returns None if both None, 0 if both 0, percentage otherwise.
    """
    if v1 is None or v2 is None:
        return None
    if v1 == 0 and v2 == 0:
        return 0.0
    if v1 == 0 or v2 == 0:
        return 100.0
    return abs(v1 - v2) / max(abs(v1), abs(v2)) * 100


# ── Main ──
def main():
    print("=== Consistency Audit ===")
    print(f"Started: {datetime.now().isoformat()}")

    # Parse all sources
    print("Parsing inventory.txt...")
    inventory = parse_inventory()
    print(f"  Found {len(inventory)} materials in inventory")

    print("Loading YAML files...")
    yaml_entries, yaml_aliases = build_yaml_lookup()
    print(f"  Found {len(yaml_entries)} YAML entries with {len(yaml_aliases)} aliases")

    print("Loading PROFILES...")
    profiles = build_profiles_lookup()
    print(f"  Found {len(profiles)} profile entries")

    print("Loading ODT_DATA...")
    odt_data = build_odt_lookup()
    print(f"  Found {len(odt_data)} ODT entries")

    # Cross-reference
    results = []
    truths = []
    truth_counter = 0

    # Process each inventory material
    for idx, mat in enumerate(inventory):
        name = mat["inventory_name"]
        row = {
            "material": name,
            "category": mat["category"],
            "depleted": mat["depleted"],
            "in_inventory": True,
            "in_yaml": False,
            "in_profiles": False,
            "in_odt": False,
            "yaml_key": "",
            "profiles_key": "",
            "odt_key": "",
            "vp_match": "",
            "odt_match": "",
            "name_match": "",
            "notes": "",
            "truth_id": "",
        }

        # Check YAML
        y_key, y_type = find_in_yaml(name, yaml_entries, yaml_aliases)
        if y_key:
            row["in_yaml"] = True
            row["yaml_key"] = y_key
            row["name_match"] = y_type

        # Check PROFILES
        p_key, p_type = find_in_profiles(name, profiles)
        if p_key:
            row["in_profiles"] = True
            row["profiles_key"] = p_key
            if not row["name_match"]:
                row["name_match"] = p_type

        # Check ODT_DATA
        o_key, o_type = find_in_odt(name, odt_data)
        if o_key:
            row["in_odt"] = True
            row["odt_key"] = o_key

        # VP comparison (YAML vs PROFILES)
        vp_y = get_vp_yaml(yaml_entries, y_key) if y_key else None
        vp_p = get_vp_profiles(profiles, p_key) if p_key else None

        if vp_y is not None and vp_p is not None:
            diff = vp_diff_pct(vp_y, vp_p)
            if diff is not None:
                if diff <= 10:
                    row["vp_match"] = "PASS"
                elif diff <= 30:
                    row["vp_match"] = f"MINOR ({diff:.1f}%)"
                else:
                    row["vp_match"] = f"FAIL ({diff:.1f}%)"
            else:
                row["vp_match"] = "N/A"
        elif vp_y is not None and vp_p is None:
            row["vp_match"] = "PROFILE_MISSING"
        elif vp_y is None and vp_p is not None:
            row["vp_match"] = "YAML_MISSING"
        else:
            row["vp_match"] = "BOTH_MISSING"

        # ODT comparison (YAML vs ODT_DATA on odt_air)
        odt_y = get_odt_air_yaml(yaml_entries, y_key) if y_key else None
        odt_o = get_odt_air_odtdata(odt_data, o_key) if o_key else None

        if odt_y is not None and odt_o is not None:
            diff = vp_diff_pct(odt_y, odt_o)
            if diff is not None:
                if diff <= 20:
                    row["odt_match"] = "PASS"
                elif diff <= 50:
                    row["odt_match"] = f"MINOR ({diff:.1f}%)"
                else:
                    row["odt_match"] = f"FAIL ({diff:.1f}%)"
            else:
                row["odt_match"] = "N/A"
        elif odt_y is not None and odt_o is None:
            row["odt_match"] = "ODT_MISSING"
        elif odt_y is None and odt_o is not None:
            row["odt_match"] = "YAML_MISSING"
        else:
            row["odt_match"] = "BOTH_MISSING"

        # Determine match quality
        sources_found = sum([row["in_yaml"], row["in_profiles"], row["in_odt"]])

        if sources_found == 3:
            row["notes"] = "FULL_COVERAGE"
        elif sources_found == 2:
            missing = []
            if not row["in_yaml"]:
                missing.append("YAML")
            if not row["in_profiles"]:
                missing.append("PROFILES")
            if not row["in_odt"]:
                missing.append("ODT")
            row["notes"] = f"MISSING: {','.join(missing)}"
        elif sources_found == 1:
            missing = []
            if not row["in_yaml"]:
                missing.append("YAML")
            if not row["in_profiles"]:
                missing.append("PROFILES")
            if not row["in_odt"]:
                missing.append("ODT")
            row["notes"] = f"MISSING: {','.join(missing)}"
        else:  # 0
            row["notes"] = "NOT_FOUND_IN_ANY_SOURCE"

        # Generate truth entries for fully verified materials
        if (
            sources_found == 3
            and row["vp_match"] == "PASS"
            and row["odt_match"] in ("PASS", "N/A", "")
        ):
            truth_counter += 1
            tid = f"consistency_{truth_counter:04d}"
            row["truth_id"] = tid
            truths.append(
                {
                    "id": tid,
                    "description": f"Material '{name}' verified consistent across all 4 data sources: inventory.txt, YAML ({y_key}), PROFILES ({p_key}), ODT_DATA ({o_key})",
                    "literature_source": "internal cross-ref",
                    "codebase_evidence": f"inventory={name}, YAML(canonical={y_key}, VP={vp_y}, ODT_air={odt_y}), PROFILES(key={p_key}, VP={vp_p}), ODT_DATA(key={o_key})",
                    "crosscheck_sources": [
                        "inventory.txt",
                        "data/materials/*.yaml",
                        "engine/ingredient_intelligence.py",
                        "engine/odor_thresholds.py",
                    ],
                    "vp_consistency": row["vp_match"],
                    "odt_consistency": row["odt_match"],
                    "verified_at": "2026-07-21",
                }
            )

        results.append(row)

    # ── Write CSV ──
    csv_path = ROOT / ".omo/evidence/consistency_audit.csv"
    fieldnames = [
        "material",
        "category",
        "depleted",
        "in_inventory",
        "in_yaml",
        "in_profiles",
        "in_odt",
        "yaml_key",
        "profiles_key",
        "odt_key",
        "vp_match",
        "odt_match",
        "name_match",
        "notes",
        "truth_id",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    print(f"\nWrote {len(results)} rows to {csv_path}")

    # ── Write truths JSONL ──
    truths_path = ROOT / ".omo/evidence/truths.jsonl"
    with open(truths_path, "a", encoding="utf-8") as f:
        for t in truths:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"Wrote {len(truths)} truth entries to {truths_path}")

    # ── Summary ──
    found_all = sum(1 for r in results if r["in_yaml"] and r["in_profiles"] and r["in_odt"])
    found_none = sum(
        1 for r in results if not r["in_yaml"] and not r["in_profiles"] and not r["in_odt"]
    )
    vp_pass = sum(1 for r in results if r["vp_match"] == "PASS")
    vp_fail = sum(1 for r in results if r["vp_match"] and r["vp_match"].startswith("FAIL"))
    vp_minor = sum(1 for r in results if r["vp_match"] and r["vp_match"].startswith("MINOR"))
    odt_pass = sum(1 for r in results if r["odt_match"] == "PASS")
    odt_fail = sum(1 for r in results if r["odt_match"] and r["odt_match"].startswith("FAIL"))
    odt_minor = sum(1 for r in results if r["odt_match"] and r["odt_match"].startswith("MINOR"))

    print("\n=== SUMMARY ===")
    print(f"Total inventory materials: {len(results)}")
    print(f"Found in all 3 sources: {found_all}")
    print(f"Found in none: {found_none}")
    print(f"Found in YAML: {sum(1 for r in results if r['in_yaml'])}")
    print(f"Found in PROFILES: {sum(1 for r in results if r['in_profiles'])}")
    print(f"Found in ODT_DATA: {sum(1 for r in results if r['in_odt'])}")
    print(f"VP PASS: {vp_pass}, MINOR: {vp_minor}, FAIL: {vp_fail}")
    print(f"ODT PASS: {odt_pass}, MINOR: {odt_minor}, FAIL: {odt_fail}")
    print(f"Truth entries: {len(truths)}")
    print(f"\nFinished: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
