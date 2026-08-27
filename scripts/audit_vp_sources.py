r"""Batch audit all 210 perfume materials for vapor pressure source tagging.

Tags every material with vp_source + evidence_class:
  _PROFILES (HEURISTIC) — default for all 210 materials
  PubChem_exp / PubChem_pred — reserved for future PubChem batch queries
  Good_Scents — reserved for future thegoodscentscompany.com scraping
  NIST — reserved for future NIST WebBook API calls

Run: python scripts/audit_vp_sources.py [--json]

Stdlib only. No external deps beyond engine/ imports.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def audit_vp_sources():
    try:
        from engine.ingredient_intelligence import _PROFILES
    except ImportError as e:
        print(f"ERROR: Cannot load profiles: {e}", file=sys.stderr)
        return None

    results = {}
    tiers: dict[str, int] = {
        "_PROFILES": 0,
        "PubChem_exp": 0,
        "PubChem_pred": 0,
        "Good_Scents": 0,
        "NIST": 0,
        "NOT_APPLICABLE": 0,
    }

    for name, profile in sorted(_PROFILES.items()):
        vp = (
            profile.get("vp", 0.0)
            if isinstance(profile, dict)
            else (getattr(profile, "vp_pa_25c", 0.0) or getattr(profile, "vp", 0.0))
        )
        mw = (
            profile.get("mw", 0.0)
            if isinstance(profile, dict)
            else (getattr(profile, "mw", 0.0) or getattr(profile, "mw_g_mol", 0.0))
        )

        if vp <= 0 and mw <= 0:
            tier = "NOT_APPLICABLE"
            evidence = "no_physical_properties"
        else:
            tier = "_PROFILES"
            evidence = "HEURISTIC"

        results[name] = {"vp_pa_25c": vp, "mw": mw, "vp_source": tier, "evidence_class": evidence}
        tiers[tier] = tiers.get(tier, 0) + 1

    return {"materials": results, "tiers": tiers, "total": len(results)}


def main():
    parser = argparse.ArgumentParser(description="Audit VP sources for all 210 perfume materials")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    report = audit_vp_sources()
    if report is None:
        return 1

    if args.json:
        import json

        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"VP Source Audit: {report['total']} materials")
        for tier in (
            "_PROFILES",
            "PubChem_exp",
            "PubChem_pred",
            "Good_Scents",
            "NIST",
            "NOT_APPLICABLE",
        ):
            count = report["tiers"].get(tier, 0)
            if count:
                pct = count / report["total"] * 100
                print(f"  {tier}: {count} ({pct:.0f}%)")
        print()
        print("All materials default to _PROFILES (HEURISTIC).")
        print(
            "Upgrade paths: thegoodscentscompany.com scrape → NIST WebBook API → primary literature"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
