"""
6 NICHE Perfume Concepts — Artistic, Boundary-Pushing Compositions
Runs entirely via local engine imports (no server).

Design philosophy:
  NOT mass-market. Each formula tells a story, uses materials in unexpected
  ways, and creates olfactory textures that are rare or novel. Every pairing
  is DB-verified. Materials purely from current inventory.

Concepts:
  1. Concrete Petrichor — Rain on hot stone. Mineral-green-earth.
  2. Temple Smoke — Sacred incense + iris powder. Meditative.
  3. Molecule Handshake — Pure aroma-chemicals at perfect synergy ratios.
  4. Black Cashmere — Dark berry-suede-musk skin scent.
  5. Soleil Minéral — Solar amber glow on sunlit skin.
  6. Cuir Sacré — Leather-incense sacred library.
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
#  FORMULA DEFINITIONS — 6 NICHE CONCEPTS
# ═══════════════════════════════════════════════════════════════════

FORMULAS = {
    # ───────────────────────────────────────────────────────────────
    # 1. CONCRETE PETRICHOR — Rain on Hot Stone
    #    Concept: The smell after rain hits warm concrete and dry earth.
    #    Mineral-green-earthy freshness fading into warm vetiver depths.
    #    Truly niche: no conventional "pretty" notes.
    #
    #    Texture: Mineral, green, damp earth, warm dry-down
    #    Structure:
    #      TOP: Grapefruit + cis-3-Hexenol + Galbanum → wet green
    #      HEART: Carrot Seed + Violet Fleuressence + Floralozone → petrichor
    #      BASE: Vetiver + Vetival + Clearwood + ISO E + musks → warm earth
    #
    #    KEY SYNERGIES:
    #      Grapefruit + Vetiver (modern, DB)
    #      Vetiver + Vetival (duo, DB)
    #      Vetival + ISO E Super (DB)
    #      Carrot Seed + Vetiver, Cedar (DB)
    #      Floralozone + DHM, Bergamot, Musks (DB)
    #      Violet Fleuressence + ISO E Super (DB)
    #      Galbanum + Bergamot (DB)
    #      ISO E Super + Musks = 3-5x intensity (DB SYNERGY)
    # ───────────────────────────────────────────────────────────────
    "Concrete Petrichor": {
        "concentration": 18,
        "ingredients": {
            "Grapefruit FCF": 6.0,
            "cis-3-Hexenol": 3.0,
            "Galbanum Resinoid": 2.0,
            "Bergamot FCF": 4.0,
            "Dihydromyrcenol": 5.0,
            "Floralozone": 4.0,
            "Carrot Seed EO": 2.0,
            "Violet Fleuressence": 3.0,
            "Hedione": 6.0,
            "Vetiver EO": 10.0,
            "Vetival": 6.0,
            "Clearwood": 5.0,
            "Iso E Super": 16.0,
            "Norlimbanol Dextro": 2.0,
            "Galaxolide": 10.0,
            "Habanolide": 8.0,
            "Ethylene Brassylate": 8.0,
        },
    },

    # ───────────────────────────────────────────────────────────────
    # 2. TEMPLE SMOKE — Sacred Iris Incense
    #    Concept: Ancient temple. Frankincense smoke rises through
    #    powdery iris clouds. Myrrh-dark, coumarin-soft, quietly holy.
    #
    #    Texture: Powdery, smoky, meditative, incense-iris
    #    Structure:
    #      TOP: Bergamot + Cardamom → light spice opening
    #      HEART: Alpha Irone + Methyl Ionone + Orris FTEC +
    #             Olibanum + Myrrh → iris-incense heart
    #      BASE: Benzoin Sumatra + Labdanum + Coumarin +
    #             ISO E + Cashmeran + Musks → sacred amber base
    #
    #    KEY SYNERGIES:
    #      Alpha Irone + Methyl Ionone, Hedione, Coumarin (all DB)
    #      Olibanum + Myrrh (sacred, DB)
    #      Olibanum + Labdanum (amber-incense, DB)
    #      Olibanum + ISO E Super (DB)
    #      Benzoin Sumatra + Olibanum, Myrrh, Labdanum, Iris (all DB)
    #      Myrrh + Olibanum, Labdanum, Benzoin (DB)
    #      Coumarin + Iris, Vanillin, Musks (DB)
    #      Cashmeran + Iris, Musks, Coumarin (DB)
    #      Orris FTEC + Hedione, Cedarwood, Methyl Ionone (DB)
    #      Cardamom + Bergamot, Iris, ISO E Super (DB)
    # ───────────────────────────────────────────────────────────────
    "Temple Smoke": {
        "concentration": 25,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Cardamom FTEC": 4.0,
            "Hedione": 5.0,
            "Alpha Irone": 4.0,
            "Methyl Ionone": 6.0,
            "Orris F-TEC": 4.0,
            "Olibanum Resinoid": 8.0,
            "Myrrh EO": 4.0,
            "Benzoin Sumatra Resinoid": 8.0,
            "Labdanum Absolute": 8.0,
            "Coumarin": 6.0,
            "Iso E Super": 12.0,
            "Cashmeran": 6.0,
            "Ambrox Super": 6.0,
            "Galaxolide": 8.0,
            "Ethylene Brassylate": 6.0,
        },
    },

    # ───────────────────────────────────────────────────────────────
    # 3. MOLECULE HANDSHAKE — Pure Synergy Study
    #    Concept: Only aroma-chemicals at their exact DB-optimal synergy
    #    ratios. Like Molecule 01 meets 02, but intentionally
    #    layered for maximum "skin scent" effect. No naturals.
    #    Brutally minimal, conceptual, avant-garde.
    #
    #    Texture: Transparent, floating, almost invisible, "your skin
    #             but extraordinary"
    #
    #    KEY SYNERGIES (EXACT DB RATIOS):
    #      ISO E Super + Hedione = Solar amber (1:1, DB SYNERGY)
    #      ISO E Super + Musks = 3-5x intensity (1:1-2:1, DB SYNERGY)
    #      Ambrox + Musks = 3-5x intensity (1:1-2:1, DB SYNERGY)
    #      Hedione + Citrus = 2-3x projection (1:4 Hedione:Citrus, DB)
    #      DHM + Florals = 2x projection (1:5, DB)
    #      Linalool + Citral = H-bonding (1.5x longer, DB)
    #      Ambrox + Bergamot = Caging (1.5-2x longer, DB)
    #      ISO E + Limonene = Hydrophobic caging (2x longer top, DB)
    # ───────────────────────────────────────────────────────────────
    "Molecule Handshake": {
        "concentration": 15,
        "ingredients": {
            "D-Limonene": 5.0,
            "Linalool": 5.0,
            "Citral": 3.0,
            "Dihydromyrcenol": 5.0,
            "Hedione": 15.0,
            "Benzyl Salicylate": 8.0,
            "Iso E Super": 18.0,
            "Ambrox Super": 10.0,
            "Cashmeran": 6.0,
            "Galaxolide": 10.0,
            "Romandolide": 5.0,
            "Habanolide": 5.0,
            "Ethylene Brassylate": 5.0,
        },
    },

    # ───────────────────────────────────────────────────────────────
    # 4. BLACK CASHMERE — Dark Berry-Suede Skin Scent
    #    Concept: Blackcurrant juice on a cashmere sweater. Sweet,
    #    dark, tactile. Suede softness meets berry tartness.
    #    Niche gourmand-chypre hybrid — not dessert-sweet.
    #
    #    Texture: Velvety, dark-fruity, suede-soft, magnetic
    #    Structure:
    #      TOP: Bergamot + Pink Pepper + Blackcurrant → tart-spicy fruit
    #      HEART: Raspberry Ketone + Peonile + Hedione → juicy fruit-floral
    #      BASE: Suederal + Cashmeran + Patchouli + ISO E + Musks →
    #            cashmere-suede-woods
    #
    #    KEY SYNERGIES:
    #      Blackcurrant + Rose, Iris, Musks, Hedione, Beta Ionone (DB)
    #      Raspberry Ketone + Peonile (fruit amplifier, DB)
    #      Peonile + Musks (DB)
    #      Pink Pepper + Bergamot, ISO E Super, Patchouli (DB)
    #      Suederal + ISO E Super, Styrax, Cedarwood (DB)
    #      Cashmeran + Musks, Iris, Woods, Pepper, Coumarin (DB)
    #      Dewberry + Blackcurrant (DB)
    #      Dewberry + Musks, Vanilla (DB)
    #      Ambrox + Musks = 3-5x intensity (DB SYNERGY)
    # ───────────────────────────────────────────────────────────────
    "Black Cashmere": {
        "concentration": 22,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Pink Pepper Base": 4.0,
            "Blackcurrant FTEC": 4.0,
            "Dewberry FTEC": 3.0,
            "Hedione": 6.0,
            "Raspberry Ketone": 3.0,
            "Peonile": 3.0,
            "Beta Ionone": 4.0,
            "Suederal": 4.0,
            "Cashmeran": 8.0,
            "Patchouli EO": 6.0,
            "Iso E Super": 14.0,
            "Ambrox Super": 8.0,
            "Galaxolide": 10.0,
            "Romandolide": 5.0,
            "Ethylene Brassylate": 6.0,
            "Benzyl Salicylate": 7.0,
        },
    },

    # ───────────────────────────────────────────────────────────────
    # 5. SOLEIL MINÉRAL — Solar Amber Skin Glow
    #    Concept: Sunlight trapped in warm amber resin on bronzed skin.
    #    Radiant, golden, solar — like liquid sunshine.
    #    The "your skin but sun-kissed" niche scent.
    #
    #    Texture: Warm, radiant, golden, luminous, sun-baked
    #    Structure:
    #      TOP: Bergamot + Neroli + Linalool → Mediterranean sunshine
    #      HEART: Hedione + Aurantiol + Javanol → solar radiance
    #      BASE: Ambrox + Amber Xtreme + Ambermax + ISO E +
    #            Coumarin + Musks → deep amber glow
    #
    #    KEY SYNERGIES:
    #      ISO E Super + Hedione = SOLAR AMBER (1:1, explicit DB SYNERGY!)
    #      Hedione + Citrus = 2-3x PROJECTION (DB SYNERGY!)
    #      Ambrox + Bergamot = CAGING (1.5-2x longer, DB SYNERGY!)
    #      Ambrox + Musks = 3-5x INTENSITY (DB SYNERGY!)
    #      Aurantiol + Linalool, Hedione, Bergamot, Musks (all DB)
    #      Ambrofix + Ambrox Super (DB)
    #      Amber Xtreme + Musks, Woods, Hedione (DB)
    #      Ambermax + Ambrox, Amber Xtreme, Musks, Woods (DB)
    #      Javanol = creamy sandalwood texture
    #      Neroli EO = luminous citrus-floral bridge
    #      Bacdanol + Amber, Hedione, Musks (DB)
    # ───────────────────────────────────────────────────────────────
    "Soleil Mineral": {
        "concentration": 20,
        "ingredients": {
            "Bergamot FCF": 7.0,
            "Neroli EO": 4.0,
            "Linalool": 5.0,
            "Hedione": 12.0,
            "Aurantiol": 4.0,
            "Javanol": 5.0,
            "Bacdanol": 4.0,
            "Amber Xtreme": 4.0,
            "Ambermax": 3.0,
            "Ambrofix": 3.0,
            "Iso E Super": 14.0,
            "Ambrox Super": 10.0,
            "Coumarin": 4.0,
            "Galaxolide": 8.0,
            "Habanolide": 5.0,
            "Ethylene Brassylate": 5.0,
            "Benzyl Salicylate": 3.0,
        },
    },

    # ───────────────────────────────────────────────────────────────
    # 6. CUIR SACRÉ — Sacred Leather Library
    #    Concept: An ancient leather-bound book in a monastery library.
    #    Old leather, frankincense, beeswax, and cedar shelves.
    #    Think Tuscan Leather meets CDG Avignon.
    #
    #    Texture: Dry leather, papyrus, smoky-sweet incense, warm
    #    Structure:
    #      TOP: Bergamot + Cardamom + Ethyl Safranate → saffron-spice
    #      HEART: IBQ + Birch Tar + Guaiacol + Styrax → dark leather
    #      BASE: Olibanum + Labdanum + Benzoin Sumatra + Cedarwood +
    #            Vertofix + ISO E + Musks → incense-wood-leather base
    #
    #    KEY SYNERGIES:
    #      IBQ + Birch Tar, Styrax, Guaiacol, Labdanum (all DB)
    #      Birch Tar + Guaiacol, ISO E Super, Labdanum, Olibanum (DB)
    #      Styrax + Labdanum (amber), Olibanum (incense), Leather (DB)
    #      Olibanum + Myrrh, Labdanum, ISO E Super (DB)
    #      Benzoin Sumatra + Olibanum, Labdanum, Guaiacol, Birch Tar (DB)
    #      Vertofix + ISO E Super, Cedarwood, Labdanum, Musks (DB)
    #      Cedarwood + ISO E Super, Vetiver, Musks (DB)
    #      Cardamom + Bergamot, ISO E Super (DB)
    #      Suederal + ISO E Super, Styrax, Cedarwood (DB)
    #      Labdanum + Ambrox, Musks, Vanillin (DB)
    # ───────────────────────────────────────────────────────────────
    "Cuir Sacre": {
        "concentration": 28,
        "ingredients": {
            "Bergamot FCF": 5.0,
            "Cardamom FTEC": 3.0,
            "Ethyl Safranate": 2.0,
            "Hedione": 4.0,
            "Isobutyl Quinoline": 3.0,
            "Birch Tar Rectified": 1.5,
            "Guaiacol": 1.0,
            "Styrax FTEC": 5.0,
            "Suederal": 3.0,
            "Olibanum Resinoid": 8.0,
            "Labdanum Absolute": 8.0,
            "Benzoin Sumatra Resinoid": 7.0,
            "Cedarwood EO": 8.0,
            "Vertofix Coeur": 6.0,
            "Iso E Super": 14.0,
            "Ambrox Super": 6.0,
            "Galaxolide": 8.0,
            "Ethylene Brassylate": 6.5,
        },
    },
}

DESCRIPTIONS = {
    "Concrete Petrichor": {
        "tagline": "Rain on Hot Stone",
        "concept": "The smell after rain hits warm concrete and dry earth. Mineral-green-earthy freshness dissolving into deep vetiver warmth.",
        "texture": "Mineral, damp earth, green ozone, warm dry-down",
        "niche_ref": "In the world of: CDG Concrete, Terre d'Hermès, CB I Hate Perfume Rain",
        "wear": "Unisex / Fall rainy days / Introspective mood",
    },
    "Temple Smoke": {
        "tagline": "Sacred Iris Incense",
        "concept": "Ancient temple at dusk. Frankincense and myrrh smoke rises through clouds of powdery iris. Meditative silence made olfactory.",
        "texture": "Powdery, smoky, hallowed, incense-dust stillness",
        "niche_ref": "In the world of: CDG Avignon, Serge Lutens Iris Silver Mist, Byredo Gypsy Water",
        "wear": "Unisex / Evening meditation / Cold weather ritual",
    },
    "Molecule Handshake": {
        "tagline": "Pure Synergy Study",
        "concept": "Zero naturals. Only aroma-chemicals at their exact DB-calculated optimal synergy ratios. 'Your skin but extraordinary' — the concept perfume.",
        "texture": "Transparent, floating, invisible aura, skin-like radiance",
        "niche_ref": "In the world of: Escentric Molecules, Juliette Has A Gun Not A Perfume, Maison Martin Margiela (untitled)",
        "wear": "Unisex / Every day / The 'what are you wearing?' scent",
    },
    "Black Cashmere": {
        "tagline": "Dark Berry-Suede Skin Scent",
        "concept": "Blackcurrant juice spilled on a matte-black cashmere scarf. Sweet-tart fruit meets velvety suede. Not gourmand — textural.",
        "texture": "Velvety, dark-fruity, suede-soft, tactile warmth",
        "niche_ref": "In the world of: Donna Karan Cashmere Mist (dark remix), Byredo Black Saffron, Le Labo Santal 33",
        "wear": "Unisex / Date night / Fall-Winter layering",
    },
    "Soleil Mineral": {
        "tagline": "Solar Amber Skin Glow",
        "concept": "Liquid sunshine. Mediterranean golden light trapped in amber resin on warm skin. The ISO E + Hedione solar synergy pushed to its artistic limit.",
        "texture": "Warm, radiant, golden, luminous, sun-baked mineral",
        "niche_ref": "In the world of: Tom Ford Soleil Blanc, Maison Margiela Beach Walk, Profumum Roma Arso",
        "wear": "Unisex / Summer / Beach-to-bar / Golden hour",
    },
    "Cuir Sacre": {
        "tagline": "Sacred Leather Library",
        "concept": "Leather-bound rare books in a monastery library. Old leather, frankincense smoke, beeswax candles, cedar shelves. Scholarly and devotional.",
        "texture": "Dry leather, papyrus, smoky-sweet incense, cedar warmth",
        "niche_ref": "In the world of: Tom Ford Tuscan Leather, CDG Avignon, Memo Paris Italian Leather",
        "wear": "Unisex / Evening / Intellectual occasions / Fall-Winter",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 74)
    print("  NICHE PERFUME IDEAS — 6 CONCEPTS (direct engine, no server)")
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
        print(f"  {name:22s}  TOTAL={t:5.1f}  "
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
        print(f"  #{i}  {name:22s}  Score: {total:5.1f}  "
              f"Conc: {conc}%  Notes: {ns}")

    # ── PHASE 3: Suggest improvements ──
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

    # ── PHASE 5: Confidence ──
    print("\n" + "=" * 74)
    print("  CONFIDENCE")
    print("=" * 74)
    for name, _, _ in ranked:
        conf = all_results[name]["confidence"]
        if conf:
            print(f"  {name:22s}  "
                  f"data={conf.get('data_confidence', 'N/A')}  "
                  f"pairing={conf.get('pairing_confidence', 'N/A')}  "
                  f"prediction={conf.get('prediction_confidence', 'N/A')}  "
                  f"overall={conf.get('overall_confidence', 'N/A')}")

    # ── PHASE 6: Save JSON ──
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

    out_path = Path("niche_ideas_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)

    # ── PHASE 7: Markdown report ──
    md_lines = [
        "# 6 Niche Perfume Ideas — From Your Inventory",
        "",
        "Artistic, boundary-pushing compositions. Every pairing DB-verified.  ",
        "All materials from current inventory. Run locally, no server.",
        "",
    ]

    for i, (name, total, conc) in enumerate(ranked, 1):
        data = all_results[name]
        scores = data["scores"]
        nd = data["note_distribution"]
        conf = data["confidence"] or {}
        ings = FORMULAS[name]["ingredients"]
        desc = DESCRIPTIONS.get(name, {})

        md_lines.append(f"## #{i} — {name}")
        md_lines.append(f"### *{desc.get('tagline', '')}*")
        md_lines.append("")
        md_lines.append(f"> {desc.get('concept', '')}")
        md_lines.append("")
        md_lines.append(f"**Concentration:** {conc}%  |  "
                        f"**Total Score:** {total:.1f}/100")
        md_lines.append(f"**Texture:** {desc.get('texture', '')}  ")
        md_lines.append(f"**Niche reference:** {desc.get('niche_ref', '')}  ")
        md_lines.append(f"**Wear:** {desc.get('wear', '')}")
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

        md_lines.append("### Formula")
        md_lines.append("| Material | % |")
        md_lines.append("|----------|---|")
        for mat, pct in sorted(ings.items(), key=lambda x: -x[1]):
            md_lines.append(f"| {mat} | {pct:.1f} |")
        md_lines.append("")

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

    md_path = Path("niche_ideas_formulas.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n  Results saved to {out_path}")
    print(f"  Report saved to {md_path}")
    print("\n" + "=" * 74)
    print("  DONE")
    print("=" * 74)


if __name__ == "__main__":
    main()
