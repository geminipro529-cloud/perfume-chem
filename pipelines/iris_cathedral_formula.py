"""Iris Cathedral — 5 Wood Layers × 7 Musks × Opus V Iris Accord

A monumental iris fragrance built on five distinct wood textures and
seven macrocyclic/polycyclic musks.  The iris accord (Opus V style,
irone-forward, buttery, lipid) floats above a cathedral of layered
woods — pencil cedar, creamy sandalwood, velvet abstract, dark vetiver,
amber wood — while seven musks rise like heat from the stone beneath.

Design principle: accord-first architecture.  The iris accord is the
noblesse, the five woods provide structure/depth, and the musks create
an invisible skin-scent envelope.  Synergy is a bonus, not the
foundation.

Comparable to: Xerjoff Ibitira × Diptyque Tam Dao × Escentric Molecules 01
Nothing on the market stacks 5 wood layers + 7 musks behind iris.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.optimizer.models import (
    FormulaVector, ObjectiveWeights,
    get_materials_db, get_theory_rules,
    _lookup_material, classify_note,
)
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer


# ═══════════════════════════════════════════════════════════════════════════
# FORMULA DEFINITION
# ═══════════════════════════════════════════════════════════════════════════

IRIS_CATHEDRAL = [
    {
        "name": "Iris Cathedral — 5 Woods, 7 Musks",
        "concept": (
            "A monumental iris floating over five strata of wood and wrapped "
            "in seven musks.  Buttery Alpha Irone dominance (Opus V school) — "
            "not powdery Dior Homme style.  Each wood layer contributes a "
            "distinct texture: pencil-sharp cedar, creamy sandalwood, velvet "
            "abstract wood, smoky vetiver, and warm amber-wood.  The musk "
            "cloud is complex — clean, metallic, powdery, waxy, green, "
            "natural, and vintage — preventing any single musk character "
            "from dominating.  The iris should remain legible throughout "
            "all phases of evolution."
        ),
        "style": "Monumental Iris-Wood-Musk Architecture",
        "texture": "Buttery iris melting into layered wood grain, "
                   "wrapped in transparent musk haze",
        "pyramid": {
            "top": (
                "Bergamot FCF, Linalool, Hedione, "
                "Aldehyde C11 undecylenic"
            ),
            "heart": (
                "Alpha Irone (10%), Methyl Ionone, Beta Ionone, "
                "Alpha Ionone, AIMI, Orivone, Molecule Iris, "
                "Dihydro Beta Ionone, Carrot Seed EO, Coumarin (20%), "
                "Heliotropin Fleuressence, Benzyl Salicylate"
            ),
            "base": (
                "Cedarwood oil Virginia, Vertofix Coeur, Sandalore, "
                "Javanol, Iso E Super, Clearwood, Vetiver EO, Vetival, "
                "Cedramber, Amberwood F, Galaxolide (80%), Habanolide, "
                "Ambrettolide (10%), Exaltolide (10%), Macrolide (10%), "
                "Zenolide, Musk Ketone (10%), Benzyl Benzoate"
            ),
        },
        "ingredients": {
            # ── TOP (10%) — citrus-floral lift, diffusion ──
            "Bergamot FCF":              2.5,   # Citrus transparency
            "Linalool":                  1.5,   # Fresh floral connector
            "Hedione":                   5.5,   # Jasmine radiance, diffusion
            "Aldehyde C11 undecylenic":  0.5,   # Waxy-clean lift (trace)

            # ── HEART (45%) — Exact Opus V Iris Accord ×0.45 ──
            # (12 materials, ratio 25:18:12:8:10:2:5:6:3:6:3:2)
            "Alpha Irone (10%)":        11.0,   # Core — buttery orris (≈1.1% active)
            "Methyl Ionone":             8.0,   # Iris body, brightness
            "Beta Ionone":               5.5,   # Warm violet bloom
            "Alpha Ionone":              3.5,   # Fruity-violet facet
            "Alpha-Isomethyl Ionone (AIMI)": 4.5,  # Soft powder envelope
            "Orivone":                   1.0,   # Metallic iris edge
            "Molecule Iris":             2.5,   # Abstract iris support
            "Dihydro Beta Ionone":       2.5,   # Woody-violet tenacity
            "Carrot Seed EO":            1.5,   # Earthy orris rootiness
            "Coumarin (20%)":            2.5,   # Powdery tonka warmth (≈0.5% active)
            "Heliotropin Fleuressence":  1.5,   # Cherry-almond powder
            "Benzyl Salicylate":         1.0,   # Balsamic fixative (accord lock)

            # ── BASE — WOOD LAYER 1: Pencil Cedar (5%) ──
            "Cedarwood oil Virginia":    3.0,   # Dry, sharp pencil-wood
            "Vertofix Coeur":            2.0,   # Woody-amber fixative

            # ── BASE — WOOD LAYER 2: Creamy Sandalwood (5%) ──
            "Sandalore":                 3.0,   # Creamy sandalwood milk
            "Javanol":                   2.0,   # Modern sandalwood, skin-close

            # ── BASE — WOOD LAYER 3: Velvet Abstract (5%) ──
            "Iso E Super":               3.0,   # Woody velvet halo (anosmic shimmer)
            "Clearwood":                 2.0,   # Transparent patchouli-wood

            # ── BASE — WOOD LAYER 4: Dark Vetiver (4%) ──
            "Vetiver EO":                2.5,   # Smoky earth, wet roots
            "Vetival":                   1.5,   # Vetiver extender, darker

            # ── BASE — WOOD LAYER 5: Amber Wood (6%) ──
            "Cedramber":                 3.0,   # Warm amber-cedar hybrid
            "Amberwood F":               3.0,   # Resinous golden wood floor

            # ── BASE — THE 7-MUSK CLOUD (18%) ──
            "Galaxolide (80%)":          4.0,   # Clean white cotton (≈3.2% active)
            "Habanolide":                3.0,   # Modern skin, metallic edge
            "Ambrettolide (10%)":        2.5,   # Natural, seedy warmth (≈0.25% active)
            "Exaltolide (10%)":          2.0,   # Classic powdery macrocyclic (≈0.2% active)
            "Macrolide (10%)":           2.0,   # Waxy, slightly animalic (≈0.2% active)
            "Zenolide":                  2.5,   # Fresh, transparent, green musk
            "Musk Ketone (10%)":         2.0,   # Vintage nitro warmth (≈0.2% active)

            # ── BASE — FIXATIVE (2%) ──
            "Benzyl Benzoate":           2.0,   # Fixative, blender
        },
        "theory_notes": {
            "roudnitska": (
                "Noblesse: Alpha Irone — the expensive, noble iris character. "
                "Éclat: Hedione + Linalool — radiance and sparkle. "
                "Transparence: ISO E Super + Clearwood — airy woody veil. "
                "Chaleur: Cedramber + Amberwood F + Musk Ketone — warmth. "
                "Peau: 7-musk cloud (Galaxolide through Musk Ketone) — skin. "
                "Profondeur: Vetiver EO + Vetival + Vertofix — anchoring depth."
            ),
            "carles": (
                "Top:Heart:Base = 10:45:45.  Heart-dominant pyramid biased "
                "toward base — correct for iris, which needs massive base "
                "anchor since ionones are volatile.  The 5 wood layers + "
                "7 musks give 45% base mass, ensuring 8-12 hour longevity "
                "with continuous iris readability."
            ),
            "jellinek": (
                "Lower-left quadrant (erogenic/narcotic): warm, skin-close, "
                "intimate via amber wood + musks.  The iris adds cool/powder "
                "counter-tension, pulling toward upper-left (rational/fresh).  "
                "Net effect: sophisticated and intimate, not cold or clinical."
            ),
            "texture_mechanism": (
                "5 wood layers create distinct molecular-weight bands: "
                "lighter terpenes (Cedarwood Virginia) → mid-MW santalols "
                "(Sandalore, Javanol) → abstract C15+ molecules (ISO E, "
                "Clearwood) → sesquiterpenes (Vetiver) → heavy amber-wood "
                "synthetics (Cedramber, Amberwood F).  This MW cascade "
                "ensures continuous wood character from first spray to "
                "drydown.  The 7-musk cloud uses 4 macrocyclics + 1 "
                "polycyclic + 1 nitro + 1 natural-type to prevent any "
                "single musk signature from homogenizing the base."
            ),
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: Theory Provenance
# ═══════════════════════════════════════════════════════════════════════════

def theory_provenance(fv: FormulaVector) -> dict:
    """Show which classical perfumery principles are fulfilled."""
    theory = get_theory_rules()

    _ROUD_KEYWORDS = {
        "transparence": ["transparenc", "clean", "airy", "sheer"],
        "chaleur":      ["chaleur", "warmth", "warm", "body"],
        "noblesse":     ["noblesse", "noble", "precious", "rare"],
        "peau":         ["peau", "skin", "soft", "musk"],
        "eclat":        ["eclat", "bright", "sparkle", "radianc"],
        "profondeur":   ["profondeur", "depth", "anchor", "fixat"],
    }
    roles = {}
    for name in fv.ingredient_list():
        mat = _lookup_material(name)
        if mat and mat.get("roudnitska_function"):
            func = mat["roudnitska_function"].lower()
            for role, keywords in _ROUD_KEYWORDS.items():
                for kw in keywords:
                    if kw in func:
                        roles.setdefault(role, []).append(name)
                        break

    quads = {}
    jellinek = theory.get("jellinek_map", {}).get("quadrants", {})
    for name in fv.ingredient_list():
        mat = _lookup_material(name)
        if mat and mat.get("jellinek_quadrant"):
            q = mat["jellinek_quadrant"].lower()
            for qk in jellinek:
                if (qk.replace("_", "-") in q
                        or jellinek[qk].get("name", "").lower() in q):
                    quads.setdefault(
                        jellinek[qk].get("name", qk), []
                    ).append(name)

    positions = {"top": [], "heart": [], "base": []}
    for name in fv.ingredient_list():
        positions[classify_note(name)].append(name)

    sar = {}
    for name in fv.ingredient_list():
        mat = _lookup_material(name)
        if mat and mat.get("sar_class"):
            sar.setdefault(mat["sar_class"], []).append(name)

    all_roud = [
        "transparence", "chaleur", "noblesse",
        "peau", "eclat", "profondeur",
    ]

    return {
        "roudnitska_roles": roles,
        "roudnitska_missing": [r for r in all_roud if r not in roles],
        "jellinek_quadrants": quads,
        "carles_distribution": {k: len(v) for k, v in positions.items()},
        "sar_classes": len(sar),
        "sar_detail": sar,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("IRIS CATHEDRAL — 5 WOODS × 7 MUSKS PIPELINE")
    print("=" * 72)

    # ── Initialize engines ──
    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    conf_scorer = ConfidenceScorer()

    results = []

    for design in IRIS_CATHEDRAL:
        print(f"\n{'─' * 72}")
        print(f"  {design['name']}")
        print(f"  Texture: {design['texture']}")
        print(f"  Style:   {design['style']}")
        print(f"{'─' * 72}")
        print(f"\n{design['concept']}\n")

        # ── 1. Build FormulaVector ──
        fv = FormulaVector(ingredients=dict(design["ingredients"]))
        total = fv.total_pct
        dist = fv.note_distribution()

        print(f"▸ Formula: {total:.1f}%  "
              f"({len(design['ingredients'])} materials)")
        print(f"  Top {dist['top']:.0f}%  |  "
              f"Heart {dist['heart']:.0f}%  |  "
              f"Base {dist['base']:.0f}%")

        # ── Inventory verification ──
        print(f"\n▸ Material Verification:")
        inv_path = Path(__file__).parent / "inventory.txt"
        if inv_path.exists():
            inv_text = inv_path.read_text(encoding="utf-8").lower()
            missing = []
            for name in sorted(design["ingredients"]):
                # Strip dilution markers for lookup
                lookup = name.split("(")[0].strip().lower()
                if lookup not in inv_text:
                    missing.append(name)
            if missing:
                print(f"  ✗ MISSING from inventory: {', '.join(missing)}")
            else:
                print(f"  ✓ All {len(design['ingredients'])} materials "
                      f"confirmed in inventory")
        else:
            print(f"  ⚠ inventory.txt not found — skipping check")

        # ── Wood layer breakdown ──
        wood_layers = {
            "Layer 1 — Pencil Cedar":       ["Cedarwood oil Virginia",
                                              "Vertofix Coeur"],
            "Layer 2 — Creamy Sandalwood":   ["Sandalore", "Javanol"],
            "Layer 3 — Velvet Abstract":     ["Iso E Super", "Clearwood"],
            "Layer 4 — Dark Vetiver":        ["Vetiver EO", "Vetival"],
            "Layer 5 — Amber Wood":          ["Cedramber", "Amberwood F"],
        }
        print(f"\n▸ Wood Architecture:")
        total_wood = 0.0
        for layer_name, mats in wood_layers.items():
            layer_pct = sum(design["ingredients"].get(m, 0) for m in mats)
            total_wood += layer_pct
            print(f"  {layer_name}: {layer_pct:.1f}%  "
                  f"({', '.join(mats)})")
        print(f"  Total wood: {total_wood:.1f}%")

        # ── Musk cloud breakdown ──
        musk_names = [
            "Galaxolide (80%)", "Habanolide", "Ambrettolide (10%)",
            "Exaltolide (10%)", "Macrolide (10%)", "Zenolide",
            "Musk Ketone (10%)",
        ]
        print(f"\n▸ Musk Cloud ({len(musk_names)} musks):")
        total_musk = 0.0
        for m in musk_names:
            pct = design["ingredients"].get(m, 0)
            total_musk += pct
            print(f"  {m}: {pct:.1f}%")
        print(f"  Total musk: {total_musk:.1f}%")

        # ── 2. Score on 6 axes (INITIAL) ──
        scores = scorer.score(fv)
        print(f"\n▸ Initial 6-Axis Score: {scores['total']:.1f}")
        print(f"  balance    = {scores['balance']:.1f}  (Carles pyramid)")
        print(f"  theory     = {scores['theory']:.1f}  "
              f"(Roudnitska, Jellinek, SAR, Arctander)")
        print(f"  longevity  = {scores['longevity']:.1f}  "
              f"(MW, CLP, base %)")
        print(f"  sillage    = {scores['sillage']:.1f}  "
              f"(VP, diffusion boosters)")
        print(f"  synergy    = {scores['synergy']:.1f}  (pairing rules)")
        print(f"  cost       = {scores['cost']:.1f}  (material economics)")

        # ── 3. Optimize ──
        result = optimizer.optimize(fv)
        opt = result.scores
        delta = result.total_score - scores["total"]

        print(f"\n▸ After Optimization: {result.total_score:.1f} "
              f"({delta:+.1f})")
        print(f"  balance    = {opt['balance']:.1f}")
        print(f"  theory     = {opt['theory']:.1f}")
        print(f"  longevity  = {opt['longevity']:.1f}")
        print(f"  sillage    = {opt['sillage']:.1f}")
        print(f"  synergy    = {opt['synergy']:.1f}")
        print(f"  cost       = {opt['cost']:.1f}")

        if result.suggestions:
            print(f"\n▸ Optimizer Suggestions:")
            for sug in result.suggestions[:8]:
                print(f"  • {sug}")

        # ── 4. Confidence scoring ──
        conf = conf_scorer.score(fv.ingredients)
        print(f"\n▸ Confidence: {conf['confidence_grade']}  "
              f"(overall={conf['overall_confidence']:.0f}%)")
        print(f"  data_confidence    = {conf['data_confidence']:.0f}  "
              f"(material profiles)")
        print(f"  pairing_confidence = {conf['pairing_confidence']:.0f}  "
              f"(pair coverage)")
        print(f"  prediction_conf    = {conf['prediction_confidence']:.0f}  "
              f"(historical data)")

        # ── 5. Theory provenance ──
        prov = theory_provenance(fv)

        roud = list(prov["roudnitska_roles"].keys())
        missing_roles = prov["roudnitska_missing"]
        jell = list(prov["jellinek_quadrants"].keys())

        print(f"\n▸ Theory Provenance:")
        print(f"  Roudnitska roles filled: "
              f"{', '.join(roud) if roud else 'none'} "
              f"({len(roud)}/6)")
        if missing_roles:
            print(f"  Missing roles:           "
                  f"{', '.join(missing_roles)}")
        print(f"  Jellinek quadrants:      "
              f"{', '.join(jell) if jell else 'none'}")
        print(f"  SAR classes:             {prov['sar_classes']}")
        c = prov["carles_distribution"]
        print(f"  Carles materials:        "
              f"top={c['top']}  heart={c['heart']}  base={c['base']}")

        # ── 6. Pyramid metadata ──
        pyramid = {"top": [], "heart": [], "base": []}
        for name in fv.ingredient_list():
            pyramid[classify_note(name)].append(name)

        # ── 7. Collect results ──
        results.append({
            "name": design["name"],
            "concept": design["concept"],
            "style": design["style"],
            "texture": design["texture"],
            "pyramid": {
                k: ", ".join(v) for k, v in pyramid.items()
            },
            "ingredients": fv.ingredients,
            "total_pct": round(total, 1),
            "note_distribution": dist,
            "wood_layers": {
                ln: {m: design["ingredients"].get(m, 0) for m in ms}
                for ln, ms in wood_layers.items()
            },
            "musk_cloud": {
                m: design["ingredients"].get(m, 0) for m in musk_names
            },
            "initial_scores": scores,
            "optimized_scores": opt,
            "optimized_total": result.total_score,
            "suggestions": result.suggestions,
            "confidence": conf,
            "theory_provenance": prov,
            "theory_notes": design["theory_notes"],
        })

    # ═══════════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════════
    print(f"\n\n{'═' * 72}")
    print("SAVING RESULTS")
    print(f"{'═' * 72}")

    output_json = Path(__file__).parent / "iris_cathedral_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✓ {output_json.name}")

    output_md = Path(__file__).parent / "iris_cathedral_results.md"
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("# Iris Cathedral — 5 Woods × 7 Musks\n\n")
        f.write("## Scoring Weights (Theory-First)\n\n")
        f.write("| Axis | Weight | Source |\n|------|--------|--------|\n")
        f.write(f"| Balance | ×{weights.balance} | Jean Carles |\n")
        f.write(f"| Theory | ×{weights.theory} | "
                f"Roudnitska, Jellinek, OPK, Arctander |\n")
        f.write(f"| Longevity | ×{weights.longevity} | "
                f"Physical chemistry |\n")
        f.write(f"| Sillage | ×{weights.sillage} | "
                f"Physical chemistry |\n")
        f.write(f"| Synergy | ×{weights.synergy} | *bonus only* |\n")
        f.write(f"| Cost | ×{weights.cost} | Material economics |\n\n")

        for entry in results:
            s = entry["optimized_scores"]
            f.write(f"## {entry['name']}\n\n")
            f.write(f"**Optimized Total**: {entry['optimized_total']:.1f}\n")
            f.write(f"**Confidence**: {entry['confidence']['confidence_grade']}"
                    f" ({entry['confidence']['overall_confidence']:.0f}%)\n\n")

            f.write("### 6-Axis Scores\n\n")
            f.write("| Axis | Score |\n|------|-------|\n")
            for axis in ["balance", "theory", "longevity",
                         "sillage", "synergy", "cost"]:
                f.write(f"| {axis} | {s[axis]:.1f} |\n")

            f.write("\n### Wood Architecture\n\n")
            f.write("| Layer | Materials | % |\n"
                    "|-------|-----------|---|\n")
            for ln, mats in entry["wood_layers"].items():
                mat_str = ", ".join(mats.keys())
                pct = sum(mats.values())
                f.write(f"| {ln} | {mat_str} | {pct:.1f} |\n")

            f.write("\n### Musk Cloud\n\n")
            f.write("| Musk | % |\n|------|---|\n")
            for m, p in entry["musk_cloud"].items():
                f.write(f"| {m} | {p:.1f} |\n")

            f.write("\n### Full Formula\n\n")
            f.write("| Material | % |\n|----------|---|\n")
            for mat, pct in sorted(entry["ingredients"].items(),
                                   key=lambda x: -x[1]):
                f.write(f"| {mat} | {pct:.1f} |\n")

            f.write("\n### Theory Notes\n\n")
            for key, val in entry["theory_notes"].items():
                f.write(f"**{key.title()}:** {val}\n\n")

            f.write("---\n\n")

    print(f"✓ {output_md.name}")
    print(f"\n{'─' * 72}")
    print("COMPLETE")
    print(f"{'─' * 72}")


if __name__ == "__main__":
    main()
