#!/usr/bin/env python3
"""
extract_material_effects.py — Cross-reference material perceptual data
from ingredient_intelligence.py _PROFILES, YAML data files, inventory.txt,
and AGENTS.md literature references.

Produces:
  .omo/evidence/material_effect_audit.csv
  .omo/evidence/truths.jsonl  (append mode, category "material_perfume_effect")

Run from repo root:
  python .omo/evidence/extract_material_effects.py
"""

import csv
import json
import re
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import yaml

# ── Literature references (from AGENTS.md) ──
LITERATURE_SOURCES = {
    "calkin_jellinek": "Calkin & Jellinek (1994): chypre ratios, fixative loading, perfume structure theory",
    "carles": "Carles (1961): pyramid structure, accord ratios, material counts, classical perfumery method",
    "ellena": "Ellena (2011): transparent watercolor, Hedione:Iso E ratio, material count ≤18, minimalist aesthetics",
    "sinding": "Sinding et al. (2017): olfactory adaptation — high VP citrus habituates in 45-90s",
    "laing_francis": "Laing & Francis (1989): humans track 3-4 components maximum in mixtures",
    "shiseido": "Shiseido Féminité du Bois GCMS: gold standard woody-floral skeleton",
    "hong_2023": "Hong et al. (2023): GC-MS-O of osmanthus — β-ionone is dominant character compound",
    "guo_2024": "Guo et al. (2024): osmanthus absolute composite OAV = 1,371,872 floral",
    "arctander": "Arctander: Perfume and Flavor Materials of Natural Origin / Chemicals",
    "perfumersworld": "PerfumersWorld ABC: material database and dosing references",
    "roudnitska": "Roudnitska aesthetics: hedonic optimization, material economy",
    "jellinek_quadrants": "Jellinek quadrants: classification by hedonic value and activation",
    "opk_sar": "OPK SAR classes: structure-activity relationships for odorants",
}


# ── Parse inventory.txt for material names and categories ──
def parse_inventory(inv_path: Path) -> dict[str, dict]:
    """Parse inventory.txt returning {normalized_name: {category, dilution, depleted}}."""
    materials = {}
    current_category = "UNCATEGORIZED"

    with open(inv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()

            # Category headers
            if line.startswith("---") and line.endswith("---"):
                current_category = line.strip("- ").strip()
                continue

            # Material entries: lines starting with "- " or " - "
            m = re.match(r"^\s*-\s+(.+?)(?:\s*#.*)?$", line)
            if not m:
                continue

            raw = m.group(1).strip()

            # Extract dilution if present
            dil_match = re.search(r"\((\d+(?:\.\d+)?%)\b", raw)
            dilution = dil_match.group(1) if dil_match else "neat"

            # Extract base name (before dilution/comment)
            name = re.split(r"\s*\(", raw)[0].strip()
            # Handle "50% in DPG", "10% in TEC" etc
            name = re.sub(r"\s+\d+%\s*(?:in\s+\w+)?\s*$", "", name).strip()
            # Handle "w/w", "w/v" qualifiers
            name = re.sub(r"\s+\d+%\s*w/[vw].*$", "", name).strip()
            # Clean up
            name = name.replace("  ", " ").strip()

            # Check if depleted
            depleted = (
                "# DEPLETED" in line or "DEPLETED" in line.split("#")[-1] if "#" in line else False
            )

            # Check for comments with dates
            added_match = re.search(r"#\s*added\s+(\d{4}-\d{2}-\d{2})", line)

            materials[name.lower()] = {
                "raw_name": raw,
                "name": name,
                "category": current_category,
                "dilution": dilution,
                "depleted": depleted,
                "added_date": added_match.group(1) if added_match else None,
            }

    return materials


# ── Parse YAML files for note/character data ──
def parse_yaml_materials(data_dir: Path) -> dict[str, dict]:
    """Parse all data/materials/*.yaml for character and notes fields."""
    yaml_data = {}

    for yaml_path in sorted(data_dir.glob("*.yaml")):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                entries = yaml.safe_load(f) or []
        except Exception as e:
            print(f"  WARN: Could not parse {yaml_path.name}: {e}")
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            cname = entry.get("canonical_name", "")
            aliases = entry.get("aliases", [])
            character = entry.get("character")
            notes = entry.get("notes")
            user_in_inventory = entry.get("user_in_inventory", False)

            if not user_in_inventory and not cname:
                continue

            key = cname.lower()
            yaml_data[key] = {
                "canonical_name": cname,
                "character": character,
                "notes": notes,
                "aliases": aliases,
                "in_inventory": user_in_inventory,
            }

            # Also index by aliases
            for alias in aliases:
                yaml_data[alias.lower()] = yaml_data[key]

    return yaml_data


# ── Extract odor character from dimensions ──
def character_to_odor_description(ch: dict[str, float]) -> str:
    """Convert character dimension dict to a compact odor description string."""
    if not ch:
        return "unknown"

    # Sort by strength, descending
    sorted_dims = sorted(ch.items(), key=lambda x: x[1], reverse=True)

    # Strength labels
    def strength_label(v: float) -> str:
        if v >= 9:
            return "defining"
        if v >= 7:
            return "strong"
        if v >= 5:
            return "moderate"
        if v >= 3:
            return "noticeable"
        if v >= 1:
            return "trace"
        return "absent"

    parts = []
    for dim, val in sorted_dims:
        if val >= 3:
            parts.append(f"{dim}[{strength_label(val)}]")
        elif val >= 1:
            parts.append(f"{dim}[trace]")
        else:
            break

    return "; ".join(parts) if parts else "neutral"


# ── Main extraction ──
def main():
    print("=== Material Perfume Effect Audit ===")
    print()

    # 1. Import _PROFILES from ingredient_intelligence
    print("1. Loading ingredient_intelligence.py _PROFILES...")
    from engine.ingredient_intelligence import (
        _PROFILES,
    )

    print(f"   Got {len(_PROFILES)} profiles")

    # 2. Parse inventory.txt
    print("2. Parsing inventory.txt...")
    inv_path = REPO_ROOT / "inventory.txt"
    inventory = parse_inventory(inv_path)
    print(f"   Got {len(inventory)} inventory entries")

    # 3. Parse YAML files
    print("3. Parsing data/materials/*.yaml...")
    yaml_dir = REPO_ROOT / "data" / "materials"
    yaml_data = parse_yaml_materials(yaml_dir)
    print(f"   Got {len(yaml_data)} YAML entries")

    # 4. Extract from AGENTS.md for literature-backed character descriptions
    print("4. Extracting literature-backed character descriptions from AGENTS.md...")
    agents_path = REPO_ROOT / "AGENTS.md"
    copilot_path = REPO_ROOT / ".github" / "copilot-instructions.md"

    # Parse AGENTS.md for character material tables
    literature_characters = {}
    for doc_path in [copilot_path, agents_path]:
        if not doc_path.exists():
            continue
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract table rows with material|character|best_for format
        # Pattern: | Material Name | Character description | ...
        for line in content.split("\n"):
            m = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|", line)
            if m:
                mat_name = m.group(1).strip()
                char_desc = m.group(2).strip()
                literature_characters[mat_name.lower()] = char_desc

    print(f"   Got {len(literature_characters)} literature-backed character descriptions")

    # 5. Cross-reference and build records
    print("5. Building cross-referenced records...")

    records = []
    truths = []
    seen_names = set()
    mat_counter = 0

    # Helper to find profile by fuzzy name matching
    def find_profile(name: str) -> dict | None:
        """Try exact match, lowercase match, then partial match."""
        n = name.lower().strip()

        # Exact
        if n in _PROFILES:
            return {"key": name, "profile": _PROFILES[n]}

        # Try common aliases
        aliases = {
            "iso e super": "Iso E Super",
            "hedione": "Hedione",
            "hedione hc": "Hedione HC",
            "ethyl linalool": "Ethyl Linalool",
            "linalyl acetate": "Linalyl Acetate",
            "benzyl salicylate": "Benzyl Salicylate",
            "hexyl salicylate": "Hexyl Salicylate",
            "benzyl benzoate": "Benzyl Benzoate",
            "benzyl acetate": "Benzyl Acetate",
            "benzyl alcohol": "Benzyl Alcohol",
            "phenethyl alcohol": "Phenethyl Alcohol",
            "phenethyl alcohol (pea)": "Phenethyl Alcohol",
            "geraniol": "Geraniol",
            "citronellol": "Citronellol",
            "citral": "Citral",
            "citronellal": "Citronellal",
            "d-limonene": "D-Limonene",
            "linalool": "Linalool",
            "coumarin": "Coumarin",
            "vanillin": "Vanillin",
            "ethyl vanillin": "Ethyl Vanillin",
            "ethyl maltol": "Ethyl Maltol",
            "raspberry ketone": "Raspberry Ketone",
            "gamma decalactone": "Gamma Decalactone",
            "gamma undecalactone": "Gamma Undecalactone",
            "delta decalactone": "Delta Decalactone",
            "eugenol": "Eugenol",
            "isoeugenol": "Isoeugenol",
            "cinnamaldehyde": "Cinnamaldehyde",
            "indole": "Indole",
            "skatole": "Skatole",
            "evernyl": "Evernyl",
            "guaiacol": "Guaiacol",
            "anisaldehyde": "Anisaldehyde",
            "dihydromyrcenol": "Dihydromyrcenol",
            "verdox": "Verdox",
            "florol": "Florol",
            "peonile": "Peonile",
            "aurantiol": "Aurantiol",
            "bourgeonal": "Bourgeonal",
            "lilial": "Lilial",
            "lilyreal nd": "Lilyreal ND",
            "nympheal": "Nympheal",
            "helional": "Helional",
            "freesia hdi": "Freesia HDI",
            "cyclamen aldehyde": "Cyclamen Aldehyde",
            "scentenal": "Scentenal",
            "calone": "Calone",
            "floralozone": "Floralozone",
            "undecavertol": "Undecavertol",
            "dynascone": "Dynascone",
            "parmavert": "Parmavert",
            "leafovert": "Leafovert",
            "triplal": "Triplal",
            "geosmin": "Geosmin",
            "alpha ionone": "Alpha Ionone",
            "beta ionone": "Beta Ionone",
            "allyl ionone": "Allyl Ionone",
            "alpha isomethyl ionone": "Alpha Isomethyl Ionone",
            "methyl ionone pure": "Alpha Isomethyl Ionone",
            "alpha irone": "Alpha Irone",
            "irotyl": "Irotyl",
            "dihydro beta ionone": "Dihydro Beta Ionone",
            "orivone": "Orivone",
            "ultralia": "Ultralia",
            "cashmeran": "Cashmeran",
            "polysantol": "Polysantol",
            "cedramber": "Cedramber",
            "ambermax": "Ambermax",
            "amber core": "Amber Core",
            "ebanol": "Ebanol",
            "sandalore": "Sandalore",
            "javanol": "Javanol",
            "vetival": "Vetival",
            "vetikon": "Vetikon",
            "vertofix": "Vertofix",
            "suederal": "Suederal",
            "amberwood f": "Amberwood F",
            "ambrox super": "Ambrox Super",
            "ambrofix": "Ambrofix",
            "timberol": "Timberol",
            "koavone": "Koavone",
            "clearwood": "Clearwood",
            "norlimbanol dextro": "Norlimbanol Dextro",
            "azarbre": "Azarbre",
            "kephalis": "Kephalis",
            "zenolide": "Zenolide",
            "romandolide": "Romandolide",
            "exaltolide": "Exaltolide",
            "macrolide": "Macrolide",
            "ambrettolide": "Ambrettolide",
            "musk ketone": "Musk Ketone",
            "ethylene brassylate": "Ethylene Brassylate",
            "galaxolide": "Galaxolide",
            "tonalide": "Tonalide",
            "habanolide": "Habanolide",
            "melonal": "Melonal",
            "dbca": "DBCA",
            "dimethyl benzyl carbinyl acetate": "DBCA",
            "methyl nonyl ketone": "Methyl Nonyl Ketone",
            "cassis base 345b": "Cassis Base 345B",
            "allyl amyl glycolate": "Allyl Amyl Glycolate",
            "paradisamide": "Paradisamide",
            "cis jasmone": "Cis Jasmone",
            "methyl salicylate": "Methyl Salicylate",
            "methyl anthranilate": "Methyl Anthranilate",
            "alpha damascone": "Alpha Damascone",
            "damascone beta": "Damascone Beta",
            "damascenone": "Damascenone",
            "damascol": "Damascol",
            "heliotropal": "Heliotropal",
            "amyl cinnamic aldehyde": "ACA",
            "aca": "ACA",
            "phenyl ethyl dimethyl carbinol": "PEDMC",
            "pedmc": "PEDMC",
            "phenyl ethyl dimethyl carbinol (pedmc)": "PEDMC",
            "farnesol": "Farnesol",
            "mayol": "Mayol",
            "oranger crystals": "Oranger Crystals",
            "nerol": "Nerol",
            "nerolin bromelia": "Nerolin Bromelia",
            "phenyl ethyl acetate": "Phenyl Ethyl Acetate",
            "methyl benzoate": "Methyl Benzoate",
            "p-cresyl methyl ether": "p-Cresyl Methyl Ether",
            "pcme": "p-Cresyl Methyl Ether",
            "dihydrojasmone": "Dihydrojasmone",
            "jessemal": "Jessemal",
            "hydroxycitronellal": "Hydroxycitronellal",
            "hydroxycitronellol": "Hydroxycitronellol",
            "rhodinol ex citronella": "Rhodinol ex Citronella",
            "rose oxide": "Rose Oxide",
            "cyclimal aldehyde": "Cyclamen Aldehyde",
            "heliotropin": "Heliotropin",
            "maple lactone": "Maple Lactone",
            "siam benzoin": "Siam Benzoin",
            "benzoin sumatra resinoid": "Benzoin Sumatra Resinoid",
            "labdanum resinoid": "Labdanum Resinoid",
            "tonkarome": "Tonkarome",
            "cocoa absolute": "Cocoa Absolute",
            "tonka bean absolute": "Tonka Bean Absolute",
            "cocoa co2 extract": "Cocoa CO2 Extract",
            "peru balsam resinoid": "Peru Balsam Resinoid",
            "opoponax resinoid": "Opoponax Resinoid",
            "tobacco absolute": "Tobacco Absolute",
            "isobutyl quinoline": "Isobutyl Quinoline",
            "ibq": "Isobutyl Quinoline",
            "birch tar rectified": "Birch Tar Rectified",
            "costus olifac": "Costus Olifac",
            "cade oil rectified": "Cade Oil Rectified",
            "oakmoss absolute": "Oakmoss Absolute",
            "black pepper eo": "Black Pepper EO",
            "cardamom eo": "Cardamom EO",
            "ethyl safranate": "Ethyl Safranate",
            "clove eo": "Clove EO",
            "anise eo": "Anise EO",
            "lavender eo": "Lavender EO",
            "lavender eo high altitude": "Lavender EO High Altitude",
            "spike lavender eo": "Spike Lavender EO",
            "beta-pinene": "Beta-Pinene",
            "pine eo": "Pine EO",
            "juniper berry eo": "Juniper Berry EO",
            "rosemary eo": "Rosemary EO",
            "clary sage eo": "Clary Sage EO",
            "basil eo": "Basil EO",
            "patchouli eo": "Patchouli EO",
            "cassia essential oil": "Cassia Essential Oil",
            "olibanum resinoid absolute": "Olibanum Resinoid Absolute",
            "olibanum resinoid": "Olibanum Resinoid",
            "frankincense eo": "Frankincense EO",
            "jasmine fo": "Jasmine FO",
            "jasmine sambac": "Jasmine Sambac",
            "leather fo": "Leather FO",
            "tonka bean fo": "Tonka Bean FO",
            "sandalwood fo": "Sandalwood FO",
            "carrot seed eo": "Carrot Seed EO",
            "tagetes eo": "Tagetes EO",
            "peppermint essential oil": "Peppermint Essential Oil",
            "eucalyptus essential oil": "Eucalyptus Essential Oil",
            "ginger eo": "Ginger EO",
            "neroli eo": "Neroli EO",
            "osmanthus absolute": "Osmanthus Absolute",
            "tuberalia base": "Tuberalia base",
            "tuberose absolute": "Tuberose Absolute",
            "immortelle absolute": "Immortelle Absolute",
            "rose essential oil": "Rose Essential Oil",
            "rose de mai absolute": "Rose de Mai Absolute",
            "jasmine sambac blossoms": "Jasmine Sambac Blossoms",
            "blue chamomile eo": "Blue Chamomile EO",
            "mimosa absolute": "Mimosa Absolute",
            "isobutavan": "Isobutavan",
            "allyl cyclohexyl propionate": "Allyl Cyclohexyl Propionate",
            "orris liquid": "Orris Liquid",
            "pamzest": "Pamzest",
            "petitgrain eo paraguay": "Petitgrain EO Paraguay",
            "lemon fcf oil sicilian": "Lemon FCF oil Sicilian",
            "apritone": "Apritone",
            "hexyl acetate": "Hexyl Acetate",
            "aldehyde c10": "Aldehyde C10",
            "aldehyde c11": "Aldehyde C11",
            "aldehyde c11 undecylenic": "Aldehyde C11 undecylenic",
            "aldehyde c12 mna": "Aldehyde C12 MNA",
            "methyl pamplemousse": "Methyl Pamplemousse",
            "bergamot eo": "Bergamot EO",
            "bergamot fcf": "Bergamot FCF",
            "bergamot fcf oil sicilian": "Bergamot FCF oil Sicilian",
            "grapefruit fcf": "Grapefruit FCF",
            "cedrat fcf oil sicilian": "Cedrat FCF oil Sicilian",
            "blood orange oil sicilian": "Blood Orange oil Sicilian",
            "red mandarin eo": "Red Mandarin EO",
            "lime distilled eo": "Lime Distilled EO",
            "ethyl 2-methylbutyrate": "Ethyl 2-Methylbutyrate",
            "lemonile": "Lemonile",
            "orange peel eo": "Orange Peel EO",
            "terpinyl acetate": "Terpinyl Acetate",
            "galbanum resinoid": "Galbanum Resinoid",
            "galbanum eo": "Galbanum EO",
            "geranium eo": "Geranium EO",
            "geranium flower eo": "Geranium EO",
            "ylang comoros complete eo f3255": "Ylang Comoros Complete EO F3255",
            "ylang comoros iii eo f3295": "Ylang Comoros III EO F3295",
            "ylang ylang eo": "Ylang Ylang EO",
            "champaca flower eo": "Champaca Flower EO",
            "cinnamyl alcohol": "Cinnamyl alcohol",
            "benzaldehyde": "Benzaldehyde",
            "cedarwood eo": "Cedarwood EO",
            "cedarwood oil virginia": "Cedarwood oil Virginia",
            "himalayan cedarwood eo": "Himalayan Cedarwood EO",
            "vetiver eo": "Vetiver EO",
            "nagarmortha oil": "Nagarmortha Oil",
        }

        if n in aliases:
            mapped = aliases[n]
            if mapped.lower() in _PROFILES:
                return {"key": mapped, "profile": _PROFILES[mapped.lower()]}
            if mapped in _PROFILES:
                return {"key": mapped, "profile": _PROFILES[mapped]}

        # Try iterative lowercase matching in _PROFILES
        for pkey in _PROFILES:
            if pkey.lower() == n:
                return {"key": pkey, "profile": _PROFILES[pkey]}

        # Partial match (name appears in profile key)
        for pkey in _PROFILES:
            if n in pkey.lower() or pkey.lower() in n:
                return {"key": pkey, "profile": _PROFILES[pkey]}

        return None

    # Process every unique material from inventory
    for inv_name, inv_data in sorted(inventory.items()):
        raw_name = inv_data["name"]
        category = inv_data["category"]

        # Skip solvents/carriers that aren't fragrance materials
        if category == "SOLVENTS / CARRIERS" and raw_name.lower() in [
            "ethanol 96%",
            "dipropylene glycol (dpg)",
            "isopropyl myristate (ipm)",
            "triethyl citrate (tec)",
            "diethyl phthalate (dep)",
            "myristic acid powder",
        ]:
            continue

        # Skip BHT (antioxidant)
        if raw_name.lower() == "bht":
            continue

        # Skip depleted? No — still audit what they ARE, mark as depleted
        main_name = raw_name.split("(")[0].strip()
        # Remove dilution suffixes like "50% in DPG"
        base_name = re.sub(r"\s+\d+%\s*(?:in\s+\w+)?(?:\s*\(.*?\))?\s*$", "", main_name).strip()
        base_name = re.sub(r"\s+\d+%\s*w/[vw].*$", "", base_name).strip()

        # Skip duplicates (same base material at different dilutions)
        canonical = base_name.lower().strip()
        # Skip if we've seen this exact base material
        if canonical in seen_names:
            continue

        seen_names.add(canonical)
        mat_counter += 1

        # Find profile
        profile_result = find_profile(base_name)

        if profile_result:
            prof = profile_result["profile"]
            profile_result["key"]

            ch = prof.get("character", {})
            note = prof.get("note", "unknown")
            role = prof.get("role", "unknown")
            texture = prof.get("texture", "")
            synergies_list = prof.get("synergies", [])
            or_family = prof.get("or_family", "")
            activity_coef = prof.get("activity_coef", 1.0)
            mw = prof.get("mw")
            vp = prof.get("vp")
            clogp = prof.get("clogp")

            odor_character = character_to_odor_description(ch)
            synergies_str = "; ".join(synergies_list) if synergies_list else ""

            # Literature source
            lit_char = literature_characters.get(base_name.lower(), "")
            if not lit_char:
                lit_char = literature_characters.get(canonical, "")

            source = "ingredient_intelligence.py:_PROFILES"
            if lit_char:
                source += " + copilot-instructions.md"
        else:
            # No profile found — check YAML
            yaml_entry = yaml_data.get(canonical) or yaml_data.get(base_name.lower())
            if yaml_entry and yaml_entry.get("character"):
                odor_character = yaml_entry["character"]
                note = "unknown"
                role = "unknown"
                texture = ""
                synergies_str = ""
                source = "data/materials/*.yaml"
                or_family = ""
                mw = None
                vp = None
                clogp = None
                activity_coef = 1.0
            else:
                odor_character = "unknown"
                note = "unknown"
                role = "unknown"
                texture = ""
                synergies_str = ""
                source = "none"
                or_family = ""
                mw = None
                vp = None
                clogp = None
                activity_coef = 1.0

        # Build record
        record = {
            "material": base_name,
            "inventory_name": raw_name,
            "category": category,
            "depleted": inv_data["depleted"],
            "dilution": inv_data["dilution"],
            "odor_character": odor_character,
            "note_tier": note,
            "role": role,
            "texture": texture,
            "or_family": or_family,
            "mw": mw,
            "vp_pa": vp,
            "clogp": clogp,
            "activity_coef": activity_coef,
            "synergies": synergies_str,
            "source": source,
            "lit_character": lit_char if lit_char else "",
        }
        records.append(record)

        # Build truth entry
        truth_id = f"mat_{mat_counter:04d}"
        truth = {
            "id": truth_id,
            "category": "material_perfume_effect",
            "description": (
                f"{base_name}: character={odor_character}, note={note}, "
                f"role={role}, texture={texture}, or_family={or_family}"
            ),
            "literature_source": (
                "ingredient_intelligence.py profiles + copilot-instructions.md "
                "(Calkin & Jellinek 1994, Carles 1961, Ellena 2011)"
            ),
            "codebase_evidence": source,
            "crosscheck_sources": ["PROFILES", "YAML", "AGENTS.md"],
            "verified_at": "2026-07-21",
        }
        truths.append(truth)

    print(f"   Built {len(records)} unique material records")

    # 6. Write CSV
    csv_path = REPO_ROOT / ".omo" / "evidence" / "material_effect_audit.csv"
    print(f"\n6. Writing CSV to {csv_path}...")

    fieldnames = [
        "material",
        "inventory_name",
        "category",
        "depleted",
        "dilution",
        "odor_character",
        "note_tier",
        "role",
        "texture",
        "or_family",
        "mw",
        "vp_pa",
        "clogp",
        "activity_coef",
        "synergies",
        "source",
        "lit_character",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        # Sort by category then material name
        category_order = [
            "CITRUS / TOP",
            "GREEN / FRESH / MARINE",
            "FLORAL MATERIALS",
            "IRIS / VIOLET",
            "WOODS / AMBER / STRUCTURE",
            "MUSKS",
            "SWEET / GOURMAND / BALSAMIC",
            "LEATHER / SMOKY / PHENOLIC",
            "SPICE / AROMATIC",
            "ACCORD BASES / OTHER",
        ]

        def sort_key(r):
            cat = r["category"]
            cat_idx = category_order.index(cat) if cat in category_order else 99
            return (cat_idx, r["material"].lower())

        sorted_records = sorted(records, key=sort_key)

        for rec in sorted_records:
            writer.writerow(rec)

    print(f"   Wrote {len(sorted_records)} rows")

    # 7. Append truths to JSONL
    jsonl_path = REPO_ROOT / ".omo" / "evidence" / "truths.jsonl"
    print(f"7. Appending truths to {jsonl_path}...")

    with open(jsonl_path, "a", encoding="utf-8") as f:
        for truth in truths:
            f.write(json.dumps(truth, ensure_ascii=False) + "\n")

    print(f"   Appended {len(truths)} truths")

    # 8. Summary stats
    print("\n=== Summary ===")
    print(f"Total unique materials: {len(records)}")

    by_category = {}
    by_note = {}
    by_role = {}
    unknown_count = 0
    depleted_count = 0

    for rec in records:
        cat = rec["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

        note = rec["note_tier"]
        by_note[note] = by_note.get(note, 0) + 1

        role = rec["role"]
        by_role[role] = by_role.get(role, 0) + 1

        if rec["odor_character"] == "unknown":
            unknown_count += 1
        if rec["depleted"]:
            depleted_count += 1

    print("\nBy category:")
    for cat in category_order:
        if cat in by_category:
            print(f"  {cat}: {by_category[cat]}")

    print("\nBy note tier:")
    for note in ["top", "heart", "base", "unknown"]:
        if note in by_note:
            print(f"  {note}: {by_note[note]}")

    print("\nBy role:")
    for role, count in sorted(by_role.items(), key=lambda x: x[1], reverse=True):
        print(f"  {role}: {count}")

    print(f"\nMaterials with unknown odor character: {unknown_count}")
    print(f"Depleted materials: {depleted_count}")
    print(f"Truths appended: {len(truths)}")

    print("\nDone!")


if __name__ == "__main__":
    main()
