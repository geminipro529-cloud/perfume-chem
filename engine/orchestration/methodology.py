"""Stage 2 — Construction Methodology Selection.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Selects an evidence-compatible construction methodology for a perfume.
Legacy composition-derived hedonic methods remain in ``future_modules`` only.

Source methodologies:
  A. Pyramid Construction (Carles / Roudnitska)        — default
  B. Accord-Based Construction (Carles / Jellinek)
  C. Hedonic Optimization (Computational; excluded from active API)
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

from dataclasses import replace

from future_modules import _shared_types
from future_modules import construction_methodology as _construction_methodology


def _export(name: str, fallback_name: str | None = None):
    """Return a symbol from methodology first, then shared-types fallback."""
    if hasattr(_construction_methodology, name):
        return getattr(_construction_methodology, name)
    if fallback_name is None:
        fallback_name = name
    if hasattr(_shared_types, fallback_name):
        return getattr(_shared_types, fallback_name)
    raise ImportError(f"Required methodology symbol {name} missing from both orchestration sources")


ANCHOR_MATERIALS = _export("ANCHOR_MATERIALS")
COST_EFFICIENCY = _export("COST_EFFICIENCY")
FIXATIVE_LOADING = _export("FIXATIVE_LOADING")
IFRA_CAT4_LIMITS = _export("IFRA_CAT4_LIMITS")
METHODOLOGY_SPECS = tuple(
    replace(
        spec,
        philosophy="Optimize cost while preserving the declared target and constraints.",
    )
    if spec.name == "Cost-Optimized Construction"
    else spec
    for spec in _export("METHODOLOGY_SPECS")
    if spec.name != "Hedonic Optimization"
)
MINIMUM_VIABLE_FORMULAS = _export("MINIMUM_VIABLE_FORMULAS")
MULTIFUNCTIONAL_MATERIALS = _export("MULTIFUNCTIONAL_MATERIALS")
NATURAL_EXTENSIONS = _export("NATURAL_EXTENSIONS")
PYRAMID_OAV_RATIOS = _export("PYRAMID_OAV_RATIOS")
TEXTURE_MATERIALS = _export("TEXTURE_MATERIALS")
T_BANGKOK = _export("T_BANGKOK", "T_BANGKOK")
T_SKIN = _export("T_SKIN", "T_SKIN")
VP_NOTE_TIERS = _export("VP_NOTE_TIERS", "VP_NOTE_TIERS")
AccordSpec = _export("AccordSpec")
AnchorMaterial = _export("AnchorMaterial")
ConcentrationBracket = _export("ConcentrationBracket")
CostEfficiencyData = _export("CostEfficiencyData")
FixativeStrategy = _export("FixativeStrategy")
FragranceFamily = _export("FragranceFamily")
IFRAConstraint = _export("IFRAConstraint")
MethodologySpec = _export("MethodologySpec")
MethodologyType = _export("MethodologyType")
MinimumViableFormula = _export("MinimumViableFormula")
NaturalExtension = _export("NaturalExtension")
NoteTier = _export("NoteTier")
PyramidBlueprint = _export("PyramidBlueprint")
TextureLayer = _export("TextureLayer")
TextureMaterial = _export("TextureMaterial")
get_extension = _export("get_extension")
get_fixative_strategy = _export("get_fixative_strategy")
get_min_viable = _export("get_min_viable")
get_oav_cost_efficiency = _export("get_oav_cost_efficiency")
get_oav_sweet_spot = _export("get_oav_sweet_spot")
get_pyramid_blueprint = _export("get_pyramid_blueprint")
get_texture_blueprint = _export("get_texture_blueprint")
get_texture_classification = _export("get_texture_classification")
materialize_accord_spec = _export("materialize_accord_spec")
recommend_accord_count = _export("recommend_accord_count")
select_anchor = _export("select_anchor")
apply_mixture_suppression = _export("apply_mixture_suppression")
check_ifra_compliance = _export("check_ifra_compliance")
evaluate_pyramid_balance = _export("evaluate_pyramid_balance")
evaporative_half_life_estimator = _export("evaporative_half_life_estimator")
estimate_mixture_suppression = _export("estimate_mixture_suppression")

# Compatibility aliases that currently live in `_shared_types`.
BANGKOK_VP_RATIO = _export("BANGKOK_VP_RATIO", "BANGKOK_VP_RATIO")
MIXTURE_SUPPRESSION_FACTOR = _export("MIXTURE_SUPPRESSION_FACTOR", "MIXTURE_SUPPRESSION_FACTOR")
OAV_PERCEPTUAL_STATUS = _export("OAV_PERCEPTUAL_STATUS", "OAV_PERCEPTUAL_STATUS")
OPTIMAL_LOG_OAV_SD = _export("OPTIMAL_LOG_OAV_SD", "OPTIMAL_LOG_OAV_SD")
TEXTURE_RATIOS = _export("TEXTURE_RATIOS", "TEXTURE_RATIOS")
clausius_clapeyron_vp_ratio = _export("clausius_clapeyron_vp_ratio")
bangkok_temperature_adjustment = _export("bangkok_temperature_adjustment")

__all__ = [
    "ANCHOR_MATERIALS",
    "BANGKOK_VP_RATIO",
    "COST_EFFICIENCY",
    "FIXATIVE_LOADING",
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
    "IFRAConstraint",
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
    "check_ifra_compliance",
    "clausius_clapeyron_vp_ratio",
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
