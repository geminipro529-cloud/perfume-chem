"""Wood Depth Model v2 as a specialist of the approved topology stack.

Wood depth is represented as target-linked differentiated information across
ratios, salience, texture, and time.  The model reuses Art Topology and the
Universal Core; it does not create a second complexity score or wood formula
generator.  Natural woods remain whole formula identities, and native OAV
coverage remains a diagnostic firewall rather than perceived-depth evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any

from engine.perception.perceptual_topology import TopologyState
from engine.perception.perfumery_art_topology import ArtTopologyResult


class WoodGroup(str, Enum):
    G16_GRAIN_ROOT = "G16_CEDAR_VETIVER_PATCHOULI_ROOT_WOODS"
    G17_CREAMY_WOODS = "G17_SANDALWOOD_CREAMY_WOODS"
    G18_TRANSPARENT_WOODS = "G18_TRANSPARENT_WOODS"
    G19_AMBERWOODS = "G19_AMBERGRIS_AMBERWOODS"
    RESIN_SMOKE_SHADOW = "RESIN_SMOKE_SHADOW"
    MUSK_ROUNDING = "MUSK_ROUNDING"


class WoodConfiguration(str, Enum):
    ELEMENTAL = "ELEMENTAL"
    PARTIALLY_CONFIGURAL = "PARTIALLY_CONFIGURAL"
    CONFIGURAL = "CONFIGURAL"
    TRANSFORMS_OVER_TIME = "TRANSFORMS_OVER_TIME"


class WoodProhibitedInference(str, Enum):
    MATERIAL_COUNT_AS_DEPTH = "MATERIAL_COUNT_AS_DEPTH"
    TOTAL_WOOD_PERCENT_AS_DEPTH = "TOTAL_WOOD_PERCENT_AS_DEPTH"
    MOLECULAR_COMPLEXITY_AS_DEPTH = "MOLECULAR_COMPLEXITY_AS_DEPTH"
    COMPUTED_HEADSPACE_AS_PERCEIVED_DEPTH = "COMPUTED_HEADSPACE_AS_PERCEIVED_DEPTH"
    NEAR_FAR_PROJECTION_WITHOUT_PHYSICAL_PROTOCOL = "NEAR_FAR_PROJECTION_WITHOUT_PHYSICAL_PROTOCOL"
    INDIVIDUAL_IDENTIFICATION_REQUIRED = "INDIVIDUAL_IDENTIFICATION_REQUIRED"
    SENSORY_PASS_WITHOUT_DATA = "SENSORY_PASS_WITHOUT_DATA"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


@dataclass(frozen=True, slots=True)
class WoodFunctionAssignment:
    """Bind an existing topology function to one specialist wood group."""

    function_id: str
    group: WoodGroup
    is_natural_mixture: bool = False
    formula_constituent_expansion: bool = False
    wood_block_fraction: float | None = None
    target_evidence_for_dominance: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "function_id",
            _text(self.function_id, "function_id"),
        )
        object.__setattr__(self, "group", WoodGroup(self.group))
        for field_name in ("is_natural_mixture", "formula_constituent_expansion"):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be bool")
        if self.formula_constituent_expansion and not self.is_natural_mixture:
            raise ValueError("formula_constituent_expansion only applies to natural mixtures")
        if self.wood_block_fraction is not None:
            fraction = float(self.wood_block_fraction)
            if not isfinite(fraction) or not 0.0 <= fraction <= 1.0:
                raise ValueError("wood_block_fraction must be between zero and one")
            object.__setattr__(self, "wood_block_fraction", fraction)
        if self.target_evidence_for_dominance is not None:
            object.__setattr__(
                self,
                "target_evidence_for_dominance",
                _text(
                    self.target_evidence_for_dominance,
                    "target_evidence_for_dominance",
                ),
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "function_id": self.function_id,
            "group": self.group.value,
            "is_natural_mixture": self.is_natural_mixture,
            "formula_constituent_expansion": self.formula_constituent_expansion,
            "wood_block_fraction": self.wood_block_fraction,
            "target_evidence_for_dominance": self.target_evidence_for_dominance,
        }


@dataclass(frozen=True, slots=True)
class WoodDepthRequest:
    art_topology: ArtTopologyResult
    wood_layer_id: str
    target_configuration: WoodConfiguration
    assignments: tuple[WoodFunctionAssignment, ...]
    prohibited_inferences: tuple[WoodProhibitedInference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.art_topology, ArtTopologyResult):
            raise TypeError("art_topology must be an ArtTopologyResult")
        object.__setattr__(
            self,
            "wood_layer_id",
            _text(self.wood_layer_id, "wood_layer_id"),
        )
        object.__setattr__(
            self,
            "target_configuration",
            WoodConfiguration(self.target_configuration),
        )
        if not isinstance(self.assignments, tuple):
            raise TypeError("assignments must be a tuple")
        if not self.assignments:
            raise ValueError("assignments must not be empty")
        if any(not isinstance(item, WoodFunctionAssignment) for item in self.assignments):
            raise TypeError("assignments must contain WoodFunctionAssignment values")
        function_ids = tuple(item.function_id for item in self.assignments)
        if len(function_ids) != len(set(function_ids)):
            raise ValueError("wood function assignments must be unique")
        if not isinstance(self.prohibited_inferences, tuple):
            raise TypeError("prohibited_inferences must be a tuple")
        if any(
            not isinstance(item, WoodProhibitedInference) for item in self.prohibited_inferences
        ):
            raise TypeError("prohibited_inferences must contain WoodProhibitedInference values")
        if len(self.prohibited_inferences) != len(set(self.prohibited_inferences)):
            raise ValueError("prohibited_inferences must not contain duplicates")


def _dimensions() -> dict[str, dict[str, Any]]:
    return {
        "grain_integrity": {
            "question": "Does tactile dry, root, or fiber identity remain?",
            "state": "STRUCTURED_HYPOTHESIS",
            "failures": ["pencil-only wood", "root mud", "generic dry base"],
        },
        "texture_contrast": {
            "question": "Are dry, creamy, rough, polished, earthy, mineral, or smoky textures intentionally differentiated?",
            "state": "STRUCTURED_HYPOTHESIS",
            "failures": [
                "homogeneous beige wood",
                "buttery sandalwood takeover",
                "uniformly scratchy wood",
            ],
        },
        "configural_balance": {
            "question": "Should facets remain recognizable, form a new wood object, or transform between both states?",
            "state": "STRUCTURED_HYPOTHESIS",
            "ratios_are_causal_variables": True,
        },
        "salience_depth": {
            "question": "Do woody qualities change salience without permanent masking?",
            "state": "STRUCTURED_HYPOTHESIS",
            "foreground_background_is_literal_space": False,
        },
        "temporal_transformation": {
            "question": "Does target-specific wood identity transform through time?",
            "state": "STRUCTURED_HYPOTHESIS",
            "required_windows": ["opening", "heart", "drydown", "8h", "24h"],
        },
        "structural_air_shadow": {
            "question": "Is there enough relief for grain and texture to remain legible?",
            "state": "STRUCTURED_HYPOTHESIS",
            "negative_space_requires_observation": True,
        },
        "late_identity": {
            "question": "Does persistence preserve target identity rather than generic woody intensity?",
            "state": "STRUCTURED_HYPOTHESIS",
        },
        "wood_cloud_collapse_risk": {
            "question": "Do differentiated wood functions converge into a generic woody, musk, or amber cloud?",
            "state": "REQUIRES_CONTROLLED_COMPARISON",
        },
    }


def _causal_tests() -> dict[str, Any]:
    return {
        "elemental_configural_ratio": {
            "arms": ["A", "B", "A:B_3:1", "A:B_1:1", "A:B_1:3"],
            "constraint": "CONSTANT_TOTAL_WOODY_LOADING",
        },
        "wood_class_ablation": {
            "arms": [
                "full",
                "minus_grain",
                "minus_cream",
                "minus_transparent",
                "minus_root_or_shadow",
            ],
            "constraint": "REPLACE_REMOVED_MASS_WITH_NEUTRAL_CARRIER",
        },
        "perturbation_percent": [-30, -20, -10, 0, 10, 20, 30],
        "temporal_profile": {
            "method": "TCATA_STYLE_MULTIATTRIBUTE_PLUS_TARGETED_INTENSITY",
            "minimum_times": ["0m", "5m", "30m", "2h", "8h", "24h"],
        },
        "adaptation_probe": {
            "purpose": "DISTINGUISH_ABSENCE_FROM_MASKING_OR_ADAPTATION",
            "authority": "EXPERIMENTAL_ONLY",
        },
        "matched_release_check": {
            "preferred": [
                "matched_blotter",
                "matched_application_mass",
                "matched_finished_concentration",
                "HS_SPME_or_equivalent_when_available",
            ],
            "release_and_sensory_evidence_kept_separate": True,
        },
    }


_PROHIBITED_BLOCKERS = {
    WoodProhibitedInference.MATERIAL_COUNT_AS_DEPTH: ("wood material count cannot establish depth"),
    WoodProhibitedInference.TOTAL_WOOD_PERCENT_AS_DEPTH: (
        "total wood percentage cannot establish depth"
    ),
    WoodProhibitedInference.MOLECULAR_COMPLEXITY_AS_DEPTH: (
        "molecular complexity cannot establish perceived depth"
    ),
    WoodProhibitedInference.COMPUTED_HEADSPACE_AS_PERCEIVED_DEPTH: (
        "computed headspace cannot establish perceived wood depth"
    ),
    WoodProhibitedInference.NEAR_FAR_PROJECTION_WITHOUT_PHYSICAL_PROTOCOL: (
        "near/far projection requires a qualified physical protocol"
    ),
    WoodProhibitedInference.INDIVIDUAL_IDENTIFICATION_REQUIRED: (
        "wood depth cannot require identification of every material"
    ),
    WoodProhibitedInference.SENSORY_PASS_WITHOUT_DATA: (
        "sensory pass cannot be claimed without physical observations"
    ),
}


@dataclass(frozen=True, slots=True)
class WoodDepthResult:
    request: WoodDepthRequest
    state: TopologyState
    blockers: tuple[str, ...]
    empirical_pass: bool = field(default=False, init=False)
    physical_depth_authority: bool = field(default=False, init=False)
    predicted_liking_authority: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        art_payload = self.request.art_topology.as_dict()
        return {
            "schema_version": "wood_depth_model_v2",
            "state": self.state.value,
            "target_identity": art_payload["target_identity"],
            "ideal_topology_ref": art_payload["ideal_topology_ref"],
            "current_inventory_build_ref": art_payload["current_inventory_build_ref"],
            "wood_layer_id": self.request.wood_layer_id,
            "target_configuration": self.request.target_configuration.value,
            "inherits": [
                "UNIVERSAL_PERCEPTUAL_TOPOLOGY_CORE",
                "PERFUMERY_ART_COMPOSITION_TOPOLOGY_V1",
                "CONSTRUCTION_COMPLEXITY_PROFILE_V1",
            ],
            "definition": (
                "Target-linked perceptual depth from differentiated woody "
                "functions, ratios, interactions, salience changes, and temporal "
                "transformations; never count, darkness, persistence, or total dose."
            ),
            "assignments": [item.as_dict() for item in self.request.assignments],
            "dimensions": _dimensions(),
            "causal_tests": _causal_tests(),
            "blockers": list(self.blockers),
            "oav_firewall": art_payload["oav_firewall"],
            "final_integrator": art_payload["final_integrator"],
            "physical_truth": "NOT_TESTED",
            "empirical_pass": self.empirical_pass,
            "physical_depth_authority": self.physical_depth_authority,
            "predicted_liking_authority": self.predicted_liking_authority,
            "sensory_similarity_authority": self.sensory_similarity_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
        }


def evaluate_wood_depth(request: WoodDepthRequest) -> WoodDepthResult:
    """Validate one wood topology and produce only controlled-test authority."""

    if not isinstance(request, WoodDepthRequest):
        raise TypeError("request must be a WoodDepthRequest")
    blockers = list(request.art_topology.blockers)
    layers = {layer.layer_id: layer for layer in request.art_topology.request.core_request.layers}
    wood_layer = layers.get(request.wood_layer_id)
    if wood_layer is None:
        blockers.append("wood_layer_id is not present in the universal topology")
        expected_function_ids: set[str] = set()
    else:
        expected_function_ids = {function.function_id for function in wood_layer.functions}
    assignment_ids = {item.function_id for item in request.assignments}
    if assignment_ids != expected_function_ids:
        blockers.append("wood assignments must cover each wood-layer function once")
    for assignment in request.assignments:
        if assignment.formula_constituent_expansion:
            blockers.append(
                f"{assignment.function_id}: natural wood complexity cannot create "
                "invented constituent rows in the formula"
            )
        if (
            assignment.wood_block_fraction is not None
            and assignment.wood_block_fraction > 0.35
            and assignment.target_evidence_for_dominance is None
        ):
            blockers.append(
                f"{assignment.function_id}: wood-block dominance above 35% requires target evidence"
            )
    blockers.extend(_PROHIBITED_BLOCKERS[item] for item in request.prohibited_inferences)
    return WoodDepthResult(
        request=request,
        state=(TopologyState.HOLD if blockers else TopologyState.DESIGN_READY_NOT_EMPIRICAL),
        blockers=tuple(blockers),
    )


__all__ = [
    "WoodConfiguration",
    "WoodDepthRequest",
    "WoodDepthResult",
    "WoodFunctionAssignment",
    "WoodGroup",
    "WoodProhibitedInference",
    "evaluate_wood_depth",
]
