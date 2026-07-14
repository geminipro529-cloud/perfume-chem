"""Stage 2 — Construction Methodology Selection.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Selects one of 10 construction methodologies for a perfume:
  A. Pyramid Construction (Carles / Roudnitska)        — default
  B. Accord-Based Construction (Carles / Jellinek)
  C. Hedonic Optimization (Computational)
  D. Single-Material Expansion (Roudnitska "One Truth")
  E. Constraint-Based Construction (Regulatory / Cost / Safety)
  F. OAV-Targeted Construction
  G. Texture-First Construction (Ellena / Modern Minimalism)
  H. Performance-First Construction
  I. Cost-Optimized Construction (Commercial)
  J. Minimum-Material Construction (Minimalist / Niche)

Re-exports the existing methodology logic from `future_modules.construction_methodology`
so the pipeline can import from the canonical `engine.orchestration` namespace.

**Inspired by:**
- Philyra (Symrise + IBM) — learns methodology from formula history
- Carles educational papers — bases → modifiers → topnotes
- Roudnitska Le Parfum (1980) — "fortunate proportions"

**Reference:** docs/ATELIER_PIPELINE_PLAN.md, Stage 2.
"""

from __future__ import annotations

from future_modules.construction_methodology import (  # type: ignore[import-not-found]
    ANCHOR_MATERIALS,
    BANGKOK_VP_RATIO,
    COST_EFFICIENCY,
    FIXATIVE_LOADING,
    HEDONIC_TARGETS,
    HEDONIC_WEIGHTS,
    IFRA_CAT4_LIMITS,
    METHODOLOGY_SPECS,
    MINIMUM_VIABLE_FORMULAS,
    MIXTURE_SUPPRESSION_FACTOR,
    MULTIFUNCTIONAL_MATERIALS,
    NATURAL_EXTENSIONS,
    OAV_PERCEPTUAL_STATUS,
    OPTIMAL_LOG_OAV_SD,
    PYRAMID_OAV_RATIOS,
    TEXTURE_MATERIALS,
    TEXTURE_RATIOS,
    T_BANGKOK,
    T_SKIN,
    VP_NOTE_TIERS,
    AccordSpec,
    AnchorMaterial,
    ConcentrationBracket,
    CostEfficiencyData,
    FixativeStrategy,
    FragranceFamily,
    HedonicCategory,
    HedonicMaterialTarget,
    IFRAConstraint,
    MarketSegment,
    MethodologySpec,
    MethodologyType,
    MinimumViableFormula,
    NaturalExtension,
    NoteTier,
    PyramidBlueprint,
    TextureLayer,
    TextureMaterial,
    apply_mixture_suppression,
    bangkok_temperature_adjustment,
    check_hedonic_distribution,
    check_ifra_compliance,
    clausius_clapeyron_vp_ratio,
    compute_hedonic_objective,
    estimate_mixture_suppression,
    evaluate_pyramid_balance,
    evaporative_half_life_estimator,
    get_extension,
    get_fixative_strategy,
    get_min_viable,
    get_oav_cost_efficiency,
    get_oav_sweet_spot,
    get_pyramid_blueprint,
    get_texture_blueprint,
    get_texture_classification,
    materialize_accord_spec,
    recommend_accord_count,
    select_anchor,
)

__all__ = [
    "ANCHOR_MATERIALS",
    "BANGKOK_VP_RATIO",
    "COST_EFFICIENCY",
    "FIXATIVE_LOADING",
    "HEDONIC_TARGETS",
    "HEDONIC_WEIGHTS",
    "IFRA_CAT4_LIMITS",
    "METHODOLOGY_SPECS",
    "MINIMUM_VIABLE_FORMULAS",
    "MIXTURE_SUPPRESSION_FACTOR",
    "MULTIFUNCTIONAL_MATERIALS",
    "NATURAL_EXTENSIONS",
    "OAV_PERCEPTUAL_STATUS",
    "OPTIMAL_LOG_OAV_SD",
    "PYRAMID_OAV_RATIOS",
    "TEXTURE_MATERIALS",
    "TEXTURE_RATIOS",
    "T_BANGKOK",
    "T_SKIN",
    "VP_NOTE_TIERS",
    "AccordSpec",
    "AnchorMaterial",
    "ConcentrationBracket",
    "CostEfficiencyData",
    "FixativeStrategy",
    "FragranceFamily",
    "HedonicCategory",
    "HedonicMaterialTarget",
    "IFRAConstraint",
    "MarketSegment",
    "MethodologySpec",
    "MethodologyType",
    "MinimumViableFormula",
    "NaturalExtension",
    "NoteTier",
    "PyramidBlueprint",
    "TextureLayer",
    "TextureMaterial",
    "apply_mixture_suppression",
    "bangkok_temperature_adjustment",
    "check_hedonic_distribution",
    "check_ifra_compliance",
    "clausius_clapeyron_vp_ratio",
    "compute_hedonic_objective",
    "estimate_mixture_suppression",
    "evaluate_pyramid_balance",
    "evaporative_half_life_estimator",
    "get_extension",
    "get_fixative_strategy",
    "get_min_viable",
    "get_oav_cost_efficiency",
    "get_oav_sweet_spot",
    "get_pyramid_blueprint",
    "get_texture_blueprint",
    "get_texture_classification",
    "materialize_accord_spec",
    "recommend_accord_count",
    "select_anchor",
]
