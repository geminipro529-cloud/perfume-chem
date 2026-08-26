"""Future Modules — Formulation Intelligence Pipeline Integration Layer.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

This package provides 12 specialized modules that encode the Formulation
Intelligence Database (May 2026) as composable, pipeline-integrable Python
modules. Each module follows the same conventions as the existing engine/
architecture: frozen dataclasses, stand-alone functions, comprehensive type
hints, and `from __future__ import annotations`.

Module summary:
  _shared_types            — Enums, constants, base dataclasses (shared vocabulary)
  construction_methodology — 10 quantified construction methods (A through J)
  balance_axes             — 8-axis balance evaluation
  family_hedonic_optimizer — Family-specific OAV targets, secret materials, pitfalls
  accord_library           — Quantified accord recipes (Grojsman, jasmine, chypre, etc.)
  synergy_matrix           — Synergy/antagonist pair database with quantitative factors
  character_shift_zones     — Hedonic dose-response zone database (indole, calone, etc.)
  chemical_compatibility    — Reactive pair detection and compatible stability checks
  performance_profiles     — VP, half-life, substantivity, sillage, climate correction
  dosing_tables            — µL dosing, stock preparation, potent material handling
  iteration_protocol       — Formula iteration timeline and Roudnitska stop criterion
  edge_cases               — Anosmia coverage, climate correction, solubility, ghost notes
  literature_references    — Tiered citation database (A through E)

Integration pattern:
  1. Import the relevant module
  2. Call its public functions with FormulaState or ingredient dicts
  3. Results are dataclasses or tuples — composable with the gate pipeline

PERFORMANCE NOTE: This __init__.py only imports _shared_types to keep the
package import fast (~15ms vs ~389ms with all submodules). Consumers import
submodules directly (e.g. `from future_modules.synergy_matrix import ...`),
which works regardless of __init__.py content since Python resolves submodule
imports via the filesystem. See gates.py for the direct-import pattern.
"""

from __future__ import annotations

# Shared types (always imported — provides the vocabulary)
from ._shared_types import (  # noqa: F401  # re-export shared vocabulary
    # Constants
    ACTIVITY_COEFFICIENT_RANGES,
    BANGKOK_VP_RATIO,
    CROSS_FAMILY_COMPATIBILITY,
    DELTA_H_VAP_DEFAULT,
    FAMILY_FLAWS,
    FIXATIVE_LOADING,
    HEDONIC_TARGETS,
    HEDONIC_WEIGHTS,
    MACERATION_STAGES,
    MATERIAL_CLASS_DISTRIBUTION,
    MIN_OVERLAP_WINDOW_MINUTES,
    MIXTURE_SUPPRESSION_FACTOR,
    OAV_PERCEPTUAL_STATUS,
    OPTIMAL_ACCORD_COUNT,
    OPTIMAL_LOG_OAV_SD,
    PYRAMID_OAV_RATIOS,
    TEXTURE_RATIOS,
    TRANSITION_FAMILIES,
    # Dataclasses
    AccordRecipe,
    AnosmiaData,
    AntagonistPair,
    BalanceReport,
    ChemicalReaction,
    CompatibilityReport,
    # Enums
    ConcentrationBracket,
    ConcentrationConversion,
    DiffusionLayer,
    DosingEntry,
    FamilyFlaw,
    FragranceFamily,
    GhostNoteMaterial,
    HedgeShiftZone,
    HedonicCategory,
    IterationStage,
    MarketSegment,
    MaterialShiftProfile,
    MethodologyType,
    NaturalEOData,
    NoteTier,
    PerformanceData,
    PyramidRatio,
    Reference,
    ReferenceTier,
    SolubilityData,
    SolubilityRisk,
    SynergyPair,
    TextureLayer,
    # Utility functions
    accelerated_aging_time,
    clausius_clapeyron_vp_ratio,
    estimate_mixture_suppression,
    get_note_tier_from_vp,
    get_oav_perceptual_status,
)
