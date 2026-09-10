"""Universal, target-first perceptual topology for Complex Perfumery.

The core is composition notation and experiment design, not a sensory model.
It preserves layer-specific functions, evidence scope, temporal hypotheses, and
anti-collapse rules without assigning beauty, liking, or perceived contribution.
Formula-bound OAV data may be attached only through the existing native OAV
gate binding and remains a downstream diagnostic firewall.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.scientific_contract import EvidenceDescriptor
from engine.scientific_validation.complexity_model_admission import OAVGateBinding

UNIVERSAL_DIMENSIONS = (
    "target_recognizer_integrity",
    "elemental_vs_configural_organization",
    "ratio_and_total_load_sensitivity",
    "dynamic_salience_structure",
    "contrast_and_negative_space",
    "temporal_transformation_and_handoff",
    "target_specific_persistence",
    "masking_suppression_and_adaptation",
    "anti_collapse",
)

MODEL_ORDER = (
    "weighted_linear_component_baseline",
    "strongest_component_baseline",
    "observed_mixture",
    "replicated_higher_order_residual",
)

SEPARATE_ENDPOINTS = (
    "component_recognition",
    "whole_profile_identity",
    "target_fidelity",
    "depth",
    "richness",
    "liking",
    "defect_intensity",
    "physical_release",
)


class TopologyState(str, Enum):
    """Design state; deliberately contains no empirical PASS value."""

    HOLD = "HOLD"
    DESIGN_READY_NOT_EMPIRICAL = "DESIGN_READY_NOT_EMPIRICAL"


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
class PerceptualFunction:
    """One target-linked function whose omission has a declared consequence."""

    function_id: str
    system_or_material: str
    target_function: str
    loss_if_omitted: str
    temporal_windows: tuple[str, ...]
    texture_axes: tuple[str, ...]
    nonredundancy_evidence: str
    evidence: EvidenceDescriptor

    def __post_init__(self) -> None:
        for field_name in (
            "function_id",
            "system_or_material",
            "target_function",
            "loss_if_omitted",
            "nonredundancy_evidence",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "temporal_windows",
            _unique_text(self.temporal_windows, "temporal_windows"),
        )
        object.__setattr__(
            self,
            "texture_axes",
            _unique_text(self.texture_axes, "texture_axes"),
        )
        if not self.temporal_windows:
            raise ValueError("temporal_windows must not be empty")
        if not self.texture_axes:
            raise ValueError("texture_axes must not be empty")
        if not isinstance(self.evidence, EvidenceDescriptor):
            raise TypeError("evidence must be an EvidenceDescriptor")

    def as_dict(self) -> dict[str, Any]:
        return {
            "function_id": self.function_id,
            "system_or_material": self.system_or_material,
            "target_function": self.target_function,
            "loss_if_omitted": self.loss_if_omitted,
            "temporal_windows": list(self.temporal_windows),
            "texture_axes": list(self.texture_axes),
            "nonredundancy_evidence": self.nonredundancy_evidence,
            "evidence": self.evidence.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class TopologyLayerContract:
    """A layer keeps native dimensions instead of inheriting literal 3-D axes."""

    layer_id: str
    target_function: str
    native_dimensions: tuple[str, ...]
    texture_contrasts: tuple[str, ...]
    failure_modes: tuple[str, ...]
    functions: tuple[PerceptualFunction, ...]

    def __post_init__(self) -> None:
        for field_name in ("layer_id", "target_function"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        for field_name in (
            "native_dimensions",
            "texture_contrasts",
            "failure_modes",
        ):
            object.__setattr__(
                self,
                field_name,
                _unique_text(getattr(self, field_name), field_name),
            )
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.functions, tuple):
            raise TypeError("functions must be a tuple")
        if not self.functions:
            raise ValueError("functions must not be empty")
        if any(not isinstance(item, PerceptualFunction) for item in self.functions):
            raise TypeError("functions must contain PerceptualFunction values")
        ids = tuple(item.function_id for item in self.functions)
        if len(ids) != len(set(ids)):
            raise ValueError("function IDs must be unique within a layer")

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "target_function": self.target_function,
            "native_dimensions": list(self.native_dimensions),
            "texture_contrasts": list(self.texture_contrasts),
            "failure_modes": list(self.failure_modes),
            "functions": [item.as_dict() for item in self.functions],
        }


@dataclass(frozen=True, slots=True)
class TopologyCoreRequest:
    """Target/ideal architecture stays separate from its inventory projection."""

    target_identity: str
    ideal_topology_ref: str
    current_inventory_build_ref: str
    target_recognizers: tuple[str, ...]
    layers: tuple[TopologyLayerContract, ...]
    oav_binding: OAVGateBinding | None = None
    component_count_used_as_depth: bool = False
    concentration_only_distinction: bool = False
    generic_chassis_substitution: bool = False
    empirical_pass_claimed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "target_identity",
            "ideal_topology_ref",
            "current_inventory_build_ref",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if self.ideal_topology_ref == self.current_inventory_build_ref:
            raise ValueError("ideal and current-inventory references must stay separate")
        object.__setattr__(
            self,
            "target_recognizers",
            _unique_text(self.target_recognizers, "target_recognizers"),
        )
        if not self.target_recognizers:
            raise ValueError("target_recognizers must not be empty")
        if not isinstance(self.layers, tuple):
            raise TypeError("layers must be a tuple")
        if not self.layers:
            raise ValueError("layers must not be empty")
        if any(not isinstance(item, TopologyLayerContract) for item in self.layers):
            raise TypeError("layers must contain TopologyLayerContract values")
        layer_ids = tuple(item.layer_id for item in self.layers)
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError("layer IDs must be unique")
        function_ids = tuple(
            function.function_id for layer in self.layers for function in layer.functions
        )
        if len(function_ids) != len(set(function_ids)):
            raise ValueError("function IDs must be unique across the topology")
        if self.oav_binding is not None and not isinstance(
            self.oav_binding,
            OAVGateBinding,
        ):
            raise TypeError("oav_binding must be an OAVGateBinding")
        for field_name in (
            "component_count_used_as_depth",
            "concentration_only_distinction",
            "generic_chassis_substitution",
            "empirical_pass_claimed",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")

    @property
    def function_ids(self) -> tuple[str, ...]:
        return tuple(function.function_id for layer in self.layers for function in layer.functions)


def _oav_firewall(binding: OAVGateBinding | None) -> dict[str, Any]:
    common = {
        "permitted_uses": [
            "dose_and_stock_anomaly_screen",
            "experiment_selection",
            "bounded_physical_release_hypothesis",
        ],
        "prohibited_uses": [
            "artistic_topology_decision",
            "automatic_formula_edit",
            "beauty_or_liking",
            "sensory_contribution_fraction",
            "target_similarity",
        ],
        "beauty_authority": False,
        "sensory_contribution_authority": False,
    }
    if binding is None:
        return {
            "state": "NOT_BOUND",
            "experiment_selection_authorized": False,
            "screening_blockers": [],
            "natural_composite_coverage_status": "NOT_BOUND",
            **common,
        }
    blockers = binding.screening_blockers
    return {
        "state": "HOLD" if blockers else "SCREEN_READY",
        "experiment_selection_authorized": not blockers,
        "screening_blockers": list(blockers),
        "natural_composite_coverage_status": (binding.natural_composite_coverage_status),
        "binding": binding.as_dict(),
        **common,
    }


@dataclass(frozen=True, slots=True)
class TopologyCoreResult:
    request: TopologyCoreRequest
    state: TopologyState
    blockers: tuple[str, ...]
    layer_ids: tuple[str, ...]
    oav_firewall: dict[str, Any]
    empirical_pass: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "universal_perceptual_topology_core_v1",
            "state": self.state.value,
            "target_identity": self.request.target_identity,
            "ideal_topology_ref": self.request.ideal_topology_ref,
            "current_inventory_build_ref": (self.request.current_inventory_build_ref),
            "target_recognizers": list(self.request.target_recognizers),
            "layers": [layer.as_dict() for layer in self.request.layers],
            "blockers": list(self.blockers),
            "contract": {
                "principle": (
                    "Target-linked information must survive and reorganize across "
                    "ratio, salience, contrast, interaction, and time."
                ),
                "universal_dimensions": list(UNIVERSAL_DIMENSIONS),
                "model_order": list(MODEL_ORDER),
                "higher_order_claim_gate": (
                    "Replicated departure from simpler baselines beyond assessor "
                    "and repeat uncertainty is required."
                ),
                "spatial_boundary": {
                    "foreground_background": ("SENSORY_HYPOTHESIS_UNTIL_MEASURED"),
                    "near_far_projection": ("NOT_TESTED_UNLESS_QUALIFIED_PHYSICAL_PROTOCOL"),
                    "literal_3d_internal_space": "CREATIVE_SHORTHAND_ONLY",
                },
                "complexity_rule": {
                    "component_count_is_depth": False,
                    "sparse_target_linked_depth_allowed": True,
                },
                "causal_program": {
                    "binary_ratios": ["4:1", "3:1", "1:1", "1:3", "1:4"],
                    "total_loads": ["LOW", "HIGH"],
                    "component_count_ladder": [1, 2, 4, 6, 8],
                    "ablation": "EQUAL_TOTAL_LOAD_CARRIER_REPLACEMENT",
                    "perturbation_percent": [-30, -20, -10, 0, 10, 20, 30],
                    "temporal_timepoints": ["0m", "5m", "30m", "2h", "8h", "24h"],
                    "extended_timepoint": "72h_for_persistent_systems",
                },
                "endpoints_kept_separate": list(SEPARATE_ENDPOINTS),
            },
            "oav_firewall": dict(self.oav_firewall),
            "empirical_pass": self.empirical_pass,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "safety_authority": self.safety_authority,
            "release_authority": self.release_authority,
        }


def evaluate_perceptual_topology(
    request: TopologyCoreRequest,
) -> TopologyCoreResult:
    """Validate a design packet without converting it into empirical truth."""

    if not isinstance(request, TopologyCoreRequest):
        raise TypeError("request must be a TopologyCoreRequest")
    blockers: list[str] = []
    if request.component_count_used_as_depth:
        blockers.append("component count cannot be used as evidence of depth")
    if request.concentration_only_distinction:
        blockers.append("concentration-only distinction is anti-collapse failure")
    if request.generic_chassis_substitution:
        blockers.append("generic wood-musk-amber chassis cannot replace target topology")
    if request.empirical_pass_claimed:
        blockers.append("a design packet cannot claim an empirical pass")
    return TopologyCoreResult(
        request=request,
        state=(TopologyState.HOLD if blockers else TopologyState.DESIGN_READY_NOT_EMPIRICAL),
        blockers=tuple(blockers),
        layer_ids=tuple(layer.layer_id for layer in request.layers),
        oav_firewall=_oav_firewall(request.oav_binding),
    )


__all__ = [
    "MODEL_ORDER",
    "SEPARATE_ENDPOINTS",
    "UNIVERSAL_DIMENSIONS",
    "PerceptualFunction",
    "TopologyCoreRequest",
    "TopologyCoreResult",
    "TopologyLayerContract",
    "TopologyState",
    "evaluate_perceptual_topology",
]
