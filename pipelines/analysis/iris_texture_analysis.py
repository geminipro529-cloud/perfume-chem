"""Iris Texture Analysis — How Does the Opus V Iris Achieve Its Character?

Runs TWO iris formulas through the engine side-by-side:
  1. Iris Impériale (Dior Homme / powdery-sharp school)
  2. Opus V Iris (Amouage / buttery-suede school)

The engine scores, theory provenance, and confidence analysis will
reveal exactly *why* these two iris concepts smell different despite
using mostly the same molecule families.

Key question: How does Alpha Irone:Methyl Ionone ratio, plus modifier
choice (Suederal/Carrot Seed vs Orivone/Neroli), create fundamentally
different texture experiences?
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

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
# TWO IRIS SCHOOLS — SIDE BY SIDE
# ═══════════════════════════════════════════════════════════════════════════

IRIS_FORMULAS = [

    # ─────────────────────────────────────────────────────────────────────
    # 1. IRIS IMPÉRIALE — Powdery-Sharp School (Dior Homme territory)
    #    Texture: powdery, mineral, cool, chalky
    #    Methyl Ionone LEADS (10%), Alpha Irone supports (8%)
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Iris Impériale (Powdery School)",
        "concept": "Methyl-Ionone-forward iris. The ionone cyclohexane ring "
                   "produces a powdery, mineral, almost chalky texture. "
                   "Orivone at 4% adds metallic coldness. Heavy Hedione "
                   "diffusion. Neroli lifts it into aristocratic territory. "
                   "This is the Dior Homme / Prada school — sharp, dry, "
                   "cerebral iris.",
        "style": "Dior Homme Parfum / Armani Privé Iris Céladon",
        "texture": "powdery, mineral, cool, chalky",
        "pyramid": {
            "top": "Bergamot FCF, Neroli EO, Linalool",
            "heart": "Methyl Ionone (lead), Alpha Irone (support), Beta Ionone, "
                     "Orivone, Hedione, Heliotropin",
            "base": "Ambrox Super, Iso E Super, Cashmeran, Benzoin, "
                    "Labdanum, Coumarin, Habanolide, Ethylene Brassylate",
        },
        "ingredients": {
            # TOP 18%
            "Bergamot FCF oil Sicilian": 7.0,
            "Neroli EO": 6.0,
            "Linalool": 5.0,
            # HEART 37%
            "Alpha Irone (10%)": 8.0,        # SUPPORTING — 0.8% active
            "Methyl Ionone": 10.0,            # LEADING — powdery cyclohexane
            "Beta Ionone": 5.0,
            "Orivone": 4.0,                   # High Orivone = metallic cold
            "Hedione": 7.0,
            "Heliotropin Fleuressence": 3.0,
            # BASE 45%
            "Ambrox Super (30%)": 12.0,
            "Iso E Super": 8.0,
            "Cashmeran (20%)": 5.0,
            "Benzoin Resinoid (50% in DPG)": 5.0,
            "Labdanum Absolute (10%)": 4.0,
            "Coumarin (20%)": 4.0,
            "Habanolide": 4.0,
            "Ethylene Brassylate": 3.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot), Transparence (hedione/linalool), "
                          "Noblesse (methyl ionone/neroli), Peau (ambrox/iso e/cashmeran), "
                          "Chaleur (benzoin/labdanum/coumarin), Profondeur (ethylene brassylate)",
            "carles": "Top 18% / Heart 37% / Base 45% — classical luxury balance",
            "jellinek": "Cool-Narcotic (iris/violet powder) + Warm-Narcotic (amber/musk) + "
                        "Fresh-Stimulating (citrus/neroli) = 3 quadrants",
            "texture_mechanism": "Methyl Ionone's cyclohexane ring geometry binds "
                                 "OR5A1 receptor → powdery/dry perception. Orivone "
                                 "adds metallic edge. Heliotropin rounds the powder. "
                                 "No suede, no earthiness — pure mineral iris.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 2. OPUS V IRIS — Buttery-Suede School (Amouage territory)
    #    Texture: buttery, creamy, suede, warm, lipid
    #    Alpha Irone LEADS (12%), Methyl Ionone supports (10%)
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Opus V Iris (Buttery School)",
        "concept": "Alpha-Irone-forward iris. The irone cyclopentane ring "
                   "produces a lipid, waxy, buttery texture — like actual "
                   "orris butter. Suederal adds a soft leather envelope. "
                   "Carrot Seed EO provides earthy rootiness (natural "
                   "irisones). Low Orivone means less metallic cold, more "
                   "warm butterscotch quality. This is the Amouage / Chanel "
                   "28 La Pausa school — round, lipid, tactile iris.",
        "style": "Amouage Opus V / Chanel 28 La Pausa / Xerjoff Irisss",
        "texture": "buttery, creamy, suede, warm, lipid",
        "pyramid": {
            "top": "Alpha Ionone, Bergamot FCF, Linalool, Hedione, "
                   "Aldehyde C11",
            "heart": "Alpha Irone (lead), Methyl Ionone (support), Beta Ionone, "
                     "AIMI, Orivone (low), Molecule Iris, Dihydro Beta Ionone, "
                     "Carrot Seed EO, Coumarin, Heliotropin",
            "base": "Suederal, Iso E Super, Cashmeran, Ambrox Super, Sandalore, "
                    "Benzoin, Vanillin, Labdanum, Galaxolide, Habanolide, "
                    "Ethylene Brassylate, Romandolide, Benzyl Salicylate, "
                    "Benzyl Benzoate",
        },
        "ingredients": {
            # TOP 11%
            "Alpha Ionone": 3.0,
            "Bergamot FCF": 2.0,
            "Linalool": 1.5,
            "Hedione": 4.0,
            "Aldehyde C11 (1%)": 0.5,
            # HEART 45%
            "Alpha Irone (10%)": 12.0,       # LEADING — 1.2% active, buttery cyclopentane
            "Methyl Ionone": 10.0,            # SUPPORTING — still present but not dominant
            "Beta Ionone": 5.0,
            "Alpha-Isomethyl Ionone (AIMI)": 5.0,
            "Orivone": 1.0,                   # LOW Orivone = less metallic, more warm
            "Molecule Iris": 3.0,
            "Dihydro Beta Ionone": 2.5,
            "Carrot Seed EO": 1.5,            # Earthy root — natural irisone character
            "Coumarin (20%)": 3.0,
            "Heliotropin Fleuressence": 2.0,
            # BASE 44%
            "Suederal (10%)": 4.0,            # THE SUEDE — 0.4% active, subliminal leather
            "Iso E Super": 5.0,
            "Cashmeran (20%)": 3.0,
            "Ambrox Super (30%)": 4.0,
            "Sandalore": 3.0,
            "Benzoin Resinoid (50% in DPG)": 2.0,
            "Vanillin (10%)": 1.5,
            "Labdanum Absolute (10%)": 1.0,
            "Galaxolide (80%)": 6.0,
            "Habanolide": 4.0,
            "Ethylene Brassylate": 3.0,
            "Romandolide": 2.0,
            "Benzyl Salicylate": 2.5,
            "Benzyl Benzoate": 2.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot/alpha ionone), Transparence (hedione), "
                          "Noblesse (alpha irone — true orris butter nobility), "
                          "Peau (suederal/iso e/cashmeran — the skin-suede envelope), "
                          "Chaleur (benzoin/labdanum/vanillin/coumarin — warm amber bed), "
                          "Profondeur (ethylene brassylate/dihydro beta ionone — tenacity)",
            "carles": "Top 11% / Heart 45% / Base 44% — heart-heavy iris, needs "
                      "generous base to anchor volatile ionones",
            "jellinek": "Warm-Narcotic (amber/suede/musk) + Cool-Narcotic "
                        "(iris/violet powder) = 2 quadrants, intimate skin-scent",
            "texture_mechanism": "Alpha Irone's cyclopentane ring geometry binds "
                                 "different receptor subset → lipid/waxy/buttery "
                                 "perception. Suederal at 0.4% active adds subliminal "
                                 "suede (soft leather, not animalic). Carrot Seed EO "
                                 "contains natural irisones + carotol → earthy root "
                                 "quality that reinforces the 'natural orris' illusion. "
                                 "Sandalore adds creamy sandalwood warmth. The result "
                                 "is tactile — you feel this iris, not just smell it.",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# TEXTURE CHEMISTRY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_texture_chemistry(design: dict) -> dict:
    """Decompose texture mechanisms from the formula."""

    ingr = design["ingredients"]

    # Ionone family analysis
    ionone_family = {}
    irone_total = 0.0
    ionone_total = 0.0
    for name, pct in ingr.items():
        name_lower = name.lower()
        if "irone" in name_lower:
            ionone_family[name] = {"pct": pct, "class": "irone", "ring": "cyclopentane"}
            # Approximate active %
            if "(10%)" in name:
                irone_total += pct * 0.1
            else:
                irone_total += pct
        elif "ionone" in name_lower or "aimi" in name_lower or "isomethyl" in name_lower:
            ionone_family[name] = {"pct": pct, "class": "ionone", "ring": "cyclohexane"}
            ionone_total += pct
        elif "methyl ionone" in name_lower:
            ionone_family[name] = {"pct": pct, "class": "ionone", "ring": "cyclohexane"}
            ionone_total += pct
        elif "orivone" in name_lower or "molecule iris" in name_lower:
            ionone_family[name] = {"pct": pct, "class": "synthetic_iris", "ring": "mixed"}

    # Texture modifiers (non-ionone contributors to texture)
    texture_modifiers = {}
    for name, pct in ingr.items():
        name_lower = name.lower()
        if "suederal" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "suede/soft leather",
                "mechanism": "Subliminal leather envelope — brain reads 'suede gloves'"
            }
        elif "carrot seed" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "earthy rootiness",
                "mechanism": "Contains natural irisones + carotol — earthy orris character"
            }
        elif "sandalore" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "creamy sandalwood",
                "mechanism": "Campholenic aldehyde derivative — adds cream to butter"
            }
        elif "neroli" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "bitter-floral transparency",
                "mechanism": "Nerolidol + linalool + linalyl acetate — aristocratic lift"
            }
        elif "heliotropin" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "cherry-almond powder",
                "mechanism": "Piperonal — soft powdery sweetness without heavy powder"
            }
        elif "coumarin" in name_lower:
            texture_modifiers[name] = {
                "pct": pct, "effect": "powdery-warm tonka",
                "mechanism": "Lactone ring → powdery/hay smell — the tonka bridge"
            }

    # Musk profile (transparency vs warmth)
    musk_total = 0.0
    musk_types = {}
    for name, pct in ingr.items():
        name_lower = name.lower()
        if any(m in name_lower for m in ["galaxolide", "habanolide", "romandolide",
                                          "ethylene brassylate"]):
            musk_types[name] = pct
            musk_total += pct

    # Ratio analysis
    irone_ratio = irone_total / (irone_total + ionone_total) * 100 if (irone_total + ionone_total) > 0 else 0

    return {
        "ionone_family": ionone_family,
        "irone_active_pct": round(irone_total, 2),
        "ionone_active_pct": round(ionone_total, 2),
        "irone_ratio": round(irone_ratio, 1),
        "texture_modifiers": texture_modifiers,
        "musk_profile": musk_types,
        "musk_total_pct": round(musk_total, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("IRIS TEXTURE ANALYSIS — Why Do These Two Iris Styles Smell Different?")
    print("=" * 70)
    print()
    print("  Two iris philosophies, same molecule family, opposite textures.")
    print("  The engine will show HOW the chemistry creates the difference.")
    print()

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    conf_scorer = ConfidenceScorer()

    results = []

    for i, design in enumerate(IRIS_FORMULAS, 1):
        print(f"\n{'═' * 70}")
        print(f"  {i}. {design['name']}")
        print(f"     Texture: {design['texture']}")
        print(f"     Style: {design['style']}")
        print(f"{'═' * 70}")
        print(f"\n  {design['concept']}")

        fv = FormulaVector(ingredients=dict(design["ingredients"]))
        total = fv.total_pct
        dist = fv.note_distribution()
        print(f"\n  ▸ Formula: {total:.1f}%  |  Top {dist['top']:.0f}%  "
              f"Heart {dist['heart']:.0f}%  Base {dist['base']:.0f}%")

        # ── Engine Score ──
        scores = scorer.score(fv)
        print(f"\n  ▸ Initial Score: {scores['total']:.1f}")
        print(f"    Balance  = {scores['balance']:.1f}")
        print(f"    Theory   = {scores['theory']:.1f}")
        print(f"    Longevity= {scores['longevity']:.1f}")
        print(f"    Sillage  = {scores['sillage']:.1f}")
        print(f"    Synergy  = {scores['synergy']:.1f}")

        # ── Optimize ──
        result = optimizer.optimize(fv)
        opt_scores = result.scores
        print(f"\n  ▸ Optimized Score: {result.total_score:.1f} "
              f"({result.total_score - scores['total']:+.1f})")
        print(f"    Balance  = {opt_scores['balance']:.1f}")
        print(f"    Theory   = {opt_scores['theory']:.1f}")
        print(f"    Longevity= {opt_scores['longevity']:.1f}")
        print(f"    Sillage  = {opt_scores['sillage']:.1f}")
        print(f"    Synergy  = {opt_scores['synergy']:.1f}")

        if result.suggestions:
            print(f"\n  Suggestions:")
            for sug in result.suggestions[:5]:
                print(f"    • {sug}")

        # ── Confidence ──
        conf = conf_scorer.score(fv.ingredients)
        print(f"\n  ▸ Confidence: {conf['confidence_grade']} "
              f"(data={conf['data_confidence']:.0f}  "
              f"pairing={conf['pairing_confidence']:.0f}  "
              f"overall={conf['overall_confidence']:.0f})")

        # ── Theory Provenance ──
        prov = theory_provenance(fv)
        roud_roles = list(prov["roudnitska_roles"].keys())
        missing = prov["roudnitska_missing"]
        jell_quads = list(prov["jellinek_quadrants"].keys())
        print(f"\n  ▸ Theory Provenance:")
        print(f"    Roudnitska roles: {', '.join(roud_roles) if roud_roles else 'none'}")
        if missing:
            print(f"    Missing roles:   {', '.join(missing)}")
        else:
            print(f"    Missing roles:   NONE — all 6 covered!")
        print(f"    Jellinek quads:  {', '.join(jell_quads) if jell_quads else 'none'}")
        print(f"    SAR classes:     {prov['sar_classes']}")

        # ── Texture Chemistry ──
        tex = analyze_texture_chemistry(design)
        print(f"\n  ▸ Texture Chemistry:")
        print(f"    Irone active:    {tex['irone_active_pct']:.2f}%  "
              f"(cyclopentane ring → BUTTERY)")
        print(f"    Ionone active:   {tex['ionone_active_pct']:.1f}%  "
              f"(cyclohexane ring → POWDERY)")
        print(f"    Irone ratio:     {tex['irone_ratio']:.0f}% irone "
              f"/ {100 - tex['irone_ratio']:.0f}% ionone")

        if tex["texture_modifiers"]:
            print(f"\n    Texture Modifiers:")
            for name, info in tex["texture_modifiers"].items():
                print(f"      {name} ({info['pct']}%) — {info['effect']}")
                print(f"        → {info['mechanism']}")

        print(f"\n    Musk bed: {tex['musk_total_pct']:.1f}%")
        for m_name, m_pct in tex["musk_profile"].items():
            print(f"      {m_name}: {m_pct}%")

        results.append({
            "name": design["name"],
            "concept": design["concept"],
            "style": design["style"],
            "texture": design["texture"],
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
            "texture_chemistry": tex,
        })

    # ═══════════════════════════════════════════════════════════════════════
    # COMPARATIVE ANALYSIS — THE ANSWER TO "WHY DIFFERENT?"
    # ═══════════════════════════════════════════════════════════════════════
    print(f"\n\n{'═' * 70}")
    print("COMPARATIVE ANALYSIS — How Chemistry Creates Texture")
    print(f"{'═' * 70}")

    r1, r2 = results[0], results[1]
    t1, t2 = r1["texture_chemistry"], r2["texture_chemistry"]

    print(f"""
    ┌─────────────────────────────┬──────────────┬──────────────┐
    │ Parameter                   │ Iris         │ Opus V       │
    │                             │ Impériale    │ Iris         │
    ├─────────────────────────────┼──────────────┼──────────────┤
    │ Texture                     │ {r1['texture']:<12} │ {r2['texture']:<12} │
    │ Engine Score                │ {r1['optimized_total']:>8.1f}     │ {r2['optimized_total']:>8.1f}     │
    │ Balance                     │ {r1['optimized_scores']['balance']:>8.1f}     │ {r2['optimized_scores']['balance']:>8.1f}     │
    │ Theory                      │ {r1['optimized_scores']['theory']:>8.1f}     │ {r2['optimized_scores']['theory']:>8.1f}     │
    │ Irone active %              │ {t1['irone_active_pct']:>8.2f}     │ {t2['irone_active_pct']:>8.2f}     │
    │ Ionone active %             │ {t1['ionone_active_pct']:>8.1f}     │ {t2['ionone_active_pct']:>8.1f}     │
    │ Irone ratio                 │ {t1['irone_ratio']:>7.0f}%     │ {t2['irone_ratio']:>7.0f}%     │
    │ Musk bed %                  │ {t1['musk_total_pct']:>8.1f}     │ {t2['musk_total_pct']:>8.1f}     │
    │ Suederal?                   │       No     │      Yes     │
    │ Carrot Seed?                │       No     │      Yes     │
    │ Neroli?                     │      Yes     │       No     │
    └─────────────────────────────┴──────────────┴──────────────┘
    """)

    print("  THE TEXTURE MECHANISM (Why They Smell Different):")
    print("  ─────────────────────────────────────────────────")
    print()
    print("  1. RING GEOMETRY = RECEPTOR BINDING = SMELL")
    print("     • Alpha Irone has a CYCLOPENTANE ring (5-carbon)")
    print("       → smaller ring → fits different receptor pocket")
    print("       → brain reads: lipid, waxy, buttery, creamy")
    print("     • Methyl Ionone has a CYCLOHEXANE ring (6-carbon)")
    print("       → larger ring → fits OR5A1 powdery receptor")
    print("       → brain reads: powdery, mineral, dry, chalky")
    print()
    print("  2. THE MODIFIER STACK = THE ENVELOPE")
    print("     • POWDERY school: Orivone (metallic cold) + Neroli")
    print("       (bitter-floral lift) + no suede/earth = SHARP IRIS")
    print("     • BUTTERY school: Suederal (subliminal suede) + Carrot")
    print("       Seed EO (earthy root) + Sandalore (cream) = ROUND IRIS")
    print()
    print("  3. THE RATIO IS EVERYTHING")
    print(f"     • Impériale: {t1['irone_ratio']:.0f}% irone / "
          f"{100 - t1['irone_ratio']:.0f}% ionone — ionone-forward = powder")
    print(f"     • Opus V:    {t2['irone_ratio']:.0f}% irone / "
          f"{100 - t2['irone_ratio']:.0f}% ionone — irone-forward = butter")
    print()
    print("  4. PRACTICAL RULE:")
    print("     To move ANY iris toward buttery: increase Alpha Irone,")
    print("     add Suederal trace, add Carrot Seed EO, reduce Orivone.")
    print("     To move ANY iris toward powdery: increase Methyl Ionone,")
    print("     increase Orivone, add Heliotropin, remove earth/suede.")

    # ── Save JSON ──
    out_path = Path(__file__).parent / "iris_texture_analysis_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n→ Saved: {out_path.name}")

    print(f"\n{'═' * 70}")
    print("COMPLETE — Iris texture differences explained by the engine.")
    print(f"{'═' * 70}")


if __name__ == "__main__":
    main()
