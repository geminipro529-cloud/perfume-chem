"""Perfumery Art & Composition Topology v1.

This layer composes the existing construction-complexity profile with the
Universal Perceptual Topology Core.  It expresses target shape, hierarchy,
ratio hypotheses, and controlled comparisons.  It cannot choose a final
formula or promote modeled physics into sensory or hedonic truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.perception.construction_complexity import ConstructionComplexityProfile
from engine.perception.perceptual_topology import (
    TopologyCoreRequest,
    TopologyCoreResult,
    TopologyState,
    evaluate_perceptual_topology,
)
from engine.scientific_contract import EvidenceDescriptor

_REQUIRED_TIMEPOINTS = ("0m", "5m", "30m", "2h", "8h", "24h")
_BINARY_RATIOS = ("9:1", "7:3", "5:5", "3:7", "1:9")


class HierarchyRole(str, Enum):
    SUBJECT = "SUBJECT"
    SUPPORT = "SUPPORT"
    BRIDGE = "BRIDGE"
    SHADOW = "SHADOW"
    STRUCTURAL = "STRUCTURAL"
    RESIDUE = "RESIDUE"


class CompositionOperator(str, Enum):
    RATIO_SWEEP = "RATIO_SWEEP"
    DOMINANCE_SHIFT = "DOMINANCE_SHIFT"
    SUBORDINATE_SUPPORT = "SUBORDINATE_SUPPORT"
    REGISTER_SEPARATION = "REGISTER_SEPARATION"
    DENSITY_REDUCTION = "DENSITY_REDUCTION"
    DENSITY_CONSTRUCTION = "DENSITY_CONSTRUCTION"
    APERTURE_OPEN = "APERTURE_OPEN"
    APERTURE_CLOSE = "APERTURE_CLOSE"
    EDGE_SHARPEN = "EDGE_SHARPEN"
    EDGE_ROUND = "EDGE_ROUND"
    CONTRAST_INSERT = "CONTRAST_INSERT"
    SHADOW_INSERT = "SHADOW_INSERT"
    AIR_INSERT = "AIR_INSERT"
    BRIDGE_INSERT = "BRIDGE_INSERT"
    BRIDGE_REMOVE = "BRIDGE_REMOVE"
    REDUNDANT_BASE_PRUNE = "REDUNDANT_BASE_PRUNE"
    TEMPORAL_RELAY = "TEMPORAL_RELAY"
    DELAYED_REVEAL = "DELAYED_REVEAL"
    RESIDUE_RECONTEXTUALIZE = "RESIDUE_RECONTEXTUALIZE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _unique_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class ArtShapeWindow:
    """Qualitative composition notation, never a measured sensory vector."""

    timepoint: str
    focus: str
    width: str
    density: str
    edge: str
    texture: tuple[str, ...]
    contrast: str
    shadow: str
    air: str
    tail: str

    def __post_init__(self) -> None:
        for field_name in (
            "timepoint",
            "focus",
            "width",
            "density",
            "edge",
            "contrast",
            "shadow",
            "air",
            "tail",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "texture",
            _unique_text(self.texture, "texture"),
        )
        if not self.texture:
            raise ValueError("texture must not be empty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "timepoint": self.timepoint,
            "focus": self.focus,
            "width": self.width,
            "density": self.density,
            "edge": self.edge,
            "texture": list(self.texture),
            "contrast": self.contrast,
            "shadow": self.shadow,
            "air": self.air,
            "tail": self.tail,
            "measurement_authority": False,
        }


@dataclass(frozen=True, slots=True)
class HierarchyEntry:
    function_id: str
    role: HierarchyRole

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "function_id",
            _text(self.function_id, "function_id"),
        )
        object.__setattr__(self, "role", HierarchyRole(self.role))

    def as_dict(self) -> dict[str, str]:
        return {"function_id": self.function_id, "role": self.role.value}


@dataclass(frozen=True, slots=True)
class RatioHypothesis:
    function_a: str
    function_b: str
    total_active_load_ref: str
    evidence: EvidenceDescriptor
    ratios: tuple[str, ...] = _BINARY_RATIOS
    local_refinement_required: bool = True

    def __post_init__(self) -> None:
        for field_name in ("function_a", "function_b", "total_active_load_ref"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if self.function_a == self.function_b:
            raise ValueError("ratio functions must be different")
        object.__setattr__(self, "ratios", _unique_text(self.ratios, "ratios"))
        if self.ratios != _BINARY_RATIOS:
            raise ValueError("binary ratio sweep must be 9:1, 7:3, 5:5, 3:7, 1:9")
        if not isinstance(self.evidence, EvidenceDescriptor):
            raise TypeError("evidence must be an EvidenceDescriptor")
        if self.local_refinement_required is not True:
            raise ValueError("local ratio refinement must remain required")

    def as_dict(self) -> dict[str, Any]:
        return {
            "function_a": self.function_a,
            "function_b": self.function_b,
            "ratios": list(self.ratios),
            "constraint": "CONSTANT_TOTAL_ACTIVE_LOAD",
            "total_active_load_ref": self.total_active_load_ref,
            "local_refinement_required": self.local_refinement_required,
            "evidence": self.evidence.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ArtTopologyRequest:
    core_request: TopologyCoreRequest
    construction_profile: ConstructionComplexityProfile
    target_shape: tuple[ArtShapeWindow, ...]
    hierarchy: tuple[HierarchyEntry, ...]
    ratio_hypotheses: tuple[RatioHypothesis, ...]
    operators: tuple[CompositionOperator, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.core_request, TopologyCoreRequest):
            raise TypeError("core_request must be a TopologyCoreRequest")
        if not isinstance(self.construction_profile, ConstructionComplexityProfile):
            raise TypeError("construction_profile must be a ConstructionComplexityProfile")
        typed_tuples = (
            ("target_shape", ArtShapeWindow),
            ("hierarchy", HierarchyEntry),
            ("ratio_hypotheses", RatioHypothesis),
            ("operators", CompositionOperator),
        )
        for field_name, expected_type in typed_tuples:
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise TypeError(f"{field_name} must be a tuple")
            if not values:
                raise ValueError(f"{field_name} must not be empty")
            if any(not isinstance(item, expected_type) for item in values):
                raise TypeError(f"{field_name} must contain {expected_type.__name__} values")
        timepoints = tuple(item.timepoint for item in self.target_shape)
        if len(timepoints) != len(set(timepoints)):
            raise ValueError("target_shape timepoints must be unique")
        hierarchy_ids = tuple(item.function_id for item in self.hierarchy)
        if len(hierarchy_ids) != len(set(hierarchy_ids)):
            raise ValueError("hierarchy function IDs must be unique")
        if len(self.operators) != len(set(self.operators)):
            raise ValueError("operators must not contain duplicates")


def _mandatory_tests() -> dict[str, Any]:
    return {
        "binary_ratio": {
            "ratios": list(_BINARY_RATIOS),
            "constraint": "CONSTANT_TOTAL_ACTIVE_LOAD",
        },
        "local_ratio_refinement": {"around_selected_region": True},
        "ternary": {
            "design": "CONSTRAINED_MIXTURE_SIMPLEX",
            "only_after_binary_screen": True,
        },
        "ablation": {"replace_removed_mass_with_neutral_carrier": True},
        "perturbation_percent": [-30, -20, -10, 0, 10, 20, 30],
        "transparency_congestion_pair": {
            "same_subject": True,
            "same_total_active_load": True,
        },
        "temporal": {"timepoints": list(_REQUIRED_TIMEPOINTS)},
        "population": {
            "assessor_identity": "REQUIRED",
            "anosmia_or_low_sensitivity_log": "REQUIRED",
        },
    }


@dataclass(frozen=True, slots=True)
class ArtTopologyResult:
    request: ArtTopologyRequest
    core_result: TopologyCoreResult
    state: TopologyState
    blockers: tuple[str, ...]
    empirical_pass: bool = field(default=False, init=False)
    final_formula_authority: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    physical_liking_authority: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    measured_headspace_authority: bool = field(default=False, init=False)
    strict_oav_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perfumery_art_composition_topology_v1",
            "state": self.state.value,
            "target_identity": self.request.core_request.target_identity,
            "ideal_topology_ref": self.request.core_request.ideal_topology_ref,
            "current_inventory_build_ref": (self.request.core_request.current_inventory_build_ref),
            "construction_profile_schema_version": (
                self.request.construction_profile.schema_version
            ),
            "inherits": [
                "UNIVERSAL_PERCEPTUAL_TOPOLOGY_CORE",
                "CONSTRUCTION_COMPLEXITY_PROFILE_V1",
                "MEANINGFUL_COMPLEXITY",
                "ANTI_COLLAPSE",
                "TARGET_FIRST_ARCHITECTURE",
                "ZERO_PASS_EMPIRICAL_TRUTH",
            ],
            "target_shape_contract": [item.as_dict() for item in self.request.target_shape],
            "hierarchy_map": [item.as_dict() for item in self.request.hierarchy],
            "ratio_hypotheses": [item.as_dict() for item in self.request.ratio_hypotheses],
            "composition_operators": [item.value for item in self.request.operators],
            "model_order": [
                "weighted_component_quality_baseline",
                "dominance_and_ratio_model",
                "observed_mixture",
                "replicated_higher_order_residual",
            ],
            "mandatory_tests": _mandatory_tests(),
            "hard_failures": [
                "equal_register_congestion",
                "universal_wood_musk_amber_chassis",
                "subject_erasure",
                "concentration_only_distinction",
                "unsupported_configural_claim",
                "complexity_by_count",
                "shadow_takeover",
                "disconnected_top_and_base",
                "generic_late_residue",
            ],
            "blockers": list(self.blockers),
            "oav_firewall": dict(self.core_result.oav_firewall),
            "final_integrator": ("SOL_5_6_XHIGH_UNTIL_BLINDED_BENCHMARK_PROVES_REPLACEMENT"),
            "physical_truth": "NOT_TESTED",
            "empirical_pass": self.empirical_pass,
            "final_formula_authority": self.final_formula_authority,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "physical_liking_authority": self.physical_liking_authority,
            "purchase_authority": self.purchase_authority,
            "safety_authority": self.safety_authority,
            "measured_headspace_authority": self.measured_headspace_authority,
            "strict_oav_authority": self.strict_oav_authority,
        }


def evaluate_art_topology(request: ArtTopologyRequest) -> ArtTopologyResult:
    """Validate a topology design and emit experiments, never formula edits."""

    if not isinstance(request, ArtTopologyRequest):
        raise TypeError("request must be an ArtTopologyRequest")
    core_result = evaluate_perceptual_topology(request.core_request)
    blockers = list(core_result.blockers)
    timepoints = tuple(item.timepoint for item in request.target_shape)
    missing_timepoints = tuple(item for item in _REQUIRED_TIMEPOINTS if item not in timepoints)
    if missing_timepoints:
        blockers.append("target temporal contour is missing: " + ", ".join(missing_timepoints))
    function_ids = set(request.core_request.function_ids)
    hierarchy_ids = {item.function_id for item in request.hierarchy}
    if hierarchy_ids != function_ids:
        blockers.append("hierarchy must cover each target-linked function exactly once")
    if sum(item.role is HierarchyRole.SUBJECT for item in request.hierarchy) != 1:
        blockers.append("hierarchy requires exactly one declared subject")
    for hypothesis in request.ratio_hypotheses:
        if {hypothesis.function_a, hypothesis.function_b} - function_ids:
            blockers.append("ratio hypothesis references an unknown topology function")
    return ArtTopologyResult(
        request=request,
        core_result=core_result,
        state=(TopologyState.HOLD if blockers else TopologyState.DESIGN_READY_NOT_EMPIRICAL),
        blockers=tuple(blockers),
    )


__all__ = [
    "ArtShapeWindow",
    "ArtTopologyRequest",
    "ArtTopologyResult",
    "CompositionOperator",
    "HierarchyEntry",
    "HierarchyRole",
    "RatioHypothesis",
    "evaluate_art_topology",
]
