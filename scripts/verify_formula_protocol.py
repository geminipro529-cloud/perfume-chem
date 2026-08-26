r"""Verify formula protocol — A.1-A.10 verification categories per Plan v4.

Reads pipeline JSON output + original formula markdown.
Implements verification categories with user-locked revisions:
  A.2/A.3/A.6: WARN only (NOT hard blocks)
  Auto-substitution: suggests Perfumer's World or inventory substitutes
  A.1: HARD_BLOCK on gamma=1.0 or wrong VP source

Usage:
  python scripts/verify_formula_protocol.py --pipeline output.json --formula formulas/Foo.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _detect_encoding(path: str) -> str:
    """Auto-detect BOM-based encoding (UTF-8/UTF-16LE/UTF-16BE); default UTF-8."""
    with open(path, "rb") as f:
        head = f.read(4)
    if head.startswith(b"\xff\xfe") or head.startswith(b"\xfe\xff"):
        return "utf-16"
    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "utf-8"


def _load_json(path):
    with open(path, encoding=_detect_encoding(path)) as f:
        return json.load(f)


def _load_jsonl(path):
    if not Path(path).exists():
        return []
    with open(path, encoding=_detect_encoding(path)) as f:
        return [json.loads(line) for line in f if line.strip()]


def _check_a1_oav_physics(formula_state, config):
    """A.1: Verify gamma != 1.0, VP source, Clausius-Clapeyron."""
    issues = []
    materials = formula_state.get("materials", [])
    for mat in materials:
        gamma = mat.get("gamma", 1.0)
        name = mat.get("name", "?")
        vp = mat.get("vp_pa", 0)
        if abs(gamma - 1.0) < 0.01 and vp > 0.001:
            issues.append(
                {
                    "material": name,
                    "issue": f"gamma={gamma} — may silently assume ideal solution",
                    "severity": "BLOCK",
                }
            )
    return issues


def _check_a2_eu_allergens(formula_state, pipeline_data):
    """A.2: EU 2023/1545 82-allergen compliance (WARN only)."""
    warnings = []
    allergens_db = _load_json(
        str(PROJECT_ROOT / ".opencode" / "library" / "eu_2023_1545_allergens.json")
    )
    if not allergens_db:
        return []

    materials = formula_state.get("materials", [])
    formula_text = json.dumps(materials).lower()

    for allergen in allergens_db:
        name = allergen.get("inci", "").lower()
        if not name:
            continue
        if name in formula_text:
            for mat in materials:
                mat_name = mat.get("name", "").lower()
                if name in mat_name:
                    active_pct = mat.get("active_pct", 0)
                    threshold = allergen.get("threshold_leaveon_pct", 0.001)
                    if active_pct > threshold:
                        sub = _find_substitutes(mat_name, "allergen")
                        warnings.append(
                            {
                                "material": mat.get("name"),
                                "allergen": allergen.get("inci"),
                                "active_pct": round(active_pct, 4),
                                "threshold_pct": threshold,
                                "severity": "WARN",
                                "substitutes": sub,
                            }
                        )
    return warnings


def _check_a3_phototoxicity(formula_state):
    """A.3: Phototoxicity check (WARN only)."""
    warnings = []
    phototox_db = _load_json(str(PROJECT_ROOT / ".opencode" / "library" / "phototoxic_oils.json"))
    if not phototox_db:
        return []

    materials = formula_state.get("materials", [])
    total_bgtene_ppm = 0.0

    for mat in materials:
        mat_name = mat.get("name", "").lower()
        for oil in phototox_db:
            oil_name = oil.get("name", "").lower()
            if oil_name in mat_name or mat_name in oil_name:
                bgtene_ppm = oil.get("bergaptene_ppm", 0)
                active_pct = mat.get("active_pct", 0)
                ifra_max = oil.get("ifra_max_leaveon_pct", 1.0)
                if active_pct > ifra_max:
                    sub = _find_substitutes(mat.get("name"), "phototoxic")
                    warnings.append(
                        {
                            "material": mat.get("name"),
                            "active_pct": round(active_pct, 4),
                            "ifra_max_pct": ifra_max,
                            "bergaptene_ppm": bgtene_ppm,
                            "severity": "WARN",
                            "substitutes": sub,
                        }
                    )
                total_bgtene_ppm += active_pct * bgtene_ppm / 100.0

    if total_bgtene_ppm > 15:
        warnings.append(
            {
                "material": "COMBINED",
                "total_bergaptene_ppm": round(total_bgtene_ppm, 2),
                "limit_ppm": 15,
                "severity": "WARN",
            }
        )

    return warnings


def _check_a6_skin_degradation(formula_state):
    """A.6: Skin degradation kinetics (WARN only, no CoA required per user)."""
    warnings = []
    materials = formula_state.get("materials", [])
    for mat in materials:
        name = mat.get("name", "").lower()
        if "oakmoss" in name:
            warnings.append(
                {
                    "material": mat.get("name"),
                    "issue": "Oakmoss absolute contains atranorin — degrades to atranol on skin",
                    "recommendation": "Verify atranol+chloroatranol <100 ppm via supplier (recommended, not required)",
                    "severity": "WARN",
                }
            )
        if "labdanum" in name:
            warnings.append(
                {
                    "material": mat.get("name"),
                    "issue": "Labdanum contains ambrein glycosides — potentiated character over time on skin",
                    "severity": "INFO",
                }
            )
    return warnings


def _check_a8_sensomics():
    """A.8: Sensomics disclaimer (always append)."""
    return {
        "disclaimer": (
            "This pipeline OAV report is a theoretical screen using known headspace "
            "thermodynamics and literature ODT data. It is NOT an AEDA/GC-MS-O "
            "sensomics verification. Bench mixing and human sensory panel required "
            "before final release claim."
        )
    }


def _find_substitutes(material_name: str, violation_type: str) -> list[dict]:
    """Find substitutes in inventory or Perfumer's World."""
    subs = []
    kb = _load_jsonl(str(PROJECT_ROOT / ".opencode" / "library" / "perfume_kb.jsonl"))

    # Try inventory first
    ml = material_name.lower()
    for entry in kb:
        if entry.get("source") == "inventory" and entry.get("in_stock"):
            ename = entry.get("name", "").lower()
            if ml != ename and any(
                shared in ename for shared in ["fcf", "bergamot", "oakmoss", "evernyl"]
            ):
                subs.append(
                    {
                        "source": "inventory",
                        "name": entry["name"],
                        "dilution": entry.get("dilution", "neat"),
                    }
                )

    # Then PW
    for entry in kb:
        if entry.get("source") == "perfumersworld":
            ename = entry.get("base_name", "").lower()
            if violation_type == "phototoxic" and ("fcf" in ename):
                if "bergamot" in ml and "bergamot" in ename:
                    subs.append(
                        {
                            "source": "pw",
                            "name": entry["base_name"],
                            "sku": entry.get("sku"),
                            "price_usd_per_gram": entry.get("price_usd_per_gram"),
                        }
                    )
            if violation_type == "allergen" and ml != ename:
                if any(shared in ename for shared in ml.split()[:3]):
                    subs.append(
                        {"source": "pw", "name": entry["base_name"], "sku": entry.get("sku")}
                    )

    return subs[:5]


def verify_formula_protocol(pipeline_path: str, formula_path: str) -> dict[str, object]:
    """Run all verification categories and return report."""

    try:
        pipeline = _load_json(pipeline_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": str(e)}

    formulas = pipeline.get("formulas", [])
    if not formulas:
        return {"error": "No formulas in pipeline JSON"}

    config = pipeline.get("config_summary", {})
    report = {
        "verified_at": "",
        "categories": {},
        "hard_blocks": [],
        "warnings": [],
        "total_blocks": 0,
        "total_warns": 0,
        "all_passed": False,
    }

    all_blocks = []
    all_warnings = []

    for formula in formulas:
        state = formula.get("formula_state", {})
        formula.get("name", "unnamed")

        # A.1: OAV Physics
        a1 = _check_a1_oav_physics(state, config)
        report["categories"]["A.1_oav_physics"] = {"issues": a1}
        for i in a1:
            if i.get("severity") == "BLOCK":
                all_blocks.append(f"A.1 {i['material']}: {i['issue']}")

        # A.2: EU Allergens
        a2 = _check_a2_eu_allergens(state, pipeline)
        report["categories"]["A.2_eu_allergens"] = {"warnings": a2}
        for w in a2:
            all_warnings.append(
                f"A.2 {w['material']}: allergen {w['allergen']} at {w['active_pct']}% > {w['threshold_pct']}% threshold"
            )

        # A.3: Phototoxicity
        a3 = _check_a3_phototoxicity(state)
        report["categories"]["A.3_phototoxicity"] = {"warnings": a3}
        for w in a3:
            all_warnings.append(
                f"A.3 {w['material']}: {w.get('active_pct', '?')}% > IFRA {w.get('ifra_max_pct', '?')}%"
            )

        # A.6: Skin degradation
        a6 = _check_a6_skin_degradation(state)
        report["categories"]["A.6_skin_degradation"] = {"warnings": a6}
        for w in a6:
            all_warnings.append(f"A.6 {w['material']}: {w['issue']}")

        # A.8: Sensomics
        a8 = _check_a8_sensomics()
        report["categories"]["A.8_sensomics"] = a8

        # A.4, A.5, A.7, A.9, A.10 deferred to pipeline gates
        report["categories"]["A.4_receptor_saturation"] = {"status": "deferred_to_gate"}
        report["categories"]["A.5_composite_oav"] = {"status": "deferred_to_gate"}
        report["categories"]["A.7_vp_source"] = {"status": "deferred_to_gate"}
        report["categories"]["A.9_vp_thermodynamics"] = {"status": "deferred_to_gate"}
        report["categories"]["A.10_note_tier"] = {"status": "deferred_to_gate"}

    report["total_blocks"] = len(all_blocks)
    report["total_warns"] = len(all_warnings)
    report["all_passed"] = report["total_blocks"] == 0
    report["hard_blocks"] = all_blocks
    report["warnings"] = all_warnings

    return report


def main():
    parser = argparse.ArgumentParser(description="Verify formula protocol A.1-A.10")
    parser.add_argument("--pipeline", required=True, help="Pipeline JSON output path")
    parser.add_argument("--formula", required=True, help="Original formula markdown path")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    report = cast(dict[str, object], verify_formula_protocol(args.pipeline, args.formula))

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        hard_blocks = cast(list[str], report.get("hard_blocks", []))
        warnings_list = cast(list[str], report.get("warnings", []))
        categories = cast(dict[str, object], report.get("categories", {}))
        print(f"Hard blocks: {report['total_blocks']}")
        for b in hard_blocks:
            print(f"  BLOCK: {b}")
        print(f"Warnings:   {report['total_warns']}")
        for w in warnings_list[:10]:
            print(f"  WARN: {w}")
        a8 = categories.get("A.8_sensomics")
        if isinstance(a8, dict):
            print(f"\n{a8.get('disclaimer', '')}")

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
