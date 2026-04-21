"""
5 MASCULINE Luxury Perfume Formulas — Synergy-Maximized Pipeline
Runs entirely via local engine imports (no server).

Design principles:
  - Every formula uses ONLY materials from inventory
  - All ingredients chosen for KNOWN synergy pairs from DB
  - Masculine archetypes: dark leather, imperial woods, oriental spice,
    modern vetiver, dark iris-suede
  - Texture, projection, longevity optimized per archetype
  - 16-17 ingredients per formula for max theory score
  - Sillage boosters deployed per theme
  - Carles ideal pyramid targeted: 20% top / 40% heart / 40% base
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))




import sys, json

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer


# ═══════════════════════════════════════════════════════════════════
#  FORMULA DEFINITIONS — 5 MASCULINE LUXURY
# ═══════════════════════════════════════════════════════════════════

FORMULAS = {
    # ---------------------------------------------------------------
    # 1. NOIR ABSOLU — Dark Amber-Leather
    #    Archetype: Smoky leather, warm amber, spices. Evening powerhouse.
    #    Texture: Rich, smoky, voluptuous, resinous warmth
    #    Opening: Bergamot + Black Pepper → fresh spicy
    #    Heart: Hedione + Styrax + Labdanum + IBQ → warm leather-balsamic
    #    Dry down: ISO E + Ambrox + Patchouli + Birch Tar + Guaiacol +
    #              Coumarin + Vanillin → massive amber-leather-smoky-powdery
    #
    #    KEY SYNERGIES ACTIVATED:
    #      IBQ + Birch Tar (leather duo)
    #      IBQ + Labdanum, Styrax, Guaiacol (all DB pairings)
    #      Birch Tar + Guaiacol, ISO E Super, Labdanum (trio)
    #      Styrax + Labdanum (balsamic-amber bridge)
    #      Labdanum + Vanillin, Ambrox (amber amplifier)
    #      Coumarin + Vanillin = TONKA BEAN synergy (explicit DB rule)
    #      Ambrox + Musks = 3-5x intensity (explicit DB synergy)
    #      Cashmeran + Musks, Ambrox, Pepper, Coumarin
    #      Patchouli + Labdanum (earth-amber)
    #      Black Pepper + Bergamot, Ambrox
    # ---------------------------------------------------------------
    "Noir Absolu": {
        "concentration": 28,
        "ingredients": {
            "Bergamot FCF": 6.0,
            "Black Pepper FTEC": 5.0,
            "Isobutyl Quinoline": 3.0,
            "Hedione": 5.0,
            "Styrax FTEC": 5.0,
            "Labdanum Absolute": 8.0,
            "Birch Tar Rectified": 1.0,
            "Guaiacol": 1.0,
            "Coumarin": 5.0,
            "Vanillin": 4.0,
            "Iso E Super": 15.0,
            "Ambrox Super": 10.0,
            "Patchouli EO": 8.0,
            "Cashmeran": 6.0,
            "Galaxolide": 10.0,
            "Ethylene Brassylate": 8.0,
        },
    },

    # ---------------------------------------------------------------
    # 2. BOIS IMPERIAL — Imperial Woods
    #    Archetype: Cedar-vetiver-iris power suit. Sophisticated daytime.
    #    Texture: Dry, elegant, powdery woody, cedar pencil shavings
    #    Opening: Bergamot + Grapefruit + Cardamom → bright spicy citrus
    #    Heart: Hedione + Alpha Irone + Methyl/Allyl Ionone → luminous iris
    #    Dry down: Cedarwood + ISO E + Vetiver + Kephalis + Vertofix →
    #              magnificent cedar-vetiver with iris powder echo
    #
    #    KEY SYNERGIES ACTIVATED:
    #      Alpha Irone + Methyl Ionone (iris amplifier, DB pairing)
    #      Alpha Irone + Allyl Ionone (ionone triad, DB pairing)
    #      Alpha Irone + Hedione (radiance, DB pairing)
    #      Alpha Irone + Coumarin (powdery depth, DB pairing)
    #      Methyl Ionone + ISO E Super, Hedione (DB pairings)
    #      Allyl Ionone + ionones, musks, coumarin, hedione (all DB)
    #      Cedarwood + ISO E Super, Vetiver, Bergamot, Musks (all DB)
    #      Kephalis + ISO E Super, Cedarwood, Vetiver (all DB)
    #      Vertofix + ISO E Super, Cedarwood, Musks (DB)
    #      Grapefruit + Vetiver (modern vetiver, DB pairing)
    #      Cardamom + Bergamot, Iris, ISO E Super (all DB)
    #      Ambrox + Woods, Iris, Musks, Spices (DB)
    # ---------------------------------------------------------------
    "Bois Imperial": {
        "concentration": 25,
        "ingredients": {
            "Bergamot FCF": 6.0,
            "Grapefruit FCF": 4.0,
            "Cardamom FTEC": 4.0,
            "Hedione": 8.0,
            "Alpha Irone": 3.0,
            "Methyl Ionone": 5.0,
            "Allyl Ionone": 4.0,
            "Cedarwood EO": 8.0,
            "Iso E Super": 14.0,
            "Vetiver EO": 6.0,
            "Kephalis": 5.0,
            "Ambrox Super": 8.0,
            "Coumarin": 5.0,
            "Galaxolide": 8.0,
            "Habanolide": 6.0,
            "Vertofix Coeur": 6.0,
        },
    },

    # ---------------------------------------------------------------
    # 3. ORIENT EXPRESS — Spiced Amber-Tobacco
    #    Archetype: Rich tobacco-vanilla-spice oriental. Date night.
    #    Texture: Opulent, warm, sweet-spicy, caramel-resinous
    #    Opening: Bergamot + Black Pepper + Cardamom → spice blast
    #    Heart: Hedione + Lavender + Labdanum + Olibanum → aromatic incense
    #    Dry down: Vanillin + Ethyl Maltol + Coumarin + Maple Lactone +
    #              ISO E + Ambrox + Cashmeran → tobacco-vanilla-caramel
    #
    #    KEY SYNERGIES ACTIVATED:
    #      Vanillin + Ethyl Maltol = RICH CARAMEL (explicit DB SYNERGY!)
    #      Vanillin + Coumarin = TONKA BEAN (explicit DB SYNERGY!)
    #      Ambrox + Musks = 3-5x INTENSITY (explicit DB SYNERGY!)
    #      Labdanum + Vanillin, Benzoin, Olibanum, Ambrox (all DB)
    #      Olibanum + Labdanum, ISO E Super (DB)
    #      Maple Lactone + Vanillin, Ethyl Maltol, Tonka (DB)
    #      Lavender + Coumarin (classic fougere, DB)
    #      Ethyl Maltol + Vanillin, Coumarin, Tonka, Maple Lactone (DB)
    #      Cardamom + Bergamot, ISO E Super (DB)
    #      Black Pepper + Bergamot, Ambrox (DB)
    #      Cashmeran + Musks, Ambrox, Coumarin, Pepper (DB)
    #      Romandolide + Other musks, ISO E Super (DB)
    # ---------------------------------------------------------------
    "Orient Express": {
        "concentration": 26,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Black Pepper FTEC": 4.0,
            "Cardamom FTEC": 4.0,
            "Hedione": 5.0,
            "Lavender EO": 4.0,
            "Labdanum Absolute": 10.0,
            "Olibanum Resinoid": 6.0,
            "Vanillin": 6.0,
            "Ethyl Maltol": 3.0,
            "Coumarin": 6.0,
            "Maple Lactone": 3.0,
            "Iso E Super": 12.0,
            "Ambrox Super": 10.0,
            "Cashmeran": 6.0,
            "Galaxolide": 8.0,
            "Romandolide": 8.0,
        },
    },

    # ---------------------------------------------------------------
    # 4. VETIVER IMPERIAL — Modern Vetiver
    #    Archetype: Clean, sophisticated vetiver-cedar. Gentleman daily.
    #    Texture: Fresh, transparent, earthy, mineral-green
    #    Opening: Bergamot + Grapefruit + DHM + Linalool → bright citrus
    #    Heart: Hedione + Floralozone + Undecavertol → airy transparent
    #    Dry down: Vetiver + Vetival + Cedarwood + ISO E + Norlimbanol +
    #              Ambrox + BenzSal + Musks → magnificent vetiver base
    #
    #    KEY SYNERGIES ACTIVATED:
    #      ISO E Super + Hedione = SOLAR AMBER (explicit DB SYNERGY!)
    #      Hedione + Citrus = 2-3x PROJECTION (explicit DB SYNERGY!)
    #      DHM + Florals = 2x PROJECTION (explicit DB SYNERGY!)
    #      Ambrox + Musks = 3-5x INTENSITY (explicit DB SYNERGY!)
    #      Vetiver + Vetival (vetiver duo, DB pairing)
    #      Vetiver + Grapefruit (modern vetiver, DB pairing)
    #      Grapefruit + Vetiver, DHM, Hedione (DB)
    #      Floralozone + Hedione, DHM, Bergamot, Musks (DB)
    #      DHM + Bergamot, Hedione, Musks (DB)
    #      Cedarwood + ISO E Super, Vetiver, Bergamot, Musks (DB)
    #      Norlimbanol + Cedarwood, ISO E Super, Musks (DB)
    #      Vetival + ISO E Super, Cedarwood, Grapefruit (DB)
    #      Benzyl Salicylate + Florals, Musks, Powder (DB)
    #      Linalool + Everything (DB)
    # ---------------------------------------------------------------
    "Vetiver Imperial": {
        "concentration": 22,
        "ingredients": {
            "Bergamot FCF": 6.0,
            "Grapefruit FCF": 5.0,
            "Dihydromyrcenol": 6.0,
            "Linalool": 4.0,
            "Hedione": 10.0,
            "Floralozone": 3.0,
            "Undecavertol": 3.0,
            "Vetiver EO": 8.0,
            "Vetival": 5.0,
            "Iso E Super": 14.0,
            "Cedarwood EO": 6.0,
            "Norlimbanol Dextro": 2.0,
            "Ambrox Super": 8.0,
            "Benzyl Salicylate": 5.0,
            "Galaxolide": 8.0,
            "Habanolide": 5.0,
            "Ethylene Brassylate": 2.0,
        },
    },

    # ---------------------------------------------------------------
    # 5. AURA NOIRE — Dark Iris-Suede
    #    Archetype: Mysterious dark iris meets suede leather. Niche luxury.
    #    Texture: Powdery-suede, velvety, dark, magnetic
    #    Opening: Bergamot + Pink Pepper + Cardamom → pink spice
    #    Heart: Hedione + Alpha Irone + Methyl Ionone + Orris FTEC +
    #           Suederal → iris-suede heart
    #    Dry down: Styrax + Labdanum + Patchouli + Cedar + ISO E +
    #              Ambrox + Cashmeran + Musks → dark woody-leather base
    #
    #    KEY SYNERGIES ACTIVATED:
    #      Alpha Irone + Methyl Ionone, Hedione (DB pairings)
    #      Methyl Ionone + ISO E Super, Hedione (DB)
    #      Orris FTEC + Hedione, Cedarwood, Methyl Ionone (DB)
    #      Suederal + ISO E Super, Styrax, Cedarwood (DB)
    #      Styrax + Labdanum, Leather notes (DB)
    #      Pink Pepper + Bergamot, ISO E Super, Patchouli (DB)
    #      Cardamom + Bergamot, Iris, ISO E Super (DB)
    #      Labdanum + Ambrox, Musks (DB)
    #      Patchouli + Cedarwood, Labdanum (DB)
    #      Cedarwood + ISO E Super, Musks (DB)
    #      Cashmeran + Musks, Ambrox, Iris, Woods, Pepper (DB)
    #      Ambrox + Musks = 3-5x INTENSITY (explicit DB SYNERGY!)
    # ---------------------------------------------------------------
    "Aura Noire": {
        "concentration": 26,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Pink Pepper Base": 4.0,
            "Cardamom FTEC": 3.0,
            "Hedione": 6.0,
            "Alpha Irone": 3.0,
            "Methyl Ionone": 6.0,
            "Orris F-TEC": 3.0,
            "Suederal": 3.0,
            "Styrax FTEC": 4.0,
            "Labdanum Absolute": 8.0,
            "Iso E Super": 15.0,
            "Ambrox Super": 10.0,
            "Patchouli EO": 6.0,
            "Cedarwood EO": 6.0,
            "Galaxolide": 8.0,
            "Cashmeran": 5.0,
            "Ethylene Brassylate": 5.0,
        },
    },
}

# Descriptions for the markdown report
DESCRIPTIONS = {
    "Noir Absolu": {
        "tagline": "Dark Amber-Leather",
        "vibe": "The midnight power move. Smoky leather and amber that commands a room.",
        "texture": "Rich, smoky, voluptuous, resinous warmth",
        "wear": "Evening / Special occasion / Cold weather",
        "projection": "Beast mode — massive sillage from Ambrox + musk synergy",
    },
    "Bois Imperial": {
        "tagline": "Imperial Woods",
        "vibe": "The refined gentleman's signature. Cedar-vetiver nobility with iris elegance.",
        "texture": "Dry, elegant, powdery woody, pencil shavings sophistication",
        "wear": "Office / Daytime / Year-round",
        "projection": "Moderate-strong — classy aura from ISO E + Hedione",
    },
    "Orient Express": {
        "tagline": "Spiced Amber-Tobacco",
        "vibe": "Opulent oriental warmth. Rich tobacco, caramel, and dark spices.",
        "texture": "Opulent, warm, sweet-spicy, caramel-resinous depth",
        "wear": "Date night / Evening / Fall-Winter",
        "projection": "Strong — Vanillin+Ethyl Maltol caramel + Ambrox amplification",
    },
    "Vetiver Imperial": {
        "tagline": "Modern Vetiver",
        "vibe": "Clean sophistication. The mineral freshness of vetiver with solar warmth.",
        "texture": "Fresh, transparent, earthy, mineral-green clarity",
        "wear": "Daily / Office / Spring-Summer",
        "projection": "Excellent reach — 3 sillage boosters (DHM, Hedione, Ambrox)",
    },
    "Aura Noire": {
        "tagline": "Dark Iris-Suede",
        "vibe": "Magnetic mystery. Noble iris wrapped in soft suede and dark amber.",
        "texture": "Powdery-suede, velvety, dark, magnetic pull",
        "wear": "Evening / Niche / Year-round",
        "projection": "Strong stealth — ISO E creates an aura effect",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 74)
    print("  MASCULINE LUXURY PIPELINE — 5 FORMULAS (direct engine, no server)")
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
        print(f"  {name:20s}  TOTAL={t:5.1f}  "
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
        print(f"  #{i}  {name:20s}  Score: {total:5.1f}  "
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

    # ── PHASE 5: Grid search on star masculine materials ──
    print("\n" + "=" * 74)
    print("  CARLES GRID SEARCH — MASCULINE STARS")
    print("=" * 74)
    for star in ["Iso E Super", "Ambrox Super", "Vetiver EO", "Patchouli EO", "Labdanum Absolute"]:
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
            print(f"  {name:20s}  "
                  f"data={conf.get('data_confidence', 'N/A')}  "
                  f"pairing={conf.get('pairing_confidence', 'N/A')}  "
                  f"prediction={conf.get('prediction_confidence', 'N/A')}  "
                  f"overall={conf.get('overall_confidence', 'N/A')}")

    # ── PHASE 7: Save JSON results ──
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

    out_path = Path("masculine_luxury_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)

    # ── PHASE 8: Generate markdown report ──
    md_lines = [
        "# 5 Masculine Luxury Perfume Formulas — Synergy-Maximized",
        "",
        "Generated via local engine pipeline (no server).  ",
        "Every ingredient chosen for DB-verified synergy pairings.  ",
        "All materials from current inventory.",
        "",
    ]

    for i, (name, total, conc) in enumerate(ranked, 1):
        data = all_results[name]
        scores = data["scores"]
        nd = data["note_distribution"]
        conf = data["confidence"] or {}
        ings = FORMULAS[name]["ingredients"]
        desc = DESCRIPTIONS.get(name, {})

        md_lines.append(f"## #{i} — {name} ({desc.get('tagline', '')})")
        md_lines.append("")
        md_lines.append(f"> *{desc.get('vibe', '')}*")
        md_lines.append("")
        md_lines.append(f"**Concentration:** {conc}% EDP  |  "
                        f"**Total Score:** {total:.1f}/100")
        md_lines.append(f"**Texture:** {desc.get('texture', '')}  ")
        md_lines.append(f"**Best for:** {desc.get('wear', '')}  ")
        md_lines.append(f"**Projection:** {desc.get('projection', '')}")
        md_lines.append("")

        md_lines.append("### Scores")
        md_lines.append("| Axis | Score |")
        md_lines.append("|------|-------|")
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

    md_path = Path("masculine_luxury_formulas.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n  Results saved to {out_path}")
    print(f"  Report saved to {md_path}")
    print("\n" + "=" * 74)
    print("  DONE")
    print("=" * 74)


if __name__ == "__main__":
    main()
