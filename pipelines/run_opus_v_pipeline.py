"""Run the full reconstruction pipeline on Amouage Opus V.

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
This script validates every module in the pipeline and produces
the category-based scorecard for the current perfume of interest.
"""

import json
import sys
import os

# Ensure engine is importable
sys.path.insert(0, os.path.dirname(__file__))

# Initialise tracing → AI Toolkit trace viewer (http://localhost:4318)
from engine.tracing import setup_tracing
setup_tracing()

from engine.reconstruction_pipeline import (
    FragranceSpec,
    run_reconstruction_pipeline,
    format_pipeline_report,
    pipeline_report_to_dict,
)
from engine.reverse_engineer import EvidenceItem


def build_opus_v_spec() -> FragranceSpec:
    """Construct the FragranceSpec for Amouage Opus V from all known evidence."""

    # ── Expert evidence items (pre-built) ────────────────────────
    expert_evidence = [
        # Allergen position-based concentration estimates
        EvidenceItem(
            source_type="expert",
            material="Benzyl Salicylate",
            confidence=0.90,
            concentration_pct=6.0,
            concentration_range=(4.0, 8.0),
            raw_text="Allergen position #1 → highest concentration. "
                     "Diffusion cushion + fixative in white floral-iris base.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Linalool",
            confidence=0.75,
            concentration_pct=1.2,
            concentration_range=(0.5, 2.5),
            raw_text="Allergen position #2 → very high. From rose + jasmine + possible "
                     "synthetic linalool addition or bergamot.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Citronellol",
            confidence=0.75,
            concentration_pct=1.0,
            concentration_range=(0.4, 2.0),
            raw_text="Allergen position #3 → high. ~35% of rose absolute. "
                     "Back-calc: if citronellol ≈ 1%, rose absolute ≈ 2.9%.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Eugenol",
            confidence=0.70,
            concentration_pct=0.4,
            concentration_range=(0.1, 1.0),
            raw_text="Allergen position #4. From rose absolute (~1.5%) + oud oil.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Benzyl Benzoate",
            confidence=0.70,
            concentration_pct=0.8,
            concentration_range=(0.3, 2.0),
            raw_text="Allergen position #5. From jasmine (~15%) + benzoin + fixative.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Farnesol",
            confidence=0.65,
            concentration_pct=0.3,
            concentration_range=(0.05, 0.8),
            raw_text="Allergen position #6. Sesquiterpene from rose, jasmine, oud.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Hydroxycitronellal",
            confidence=0.80,
            concentration_pct=1.5,
            concentration_range=(0.3, 3.0),
            raw_text="Allergen position #7. SYNTHETIC — deliberate addition. "
                     "Dewy muguet transparency modifier.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Geraniol",
            confidence=0.75,
            concentration_pct=0.5,
            concentration_range=(0.1, 1.0),
            raw_text="Allergen position #8. ~18% of rose absolute. "
                     "Ratio with citronellol = 1.94:1.",
        ),
        EvidenceItem(
            source_type="expert",
            material="D-Limonene",
            confidence=0.65,
            concentration_pct=0.2,
            concentration_range=(0.05, 0.5),
            raw_text="Allergen position #9. From citrus EO in rum accord.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Benzyl Alcohol",
            confidence=0.70,
            concentration_pct=0.15,
            concentration_range=(0.03, 0.5),
            raw_text="Allergen position #10. From jasmine (~5%) + balsams.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Alpha-Isomethyl Ionone",
            confidence=0.80,
            concentration_pct=0.8,
            concentration_range=(0.1, 2.0),
            raw_text="Allergen position #11 = LAST. Confirmed present but at "
                     "LOWEST concentration among all allergens.",
        ),
        # Firmenich captives — Cavallier access
        EvidenceItem(
            source_type="expert",
            material="Hedione",
            confidence=0.85,
            concentration_pct=8.0,
            concentration_range=(4.0, 15.0),
            raw_text="Cavallier = Firmenich perfumer. Hedione is Firmenich signature "
                     "captive and Cavallier's most-used radiance amplifier.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Iso E Super",
            confidence=0.75,
            concentration_pct=8.0,
            concentration_range=(3.0, 15.0),
            raw_text="Molecular wood/cedar base. Universal in modern woody orientals. "
                     "Dry wood accord declared base note.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Habanolide",
            confidence=0.70,
            concentration_pct=2.0,
            concentration_range=(0.5, 4.0),
            raw_text="Firmenich captive macrocyclic musk. Cavallier's preferred musk.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Alpha Irone 10%",
            confidence=0.85,
            concentration_pct=1.5,
            concentration_range=(0.5, 4.0),
            raw_text="Orris declared in TOP and HEART. Alpha-Irone is primary "
                     "odorant of orris (12-18% of concrete). Amouage budget permits.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Rose Absolute",
            confidence=0.85,
            concentration_pct=3.0,
            concentration_range=(1.5, 5.0),
            raw_text="5 allergens confirm real rose. Amouage owns rose fields. "
                     "Back-calculated: rose ≈ 2.9% from citronellol/geraniol.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Jasmine Absolute",
            confidence=0.80,
            concentration_pct=2.0,
            concentration_range=(1.0, 4.0),
            raw_text="4 allergens confirm real jasmine absolute. Heart note.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Oud Oil",
            confidence=0.65,
            concentration_pct=0.5,
            concentration_range=(0.1, 2.0),
            raw_text="Agarwood declared base. Amouage specializes in oud.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Galaxolide 80%",
            confidence=0.55,
            concentration_pct=2.0,
            raw_text="Standard polycyclic musk in luxury fragrances.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Ambrox Super 30%",
            confidence=0.60,
            concentration_pct=1.0,
            raw_text="Ambroxide standard in luxury. Mineral-crystalline amber.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Patchouli EO",
            confidence=0.55,
            concentration_pct=1.5,
            raw_text="18% community detection. Woody anchor in dry wood accord.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Cedarwood EO",
            confidence=0.60,
            concentration_pct=2.0,
            raw_text="30% community detection. Part of dry wood accord base.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Vetiver EO",
            confidence=0.50,
            concentration_pct=1.0,
            raw_text="22% detect vetiver earthiness. Mineral root dimension.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Benzoin Resinoid 50%",
            confidence=0.55,
            concentration_pct=2.0,
            raw_text="Contains Benzyl Benzoate + Benzyl Alcohol (both on allergen list). "
                     "Warm balsamic-churchy sweetness.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Ethyl Vanillin",
            confidence=0.65,
            concentration_pct=0.5,
            raw_text="Rum accord requires vanilla-caramel warmth.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Labdanum",
            confidence=0.50,
            concentration_pct=0.8,
            raw_text="Amber warmth for rum accord. Natural amber-resinous.",
        ),
        # Linalool ratio analysis
        EvidenceItem(
            source_type="expert",
            material="Linalool",
            confidence=0.70,
            concentration_pct=1.0,
            concentration_range=(0.4, 2.0),
            raw_text="RATIO ANALYSIS: Linalool at position #2 cannot come from "
                     "rose+jasmine alone. Deficit of ~0.83%. Implies bergamot or "
                     "synthetic linalool.",
        ),
        EvidenceItem(
            source_type="expert",
            material="Bergamot FCF",
            confidence=0.45,
            concentration_pct=1.5,
            raw_text="Linalool surplus implies linalool-rich citrus EO. "
                     "Bergamot (20-30% linalool) in rum top note.",
        ),
    ]

    # ── Absent allergen evidence (negative) ──────────────────────
    absent_allergens_evidence = []
    for material, text in [
        ("Coumarin", "NOT on allergen list → absent or below threshold. Eliminates tonka."),
        ("Oakmoss", "NOT on allergen list → no chypre base."),
        ("Treemoss", "NOT on allergen list → no chypre base."),
        ("Isoeugenol", "NOT on allergen list → eugenol from naturals, not synthetic."),
        ("Cinnamaldehyde", "NOT on allergen list → no cinnamon."),
        ("Cinnamyl Alcohol", "NOT on allergen list → no cinnamon alcohol."),
        ("Hexyl Cinnamal", "NOT on allergen list → no hexyl cinnamal."),
        ("Amyl Cinnamal", "NOT on allergen list → no amylcinnamaldehyde."),
    ]:
        absent_allergens_evidence.append(EvidenceItem(
            source_type="allergen",
            material=material,
            confidence=0.05,
            raw_text=text,
        ))

    spec = FragranceSpec(
        name="Amouage Opus V",
        perfumer="Jacques Cavallier-Belletrud",  # Must match perfumer_signature.py keys
        house="Amouage",
        year=2012,
        retail_price_usd=230.0,
        bottle_size_ml=100,
        concentration_pct=25.0,

        # Official note pyramid
        top_notes=["orris", "iris", "rum"],
        heart_notes=["orris", "rose", "jasmine"],
        base_notes=["oud", "leather", "wood", "amber"],

        # Box allergen declaration (ordered by concentration)
        declared_allergens=[
            "Benzyl Salicylate",
            "Linalool",
            "Citronellol",
            "Eugenol",
            "Benzyl Benzoate",
            "Farnesol",
            "Hydroxycitronellal",
            "Geraniol",
            "Limonene",
            "Benzyl Alcohol",
            "Alpha-Isomethyl Ionone",
        ],

        # Community review votes (Fragrantica + Basenotes aggregate)
        community_votes={
            "iris":       0.85,
            "orris":      0.72,
            "wood":       0.68,
            "powder":     0.55,
            "oud":        0.52,
            "rose":       0.48,
            "musk":       0.45,
            "leather":    0.38,
            "amber":      0.35,
            "jasmine":    0.30,
            "vanilla":    0.25,
            "vetiver":    0.22,
            "patchouli":  0.18,
            "sandalwood": 0.15,
            "cedar":      0.30,
        },
        total_reviewers=200,

        # Known allergen ratios from GC-MS of naturals
        allergen_ratios={"citronellol:geraniol": 1.94},

        # Estimated materials % for COG analysis
        estimated_materials_pct={
            "Rose Absolute":     2.82,
            "Jasmine Absolute":  2.33,
            "Alpha Irone":       0.15,  # 10% dilution × 1.5%
            "Oud Oil":           0.50,
            "Hedione":           8.00,
            "Iso E Super":       8.00,
            "Benzyl Salicylate": 6.00,
            "Habanolide":        2.00,
            "Galaxolide":        1.60,  # 80% dilution × 2.0%
            "Ambrox":            0.30,  # 30% dilution × 1.0%
            "Hydroxycitronellal":1.50,
            "Patchouli EO":      1.50,
            "Cedarwood EO":      2.00,
            "Vetiver EO":        1.00,
            "Benzoin":           1.00,  # 50% dilution × 2.0%
            "Ethyl Vanillin":    0.50,
            "Labdanum":          0.80,
            "AIMI":              0.80,
            "Bergamot FCF":      1.50,
            "D-Limonene":        0.20,
        },

        price_tier="luxury_niche",
        fragrance_family="iris",
        known_reformulation_year=None,

        # All pre-built evidence
        additional_evidence=expert_evidence + absent_allergens_evidence,
    )

    return spec


def main():
    print("=" * 80)
    print("  OPUS V RECONSTRUCTION PIPELINE — Full Validation Run")
    print("=" * 80)
    print()

    # Build specification
    print("Building FragranceSpec for Amouage Opus V...")
    spec = build_opus_v_spec()
    print(f"  Allergens: {len(spec.declared_allergens)}")
    print(f"  Expert evidence items: {len(spec.additional_evidence)}")
    print(f"  Community notes: {len(spec.community_votes)}")
    print(f"  Material estimates: {len(spec.estimated_materials_pct)}")
    print()

    # Run pipeline
    print("Running reconstruction pipeline (7 stages)...")
    print("-" * 80)
    try:
        report = run_reconstruction_pipeline(spec)
    except Exception as e:
        print(f"\n*** PIPELINE FAILED ***")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Print the report
    print()
    print(format_pipeline_report(report))

    # Summary validation
    print()
    print("=" * 80)
    print("  VALIDATION SUMMARY")
    print("=" * 80)
    print(f"  Pipeline completed: YES")
    print(f"  Elapsed: {report.elapsed_seconds:.2f}s")
    print(f"  Categories scored: {len(report.category_scores)}/12")
    print(f"  Overall confidence: {report.overall_confidence:.1f}/100")
    print(f"  Strongest: {report.strongest_category.category} ({report.strongest_category.score:.1f})")
    print(f"  Weakest: {report.weakest_category.category} ({report.weakest_category.score:.1f})")
    print(f"  Materials identified: {len(report.final_materials)}")
    print(f"  Optimization targets: {len(report.optimization_targets)}")

    # Check each module produced output
    modules_ok = {
        "Bayesian": report.bayesian_result is not None,
        "IFRA": report.ifra_result is not None,
        "Allergen": report.allergen_result is not None,
        "Perfumer": report.perfumer_result is not None,
        "COG": report.cost_result is not None,
        "ODT": report.odt_result is not None,
        "Interactions": report.interaction_result is not None,
        "VaporPressure": report.vp_result is not None,
        "Temporal": report.temporal_result is not None,
        "Captive": report.captive_result is not None,
        "Regulatory": report.regulatory_result is not None,
        "MolecularWeight": report.mw_result is not None,
    }
    print(f"\n  Module status:")
    for mod, ok in modules_ok.items():
        status = "OK" if ok else "FAILED"
        print(f"    {mod:15s}: {status}")

    all_ok = all(modules_ok.values())
    print(f"\n  All modules passed: {'YES' if all_ok else 'NO'}")

    # Save JSON output
    output_path = os.path.join(os.path.dirname(__file__), "opus_v_pipeline_results.json")
    result_dict = pipeline_report_to_dict(report)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    main()