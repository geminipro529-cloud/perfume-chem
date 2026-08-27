"""Perfumery Art & Composition Topology v1.

This layer composes the existing construction-complexity profile with the
Universal Perceptual Topology Core.  It expresses target shape, hierarchy,
ratio hypotheses, and controlled comparisons.  It cannot choose a final
formula or promote modeled physics into sensory or hedonic truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any

from engine.perception.construction_complexity import ConstructionComplexityProfile
from engine.perception.perceptual_topology import (
    FINAL_INTEGRATOR,
    CurrentBuildProjection,
    TopologyCoreRequest,
    TopologyCoreResult,
    TopologyState,
    evaluate_perceptual_topology,
)
from engine.scientific_contract import EvidenceDescriptor
from engine.sensory.ledger import TemporalEvidenceResult, TemporalEvidenceState
from engine.sensory.order_balance import PresentationSchedule, generate_williams_schedule

_REQUIRED_TIMEPOINTS = ("0m", "5m", "30m", "2h", "8h", "24h")
_BINARY_RATIOS = ("9:1", "7:3", "5:5", "3:7", "1:9")
_PERTURBATION_PERCENT = (-30, -20, -10, 0, 10, 20, 30)


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
    final_acceptance_authority: bool = field(default=False, init=False)

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
            "final_integrator": FINAL_INTEGRATOR,
            "physical_truth": "NOT_TESTED",
            "empirical_pass": self.empirical_pass,
            "final_formula_authority": self.final_formula_authority,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "physical_liking_authority": self.physical_liking_authority,
            "purchase_authority": self.purchase_authority,
            "safety_authority": self.safety_authority,
            "measured_headspace_authority": self.measured_headspace_authority,
            "strict_oav_authority": self.strict_oav_authority,
            "final_acceptance_authority": self.final_acceptance_authority,
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


class ArtEvidenceState(str, Enum):
    """Observation-binding state; deliberately contains no PASS value."""

    HOLD = "HOLD"
    OBSERVATIONS_INCOMPLETE = "OBSERVATIONS_INCOMPLETE"
    OBSERVATIONS_BOUND_NOT_ACCEPTED = "OBSERVATIONS_BOUND_NOT_ACCEPTED"


@dataclass(frozen=True, slots=True)
class ArtExperimentArm:
    """One numerical function-level arm; not an authorized formula mutation."""

    arm_id: str
    experiment_kind: str
    function_active_ul: tuple[tuple[str, float], ...]
    neutral_carrier_replacement_ul: float = 0.0
    ratio_label: str | None = None
    perturbation_percent: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "arm_id", _text(self.arm_id, "arm_id"))
        object.__setattr__(
            self,
            "experiment_kind",
            _text(self.experiment_kind, "experiment_kind"),
        )
        rows = tuple((str(key).strip(), float(value)) for key, value in self.function_active_ul)
        if not rows or any(not key or not isfinite(value) or value < 0 for key, value in rows):
            raise ValueError("function_active_ul must contain nonnegative finite values")
        if len({key for key, _value in rows}) != len(rows):
            raise ValueError("function_active_ul function IDs must be unique")
        object.__setattr__(
            self,
            "function_active_ul",
            tuple(sorted(rows, key=lambda item: item[0].casefold())),
        )
        carrier = float(self.neutral_carrier_replacement_ul)
        if not isfinite(carrier) or carrier < 0:
            raise ValueError("neutral_carrier_replacement_ul must be finite and nonnegative")
        object.__setattr__(self, "neutral_carrier_replacement_ul", round(carrier, 12))
        if self.ratio_label is not None:
            object.__setattr__(self, "ratio_label", _text(self.ratio_label, "ratio_label"))
        if self.perturbation_percent is not None:
            value = int(self.perturbation_percent)
            if value not in _PERTURBATION_PERCENT:
                raise ValueError("perturbation_percent must use the approved perturbation grid")
            object.__setattr__(self, "perturbation_percent", value)

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "experiment_kind": self.experiment_kind,
            "function_active_ul": dict(self.function_active_ul),
            "neutral_carrier_replacement_ul": self.neutral_carrier_replacement_ul,
            "ratio_label": self.ratio_label,
            "perturbation_percent": self.perturbation_percent,
            "amount_basis": "CANONICAL_CURRENT_BUILD_ACTIVE_UL",
            "formula_mutation_authorized": False,
            "physical_execution_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class ArtExperimentBlock:
    block_id: str
    protocol_id: str
    arms: tuple[ArtExperimentArm, ...]
    schedule: PresentationSchedule

    def __post_init__(self) -> None:
        for field_name in ("block_id", "protocol_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.arms, tuple) or len(self.arms) < 2:
            raise ValueError("experiment block requires at least two arms")
        if any(not isinstance(item, ArtExperimentArm) for item in self.arms):
            raise TypeError("arms must contain ArtExperimentArm values")
        if len({item.arm_id for item in self.arms}) != len(self.arms):
            raise ValueError("experiment arm IDs must be unique within a block")
        if not isinstance(self.schedule, PresentationSchedule):
            raise TypeError("schedule must be a PresentationSchedule")
        if set(self.schedule.labels) != {item.arm_id for item in self.arms}:
            raise ValueError("presentation schedule labels must match experiment arms")

    def as_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "protocol_id": self.protocol_id,
            "arms": [item.as_dict() for item in self.arms],
            "presentation_schedule": self.schedule.as_dict(),
            "random_assignment_authorized": False,
            "physical_execution_authorized": False,
            "sensory_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ArtExperimentPlan:
    art_topology: ArtTopologyResult
    current_build: CurrentBuildProjection
    protocol_id: str
    state: TopologyState
    blockers: tuple[str, ...]
    blocks: tuple[ArtExperimentBlock, ...]
    empirical_pass: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    random_assignment_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    final_acceptance_authority: bool = field(default=False, init=False)

    def block_by_id(self, block_id: str) -> ArtExperimentBlock:
        normalized = _text(block_id, "block_id")
        for block in self.blocks:
            if block.block_id == normalized:
                return block
        raise KeyError(normalized)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perfumery_art_experiment_plan_v1",
            "state": self.state.value,
            "protocol_id": self.protocol_id,
            "target_identity": self.art_topology.request.core_request.target_identity,
            "ideal_topology_ref": (
                self.art_topology.request.core_request.ideal_topology_ref
            ),
            "current_inventory_build_ref": (
                self.art_topology.request.core_request.current_inventory_build_ref
            ),
            "dose_receipt_sha256": self.current_build.dose_receipt.receipt_sha256,
            "required_timepoints": list(_REQUIRED_TIMEPOINTS),
            "blocks": [block.as_dict() for block in self.blocks],
            "blockers": list(self.blockers),
            "oav_role": "EXPERIMENT_SELECTION_FIREWALL_ONLY",
            "oav_beauty_authority": False,
            "oav_sensory_contribution_authority": False,
            "final_integrator": FINAL_INTEGRATOR,
            "empirical_pass": self.empirical_pass,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "random_assignment_authorized": self.random_assignment_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
            "final_acceptance_authority": self.final_acceptance_authority,
        }


def _amount_rows(values: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(
        (key, round(value, 12))
        for key, value in sorted(values.items(), key=lambda item: item[0].casefold())
    )


def _block(
    *,
    block_id: str,
    protocol_root: str,
    arms: tuple[ArtExperimentArm, ...],
) -> ArtExperimentBlock:
    labels = tuple(arm.arm_id for arm in arms)
    return ArtExperimentBlock(
        block_id=block_id,
        protocol_id=f"{protocol_root}:{block_id}",
        arms=arms,
        schedule=generate_williams_schedule(labels),
    )


def _ratio_blocks(
    art_topology: ArtTopologyResult,
    baseline: dict[str, float],
    protocol_id: str,
) -> tuple[ArtExperimentBlock, ...]:
    blocks: list[ArtExperimentBlock] = []
    for hypothesis in art_topology.request.ratio_hypotheses:
        pair_total = baseline[hypothesis.function_a] + baseline[hypothesis.function_b]
        arms: list[ArtExperimentArm] = []
        for ratio_label in hypothesis.ratios:
            left, right = (int(value) for value in ratio_label.split(":"))
            amounts = dict(baseline)
            amounts[hypothesis.function_a] = pair_total * left / (left + right)
            amounts[hypothesis.function_b] = pair_total * right / (left + right)
            arms.append(
                ArtExperimentArm(
                    arm_id=(
                        f"ratio:{hypothesis.function_a}:{hypothesis.function_b}:"
                        f"{ratio_label}"
                    ),
                    experiment_kind="CONSTANT_PAIR_ACTIVE_LOAD_RATIO_SWEEP",
                    function_active_ul=_amount_rows(amounts),
                    ratio_label=ratio_label,
                )
            )
        block_id = f"ratio:{hypothesis.function_a}:{hypothesis.function_b}"
        blocks.append(
            _block(block_id=block_id, protocol_root=protocol_id, arms=tuple(arms))
        )
    return tuple(blocks)


def _ablation_block(
    baseline: dict[str, float],
    protocol_id: str,
) -> ArtExperimentBlock:
    block_id = "ablation:all-functions"
    arms = [
        ArtExperimentArm(
            arm_id=f"{block_id}:full",
            experiment_kind="FULL_CURRENT_BUILD_CONTROL",
            function_active_ul=_amount_rows(baseline),
        )
    ]
    for function_id in baseline:
        amounts = dict(baseline)
        removed = amounts[function_id]
        amounts[function_id] = 0.0
        arms.append(
            ArtExperimentArm(
                arm_id=f"{block_id}:minus:{function_id}",
                experiment_kind="FUNCTION_ABLATION_CARRIER_MATCHED",
                function_active_ul=_amount_rows(amounts),
                neutral_carrier_replacement_ul=removed,
            )
        )
    return _block(block_id=block_id, protocol_root=protocol_id, arms=tuple(arms))


def _perturbation_block(
    baseline: dict[str, float],
    function_id: str,
    protocol_id: str,
) -> ArtExperimentBlock:
    block_id = f"perturbation:{function_id}"
    total = sum(baseline.values())
    focal = baseline[function_id]
    complement_ids = tuple(key for key in baseline if key != function_id)
    complement_total = total - focal
    arms: list[ArtExperimentArm] = []
    for percent in _PERTURBATION_PERCENT:
        amounts = dict(baseline)
        amounts[function_id] = focal * (1.0 + percent / 100.0)
        target_complement = total - amounts[function_id]
        scale = target_complement / complement_total
        for key in complement_ids:
            amounts[key] = baseline[key] * scale
        rounded = dict(_amount_rows(amounts))
        rounded[complement_ids[-1]] = round(
            rounded[complement_ids[-1]] + total - sum(rounded.values()),
            12,
        )
        arms.append(
            ArtExperimentArm(
                arm_id=f"{block_id}:{percent:+d}",
                experiment_kind="MATCHED_TOTAL_ACTIVE_LOAD_PERTURBATION",
                function_active_ul=_amount_rows(rounded),
                perturbation_percent=percent,
            )
        )
    return _block(block_id=block_id, protocol_root=protocol_id, arms=tuple(arms))


def build_art_experiment_plan(
    *,
    art_topology: ArtTopologyResult,
    current_build: CurrentBuildProjection,
    protocol_id: str,
) -> ArtExperimentPlan:
    """Create numerical controlled-comparison arms from one bound current build."""

    if not isinstance(art_topology, ArtTopologyResult):
        raise TypeError("art_topology must be an ArtTopologyResult")
    if not isinstance(current_build, CurrentBuildProjection):
        raise TypeError("current_build must be a CurrentBuildProjection")
    protocol_id = _text(protocol_id, "protocol_id")
    blockers = list(art_topology.blockers) + list(current_build.blockers)
    if art_topology.request.core_request != current_build.core_request:
        blockers.append("art topology and current build do not share the same core request")
    oav_firewall = art_topology.core_result.oav_firewall
    if not oav_firewall["experiment_selection_authorized"]:
        blockers.extend(oav_firewall.get("screening_blockers", ()))
        if not oav_firewall.get("screening_blockers"):
            blockers.append("OAV experiment-selection firewall is not ready")
    binding = art_topology.request.core_request.oav_binding
    if binding is None:
        blockers.append("experiment selection requires a formula-bound native OAV gate")
    else:
        if binding.formula_sha256 != current_build.dose_receipt.formula_input_sha256:
            blockers.append("OAV formula hash does not match the canonical current build")
        if binding.dose_receipt_sha256 != current_build.dose_receipt.receipt_sha256:
            blockers.append("OAV dose receipt hash does not match the canonical current build")
    baseline = current_build.function_amounts
    if any(value <= 0.0 for value in baseline.values()):
        blockers.append("every target-linked function needs positive canonical active load")
    if len(baseline) < 2:
        blockers.append("matched-load perturbation requires at least two functions")
    if blockers:
        return ArtExperimentPlan(
            art_topology=art_topology,
            current_build=current_build,
            protocol_id=protocol_id,
            state=TopologyState.HOLD,
            blockers=tuple(blockers),
            blocks=(),
        )
    blocks = list(_ratio_blocks(art_topology, baseline, protocol_id))
    blocks.append(_ablation_block(baseline, protocol_id))
    blocks.extend(
        _perturbation_block(baseline, function_id, protocol_id)
        for function_id in baseline
    )
    return ArtExperimentPlan(
        art_topology=art_topology,
        current_build=current_build,
        protocol_id=protocol_id,
        state=TopologyState.DESIGN_READY_NOT_EMPIRICAL,
        blockers=(),
        blocks=tuple(blocks),
    )


@dataclass(frozen=True, slots=True)
class ArtEvidenceBinding:
    plan: ArtExperimentPlan
    block_id: str
    evidence: TemporalEvidenceResult
    state: ArtEvidenceState
    blockers: tuple[str, ...]
    empirical_pass: bool = field(default=False, init=False)
    final_formula_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    final_acceptance_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perfumery_art_temporal_evidence_binding_v1",
            "state": self.state.value,
            "block_id": self.block_id,
            "protocol_id": self.evidence.protocol_id,
            "schedule_sha256": self.evidence.schedule_sha256,
            "temporal_evidence_state": self.evidence.state.value,
            "expected_cell_count": self.evidence.expected_cell_count,
            "observed_cell_count": self.evidence.observed_cell_count,
            "missing_cell_count": len(self.evidence.missing_cells),
            "blockers": list(self.blockers),
            "observation_evidence_bound": not self.blockers,
            "acceptance_boundary": (
                "OBSERVATIONS_REQUIRE_SEPARATE_REPLICATED_INFERENCE_AND_SOL_ACCEPTANCE"
            ),
            "final_integrator": FINAL_INTEGRATOR,
            "empirical_pass": self.empirical_pass,
            "final_formula_authority": self.final_formula_authority,
            "sensory_authority": self.sensory_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
            "final_acceptance_authority": self.final_acceptance_authority,
        }


def bind_art_temporal_evidence(
    *,
    plan: ArtExperimentPlan,
    block_id: str,
    evidence: TemporalEvidenceResult,
) -> ArtEvidenceBinding:
    """Bind canonical ledger output to a plan without converting it to PASS."""

    if not isinstance(plan, ArtExperimentPlan):
        raise TypeError("plan must be an ArtExperimentPlan")
    if not isinstance(evidence, TemporalEvidenceResult):
        raise TypeError("evidence must be a TemporalEvidenceResult")
    block = plan.block_by_id(block_id)
    blockers = list(plan.blockers) + list(evidence.blockers)
    if evidence.protocol_id != block.protocol_id:
        blockers.append("temporal evidence protocol does not match experiment block")
    if evidence.schedule_sha256 != block.schedule.schedule_sha256:
        blockers.append("temporal evidence schedule does not match experiment block")
    if blockers or evidence.state is TemporalEvidenceState.HOLD:
        state = ArtEvidenceState.HOLD
    elif evidence.state is TemporalEvidenceState.INCOMPLETE:
        state = ArtEvidenceState.OBSERVATIONS_INCOMPLETE
    else:
        state = ArtEvidenceState.OBSERVATIONS_BOUND_NOT_ACCEPTED
    return ArtEvidenceBinding(
        plan=plan,
        block_id=block.block_id,
        evidence=evidence,
        state=state,
        blockers=tuple(blockers),
    )


__all__ = [
    "ArtEvidenceBinding",
    "ArtEvidenceState",
    "ArtExperimentArm",
    "ArtExperimentBlock",
    "ArtExperimentPlan",
    "ArtShapeWindow",
    "ArtTopologyRequest",
    "ArtTopologyResult",
    "CompositionOperator",
    "HierarchyEntry",
    "HierarchyRole",
    "RatioHypothesis",
    "bind_art_temporal_evidence",
    "build_art_experiment_plan",
    "evaluate_art_topology",
]
