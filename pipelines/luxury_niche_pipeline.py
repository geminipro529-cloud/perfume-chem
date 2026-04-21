"""Luxury Niche Perfume Pipeline — 5 Hand-Curated Formulas

Uses the best materials from inventory, built on accords from the library,
scored and optimized by the theory-first engine.

Each perfume is designed around:
  1. Accords from perfume_accord_library.txt (foundation)
  2. Premium star materials (character)
  3. Classical theory (Carles method, Roudnitska roles, Jellinek map)
  4. Synergy as bonus only
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from engine.optimizer.models import (
    FormulaVector, ObjectiveWeights,
    get_materials_db, get_theory_rules,
    _lookup_material, classify_note,
)
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer
from accord_pipeline import theory_provenance


# ═══════════════════════════════════════════════════════════════════════════
# 5 LUXURY NICHE PERFUME DESIGNS
# ═══════════════════════════════════════════════════════════════════════════
#
# Each design specifies:
#   name       — luxury house style name
#   concept    — creative brief
#   style      — reference fragrances in the same territory
#   pyramid    — Carles-method note architecture
#   ingredients — full formula (% of concentrate, totals 100%)
#   theory     — which frameworks justify each choice
#
# Design principles:
#   - Accords from library as foundations (not ad-hoc combos)
#   - Premium materials as stars and modifiers
#   - Roudnitska: aim for all 6 roles covered
#   - Carles: ~20% top / ~35-40% heart / ~40-45% base
#   - Jellinek: span 2-3 quadrants minimum
#   - A "twist" ingredient for memorability (Calkin & Jellinek principle)

LUXURY_FORMULAS = [
    # ─────────────────────────────────────────────────────────────────────
    # 1. IRIS IMPÉRIALE — Powdery Iris + Amber + Neroli
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Iris Impériale",
        "concept": "A regal iris built on the Iris Luxury Base accord, "
                   "crowned with true Alpha Irone and lifted by Sicilian "
                   "bergamot and neroli. Warm amber base wraps the "
                   "composition in skin-like radiance.",
        "style": "Dior Homme Parfum / Armani Privé Iris Céladon",
        "pyramid": {
            "top": "Bergamot FCF oil Sicilian, Neroli EO, Linalool",
            "heart": "Alpha Irone, Methyl Ionone, Beta Ionone, Orivone, "
                     "Hedione, Heliotropin Fleuressence",
            "base": "Ambrox Super, Iso E Super, Cashmeran, Benzoin Resinoid, "
                    "Labdanum Absolute, Coumarin, Habanolide, Ethylene Brassylate",
        },
        "ingredients": {
            # TOP — éclat + transparence (~18%)
            "Bergamot FCF oil Sicilian": 7.0,  # Eclat: citrus sparkle, projection
            "Neroli EO": 6.0,                   # Noblesse: precious floral lift
            "Linalool": 5.0,                     # Transparence: airy freshness

            # HEART — noblesse + character (~37%)
            "Alpha Irone (10%)": 8.0,            # Noblesse: true orris butter (0.8% active)
            "Methyl Ionone": 10.0,               # Iris body, violet-powdery
            "Beta Ionone": 5.0,                   # Iris-violet woody facet
            "Orivone": 4.0,                       # Iris radiance, pure chemical
            "Hedione": 7.0,                      # Transparence: jasmine lift, diffusion
            "Heliotropin Fleuressence": 3.0,     # Powdery-sweet bridge to base

            # BASE — chaleur + peau + profondeur (~45%)
            "Ambrox Super (30%)": 12.0,          # Peau: amber radiance (3.6% active)
            "Iso E Super": 8.0,                  # Peau: woody velvet aura
            "Cashmeran (20%)": 5.0,              # Peau: cashmere warmth (1% active)
            "Benzoin Resinoid (50% in DPG)": 5.0,# Chaleur: balsamic depth (2.5% active)
            "Labdanum Absolute (10%)": 4.0,      # Chaleur: warm amber leather (0.4% active)
            "Coumarin (20%)": 4.0,               # Chaleur: powdery tonka (0.8% active)
            "Habanolide": 4.0,                   # Peau: clean macrocyclic musk
            "Ethylene Brassylate": 3.0,          # Profondeur: powdery fixative musk
        },
        "theory_notes": {
            "roudnitska": "All 6 roles: eclat (bergamot), transparence (hedione/linalool), "
                          "noblesse (alpha irone/neroli), peau (ambrox/cashmeran/iso e super), "
                          "chaleur (benzoin/labdanum/coumarin), profondeur (ethylene brassylate)",
            "carles": "Top 18% / Heart 37% / Base 45% — ideal luxury distribution",
            "jellinek": "Cool-Narcotic (iris/violet) + Warm-Narcotic (amber/musk) + "
                        "Fresh-Stimulating (citrus/neroli) = 3 quadrants",
            "twist": "Neroli EO — adds an unexpected bitter-floral transparency to "
                     "what could be a heavy iris-amber. Creates the 'luxury lift'.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 2. ENCENS SACRÉ — Sacred Incense + Dark Leather
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Encens Sacré",
        "concept": "Ancient temple smoke layered on dark leather. Built on "
                   "the Incense-Resin Base accord with Leather Dark elements, "
                   "starring Olibanum Resinoid and Myrrh. Ethyl Safranate "
                   "adds a precious saffron thread.",
        "style": "CdG Avignon / Tom Ford Ombré Leather / Tauer L'Air du Désert",
        "pyramid": {
            "top": "Bergamot FCF, Cardamom FTEC, Ethyl Safranate, Pink Pepper Base",
            "heart": "Olibanum Resinoid, Myrrh EO, Styrax FTEC, Hedione",
            "base": "Labdanum Absolute, Birch Tar Rectified, Iso E Super, "
                    "Benzoin Sumatra Resinoid, Cashmeran, Patchouli EO, "
                    "Guaiacol, Ambrox Super, Galaxolide",
        },
        "ingredients": {
            # TOP — éclat + stimulation (~17%)
            "Bergamot FCF": 5.0,                 # Eclat: citrus opening
            "Cardamom FTEC (10%)": 4.0,          # Stimulating spice (0.4% active)
            "Ethyl Safranate": 4.0,              # Noblesse: precious saffron
            "Pink Pepper Base": 4.0,             # Eclat: rosy-spice sparkle

            # HEART — sacred smoke (~28%)
            "Olibanum Resinoid": 12.0,           # Noblesse: frankincense core
            "Myrrh EO": 6.0,                     # Profondeur: warm balsamic depth
            "Styrax FTEC": 5.0,                  # Chaleur: balsamic resin
            "Hedione": 5.0,                      # Transparence: diffusion, keeps it breathable

            # BASE — dark leather + depth (~55%)
            "Labdanum Absolute (10%)": 8.0,      # Chaleur: warm amber-leather (0.8% active)
            "Birch Tar Rectified": 3.0,          # Profondeur: smoky campfire leather
            "Iso E Super": 10.0,                 # Peau: woody velvet blender
            "Benzoin Sumatra Resinoid (10%)": 6.0,# Chaleur: smoky-balsamic (0.6% active)
            "Cashmeran (20%)": 5.0,              # Peau: cashmere warmth (1% active)
            "Patchouli EO": 5.0,                 # Profondeur: earthy grounding
            "Guaiacol": 2.0,                     # Profondeur: smoke reinforcement
            "Ambrox Super (30%)": 8.0,           # Peau: amber radiance (2.4% active)
            "Galaxolide (80%)": 4.0,             # Peau: musk base (3.2% active)
            "Coumarin (20%)": 3.0,               # Chaleur: powdery warmth (0.6% active)
        },
        "theory_notes": {
            "roudnitska": "All 6 roles: eclat (bergamot/pink pepper), "
                          "transparence (hedione), noblesse (olibanum/safranate), "
                          "peau (iso e super/cashmeran/ambrox/galaxolide), "
                          "chaleur (labdanum/benzoin/styrax/coumarin), "
                          "profondeur (birch tar/patchouli/myrrh/guaiacol)",
            "carles": "Top 17% / Heart 28% / Base 55% — heavy base for an oriental/incense",
            "jellinek": "Warm-Narcotic (resins/amber) + Warm-Stimulating (spices/pepper) + "
                        "Fresh-Stimulating (bergamot) = 3 quadrants",
            "twist": "Ethyl Safranate — adds a precious metallic-saffron glint that "
                     "lifts the dark incense-leather into luxury territory.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 3. TERRE PROFONDE — Vetiver + Cedar + Amber
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Terre Profonde",
        "concept": "Earth after rain. Built on the Vetiver Earthy Base "
                   "accord with premium woods (Clearwood, Javanol) and "
                   "amber radiance. Galbanum and grapefruit create a "
                   "bitter-green opening. Norlimbanol anchors the dry-down.",
        "style": "Chanel Sycomore / Terre d'Hermès Parfum / Vetiver Extraordinaire",
        "pyramid": {
            "top": "Grapefruit FCF, Bergamot FCF oil Sicilian, "
                   "Galbanum Resinoid, Dihydromyrcenol",
            "heart": "Vetiver EO, Clearwood, Javanol, Hedione, Geraniol",
            "base": "Cedarwood oil Virginia, Iso E Super, Cedramber, Ambrox Super, "
                    "Patchouli EO, Vertofix Coeur, Norlimbanol Dextro, "
                    "Cashmeran, Habanolide",
        },
        "ingredients": {
            # TOP — green-bitter éclat (~18%)
            "Grapefruit FCF": 5.0,               # Eclat: bitter citrus
            "Bergamot FCF oil Sicilian": 5.0,     # Eclat: citrus sparkle
            "Galbanum Resinoid (10%)": 4.0,       # Transparence: green bitter edge (0.4% active)
            "Dihydromyrcenol": 4.0,               # Transparence: metallic freshness

            # HEART — earthy-woody character (~30%)
            "Vetiver EO": 10.0,                   # Profondeur: earthy-smoky core
            "Clearwood": 6.0,                     # Profondeur: sustainable patchouli-woody
            "Javanol": 5.0,                       # Noblesse: premium sandalwood
            "Hedione": 5.0,                       # Transparence: jasmine diffusion
            "Geraniol": 4.0,                      # Eclat: green-rosy bridge

            # BASE — woody-amber depth (~52%)
            "Cedarwood oil Virginia": 8.0,        # Profondeur: dry pencil-shaving cedar
            "Iso E Super": 10.0,                  # Peau: woody-amber aura
            "Cedramber": 6.0,                     # Chaleur: rich warm cedar
            "Ambrox Super (30%)": 7.0,            # Peau: amber radiance (2.1% active)
            "Patchouli EO": 5.0,                  # Profondeur: earthy depth
            "Vertofix Coeur": 5.0,                # Profondeur: cedar heartwood persistence
            "Norlimbanol Dextro (1%)": 3.0,       # Profondeur: woody fixation (0.03% active)
            "Cashmeran (20%)": 4.0,               # Peau: cashmere warmth (0.8% active)
            "Habanolide": 4.0,                    # Peau: clean musk fixative
        },
        "theory_notes": {
            "roudnitska": "All 6 roles: eclat (grapefruit/bergamot/geraniol), "
                          "transparence (galbanum/dihydromyrcenol/hedione), "
                          "noblesse (javanol/vetiver), "
                          "peau (iso e super/ambrox/cashmeran/habanolide), "
                          "chaleur (cedramber), "
                          "profondeur (vetiver/patchouli/cedarwood/clearwood/vertofix/norlimbanol)",
            "carles": "Top 18% / Heart 30% / Base 52% — earthy-woody skews base-heavy",
            "jellinek": "Fresh-Stimulating (citrus/green) + Cool-Narcotic (vetiver/woody) + "
                        "Warm-Narcotic (amber/cedar) = 3 quadrants",
            "twist": "Galbanum Resinoid — adds a bitter, almost metallic green flash "
                     "that makes the vetiver feel alive and modern, not muddy.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 4. OR LIQUIDE — Saffron + Amber + Musk
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Or Liquide",
        "concept": "Liquid gold. Built on the Amber Radiant Base accord, "
                   "lifted by saffron (Ethyl Safranate) and enriched with "
                   "Iris powdery notes. A touch of gourmand sweetness from "
                   "benzoin and tonka. Romandolide projects the amber trail.",
        "style": "MFK Baccarat Rouge 540 / Amouage Jubilation / Xerjoff Alexandria II",
        "pyramid": {
            "top": "Cedrat FCF oil Sicilian, Blood Orange oil Sicilian, "
                   "Ethyl Safranate",
            "heart": "Hedione, Alpha Irone, Molecule Iris, Benzyl Salicylate, "
                     "Cyclamen Aldehyde",
            "base": "Ambrox Super, Iso E Super, Labdanum Absolute, "
                    "Benzoin Resinoid, Vanillin, Coumarin, Ethyl Maltol, "
                    "Amber Xtreme, Romandolide, Ethylene Brassylate",
        },
        "ingredients": {
            # TOP — precious sparkle (~16%)
            "Cedrat FCF oil Sicilian": 5.0,      # Eclat: lemon-citrus brightness
            "Blood Orange oil Sicilian": 4.0,     # Eclat: juicy blood orange
            "Ethyl Safranate": 4.0,               # Noblesse: precious saffron-metallic
            "Linalool": 3.0,                      # Transparence: fresh floral bridge

            # HEART — powdery-iris amber heart (~26%)
            "Hedione": 8.0,                       # Transparence: jasmine radiance, massive diffusion
            "Alpha Irone (10%)": 5.0,             # Noblesse: orris butter (0.5% active)
            "Molecule Iris": 4.0,                 # Noblesse: abstract iris
            "Benzyl Salicylate": 5.0,             # Chaleur: balsamic blender
            "Cyclamen Aldehyde": 4.0,             # Transparence: powdery transparent muguet

            # BASE — amber radiance + gourmand (~58%)
            "Ambrox Super (30%)": 14.0,           # Peau: primary amber radiance (4.2% active)
            "Iso E Super": 10.0,                  # Peau: woody-amber aura
            "Labdanum Absolute (10%)": 5.0,       # Chaleur: warm amber leather (0.5% active)
            "Benzoin Resinoid (50% in DPG)": 5.0, # Chaleur: balsamic vanilla (2.5% active)
            "Vanillin (10%)": 4.0,                # Chaleur: creamy sweetness (0.4% active)
            "Coumarin (20%)": 4.0,                # Chaleur: powdery tonka (0.8% active)
            "Ethyl Maltol (10%)": 2.0,            # Chaleur: subliminal cotton candy (0.2% active)
            "Amber Xtreme": 4.0,                  # Peau: modern amber molecule
            "Romandolide": 5.0,                   # Peau: projecting musk
            "Ethylene Brassylate": 4.0,           # Profondeur: powdery musk fixation
        },
        "theory_notes": {
            "roudnitska": "All 6 roles: eclat (cedrat/blood orange), "
                          "transparence (hedione/cyclamen aldehyde/linalool), "
                          "noblesse (alpha irone/safranate/molecule iris), "
                          "peau (ambrox/iso e super/amber xtreme/romandolide), "
                          "chaleur (labdanum/benzoin/vanillin/coumarin/ethyl maltol), "
                          "profondeur (ethylene brassylate/benzyl salicylate)",
            "carles": "Top 16% / Heart 26% / Base 58% — classic oriental distribution",
            "jellinek": "Warm-Narcotic (amber/vanilla/musk) + Cool-Narcotic (iris/powdery) + "
                        "Fresh-Stimulating (citrus) = 3 quadrants",
            "twist": "Cyclamen Aldehyde — adds a watery, almost metallic transparency "
                     "that prevents the amber-gourmand from becoming cloying.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 5. CUIR SAUVAGE — Smoky Leather + Spice + Dark Woods
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Cuir Sauvage",
        "concept": "Untamed leather. Built on the Leather Dark Base accord "
                   "with Peppery-Spice accents, dark woods (Clearwood, Vetiver), "
                   "and resinous smoke. Birch tar and Styrax for authenticity. "
                   "Blood orange adds a feral, animalic opening.",
        "style": "Tom Ford Tuscan Leather / Parfums de Marly Herod / "
                 "Memo African Leather",
        "pyramid": {
            "top": "Blood Orange oil Sicilian, Black Pepper FTEC, "
                   "Pink Pepper Base, Bergamot FCF",
            "heart": "Styrax FTEC, Olibanum Resinoid, Hedione, Geraniol, "
                     "Isobutyl Quinoline",
            "base": "Birch Tar Rectified, Labdanum Absolute, Iso E Super, "
                    "Cashmeran, Clearwood, Vetiver EO, Suederal, "
                    "Ambrox Super, Vanillin, Benzyl Benzoate",
        },
        "ingredients": {
            # TOP — blood + spice (~18%)
            "Blood Orange oil Sicilian": 5.0,    # Eclat: juicy, slightly feral
            "Black Pepper FTEC": 4.0,            # Eclat: warm dark pepper
            "Pink Pepper Base": 4.0,             # Eclat: rosy-spicy brightness
            "Bergamot FCF": 5.0,                 # Eclat: citrus bridge

            # HEART — leather + smoke (~27%)
            "Styrax FTEC": 7.0,                  # Chaleur: balsamic leather warmth
            "Olibanum Resinoid": 5.0,            # Noblesse: sacred frankincense
            "Hedione": 5.0,                      # Transparence: breathing room
            "Geraniol": 4.0,                     # Eclat: rosy-green bridge
            "Isobutyl Quinoline (10%)": 3.0,     # Noblesse: bitter leather (0.3% active)
            "Eugenol": 3.0,                      # Chaleur: clove warmth, spice bridge

            # BASE — dark leather + woods (~55%)
            "Birch Tar Rectified": 4.0,          # Profondeur: smoky campfire leather
            "Labdanum Absolute (10%)": 6.0,      # Chaleur: warm amber-leather (0.6% active)
            "Iso E Super": 10.0,                 # Peau: woody velvet blender
            "Cashmeran (20%)": 5.0,              # Peau: cashmere comfort (1% active)
            "Clearwood": 5.0,                    # Profondeur: sustainable patchouli-clean
            "Vetiver EO": 5.0,                   # Profondeur: earthy smoky depth
            "Suederal (10%)": 4.0,               # Peau: suede texture (0.4% active)
            "Ambrox Super (30%)": 7.0,           # Peau: amber radiance (2.1% active)
            "Vanillin (10%)": 3.0,               # Chaleur: sweetness smoothing (0.3% active)
            "Benzyl Benzoate": 3.0,              # Fixative
            "Coumarin (20%)": 3.0,               # Chaleur: powdery warmth (0.6% active)
        },
        "theory_notes": {
            "roudnitska": "All 6 roles: eclat (blood orange/bergamot/pepper/geraniol), "
                          "transparence (hedione), noblesse (olibanum/IBQ), "
                          "peau (iso e super/cashmeran/suederal/ambrox), "
                          "chaleur (styrax/labdanum/vanillin/eugenol/coumarin), "
                          "profondeur (birch tar/clearwood/vetiver)",
            "carles": "Top 18% / Heart 27% / Base 55% — heavy base for tenacious leather",
            "jellinek": "Warm-Narcotic (leather/amber) + Warm-Stimulating (spice/pepper) + "
                        "Fresh-Stimulating (citrus/green) = 3 quadrants",
            "twist": "Blood Orange Sicilian — adds a raw, almost animalic citrus "
                     "that evokes sun-baked leather rather than clean cologne.",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════

def build_formula_vector(design: dict) -> FormulaVector:
    """Convert a design dict into a FormulaVector for scoring."""
    fv = FormulaVector()
    fv.ingredients = dict(design["ingredients"])
    return fv


def main():
    print("=" * 70)
    print("LUXURY NICHE PERFUME COLLECTION")
    print("5 Hand-Curated Formulas — Theory-First, Accord-Built")
    print("=" * 70)

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    conf_scorer = ConfidenceScorer()

    results = []

    for i, design in enumerate(LUXURY_FORMULAS, 1):
        print(f"\n{'─' * 70}")
        print(f"  {i}. {design['name'].upper()}")
        print(f"{'─' * 70}")
        print(f"  Style: {design['style']}")
        print(f"  Concept: {design['concept'][:100]}...")

        # Build FormulaVector
        fv = build_formula_vector(design)
        total = fv.total_pct
        dist = fv.note_distribution()
        print(f"\n  Ingredients: {len(fv.ingredients)}")
        print(f"  Total: {total:.1f}%")
        print(f"  Pyramid: top={dist['top']:.0f}% heart={dist['heart']:.0f}% base={dist['base']:.0f}%")

        # Score
        scores = scorer.score(fv)
        print(f"\n  ▸ Initial Score: {scores['total']:.1f}")
        print(f"    Balance={scores['balance']:.1f}  Theory={scores['theory']:.1f}  "
              f"Longevity={scores['longevity']:.1f}  Sillage={scores['sillage']:.1f}  "
              f"Synergy={scores['synergy']:.1f}")

        # Optimize
        result = optimizer.optimize(fv)
        opt_scores = result.scores
        print(f"\n  ▸ Optimized Score: {result.total_score:.1f} ({result.total_score - scores['total']:+.1f})")
        print(f"    Balance={opt_scores['balance']:.1f}  Theory={opt_scores['theory']:.1f}  "
              f"Longevity={opt_scores['longevity']:.1f}  Sillage={opt_scores['sillage']:.1f}  "
              f"Synergy={opt_scores['synergy']:.1f}")

        if result.suggestions:
            print(f"  Suggestions:")
            for sug in result.suggestions[:3]:
                print(f"    • {sug}")

        # Confidence
        conf = conf_scorer.score(fv.ingredients)
        print(f"\n  ▸ Confidence: {conf['confidence_grade']} "
              f"(data={conf['data_confidence']:.0f}  "
              f"pairing={conf['pairing_confidence']:.0f}  "
              f"overall={conf['overall_confidence']:.0f})")

        # Theory provenance
        prov = theory_provenance(fv)
        roud_roles = list(prov["roudnitska_roles"].keys())
        missing = prov["roudnitska_missing"]
        jell_quads = list(prov["jellinek_quadrants"].keys())
        print(f"\n  ▸ Theory Provenance:")
        print(f"    Roudnitska roles: {', '.join(roud_roles) if roud_roles else 'none'}")
        if missing:
            print(f"    Missing roles: {', '.join(missing)}")
        print(f"    Jellinek quadrants: {', '.join(jell_quads) if jell_quads else 'none'}")
        print(f"    SAR classes: {prov['sar_classes']}")

        results.append({
            "name": design["name"],
            "concept": design["concept"],
            "style": design["style"],
            "pyramid": design["pyramid"],
            "ingredients": fv.ingredients,
            "total_pct": total,
            "note_distribution": dist,
            "initial_scores": scores,
            "optimized_scores": opt_scores,
            "optimized_total": result.total_score,
            "suggestions": result.suggestions,
            "confidence": conf,
            "theory_provenance": prov,
            "theory_notes": design["theory_notes"],
        })

    # ── Save JSON ──
    json_path = Path(__file__).parent / "luxury_niche_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n→ Saved: {json_path.name}")

    # ── Save Markdown ──
    md_path = Path(__file__).parent / "luxury_niche_collection.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Luxury Niche Perfume Collection\n\n")
        f.write("5 hand-curated formulas built on accords from the library, "
                "scored by classical theory.\\\n")
        f.write("**Engine**: Theory-first (balance ×1.5, theory ×1.5, synergy ×0.3 bonus only)\n\n")
        f.write("---\n\n")

        for i, r in enumerate(results, 1):
            s = r["optimized_scores"]
            d = r["note_distribution"]

            f.write(f"## {i}. {r['name']}\n\n")
            f.write(f"**Style**: {r['style']}\\\n")
            f.write(f"**Concept**: {r['concept']}\n\n")

            f.write(f"**Score**: {r['initial_scores']['total']:.1f} → "
                    f"**{r['optimized_total']:.1f}** (optimized)\n\n")

            # Score breakdown
            f.write("| Axis | Score |\n|------|-------|\n")
            for axis in ["balance", "theory", "longevity", "sillage", "synergy", "cost"]:
                f.write(f"| {axis.title()} | {s.get(axis, 0):.1f} |\n")

            conf = r["confidence"]
            f.write(f"\n**Confidence**: {conf.get('confidence_grade', 'N/A')} "
                    f"(overall={conf.get('overall_confidence', 0):.0f})\n\n")

            # Pyramid
            pyr = r["pyramid"]
            f.write("### Pyramid\n\n")
            f.write(f"- **Top** ({d['top']:.0f}%): {pyr['top']}\n")
            f.write(f"- **Heart** ({d['heart']:.0f}%): {pyr['heart']}\n")
            f.write(f"- **Base** ({d['base']:.0f}%): {pyr['base']}\n\n")

            # Formula table
            f.write("### Formula (% of concentrate)\n\n")
            f.write("| Material | % | Note |\n|----------|---|------|\n")
            for mat, pct in sorted(r["ingredients"].items(), key=lambda x: -x[1]):
                note = classify_note(mat)
                f.write(f"| {mat} | {pct:.1f} | {note} |\n")
            f.write(f"| **TOTAL** | **{r['total_pct']:.1f}** | |\n")

            # Theory provenance
            prov = r["theory_provenance"]
            tn = r["theory_notes"]
            f.write(f"\n### Theory\n\n")
            f.write(f"- **Roudnitska**: {tn['roudnitska']}\n")
            f.write(f"- **Carles**: {tn['carles']}\n")
            f.write(f"- **Jellinek**: {tn['jellinek']}\n")
            f.write(f"- **The Twist**: {tn['twist']}\n")

            if r.get("suggestions"):
                f.write(f"\n### Optimizer Suggestions\n\n")
                for sug in r["suggestions"]:
                    f.write(f"- {sug}\n")

            # Usage
            f.write(f"\n### Usage\n\n")
            f.write(f"- **Concentration**: EDP 15-20% in ethanol\n")
            f.write(f"- **Maceration**: 2-4 weeks minimum (iris/vetiver formulas: 4+ weeks)\n")
            f.write(f"- **30mL EDP** at 18%: {30 * 0.18:.1f}g concentrate + "
                    f"{30 * 0.82:.1f}g ethanol\n")

            f.write("\n---\n\n")

        # Summary table
        f.write("## Summary\n\n")
        f.write("| # | Name | Score | Confidence | Top/Heart/Base | Ingredients |\n")
        f.write("|---|------|-------|------------|----------------|-------------|\n")
        for i, r in enumerate(results, 1):
            d = r["note_distribution"]
            f.write(f"| {i} | {r['name']} | {r['optimized_total']:.1f} "
                    f"| {r['confidence'].get('confidence_grade', 'N/A')} "
                    f"| {d['top']:.0f}/{d['heart']:.0f}/{d['base']:.0f} "
                    f"| {len(r['ingredients'])} |\n")

    print(f"→ Saved: {md_path.name}")
    print(f"\n{'=' * 70}")
    print("COMPLETE — 5 Luxury Niche Perfumes, Theory-First")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
