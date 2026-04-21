"""
5 NEW Luxury Perfume Formulas — Synergy-Optimized Pipeline
Runs entirely via local engine imports (no server).

Design principles:
  - Every formula uses ONLY materials from inventory
  - Ingredients chosen for known synergy pairs (DB pairing rules)
  - Target note pyramid: 20% top / 40% heart / 40% base (Carles ideal)
  - Sillage boosters: Hedione, Iso E Super, Dihydromyrcenol where thematic
  - Roudnitska roles + Jellinek quadrant coverage for max theory score
  - Texture & modifier effects considered per material
  - 10-14 ingredients per formula (sweet spot for theory score)
"""

import sys, json
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer


# ═══════════════════════════════════════════════════════════════════
#  FORMULA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

FORMULAS = {
    # ---------------------------------------------------------------
    # 1. SOIE CELESTE — Heavenly Silk
    #    Transparent radiant floral-musk, maximum sillage
    #    Texture: silky, weightless, skin-like glow
    #    Key synergies: Aurantiol+Linalool, Aurantiol+Hedione,
    #      Aurantiol+Bergamot, Ambrox+florals, Ambrox+musks,
    #      Benzyl Salicylate+florals+musks
    #    Sillage boosters: Hedione, Iso E Super, Dihydromyrcenol (3/4)
    # ---------------------------------------------------------------
    "Soie Celeste": {
        "concentration": 22,
        "ingredients": {
            "Bergamot FCF": 8.0,
            "Linalool": 6.0,
            "Dihydromyrcenol": 6.0,
            "Hedione": 14.0,
            "Hydroxycitronellal": 6.0,
            "Aurantiol": 5.0,
            "Floralozone": 4.0,
            "Benzyl Salicylate": 7.0,
            "Iso E Super": 12.0,
            "Ambrox Super": 10.0,
            "Galaxolide": 10.0,
            "Habanolide": 6.0,
            "Romandolide": 6.0,
        },
    },

    # ---------------------------------------------------------------
    # 2. BOIS SACRES — Sacred Woods
    #    Deep woody-incense resinous amber
    #    Texture: velvety, warm, smoky-resinous depth
    #    Key synergies: Benzoin Sumatra+Olibanum (incense triad),
    #      Benzoin Sumatra+Labdanum, Ambrox+woods+spices,
    #      Patchouli+cedarwood, Labdanum+amber
    #    Sillage boosters: Hedione, Iso E Super (2/4)
    # ---------------------------------------------------------------
    "Bois Sacres": {
        "concentration": 28,
        "ingredients": {
            "Bergamot FCF": 6.0,
            "Black Pepper FTEC": 5.0,
            "Cardamom FTEC": 4.0,
            "Hedione": 5.0,
            "Patchouli EO": 10.0,
            "Iso E Super": 12.0,
            "Ambrox Super": 8.0,
            "Cedarwood EO": 8.0,
            "Olibanum Resinoid": 8.0,
            "Benzoin Sumatra Resinoid": 8.0,
            "Labdanum Absolute": 10.0,
            "Cashmeran": 8.0,
            "Vetiver EO": 8.0,
        },
    },

    # ---------------------------------------------------------------
    # 3. IRIS ABSOLU — Absolute Iris
    #    Powdery-creamy iris with maximum synergy density
    #    Texture: powdery, noble, suede-like softness
    #    Key synergies: Alpha Irone+Methyl Ionone, Alpha Irone+Allyl Ionone,
    #      Alpha Irone+Hedione, Alpha Irone+Coumarin,
    #      Allyl Ionone+other ionones+coumarin+hedione,
    #      Beta Ionone+other ionones+coumarin,
    #      Bacdanol+iris+hedione, Benzyl Salicylate+iris
    #    18+ potential synergy pair hits — highest synergy density
    #    Sillage boosters: Hedione, Iso E Super (2/4)
    # ---------------------------------------------------------------
    "Iris Absolu": {
        "concentration": 25,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Linalool": 5.0,
            "Alpha Irone": 6.0,
            "Methyl Ionone": 8.0,
            "Allyl Ionone": 6.0,
            "Beta Ionone": 4.0,
            "Hedione": 10.0,
            "Bacdanol": 8.0,
            "Coumarin": 6.0,
            "Iso E Super": 12.0,
            "Ambrox Super": 8.0,
            "Habanolide": 8.0,
            "Cashmeran": 8.0,
            "Benzyl Salicylate": 6.0,
        },
    },

    # ---------------------------------------------------------------
    # 4. CUIR OTTOMAN — Ottoman Leather
    #    Dark smoky spiced leather with balsamic warmth
    #    Texture: rich, smoky, animalic, resinous
    #    Key synergies: Benzoin Sumatra+Birch Tar, Benzoin Sumatra+Labdanum,
    #      Benzoin+Vanillin (amber triad), Ambrox+woods+spices,
    #      IQ+leather character, Patchouli+woods
    #    Sillage boosters: Hedione, Iso E Super (2/4)
    # ---------------------------------------------------------------
    "Cuir Ottoman": {
        "concentration": 28,
        "ingredients": {
            "Bergamot FCF": 6.0,
            "Black Pepper FTEC": 6.0,
            "Isobutyl Quinoline": 5.0,
            "Birch Tar Rectified": 3.0,
            "Styrax FTEC": 5.0,
            "Hedione": 5.0,
            "Benzoin Sumatra Resinoid": 10.0,
            "Labdanum Absolute": 10.0,
            "Vanillin": 8.0,
            "Iso E Super": 14.0,
            "Ambrox Super": 10.0,
            "Patchouli EO": 10.0,
            "Cashmeran": 8.0,
        },
    },

    # ---------------------------------------------------------------
    # 5. JARDIN D'OR — Golden Garden
    #    Luminous dewy green-floral-citrus with golden warmth
    #    Texture: fresh, radiant, dewy, transparent
    #    Key synergies: Aurantiol+Linalool (if added), Bergamot+everything,
    #      Ambrox+florals+musks, Hydroxycitronellal+Aldehyde C11,
    #      Benzyl Salicylate+florals+musks
    #    Sillage boosters: Hedione, Iso E Super, Dihydromyrcenol (3/4)
    # ---------------------------------------------------------------
    "Jardin d'Or": {
        "concentration": 20,
        "ingredients": {
            "Bergamot FCF": 8.0,
            "Neroli EO": 5.0,
            "Linalool": 5.0,
            "Dihydromyrcenol": 7.0,
            "Hedione": 14.0,
            "Hydroxycitronellal": 6.0,
            "PEA": 5.0,
            "Undecavertol": 3.0,
            "Iso E Super": 12.0,
            "Ambrox Super": 8.0,
            "Galaxolide": 10.0,
            "Javanol": 7.0,
            "Benzyl Salicylate": 8.0,
            "Aldehyde C12 MNA": 2.0,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 74)
    print("  LUXURY V2 PIPELINE — 5 NEW FORMULAS (direct engine, no server)")
    print("=" * 74)

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    confidence_scorer = ConfidenceScorer()
    all_results = {}

    # ── PHASE 1: Score ──
    print("\n>>> PHASE 1: SCORING\n")
    for name, data in FORMULAS.items():
        fv = FormulaVector(ingredients=data["ingredients"])
        scores = scorer.score(fv)
        note_dist = fv.note_distribution()
        confidence = confidence_scorer.score(data["ingredients"])
        all_results[name] = {
            "fv": fv,
            "scores": scores,
            "note_distribution": note_dist,
            "confidence": confidence,
            "concentration": data["concentration"],
        }
        t = scores["total"]
        print(f"  {name:18s}  TOTAL={t:5.1f}  "
              f"lon={scores['longevity']:5.1f}  sil={scores['sillage']:5.1f}  "
              f"bal={scores['balance']:5.1f}  syn={scores['synergy']:5.1f}  "
              f"the={scores['theory']:5.1f}  cos={scores['cost']:5.1f}")

    # ── PHASE 2: Rank ──
    print("\n" + "=" * 74)
    print("  RANKING")
    print("=" * 74)
    ranked = sorted(
        [(n, d["scores"]["total"], d["concentration"])
         for n, d in all_results.items()],
        key=lambda x: x[1], reverse=True
    )
    for i, (name, total, conc) in enumerate(ranked, 1):
        nd = all_results[name]["note_distribution"]
        ns = ", ".join(f"{k}:{v:.0f}%"
                       for k, v in sorted(nd.items(), key=lambda x: -x[1]) if v > 0)
        print(f"  #{i}  {name:18s}  Score: {total:5.1f}  "
              f"Conc: {conc}%  Notes: {ns}")

    # ── PHASE 3: Suggest ──
    print("\n" + "=" * 74)
    print("  SUGGESTIONS (top 3)")
    print("=" * 74)
    for name, _, _ in ranked[:3]:
        fv = all_results[name]["fv"]
        suggestions = optimizer.suggest(fv)
        print(f"\n  {name}:")
        if suggestions:
            for s in suggestions[:5]:
                print(f"    -> {s}")
        else:
            print("    (none)")

    # ── PHASE 4: Optimize top 3 ──
    print("\n" + "=" * 74)
    print("  OPTIMIZATION (top 3)")
    print("=" * 74)
    optimized_results = {}
    for name, orig_total, _ in ranked[:3]:
        fv = all_results[name]["fv"]
        result = optimizer.optimize(fv)
        delta = round(result.total_score - orig_total, 1)
        optimized_results[name] = result
        print(f"\n  {name}:")
        print(f"    Original: {orig_total:.1f}  ->  Optimized: {result.total_score:.1f}  (delta {delta:+.1f})")
        if result.reasoning:
            for r in result.reasoning[1:6]:
                print(f"    {r}")
        added = set(result.formula.ingredients.keys()) - set(FORMULAS[name]["ingredients"].keys())
        removed = set(FORMULAS[name]["ingredients"].keys()) - set(result.formula.ingredients.keys())
        if added:
            print(f"    + Added: {', '.join(added)}")
        if removed:
            print(f"    - Removed: {', '.join(removed)}")

    # ── PHASE 5: Grid search on star materials ──
    print("\n" + "=" * 74)
    print("  CARLES GRID SEARCH")
    print("=" * 74)
    for star in ["Alpha Irone", "Hedione", "Ambrox Super", "Patchouli EO"]:
        results_list = optimizer.carles_grid_search(star, n_results=3)
        print(f"\n  Star: {star}")
        for j, res in enumerate(results_list, 1):
            keys = list(res.formula.ingredients.keys())[:6]
            print(f"    #{j}  Score: {res.total_score:.1f}  "
                  f"Ingredients: {', '.join(keys)}...")

    # ── PHASE 6: Confidence ──
    print("\n" + "=" * 74)
    print("  CONFIDENCE")
    print("=" * 74)
    for name, _, _ in ranked:
        conf = all_results[name]["confidence"]
        if conf:
            print(f"  {name:18s}  "
                  f"data={conf.get('data_confidence', 'N/A')}  "
                  f"pairing={conf.get('pairing_confidence', 'N/A')}  "
                  f"prediction={conf.get('prediction_confidence', 'N/A')}  "
                  f"overall={conf.get('overall_confidence', 'N/A')}")

    # ── PHASE 7: Save results ──
    serializable = {}
    for name, data in all_results.items():
        serializable[name] = {
            "concentration": data["concentration"],
            "ingredients": dict(data["fv"].ingredients),
            "scores": data["scores"],
            "note_distribution": data["note_distribution"],
            "confidence": data["confidence"],
        }
    if optimized_results:
        serializable["_optimized"] = {}
        for name, result in optimized_results.items():
            serializable["_optimized"][name] = {
                "optimized_score": result.total_score,
                "optimized_ingredients": dict(result.formula.ingredients),
                "optimized_scores": result.scores,
                "reasoning": result.reasoning,
                "suggestions": result.suggestions,
            }

    out_path = Path("luxury_v2_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)

    # ── PHASE 8: Generate markdown report ──
    md_lines = [
        "# Luxury Perfume Formulas V2 — Synergy-Optimized",
        "",
        "Generated via local engine pipeline (no server).",
        "",
    ]

    for i, (name, total, conc) in enumerate(ranked, 1):
        data = all_results[name]
        scores = data["scores"]
        nd = data["note_distribution"]
        conf = data["confidence"] or {}
        ings = FORMULAS[name]["ingredients"]

        md_lines.append(f"## #{i} — {name}")
        md_lines.append(f"**Concentration:** {conc}% EDP  |  "
                        f"**Total Score:** {total:.1f}/100")
        md_lines.append("")
        md_lines.append("### Scores")
        md_lines.append(f"| Axis | Score |")
        md_lines.append(f"|------|-------|")
        for axis in ["longevity", "sillage", "balance", "synergy", "theory", "cost"]:
            md_lines.append(f"| {axis.title()} | {scores.get(axis, 0):.1f} |")
        md_lines.append("")
        md_lines.append("### Note Distribution")
        md_lines.append(f"Top: {nd.get('top',0):.0f}%  |  "
                        f"Heart: {nd.get('heart',0):.0f}%  |  "
                        f"Base: {nd.get('base',0):.0f}%")
        md_lines.append("")
        md_lines.append("### Ingredients")
        md_lines.append("| Material | % |")
        md_lines.append("|----------|---|")
        for mat, pct in sorted(ings.items(), key=lambda x: -x[1]):
            md_lines.append(f"| {mat} | {pct:.1f} |")
        md_lines.append("")

        # Optimized version if available
        if name in optimized_results:
            opt = optimized_results[name]
            md_lines.append(f"### Optimized Version (Score: {opt.total_score:.1f})")
            md_lines.append("")
            md_lines.append("| Material | % |")
            md_lines.append("|----------|---|")
            for mat, pct in sorted(opt.formula.ingredients.items(), key=lambda x: -x[1]):
                md_lines.append(f"| {mat} | {pct:.1f} |")
            md_lines.append("")
            if opt.reasoning:
                md_lines.append("**Changes:**")
                for r in opt.reasoning[1:]:
                    md_lines.append(f"- {r}")
                md_lines.append("")

        md_lines.append("### Confidence")
        md_lines.append(f"Data: {conf.get('data_confidence', 'N/A')}  |  "
                        f"Pairing: {conf.get('pairing_confidence', 'N/A')}  |  "
                        f"Prediction: {conf.get('prediction_confidence', 'N/A')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_path = Path("luxury_formulas_v2.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n  Results saved to {out_path}")
    print(f"  Report saved to {md_path}")
    print("\n" + "=" * 74)
    print("  DONE")
    print("=" * 74)


if __name__ == "__main__":
    main()