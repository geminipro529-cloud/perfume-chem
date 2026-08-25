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
from itertools import combinations
from math import isclose, isfinite, sqrt
from typing import Any

from engine.pipeline.formula_state import FormulaState
from engine.pipeline.preflight import FormulaDoseReceipt
from engine.pipeline.simulator import SimulationFrame
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

FINAL_INTEGRATOR = "SOL_5_6_XHIGH_UNTIL_BLINDED_BENCHMARK_PROVES_REPLACEMENT"


class TopologyState(str, Enum):
    """Design state; deliberately contains no empirical PASS value."""

    HOLD = "HOLD"
    DESIGN_READY_NOT_EMPIRICAL = "DESIGN_READY_NOT_EMPIRICAL"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"


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
            "final_integrator": FINAL_INTEGRATOR,
            "final_acceptance_authority": False,
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


@dataclass(frozen=True, slots=True)
class TopologyMaterialBinding:
    """Map one canonical formula row to one target-linked function.

    The binding allocates the row for design accounting. It neither decomposes
    natural mixtures nor claims that the allocation is a perceived-contribution
    fraction.
    """

    material_name: str
    layer_id: str
    function_id: str
    evidence: EvidenceDescriptor

    def __post_init__(self) -> None:
        for field_name in ("material_name", "layer_id", "function_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.evidence, EvidenceDescriptor):
            raise TypeError("evidence must be an EvidenceDescriptor")

    def as_dict(self) -> dict[str, Any]:
        return {
            "material_name": self.material_name,
            "layer_id": self.layer_id,
            "function_id": self.function_id,
            "evidence": self.evidence.as_dict(),
            "allocation_authority": "TARGET_LINKED_DESIGN_ACCOUNTING_ONLY",
            "perceptual_contribution_authority": False,
        }


def _sorted_amounts(values: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(
        (key, round(float(value), 12))
        for key, value in sorted(values.items(), key=lambda item: item[0].casefold())
    )


@dataclass(frozen=True, slots=True)
class CurrentBuildProjection:
    """Receipt-bound projection of one current-inventory formula state."""

    core_request: TopologyCoreRequest
    dose_receipt: FormulaDoseReceipt
    bindings: tuple[TopologyMaterialBinding, ...]
    state: TopologyState
    blockers: tuple[str, ...]
    material_active_ul: tuple[tuple[str, float], ...]
    function_active_ul: tuple[tuple[str, float], ...]
    layer_active_ul: tuple[tuple[str, float], ...]
    temporal_material_active_ul: tuple[
        tuple[str, tuple[tuple[str, float], ...]], ...
    ]
    temporal_function_active_ul: tuple[
        tuple[str, tuple[tuple[str, float], ...]], ...
    ]
    empirical_pass: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    perceptual_contribution_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    @property
    def material_amounts(self) -> dict[str, float]:
        return dict(self.material_active_ul)

    @property
    def function_amounts(self) -> dict[str, float]:
        return dict(self.function_active_ul)

    @property
    def layer_amounts(self) -> dict[str, float]:
        return dict(self.layer_active_ul)

    @property
    def total_active_ul(self) -> float:
        return sum(self.material_amounts.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "current_inventory_topology_projection_v1",
            "state": self.state.value,
            "target_identity": self.core_request.target_identity,
            "ideal_topology_ref": self.core_request.ideal_topology_ref,
            "current_inventory_build_ref": self.core_request.current_inventory_build_ref,
            "formula_input_sha256": self.dose_receipt.formula_input_sha256,
            "dose_receipt_sha256": self.dose_receipt.receipt_sha256,
            "inventory_authority": {
                "status": self.dose_receipt.status,
                "snapshot_sha256": self.dose_receipt.inventory_snapshot_sha256,
                "source_workbook_sha256": (
                    self.dose_receipt.inventory_source_workbook_sha256
                ),
                "authority_sheet": self.dose_receipt.inventory_authority_sheet,
                "quantity_authority": "PLANNED_VOLUME_SCREEN_ONLY",
                "physical_metrology_authority": False,
                "release_authority": False,
            },
            "bindings": [binding.as_dict() for binding in self.bindings],
            "material_active_ul": dict(self.material_active_ul),
            "function_active_ul": dict(self.function_active_ul),
            "layer_active_ul": dict(self.layer_active_ul),
            "temporal_material_active_ul": {
                label: dict(values) for label, values in self.temporal_material_active_ul
            },
            "temporal_function_active_ul": {
                label: dict(values) for label, values in self.temporal_function_active_ul
            },
            "vector_basis": (
                "CANONICAL_ACTIVE_UL_ALLOCATION_DIAGNOSTIC_NOT_HEADSPACE_OR_SENSORY"
            ),
            "formula_identity_policy": (
                "ONE_CANONICAL_RECEIPT_ROW_PER_MATERIAL_NO_NATURAL_CONSTITUENT_EXPANSION"
            ),
            "blockers": list(self.blockers),
            "final_integrator": FINAL_INTEGRATOR,
            "final_acceptance_authority": False,
            "empirical_pass": self.empirical_pass,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "perceptual_contribution_authority": (
                self.perceptual_contribution_authority
            ),
            "release_authority": self.release_authority,
        }


def project_current_inventory_build(
    *,
    core_request: TopologyCoreRequest,
    dose_receipt: FormulaDoseReceipt,
    formula_state: FormulaState,
    bindings: tuple[TopologyMaterialBinding, ...],
    temporal_frames: tuple[SimulationFrame, ...] = (),
) -> CurrentBuildProjection:
    """Bind design topology to canonical active amounts without sensory claims."""

    if not isinstance(core_request, TopologyCoreRequest):
        raise TypeError("core_request must be a TopologyCoreRequest")
    if not isinstance(dose_receipt, FormulaDoseReceipt):
        raise TypeError("dose_receipt must be a FormulaDoseReceipt")
    if not isinstance(formula_state, FormulaState):
        raise TypeError("formula_state must be a FormulaState")
    if not isinstance(bindings, tuple) or any(
        not isinstance(item, TopologyMaterialBinding) for item in bindings
    ):
        raise TypeError("bindings must be a tuple of TopologyMaterialBinding values")
    if not isinstance(temporal_frames, tuple) or any(
        not isinstance(item, SimulationFrame) for item in temporal_frames
    ):
        raise TypeError("temporal_frames must be a tuple of SimulationFrame values")

    core_result = evaluate_perceptual_topology(core_request)
    blockers = list(core_result.blockers)
    expected_build_ref = f"CURRENT-INVENTORY:{dose_receipt.receipt_sha256}"
    if core_request.current_inventory_build_ref != expected_build_ref:
        blockers.append(
            "current inventory build reference is not bound to the dose receipt hash"
        )
    if dose_receipt.status != "BOUND":
        blockers.append(
            "inventory authority is not BOUND: " + "; ".join(dose_receipt.reasons)
        )

    receipt_by_name = {line.material_name.casefold(): line for line in dose_receipt.lines}
    state_by_name = {material.name.casefold(): material for material in formula_state.materials}
    binding_by_name: dict[str, TopologyMaterialBinding] = {}
    for binding in bindings:
        key = binding.material_name.casefold()
        if key in binding_by_name:
            blockers.append(
                f"{binding.material_name}: one canonical formula row cannot be allocated twice"
            )
        else:
            binding_by_name[key] = binding

    receipt_names = set(receipt_by_name)
    state_names = set(state_by_name)
    binding_names = set(binding_by_name)
    if state_names != receipt_names:
        missing = sorted(receipt_names - state_names)
        extra = sorted(state_names - receipt_names)
        if missing:
            blockers.append("canonical formula state is missing receipt rows: " + ", ".join(missing))
        if extra:
            blockers.append("canonical formula state has rows absent from receipt: " + ", ".join(extra))
    if binding_names != receipt_names:
        missing = sorted(receipt_names - binding_names)
        extra = sorted(binding_names - receipt_names)
        if missing:
            blockers.append("topology bindings are missing receipt rows: " + ", ".join(missing))
        if extra:
            blockers.append("topology bindings invent non-receipt rows: " + ", ".join(extra))

    layer_functions = {
        layer.layer_id: {function.function_id for function in layer.functions}
        for layer in core_request.layers
    }
    for binding in bindings:
        if binding.layer_id not in layer_functions:
            blockers.append(f"{binding.material_name}: topology binding uses an unknown layer")
        elif binding.function_id not in layer_functions[binding.layer_id]:
            blockers.append(
                f"{binding.material_name}: topology binding uses a function outside its layer"
            )

    material_amounts: dict[str, float] = {}
    function_amounts = {function_id: 0.0 for function_id in core_request.function_ids}
    layer_amounts = {layer.layer_id: 0.0 for layer in core_request.layers}
    for key in sorted(receipt_names & state_names):
        line = receipt_by_name[key]
        material = state_by_name[key]
        active_ul = float(material.active_ul)
        if line.active_ul is None or not isclose(
            active_ul,
            float(line.active_ul),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            blockers.append(
                f"{line.material_name}: canonical active amount does not match dose receipt"
            )
        material_amounts[line.material_name] = active_ul
        row_binding = binding_by_name.get(key)
        if row_binding is not None and row_binding.layer_id in layer_functions:
            function_amounts[row_binding.function_id] = (
                function_amounts.get(row_binding.function_id, 0.0) + active_ul
            )
            layer_amounts[row_binding.layer_id] = (
                layer_amounts.get(row_binding.layer_id, 0.0) + active_ul
            )

    labels = tuple(frame.label for frame in temporal_frames)
    times = tuple(float(frame.t_seconds) for frame in temporal_frames)
    if len(labels) != len(set(labels)):
        blockers.append("temporal frame labels must be unique")
    if times != tuple(sorted(times)) or any(not isfinite(value) or value < 0 for value in times):
        blockers.append("temporal frames must be increasing, finite, and nonnegative")
    temporal_material: list[tuple[str, tuple[tuple[str, float], ...]]] = []
    temporal_function: list[tuple[str, tuple[tuple[str, float], ...]]] = []
    for frame in temporal_frames:
        frame_by_name = {material.name.casefold(): material for material in frame.state.materials}
        invented = sorted(set(frame_by_name) - receipt_names)
        if invented:
            blockers.append(
                f"{frame.label}: temporal state invents non-receipt rows: " + ", ".join(invented)
            )
        frame_material_amounts: dict[str, float] = {}
        frame_function_amounts = {
            function_id: 0.0 for function_id in core_request.function_ids
        }
        for key, line in receipt_by_name.items():
            active_ul = float(frame_by_name[key].active_ul) if key in frame_by_name else 0.0
            initial_ul = material_amounts.get(line.material_name, 0.0)
            if active_ul > initial_ul + 1e-9:
                blockers.append(
                    f"{frame.label}:{line.material_name}: temporal active amount exceeds current build"
                )
            frame_material_amounts[line.material_name] = active_ul
            row_binding = binding_by_name.get(key)
            if row_binding is not None:
                frame_function_amounts[row_binding.function_id] = (
                    frame_function_amounts.get(row_binding.function_id, 0.0) + active_ul
                )
        temporal_material.append((frame.label, _sorted_amounts(frame_material_amounts)))
        temporal_function.append((frame.label, _sorted_amounts(frame_function_amounts)))

    return CurrentBuildProjection(
        core_request=core_request,
        dose_receipt=dose_receipt,
        bindings=bindings,
        state=(TopologyState.HOLD if blockers else TopologyState.DESIGN_READY_NOT_EMPIRICAL),
        blockers=tuple(blockers),
        material_active_ul=_sorted_amounts(material_amounts),
        function_active_ul=_sorted_amounts(function_amounts),
        layer_active_ul=_sorted_amounts(layer_amounts),
        temporal_material_active_ul=tuple(temporal_material),
        temporal_function_active_ul=tuple(temporal_function),
    )


@dataclass(frozen=True, slots=True)
class TopologyPortfolioRequest:
    projections: tuple[CurrentBuildProjection, ...]
    similarity_threshold: float = 0.95
    concentration_only_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if not isinstance(self.projections, tuple) or len(self.projections) < 2:
            raise ValueError("projections must contain at least two current builds")
        if any(not isinstance(item, CurrentBuildProjection) for item in self.projections):
            raise TypeError("projections must contain CurrentBuildProjection values")
        if len({item.dose_receipt.receipt_sha256 for item in self.projections}) != len(
            self.projections
        ):
            raise ValueError("portfolio projections must have distinct dose receipts")
        threshold = float(self.similarity_threshold)
        tolerance = float(self.concentration_only_tolerance)
        if not isfinite(threshold) or not 0.5 <= threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.5 and 1.0")
        if not isfinite(tolerance) or not 0.0 < tolerance < 0.01:
            raise ValueError("concentration_only_tolerance must be in (0, 0.01)")
        object.__setattr__(self, "similarity_threshold", threshold)
        object.__setattr__(self, "concentration_only_tolerance", tolerance)


def _cosine(left: dict[str, float], right: dict[str, float]) -> float | None:
    keys = set(left) | set(right)
    left_norm = sqrt(sum(float(left.get(key, 0.0)) ** 2 for key in keys))
    right_norm = sqrt(sum(float(right.get(key, 0.0)) ** 2 for key in keys))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    value = sum(float(left.get(key, 0.0)) * float(right.get(key, 0.0)) for key in keys)
    return max(0.0, min(1.0, value / (left_norm * right_norm)))


def _flatten_temporal(
    values: tuple[tuple[str, tuple[tuple[str, float], ...]], ...],
) -> dict[str, float]:
    return {
        f"{label}:{key}": amount
        for label, rows in values
        for key, amount in rows
    }


@dataclass(frozen=True, slots=True)
class PortfolioPairDiagnostic:
    left_receipt_sha256: str
    right_receipt_sha256: str
    left_target_identity: str
    right_target_identity: str
    full_formula_cosine_similarity: float | None
    base_drydown_cosine_similarity: float | None
    module_allocation_cosine_similarity: float | None
    temporal_residue_cosine_similarity: float | None
    flags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        def rounded(value: float | None) -> float | None:
            return None if value is None else round(value, 9)

        return {
            "left_receipt_sha256": self.left_receipt_sha256,
            "right_receipt_sha256": self.right_receipt_sha256,
            "left_target_identity": self.left_target_identity,
            "right_target_identity": self.right_target_identity,
            "full_formula_cosine_similarity": rounded(
                self.full_formula_cosine_similarity
            ),
            "base_drydown_cosine_similarity": rounded(
                self.base_drydown_cosine_similarity
            ),
            "module_allocation_cosine_similarity": rounded(
                self.module_allocation_cosine_similarity
            ),
            "temporal_residue_cosine_similarity": rounded(
                self.temporal_residue_cosine_similarity
            ),
            "flags": list(self.flags),
            "metric_authority": "ENGINEERING_ANTI_COLLAPSE_DIAGNOSTIC_ONLY",
            "sensory_similarity_authority": False,
        }


@dataclass(frozen=True, slots=True)
class TopologyPortfolioResult:
    request: TopologyPortfolioRequest
    state: TopologyState
    blockers: tuple[str, ...]
    pair_diagnostics: tuple[PortfolioPairDiagnostic, ...]
    diagnostic_only: bool = field(default=True, init=False)
    empirical_pass: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perceptual_topology_portfolio_diagnostic_v1",
            "state": self.state.value,
            "diagnostic_thresholds": {
                "cosine_similarity": self.request.similarity_threshold,
                "concentration_only_tolerance": (
                    self.request.concentration_only_tolerance
                ),
                "authority": "ENGINEERING_HEURISTIC_NOT_SENSORY_THRESHOLD",
            },
            "vector_families": [
                "full_formula_active_allocation",
                "base_drydown_active_residue",
                "module_function_active_allocation",
                "temporal_function_active_residue",
            ],
            "pair_diagnostics": [item.as_dict() for item in self.pair_diagnostics],
            "blockers": list(self.blockers),
            "final_integrator": FINAL_INTEGRATOR,
            "final_acceptance_authority": False,
            "diagnostic_only": self.diagnostic_only,
            "empirical_pass": self.empirical_pass,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
        }


def evaluate_topology_portfolio(
    request: TopologyPortfolioRequest,
) -> TopologyPortfolioResult:
    """Detect structural collapse without calling vector similarity perception."""

    if not isinstance(request, TopologyPortfolioRequest):
        raise TypeError("request must be a TopologyPortfolioRequest")
    blockers = [
        f"{projection.dose_receipt.receipt_sha256}: " + "; ".join(projection.blockers)
        for projection in request.projections
        if projection.state is TopologyState.HOLD
    ]
    diagnostics: list[PortfolioPairDiagnostic] = []
    for left, right in combinations(request.projections, 2):
        full = _cosine(left.material_amounts, right.material_amounts)
        left_last = (
            dict(left.temporal_material_active_ul[-1][1])
            if left.temporal_material_active_ul
            else {}
        )
        right_last = (
            dict(right.temporal_material_active_ul[-1][1])
            if right.temporal_material_active_ul
            else {}
        )
        base = _cosine(left_last, right_last)
        module = _cosine(left.function_amounts, right.function_amounts)
        temporal = _cosine(
            _flatten_temporal(left.temporal_function_active_ul),
            _flatten_temporal(right.temporal_function_active_ul),
        )
        def high(value: float | None) -> bool:
            return value is not None and value >= request.similarity_threshold

        flags: list[str] = []
        if high(full):
            flags.append("REPEATED_CHASSIS")
        if high(base):
            flags.append("GENERIC_LATE_RESIDUE")
        if high(module):
            flags.append("MODULE_ALLOCATION_COLLAPSE")
        if high(temporal):
            flags.append("TEMPORAL_RESIDUE_COLLAPSE")
        concentration_only = bool(
            full is not None
            and full >= 1.0 - request.concentration_only_tolerance
            and not isclose(
                left.total_active_ul,
                right.total_active_ul,
                rel_tol=request.concentration_only_tolerance,
                abs_tol=request.concentration_only_tolerance,
            )
        )
        if concentration_only:
            flags.append("CONCENTRATION_ONLY_SIBLINGS")
        different_targets = (
            left.core_request.target_identity.casefold()
            != right.core_request.target_identity.casefold()
        )
        if different_targets and (
            concentration_only or sum(high(value) for value in (full, base, module, temporal)) >= 3
        ):
            flags.append("TARGET_IDENTITY_COLLAPSE")
        if flags:
            blockers.append(
                f"{left.dose_receipt.receipt_sha256} vs "
                f"{right.dose_receipt.receipt_sha256}: " + ", ".join(flags)
            )
        diagnostics.append(
            PortfolioPairDiagnostic(
                left_receipt_sha256=left.dose_receipt.receipt_sha256,
                right_receipt_sha256=right.dose_receipt.receipt_sha256,
                left_target_identity=left.core_request.target_identity,
                right_target_identity=right.core_request.target_identity,
                full_formula_cosine_similarity=full,
                base_drydown_cosine_similarity=base,
                module_allocation_cosine_similarity=module,
                temporal_residue_cosine_similarity=temporal,
                flags=tuple(flags),
            )
        )
    return TopologyPortfolioResult(
        request=request,
        state=TopologyState.HOLD if blockers else TopologyState.DIAGNOSTIC_ONLY,
        blockers=tuple(blockers),
        pair_diagnostics=tuple(diagnostics),
    )


__all__ = [
    "CurrentBuildProjection",
    "FINAL_INTEGRATOR",
    "MODEL_ORDER",
    "SEPARATE_ENDPOINTS",
    "UNIVERSAL_DIMENSIONS",
    "PerceptualFunction",
    "PortfolioPairDiagnostic",
    "TopologyMaterialBinding",
    "TopologyPortfolioRequest",
    "TopologyPortfolioResult",
    "TopologyCoreRequest",
    "TopologyCoreResult",
    "TopologyLayerContract",
    "TopologyState",
    "evaluate_topology_portfolio",
    "evaluate_perceptual_topology",
    "project_current_inventory_build",
]
