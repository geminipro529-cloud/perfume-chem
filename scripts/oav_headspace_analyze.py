"""Reusable OAV + headspace + pipeline scoring for any formula.

Usage:
    python scripts/oav_headspace_analyze.py --formula-file formulas/Green_Patchouli_Cologne_V4_30mL_EDP.md
    python scripts/oav_headspace_analyze.py --formula-file formulas/Jasmin_dOrris_HenryJacques_30mL_EdP.md

Outputs:
    - Terminal report: ppm, OAV_simple, OAV_headspace per material
    - Airborne composition (% of headspace)
    - Character transfer efficiency (bottle vs air per group)
    - Pipeline scores (10 axes + geometric composite)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from scripts.verify_formula_workflow import parse_formula_markdown

P_ATM = 101325.0


def get_activity_coef(name: str) -> float:
    n = name.lower()
    if any(
        x in n
        for x in [
            "coumarin",
            "vanillin",
            "benzoin",
            "benzoate",
            "salicylate",
            "myristic",
            "quinoline",
        ]
    ):
        return 0.55
    if any(
        x in n
        for x in [
            "romandolide",
            "ethylene brass",
            "habanolide",
            "galaxolide",
            "ambrettolide",
            "exaltolide",
            "macrolide",
        ]
    ):
        return 0.50
    if any(x in n for x in ["acetate", "hedione", "lactone", "dihydrojasmone"]):
        return 1.75
    if any(
        x in n
        for x in [
            "limonene",
            "pinene",
            "bergamot",
            "grapefruit",
            "petitgrain",
            "black pepper",
            "cardamom",
            "lavender",
            "vetiver",
            "cedar",
            "patchouli",
            "clearwood",
            "evernyl",
            "azarbre",
            "frankincense",
            "nagarmortha",
            "olibanum",
        ]
    ):
        return 3.10
    if any(
        x in n
        for x in ["cedramber", "ambrox", "iso e super", "ethyl linalool", "damascone", "clary"]
    ):
        return 1.80
    return 1.50


def lookup_odt(name: str) -> float:
    nl = name.lower().strip().replace("**", "").strip("_")
    # Practical ODT map (known values from formula files + ODT_DATA)
    practical = {
        "patchouli eo": 10.0,
        "nagarmortha oil": 5.0,
        "clearwood": 5.0,
        "benzyl salicylate": 120.0,
        "ambrox super": 0.3,
        "vetiver eo": 5.0,
        "romandolide": 1.0,
        "cedramber": 1.0,
        "coumarin": 45.0,
        "evernyl": 0.5,
        "isobutyl quinoline": 0.5,
        "hedione": 25.0,
        "iso e super": 0.05,
        "lavender eo": 2.0,
        "geraniol": 40.0,
        "vanillin": 10.0,
        "dihydrojasmone": 0.75,
        "azarbre": 1.0,
        "frankincense eo": 2.0,
        "bergamot fcf oil sicilian": 15.0,
        "grapefruit fcf": 10.0,
        "petitgrain eo": 12.0,
        "black pepper eo": 3.0,
        "cardamom eo": 3.0,
        "cedrat fcf oil sicilian": 12.0,
        "lemon fcf oil sicilian": 8.0,
        "jasmin": 8.0,
        "benzyl acetate": 20.0,
        "cis-jasmone": 0.5,
        "sandalore": 10.0,
        "javanol": 3.0,
        "ebanol": 8.0,
        "vertofix": 1.0,
        "alpha irone": 0.1,
        "orivone": 3.0,
        "alpha isomethyl ionone": 5.0,
        "dihydro beta ionone": 5.0,
        "alpha ionone": 0.4,
        "ultralia": 0.3,
        "benzyl benzoate": 500.0,
        "cashmeran": 2.0,
        "ethylene brassylate": 1.0,
        "habanolide": 2.0,
        "galaxolide": 1.0,
        "heliotropal": 5.0,
        "phenethyl alcohol": 200.0,
        "peony flower": 3.0,
        "indole": 0.03,
        "gamma undecalactone": 1.0,
        "ambertteolide": 2.0,
        "exaltolide": 1.5,
        "ambrofix": 0.3,
        "siambenzoin": 50.0,
        "tobacco ftec": 10.0,
        "styrax": 10.0,
        "immortelle": 5.0,
        "eugenol": 2.0,
        "isoeugenol": 0.5,
        "methyl salicylate": 10.0,
        "peppermint": 5.0,
        "aldehyde c10": 2.0,
        "aldehyde c11": 1.0,
        "aldehyde c12 mna": 0.5,
        "aldehyde c11 undecylenic": 1.5,
        "undecavertol": 1.0,
        "dihydromyrcenol": 0.5,
        "floralozone": 0.3,
        "triplal": 0.01,
        "geosmin": 0.006,
    }
    for key, val in practical.items():
        if key in nl or nl in key:
            return val
    return 10.0


def compute(formula_data: list[tuple[str, float, float]]) -> dict[str, Any]:
    """Compute complete OAV + headspace analysis from formula data.

    Args:
        formula_data: list of (material_name, stock_uL, dilution_pct)
    """
    from engine.ingredient_intelligence import get_profile as _get_profile

    total_conc = sum(s for _, s, _ in formula_data)

    # Build mole data
    all_moles = 0.0
    materials: list[dict] = []
    for name, stock_ul, dil_pct in formula_data:
        dilution = dil_pct / 100.0
        active_ul = stock_ul * dilution
        prof = _get_profile(name)
        mw = prof.mw if prof else 200.0
        vp = prof.vp if prof else 0.01
        weight_g = active_ul / 1000.0
        moles = weight_g / mw if mw > 0 else 0
        all_moles += moles
        materials.append(
            {
                "name": name,
                "stock_ul": stock_ul,
                "active_ul": active_ul,
                "mw": mw,
                "vp": vp,
                "moles": moles,
            }
        )

    # Compute per-material OAV
    total_oav_s = 0.0
    total_oav_h = 0.0
    results: list[dict] = []
    for m in materials:
        conc_ppm = m["active_ul"] / 30000.0 * 1e6
        odt = lookup_odt(m["name"])
        oav_s = conc_ppm / odt if odt > 0 else 0

        mole_frac = m["moles"] / all_moles if all_moles > 0 else 0
        gamma = get_activity_coef(m["name"])
        p_i = gamma * mole_frac * m["vp"]
        oav_h = (p_i / P_ATM) * 1e9 / odt if odt > 0 else 0
        waste_ratio = oav_s / oav_h if oav_h > 0 else 99999

        total_oav_s += oav_s
        total_oav_h += oav_h

        results.append(
            {
                **m,
                "conc_ppm": round(conc_ppm, 0),
                "odt": round(odt, 2),
                "oav_simple": round(oav_s, 0),
                "gamma": round(gamma, 2),
                "mole_frac": round(mole_frac, 6),
                "p_i": round(p_i, 6),
                "oav_headspace": round(oav_h, 1),
                "waste_ratio": round(waste_ratio, 0),
            }
        )

    # Headspace composition
    headspace = sorted(
        [r for r in results if r["oav_headspace"] / total_oav_h > 0.005],
        key=lambda x: -x["oav_headspace"],
    )
    for r in headspace:
        r["air_pct"] = round(r["oav_headspace"] / total_oav_h * 100, 1)

    # Character groups
    groups = {
        "Dark earthy (patchouli family)": [
            "Patchouli EO",
            "Nagarmortha Oil",
            "Clearwood",
            "Vetiver EO",
        ],
        "Warm sweet (vanilla-amber)": [
            "Vanillin",
            "Coumarin",
            "Cedramber",
            "Frankincense EO",
            "Siam Benzoin",
            "Benzoin Resinoid",
        ],
        "Clean musk": [
            "Romandolide",
            "Galaxolide",
            "Ethylene Brassylate",
            "Habanolide",
            "Ambrettolide",
        ],
        "Herbal (lavender-geranium)": ["Lavender EO", "Geraniol", "Clary Sage EO", "Rosemary EO"],
        "Jasmine-floral body": [
            "Dihydrojasmone",
            "Hedione",
            "Hedione HC",
            "cis-Jasmone",
            "Jasmine Absolute",
            "Jasmine Sambac",
        ],
        "Spice-aromatic": ["Cardamom EO", "Black Pepper EO", "Azarbre", "Kephalis", "Timberol"],
        "Citrus top": [
            "Bergamot FCF oil Sicilian",
            "Grapefruit FCF",
            "Petitgrain EO",
            "Lemon FCF oil Sicilian",
            "Cedrat FCF oil Sicilian",
        ],
        "Fixatives": [
            "Benzyl Salicylate",
            "Ambrox Super",
            "Evernyl",
            "Isobutyl Quinoline",
            "Iso E Super",
            "Ambrofix",
            "Benzyl Benzoate",
            "Hexyl Salicylate",
        ],
    }
    char_transfer = []
    for group_name, mat_names in groups.items():
        bottle_ul = sum(m["stock_ul"] for m in materials if m["name"] in mat_names)
        air_oav = sum(r["oav_headspace"] for r in results if r["name"] in mat_names)
        char_transfer.append(
            {
                "group": group_name,
                "bottle_ul": bottle_ul,
                "bottle_pct": round(bottle_ul / total_conc * 100, 1),
                "air_oav": round(air_oav, 1),
                "air_pct": round(air_oav / total_oav_h * 100, 1) if total_oav_h else 0,
                "transfer_eff": round(air_oav / bottle_ul, 4) if bottle_ul else 0,
            }
        )
    char_transfer.sort(key=lambda x: -x["air_oav"])

    return {
        "total_conc": total_conc,
        "edp_pct": round(total_conc / 30000 * 100, 1),
        "n_materials": len(formula_data),
        "total_oav_simple": round(total_oav_s, 0),
        "total_oav_headspace": round(total_oav_h, 1),
        "materials": results,
        "headspace": headspace,
        "character_transfer": char_transfer,
    }


def print_report(result: dict[str, Any]) -> None:
    print("=" * 85)
    print("  OAV + HEADSPACE ANALYSIS")
    print(
        f"  {result['n_materials']} materials / {result['total_conc']} uL conc / {result['edp_pct']}% EdP"
    )
    print("=" * 85)

    print(
        f"\n{'Material':30s} {'uL':>5s} {'ppm':>7s} {'ODT':>6s} {'OAV_s':>9s} {'VP':>7s} {'OAV_h':>9s} {'wr':>6s}"
    )
    print("-" * 85)
    for r in result["materials"]:
        print(
            f"{r['name']:30s} {r['stock_ul']:5.0f} {r['conc_ppm']:7.0f} {r['odt']:6.2f} {r['oav_simple']:9.0f} {r['vp']:7.4f} {r['oav_headspace']:9.1f} {r['waste_ratio']:6.0f}:1"
        )

    print(f"\n  Simple OAV total: {result['total_oav_simple']:,.0f}")
    print(f"  Headspace OAV total: {result['total_oav_headspace']:,.0f}")

    print(f"\n{'=' * 50}")
    print("  AIRBORNE COMPOSITION")
    print(f"{'=' * 50}")
    for r in result["headspace"]:
        bar = "#" * min(int(r["air_pct"] / 2), 30)
        print(f"  {r['name']:30s} {r['air_pct']:5.1f}% ({r['oav_headspace']:5.0f}) {bar}")

    print(f"\n{'=' * 50}")
    print("  CHARACTER TRANSFER (bottle to air)")
    print(f"{'=' * 50}")
    print(f"{'Group':35s} {'uL':>6s} {'%bott':>6s} {'airOAV':>7s} {'%air':>6s} {'eff':>6s}")
    print("-" * 70)
    for c in result["character_transfer"]:
        print(
            f"{c['group']:35s} {c['bottle_ul']:6.0f} {c['bottle_pct']:5.1f}% {c['air_oav']:7.1f} {c['air_pct']:5.1f}% {c['transfer_eff']:6.4f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="OAV + headspace + pipeline analysis")
    parser.add_argument("--formula-file", required=True, help="Path to formula markdown file")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of terminal report")
    args = parser.parse_args()

    path = Path(args.formula_file)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    from engine.formula_metadata import parse_formula_metadata

    meta = parse_formula_metadata(str(path))
    if not meta.has_metadata() and not meta.is_unclaimed():
        print(
            "ERROR: Formula missing metadata block. Add metadata or set `**Reference claim:** none`.",
            file=sys.stderr,
        )
        return 1

    formulas = parse_formula_markdown(path)
    if not formulas:
        print(f"ERROR: No parseable formulas in {path}", file=sys.stderr)
        return 1

    for formula in formulas:
        name = formula["name"]
        body = formula.get("body", "")

        # Extract formula data from body
        formula_data = []
        for line in body.splitlines():
            match = re.match(
                r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
                line,
            )
            if not match:
                continue
            ingredient = match.group(2).replace("**", "").strip()
            if "ethanol" in ingredient.lower() or "total" in ingredient.lower():
                continue
            dilution_raw = match.group(3).strip()
            amount_ul = float(match.group(4))
            dil_pct = 100.0
            if "%" in dilution_raw:
                match = re.search(r"(\d+(?:\.\d+)?)\s*%", dilution_raw)
                if match:
                    dil_pct = float(match.group(1))
            elif dilution_raw.lower() in ("neat", ""):
                dil_pct = 100.0
            formula_data.append((ingredient, amount_ul, dil_pct))

        if not formula_data:
            print(f"ERROR: No ingredients parsed for {name}", file=sys.stderr)
            continue

        print(f"\nFormula: {name}")
        result = compute(formula_data)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_report(result)

        # Pipeline scores
        try:
            total_conc = sum(s for _, s, _ in formula_data)
            ingredients_pct = {}
            dilutions = {}
            for ing, stock_ul, dil_pct in formula_data:
                dilution = dil_pct / 100.0
                active_ul = stock_ul * dilution
                ingredients_pct[ing] = active_ul / total_conc * 100 if total_conc else 0
                dilutions[ing] = dilution
            fv = FormulaVector(ingredients=ingredients_pct, dilutions=dilutions)
            scorer = FormulaScorer()
            scores = scorer.score(fv)
            print(f"\n{'=' * 50}")
            print("  PIPELINE SCORES")
            print(f"{'=' * 50}")
            for k in [
                "geometric_total",
                "longevity",
                "sillage",
                "synergy",
                "luxury",
                "texture",
                "stacking_depth",
                "skin_performance",
                "hedonic",
                "perceptual_clarity",
                "photorealism",
            ]:
                print(f"  {k:25s}: {scores.get(k, 'N/A')}")
        except Exception as e:
            print(f"  (scores unavailable: {e})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
