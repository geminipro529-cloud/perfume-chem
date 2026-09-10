#!/usr/bin/env python3
"""Scan full inventory + profiles → show everything organized by category.
Purpose: eliminate blind spots by systematically reviewing every material
before composing a formula.

Usage:
    python scripts/scan_inventory.py                           # full scan
    python scripts/scan_inventory.py --quick                   # name-only scan
    python scripts/scan_inventory.py --blind <formula.md>      # check formula against inventory
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import parse_inventory
from engine.odor_thresholds import ODT_DATA


def get_odt(material: str) -> dict:
    key = material.lower().strip().split("  #")[0].strip()
    for odt_key, data in ODT_DATA.items():
        if odt_key.lower() == key:
            return data
    for odt_key, data in ODT_DATA.items():
        if key in odt_key.lower() or odt_key.lower() in key:
            return data
    return {}


def scan(quick: bool = False) -> None:
    inv = parse_inventory()
    mats = sorted([m.name for m in inv], key=lambda x: x.lower())

    category_map = [
        ("SOLVENTS / CARRIERS", ["solvent", "ethanol", "dpg", "dep", "ipm", "tec", "myristic"]),
        (
            "CITRUS / TOP",
            [
                "citrus",
                "bergamot",
                "grapefruit",
                "cedrat",
                "mandarin",
                "orange",
                "lemon",
                "lime",
                "citronellal",
                "citral",
                "limonene",
                "linalool",
                "linalyl",
                "petitgrain",
                "apritone",
                "pamzest",
                "methyl pamplemousse",
                "aldehyd",
                "hexyl acetate",
                "lemonile",
                "terpinyl",
            ],
        ),
        (
            "GREEN / FRESH / MARINE",
            [
                "dihydromyrcenol",
                "cis-3",
                "verdox",
                "galbanum",
                "cyclamen",
                "scentenal",
                "calone",
                "floralozone",
                "undecavertol",
                "dynascone",
                "parmavert",
                "leafovert",
                "triplal",
                "geosmin",
            ],
        ),
        (
            "FLORAL",
            [
                "hedione",
                "jasmone",
                "jessemal",
                "hydroxycitronellal",
                "phenethyl",
                "cinnamyl",
                "florol",
                "peonile",
                "aurantiol",
                "geraniol",
                "citronellol",
                "rhodinol",
                "rose oxide",
                "benzyl salicylate",
                "benzyl benzoate",
                "benzyl acetate",
                "indole",
                "bourgeonal",
                "freesia",
                "lilyreal",
                "lilial",
                "cyclimal",
                "nympheal",
                "helional",
                "ylang",
                "champaca",
                "methyl benzoate",
                "p-cresyl",
                "paradisamide",
                "cis jasmone",
                "methyl salicylate",
                "methyl anthranilate",
                "damascone",
                "damascenone",
                "damascol",
                "heliotrop",
                "aca",
                "pedmc",
                "farnesol",
                "mayol",
                "oranger crystals",
                "nerol",
                "nerolin",
                "coumarin",
            ],
        ),
        (
            "IRIS / VIOLET",
            ["irone", "ionone", "irotyl", "orivone", "ultralia", "iris", "orris", "carrot seed"],
        ),
        (
            "WOODS / AMBER / STRUCTURE",
            [
                "iso e super",
                "cashmeran",
                "polysantol",
                "cedramber",
                "ambermax",
                "amber core",
                "ebanol",
                "sandalore",
                "vetival",
                "vertofix",
                "suederal",
                "javanol",
                "amberwood",
                "ambrox",
                "ambrofix",
                "timberol",
                "koavone",
                "cedarwood",
                "vetiver",
                "nagarmortha",
                "vetikon",
                "clearwood",
                "norlimbanol",
                "azarbre",
                "kephalis",
                "evernyl",
            ],
        ),
        (
            "MUSKS",
            [
                "galaxolide",
                "tonalide",
                "habanolide",
                "zenolide",
                "romandolide",
                "exaltolide",
                "macrolide",
                "ambrettolide",
                "musk",
                "ethylene brassylate",
            ],
        ),
        (
            "SWEET / GOURMAND / BALSAMIC",
            [
                "ethyl maltol",
                "vanillin",
                "maple lactone",
                "raspberry ketone",
                "benzoin",
                "anisaldehyde",
                "decalactone",
                "undecylactone",
                "allyl amyl",
            ],
        ),
        (
            "LEATHER / SMOKY / PHENOLIC",
            ["tobacco", "isobutyl quinoline", "birch tar", "costus", "guaiacol", "skatole"],
        ),
        (
            "SPICE / AROMATIC",
            [
                "black pepper",
                "cardamom",
                "ethyl safranate",
                "eugenol",
                "isoeugenol",
                "cinnamaldehyde",
                "lavender",
                "spike lavender",
                "beta-pinene",
                "pine eo",
                "juniper",
                "rosemary",
                "clary sage",
                "patchouli",
                "olibanum",
            ],
        ),
        (
            "ACCORD BASES / OTHER",
            [
                "jasmine fo",
                "leather fo",
                "tonka bean fo",
                "sandalwood fo",
                "melonal",
                "dbca",
                "methyl nonyl ketone",
            ],
        ),
    ]

    print(f"\n{'=' * 70}")
    print(f"  INVENTORY — {len(mats)} materials")
    print(f"{'=' * 70}")

    for cat_name, keywords in category_map:
        cat_mats = [m for m in mats if any(kw in m.lower() for kw in keywords)]
        if not cat_mats:
            continue

        print(f"\n── {cat_name} ({len(cat_mats)}) ──")

        for m in cat_mats:
            display = m.split("  #")[0].strip()
            if quick:
                print(f"  {display}")
                continue

            profile = get_profile(display)
            odt = get_odt(m)

            note = profile.note if profile else "—"
            role = profile.role if profile else "—"
            odt_val = odt.get("odt_air", "—")
            vfy = odt.get("vfy", "")
            vfy_str = f" [{vfy}]" if vfy else ""

            char = profile.numeric_character if profile else None
            char_str = (
                " | ".join(f"{k}={v}" for k, v in sorted(char.items(), key=lambda x: -x[1])[:4])
                if char
                else (
                    f"character={profile.character_status.value}"
                    if profile
                    else ""
                )
            )

            syns = profile.synergies if profile and profile.synergies else []
            syn_str = f"  ⟷ {', '.join(syns[:4])}" if syns else ""

            mw = profile.mw if profile else ""
            vp = profile.vp if profile else ""

            phys = ""
            if mw or vp:
                phys = f"  MW={mw} VP={vp}"

            # Mark if ODT data is missing
            missing = " ⚠️ NO ODT" if odt_val == "—" else ""

            print(
                f"  {display:35s} {note:5s} {role:12s} ODT={str(odt_val):>8s} ppb{vfy_str}{missing}"
            )
            if char_str:
                print(f"  {'':35s} {char_str}")
            if syn_str:
                print(f"  {'':35s}{syn_str}")
            if phys:
                print(f"  {'':35s}{phys}")

    print(f"\n{'=' * 70}")
    print(f"  DONE — {len(mats)} materials")
    print(f"{'=' * 70}\n")


def blind_spot_check(formula_path: str) -> None:
    from scripts.verify_formula_workflow import parse_formula_markdown

    inv = parse_inventory()
    inv_names = {m.name.lower().split("  #")[0].strip() for m in inv}

    formulas = parse_formula_markdown(Path(formula_path))
    if not formulas:
        print("No formulas parsed.")
        return

    for f in formulas:
        ings = f.get("ingredients_ul", {})
        print(f"\n{'=' * 60}")
        print(f"  Checking: {Path(formula_path).name}")
        print(f"{'=' * 60}")
        for mat in ings:
            mat_clean = mat.lower().strip()
            found = mat_clean in inv_names
            if not found:
                found = any(mat_clean in n for n in inv_names)
            status = "✅" if found else "❌ NOT IN INVENTORY"
            print(f"  {status} {mat}")


if __name__ == "__main__":
    if "--blind" in sys.argv:
        idx = sys.argv.index("--blind") + 1
        blind_spot_check(sys.argv[idx])
    elif "--quick" in sys.argv:
        scan(quick=True)
    else:
        scan()
