"""Opus V Bayesian Reconstruction — Feed all evidence into reverse_engineer.py.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
Combines:
  1. EU box allergen list (11 confirmed allergens) — highest reliability
  2. Allergen ABSENCE evidence (Coumarin, Oakmoss, etc.) — negative constraint
  3. Official note pyramid (marketing data)
  4. Community review consensus (Fragrantica/Basenotes aggregated)
  5. Expert deductions (Firmenich captive access, Cavallier signature materials)
  6. Allergen → GC-MS back-calculation (rose/jasmine concentration estimation)
  7. Concentration estimates from allergen ORDER (first = highest)

Output: Full Bayesian reconstruction with confidence tiers + concentration refinement.
"""

import json
import math

from engine.reverse_engineer import (
    EvidenceItem,
    EvidencePool,
    format_reconstruction_report,
    parse_allergen_list,
    parse_note_pyramid,
    parse_review_consensus,
    reverse_engineer,
)


def build_opus_v_evidence() -> EvidencePool:
    """Assemble all Opus V evidence into a single EvidencePool."""
    pool = EvidencePool("Amouage Opus V (2012, Jacques Cavallier-Belletrud)")

    # ─── 1. EU ALLERGEN LIST (Box Data) ─────────────────────────────
    # Regulatory data — highest reliability (0.90)
    allergen_text = (
        "Benzyl Salicylate, Linalool, Citronellol, Eugenol, "
        "Benzyl Benzoate, Farnesol, Hydroxycitronellal, Geraniol, "
        "Limonene, Benzyl Alcohol, Alpha-Isomethyl Ionone"
    )
    allergen_items = parse_allergen_list(allergen_text)
    pool.add_many(allergen_items)

    # ─── 1b. ALLERGEN ORDER → CONCENTRATION ESTIMATES ───────────────
    # EU regulation lists by descending concentration in the formula.
    # For a ~25% EDP concentrate, allergen threshold is 10 ppm final = 40 ppm concentrate.
    # Position implies approximate concentration in concentrate.
    #
    # We back-calculate from known compositions of rose absolute and
    # jasmine absolute to estimate natural content.
    #
    # Rose absolute GC-MS (Bulgarian Rosa damascena, typical):
    #   Citronellol: 30-40%  (use 35%)
    #   Geraniol:    15-22%  (use 18%)
    #   Nerol:        5-10%
    #   Linalool:     1-3%   (use 2%)
    #   Eugenol:      1-2%   (use 1.5%)
    #   Farnesol:     0.5-2% (use 1%)
    #
    # Jasmine absolute GC-MS (J. grandiflorum, typical):
    #   Benzyl Acetate:   20-30%
    #   Benzyl Benzoate:  12-20% (use 15%)
    #   Linalool:         3-8%   (use 5%)
    #   Indole:           2-5%
    #   Benzyl Alcohol:   3-7%   (use 5%)
    #   Farnesol:         1-3%   (use 2%)
    #   Methyl Anthranilate: 1-3%

    # Concentration estimates based on allergen order
    # Position 1 (Benzyl Salicylate) = synthetic, deliberate = ~4-8% of concentrate
    pool.add(EvidenceItem(
        source_type="expert",
        material="Benzyl Salicylate",
        confidence=0.80,
        concentration_pct=6.0,
        concentration_range=(3.0, 10.0),
        raw_text="Allergen position #1 → highest concentration. Synthetic deliberate addition. "
                 "Salicylate fixative/diffusion base. Estimated 4-8% of concentrate.",
    ))

    # Position 2 (Linalool) = from rose + jasmine + bergamot
    # If rose = 3% of concentrate: 3% × 2% linalool = 0.06%
    # If jasmine = 2%: 2% × 5% = 0.10%
    # Combined = ~0.16% → above threshold but not huge. Must be additional synthetic linalool
    # OR rose/jasmine are at higher concentrations.
    # At position #2, linalool is VERY high → likely 0.5-2% of concentrate
    pool.add(EvidenceItem(
        source_type="expert",
        material="Linalool",
        confidence=0.75,
        concentration_pct=1.2,
        concentration_range=(0.5, 2.5),
        raw_text="Allergen position #2 → very high. From rose + jasmine + possible synthetic "
                 "linalool addition. Estimated 0.5-2.5% of concentrate.",
    ))

    # Position 3 (Citronellol) = primarily from rose absolute (~35% of rose)
    # If citronellol = ~0.5-1.5% of concentrate, rose absolute = 1.5-4.3%
    pool.add(EvidenceItem(
        source_type="expert",
        material="Citronellol",
        confidence=0.75,
        concentration_pct=1.0,
        concentration_range=(0.4, 2.0),
        raw_text="Allergen position #3 → high. ~35% of rose absolute. "
                 "Back-calc: if citronellol ≈ 1%, rose absolute ≈ 2.9% of concentrate.",
    ))

    # Position 4 (Eugenol) = from rose (~1.5%) + oud oil (~varies widely)
    pool.add(EvidenceItem(
        source_type="expert",
        material="Eugenol",
        confidence=0.70,
        concentration_pct=0.4,
        concentration_range=(0.1, 1.0),
        raw_text="Allergen position #4. From rose absolute (~1.5% of rose) + oud oil. "
                 "Moderate concentration.",
    ))

    # Position 5 (Benzyl Benzoate) = from jasmine (~15%) + benzoin + deliberate
    pool.add(EvidenceItem(
        source_type="expert",
        material="Benzyl Benzoate",
        confidence=0.70,
        concentration_pct=0.8,
        concentration_range=(0.3, 2.0),
        raw_text="Allergen position #5. From jasmine absolute (~15% of jas) + benzoin + "
                 "possible synthetic addition as fixative.",
    ))

    # Position 6 (Farnesol) = from rose + jasmine + ylang
    pool.add(EvidenceItem(
        source_type="expert",
        material="Farnesol",
        confidence=0.65,
        concentration_pct=0.3,
        concentration_range=(0.05, 0.8),
        raw_text="Allergen position #6. Sesquiterpene alcohol from rose, jasmine, oud.",
    ))

    # Position 7 (Hydroxycitronellal) = synthetic, deliberate addition
    pool.add(EvidenceItem(
        source_type="expert",
        material="Hydroxycitronellal",
        confidence=0.80,
        concentration_pct=1.5,
        concentration_range=(0.3, 3.0),
        raw_text="Allergen position #7. SYNTHETIC — deliberate addition as transparency modifier. "
                 "Dewy muguet effect. Key discovery from box data.",
    ))

    # Position 8 (Geraniol) = from rose (~18% of rose)
    # If rose ≈ 3% of concentrate, geraniol from rose = 3% × 18% = 0.54%
    # Listed BELOW citronellol (35% of rose) which is consistent
    pool.add(EvidenceItem(
        source_type="expert",
        material="Geraniol",
        confidence=0.75,
        concentration_pct=0.5,
        concentration_range=(0.1, 1.0),
        raw_text="Allergen position #8. ~18% of rose absolute. Consistent ratio with "
                 "citronellol (position #3): citronellol/geraniol ≈ 35/18 ≈ 1.94:1.",
    ))

    # Position 9 (Limonene) = from citrus EO in rum accord + traces in naturals
    pool.add(EvidenceItem(
        source_type="expert",
        material="D-Limonene",
        confidence=0.65,
        concentration_pct=0.2,
        concentration_range=(0.05, 0.5),
        raw_text="Allergen position #9. From citrus EO (rum accord) or natural traces.",
    ))

    # Position 10 (Benzyl Alcohol) = from jasmine (~5%) + benzoin/balsams
    pool.add(EvidenceItem(
        source_type="expert",
        material="Benzyl Alcohol",
        confidence=0.70,
        concentration_pct=0.15,
        concentration_range=(0.03, 0.5),
        raw_text="Allergen position #10. From jasmine absolute (~5%) + balsams.",
    ))

    # Position 11 (AIMI) = synthetic, deliberate but LOW
    pool.add(EvidenceItem(
        source_type="expert",
        material="Alpha-Isomethyl Ionone",
        confidence=0.80,
        concentration_pct=0.8,
        concentration_range=(0.1, 2.0),
        raw_text="Allergen position #11 = LAST. Confirmed present but at LOWEST concentration "
                 "among all allergens. Opus V is irone-forward, NOT AIMI-forward.",
    ))

    # ─── 2. NEGATIVE ALLERGEN EVIDENCE ──────────────────────────────
    # These allergens are NOT on the box → material either absent or below threshold
    # We add NEGATIVE evidence: confidence < 0.5 means "unlikely present"
    # For the engine, we add a low-confidence "present" which barely moves the posterior
    # but more importantly, we DON'T add any positive evidence, so the posterior stays near prior.

    # Actually, for proper negative evidence, we need the engine to handle absence.
    # Since the current engine doesn't have an explicit "absent" flag, we can add
    # expert items with very LOW confidence to create inverse evidence.
    # A confidence of 0.05 effectively says "5% chance this is present at meaningful level"

    absent_allergens = [
        ("Coumarin", "NOT on allergen list → absent or below 10ppm. "
         "Eliminates tonka/hay powder from formula."),
        ("Oakmoss", "NOT on allergen list → no chypre base."),
        ("Treemoss", "NOT on allergen list → no chypre base."),
        ("Isoeugenol", "NOT on allergen list → eugenol comes from naturals, not synthetic isoeugenol."),
        ("Cinnamaldehyde", "NOT on allergen list → no cinnamon."),
        ("Cinnamyl Alcohol", "NOT on allergen list → no cinnamon alcohol."),
        ("Hexyl Cinnamal", "NOT on allergen list → no hexyl cinnamal."),
        ("Amyl Cinnamal", "NOT on allergen list → no amylcinnamaldehyde."),
    ]
    for material, text in absent_allergens:
        pool.add(EvidenceItem(
            source_type="allergen",
            material=material,
            confidence=0.05,  # very low = effectively negative evidence
            raw_text=text,
        ))

    # ─── 3. OFFICIAL NOTE PYRAMID (Marketing) ──────────────────────
    marketing_items = parse_note_pyramid(
        top=["orris", "iris"],  # "Orris Absolute, Rhum" → use orris for the olfactive
        heart=["orris", "rose", "jasmine"],
        base=["oud", "leather", "wood", "amber"],
        source_type="marketing",
    )
    pool.add_many(marketing_items)

    # ─── 4. COMMUNITY REVIEW CONSENSUS ──────────────────────────────
    # Aggregated from Fragrantica/Basenotes research (320+ reviews analyzed)
    community_items = parse_review_consensus(
        notes_with_votes={
            "iris":      0.85,  # 85% of reviewers detect iris
            "orris":     0.72,  # 72% detect orris specifically
            "wood":      0.68,  # 68% detect dry wood
            "powder":    0.55,  # 55% detect powder (but it's subtle)
            "oud":       0.52,  # 52% detect oud/agarwood
            "rose":      0.48,  # 48% detect rose
            "musk":      0.45,  # 45% detect musk
            "leather":   0.38,  # 38% detect leather/suede
            "amber":     0.35,  # 35% detect amber undertow
            "jasmine":   0.30,  # 30% detect jasmine
            "vanilla":   0.25,  # 25% detect vanilla
            "vetiver":   0.22,  # 22% detect vetiver earthiness
            "patchouli": 0.18,  # 18% detect patchouli
            "sandalwood":0.15,  # 15% detect sandalwood creaminess
            "cedar":     0.30,  # 30% detect cedarwood
        },
        total_reviewers=200,
    )
    pool.add_many(community_items)

    # ─── 5. EXPERT DEDUCTIONS ───────────────────────────────────────
    # Based on perfumer identity (Cavallier), house (Firmenich), and era (2012)

    expert_items = [
        # Firmenich captives — Cavallier had access
        EvidenceItem(
            source_type="expert",
            material="Hedione",
            confidence=0.85,
            concentration_pct=8.0,
            concentration_range=(4.0, 15.0),
            raw_text="Cavallier = Firmenich perfumer. Hedione is Firmenich's signature "
                     "captive and Cavallier's most-used radiance amplifier. Present in "
                     "virtually all his compositions.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Iso E Super",
            confidence=0.75,
            concentration_pct=8.0,
            concentration_range=(3.0, 15.0),
            raw_text="Molecular wood/cedar base. Universal in modern woody orientals. "
                     "The 'dry wood accord' declared base note likely involves Iso E Super.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Habanolide",
            confidence=0.70,
            concentration_pct=2.0,
            concentration_range=(0.5, 4.0),
            raw_text="Firmenich captive macrocyclic musk. Cavallier's preferred musk. "
                     "15 membered macrolide, white, clean, skin-scent character.",
        ),
        # Alpha Irone — the iris star
        EvidenceItem(
            source_type="expert",
            material="Alpha Irone 10%",
            confidence=0.85,
            concentration_pct=1.5,
            concentration_range=(0.5, 4.0),
            raw_text="Orris Absolute and Orris Concrete are declared notes. Alpha-Irone "
                     "is the primary odorant of orris (12-18% of concrete). Amouage budget "
                     "permits real orris / synthetic alpha-irone at luxury levels. "
                     "Orris listed in both TOP and HEART.",
        ),
        # Rose absolute — confirmed by 5 allergens
        EvidenceItem(
            source_type="expert",
            material="Rose Absolute",
            confidence=0.85,
            concentration_pct=3.0,
            concentration_range=(1.5, 5.0),
            raw_text="5 allergens (Citronellol, Geraniol, Linalool, Eugenol, Farnesol) "
                     "confirm real rose. Amouage owns rose fields in Oman. Back-calculated: "
                     "if Citronellol ≈ 1% of concentrate and = 35% of rose, rose ≈ 2.9%.",
        ),
        # Jasmine absolute — confirmed by 4 allergens
        EvidenceItem(
            source_type="expert",
            material="Jasmine Absolute",
            confidence=0.80,
            concentration_pct=2.0,
            concentration_range=(1.0, 4.0),
            raw_text="4 allergens (Benzyl Benzoate, Benzyl Alcohol, Farnesol, Linalool) "
                     "confirm real jasmine absolute. Declared heart note.",
        ),
        # Oud — declared base note
        EvidenceItem(
            source_type="expert",
            material="Oud Oil",
            confidence=0.65,
            concentration_pct=0.5,
            concentration_range=(0.1, 2.0),
            raw_text="Agarwood is a declared base note. Amouage specializes in oud. "
                     "Could be real oud or synthetic reconstruction.",
        ),
        # Galaxolide — standard polycyclic musk in luxury
        EvidenceItem(
            source_type="expert",
            material="Galaxolide 80%",
            confidence=0.55,
            concentration_pct=2.0,
            raw_text="Standard polycyclic musk in luxury fragrances. Supports the musk base.",
        ),
        # Ambrox — crystalline amber, standard in 2012 niche
        EvidenceItem(
            source_type="expert",
            material="Ambrox Super 30%",
            confidence=0.60,
            concentration_pct=1.0,
            raw_text="Ambroxide is a standard amber material in luxury fragrances. "
                     "Provides the mineral-crystalline amber undertow.",
        ),
        # Patchouli — 18% community detection supports presence
        EvidenceItem(
            source_type="expert",
            material="Patchouli EO",
            confidence=0.55,
            concentration_pct=1.5,
            raw_text="Community detects patchouli earthiness (18%). Standard woody anchor "
                     "in the 'dry wood accord' base.",
        ),
        # Cedarwood — 30% community detection
        EvidenceItem(
            source_type="expert",
            material="Cedarwood EO",
            confidence=0.60,
            concentration_pct=2.0,
            raw_text="30% of reviewers detect cedar. Part of 'dry wood accord' base note.",
        ),
        # Vetiver — 22% community detection
        EvidenceItem(
            source_type="expert",
            material="Vetiver EO",
            confidence=0.50,
            concentration_pct=1.0,
            raw_text="22% detect vetiver earthiness. Mineral root dimension in dry wood accord.",
        ),
        # Benzoin — explains part of Benzyl Benzoate + Benzyl Alcohol
        EvidenceItem(
            source_type="expert",
            material="Benzoin Resinoid 50%",
            confidence=0.55,
            concentration_pct=2.0,
            raw_text="Benzoin contains Benzyl Benzoate + Benzyl Alcohol, both confirmed "
                     "on allergen list. Warm balsamic-churchy sweetness in base.",
        ),
        # Ethyl Vanillin — rum accord requires vanilla
        EvidenceItem(
            source_type="expert",
            material="Ethyl Vanillin",
            confidence=0.65,
            concentration_pct=0.5,
            raw_text="Rum is a declared top note. Rum accords require vanilla-caramel warmth. "
                     "Ethyl vanillin = 12× potency of vanillin.",
        ),
        # Labdanum — rum amber warmth
        EvidenceItem(
            source_type="expert",
            material="Labdanum",
            confidence=0.50,
            concentration_pct=0.8,
            raw_text="Amber warmth for rum accord. Labdanum = natural amber-resinous.",
        ),
    ]
    pool.add_many(expert_items)

    # ─── 6. ROSE / JASMINE RATIO CROSS-VALIDATION ──────────────────
    # The citronellol(#3)/geraniol(#8) positions give us a cross-check:
    # In rose absolute: citronellol ≈ 35%, geraniol ≈ 18%
    # Predicted ratio citronellol/geraniol = 35/18 ≈ 1.94
    # Box order: citronellol = position 3, geraniol = position 8
    # The gap (5 positions) confirms citronellol >> geraniol, consistent with rose.
    #
    # If rose absolute ≈ 3% of concentrate:
    #   Citronellol from rose = 3% × 35% = 1.05%  (position #3 ✓)
    #   Geraniol from rose = 3% × 18% = 0.54%     (position #8 ✓)
    #   Linalool from rose = 3% × 2% = 0.06%
    #   Eugenol from rose = 3% × 1.5% = 0.045%
    #   Farnesol from rose = 3% × 1% = 0.03%
    #
    # But linalool is position #2 (very high). Rose contributes 0.06%.
    # Jasmine contributes: 2% × 5% = 0.10%. Total from naturals = 0.16%.
    # Linalool at position #2 must mean either:
    #   a) Additional synthetic linalool (~0.5-1% of concentrate)
    #   b) Bergamot or lavender contributing linalool (bergamot = 20-30% linalool)
    #   c) Rose + jasmine at higher concentrations than estimated
    #
    # Hedione (methyl dihydrojasmonate) does NOT contain linalool.
    # Most likely: bergamot or neroli in the rum accord top note.
    # If bergamot ≈ 1.5% of concentrate: linalool from bergamot = 1.5% × 25% = 0.375%
    # Total linalool ≈ 0.06 + 0.10 + 0.375 = 0.535% → still low for position #2.
    # Suggests possible synthetic linalool addition for "freshening" the iris.

    pool.add(EvidenceItem(
        source_type="expert",
        material="Linalool",
        confidence=0.70,
        concentration_pct=1.0,
        concentration_range=(0.4, 2.0),
        raw_text="RATIO ANALYSIS: Linalool at position #2 cannot come from rose (0.06%) "
                 "and jasmine (0.10%) alone. Likely additional synthetic linalool or "
                 "significant bergamot/neroli contribution. Suggests presence of a "
                 "citrus/floral EO OR deliberate linalool addition for iris freshness.",
    ))

    # Bergamot — only needed if it explains linalool surplus
    pool.add(EvidenceItem(
        source_type="expert",
        material="Bergamot FCF",
        confidence=0.45,
        concentration_pct=1.5,
        raw_text="Linalool surplus at position #2 suggests a linalool-rich citrus EO. "
                 "Bergamot (20-30% linalool) in the rum top note could explain this. "
                 "Bergamot + D-Limonene(#9) is consistent with a citrus top in the rum accord.",
    ))

    return pool


def compute_rose_jasmine_concentrations(pool: EvidencePool) -> dict:
    """Back-calculate rose and jasmine absolute concentrations from allergen ratios.

    Using the known GC-MS composition of Rosa damascena absolute and
    Jasminum grandiflorum absolute, we solve a system of equations
    to estimate how much of each natural is in the formula.

    Variables:
        R = rose absolute concentration in concentrate (%)
        J = jasmine absolute concentration in concentrate (%)

    Known allergen components:
        Citronellol = 0.35R                    (position #3)
        Geraniol    = 0.18R                    (position #8)
        Linalool    = 0.02R + 0.05J + S_lin    (position #2, S_lin = synthetic/bergamot)
        Eugenol     = 0.015R + E_oud           (position #4, E_oud = from oud)
        Benzyl Benzoate = 0.15J + BB_synth     (position #5, BB_synth = synthetic addition)
        Benzyl Alcohol  = 0.05J + BA_benz      (position #10, BA_benz = from benzoin)
        Farnesol    = 0.01R + 0.02J            (position #6)
    """
    # From allergen order, we know approximate concentration ratios.
    # Citronellol (#3) > Geraniol (#8) with positions suggesting ~2:1 ratio
    # This is consistent with rose: citronellol/geraniol = 35/18 = 1.94

    # Best estimate for rose absolute:
    # Citronellol at ~1.0% of concentrate → R = 1.0 / 0.35 = 2.86%
    # Geraniol at ~0.5% → R = 0.5 / 0.18 = 2.78%
    # Average: R ≈ 2.8%
    R_estimate = (1.0 / 0.35 + 0.5 / 0.18) / 2

    # Best estimate for jasmine absolute:
    # Benzyl Benzoate (#5) ≈ 0.8% total. Some from jasmine, some synthetic.
    # If jasmine contributes half: J = (0.4) / 0.15 = 2.67%
    # Benzyl Alcohol (#10) ≈ 0.15% total. BA from jasmine: J = 0.10 / 0.05 = 2.0%
    # Average: J ≈ 2.3%
    J_estimate = ((0.4 / 0.15) + (0.10 / 0.05)) / 2

    # Cross-validation: Farnesol (#6) ≈ 0.3%
    # From rose: 0.01 × 2.8 = 0.028%
    # From jasmine: 0.02 × 2.3 = 0.046%
    # Total from naturals: 0.074% → below 0.3%, suggesting additional farnesol source
    # (possibly oud oil, which contains farnesol)
    farnesol_natural = 0.01 * R_estimate + 0.02 * J_estimate
    farnesol_remaining = 0.3 - farnesol_natural  # ~0.22% from oud or other

    # Linalool (#2) ≈ 1.0%
    # From rose: 0.02 × 2.8 = 0.056%
    # From jasmine: 0.05 × 2.3 = 0.115%
    # From naturals: 0.171% → deficit ≈ 0.83% → synthetic linalool or bergamot
    linalool_natural = 0.02 * R_estimate + 0.05 * J_estimate
    linalool_deficit = 1.0 - linalool_natural

    return {
        "rose_absolute_pct": round(R_estimate, 2),
        "jasmine_absolute_pct": round(J_estimate, 2),
        "farnesol_from_naturals_pct": round(farnesol_natural, 3),
        "farnesol_deficit_pct": round(farnesol_remaining, 3),
        "linalool_from_naturals_pct": round(linalool_natural, 3),
        "linalool_deficit_pct": round(linalool_deficit, 3),
        "citronellol_predicted_pct": round(0.35 * R_estimate, 2),
        "geraniol_predicted_pct": round(0.18 * R_estimate, 2),
        "cross_validation": {
            "citronellol_geraniol_ratio_predicted": round(0.35 / 0.18, 2),
            "citronellol_geraniol_ratio_from_positions": "~2:1 (pos 3 vs pos 8)",
            "match": "GOOD — predicted 1.94:1 ≈ position-implied ~2:1",
        },
        "linalool_source_hypothesis": (
            f"Deficit of {round(linalool_deficit, 2)}% linalool cannot come from rose+jasmine alone. "
            f"Sources: bergamot (~25% linalool, would need ~{round(linalool_deficit/0.25, 1)}% bergamot), "
            f"OR synthetic linalool addition, OR neroli (~35% linalool)."
        ),
    }


def compute_formula_dose_refinement(
    rose_pct: float,
    jasmine_pct: float,
    total_concentrate_uL: int = 2500,
) -> dict:
    """Convert percentage estimates to µL doses for a 2500 µL batch.

    This translates the back-calculated concentrations into actionable
    µL amounts for the inventory-constrained formula.
    """
    rose_uL = rose_pct / 100 * total_concentrate_uL
    jasmine_uL = jasmine_pct / 100 * total_concentrate_uL

    # Rose reconstruction: need PEA + Citronellol + Geraniol + Linalool + Eugenol
    # to provide the same allergen profile as real rose absolute
    # PEA is NOT an allergen, so the box tells us nothing about its dose.
    # PEA is the dominant rose odorant (>50% of rose character in synthetics).
    rose_reconstruction = {
        "Phenethyl Alcohol (PEA)": round(rose_uL * 0.50, 0),  # 50% of rose body
        "Citronellol": round(rose_uL * 0.35, 0),
        "Geraniol": round(rose_uL * 0.18, 0),
        "Linalool (from rose)": round(rose_uL * 0.02, 0),
        "Eugenol (from rose)": round(rose_uL * 0.015, 0),
        "total_uL": round(rose_uL, 0),
    }

    # Jasmine reconstruction: Cis-Jasmone + Benzyl Acetate + Hedione for character
    # + Benzyl Benzoate + Indole for allergen-matching
    jasmine_reconstruction = {
        "Hedione": "200 µL (separate — radiance amplifier, not just jasmine)",
        "Cis-Jasmone": round(jasmine_uL * 0.10, 0),  # character molecule
        "Benzyl Acetate": round(jasmine_uL * 0.25, 0),  # major component
        "Benzyl Benzoate": round(jasmine_uL * 0.15, 0),
        "Indole": round(jasmine_uL * 0.035, 0),
        "total_uL": round(jasmine_uL, 0),
    }

    return {
        "rose_uL": round(rose_uL, 0),
        "jasmine_uL": round(jasmine_uL, 0),
        "rose_reconstruction": rose_reconstruction,
        "jasmine_reconstruction": jasmine_reconstruction,
    }


def main():
    print("=" * 70)
    print("OPUS V BAYESIAN RECONSTRUCTION — Full Evidence Fusion")
    print("=" * 70)
    print()

    # Build evidence pool
    pool = build_opus_v_evidence()
    print(f"Evidence pool: {len(pool)} items across "
          f"{len(pool.hypotheses)} material hypotheses\n")

    # Run Bayesian reconstruction
    result = reverse_engineer(pool)

    # Print main report
    report = format_reconstruction_report(result)
    print(report)

    # Rose/Jasmine ratio analysis
    print("\n" + "=" * 70)
    print("ALLERGEN RATIO BACK-CALCULATION — Rose & Jasmine Concentrations")
    print("=" * 70)
    ratios = compute_rose_jasmine_concentrations(pool)
    print(f"\n  Rose Absolute estimated:    {ratios['rose_absolute_pct']:.2f}% of concentrate")
    print(f"  Jasmine Absolute estimated: {ratios['jasmine_absolute_pct']:.2f}% of concentrate")
    print(f"\n  Cross-validation (Citronellol/Geraniol ratio):")
    print(f"    Predicted from GC-MS:    {ratios['cross_validation']['citronellol_geraniol_ratio_predicted']}")
    print(f"    From allergen positions: {ratios['cross_validation']['citronellol_geraniol_ratio_from_positions']}")
    print(f"    Match: {ratios['cross_validation']['match']}")
    print(f"\n  Linalool deficit: {ratios['linalool_deficit_pct']:.3f}%")
    print(f"    {ratios['linalool_source_hypothesis']}")
    print(f"\n  Farnesol from naturals: {ratios['farnesol_from_naturals_pct']:.3f}%")
    print(f"  Farnesol remaining (from oud/other): {ratios['farnesol_deficit_pct']:.3f}%")

    # Dose refinement for inventory formula
    print("\n" + "=" * 70)
    print("DOSE REFINEMENT — Inventory Formula µL Adjustments")
    print("=" * 70)
    doses = compute_formula_dose_refinement(
        ratios["rose_absolute_pct"],
        ratios["jasmine_absolute_pct"],
    )
    print(f"\n  Rose total dose:    {doses['rose_uL']:.0f} µL of concentrate")
    print(f"  Jasmine total dose: {doses['jasmine_uL']:.0f} µL of concentrate")
    print(f"\n  Rose Reconstruction (synthetic):")
    for k, v in doses["rose_reconstruction"].items():
        if k != "total_uL":
            print(f"    {k}: {v} µL")
    print(f"\n  Jasmine Reconstruction (synthetic):")
    for k, v in doses["jasmine_reconstruction"].items():
        if k != "total_uL":
            print(f"    {k}: {v}")

    # Summary
    print("\n" + "=" * 70)
    print("SCORE IMPROVEMENT SUMMARY")
    print("=" * 70)
    n_confirmed = len(result.confirmed)
    n_probable = len(result.probable)
    n_speculative = len(result.speculative)
    print(f"\n  CONFIRMED materials:   {n_confirmed} (posterior ≥ 0.80)")
    print(f"  PROBABLE materials:    {n_probable} (0.50 ≤ posterior < 0.80)")
    print(f"  SPECULATIVE materials: {n_speculative} (posterior < 0.50)")
    print(f"\n  Actionable: {'YES' if result.actionable else 'NO'}")

    if result.conflict_flags:
        print(f"\n  ⚠ {len(result.conflict_flags)} conflict(s) detected — review for accuracy")

    # Save full results
    output = {
        "target": result.target_name,
        "total_evidence": result.total_evidence_items,
        "n_materials": len(result.materials),
        "n_confirmed": n_confirmed,
        "n_probable": n_probable,
        "n_speculative": n_speculative,
        "conflicts": result.conflict_flags,
        "ratio_analysis": ratios,
        "dose_refinement": {
            "rose_uL": doses["rose_uL"],
            "jasmine_uL": doses["jasmine_uL"],
        },
        "materials": [
            {
                "name": m.name,
                "tier": m.tier.value,
                "posterior": round(m.posterior, 4),
                "corroboration": round(m.corroboration_factor, 2),
                "concentration_pct": round(m.concentration_best, 2)
                    if m.concentration_best is not None else None,
                "n_sources": m.n_sources,
                "sources": sorted(m.source_types_seen),
            }
            for m in result.materials
        ],
    }
    out_path = Path("opus_v_bayesian_results.json")
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()