"""Probe Pine EO / Beta-Pinene / Juniper Berry EO under the same two-gate
priority used by `_opt_layton_fougere_addonly.py`:

  Priority 1 (performance): Thai mass-market smell, sillage, longevity.
  Priority 2 (family):      masculine aromatic fougere classification.

This re-uses the existing objective and base-bottle model. It does not retune
the gates: it just scores variants where Pine EO, Beta-Pinene, and Juniper
Berry EO are individually pushed against the current performance-first table.

The objective returns a higher (less negative) score when the formula better
satisfies the two constraints.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import _opt_layton_fougere_addonly as base


ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "_probe_pine_juniper_betapinene_out.json"


# ---- 1. Patch Pine EO into the optimizer's family/physics/ODT tables --------

base.FAMILY["Pine EO"] = "aromatic"

# Pine EO is dominated by alpha-pinene/beta-pinene/limonene. Use a representative
# MW = 136.2 (pinene), VP = 470 Pa (alpha-pinene 25 C, slightly above beta-pinene
# at 390 Pa since Pine EO is alpha-dominant), ODT ~ 6 ppb (sharper than juniper).
base.PHYSICS_OVERRIDES["Pine EO"] = (136.2, 470.0)
base.ODT_OVERRIDES_PPB["Pine EO"] = 6.0

# Allow Pine EO into the candidate space for fair comparison.
base.CANDIDATE_BOUNDS_UL["Pine EO"] = (0, 60)


# ---- 2. Build the comparison variants ---------------------------------------

PERF = base.PERFORMANCE_FIRST_ADDITIONS_UL


def variant(label: str, **deltas) -> dict[str, float]:
    """Make a copy of the performance-first table with deltas applied."""
    out = dict(PERF)
    for mat, change in deltas.items():
        out[mat] = max(0.0, out.get(mat, 0.0) + change)
    return out


VARIANTS: dict[str, dict[str, float]] = {
    # Anchor: the current performance-first plan.
    "00_baseline_performance_first": dict(PERF),

    # Pine EO probe: add at 3 doses, take volume from low-marginal Petitgrain.
    "01_pine_15ul": variant("pine_15", **{"Pine EO": +15, "Petitgrain EO": -15}),
    "02_pine_30ul": variant("pine_30", **{"Pine EO": +30, "Petitgrain EO": -20, "Cedarwood oil Virginia": -10}),
    "03_pine_45ul": variant("pine_45", **{"Pine EO": +45, "Petitgrain EO": -20, "Cedarwood oil Virginia": -15, "Lime Distilled EO": -10}),

    # Beta-Pinene probe: raise current 5 -> 12 / 20 / 25 uL.
    "04_betapinene_12ul": variant("bp_12", **{"Beta-Pinene": +7, "Petitgrain EO": -7}),
    "05_betapinene_20ul": variant("bp_20", **{"Beta-Pinene": +15, "Petitgrain EO": -10, "Cedarwood oil Virginia": -5}),
    "06_betapinene_25ul": variant("bp_25", **{"Beta-Pinene": +20, "Petitgrain EO": -10, "Cedarwood oil Virginia": -10}),

    # Juniper Berry EO probe: raise current 10 -> 18 / 25 / 35 uL.
    "07_juniper_18ul": variant("jun_18", **{"Juniper Berry EO": +8, "Petitgrain EO": -8}),
    "08_juniper_25ul": variant("jun_25", **{"Juniper Berry EO": +15, "Petitgrain EO": -8, "Cedarwood oil Virginia": -3, "Lime Distilled EO": -4}),
    "09_juniper_35ul": variant("jun_35", **{"Juniper Berry EO": +25, "Petitgrain EO": -10, "Cedarwood oil Virginia": -8, "Lime Distilled EO": -7}),

    # Combined scenarios.
    "10_juniper_25_betapinene_8": variant(
        "jun_25_bp_8",
        **{"Juniper Berry EO": +15, "Beta-Pinene": +3, "Petitgrain EO": -10, "Cedarwood oil Virginia": -5, "Lime Distilled EO": -3},
    ),
    "11_juniper_25_pine_15": variant(
        "jun_25_pine_15",
        **{"Juniper Berry EO": +15, "Pine EO": +15, "Petitgrain EO": -15, "Cedarwood oil Virginia": -10, "Lime Distilled EO": -5},
    ),
    "12_juniper_25_no_pine_no_extra_bp": variant(
        "jun_25_clean",
        **{"Juniper Berry EO": +15, "Petitgrain EO": -8, "Cedarwood oil Virginia": -3, "Lime Distilled EO": -4},
    ),
}


# ---- 3. Score each variant under the same objective ------------------------


def evaluate() -> dict:
    materials = sorted(set(base.BASE_STOCK_UL) | set(base.CANDIDATE_BOUNDS_UL))
    tables = base.build_tables(materials)
    base_snap = base.snapshots(base.BASE_STOCK_UL, tables)
    base_env = base.family_envelope(base_snap)

    results: dict[str, dict] = {}
    for name, additions in VARIANTS.items():
        score = base.objective(additions, base_env, tables)
        stock = base.combine(additions)
        env = base.family_envelope(base.snapshots(stock, tables))
        total = sum(additions.values())
        new_total = sum(additions.get(m, 0.0) for m in base.NEW_MATERIALS)

        delta_top_fresh = env["top"].get("fresh", 0) - base_env["top"].get("fresh", 0)
        delta_top_aromatic = env["top"].get("aromatic", 0) - base_env["top"].get("aromatic", 0)
        delta_heart_aromatic = env["heart"].get("aromatic", 0) - base_env["heart"].get("aromatic", 0)
        delta_base_moss = env["base"].get("moss", 0) - base_env["base"].get("moss", 0)
        delta_base_wood = env["base"].get("wood", 0) - base_env["base"].get("wood", 0)

        results[name] = {
            "score": round(score, 4),
            "total_add_ul": round(total, 1),
            "new_material_add_ul": round(new_total, 1),
            "additions_ul": {k: round(v, 1) for k, v in sorted(additions.items()) if v > 0},
            "delta_vs_base": {
                "top_fresh": round(delta_top_fresh, 2),
                "top_aromatic": round(delta_top_aromatic, 2),
                "heart_aromatic": round(delta_heart_aromatic, 2),
                "base_moss": round(delta_base_moss, 3),
                "base_wood": round(delta_base_wood, 3),
            },
        }

    baseline_score = results["00_baseline_performance_first"]["score"]
    for name, payload in results.items():
        payload["delta_score_vs_baseline"] = round(payload["score"] - baseline_score, 4)

    ranked = sorted(results.items(), key=lambda kv: -kv[1]["score"])
    return {"baseline_score": baseline_score, "ranked": [k for k, _ in ranked], "variants": results}


def main() -> int:
    out = evaluate()
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("Two-gate probe (perf first, fougere second). Higher score = better.")
    print(f"Baseline (performance-first): {out['baseline_score']:.4f}")
    print()
    print(f"{'rank':<5}{'variant':<42}{'score':>10}{'dScore':>10}{'totalUL':>9}{'newUL':>7}")
    for rank, name in enumerate(out["ranked"], 1):
        v = out["variants"][name]
        print(f"{rank:<5}{name:<42}{v['score']:>10.4f}{v['delta_score_vs_baseline']:>+10.4f}{v['total_add_ul']:>9.1f}{v['new_material_add_ul']:>7.1f}")
    print()
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
