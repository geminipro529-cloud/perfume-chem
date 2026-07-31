"""Pure B8 priority policy, ranking, and stratified dashboard helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_EVIDENCE_CLASSES,
    BACKFILL_GAP_STATES,
    BACKFILL_REQUIREMENT_TYPES,
)

BACKFILL_PRIORITY_DIMENSIONS = (
    "CURRENT_INVENTORY",
    "ACTIVE_OR_SHIPPED_FORMULA",
    "HIGH_DOSE_STRUCTURE",
    "POTENT_TRACE",
    "REGULATORY_OR_FAMILY_DRIVER",
    "ANALYTICAL_STANDARD",
    "NATURAL_CONSTITUENT",
    "MODEL_SENSITIVITY",
)
BACKFILL_PRIORITY_POLICY = {
    "policy_version": "b8-priority-v1",
    "ranking_method": "STRICT_LEXICOGRAPHIC",
    "dimensions": list(BACKFILL_PRIORITY_DIMENSIONS),
    "requirement_types": list(BACKFILL_REQUIREMENT_TYPES),
    "aggregate_coverage_score": False,
    "release_authority": False,
}

_CRITICAL_REQUIREMENTS = {
    "EXACT_IDENTITY",
    "GRADE_IDENTITY",
    "MOLECULAR_WEIGHT",
    "DENSITY",
    "CONTEXTUAL_THRESHOLD",
    "SAFETY_DOCUMENTATION",
}
_UNRESOLVED_GAP_STATES = {
    "MISSING",
    "UNKNOWN",
    "WEAK",
    "CONFLICTED",
}
_BANNED_DASHBOARD_KEYS = {
    "OVERALL",
    "TOTAL_CONFIDENCE",
    "COVERAGE_SCORE",
    "CONFIDENCE_PERCENT",
}


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def backfill_policy_hash() -> str:
    return _sha(BACKFILL_PRIORITY_POLICY)


@dataclass(frozen=True, slots=True)
class BackfillSignalVector:
    current_inventory: bool | None
    active_or_shipped_formula: bool | None
    high_dose_structure: float | None
    potent_trace: float | None
    regulatory_or_family_driver: int | None
    analytical_standard: bool | None
    natural_constituent: bool | None
    model_sensitivity: float | None


@dataclass(frozen=True, slots=True)
class BackfillGapProjection:
    requirement_type: str
    state: str
    evidence_class: str

    def __post_init__(self) -> None:
        if self.requirement_type not in BACKFILL_REQUIREMENT_TYPES:
            raise ValueError("unknown B8 requirement type")
        if self.state not in BACKFILL_GAP_STATES:
            raise ValueError("unknown B8 gap state")
        if self.evidence_class not in BACKFILL_EVIDENCE_CLASSES:
            raise ValueError("unknown B8 evidence class")


@dataclass(frozen=True, slots=True)
class ResolvedBackfillMaterial:
    material_id: str
    canonical_name: str
    chemical_family: str | None
    evidence_class: str
    signal_vector: BackfillSignalVector
    gaps: tuple[BackfillGapProjection, ...]

    def __post_init__(self) -> None:
        if not self.material_id.strip():
            raise ValueError("material_id must not be blank")
        if not self.canonical_name.strip():
            raise ValueError("canonical_name must not be blank")
        if self.evidence_class not in BACKFILL_EVIDENCE_CLASSES:
            raise ValueError("unknown B8 material evidence class")
        requirement_types = tuple(gap.requirement_type for gap in self.gaps)
        if len(requirement_types) != len(set(requirement_types)):
            raise ValueError("duplicate B8 gap requirement")


@dataclass(frozen=True, slots=True)
class RankedBackfillMaterial:
    material_id: str
    canonical_name: str
    chemical_family: str | None
    evidence_class: str
    signal_vector: BackfillSignalVector
    gaps: tuple[BackfillGapProjection, ...]
    rank: int
    primary_priority_class: str
    rank_key: tuple[object, ...]
    rank_key_sha256: str
    critical_unresolved_gap_count: int
    total_unresolved_gap_count: int


@dataclass(frozen=True, slots=True)
class BackfillDashboardProjection:
    dimension: str
    dimension_key: str
    material_count: int
    requirements_total: int
    accepted_exact_count: int
    accepted_scoped_count: int
    weak_count: int
    conflicted_count: int
    unknown_count: int
    missing_count: int
    not_applicable_count: int
    content_sha256: str


def _normalized_number(
    value: float | int | None,
    *,
    name: str,
    minimum: Decimal = Decimal("0"),
    maximum: Decimal | None = None,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    try:
        normalized = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if normalized < minimum or (
        maximum is not None and normalized > maximum
    ):
        raise ValueError(f"{name} is outside the accepted range")
    return normalized


def _bool_key(value: bool | None) -> tuple[int, int]:
    if value is None:
        return (0, 0)
    if not isinstance(value, bool):
        raise ValueError("boolean B8 signal must be true, false, or unknown")
    return (1, int(value))


def _number_key(
    value: float | int | None,
    *,
    name: str,
    maximum: Decimal | None = None,
) -> tuple[int, Decimal]:
    normalized = _normalized_number(
        value,
        name=name,
        maximum=maximum,
    )
    if normalized is None:
        return (0, Decimal("0"))
    return (1, normalized)


def _priority_key(
    material: ResolvedBackfillMaterial,
) -> tuple[tuple[object, ...], int, int]:
    signal = material.signal_vector
    dimensions: tuple[tuple[object, ...], ...] = (
        _bool_key(signal.current_inventory),
        _bool_key(signal.active_or_shipped_formula),
        _number_key(
            signal.high_dose_structure,
            name="high_dose_structure",
            maximum=Decimal("1"),
        ),
        _number_key(signal.potent_trace, name="potent_trace"),
        _number_key(
            signal.regulatory_or_family_driver,
            name="regulatory_or_family_driver",
        ),
        _bool_key(signal.analytical_standard),
        _bool_key(signal.natural_constituent),
        _number_key(
            signal.model_sensitivity,
            name="model_sensitivity",
            maximum=Decimal("1"),
        ),
    )
    unresolved = tuple(
        gap for gap in material.gaps if gap.state in _UNRESOLVED_GAP_STATES
    )
    critical_count = sum(
        gap.requirement_type in _CRITICAL_REQUIREMENTS for gap in unresolved
    )
    total_count = len(unresolved)
    flattened: tuple[object, ...] = tuple(
        item for dimension in dimensions for item in dimension
    )
    return flattened, critical_count, total_count


def _primary_priority_class(vector: BackfillSignalVector) -> str:
    if vector.current_inventory is True:
        return "CURRENT_INVENTORY"
    if vector.active_or_shipped_formula is True:
        return "ACTIVE_OR_SHIPPED_FORMULA"
    if (
        _normalized_number(
            vector.high_dose_structure,
            name="high_dose_structure",
            maximum=Decimal("1"),
        )
        or Decimal("0")
    ) > 0:
        return "HIGH_DOSE_STRUCTURE"
    if (
        _normalized_number(vector.potent_trace, name="potent_trace")
        or Decimal("0")
    ) > 0:
        return "POTENT_TRACE"
    if (
        _normalized_number(
            vector.regulatory_or_family_driver,
            name="regulatory_or_family_driver",
        )
        or Decimal("0")
    ) > 0:
        return "REGULATORY_OR_FAMILY_DRIVER"
    if vector.analytical_standard is True:
        return "ANALYTICAL_STANDARD"
    if vector.natural_constituent is True:
        return "NATURAL_CONSTITUENT"
    if (
        _normalized_number(
            vector.model_sensitivity,
            name="model_sensitivity",
            maximum=Decimal("1"),
        )
        or Decimal("0")
    ) > 0:
        return "MODEL_SENSITIVITY"
    return "UNPRIORITIZED"


def rank_backfill_materials(
    materials: Sequence[ResolvedBackfillMaterial],
) -> tuple[RankedBackfillMaterial, ...]:
    if not materials:
        raise ValueError("B8 campaign must include at least one material")
    if len({item.material_id for item in materials}) != len(materials):
        raise ValueError("duplicate B8 material")

    prepared: list[
        tuple[
            ResolvedBackfillMaterial,
            tuple[object, ...],
            int,
            int,
        ]
    ] = []
    for material in materials:
        key, critical_count, total_count = _priority_key(material)
        prepared.append((material, key, critical_count, total_count))

    def sort_key(
        item: tuple[
            ResolvedBackfillMaterial,
            tuple[object, ...],
            int,
            int,
        ],
    ) -> tuple[object, ...]:
        material, key, critical_count, total_count = item
        numeric_key = tuple(
            -value if isinstance(value, (int, Decimal)) else value
            for value in key
        )
        return (
            *numeric_key,
            -critical_count,
            -total_count,
            material.canonical_name.casefold(),
            material.material_id,
        )

    ordered = sorted(prepared, key=sort_key)
    result: list[RankedBackfillMaterial] = []
    for rank, (material, key, critical_count, total_count) in enumerate(
        ordered,
        start=1,
    ):
        serializable_key = [
            str(value) if isinstance(value, Decimal) else value for value in key
        ]
        result.append(
            RankedBackfillMaterial(
                material_id=material.material_id,
                canonical_name=material.canonical_name,
                chemical_family=material.chemical_family,
                evidence_class=material.evidence_class,
                signal_vector=material.signal_vector,
                gaps=material.gaps,
                rank=rank,
                primary_priority_class=_primary_priority_class(
                    material.signal_vector
                ),
                rank_key=tuple(serializable_key),
                rank_key_sha256=_sha(serializable_key),
                critical_unresolved_gap_count=critical_count,
                total_unresolved_gap_count=total_count,
            )
        )
    return tuple(result)


def _state_counts(gaps: Sequence[BackfillGapProjection]) -> dict[str, int]:
    return {state: sum(gap.state == state for gap in gaps) for state in BACKFILL_GAP_STATES}


def _inventory_key(value: bool | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "IN_SCOPE" if value else "OUT_OF_SCOPE"


def _regulatory_key(value: int | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "DRIVER" if value > 0 else "NON_DRIVER"


def _sensitivity_key(value: float | None) -> str:
    normalized = _normalized_number(
        value,
        name="model_sensitivity",
        maximum=Decimal("1"),
    )
    if normalized is None:
        return "UNKNOWN"
    if normalized >= Decimal("0.67"):
        return "HIGH"
    if normalized >= Decimal("0.33"):
        return "MEDIUM"
    return "LOW"


def build_backfill_dashboard(
    materials: Sequence[RankedBackfillMaterial],
) -> tuple[BackfillDashboardProjection, ...]:
    if not materials:
        raise ValueError("B8 dashboard requires at least one material")

    groups: dict[
        tuple[str, str],
        list[tuple[str, BackfillGapProjection]],
    ] = defaultdict(list)
    material_members: dict[tuple[str, str], set[str]] = defaultdict(set)

    for material in materials:
        vector = material.signal_vector
        material_dimensions = (
            (
                "CURRENT_INVENTORY",
                _inventory_key(vector.current_inventory),
            ),
            (
                "ACTIVE_FORMULA",
                _inventory_key(vector.active_or_shipped_formula),
            ),
            (
                "CHEMICAL_FAMILY",
                material.chemical_family.strip()
                if material.chemical_family
                else "UNKNOWN",
            ),
            (
                "REGULATORY_IMPACT",
                _regulatory_key(vector.regulatory_or_family_driver),
            ),
            (
                "MODEL_SENSITIVITY",
                _sensitivity_key(vector.model_sensitivity),
            ),
        )
        for gap in material.gaps:
            direct_dimensions = (
                ("EVIDENCE_CLASS", gap.evidence_class),
                ("PROPERTY", gap.requirement_type),
            )
            for dimension, dimension_key in (
                *direct_dimensions,
                *material_dimensions,
            ):
                if (
                    dimension.upper() in _BANNED_DASHBOARD_KEYS
                    or dimension_key.upper() in _BANNED_DASHBOARD_KEYS
                ):
                    raise ValueError("aggregate B8 dashboard keys are forbidden")
                groups[(dimension, dimension_key)].append(
                    (material.material_id, gap)
                )
                material_members[(dimension, dimension_key)].add(
                    material.material_id
                )

    cells: list[BackfillDashboardProjection] = []
    for (dimension, dimension_key), members in sorted(groups.items()):
        gaps = [gap for _, gap in members]
        counts = _state_counts(gaps)
        payload = {
            "dimension": dimension,
            "dimension_key": dimension_key,
            "material_count": len(material_members[(dimension, dimension_key)]),
            "requirements_total": len(gaps),
            "accepted_exact_count": counts["ACCEPTED_EXACT"],
            "accepted_scoped_count": counts["ACCEPTED_SCOPED"],
            "weak_count": counts["WEAK"],
            "conflicted_count": counts["CONFLICTED"],
            "unknown_count": counts["UNKNOWN"],
            "missing_count": counts["MISSING"],
            "not_applicable_count": counts["NOT_APPLICABLE"],
        }
        cells.append(
            BackfillDashboardProjection(
                dimension=dimension,
                dimension_key=dimension_key,
                material_count=len(
                    material_members[(dimension, dimension_key)]
                ),
                requirements_total=len(gaps),
                accepted_exact_count=counts["ACCEPTED_EXACT"],
                accepted_scoped_count=counts["ACCEPTED_SCOPED"],
                weak_count=counts["WEAK"],
                conflicted_count=counts["CONFLICTED"],
                unknown_count=counts["UNKNOWN"],
                missing_count=counts["MISSING"],
                not_applicable_count=counts["NOT_APPLICABLE"],
                content_sha256=_sha(payload),
            )
        )
    if {cell.dimension for cell in cells} != set(
        BACKFILL_DASHBOARD_DIMENSIONS
    ):
        raise ValueError("B8 dashboard is missing a required dimension")
    return tuple(cells)


__all__ = [
    "BACKFILL_PRIORITY_DIMENSIONS",
    "BACKFILL_PRIORITY_POLICY",
    "BackfillDashboardProjection",
    "BackfillGapProjection",
    "BackfillSignalVector",
    "RankedBackfillMaterial",
    "ResolvedBackfillMaterial",
    "backfill_policy_hash",
    "build_backfill_dashboard",
    "rank_backfill_materials",
]
