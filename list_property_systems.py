"""
Overview of all ingredient property systems in the perfume-chem engine.
"""
import sys

sys.path.insert(0, r'D:\chatbots\perfume-chem')

def list_all_property_systems():
    """List all available property tracking systems."""
    print("=" * 80)
    print("INGREDIENT PROPERTY SYSTEMS IN PERFUME-CHEM")
    print("=" * 80)

    # 1. Ingredient Intelligence (Main profiles)
    print("\n1. INGREDIENT INTELLIGENCE (engine/ingredient_intelligence.py)")
    print("-" * 60)
    print("   Primary material profiles with 13 character dimensions:")
    print("   - warmth, sweetness, freshness, powdery, green")
    print("   - animalic, radiance, woody, spicy, floral")
    print("   - smoky, creamy, transparency")
    print("   - Physical: MW, VP, ClogP, ODT")
    print("   - Classification: note, role, texture")
    print("   - Relationships: synergies, avoid list")
    print("   - Scientific: activity_coef, hedonic, or_family")

    from engine.ingredient_intelligence import _PROFILES
    print(f"   Profiles loaded: {len(_PROFILES)} materials")

    # 2. Data Spine Material Schema
    print("\n2. DATA SPINE MATERIAL SCHEMA (engine/data_spine/material.py)")
    print("-" * 60)
    print("   Canonical material record with comprehensive fields:")
    print("   - Identity: canonical_name, aliases, CAS, SMILES, InChIKey")
    print("   - Physical: MW, density, logP, functional groups, chirality")
    print("   - Vapor: VP@25C, Antoine constants, dH_vap")
    print("   - Solubility: Hansen HSP (delta_d, delta_p, delta_h)")
    print("   - Olfactory: ODT (air, ethanol), Stevens exponent")
    print("   - Receptor: OR targets (gene, EC50, Hill)")
    print("   - Trigeminal: TRPM8, TRPA1, TRPV1, TRPV3, nasal_pungency")
    print("   - Regulatory: hedonic_valence, IFRA cap")
    print("   - Supplier: PerfumersWorld SKU, price")
    print("   - Categorization: families, character blurb")

    # 3. Odor Thresholds
    print("\n3. ODOR THRESHOLDS (engine/odor_thresholds.py)")
    print("-" * 60)
    from engine.odor_thresholds import ODT_DATA
    print("   ODT values for materials:")
    print("   - odt_air_ppb: detection in air (parts per billion)")
    print("   - odt_ethanol_ppm: detection in ethanol (parts per million)")
    print("   - character: odor description")
    print(f"   Materials tracked: {len(ODT_DATA)}")

    # 4. IFRA Safety
    print("\n4. IFRA SAFETY (engine/ifra_safety.py)")
    print("-" * 60)
    from engine.ifra_safety import IFRA_CAT4_LIMITS
    print("   Regulatory limits for Category 4 (Fine Fragrance):")
    print("   - Max use levels (% in finished product)")
    print("   - EU Cosmetics Regulation 1223/2009 Annex III (26 allergens)")
    print(f"   Materials with limits: {len(IFRA_CAT4_LIMITS)}")

    # 5. Cost Analysis
    print("\n5. COST ANALYSIS (engine/cost_analysis.py)")
    print("-" * 60)
    from engine.cost_analysis import MATERIAL_COSTS_PER_KG
    print("   Material costs for budget estimation:")
    print("   - USD per kg (industry bulk pricing)")
    print("   - Used for COG (Cost of Goods) estimation")
    print(f"   Materials priced: {len(MATERIAL_COSTS_PER_KG)}")

    # 6. Skin Interaction
    print("\n6. SKIN INTERACTION (engine/skin_interaction.py)")
    print("-" * 60)
    from engine.skin_interaction import SKIN_PHYSCHEM
    print("   Skin permeation and substantivity data:")
    print("   - logP, MW, substantivity index")
    print("   - Skin partition modeling")
    print(f"   Materials tracked: {len(SKIN_PHYSCHEM)}")

    # 7. Temporal Graph
    print("\n7. TEMPORAL GRAPH (engine/temporal_graph.py)")
    print("-" * 60)
    print("   Temporal evolution modeling:")
    print("   - Top/heart/base classification over time")
    print("   - Projection and sillage curves")
    print("   - Uses VP, MW, and ODT for time-evolution")

    # 8. Hedonic Model
    print("\n8. HEDONIC MODEL (engine/hedonic_model.py)")
    print("-" * 60)
    from engine.hedonic_model import HEDONIC_VALENCE
    print("   Pleasantness ratings:")
    print("   - Scale: -1.0 (unpleasant) to +1.0 (pleasant)")
    print(f"   Materials rated: {len(HEDONIC_VALENCE)}")

    # 9. Diffusion Model
    print("\n9. DIFFUSION MODEL (engine/diffusion_model.py)")
    print("-" * 60)
    print("   Vapor-phase diffusion and projection:")
    print("   - Graham's Law diffusion rates")
    print("   - Air-liquid partition coefficients")
    print("   - Sillage cone geometry")

    # 10. Volatility Model
    print("\n10. VOLATILITY MODEL (engine/volatility.py)")
    print("-" * 60)
    print("   Vapor pressure and volatility classification:")
    print("   - VP @ 25C in Pa")
    print("   - Boiling points")
    print("   - Volatility curves over time")

    # 11. Material Interactions
    print("\n11. MATERIAL INTERACTIONS (engine/material_interactions.py)")
    print("-" * 60)
    from engine.material_interactions import CO_OCCURRENCE_RULES
    print("   Known material interactions:")
    print("   - Synergies, boosts, suppressions")
    print("   - Bridge materials")
    print(f"   Interactions tracked: {len(CO_OCCURRENCE_RULES)}")

    # 12. Receptor Binding
    print("\n12. RECEPTOR BINDING (engine/receptor/binding.py)")
    print("-" * 60)
    print("   Olfactory receptor binding data:")
    print("   - OR targets with EC50 values")
    print("   - Hill coefficients")

    # 13. Trigeminal
    print("\n13. TRIGEMINAL EFFECTS (engine/trigeminal.py)")
    print("-" * 60)
    from engine.trigeminal import TRIGEMINAL_PROFILES
    print("   Chemesthetic (non-olfactory) effects:")
    print("   - Cooling, warming, pungency scores")
    print("   - TRP channel activation")
    print(f"   Materials tracked: {len(TRIGEMINAL_PROFILES)}")

    # 14. Fingerprint
    print("\n14. MOLECULAR FINGERPRINTS (engine/fingerprint.py)")
    print("-" * 60)
    print("   Vector representations for ML:")
    print("   - Property vectors for similarity search")
    print("   - Used in reconstruction pipeline")

    # 15. Science Data
    print("\n15. SCIENCE DATA (engine/science_data.py)")
    print("-" * 60)
    print("   Scientific/physical data:")
    print("   - Molecular weights, vapor pressures")
    print("   - Partition coefficients")
    print("   - Stability and adaptation profiles")

    print("\n" + "=" * 80)
    print("SYSTEM SUMMARY")
    print("=" * 80)
    print("The perfume-chem engine tracks ingredients across multiple domains:")
    print("  - PERCEPTION: Character dimensions, hedonic value, odor thresholds")
    print("  - PHYSICS: MW, VP, diffusion, volatility, skin interaction")
    print("  - BIOLOGY: OR binding, trigeminal effects, substantivity")
    print("  - REGULATION: IFRA limits, allergen declarations")
    print("  - ECONOMICS: Cost per kg, COG estimation")
    print("  - RELATIONSHIPS: Synergies, avoid lists, interactions")
    print("=" * 80)


if __name__ == "__main__":
    list_all_property_systems()
