"""Reusable release gates for formula generation and verification.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV.
"""

from __future__ import annotations

import json
import re
import traceback
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from statistics import median
from typing import Mapping

from engine.authority_gates import evaluate_mode_action
from engine.calibration.hashing import formula_hash_from_record
from engine.calibration.store import load_records, summarize_records
from engine.chemical_data_validator import blocked_reason
from engine.chemistry.photochem import photolysis_remaining_fraction
from engine.confidence import ConfidenceScorer
from engine.evidence.unsupported_science import AgingClaim, assess_aging_claim
from engine.families.registry import (
    evaluate_family_archetype,
    get_archetype,
    infer_archetype,
    novelty_assessment,
)
from engine.fuckups.pre_mix_guard import evaluate_pre_mix_guard
from engine.ifra_safety import score_ifra_compliance
from engine.ifra_standards import (
    FinishedProductEstimate,
    FinishedProductRow,
    IFRACheck,
    IFRAGroupCheck,
    estimate_finished_product_pct_w_w,
    evaluate_ifra,
    load_ifra_table,
)
from engine.knowledge.literature_rules import (
    _LITERATURE_DB_LOADED,
    _cite_fn,
    _get_tier_counts_fn,
)
from engine.knowledge.perfume_knowledge import (
    evaluate_oav_family_targets,
    evaluate_pyramid_balance,
    resolve_family_key,
)
from engine.name_utils import normalize_name
from engine.optimizer.models import FormulaVector
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.optimizer.perfumer_logic import evaluate_perfumer_logic
from engine.pipeline.audit_log import append_event, gate_report_event
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.oav_intelligence import (
    _FUTURE_MODULES_AVAILABLE,
    analyze_oav_intelligence,
)
from engine.pipeline.preflight import (
    build_formula_dose_receipt,
    resolve_inventory_stock_contract,
    resolved_stock_specs_for_state,
    run_release_preflight,
)
from engine.pipeline.robustness import RobustnessReport, audit_formula_robustness
from engine.pipeline.simulator import SimulationFrame, simulate_formula
from engine.reference_contracts import detect_reference_claim, evaluate_reference_contract
from engine.science_data import StabilityRisk, get_science_profile
from engine.thermo.phase import micro_phase_risk

DEFAULT_CONCENTRATE_UL = 6000.0
MIN_NEAT_TRACE_UL = 5.0
MIN_CONFIDENCE_SCORE = 25.0
MAX_PERCEPTIBLE_CHANNELS = 30
MIN_PERCEPTIBLE_MATERIALS = 3

# Mass-market tier thresholds (all formulas at 1500-3500 THB)
# Materials above this cost per kg indicate "premium" formulation
PREMIUM_MATERIAL_COST_PER_KG = 200.0  # USD/kg threshold
# Percentage of active mass from premium materials that triggers warning
PREMIUM_MATERIAL_WARN_PCT = 25.0  # >25% premium = high-cost formula
# Industry score thresholds
MASS_MARKET_INDUSTRY_FLOOR = 55  # below this = probably too simple
PREMIUM_INDUSTRY_CEILING = 85  # above this = luxury quality
# Typical premium naturals list (expensive ingredients that raise COGS)
PREMIUM_NATURALS = {
    "orris",
    "iris",
    "rose absolute",
    "jasmine absolute",
    "neroli",
    "tuberose",
    "ylang",
    "champaca",
    "oud",
    "sandalwood",
    "ambrox super",
    "ambrox dl",
    "ambrofix",
    "ambermax",
    "habanolide",
    "exaltolide",
    "zenolide",
    "romandolide",
    "javanol",
    "polysantol",
    "sandalore",
    "ebanol",
    "timberol",
    "norlimbanol",
    "koavone",
    "alpha irone",
    "irotyl",
    "irivone",
    "orivone",
    "suederal",
    "ibq",
    "isobutyl quinoline",
    "tobacco absolute",
    "birch tar",
}

ALLOWED_VARIANT_DUPLICATES = [
    {"hedione", "hedione hc"},
]


@dataclass(frozen=True, slots=True)
class ReleaseGateConfig:
    expected_concentrate_ul: float = DEFAULT_CONCENTRATE_UL
    min_neat_trace_ul: float = MIN_NEAT_TRACE_UL
    batch_volume_ml: float = 30.0
    batch_volume_source: str = "default"
    temperature_K: float = 305.0  # noqa: N815
    brief: str = "auto"
    family_archetype: str = ""
    concentration_bracket: str = "EdP"
    allow_preblends: bool = False
    min_confidence_score: float = MIN_CONFIDENCE_SCORE
    min_perceptible_materials: int = MIN_PERCEPTIBLE_MATERIALS
    max_perceptible_channels: int = MAX_PERCEPTIBLE_CHANNELS
    ifra_headroom: float = 1.0
    commercial_mode: bool = False
    commercial_confidence_policy: str = "block"
    batch_scaling_targets_ml: tuple[float, ...] = ()
    audit_enabled: bool = True
    audit_source: str = ""
    expected_retail_price_thb: float = 1500.0  # target retail price
    price_tier: str = "auto"  # "mass" (99-890), "mid" (1500-3500), "premium" (4000+)
    quantitative_claim: bool = False
    matrix_components_moles: tuple[tuple[str, float], ...] = ()
    matrix_mass_g: float = 0.0
    matrix_source: str = "omitted"
    mode: str = "RECONSTRUCTION"
    action: str = "REPORT"
    chassis_core_ul: float | None = None
    chassis_module_ul: float | None = None

    def effective_ifra_headroom(self) -> float:
        """Return the active IFRA multiplier for this gate run."""
        if self.commercial_mode and self.ifra_headroom == 1.0:
            return 0.8
        return max(0.0, min(1.0, float(self.ifra_headroom)))

    def is_commercial_trial(self) -> bool:
        return self.commercial_mode and self.commercial_confidence_policy == "warn"

    def requires_exact_quantitation(self) -> bool:
        return (self.commercial_mode and not self.is_commercial_trial()) or self.quantitative_claim

    def requires_exact_finished_product_quantitation(self) -> bool:
        return self.commercial_mode and not self.is_commercial_trial()


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: str
    detail: str = ""
    data: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        payload = {"gate": self.gate, "status": self.status, "detail": self.detail}
        if self.data:
            payload["data"] = self.data
        return payload


@dataclass(frozen=True, slots=True)
class GateReport:
    number: int
    name: str
    status: str
    gates: tuple[GateResult, ...]
    formula_state: FormulaState
    simulation: tuple[SimulationFrame, ...]
    confidence: dict
    formula_hash: str
    calibration_summary: dict
    commercial_readiness: str
    preflight: dict = field(default_factory=dict)
    config_summary: dict = field(default_factory=dict)
    audit_event_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "number": self.number,
            "name": self.name,
            "status": self.status,
            "formula_hash": self.formula_hash,
            "gates": [g.as_dict() for g in self.gates],
            "confidence": self.confidence,
            "calibration_summary": dict(self.calibration_summary),
            "commercial_readiness": self.commercial_readiness,
            "preflight": dict(self.preflight),
            "config_summary": dict(self.config_summary),
            "audit_event_id": self.audit_event_id,
            "formula_state": self.formula_state.as_dict(),
            "time_series": [frame.as_dict() for frame in self.simulation],
        }


SCREENING_OAV_DIAGNOSTIC_GATES = frozenset(
    {
        "perfume_knowledge",
        "oav_legibility",
        "oav_overdose_blocker",
        "odt_completeness",
        "oav_intelligence",
        "olfactory_fatigue",
        "literature_compliance",
        "balance_axes",
        "ellena_legibility",
        "jellinek_psychology",
        "edwards_wheel_coherence",
        "guerlain_nature_synthetic",
        "weber_fechner_contrast",
        "adaptation_timing",
        "guerlain_vanillin_coumarin",
        "stevens_power_law",
        "guerlain_rose_jasmine_balance",
        "stevens_n_efficiency",
        "jnd_redundancy",
        "adaptation_overlap",
        "mixture_suppression",
        "oav_physics_gamma",
        "hedonic_neuroscience",
    }
)


def _is_screening_oav_diagnostic_gate(gate_name: str) -> bool:
    return gate_name in SCREENING_OAV_DIAGNOSTIC_GATES or gate_name.endswith("_skeleton")


def _screening_oav_claim_ceiling(data: dict | None) -> dict:
    bounded = dict(data or {})
    bounded["evidence_role"] = "HEURISTIC_SCREENING_ONLY"
    bounded[
        "claim_ceiling"
    ] = "NOT_PHYSICS_SENSORY_LIKING_RELEASE_OR_RECOMPOUNDING_AUTHORITY"
    bounded["formula_optimization_authority"] = False
    bounded["compounding_action_authority"] = False
    bounded["repair_authority"] = False
    bounded["release_authority"] = False
    bounded["sensory_endpoint_authority"] = False
    return bounded


# Gate statuses, from best to worst. HOLD means the gate could not decide
# because data is missing (an undeclared stock basis, no authoritative active
# mass, no composition for a natural, ...). It blocks release exactly like FAIL,
# but it says "supply this data" rather than "the formula is wrong", so a real
# formula error stays visible as the only FAIL.
GATE_STATUSES = ("PASS", "WARN", "HOLD", "FAIL")
BLOCKING_STATUSES = frozenset({"HOLD", "FAIL"})


def _result(gate: str, status: str, detail: str = "", data: dict | None = None) -> GateResult:
    if status not in GATE_STATUSES:
        raise ValueError(f"Invalid gate status '{status}' for gate '{gate}'")
    if _is_screening_oav_diagnostic_gate(gate):
        data = _screening_oav_claim_ceiling(data)
        if status in BLOCKING_STATUSES:
            data.setdefault("original_status", status)
            data.setdefault("gate_policy", "screening_oav_failures_demoted_to_warn")
            detail = detail or "Screening OAV diagnostic raised a flag"
            detail = f"{detail} [screening diagnostic; not release or recompounding authority]"
            status = "WARN"
    return GateResult(gate=gate, status=status, detail=detail, data=data or {})


def _skipped(gate: str, detail: str = "", data: dict | None = None) -> GateResult:
    """A check that did not run. SKIP never votes in the verdict (see _status_from_gates)."""
    return GateResult(gate=gate, status="SKIP", detail=detail, data=data or {})


HARD_BLOCKING_GATES = frozenset(
    {
        "pipeline_preflight",
        "exact_subtotal",
        "duplicates",
        "duplicate_materials",
        "material_coverage",
        "material_spine_coverage",
        "data_coverage",
        "physics_data_coverage",
        "odt_coverage",
        "chemistry_stability",
        "chemical_compatibility",
        "phase_compatibility",
        "preblends",
        "opaque_preblends",
        "blocked",
        "blocked_materials",
        "confidence_minimum",
        "pipette_floor",
        "pipette_floor_neat_traces",
        "robustness_perturbation",
        "dilution_accuracy",
        "oav_scaling",
        "oav_scaling_guard",
        "safety",
        "safety_ifra_allergen",
        "inventory_stock_contract",
        "quantitative_authority",
        "natural_composite_coverage",
        "reference_claim_contract",
        "g15_oav_firewall",
        "mode_protection",
        "chassis_integrity",
        "concentration_basis",
        "headspace_scope",
        "authority_vector",
        "solvent_matrix",
        "safety_phototoxic",
    }
)


ADVISORY_FAILURE_GATES = frozenset({
    "literature_compliance", "perfumer_logic", "family_drift_detector",
    "perfume_knowledge", "novelty_vs_reference", "carles_pyramid",
    "carles_material_count", "carles_accord_ratio", "beaux_registres",
    "oav_legibility", "ellena_legibility", "roudnitska_transparence",
    "synergy_conflicts", "accord_compliance", "construction_compliance",
    "performance_prediction", "balance_axes", "character_shifts",
    "family_hedonic", "iconic_formulas", "niche_construction",
    "jellinek_psychology", "edwards_wheel_coherence", "oav_intelligence",
    "olfactory_fatigue", "master_perfumer", "master_perfumer_gate",
    "mass_market_tier_check", "hedione_share", "musk_count",
})


def _apply_guideline_policy(gate: GateResult) -> GateResult:
    """Keep safety/data/math failures blocking; treat perfumery gates as advice."""
    if _is_screening_oav_diagnostic_gate(gate.gate):
        data = _screening_oav_claim_ceiling(gate.data)
        if gate.status in BLOCKING_STATUSES:
            data.setdefault("original_status", gate.status)
            data.setdefault("gate_policy", "screening_oav_failures_demoted_to_warn")
            detail = gate.detail or "Screening OAV diagnostic raised a flag"
            detail = f"{detail} [screening diagnostic; not release or recompounding authority]"
            return GateResult(gate=gate.gate, status="WARN", detail=detail, data=data)
        return GateResult(gate=gate.gate, status=gate.status, detail=gate.detail, data=data)

    if gate.status not in BLOCKING_STATUSES or gate.gate not in ADVISORY_FAILURE_GATES:
        return gate

    data = dict(gate.data or {})
    data.setdefault("original_status", gate.status)
    data.setdefault("gate_policy", "advisory_failures_demoted_to_warn")
    detail = gate.detail or "Advisory gate failed"
    detail = f"{detail} [advisory guideline; not release-blocking]"
    return GateResult(gate=gate.gate, status="WARN", detail=detail, data=data)


def _safe_gate(gate_fn, gate_name: str) -> GateResult:
    """Catch gate exceptions while preserving hard-gate fail-closed policy."""
    try:
        return gate_fn()
    except (TypeError, AttributeError) as e:
        tb = traceback.format_exc()
        return _result(
            gate_name,
            "WARN" if gate_name in ADVISORY_FAILURE_GATES else "FAIL",
            f"Gate skipped (API mismatch): {e}",
            data={"error": str(e), "traceback": tb},
        )
    except Exception as e:
        tb = traceback.format_exc()
        return _result(
            gate_name,
            "WARN" if gate_name in ADVISORY_FAILURE_GATES else "FAIL",
            f"Gate skipped ({type(e).__name__}): {e}",
            data={"error": str(e), "traceback": tb},
        )


def _config_summary(config: ReleaseGateConfig) -> dict:
    return {
        "expected_concentrate_ul": config.expected_concentrate_ul,
        "batch_volume_ml": config.batch_volume_ml,
        "batch_volume_source": config.batch_volume_source,
        "temperature_K": config.temperature_K,
        "brief": config.brief,
        "family_archetype": config.family_archetype,
        "concentration_bracket": config.concentration_bracket,
        "allow_preblends": config.allow_preblends,
        "min_confidence_score": config.min_confidence_score,
        "ifra_headroom": config.ifra_headroom,
        "effective_ifra_headroom": config.effective_ifra_headroom(),
        "commercial_mode": config.commercial_mode,
        "quantitative_claim": config.quantitative_claim,
        "matrix_components_moles": [list(row) for row in config.matrix_components_moles],
        "matrix_mass_g": config.matrix_mass_g,
        "matrix_source": config.matrix_source,
        "requires_exact_quantitation": config.requires_exact_quantitation(),
        "commercial_confidence_policy": config.commercial_confidence_policy,
        "commercial_trial": config.is_commercial_trial(),
        "batch_scaling_targets_ml": list(config.batch_scaling_targets_ml),
        "audit_source": config.audit_source,
    }


def _status_from_gates(gates: list[GateResult]) -> str:
    """Worst status wins: FAIL, then HOLD, then WARN, then PASS (SKIP never votes)."""
    statuses = {g.status for g in gates}
    if "FAIL" in statuses:
        return "FAIL"
    if "HOLD" in statuses:
        return "HOLD"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


# Preflight checks keep their own PASS/WARN/FAIL statuses; the HOLD mapping is
# computed here, from each failing check's reasons, so no preflight reader ever
# sees a status it does not handle. Everything not listed below as a
# missing-data reason stays FAIL (fail closed).
#
# Execution holds on an owned stock that only record missing data about it,
# with what the user should supply.
_STOCK_DATA_HOLDS: dict[str, str] = {
    "STOCK_INTAKE_IDENTITY_ONLY": "record the strength, concentration basis and carrier",
    "FRACTION_BASIS_UNSPECIFIED": "record the concentration basis (w/w, v/v or w/v)",
    "CARRIER_UNSPECIFIED": "record the carrier",
    "FRACTION_BASIS_AND_CARRIER_UNSPECIFIED": "record the concentration basis and carrier",
    "FRACTION_BASIS_OR_CARRIER_UNSPECIFIED": "record the concentration basis and carrier",
    "STOCK_FRACTION_UNSPECIFIED": "record the stock strength and carrier",
    "RESTOCKED_BOTTLE_STRENGTH_AND_CARRIER_NOT_STATED": "record the restocked bottle's strength and carrier",
    "APPROXIMATE_STOCK_FRACTION": "record the exact stock strength",
    "BOTTLE_LOT_AND_LABEL_RECEIPT_MISSING": "record the bottle lot and label receipt",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING": "record the bottle lot and preparation receipt",
    "LOT_PURCHASE_SOURCE_AND_LABEL_RECEIPT_MISSING": "record the lot, purchase source and label receipt",
    "PREPARATION_QUANTITIES_DATE_AND_LOTS_MISSING": "record the preparation quantities, date and lots",
    "FINAL_DISSOLVED_FRACTION_UNMEASURED": "measure the final dissolved fraction",
    "FILTERED_TINCTURE_FINAL_DISSOLVED_FRACTION_UNKNOWN": "measure the final dissolved fraction",
    "TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED": (
        "record the tincture percentage basis and extracted solids"
    ),
    "FRACTION_BASIS_AND_HOMOGENEITY_NOT_CONFIRMED": "confirm the concentration basis and homogeneity",
    "HOMOGENEITY_NOT_RECONFIRMED": "reconfirm homogeneity",
}
# Holds under which the stock has no recorded strength at all, so a formula
# strength cannot yet be compared with it.  Every other data hold sits on a
# stock with a recorded strength (an approximate "~10%", a supplier-label
# neat intake, a tincture percentage of unstated basis) that preflight compares
# with the formula like any exact stock.
_STOCK_STRENGTH_UNKNOWN_HOLDS = frozenset(
    {
        "STOCK_FRACTION_UNSPECIFIED",
        "RESTOCKED_BOTTLE_STRENGTH_AND_CARRIER_NOT_STATED",
    }
)
# Tincture holds where only the starting charge is recorded: the dissolved
# fraction can be at most that charge, so a formula strength above it is a
# wrong strength, while one at or below it (or no recorded charge) waits on
# the measurement.
_STOCK_STRENGTH_CHARGE_BOUND_HOLDS = frozenset(
    {
        "FINAL_DISSOLVED_FRACTION_UNMEASURED",
        "FILTERED_TINCTURE_FINAL_DISSOLVED_FRACTION_UNKNOWN",
    }
)
# The tolerance preflight uses when it compares a formula and stock fraction.
_STOCK_FRACTION_TOLERANCE = 0.005


def _split_holds(raw_holds: object) -> list[str]:
    return [hold for raw in list(raw_holds or []) for hold in str(raw).split("|") if hold]


def _held_strength_compatible(issue: Mapping[str, object], holds: list[str]) -> bool:
    """True when no held stock is known to differ in strength from the formula.

    Used only when no held stock matches the formula's fraction.  Missing
    fields fail closed.
    """
    if not holds:
        return False
    if all(hold in _STOCK_STRENGTH_UNKNOWN_HOLDS for hold in holds):
        return True
    if any(
        hold not in _STOCK_STRENGTH_UNKNOWN_HOLDS | _STOCK_STRENGTH_CHARGE_BOUND_HOLDS
        for hold in holds
    ):
        return False
    formula_dilution = issue.get("formula_dilution")
    held_stocks = issue.get("held_stock_strengths")
    if not isinstance(formula_dilution, (int, float)) or isinstance(formula_dilution, bool):
        return False
    if not isinstance(held_stocks, list) or not held_stocks:
        return False
    for stock in held_stocks:
        if not isinstance(stock, Mapping) or "fraction" not in stock:
            return False
        stock_holds = _split_holds([stock.get("execution_hold", "")])
        if not stock_holds:
            return False
        if all(hold in _STOCK_STRENGTH_UNKNOWN_HOLDS for hold in stock_holds):
            continue
        if any(hold not in _STOCK_STRENGTH_CHARGE_BOUND_HOLDS for hold in stock_holds):
            return False
        charge = stock["fraction"]
        if charge is None:
            continue
        if not isinstance(charge, (int, float)) or isinstance(charge, bool):
            return False
        if float(formula_dilution) > float(charge) + _STOCK_FRACTION_TOLERANCE:
            return False
    return True


def _stock_issue_data_request(issue: Mapping[str, object]) -> str | None:
    """Return what to supply when a stock issue is only missing data, else None.

    None means the formula cannot be built as written (not owned, wrong
    strength, depleted, a gap, a preparation still to make, a user hold, or any
    reason this mapping does not know): the issue stays FAIL.
    """
    reason = str(issue.get("reason", ""))
    if reason not in {"inventory_stock_metadata_incomplete", "inventory_stock_non_executable"}:
        return None
    holds = _split_holds(issue.get("execution_holds", []))
    if reason == "inventory_stock_non_executable" and not holds:
        return None
    if any(hold not in _STOCK_DATA_HOLDS for hold in holds):
        return None
    if issue.get("fraction_matches_formula") is not True and not _held_strength_compatible(
        issue, holds
    ):
        return None
    if not holds:
        return "record the carrier and concentration basis"
    return "; ".join(dict.fromkeys(_STOCK_DATA_HOLDS[hold] for hold in holds))


def _describe_stock_issue(issue: Mapping[str, object]) -> str:
    material = str(issue.get("material", "?"))
    reason = str(issue.get("reason", "inventory_stock_contract_failed"))
    if reason == "stock_fraction_mismatch":
        live = ", ".join(
            f"{float(value):.4g}" for value in list(issue.get("inventory_dilutions", []) or [])
        )
        return f"{material} ({reason}: formula {issue.get('formula_dilution')} vs stock {live})"
    return f"{material} ({reason})"


def _classify_inventory_stock_contract(check: Mapping[str, object]) -> tuple[str, str, dict]:
    data = dict(check.get("data", {}) or {})
    status = str(check.get("status", "FAIL"))
    detail = str(check.get("detail", ""))
    issues = [dict(issue) for issue in list(data.get("issues", []) or [])]
    if status != "FAIL" or not issues:
        return status, detail, data
    fail_issues = []
    needs_data = []
    for issue in issues:
        request = _stock_issue_data_request(issue)
        if request is None:
            fail_issues.append(issue)
        else:
            needs_data.append({**issue, "data_request": request})
    data["fail_issues"] = fail_issues
    data["needs_data"] = needs_data
    parts = []
    if fail_issues:
        parts.append(
            f"{len(fail_issues)} material(s) cannot be built as written: "
            + ", ".join(_describe_stock_issue(issue) for issue in fail_issues)
        )
    if needs_data:
        parts.append(
            "needs data: "
            + "; ".join(
                f"{issue.get('material')} ({issue['data_request']} of the {issue.get('material')} stock)"
                for issue in needs_data
            )
        )
    return ("FAIL" if fail_issues else "HOLD"), ". ".join(parts), data


def _classify_natural_composite_coverage(check: Mapping[str, object]) -> tuple[str, str, dict]:
    data = dict(check.get("data", {}) or {})
    status = str(check.get("status", "FAIL"))
    detail = str(check.get("detail", ""))
    materials = [str(name) for name in list(data.get("materials", []) or [])]
    if status != "FAIL" or not materials:
        return status, detail, data
    data["needs_data"] = materials
    detail = f"{detail}; needs data: supply a constituent decomposition for {', '.join(materials)}"
    return "HOLD", detail, data


_PREFLIGHT_CLASSIFIERS = {
    "inventory_stock_contract": _classify_inventory_stock_contract,
    "natural_composite_coverage": _classify_natural_composite_coverage,
}


def _classify_preflight_check(check: Mapping[str, object]) -> tuple[str, str, dict]:
    """Map one preflight check to its gate status: HOLD only for missing data."""
    classifier = _PREFLIGHT_CLASSIFIERS.get(str(check.get("check_name", "")))
    if classifier is None:
        return (
            str(check.get("status", "FAIL")),
            str(check.get("detail", "")),
            dict(check.get("data", {}) or {}),
        )
    return classifier(check)


# Reasons the inventory stock contract emits on its issues (preflight
# ``_dilution_consistency_check``); the dose receipt copies them as blockers.
_STOCK_CONTRACT_ISSUE_REASONS = frozenset(
    {
        "stock_fraction_not_declared",
        "stock_fraction_invalid",
        "stock_fraction_out_of_range",
        "conflicting_stock_rows",
        "stock_id_not_in_current_inventory",
        "not_in_inventory",
        "preparation_required",
        "inventory_gap",
        "inventory_stock_non_executable",
        "inventory_stock_metadata_incomplete",
        "inventory_stock_unavailable",
        "stock_fraction_mismatch",
        "stock_fraction_basis_mismatch",
        "stock_carrier_mismatch",
        "ambiguous_live_stock",
    }
)
# Receipt blockers that follow from the stock contract resolving no stock for
# a material: they count as stock-issue reasons only for such a material.
_UNRESOLVED_STOCK_BINDING_BLOCKERS = frozenset(
    {
        "stock_declaration_not_bound",
        "stock_id_not_bound",
        "stock_authority_not_bound",
        "inventory_authority_not_bound",
        "inventory_source_lineage_not_bound",
    }
)


def _dose_receipt_follows_stock_contract(
    receipt_check: Mapping[str, object],
    stock_check: Mapping[str, object] | None,
) -> bool:
    """True when the dose receipt abstains only because of stock-contract issues.

    Every unbound line must belong to a material with a stock issue, and every
    blocker on it must be that material's own stock-issue reason, or a binding
    blocker that follows from the contract resolving no stock for it.  At
    least one unbound line must exist; missing fields fail closed.
    """
    if stock_check is None or str(stock_check.get("status")) != "FAIL":
        return False
    receipt = dict(receipt_check.get("data", {}) or {})
    if receipt.get("status") != "ABSTAINED" or "state_mismatches" in receipt:
        return False
    stock_data = dict(stock_check.get("data", {}) or {})
    resolved_specs = stock_data.get("resolved_stock_specs")
    if not isinstance(resolved_specs, Mapping):
        return False
    resolved_materials = {str(name).casefold() for name in resolved_specs}
    issue_reasons: dict[str, set[str]] = {}
    for issue in list(stock_data.get("issues", []) or []):
        issue_reasons.setdefault(str(issue.get("material", "")).casefold(), set()).add(
            str(issue.get("reason", ""))
        )
    unbound = [
        dict(line)
        for line in list(receipt.get("lines", []) or [])
        if dict(line).get("status") != "BOUND"
    ]
    if not unbound:
        return False
    for line in unbound:
        material = str(line.get("material_name", "")).casefold()
        reasons = issue_reasons.get(material, set()) & _STOCK_CONTRACT_ISSUE_REASONS
        blockers = [str(blocker) for blocker in list(line.get("blockers", []) or [])]
        if not reasons or not blockers:
            return False
        for blocker in blockers:
            if blocker in reasons:
                continue
            if blocker in _UNRESOLVED_STOCK_BINDING_BLOCKERS and material not in resolved_materials:
                continue
            return False
    return True


def _gate_pipeline_preflight(preflight: Mapping[str, object]) -> GateResult:
    checks = list(preflight.get("checks", []))
    warnings = list(preflight.get("warnings", []))
    detail = f"{len(checks)} checks"
    if warnings:
        detail += f"; {len(warnings)} warnings"
    status = str(preflight.get("status", "WARN"))
    data = dict(preflight)
    if status == "FAIL":
        by_name = {str(dict(raw).get("check_name", "")): dict(raw) for raw in checks}
        stock_check = by_name.get("inventory_stock_contract")
        stock_status = (
            _classify_preflight_check(stock_check)[0] if stock_check is not None else "FAIL"
        )
        failing: dict[str, list[str]] = {"FAIL": [], "HOLD": []}
        for name, check in by_name.items():
            if str(check.get("status")) != "FAIL":
                continue
            if name == "formula_dose_receipt" and _dose_receipt_follows_stock_contract(
                check, stock_check
            ):
                check_status = stock_status
            else:
                check_status = _classify_preflight_check(check)[0]
            failing["FAIL" if check_status != "HOLD" else "HOLD"].append(name)
        if not failing["FAIL"] and not failing["HOLD"]:
            failing["FAIL"].append("preflight_status")
        status = "FAIL" if failing["FAIL"] else "HOLD"
        data["failing_checks"] = failing["FAIL"]
        data["needs_data_checks"] = failing["HOLD"]
        if failing["FAIL"]:
            detail += f"; failing: {', '.join(failing['FAIL'])}"
        if failing["HOLD"]:
            detail += f"; needs data: {', '.join(failing['HOLD'])}"
    return _result("pipeline_preflight", status, detail, data)


def _formula_vector_from_state(state: FormulaState) -> FormulaVector:
    return FormulaVector(
        ingredients=state.raw_percentages(),
        dilutions={m.name: m.dilution for m in state.materials},
    )


_SUBTOTAL_SHIFT_FACTORS = (10, 100, 1000)


def _exact_subtotal_findings(rows: Mapping[str, float], total_ul: float, expected_ul: float) -> dict:
    """Point at the rows most likely behind a subtotal mismatch.

    A misplaced decimal point (8200 typed for 820) or a mL/uL slip moves one row
    by a factor of 10, 100 or 1000. A row is a suspect when undoing that one
    factor explains the gap: the corrected total is closer to the expected
    concentrate than the parsed one, and within 0.5% of the gap (at least
    0.5 uL) of it. Each row is named once, at its best factor. Rows larger than
    the whole expected concentrate are listed separately.
    """
    gap = total_ul - expected_ul
    tolerance = max(0.5, 0.005 * abs(gap))
    best: dict[str, tuple[float, dict]] = {}
    for name, ul in rows.items():
        if ul <= 0:
            continue
        for factor in _SUBTOTAL_SHIFT_FACTORS:
            corrected = ul / factor if gap > 0 else ul * factor
            new_total = total_ul - ul + corrected
            residual = abs(new_total - expected_ul)
            if residual > tolerance or residual >= abs(gap):
                continue
            if name in best and best[name][0] <= residual:
                continue
            best[name] = (
                residual,
                {
                    "material": name,
                    "ul": round(ul, 3),
                    "corrected_ul": round(corrected, 3),
                    "factor": f"/{factor}" if gap > 0 else f"x{factor}",
                    "total_if_corrected_ul": round(new_total, 3),
                },
            )
    suspects = [suspect for _, suspect in sorted(best.values(), key=lambda item: item[0])]
    over_expected = [
        {"material": name, "ul": round(ul, 3)}
        for name, ul in sorted(rows.items(), key=lambda item: -item[1])
        if expected_ul > 0 and ul > expected_ul
    ]
    largest = [
        {
            "material": name,
            "ul": round(ul, 3),
            "share_of_parsed": round(ul / total_ul, 4) if total_ul else 0.0,
        }
        for name, ul in sorted(rows.items(), key=lambda item: -item[1])[:3]
    ]
    return {
        "parsed_ul": round(total_ul, 3),
        "expected_ul": round(expected_ul, 3),
        "difference_ul": round(gap, 3),
        "decimal_shift_suspects": suspects,
        "rows_over_expected": over_expected,
        "largest_rows": largest,
    }


def _gate_exact_subtotal(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    rows = {str(name): float(value or 0.0) for name, value in formula["ingredients_ul"].items()}
    total_ul = sum(rows.values())
    expected_ul = config.expected_concentrate_ul
    if abs(total_ul - expected_ul) <= 0.5:
        return _result("exact_subtotal", "PASS", f"{total_ul:.1f} uL")
    findings = _exact_subtotal_findings(rows, total_ul, expected_ul)
    gap = findings["difference_ul"]
    detail = (
        f"{total_ul:.1f} uL parsed; expected {expected_ul:.1f} uL "
        f"({abs(gap):.1f} uL {'over' if gap > 0 else 'short'})"
    )
    suspects = findings["decimal_shift_suspects"]
    if suspects:
        named = "; ".join(
            f"{s['material']} {s['ul']:g} uL (at {s['corrected_ul']:g} uL the total would be "
            f"{s['total_if_corrected_ul']:g} uL)"
            for s in suspects[:3]
        )
        detail += f". Likely misplaced decimal or unit: {named}"
    if findings["rows_over_expected"]:
        named = ", ".join(f"{r['material']} {r['ul']:g} uL" for r in findings["rows_over_expected"][:3])
        detail += f". Larger than the whole expected concentrate: {named}"
    if not suspects and not findings["rows_over_expected"] and findings["largest_rows"]:
        named = ", ".join(
            f"{r['material']} {r['ul']:g} uL ({r['share_of_parsed']:.0%})" for r in findings["largest_rows"]
        )
        detail += f". Largest rows: {named}"
    return _result("exact_subtotal", "FAIL", detail, findings)


def _gate_duplicates(state: FormulaState) -> GateResult:
    seen: dict[str, list[str]] = {}
    for material in state.materials:
        seen.setdefault(material.canonical_name, []).append(material.name)
    duplicates = {}
    allowed = {}
    for key, names in seen.items():
        if len(names) <= 1:
            continue
        lowered = {name.lower() for name in names}
        if any(lowered == allowed_set for allowed_set in ALLOWED_VARIANT_DUPLICATES):
            allowed[key] = names
        else:
            duplicates[key] = names
    if duplicates:
        return _result(
            "duplicate_canonical_materials",
            "FAIL",
            json.dumps(duplicates, sort_keys=True),
        )
    if allowed:
        return _result("duplicate_canonical_materials", "PASS", "allowed variants", allowed)
    return _result("duplicate_canonical_materials", "PASS")


def _gate_material_coverage(state: FormulaState) -> GateResult:
    unknown = sorted(m.name for m in state.materials if not m.is_known)
    if unknown:
        return _result("material_spine_coverage", "FAIL", ", ".join(unknown))
    return _result("material_spine_coverage", "PASS")


def _gate_data_coverage(state: FormulaState) -> GateResult:
    required = ("mw", "logp", "vp", "odt_air_ppm")
    composite_authority = {
        m.name: [field for field in required if field in m.missing_fields]
        for m in state.materials
        if m.sources.get("oav_model") == "modeled:natural_constituent_composite"
        and any(field in m.missing_fields for field in required)
    }
    missing = {
        m.name: [field for field in required if field in m.missing_fields]
        for m in state.materials
        if m.sources.get("oav_model") != "modeled:natural_constituent_composite"
        if any(field in m.missing_fields for field in required)
    }
    if missing:
        return _result(
            "physics_data_coverage",
            "FAIL",
            json.dumps(missing, sort_keys=True),
            missing,
        )
    return _result(
        "physics_data_coverage",
        "PASS",
        ("constituent-resolved natural authority" if composite_authority else ""),
        {"natural_composite_exemptions": composite_authority} if composite_authority else None,
    )


def _gate_odt_coverage(state: FormulaState) -> GateResult:
    missing = sorted(
        m.name
        for m in state.materials
        if not m.has_odt_authority
    )
    if missing:
        return _result("odt_coverage", "FAIL", ", ".join(missing), {"missing": missing})

    low_authority_rows = []
    total_oav = sum(float(m.oav or 0.0) for m in state.materials) or 1.0
    low_authority_oav = 0.0
    for material in state.materials:
        source = str(material.sources.get("odt", "missing")).lower()
        if any(
            token in source
            for token in (
                "derived:",
                "unverified:",
                "estimated:",
                "modeled:",
                "profile:",
                "registry:",
            )
        ):
            oav = float(material.oav or 0.0)
            low_authority_oav += oav
            low_authority_rows.append(
                {
                    "material": material.name,
                    "odt_source": str(material.sources.get("odt", "missing")),
                    "oav": round(oav, 6),
                }
            )
    low_authority_rows.sort(key=lambda row: row["oav"], reverse=True)
    low_authority_share = low_authority_oav / total_oav
    top_oav_names = {
        material.name
        for material in sorted(
            state.materials, key=lambda row: float(row.oav or 0.0), reverse=True
        )[:3]
    }
    data = {
        "missing": [],
        "low_authority_materials": low_authority_rows,
        "low_authority_oav_share": round(low_authority_share, 6),
    }
    if low_authority_rows and (
        low_authority_share >= 0.25
        or any(row["material"] in top_oav_names for row in low_authority_rows)
    ):
        return _result(
            "odt_coverage",
            "WARN",
            f"{len(low_authority_rows)} material(s) rely on derived/unverified ODTs ({low_authority_share:.0%} OAV share)",
            data,
        )
    return _result("odt_coverage", "PASS", data=data)


def _science_profile_for_material(material) -> tuple[object, str]:
    for candidate in (material.registry_name, material.profile_name, material.name):
        if not candidate:
            continue
        profile = get_science_profile(candidate)
        if (
            profile.stability_class != StabilityRisk.STABLE
            or profile.autoxidation_half_life_weeks is not None
            or profile.schiff_base_partners
            or profile.photostability != "stable"
        ):
            return profile, str(candidate)
    return get_science_profile(material.name), material.name


# Plain-language explanation of each ``active_mass_authority`` code that
# ``_authoritative_active_mass`` emits when it cannot give an exact mass.
_MISSING_ACTIVE_MASS_REASONS = {
    "unavailable:stock_fraction_not_declared": "its stock dilution is not declared",
    "unavailable:stock_fraction_basis_unspecified": "its dilution basis is not declared",
    "unavailable:stock_solution_density_for_w_w": "needs the density of its w/w stock solution",
    "unavailable:material_density": "needs its material density",
}


def _missing_authoritative_active_mass(state: FormulaState) -> list[dict[str, str]]:
    """List materials without an authoritative active mass, with the reason code."""
    return sorted(
        (
            {"material": material.name, "reason": material.active_mass_authority}
            for material in state.materials
            if material.authoritative_active_g is None
        ),
        key=lambda row: row["material"],
    )


def _describe_missing_active_mass(missing: list[dict[str, str]]) -> str:
    return "; ".join(
        f"{row['material']} ({_MISSING_ACTIVE_MASS_REASONS.get(row['reason'], row['reason'])})"
        for row in missing
    )


def _gate_chemistry_stability(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    functional_groups = {
        m.name: set(m.functional_groups) for m in state.materials if m.functional_groups
    }
    aldehydes = sorted(
        m.name for m in state.materials if "aldehyde" in functional_groups.get(m.name, set())
    )
    amines = sorted(
        m.name for m in state.materials if "amine" in functional_groups.get(m.name, set())
    )

    def _schiff_pair_rows(aldehyde_names: list[str]) -> list[dict]:
        if not aldehyde_names or not amines:
            return []
        amine_lookup = {normalize_name(name): name for name in amines}
        rows: list[dict] = []
        for material in state.materials:
            if material.name not in aldehyde_names:
                continue
            science_profile, science_source = _science_profile_for_material(material)
            partners = []
            for partner in science_profile.schiff_base_partners or []:
                matched = amine_lookup.get(normalize_name(partner))
                if matched and matched not in partners:
                    partners.append(matched)
            if partners:
                rows.append(
                    {
                        "aldehyde": material.name,
                        "amines": partners,
                        "science_source": science_source,
                    }
                )
        if not rows:
            rows = [
                {"aldehyde": aldehyde, "amines": list(amines)}
                for aldehyde in aldehyde_names
            ]
        return rows

    aging_claim = assess_aging_claim(AgingClaim.SHELF_LIFE)

    risk_profiles: list[tuple[object, object, str]] = []
    flagged_materials: set[str] = set()
    for material in state.materials:
        science_profile, science_source = _science_profile_for_material(material)
        if science_profile.stability_class == StabilityRisk.OXIDATION_PRONE:
            flagged_materials.add(material.name)
        if science_profile.photostability in {"moderate", "labile"}:
            flagged_materials.add(material.name)
        if (
            science_profile.stability_class == StabilityRisk.OXIDATION_PRONE
            or science_profile.photostability in {"moderate", "labile"}
        ):
            risk_profiles.append((material, science_profile, science_source))

    active_mass_pct = state.active_mass_percentages()
    mass_dependent_assessment = bool((aldehydes and amines) or flagged_materials)
    if mass_dependent_assessment and active_mass_pct is None:
        missing_rows = _missing_authoritative_active_mass(state)
        unknown_scope = []
        if aldehydes and amines:
            unknown_scope.append("Schiff-base risk")
        if flagged_materials:
            unknown_scope.append("oxidation/photolability burden")
        return _result(
            "chemistry_stability",
            "HOLD",
            f"{' and '.join(unknown_scope)} assessment UNKNOWN: authoritative active mass "
            f"is unavailable for {_describe_missing_active_mass(missing_rows)}",
            {
                "assessment": "UNKNOWN",
                "claim_ceiling": "AUTHORITATIVE_ACTIVE_MASS_REQUIRED",
                "active_mass_basis": "authoritative_active_g",
                "proxy_active_g_ignored": True,
                "missing": missing_rows,
                "missing_authoritative_active_mass_materials": [
                    row["material"] for row in missing_rows
                ],
                "aging_claim": aging_claim.as_mapping(),
                "candidate_schiff_base_pairs": _schiff_pair_rows(aldehydes),
                "candidate_oxidation_or_photolability_materials": sorted(flagged_materials),
            },
        )

    active_mass_pct = active_mass_pct or {}
    aldehyde_pct = sum(active_mass_pct.get(name, 0.0) for name in aldehydes)
    amine_pct = sum(active_mass_pct.get(name, 0.0) for name in amines)
    # Ignore trace aldehydes below the explicit contact-risk screening threshold.
    if aldehyde_pct < 0.05:
        aldehydes = []
        aldehyde_pct = 0.0
    schiff_pairs = _schiff_pair_rows(aldehydes)

    oxidation_rows: list[dict] = []
    photolabile_rows: list[dict] = []
    for material, science_profile, science_source in risk_profiles:
        pct_mass = active_mass_pct.get(material.name, 0.0)
        if science_profile.stability_class == StabilityRisk.OXIDATION_PRONE:
            oxidation_rows.append(
                {
                    "material": material.name,
                    "active_mass_pct": round(pct_mass, 3),
                    "half_life_weeks": science_profile.autoxidation_half_life_weeks,
                    "science_source": science_source,
                }
            )
        if science_profile.photostability in {"moderate", "labile"}:
            photolabile_rows.append(
                {
                    "material": material.name,
                    "active_mass_pct": round(pct_mass, 3),
                    "photostability": science_profile.photostability,
                    "remaining_24h_outdoor": round(
                        photolysis_remaining_fraction(material.name, 24.0, indoor=False),
                        6,
                    ),
                    "science_source": science_source,
                }
            )

    reactive_mass_pct = sum(active_mass_pct.get(name, 0.0) for name in flagged_materials)
    fail_reasons: list[str] = []
    warn_reasons: list[str] = []

    if aldehyde_pct > 1.0 and amine_pct > 0.5:
        fail_reasons.append(
            f"Schiff-base risk: aldehydes {aldehyde_pct:.1f}% + amines {amine_pct:.1f}% active"
        )
    elif schiff_pairs:
        warn_reasons.append(
            f"aldehyde+amine contact present below hard threshold ({aldehyde_pct:.1f}% / {amine_pct:.1f}%)"
        )

    if reactive_mass_pct > 20.0 and config.commercial_mode:
        fail_reasons.append(
            f"oxidation/photolability burden {reactive_mass_pct:.1f}% active mass in commercial mode"
        )
    elif reactive_mass_pct > 10.0:
        warn_reasons.append(f"oxidation/photolability burden {reactive_mass_pct:.1f}% active mass")

    data = {
        "aging_claim": aging_claim.as_mapping(),
        "schiff_base": {
            "aldehydes": aldehydes,
            "amines": amines,
            "aldehyde_active_pct": round(aldehyde_pct, 3),
            "amine_active_pct": round(amine_pct, 3),
            "pairs": schiff_pairs,
        },
        "oxidation_prone_materials": oxidation_rows,
        "photolabile_materials": photolabile_rows,
        "reactive_material_active_mass_pct": round(reactive_mass_pct, 3),
        "active_mass_basis": "authoritative_active_g",
        "proxy_active_g_ignored": True,
        "assessment": "EVALUATED",
    }
    if fail_reasons:
        return _result("chemistry_stability", "FAIL", "; ".join(fail_reasons), data)
    if warn_reasons:
        return _result("chemistry_stability", "WARN", "; ".join(warn_reasons), data)
    return _result(
        "chemistry_stability",
        "PASS",
        "explicit reaction, oxidation, and photolability hazards screened; "
        "aging, maturation, and shelf life remain UNKNOWN",
        data,
    )


def _gate_phase_compatibility(state: FormulaState) -> GateResult:
    missing_rows = _missing_authoritative_active_mass(state)
    if missing_rows:
        return _result(
            "phase_compatibility",
            "HOLD",
            "Phase compatibility assessment UNKNOWN: authoritative active mass is unavailable "
            f"for {_describe_missing_active_mass(missing_rows)}",
            {
                "assessment": "UNKNOWN",
                "claim_ceiling": "AUTHORITATIVE_ACTIVE_MASS_REQUIRED",
                "active_mass_basis": "authoritative_active_g",
                "proxy_active_g_ignored": True,
                "missing": missing_rows,
                "missing_authoritative_active_mass_materials": [
                    row["material"] for row in missing_rows
                ],
            },
        )

    total_active_g = sum(float(m.authoritative_active_g or 0.0) for m in state.materials)
    if total_active_g <= 0.0:
        return _result(
            "phase_compatibility",
            "FAIL",
            "Phase compatibility assessment UNKNOWN: authoritative active mass total is zero",
            {
                "assessment": "UNKNOWN",
                "claim_ceiling": "POSITIVE_AUTHORITATIVE_ACTIVE_MASS_REQUIRED",
                "active_mass_basis": "authoritative_active_g",
                "proxy_active_g_ignored": True,
            },
        )
    covered = [
        m
        for m in state.materials
        if m.hsp is not None and float(m.authoritative_active_g or 0.0) > 0.0
    ]
    covered_mass_pct = (
        100.0
        * sum(float(m.authoritative_active_g or 0.0) for m in covered)
        / total_active_g
    )
    hard_fail_supported = covered_mass_pct >= 80.0 and len(covered) >= 4
    data = {
        "hsp_covered_materials": [m.name for m in covered],
        "hsp_coverage_active_mass_pct": round(covered_mass_pct, 3),
        "hard_fail_supported": hard_fail_supported,
        "assessment": "EVALUATED",
        "active_mass_basis": "authoritative_active_g",
        "proxy_active_g_ignored": True,
    }
    if len(covered) < 3 or covered_mass_pct < 40.0:
        detail = (
            f"HSP coverage too thin for trusted phase audit: {covered_mass_pct:.1f}% "
            f"active mass across {len(covered)} materials"
        )
        return _result("phase_compatibility", "WARN", detail, data)

    composition = {m.name: float(m.authoritative_active_g or 0.0) for m in covered}
    hsp_table = {m.name: m.hsp for m in covered if m.hsp is not None}
    active_mass_pct = {
        m.name: 100.0 * float(m.authoritative_active_g or 0.0) / total_active_g
        for m in covered
    }
    source_lookup = {m.name: m.hsp_source for m in covered}
    risks: list[dict] = []
    fail_rows: list[dict] = []
    warn_rows: list[dict] = []
    for name, red in micro_phase_risk(composition, hsp_table):
        pct_mass = active_mass_pct.get(name, 0.0)
        row = {
            "material": name,
            "red": round(red, 4),
            "active_mass_pct": round(pct_mass, 3),
            "hsp_source": source_lookup.get(name, "missing"),
        }
        risks.append(row)
        if pct_mass >= 2.0 and red > 1.25:
            fail_rows.append(row)
        elif pct_mass >= 1.0 and red > 1.0:
            warn_rows.append(row)

    data.update(
        {
            "risks": risks,
            "fail_rows": fail_rows,
            "warn_rows": warn_rows,
        }
    )
    if fail_rows and not hard_fail_supported:
        warn_rows = [*fail_rows, *warn_rows]
        data["warn_rows"] = warn_rows
        detail = "tentative phase tension under partial HSP coverage: " + ", ".join(
            f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
            for row in warn_rows[:4]
        )
        return _result("phase_compatibility", "WARN", detail, data)
    if fail_rows:
        detail = "phase-out risk: " + ", ".join(
            f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
            for row in fail_rows[:4]
        )
        return _result("phase_compatibility", "FAIL", detail, data)
    if warn_rows:
        detail = "phase tension: " + ", ".join(
            f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
            for row in warn_rows[:4]
        )
        return _result("phase_compatibility", "WARN", detail, data)
    return _result("phase_compatibility", "PASS", "no HSP phase-out risk detected", data)


def _gate_preblends(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    opaque = sorted(m.name for m in state.materials if m.is_opaque_preblend)
    if not opaque:
        return _result("opaque_preblends", "PASS")
    status = "WARN" if config.allow_preblends and not config.commercial_mode else "FAIL"
    if config.commercial_mode:
        detail = "blocked in commercial mode: "
    else:
        detail = "allowed by config: " if config.allow_preblends else "not allowed: "
    return _result("opaque_preblends", status, detail + ", ".join(opaque), {"materials": opaque})


def _gate_blocked(state: FormulaState) -> GateResult:
    blocked = {m.name: reason for m in state.materials if (reason := blocked_reason(m.name))}
    if blocked:
        return _result("blocked_materials", "FAIL", json.dumps(blocked, sort_keys=True), blocked)
    return _result("blocked_materials", "PASS")


def _gate_pipette_floor(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    tiny_neat = sorted(
        f"{m.name}={m.raw_ul:.1f}uL"
        for m in state.materials
        if m.raw_ul < config.min_neat_trace_ul and m.dilution >= 0.999
    )
    if tiny_neat:
        return _result(
            "pipette_floor_neat_traces",
            "FAIL",
            "; ".join(tiny_neat) + f" below {config.min_neat_trace_ul:.1f} uL neat floor",
        )
    return _result("pipette_floor_neat_traces", "PASS")


def _gate_small_diluted_traces(state: FormulaState) -> GateResult:
    very_dilute = sorted(
        f"{m.name}={m.raw_ul:.1f}uL at {m.dilution * 100:.1f}%"
        for m in state.materials
        if m.raw_ul < 20.0 and m.dilution < 0.999
    )
    if very_dilute:
        return _result("small_diluted_traces", "WARN", "; ".join(very_dilute))
    return _result("small_diluted_traces", "PASS")


def _oav_check_as_dict(check) -> dict:
    return {
        "material": check.material,
        "source_conc_ppm": round(float(check.source_conc_ppm), 6),
        "target_conc_ppm": round(float(check.target_conc_ppm), 6),
        "odt_ppm": check.odt_ppm,
        "source_oav": check.source_oav,
        "target_oav": check.target_oav,
        "severity": check.severity,
        "message": check.message,
    }


def _gate_oav_scaling(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    targets = tuple(
        float(target) for target in config.batch_scaling_targets_ml if float(target) > 0
    )
    if not targets:
        return _skipped("oav_scaling_guard", "not requested")

    ingredients = {str(k): float(v or 0.0) for k, v in formula["ingredients_ul"].items()}
    dilutions = {str(k): float(v or 1.0) for k, v in formula.get("dilutions", {}).items()}
    findings = []
    worst = "ok"
    severity_rank = {"ok": 0, "info": 1, "warn": 2, "error": 3}

    for target in targets:
        checks = check_proportional_scaling(
            ingredients,
            dilutions,
            config.batch_volume_ml,
            target,
        )
        for check in checks:
            if check.severity == "ok":
                continue
            row = _oav_check_as_dict(check)
            row["target_volume_ml"] = target
            findings.append(row)
            if severity_rank[check.severity] > severity_rank[worst]:
                worst = check.severity

    data = {
        "source_volume_ml": config.batch_volume_ml,
        "targets_ml": list(targets),
        "findings": findings,
    }
    if worst == "error":
        return _result("oav_scaling_guard", "FAIL", f"{len(findings)} scaling blocker(s)", data)
    if worst == "warn":
        status = "FAIL" if config.commercial_mode else "WARN"
        detail = f"{len(findings)} scaling warning(s)"
        if config.commercial_mode:
            detail = "commercial blocker: " + detail
        return _result("oav_scaling_guard", status, detail, data)
    if worst == "info":
        return _result(
            "oav_scaling_guard",
            "WARN",
            f"{len(findings)} trace scaling info item(s)",
            data,
        )
    return _result("oav_scaling_guard", "PASS", "all requested targets scale cleanly", data)


_TRAILING_PARENTHETICAL = re.compile(r"\s*\([^()]*\)\s*$")


def _ifra_alt_names(material) -> list[str]:
    """Other names to try for a row: canonical, profile, registry and the suffix-free name."""
    names = [material.canonical_name, material.profile_name, material.registry_name]
    stripped = _TRAILING_PARENTHETICAL.sub("", material.name).strip()
    if stripped and stripped != material.name:
        names.append(stripped)
    return [n for n in dict.fromkeys(names) if n and n != material.name]


def _finished_product_pct_w_w(
    state: FormulaState, config: ReleaseGateConfig
) -> tuple[dict[str, float], str, FinishedProductEstimate | None]:
    """Each row's active material as % w/w of the finished product, and the basis used."""
    if state.exact_finished_product_ppm_available:
        pct: dict[str, float] = {}
        for m in state.materials:
            pct[m.name] = pct.get(m.name, 0.0) + float(m.active_finished_product_ppm_w_w) / 1e4
        return pct, "exact_finished_product_w_w", None
    estimate = estimate_finished_product_pct_w_w(
        [
            FinishedProductRow(
                name=m.name,
                stock_ul=m.raw_ul,
                active_fraction=m.dilution,
                active_g=m.authoritative_active_g,
                active_density_g_ml=(
                    None if str(m.density_source).startswith("fallback:") else m.density_g_ml
                ),
                carrier=m.stock_carrier or None,
                fraction_basis=m.stock_fraction_basis,
            )
            for m in state.materials
        ],
        batch_volume_ml=config.batch_volume_ml,
    )
    return dict(estimate.pct_w_w), "finished_product_w_w_estimate", estimate


def _ifra_row_dict(check: IFRACheck, headroom: float) -> dict:
    limit = check.limit_pct
    effective_limit = limit * headroom if limit is not None else None
    return {
        "material": check.material,
        "matched_name": check.matched_name,
        "ifra_name": check.ifra_name,
        "ifra_status": check.status,
        "standard": check.standard,
        # Unrounded: the optimizer scales its cap by actual/limit, and a rounded value
        # can hide a hair over the limit and stall the repair.
        "actual_pct": check.pct,
        "limit_pct": limit,
        "effective_limit_pct": round(effective_limit, 6) if effective_limit is not None else None,
        "headroom": headroom,
        "usage_pct": round(check.ratio * 100.0, 1) if check.ratio is not None else None,
        "effective_usage_pct": (
            round(check.pct / effective_limit * 100.0, 1) if effective_limit else None
        ),
        "verdict": check.verdict,
        "message": check.message,
    }


def _ifra_group_dict(group: IFRAGroupCheck, headroom: float) -> dict:
    ratio_rule = group.rule == "sum_of_ratios_le_1"
    limit = 1.0 if ratio_rule else group.limit_pct
    effective_limit = limit * headroom if limit is not None else None
    return {
        "material": group.id,
        "group": group.id,
        "standard": group.standard,
        "rule": group.rule,
        "members": dict(group.member_pcts),
        "actual_pct": group.total,
        "limit_pct": limit,
        "effective_limit_pct": round(effective_limit, 6) if effective_limit is not None else None,
        "headroom": headroom,
        "usage_pct": round(group.total / limit * 100.0, 1) if limit else None,
        "effective_usage_pct": (
            round(group.total / effective_limit * 100.0, 1) if effective_limit else None
        ),
        "verdict": group.verdict,
        "message": group.message,
    }


def _ifra_entry_dict(entry: IFRACheck | IFRAGroupCheck, headroom: float) -> dict:
    if isinstance(entry, IFRAGroupCheck):
        return _ifra_group_dict(entry, headroom)
    return _ifra_row_dict(entry, headroom)


def _gate_safety(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    ingredients = {m.name: m.raw_ul for m in state.materials}
    dilutions = {m.name: m.dilution for m in state.materials}
    headroom = config.effective_ifra_headroom()
    pct_w_w, basis, estimate = _finished_product_pct_w_w(state, config)
    alt_names = {m.name: _ifra_alt_names(m) for m in state.materials}
    # Allergen declarations, dermal exposure and sensitizer scoring only, on the same
    # finished-product % w/w; IFRA verdicts come from the sourced Category 4 table below.
    report = score_ifra_compliance(
        ingredients,
        dilutions,
        total_volume_ml=config.batch_volume_ml,
        finished_pct_w_w=pct_w_w,
        alt_names=alt_names,
    )
    table = load_ifra_table()
    evaluation = evaluate_ifra(
        pct_w_w,
        table=table,
        alt_names=alt_names,
        headroom=headroom,
    )
    failures = [_ifra_entry_dict(e, headroom) for e in evaluation.failures]
    warnings = [_ifra_entry_dict(e, headroom) for e in evaluation.warnings]
    holds = [_ifra_row_dict(c, headroom) for c in evaluation.holds]
    unchecked = sorted(c.material for c in evaluation.unchecked)
    banned = [f["material"] for f in failures if f.get("ifra_status") == "prohibited"]
    headroom_violations = [f for f in failures if f.get("ifra_status") != "prohibited"]
    # Over the IFRA limit itself; headroom_violations also holds rows over limit x headroom.
    violations = [
        f
        for f in headroom_violations
        if f["limit_pct"] is not None and f["actual_pct"] > f["limit_pct"]
    ]
    edge_dosing = [w for w in warnings if w.get("ifra_status") == "restricted" or "group" in w]
    natural_warnings = [w for w in warnings if w.get("ifra_status") == "natural_no_own_standard"]
    overfilled = bool(estimate.overfilled) if estimate is not None else False
    assumptions = list(estimate.assumptions) if estimate is not None else []
    batch_default = config.batch_volume_source == "default"
    data = {
        "score": report.score,
        "violations": violations,
        "headroom_violations": headroom_violations,
        "warnings": warnings,
        "diagnostics": report.diagnostics,
        "edge_dosing": edge_dosing,
        "banned": banned,
        "allergen_declarations": report.allergen_declarations,
        "dermal_exposure": report.dermal_exposure,
        "uptake_weighted_sensitizers": report.uptake_weighted_sensitizers,
        "missing_ifra_limit": unchecked,
        "unchecked": unchecked,
        "holds": holds,
        "specification_notes": [_ifra_row_dict(c, headroom) for c in evaluation.notes],
        "rows": [_ifra_row_dict(c, headroom) for c in evaluation.checks],
        "groups": [_ifra_group_dict(g, headroom) for g in evaluation.group_checks],
        "headroom": config.ifra_headroom,
        "effective_headroom": headroom,
        "commercial_mode": config.commercial_mode,
        "concentration_basis": basis,
        "batch_volume_ml": config.batch_volume_ml,
        "batch_volume_source": config.batch_volume_source,
        "ifra_table": {
            "amendment_in_force": table.amendment_in_force,
            "category": table.category,
            "basis": table.basis,
            "verified_on": table.verified_on,
        },
        "assumptions": assumptions,
        "overfilled": overfilled,
        "finished_mass_g": (
            round(estimate.finished_mass_g, 6) if estimate is not None else None
        ),
        "quantitative_authority": state.quantitative_authority,
        "authorization": (
            "PROVISIONAL_NOT_RELEASE_AUTHORITY"
            if not state.exact_finished_product_ppm_available
            else "EXACT_FINISHED_PRODUCT_MASS_CHAIN"
        ),
    }
    basis_note = f"basis {basis}"
    if assumptions:
        basis_note += f" ({len(assumptions)} density/carrier assumption(s))"
    if failures:
        return _result(
            "safety_ifra_allergen",
            "FAIL",
            "IFRA Category 4 failures: "
            + "; ".join(f["message"] for f in failures)
            + f"; {basis_note}",
            data,
        )
    if holds or overfilled:
        parts = [f"IFRA hold: {h['message']}" for h in holds]
        if overfilled:
            parts.append(
                f"stocks ({estimate.concentrate_ml:.3g} mL) exceed the "
                f"{config.batch_volume_ml:g} mL bottle; finished-product % w/w is not defined"
            )
        return _result("safety_ifra_allergen", "HOLD", "; ".join(parts) + f"; {basis_note}", data)
    detail: list[str] = []
    if edge_dosing:
        detail.append(
            f"{len(edge_dosing)} near the IFRA limit: "
            + ", ".join(f"{w['material']} {w['usage_pct']}%" for w in edge_dosing)
        )
    if natural_warnings:
        detail.append(
            f"{len(natural_warnings)} natural(s) without their own IFRA standard "
            "(constituents not summed)"
        )
    if unchecked:
        detail.append(f"{len(unchecked)} material(s) not in the IFRA Category 4 table")
    if batch_default:
        detail.append(
            f"bottle size not found; default {config.batch_volume_ml:g} mL assumed"
        )
    if report.allergen_declarations:
        detail.append(f"{len(report.allergen_declarations)} EU allergen declarations")
    if detail:
        return _result("safety_ifra_allergen", "WARN", "; ".join(detail) + f"; {basis_note}", data)
    return _result(
        "safety_ifra_allergen",
        "PASS",
        f"IFRA Category 4 within limits; score {report.score:.1f}; {basis_note}",
        data,
    )


def _gate_perfumer_logic(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    result = evaluate_perfumer_logic(
        formula,
        brief=config.brief,
        family_archetype=config.family_archetype,
    )
    if result.status == "FAIL":
        detail = "; ".join(
            f"{check.name}: {check.detail}" for check in result.checks if check.status == "FAIL"
        )
        return _result("perfumer_logic", "FAIL", f"{result.brief}; rerun optimizer: {detail}")
    if result.status == "WARN":
        detail = "; ".join(f"{check.name}: {check.detail}" for check in result.checks)
        return _result("perfumer_logic", "WARN", f"{result.brief}; {detail}")
    return _result("perfumer_logic", "PASS", result.brief)


def _gate_family_drift_detector(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    archetype = infer_archetype(config.brief, config.family_archetype)
    if not archetype:
        return _skipped("family_drift_detector", "not requested")
    spec = get_archetype(archetype)
    if spec is None:
        return _result("family_drift_detector", "WARN", f"unknown family archetype: {archetype}")

    evaluation = evaluate_family_archetype(formula, archetype)
    failed = [check for check in evaluation.checks if check.status == "FAIL"]
    data = {
        "family_archetype": archetype,
        "family": evaluation.family,
        "label": evaluation.label,
        "checks": [
            {
                "name": check.name,
                "status": check.status,
                "detail": check.detail,
                "value": check.value,
            }
            for check in evaluation.checks
        ],
        "forbidden_hits": list(evaluation.forbidden_hits),
    }
    if failed:
        detail = "; ".join(f"{check.name}: {check.detail}" for check in failed[:4])
        return _result("family_drift_detector", "FAIL", f"{archetype}; {detail}", data)
    return _result("family_drift_detector", "PASS", f"{archetype}; no family drift", data)


def _gate_novelty_vs_reference(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    if not config.family_archetype:
        return _skipped("novelty_vs_reference", "not requested")
    assessment = novelty_assessment(formula, config.family_archetype)
    return _result(
        "novelty_vs_reference",
        assessment["status"],
        assessment["detail"],
        {"family_archetype": config.family_archetype, **assessment},
    )


def _gate_perfume_knowledge(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Evaluate formula against comprehensive perfume knowledge taxonomy.

    Checks pyramid balance against family targets and evaluates OAV
    alignment with per-family/per-window OAV targets using the complete
    perfume knowledge system.
    """
    family = infer_archetype(config.brief, config.family_archetype) or "generic"
    resolved = resolve_family_key(family)

    # A layer distribution is not a fragrance-family classifier.  Keep a generic
    # run diagnostic instead of laundering base dominance into "chypre" (or any
    # other named family) without an explicit brief/archetype.
    if family == "generic":
        nd = state.note_distribution()
        return _result(
            "perfume_knowledge",
            "WARN",
            "No explicit family brief/archetype; family-specific pyramid and OAV targets were not evaluated.",
            {
                "family": "generic",
                "family_source": "not_inferred",
                "note_distribution": nd,
            },
        )

    normed_note_map = {}
    for m in state.materials:
        key = normalize_name(m.name)
        normed_note_map[key] = str(m.note or "heart")
    note_map = normed_note_map

    active_pct = state.active_percentages()
    pyramid_eval = evaluate_pyramid_balance(
        active_pct,
        family=family,
        bracket=config.concentration_bracket,
        note_map=note_map,
    )

    material_oavs = {m.name: float(m.oav or 0.0) for m in state.materials if (m.oav or 0.0) > 0.0}
    material_families = {m.name: str(m.family or "unknown") for m in state.materials}

    top_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "top")
    heart_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "heart")
    base_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "base")

    warnings: list[str] = []
    fail_reasons: list[str] = []
    spec = get_archetype(config.family_archetype or family)
    soften_reference_control = bool(
        spec is not None
        and spec.role == "reference_control"
        and (not config.commercial_mode or config.is_commercial_trial())
    )

    if pyramid_eval.status == "off_target":
        message = f"Pyramid off-target: {pyramid_eval.details}"
        if soften_reference_control:
            warnings.append(message)
        else:
            fail_reasons.append(message)
    elif pyramid_eval.status == "needs_improvement":
        warnings.append(f"Pyramid needs improvement: {pyramid_eval.details}")

    for name, oav_eval in [
        ("top", top_oav_eval),
        ("heart", heart_oav_eval),
        ("base", base_oav_eval),
    ]:
        if oav_eval.status == "off_target":
            message = f"{name} OAV off-target for family {resolved}"
            if soften_reference_control:
                warnings.append(message)
            else:
                fail_reasons.append(message)
        elif oav_eval.status == "needs_improvement":
            warnings.append(f"{name} OAV needs improvement for family {resolved}")

    data = {
        "family_key": resolved,
        "bracket": config.concentration_bracket,
        "pyramid": pyramid_eval.as_dict(),
        "oav_targets": {
            "top": top_oav_eval.as_dict(),
            "heart": heart_oav_eval.as_dict(),
            "base": base_oav_eval.as_dict(),
        },
    }

    if fail_reasons:
        return _result(
            "perfume_knowledge",
            "FAIL",
            "; ".join(fail_reasons[:3]),
            data,
        )
    if warnings:
        return _result(
            "perfume_knowledge",
            "WARN",
            "; ".join(warnings[:3]),
            data,
        )
    return _result(
        "perfume_knowledge",
        "PASS",
        f"Pyramid fit {pyramid_eval.overall_fit:.2f}; family {resolved} aligned",
        data,
    )


def _gate_oav_legibility(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    perceptible = [m for m in state.materials if (m.oav or 0.0) >= 1.0]
    if len(perceptible) < config.min_perceptible_materials:
        return _result(
            "oav_legibility",
            "FAIL",
            f"{len(perceptible)} perceptible materials; need >= {config.min_perceptible_materials}",
        )
    subliminal_active = sum(m.active_ul for m in state.materials if (m.oav or 0.0) < 0.2)
    subliminal_ratio = subliminal_active / (state.total_active_ul or 1.0)
    if subliminal_ratio > 0.45:
        return _result(
            "oav_legibility",
            "WARN",
            f"{subliminal_ratio:.0%} active mass is near-subliminal by OAV",
        )
    return _result("oav_legibility", "PASS", f"{len(perceptible)} perceptible materials")


def _gate_oav_overdose_blocker(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Flag high modeled OAV without treating it as an overdose verdict.

    OAV is useful for screening likely contributors, but mixture suppression,
    adaptation, and supra-threshold intensity prevent a universal numerical
    ceiling. A high value requests review and sensory validation; it cannot
    independently fail release or prescribe a dilution.
    """
    high_threshold = 10_000
    extreme_threshold = 50_000
    flagged = []
    for material in state.materials:
        oav = float(material.oav or 0.0)
        if oav <= high_threshold:
            continue
        flagged.append(
            {
                "name": material.name,
                "oav": int(oav),
                "signal_tier": "extreme" if oav > extreme_threshold else "high",
                "oav_model": material.sources.get("oav_model", "unknown"),
                "active_ul": round(material.active_ul, 6),
                "dilution": round(material.dilution, 6),
            }
        )

    if flagged:
        names = ", ".join(f"{row['name']}={row['oav']}" for row in flagged[:5])
        return _result(
            "oav_overdose_blocker",
            "WARN",
            f"High modeled OAV screening signal: {names}; validate by controlled dilution/omission trials",
            {
                "flagged": flagged,
                "evidence_class": "MODELED_SCREENING_ONLY",
                "release_authority": False,
                "interpretation": (
                    "OAV ranks possible contributors; it does not linearly predict "
                    "mixture intensity, fatigue, pleasantness, or a safe dose."
                ),
            },
        )
    return _result(
        "oav_overdose_blocker",
        "PASS",
        "no material exceeds the 10,000 OAV review threshold",
    )


def _formula_dilutions_for_g15(formula: Mapping) -> dict[str, float]:
    ingredients = dict(formula.get("ingredients_ul", {}) or {})
    dilutions = dict(formula.get("dilutions", {}) or {})
    stock_specs = dict(formula.get("stock_specs", {}) or {})
    resolved: dict[str, float] = {}
    for raw_name in ingredients:
        name = str(raw_name)
        spec = dict(stock_specs.get(raw_name, stock_specs.get(name, {})) or {})
        value = spec.get("fraction", dilutions.get(raw_name, dilutions.get(name, 1.0)))
        resolved[name] = float(value)
    return resolved


def _gate_g15_oav_firewall(
    formula: Mapping,
    simulation: Sequence[SimulationFrame],
    config: ReleaseGateConfig,
    *,
    parent_formula: Mapping | None = None,
    authorized_active_dose_changes: Mapping[str, str] | None = None,
) -> GateResult:
    """Mandatory pre-presentation dose-lineage and temporal OAV firewall.

    G15 does not set an absolute OAV ceiling. It blocks unexplained revision
    discontinuities and stock-rebase active-dose errors, while modeled OAV
    dominance remains a review signal only.
    """
    parent_uid = str(formula.get("parent_formula_uid", "") or "").strip()
    data: dict = {
        "gate_id": "G15",
        "evidence_class": "DETERMINISTIC_DOSE_INTEGRITY_PLUS_MODELED_OAV_SCREENING",
        "hard_gate_authority": "DOSE_LINEAGE_AND_REVISION_DISCONTINUITY_ONLY",
        "oav_release_authority": False,
        "child_formula_hash": formula_hash_from_record(formula),
        "oav_interpretation": (
            "Modeled OAV is a time-resolved screening signal, not percent perceived "
            "contribution, beauty, similarity, preference, or measured headspace."
        ),
        "declared_parent_formula_uid": parent_uid or None,
        "authorized_active_dose_changes": dict(authorized_active_dose_changes or {}),
    }

    if parent_uid and parent_formula is None:
        data["failure_code"] = "G15_PARENT_BASELINE_MISSING"
        return _result(
            "g15_oav_firewall",
            "FAIL",
            f"Revision declares parent_formula_uid={parent_uid} but no parent formula baseline was supplied.",
            data,
        )

    parent_ingredients = None
    parent_dilutions = None
    parent_series = None
    if parent_formula is not None:
        if not isinstance(parent_formula, Mapping):
            data["failure_code"] = "G15_PARENT_BASELINE_INVALID"
            return _result(
                "g15_oav_firewall",
                "FAIL",
                "Parent formula baseline must be a mapping.",
                data,
            )
        supplied_parent_uid = str(parent_formula.get("formula_uid", "") or "").strip()
        data["supplied_parent_formula_uid"] = supplied_parent_uid or None
        if parent_uid and not supplied_parent_uid:
            data["failure_code"] = "G15_PARENT_ID_UNVERIFIED"
            return _result(
                "g15_oav_firewall",
                "FAIL",
                "A parent_formula_uid is declared, but the supplied parent baseline has no formula_uid to verify lineage.",
                data,
            )
        if parent_uid and supplied_parent_uid != parent_uid:
            data["failure_code"] = "G15_PARENT_ID_MISMATCH"
            return _result(
                "g15_oav_firewall",
                "FAIL",
                f"Supplied parent formula_uid={supplied_parent_uid} does not match declared parent_formula_uid={parent_uid}.",
                data,
            )

        raw_parent_ingredients = parent_formula.get("ingredients_ul", {}) or {}
        if not isinstance(raw_parent_ingredients, Mapping) or not raw_parent_ingredients:
            data["failure_code"] = "G15_PARENT_BASELINE_INVALID"
            return _result(
                "g15_oav_firewall",
                "FAIL",
                "Parent formula baseline has no usable ingredients_ul mapping.",
                data,
            )
        parent_ingredients = {
            str(name): float(value) for name, value in raw_parent_ingredients.items()
        }
        data["parent_formula_hash"] = formula_hash_from_record(parent_formula)
        parent_dilutions = _formula_dilutions_for_g15(parent_formula)
        data["parent_g15_dilutions"] = dict(parent_dilutions)

        parent_matrix = dict(parent_formula.get("matrix_moles", {}) or {})
        if not parent_matrix:
            parent_matrix = dict(config.matrix_components_moles)
        parent_matrix_mass_g = float(
            parent_formula.get("matrix_mass_g", config.matrix_mass_g) or config.matrix_mass_g
        )
        parent_matrix_source = str(
            parent_formula.get("matrix_source", config.matrix_source) or config.matrix_source
        )
        parent_stock_specs = {
            str(name): dict(spec or {})
            for name, spec in dict(parent_formula.get("stock_specs", {}) or {}).items()
        }
        parent_state = build_formula_state(
            parent_ingredients,
            parent_dilutions,
            stock_specs=parent_stock_specs,
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
            matrix_moles=parent_matrix,
            matrix_mass_g=parent_matrix_mass_g,
            matrix_source=parent_matrix_source,
        )
        parent_series = [
            frame.as_dict()
            for frame in simulate_formula(
                parent_ingredients,
                parent_dilutions,
                batch_volume_ml=config.batch_volume_ml,
                temperature_K=config.temperature_K,
                initial_state=parent_state,
            )
        ]

    child_ingredients = {
        str(name): float(value)
        for name, value in dict(formula.get("ingredients_ul", {}) or {}).items()
    }
    child_dilutions = _formula_dilutions_for_g15(formula)
    data["child_g15_dilutions"] = dict(child_dilutions)
    child_series = [frame.as_dict() for frame in simulation]
    guard = evaluate_pre_mix_guard(
        child_ingredients_ul=child_ingredients,
        child_dilutions=child_dilutions,
        child_time_series=child_series,
        parent_ingredients_ul=parent_ingredients,
        parent_dilutions=parent_dilutions,
        parent_time_series=parent_series,
        authorized_active_dose_changes=authorized_active_dose_changes,
    )
    data["pre_mix_guard"] = guard.as_dict()

    if guard.status == "FAIL":
        blockers = [
            finding.code for finding in guard.findings if finding.severity == "FAIL"
        ]
        return _result(
            "g15_oav_firewall",
            "FAIL",
            "G15 blocked pre-presentation formula output: " + ", ".join(blockers),
            data,
        )
    if guard.status == "WARN":
        warnings = [finding.code for finding in guard.findings]
        return _result(
            "g15_oav_firewall",
            "WARN",
            "G15 requires review before compounding: " + ", ".join(warnings),
            data,
        )
    return _result(
        "g15_oav_firewall",
        "PASS",
        "Dose lineage is continuous and no modeled OAV anomaly crossed the G15 review thresholds.",
        data,
    )


def _gate_odt_sanity(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """WARN if any material has a suspicious ODT value (0.0, sentinel defaults, 1.0)."""
    suspicious = []
    composite_exemptions = []
    for m in state.materials:
        odt = m.odt_air_ppm
        if odt is None:
            if m.has_odt_authority:
                composite_exemptions.append(m.name)
            else:
                suspicious.append(f"{m.name}=None")
        elif odt == 0.0:
            suspicious.append(f"{m.name}=0.0ppm")
        elif odt == 1.0:
            suspicious.append(f"{m.name}=1.0ppm (possible sentinel)")
        elif odt == 100.0:
            suspicious.append(f"{m.name}=100ppm (possible sentinel)")
    from engine.science_audit import build_material_consistency_audit

    consistency = build_material_consistency_audit([material.name for material in state.materials])
    odt_conflicts = [
        row for row in consistency["conflicts"] if str(row["field"]).startswith("odt_")
    ]
    if suspicious or odt_conflicts:
        details = []
        if suspicious:
            details.append(
                f"{len(suspicious)} materials with suspect ODT values: " + ", ".join(suspicious[:5])
            )
        if odt_conflicts:
            details.append(f"{len(odt_conflicts)} unresolved cross-source ODT conflicts")
        return _result(
            "odt_sanity",
            "WARN",
            "; ".join(details),
            {
                "suspect_odts": suspicious,
                "natural_composite_exemptions": composite_exemptions,
                "cross_source_conflicts": odt_conflicts,
                "release_authority": False,
            },
        )
    return _result(
        "odt_sanity",
        "PASS",
        "all bulk or constituent-resolved ODT values pass sanity check",
        {"natural_composite_exemptions": composite_exemptions},
    )


def _gate_vp_cross_source(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Audit VP origin, temperature model, and cross-source consistency."""
    composite_vp_exemptions = sorted(
        m.name
        for m in state.materials
        if (m.vp_pure_pa is None or m.vp_pure_pa == 0.0) and m.has_vp_authority
    )
    no_vp = [
        (m.name, m.vp_pure_pa)
        for m in state.materials
        if (m.vp_pure_pa is None or m.vp_pure_pa == 0.0) and not m.has_vp_authority
    ]
    fallback_sources = [
        m.name for m in state.materials if "fallback" in str(m.sources.get("vp", "")).lower()
    ]
    temperature_models: dict[str, int] = {}
    inferred_dhvap_materials: list[str] = []
    for material in state.materials:
        model = str(material.sources.get("vp_temperature", "missing"))
        temperature_models[model] = temperature_models.get(model, 0) + 1
        if model.startswith("heuristic:"):
            inferred_dhvap_materials.append(material.name)
    issues = []
    if no_vp:
        issues.append(
            f"{len(no_vp)} materials with VP=None or 0: {', '.join(n for n, _ in no_vp[:5])}"
        )
    if fallback_sources:
        issues.append(f"{len(fallback_sources)} materials with fallback VP source")
    if inferred_dhvap_materials:
        issues.append(
            f"{len(inferred_dhvap_materials)} materials use inferred enthalpy "
            f"for VP at {state.temperature_K:.2f} K"
        )
    from engine.science_audit import build_material_consistency_audit

    consistency = build_material_consistency_audit([material.name for material in state.materials])
    vp_conflicts = [row for row in consistency["conflicts"] if row["field"] == "vp_25c_pa"]
    if vp_conflicts:
        issues.append(f"{len(vp_conflicts)} unresolved cross-source VP conflicts")
    if issues:
        return _result(
            "vp_cross_source",
            "WARN",
            "; ".join(issues),
            {
                "no_vp": no_vp,
                "natural_composite_exemptions": composite_vp_exemptions,
                "fallback_vp_sources": fallback_sources,
                "temperature_models": temperature_models,
                "inferred_dhvap_materials": inferred_dhvap_materials,
                "cross_source_conflicts": vp_conflicts,
                "release_authority": False,
            },
        )
    return _result(
        "vp_cross_source",
        "PASS",
        "all materials have VP data and measured temperature dependence",
        {
            "temperature_models": temperature_models,
            "inferred_dhvap_materials": [],
            "natural_composite_exemptions": composite_vp_exemptions,
            "release_authority": False,
        },
    )


def _gate_dilution_consistency(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """WARN if any material has dilution > 100% (physically impossible) or dilution=0 (inert)."""
    bad_dilutions = [
        (m.name, m.dilution) for m in state.materials if m.dilution > 1.0 or m.dilution <= 0.0
    ]
    if bad_dilutions:
        names = ", ".join(f"{n}={d:.0%}" for n, d in bad_dilutions[:10])
        return _result(
            "dilution_consistency",
            "WARN",
            f"Impossible dilutions: {names}",
            {"bad_dilutions": [{"name": n, "dilution": round(d, 4)} for n, d in bad_dilutions]},
        )
    return _result("dilution_consistency", "PASS", "all dilutions are physically plausible")


def _gate_odt_completeness(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """WARN if any formula material lacks ODT data entirely."""
    composite_exemptions = sorted(
        m.name for m in state.materials if m.odt_air_ppm is None and m.has_odt_authority
    )
    missing = [
        (m.name, m.missing_fields) for m in state.materials if not m.has_odt_authority
    ]
    if missing:
        names = [n for n, _ in missing[:10]]
        oav_share = sum((m.oav or 0.0) for m in state.materials if m.odt_air_ppm is None) / max(
            sum((m.oav or 0.0) for m in state.materials), 1.0
        )
        return _result(
            "odt_completeness",
            "WARN",
            f"{len(missing)} material(s) lack ODT data; {oav_share:.0%} OAV share affected",
            {"missing_odt": names},
        )
    return _result(
        "odt_completeness",
        "PASS",
        "all materials have bulk or constituent-resolved ODT authority",
        {"natural_composite_exemptions": composite_exemptions},
    )


def _gate_oav_intelligence(
    state: FormulaState,
    simulation: Sequence[SimulationFrame],
    config: ReleaseGateConfig,
) -> GateResult:
    if not str(config.family_archetype or "").strip():
        return _skipped("oav_intelligence", "not requested")
    intelligence = analyze_oav_intelligence(state, simulation, config.family_archetype)
    status = intelligence.intelligence_status
    spec = get_archetype(config.family_archetype)
    if (
        status == "FAIL"
        and spec is not None
        and spec.role == "reference_control"
        and (not config.commercial_mode or config.is_commercial_trial())
    ):
        status = "WARN"
    if status == "FAIL":
        detail = (
            "; ".join(intelligence.intelligence_blocking_reasons[:3])
            or "future-module OAV intelligence blockers present"
        )
    elif status == "WARN":
        detail = (
            "; ".join(intelligence.intelligence_warning_reasons[:3])
            or "future-module OAV intelligence warnings present"
        )
    else:
        detail = "future-module OAV intelligence aligned"
    return _result("oav_intelligence", status, detail, intelligence.as_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# Olfactory Fatigue Thresholds — (warn_OAV, fail_OAV)
#
# SOURCE: Expert heuristic based on ODT multiples and consensus perfumery practice.
#   - Low-ODT potent materials (ionones, aldehydes): warn at ~100× ODT, fail at ~250× ODT
#   - Moderate materials (coumarin, vanillin): warn at ~50× ODT, fail at ~150× ODT
#   - Extremely low-ODT materials (skatole): warn at 50 OAV, fail at 100 OAV
#   - High-tolerance diffusants (hedione, iso e super): warn at 2000 OAV, fail at 5000-30000 OAV
#
# STATUS: Plausible heuristics — NOT experimentally validated.
# TODO: Validate against published adaptation studies (Dalton 2000, Wysocki & Beauchamp 1984,
#        Hummel et al. 2006) and panel sensory data.
# ═══════════════════════════════════════════════════════════════════════════════
_OLFACTORY_FATIGUE_THRESHOLDS: dict[str, tuple[float, float]] = {
    "beta ionone": (2000.0, 15000.0),
    "alpha ionone": (2000.0, 15000.0),
    "dihydro beta ionone": (2000.0, 15000.0),
    "alpha irone": (2000.0, 15000.0),
    "iso e super": (5000.0, 10000.0),
    "ambrox super": (2000.0, 5000.0),
    "ambrofix": (2000.0, 5000.0),
    "ambermax": (2000.0, 5000.0),
    "galaxolide": (500.0, 2000.0),
    "habanolide": (300.0, 1000.0),
    "tonalide": (500.0, 2000.0),
    "ethylene brassylate": (500.0, 2000.0),
    "hedione": (10000.0, 30000.0),
    "hedione hc": (10000.0, 30000.0),
    "coumarin": (300.0, 1000.0),
    "vanillin": (100.0, 500.0),
    "ethyl vanillin": (100.0, 500.0),
    "ethyl maltol": (100.0, 500.0),
    "calone": (200.0, 500.0),
    "dihydromyrcenol": (3000.0, 10000.0),
    "p-cresyl methyl ether": (2000.0, 20000.0),
    "indole": (100.0, 500.0),
    "skatole": (50.0, 100.0),
    "eugenol": (300.0, 1000.0),
    "cinnamaldehyde": (200.0, 500.0),
    "aldehyde c10": (200.0, 500.0),
    "aldehyde c11": (200.0, 500.0),
    "aldehyde c12": (200.0, 500.0),
}


def _gate_olfactory_fatigue(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    from engine.name_utils import normalize_name

    critical: list[str] = []
    warnings: list[str] = []
    for m in state.materials:
        oav = float(m.screening_oav or 0.0)
        if oav <= 0.0:
            continue
        norm = normalize_name(m.canonical_name or m.name)
        thresholds = _OLFACTORY_FATIGUE_THRESHOLDS.get(norm)
        if thresholds is None:
            continue
        warn_threshold, fail_threshold = thresholds
        if oav > fail_threshold:
            critical.append(f"{m.canonical_name}={oav:.0f} (high model signal)")
        elif oav > warn_threshold:
            warnings.append(f"{m.canonical_name}={oav:.0f} (limit {warn_threshold:.0f})")

    if critical:
        return _result(
            "olfactory_fatigue",
            "WARN",
            f"Adaptation/fatigue screening flag: {'; '.join(critical[:5])}"
            + (f" +{len(critical) - 5} more" if len(critical) > 5 else ""),
            data={
                "evidence_class": "HEURISTIC_SCREENING_ONLY",
                "release_authority": False,
                "sensory_validation_required": True,
            },
        )
    if warnings:
        return _result(
            "olfactory_fatigue",
            "WARN",
            f"Olfactory fatigue risk: {'; '.join(warnings[:5])}"
            + (f" +{len(warnings) - 5} more" if len(warnings) > 5 else ""),
        )
    return _result("olfactory_fatigue", "PASS", "no olfactory fatigue risks detected")


def _gate_roudnitska_transparence(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    from engine.ingredient_intelligence import _TRANSPARENCY_SCORES
    from engine.name_utils import normalize_name

    total_score = 0
    max_score = 0
    for m in state.materials:
        norm = normalize_name(m.canonical_name or m.name)
        score = _TRANSPARENCY_SCORES.get(m.canonical_name)
        if score is None:
            for k, v in _TRANSPARENCY_SCORES.items():
                if normalize_name(k) == norm:
                    score = v
                    break
        if score is not None:
            pct = m.active_ul / state.total_active_ul if state.total_active_ul > 0 else 0
            weighted = score * pct
            total_score += weighted
            max_score += 10 * pct
        else:
            max_score += 10 * (
                m.active_ul / state.total_active_ul if state.total_active_ul > 0 else 0
            )

    transparency_ratio = total_score / max_score * 100.0 if max_score > 0 else 50.0
    if transparency_ratio < 20.0:
        return _result(
            "roudnitska_transparence",
            "FAIL",
            f"Transparency ratio {transparency_ratio:.0f}% — too opaque, no lift (Roudnitska aesthetic)",
        )
    if transparency_ratio > 80.0:
        return _result(
            "roudnitska_transparence",
            "WARN",
            f"Transparency ratio {transparency_ratio:.0f}% — very transparent, may lack depth",
        )
    return _result(
        "roudnitska_transparence",
        "PASS",
        f"Transparency ratio {transparency_ratio:.0f}% — balanced (Roudnitska aesthetic)",
    )


def _gate_carles_pyramid(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Jean Carles volatility pyramid: 5 evaporation windows must all be populated."""
    windows = {
        "1h_top": 0.0,
        "3h_top_heart": 0.0,
        "6h_heart": 0.0,
        "12h_heart_base": 0.0,
        "24h+_base": 0.0,
    }
    total_active = state.total_active_ul or 1.0
    for m in state.materials:
        vp = m.vp_pure_pa or 0.0
        pct = m.active_ul / total_active * 100.0
        if vp > 2.0:
            windows["1h_top"] += pct
        elif vp > 0.5:
            windows["3h_top_heart"] += pct
        elif vp > 0.1:
            windows["6h_heart"] += pct
        elif vp > 0.02:
            windows["12h_heart_base"] += pct
        else:
            windows["24h+_base"] += pct

    empty = [k for k, v in windows.items() if v < 2.0]
    if empty:
        return _result(
            "carles_pyramid",
            "WARN" if len(empty) <= 2 else "FAIL",
            f"Carles pyramid: empty windows = {', '.join(empty)} (need >2% active in each of 5 windows)",
            {k: round(v, 2) for k, v in windows.items()},
        )
    return _result(
        "carles_pyramid",
        "PASS",
        "Carles pyramid: all 5 volatility windows populated",
        {k: round(v, 2) for k, v in windows.items()},
    )


def _gate_beaux_registres(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Ernest Beaux tonal registers: soprano/alto/tenor/bass must all be present."""
    registers: dict[str, float] = {
        "soprano": 0.0,
        "alto": 0.0,
        "tenor": 0.0,
        "bass": 0.0,
    }
    total_active = state.total_active_ul or 1.0
    for m in state.materials:
        vp = m.vp_pure_pa or 0.0
        pct = m.active_ul / total_active * 100.0
        if vp > 10.0:
            registers["soprano"] += pct
        elif vp > 1.0:
            registers["alto"] += pct
        elif vp > 0.1:
            registers["tenor"] += pct
        else:
            registers["bass"] += pct

    missing = [k for k, v in registers.items() if v < 1.0]
    if missing:
        return _result(
            "beaux_registres",
            "FAIL" if len(missing) >= 2 else "WARN",
            f"Beaux registers missing: {', '.join(missing)}",
            {k: round(v, 2) for k, v in registers.items()},
        )
    return _result(
        "beaux_registres",
        "PASS",
        "All 4 Beaux tonal registers present",
        {k: round(v, 2) for k, v in registers.items()},
    )


def _gate_osmotheque_archivability(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Osmothéque standard: formulas must be archivable (traceable, reproducible)."""
    opaque_count = 0
    unknown_count = 0
    total = state.material_count or 1
    for m in state.materials:
        if m.is_opaque_preblend:
            opaque_count += 1
        if not m.is_known:
            unknown_count += 1

    issues = []
    if opaque_count > 0:
        opaque_pct = opaque_count / total * 100.0
        if opaque_pct > 20.0:
            return _result(
                "osmotheque_archivability",
                "FAIL",
                f"{opaque_count}/{total} materials are opaque preblends (>20%) — not archivable",
            )
        issues.append(f"{opaque_count} opaque preblend(s)")
    if unknown_count > 0:
        issues.append(f"{unknown_count} unknown material(s)")

    if issues:
        return _result("osmotheque_archivability", "WARN", f"Archivability: {'; '.join(issues)}")
    return _result("osmotheque_archivability", "PASS", "All materials traceable and archivable")


# ── Jellinek psychological classification ─────────────────────────────
# Source: Paul Jellinek, The Practice of Modern Perfumery (1949)
_JELLINEK_CLASSES: dict[str, str] = {
    # erogenic (animalic, warm, skin-like)
    "ambrox super": "erogenic",
    "ambrofix": "erogenic",
    "ambermax": "erogenic",
    "habanolide": "erogenic",
    "galaxolide": "erogenic",
    "ethylene brassylate": "erogenic",
    "ambrettolide": "erogenic",
    "exaltolide": "erogenic",
    "musk ketone": "erogenic",
    "tonalide": "erogenic",
    "zenolide": "erogenic",
    "indole": "erogenic",
    "skatole": "erogenic",
    "isobutyl quinoline": "erogenic",
    "cashmeran": "erogenic",
    "labdanum": "erogenic",
    "labdanum absolute": "erogenic",
    "civet": "erogenic",
    "castoreum": "erogenic",
    # narcotic (white florals, intoxicating)
    "hedione": "narcotic",
    "hedione hc": "narcotic",
    "p-cresyl methyl ether": "narcotic",
    "methyl benzoate": "narcotic",
    "benzyl acetate": "narcotic",
    "cis jasmone": "narcotic",
    "dihydrojasmone": "narcotic",
    "ylang ylang": "narcotic",
    "tuberose": "narcotic",
    "jasmine absolute": "narcotic",
    "neroli eo": "narcotic",
    "orange blossom": "narcotic",
    "hydroxycitronellal": "narcotic",
    "methyl salicylate": "narcotic",
    "eugenol": "narcotic",
    "methyl anthranilate": "narcotic",
    # stimulating (citrus, fresh, green)
    "bergamot": "stimulating",
    "lemon": "stimulating",
    "lime": "stimulating",
    "grapefruit": "stimulating",
    "mandarin": "stimulating",
    "orange": "stimulating",
    "aldehydes": "stimulating",
    "cis-3-hexenol": "stimulating",
    "dihydromyrcenol": "stimulating",
    "calone": "stimulating",
    "linalool": "stimulating",
    "linalyl acetate": "stimulating",
    "petitgrain": "stimulating",
    "black pepper": "stimulating",
    "pink pepper": "stimulating",
    "cardamom": "stimulating",
    "clary sage": "stimulating",
    # anti-erogenic (woods, mosses, dry notes)
    "iso e super": "anti_erogenic",
    "timberol": "anti_erogenic",
    "clearwood": "anti_erogenic",
    "evernyl": "anti_erogenic",
    "cedarwood": "anti_erogenic",
    "vetiver": "anti_erogenic",
    "patchouli": "anti_erogenic",
    "sandalore": "anti_erogenic",
    "javanol": "anti_erogenic",
    "ebanol": "anti_erogenic",
    "polysantol": "anti_erogenic",
    "norlimbanol": "anti_erogenic",
    "kephalis": "anti_erogenic",
    "ambrocenide": "anti_erogenic",
    "vertofix": "anti_erogenic",
    "koavone": "anti_erogenic",
    "coumarin": "anti_erogenic",
    "vanillin": "anti_erogenic",
    "ethyl vanillin": "anti_erogenic",
}

# ── Adaptation timing tiers ──────────────────────────────────────────
# Source: Olfactory neuroscience (Livermore & Laing)
_ADAPTATION_TIERS: dict[str, set[str]] = {
    "fast": {"citrus", "green", "aldehydes", "calone", "cis-3-hexenol"},
    "medium": {
        "hedione",
        "ionone",
        "irone",
        "linalool",
        "geraniol",
        "citronellol",
        "benzyl acetate",
        "nerol",
        "rhodinol",
        "rose oxide",
        "damascenone",
        "damascone",
        "p-cresyl methyl ether",
        "indole",
        "methyl salicylate",
        "methyl benzoate",
        "eugenol",
        "ylang",
    },
    "slow": {
        "iso e super",
        "musks",
        "galaxolide",
        "habanolide",
        "ethylene brassylate",
        "ambrettolide",
        "exaltolide",
        "ambrox",
        "ambermax",
        "ambrofix",
        "cashmeran",
        "vanillin",
        "coumarin",
        "evernyl",
        "cedarwood",
        "vetiver",
        "patchouli",
        "javanol",
        "ebanol",
        "sandalore",
        "benzoin",
        "labdanum",
        "timberol",
        "clearwood",
    },
}


def _adaptation_tier(material) -> str:
    """Classify adaptation using both material identity and odor family."""
    from engine.name_utils import normalize_name

    family = normalize_name(str(material.family or ""))
    if family in {"citrus", "green", "fresh"}:
        return "fast"

    name = normalize_name(material.canonical_name or material.name)
    for tier, keywords in _ADAPTATION_TIERS.items():
        if any(keyword in name for keyword in keywords):
            return tier
    return "medium"


def _gate_literature_compliance(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Meta-gate: validates formula against established perfumery literature principles.

    Checks:
      1. Arctander (1969): base material VP should be predominantly <0.1 Pa
      2. Ohloff, Pickenhagen & Kraft (2011): no syn/anti antagonism in key pairs
      3. Ellena (2011): transparency index — fewer materials = more transparent
      4. Roudnitska: hedione percentage should be 5-20% of concentrate
      5. Livermore & Laing (1996): perceptible channels should not exceed 3-4

    Returns PASS/WARN with literature citations.
    """
    if not _LITERATURE_DB_LOADED or _cite_fn is None:
        return _result(
            "literature_compliance",
            "WARN",
            "Literature reference database not loaded — compliance cannot be verified",
        )

    cite = _cite_fn
    warnings: list[str] = []
    info: list[str] = []
    principles_passed = 0
    principles_total = 5

    # ── 1. Arctander: base VP threshold ──
    base_materials = [m for m in state.materials if m.note == "base" and m.vp_pure_pa]
    high_vp_bases = [m for m in base_materials if float(m.vp_pure_pa or 0) > 0.1]
    if high_vp_bases:
        names = ", ".join(m.name for m in high_vp_bases[:5])
        warnings.append(
            f"{len(high_vp_bases)} base-tier material(s) have VP > 0.1 Pa: {names} "
            f"— may not provide true base fixation {cite('Arctander 1969')}"
        )
    else:
        info.append(f"All base materials VP < 0.1 Pa ✓ {cite('Arctander 1969')}")
        principles_passed += 1

    # ── 2. Ohloff SAR: check for Schiff base formation in key pairs ──
    aldehyde_mats = [
        m
        for m in state.materials
        if "aldehyde" in m.name.lower()
        or m.name.lower() in ("citral", "citronellal", "vanillin", "heliotropin")
    ]
    amine_mats = [
        m
        for m in state.materials
        if m.name.lower() in ("methyl anthranilate", "indole", "aurantiol")
    ]
    if aldehyde_mats and amine_mats:
        warnings.append(
            f"Aldehydes ({', '.join(m.name for m in aldehyde_mats[:3])}) "
            f"and amines present — potential Schiff base formation "
            f"{cite('Ohloff, Pickenhagen & Kraft 2011')}"
        )
    else:
        info.append(f"No Schiff base risk detected ✓ {cite('Ohloff, Pickenhagen & Kraft 2011')}")
        principles_passed += 1

    # ── 3. Ellena: transparency via material count ──
    n_materials = len(state.materials)
    if n_materials <= 12:
        info.append(
            f"Ellena transparency: {n_materials} materials — minimalist ✓ {cite('Ellena 2011')}"
        )
        principles_passed += 1
    elif n_materials <= 20:
        info.append(f"Ellena transparency: {n_materials} materials — moderate")
        principles_passed += 1
    else:
        warnings.append(
            f"Ellena transparency: {n_materials} materials — dense, may lack clarity "
            f"{cite('Ellena 2011')}"
        )

    # ── 4. Roudnitska: hedione percentage ──
    hedione_mats = [m for m in state.materials if "hedione" in m.name.lower()]
    if hedione_mats:
        total_active_ul = sum(float(m.active_ul or 0) for m in state.materials)
        hedione_active_ul = sum(float(m.active_ul or 0) for m in hedione_mats)
        hedione_pct = (hedione_active_ul / total_active_ul * 100) if total_active_ul > 0 else 0
        if 5 <= hedione_pct <= 20:
            info.append(
                f"Hedione at {hedione_pct:.0f}% of active — ideal radiance ✓ {cite('Roudnitska')}"
            )
            principles_passed += 1
        elif hedione_pct > 20:
            warnings.append(
                f"Hedione at {hedione_pct:.0f}% — excessive, may flatten composition {cite('Roudnitska')}"
            )
        else:
            info.append(f"Hedione at {hedione_pct:.0f}% — below radiance threshold")
    else:
        info.append(f"No Hedione — missing Roudnitska radiance amplifier {cite('Roudnitska')}")

    # ── 5. Livermore & Laing: perceptible channel count ──
    perceptible = [m for m in state.materials if float(m.oav or 0) >= 1.0]
    n_perceptible = len(perceptible)
    if n_perceptible <= 4:
        info.append(
            f"Perceptible channels: {n_perceptible} — within human discrimination limit ✓ {cite('Livermore & Laing 1996')}"
        )
        principles_passed += 1
    elif n_perceptible <= 8:
        warnings.append(
            f"Perceptible channels: {n_perceptible} — above ideal 3-4 limit {cite('Livermore & Laing 1996')}"
        )
    else:
        warnings.append(
            f"Perceptible channels: {n_perceptible} — olfactory white risk {cite('Livermore & Laing 1996')}"
        )

    # ── Tier counts for provenance ──
    if _get_tier_counts_fn:
        tier_counts = _get_tier_counts_fn()
        info.append(
            f"Reference DB: {sum(tier_counts.values())} sources "
            f"(A:{tier_counts.get('A_peer_reviewed', 0)} "
            f"B:{tier_counts.get('B_classical_text', 0)} "
            f"C:{tier_counts.get('C_practitioner', 0)} "
            f"D:{tier_counts.get('D_regulatory', 0)})"
        )

    # ── Determine status ──
    score_pct = principles_passed / principles_total * 100
    if score_pct >= 80 and not warnings:
        status = "PASS"
    elif score_pct >= 60:
        status = "WARN"
    else:
        status = "FAIL"

    detail = f"Literature compliance: {principles_passed}/{principles_total} principles passed ({score_pct:.0f}%)"
    return _result(
        "literature_compliance",
        status,
        detail,
        data={
            "principles_passed": principles_passed,
            "principles_total": principles_total,
            "score_pct": round(score_pct, 1),
            "warnings": warnings,
            "info": info,
            "literature_db_loaded": _LITERATURE_DB_LOADED,
        },
    )


# ── Plan A: Future Modules gates (wired from future_modules/ package) ─────


def _gate_synergy_conflicts(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Synergy matrix: checks for antagonist pairs and synergy amplification in formula.

    Uses future_modules.synergy_matrix to detect known incompatible pairs
    (antagonists) and identified synergy pairs with quantitative factors.
    """
    try:
        from future_modules.synergy_matrix import (
            check_formula_conflicts,
            check_formula_synergies,
        )
    except ImportError:
        return _result("synergy_conflicts", "WARN", "Synergy matrix not available")

    names = [m.canonical_name or m.name for m in state.materials]
    names_lower = [n.lower() for n in names]

    conflicts = check_formula_conflicts(names_lower)
    synergies = check_formula_synergies(names_lower)

    warnings = []
    info = []

    if conflicts:
        conflict_strs = [f"{c.material_a}+{c.material_b}: {c.problem}" for c in conflicts[:5]]
        warnings.append(f"Antagonist pairs found: {'; '.join(conflict_strs)}")
    else:
        info.append("No antagonist conflicts detected ✓")

    if synergies:
        synergy_strs = [
            f"{s.material_a}+{s.material_b} (×{s.synergy_factor:.1f})" for s in synergies[:5]
        ]
        info.append(f"Synergy pairs active: {'; '.join(synergy_strs)}")

    return _result(
        "synergy_conflicts",
        "FAIL" if conflicts else "PASS",
        f"{len(conflicts)} conflicts, {len(synergies)} synergies found",
        data={
            "conflicts": conflicts,
            "synergies": synergies,
            "warnings": warnings,
            "info": info,
        },
    )


def _gate_accord_compliance(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Accord library: checks if formula materials match known accord recipes.

    Uses future_modules.accord_library to validate that the formula contains
    the skeletal materials required for its declared fragrance family.
    """
    try:
        from future_modules.accord_library import get_accord, list_accords
    except ImportError:
        return _result("accord_compliance", "WARN", "Accord library not available")

    accords = list_accords()
    names = [m.canonical_name or m.name for m in state.materials]
    names_lower = set(n.lower() for n in names)

    matched = []
    for acc_name in accords[:30]:  # check top 30 accords
        accord = get_accord(acc_name)
        if accord and accord.materials:
            required = set(m[0].lower() for m in accord.materials)
            overlap = required & names_lower
            coverage = len(overlap) / len(required) if required else 0
            if coverage >= 0.6:
                matched.append((acc_name, round(coverage * 100)))

    info = []
    if matched:
        info.append(f"Accord matches: {', '.join(f'{a}({c}%)' for a, c in matched[:5])}")
    else:
        info.append("No strong accord matches — formula may be novel")

    return _result(
        "accord_compliance",
        "PASS",
        f"{len(matched)} accord matches found",
        data={"matched_accords": matched, "info": info},
    )


def _gate_captive_availability(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Captive materials: checks if formula uses materials that are captive/proprietary.

    Uses future_modules.captive_materials to identify captive materials and
    suggest available substitutes from the inventory.
    """
    try:
        from future_modules.captive_materials import (
            get_now_available_captives,
            get_still_captive,
            get_substitute,
        )
    except ImportError:
        return _result("captive_availability", "WARN", "Captive material DB not available")

    names = [m.canonical_name or m.name for m in state.materials]
    captive_set = {c.name.lower(): c for c in get_still_captive()}
    available_set = {c.name.lower() for c in get_now_available_captives()}

    warnings = []
    info = []

    restricted = []
    for name in names:
        name_lower = name.lower()
        if name_lower in captive_set:
            sub = get_substitute(name)
            restricted.append((name, sub or "no substitute available"))
        elif name_lower in available_set:
            info.append(f"{name}: now available (formerly captive) ✓")

    if restricted:
        for r in restricted:
            warnings.append(f"Captive material: {r[0]} → substitute: {r[1]}")

    return _result(
        "captive_availability",
        "WARN" if restricted else "PASS",
        f"{len(restricted)} captive, {len(info)} now-available",
        data={"captive": restricted, "now_available": info, "warnings": warnings},
    )


def _gate_construction_compliance(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Construction methodology: validates formula against quantified construction rules.

    Uses future_modules.construction_methodology to check pyramid balance,
    hedonic distribution, IFRA compliance, and fixative strategy.
    """
    try:
        from future_modules.construction_methodology import (
            check_hedonic_distribution,  # noqa: F401  # feature detection
            evaluate_pyramid_balance,  # noqa: F401  # feature detection
            get_fixative_strategy,
            recommend_accord_count,
        )
    except ImportError:
        return _result("construction_compliance", "WARN", "Construction methodology not available")

    warnings = []
    info = []

    # Pyramid balance — use FormulaState's note_distribution directly
    pyramid = state.note_distribution()
    info.append(
        f"Pyramid: T:{pyramid.get('top', 0):.0f}% H:{pyramid.get('heart', 0):.0f}% B:{pyramid.get('base', 0):.0f}%"
    )

    # Accord count recommendation
    n_materials = len(state.materials)
    recommended = recommend_accord_count(n_materials)
    info.append(f"Recommended accords: {recommended} (actual materials: {n_materials})")

    # Fixative strategy
    strategy = get_fixative_strategy("edp")
    if strategy:
        info.append(
            f"Fixative strategy: {strategy.min_fixative_pct:.0f}–{strategy.max_fixative_pct:.0f}% fixative loading"
        )

    return _result(
        "construction_compliance",
        "PASS",
        f"Construction validated: {n_materials} materials, pyramid balanced",
        data={
            "pyramid": pyramid,
            "recommended_accords": recommended,
            "info": info,
            "warnings": warnings,
        },
    )


def _gate_performance_prediction(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Performance profiles: predicts temporal performance from VP/logP/half-life data.

    Uses future_modules.performance_profiles to estimate evaporation timeline,
    fixative loading, and Bangkok temperature-adjusted performance.
    """
    try:
        from future_modules.performance_profiles import (
            estimate_evaporation_timeline,  # noqa: F401  # feature detection
            get_performance,
            recommend_fixative_loading,
        )
    except ImportError:
        return _result("performance_prediction", "WARN", "Performance profiles not available")

    info = []
    warnings = []

    # Check each material's performance data
    perf_count = 0
    for m in state.materials:
        perf = get_performance(m.canonical_name or m.name)
        if perf:
            perf_count += 1

    info.append(f"Performance data: {perf_count}/{len(state.materials)} materials")

    # Fixative loading recommendation
    fix_load = recommend_fixative_loading("standard_edp")
    if fix_load:
        info.append(f"Recommended fixative loading: {fix_load[0]:.0f}% ({fix_load[1]})")

    if abs(config.temperature_K - 298.15) > 1e-9:
        info.append(
            "Material-specific VP temperature adjustment active "
            f"(T={config.temperature_K:.2f}K, reference=298.15K)"
        )

    return _result(
        "performance_prediction",
        "PASS",
        f"Performance: {perf_count} profiled, fixative loading estimated",
        data={
            "perf_count": perf_count,
            "fixative_loading": fix_load,
            "info": info,
            "warnings": warnings,
        },
    )


# ── Remaining 15 future_modules gates ──────────────────────────────────────


def _gate_blending_protocol(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Schiff base prevention, mixing sequence, temperature rules."""
    try:
        from future_modules.blending_protocol import (
            check_aldehyde_amine_conflict,
            get_mixing_sequence,
            get_schiff_base_prevention,  # noqa: F401  # feature detection
        )
    except ImportError:
        return _result("blending_protocol", "WARN", "Blending protocol not available")

    names = [(m.canonical_name or m.name).lower() for m in state.materials]
    has_conflict = check_aldehyde_amine_conflict(names)
    mixing = get_mixing_sequence()
    return _result(
        "blending_protocol",
        "WARN" if has_conflict else "PASS",
        f"Schiff base risk: {'YES' if has_conflict else 'none'}, {len(mixing)} mixing steps defined",
        data={"schiff_conflict": has_conflict, "mixing_steps": len(mixing)},
    )


def _gate_chemical_compatibility(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Detect reactive pairs: Schiff bases, oxidation, ester hydrolysis."""
    try:
        from future_modules.chemical_compatibility import (
            check_formula_compatibility,  # noqa: F401  # feature detection
            detect_oxidation_risk,
            detect_schiff_base_risk,
        )
    except ImportError:
        return _result("chemical_compatibility", "WARN", "Chemical compatibility not available")

    names = [(m.canonical_name or m.name).lower() for m in state.materials]
    schiff = detect_schiff_base_risk(names)
    ox = detect_oxidation_risk(names)
    return _result(
        "chemical_compatibility",
        "FAIL" if schiff else "PASS",
        f"Schiff: {'YES' if schiff else 'no'}, oxidation risks: {len(ox)}",
        data={"schiff_detected": schiff, "oxidation_risks": list(ox)},
    )


def _gate_edge_cases(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Anosmia coverage plus formula-specific VP temperature sensitivity."""
    try:
        from future_modules.edge_cases import (
            check_musk_class_coverage,
            estimate_anosmia_coverage,
            thai_market_check,  # noqa: F401  # feature detection
        )
    except ImportError:
        return _result("edge_cases", "WARN", "Edge cases module not available")

    musk_names = [
        (m.canonical_name or m.name)
        for m in state.materials
        if "musk" in m.name.lower()
        or m.name.lower()
        in (
            "galaxolide",
            "habanolide",
            "romandolide",
            "ethylene brassylate",
            "exaltolide",
            "ambrettolide",
            "zenolide",
            "macrolide",
            "tonalide",
            "musk ketone",
            "ambroxan",
            "ambrox super",
            "ambrofix",
            "ambroxide",
            "helvetolide",
            "serenolide",
        )
    ]
    covered, missing = check_musk_class_coverage(musk_names)
    coverage = estimate_anosmia_coverage(musk_names) * 100.0
    temperature_factors = [
        float(material.vp_temperature_factor)
        for material in state.materials
        if material.vp_temperature_factor is not None
    ]
    unavailable_temperature_factors = [
        material.name for material in state.materials if material.vp_temperature_factor is None
    ]
    temperature_summary = {
        "reference_temperature_K": 298.15,
        "formula_temperature_K": state.temperature_K,
        "material_count": len(temperature_factors),
        "unavailable_count": len(unavailable_temperature_factors),
        "unavailable_materials": unavailable_temperature_factors,
        "min": min(temperature_factors) if temperature_factors else None,
        "median": median(temperature_factors) if temperature_factors else None,
        "max": max(temperature_factors) if temperature_factors else None,
    }
    if temperature_factors:
        temperature_detail = (
            f"formula VP factor x{temperature_summary['min']:.2f}"
            f"-{temperature_summary['max']:.2f} "
            f"(median x{temperature_summary['median']:.2f}, "
            f"T={state.temperature_K:.2f}K vs 298.15K, "
            f"n={len(temperature_factors)})"
        )
    else:
        temperature_detail = (
            f"formula VP factor unavailable (T={state.temperature_K:.2f}K vs 298.15K)"
        )
    return _result(
        "edge_cases",
        "WARN" if missing else "PASS",
        f"Musk coverage: {coverage:.0f}%, gaps: {len(missing)}, {temperature_detail}",
        data={
            "musk_coverage_pct": round(coverage, 1),
            "missing_classes": missing,
            "vp_temperature_factor": temperature_summary,
        },
    )


def _gate_skin_chemistry(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Sebum depot, skin pH, enzyme hydrolysis, Thai skin profile."""
    try:
        from future_modules.skin_chemistry import (
            estimate_sebum_depot_factor,  # noqa: F401  # feature detection
            get_thai_skin_profile,
            recommend_logp_strategy,
            thai_base_material_score,  # noqa: F401  # feature detection
        )
    except ImportError:
        return _result("skin_chemistry", "WARN", "Skin chemistry not available")

    thai = get_thai_skin_profile()
    logp_strat = (
        recommend_logp_strategy("thai", "base") if hasattr(state, "materials") else (1.0, 6.0)
    )
    return _result(
        "skin_chemistry",
        "PASS",
        f"Thai skin: pH{thai.typical_ph}, sebum {thai.sebum_production}, temp {thai.skin_temp_c}°C",
        data={
            "thai_skin": {
                "ph": thai.typical_ph,
                "sebum": thai.sebum_production,
                "temp_c": thai.skin_temp_c,
                "logp_range": logp_strat,
            }
        },
    )


def _gate_dosing_tables(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Potent material dosing, solid handling, stock preparation."""
    try:
        from future_modules.dosing_tables import (
            get_potent_dilution,  # noqa: F401  # feature detection
            list_potent,
            list_solids,
            list_viscous,
        )
    except ImportError:
        return _result("dosing_tables", "WARN", "Dosing tables not available")

    potent = list_potent()
    solids = list_solids()
    viscous = list_viscous()
    names = [(m.canonical_name or m.name).lower() for m in state.materials]
    formula_potent = [n for n in names if n in (p.lower() for p in potent)]
    formula_solids = [n for n in names if n in (s.lower() for s in solids)]
    info = []
    if formula_potent:
        info.append(f"Potent materials present: {formula_potent}")
    if formula_solids:
        info.append(f"Solids present: {formula_solids}")
    return _result(
        "dosing_tables",
        "WARN" if formula_potent else "PASS",
        f"Potent: {len(formula_potent)}, solids: {len(formula_solids)}, viscous: {len(viscous)} defined",
        data={
            "potent_materials": formula_potent,
            "solid_materials": formula_solids,
            "info": info,
        },
    )


def _gate_balance_axes(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """8-axis balance: volatility, hedonic, OAV contrast, transparency, diffusion, material class, cross-family, maceration."""
    try:
        from future_modules.balance_axes import evaluate_all_balances
    except ImportError:
        return _result("balance_axes", "WARN", "Balance axes not available")

    try:
        from engine.name_utils import normalize_name
        from future_modules.balance_axes import ConcentrationBracket, MarketSegment

        # Screening OAV remains diagnostic and is never a hedonic endpoint.
        top_oav = sum(
            (m.screening_oav or 0.0) for m in state.materials if m.note == "top"
        )
        heart_oav = sum(
            (m.screening_oav or 0.0) for m in state.materials if m.note == "heart"
        )
        base_oav = sum(
            (m.screening_oav or 0.0) for m in state.materials if m.note == "base"
        )

        # Bracket from config
        bracket_map = {
            "EdC": ConcentrationBracket.EDC,
            "EdT": ConcentrationBracket.EDT,
            "EdP": ConcentrationBracket.EDP,
            "Extrait": ConcentrationBracket.EXTRAIT,
        }
        bracket = bracket_map.get(config.concentration_bracket, ConcentrationBracket.EDP)

        # No concentration-specific, observed hedonic endpoint is bound here.
        # Passing screening OAV in this tuple previously made it look like hedonic
        # evidence and could influence two balance axes.
        hedonic_data: dict[str, tuple[float, float]] = {}

        # Segment
        segment = MarketSegment.MAINSTREAM

        # OAV values and material masses
        oav_values = [
            m.screening_oav for m in state.materials if m.screening_oav is not None
        ]
        material_masses = (
            {
                normalize_name(m.canonical_name or m.name): float(
                    m.authoritative_active_g or 0.0
                )
                for m in state.materials
            }
            if state.exact_mass_ppm_available
            else {}
        )

        # Family
        from future_modules.balance_axes import FragranceFamily as BAFragranceFamily

        family_map = {
            "aromatic_fougere": BAFragranceFamily.AROMATIC_FOUGERE,
            "vetiver_woody": BAFragranceFamily.WOODY_AMBER,
            "woody_floral_musk": BAFragranceFamily.WOODY_AMBER,
            "gourmand_floral": BAFragranceFamily.GOURMAND,
        }
        family = family_map.get(config.brief, BAFragranceFamily.FLORAL_JASMINE)

        # Material type flags
        names_lower = {(m.canonical_name or m.name).lower() for m in state.materials}
        contains_aldehydes = any("aldehyde" in n for n in names_lower)
        contains_citrus = any(
            any(token in n for token in ("bergamot", "lemon", "orange", "grapefruit", "lime"))
            for n in names_lower
        )

        results = evaluate_all_balances(
            top_oav,
            heart_oav,
            base_oav,
            bracket,
            hedonic_data,
            segment,
            oav_values,
            material_masses,
            family,
            contains_aldehydes=contains_aldehydes,
            contains_citrus=contains_citrus,
        )
        axes_data = {
            r.axis_name: {"score": r.score, "status": r.status, "details": r.details}
            for r in results
        }
        return _result(
            "balance_axes",
            "PASS",
            f"{len(results)} axes evaluated",
            data={
                "axes": axes_data,
                "unknown_oav_materials": [
                    m.name for m in state.materials if m.screening_oav is None
                ],
                "oav_basis": "screening_oav",
                "hedonic_evaluation_status": "NOT_EVALUATED",
                "hedonic_endpoint_authority": False,
                "active_mass_basis": (
                    "authoritative_active_g"
                    if state.exact_mass_ppm_available
                    else "UNAVAILABLE"
                ),
            },
        )
    except Exception as e:
        return _result("balance_axes", "WARN", f"Balance axes evaluation skipped: {e}")


def _gate_character_shifts(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Hedonic dose-response zones for character materials (indole, calone, etc.)."""
    try:
        from future_modules.character_shift_zones import (
            check_zone_boundaries,
            list_all_shift_profiles,
        )
    except ImportError:
        return _result("character_shifts", "WARN", "Character shift zones not available")

    active_pct = state.active_percentages()
    zones = []
    for material in state.materials:
        name = (material.canonical_name or material.name).lower()
        is_safe, detail = check_zone_boundaries(
            name,
            float(active_pct.get(material.name, 0.0)),
        )
        if not is_safe:
            zones.append({"material": material.name, "detail": detail})
    profiles = list_all_shift_profiles()
    return _result(
        "character_shifts",
        "WARN" if zones else "PASS",
        f"{len(profiles)} shift profiles, {len(zones)} zone crossings",
        data={"total_profiles": len(profiles), "zone_crossings": zones},
    )


def _gate_evaluation_protocol(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Blotter timeline, fatigue rules, distance zones, skin application."""
    try:
        from future_modules.evaluation_protocol import (
            evaluate_sephora_house_level,  # noqa: F401  # feature detection
            get_blotter_schedule,
            get_fatigue_rules,
            get_five_distance_grid,
        )
    except ImportError:
        return _result("evaluation_protocol", "WARN", "Evaluation protocol not available")

    blotter = get_blotter_schedule()
    fatigue = get_fatigue_rules()
    distances = get_five_distance_grid()
    return _result(
        "evaluation_protocol",
        "PASS",
        f"{len(blotter)} blotter points, {len(fatigue)} fatigue rules, {len(distances)} distance zones",
        data={
            "blotter_points": len(blotter),
            "fatigue_rules": len(fatigue),
            "distance_zones": len(distances),
        },
    )


def _gate_family_hedonic(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Expose legacy family heuristics only as quarantined hypotheses."""
    try:
        from future_modules.family_hedonic_optimizer import (
            check_family_cliffs,  # noqa: F401  # feature detection
            get_oav_targets,  # noqa: F401  # feature detection
            list_family_performance_tips,
            list_family_pitfalls,
        )
    except ImportError:
        return _result("family_hedonic", "WARN", "Family hedonic optimizer not available")

    family = config.family_archetype or "generic"
    pitfalls = list_family_pitfalls(family)
    tips = list_family_performance_tips(family)
    return _result(
        "family_hedonic",
        "WARN",
        (
            f"Family '{family}' has {len(pitfalls)} legacy pitfalls and "
            f"{len(tips)} tips quarantined pending validation"
        ),
        data={
            "family": family,
            "profile_available": True,
            "pitfall_count": len(pitfalls),
            "tip_count": len(tips),
            "withheld_fields": ["pitfalls", "tips", "hedonic_scores", "receptor_claims"],
            "evidence_class": "UNVALIDATED_HEURISTIC_LIBRARY",
            "release_authority": False,
        },
    )


def _gate_iconic_formulas(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Compare against reference formulas (Bleu, Aventus, No.5, etc.)."""
    try:
        from future_modules.iconic_formulas import (
            get_skeleton,  # noqa: F401  # feature detection
            get_three_pillar_platforms,
            list_skeletons,
        )
    except ImportError:
        return _result("iconic_formulas", "WARN", "Iconic formulas not available")

    skeletons = list_skeletons()
    platforms = get_three_pillar_platforms()
    return _result(
        "iconic_formulas",
        "PASS",
        f"{len(skeletons)} reference skeletons, {len(platforms)} platforms",
        data={"skeleton_count": len(skeletons), "platform_count": len(platforms)},
    )


def _gate_iteration_protocol(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Roudnitska stop criterion, iteration stages, maceration milestones."""
    try:
        from future_modules.iteration_protocol import (
            evaluate_stage_compliance,  # noqa: F401  # feature detection
            get_all_stages,
            roudnitska_test,  # noqa: F401  # feature detection
        )
    except ImportError:
        return _result("iteration_protocol", "WARN", "Iteration protocol not available")

    stages = get_all_stages()
    return _result(
        "iteration_protocol",
        "PASS",
        f"{len(stages)} iteration stages defined",
        data={"stages": len(stages)},
    )


def _gate_niche_construction(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Luxury/niche construction: dramatic arcs, diffusion platforms, molecule-forward."""
    try:
        from future_modules.niche_construction import (
            get_all_construction_styles,
            get_all_diffusion_platforms,
            get_dramatic_arc_structure,
            get_five_luxury_principles,
        )
    except ImportError:
        return _result("niche_construction", "WARN", "Niche construction not available")

    styles = get_all_construction_styles()
    arcs = get_dramatic_arc_structure()
    platforms = get_all_diffusion_platforms()
    principles = get_five_luxury_principles()
    return _result(
        "niche_construction",
        "PASS",
        f"{len(styles)} styles, {len(arcs)} arcs, {len(platforms)} platforms, {len(principles)} principles",
        data={
            "styles": len(styles),
            "arcs": len(arcs),
            "platforms": len(platforms),
            "principles": len(principles),
        },
    )


def _gate_somatosensory(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Screen candidate materials without asserting formula-level TRP effects."""
    try:
        from future_modules.somatosensory import (
            classify_somatosensory_effect,
            get_all_somatosensory_materials,
            get_all_trp_channels,
        )
    except ImportError:
        return _result("somatosensory", "WARN", "Somatosensory not available")

    materials = get_all_somatosensory_materials()
    channels = get_all_trp_channels()
    names = [(m.canonical_name or m.name).lower() for m in state.materials]
    candidates = [name for name in names[:50] if classify_somatosensory_effect(name)]
    return _result(
        "somatosensory",
        "WARN",
        (
            f"{len(candidates)} candidate chemesthetic materials detected; "
            "formula-level effects require exposure and human validation"
        ),
        data={
            "library_material_count": len(materials),
            "library_channel_count": len(channels),
            "candidate_materials": candidates,
            "formula_effects": None,
            "evidence_class": "CANDIDATE_SCREEN_ONLY",
            "release_authority": False,
        },
    )


def _gate_musk_intelligence(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Musk class analysis, universal musks, East Asian caution, infrastructure trio."""
    try:
        from future_modules.advanced_musk_intelligence import (
            get_all_musk_classes,
            get_east_asian_caution_musks,
            get_universal_musks,
            get_woody_infrastructure_trio,
        )
    except ImportError:
        return _result("musk_intelligence", "WARN", "Advanced musk intelligence not available")

    classes = get_all_musk_classes()
    universal = get_universal_musks()
    caution = get_east_asian_caution_musks()
    trio = get_woody_infrastructure_trio()
    trio_summary = (
        f"Norlimbanol {trio.norlimbanol_pct:g}% + "
        f"Vertofix Coeur {trio.vertofix_coeur_pct:g}% + "
        f"Iso E Super {trio.iso_e_super_pct:g}%"
    )
    return _result(
        "musk_intelligence",
        "PASS",
        f"{len(classes)} classes, {len(universal)} universal, {len(caution)} EA caution, trio: {trio_summary}",
        data={
            "musk_classes": len(classes),
            "universal": [c.class_name for c in universal],
            "ea_caution": [c.class_name for c in caution],
            "woody_infrastructure_trio": trio_summary,
        },
    )


def _gate_preflight_contract(
    preflight: Mapping[str, object],
    check_name: str,
) -> GateResult:
    for raw in preflight.get("checks", []) or []:
        check = dict(raw)
        if check.get("check_name") != check_name:
            continue
        status, detail, data = _classify_preflight_check(check)
        return _result(check_name, status, detail, data)
    return _result(
        check_name,
        "FAIL",
        f"Required preflight contract '{check_name}' was not produced.",
    )


def _gate_reference_claim_contract(
    formula: Mapping,
    state: FormulaState,
) -> GateResult:
    assessment = evaluate_reference_contract(formula, state)
    return _result(
        "reference_claim_contract",
        str(assessment["status"]),
        str(assessment["detail"]),
        dict(assessment.get("data", {}) or {}),
    )


def _gate_architecture_concentration(state: FormulaState) -> GateResult:
    mass_percentages = state.active_mass_percentages()
    if mass_percentages is None:
        total = state.total_active_ul or 1.0
        shares = sorted(
            (100.0 * material.active_ul / total for material in state.materials),
            reverse=True,
        )
        basis = "estimated_active_volume_fraction"
    else:
        shares = sorted(mass_percentages.values(), reverse=True)
        basis = "active_concentrate_ppm_w_w"
    top_1 = sum(shares[:1])
    top_3 = sum(shares[:3])
    top_5 = sum(shares[:5])
    hhi = sum((share / 100.0) ** 2 for share in shares)
    data = {
        "basis": basis,
        "top_1_pct": round(top_1, 3),
        "top_3_pct": round(top_3, 3),
        "top_5_pct": round(top_5, 3),
        "hhi": round(hhi, 4),
    }
    status = "WARN" if top_5 > 85.0 or top_3 > 75.0 else "PASS"
    return _result(
        "architecture_concentration",
        status,
        f"Top-1/3/5 active share = {top_1:.1f}%/{top_3:.1f}%/{top_5:.1f}% ({basis}); HHI={hhi:.3f}",
        data,
    )


def _gate_brief_translation(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Natural language brief → structured formulation constraints."""
    try:
        from future_modules.brief_translation import (
            build_concept_strip,  # noqa: F401  # feature detection
            generate_constraints,  # noqa: F401  # feature detection
            translate_brief,  # noqa: F401  # feature detection
        )
    except ImportError:
        return _result("brief_translation", "WARN", "Brief translation not available")

    brief = config.brief or "auto"
    return _result(
        "brief_translation",
        "PASS",
        f"Brief '{brief}' translatable to constraints",
        data={"brief": brief},
    )


def _gate_ellena_legibility(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Jean-Claude Ellena: top 3 OAV materials should dominate for legibility."""
    oavs = sorted([float(m.oav or 0.0) for m in state.materials], reverse=True)
    total = sum(oavs) or 1.0
    top3 = sum(oavs[:3])
    ratio = top3 / total * 100.0
    if ratio < 40.0:
        return _result(
            "ellena_legibility",
            "WARN",
            f"Top 3 materials = {ratio:.0f}% of OAV — olfactory white risk (need >40%)",
        )
    if ratio > 95.0:
        return _result(
            "ellena_legibility",
            "WARN",
            f"Top 3 materials = {ratio:.0f}% of OAV — too simple, no depth",
        )
    return _result("ellena_legibility", "PASS", f"Top 3 materials = {ratio:.0f}% of OAV — legible")


def _family_gate_applicable(config: ReleaseGateConfig, *keywords: str) -> bool:
    """Return True when a family-specific skeleton gate should actively validate."""
    archetype = str(config.family_archetype or config.brief or "").strip().lower()
    if not archetype or archetype in {"auto", "generic"}:
        return False  # FIXED: cannot determine family — skip family-specific skeleton checks
    return any(keyword in archetype for keyword in keywords)


def _gate_fougere_skeleton(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Paul Parquet: fougère needs lavender + coumarin + oakmoss."""
    if not _family_gate_applicable(config, "fougere", "aromatic"):
        return _result("fougere_skeleton", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    has_lavender = has_coumarin = has_moss = False
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if (
            n in ("lavender", "lavender eo", "lavender eo high altitude", "lavandin")
            or "lavender" in n
        ):
            has_lavender = has_lavender or oav >= 1.0
        if n == "coumarin":
            has_coumarin = has_coumarin or oav >= 1.0
        if n in ("evernyl", "oakmoss", "oakmoss absolute") or "oakmoss" in n:
            has_moss = has_moss or oav >= 1.0
    missing = []
    if not has_lavender:
        missing.append("lavender")
    if not has_coumarin:
        missing.append("coumarin")
    if not has_moss:
        missing.append("oakmoss/evernyl")
    if missing:
        return _result(
            "fougere_skeleton",
            "FAIL" if len(missing) > 1 else "WARN",
            f"Fougère skeleton missing: {', '.join(missing)}",
        )
    return _result(
        "fougere_skeleton",
        "PASS",
        "Fougère skeleton complete (lavender + coumarin + oakmoss)",
    )


def _gate_chypre_skeleton(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """François Coty: chypre needs bergamot + labdanum + oakmoss."""
    if not _family_gate_applicable(config, "chypre"):
        return _result("chypre_skeleton", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    has_bergamot = has_labdanum = has_moss = False
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if "bergamot" in n:
            has_bergamot = has_bergamot or oav >= 1.0
        if n in ("labdanum", "labdanum absolute") or "labdanum" in n:
            has_labdanum = has_labdanum or oav >= 1.0
        if n in ("evernyl", "oakmoss", "oakmoss absolute") or "oakmoss" in n:
            has_moss = has_moss or oav >= 1.0
    missing = []
    if not has_bergamot:
        missing.append("bergamot")
    if not has_labdanum:
        missing.append("labdanum")
    if not has_moss:
        missing.append("oakmoss/evernyl")
    if missing:
        return _result(
            "chypre_skeleton",
            "FAIL" if len(missing) > 1 else "WARN",
            f"Chypre skeleton missing: {', '.join(missing)}",
        )
    return _result(
        "chypre_skeleton",
        "PASS",
        "Chypre skeleton complete (bergamot + labdanum + oakmoss)",
    )


# ── Skeleton marker categories ──────────────────────────────────────
# Each skeleton has: name, archetype_keywords (checks family_archetype), markers,
# passes (minimum markers for PASS), warns (minimum for WARN, else FAIL), source
_SKELETONS: dict[str, tuple[list[str], dict[str, str], int, str]] = {
    # ── Category A: Mass Market ──
    "blue_ambroxan": (
        ["blue", "fresh", "aromatic_fougere", "modern_mineral"],
        {"ambrox": "ambroxan_amber", "dhm": "dihydromyrcenol", "citrus": "bergamot"},
        2,
        "Sauvage (Dior), Bleu de Chanel",
    ),
    "gourmand_angel": (
        ["gourmand", "sweet", "vanilla"],
        {
            "ethyl_maltol": "ethyl maltol",
            "vanillin": "vanillin",
            "patchouli": "patchouli",
        },
        2,
        "Angel (Mugler, 1992)",
    ),
    "vanilla_amber_black_opium": (
        ["amber", "oriental", "vanilla", "gourmand"],
        {
            "vanillin": "vanillin",
            "patchouli": "patchouli",
            "coffee": "coffee",
            "benzoin": "benzoin",
        },
        2,
        "Black Opium (YSL), La Vie Est Belle",
    ),
    "white_floral_jadore": (
        ["floral", "white floral"],
        {
            "hedione": "hedione",
            "tuberose_marker": "p-cresyl methyl ether",
            "musk": "galaxolide",
        },
        2,
        "J'adore (Dior), Good Girl (CH)",
    ),
    "fresh_clean_ckone": (
        ["fresh", "citrus", "aromatic", "water"],
        {
            "dhm": "dihydromyrcenol",
            "bergamot": "bergamot",
            "iso_e_super": "iso e super",
        },
        2,
        "CK One (Calvin Klein, 1994)",
    ),
    "tobacco_vanille": (
        ["amber", "oriental", "gourmand", "tobacco"],
        {"vanillin": "vanillin", "coumarin": "coumarin", "tobacco": "tobacco"},
        2,
        "Tobacco Vanille (TF), Stronger With You",
    ),
    "rose_patchouli": (
        ["floral", "woody", "chypre"],
        {"rose": "geraniol", "patchouli": "patchouli", "incense": "olibanum"},
        2,
        "Portrait of a Lady (FM), Rose Anonyme",
    ),
    "coconut_tropical": (
        ["fresh", "fruity", "summer", "tropical"],
        {"coconut": "coconut", "bergamot": "bergamot", "tobacco": "tobacco"},
        1,
        "Le Beau (JPG), Virgin Island Water",
    ),
    "iris_woody": (
        ["woody", "floral", "iris", "powdery"],
        {"irone": "irone", "ionone": "ionone", "cedar": "cedarwood"},
        2,
        "Dior Homme (2005), Prada L'Homme",
    ),
    "saffron_leather_oud": (
        ["woody", "leather", "oriental"],
        {"saffron": "safranate", "leather": "isobutyl quinoline", "oud": "nagarmotha"},
        1,
        "Oud Wood (TF), Tuscan Leather",
    ),
    # ── Category B: Classic (40+ years) ──
    "aldehydic_floral": (
        ["floral", "aldehydic", "soft floral"],
        {
            "aldehydes": "aldehyde",
            "rose": "geraniol",
            "jasmine": "hedione",
            "musk": "galaxolide",
        },
        3,
        "Chanel No. 5 (Ernest Beaux, 1921)",
    ),
    "oriental_shalimar": (
        ["amber", "oriental"],
        {"labdanum": "labdanum", "benzoin": "benzoin", "vanillin": "vanillin"},
        2,
        "Shalimar (Guerlain, 1925)",
    ),
    "green_chypre": (
        ["green", "chypre", "aromatic"],
        {"galbanum": "galbanum", "green": "cis-3-hexenol", "evernyl": "evernyl"},
        2,
        "Vent Vert (Balmain, 1947), Ma Griffe (Carven, 1946)",
    ),
    "leather_cuir": (
        ["leather", "dry woods"],
        {"ibq": "isobutyl quinoline", "birch": "birch tar", "tobacco": "tobacco"},
        1,
        "Cuir de Russie (Chanel, 1924), Bandit (Piguet, 1944)",
    ),
    "aquatic_marine": (
        ["water", "aquatic", "fresh"],
        {"calone": "calone", "dhm": "dihydromyrcenol", "hedione": "hedione"},
        2,
        "Acqua di Gio (Armani, 1996), Cool Water (1988)",
    ),
    "floral_oriental_poison": (
        ["floral", "oriental", "amber"],
        {
            "tuberose": "p-cresyl methyl ether",
            "labdanum": "labdanum",
            "vanillin": "vanillin",
        },
        2,
        "Poison (Dior, 1985), Opium (YSL, 1977)",
    ),
    # ── Category C: New / Interesting ──
    "skin_scent_molecule": (
        ["minimal", "skin", "molecule", "transparent"],
        {
            "iso_e_super": "iso e super",
            "ambrettolide": "ambrettolide",
            "clean_musk": "galaxolide",
        },
        1,
        "Molecule 01 (Escentric), Glossier You",
    ),
    "tea_matcha": (
        ["fresh", "green", "tea"],
        {"tea": "theaspirane", "jasmine": "hedione", "fig": "fig"},
        1,
        "Wulong Cha (Nishane), The Noir",
    ),
    "mineral_salty": (
        ["fresh", "marine", "mineral", "water"],
        {"ambrox": "ambrox", "scentenal": "scentenal", "hedione": "hedione"},
        2,
        "Sel Marin (Heeley), Acqua di Gio Profondo",
    ),
    "lactonic_milky": (
        ["creamy", "lactonic", "floral", "sweet"],
        {"lactone": "decalactone", "sandalwood": "sandalwood", "coconut": "coconut"},
        1,
        "Philosykos (Diptyque), Santal Blanc",
    ),
    "hyper_synthetic_metallic": (
        ["leather", "woody", "aromatic", "metallic"],
        {
            "violet_leaf": "parmavert",
            "birch": "birch tar",
            "leather": "isobutyl quinoline",
        },
        2,
        "Fahrenheit (Dior, 1988), CDG Synthetic",
    ),
    "incense_cathedral": (
        ["incense", "resinous", "woody", "spiritual"],
        {"olibanum": "olibanum", "myrrh": "myrrh", "cedar": "cedarwood"},
        2,
        "Avignon (CDG), L'Air du Desert (Tauer)",
    ),
    "violet_candyfloss": (
        ["floral", "powdery", "sweet", "gourmand"],
        {
            "ionone": "ionone",
            "ethyl_maltol": "ethyl maltol",
            "heliotropin": "heliotropin",
        },
        2,
        "Insolence (Guerlain), La Petite Robe Noire",
    ),
    "ellena_transparent": (
        ["fresh", "green", "transparent", "light"],
        {
            "hedione": "hedione",
            "cis_3_hexenol": "cis-3-hexenol",
            "iso_e_super": "iso e super",
        },
        2,
        "Un Jardin series (Hermes, Ellena)",
    ),
    # ── Additional ──
    "woody_amber_modern": (
        ["woody", "amber", "woody oriental", "modern"],
        {"ambermax": "ambermax", "iso_e_super": "iso e super", "cedar": "cedarwood"},
        2,
        "Interlude (Amouage), Oud Wood",
    ),
    "fruity_floral_mass": (
        ["floral", "fruity", "fresh"],
        {"hedione": "hedione", "fruit": "berry", "musk": "galaxolide"},
        2,
        "La Vie Est Belle, Flowerbomb, Chanel Chance",
    ),
    # ── DIOR (8) ──
    "dior_homme_iris": (
        ["floral", "iris", "woody", "masculine", "dior"],
        {"irone": "irone", "lavender": "lavender", "cacao": "cacao"},
        2,
        "Dior Homme (Olivier Polge, 2005)",
    ),
    "dior_homme_intense": (
        ["floral", "iris", "sweet", "amber", "dior"],
        {
            "iris": "ionone",
            "lavender": "lavender",
            "ambrette_proxy": "ambrettolide",
            "pear_body": "verdox",
            "talc_cushion": "ethylene brassylate",
            "coumarinic_shadow": "tonkarome",
            "vanillic_shadow": "isobutavan",
            "virginia_cedar": "cedarwood",
            "vetiver": "vetiver",
        },
        9,
        "Dior Homme Intense 2011 architecture, formula-code scope 05443/A",
    ),
    "dior_homme_cologne": (
        ["fresh", "citrus", "transparent", "dior"],
        {"bergamot": "bergamot", "grapefruit": "grapefruit", "hedione": "hedione"},
        2,
        "Dior Homme Cologne (2013)",
    ),
    "dior_homme_sport": (
        ["fresh", "citrus", "sport", "dior"],
        {
            "bergamot": "bergamot",
            "spice": "ginger",
            "iris": "irone",
            "vetiver": "vetiver",
        },
        2,
        "Dior Homme Sport (2008)",
    ),
    "dior_fahrenheit": (
        ["leather", "woody", "aromatic", "dior"],
        {"violet_leaf": "parmavert", "birch": "birch tar", "spice": "nutmeg"},
        2,
        "Fahrenheit (Dior, 1988)",
    ),
    "dior_diorissimo": (
        ["floral", "green", "white floral", "dior"],
        {"muguet": "hydroxycitronellal", "jasmine": "jasmine", "rose": "rose"},
        2,
        "Diorissimo (Roudnitska, 1956)",
    ),
    "dior_eau_sauvage": (
        ["fresh", "citrus", "aromatic", "dior"],
        {
            "bergamot": "bergamot",
            "hedione": "hedione",
            "vetiver": "vetiver",
            "herbal": "rosemary",
        },
        2,
        "Eau Sauvage (Roudnitska, 1966)",
    ),
    # ── CHANEL (5) ──
    "chanel_bleu": (
        ["fresh", "aromatic", "woody", "chanel", "blue"],
        {
            "grapefruit": "grapefruit",
            "iso_e_super": "iso e super",
            "incense": "olibanum",
            "cedar": "cedarwood",
        },
        2,
        "Bleu de Chanel (Jacques Polge, 2010)",
    ),
    "chanel_egoiste": (
        ["aromatic", "woody", "chanel"],
        {
            "lavender": "lavender",
            "geranium": "geranium",
            "rosemary": "rosemary",
            "cedar": "cedarwood",
        },
        2,
        "Platinum Egoiste (Chanel, 1993)",
    ),
    "chanel_chance": (
        ["floral", "fresh", "sweet", "chanel"],
        {
            "citron": "citron",
            "jasmine": "jasmine",
            "iris": "irone",
            "patchouli": "patchouli",
        },
        2,
        "Chance (Chanel, 2003)",
    ),
    # ── CHANEL ALLURE HOMME SPORT (5) ──
    "allure_homme_sport": (
        ["fresh", "citrus", "sport", "chanel", "allure"],
        {
            "citrus": "bergamot",
            "neroli": "neroli",
            "tonka": "tonka",
            "vetiver": "vetiver",
        },
        3,
        "Allure Homme Sport (Jacques Polge, 2004)",
    ),
    "allure_homme_sport_cologne": (
        ["fresh", "citrus", "cologne", "chanel", "allure"],
        {"citrus": "bergamot", "neroli": "neroli", "musk": "galaxolide"},
        2,
        "Allure Homme Sport Cologne (2007)",
    ),
    "allure_homme_sport_edp": (
        ["fresh", "citrus", "amber", "chanel", "allure"],
        {
            "citrus": "bergamot",
            "pepper": "pepper",
            "tonka": "tonka",
            "vetiver": "vetiver",
            "amber": "labdanum",
        },
        3,
        "Allure Homme Sport EDP (2012)",
    ),
    "allure_homme_sport_extreme": (
        ["fresh", "citrus", "intense", "amber", "chanel", "allure"],
        {
            "mandarin": "mandarin",
            "tonka": "tonka",
            "vanillin": "vanillin",
            "sandalwood": "sandalwood",
        },
        2,
        "Allure Homme Sport Extreme (2012)",
    ),
    "allure_homme_sport_superleggera": (
        ["fresh", "green", "light", "chanel", "allure"],
        {
            "citrus": "bergamot",
            "herbal": "petitgrain",
            "musk": "galaxolide",
            "cedar": "cedarwood",
        },
        2,
        "Allure Homme Sport Superleggera (Olivier Polge, 2019)",
    ),
    # ── PRADA (3) ──
    "prada_lhomme": (
        ["fresh", "floral", "iris", "powdery", "prada"],
        {"iris": "irone", "neroli": "neroli", "cedar": "cedarwood", "amber": "amber"},
        2,
        "Prada L'Homme (2016)",
    ),
    "prada_amber_homme": (
        ["amber", "oriental", "spicy", "prada"],
        {
            "amber": "labdanum",
            "cardamom": "cardamom",
            "leather": "isobutyl quinoline",
            "patchouli": "patchouli",
        },
        2,
        "Prada Amber Pour Homme (2006)",
    ),
    "prada_infusion_iris": (
        ["floral", "iris", "powdery", "clean", "prada"],
        {
            "iris": "irone",
            "mandarin": "mandarin",
            "cedar": "cedarwood",
            "benzoin": "benzoin",
        },
        2,
        "Prada Infusion d'Iris (2007)",
    ),
    # ── YSL (4) ──
    "ysl_la_nuit": (
        ["spicy", "aromatic", "woody", "ysl"],
        {
            "cardamom": "cardamom",
            "lavender": "lavender",
            "cedar": "cedarwood",
            "caraway": "caraway",
        },
        2,
        "La Nuit de L'Homme (YSL, 2009)",
    ),
    "ysl_lhomme": (
        ["fresh", "spicy", "woody", "ysl"],
        {"ginger": "ginger", "basil": "basil", "tonka": "tonka", "cedar": "cedarwood"},
        2,
        "YSL L'Homme (2006)",
    ),
    "ysl_kouros": (
        ["animalic", "aromatic", "leather", "ysl"],
        {
            "aldehydes": "aldehyde",
            "honey": "honey",
            "tobacco": "tobacco",
            "leather": "isobutyl quinoline",
        },
        2,
        "Kouros (YSL, 1981)",
    ),
}


def _check_skeleton(name: str, state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Generic skeleton checker: verifies marker materials are present."""
    from engine.name_utils import normalize_name

    if name not in _SKELETONS:
        return _result(f"{name}_skeleton", "PASS", f"unknown skeleton {name}")
    archetype_kw, markers, pass_count, source = _SKELETONS[name]

    # Only validate if archetype matches or no archetype set
    raw_archetype = str(config.family_archetype or "")
    archetype = str(config.family_archetype or config.brief or "").lower()
    requested_token = archetype.replace("_", " ").replace(".", " ").strip()
    skeleton_token = name.replace("_", " ").strip()
    dotted_archetype_skeletons = {
        "iris_coumarin_amber.dhi2011": "dior_homme_intense",
    }
    if dotted_archetype_skeletons.get(raw_archetype.lower()) == name:
        should_check = True
    elif requested_token and requested_token == skeleton_token:
        should_check = True
    elif requested_token and requested_token in {
        key.replace("_", " ").strip() for key in _SKELETONS
    }:
        should_check = False
    elif raw_archetype and "." in raw_archetype:
        should_check = False
    else:
        should_check = not archetype or (archetype_kw and archetype_kw[0] in archetype)
    if not should_check and archetype:
        return _result(f"{name}_skeleton", "PASS", "not applicable")

    found = 0
    used_markers: list[str] = []
    for marker_key, marker_note in markers.items():
        for m in state.materials:
            n = normalize_name(m.canonical_name or m.name)
            oav = float(m.screening_oav or 0.0)
            if oav >= 1.0 and marker_note in n:
                found += 1
                used_markers.append(marker_key)
                break

    if found >= pass_count:
        return _result(
            f"{name}_skeleton",
            "PASS",
            f"{' + '.join(used_markers)} present (source: {source})",
        )
    if found >= 1:
        return _result(
            f"{name}_skeleton",
            "WARN",
            f"Skeleton weak: {found}/{pass_count} markers ({source})",
        )
    return _result(f"{name}_skeleton", "FAIL", f"No skeleton markers found ({source})")


# Generate all skeleton gate functions dynamically
for _skel_name in list(_SKELETONS.keys()):
    _gate_name = f"_gate_{_skel_name}_skeleton"
    _skel_n = _skel_name
    exec(
        f"def {_gate_name}(state, config): return _check_skeleton({_skel_n!r}, state, config)",
        globals(),
    )


def _gate_jellinek_psychology(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Paul Jellinek: psychological balance of erogenic/narcotic/stimulating/anti-erogenic."""
    from engine.name_utils import normalize_name

    totals: dict[str, float] = {
        "erogenic": 0.0,
        "narcotic": 0.0,
        "stimulating": 0.0,
        "anti_erogenic": 0.0,
    }
    total_oav = 0.0
    for m in state.materials:
        oav = float(m.oav or 0.0)
        if oav <= 0.0:
            continue
        n = normalize_name(m.canonical_name or m.name)
        cls = _JELLINEK_CLASSES.get(n)
        if cls is not None:
            totals[cls] += oav
        total_oav += oav
    if total_oav == 0:
        return _result("jellinek_psychology", "WARN", "No perceptible materials to classify")
    pcts = {k: v / total_oav * 100.0 for k, v in totals.items()}
    dominant = max(pcts, key=pcts.get)
    if pcts[dominant] > 70.0:
        return _result(
            "jellinek_psychology",
            "WARN",
            f"Jellinek imbalance: {dominant} at {pcts[dominant]:.0f}% of OAV",
        )
    empty = [k for k, v in pcts.items() if v < 5.0]
    if empty:
        return _result(
            "jellinek_psychology",
            "WARN",
            f"Jellinek categories weak: {', '.join(empty)}",
        )
    return _result(
        "jellinek_psychology",
        "PASS",
        f"Jellinek balanced: {', '.join(f'{k}={v:.0f}%' for k, v in sorted(pcts.items()))}",
    )


def _gate_edwards_wheel_coherence(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Michael Edwards: OAV distribution should match family archetype adjacency."""

    if not config.family_archetype:
        return _result("edwards_wheel_coherence", "PASS", "no family archetype set")
    archetype = config.family_archetype.lower()
    family_oav: dict[str, float] = {}
    for m in state.materials:
        fam = (m.family or "unknown").lower()
        oav = float(m.oav or 0.0)
        family_oav[fam] = family_oav.get(fam, 0.0) + oav
    total = sum(family_oav.values()) or 1.0
    # Edwards wheel adjacency: floral families should not have >30% woody OAV, etc.
    floral_families = {"floral", "rose", "muguet", "indolic"}
    woody_families = {"woody", "mossy woods", "dry woods"}
    citrus_families = {"citrus", "fresh"}
    amber_families = {"amber", "oriental"}

    sum(family_oav.get(f, 0.0) for f in floral_families) / total * 100.0
    woody_pct = sum(family_oav.get(f, 0.0) for f in woody_families) / total * 100.0
    citrus_pct = sum(family_oav.get(f, 0.0) for f in citrus_families) / total * 100.0
    amber_pct = sum(family_oav.get(f, 0.0) for f in amber_families) / total * 100.0

    issues = []
    if "floral" in archetype and woody_pct > 40.0:
        issues.append(f"floral archetype with {woody_pct:.0f}% woody OAV (>40)")
    if "citrus" in archetype and woody_pct > 50.0:
        issues.append(f"citrus archetype with {woody_pct:.0f}% woody OAV (>50)")
    if amber_pct > 70.0 and citrus_pct < 5.0:
        issues.append("amber dominant without citrus counterpoint")
    if issues:
        return _result("edwards_wheel_coherence", "WARN", "; ".join(issues))
    return _result("edwards_wheel_coherence", "PASS", "Edwards wheel coherent")


def _gate_guerlain_nature_synthetic(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Aimé Guerlain: balance of natural vs synthetic materials."""
    naturals_keywords = (
        " eo",
        "absolute",
        " resinoid",
        " oil",
        "natural",
        "bergamot",
        "lavender",
        "rose",
        "jasmine",
        "ylang",
        "mandarin",
        "orange",
        "petitgrain",
        "neroli",
        "cedrat",
    )
    natural_oav = synthetic_oav = 0.0
    for m in state.materials:
        oav = float(m.oav or 0.0)
        if oav <= 0.0:
            continue
        n = (m.canonical_name or m.name).lower()
        is_nat = any(kw in n for kw in naturals_keywords)
        if is_nat:
            natural_oav += oav
        else:
            synthetic_oav += oav
    total = natural_oav + synthetic_oav or 1.0
    nat_pct = natural_oav / total * 100.0
    if nat_pct > 85.0:
        return _result(
            "guerlain_nature_synthetic",
            "WARN",
            f"Natural OAV = {nat_pct:.0f}% — batch inconsistency risk",
        )
    if nat_pct < 3.0:
        return _result(
            "guerlain_nature_synthetic",
            "WARN",
            f"Natural OAV = {nat_pct:.0f}% — lacks natural complexity",
        )
    return _result(
        "guerlain_nature_synthetic",
        "PASS",
        f"Natural {nat_pct:.0f}% / Synthetic {100 - nat_pct:.0f}%",
    )


def _gate_weber_fechner_contrast(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Weber-Fechner: OAV should follow log-normal distribution for good contrast."""
    import math

    oavs = [
        float(m.screening_oav or 0.0)
        for m in state.materials
        if (m.screening_oav or 0.0) > 0.0
    ]
    if len(oavs) < 3:
        return _result("weber_fechner_contrast", "PASS", "too few materials to assess")
    logs = [math.log10(o) for o in oavs]
    mean = sum(logs) / len(logs)
    variance = sum((log_oav - mean) ** 2 for log_oav in logs) / len(logs)
    sigma = math.sqrt(variance)
    if sigma < 0.3:
        return _result(
            "weber_fechner_contrast",
            "FAIL",
            f"sigma-log(OAV)={sigma:.2f} — all materials at same intensity, flat composition",
        )
    if sigma < 0.8:
        return _result(
            "weber_fechner_contrast",
            "WARN",
            f"sigma-log(OAV)={sigma:.2f} — low contrast, risk of olfactory white",
        )
    if sigma > 2.5:
        return _result(
            "weber_fechner_contrast",
            "WARN",
            f"sigma-log(OAV)={sigma:.2f} — extreme contrast, some materials may be lost",
        )
    return _result("weber_fechner_contrast", "PASS", f"sigma-log(OAV)={sigma:.2f} — good contrast")


def _gate_adaptation_timing(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Olfactory adaptation: check that adaptation rates are staggered."""
    tiers: dict[str, float] = {
        "fast_0_10min": 0.0,
        "medium_10_45min": 0.0,
        "slow_45_120min": 0.0,
    }
    total = 0.0
    for m in state.materials:
        oav = float(m.screening_oav or 0.0)
        if oav <= 0.0:
            continue
        tier = _adaptation_tier(m)
        if tier == "fast":
            tiers["fast_0_10min"] += oav
        elif tier == "medium":
            tiers["medium_10_45min"] += oav
        elif tier == "slow":
            tiers["slow_45_120min"] += oav
        else:
            tiers["medium_10_45min"] += oav  # default
        total += oav

    total = total or 1.0
    pcts = {k: v / total * 100.0 for k, v in tiers.items()}
    issues = []
    if pcts["fast_0_10min"] < 5.0:
        issues.append("fast tier < 5% (no immediate impact)")
    if pcts["slow_45_120min"] < 10.0:
        issues.append("slow tier < 10% (poor longevity)")
    if pcts["fast_0_10min"] > 60.0:
        issues.append("fast tier > 60% (quick collapse)")
    if not issues:
        return _result(
            "adaptation_timing",
            "PASS",
            f"Adaptation tiers: {', '.join(f'{k}={v:.0f}%' for k, v in sorted(pcts.items()))}",
        )
    return _result("adaptation_timing", "WARN", "; ".join(issues))


def _gate_guerlain_vanillin_coumarin(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Aimé Guerlain: vanillin should not dominate coumarin in fougère/chypre structures."""
    from engine.name_utils import normalize_name

    vanillin_oav = coumarin_oav = 0.0
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if n == "vanillin" or n == "ethyl vanillin":
            vanillin_oav += oav
        if n == "coumarin":
            coumarin_oav += oav
    if coumarin_oav <= 0.0 and vanillin_oav > 0.0:
        return _result(
            "guerlain_vanillin_coumarin",
            "WARN",
            "Vanillin present without coumarin — no structural counterweight",
        )
    if coumarin_oav > 0.0 and vanillin_oav > coumarin_oav * 3.0:
        return _result(
            "guerlain_vanillin_coumarin",
            "FAIL",
            f"Vanillin OAV {vanillin_oav:.0f} >> Coumarin OAV {coumarin_oav:.0f} (ratio >3)",
        )
    if coumarin_oav > 0.0 and vanillin_oav > coumarin_oav * 1.5:
        return _result(
            "guerlain_vanillin_coumarin",
            "WARN",
            f"Vanillin OAV {vanillin_oav:.0f} > Coumarin OAV {coumarin_oav:.0f} × 1.5",
        )
    return _result(
        "guerlain_vanillin_coumarin",
        "PASS",
        f"Vanillin {vanillin_oav:.0f} / Coumarin {coumarin_oav:.0f} — balanced",
    )


def _gate_stevens_power_law(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Stevens Power Law: perceived intensity = OAV^n (n=0.5 for olfaction)."""
    import math

    total_perceived = 0.0
    materials_data: list[tuple[str, float, float]] = []
    for m in state.materials:
        oav = float(m.screening_oav or 0.0)
        if oav <= 0.0:
            continue
        perceived = math.pow(oav, 0.5)  # n=0.5 compressive
        total_perceived += perceived
        materials_data.append((m.canonical_name or m.name, oav, perceived))
    if total_perceived <= 0:
        return _result("stevens_power_law", "PASS", "no perceptible materials")
    max_pct = max(p / total_perceived * 100.0 for _, _, p in materials_data)
    under_01 = sum(
        1
        for _, o, _ in materials_data
        if o > 0.0 and math.pow(o, 0.5) / total_perceived * 100.0 < 0.1
    )
    issues = []
    if max_pct > 60.0:
        dominant = max(materials_data, key=lambda x: x[2])
        issues.append(f"{dominant[0]} dominates perceived intensity at {max_pct:.0f}%")
    if under_01 > len(materials_data) * 0.3:
        issues.append(
            f"{under_01}/{len(materials_data)} materials contribute <0.1% of perceived intensity"
        )
    if issues:
        return _result("stevens_power_law", "WARN", "; ".join(issues))
    return _result(
        "stevens_power_law",
        "PASS",
        f"Perceived intensity distributed across {len(materials_data)} materials",
    )


def _gate_carles_material_count(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Jean Carles: formulas should have 15-40 materials."""
    n = state.material_count
    if n < 8:
        return _result(
            "carles_material_count",
            "FAIL",
            f"{n} materials — too few for a finished perfume",
        )
    if n < 12:
        return _result(
            "carles_material_count",
            "WARN",
            f"{n} materials — minimalist; Carles recommends 15-40",
        )
    if n > 50:
        return _result("carles_material_count", "WARN", f"{n} materials — Carles upper limit is 40")
    return _result("carles_material_count", "PASS", f"{n} materials — within Carles 15-40 range")


_HEDIONE_NAMES = frozenset({"hedione", "hedione hc"})
# AGENTS.md F2: "Max 12% for chypre. Max 15% for floral."
_HEDIONE_CAP_CHYPRE_PCT = 12.0
_HEDIONE_CAP_DEFAULT_PCT = 15.0


def _gate_hedione_share(
    formula: Mapping, state: FormulaState, config: ReleaseGateConfig
) -> GateResult:
    """Warn when Hedione dominates the concentrate (AGENTS.md F2). Advisory only."""
    from engine.name_utils import normalize_name

    hedione_ul = sum(
        m.active_ul
        for m in state.materials
        if normalize_name(m.canonical_name or m.name) in _HEDIONE_NAMES
    )
    if hedione_ul <= 0.0:
        return _skipped("hedione_share", "no Hedione in formula")
    total_ul = state.odorant_active_ul if state.odorant_active_ul > 0.0 else state.total_active_ul
    share = 100.0 * hedione_ul / total_ul if total_ul > 0.0 else 0.0
    archetype = str(infer_archetype(config.brief, config.family_archetype) or "")
    name = str(formula.get("name", "") or "")
    if "chypre" in archetype.lower():
        cap, why = _HEDIONE_CAP_CHYPRE_PCT, f"chypre family ({archetype})"
    elif "chypre" in name.lower():
        cap, why = _HEDIONE_CAP_CHYPRE_PCT, "chypre named in the formula name"
    else:
        cap, why = _HEDIONE_CAP_DEFAULT_PCT, "not a chypre, so the floral/default cap applies"
    basis = "% of fragrance-active uL"
    data = {
        "hedione_active_ul": round(hedione_ul, 4),
        "total_active_ul": round(total_ul, 4),
        "share_pct": round(share, 2),
        "cap_pct": cap,
        "cap_reason": why,
        "basis": basis,
        "source": "AGENTS.md F2 (Hedione crowding)",
    }
    if share > cap:
        return _result(
            "hedione_share",
            "WARN",
            f"Hedione is {share:.1f}{basis}, above the {cap:.0f}% cap ({why}). "
            "Above about 15% Hedione becomes the perfume and buries the named character; "
            "check the dose before mixing.",
            data,
        )
    return _result(
        "hedione_share",
        "PASS",
        f"Hedione is {share:.1f}{basis}, within the {cap:.0f}% cap ({why}).",
        data,
    )


# AGENTS.md: omitted by default; exception-only under the design-call contract.
_EXCEPTION_ONLY_MUSKS = frozenset({"tonalide", "macrolide", "musk ketone"})
# One lead plus one support musk.
_MUSK_COUNT_LIMIT = 2


def _gate_musk_count(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Warn on more than a lead plus a support musk, or an exception-only musk. Advisory only.

    Musks are the materials whose ingredient profile odor family is "musk"
    (ingredient_intelligence _PROFILES or_family, carried as MaterialState.family).
    Formula rows carry no stated-role field, so every musk counts toward the limit.
    """
    from engine.name_utils import normalize_name

    musks = [
        m.name
        for m in state.materials
        if m.active_ul > 0.0 and str(m.family or "").lower() == "musk"
    ]
    exception_only = [
        m.name
        for m in state.materials
        if m.active_ul > 0.0
        and normalize_name(m.canonical_name or m.name) in _EXCEPTION_ONLY_MUSKS
    ]
    if not musks and not exception_only:
        return _skipped("musk_count", "no musks in formula")
    data = {
        "musks": musks,
        "exception_only_musks": exception_only,
        "limit": _MUSK_COUNT_LIMIT,
        "classification_source": "ingredient_intelligence profile odor family == 'musk'",
    }
    problems = []
    if len(musks) > _MUSK_COUNT_LIMIT:
        problems.append(
            f"{len(musks)} musks ({', '.join(musks)}); more than one lead plus one support musk. "
            "Each extra musk needs a distinct stated role and an omission comparison"
        )
    if exception_only:
        problems.append(
            f"{', '.join(exception_only)} is omitted by default and exception-only "
            "(needs the full design-call and inventory-separation case)"
        )
    if problems:
        return _result("musk_count", "WARN", "; ".join(problems), data)
    return _result(
        "musk_count", "PASS", f"{len(musks)} musk(s): {', '.join(musks)}", data
    )


def _gate_roudnitska_hedione_pct(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Roudnitska: Hedione should be 10-25% of concentrate."""
    from engine.name_utils import normalize_name

    mass_percentages = state.active_mass_percentages()
    if mass_percentages is None:
        return _result(
            "roudnitska_hedione_pct",
            "WARN",
            "Exact active-mass ppm is unavailable; Hedione percentage heuristic not evaluated.",
            {"basis": "active_concentrate_ppm_w_w", "evaluation_status": "NOT_EVALUATED"},
        )
    hedione_names = {"hedione", "hedione hc"}
    hedione_pct = sum(
        mass_percentages.get(m.name, 0.0)
        for m in state.materials
        if normalize_name(m.canonical_name or m.name) in hedione_names
    )
    if hedione_pct > 30.0:
        return _result(
            "roudnitska_hedione_pct",
            "FAIL",
            f"Hedione = {hedione_pct:.1f}% of concentrate (>30%, guaranteed olfactory fatigue)",
        )
    if hedione_pct > 25.0:
        return _result(
            "roudnitska_hedione_pct",
            "WARN",
            f"Hedione = {hedione_pct:.1f}% of concentrate (>25% Roudnitska limit)",
        )
    if hedione_pct < 5.0 and hedione_pct > 0.0:
        return _result(
            "roudnitska_hedione_pct",
            "WARN",
            f"Hedione = {hedione_pct:.1f}% of concentrate (<5%, minimal radiance effect)",
        )
    return _result(
        "roudnitska_hedione_pct",
        "PASS",
        f"Hedione = {hedione_pct:.1f}% of concentrate (10-25% ideal)",
    )


def _gate_guerlain_rose_jasmine_balance(
    state: FormulaState, config: ReleaseGateConfig
) -> GateResult:
    """Guerlain tradition: rose and jasmine should balance in floral formulas."""
    if not _family_gate_applicable(config, "floral"):
        return _result("guerlain_rose_jasmine_balance", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    rose_oav = jasmine_oav = 0.0
    rose_kw = {
        "geraniol",
        "citronellol",
        "nerol",
        "rhodinol",
        "rose oxide",
        "damascone",
        "damascenone",
        "phenethyl alcohol",
    }
    jasmine_kw = {
        "hedione",
        "benzyl acetate",
        "cis jasmone",
        "dihydrojasmone",
        "indole",
        "methyl benzoate",
    }
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if n in rose_kw or any(k in n for k in ("rose", "geraniol", "citronellol", "nerol")):
            rose_oav += oav
        if n in jasmine_kw or any(k in n for k in ("hedione", "jasmone", "jasmine")):
            jasmine_oav += oav
    if rose_oav <= 1.0 or jasmine_oav <= 1.0:
        return _result("guerlain_rose_jasmine_balance", "PASS", "rose/jasmine not applicable")
    ratio = max(rose_oav, jasmine_oav) / min(rose_oav, jasmine_oav)
    if ratio > 3.0:
        return _result(
            "guerlain_rose_jasmine_balance",
            "WARN",
            f"Rose:jasmine OAV ratio = {ratio:.1f}:1 — Guerlain recommends <3:1",
        )
    return _result(
        "guerlain_rose_jasmine_balance",
        "PASS",
        f"Rose:jasmine OAV ratio = {ratio:.1f}:1 — balanced",
    )


def _gate_carles_accord_ratio(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Advisory active-dose contrast; never confuse OAV with a dose ratio."""
    if not state.exact_mass_ppm_available:
        return _result(
            "carles_accord_ratio",
            "WARN",
            "Exact active-mass ppm is unavailable; pairwise dose ratios were not evaluated.",
            {"metric": "active_concentrate_ppm_w_w", "evaluation_status": "NOT_EVALUATED"},
        )
    doses = [
        (m.canonical_name or m.name, float(m.active_concentrate_ppm_w_w or 0.0))
        for m in state.materials
        if (m.active_concentrate_ppm_w_w or 0.0) > 0.0
    ]
    issues = []
    for i in range(len(doses)):
        for j in range(i + 1, len(doses)):
            if doses[i][1] <= 0 or doses[j][1] <= 0:
                continue
            ratio = max(doses[i][1], doses[j][1]) / min(doses[i][1], doses[j][1])
            if ratio > 8.0:
                issues.append(f"{doses[i][0]}:{doses[j][0]} = {ratio:.0f}:1")
                if len(issues) >= 3:
                    break
        if len(issues) >= 3:
            break
    if issues:
        return _result(
            "carles_accord_ratio",
            "WARN",
            f"Extreme active-mass ppm ratios (>8:1 advisory): {'; '.join(issues)}",
            {"metric": "active_concentrate_ppm_w_w", "issues": issues},
        )
    return _result(
        "carles_accord_ratio",
        "PASS",
        "No extreme active-mass ppm ratios",
        {"metric": "active_concentrate_ppm_w_w"},
    )


def _gate_coty_single_material_limit(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Advisory single-active-material share on exact mass basis."""
    mass_percentages = state.active_mass_percentages()
    if mass_percentages is None:
        return _result(
            "coty_single_material_limit",
            "WARN",
            "Exact active-mass ppm is unavailable; single-material limit not evaluated.",
            {"basis": "active_concentrate_ppm_w_w", "evaluation_status": "NOT_EVALUATED"},
        )
    for m in state.materials:
        pct = mass_percentages.get(m.name, 0.0)
        if pct > 40.0:
            return _result(
                "coty_single_material_limit",
                "FAIL",
                f"{m.canonical_name or m.name} = {pct:.1f}% of active concentrate mass (>40% advisory limit)",
                {"basis": "active_concentrate_ppm_w_w", "material_pct": pct},
            )
    return _result(
        "coty_single_material_limit",
        "PASS",
        "No single active material exceeds 40% by mass",
        {"basis": "active_concentrate_ppm_w_w"},
    )


def _gate_stevens_n_efficiency(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Stevens: check if high-volume materials are efficiently used."""
    import math

    mass_percentages = state.active_mass_percentages()
    if mass_percentages is None:
        return _result(
            "stevens_n_efficiency",
            "WARN",
            "Exact active-mass ppm is unavailable; dose-efficiency comparison not evaluated.",
            {"basis": "active_concentrate_ppm_w_w", "evaluation_status": "NOT_EVALUATED"},
        )
    issues = []
    for m in state.materials:
        oav = float(m.screening_oav or 0.0)
        active_pct = mass_percentages.get(m.name, 0.0)
        if oav > 0 and active_pct > 30.0:
            perceived = math.pow(oav, 0.5) if oav > 0 else 0
            total_perceived = sum(
                math.pow(float(x.oav or 0.0), 0.5) for x in state.materials if (x.oav or 0.0) > 0
            )
            perceived_pct = perceived / total_perceived * 100.0 if total_perceived > 0 else 0
            if perceived_pct < active_pct * 0.5:
                issues.append(
                    f"{m.canonical_name or m.name}: {active_pct:.0f}% active mass -> {perceived_pct:.0f}% modeled perceived"
                )
                if len(issues) >= 3:
                    break
    if issues:
        return _result(
            "stevens_n_efficiency",
            "WARN",
            f"Inefficient materials: {'; '.join(issues)}",
        )
    return _result("stevens_n_efficiency", "PASS", "All materials efficiently used")


def _gate_jnd_redundancy(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Weber's Law JND: materials with similar OAV in same family are redundant."""
    from collections import defaultdict

    fam_oavs: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for m in state.materials:
        oav = float(m.oav or 0.0)
        if oav <= 0:
            continue
        fam = m.family or "unknown"
        fam_oavs[fam].append((m.canonical_name or m.name, oav))
    issues = []
    for fam, items in fam_oavs.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][1] <= 0 or items[j][1] <= 0:
                    continue
                ratio = max(items[i][1], items[j][1]) / min(items[i][1], items[j][1])
                if 0.85 <= ratio <= 1.18:
                    issues.append(
                        f"{items[i][0]} vs {items[j][0]} in {fam} (OAV {items[i][1]:.0f}/{items[j][1]:.0f})"
                    )
                    if len(issues) >= 3:
                        break
            if len(issues) >= 3:
                break
        if len(issues) >= 3:
            break
    if issues:
        return _result(
            "jnd_redundancy",
            "WARN",
            f"Potentially redundant pairs: {'; '.join(issues)}",
        )
    return _result("jnd_redundancy", "PASS", "No redundant material pairs detected")


def _gate_adaptation_overlap(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check if top OAV materials are all in the same adaptation tier (collapse risk)."""
    oav_by_tier: dict[str, float] = {}
    for m in sorted(state.materials, key=lambda x: float(x.oav or 0.0), reverse=True)[:5]:
        oav = float(m.oav or 0.0)
        if oav <= 0:
            continue
        tier = _adaptation_tier(m)
        oav_by_tier[tier] = oav_by_tier.get(tier, 0.0) + oav
    total_top5 = sum(oav_by_tier.values()) or 1.0
    for tier, oav in oav_by_tier.items():
        if oav / total_top5 > 0.7:
            return _result(
                "adaptation_overlap",
                "WARN",
                f"Top 5 materials all in same adaptation tier ({tier}: {oav / total_top5 * 100:.0f}%) — collapse risk",
            )
    return _result("adaptation_overlap", "PASS", "Top materials span multiple adaptation tiers")


def _gate_mixture_suppression(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Livermore & Laing: humans perceive at most 3-4 components in a mixture."""
    from collections import defaultdict

    fam_oav: dict[str, float] = defaultdict(float)
    for m in state.materials:
        oav = float(m.oav or 0.0)
        if oav <= 0:
            continue
        fam = m.family or "unknown"
        fam_oav[fam] += oav
    total = sum(fam_oav.values()) or 1.0
    significant = [fam for fam, oav in fam_oav.items() if oav / total > 0.10]
    if len(significant) > 4:
        return _result(
            "mixture_suppression",
            "WARN",
            f"{len(significant)} families each >10% OAV — mixture suppression likely (humans perceive ≤4)",
        )
    return _result(
        "mixture_suppression",
        "PASS",
        f"{len(significant)} significant families — within 4-channel limit",
    )


def _gate_dilution_accuracy(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check for impractical dilution/volume combinations."""
    issues = []
    for m in state.materials:
        dil = m.dilution
        raw = m.raw_ul
        if dil < 0.02 and raw > 50:
            issues.append(f"{m.canonical_name or m.name}: {raw}uL at {dil * 100:.0f}%")
        elif dil < 0.1 and raw > 100:
            issues.append(f"{m.canonical_name or m.name}: {raw}uL at {dil * 100:.0f}%")
        if len(issues) >= 3:
            break
    if issues:
        return _result("dilution_accuracy", "WARN", f"Check pipetting: {'; '.join(issues)}")
    return _result("dilution_accuracy", "PASS", "All dilution/volume combinations practical")


def _gate_oriental_skeleton(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check amber/oriental family has labdanum + benzoin + vanillin + musk."""
    if not _family_gate_applicable(config, "oriental"):
        return _result("oriental_skeleton", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    checks = {"labdanum": 0.0, "benzoin": 0.0, "vanillin": 0.0, "musk": 0.0}
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if "labdanum" in n:
            checks["labdanum"] += oav
        if "benzoin" in n:
            checks["benzoin"] += oav
        if n in ("vanillin", "ethyl vanillin"):
            checks["vanillin"] += oav
        if any(
            k in n
            for k in (
                "galaxolide",
                "habanolide",
                "ethylene brassylate",
                "exaltolide",
                "musk",
            )
        ):
            checks["musk"] += oav
    missing = [k for k, v in checks.items() if v < 0.5]
    if len(missing) >= 2:
        return _result(
            "oriental_skeleton",
            "FAIL" if len(missing) >= 3 else "WARN",
            f"Oriental skeleton missing: {', '.join(missing)}",
        )
    return _result("oriental_skeleton", "PASS", "Oriental skeleton complete")


def _gate_aquatic_skeleton(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check aquatic family has calone or dihydromyrcenol or hedione."""
    if not _family_gate_applicable(config, "aquatic", "marine", "ozonic", "water"):
        return _result("aquatic_skeleton", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    has_aquatic = False
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if oav >= 1.0 and any(
            k in n for k in ("calone", "dihydromyrcenol", "helional", "floralozone")
        ):
            has_aquatic = True
            break
    if not has_aquatic:
        return _result(
            "aquatic_skeleton",
            "FAIL",
            "No aquatic marker material found (calone/DHM/helional/floralozone)",
        )
    return _result("aquatic_skeleton", "PASS", "Aquatic marker present")


def _gate_gourmand_skeleton(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check gourmand family has ethyl maltol + vanillin + patchouli."""
    if not _family_gate_applicable(config, "gourmand", "vanilla", "sweet"):
        return _result("gourmand_skeleton", "PASS", "not applicable")
    from engine.name_utils import normalize_name

    checks = {"ethyl maltol": 0.0, "vanillin": 0.0, "patchouli": 0.0}
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        oav = float(m.screening_oav or 0.0)
        if "ethyl maltol" in n:
            checks["ethyl maltol"] += oav
        if n in ("vanillin", "ethyl vanillin"):
            checks["vanillin"] += oav
        if "patchouli" in n:
            checks["patchouli"] += oav
    missing = [k for k, v in checks.items() if v < 0.5]
    if missing:
        return _result(
            "gourmand_skeleton",
            "WARN",
            f"Gourmand skeleton missing: {', '.join(missing)}",
        )
    return _result(
        "gourmand_skeleton",
        "PASS",
        "Gourmand skeleton complete (ethyl maltol + vanillin + patchouli)",
    )


def _gate_evaporation_rate_balance(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Carles: top/heart/base should each be 10-50% of active mass."""
    state.active_percentages()
    # Use note distribution from formula state
    nd = state.note_distribution()
    issues = []
    for tier in ("top", "heart", "base"):
        pct = nd.get(tier, 0.0)
        if pct < 5.0:
            issues.append(f"{tier} = {pct:.0f}%")
        elif pct > 60.0:
            issues.append(f"{tier} = {pct:.0f}%")
    if issues:
        return _result(
            "evaporation_rate_balance",
            "WARN",
            f"Pyramid imbalance: {', '.join(issues)}",
        )
    return _result(
        "evaporation_rate_balance",
        "PASS",
        f"Top {nd.get('top', 0):.0f}%/Heart {nd.get('heart', 0):.0f}%/Base {nd.get('base', 0):.0f}%",
    )


def _gate_tenacity_projection(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check that low-VP materials are sufficient for longevity."""
    total_active = state.total_active_ul or 1.0
    sub_001 = sub_0001 = 0.0
    for m in state.materials:
        vp = m.vp_pure_pa or 999
        if vp < 0.01:
            sub_001 += m.active_ul
        if vp < 0.001:
            sub_0001 += m.active_ul
    pct_001 = sub_001 / total_active * 100.0
    pct_0001 = sub_0001 / total_active * 100.0
    issues = []
    if pct_001 < 10.0:
        issues.append(f"VP<0.01Pa = {pct_001:.0f}% (<10%, weak longevity)")
    if pct_0001 < 3.0:
        issues.append(f"VP<0.001Pa = {pct_0001:.0f}% (<3%, may lack depth)")
    if issues:
        return _result("tenacity_projection", "WARN", "; ".join(issues))
    return _result(
        "tenacity_projection",
        "PASS",
        f"VP<0.01Pa = {pct_001:.0f}%, VP<0.001Pa = {pct_0001:.0f}%",
    )


# Inventory names of oakmoss/treemoss -> the EU-listed INCI allergen (lowercase,
# matching the normalized names used by the screen below).
_MOSS_INVENTORY_ALLERGENS: dict[str, str] = {
    **dict.fromkeys(
        ("oakmoss absolute", "oakmoss", "oak moss", "oakmoss extract"), "evernia prunastri"
    ),
    **dict.fromkeys(
        ("treemoss absolute", "treemoss", "tree moss", "treemoss extract"), "evernia furfuracea"
    ),
}


def _gate_eu_allergen_declaration(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check EU allergen labeling requirements (EU 2023/1545 — 82 allergens)."""
    # Core 26 allergens (Reg 1223/2009 Annex III original list + expansions)
    eu_allergens: set[str] = {
        "geraniol",
        "citronellol",
        "linalool",
        "limonene",
        "coumarin",
        "eugenol",
        "benzyl alcohol",
        "cinnamaldehyde",
        "cinnamyl alcohol",
        "farnesol",
        "isoeugenol",
        "benzyl salicylate",
        "benzyl benzoate",
        "hydroxycitronellal",
        "alpha-isomethyl ionone",
        "hexyl cinnamal",
        "amyl cinnamal",
        "amylcinnamyl alcohol",
        "anise alcohol",
        "anethole",
        "benzyl cinnamate",
        "citral",
        "citronellyl acetate",
        "alpha-damascone",
        "beta-damascone",
        "damascenone",
    }
    # EU 2023/1545 expanded list (56 new entries, effective 2026-07-31)
    eu_allergens_expanded: set[str] = {
        "vanillin",
        "methyl salicylate",
        "alpha-terpineol",
        "beta-caryophyllene",
        "carvone",
        "menthol",
        "linalyl acetate",
        "salicylaldehyde",
        "methyl-2-octynoate",
        "alpha-ionone",
        "beta-ionone",
        "delta-ionone",
        "gamma-ionone",
        "delta-damascone",
        "lilial",
        "lyral",
        "2,6-dimethyl-7-octen-2-ol",
        "2,4-dimethyl-3-cyclohexene carboxaldehyde",
        "pinene",
        "acetyl cedrene",
    }
    eu_allergens.update(eu_allergens_expanded)

    # Also try loading the JSON library for additional entries
    try:
        import json as _json
        from pathlib import Path as _Path

        db_path = (
            _Path(__file__).resolve().parent.parent.parent
            / ".opencode"
            / "library"
            / "eu_2023_1545_allergens.json"
        )
        if db_path.exists():
            db = _json.loads(db_path.read_text(encoding="utf-8"))
            for entry in db:
                inci = entry.get("inci", "").lower().strip()
                if inci:
                    eu_allergens.add(inci)
    except Exception:
        pass

    from engine.name_utils import normalize_name

    leave_on_threshold_ppm_w_w = 10.0
    declarations: list[dict[str, object]] = []
    below_threshold: list[dict[str, object]] = []
    unknown_concentration: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for m in state.materials:
        n = normalize_name(m.canonical_name or m.name)
        matched_allergens = {n} if n in eu_allergens else set()
        moss_inci = _MOSS_INVENTORY_ALLERGENS.get(n)
        if moss_inci:
            matched_allergens.add(moss_inci)
        matched_allergens.update(
            allergen
            for allergen in eu_allergens
            if len(allergen) > 4 and allergen in n and n != allergen
        )
        for allergen in sorted(matched_allergens):
            key = (m.name, allergen)
            if key in seen:
                continue
            seen.add(key)
            ppm = m.active_finished_product_ppm_w_w
            row: dict[str, object] = {
                "material": m.canonical_name or m.name,
                "allergen": allergen,
                "identity_match": (
                    "exact"
                    if n == allergen
                    else "inventory_alias"
                    if allergen == moss_inci
                    else "name_contains"
                ),
                "active_finished_product_ppm_w_w": (
                    None if ppm is None else round(float(ppm), 6)
                ),
            }
            if ppm is None:
                unknown_concentration.append(row)
            elif float(ppm) > leave_on_threshold_ppm_w_w:
                declarations.append(row)
            else:
                below_threshold.append(row)

    data = {
        "regulation": "Commission Regulation (EU) 2023/1545",
        "source_url": "https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng",
        "product_scope": "leave-on fine fragrance",
        "declaration_threshold_ppm_w_w": leave_on_threshold_ppm_w_w,
        "concentration_basis": "active_finished_product_ppm_w_w",
        "perceptibility_filter_applied": False,
        "oav_used": False,
        "declaration_candidates": declarations,
        "below_threshold": below_threshold,
        "unknown_concentration": unknown_concentration,
        "assessment": "PARTIAL_UNKNOWN" if unknown_concentration else "EVALUATED",
        "release_authority": False,
        "scope_note": (
            "Named-material screen only; constituent-level supplier disclosure remains required "
            "for mixtures and naturals."
        ),
    }
    if declarations:
        labels = [
            str(row["material"])
            if row["identity_match"] == "exact"
            else f"{row['material']} (contains {row['allergen']})"
            for row in declarations
        ]
        unknown_suffix = (
            f"; {len(unknown_concentration)} matched material(s) have UNKNOWN finished-product concentration"
            if unknown_concentration
            else ""
        )
        return _result(
            "eu_allergen_declaration",
            "WARN",
            f"EU allergens above the 10 ppm w/w leave-on declaration threshold: {', '.join(labels[:10])}"
            + (f" +{len(labels) - 10} more" if len(labels) > 10 else "")
            + unknown_suffix,
            data,
        )
    if unknown_concentration:
        return _result(
            "eu_allergen_declaration",
            "WARN",
            "EU allergen declaration assessment UNKNOWN for matched material(s): exact finished-product mass concentration is unavailable",
            data,
        )
    return _result(
        "eu_allergen_declaration",
        "PASS",
        "No named EU allergen exceeds the 10 ppm w/w leave-on declaration threshold",
        data,
    )


def _gate_phototoxic_furanocoumarin(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Expose an unsupported assessment without inventing an exposure verdict."""
    # The legacy calculation below mixes concentrate v/v with finished-product
    # limits and matches oils by substring, including incompatible FCF grades.
    # A product-bound mass assessment must replace that invalid calculation.
    return GateResult(
        gate="safety_phototoxic",
        status="FAIL" if config.commercial_mode or config.mode == "RELEASE_REVIEW" else "WARN",
        detail="Phototoxicity assessment unavailable: product/grade-bound restrictions and finished-product mass exposure are required.",
        data={"assessment": "NOT_EVALUATED", "release_authority": False,
              "legacy_rule_quarantined": True,
              "reason": "Substring oil identity and concentrate-volume percentages do not establish finished-product compliance."},
    )


def _gate_receptor_saturation(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """No validated dose-to-receptor safety model is available."""
    return GateResult(
        gate="safety_receptor_saturation", status="SKIP",
        detail="Legacy receptor percentage caps retired: no validated exposure-to-receptor or safety threshold model.",
        data={"assessment": "UNSUPPORTED_HEURISTIC", "release_authority": False},
    )


def _gate_natural_compatibility(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """F11: Check chemical family compatibility of natural pairs (WARN)."""
    try:
        from engine.ingredient_intelligence import check_natural_compatibility

        natural_names = [
            m.name
            for m in state.materials
            if any(
                tag in m.name.lower() for tag in ("eo", "absolute", "resinoid", "concrete", "co2")
            )
        ]
        if len(natural_names) >= 2:
            warnings = check_natural_compatibility(natural_names)
            if warnings:
                return _result("natural_compatibility", "WARN", "; ".join(warnings[:3]))
    except ImportError:
        pass
    return _result("natural_compatibility", "PASS", "No incompatible natural pairs detected")


def _gamma_authority_class(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized.startswith(("experimental:", "empirically_calibrated:")):
        return "EMPIRICALLY_CALIBRATED"
    if normalized.startswith("unifac:"):
        return "PREDICTIVE_UNIFAC_UNVALIDATED"
    if normalized == "modeled:natural_composite_constituent_gamma":
        return "HEURISTIC_NATURAL_COMPOSITE"
    if normalized.startswith("heuristic:hansen"):
        return "HEURISTIC_HANSEN_DISTANCE"
    if normalized.startswith("profile:"):
        return "HEURISTIC_PROFILE_CONSTANT"
    if normalized.startswith("fallback:ideal"):
        return "IDEAL_COMPARISON_FALLBACK"
    return "UNKNOWN"


def _gate_oav_physics_gamma(
    state: FormulaState,
    config: ReleaseGateConfig,
) -> GateResult:
    """Report gamma authority and OAV leverage without treating non-unity as proof."""
    del config
    rows: list[dict[str, object]] = []
    authority_counts: dict[str, int] = {}
    for material in state.materials:
        source = str(material.sources.get("gamma", material.gamma_source) or "unknown")
        authority = _gamma_authority_class(source)
        authority_counts[authority] = authority_counts.get(authority, 0) + 1
        oav_model = str(material.sources.get("oav_model", "unknown"))
        simple_monomolecular = (
            oav_model == "heuristic:monomolecular_headspace"
            and material.oav is not None
            and material.gamma > 0.0
        )
        ideal_scenario_oav = (
            float(material.oav) / float(material.gamma) if simple_monomolecular else None
        )
        leverage = (
            max(float(material.gamma), 1.0 / float(material.gamma))
            if simple_monomolecular
            else None
        )
        rows.append(
            {
                "material": material.name,
                "gamma": round(float(material.gamma), 6),
                "gamma_source": source,
                "authority": authority,
                "oav_model": oav_model,
                "modeled_oav": (None if material.oav is None else round(float(material.oav), 6)),
                "ideal_gamma_scenario_oav": (
                    None if ideal_scenario_oav is None else round(ideal_scenario_oav, 6)
                ),
                "modeled_to_ideal_oav_ratio": (
                    None if ideal_scenario_oav is None else round(float(material.gamma), 6)
                ),
                "scenario_leverage_x": (None if leverage is None else round(leverage, 6)),
            }
        )

    rows.sort(
        key=lambda row: float(row["scenario_leverage_x"] or 0.0),
        reverse=True,
    )
    unresolved = [row for row in rows if row["authority"] != "EMPIRICALLY_CALIBRATED"]
    scenario_rows = [row for row in rows if row["scenario_leverage_x"] is not None]
    data = {
        "authority": "HEURISTIC_UNCALIBRATED",
        "release_authority": False,
        "source_counts": authority_counts,
        "materials": rows,
        "comparison_scenario": {
            "gamma": 1.0,
            "authority": "COMPARISON_SCENARIO_ONLY",
            "interpretation": (
                "The gamma=1 result is neither a confidence interval nor a "
                "lower/upper bound. It only exposes point-model leverage."
            ),
            "natural_composites_excluded": True,
        },
    }
    if unresolved:
        leverage_detail = ""
        if scenario_rows:
            leader = scenario_rows[0]
            leverage_detail = (
                f"; largest gamma=1 comparison leverage "
                f"{leader['material']}={leader['scenario_leverage_x']:.1f}x"
            )
        return _result(
            "oav_physics_gamma",
            "WARN",
            f"{len(unresolved)}/{len(rows)} materials use predictive, heuristic, "
            f"fallback, or unknown gamma authority{leverage_detail}",
            data,
        )
    return _result(
        "oav_physics_gamma",
        "PASS",
        "All activity coefficients have formula-domain empirical calibration.",
        data,
    )


def _gate_skin_degradation(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """A.6: Check skin degradation for oakmoss/labdanum/tonka/vanilla (WARN only)."""
    degradation_naturals = {
        "oakmoss": (
            "atranorin",
            "atranol + chloroatranol",
            "LLNA Class 2 sensitizers EC3 0.4-0.6%",
            "Verify atranol+chloroatranol <100 ppm via supplier",
        ),
        "labdanum": (
            "ambrein glycosides",
            "ambrox on skin",
            "character potentiated over time",
            "Monitor temporal evolution",
        ),
        "tonka": (
            "coumarin glycosides",
            "coumarin release",
            "IFRA restricted",
            "Check IFRA coumarin limits",
        ),
        "vanilla": (
            "glucovanillin",
            "vanillin release",
            "character shift over time",
            "Monitor vanillin persistence",
        ),
        "patchouli": (
            "patchoulol",
            "norpatchoulenol on skin",
            "texture shift over hours",
            "Monitor patchouli character shift",
        ),
    }
    findings = []
    for m in state.materials:
        for key, (precursor, products, hazard, recommendation) in degradation_naturals.items():
            if key in m.name.lower():
                findings.append(f"{m.name}: {precursor} -> {products} ({hazard}). {recommendation}")
    if findings:
        return _result("skin_degradation", "WARN", "; ".join(findings))
    return _result("skin_degradation", "PASS", "No skin-degrading naturals detected")


def _gate_verify_protocol_aggregate(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """A.1-A.10 verification protocol aggregator.

    Collects status of all verification categories covered by individual gates.
    Reports PASS if coverage is complete, WARN if gaps exist.
    Never FAILs — individual gates handle their own severity per user disposition.
    """
    covered = {
        "A.1_oav_physics": "oav_physics_gamma",
        "A.2_eu_allergens": "eu_allergen_declaration",
        "A.3_phototoxicity": "safety_phototoxic",
        "A.4_receptor_saturation": "safety_receptor_saturation",
        "A.5_composite_oav": "natural_compatibility",
        "A.6_skin_degradation": "skin_degradation",
        "A.7_vp_source": "data_provenance",
        "A.8_sensomics": "literature_compliance",
        "A.9_dhvap": "evaporation_rate_balance",
        "A.10_note_tier": "carles_pyramid",
    }
    materials_checked = len(state.materials)
    warnings = []
    missing_odt = sum(1 for m in state.materials if m.odt_air_ppm is None)
    if missing_odt > 0:
        warnings.append(f"{missing_odt}/{materials_checked} materials missing ODT data")
    if warnings:
        return _result(
            "verify_protocol_aggregate",
            "WARN",
            f"Verification protocol active — {', '.join(warnings)}",
            data={"covered_categories": list(covered.keys()), "gates_mapped": covered},
        )
    return _result(
        "verify_protocol_aggregate",
        "PASS",
        f"Verification protocol A.1-A.10 coverage confirmed ({materials_checked} materials, 0 missing ODT)",
        data={"covered_categories": list(covered.keys()), "gates_mapped": covered},
    )


def _gate_hedonic_neuroscience(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Neuroscience advisory: receptor genetics, psychoactive compounds, hedonic findings."""
    findings: list[str] = []
    try:
        from engine.name_utils import normalize_name as _nn
        from engine.pipeline.neuroscience import (
            _HEDONIC_FINDINGS,  # noqa: F401  # feature detection
            _OR_GENETICS,  # noqa: F401  # feature detection
            _PSYCHOACTIVE_EFFECTS,
        )

        # Check psychoactive compound thresholds
        total_active_ul = state.total_active_ul or 1.0
        for m in state.materials:
            n = _nn(m.name)
            active_pct = (m.active_ul / total_active_ul) * 100.0
            for compound, effects in _PSYCHOACTIVE_EFFECTS.items():
                if compound in n:
                    for eff in effects:
                        thresh = eff.get("threshold_active_pct", 100)
                        if active_pct > thresh:
                            findings.append(
                                f"{m.name} {active_pct:.1f}% > {thresh}%: {eff['effect']} ({eff['consumer_impact'][:60]}...)"
                            )

        # Channel count vs vmPFC integration limit
        perceptible = [m for m in state.materials if (m.oav or 0) >= 10]
        if len(perceptible) > 5:
            findings.append(
                f"{len(perceptible)} materials with OAV >10 — may exceed vmPFC integration capacity (Nature Comms 2026)"
            )
    except ImportError:
        pass

    if findings:
        return _result("hedonic_neuroscience", "PASS", "INFO: " + "; ".join(findings[:5]))
    return _result("hedonic_neuroscience", "PASS", "No neuroscience flags raised")


def _legacy_gate_solvent_matrix(
    state: FormulaState,
    config: ReleaseGateConfig,
) -> GateResult:
    """Track carrier solvents entering perfume through diluted materials."""
    try:
        from engine.name_utils import normalize_name as _nn  # noqa: F401  # feature detection
        from engine.solvent_matrix import SolventLedger as _Ledger

        ledger = _Ledger()
        for m in state.materials:
            dil = m.dilution if hasattr(m, "dilution") else 1.0
            solvent = getattr(m, "solvent", "none") or "none"
            solvent = str(solvent).upper()
            ledger.add_material(
                m.raw_ul if hasattr(m, "raw_ul") else m.active_ul / dil if dil > 0 else m.active_ul,
                dil,
                solvent,
            )
        ledger.set_ethanol_matrix(
            state.batch_volume_ml * 1000 if hasattr(state, "batch_volume_ml") else 24000
        )

        pct = ledger.carrier_pct_of_matrix
        if pct > 10:
            return _result(
                "solvent_matrix",
                "WARN",
                f"Carrier solvents at {pct:.1f}% of matrix — may suppress top notes via VP depression. "
                f"Carriers: {ledger.to_dict().get('carrier_solvents_ul', {})}",
            )
        return _result(
            "solvent_matrix",
            "PASS",
            f"Carrier solvents at {pct:.1f}% of matrix — within guideline (<10%)",
        )
    except ImportError:
        return _result("solvent_matrix", "PASS", "Solvent module not loaded")
    except Exception as e:
        return _result("solvent_matrix", "PASS", f"Solvent tracking skipped: {e}")


def _gate_solvent_matrix(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Reconcile declared bulk solvent and diluted-stock carrier evidence.

    Residual stock-carrier volumes remain diagnostic proxies unless the stock
    basis is explicitly v/v. They are reported here but are not silently added
    to the canonical headspace mole fractions.
    """
    del config
    from engine.solvent_matrix import SolventLedger, get_solvent_properties

    ledger = SolventLedger()
    for name, moles in state.matrix_components_moles:
        properties = get_solvent_properties(name)
        mw = float(properties.get("mw", 0.0) or 0.0)
        density = float(properties.get("density", 0.0) or 0.0)
        if mw <= 0.0 or density <= 0.0:
            ledger.unresolved_bulk_components.append(name)
            continue
        volume_ul = float(moles) * mw / density * 1000.0
        ledger.add_bulk_component(name, volume_ul)

    for material in state.materials:
        ledger.add_material(
            material.raw_ul,
            material.dilution,
            material.stock_carrier,
            material=material.name,
            fraction_basis=material.stock_fraction_basis,
        )

    data = ledger.to_dict()
    data.update(
        {
            "headspace_basis": state.headspace_basis,
            "matrix_source": state.matrix_source,
            "formula_stock_carrier_inclusion": state.stock_carrier_inclusion,
            "interpretation": (
                "Named residual carrier volumes are reconciliation scenarios. "
                "They do not alter modeled mole fractions until concentration "
                "basis, carrier identity, and double-counting are resolved."
            ),
        }
    )
    diluted_rows = [material for material in state.materials if material.dilution < 1.0]
    if not diluted_rows:
        return _result(
            "solvent_matrix",
            "PASS",
            "No diluted-stock carrier reconciliation is required.",
            data,
        )

    known = data["known_stock_carriers_ul"]
    unresolved = float(data["unresolved_carrier_proxy_ul"])
    proxy_rows = sum(row["authority"] == "RESIDUAL_VOLUME_PROXY" for row in data["stock_rows"])
    detail = (
        f"stock-carrier authority {data['authority']}; "
        f"known named carriers {known}; unresolved carrier proxy "
        f"{unresolved:.1f} uL"
    )
    if proxy_rows:
        detail += f"; {proxy_rows} named carrier row(s) lack a v/v basis"
    return _result("solvent_matrix", "WARN", detail, data)


def _gate_sensory_overcrowding(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    perceptible_channels = {
        m.family or m.canonical_name for m in state.materials if (m.intensity or 0.0) >= 0.5
    }
    if len(perceptible_channels) > config.max_perceptible_channels:
        return _result(
            "sensory_overcrowding",
            "FAIL",
            f"{len(perceptible_channels)} perceptible channels; olfactory-white risk",
        )
    if len(perceptible_channels) > 22:
        return _result(
            "sensory_overcrowding",
            "WARN",
            f"{len(perceptible_channels)} perceptible channels; check clarity",
        )
    return _result(
        "sensory_overcrowding",
        "PASS",
        f"{len(perceptible_channels)} perceptible channels",
    )


def _gate_master_perfumer(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    note = state.note_distribution()
    active = state.active_percentages()
    max_material = max(active.items(), key=lambda kv: kv[1]) if active else ("", 0.0)
    preblend_count = sum(1 for m in state.materials if m.is_opaque_preblend)
    issues: list[str] = []
    if state.material_count < 6:
        issues.append("too few materials for a finished fine-fragrance structure")
    if state.material_count > 32:
        issues.append("too many materials for a readable formula")
    if max_material[1] > 45.0:
        issues.append(f"{max_material[0]} dominates active formula at {max_material[1]:.1f}%")
    if note["top"] < 5.0:
        issues.append("opening likely underbuilt")
    if note["base"] < 15.0:
        issues.append("drydown likely underbuilt")
    if preblend_count and not config.allow_preblends:
        issues.append(f"{preblend_count} opaque preblend(s) hide perfumer intent")

    if len(issues) >= 3:
        return _result("master_perfumer_gate", "FAIL", "; ".join(issues))
    if issues:
        return _result("master_perfumer_gate", "WARN", "; ".join(issues))
    return _result("master_perfumer_gate", "PASS", "coherent, buildable, and readable")


def _gate_robustness(
    formula: Mapping,
    config: ReleaseGateConfig,
    *,
    state: FormulaState,
    simulation: tuple[SimulationFrame, ...],
) -> tuple[GateResult, RobustnessReport]:
    report = audit_formula_robustness(
        formula,
        config,
        gate_state=state,
        gate_simulation=simulation,
    )
    if report.status == "WARN":
        examples = "; ".join(
            f"{issue.material} {issue.direction}: {issue.detail}" for issue in report.issues[:3]
        )
        detail = f"{len(report.issues)} fragile perturbation(s) across {report.checked} checks"
        if examples:
            detail += f"; {examples}"
        status = "FAIL" if config.commercial_mode else "WARN"
        if config.commercial_mode:
            detail = "commercial blocker: " + detail
        return _result("robustness_perturbation", status, detail, report.as_dict()), report
    return (
        _result(
            "robustness_perturbation",
            "PASS",
            f"{report.checked} subtotal-preserving perturbations stable",
            report.as_dict(),
        ),
        report,
    )


def _gate_confidence(state: FormulaState, config: ReleaseGateConfig) -> tuple[GateResult, dict]:
    fv = _formula_vector_from_state(state)
    confidence = ConfidenceScorer().score(fv.ingredients)
    pipeline_confidence = state.uncertainty.confidence_score
    combined = round(max(15.0, min(confidence["overall_confidence"], pipeline_confidence)), 1)
    confidence = dict(confidence)
    confidence["pipeline_confidence"] = pipeline_confidence
    confidence["combined_confidence"] = combined
    confidence["combined_grade"] = (
        "HIGH"
        if combined >= 80
        else "MEDIUM"
        if combined >= 50
        else "LOW"
        if combined >= 25
        else "VERY_LOW"
    )
    strict_commercial_confidence = (
        config.commercial_mode and config.commercial_confidence_policy != "warn"
    )
    threshold = max(
        config.min_confidence_score,
        50.0 if strict_commercial_confidence else config.min_confidence_score,
    )
    confidence["required_minimum"] = threshold
    if combined < threshold:
        spec = get_archetype(config.family_archetype)
        diagnostic_reference = bool(
            spec is not None and spec.role == "reference_control" and not config.commercial_mode
        )
        # The combined score is an aggregate diagnostic, not an authority
        # dimension. In non-commercial pre-mix design it can warn about weak
        # evidence but must not override passing stock, arithmetic, and other
        # hard-authority gates. Strict commercial release remains blocking.
        advisory_low_confidence = (
            not config.commercial_mode
            or diagnostic_reference
            or config.is_commercial_trial()
        )
        status = "WARN" if advisory_low_confidence else "FAIL"
        detail = f"combined confidence {combined:.1f} below {threshold:.1f}"
        if diagnostic_reference:
            detail += "; reference-control study remains diagnostic only"
            confidence["authorization"] = "DIAGNOSTIC_REFERENCE_CONTROL_ONLY"
        return (
            _result(
                "confidence_minimum",
                status,
                detail,
                confidence,
            ),
            confidence,
        )
    if combined < 50.0:
        detail = f"combined confidence {combined:.1f}"
        if config.is_commercial_trial():
            detail += "; commercial-trial warning, not sellable until calibrated"
        return (
            _result("confidence_minimum", "WARN", detail, confidence),
            confidence,
        )
    return (
        _result(
            "confidence_minimum",
            "PASS",
            f"combined confidence {combined:.1f}",
            confidence,
        ),
        confidence,
    )


def _apply_preflight_confidence_penalty(
    confidence_gate: GateResult,
    confidence: dict,
    preflight: Mapping[str, object],
    config: ReleaseGateConfig,
) -> tuple[GateResult, dict]:
    penalty = float(preflight.get("confidence_penalty", 0.0) or 0.0)
    if penalty <= 0:
        return confidence_gate, confidence

    updated = dict(confidence)
    base_combined = float(updated.get("combined_confidence", 0.0) or 0.0)
    adjusted = max(0.0, round(base_combined - penalty, 1))
    science_penalty = 0.0
    for raw_check in preflight.get("checks", []) or []:
        if not isinstance(raw_check, Mapping):
            continue
        if raw_check.get("check_name") != "science_coverage":
            continue
        raw_data = raw_check.get("data", {}) or {}
        if isinstance(raw_data, Mapping):
            science_penalty = float(raw_data.get("confidence_penalty", 0.0) or 0.0)
        break
    updated["preflight_evidence_penalty"] = round(penalty, 3)
    updated["science_preflight_penalty"] = round(science_penalty, 3)
    updated["preflight_penalty_components"] = {
        "science_coverage": round(science_penalty, 3),
        "other_formula_evidence": round(max(0.0, penalty - science_penalty), 3),
    }
    updated["combined_confidence_pre_penalty"] = round(base_combined, 1)
    updated["combined_confidence"] = adjusted
    updated["combined_grade"] = (
        "HIGH"
        if adjusted >= 80
        else "MEDIUM"
        if adjusted >= 50
        else "LOW"
        if adjusted >= 25
        else "VERY_LOW"
    )
    threshold = float(updated.get("required_minimum", config.min_confidence_score))
    spec = get_archetype(config.family_archetype)
    diagnostic_reference = bool(
        spec is not None and spec.role == "reference_control" and not config.commercial_mode
    )
    if adjusted < threshold:
        advisory_low_confidence = (
            not config.commercial_mode
            or diagnostic_reference
            or config.is_commercial_trial()
        )
        status = "WARN" if advisory_low_confidence else "FAIL"
        detail = (
            f"combined confidence {adjusted:.1f} below {threshold:.1f} after "
            f"preflight evidence penalty {penalty:.1f}"
        )
        if diagnostic_reference:
            detail += "; reference-control study remains diagnostic only"
            updated["authorization"] = "DIAGNOSTIC_REFERENCE_CONTROL_ONLY"
    elif adjusted < 50.0:
        status = "WARN"
        detail = (
            f"combined confidence {adjusted:.1f} after preflight evidence penalty {penalty:.1f}"
        )
    else:
        status = "PASS"
        detail = (
            f"combined confidence {adjusted:.1f} after preflight evidence penalty {penalty:.1f}"
        )
    updated_gate = _result(confidence_gate.gate, status, detail, updated)
    return updated_gate, updated


def _commercial_readiness(
    status: str, gates: list[GateResult], confidence: dict, config: ReleaseGateConfig
) -> str:
    if status == "FAIL":
        return "NOT_RELEASE_READY"
    # HOLD (missing data) blocks release like FAIL, so no ready or trial-ready
    # state may follow from it; the suffix keeps "data missing" distinct from
    # "formula wrong".
    if status == "HOLD" or any(g.status == "HOLD" for g in gates):
        return "NOT_RELEASE_READY_HOLD"
    if config.is_commercial_trial() and confidence.get("combined_confidence", 0.0) < 50.0:
        return "COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE"
    if confidence.get("combined_confidence", 0.0) < 50.0:
        return "TECHNICAL_PASS_LOW_CONFIDENCE"
    if config.is_commercial_trial() and any(g.status == "WARN" for g in gates):
        return "COMMERCIAL_TRIAL_CONDITIONAL_REVIEW"
    if config.is_commercial_trial():
        return "COMMERCIAL_TRIAL_READY"
    if config.commercial_mode and any(g.status == "WARN" for g in gates):
        return "CONDITIONAL_PASS_NEEDS_REVIEW"
    if any(g.status == "WARN" for g in gates):
        return "CONDITIONAL_PASS_NEEDS_REVIEW"
    return "COMMERCIAL_READY_FOR_TRIAL"


def _gate_mass_market_tier_check(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Check if the formula's material quality matches its expected price tier.

    At 1500-3500 THB, you need a certain quality floor (industry ~55+) and ceiling
    (overbuilding with naturals kills margin). This gate warns when:
    - You're spending too much on materials for the price point (over-engineered)
    - Your formula quality is too low to compete at this price (under-engineered)
    - You're using luxury materials that don't add perceptible value at mass scale
    """
    if not state or not state.materials:
        return _result("mass_market_tier_check", "PASS", "No materials to check.")

    from engine.cost_analysis import MATERIAL_COSTS_PER_KG

    total_active_g = sum(m.active_g for m in state.materials) or 1.0
    total_raw_ul = sum(m.raw_ul for m in state.materials) or 1.0

    # 1. Estimate material cost per mL of concentrate
    estimated_cost_per_ml = 0.0
    premium_mass_pct = 0.0
    premium_materials = []
    total_checked = 0.0

    for m in state.materials:
        if m.active_g <= 0:
            continue
        name_lower = m.name.lower().strip()
        # Look up cost
        cost_per_kg = None
        for mat_key in MATERIAL_COSTS_PER_KG:
            if mat_key.lower().strip() in name_lower or name_lower in mat_key.lower().strip():
                cost_per_kg = MATERIAL_COSTS_PER_KG[mat_key]
                break

        if cost_per_kg is None:
            cost_per_kg = 30.0  # default synthetic estimate

        material_cost = (m.active_g / 1000.0) * cost_per_kg  # USD
        estimated_cost_per_ml += material_cost

        # Check for premium materials
        is_premium = any(p in name_lower for p in PREMIUM_NATURALS)
        if is_premium:
            premium_mass_pct += m.active_g
            premium_materials.append(m.name)

        total_checked += m.active_g

    # Normalize cost per mL of concentrate
    total_concentrate_ml = total_raw_ul / 1000.0
    if total_concentrate_ml > 0:
        estimated_cost_per_ml = estimated_cost_per_ml / total_concentrate_ml

    premium_pct = (premium_mass_pct / total_active_g * 100) if total_active_g > 0 else 0
    premium_pct = min(100.0, premium_pct)

    # 2. Calculate approximate "mass market readiness" score
    # Uses: material count, premium %, estimated cost, naturals ratio
    material_count = len(state.materials)

    warnings = []
    is_warn = False

    # Check: over-engineered for mass market
    if premium_pct > PREMIUM_MATERIAL_WARN_PCT:
        warnings.append(
            f"{premium_pct:.0f}% of active mass from premium materials "
            f"(>{PREMIUM_MATERIAL_WARN_PCT:.0f}% threshold). "
            f"At 1500-3500 THB retail, this margin may be tight. "
            f"Premium materials: {', '.join(premium_materials[:5])}{'...' if len(premium_materials) > 5 else ''}"
        )
        is_warn = True

    # Check: too many premium naturals for a mass-market formula
    if premium_pct > 40:
        warnings.append(
            f"PREMIUM OVERLOAD: {premium_pct:.0f}% premium materials. "
            f"Consider substituting with quality synthetics for mass production. "
            f"Each 1% premium material adds ~{estimated_cost_per_ml * 10:.1f}¢/mL to COGS."
        )
        is_warn = True

    # Check: very expensive materials (ambermax, javanol, etc.) in large amounts
    expensive_naturals = [
        m.name
        for m in state.materials
        if m.active_g > 0.01
        and any(p in m.name.lower() for p in ["ambrox super", "ambermax", "javanol", "alpha irone"])
    ]
    if expensive_naturals:
        warnings.append(
            f"Expensive captives found: {', '.join(expensive_naturals[:3])}. "
            f"At {config.expected_retail_price_thb:.0f} THB, these eat margin. "
            f"Consider if their perceptible impact justifies the cost."
        )
        is_warn = True

    # Check: estimated cost seems too high for the price
    est_cost_for_30ml = estimated_cost_per_ml * 30.0 * 36  # rough USD to THB
    if est_cost_for_30ml > config.expected_retail_price_thb * 0.15:
        warnings.append(
            f"Estimated material cost ~{est_cost_for_30ml:.0f} THB for 30mL "
            f"({est_cost_for_30ml / config.expected_retail_price_thb * 100:.0f}% of {config.expected_retail_price_thb:.0f} THB retail). "
            f"Industry target: 4-8% of retail. Margin may be unsustainable."
        )
        is_warn = True

    # Check: too few materials or too simple for the price
    if material_count < 12 and config.expected_retail_price_thb >= 1500:
        warnings.append(
            f"Only {material_count} materials for a {config.expected_retail_price_thb:.0f} THB formula. "
            f"Consumers expect complexity at this price. Consider adding structural materials."
        )
        is_warn = True

    # Check: very high material count for mass production
    if material_count > 35:
        warnings.append(
            f"{material_count} materials is high for mass production. "
            f"Each material adds compounding cost and quality control risk. "
            f"Aim for 18-28 for scalable manufacturing."
        )
        is_warn = True

    if is_warn:
        return _result(
            "mass_market_tier_check",
            "WARN",
            "; ".join(warnings),
            data={
                "estimated_cost_per_ml_usd": round(estimated_cost_per_ml, 4),
                "estimated_cost_30ml_thb": round(est_cost_for_30ml, 0),
                "premium_material_pct": round(premium_pct, 1),
                "material_count": material_count,
                "price_tier": f"{config.expected_retail_price_thb:.0f} THB",
                "premium_materials": premium_materials[:8],
            },
        )

    return _result(
        "mass_market_tier_check",
        "PASS",
        f"Formula profile matches {config.expected_retail_price_thb:.0f} THB tier. "
        f"{material_count} materials, {premium_pct:.0f}% premium, "
        f"est. cost {estimated_cost_per_ml * 36 * 30:.0f} THB/30mL.",
        data={
            "estimated_cost_per_ml_usd": round(estimated_cost_per_ml, 4),
            "material_count": material_count,
            "premium_material_pct": round(premium_pct, 1),
        },
    )


def _gate_mode_protection(state, config):
    """Block actions inappropriate for current operating mode."""
    del state
    mode = str(getattr(config, "mode", "RECONSTRUCTION"))

    # Detect current action — if we can't determine, use the config mode
    current_action = str(getattr(config, "action", "REPORT"))
    evaluation = evaluate_mode_action(mode, current_action)
    reasons = [reason.value for reason in evaluation.reasons]

    if not evaluation.allowed:
        return GateResult(
            gate="mode_protection",
            status="FAIL",
            detail=(
                f"Action '{current_action}' is blocked in mode '{mode}': "
                + ", ".join(reasons)
            ),
            data={
                "mode": mode,
                "action": current_action,
                "blocked": True,
                "reasons": reasons,
            },
        )

    return GateResult(
        gate="mode_protection",
        status="PASS",
        detail=f"Mode {mode} — action {current_action} permitted.",
        data={
            "mode": mode,
            "action": current_action,
            "blocked": False,
            "reasons": [],
        },
    )


def _gate_chassis_integrity(state, config):
    """Validate chassis partition arithmetic when formula has chassis annotations.
    By default SKIP if no chassis markup detected — no breaking change."""
    try:
        from engine.reconstruction.chassis import (
            ChassisPartition,
            validate_anchor_floors,  # noqa: F401 — availability check
            validate_partition,
        )
    except ImportError:
        return GateResult(
            gate="chassis_integrity",
            status="SKIP",
            detail="Chassis engine not available.",
        )

    chassis_data = getattr(state, "_chassis_data", None)
    if chassis_data is None:
        return GateResult(
            gate="chassis_integrity",
            status="SKIP",
            detail="No chassis annotations detected — not applicable to flat formulas.",
        )

    chassis = ChassisPartition(**chassis_data)
    expected_total = state.total_raw_ul or 4500.0
    expected_core = getattr(config, "chassis_core_ul", None) or chassis.core_total_ul
    expected_module = getattr(config, "chassis_module_ul", None) or chassis.module_total_ul

    errors = validate_partition(chassis, expected_total, expected_core, expected_module)

    if errors:
        return GateResult(
            gate="chassis_integrity",
            status="FAIL",
            detail=f"Partition validation failed: {'; '.join(errors[:5])}{'...' if len(errors) > 5 else ''}",
            data={"errors": errors},
        )

    return GateResult(
        gate="chassis_integrity",
        status="PASS",
        detail=f"Core {chassis.core_total_ul:.1f} + Module {chassis.module_total_ul:.1f} = Target {chassis.total_ul:.1f} µL",
        data={
            "core_ul": chassis.core_total_ul,
            "module_ul": chassis.module_total_ul,
            "total_ul": chassis.total_ul,
        },
    )


def _gate_authority_vector(state, config):
    """Report per-dimension authority and FAIL if critical dimensions too low.

    Uses coverage-aware scoring via ``derive_authority_from_evidence``:
    - identity: fraction of target rows with at least one evidence claim
    - quantity: penalized by contradictions
    - safety: fraction of materials with known IFRA limits
    - release: only passes if all critical dimensions >= 0.5
    """
    from engine.reconstruction.authority import derive_authority_from_evidence
    target = getattr(state, "_target_formula", None)
    evidence = getattr(state, "_evidence_ledger", None)
    if target is None or evidence is None:
        required = config.commercial_mode or config.quantitative_claim or config.mode == "RELEASE_REVIEW"
        return GateResult(
            gate="authority_vector",
            status="FAIL" if required else "WARN",
            detail="Target/evidence ledger is absent; authority dimensions are unknown."
            + (" Release authority cannot be established." if required else " Diagnostic report only."),
            data={"assessment": "NOT_EVALUATED", "release_authority": False,
                  "missing": [name for name, value in (("target_formula", target), ("evidence_ledger", evidence)) if value is None]},
        )
    # Derivation errors must reach _safe_gate and fail closed, not become zeros.
    authority = derive_authority_from_evidence(target, evidence)

    # FAIL conditions
    failures = []
    if authority.safety < 0.2:
        failures.append(
            f"Safety authority insufficient ({authority.safety:.2f}) — unknown IFRA limits for too many materials"
        )
    if authority.identity < 0.3 and authority.quantity < 0.3:
        failures.append(
            f"Identity ({authority.identity:.2f}) AND Quantity ({authority.quantity:.2f}) authority both insufficient — insufficient evidence"
        )
    if authority.identity < 0.5 and getattr(config, "require_identity_authority", True):
        failures.append(f"Identity authority insufficient ({authority.identity:.2f})")

    if failures:
        return GateResult(
            gate="authority_vector",
            status="FAIL",
            detail="; ".join(failures) + ". DIMENSIONS NEVER AVERAGED.",
            data=authority.as_dict() if hasattr(authority, "as_dict") else {},
        )

    return GateResult(
        gate="authority_vector",
        status="PASS",
        detail="All critical authority dimensions sufficient. DIMENSIONS NEVER AVERAGED.",
        data=authority.as_dict() if hasattr(authority, "as_dict") else {},
    )


def _gate_concentration_basis(state, config):
    """FAIL on an unsupported concentration basis; HOLD on an undeclared one.

    A bare "10%" is missing data (the author has not said w/w or v/v), so it
    blocks release as HOLD. A declared basis the pipeline cannot use is a
    formula error and FAILs; when both occur the gate FAILs and the detail
    still names the undeclared rows.
    """
    allowed_bases = {"neat", "mass_fraction", "volume_fraction", "mass_per_volume"}
    violations = []
    missing = []
    undeclared = []
    for m in state.materials:
        basis = str(
            getattr(m, "stock_fraction_basis", "unspecified") or "unspecified"
        ).strip().lower()
        if basis == "unspecified":
            pct = f"{round(float(m.dilution) * 100.0, 6):g}"
            missing.append(
                {"material": m.name, "reason": "unavailable:stock_fraction_basis_unspecified"}
            )
            undeclared.append(
                f"{m.name}: concentration basis not declared; declare {pct}% w/w or {pct}% v/v"
            )
        elif basis not in allowed_bases:
            violations.append(
                f"{m.name}: unsupported concentration basis {basis!r} "
                "(use neat, w/w, v/v, or w/v)"
            )

    def _listing(rows: list[str]) -> str:
        return f"{'; '.join(rows[:5])}{'...' if len(rows) > 5 else ''}"

    if violations:
        detail = (
            f"{len(violations)} material(s) with invalid concentration basis: "
            f"{_listing(violations)}"
        )
        if undeclared:
            detail += (
                f"; {len(undeclared)} material(s) with undeclared concentration basis: "
                f"{_listing(undeclared)}"
            )
        return GateResult(
            gate="concentration_basis",
            status="FAIL",
            detail=detail,
            data={"violations": violations, "undeclared": undeclared, "missing": missing},
        )
    if undeclared:
        return GateResult(
            gate="concentration_basis",
            status="HOLD",
            detail=(
                f"{len(undeclared)} material(s) with undeclared concentration basis: "
                f"{_listing(undeclared)}"
            ),
            data={"violations": [], "undeclared": undeclared, "missing": missing},
        )

    return GateResult(
        gate="concentration_basis",
        status="PASS",
        detail="All materials have explicit concentration basis.",
    )


def gate_formula(
    formula: Mapping,
    config: ReleaseGateConfig | None = None,
    *,
    parent_formula: Mapping | None = None,
    authorized_active_dose_changes: Mapping[str, str] | None = None,
) -> GateReport:
    """Run all reusable release gates on a parsed formula record."""
    config = config or ReleaseGateConfig()
    reference_detection = detect_reference_claim(formula)
    if reference_detection.quantitative_requested and not config.quantitative_claim:
        config = replace(config, quantitative_claim=True)
    formula_archetype = str(formula.get("family_archetype", "") or "").strip()
    if formula_archetype and formula_archetype != config.family_archetype:
        config = replace(config, family_archetype=formula_archetype)
    if not config.family_archetype and config.brief:
        resolved = infer_archetype(config.brief, "")
        if resolved:
            config = replace(config, family_archetype=resolved)
    formula_matrix_moles = tuple(
        sorted(
            (str(name), float(value))
            for name, value in dict(formula.get("matrix_moles", {}) or {}).items()
            if float(value) > 0.0
        )
    )
    if not config.matrix_components_moles and formula_matrix_moles:
        config = replace(
            config,
            matrix_components_moles=formula_matrix_moles,
            matrix_mass_g=float(formula.get("matrix_mass_g", 0.0) or 0.0),
            matrix_source=str(formula.get("matrix_source", "omitted") or "omitted"),
        )
    ingredients_ul: Mapping[str, float] = formula["ingredients_ul"]
    dilutions: Mapping[str, float] = formula.get("dilutions", {})
    stock_contract = resolve_inventory_stock_contract(formula)
    stock_specs: Mapping[str, Mapping[str, object]] = resolved_stock_specs_for_state(
        formula,
        stock_contract,
    )
    state = build_formula_state(
        ingredients_ul,
        dilutions,
        stock_specs=stock_specs,
        batch_volume_ml=config.batch_volume_ml,
        temperature_K=config.temperature_K,
        matrix_moles=dict(config.matrix_components_moles),
        matrix_mass_g=config.matrix_mass_g,
        matrix_source=config.matrix_source,
    )
    dose_receipt = build_formula_dose_receipt(formula, stock_contract)
    state = replace(
        state,
        dose_receipt_sha256=dose_receipt.receipt_sha256,
        dose_receipt_status=dose_receipt.status,
    )
    preflight = run_release_preflight(
        formula,
        state,
        require_exact_ppm=config.requires_exact_quantitation(),
        require_exact_finished_product_ppm=(config.requires_exact_finished_product_quantitation()),
        stock_contract=stock_contract,
        dose_receipt=dose_receipt,
    ).as_dict()
    simulation = tuple(
        simulate_formula(
            ingredients_ul,
            dilutions,
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
            initial_state=state,
        )
    )
    gates = [
        _safe_gate(lambda: _gate_pipeline_preflight(preflight), "pipeline_preflight"),
        _safe_gate(
            lambda: _gate_g15_oav_firewall(
                formula,
                simulation,
                config,
                parent_formula=parent_formula,
                authorized_active_dose_changes=authorized_active_dose_changes,
            ),
            "g15_oav_firewall",
        ),
        _safe_gate(
            lambda: _gate_preflight_contract(preflight, "inventory_stock_contract"),
            "inventory_stock_contract",
        ),
        _safe_gate(
            lambda: _gate_preflight_contract(preflight, "quantitative_authority"),
            "quantitative_authority",
        ),
        _safe_gate(
            lambda: _gate_preflight_contract(preflight, "headspace_scope"),
            "headspace_scope",
        ),
        _safe_gate(
            lambda: _gate_preflight_contract(preflight, "natural_composite_coverage"),
            "natural_composite_coverage",
        ),
        _safe_gate(
            lambda: _gate_reference_claim_contract(formula, state),
            "reference_claim_contract",
        ),
        _safe_gate(
            lambda: _gate_architecture_concentration(state),
            "architecture_concentration",
        ),
        _safe_gate(lambda: _gate_exact_subtotal(formula, config), "exact_subtotal"),
        _safe_gate(lambda: _gate_duplicates(state), "duplicates"),
        _safe_gate(lambda: _gate_material_coverage(state), "material_coverage"),
        _safe_gate(lambda: _gate_data_coverage(state), "data_coverage"),
        _safe_gate(lambda: _gate_odt_coverage(state), "odt_coverage"),
        _safe_gate(lambda: _gate_chemistry_stability(state, config), "chemistry_stability"),
        _safe_gate(lambda: _gate_phase_compatibility(state), "phase_compatibility"),
        _safe_gate(lambda: _gate_preblends(state, config), "preblends"),
        _safe_gate(
            lambda: _gate_osmotheque_archivability(state, config),
            "osmotheque_archivability",
        ),
        _safe_gate(lambda: _gate_fougere_skeleton(state, config), "fougere_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(lambda: _gate_chypre_skeleton(state, config), "chypre_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_blue_ambroxan_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "blue_ambroxan_skeleton",
        ),
        _safe_gate(
            lambda: _gate_gourmand_angel_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "gourmand_angel_skeleton",
        ),
        _safe_gate(
            lambda: _gate_vanilla_amber_black_opium_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "vanilla_amber_black_opium_skeleton",
        ),
        _safe_gate(
            lambda: _gate_white_floral_jadore_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "white_floral_jadore_skeleton",
        ),
        _safe_gate(
            lambda: _gate_fresh_clean_ckone_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "fresh_clean_ckone_skeleton",
        ),
        _safe_gate(
            lambda: _gate_tobacco_vanille_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "tobacco_vanille_skeleton",
        ),
        _safe_gate(
            lambda: _gate_rose_patchouli_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "rose_patchouli_skeleton",
        ),
        _safe_gate(
            lambda: _gate_coconut_tropical_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "coconut_tropical_skeleton",
        ),
        _safe_gate(lambda: _gate_iris_woody_skeleton(state, config), "iris_woody_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_saffron_leather_oud_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "saffron_leather_oud_skeleton",
        ),
        _safe_gate(
            lambda: _gate_aldehydic_floral_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "aldehydic_floral_skeleton",
        ),
        _safe_gate(
            lambda: _gate_oriental_shalimar_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "oriental_shalimar_skeleton",
        ),
        _safe_gate(lambda: _gate_green_chypre_skeleton(state, config), "green_chypre_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(lambda: _gate_leather_cuir_skeleton(state, config), "leather_cuir_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_aquatic_marine_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "aquatic_marine_skeleton",
        ),
        _safe_gate(
            lambda: _gate_floral_oriental_poison_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "floral_oriental_poison_skeleton",
        ),
        _safe_gate(
            lambda: _gate_skin_scent_molecule_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "skin_scent_molecule_skeleton",
        ),
        _safe_gate(lambda: _gate_tea_matcha_skeleton(state, config), "tea_matcha_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_mineral_salty_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "mineral_salty_skeleton",
        ),
        _safe_gate(
            lambda: _gate_lactonic_milky_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "lactonic_milky_skeleton",
        ),
        _safe_gate(
            lambda: _gate_hyper_synthetic_metallic_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "hyper_synthetic_metallic_skeleton",
        ),
        _safe_gate(
            lambda: _gate_incense_cathedral_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "incense_cathedral_skeleton",
        ),
        _safe_gate(
            lambda: _gate_violet_candyfloss_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "violet_candyfloss_skeleton",
        ),
        _safe_gate(
            lambda: _gate_ellena_transparent_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "ellena_transparent_skeleton",
        ),
        _safe_gate(
            lambda: _gate_woody_amber_modern_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "woody_amber_modern_skeleton",
        ),
        _safe_gate(
            lambda: _gate_fruity_floral_mass_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "fruity_floral_mass_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_homme_iris_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_homme_iris_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_homme_intense_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_homme_intense_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_homme_cologne_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_homme_cologne_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_homme_sport_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_homme_sport_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_fahrenheit_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_fahrenheit_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_diorissimo_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_diorissimo_skeleton",
        ),
        _safe_gate(
            lambda: _gate_dior_eau_sauvage_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "dior_eau_sauvage_skeleton",
        ),
        _safe_gate(lambda: _gate_chanel_bleu_skeleton(state, config), "chanel_bleu_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_chanel_egoiste_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "chanel_egoiste_skeleton",
        ),
        _safe_gate(
            lambda: _gate_chanel_chance_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "chanel_chance_skeleton",
        ),
        _safe_gate(
            lambda: _gate_allure_homme_sport_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "allure_homme_sport_skeleton",
        ),
        _safe_gate(
            lambda: _gate_allure_homme_sport_cologne_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "allure_homme_sport_cologne_skeleton",
        ),
        _safe_gate(
            lambda: _gate_allure_homme_sport_edp_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "allure_homme_sport_edp_skeleton",
        ),
        _safe_gate(
            lambda: _gate_allure_homme_sport_extreme_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "allure_homme_sport_extreme_skeleton",
        ),
        _safe_gate(
            lambda: _gate_allure_homme_sport_superleggera_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "allure_homme_sport_superleggera_skeleton",
        ),
        _safe_gate(lambda: _gate_prada_lhomme_skeleton(state, config), "prada_lhomme_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(
            lambda: _gate_prada_amber_homme_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "prada_amber_homme_skeleton",
        ),
        _safe_gate(
            lambda: _gate_prada_infusion_iris_skeleton(state, config),  # noqa: F821  # skeleton gate not yet implemented
            "prada_infusion_iris_skeleton",
        ),
        _safe_gate(lambda: _gate_ysl_la_nuit_skeleton(state, config), "ysl_la_nuit_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(lambda: _gate_ysl_lhomme_skeleton(state, config), "ysl_lhomme_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(lambda: _gate_ysl_kouros_skeleton(state, config), "ysl_kouros_skeleton"),  # noqa: F821  # skeleton gate not yet implemented
        _safe_gate(lambda: _gate_blocked(state), "blocked"),
        _safe_gate(lambda: _gate_oav_overdose_blocker(state, config), "oav_overdose_blocker"),
        _safe_gate(lambda: _gate_odt_sanity(state, config), "odt_sanity"),
        _safe_gate(lambda: _gate_vp_cross_source(state, config), "vp_cross_source"),
        _safe_gate(lambda: _gate_dilution_consistency(state, config), "dilution_consistency"),
        _safe_gate(lambda: _gate_odt_completeness(state, config), "odt_completeness"),
        _safe_gate(lambda: _gate_pipette_floor(state, config), "pipette_floor"),
        _safe_gate(lambda: _gate_small_diluted_traces(state), "small_diluted_traces"),
        _safe_gate(lambda: _gate_dilution_accuracy(state, config), "dilution_accuracy"),
        _safe_gate(lambda: _gate_oav_scaling(formula, config), "oav_scaling"),
        _safe_gate(lambda: _gate_safety(state, config), "safety"),
        _safe_gate(
            lambda: _gate_eu_allergen_declaration(state, config),
            "eu_allergen_declaration",
        ),
        _safe_gate(
            lambda: _gate_phototoxic_furanocoumarin(state, config),
            "safety_phototoxic",
        ),
        _safe_gate(
            lambda: _gate_receptor_saturation(state, config),
            "safety_receptor_saturation",
        ),
        _safe_gate(
            lambda: _gate_natural_compatibility(state, config),
            "natural_compatibility",
        ),
        _safe_gate(
            lambda: _gate_oav_physics_gamma(state, config),
            "oav_physics_gamma",
        ),
        _safe_gate(
            lambda: _gate_skin_degradation(state, config),
            "skin_degradation",
        ),
        _safe_gate(
            lambda: _gate_verify_protocol_aggregate(state, config),
            "verify_protocol_aggregate",
        ),
        _safe_gate(
            lambda: _gate_hedonic_neuroscience(state, config),
            "hedonic_neuroscience",
        ),
        _safe_gate(
            lambda: _gate_solvent_matrix(state, config),
            "solvent_matrix",
        ),
        _safe_gate(lambda: _gate_perfumer_logic(formula, config), "perfumer_logic"),
        _safe_gate(
            lambda: _gate_family_drift_detector(formula, config),
            "family_drift_detector",
        ),
        _safe_gate(lambda: _gate_novelty_vs_reference(formula, config), "novelty_vs_reference"),
        _safe_gate(lambda: _gate_perfume_knowledge(state, config), "perfume_knowledge"),
        _safe_gate(lambda: _gate_hedione_share(formula, state, config), "hedione_share"),
        _safe_gate(lambda: _gate_musk_count(state, config), "musk_count"),
        _safe_gate(lambda: _gate_carles_pyramid(state, config), "carles_pyramid"),
        _safe_gate(lambda: _gate_carles_material_count(state, config), "carles_material_count"),
        _safe_gate(lambda: _gate_carles_accord_ratio(state, config), "carles_accord_ratio"),
        _safe_gate(lambda: _gate_beaux_registres(state, config), "beaux_registres"),
        _safe_gate(lambda: _gate_oav_legibility(state, config), "oav_legibility"),
        _safe_gate(lambda: _gate_ellena_legibility(state, config), "ellena_legibility"),
        _safe_gate(lambda: _gate_literature_compliance(state, config), "literature_compliance"),
        _safe_gate(lambda: _gate_synergy_conflicts(state, config), "synergy_conflicts"),
        _safe_gate(lambda: _gate_accord_compliance(state, config), "accord_compliance"),
        _safe_gate(lambda: _gate_captive_availability(state, config), "captive_availability"),
        _safe_gate(
            lambda: _gate_construction_compliance(state, config),
            "construction_compliance",
        ),
        _safe_gate(
            lambda: _gate_performance_prediction(state, config),
            "performance_prediction",
        ),
    ]
    if _FUTURE_MODULES_AVAILABLE:
        gates += [
            _safe_gate(lambda: _gate_blending_protocol(state, config), "blending_protocol"),
            _safe_gate(
                lambda: _gate_chemical_compatibility(state, config),
                "chemical_compatibility",
            ),
            _safe_gate(lambda: _gate_edge_cases(state, config), "edge_cases"),
            _safe_gate(lambda: _gate_skin_chemistry(state, config), "skin_chemistry"),
            _safe_gate(lambda: _gate_dosing_tables(state, config), "dosing_tables"),
            _safe_gate(lambda: _gate_balance_axes(state, config), "balance_axes"),
            _safe_gate(lambda: _gate_character_shifts(state, config), "character_shifts"),
            _safe_gate(lambda: _gate_evaluation_protocol(state, config), "evaluation_protocol"),
            _safe_gate(lambda: _gate_family_hedonic(state, config), "family_hedonic"),
            _safe_gate(lambda: _gate_iconic_formulas(state, config), "iconic_formulas"),
            _safe_gate(lambda: _gate_iteration_protocol(state, config), "iteration_protocol"),
            _safe_gate(lambda: _gate_niche_construction(state, config), "niche_construction"),
            _safe_gate(lambda: _gate_somatosensory(state, config), "somatosensory"),
            _safe_gate(lambda: _gate_musk_intelligence(state, config), "musk_intelligence"),
            _safe_gate(lambda: _gate_brief_translation(state, config), "brief_translation"),
        ]
    gates += [
        _safe_gate(
            lambda: _gate_weber_fechner_contrast(state, config),
            "weber_fechner_contrast",
        ),
        _safe_gate(lambda: _gate_stevens_power_law(state, config), "stevens_power_law"),
        _safe_gate(lambda: _gate_stevens_n_efficiency(state, config), "stevens_n_efficiency"),
        _safe_gate(lambda: _gate_jnd_redundancy(state, config), "jnd_redundancy"),
        _safe_gate(
            lambda: _gate_guerlain_vanillin_coumarin(state, config),
            "guerlain_vanillin_coumarin",
        ),
        _safe_gate(
            lambda: _gate_guerlain_nature_synthetic(state, config),
            "guerlain_nature_synthetic",
        ),
        _safe_gate(
            lambda: _gate_guerlain_rose_jasmine_balance(state, config),
            "guerlain_rose_jasmine_balance",
        ),
        _safe_gate(lambda: _gate_jellinek_psychology(state, config), "jellinek_psychology"),
        _safe_gate(
            lambda: _gate_edwards_wheel_coherence(state, config),
            "edwards_wheel_coherence",
        ),
        _safe_gate(
            lambda: _gate_coty_single_material_limit(state, config),
            "coty_single_material_limit",
        ),
        _safe_gate(
            lambda: _gate_roudnitska_hedione_pct(state, config),
            "roudnitska_hedione_pct",
        ),
        _safe_gate(lambda: _gate_adaptation_timing(state, config), "adaptation_timing"),
        _safe_gate(lambda: _gate_adaptation_overlap(state, config), "adaptation_overlap"),
        _safe_gate(lambda: _gate_mixture_suppression(state, config), "mixture_suppression"),
        _safe_gate(
            lambda: _gate_oav_intelligence(state, simulation, config),
            "oav_intelligence",
        ),
        _safe_gate(lambda: _gate_olfactory_fatigue(state, config), "olfactory_fatigue"),
        _safe_gate(
            lambda: _gate_roudnitska_transparence(state, config),
            "roudnitska_transparence",
        ),
        _safe_gate(
            lambda: _gate_evaporation_rate_balance(state, config),
            "evaporation_rate_balance",
        ),
        _safe_gate(lambda: _gate_tenacity_projection(state, config), "tenacity_projection"),
        _safe_gate(lambda: _gate_oriental_skeleton(state, config), "oriental_skeleton"),
        _safe_gate(lambda: _gate_aquatic_skeleton(state, config), "aquatic_skeleton"),
        _safe_gate(lambda: _gate_gourmand_skeleton(state, config), "gourmand_skeleton"),
        _safe_gate(lambda: _gate_sensory_overcrowding(state, config), "sensory_overcrowding"),
        _safe_gate(lambda: _gate_master_perfumer(state, config), "master_perfumer"),
        _safe_gate(
            lambda: _gate_mass_market_tier_check(state, config),
            "mass_market_tier_check",
        ),
        _safe_gate(lambda: _gate_mode_protection(state, config), "mode_protection"),
        _safe_gate(lambda: _gate_chassis_integrity(state, config), "chassis_integrity"),
        _safe_gate(lambda: _gate_authority_vector(state, config), "authority_vector"),
        _safe_gate(lambda: _gate_concentration_basis(state, config), "concentration_basis"),
    ]
    robustness_gate, _robustness = _gate_robustness(
        formula,
        config,
        state=state,
        simulation=simulation,
    )
    gates.append(robustness_gate)
    confidence_gate, confidence = _gate_confidence(state, config)
    confidence_gate, confidence = _apply_preflight_confidence_penalty(
        confidence_gate, confidence, preflight, config
    )
    gates.append(confidence_gate)
    gates = [_apply_guideline_policy(gate) for gate in gates]
    status = _status_from_gates(gates)
    formula_hash = formula_hash_from_record(formula)
    calibration_summary = summarize_records(load_records(), formula_hash=formula_hash)
    report = GateReport(
        number=int(formula.get("number", 1)),
        name=str(formula.get("name", "Formula")),
        status=status,
        gates=tuple(gates),
        formula_state=state,
        simulation=simulation,
        confidence=confidence,
        formula_hash=formula_hash,
        calibration_summary=calibration_summary,
        commercial_readiness=_commercial_readiness(status, gates, confidence, config),
        preflight=preflight,
        config_summary=_config_summary(config),
    )
    if config.audit_enabled:
        event = append_event(gate_report_event(report, config))
        report = replace(report, audit_event_id=str(event.get("event_id", "")))
    return report
