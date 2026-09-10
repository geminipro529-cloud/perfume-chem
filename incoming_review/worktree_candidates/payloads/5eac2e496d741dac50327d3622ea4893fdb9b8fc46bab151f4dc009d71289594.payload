"""Typed target-first contracts for perceptual perfume architecture.

These contracts describe relations that a perfume design intends to create.
They do not infer perception from composition, reward ingredient count, or
grant formula, compounding, sensory, hedonic, safety, stability, purchase, or
release authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from engine.perception.architectural_delta import ArchitecturalDeltaCandidate


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _text_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in tuple(values))
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must be nonempty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _sha256(value: object, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return text


class ArchitectureStrategyId(str, Enum):
    """Non-ranked architectural grammars available to a target."""

    CHIAROSCURO_DUAL_STATE = "CHIAROSCURO_DUAL_STATE"
    OBJECT_ANATOMY_TRANSFORMATION = "OBJECT_ANATOMY_TRANSFORMATION"
    TEMPORAL_METAMORPHOSIS = "TEMPORAL_METAMORPHOSIS"
    MINIMAL_PRECISION = "MINIMAL_PRECISION"
    POLYPHONIC_COUNTERPOINT = "POLYPHONIC_COUNTERPOINT"
    SATURATED_ENCLOSURE = "SATURATED_ENCLOSURE"
    SPATIAL_FIELD = "SPATIAL_FIELD"
    MATERIAL_TEXTURE = "MATERIAL_TEXTURE"


class ArchitectureCompilationState(str, Enum):
    HOLD = "HOLD"
    NO_CHANGE = "NO_CHANGE"
    EXPERIMENT_PROPOSED = "EXPERIMENT_PROPOSED"


@dataclass(frozen=True, slots=True)
class ArchitectureStrategyAssignment:
    strategy_id: ArchitectureStrategyId
    owns_function_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", ArchitectureStrategyId(self.strategy_id))
        object.__setattr__(
            self,
            "owns_function_ids",
            _text_tuple(tuple(self.owns_function_ids), "owns_function_ids"),
        )
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy_id": self.strategy_id.value,
            "owns_function_ids": list(self.owns_function_ids),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class TargetFunctionContract:
    """One target-required perceptual job and its falsifiable loss."""

    function_id: str
    description: str
    target_link: str
    omission_loss: str
    success_observable: str
    failure_observable: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "function_id",
            "description",
            "target_link",
            "omission_loss",
            "success_observable",
            "failure_observable",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(tuple(self.evidence_refs), "evidence_refs"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "function_id": self.function_id,
            "description": self.description,
            "target_link": self.target_link,
            "omission_loss": self.omission_loss,
            "success_observable": self.success_observable,
            "failure_observable": self.failure_observable,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ArchitectureLayerContract:
    """A declared temporal, spatial, and textural locus in the design."""

    layer_id: str
    temporal_position: str
    spatial_position: str
    texture: str
    function_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "layer_id",
            "temporal_position",
            "spatial_position",
            "texture",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "function_ids",
            _text_tuple(tuple(self.function_ids), "function_ids"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "layer_id": self.layer_id,
            "temporal_position": self.temporal_position,
            "spatial_position": self.spatial_position,
            "texture": self.texture,
            "function_ids": list(self.function_ids),
        }


@dataclass(frozen=True, slots=True)
class ArchitectureTransitionContract:
    """A relation between layers, not a predicted evaporation narrative."""

    transition_id: str
    from_layer_id: str
    to_layer_id: str
    relation: str
    intended_effect: str
    failure_mode: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "transition_id",
            "from_layer_id",
            "to_layer_id",
            "relation",
            "intended_effect",
            "failure_mode",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if self.from_layer_id == self.to_layer_id:
            raise ValueError("a transition must connect two distinct layers")
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(tuple(self.evidence_refs), "evidence_refs"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "transition_id": self.transition_id,
            "from_layer_id": self.from_layer_id,
            "to_layer_id": self.to_layer_id,
            "relation": self.relation,
            "intended_effect": self.intended_effect,
            "failure_mode": self.failure_mode,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ArchitectureMaterialHypothesis:
    """A material-to-function hypothesis, never a direct note-to-molecule map."""

    material_name: str
    function_id: str
    role: str
    ideal_status: str
    current_build_intent: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "material_name",
            "function_id",
            "role",
            "ideal_status",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.current_build_intent, bool):
            raise TypeError("current_build_intent must be boolean")
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(tuple(self.evidence_refs), "evidence_refs"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "material_name": self.material_name,
            "function_id": self.function_id,
            "role": self.role,
            "ideal_status": self.ideal_status,
            "current_build_intent": self.current_build_intent,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ArchitectureCompileRequest:
    """Complete target lock and relational design submitted to the compiler."""

    target_identity: str
    target_reference: str
    family_adapter_id: str
    target_recognizers: tuple[str, ...]
    target_invariants: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    ideal_formula_ref: str
    current_inventory_build_ref: str
    formula_lineage_sha256: str
    primary_strategy: ArchitectureStrategyAssignment
    secondary_strategies: tuple[ArchitectureStrategyAssignment, ...]
    functions: tuple[TargetFunctionContract, ...]
    layers: tuple[ArchitectureLayerContract, ...]
    transitions: tuple[ArchitectureTransitionContract, ...]
    material_hypotheses: tuple[ArchitectureMaterialHypothesis, ...]
    delta_candidates: tuple[ArchitecturalDeltaCandidate, ...]
    no_change_reason: str
    evidence_refs: tuple[str, ...]
    component_count_used_as_complexity: bool = False
    predicted_oav_used_as_perception: bool = False
    composition_score_used_as_hedonic: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "target_identity",
            "target_reference",
            "family_adapter_id",
            "ideal_formula_ref",
            "current_inventory_build_ref",
            "no_change_reason",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if self.ideal_formula_ref == self.current_inventory_build_ref:
            raise ValueError(
                "ideal_formula_ref and current_inventory_build_ref must remain distinct"
            )
        object.__setattr__(
            self,
            "formula_lineage_sha256",
            _sha256(self.formula_lineage_sha256, "formula_lineage_sha256"),
        )
        for field_name in (
            "target_recognizers",
            "target_invariants",
            "forbidden_drift",
            "evidence_refs",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(tuple(getattr(self, field_name)), field_name),
            )
        if not isinstance(self.primary_strategy, ArchitectureStrategyAssignment):
            raise TypeError("primary_strategy must be an ArchitectureStrategyAssignment")
        object.__setattr__(self, "secondary_strategies", tuple(self.secondary_strategies))
        if len(self.secondary_strategies) > 2:
            raise ValueError("at most two secondary strategies are allowed")
        if any(
            not isinstance(value, ArchitectureStrategyAssignment)
            for value in self.secondary_strategies
        ):
            raise TypeError(
                "secondary_strategies must contain ArchitectureStrategyAssignment values"
            )
        assigned_ids = (
            self.primary_strategy.strategy_id,
            *(value.strategy_id for value in self.secondary_strategies),
        )
        if len(assigned_ids) != len(set(assigned_ids)):
            raise ValueError("primary and secondary strategy IDs must be distinct")

        typed_collections: tuple[tuple[str, type[Any]], ...] = (
            ("functions", TargetFunctionContract),
            ("layers", ArchitectureLayerContract),
            ("transitions", ArchitectureTransitionContract),
            ("material_hypotheses", ArchitectureMaterialHypothesis),
            ("delta_candidates", ArchitecturalDeltaCandidate),
        )
        for field_name, expected_type in typed_collections:
            values = tuple(getattr(self, field_name))
            if field_name in {"functions", "layers"} and not values:
                raise ValueError(f"{field_name} must be nonempty")
            if any(not isinstance(value, expected_type) for value in values):
                raise TypeError(
                    f"{field_name} must contain {expected_type.__name__} values"
                )
            object.__setattr__(self, field_name, values)

        identity_fields = (
            ("functions", tuple(value.function_id for value in self.functions)),
            ("layers", tuple(value.layer_id for value in self.layers)),
            (
                "transitions",
                tuple(value.transition_id for value in self.transitions),
            ),
            (
                "delta_candidates",
                tuple(value.candidate_id for value in self.delta_candidates),
            ),
        )
        for field_name, identifiers in identity_fields:
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{field_name} identifiers must be unique")
        for field_name in (
            "component_count_used_as_complexity",
            "predicted_oav_used_as_perception",
            "composition_score_used_as_hedonic",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")

    def target_lock_payload(self) -> dict[str, object]:
        """Return the target identity before inventory or family adaptation."""

        return {
            "target_identity": self.target_identity,
            "target_reference": self.target_reference,
            "target_recognizers": list(self.target_recognizers),
            "target_invariants": list(self.target_invariants),
            "forbidden_drift": list(self.forbidden_drift),
            "ideal_formula_ref": self.ideal_formula_ref,
            "formula_lineage_sha256": self.formula_lineage_sha256,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            **self.target_lock_payload(),
            "family_adapter_id": self.family_adapter_id,
            "current_inventory_build_ref": self.current_inventory_build_ref,
            "primary_strategy": self.primary_strategy.as_dict(),
            "secondary_strategies": [
                value.as_dict() for value in self.secondary_strategies
            ],
            "functions": [value.as_dict() for value in self.functions],
            "layers": [value.as_dict() for value in self.layers],
            "transitions": [value.as_dict() for value in self.transitions],
            "material_hypotheses": [
                value.as_dict() for value in self.material_hypotheses
            ],
            "delta_candidate_ids": [
                value.candidate_id for value in self.delta_candidates
            ],
            "no_change_reason": self.no_change_reason,
            "evidence_refs": list(self.evidence_refs),
            "component_count_used_as_complexity": (
                self.component_count_used_as_complexity
            ),
            "predicted_oav_used_as_perception": self.predicted_oav_used_as_perception,
            "composition_score_used_as_hedonic": (
                self.composition_score_used_as_hedonic
            ),
        }


__all__ = [
    "ArchitectureCompilationState",
    "ArchitectureCompileRequest",
    "ArchitectureLayerContract",
    "ArchitectureMaterialHypothesis",
    "ArchitectureStrategyAssignment",
    "ArchitectureStrategyId",
    "ArchitectureTransitionContract",
    "TargetFunctionContract",
]
