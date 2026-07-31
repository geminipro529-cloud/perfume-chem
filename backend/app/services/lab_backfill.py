"""Pure B8 priority policy, ranking, and stratified dashboard helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_EVIDENCE_CLASSES,
    BACKFILL_GAP_STATES,
    BACKFILL_REQUIREMENT_TYPES,
    BACKFILL_SIGNAL_TYPES,
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
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
_ACCEPTED_GAP_STATES = {"ACCEPTED_EXACT", "ACCEPTED_SCOPED"}
_SIGNAL_FOREIGN_KEYS = (
    "stock_solution_id",
    "formula_component_id",
    "oav_assessment_id",
    "knowledge_rule_id",
    "regulatory_snapshot_version_id",
    "analytical_sequence_entry_id",
    "composition_entry_id",
    "prediction_id",
)
_REQUIREMENT_CLAIM_TYPES = {
    "EXACT_IDENTITY": {"EXACT_CHEMICAL_IDENTITY"},
    "GRADE_IDENTITY": {"GRADE_IDENTITY"},
    "MOLECULAR_WEIGHT": {"PROPERTY_VALUE"},
    "DENSITY": {"PROPERTY_VALUE"},
    "VAPOR_PRESSURE": {"PROPERTY_VALUE"},
    "CONTEXTUAL_THRESHOLD": {"THRESHOLD"},
    "SAFETY_DOCUMENTATION": {"REGULATORY_SCREENING"},
    "RETENTION_INDEX": {"ANALYTICAL_IDENTIFICATION"},
    "ANALYTICAL_REFERENCE": {
        "ANALYTICAL_IDENTIFICATION",
        "ANALYTICAL_QUANTITATION",
    },
    "NATURAL_LOT_COMPOSITION": {"NATURAL_CONSTITUENT_PROFILE"},
}
_REQUIREMENT_PROPERTY_TYPES = {
    "MOLECULAR_WEIGHT": {"MOLECULAR_WEIGHT", "MOLECULAR_MASS"},
    "DENSITY": {"DENSITY"},
    "VAPOR_PRESSURE": {"VAPOR_PRESSURE"},
}


def _required_text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    return normalized


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


class BackfillConflictError(ValueError):
    """Fail-closed B8 campaign or reconstruction error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class BackfillSignalCommand:
    signal_type: str
    source_id: str
    operational_status: str | None = None
    normalized_sensitivity: float | None = None

    def __post_init__(self) -> None:
        signal_type = _required_text(
            self.signal_type,
            "signal_type",
        ).upper()
        source_id = _required_text(self.source_id, "source_id")
        if signal_type not in BACKFILL_SIGNAL_TYPES:
            raise ValueError("unknown B8 signal type")
        status = (
            _required_text(self.operational_status, "operational_status").upper()
            if self.operational_status is not None
            else None
        )
        expected_status = {
            "ACTIVE_FORMULA": "ACTIVE",
            "SHIPPED_FORMULA": "SHIPPED",
            "REFERENCE_FORMULA": "REFERENCE",
        }.get(signal_type)
        if expected_status is not None and status != expected_status:
            raise ValueError(
                f"{signal_type} requires operational_status={expected_status}"
            )
        if expected_status is None and status is not None:
            raise ValueError(
                "operational_status is only valid for formula-status signals"
            )
        sensitivity = self.normalized_sensitivity
        if signal_type == "MODEL_SENSITIVITY":
            normalized = _normalized_number(
                sensitivity,
                name="normalized_sensitivity",
                maximum=Decimal("1"),
            )
            if normalized is None:
                raise ValueError(
                    "MODEL_SENSITIVITY requires normalized_sensitivity"
                )
            sensitivity = float(normalized)
        elif sensitivity is not None:
            raise ValueError(
                "normalized_sensitivity is only valid for MODEL_SENSITIVITY"
            )
        object.__setattr__(self, "signal_type", signal_type)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "operational_status", status)
        object.__setattr__(self, "normalized_sensitivity", sensitivity)


@dataclass(frozen=True, slots=True)
class BackfillGapCommand:
    requirement_type: str
    state: str
    evidence_class: str
    claim_authority_version_id: str | None
    applicability_scope: Mapping[str, object]
    conflicts: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        requirement = _required_text(
            self.requirement_type,
            "requirement_type",
        ).upper()
        state = _required_text(self.state, "state").upper()
        evidence_class = _required_text(
            self.evidence_class,
            "evidence_class",
        ).upper()
        if requirement not in BACKFILL_REQUIREMENT_TYPES:
            raise ValueError("unknown B8 requirement type")
        if state not in BACKFILL_GAP_STATES:
            raise ValueError("unknown B8 gap state")
        if evidence_class not in BACKFILL_EVIDENCE_CLASSES:
            raise ValueError("unknown B8 evidence class")
        authority_id = (
            _required_text(
                self.claim_authority_version_id,
                "claim_authority_version_id",
            )
            if self.claim_authority_version_id is not None
            else None
        )
        if state in _ACCEPTED_GAP_STATES and authority_id is None:
            raise ValueError("accepted B8 gaps require B7 authority")
        if state not in _ACCEPTED_GAP_STATES and authority_id is not None:
            raise ValueError("unaccepted B8 gaps cannot carry B7 authority")
        scope = dict(self.applicability_scope)
        if not scope:
            raise ValueError("applicability_scope must not be empty")
        conflicts = tuple(
            sorted(
                {
                    _required_text(item, "conflict")
                    for item in self.conflicts
                }
            )
        )
        missing = tuple(
            sorted(
                {
                    _required_text(item, "missing_requirement")
                    for item in self.missing_requirements
                }
            )
        )
        if state in _ACCEPTED_GAP_STATES and (conflicts or missing):
            raise ValueError("accepted B8 gaps cannot retain blockers")
        object.__setattr__(self, "requirement_type", requirement)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "evidence_class", evidence_class)
        object.__setattr__(self, "claim_authority_version_id", authority_id)
        object.__setattr__(self, "applicability_scope", scope)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "missing_requirements", missing)


@dataclass(frozen=True, slots=True)
class BackfillMaterialCommand:
    material_id: str
    chemical_family: str | None
    signals: tuple[BackfillSignalCommand, ...]
    gaps: tuple[BackfillGapCommand, ...]

    def __post_init__(self) -> None:
        material_id = _required_text(self.material_id, "material_id")
        family = (
            _required_text(self.chemical_family, "chemical_family")
            if self.chemical_family is not None
            else None
        )
        signals = tuple(self.signals)
        signal_types = tuple(item.signal_type for item in signals)
        if len(signal_types) != len(set(signal_types)):
            raise ValueError("duplicate B8 signal type")
        formula_status_count = sum(
            signal_type
            in {"ACTIVE_FORMULA", "SHIPPED_FORMULA", "REFERENCE_FORMULA"}
            for signal_type in signal_types
        )
        if formula_status_count > 1:
            raise ValueError("conflicting B8 formula operational statuses")
        gaps = tuple(self.gaps)
        requirements = tuple(item.requirement_type for item in gaps)
        if len(requirements) != len(set(requirements)):
            raise ValueError("duplicate B8 gap requirement")
        if set(requirements) != set(BACKFILL_REQUIREMENT_TYPES):
            raise ValueError("B8 material must classify every requirement")
        object.__setattr__(self, "material_id", material_id)
        object.__setattr__(self, "chemical_family", family)
        object.__setattr__(
            self,
            "signals",
            tuple(sorted(signals, key=lambda item: item.signal_type)),
        )
        object.__setattr__(
            self,
            "gaps",
            tuple(
                sorted(
                    gaps,
                    key=lambda item: BACKFILL_REQUIREMENT_TYPES.index(
                        item.requirement_type
                    ),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class CreateBackfillCampaignCommand:
    campaign_key: str
    name: str
    purpose: str
    as_of_utc: datetime
    reviewer_pseudonym: str
    reviewed_at: datetime
    materials: tuple[BackfillMaterialCommand, ...]
    parent_version_id: str | None = None

    def __post_init__(self) -> None:
        campaign_key = _required_text(self.campaign_key, "campaign_key")
        name = _required_text(self.name, "name")
        purpose = _required_text(self.purpose, "purpose")
        reviewer = _required_text(
            self.reviewer_pseudonym,
            "reviewer_pseudonym",
        )
        as_of = _utc(self.as_of_utc, "as_of_utc")
        reviewed = _utc(self.reviewed_at, "reviewed_at")
        if reviewed < as_of:
            raise ValueError("reviewed_at cannot precede as_of_utc")
        materials = tuple(self.materials)
        if not materials:
            raise ValueError("B8 campaign requires at least one material")
        material_ids = tuple(item.material_id for item in materials)
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("duplicate B8 campaign material")
        parent_id = (
            _required_text(self.parent_version_id, "parent_version_id")
            if self.parent_version_id is not None
            else None
        )
        object.__setattr__(self, "campaign_key", campaign_key)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "reviewer_pseudonym", reviewer)
        object.__setattr__(self, "as_of_utc", as_of)
        object.__setattr__(self, "reviewed_at", reviewed)
        object.__setattr__(
            self,
            "materials",
            tuple(sorted(materials, key=lambda item: item.material_id)),
        )
        object.__setattr__(self, "parent_version_id", parent_id)


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


@dataclass(frozen=True, slots=True)
class _ResolvedBackfillSignal:
    command: BackfillSignalCommand
    evidence_class: str
    foreign_keys: Mapping[str, str | None]
    signal_value: Mapping[str, object]
    applicability: Mapping[str, object]
    limitations: tuple[str, ...]
    upstream_content_sha256: str


@dataclass(frozen=True, slots=True)
class _ResolvedBackfillGap:
    command: BackfillGapCommand
    projection: BackfillGapProjection
    applicability_scope_sha256: str
    source_references: tuple[Mapping[str, object], ...]
    upstream_content_sha256: str | None


@dataclass(frozen=True, slots=True)
class _ResolvedBackfillBundle:
    command: BackfillMaterialCommand
    canonical_name: str
    signals: tuple[_ResolvedBackfillSignal, ...]
    gaps: tuple[_ResolvedBackfillGap, ...]
    projection: ResolvedBackfillMaterial


def _signal_foreign_keys(
    selected_key: str,
    source_id: str,
) -> dict[str, str | None]:
    if selected_key not in _SIGNAL_FOREIGN_KEYS:
        raise ValueError("unknown B8 signal foreign key")
    return {
        key: source_id if key == selected_key else None
        for key in _SIGNAL_FOREIGN_KEYS
    }


def _signal_source_id(row: LabBackfillPrioritySignalLink) -> str:
    values = [
        str(getattr(row, key))
        for key in _SIGNAL_FOREIGN_KEYS
        if getattr(row, key) is not None
    ]
    if len(values) != 1:
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_SHAPE_MISMATCH",
            "A persisted B8 signal must have exactly one typed source.",
        )
    return values[0]


def _signal_vector(
    signals: Sequence[_ResolvedBackfillSignal],
) -> BackfillSignalVector:
    current_inventory: bool | None = None
    active_or_shipped: bool | None = None
    high_dose: float | None = None
    potent_trace: float | None = None
    regulatory_or_family: int | None = None
    analytical_standard: bool | None = None
    natural_constituent: bool | None = None
    model_sensitivity: float | None = None
    for resolved in signals:
        signal_type = resolved.command.signal_type
        value = resolved.signal_value
        if signal_type == "CURRENT_INVENTORY":
            current_inventory = bool(value["positive_balance"])
        elif signal_type in {"ACTIVE_FORMULA", "SHIPPED_FORMULA"}:
            active_or_shipped = True
        elif signal_type == "REFERENCE_FORMULA":
            if active_or_shipped is None:
                active_or_shipped = False
        elif signal_type == "HIGH_DOSE_STRUCTURE":
            high_dose = _object_float(value["active_mass_share"])
        elif signal_type == "POTENT_TRACE":
            potent_trace = _object_float(value["potency_priority"])
        elif signal_type in {"REGULATORY_DRIVER", "FAMILY_DRIVER"}:
            regulatory_or_family = (
                (regulatory_or_family or 0)
                + _object_int(value["driver_count"])
            )
        elif signal_type == "ANALYTICAL_STANDARD":
            analytical_standard = True
        elif signal_type == "NATURAL_CONSTITUENT":
            natural_constituent = True
        elif signal_type == "MODEL_SENSITIVITY":
            model_sensitivity = _object_float(
                value["normalized_sensitivity"]
            )
    return BackfillSignalVector(
        current_inventory=current_inventory,
        active_or_shipped_formula=active_or_shipped,
        high_dose_structure=high_dose,
        potent_trace=potent_trace,
        regulatory_or_family_driver=regulatory_or_family,
        analytical_standard=analytical_standard,
        natural_constituent=natural_constituent,
        model_sensitivity=model_sensitivity,
    )


def _object_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float, str, Decimal),
    ):
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_VALUE_INVALID",
            "A B8 numeric signal value is invalid.",
        )
    try:
        normalized = float(value)
    except ValueError as exc:
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_VALUE_INVALID",
            "A B8 numeric signal value is invalid.",
        ) from exc
    if not isfinite(normalized):
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_VALUE_INVALID",
            "A B8 numeric signal value must be finite.",
        )
    return normalized


def _object_int(value: object) -> int:
    normalized = _object_float(value)
    if not normalized.is_integer():
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_VALUE_INVALID",
            "A B8 count signal must be an integer.",
        )
    return int(normalized)


def _signal_vector_json(
    vector: BackfillSignalVector,
    *,
    chemical_family: str | None,
    evidence_class: str,
) -> dict[str, object]:
    return {
        "current_inventory": vector.current_inventory,
        "active_or_shipped_formula": vector.active_or_shipped_formula,
        "high_dose_structure": vector.high_dose_structure,
        "potent_trace": vector.potent_trace,
        "regulatory_or_family_driver": (
            vector.regulatory_or_family_driver
        ),
        "analytical_standard": vector.analytical_standard,
        "natural_constituent": vector.natural_constituent,
        "model_sensitivity": vector.model_sensitivity,
        "chemical_family": chemical_family,
        "evidence_class": evidence_class,
    }


def _material_evidence_class(
    gaps: Sequence[_ResolvedBackfillGap],
) -> str:
    classes = {gap.command.evidence_class for gap in gaps}
    if len(classes) == 1:
        return next(iter(classes))
    return "UNKNOWN"


def _input_snapshot_payload(
    bundles: Sequence[_ResolvedBackfillBundle],
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-input-v1",
        "materials": [
            {
                "material_id": bundle.command.material_id,
                "canonical_name": bundle.canonical_name,
                "chemical_family": bundle.command.chemical_family,
                "signals": [
                    {
                        "signal_type": signal.command.signal_type,
                        "source_id": signal.command.source_id,
                        "operational_status": (
                            signal.command.operational_status
                        ),
                        "normalized_sensitivity": (
                            signal.command.normalized_sensitivity
                        ),
                        "upstream_content_sha256": (
                            signal.upstream_content_sha256
                        ),
                    }
                    for signal in bundle.signals
                ],
                "gaps": [
                    {
                        "requirement_type": gap.command.requirement_type,
                        "state": gap.command.state,
                        "evidence_class": gap.command.evidence_class,
                        "claim_authority_version_id": (
                            gap.command.claim_authority_version_id
                        ),
                        "applicability_scope": dict(
                            gap.command.applicability_scope
                        ),
                        "conflicts": list(gap.command.conflicts),
                        "missing_requirements": list(
                            gap.command.missing_requirements
                        ),
                        "upstream_content_sha256": (
                            gap.upstream_content_sha256
                        ),
                    }
                    for gap in bundle.gaps
                ],
            }
            for bundle in bundles
        ],
    }


def _signal_row_payload(
    *,
    campaign_key: str,
    version_number: int,
    material_id: str,
    position: int,
    signal: _ResolvedBackfillSignal,
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-signal-v1",
        "campaign_key": campaign_key,
        "version_number": version_number,
        "material_id": material_id,
        "position": position,
        "signal_type": signal.command.signal_type,
        "source_id": signal.command.source_id,
        "evidence_class": signal.evidence_class,
        "signal_value": dict(signal.signal_value),
        "applicability": dict(signal.applicability),
        "limitations": list(signal.limitations),
        "upstream_content_sha256": signal.upstream_content_sha256,
    }


def _gap_row_payload(
    *,
    campaign_key: str,
    version_number: int,
    material_id: str,
    position: int,
    gap: _ResolvedBackfillGap,
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-gap-v1",
        "campaign_key": campaign_key,
        "version_number": version_number,
        "material_id": material_id,
        "position": position,
        "requirement_type": gap.command.requirement_type,
        "state": gap.command.state,
        "evidence_class": gap.command.evidence_class,
        "claim_authority_version_id": (
            gap.command.claim_authority_version_id
        ),
        "applicability_scope": dict(gap.command.applicability_scope),
        "applicability_scope_sha256": gap.applicability_scope_sha256,
        "conflicts": list(gap.command.conflicts),
        "missing_requirements": list(gap.command.missing_requirements),
        "source_references": [
            dict(reference) for reference in gap.source_references
        ],
        "upstream_content_sha256": gap.upstream_content_sha256,
    }


def _priority_source_references(
    bundle: _ResolvedBackfillBundle,
) -> list[dict[str, object]]:
    references: list[dict[str, object]] = [
        {
            "kind": signal.command.signal_type,
            "source_id": signal.command.source_id,
            "upstream_content_sha256": signal.upstream_content_sha256,
        }
        for signal in bundle.signals
    ]
    references.extend(
        {
            "kind": gap.command.requirement_type,
            "source_id": gap.command.claim_authority_version_id,
            "upstream_content_sha256": gap.upstream_content_sha256,
        }
        for gap in bundle.gaps
        if gap.upstream_content_sha256 is not None
    )
    return references


def _priority_row_payload(
    *,
    campaign_key: str,
    version_number: int,
    ranked: RankedBackfillMaterial,
    signal_vector_json: Mapping[str, object],
    source_references: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-priority-v1",
        "campaign_key": campaign_key,
        "version_number": version_number,
        "material_id": ranked.material_id,
        "rank": ranked.rank,
        "primary_priority_class": ranked.primary_priority_class,
        "signal_vector": dict(signal_vector_json),
        "rank_key": list(ranked.rank_key),
        "rank_key_sha256": ranked.rank_key_sha256,
        "critical_unresolved_gap_count": (
            ranked.critical_unresolved_gap_count
        ),
        "total_unresolved_gap_count": ranked.total_unresolved_gap_count,
        "source_references": [
            dict(reference) for reference in source_references
        ],
    }


def _dashboard_row_payload(
    *,
    campaign_key: str,
    version_number: int,
    cell: BackfillDashboardProjection,
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-dashboard-cell-v1",
        "campaign_key": campaign_key,
        "version_number": version_number,
        "dimension": cell.dimension,
        "dimension_key": cell.dimension_key,
        "material_count": cell.material_count,
        "requirements_total": cell.requirements_total,
        "accepted_exact_count": cell.accepted_exact_count,
        "accepted_scoped_count": cell.accepted_scoped_count,
        "weak_count": cell.weak_count,
        "conflicted_count": cell.conflicted_count,
        "unknown_count": cell.unknown_count,
        "missing_count": cell.missing_count,
        "not_applicable_count": cell.not_applicable_count,
    }


def _campaign_row_payload(
    *,
    campaign_key: str,
    version_number: int,
    name: str,
    purpose: str,
    as_of_utc: datetime,
    priority_policy_sha256: str,
    input_snapshot_sha256: str,
    counts: Mapping[str, int],
    reviewer_pseudonym: str,
    reviewed_at: datetime,
    parent_sha256: str | None,
    child_hashes: Mapping[str, Sequence[str]],
) -> dict[str, object]:
    return {
        "schema": "lab-backfill-campaign-v1",
        "campaign_key": campaign_key,
        "version_number": version_number,
        "name": name,
        "purpose": purpose,
        "as_of_utc": as_of_utc.isoformat(),
        "priority_policy_version": "b8-priority-v1",
        "priority_policy": BACKFILL_PRIORITY_POLICY,
        "priority_policy_sha256": priority_policy_sha256,
        "input_snapshot_sha256": input_snapshot_sha256,
        **dict(counts),
        "release_authority": False,
        "reviewer_pseudonym": reviewer_pseudonym,
        "reviewed_at": reviewed_at.isoformat(),
        "parent_sha256": parent_sha256,
        "child_hashes": {
            key: list(values) for key, values in child_hashes.items()
        },
    }


class LabBackfillServiceMixin:
    """Atomic B8 campaign creation and deterministic reconstruction."""

    repository: Any

    if TYPE_CHECKING:

        def _transaction(self) -> Any: ...

        async def reconstruct_claim_authority(
            self,
            version_id: str,
        ) -> dict[str, Any]: ...

    async def _resolve_backfill_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
        reviewer_pseudonym: str,
        reviewed_at: datetime,
    ) -> _ResolvedBackfillSignal:
        if command.signal_type == "CURRENT_INVENTORY":
            return await self._resolve_inventory_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type in {
            "ACTIVE_FORMULA",
            "SHIPPED_FORMULA",
            "REFERENCE_FORMULA",
            "HIGH_DOSE_STRUCTURE",
        }:
            return await self._resolve_formula_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
                reviewer_pseudonym=reviewer_pseudonym,
                reviewed_at=reviewed_at,
            )
        if command.signal_type == "MODEL_SENSITIVITY":
            return await self._resolve_model_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type == "POTENT_TRACE":
            return await self._resolve_potent_trace_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type == "FAMILY_DRIVER":
            return await self._resolve_family_driver_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type == "REGULATORY_DRIVER":
            return await self._resolve_regulatory_driver_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type == "ANALYTICAL_STANDARD":
            return await self._resolve_analytical_standard_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        if command.signal_type == "NATURAL_CONSTITUENT":
            return await self._resolve_natural_constituent_signal(
                material_id=material_id,
                command=command,
                as_of_utc=as_of_utc,
            )
        raise BackfillConflictError(
            "BACKFILL_SIGNAL_NOT_IMPLEMENTED",
            f"B8 signal resolution is unavailable: {command.signal_type}.",
        )

    async def _resolve_inventory_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        stock = await self.repository.get_stock(command.source_id)
        if stock is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 inventory stock source does not exist.",
            )
        if stock.material_id != material_id:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B8 inventory stock belongs to another material.",
            )
        balance_g = float(
            await self.repository.stock_balance_g(command.source_id)
        )
        if not isfinite(balance_g) or balance_g <= 0:
            raise BackfillConflictError(
                "BACKFILL_INVENTORY_NOT_POSITIVE",
                "Current-inventory priority requires a positive balance.",
            )
        stock_snapshot = {
            "schema": "lab-stock-snapshot-v1",
            "stock_solution_id": stock.id,
            "created_at": stock.created_at.isoformat(),
            "material_id": stock.material_id,
            "supplier": stock.supplier,
            "lot_number": stock.lot_number,
            "active_fraction": float(stock.active_fraction),
            "fraction_basis": stock.fraction_basis,
            "density_g_ml": (
                float(stock.density_g_ml)
                if stock.density_g_ml is not None
                else None
            ),
            "solvent_name": stock.solvent_name,
            "initial_mass_g": float(stock.initial_mass_g),
            "remaining_mass_g": (
                float(stock.remaining_mass_g)
                if stock.remaining_mass_g is not None
                else None
            ),
            "source": stock.source_json,
            "reconstructed_balance_g": balance_g,
        }
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="UNKNOWN",
            foreign_keys=_signal_foreign_keys(
                "stock_solution_id",
                stock.id,
            ),
            signal_value={
                "positive_balance": True,
                "balance_g": balance_g,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
            },
            limitations=(
                "OPERATIONAL_INVENTORY_SIGNAL_NOT_SCIENTIFIC_AUTHORITY",
            ),
            upstream_content_sha256=_sha(stock_snapshot),
        )

    async def _resolve_formula_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
        reviewer_pseudonym: str,
        reviewed_at: datetime,
    ) -> _ResolvedBackfillSignal:
        component = await self.repository.get_formula_component(
            command.source_id
        )
        if component is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 formula component source does not exist.",
            )
        stock = await self.repository.get_stock(
            component.stock_solution_id
        )
        if stock is None:
            raise BackfillConflictError(
                "BACKFILL_FORMULA_STOCK_NOT_FOUND",
                "The B8 formula component stock does not exist.",
            )
        if stock.material_id != material_id:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B8 formula component belongs to another material.",
            )
        formula_version = await self.repository.get_formula_version(
            component.formula_version_id
        )
        if formula_version is None:
            raise BackfillConflictError(
                "BACKFILL_FORMULA_VERSION_NOT_FOUND",
                "The B8 formula version does not exist.",
            )
        components = await self.repository.formula_components(
            formula_version.id
        )
        if not components or not any(
            item.id == component.id for item in components
        ):
            raise BackfillConflictError(
                "BACKFILL_FORMULA_INCOMPLETE",
                "The B8 formula component set is incomplete.",
            )
        component_snapshots: list[dict[str, object]] = []
        total_active_mass = 0.0
        component_active_mass = 0.0
        for item in components:
            item_stock = await self.repository.get_stock(
                item.stock_solution_id
            )
            requested_mass = float(item.requested_mass_g)
            if (
                item_stock is None
                or item.unit != "g"
                or not isfinite(requested_mass)
                or requested_mass <= 0
                or not 0 < float(item_stock.active_fraction) <= 1
            ):
                raise BackfillConflictError(
                    "BACKFILL_FORMULA_INCOMPLETE",
                    "High-dose priority requires complete active-mass inputs.",
                )
            active_mass = requested_mass * float(
                item_stock.active_fraction
            )
            total_active_mass += active_mass
            if item.id == component.id:
                component_active_mass = active_mass
            component_snapshots.append(
                {
                    "component_id": item.id,
                    "stock_solution_id": item.stock_solution_id,
                    "material_id": item_stock.material_id,
                    "position": item.position,
                    "requested_mass_g": requested_mass,
                    "requested_volume_ul": item.requested_volume_ul,
                    "role": item.role,
                    "unit": item.unit,
                    "active_fraction": float(
                        item_stock.active_fraction
                    ),
                }
            )
        if total_active_mass <= 0 or component_active_mass <= 0:
            raise BackfillConflictError(
                "BACKFILL_FORMULA_INCOMPLETE",
                "The B8 formula has no positive active-mass denominator.",
            )
        active_mass_share = component_active_mass / total_active_mass
        formula_snapshot = {
            "schema": "lab-formula-component-snapshot-v1",
            "formula_version_id": formula_version.id,
            "formula_id": formula_version.formula_id,
            "version_number": formula_version.version_number,
            "brief": formula_version.brief_json,
            "constraints": formula_version.constraints_json,
            "concentration_fraction": (
                float(formula_version.concentration_fraction)
                if formula_version.concentration_fraction is not None
                else None
            ),
            "concentration_basis": (
                formula_version.concentration_basis
            ),
            "source": formula_version.source_json,
            "components": component_snapshots,
        }
        status_signal = command.signal_type in {
            "ACTIVE_FORMULA",
            "SHIPPED_FORMULA",
            "REFERENCE_FORMULA",
        }
        signal_value: dict[str, object]
        limitations: tuple[str, ...]
        applicability = {
            "material_id": material_id,
            "formula_version_id": formula_version.id,
            "as_of_utc": as_of_utc.isoformat(),
            "operational_status": command.operational_status,
            "reviewer_pseudonym": (
                reviewer_pseudonym if status_signal else None
            ),
            "reviewed_at": (
                reviewed_at.isoformat() if status_signal else None
            ),
        }
        if status_signal:
            signal_value = {
                "declared_status": str(command.operational_status),
                "reviewed_local_record": True,
            }
            limitations = (
                "LOCAL_RECORD_FORMULA_STATUS_NOT_SCIENTIFIC_AUTHORITY",
            )
        else:
            signal_value = {
                "active_mass_share": active_mass_share,
                "component_active_mass_g": component_active_mass,
                "formula_active_mass_g": total_active_mass,
            }
            limitations = (
                "FORMULA_DOSE_IS_A_PLANNING_SIGNAL_NOT_EVIDENCE_QUALITY",
            )
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="UNKNOWN",
            foreign_keys=_signal_foreign_keys(
                "formula_component_id",
                component.id,
            ),
            signal_value=signal_value,
            applicability=applicability,
            limitations=limitations,
            upstream_content_sha256=_sha(formula_snapshot),
        )

    async def _resolve_model_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        prediction = await self.repository.get_prediction(command.source_id)
        if prediction is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 model prediction source does not exist.",
            )
        if prediction.status.upper() not in {
            "COMPUTED",
            "COMPLETE",
            "READY",
            "SUCCEEDED",
        }:
            raise BackfillConflictError(
                "BACKFILL_MODEL_NOT_COMPUTED",
                "Model sensitivity requires a completed prediction.",
            )
        sensitivity_map = prediction.prediction_json.get(
            "normalized_sensitivity_by_material"
        )
        if not isinstance(sensitivity_map, dict) or (
            material_id not in sensitivity_map
        ):
            raise BackfillConflictError(
                "BACKFILL_MODEL_MATERIAL_MISSING",
                "The model prediction lacks exact material sensitivity.",
            )
        stored_sensitivity = _normalized_number(
            sensitivity_map[material_id],
            name="normalized_sensitivity",
            maximum=Decimal("1"),
        )
        requested_sensitivity = _normalized_number(
            command.normalized_sensitivity,
            name="normalized_sensitivity",
            maximum=Decimal("1"),
        )
        if (
            stored_sensitivity is None
            or requested_sensitivity is None
            or stored_sensitivity != requested_sensitivity
        ):
            raise BackfillConflictError(
                "BACKFILL_MODEL_SENSITIVITY_MISMATCH",
                "Caller sensitivity differs from the model record.",
            )
        prediction_snapshot = {
            "schema": "lab-prediction-snapshot-v1",
            "prediction_id": prediction.id,
            "created_at": prediction.created_at.isoformat(),
            "experiment_id": prediction.experiment_id,
            "sample_id": prediction.sample_id,
            "model_key": prediction.model_key,
            "model_version": prediction.model_version,
            "status": prediction.status,
            "prediction": prediction.prediction_json,
            "evidence_id": prediction.evidence_id,
        }
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="MODEL_ESTIMATED",
            foreign_keys=_signal_foreign_keys(
                "prediction_id",
                prediction.id,
            ),
            signal_value={
                "normalized_sensitivity": float(stored_sensitivity),
                "model_key": prediction.model_key,
                "model_version": prediction.model_version,
                "status": prediction.status,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
            },
            limitations=(
                "MODEL_SENSITIVITY_IS_MODEL_ESTIMATED_NOT_MEASURED",
            ),
            upstream_content_sha256=_sha(prediction_snapshot),
        )

    async def _resolve_potent_trace_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        assessment = await self.repository.get_oav_assessment(
            command.source_id
        )
        if assessment is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 OAV assessment source does not exist.",
            )
        if (
            not assessment.strict_science_mode
            or assessment.status != "COMPUTED"
            or assessment.mismatch_count != 0
            or assessment.oav_value is None
            or not isfinite(float(assessment.oav_value))
            or float(assessment.oav_value) <= 0
        ):
            raise BackfillConflictError(
                "BACKFILL_OAV_NOT_STRICT",
                "Potent-trace priority requires a strict computed B3 OAV.",
            )
        concentration = await self.repository.get_property_observation(
            assessment.concentration_observation_id
        )
        if concentration is None:
            raise BackfillConflictError(
                "BACKFILL_OAV_CONCENTRATION_NOT_FOUND",
                "The B3 OAV concentration observation does not exist.",
            )
        identity = concentration.subject_identity_json
        if (
            not isinstance(identity, dict)
            or str(identity.get("material_id")) != material_id
        ):
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B3 OAV concentration belongs to another material.",
            )
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="LITERATURE_DERIVED",
            foreign_keys=_signal_foreign_keys(
                "oav_assessment_id",
                assessment.id,
            ),
            signal_value={
                "potency_priority": float(assessment.oav_value),
                "oav_value": float(assessment.oav_value),
                "status": assessment.status,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
                "requested_endpoint": assessment.requested_endpoint,
                "requested_route": assessment.requested_route,
                "input_snapshot": assessment.input_snapshot_json,
            },
            limitations=(
                "OAV_IS_CONTEXT_SPECIFIC_AND_NOT_AN_ODOR_QUALITY_SCORE",
            ),
            upstream_content_sha256=_sha(
                {
                    "schema": "lab-b8-oav-source-v1",
                    "assessment_content_sha256": (
                        assessment.content_sha256
                    ),
                    "concentration_observation_id": concentration.id,
                    "concentration_evidence_class": (
                        concentration.evidence_class
                    ),
                    "material_id": material_id,
                }
            ),
        )

    async def _resolve_family_driver_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        rule = await self.repository.get_knowledge_rule(command.source_id)
        if rule is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 family-rule source does not exist.",
            )
        if (
            rule.status != "AUTHORITATIVE"
            or rule.review_state != "APPROVED"
            or rule.runtime_role != "BLOCKING"
        ):
            raise BackfillConflictError(
                "BACKFILL_RULE_NOT_AUTHORITATIVE",
                "Family-driver priority requires an approved blocking rule.",
            )
        matrix_context = rule.matrix_context_json
        material_ids = (
            matrix_context.get("material_ids")
            if isinstance(matrix_context, dict)
            else None
        )
        bound_by_context = (
            isinstance(matrix_context, dict)
            and str(matrix_context.get("material_id")) == material_id
        ) or (
            isinstance(material_ids, list)
            and material_id in {str(item) for item in material_ids}
        )
        identity_hash = _sha({"material_id": material_id})
        bound_by_identity = identity_hash in {
            rule.subject_identity_scope_sha256,
            rule.object_identity_scope_sha256,
        }
        if not bound_by_context and not bound_by_identity:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B4 family rule is not bound to this material.",
            )
        evidence_class = (
            rule.evidence_class
            if rule.evidence_class in BACKFILL_EVIDENCE_CLASSES
            else "UNKNOWN"
        )
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class=evidence_class,
            foreign_keys=_signal_foreign_keys(
                "knowledge_rule_id",
                rule.id,
            ),
            signal_value={
                "driver_count": 1,
                "runtime_role": rule.runtime_role,
                "relation": rule.relation,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
                "matrix_context": matrix_context,
            },
            limitations=(
                "RULE_APPLIES_ONLY_WITHIN_ITS_EXACT_B4_DOMAIN",
            ),
            upstream_content_sha256=_sha(
                {
                    "schema": "lab-b8-family-rule-source-v1",
                    "rule_content_sha256": rule.content_sha256,
                    "material_id": material_id,
                }
            ),
        )

    async def _resolve_regulatory_driver_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        snapshot = (
            await self.repository.get_regulatory_snapshot_version(
                command.source_id
            )
        )
        if snapshot is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 regulatory snapshot source does not exist.",
            )
        if snapshot.result_state != "PASS_FOR_DECLARED_SCOPE":
            raise BackfillConflictError(
                "BACKFILL_REGULATORY_NOT_PASSING",
                "Regulatory priority requires a passing exact B6 snapshot.",
            )
        if snapshot.subject_type != "FORMULA_VERSION":
            raise BackfillConflictError(
                "BACKFILL_REGULATORY_SUBJECT_UNSUPPORTED",
                "B8 material binding currently requires a formula snapshot.",
            )
        formula_version = await self.repository.get_formula_version(
            snapshot.subject_id
        )
        if formula_version is None:
            raise BackfillConflictError(
                "BACKFILL_FORMULA_VERSION_NOT_FOUND",
                "The B6 regulatory formula version does not exist.",
            )
        components = await self.repository.formula_components(
            formula_version.id
        )
        matched_components: list[str] = []
        for component in components:
            stock = await self.repository.get_stock(
                component.stock_solution_id
            )
            if stock is not None and stock.material_id == material_id:
                matched_components.append(component.id)
        if not matched_components:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B6 regulatory formula does not contain this material.",
            )
        driver_count = max(1, len(snapshot.rule_version_ids_json))
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="LITERATURE_DERIVED",
            foreign_keys=_signal_foreign_keys(
                "regulatory_snapshot_version_id",
                snapshot.id,
            ),
            signal_value={
                "driver_count": driver_count,
                "result_state": snapshot.result_state,
                "rule_count": len(snapshot.rule_version_ids_json),
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
                "formula_version_id": formula_version.id,
                "component_ids": sorted(matched_components),
                "jurisdiction": snapshot.jurisdiction,
                "product_category": snapshot.product_category,
                "use_classification": snapshot.use_classification,
            },
            limitations=(
                "REGULATORY_RESULT_APPLIES_ONLY_TO_DECLARED_B6_SCOPE",
            ),
            upstream_content_sha256=_sha(
                {
                    "schema": "lab-b8-regulatory-source-v1",
                    "snapshot_content_sha256": snapshot.content_sha256,
                    "material_id": material_id,
                    "component_ids": sorted(matched_components),
                }
            ),
        )

    async def _resolve_analytical_standard_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        entry = await self.repository.get_analytical_sequence_entry(
            command.source_id
        )
        if entry is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 analytical sequence-entry source does not exist.",
            )
        if str(entry.level_json.get("material_id")) != material_id:
            raise BackfillConflictError(
                "BACKFILL_ANALYTICAL_MATERIAL_MISMATCH",
                "The B5 analytical entry is not bound to this material.",
            )
        accepted_roles = {
            "CALIBRATION_STANDARD",
            "INTERNAL_STANDARD",
            "SPIKE",
            "RI_STANDARD",
            "CONTROL",
        }
        if entry.role not in accepted_roles:
            raise BackfillConflictError(
                "BACKFILL_ANALYTICAL_ROLE_INVALID",
                "The B5 entry is not an analytical-standard role.",
            )
        sequence = await self.repository.get_analytical_sequence(
            entry.sequence_id
        )
        if sequence is None or sequence.status == "CANCELLED":
            raise BackfillConflictError(
                "BACKFILL_ANALYTICAL_SEQUENCE_INVALID",
                "The B5 analytical sequence is absent or cancelled.",
            )
        sequence_entries = (
            await self.repository.analytical_sequence_entries(sequence.id)
        )
        if (
            sequence.entry_count != len(sequence_entries)
            or not any(item.id == entry.id for item in sequence_entries)
        ):
            raise BackfillConflictError(
                "BACKFILL_ANALYTICAL_SEQUENCE_INVALID",
                "The B5 sequence entry set does not reconcile.",
            )
        method = (
            await self.repository.get_analytical_method_authority(
                sequence.method_authority_id
            )
        )
        if method is None or method.status not in {
            "VERIFIED",
            "VALIDATED_FOR_SCOPE",
        }:
            raise BackfillConflictError(
                "BACKFILL_ANALYTICAL_METHOD_INVALID",
                "The B5 analytical method is not verified for use.",
            )
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class="UNKNOWN",
            foreign_keys=_signal_foreign_keys(
                "analytical_sequence_entry_id",
                entry.id,
            ),
            signal_value={
                "standard_role": entry.role,
                "sequence_status": sequence.status,
                "method_status": method.status,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
                "level": entry.level_json,
                "sequence_id": sequence.id,
                "method_authority_id": method.id,
            },
            limitations=(
                "ANALYTICAL_STANDARD_USE_IS_NOT_ITSELF_A_MEASUREMENT_CLAIM",
            ),
            upstream_content_sha256=_sha(
                {
                    "schema": "lab-b8-analytical-standard-source-v1",
                    "entry_content_sha256": entry.content_sha256,
                    "sequence_content_sha256": sequence.content_sha256,
                    "method_content_sha256": method.content_sha256,
                }
            ),
        )

    async def _resolve_natural_constituent_signal(
        self,
        *,
        material_id: str,
        command: BackfillSignalCommand,
        as_of_utc: datetime,
    ) -> _ResolvedBackfillSignal:
        entry = await self.repository.get_regulatory_composition_entry(
            command.source_id
        )
        if entry is None:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_SOURCE_NOT_FOUND",
                "The B8 natural-composition entry source does not exist.",
            )
        if entry.material_id != material_id:
            raise BackfillConflictError(
                "BACKFILL_SIGNAL_MATERIAL_MISMATCH",
                "The B6 composition entry belongs to another material.",
            )
        profile = (
            await self.repository.get_regulatory_composition_profile(
                entry.composition_profile_id
            )
        )
        if (
            profile is None
            or profile.origin != "NATURAL"
            or profile.completeness != "COMPLETE"
        ):
            raise BackfillConflictError(
                "BACKFILL_NATURAL_PROFILE_INCOMPLETE",
                "Natural priority requires a complete B6 natural profile.",
            )
        fraction = float(entry.fraction)
        if not isfinite(fraction) or fraction <= 0 or fraction > 1:
            raise BackfillConflictError(
                "BACKFILL_NATURAL_FRACTION_INVALID",
                "The B6 natural constituent fraction is invalid.",
            )
        evidence_class = (
            "SUPPLIER_PROVIDED"
            if profile.supplier_document_binding_id is not None
            else "UNKNOWN"
        )
        return _ResolvedBackfillSignal(
            command=command,
            evidence_class=evidence_class,
            foreign_keys=_signal_foreign_keys(
                "composition_entry_id",
                entry.id,
            ),
            signal_value={
                "fraction": fraction,
                "fraction_basis": entry.fraction_basis,
                "profile_completeness": profile.completeness,
            },
            applicability={
                "material_id": material_id,
                "as_of_utc": as_of_utc.isoformat(),
                "operational_status": None,
                "composition_profile_id": profile.id,
                "natural_stock_solution_id": profile.stock_solution_id,
            },
            limitations=(
                "NATURAL_COMPOSITION_IS_PROFILE_AND_LOT_SCOPE_SPECIFIC",
            ),
            upstream_content_sha256=_sha(
                {
                    "schema": "lab-b8-natural-constituent-source-v1",
                    "entry_content_sha256": entry.content_sha256,
                    "profile_content_sha256": profile.content_sha256,
                }
            ),
        )

    async def _resolve_backfill_gap(
        self,
        *,
        material_id: str,
        command: BackfillGapCommand,
    ) -> _ResolvedBackfillGap:
        scoped_material = command.applicability_scope.get("material_id")
        if scoped_material is not None and str(scoped_material) != material_id:
            raise BackfillConflictError(
                "BACKFILL_GAP_MATERIAL_MISMATCH",
                "The B8 gap scope belongs to another material.",
            )
        authority_hash: str | None = None
        source_references: tuple[Mapping[str, object], ...] = ()
        if command.state in _ACCEPTED_GAP_STATES:
            authority_id = str(command.claim_authority_version_id)
            try:
                authority = await self.reconstruct_claim_authority(
                    authority_id
                )
            except ValueError as exc:
                raise BackfillConflictError(
                    "BACKFILL_B7_RECONSTRUCTION_FAILED",
                    "The proposed B7 authority did not reconstruct.",
                ) from exc
            expected_decision = (
                "ALLOW_EXACT"
                if command.state == "ACCEPTED_EXACT"
                else "ALLOW_SCOPED"
            )
            if authority["decision"] != expected_decision:
                raise BackfillConflictError(
                    "BACKFILL_B7_DECISION_MISMATCH",
                    "The B7 decision does not match the accepted gap state.",
                )
            authority_identity_scope = authority["identity_scope"]
            if (
                not isinstance(authority_identity_scope, dict)
                or str(authority_identity_scope.get("material_id"))
                != material_id
            ):
                raise BackfillConflictError(
                    "BACKFILL_B7_SUBJECT_MISMATCH",
                    "The B7 identity scope does not govern this material.",
                )
            if authority["claim_type"] not in _REQUIREMENT_CLAIM_TYPES[
                command.requirement_type
            ]:
                raise BackfillConflictError(
                    "BACKFILL_B7_CLAIM_TYPE_MISMATCH",
                    "The B7 claim type cannot resolve this requirement.",
                )
            expected_property_types = _REQUIREMENT_PROPERTY_TYPES.get(
                command.requirement_type
            )
            if expected_property_types is not None:
                claim_payload = authority["claim_payload"]
                property_type = (
                    str(claim_payload.get("property_type", "")).upper()
                    if isinstance(claim_payload, dict)
                    else ""
                )
                if property_type not in expected_property_types:
                    raise BackfillConflictError(
                        "BACKFILL_B7_PROPERTY_MISMATCH",
                        "The B7 property subtype cannot resolve this gap.",
                    )
            if (
                command.applicability_scope.get("identity_scope")
                != authority["identity_scope"]
                or command.applicability_scope.get("condition_scope")
                != authority["condition_scope"]
            ):
                raise BackfillConflictError(
                    "BACKFILL_B7_SCOPE_MISMATCH",
                    "The B8 applicability scope differs from B7 authority.",
                )
            authority_hash = str(authority["content_sha256"])
            source_references = tuple(
                dict(reference)
                for reference in authority["source_references"]
            )
        return _ResolvedBackfillGap(
            command=command,
            projection=BackfillGapProjection(
                requirement_type=command.requirement_type,
                state=command.state,
                evidence_class=command.evidence_class,
            ),
            applicability_scope_sha256=_sha(
                dict(command.applicability_scope)
            ),
            source_references=source_references,
            upstream_content_sha256=authority_hash,
        )

    async def _resolve_backfill_material(
        self,
        command: BackfillMaterialCommand,
        *,
        as_of_utc: datetime,
        reviewer_pseudonym: str,
        reviewed_at: datetime,
    ) -> _ResolvedBackfillBundle:
        material = await self.repository.get_material(command.material_id)
        if material is None:
            raise BackfillConflictError(
                "BACKFILL_MATERIAL_NOT_FOUND",
                f"B8 material not found: {command.material_id}.",
            )
        signals = tuple(
            [
                await self._resolve_backfill_signal(
                    material_id=command.material_id,
                    command=signal,
                    as_of_utc=as_of_utc,
                    reviewer_pseudonym=reviewer_pseudonym,
                    reviewed_at=reviewed_at,
                )
                for signal in command.signals
            ]
        )
        gaps = tuple(
            [
                await self._resolve_backfill_gap(
                    material_id=command.material_id,
                    command=gap,
                )
                for gap in command.gaps
            ]
        )
        vector = _signal_vector(signals)
        evidence_class = _material_evidence_class(gaps)
        projection = ResolvedBackfillMaterial(
            material_id=command.material_id,
            canonical_name=material.canonical_name,
            chemical_family=command.chemical_family,
            evidence_class=evidence_class,
            signal_vector=vector,
            gaps=tuple(gap.projection for gap in gaps),
        )
        return _ResolvedBackfillBundle(
            command=command,
            canonical_name=material.canonical_name,
            signals=signals,
            gaps=gaps,
            projection=projection,
        )

    async def _backfill_parent(
        self,
        command: CreateBackfillCampaignCommand,
    ) -> tuple[LabBackfillCampaignVersion | None, int]:
        latest = await self.repository.latest_backfill_campaign_version(
            command.campaign_key
        )
        if command.parent_version_id is None:
            if latest is not None:
                raise BackfillConflictError(
                    "BACKFILL_CAMPAIGN_EXISTS",
                    "An existing B8 campaign key requires its latest parent.",
                )
            return None, 1
        parent = await self.repository.get_backfill_campaign_version(
            command.parent_version_id
        )
        if parent is None:
            raise BackfillConflictError(
                "BACKFILL_PARENT_NOT_FOUND",
                "The B8 parent campaign version does not exist.",
            )
        if parent.campaign_key != command.campaign_key:
            raise BackfillConflictError(
                "BACKFILL_PARENT_CAMPAIGN_MISMATCH",
                "The B8 parent belongs to another campaign key.",
            )
        if latest is None or latest.id != parent.id:
            raise BackfillConflictError(
                "BACKFILL_PARENT_NOT_LATEST",
                "A B8 revision must use the latest parent.",
            )
        parent_priorities = (
            await self.repository.backfill_material_priorities(parent.id)
        )
        if {row.material_id for row in parent_priorities} != {
            material.material_id for material in command.materials
        }:
            raise BackfillConflictError(
                "BACKFILL_SCOPE_CHANGED",
                "A B8 revision cannot change its material scope.",
            )
        return parent, parent.version_number + 1

    async def create_backfill_campaign(
        self,
        command: CreateBackfillCampaignCommand,
    ) -> LabBackfillCampaignVersion:
        async with self._transaction():
            parent, version_number = await self._backfill_parent(command)
            bundles = tuple(
                [
                    await self._resolve_backfill_material(
                        material,
                        as_of_utc=command.as_of_utc,
                        reviewer_pseudonym=command.reviewer_pseudonym,
                        reviewed_at=command.reviewed_at,
                    )
                    for material in command.materials
                ]
            )
            ranked = rank_backfill_materials(
                [bundle.projection for bundle in bundles]
            )
            bundle_by_material = {
                bundle.command.material_id: bundle for bundle in bundles
            }
            dashboard = build_backfill_dashboard(ranked)
            policy_sha256 = backfill_policy_hash()
            input_snapshot_sha256 = _sha(
                _input_snapshot_payload(bundles)
            )

            priority_rows: list[LabBackfillMaterialPriority] = []
            signal_rows: list[LabBackfillPrioritySignalLink] = []
            gap_rows: list[LabBackfillGapItem] = []
            priority_hashes: list[str] = []
            signal_hashes: list[str] = []
            gap_hashes: list[str] = []
            for ranked_material in ranked:
                bundle = bundle_by_material[ranked_material.material_id]
                priority_id = str(uuid4())
                vector_json = _signal_vector_json(
                    ranked_material.signal_vector,
                    chemical_family=ranked_material.chemical_family,
                    evidence_class=ranked_material.evidence_class,
                )
                source_references = _priority_source_references(bundle)
                priority_payload = _priority_row_payload(
                    campaign_key=command.campaign_key,
                    version_number=version_number,
                    ranked=ranked_material,
                    signal_vector_json=vector_json,
                    source_references=source_references,
                )
                priority_hash = _sha(priority_payload)
                priority_hashes.append(priority_hash)
                priority_rows.append(
                    LabBackfillMaterialPriority(
                        id=priority_id,
                        campaign_version_id="pending",
                        material_id=ranked_material.material_id,
                        rank=ranked_material.rank,
                        primary_priority_class=(
                            ranked_material.primary_priority_class
                        ),
                        signal_vector_json=vector_json,
                        rank_key_json=list(ranked_material.rank_key),
                        rank_key_sha256=ranked_material.rank_key_sha256,
                        critical_unresolved_gap_count=(
                            ranked_material.critical_unresolved_gap_count
                        ),
                        total_unresolved_gap_count=(
                            ranked_material.total_unresolved_gap_count
                        ),
                        source_references_json=source_references,
                        content_sha256=priority_hash,
                    )
                )
                for position, signal in enumerate(bundle.signals, start=1):
                    signal_payload = _signal_row_payload(
                        campaign_key=command.campaign_key,
                        version_number=version_number,
                        material_id=ranked_material.material_id,
                        position=position,
                        signal=signal,
                    )
                    signal_hash = _sha(signal_payload)
                    signal_hashes.append(signal_hash)
                    signal_rows.append(
                        LabBackfillPrioritySignalLink(
                            material_priority_id=priority_id,
                            position=position,
                            signal_type=signal.command.signal_type,
                            evidence_class=signal.evidence_class,
                            signal_value_json=dict(signal.signal_value),
                            applicability_json=dict(signal.applicability),
                            limitations_json=list(signal.limitations),
                            upstream_content_sha256=(
                                signal.upstream_content_sha256
                            ),
                            content_sha256=signal_hash,
                            **dict(signal.foreign_keys),
                        )
                    )
                for position, gap in enumerate(bundle.gaps, start=1):
                    gap_payload = _gap_row_payload(
                        campaign_key=command.campaign_key,
                        version_number=version_number,
                        material_id=ranked_material.material_id,
                        position=position,
                        gap=gap,
                    )
                    gap_hash = _sha(gap_payload)
                    gap_hashes.append(gap_hash)
                    gap_rows.append(
                        LabBackfillGapItem(
                            material_priority_id=priority_id,
                            position=position,
                            requirement_type=gap.command.requirement_type,
                            state=gap.command.state,
                            evidence_class=gap.command.evidence_class,
                            claim_authority_version_id=(
                                gap.command.claim_authority_version_id
                            ),
                            applicability_scope_json=dict(
                                gap.command.applicability_scope
                            ),
                            applicability_scope_sha256=(
                                gap.applicability_scope_sha256
                            ),
                            conflicts_json=list(gap.command.conflicts),
                            conflict_count=len(gap.command.conflicts),
                            missing_requirements_json=list(
                                gap.command.missing_requirements
                            ),
                            missing_requirement_count=len(
                                gap.command.missing_requirements
                            ),
                            source_references_json=[
                                dict(reference)
                                for reference in gap.source_references
                            ],
                            upstream_content_sha256=(
                                gap.upstream_content_sha256
                            ),
                            content_sha256=gap_hash,
                        )
                    )

            dashboard_rows: list[LabBackfillDashboardCell] = []
            dashboard_hashes: list[str] = []
            for cell in dashboard:
                payload = _dashboard_row_payload(
                    campaign_key=command.campaign_key,
                    version_number=version_number,
                    cell=cell,
                )
                cell_hash = _sha(payload)
                dashboard_hashes.append(cell_hash)
                dashboard_rows.append(
                    LabBackfillDashboardCell(
                        campaign_version_id="pending",
                        dimension=cell.dimension,
                        dimension_key=cell.dimension_key,
                        material_count=cell.material_count,
                        requirements_total=cell.requirements_total,
                        accepted_exact_count=cell.accepted_exact_count,
                        accepted_scoped_count=cell.accepted_scoped_count,
                        weak_count=cell.weak_count,
                        conflicted_count=cell.conflicted_count,
                        unknown_count=cell.unknown_count,
                        missing_count=cell.missing_count,
                        not_applicable_count=cell.not_applicable_count,
                        content_sha256=cell_hash,
                    )
                )

            state_counts = _state_counts(
                [
                    gap.projection
                    for bundle in bundles
                    for gap in bundle.gaps
                ]
            )
            counts = {
                "material_count": len(bundles),
                "signal_count": len(signal_rows),
                "gap_count": len(gap_rows),
                "dashboard_cell_count": len(dashboard_rows),
                "accepted_exact_count": state_counts["ACCEPTED_EXACT"],
                "accepted_scoped_count": state_counts["ACCEPTED_SCOPED"],
                "weak_count": state_counts["WEAK"],
                "conflicted_count": state_counts["CONFLICTED"],
                "unknown_count": state_counts["UNKNOWN"],
                "missing_count": state_counts["MISSING"],
                "not_applicable_count": state_counts["NOT_APPLICABLE"],
            }
            child_hashes = {
                "priorities": priority_hashes,
                "signals": signal_hashes,
                "gaps": gap_hashes,
                "dashboard_cells": dashboard_hashes,
            }
            parent_sha256 = parent.content_sha256 if parent else None
            campaign_payload = _campaign_row_payload(
                campaign_key=command.campaign_key,
                version_number=version_number,
                name=command.name,
                purpose=command.purpose,
                as_of_utc=command.as_of_utc,
                priority_policy_sha256=policy_sha256,
                input_snapshot_sha256=input_snapshot_sha256,
                counts=counts,
                reviewer_pseudonym=command.reviewer_pseudonym,
                reviewed_at=command.reviewed_at,
                parent_sha256=parent_sha256,
                child_hashes=child_hashes,
            )
            campaign_hash = _sha(campaign_payload)
            if (
                await self.repository.backfill_campaign_by_hash(
                    campaign_hash
                )
                is not None
            ):
                raise BackfillConflictError(
                    "BACKFILL_CAMPAIGN_ALREADY_EXISTS",
                    "An identical B8 campaign version already exists.",
                )
            campaign_id = str(uuid4())
            campaign = LabBackfillCampaignVersion(
                id=campaign_id,
                campaign_key=command.campaign_key,
                version_number=version_number,
                parent_version_id=parent.id if parent else None,
                name=command.name,
                purpose=command.purpose,
                as_of_utc=command.as_of_utc,
                priority_policy_version="b8-priority-v1",
                priority_policy_json=json.loads(
                    _canonical_json(BACKFILL_PRIORITY_POLICY)
                ),
                priority_policy_sha256=policy_sha256,
                input_snapshot_sha256=input_snapshot_sha256,
                **counts,
                release_authority=False,
                reviewer_pseudonym=command.reviewer_pseudonym,
                reviewed_at=command.reviewed_at,
                content_sha256=campaign_hash,
                parent_sha256=parent_sha256,
            )
            await self.repository.add(campaign)
            for priority_row in priority_rows:
                priority_row.campaign_version_id = campaign_id
                await self.repository.add(priority_row)
            for signal_row in signal_rows:
                await self.repository.add(signal_row)
            for gap_row in gap_rows:
                await self.repository.add(gap_row)
            for dashboard_row in dashboard_rows:
                dashboard_row.campaign_version_id = campaign_id
                await self.repository.add(dashboard_row)
            return campaign

    async def reconstruct_backfill_campaign(
        self,
        version_id: str,
    ) -> dict[str, object]:
        campaign = await self.repository.get_backfill_campaign_version(
            _required_text(version_id, "version_id")
        )
        if campaign is None:
            raise BackfillConflictError(
                "BACKFILL_CAMPAIGN_NOT_FOUND",
                f"B8 campaign version not found: {version_id}.",
            )
        if (
            campaign.priority_policy_version != "b8-priority-v1"
            or campaign.priority_policy_json != BACKFILL_PRIORITY_POLICY
            or campaign.priority_policy_sha256 != backfill_policy_hash()
        ):
            raise BackfillConflictError(
                "BACKFILL_POLICY_DRIFT",
                "The persisted B8 priority policy does not match code.",
            )
        parent = None
        if campaign.parent_version_id is not None:
            parent = await self.repository.get_backfill_campaign_version(
                campaign.parent_version_id
            )
            if (
                parent is None
                or parent.content_sha256 != campaign.parent_sha256
                or parent.version_number + 1 != campaign.version_number
                or parent.campaign_key != campaign.campaign_key
            ):
                raise BackfillConflictError(
                    "BACKFILL_PARENT_HASH_MISMATCH",
                    "The persisted B8 parent chain does not reconstruct.",
                )

        priorities = await self.repository.backfill_material_priorities(
            campaign.id
        )
        bundles: list[_ResolvedBackfillBundle] = []
        stored_by_material = {row.material_id: row for row in priorities}
        reconstructed_signals: dict[
            str,
            list[dict[str, object]],
        ] = {}
        for priority in priorities:
            material = await self.repository.get_material(
                priority.material_id
            )
            if material is None:
                raise BackfillConflictError(
                    "BACKFILL_MATERIAL_NOT_FOUND",
                    "A persisted B8 material no longer resolves.",
                )
            stored_signals = (
                await self.repository.backfill_priority_signals(priority.id)
            )
            signals: list[_ResolvedBackfillSignal] = []
            signal_payloads: list[dict[str, object]] = []
            for stored_signal in stored_signals:
                source_id = _signal_source_id(stored_signal)
                signal_command = BackfillSignalCommand(
                    signal_type=stored_signal.signal_type,
                    source_id=source_id,
                    operational_status=stored_signal.applicability_json.get(
                        "operational_status"
                    ),
                    normalized_sensitivity=(
                        stored_signal.signal_value_json.get(
                            "normalized_sensitivity"
                        )
                        if stored_signal.signal_type == "MODEL_SENSITIVITY"
                        else None
                    ),
                )
                signal_resolved = await self._resolve_backfill_signal(
                    material_id=priority.material_id,
                    command=signal_command,
                    as_of_utc=campaign.as_of_utc,
                    reviewer_pseudonym=campaign.reviewer_pseudonym,
                    reviewed_at=campaign.reviewed_at,
                )
                payload = _signal_row_payload(
                    campaign_key=campaign.campaign_key,
                    version_number=campaign.version_number,
                    material_id=priority.material_id,
                    position=stored_signal.position,
                    signal=signal_resolved,
                )
                if (
                    stored_signal.evidence_class
                    != signal_resolved.evidence_class
                    or stored_signal.signal_value_json
                    != dict(signal_resolved.signal_value)
                    or stored_signal.applicability_json
                    != dict(signal_resolved.applicability)
                    or stored_signal.limitations_json
                    != list(signal_resolved.limitations)
                    or stored_signal.upstream_content_sha256
                    != signal_resolved.upstream_content_sha256
                    or stored_signal.content_sha256 != _sha(payload)
                    or any(
                        getattr(stored_signal, key)
                        != signal_resolved.foreign_keys[key]
                        for key in _SIGNAL_FOREIGN_KEYS
                    )
                ):
                    raise BackfillConflictError(
                        "BACKFILL_SIGNAL_HASH_MISMATCH",
                        "A persisted B8 signal does not reconstruct.",
                    )
                signals.append(signal_resolved)
                signal_payloads.append(
                    {
                        **payload,
                        "content_sha256": stored_signal.content_sha256,
                    }
                )
            reconstructed_signals[priority.material_id] = signal_payloads

            stored_gaps = await self.repository.backfill_gap_items(
                priority.id
            )
            gaps: list[_ResolvedBackfillGap] = []
            for stored_gap in stored_gaps:
                gap_command = BackfillGapCommand(
                    requirement_type=stored_gap.requirement_type,
                    state=stored_gap.state,
                    evidence_class=stored_gap.evidence_class,
                    claim_authority_version_id=(
                        stored_gap.claim_authority_version_id
                    ),
                    applicability_scope=(
                        stored_gap.applicability_scope_json
                    ),
                    conflicts=tuple(stored_gap.conflicts_json),
                    missing_requirements=tuple(
                        stored_gap.missing_requirements_json
                    ),
                )
                gap_resolved = await self._resolve_backfill_gap(
                    material_id=priority.material_id,
                    command=gap_command,
                )
                payload = _gap_row_payload(
                    campaign_key=campaign.campaign_key,
                    version_number=campaign.version_number,
                    material_id=priority.material_id,
                    position=stored_gap.position,
                    gap=gap_resolved,
                )
                if (
                    stored_gap.applicability_scope_sha256
                    != gap_resolved.applicability_scope_sha256
                    or stored_gap.source_references_json
                    != [
                        dict(reference)
                        for reference in gap_resolved.source_references
                    ]
                    or stored_gap.upstream_content_sha256
                    != gap_resolved.upstream_content_sha256
                    or stored_gap.conflict_count
                    != len(gap_resolved.command.conflicts)
                    or stored_gap.missing_requirement_count
                    != len(gap_resolved.command.missing_requirements)
                    or stored_gap.content_sha256 != _sha(payload)
                ):
                    raise BackfillConflictError(
                        "BACKFILL_GAP_HASH_MISMATCH",
                        "A persisted B8 gap does not reconstruct.",
                    )
                gaps.append(gap_resolved)
            family_value = priority.signal_vector_json.get(
                "chemical_family"
            )
            family = str(family_value) if family_value is not None else None
            vector = _signal_vector(signals)
            evidence_class = _material_evidence_class(gaps)
            bundles.append(
                _ResolvedBackfillBundle(
                    command=BackfillMaterialCommand(
                        material_id=priority.material_id,
                        chemical_family=family,
                        signals=tuple(signal.command for signal in signals),
                        gaps=tuple(gap.command for gap in gaps),
                    ),
                    canonical_name=material.canonical_name,
                    signals=tuple(signals),
                    gaps=tuple(gaps),
                    projection=ResolvedBackfillMaterial(
                        material_id=priority.material_id,
                        canonical_name=material.canonical_name,
                        chemical_family=family,
                        evidence_class=evidence_class,
                        signal_vector=vector,
                        gaps=tuple(gap.projection for gap in gaps),
                    ),
                )
            )

        ranked = rank_backfill_materials(
            [bundle.projection for bundle in bundles]
        )
        bundle_by_material = {
            bundle.command.material_id: bundle for bundle in bundles
        }
        priority_hashes: list[str] = []
        for ranked_material in ranked:
            stored = stored_by_material.get(ranked_material.material_id)
            if stored is None:
                raise BackfillConflictError(
                    "BACKFILL_PRIORITY_MISSING",
                    "A reconstructed B8 priority row is missing.",
                )
            bundle = bundle_by_material[ranked_material.material_id]
            vector_json = _signal_vector_json(
                ranked_material.signal_vector,
                chemical_family=ranked_material.chemical_family,
                evidence_class=ranked_material.evidence_class,
            )
            source_references = _priority_source_references(bundle)
            payload = _priority_row_payload(
                campaign_key=campaign.campaign_key,
                version_number=campaign.version_number,
                ranked=ranked_material,
                signal_vector_json=vector_json,
                source_references=source_references,
            )
            expected_hash = _sha(payload)
            priority_hashes.append(expected_hash)
            if (
                stored.rank != ranked_material.rank
                or stored.primary_priority_class
                != ranked_material.primary_priority_class
                or stored.signal_vector_json != vector_json
                or stored.rank_key_json != list(ranked_material.rank_key)
                or stored.rank_key_sha256
                != ranked_material.rank_key_sha256
                or stored.critical_unresolved_gap_count
                != ranked_material.critical_unresolved_gap_count
                or stored.total_unresolved_gap_count
                != ranked_material.total_unresolved_gap_count
                or stored.source_references_json != source_references
                or stored.content_sha256 != expected_hash
            ):
                raise BackfillConflictError(
                    "BACKFILL_PRIORITY_HASH_MISMATCH",
                    "A persisted B8 priority does not reconstruct.",
                )

        dashboard = build_backfill_dashboard(ranked)
        stored_dashboard = await self.repository.backfill_dashboard_cells(
            campaign.id
        )
        dashboard_by_key = {
            (row.dimension, row.dimension_key): row
            for row in stored_dashboard
        }
        dashboard_hashes: list[str] = []
        for cell in dashboard:
            stored = dashboard_by_key.get(
                (cell.dimension, cell.dimension_key)
            )
            payload = _dashboard_row_payload(
                campaign_key=campaign.campaign_key,
                version_number=campaign.version_number,
                cell=cell,
            )
            expected_hash = _sha(payload)
            dashboard_hashes.append(expected_hash)
            expected_values = (
                cell.material_count,
                cell.requirements_total,
                cell.accepted_exact_count,
                cell.accepted_scoped_count,
                cell.weak_count,
                cell.conflicted_count,
                cell.unknown_count,
                cell.missing_count,
                cell.not_applicable_count,
            )
            if stored is None or (
                (
                    stored.material_count,
                    stored.requirements_total,
                    stored.accepted_exact_count,
                    stored.accepted_scoped_count,
                    stored.weak_count,
                    stored.conflicted_count,
                    stored.unknown_count,
                    stored.missing_count,
                    stored.not_applicable_count,
                )
                != expected_values
                or stored.content_sha256 != expected_hash
            ):
                raise BackfillConflictError(
                    "BACKFILL_DASHBOARD_HASH_MISMATCH",
                    "A persisted B8 dashboard cell does not reconstruct.",
                )
        if len(stored_dashboard) != len(dashboard):
            raise BackfillConflictError(
                "BACKFILL_DASHBOARD_COUNT_MISMATCH",
                "The B8 dashboard contains unexpected cells.",
            )

        all_signal_rows = [
            row
            for priority in priorities
            for row in await self.repository.backfill_priority_signals(
                priority.id
            )
        ]
        all_gap_rows = [
            row
            for priority in priorities
            for row in await self.repository.backfill_gap_items(priority.id)
        ]
        state_counts = _state_counts(
            [
                gap.projection
                for bundle in bundles
                for gap in bundle.gaps
            ]
        )
        counts = {
            "material_count": len(bundles),
            "signal_count": len(all_signal_rows),
            "gap_count": len(all_gap_rows),
            "dashboard_cell_count": len(stored_dashboard),
            "accepted_exact_count": state_counts["ACCEPTED_EXACT"],
            "accepted_scoped_count": state_counts["ACCEPTED_SCOPED"],
            "weak_count": state_counts["WEAK"],
            "conflicted_count": state_counts["CONFLICTED"],
            "unknown_count": state_counts["UNKNOWN"],
            "missing_count": state_counts["MISSING"],
            "not_applicable_count": state_counts["NOT_APPLICABLE"],
        }
        if any(getattr(campaign, key) != value for key, value in counts.items()):
            raise BackfillConflictError(
                "BACKFILL_CAMPAIGN_COUNT_MISMATCH",
                "The B8 campaign counts do not reconcile.",
            )
        input_snapshot_sha256 = _sha(_input_snapshot_payload(bundles))
        if campaign.input_snapshot_sha256 != input_snapshot_sha256:
            raise BackfillConflictError(
                "BACKFILL_INPUT_HASH_MISMATCH",
                "The B8 input snapshot does not reconstruct.",
            )
        signal_hashes = [
            row.content_sha256
            for row in sorted(
                all_signal_rows,
                key=lambda item: (
                    stored_by_material[
                        next(
                            priority.material_id
                            for priority in priorities
                            if priority.id == item.material_priority_id
                        )
                    ].rank,
                    item.position,
                ),
            )
        ]
        gap_hashes = [
            row.content_sha256
            for row in sorted(
                all_gap_rows,
                key=lambda item: (
                    stored_by_material[
                        next(
                            priority.material_id
                            for priority in priorities
                            if priority.id == item.material_priority_id
                        )
                    ].rank,
                    item.position,
                ),
            )
        ]
        child_hashes = {
            "priorities": priority_hashes,
            "signals": signal_hashes,
            "gaps": gap_hashes,
            "dashboard_cells": dashboard_hashes,
        }
        campaign_payload = _campaign_row_payload(
            campaign_key=campaign.campaign_key,
            version_number=campaign.version_number,
            name=campaign.name,
            purpose=campaign.purpose,
            as_of_utc=campaign.as_of_utc,
            priority_policy_sha256=campaign.priority_policy_sha256,
            input_snapshot_sha256=input_snapshot_sha256,
            counts=counts,
            reviewer_pseudonym=campaign.reviewer_pseudonym,
            reviewed_at=campaign.reviewed_at,
            parent_sha256=campaign.parent_sha256,
            child_hashes=child_hashes,
        )
        if campaign.content_sha256 != _sha(campaign_payload):
            raise BackfillConflictError(
                "BACKFILL_CAMPAIGN_HASH_MISMATCH",
                "The persisted B8 campaign does not reconstruct.",
            )
        return {
            **campaign_payload,
            "version_id": campaign.id,
            "content_sha256": campaign.content_sha256,
            "materials": [
                {
                    "material_id": ranked_material.material_id,
                    "canonical_name": ranked_material.canonical_name,
                    "rank": ranked_material.rank,
                    "primary_priority_class": (
                        ranked_material.primary_priority_class
                    ),
                    "signals": reconstructed_signals[
                        ranked_material.material_id
                    ],
                    "gaps": [
                        {
                            "requirement_type": gap.command.requirement_type,
                            "state": gap.command.state,
                            "evidence_class": (
                                gap.command.evidence_class
                            ),
                            "content_sha256": next(
                                row.content_sha256
                                for row in all_gap_rows
                                if (
                                    row.material_priority_id
                                    == stored_by_material[
                                        ranked_material.material_id
                                    ].id
                                    and row.requirement_type
                                    == gap.command.requirement_type
                                )
                            ),
                        }
                        for gap in bundle_by_material[
                            ranked_material.material_id
                        ].gaps
                    ],
                }
                for ranked_material in ranked
            ],
            "dashboard_cells": [
                {
                    **_dashboard_row_payload(
                        campaign_key=campaign.campaign_key,
                        version_number=campaign.version_number,
                        cell=cell,
                    ),
                    "content_sha256": dashboard_by_key[
                        (cell.dimension, cell.dimension_key)
                    ].content_sha256,
                }
                for cell in dashboard
            ],
            "integrity_verified": True,
        }


__all__ = [
    "BACKFILL_PRIORITY_DIMENSIONS",
    "BACKFILL_PRIORITY_POLICY",
    "BackfillConflictError",
    "BackfillDashboardProjection",
    "BackfillGapProjection",
    "BackfillGapCommand",
    "BackfillMaterialCommand",
    "BackfillSignalCommand",
    "BackfillSignalVector",
    "CreateBackfillCampaignCommand",
    "LabBackfillServiceMixin",
    "RankedBackfillMaterial",
    "ResolvedBackfillMaterial",
    "backfill_policy_hash",
    "build_backfill_dashboard",
    "rank_backfill_materials",
]
