"""Validate harvested top-3 formulas in fresh process, all scored against in-process v3."""
import json
from _opt_iris_reverie_15probes import (
    IRL_V3, IRL_DIL_BASE, BATCH_ML,
    score_formula, FormulaScorer, SynergyGraph, AXES,
)

def main():
    with open("_opt_iris_top3_harvest.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    v3_geo, v3_det = score_formula(IRL_V3, IRL_DIL_BASE, scorer)
    print(f"\n  v3 (fresh process): geo={v3_geo:.3f}\n")

    rows = [("v3", v3_geo, 0.0, v3_det, IRL_V3)]
    for tag, d in data["probes"].items():
        ing = {k: float(v) for k, v in d["ing"].items()}
        dil = {k: float(v) for k, v in d["dil"].items()} if d.get("dil") else IRL_DIL_BASE
        geo, det = score_formula(ing, dil, scorer)
        rows.append((tag, geo, geo - v3_geo, det, ing))

    print(f"  {'label':28s} {'geo':>8s} {'Δ vs v3':>10s}")
    for tag, geo, dv, _, _ in rows:
        print(f"  {tag:28s} {geo:8.3f} {dv:+10.3f}")

    # Axis table for all
    print("\n  AXIS TABLE")
    print(f"  {'axis':22s}" + "".join(f" {r[0][:10]:>10s}" for r in rows))
    for a in AXES:
        line = f"  {a:22s}"
        for _, _, _, det, _ in rows:
            v = det.get(a, 0.0) if isinstance(det, dict) else det.scores.get(a, 0.0)
            line += f" {v:10.2f}"
        print(line)

    # Winner
    ranked = sorted(rows[1:], key=lambda r: -r[1])
    best = ranked[0]
    print(f"\n  WINNER: {best[0]} geo={best[1]:.3f} (Δ{best[2]:+.3f} vs v3)")
    if best[2] > 0.05:
        print(f"  → real gain, build formula")
    else:
        print(f"  → too small, v3 stands")

if __name__ == "__main__":
    main()
