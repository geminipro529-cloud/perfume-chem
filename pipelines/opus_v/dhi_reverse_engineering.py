"""Dior Homme Intense — Full Reverse Engineering Analysis

Reverse engineers the ORIGINAL DHI (Olivier Polge, 2007/2011 EDP)
through the perfume-chem engine pipeline.

Runs TWO formulas:
  1. DHI Reference — theoretical original formula (all materials, including
     ones not in inventory) to establish the benchmark
  2. DHI Inventory Build — adapted formula using ONLY materials from
     the current inventory, with substitutions documented

Engine outputs: 6-axis scoring, theory provenance, confidence, texture
chemistry, and comparative analysis.

References:
  - EU allergen declarations (AIMI, coumarin, eugenol, linalool confirmed)
  - Ohloff/Pickenhagen/Kraft logP cascading
  - Polge's documented IFF palette constraints
  - Fragrantica/Parfumo consensus note pyramid
  - Existing 2024 DHI document (cross-reference Polge percentages)
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
# DHI FORMULA DESIGNS
# ═══════════════════════════════════════════════════════════════════════════

DHI_FORMULAS = [

    # ─────────────────────────────────────────────────────────────────────
    # 1. DHI REFERENCE — Polge Original (2011 formula, ~16% EDP)
    #    Materials mapped to engine-recognizable names.
    #    Some materials are NOT in user's inventory — this is the
    #    theoretical benchmark.
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "DHI Original (Polge 2011) — Reference",
        "concept": "The definitive lipstick-iris fragrance. Olivier Polge "
                   "built this at IFF using their captive palette. The formula "
                   "is an iris wall — AIMI at 17.8% of concentrate creates an "
                   "opaque, powdery, cosmetic iris saturated in cocoa butter "
                   "and anchored by a massive ISO E Super + Ambroxan amber bed. "
                   "Leather (isobutyl quinoline) and polycyclic musks (Galaxolide) "
                   "complete the masculine warmth. This is midnight iris — dense, "
                   "dark, enveloping.",
        "style": "Dior Homme Intense EDP (2011) — The Iris-Cocoa Masterpiece",
        "texture": "opaque, powdery, lipstick, cocoa-butter, suede",
        "pyramid": {
            "top": "Lavender, Pear (ethyl 2-methylbutyrate), Bergamot, Linalool",
            "heart": "AIMI (dominant), Methyl Ionone, Alpha-Irone, Cocoa Absolute, "
                     "Coumarin, Hydroxycitronellal, Lilial, Lyral, Heliotropin",
            "base": "ISO E Super, Ambroxan, Cashmeran, Vetiver, Cedarwood, "
                    "Isobutyl Quinoline, Labdanum, Galaxolide, Musk Ketone, "
                    "Ethylene Brassylate, Vanillin",
        },
        "ingredients": {
            # TOP ~12%  (of concentrate)
            "Lavender EO": 3.2,
            "Linalool": 0.8,
            "Bergamot FCF": 1.0,
            "Ethyl 2-Methylbutyrate": 0.5,     # Pear ester (authentic)
            "Hedione": 3.1,                      # Standard grade (not HC)
            "Dihydromyrcenol": 0.8,
            "Petitgrain EO": 0.6,

            # HEART ~48%
            "Alpha-Isomethyl Ionone (AIMI)": 17.8,  # THE spine
            "Methyl Ionone": 5.6,
            "Alpha Irone (10%)": 11.0,               # 1.1% active irone
            "Coumarin (20%)": 6.3,                   # 1.26% active
            "Hydroxycitronellal": 1.6,
            "Heliotropin Fleuressence": 1.4,
            "Eugenol": 0.3,                          # cocoa support + direct
            "Phenethyl Alcohol (PEA)": 0.4,
            "Cyclamen Aldehyde": 0.5,
            "Bourgeonal": 0.8,                       # Lilial replacement
            "Florol": 0.3,                           # Lyral replacement partial

            # BASE ~40%
            "Iso E Super": 8.1,
            "Ambrox Super (30%)": 7.5,               # 2.25% active
            "Cashmeran (20%)": 2.0,                  # 0.4% active
            "Vetiver EO": 1.9,
            "Cedarwood oil Virginia": 1.6,
            "Isobutyl Quinoline (10%)": 7.5,         # 0.75% active leather
            "Labdanum Absolute (10%)": 0.9,
            "Benzoin Resinoid (50% in DPG)": 0.6,
            "Galaxolide (80%)": 3.1,                 # 2.48% active
            "Musk Ketone (10%)": 0.5,
            "Ethylene Brassylate": 0.9,
            "Vanillin (10%)": 3.5,                   # 0.35% active
            "Ethyl Vanillin": 0.2,
            "Benzyl Benzoate": 0.6,
            "Benzyl Salicylate": 0.5,
            "Patchouli EO": 0.4,
        },
        "theory_notes": {
            "roudnitska": "Eclat (lavender/bergamot — aromatic spark), "
                          "Transparence (hedione/linalool — diffusion engine), "
                          "Noblesse (AIMI/alpha irone — iris is the noble heart), "
                          "Peau (ISO E/cashmeran/ambroxan — warm skin envelope), "
                          "Chaleur (coumarin/labdanum/vanillin — powdery warmth), "
                          "Profondeur (galaxolide/ethylene brassylate/vetiver — deep base)",
            "carles": "Top 12% / Heart 48% / Base 40% — heart-dominant "
                      "lipstick-iris construction, base anchors it for 8-10hr",
            "jellinek": "Warm-Narcotic (amber/musk/cocoa) + Cool-Narcotic "
                        "(iris/violet powder) + Fresh (lavender/bergamot) = "
                        "3 quadrants — heavily weighted toward narcotic warmth",
            "texture_mechanism": "AIMI at 17.8% creates an opaque iris wall. "
                                 "Cyclohexane ring geometry → powdery/cosmetic receptor "
                                 "binding. Alpha Irone at 1.1% active adds the buttery "
                                 "orris authenticity underneath. Coumarin at 1.26% active "
                                 "extends the powder into tonka territory. Isobutyl quinoline "
                                 "at 0.75% active adds the suede-leather dimension that "
                                 "transforms 'iris powder' into 'iris lipstick on warm skin'. "
                                 "Cocoa absolute (absent here — see inventory build) amplifies "
                                 "the iris via pyrazine-ionone cross-receptor enhancement.",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 2. DHI INVENTORY BUILD — Your Materials Only
    #    Adapted formula using ONLY materials from the current inventory.
    #    Key substitutions documented.
    #    Target: Capture the DHI character with what you have.
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "DHI Inventory Build — Your Materials",
        "concept": "Adapted DHI using only materials from your inventory. "
                   "The core AIMI + Methyl Ionone + Alpha Irone iris spine "
                   "is fully intact — you own all three. Coumarin, hedione, "
                   "lavender, and the amber bed are all present. Key gap: "
                   "NO cocoa absolute — replaced with a eugenol + vanillin + "
                   "ethyl vanillin + heliotropin 'cocoa shadow' accord. "
                   "Orris F-TEC replaces orris concrete. Musk bed uses your "
                   "Galaxolide + Habanolide + Exaltolide.",
        "style": "DHI from YOUR shelf — iris-cocoa reconstruction",
        "texture": "powdery, lipstick, warm amber, suede",
        "pyramid": {
            "top": "Lavender EO, Bergamot FCF, Linalool, Hedione, "
                   "Ethyl 2-Methylbutyrate, Dihydromyrcenol",
            "heart": "AIMI (dominant), Methyl Ionone, Alpha Irone, Beta Ionone, "
                     "Orivone, Molecule Iris, Coumarin, Hydroxycitronellal, "
                     "Heliotropin, Eugenol, Bourgeonal, Cyclamen Aldehyde",
            "base": "Iso E Super, Ambrox Super, Cashmeran, Vetiver EO, "
                    "Cedarwood Virginia, Isobutyl Quinoline, Labdanum, "
                    "Benzoin, Galaxolide, Habanolide, Exaltolide, "
                    "Vanillin, Ethyl Vanillin, Ethyl Maltol",
        },
        "ingredients": {
            # TOP ~12%
            "Lavender EO": 3.0,
            "Bergamot FCF": 1.5,
            "Linalool": 1.0,
            "Hedione": 3.0,
            "Ethyl 2-Methylbutyrate": 0.8,      # Authentic pear ester
            "Dihydromyrcenol": 0.5,
            "Petitgrain EO": 0.5,

            # HEART ~46%
            "Alpha-Isomethyl Ionone (AIMI)": 17.0,  # THE spine — kept near original
            "Methyl Ionone": 5.5,
            "Alpha Irone (10%)": 10.0,               # 1.0% active irone
            "Beta Ionone": 2.0,                      # Violet sweetness bridge
            "Orivone": 1.0,                          # Metallic iris accent
            "Molecule Iris": 1.5,                    # Transparent iris body
            "Coumarin (20%)": 6.0,                   # 1.2% active
            "Hydroxycitronellal": 1.5,
            "Heliotropin Fleuressence": 2.0,         # Bumped — cocoa substitute duty
            "Eugenol": 0.8,                          # Cocoa spice substitute
            "Bourgeonal": 0.8,                       # Lilial replacement
            "Cyclamen Aldehyde": 0.5,
            "Florol": 0.3,                           # Muguet transparency

            # BASE ~42%
            "Iso E Super": 8.0,
            "Ambrox Super (30%)": 7.0,               # 2.1% active
            "Cashmeran (20%)": 2.5,                  # 0.5% active
            "Vetiver EO": 1.5,
            "Cedarwood oil Virginia": 1.5,
            "Cedarwood EO": 0.5,                     # Atlas-type supplement
            "Isobutyl Quinoline (10%)": 6.0,         # 0.6% active leather
            "Labdanum Absolute (10%)": 1.0,
            "Labdanum": 0.5,                         # Undiluted labdanum
            "Benzoin Resinoid (50% in DPG)": 1.0,
            "Galaxolide (80%)": 3.0,                 # 2.4% active
            "Habanolide": 2.0,                       # Modern musk supplement
            "Exaltolide (10%)": 1.5,
            "Musk Ketone (10%)": 0.5,
            "Vanillin (10%)": 3.0,                   # 0.3% active
            "Ethyl Vanillin": 0.5,                   # Cocoa depth substitute
            "Ethyl Maltol (10%)": 0.5,               # Subliminal sweetness
            "Benzyl Benzoate": 0.5,
            "Benzyl Salicylate": 0.5,
            "Patchouli EO": 0.3,
        },
        "theory_notes": {
            "roudnitska": "Eclat (lavender/bergamot — aromatic spark), "
                          "Transparence (hedione/linalool — diffusion engine), "
                          "Noblesse (AIMI/alpha irone — iris nobility intact), "
                          "Peau (ISO E/cashmeran/ambroxan — warm skin envelope), "
                          "Chaleur (coumarin/labdanum/benzoin/vanillin — warm anchor), "
                          "Profondeur (galaxolide/habanolide/exaltolide/vetiver)",
            "carles": "Top 12% / Heart 46% / Base 42% — heart-dominant iris, "
                      "close to original Polge distribution",
            "jellinek": "Warm-Narcotic (amber/labdanum/musk) + Cool-Narcotic "
                        "(iris/violet powder/coumarin) + Fresh-Stimulating "
                        "(lavender/bergamot) = 3 quadrants — narcotic warmth dominant",
            "texture_mechanism": "AIMI at 17% maintains the opaque iris wall. "
                                 "Alpha Irone at 1.0% active provides buttery orris "
                                 "underneath. Beta Ionone at 2% adds violet sweetness "
                                 "that partially compensates for absent cocoa. "
                                 "Orivone + Molecule Iris extend the synthetic iris "
                                 "palette. Heliotropin bumped to 2% (from 1.4%) bridges "
                                 "the cocoa gap with its cherry-almond powder. "
                                 "Isobutyl quinoline at 0.6% active creates the suede. "
                                 "Galaxolide + Habanolide = old + modern musk blend.",
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════════
# TEXTURE CHEMISTRY ANALYSIS — DHI-specific
# ═══════════════════════════════════════════════════════════════════════════

def analyze_dhi_chemistry(design: dict) -> dict:
    """Decompose DHI-specific chemistry from the formula."""

    ingr = design["ingredients"]

    # Iris family analysis
    iris_family = {}
    irone_total = 0.0
    ionone_total = 0.0
    aimi_pct = 0.0
    methyl_ionone_pct = 0.0

    for name, pct in ingr.items():
        nl = name.lower()
        if "irone" in nl:
            active = pct * 0.1 if "(10%)" in name else pct
            iris_family[name] = {"pct": pct, "active": active, "class": "irone"}
            irone_total += active
        elif "aimi" in nl or "isomethyl ionone" in nl:
            iris_family[name] = {"pct": pct, "active": pct, "class": "AIMI"}
            ionone_total += pct
            aimi_pct = pct
        elif "methyl ionone" in nl:
            iris_family[name] = {"pct": pct, "active": pct, "class": "methyl_ionone"}
            ionone_total += pct
            methyl_ionone_pct = pct
        elif any(k in nl for k in ["beta ionone", "alpha ionone", "allyl ionone",
                                    "dihydro beta"]):
            iris_family[name] = {"pct": pct, "active": pct, "class": "ionone"}
            ionone_total += pct
        elif any(k in nl for k in ["orivone", "molecule iris", "ultralia"]):
            iris_family[name] = {"pct": pct, "active": pct, "class": "synthetic_iris"}

    # Cocoa / gourmand dimension
    cocoa_materials = {}
    cocoa_total = 0.0
    for name, pct in ingr.items():
        nl = name.lower()
        if "cocoa" in nl:
            cocoa_materials[name] = pct
            cocoa_total += pct
        elif "eugenol" in nl and "iso" not in nl:
            cocoa_materials[name + " (cocoa spice)"] = pct
            cocoa_total += pct
        elif "heliotropin" in nl:
            cocoa_materials[name + " (cocoa bridge)"] = pct * 0.3  # partial contribution
            cocoa_total += pct * 0.3

    # Coumarin / powder system
    coumarin_pct = 0.0
    for name, pct in ingr.items():
        if "coumarin" in name.lower():
            active = pct * 0.2 if "(20%)" in name else pct
            coumarin_pct += active

    # Leather dimension
    leather_pct = 0.0
    for name, pct in ingr.items():
        if "quinoline" in name.lower():
            active = pct * 0.1 if "(10%)" in name else pct
            leather_pct += active

    # Amber bed (ISO E + Ambroxan)
    amber_total = 0.0
    amber_materials = {}
    for name, pct in ingr.items():
        nl = name.lower()
        if "iso e" in nl:
            amber_materials["ISO E Super"] = pct
            amber_total += pct
        elif "ambrox" in nl or "ambrofix" in nl:
            active = pct * 0.3 if "(30%)" in name else pct
            amber_materials["Ambroxan (active)"] = active
            amber_total += active

    # Musk profile
    musk_total = 0.0
    musk_types = {}
    for name, pct in ingr.items():
        nl = name.lower()
        if any(m in nl for m in ["galaxolide", "habanolide", "romandolide",
                                  "ethylene brassylate", "musk ketone",
                                  "exaltolide", "ambrettolide"]):
            active = pct
            if "(80%)" in name:
                active = pct * 0.8
            elif "(10%)" in name:
                active = pct * 0.1
            musk_types[name] = {"pct": pct, "active": active}
            musk_total += active

    # Hedione type & dose
    hedione_pct = 0.0
    for name, pct in ingr.items():
        if "hedione" in name.lower():
            hedione_pct = pct

    return {
        "iris_family": iris_family,
        "aimi_pct": aimi_pct,
        "methyl_ionone_pct": methyl_ionone_pct,
        "irone_active_pct": round(irone_total, 2),
        "ionone_active_pct": round(ionone_total, 2),
        "total_iris_pct": round(irone_total + ionone_total, 2),
        "aimi_ratio": round(aimi_pct / (aimi_pct + methyl_ionone_pct) * 100, 1)
        if (aimi_pct + methyl_ionone_pct) > 0 else 0,
        "cocoa_materials": cocoa_materials,
        "cocoa_total": round(cocoa_total, 2),
        "coumarin_active_pct": round(coumarin_pct, 2),
        "leather_active_pct": round(leather_pct, 2),
        "amber_bed": amber_materials,
        "amber_total": round(amber_total, 2),
        "musk_profile": musk_types,
        "musk_total": round(musk_total, 2),
        "hedione_pct": hedione_pct,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("DIOR HOMME INTENSE — REVERSE ENGINEERING ANALYSIS")
    print("Polge 2011 Original vs. Your Inventory Build")
    print("=" * 72)
    print()
    print("  The lipstick-iris-cocoa masterpiece, decoded.")
    print("  Engine: 6-axis scoring, theory provenance, confidence,")
    print("  and DHI-specific texture chemistry analysis.")
    print()

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    conf_scorer = ConfidenceScorer()

    results = []

    for i, design in enumerate(DHI_FORMULAS, 1):
        print(f"\n{'═' * 72}")
        print(f"  {i}. {design['name']}")
        print(f"     Texture: {design['texture']}")
        print(f"     Style: {design['style']}")
        print(f"{'═' * 72}")
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

        # ── DHI-Specific Chemistry ──
        chem = analyze_dhi_chemistry(design)
        print(f"\n  ▸ DHI Chemistry:")
        print(f"    AIMI loading:    {chem['aimi_pct']:.1f}%  "
              f"(THE iris wall)")
        print(f"    Methyl Ionone:   {chem['methyl_ionone_pct']:.1f}%  "
              f"(bright iris support)")
        print(f"    Alpha Irone:     {chem['irone_active_pct']:.2f}% active  "
              f"(buttery orris)")
        print(f"    AIMI ratio:      {chem['aimi_ratio']:.0f}% AIMI / "
              f"{100 - chem['aimi_ratio']:.0f}% Methyl Ionone")
        print(f"    Total iris:      {chem['total_iris_pct']:.1f}%")
        print(f"    Coumarin active: {chem['coumarin_active_pct']:.2f}%  "
              f"(powder extension)")
        print(f"    Leather active:  {chem['leather_active_pct']:.2f}%  "
              f"(suede dimension)")
        print(f"    Hedione:         {chem['hedione_pct']:.1f}%  "
              f"(diffusion engine)")

        print(f"\n    Cocoa dimension: {chem['cocoa_total']:.2f}%")
        for cn, cv in chem["cocoa_materials"].items():
            print(f"      {cn}: {cv:.2f}%")

        print(f"\n    Amber bed: {chem['amber_total']:.2f}%")
        for an, av in chem["amber_bed"].items():
            print(f"      {an}: {av:.2f}%")

        print(f"\n    Musk bed: {chem['musk_total']:.2f}%")
        for mn, mv in chem["musk_profile"].items():
            print(f"      {mn}: {mv['active']:.2f}% active ({mv['pct']}% formula)")

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
            "dhi_chemistry": chem,
        })

    # ═══════════════════════════════════════════════════════════════════════
    # COMPARATIVE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    print(f"\n\n{'═' * 72}")
    print("COMPARATIVE ANALYSIS — Reference vs. Your Build")
    print(f"{'═' * 72}")

    r1, r2 = results[0], results[1]
    c1, c2 = r1["dhi_chemistry"], r2["dhi_chemistry"]

    print(f"""
    ┌──────────────────────────────┬──────────────┬──────────────┐
    │ Parameter                    │ Reference    │ Your Build   │
    │                              │ (Polge 2011) │ (Inventory)  │
    ├──────────────────────────────┼──────────────┼──────────────┤
    │ Engine Score                 │ {r1['optimized_total']:>8.1f}     │ {r2['optimized_total']:>8.1f}     │
    │ Balance                      │ {r1['optimized_scores']['balance']:>8.1f}     │ {r2['optimized_scores']['balance']:>8.1f}     │
    │ Theory                       │ {r1['optimized_scores']['theory']:>8.1f}     │ {r2['optimized_scores']['theory']:>8.1f}     │
    │ Longevity                    │ {r1['optimized_scores']['longevity']:>8.1f}     │ {r2['optimized_scores']['longevity']:>8.1f}     │
    │ Sillage                      │ {r1['optimized_scores']['sillage']:>8.1f}     │ {r2['optimized_scores']['sillage']:>8.1f}     │
    │ AIMI loading                 │ {c1['aimi_pct']:>8.1f}%    │ {c2['aimi_pct']:>8.1f}%    │
    │ Methyl Ionone                │ {c1['methyl_ionone_pct']:>8.1f}%    │ {c2['methyl_ionone_pct']:>8.1f}%    │
    │ Alpha Irone (active)         │ {c1['irone_active_pct']:>8.2f}%    │ {c2['irone_active_pct']:>8.2f}%    │
    │ Total iris %                 │ {c1['total_iris_pct']:>8.1f}%    │ {c2['total_iris_pct']:>8.1f}%    │
    │ Cocoa dimension              │ {c1['cocoa_total']:>8.2f}%    │ {c2['cocoa_total']:>8.2f}%    │
    │ Coumarin (active)            │ {c1['coumarin_active_pct']:>8.2f}%    │ {c2['coumarin_active_pct']:>8.2f}%    │
    │ Leather (active)             │ {c1['leather_active_pct']:>8.2f}%    │ {c2['leather_active_pct']:>8.2f}%    │
    │ Amber bed                    │ {c1['amber_total']:>8.2f}%    │ {c2['amber_total']:>8.2f}%    │
    │ Musk bed                     │ {c1['musk_total']:>8.2f}%    │ {c2['musk_total']:>8.2f}%    │
    │ Hedione                      │ {c1['hedione_pct']:>8.1f}%    │ {c2['hedione_pct']:>8.1f}%    │
    │ Cocoa Absolute?              │  Needed      │  Missing     │
    │ Orris Conc/Butter?           │  Needed      │  Use F-TEC   │
    └──────────────────────────────┴──────────────┴──────────────┘
    """)

    print("  WHAT YOUR BUILD CAPTURES:")
    print("  ─────────────────────────")
    print("  ✓ The AIMI iris wall (17% — nearly identical to Polge's 17.8%)")
    print("  ✓ The Methyl Ionone bright iris support")
    print("  ✓ The Alpha Irone buttery orris dimension")
    print("  ✓ The coumarin powdery warmth")
    print("  ✓ The isobutyl quinoline suede-leather")
    print("  ✓ The Hedione diffusion engine")
    print("  ✓ The ISO E Super + Ambroxan amber bed")
    print("  ✓ The Galaxolide musk foundation")
    print("  ✓ The vanillin-coumarin sweet powder bridge")
    print()
    print("  WHAT'S MISSING OR SUBSTITUTED:")
    print("  ──────────────────────────────")
    print("  ✗ Cocoa Absolute — THE iconic DHI co-star")
    print("    → Substituted with eugenol + heliotropin + vanillin shadow")
    print("    → Captures spice and powder, misses the actual chocolate")
    print("    → Impact: ~15% of DHI's character identity is approximate")
    print("  ✓ Ethyl 2-Methylbutyrate — NOW IN STOCK")
    print("    → Authentic pear ester, used directly at 0.8%")
    print("    → Replaces former Hexyl Acetate substitute")
    print("  ✗ Orris Concrete/Butter — natural orris root")
    print("    → Alpha Irone at 10% provides the irone character")
    print("    → Missing: myristic acid matrix 'slow release' effect")
    print("    → Add Orris F-TEC if you want the natural orris impression")
    print("  ✗ Lilial & Lyral (both banned)")
    print("    → Bourgeonal + Cyclamen Aldehyde + Florol cover this")
    print()
    print("  RECOMMENDATION:")
    print("  ────────────────")
    print("  Buy Cocoa Absolute. It's ~$15-25 for 10g (affordable).")
    print("  That single purchase closes the biggest character gap.")
    print("  Everything else in your build is solid DHI territory.")

    # Save results
    output_file = Path(__file__).parent / "dhi_reverse_engineering_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_file.name}")


if __name__ == "__main__":
    main()
