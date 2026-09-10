"""Dimension-wise comparison of perfume-depth design profiles.

Comparison output is descriptive and abstaining. It cannot rank perfumes or
infer sensory similarity, preference, depth, luxury, or release readiness.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.depth_contracts import (
    DepthArchitectureProfileV1,
    DepthDimension,
    DepthEvidenceState,
    DepthMechanismKind,
    DepthProbeType,
    PerfumeFamily,
)


class DepthDimensionAlignment(str, Enum):
    TARGET_ALIGNED = "TARGET_ALIGNED"
    SAME_CONSTRUCT_DIFFERENT_TARGET = "SAME_CONSTRUCT_DIFFERENT_TARGET"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if is_dataclass(value) and hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return, union-attr]
    return value


class _CanonicalRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _json_value(getattr(self, item.name)) for item in fields(self)},
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class DepthDimensionComparisonV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_dimension_comparison_v1"

    dimension: DepthDimension
    alignment: DepthDimensionAlignment
    left_target_definition: str | None
    right_target_definition: str | None
    shared_mechanism_kinds: tuple[DepthMechanismKind, ...]
    left_only_mechanism_ids: tuple[str, ...]
    right_only_mechanism_ids: tuple[str, ...]
    left_probe_types: tuple[DepthProbeType, ...]
    right_probe_types: tuple[DepthProbeType, ...]
    left_evidence_states: tuple[DepthEvidenceState, ...]
    right_evidence_states: tuple[DepthEvidenceState, ...]
    abstentions: tuple[str, ...]

    @property
    def comparison_sha256(self) -> str:
        return self.record_sha256


@dataclass(frozen=True, slots=True)
class DepthProfileComparisonV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_profile_comparison_v1"

    left_profile_sha256: str
    right_profile_sha256: str
    left_profile_id: str
    right_profile_id: str
    left_family: PerfumeFamily
    right_family: PerfumeFamily
    same_family: bool
    dimension_comparisons: tuple[DepthDimensionComparisonV1, ...]
    target_incompatibilities: tuple[str, ...]
    abstentions: tuple[str, ...]
    formula_authority: bool = field(default=False, init=False)
    sensory_similarity_authority: bool = field(default=False, init=False)
    sensory_preference_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    @property
    def comparison_sha256(self) -> str:
        return self.record_sha256


_DIMENSION_ORDER = {value: index for index, value in enumerate(DepthDimension)}
_MECHANISM_ORDER = {value: index for index, value in enumerate(DepthMechanismKind)}
_PROBE_ORDER = {value: index for index, value in enumerate(DepthProbeType)}
_EVIDENCE_ORDER = {value: index for index, value in enumerate(DepthEvidenceState)}


def _ordered_unique(values: tuple[Enum, ...], order: dict[Any, int]) -> tuple[Any, ...]:
    return tuple(sorted(set(values), key=order.__getitem__))


def compare_depth_profiles(
    left: DepthArchitectureProfileV1,
    right: DepthArchitectureProfileV1,
) -> DepthProfileComparisonV1:
    """Compare declared structures while withholding every superiority claim."""

    if not isinstance(left, DepthArchitectureProfileV1) or not isinstance(
        right, DepthArchitectureProfileV1
    ):
        raise TypeError("left and right must be DepthArchitectureProfileV1 values")

    left_contracts = {item.dimension: item for item in left.dimension_contracts}
    right_contracts = {item.dimension: item for item in right.dimension_contracts}
    left_mechanisms = {item.mechanism_id: item for item in left.mechanisms}
    right_mechanisms = {item.mechanism_id: item for item in right.mechanisms}
    left_probes = {item.probe_id: item for item in left.probes}
    right_probes = {item.probe_id: item for item in right.probes}

    dimension_values = tuple(
        sorted(set(left_contracts) | set(right_contracts), key=_DIMENSION_ORDER.__getitem__)
    )
    comparisons: list[DepthDimensionComparisonV1] = []
    target_incompatibilities: list[str] = []

    for dimension in dimension_values:
        left_contract = left_contracts.get(dimension)
        right_contract = right_contracts.get(dimension)
        if left_contract is None:
            alignment = DepthDimensionAlignment.RIGHT_ONLY
        elif right_contract is None:
            alignment = DepthDimensionAlignment.LEFT_ONLY
        elif left_contract.target_definition == right_contract.target_definition:
            alignment = DepthDimensionAlignment.TARGET_ALIGNED
        else:
            alignment = DepthDimensionAlignment.SAME_CONSTRUCT_DIFFERENT_TARGET
            target_incompatibilities.append(
                f"{dimension.value} has different target definitions and cannot be equated"
            )

        left_dimension_mechanisms = tuple(
            left_mechanisms[mechanism_id]
            for mechanism_id in (() if left_contract is None else left_contract.mechanism_ids)
            if mechanism_id in left_mechanisms
        )
        right_dimension_mechanisms = tuple(
            right_mechanisms[mechanism_id]
            for mechanism_id in (() if right_contract is None else right_contract.mechanism_ids)
            if mechanism_id in right_mechanisms
        )
        left_kinds = {item.kind for item in left_dimension_mechanisms}
        right_kinds = {item.kind for item in right_dimension_mechanisms}
        shared_kinds = tuple(sorted(left_kinds & right_kinds, key=_MECHANISM_ORDER.__getitem__))
        left_only_ids = tuple(
            item.mechanism_id
            for item in left_dimension_mechanisms
            if item.kind not in right_kinds
        )
        right_only_ids = tuple(
            item.mechanism_id
            for item in right_dimension_mechanisms
            if item.kind not in left_kinds
        )

        left_dimension_probes = tuple(
            left_probes[probe_id]
            for probe_id in (() if left_contract is None else left_contract.probe_ids)
            if probe_id in left_probes
        )
        right_dimension_probes = tuple(
            right_probes[probe_id]
            for probe_id in (() if right_contract is None else right_contract.probe_ids)
            if probe_id in right_probes
        )
        dimension_abstentions = (
            "Declared mechanism overlap is not sensory similarity evidence.",
            "Probe coverage records testability, not successful physical performance.",
        )
        comparisons.append(
            DepthDimensionComparisonV1(
                dimension=dimension,
                alignment=alignment,
                left_target_definition=(
                    None if left_contract is None else left_contract.target_definition
                ),
                right_target_definition=(
                    None if right_contract is None else right_contract.target_definition
                ),
                shared_mechanism_kinds=shared_kinds,
                left_only_mechanism_ids=left_only_ids,
                right_only_mechanism_ids=right_only_ids,
                left_probe_types=_ordered_unique(
                    tuple(item.probe_type for item in left_dimension_probes),
                    _PROBE_ORDER,
                ),
                right_probe_types=_ordered_unique(
                    tuple(item.probe_type for item in right_dimension_probes),
                    _PROBE_ORDER,
                ),
                left_evidence_states=_ordered_unique(
                    tuple(item.evidence_state for item in left_dimension_mechanisms),
                    _EVIDENCE_ORDER,
                ),
                right_evidence_states=_ordered_unique(
                    tuple(item.evidence_state for item in right_dimension_mechanisms),
                    _EVIDENCE_ORDER,
                ),
                abstentions=dimension_abstentions,
            )
        )

    same_family = left.family is right.family
    if not same_family:
        target_incompatibilities.insert(
            0,
            (
                f"family-specific anatomy differs: {left.family.value} versus "
                f"{right.family.value}"
            ),
        )
    abstentions = [
        "No physical sensory evidence is present for a preference or depth conclusion.",
        "Formula or material overlap does not establish sensory similarity.",
    ]
    if not same_family:
        abstentions.append(
            "Cross-family structural comparison cannot convert different target anatomies into superiority."
        )

    return DepthProfileComparisonV1(
        left_profile_sha256=left.profile_sha256,
        right_profile_sha256=right.profile_sha256,
        left_profile_id=left.profile_id,
        right_profile_id=right.profile_id,
        left_family=left.family,
        right_family=right.family,
        same_family=same_family,
        dimension_comparisons=tuple(comparisons),
        target_incompatibilities=tuple(target_incompatibilities),
        abstentions=tuple(abstentions),
    )


__all__ = [
    "DepthDimensionAlignment",
    "DepthDimensionComparisonV1",
    "DepthProfileComparisonV1",
    "compare_depth_profiles",
]
