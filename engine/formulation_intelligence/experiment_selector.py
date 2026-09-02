"""Minimum-information, design-only experiment protocol selection.

The selector maps one decision-relevant unknown to the smallest protocol family
that can address it.  It does not optimize a scalar utility, prepare samples,
allocate assessors, execute a study, interpret observations, or grant sensory,
safety, physical, or release authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, TypeVar

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
    _canonical_json_bytes,
    _CanonicalRecord,
    _normalized_identifier,
    _normalized_text,
    _payload,
    _sha256_digest,
)

_RecordT = TypeVar("_RecordT", bound=_CanonicalRecord)


def _optional_text(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalized_text(value, field_name)


def _optional_identifier(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalized_identifier(value, field_name)


def _positive_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None")
    if value < 1:
        raise ValueError(f"{field_name} must be positive")
    return value


def _nonnegative_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or None")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _ordered_values(
    values: Iterable[str],
    field_name: str,
    *,
    identifiers: bool,
) -> tuple[str, ...]:
    normalizer = _normalized_identifier if identifiers else _normalized_text
    normalized = tuple(normalizer(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _records(
    values: Iterable[_RecordT],
    *,
    record_type: type[_RecordT],
    field_name: str,
    id_attribute: str,
) -> tuple[_RecordT, ...]:
    by_id: dict[str, _RecordT] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = getattr(value, id_attribute)
        if identifier in by_id:
            raise ValueError(f"{field_name} must contain unique {id_attribute} values")
        by_id[identifier] = value
    return tuple(by_id[key] for key in sorted(by_id))


def _nested_payload(
    payload: Mapping[str, Any],
    record_type: type[_RecordT],
) -> Mapping[str, Any]:
    """Restore the schema tag omitted by nested canonical serialization."""

    if "schema_version" in payload:
        return payload
    return {"schema_version": record_type.SCHEMA_VERSION, **payload}


class DecisionNeed(str, Enum):
    """The single unknown whose resolution matters to the current decision."""

    NO_UNRESOLVED_DECISION = "no_unresolved_decision"
    CANDIDATE_DIFFERENCE = "candidate_difference"
    COMPONENT_NECESSITY = "component_necessity"
    RECONSTRUCTION_SUFFICIENCY = "reconstruction_sufficiency"
    RATIO_OR_LOAD = "ratio_or_load"
    TIME_LOCAL_EFFECT = "time_local_effect"
    PREPARATION_REPRODUCIBILITY = "preparation_reproducibility"
    ASSESSOR_HETEROGENEITY = "assessor_heterogeneity"


class ProtocolKind(str, Enum):
    ZERO_INTERVENTION = "zero_intervention"
    CARRIER_MATCHED_AB = "carrier_matched_ab"
    COMPLETE_OMISSION = "complete_omission"
    FULL_RECOMBINATION = "full_recombination"
    RATIO_LOAD_SWEEP = "ratio_load_sweep"
    TEMPORAL_OBSERVATION = "temporal_observation"
    INDEPENDENT_PREPARATION = "independent_preparation"
    ASSESSOR_REPLICATION = "assessor_replication"


class ProtocolReadiness(str, Enum):
    NO_EXPERIMENT_REQUIRED = "no_experiment_required"
    PROTOCOL_DESIGN_COMPLETE = "protocol_design_complete"
    HOLD_MISSING_BINDINGS = "hold_missing_bindings"


class SequenceMethod(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    AB_BA = "ab_ba"
    WILLIAMS_FIRST_ORDER_BALANCED = "williams_first_order_balanced"


class MissingOutcome(str, Enum):
    MISSING = "missing"
    PROTOCOL_ABORT = "protocol_abort"
    CANNOT_JUDGE = "cannot_judge"
    NO_PERCEPTIBLE_DIFFERENCE = "no_perceptible_difference"


class MissingnessRule(str, Enum):
    PRESERVE_NO_IMPUTATION = "preserve_no_imputation"


class LineageSourceKind(str, Enum):
    """Upstream versioned artifacts whose bytes and scopes are bound by hash."""

    PLANE_SYNTHESIS = "plane_synthesis"
    CANDIDATE_ASSEMBLY = "candidate_assembly"
    INVENTORY_PROJECTION = "inventory_projection"


class DecisionSourceKind(str, Enum):
    """Decision-relevant source record kinds; selection never resolves them."""

    UNKNOWN_FACT = "unknown_fact"
    CONFLICT = "conflict"
    PRIOR_EXPERIMENT = "prior_experiment"


class DesignRecordKind(str, Enum):
    CANDIDATE = "candidate"
    COMPONENT = "component"


class SourceReadiness(str, Enum):
    CLEAR = "clear"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class LineageSourceRef(_CanonicalRecord):
    """Hash-only reference to one exact upstream artifact and its native scopes."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_lineage_source_ref_v1"

    source_kind: LineageSourceKind
    source_id: str
    artifact_sha256: str
    scopes: tuple[AssessmentScope, ...]
    readiness: SourceReadiness

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", LineageSourceKind(self.source_kind))
        object.__setattr__(
            self,
            "source_id",
            _normalized_identifier(self.source_id, "source_id"),
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _sha256_digest(self.artifact_sha256, "artifact_sha256"),
        )
        scopes = tuple(self.scopes)
        if any(not isinstance(scope, AssessmentScope) for scope in scopes):
            raise TypeError("scopes must contain AssessmentScope values")
        by_key = {scope.key: scope for scope in scopes}
        if len(by_key) != len(scopes):
            raise ValueError("scopes must contain unique exact scopes")
        if not by_key:
            raise ValueError("scopes must not be empty")
        object.__setattr__(self, "scopes", tuple(by_key[key] for key in sorted(by_key)))
        object.__setattr__(self, "readiness", SourceReadiness(self.readiness))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LineageSourceRef:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            source_kind=LineageSourceKind(data["source_kind"]),
            source_id=data["source_id"],
            artifact_sha256=data["artifact_sha256"],
            scopes=tuple(AssessmentScope.from_dict(item) for item in data["scopes"]),
            readiness=SourceReadiness(data["readiness"]),
        )


@dataclass(frozen=True, slots=True)
class DecisionSourceRef(_CanonicalRecord):
    """Exact unresolved fact, conflict, or prior-experiment record under test."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_decision_source_ref_v1"

    source_kind: DecisionSourceKind
    source_id: str
    record_sha256: str
    scope: AssessmentScope

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind", DecisionSourceKind(self.source_kind))
        object.__setattr__(
            self,
            "source_id",
            _normalized_identifier(self.source_id, "source_id"),
        )
        object.__setattr__(
            self,
            "record_sha256",
            _sha256_digest(self.record_sha256, "record_sha256"),
        )
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DecisionSourceRef:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            source_kind=DecisionSourceKind(data["source_kind"]),
            source_id=data["source_id"],
            record_sha256=data["record_sha256"],
            scope=AssessmentScope.from_dict(data["scope"]),
        )


@dataclass(frozen=True, slots=True)
class DesignVersionRecord(_CanonicalRecord):
    """Content-addressed candidate/component identity from one design version."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_design_version_record_v1"

    record_id: str
    record_kind: DesignRecordKind
    design_version_id: str
    record_sha256: str
    semantic_target_id: str
    scope: AssessmentScope

    def __post_init__(self) -> None:
        for field_name in ("record_id", "design_version_id", "semantic_target_id"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "record_kind", DesignRecordKind(self.record_kind))
        object.__setattr__(
            self,
            "record_sha256",
            _sha256_digest(self.record_sha256, "record_sha256"),
        )
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DesignVersionRecord:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            record_id=data["record_id"],
            record_kind=DesignRecordKind(data["record_kind"]),
            design_version_id=data["design_version_id"],
            record_sha256=data["record_sha256"],
            semantic_target_id=data["semantic_target_id"],
            scope=AssessmentScope.from_dict(data["scope"]),
        )


@dataclass(frozen=True, slots=True)
class ProtocolQuestion(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_protocol_question_v2"

    question_id: str
    decision_need: DecisionNeed
    semantic_target_id: str | None = None
    semantic_target_receipt_sha256: str | None = None
    lineage_sources: tuple[LineageSourceRef, ...] = ()
    decision_source_refs: tuple[DecisionSourceRef, ...] = ()
    design_records: tuple[DesignVersionRecord, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    component_ids: tuple[str, ...] = ()
    sweep_levels: tuple[str, ...] = ()
    temporal_windows: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "question_id",
            _normalized_identifier(self.question_id, "question_id"),
        )
        object.__setattr__(self, "decision_need", DecisionNeed(self.decision_need))
        object.__setattr__(
            self,
            "semantic_target_id",
            _optional_identifier(self.semantic_target_id, "semantic_target_id"),
        )
        object.__setattr__(
            self,
            "semantic_target_receipt_sha256",
            (
                _sha256_digest(
                    self.semantic_target_receipt_sha256,
                    "semantic_target_receipt_sha256",
                )
                if self.semantic_target_receipt_sha256 is not None
                else None
            ),
        )
        lineage_by_kind: dict[LineageSourceKind, LineageSourceRef] = {}
        lineage_ids: set[str] = set()
        for source in self.lineage_sources:
            if not isinstance(source, LineageSourceRef):
                raise TypeError("lineage_sources must contain LineageSourceRef values")
            if source.source_kind in lineage_by_kind:
                raise ValueError("lineage_sources must contain one record per source kind")
            if source.source_id in lineage_ids:
                raise ValueError("lineage_sources must contain unique source IDs")
            lineage_by_kind[source.source_kind] = source
            lineage_ids.add(source.source_id)
        object.__setattr__(
            self,
            "lineage_sources",
            tuple(lineage_by_kind[key] for key in sorted(lineage_by_kind, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "decision_source_refs",
            _records(
                self.decision_source_refs,
                record_type=DecisionSourceRef,
                field_name="decision_source_refs",
                id_attribute="source_id",
            ),
        )
        object.__setattr__(
            self,
            "design_records",
            _records(
                self.design_records,
                record_type=DesignVersionRecord,
                field_name="design_records",
                id_attribute="record_id",
            ),
        )
        object.__setattr__(
            self,
            "candidate_ids",
            _ordered_values(self.candidate_ids, "candidate_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "component_ids",
            _ordered_values(self.component_ids, "component_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "sweep_levels",
            _ordered_values(self.sweep_levels, "sweep_levels", identifiers=False),
        )
        object.__setattr__(
            self,
            "temporal_windows",
            _ordered_values(
                self.temporal_windows,
                "temporal_windows",
                identifiers=False,
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProtocolQuestion:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            question_id=data["question_id"],
            decision_need=DecisionNeed(data["decision_need"]),
            semantic_target_id=data["semantic_target_id"],
            semantic_target_receipt_sha256=data["semantic_target_receipt_sha256"],
            lineage_sources=tuple(
                LineageSourceRef.from_dict(_nested_payload(item, LineageSourceRef))
                for item in data["lineage_sources"]
            ),
            decision_source_refs=tuple(
                DecisionSourceRef.from_dict(_nested_payload(item, DecisionSourceRef))
                for item in data["decision_source_refs"]
            ),
            design_records=tuple(
                DesignVersionRecord.from_dict(_nested_payload(item, DesignVersionRecord))
                for item in data["design_records"]
            ),
            candidate_ids=tuple(data["candidate_ids"]),
            component_ids=tuple(data["component_ids"]),
            sweep_levels=tuple(data["sweep_levels"]),
            temporal_windows=tuple(data["temporal_windows"]),
        )


@dataclass(frozen=True, slots=True)
class StoppingCondition(_CanonicalRecord):
    """One native stopping condition; conditions are never aggregated."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_stopping_condition_v1"

    condition_id: str
    criterion_id: str
    rule: str
    minimum_complete_blocks: int
    maximum_complete_blocks: int
    missingness_audit_required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "condition_id",
            _normalized_identifier(self.condition_id, "condition_id"),
        )
        object.__setattr__(
            self,
            "criterion_id",
            _normalized_identifier(self.criterion_id, "criterion_id"),
        )
        object.__setattr__(self, "rule", _normalized_text(self.rule, "rule"))
        minimum = _positive_int(
            self.minimum_complete_blocks,
            "minimum_complete_blocks",
        )
        maximum = _positive_int(
            self.maximum_complete_blocks,
            "maximum_complete_blocks",
        )
        assert minimum is not None and maximum is not None
        if minimum > maximum:
            raise ValueError(
                "minimum_complete_blocks must not exceed maximum_complete_blocks"
            )
        object.__setattr__(self, "minimum_complete_blocks", minimum)
        object.__setattr__(self, "maximum_complete_blocks", maximum)
        if not isinstance(self.missingness_audit_required, bool):
            raise TypeError("missingness_audit_required must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StoppingCondition:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            condition_id=data["condition_id"],
            criterion_id=data["criterion_id"],
            rule=data["rule"],
            minimum_complete_blocks=data["minimum_complete_blocks"],
            maximum_complete_blocks=data["maximum_complete_blocks"],
            missingness_audit_required=data.get(
                "missingness_audit_required",
                True,
            ),
        )


@dataclass(frozen=True, slots=True)
class RealizedOrder(_CanonicalRecord):
    """Observed presentation order kept separate from the planned schedule."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_realized_order_v1"

    block_id: str
    participant_id: str | None
    repeat_index: int
    sample_order: tuple[str, ...]
    predecessor_sample_id: str | None = None
    realized_washout_seconds: int | None = None
    missing_sample_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "block_id",
            _normalized_identifier(self.block_id, "block_id"),
        )
        object.__setattr__(
            self,
            "participant_id",
            _optional_identifier(self.participant_id, "participant_id"),
        )
        repeat_index = _positive_int(self.repeat_index, "repeat_index")
        assert repeat_index is not None
        object.__setattr__(self, "repeat_index", repeat_index)
        order = _ordered_values(self.sample_order, "sample_order", identifiers=True)
        if not order:
            raise ValueError("sample_order must not be empty")
        object.__setattr__(self, "sample_order", order)
        object.__setattr__(
            self,
            "predecessor_sample_id",
            _optional_identifier(
                self.predecessor_sample_id,
                "predecessor_sample_id",
            ),
        )
        object.__setattr__(
            self,
            "realized_washout_seconds",
            _nonnegative_int(
                self.realized_washout_seconds,
                "realized_washout_seconds",
            ),
        )
        missing = _ordered_values(
            self.missing_sample_ids,
            "missing_sample_ids",
            identifiers=True,
        )
        if not set(missing).issubset(order):
            raise ValueError("missing_sample_ids must be present in sample_order")
        object.__setattr__(self, "missing_sample_ids", missing)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RealizedOrder:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            block_id=data["block_id"],
            participant_id=data.get("participant_id"),
            repeat_index=data["repeat_index"],
            sample_order=tuple(data["sample_order"]),
            predecessor_sample_id=data.get("predecessor_sample_id"),
            realized_washout_seconds=data.get("realized_washout_seconds"),
            missing_sample_ids=tuple(data.get("missing_sample_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class ProtocolBindings(_CanonicalRecord):
    """Protocol facts supplied by the study owner; missing values stay missing."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_protocol_bindings_v1"

    total_basis: str | None = None
    carrier_composition: str | None = None
    washout_seconds: int | None = None
    repeat_count: int | None = None
    independent_preparation_count: int | None = None
    assessor_count: int | None = None
    stopping_conditions: tuple[StoppingCondition, ...] = ()
    realized_orders: tuple[RealizedOrder, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "total_basis",
            _optional_text(self.total_basis, "total_basis"),
        )
        object.__setattr__(
            self,
            "carrier_composition",
            _optional_text(self.carrier_composition, "carrier_composition"),
        )
        object.__setattr__(
            self,
            "washout_seconds",
            _positive_int(self.washout_seconds, "washout_seconds"),
        )
        object.__setattr__(
            self,
            "repeat_count",
            _positive_int(self.repeat_count, "repeat_count"),
        )
        object.__setattr__(
            self,
            "independent_preparation_count",
            _positive_int(
                self.independent_preparation_count,
                "independent_preparation_count",
            ),
        )
        object.__setattr__(
            self,
            "assessor_count",
            _positive_int(self.assessor_count, "assessor_count"),
        )
        object.__setattr__(
            self,
            "stopping_conditions",
            _records(
                self.stopping_conditions,
                record_type=StoppingCondition,
                field_name="stopping_conditions",
                id_attribute="condition_id",
            ),
        )
        object.__setattr__(
            self,
            "realized_orders",
            _records(
                self.realized_orders,
                record_type=RealizedOrder,
                field_name="realized_orders",
                id_attribute="block_id",
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProtocolBindings:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            total_basis=data.get("total_basis"),
            carrier_composition=data.get("carrier_composition"),
            washout_seconds=data.get("washout_seconds"),
            repeat_count=data.get("repeat_count"),
            independent_preparation_count=data.get(
                "independent_preparation_count"
            ),
            assessor_count=data.get("assessor_count"),
            stopping_conditions=tuple(
                StoppingCondition.from_dict(_nested_payload(item, StoppingCondition))
                for item in data.get("stopping_conditions", ())
            ),
            realized_orders=tuple(
                RealizedOrder.from_dict(_nested_payload(item, RealizedOrder))
                for item in data.get("realized_orders", ())
            ),
        )


@dataclass(frozen=True, slots=True)
class ProtocolArm(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_protocol_arm_v1"

    arm_id: str
    coded_sample_id: str
    condition_role: str
    source_ids: tuple[str, ...]
    change_description: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "arm_id",
            _normalized_identifier(self.arm_id, "arm_id"),
        )
        object.__setattr__(
            self,
            "coded_sample_id",
            _normalized_identifier(self.coded_sample_id, "coded_sample_id"),
        )
        object.__setattr__(
            self,
            "condition_role",
            _normalized_text(self.condition_role, "condition_role"),
        )
        object.__setattr__(
            self,
            "source_ids",
            _ordered_values(self.source_ids, "source_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "change_description",
            _normalized_text(self.change_description, "change_description"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProtocolArm:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            arm_id=data["arm_id"],
            coded_sample_id=data["coded_sample_id"],
            condition_role=data["condition_role"],
            source_ids=tuple(data["source_ids"]),
            change_description=data["change_description"],
        )


@dataclass(frozen=True, slots=True)
class ControlPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_control_plan_v1"

    constant_total_required: bool
    total_basis: str | None
    carrier_match_required: bool
    carrier_composition: str | None
    carrier_displacement_required: bool
    carrier_displacement_rule: str

    def __post_init__(self) -> None:
        for field_name in (
            "constant_total_required",
            "carrier_match_required",
            "carrier_displacement_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")
        object.__setattr__(
            self,
            "total_basis",
            _optional_text(self.total_basis, "total_basis"),
        )
        object.__setattr__(
            self,
            "carrier_composition",
            _optional_text(self.carrier_composition, "carrier_composition"),
        )
        object.__setattr__(
            self,
            "carrier_displacement_rule",
            _normalized_text(
                self.carrier_displacement_rule,
                "carrier_displacement_rule",
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ControlPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            constant_total_required=data["constant_total_required"],
            total_basis=data.get("total_basis"),
            carrier_match_required=data["carrier_match_required"],
            carrier_composition=data.get("carrier_composition"),
            carrier_displacement_required=data["carrier_displacement_required"],
            carrier_displacement_rule=data["carrier_displacement_rule"],
        )


@dataclass(frozen=True, slots=True)
class BlindingPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_blinding_plan_v1"

    coded_samples_required: bool
    assessor_blinded: bool
    code_key_separation_required: bool
    unblinding_rule: str

    def __post_init__(self) -> None:
        for field_name in (
            "coded_samples_required",
            "assessor_blinded",
            "code_key_separation_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")
        object.__setattr__(
            self,
            "unblinding_rule",
            _normalized_text(self.unblinding_rule, "unblinding_rule"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BlindingPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            coded_samples_required=data["coded_samples_required"],
            assessor_blinded=data["assessor_blinded"],
            code_key_separation_required=data["code_key_separation_required"],
            unblinding_rule=data["unblinding_rule"],
        )


@dataclass(frozen=True, slots=True)
class OrderPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_order_plan_v1"

    method: SequenceMethod
    planned_sequences: tuple[tuple[str, ...], ...]
    realized_orders: tuple[RealizedOrder, ...]
    realized_order_required: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", SequenceMethod(self.method))
        sequences = tuple(
            _ordered_values(sequence, "planned_sequence", identifiers=True)
            for sequence in self.planned_sequences
        )
        object.__setattr__(self, "planned_sequences", sequences)
        object.__setattr__(
            self,
            "realized_orders",
            _records(
                self.realized_orders,
                record_type=RealizedOrder,
                field_name="realized_orders",
                id_attribute="block_id",
            ),
        )
        if not isinstance(self.realized_order_required, bool):
            raise TypeError("realized_order_required must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OrderPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            method=SequenceMethod(data["method"]),
            planned_sequences=tuple(
                tuple(sequence) for sequence in data["planned_sequences"]
            ),
            realized_orders=tuple(
                RealizedOrder.from_dict(_nested_payload(item, RealizedOrder))
                for item in data["realized_orders"]
            ),
            realized_order_required=data["realized_order_required"],
        )


@dataclass(frozen=True, slots=True)
class WashoutPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_washout_plan_v1"

    planned_seconds: int | None
    realized_seconds_required: bool
    adequacy_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "planned_seconds",
            _positive_int(self.planned_seconds, "planned_seconds"),
        )
        if not isinstance(self.realized_seconds_required, bool):
            raise TypeError("realized_seconds_required must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WashoutPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data.get("adequacy_authority", False) is not False:
            raise ValueError("washout plans cannot grant adequacy authority")
        return cls(
            planned_seconds=data.get("planned_seconds"),
            realized_seconds_required=data["realized_seconds_required"],
        )


@dataclass(frozen=True, slots=True)
class RepeatPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_repeat_plan_v1"

    planned_repeat_count: int | None
    independent_preparation_count: int | None
    assessor_count: int | None
    missing_cell_repeats_are_new_records: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "planned_repeat_count",
            "independent_preparation_count",
            "assessor_count",
        ):
            object.__setattr__(
                self,
                field_name,
                _positive_int(getattr(self, field_name), field_name),
            )
        if not isinstance(self.missing_cell_repeats_are_new_records, bool):
            raise TypeError("missing_cell_repeats_are_new_records must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RepeatPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            planned_repeat_count=data.get("planned_repeat_count"),
            independent_preparation_count=data.get(
                "independent_preparation_count"
            ),
            assessor_count=data.get("assessor_count"),
            missing_cell_repeats_are_new_records=data.get(
                "missing_cell_repeats_are_new_records",
                True,
            ),
        )


@dataclass(frozen=True, slots=True)
class MissingnessPlan(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "experiment_missingness_plan_v1"

    rule: MissingnessRule
    distinct_outcomes: tuple[MissingOutcome, ...]
    imputation_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule", MissingnessRule(self.rule))
        outcomes = tuple(MissingOutcome(value) for value in self.distinct_outcomes)
        if len(outcomes) != len(set(outcomes)):
            raise ValueError("distinct_outcomes must contain unique values")
        object.__setattr__(self, "distinct_outcomes", outcomes)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MissingnessPlan:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data.get("imputation_authorized", False) is not False:
            raise ValueError("missingness plans cannot authorize imputation")
        return cls(
            rule=MissingnessRule(data["rule"]),
            distinct_outcomes=tuple(
                MissingOutcome(value) for value in data["distinct_outcomes"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ProtocolBurden(_CanonicalRecord):
    """Separate native burdens; no weighted sum or aggregate rank is defined."""

    SCHEMA_VERSION: ClassVar[str] = "experiment_protocol_burden_v1"

    condition_count: int
    planned_repeat_count: int | None
    independent_preparation_count: int | None
    assessor_count: int | None
    temporal_window_count: int
    intervention_required: bool

    def __post_init__(self) -> None:
        condition_count = _nonnegative_int(self.condition_count, "condition_count")
        temporal_count = _nonnegative_int(
            self.temporal_window_count,
            "temporal_window_count",
        )
        assert condition_count is not None and temporal_count is not None
        object.__setattr__(self, "condition_count", condition_count)
        object.__setattr__(self, "temporal_window_count", temporal_count)
        for field_name in (
            "planned_repeat_count",
            "independent_preparation_count",
            "assessor_count",
        ):
            object.__setattr__(
                self,
                field_name,
                _positive_int(getattr(self, field_name), field_name),
            )
        if not isinstance(self.intervention_required, bool):
            raise TypeError("intervention_required must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProtocolBurden:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            condition_count=data["condition_count"],
            planned_repeat_count=data.get("planned_repeat_count"),
            independent_preparation_count=data.get(
                "independent_preparation_count"
            ),
            assessor_count=data.get("assessor_count"),
            temporal_window_count=data["temporal_window_count"],
            intervention_required=data["intervention_required"],
        )


_AUTHORITY_FIELDS = (
    "formula_generation_authorized",
    "sample_preparation_authorized",
    "physical_execution_authorized",
    "assessor_allocation_authorized",
    "sensory_inference_authority",
    "safety_authority",
    "release_authority",
    "source_unknown_resolved",
    "source_conflict_resolved",
    "source_experiment_observed",
)


@dataclass(frozen=True, slots=True)
class ExperimentProtocol(_CanonicalRecord):
    """A protocol-only result with every downstream authority hard-false."""

    SCHEMA_VERSION: ClassVar[str] = "minimum_information_experiment_protocol_v2"

    protocol_id: str
    question_id: str
    kind: ProtocolKind
    decision_need: DecisionNeed
    semantic_target_id: str | None
    semantic_target_receipt_sha256: str | None
    lineage_sources: tuple[LineageSourceRef, ...]
    decision_source_refs: tuple[DecisionSourceRef, ...]
    design_records: tuple[DesignVersionRecord, ...]
    selection_basis: str
    arms: tuple[ProtocolArm, ...]
    controls: ControlPlan
    blinding: BlindingPlan
    order: OrderPlan
    washout: WashoutPlan
    repeats: RepeatPlan
    missingness: MissingnessPlan
    stopping_conditions: tuple[StoppingCondition, ...]
    temporal_windows: tuple[str, ...]
    burden: ProtocolBurden
    readiness: ProtocolReadiness
    hold_reasons: tuple[str, ...]
    authority_ceiling: AuthorityCeiling = field(
        default=AuthorityCeiling.DESIGN_ONLY,
        init=False,
    )
    formula_generation_authorized: bool = field(default=False, init=False)
    sample_preparation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    assessor_allocation_authorized: bool = field(default=False, init=False)
    sensory_inference_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    source_unknown_resolved: bool = field(default=False, init=False)
    source_conflict_resolved: bool = field(default=False, init=False)
    source_experiment_observed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "protocol_id",
            _normalized_identifier(self.protocol_id, "protocol_id"),
        )
        object.__setattr__(
            self,
            "question_id",
            _normalized_identifier(self.question_id, "question_id"),
        )
        object.__setattr__(self, "kind", ProtocolKind(self.kind))
        object.__setattr__(self, "decision_need", DecisionNeed(self.decision_need))
        object.__setattr__(
            self,
            "semantic_target_id",
            _optional_identifier(self.semantic_target_id, "semantic_target_id"),
        )
        object.__setattr__(
            self,
            "semantic_target_receipt_sha256",
            (
                _sha256_digest(
                    self.semantic_target_receipt_sha256,
                    "semantic_target_receipt_sha256",
                )
                if self.semantic_target_receipt_sha256 is not None
                else None
            ),
        )
        lineage_by_kind: dict[LineageSourceKind, LineageSourceRef] = {}
        for source in self.lineage_sources:
            if not isinstance(source, LineageSourceRef):
                raise TypeError("lineage_sources must contain LineageSourceRef values")
            if source.source_kind in lineage_by_kind:
                raise ValueError("lineage_sources must contain one record per source kind")
            lineage_by_kind[source.source_kind] = source
        object.__setattr__(
            self,
            "lineage_sources",
            tuple(lineage_by_kind[key] for key in sorted(lineage_by_kind, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "decision_source_refs",
            _records(
                self.decision_source_refs,
                record_type=DecisionSourceRef,
                field_name="decision_source_refs",
                id_attribute="source_id",
            ),
        )
        object.__setattr__(
            self,
            "design_records",
            _records(
                self.design_records,
                record_type=DesignVersionRecord,
                field_name="design_records",
                id_attribute="record_id",
            ),
        )
        object.__setattr__(
            self,
            "selection_basis",
            _normalized_text(self.selection_basis, "selection_basis"),
        )
        arms = tuple(self.arms)
        if any(not isinstance(item, ProtocolArm) for item in arms):
            raise TypeError("arms must contain ProtocolArm values")
        if len({item.arm_id for item in arms}) != len(arms):
            raise ValueError("arms must contain unique arm_id values")
        if len({item.coded_sample_id for item in arms}) != len(arms):
            raise ValueError("arms must contain unique coded_sample_id values")
        object.__setattr__(self, "arms", arms)
        for field_name, record_type in (
            ("controls", ControlPlan),
            ("blinding", BlindingPlan),
            ("order", OrderPlan),
            ("washout", WashoutPlan),
            ("repeats", RepeatPlan),
            ("missingness", MissingnessPlan),
            ("burden", ProtocolBurden),
        ):
            if not isinstance(getattr(self, field_name), record_type):
                raise TypeError(f"{field_name} must be {record_type.__name__}")
        object.__setattr__(
            self,
            "stopping_conditions",
            _records(
                self.stopping_conditions,
                record_type=StoppingCondition,
                field_name="stopping_conditions",
                id_attribute="condition_id",
            ),
        )
        object.__setattr__(
            self,
            "temporal_windows",
            _ordered_values(
                self.temporal_windows,
                "temporal_windows",
                identifiers=False,
            ),
        )
        object.__setattr__(self, "readiness", ProtocolReadiness(self.readiness))
        object.__setattr__(
            self,
            "hold_reasons",
            tuple(
                sorted(
                    {
                        _normalized_text(value, "hold_reasons")
                        for value in self.hold_reasons
                    },
                    key=lambda item: (item.casefold(), item),
                )
            ),
        )
        if self.kind is ProtocolKind.ZERO_INTERVENTION:
            if self.readiness is not ProtocolReadiness.NO_EXPERIMENT_REQUIRED:
                raise ValueError(
                    "zero intervention requires no_experiment_required readiness"
                )
            if self.arms:
                raise ValueError("zero intervention cannot define experimental arms")
        if self.burden.condition_count != len(self.arms):
            raise ValueError("burden condition_count must equal the arm count")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ExperimentProtocol:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data.get("authority_ceiling") != AuthorityCeiling.DESIGN_ONLY.value:
            raise ValueError("experiment protocols are design-only")
        for field_name in _AUTHORITY_FIELDS:
            if data.get(field_name, False) is not False:
                raise ValueError(f"{field_name} must remain false")
        return cls(
            protocol_id=data["protocol_id"],
            question_id=data["question_id"],
            kind=ProtocolKind(data["kind"]),
            decision_need=DecisionNeed(data["decision_need"]),
            semantic_target_id=data["semantic_target_id"],
            semantic_target_receipt_sha256=data["semantic_target_receipt_sha256"],
            lineage_sources=tuple(
                LineageSourceRef.from_dict(_nested_payload(item, LineageSourceRef))
                for item in data["lineage_sources"]
            ),
            decision_source_refs=tuple(
                DecisionSourceRef.from_dict(_nested_payload(item, DecisionSourceRef))
                for item in data["decision_source_refs"]
            ),
            design_records=tuple(
                DesignVersionRecord.from_dict(_nested_payload(item, DesignVersionRecord))
                for item in data["design_records"]
            ),
            selection_basis=data["selection_basis"],
            arms=tuple(
                ProtocolArm.from_dict(_nested_payload(item, ProtocolArm))
                for item in data["arms"]
            ),
            controls=ControlPlan.from_dict(
                _nested_payload(data["controls"], ControlPlan)
            ),
            blinding=BlindingPlan.from_dict(
                _nested_payload(data["blinding"], BlindingPlan)
            ),
            order=OrderPlan.from_dict(_nested_payload(data["order"], OrderPlan)),
            washout=WashoutPlan.from_dict(
                _nested_payload(data["washout"], WashoutPlan)
            ),
            repeats=RepeatPlan.from_dict(
                _nested_payload(data["repeats"], RepeatPlan)
            ),
            missingness=MissingnessPlan.from_dict(
                _nested_payload(data["missingness"], MissingnessPlan)
            ),
            stopping_conditions=tuple(
                StoppingCondition.from_dict(_nested_payload(item, StoppingCondition))
                for item in data["stopping_conditions"]
            ),
            temporal_windows=tuple(data["temporal_windows"]),
            burden=ProtocolBurden.from_dict(
                _nested_payload(data["burden"], ProtocolBurden)
            ),
            readiness=ProtocolReadiness(data["readiness"]),
            hold_reasons=tuple(data["hold_reasons"]),
        )


_KIND_BY_NEED = {
    DecisionNeed.NO_UNRESOLVED_DECISION: ProtocolKind.ZERO_INTERVENTION,
    DecisionNeed.CANDIDATE_DIFFERENCE: ProtocolKind.CARRIER_MATCHED_AB,
    DecisionNeed.COMPONENT_NECESSITY: ProtocolKind.COMPLETE_OMISSION,
    DecisionNeed.RECONSTRUCTION_SUFFICIENCY: ProtocolKind.FULL_RECOMBINATION,
    DecisionNeed.RATIO_OR_LOAD: ProtocolKind.RATIO_LOAD_SWEEP,
    DecisionNeed.TIME_LOCAL_EFFECT: ProtocolKind.TEMPORAL_OBSERVATION,
    DecisionNeed.PREPARATION_REPRODUCIBILITY: (
        ProtocolKind.INDEPENDENT_PREPARATION
    ),
    DecisionNeed.ASSESSOR_HETEROGENEITY: ProtocolKind.ASSESSOR_REPLICATION,
}

_SELECTION_BASIS = {
    ProtocolKind.ZERO_INTERVENTION: (
        "No decision-relevant unknown is declared, so adding a comparison would "
        "not resolve a current decision."
    ),
    ProtocolKind.CARRIER_MATCHED_AB: (
        "A two-candidate contrast is the smallest comparison that can test the "
        "declared candidate difference."
    ),
    ProtocolKind.COMPLETE_OMISSION: (
        "A complete-system reference against one complete omission is the "
        "smallest causal contrast for the declared component-necessity question."
    ),
    ProtocolKind.FULL_RECOMBINATION: (
        "A native reference against the full recombination is the smallest "
        "sufficiency comparison for the declared reconstruction question."
    ),
    ProtocolKind.RATIO_LOAD_SWEEP: (
        "At least three ordered levels are required to distinguish a local "
        "ratio or load response from a single pairwise contrast."
    ),
    ProtocolKind.TEMPORAL_OBSERVATION: (
        "Repeated observations of the same coded condition are the smallest "
        "design that can localize the declared effect in time."
    ),
    ProtocolKind.INDEPENDENT_PREPARATION: (
        "Independent preparations are the smallest design that can separate "
        "preparation reproducibility from one-batch behavior."
    ),
    ProtocolKind.ASSESSOR_REPLICATION: (
        "Participant-linked replication is the smallest design that can expose "
        "stable assessor heterogeneity without pooling it away."
    ),
}


def _coded_arm(
    question: ProtocolQuestion,
    kind: ProtocolKind,
    index: int,
    *,
    role: str,
    source_ids: tuple[str, ...],
    change: str,
) -> ProtocolArm:
    digest = sha256(
        _canonical_json_bytes(
            {
                "question_id": question.question_id,
                "kind": kind.value,
                "index": index,
                "role": role,
                "source_ids": source_ids,
                "change": change,
            }
        )
    ).hexdigest()
    return ProtocolArm(
        arm_id=f"arm:{index + 1}",
        coded_sample_id=f"coded-{digest[:12]}",
        condition_role=role,
        source_ids=source_ids,
        change_description=change,
    )


def _arms(
    question: ProtocolQuestion,
    kind: ProtocolKind,
    bindings: ProtocolBindings,
) -> tuple[ProtocolArm, ...]:
    drafts: list[tuple[str, tuple[str, ...], str]] = []
    if kind is ProtocolKind.ZERO_INTERVENTION:
        return ()
    if kind in {
        ProtocolKind.CARRIER_MATCHED_AB,
        ProtocolKind.FULL_RECOMBINATION,
        ProtocolKind.ASSESSOR_REPLICATION,
    }:
        drafts.extend(
            (
                "coded candidate condition",
                (candidate_id,),
                "candidate identity differs; total and carrier remain locked",
            )
            for candidate_id in question.candidate_ids
        )
    elif kind is ProtocolKind.COMPLETE_OMISSION:
        source = question.candidate_ids
        components = ", ".join(question.component_ids) or "unbound component"
        drafts.extend(
            (
                ("complete-system reference", source, "no component omitted"),
                (
                    "complete omission",
                    (*source, *question.component_ids),
                    f"omit the complete declared component set: {components}",
                ),
            )
        )
    elif kind is ProtocolKind.RATIO_LOAD_SWEEP:
        drafts.extend(
            (
                "ordered ratio/load level",
                (*question.candidate_ids, f"level:{level}"),
                f"bind the preregistered level {level}",
            )
            for level in question.sweep_levels
        )
    elif kind is ProtocolKind.TEMPORAL_OBSERVATION:
        drafts.extend(
            (
                "time-resolved coded condition",
                (candidate_id,),
                "condition remains unchanged across declared temporal windows",
            )
            for candidate_id in question.candidate_ids
        )
    elif kind is ProtocolKind.INDEPENDENT_PREPARATION:
        count = bindings.independent_preparation_count or 0
        drafts.extend(
            (
                "independent preparation",
                (*question.candidate_ids, f"preparation:{index + 1}"),
                "preparation is independent while the declared condition is locked",
            )
            for index in range(count)
        )
    return tuple(
        _coded_arm(
            question,
            kind,
            index,
            role=role,
            source_ids=source_ids,
            change=change,
        )
        for index, (role, source_ids, change) in enumerate(drafts)
    )


def _williams_sequences(codes: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    count = len(codes)
    first_indices = tuple(
        0
        if position == 0
        else (position + 1) // 2
        if position % 2
        else count - position // 2
        for position in range(count)
    )
    index_rows = tuple(
        tuple((value + shift) % count for value in first_indices)
        for shift in range(count)
    )
    if count % 2:
        index_rows = index_rows + tuple(tuple(reversed(row)) for row in index_rows)
    return tuple(tuple(codes[index] for index in row) for row in index_rows)


def _order_plan(
    arms: tuple[ProtocolArm, ...],
    kind: ProtocolKind,
    bindings: ProtocolBindings,
) -> OrderPlan:
    codes = tuple(arm.coded_sample_id for arm in arms)
    if len(codes) < 2:
        method = SequenceMethod.NOT_APPLICABLE
        sequences: tuple[tuple[str, ...], ...] = ()
    elif len(codes) == 2:
        method = SequenceMethod.AB_BA
        sequences = (codes, tuple(reversed(codes)))
    else:
        method = SequenceMethod.WILLIAMS_FIRST_ORDER_BALANCED
        sequences = _williams_sequences(codes)
    return OrderPlan(
        method=method,
        planned_sequences=sequences,
        realized_orders=bindings.realized_orders,
        realized_order_required=kind is not ProtocolKind.ZERO_INTERVENTION,
    )


def _lineage_hold_reasons(question: ProtocolQuestion) -> tuple[str, ...]:
    """Return exact lineage failures without interpreting any source artifact."""

    reasons: list[str] = []
    target_id = question.semantic_target_id
    if target_id is None:
        reasons.append("semantic target ID is unbound")
    if question.semantic_target_receipt_sha256 is None:
        reasons.append("semantic target receipt hash is unbound")

    sources = {source.source_kind: source for source in question.lineage_sources}
    if set(sources) != set(LineageSourceKind):
        reasons.append("source lineage is incomplete")
    exact_source_scopes = {
        scope.key
        for source in question.lineage_sources
        for scope in source.scopes
    }
    for source in question.lineage_sources:
        if source.readiness is SourceReadiness.HOLD:
            reasons.append(f"source {source.source_kind.value.replace('_', ' ')} remains HOLD")
        if target_id is not None and any(
            scope.target_scope != target_id for scope in source.scopes
        ):
            reasons.append(
                f"{source.source_kind.value} source scopes do not bind the semantic target"
            )

    if not question.decision_source_refs:
        reasons.append("decision source records are unbound")
    for source_ref in question.decision_source_refs:
        if target_id is not None and source_ref.scope.target_scope != target_id:
            reasons.append(
                f"decision source {source_ref.source_id} does not bind the semantic target"
            )
        if source_ref.scope.key not in exact_source_scopes:
            reasons.append(
                f"decision source {source_ref.source_id} scope is absent from source lineage"
            )

    design_by_id = {record.record_id: record for record in question.design_records}
    expected_records = {
        **{record_id: DesignRecordKind.CANDIDATE for record_id in question.candidate_ids},
        **{record_id: DesignRecordKind.COMPONENT for record_id in question.component_ids},
    }
    if set(design_by_id) != set(expected_records):
        reasons.append("design-version record coverage does not exactly match referenced IDs")
    for record_id, record_kind in expected_records.items():
        record = design_by_id.get(record_id)
        if record is None:
            reasons.append(f"{record_kind.value} {record_id} has no design-version record")
            continue
        if record.record_kind is not record_kind:
            reasons.append(
                f"{record_kind.value} {record_id} has the wrong design record kind"
            )
        if target_id is not None and record.semantic_target_id != target_id:
            reasons.append(
                f"{record_kind.value} {record_id} design record does not bind the semantic target"
            )
        if record.scope.key not in exact_source_scopes:
            reasons.append(
                f"{record_kind.value} {record_id} scope is absent from source lineage"
            )
    return tuple(reasons)


def _hold_reasons(
    question: ProtocolQuestion,
    kind: ProtocolKind,
    bindings: ProtocolBindings,
    arms: tuple[ProtocolArm, ...],
) -> tuple[str, ...]:
    if kind is ProtocolKind.ZERO_INTERVENTION:
        return ()
    reasons = list(_lineage_hold_reasons(question))
    if bindings.total_basis is None:
        reasons.append("total basis is unbound")
    if bindings.carrier_composition is None:
        reasons.append("carrier composition is unbound")
    if bindings.washout_seconds is None:
        reasons.append("washout duration is unbound")
    if bindings.repeat_count is None:
        reasons.append("repeat count is unbound")
    if not bindings.stopping_conditions:
        reasons.append("stopping conditions are unbound")

    candidate_count = len(question.candidate_ids)
    if kind in {
        ProtocolKind.CARRIER_MATCHED_AB,
        ProtocolKind.FULL_RECOMBINATION,
        ProtocolKind.ASSESSOR_REPLICATION,
    } and candidate_count != 2:
        reasons.append("exactly two candidate conditions are required")
    if kind is ProtocolKind.COMPLETE_OMISSION:
        if candidate_count != 1:
            reasons.append("one complete-system candidate is required")
        if not question.component_ids:
            reasons.append("at least one complete omission component is required")
    if kind is ProtocolKind.RATIO_LOAD_SWEEP:
        if candidate_count != 1:
            reasons.append("one candidate system is required for a ratio/load sweep")
        if len(question.sweep_levels) < 3:
            reasons.append("at least three ratio/load levels are required")
    if kind is ProtocolKind.TEMPORAL_OBSERVATION:
        if candidate_count < 1:
            reasons.append("at least one temporal candidate is required")
        if len(question.temporal_windows) < 2:
            reasons.append("at least two temporal windows are required")
    if kind is ProtocolKind.INDEPENDENT_PREPARATION:
        if candidate_count != 1:
            reasons.append("one candidate system is required for preparation replication")
        if (bindings.independent_preparation_count or 0) < 2:
            reasons.append("at least two independent preparations are required")
    if kind is ProtocolKind.ASSESSOR_REPLICATION and (
        bindings.assessor_count or 0
    ) < 2:
        reasons.append("at least two participant-linked assessors are required")

    planned_codes = {arm.coded_sample_id for arm in arms}
    for realized in bindings.realized_orders:
        if set(realized.sample_order) != planned_codes:
            reasons.append(
                f"realized order {realized.block_id} does not contain every planned "
                "coded arm exactly once"
            )
    return tuple(reasons)


def select_experiment(
    question: ProtocolQuestion,
    bindings: ProtocolBindings | None = None,
) -> ExperimentProtocol:
    """Select one protocol family without executing or scoring an experiment."""

    if not isinstance(question, ProtocolQuestion):
        raise TypeError("question must be a ProtocolQuestion")
    supplied = bindings or ProtocolBindings()
    if not isinstance(supplied, ProtocolBindings):
        raise TypeError("bindings must be ProtocolBindings or None")
    kind = _KIND_BY_NEED[question.decision_need]
    arms = _arms(question, kind, supplied)
    hold_reasons = _hold_reasons(question, kind, supplied, arms)
    if kind is ProtocolKind.ZERO_INTERVENTION:
        readiness = ProtocolReadiness.NO_EXPERIMENT_REQUIRED
    elif hold_reasons:
        readiness = ProtocolReadiness.HOLD_MISSING_BINDINGS
    else:
        readiness = ProtocolReadiness.PROTOCOL_DESIGN_COMPLETE

    comparative = kind is not ProtocolKind.ZERO_INTERVENTION
    displacement = kind not in {
        ProtocolKind.ZERO_INTERVENTION,
        ProtocolKind.TEMPORAL_OBSERVATION,
        ProtocolKind.ASSESSOR_REPLICATION,
    }
    controls = ControlPlan(
        constant_total_required=comparative,
        total_basis=supplied.total_basis if comparative else None,
        carrier_match_required=comparative,
        carrier_composition=(
            supplied.carrier_composition if comparative else None
        ),
        carrier_displacement_required=displacement,
        carrier_displacement_rule=(
            "Any removed or varied fraction is paired with the exact declared "
            "carrier displacement; an unresolved carrier keeps the protocol on hold."
            if displacement
            else "No carrier displacement is introduced by this protocol family."
        ),
    )
    blinding = BlindingPlan(
        coded_samples_required=comparative,
        assessor_blinded=comparative,
        code_key_separation_required=comparative,
        unblinding_rule=(
            "Keep the code key separate until realized order, missingness, and every "
            "preregistered stopping condition have been audited."
            if comparative
            else "No sample code key exists because no experiment is proposed."
        ),
    )
    order = _order_plan(arms, kind, supplied)
    washout = WashoutPlan(
        planned_seconds=supplied.washout_seconds if comparative else None,
        realized_seconds_required=comparative,
    )
    repeats = RepeatPlan(
        planned_repeat_count=supplied.repeat_count if comparative else None,
        independent_preparation_count=(
            supplied.independent_preparation_count if comparative else None
        ),
        assessor_count=supplied.assessor_count if comparative else None,
    )
    missingness = MissingnessPlan(
        rule=MissingnessRule.PRESERVE_NO_IMPUTATION,
        distinct_outcomes=tuple(MissingOutcome),
    )
    burden = ProtocolBurden(
        condition_count=len(arms),
        planned_repeat_count=repeats.planned_repeat_count,
        independent_preparation_count=repeats.independent_preparation_count,
        assessor_count=repeats.assessor_count,
        temporal_window_count=len(question.temporal_windows),
        intervention_required=kind
        not in {
            ProtocolKind.ZERO_INTERVENTION,
            ProtocolKind.TEMPORAL_OBSERVATION,
            ProtocolKind.ASSESSOR_REPLICATION,
        },
    )
    protocol_digest = sha256(
        _canonical_json_bytes(
            {
                "question": question.as_dict(),
                "bindings": supplied.as_dict(),
                "kind": kind.value,
            }
        )
    ).hexdigest()
    return ExperimentProtocol(
        protocol_id=f"protocol:{protocol_digest[:24]}",
        question_id=question.question_id,
        kind=kind,
        decision_need=question.decision_need,
        semantic_target_id=question.semantic_target_id,
        semantic_target_receipt_sha256=question.semantic_target_receipt_sha256,
        lineage_sources=question.lineage_sources,
        decision_source_refs=question.decision_source_refs,
        design_records=question.design_records,
        selection_basis=_SELECTION_BASIS[kind],
        arms=arms,
        controls=controls,
        blinding=blinding,
        order=order,
        washout=washout,
        repeats=repeats,
        missingness=missingness,
        stopping_conditions=(
            supplied.stopping_conditions if comparative else ()
        ),
        temporal_windows=question.temporal_windows,
        burden=burden,
        readiness=readiness,
        hold_reasons=hold_reasons,
    )


def protocol_to_plane_assessment(
    protocol: ExperimentProtocol,
    scope: AssessmentScope,
) -> PlaneAssessment:
    """Adapt a selected protocol into one exact-scope EXPERIMENT assessment.

    The adapter preserves content-addressed lineage and unresolved source records.
    It does not execute the protocol, observe an outcome, resolve an upstream
    unknown/conflict, or grant formula, sensory, safety, or release authority.
    """

    if not isinstance(protocol, ExperimentProtocol):
        raise TypeError("protocol must be an ExperimentProtocol")
    if not isinstance(scope, AssessmentScope):
        raise TypeError("scope must be an AssessmentScope")
    target_id = protocol.semantic_target_id
    if target_id is None:
        raise ValueError("protocol semantic target is unbound")
    if scope.target_scope != target_id:
        raise ValueError("assessment scope does not bind the protocol semantic target")
    source_scope_keys = {
        source_scope.key
        for source in protocol.lineage_sources
        for source_scope in source.scopes
    }
    if scope.key not in source_scope_keys:
        raise ValueError("assessment scope is absent from protocol source lineage")
    if any(item.scope != scope for item in protocol.decision_source_refs):
        raise ValueError("decision source records do not share the exact assessment scope")
    if any(item.scope != scope for item in protocol.design_records):
        raise ValueError("design-version records do not share the exact assessment scope")

    protocol_provenance = ProvenanceRef(
        provenance_id=f"experiment-protocol:{protocol.protocol_id}",
        source_ref=f"selected experiment protocol {protocol.protocol_id}",
        evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        independence_key=f"experiment-protocol:{protocol.protocol_id}",
        source_sha256=protocol.content_sha256,
    )
    lineage_provenance = tuple(
        ProvenanceRef(
            provenance_id=(
                f"experiment-lineage:{source.source_kind.value}:{source.source_id}"
            ),
            source_ref=f"{source.source_kind.value} {source.source_id}",
            evidence_class=EvidenceClass.UNKNOWN,
            independence_key=(
                f"experiment-lineage:{source.source_kind.value}:{source.source_id}"
            ),
            source_sha256=source.artifact_sha256,
        )
        for source in protocol.lineage_sources
    )
    decision_provenance = {
        source.source_id: ProvenanceRef(
            provenance_id=(
                f"experiment-decision-source:{source.source_kind.value}:"
                f"{source.source_id}"
            ),
            source_ref=f"{source.source_kind.value} {source.source_id}",
            evidence_class=EvidenceClass.UNKNOWN,
            independence_key=(
                f"experiment-decision-source:{source.source_kind.value}:"
                f"{source.source_id}"
            ),
            source_sha256=source.record_sha256,
        )
        for source in protocol.decision_source_refs
    }

    claim_specs = (
        ("protocol_kind", protocol.kind.value, ClaimKind.HYPOTHESIS),
        ("protocol_readiness", protocol.readiness.value, ClaimKind.HYPOTHESIS),
        ("physical_execution_state", "not_authorized", ClaimKind.PROHIBITION),
        ("source_resolution_state", "unresolved", ClaimKind.PROHIBITION),
        ("source_observation_state", "not_observed", ClaimKind.PROHIBITION),
    )
    claims = tuple(
        ScopedClaim(
            claim_id=f"experiment:{protocol.protocol_id}:{claim_key}",
            claim_key=claim_key,
            claim_value=claim_value,
            claim_kind=claim_kind,
            authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
            provenance_refs=(protocol_provenance,),
        )
        for claim_key, claim_value, claim_kind in claim_specs
    )
    unknowns = tuple(
        UnknownFact(
            unknown_id=source.source_id,
            field_key={
                DecisionSourceKind.UNKNOWN_FACT: "source_unknown",
                DecisionSourceKind.CONFLICT: "source_conflict",
                DecisionSourceKind.PRIOR_EXPERIMENT: "source_experiment_observation",
            }[source.source_kind],
            reason={
                DecisionSourceKind.UNKNOWN_FACT: (
                    "the source unknown remains unresolved by protocol selection"
                ),
                DecisionSourceKind.CONFLICT: (
                    "the source conflict remains unresolved by protocol selection"
                ),
                DecisionSourceKind.PRIOR_EXPERIMENT: (
                    "the prior experiment remains an unobserved source record in this adapter"
                ),
            }[source.source_kind],
            needed_evidence={
                DecisionSourceKind.UNKNOWN_FACT: (
                    "execute the preregistered protocol and record the required observation"
                ),
                DecisionSourceKind.CONFLICT: (
                    "execute a decision-resolving comparison without averaging alternatives"
                ),
                DecisionSourceKind.PRIOR_EXPERIMENT: (
                    "supply the exact realized-order and observation record"
                ),
            }[source.source_kind],
            provenance_refs=(decision_provenance[source.source_id],),
        )
        for source in protocol.decision_source_refs
    )
    freshness_hashes = {
        protocol.content_sha256,
        *(source.artifact_sha256 for source in protocol.lineage_sources),
        *(source.record_sha256 for source in protocol.decision_source_refs),
        *(record.record_sha256 for record in protocol.design_records),
    }
    if protocol.semantic_target_receipt_sha256 is not None:
        freshness_hashes.add(protocol.semantic_target_receipt_sha256)
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "experiment_plane_assessment_identity_v1",
                "protocol_sha256": protocol.content_sha256,
                "scope": scope,
            }
        )
    ).hexdigest()
    return PlaneAssessment(
        assessment_id=f"experiment-assessment:{digest[:24]}",
        module_id="experiment_selector",
        plane_id=PlaneId.EXPERIMENT,
        scope=scope,
        claims=claims,
        support_intervals=(),
        conflicts=(),
        unknowns=unknowns,
        failure_modes=(
            *protocol.hold_reasons,
            "protocol selection does not execute, observe, or resolve source records",
        ),
        proposed_experiments=(protocol.protocol_id,),
        provenance_refs=(protocol_provenance, *lineage_provenance),
        authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
        freshness_hashes=tuple(freshness_hashes),
        native_criteria=(),
    )


__all__ = [
    "BlindingPlan",
    "ControlPlan",
    "DecisionNeed",
    "DecisionSourceKind",
    "DecisionSourceRef",
    "DesignRecordKind",
    "DesignVersionRecord",
    "ExperimentProtocol",
    "LineageSourceKind",
    "LineageSourceRef",
    "MissingOutcome",
    "MissingnessPlan",
    "MissingnessRule",
    "OrderPlan",
    "ProtocolArm",
    "ProtocolBindings",
    "ProtocolBurden",
    "ProtocolKind",
    "ProtocolQuestion",
    "ProtocolReadiness",
    "RealizedOrder",
    "RepeatPlan",
    "SequenceMethod",
    "StoppingCondition",
    "SourceReadiness",
    "WashoutPlan",
    "protocol_to_plane_assessment",
    "select_experiment",
]
