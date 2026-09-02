"""Evidence-bounded structural candidate selection for perfume architecture.

The selector consumes caller-supplied target requirements and material capability
declarations.  It does not discover materials, infer stock, invent quantities, or
construct a formula.  IDEAL and CURRENT-INVENTORY BUILD are separate views: a
stock ambiguity can hold the build view without rewriting target-level fitness.

Pareto membership is computed by set containment over target recognizers and
temporal, spatial, and functional roles plus an explicit authority ceiling.  No
weighted sum, scalar utility, ingredient-count reward, or sensory equivalence is
used.  Coverage alternatives are structural hypotheses only.
"""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, cast

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name, identifier=True)


def _tokens(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name, identifier=True) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _codes(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(
        _text(value, field_name, identifier=True).replace(" ", "_").upper()
        for value in values
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _CanonicalSelectionRecord):
        return value.as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not permit non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _strict_payload(
    payload: Mapping[str, Any],
    record_type: type[_CanonicalSelectionRecord],
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("canonical payload must be a mapping")
    expected = {
        "schema_version",
        *(item.name for item in fields(cast(Any, record_type))),
    }
    received = set(payload)
    if received != expected:
        missing = sorted(expected - received)
        extra = sorted(received - expected)
        raise ValueError(
            f"{record_type.SCHEMA_VERSION} payload does not match the closed schema; "
            f"missing={missing!r}, extra={extra!r}"
        )
    declared = payload["schema_version"]
    if declared != record_type.SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {record_type.SCHEMA_VERSION!r}, "
            f"received {declared!r}"
        )
    return payload


class _CanonicalSelectionRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _to_primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()


class InventoryState(str, Enum):
    """Caller-declared present inventory state; unknown is not false."""

    OWNED = "owned"
    NOT_OWNED = "not_owned"
    UNKNOWN = "unknown"


class SelectionView(str, Enum):
    """Independent target and executable-stock views."""

    IDEAL = "ideal"
    CURRENT_INVENTORY_BUILD = "current_inventory_build"


class CandidateDisposition(str, Enum):
    """Structural decision state; no member authorizes formula execution."""

    FRONTIER = "frontier"
    DOMINATED = "dominated"
    HOLD = "hold"
    EXCLUDED = "excluded"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT_AUTHORITY = "insufficient_authority"
    NO_TARGET_FIT = "no_target_fit"


@dataclass(frozen=True, slots=True)
class CandidateRequirement(_CanonicalSelectionRecord):
    """Exact target-linked feature request used for structural comparison."""

    SCHEMA_VERSION: ClassVar[str] = "candidate_requirement_v1"

    target_id: str
    target_name: str
    required_recognizers: tuple[str, ...]
    exclusions: tuple[str, ...]
    required_temporal_roles: tuple[str, ...]
    required_spatial_roles: tuple[str, ...]
    required_functional_roles: tuple[str, ...]
    minimum_authority: AuthorityCeiling

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _text(self.target_id, "target_id", identifier=True))
        object.__setattr__(self, "target_name", _text(self.target_name, "target_name"))
        for field_name in (
            "required_recognizers",
            "exclusions",
            "required_temporal_roles",
            "required_spatial_roles",
            "required_functional_roles",
        ):
            object.__setattr__(self, field_name, _tokens(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "minimum_authority",
            AuthorityCeiling(self.minimum_authority),
        )
        if not any(
            (
                self.required_recognizers,
                self.required_temporal_roles,
                self.required_spatial_roles,
                self.required_functional_roles,
            )
        ):
            raise ValueError("at least one target-linked capability requirement is required")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateRequirement:
        data = _strict_payload(payload, cls)
        return cls(
            target_id=data["target_id"],
            target_name=data["target_name"],
            required_recognizers=tuple(data["required_recognizers"]),
            exclusions=tuple(data["exclusions"]),
            required_temporal_roles=tuple(data["required_temporal_roles"]),
            required_spatial_roles=tuple(data["required_spatial_roles"]),
            required_functional_roles=tuple(data["required_functional_roles"]),
            minimum_authority=AuthorityCeiling(data["minimum_authority"]),
        )


@dataclass(frozen=True, slots=True)
class MaterialCapabilityDeclaration(_CanonicalSelectionRecord):
    """Caller-supplied identity, capability, evidence, and stock declaration.

    ``execution_ready`` is accepted only as a bounded upstream declaration.  It
    never grants execution here and carries no dose, fraction, carrier, ppm, OAV,
    sensory, safety, or release meaning.
    """

    SCHEMA_VERSION: ClassVar[str] = "material_capability_declaration_v1"

    candidate_id: str
    material_name: str
    exact_identity_ref: str | None
    target_recognizers: tuple[str, ...]
    exclusion_tags: tuple[str, ...]
    temporal_roles: tuple[str, ...]
    spatial_roles: tuple[str, ...]
    functional_roles: tuple[str, ...]
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[str, ...]
    declaration_complete: bool
    missing_data: tuple[str, ...]
    inventory_state: InventoryState
    exact_stock_ref: str | None
    execution_ready: bool | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _text(self.candidate_id, "candidate_id", identifier=True),
        )
        object.__setattr__(self, "material_name", _text(self.material_name, "material_name"))
        object.__setattr__(
            self,
            "exact_identity_ref",
            _optional_identifier(self.exact_identity_ref, "exact_identity_ref"),
        )
        for field_name in (
            "target_recognizers",
            "exclusion_tags",
            "temporal_roles",
            "spatial_roles",
            "functional_roles",
        ):
            object.__setattr__(self, field_name, _tokens(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling(self.authority_ceiling),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _tokens(self.provenance_refs, "provenance_refs", allow_empty=False),
        )
        if not isinstance(self.declaration_complete, bool):
            raise TypeError("declaration_complete must be bool")
        object.__setattr__(self, "missing_data", _tokens(self.missing_data, "missing_data"))
        if self.declaration_complete and self.missing_data:
            raise ValueError("complete declarations cannot list missing_data")
        if not self.declaration_complete and not self.missing_data:
            raise ValueError("incomplete declarations must identify missing_data")
        state = InventoryState(self.inventory_state)
        object.__setattr__(self, "inventory_state", state)
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_identifier(self.exact_stock_ref, "exact_stock_ref"),
        )
        if self.execution_ready is not None and not isinstance(self.execution_ready, bool):
            raise TypeError("execution_ready must be bool or None")
        if state is InventoryState.NOT_OWNED:
            if self.exact_stock_ref is not None or self.execution_ready is True:
                raise ValueError("non-owned inventory cannot claim an exact stock or readiness")
        if state is InventoryState.UNKNOWN and self.execution_ready is True:
            raise ValueError("unknown inventory cannot claim execution readiness")
        if self.execution_ready is True and self.exact_stock_ref is None:
            raise ValueError("execution-ready owned inventory requires exact_stock_ref")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MaterialCapabilityDeclaration:
        data = _strict_payload(payload, cls)
        return cls(
            candidate_id=data["candidate_id"],
            material_name=data["material_name"],
            exact_identity_ref=data["exact_identity_ref"],
            target_recognizers=tuple(data["target_recognizers"]),
            exclusion_tags=tuple(data["exclusion_tags"]),
            temporal_roles=tuple(data["temporal_roles"]),
            spatial_roles=tuple(data["spatial_roles"]),
            functional_roles=tuple(data["functional_roles"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(data["provenance_refs"]),
            declaration_complete=data["declaration_complete"],
            missing_data=tuple(data["missing_data"]),
            inventory_state=InventoryState(data["inventory_state"]),
            exact_stock_ref=data["exact_stock_ref"],
            execution_ready=data["execution_ready"],
        )


@dataclass(frozen=True, slots=True)
class CandidateAssessment(_CanonicalSelectionRecord):
    """One candidate decision in exactly one selection view."""

    SCHEMA_VERSION: ClassVar[str] = "candidate_structural_assessment_v1"

    assessment_id: str
    target_id: str
    view: SelectionView
    candidate_id: str
    material_name: str
    exact_identity_ref: str | None
    inventory_state: InventoryState
    exact_stock_ref: str | None
    execution_ready: bool | None
    authority_ceiling: AuthorityCeiling
    disposition: CandidateDisposition
    matched_recognizers: tuple[str, ...]
    matched_temporal_roles: tuple[str, ...]
    matched_spatial_roles: tuple[str, ...]
    matched_functional_roles: tuple[str, ...]
    exclusion_hits: tuple[str, ...]
    hold_reasons: tuple[str, ...]
    dominated_by: tuple[str, ...]
    omission_alternatives: tuple[str, ...]
    nonredundant_features: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("assessment_id", "target_id", "candidate_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        object.__setattr__(self, "view", SelectionView(self.view))
        object.__setattr__(self, "material_name", _text(self.material_name, "material_name"))
        object.__setattr__(
            self,
            "exact_identity_ref",
            _optional_identifier(self.exact_identity_ref, "exact_identity_ref"),
        )
        object.__setattr__(self, "inventory_state", InventoryState(self.inventory_state))
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_identifier(self.exact_stock_ref, "exact_stock_ref"),
        )
        if self.execution_ready is not None and not isinstance(self.execution_ready, bool):
            raise TypeError("execution_ready must be bool or None")
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling(self.authority_ceiling),
        )
        disposition = CandidateDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        for field_name in (
            "matched_recognizers",
            "matched_temporal_roles",
            "matched_spatial_roles",
            "matched_functional_roles",
            "exclusion_hits",
            "dominated_by",
            "omission_alternatives",
            "nonredundant_features",
        ):
            object.__setattr__(self, field_name, _tokens(getattr(self, field_name), field_name))
        object.__setattr__(self, "hold_reasons", _codes(self.hold_reasons, "hold_reasons"))
        if disposition is CandidateDisposition.FRONTIER:
            if self.hold_reasons or self.exclusion_hits or self.dominated_by:
                raise ValueError("frontier assessments cannot carry blocking fields")
        elif disposition is CandidateDisposition.DOMINATED:
            if not self.dominated_by or self.hold_reasons or self.exclusion_hits:
                raise ValueError("dominated assessments require only dominated_by blockers")
        elif disposition is CandidateDisposition.EXCLUDED:
            if not self.exclusion_hits:
                raise ValueError("excluded assessments require exclusion_hits")
        elif not self.hold_reasons:
            raise ValueError(f"{disposition.value} assessments require hold_reasons")

    @property
    def criterion_features(self) -> tuple[str, ...]:
        values = (
            *(f"recognizer:{value}" for value in self.matched_recognizers),
            *(f"temporal:{value}" for value in self.matched_temporal_roles),
            *(f"spatial:{value}" for value in self.matched_spatial_roles),
            *(f"functional:{value}" for value in self.matched_functional_roles),
        )
        return tuple(sorted(values))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateAssessment:
        data = _strict_payload(payload, cls)
        return cls(
            assessment_id=data["assessment_id"],
            target_id=data["target_id"],
            view=SelectionView(data["view"]),
            candidate_id=data["candidate_id"],
            material_name=data["material_name"],
            exact_identity_ref=data["exact_identity_ref"],
            inventory_state=InventoryState(data["inventory_state"]),
            exact_stock_ref=data["exact_stock_ref"],
            execution_ready=data["execution_ready"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            disposition=CandidateDisposition(data["disposition"]),
            matched_recognizers=tuple(data["matched_recognizers"]),
            matched_temporal_roles=tuple(data["matched_temporal_roles"]),
            matched_spatial_roles=tuple(data["matched_spatial_roles"]),
            matched_functional_roles=tuple(data["matched_functional_roles"]),
            exclusion_hits=tuple(data["exclusion_hits"]),
            hold_reasons=tuple(data["hold_reasons"]),
            dominated_by=tuple(data["dominated_by"]),
            omission_alternatives=tuple(data["omission_alternatives"]),
            nonredundant_features=tuple(data["nonredundant_features"]),
        )


@dataclass(frozen=True, slots=True)
class CandidateSelectionReport(_CanonicalSelectionRecord):
    """Deterministic dual-view structural selection report."""

    SCHEMA_VERSION: ClassVar[str] = "candidate_selection_report_v1"

    report_id: str
    requirement_sha256: str
    declaration_sha256s: tuple[str, ...]
    selection_method: str
    ideal_frontier_ids: tuple[str, ...]
    current_inventory_frontier_ids: tuple[str, ...]
    ideal_assessments: tuple[CandidateAssessment, ...]
    current_inventory_assessments: tuple[CandidateAssessment, ...]
    scalar_utility_used: bool
    structural_alternatives_are_sensory_equivalence: bool
    execution_authorized: bool
    sensory_claims_authorized: bool
    liking_claims_authorized: bool
    safety_claims_authorized: bool
    release_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _text(self.report_id, "report_id", identifier=True))
        object.__setattr__(
            self,
            "requirement_sha256",
            _text(self.requirement_sha256, "requirement_sha256", identifier=True),
        )
        if len(self.requirement_sha256) != 64 or any(
            value not in "0123456789abcdef" for value in self.requirement_sha256
        ):
            raise ValueError("requirement_sha256 must be a lowercase SHA-256 digest")
        object.__setattr__(
            self,
            "declaration_sha256s",
            _tokens(self.declaration_sha256s, "declaration_sha256s"),
        )
        method = _text(self.selection_method, "selection_method", identifier=True)
        if method != "set-containment-pareto-v1":
            raise ValueError("selection_method must be set-containment-pareto-v1")
        object.__setattr__(self, "selection_method", method)
        object.__setattr__(
            self,
            "ideal_frontier_ids",
            _tokens(self.ideal_frontier_ids, "ideal_frontier_ids"),
        )
        object.__setattr__(
            self,
            "current_inventory_frontier_ids",
            _tokens(self.current_inventory_frontier_ids, "current_inventory_frontier_ids"),
        )
        for field_name, expected_view in (
            ("ideal_assessments", SelectionView.IDEAL),
            ("current_inventory_assessments", SelectionView.CURRENT_INVENTORY_BUILD),
        ):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, CandidateAssessment) for item in values):
                raise TypeError(f"{field_name} must contain CandidateAssessment values")
            by_id = {item.candidate_id: item for item in values}
            if len(by_id) != len(values):
                raise ValueError(f"{field_name} must contain unique candidate_id values")
            if any(item.view is not expected_view for item in values):
                raise ValueError(f"{field_name} contains an assessment for the wrong view")
            object.__setattr__(self, field_name, tuple(by_id[key] for key in sorted(by_id)))
        ideal_ids = tuple(
            item.candidate_id
            for item in self.ideal_assessments
            if item.disposition is CandidateDisposition.FRONTIER
        )
        current_ids = tuple(
            item.candidate_id
            for item in self.current_inventory_assessments
            if item.disposition is CandidateDisposition.FRONTIER
        )
        if self.ideal_frontier_ids != ideal_ids:
            raise ValueError("ideal_frontier_ids must exactly match ideal assessments")
        if self.current_inventory_frontier_ids != current_ids:
            raise ValueError(
                "current_inventory_frontier_ids must exactly match current assessments"
            )
        for field_name in (
            "scalar_utility_used",
            "structural_alternatives_are_sensory_equivalence",
            "execution_authorized",
            "sensory_claims_authorized",
            "liking_claims_authorized",
            "safety_claims_authorized",
            "release_authorized",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value:
                raise ValueError(f"{field_name} must remain false in structural selection")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateSelectionReport:
        data = _strict_payload(payload, cls)
        return cls(
            report_id=data["report_id"],
            requirement_sha256=data["requirement_sha256"],
            declaration_sha256s=tuple(data["declaration_sha256s"]),
            selection_method=data["selection_method"],
            ideal_frontier_ids=tuple(data["ideal_frontier_ids"]),
            current_inventory_frontier_ids=tuple(data["current_inventory_frontier_ids"]),
            ideal_assessments=tuple(
                CandidateAssessment.from_dict(item) for item in data["ideal_assessments"]
            ),
            current_inventory_assessments=tuple(
                CandidateAssessment.from_dict(item)
                for item in data["current_inventory_assessments"]
            ),
            scalar_utility_used=data["scalar_utility_used"],
            structural_alternatives_are_sensory_equivalence=data[
                "structural_alternatives_are_sensory_equivalence"
            ],
            execution_authorized=data["execution_authorized"],
            sensory_claims_authorized=data["sensory_claims_authorized"],
            liking_claims_authorized=data["liking_claims_authorized"],
            safety_claims_authorized=data["safety_claims_authorized"],
            release_authorized=data["release_authorized"],
        )


@dataclass(frozen=True, slots=True)
class _DraftAssessment:
    declaration: MaterialCapabilityDeclaration
    view: SelectionView
    disposition: CandidateDisposition
    matched_recognizers: tuple[str, ...]
    matched_temporal_roles: tuple[str, ...]
    matched_spatial_roles: tuple[str, ...]
    matched_functional_roles: tuple[str, ...]
    exclusion_hits: tuple[str, ...]
    hold_reasons: tuple[str, ...]

    @property
    def features(self) -> frozenset[str]:
        return frozenset(
            (
                *(f"recognizer:{value}" for value in self.matched_recognizers),
                *(f"temporal:{value}" for value in self.matched_temporal_roles),
                *(f"spatial:{value}" for value in self.matched_spatial_roles),
                *(f"functional:{value}" for value in self.matched_functional_roles),
            )
        )


def _intersection(required: tuple[str, ...], declared: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(required).intersection(declared)))


def _authority_meets(
    candidate: AuthorityCeiling,
    minimum: AuthorityCeiling,
) -> bool:
    return minimum.is_no_stronger_than(candidate)


def _draft(
    requirement: CandidateRequirement,
    declaration: MaterialCapabilityDeclaration,
    view: SelectionView,
) -> _DraftAssessment:
    matched_recognizers = _intersection(
        requirement.required_recognizers, declaration.target_recognizers
    )
    matched_temporal = _intersection(
        requirement.required_temporal_roles, declaration.temporal_roles
    )
    matched_spatial = _intersection(
        requirement.required_spatial_roles, declaration.spatial_roles
    )
    matched_functional = _intersection(
        requirement.required_functional_roles, declaration.functional_roles
    )
    exclusion_hits = _intersection(requirement.exclusions, declaration.exclusion_tags)

    disposition = CandidateDisposition.FRONTIER
    reasons: tuple[str, ...] = ()
    if exclusion_hits:
        disposition = CandidateDisposition.EXCLUDED
    elif not declaration.declaration_complete:
        disposition = CandidateDisposition.HOLD
        reasons = (
            "DECLARATION_INCOMPLETE",
            *(f"MISSING_DATA:{value}" for value in declaration.missing_data),
        )
    elif declaration.exact_identity_ref is None:
        disposition = CandidateDisposition.HOLD
        reasons = ("EXACT_IDENTITY_UNRESOLVED",)
    elif not _authority_meets(
        declaration.authority_ceiling, requirement.minimum_authority
    ):
        disposition = CandidateDisposition.INSUFFICIENT_AUTHORITY
        reasons = ("AUTHORITY_BELOW_TARGET_MINIMUM",)
    elif not any((matched_recognizers, matched_temporal, matched_spatial, matched_functional)):
        disposition = CandidateDisposition.NO_TARGET_FIT
        reasons = ("NO_TARGET_LINKED_CAPABILITY",)
    elif view is SelectionView.CURRENT_INVENTORY_BUILD:
        if declaration.inventory_state is InventoryState.UNKNOWN:
            disposition = CandidateDisposition.HOLD
            reasons = ("INVENTORY_STATE_UNKNOWN",)
        elif declaration.inventory_state is InventoryState.NOT_OWNED:
            disposition = CandidateDisposition.UNAVAILABLE
            reasons = ("NO_CURRENT_OWNED_STOCK",)
        elif declaration.exact_stock_ref is None:
            disposition = CandidateDisposition.HOLD
            reasons = ("EXACT_STOCK_REF_UNBOUND",)
        elif declaration.execution_ready is None:
            disposition = CandidateDisposition.HOLD
            reasons = ("EXECUTION_READINESS_UNKNOWN",)
        elif declaration.execution_ready is False:
            disposition = CandidateDisposition.HOLD
            reasons = ("EXECUTION_NOT_READY",)

    return _DraftAssessment(
        declaration=declaration,
        view=view,
        disposition=disposition,
        matched_recognizers=matched_recognizers,
        matched_temporal_roles=matched_temporal,
        matched_spatial_roles=matched_spatial,
        matched_functional_roles=matched_functional,
        exclusion_hits=exclusion_hits,
        hold_reasons=reasons,
    )


def _authority_at_least(
    left: AuthorityCeiling,
    right: AuthorityCeiling,
) -> bool:
    """Whether left has at least right's ceiling in the explicit authority meet."""

    return right.is_no_stronger_than(left)


def _dominates(left: _DraftAssessment, right: _DraftAssessment) -> bool:
    features_at_least = left.features.issuperset(right.features)
    authority_at_least = _authority_at_least(
        left.declaration.authority_ceiling,
        right.declaration.authority_ceiling,
    )
    strict = (
        left.features != right.features
        or left.declaration.authority_ceiling is not right.declaration.authority_ceiling
    )
    return features_at_least and authority_at_least and strict


def _assessment_id(
    requirement: CandidateRequirement,
    draft: _DraftAssessment,
) -> str:
    payload = {
        "requirement_sha256": requirement.content_sha256,
        "declaration_sha256": draft.declaration.content_sha256,
        "view": draft.view.value,
    }
    return f"candidate-assessment-{sha256(_canonical_json_bytes(payload)).hexdigest()[:24]}"


def _finalize_view(
    requirement: CandidateRequirement,
    declarations: tuple[MaterialCapabilityDeclaration, ...],
    view: SelectionView,
) -> tuple[CandidateAssessment, ...]:
    drafts = tuple(_draft(requirement, declaration, view) for declaration in declarations)
    eligible = tuple(
        draft for draft in drafts if draft.disposition is CandidateDisposition.FRONTIER
    )
    assessments: list[CandidateAssessment] = []
    for draft in drafts:
        dominated_by: tuple[str, ...] = ()
        alternatives: tuple[str, ...] = ()
        nonredundant: tuple[str, ...] = ()
        disposition = draft.disposition
        if draft in eligible:
            others = tuple(item for item in eligible if item is not draft)
            dominated_by = tuple(
                sorted(
                    item.declaration.candidate_id
                    for item in others
                    if _dominates(item, draft)
                )
            )
            if dominated_by:
                disposition = CandidateDisposition.DOMINATED
            alternatives = tuple(
                sorted(
                    item.declaration.candidate_id
                    for item in others
                    if item.features.issuperset(draft.features)
                    and _authority_at_least(
                        item.declaration.authority_ceiling,
                        draft.declaration.authority_ceiling,
                    )
                )
            )
            covered_elsewhere = frozenset().union(*(item.features for item in others))
            nonredundant = tuple(sorted(draft.features - covered_elsewhere))

        assessments.append(
            CandidateAssessment(
                assessment_id=_assessment_id(requirement, draft),
                target_id=requirement.target_id,
                view=view,
                candidate_id=draft.declaration.candidate_id,
                material_name=draft.declaration.material_name,
                exact_identity_ref=draft.declaration.exact_identity_ref,
                inventory_state=draft.declaration.inventory_state,
                exact_stock_ref=draft.declaration.exact_stock_ref,
                execution_ready=draft.declaration.execution_ready,
                authority_ceiling=draft.declaration.authority_ceiling,
                disposition=disposition,
                matched_recognizers=draft.matched_recognizers,
                matched_temporal_roles=draft.matched_temporal_roles,
                matched_spatial_roles=draft.matched_spatial_roles,
                matched_functional_roles=draft.matched_functional_roles,
                exclusion_hits=draft.exclusion_hits,
                hold_reasons=draft.hold_reasons,
                dominated_by=dominated_by,
                omission_alternatives=alternatives,
                nonredundant_features=nonredundant,
            )
        )
    return tuple(sorted(assessments, key=lambda item: item.candidate_id))


def select_candidates(
    requirement: CandidateRequirement,
    declarations: Iterable[MaterialCapabilityDeclaration],
) -> CandidateSelectionReport:
    """Return deterministic structural Pareto frontiers for ideal and build views.

    This function is deliberately non-generative.  It compares only explicitly
    supplied identities and declared capabilities.  The returned current-build
    frontier means that upstream stock/readiness declarations are bound; it is
    not a physical-compounding, formula, sensory, safety, or release approval.
    """

    if not isinstance(requirement, CandidateRequirement):
        raise TypeError("requirement must be a CandidateRequirement")
    values = tuple(declarations)
    if any(not isinstance(item, MaterialCapabilityDeclaration) for item in values):
        raise TypeError(
            "declarations must contain MaterialCapabilityDeclaration values"
        )
    by_id = {item.candidate_id: item for item in values}
    if len(by_id) != len(values):
        raise ValueError("declarations must contain unique candidate_id values")
    ordered = tuple(by_id[key] for key in sorted(by_id))
    ideal = _finalize_view(requirement, ordered, SelectionView.IDEAL)
    current = _finalize_view(
        requirement,
        ordered,
        SelectionView.CURRENT_INVENTORY_BUILD,
    )
    declaration_hashes = tuple(
        f"{item.candidate_id}={item.content_sha256}" for item in ordered
    )
    identity_payload = {
        "requirement_sha256": requirement.content_sha256,
        "declaration_sha256s": declaration_hashes,
        "selection_method": "set-containment-pareto-v1",
        "ideal_assessments": tuple(item.content_sha256 for item in ideal),
        "current_inventory_assessments": tuple(item.content_sha256 for item in current),
    }
    report_id = (
        "candidate-selection-"
        f"{sha256(_canonical_json_bytes(identity_payload)).hexdigest()[:24]}"
    )
    return CandidateSelectionReport(
        report_id=report_id,
        requirement_sha256=requirement.content_sha256,
        declaration_sha256s=declaration_hashes,
        selection_method="set-containment-pareto-v1",
        ideal_frontier_ids=tuple(
            item.candidate_id
            for item in ideal
            if item.disposition is CandidateDisposition.FRONTIER
        ),
        current_inventory_frontier_ids=tuple(
            item.candidate_id
            for item in current
            if item.disposition is CandidateDisposition.FRONTIER
        ),
        ideal_assessments=ideal,
        current_inventory_assessments=current,
        scalar_utility_used=False,
        structural_alternatives_are_sensory_equivalence=False,
        execution_authorized=False,
        sensory_claims_authorized=False,
        liking_claims_authorized=False,
        safety_claims_authorized=False,
        release_authorized=False,
    )


def _stable_identifier(prefix: str, *parts: str) -> str:
    digest = sha256(_canonical_json_bytes((prefix, *parts))).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _requirement_provenance(
    requirement: CandidateRequirement,
) -> tuple[ProvenanceRef, ...]:
    return (
        ProvenanceRef(
            provenance_id=_stable_identifier(
                "candidate-requirement-provenance",
                requirement.target_id,
                requirement.content_sha256,
            ),
            source_ref=f"CandidateRequirement for {requirement.target_name}",
            evidence_class=EvidenceClass.USER_REPORT,
            independence_key=f"candidate-requirement:{requirement.content_sha256}",
            source_sha256=requirement.content_sha256,
        ),
    )


def _declaration_provenance(
    declaration: MaterialCapabilityDeclaration,
) -> tuple[ProvenanceRef, ...]:
    """Bind raw caller source labels without promoting them to observations."""

    return tuple(
        ProvenanceRef(
            provenance_id=_stable_identifier(
                "candidate-declaration-provenance",
                declaration.candidate_id,
                source_ref,
            ),
            source_ref=source_ref,
            evidence_class=EvidenceClass.USER_REPORT,
            independence_key=f"caller-declared-source:{source_ref}",
            source_sha256=declaration.content_sha256,
        )
        for source_ref in declaration.provenance_refs
    )


def _candidate_status_value(
    assessment: CandidateAssessment,
    *,
    include_inventory: bool,
) -> str:
    parts = [
        f"candidate_id={assessment.candidate_id}",
        f"material_name={assessment.material_name}",
        f"exact_identity_ref={assessment.exact_identity_ref or 'UNKNOWN'}",
    ]
    if include_inventory:
        parts.extend(
            (
                f"inventory_state={assessment.inventory_state.value}",
                f"exact_stock_ref={assessment.exact_stock_ref or 'UNKNOWN'}",
                "execution_ready="
                + (
                    "UNKNOWN"
                    if assessment.execution_ready is None
                    else str(assessment.execution_ready).casefold()
                ),
            )
        )
    parts.append(f"disposition={assessment.disposition.value}")
    return "; ".join(parts)


def selection_to_function_plane_assessment(
    requirement: CandidateRequirement,
    selection_result: CandidateSelectionReport,
    declarations: Iterable[MaterialCapabilityDeclaration],
) -> PlaneAssessment:
    """Adapt an exact candidate result into the structural FUNCTION plane.

    The semantic target remains ``requirement.target_id``.  Current inventory
    facts are represented only in the current-build collection and as unknowns;
    they cannot change any IDEAL disposition.  Declaration provenance is retained
    as caller-reported source lineage and does not become a smell observation.
    """

    if not isinstance(requirement, CandidateRequirement):
        raise TypeError("requirement must be a CandidateRequirement")
    if not isinstance(selection_result, CandidateSelectionReport):
        raise TypeError("selection_result must be a CandidateSelectionReport")
    values = tuple(declarations)
    if any(not isinstance(item, MaterialCapabilityDeclaration) for item in values):
        raise TypeError(
            "declarations must contain MaterialCapabilityDeclaration values"
        )
    expected_result = select_candidates(requirement, values)
    if selection_result != expected_result:
        raise ValueError(
            "selection_result must match the exact requirement and declarations"
        )
    by_id = {item.candidate_id: item for item in values}
    ordered = tuple(by_id[key] for key in sorted(by_id))
    requirement_provenance = _requirement_provenance(requirement)
    provenance_by_candidate = {
        item.candidate_id: _declaration_provenance(item) for item in ordered
    }
    claims: list[ScopedClaim] = []

    def add_claim(
        *,
        claim_key: str,
        claim_value: str,
        claim_kind: ClaimKind,
        member_id: str,
        authority: AuthorityCeiling,
        provenance: tuple[ProvenanceRef, ...],
    ) -> None:
        claims.append(
            ScopedClaim(
                claim_id=_stable_identifier(
                    "candidate-function-claim",
                    claim_key,
                    member_id,
                    claim_value,
                ),
                claim_key=claim_key,
                claim_value=claim_value,
                claim_kind=claim_kind,
                authority_ceiling=authority,
                provenance_refs=provenance,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=member_id,
            )
        )

    for claim_key, claim_kind, values_to_add in (
        (
            "target_recognizer_requirement",
            ClaimKind.REQUIREMENT,
            requirement.required_recognizers,
        ),
        (
            "target_exclusion",
            ClaimKind.PROHIBITION,
            requirement.exclusions,
        ),
        (
            "target_temporal_role_requirement",
            ClaimKind.REQUIREMENT,
            requirement.required_temporal_roles,
        ),
        (
            "target_spatial_role_requirement",
            ClaimKind.REQUIREMENT,
            requirement.required_spatial_roles,
        ),
        (
            "target_functional_role_requirement",
            ClaimKind.REQUIREMENT,
            requirement.required_functional_roles,
        ),
    ):
        for value in values_to_add:
            add_claim(
                claim_key=claim_key,
                claim_value=value,
                claim_kind=claim_kind,
                member_id=_stable_identifier(claim_key, value),
                authority=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance=requirement_provenance,
            )

    ideal_by_id = {
        item.candidate_id: item for item in selection_result.ideal_assessments
    }
    current_by_id = {
        item.candidate_id: item
        for item in selection_result.current_inventory_assessments
    }
    for declaration in ordered:
        candidate_id = declaration.candidate_id
        provenance = provenance_by_candidate[candidate_id]
        ideal = ideal_by_id[candidate_id]
        current = current_by_id[candidate_id]
        add_claim(
            claim_key="ideal_candidate_disposition",
            claim_value=_candidate_status_value(ideal, include_inventory=False),
            claim_kind=ClaimKind.DIAGNOSTIC,
            member_id=candidate_id,
            authority=declaration.authority_ceiling,
            provenance=provenance,
        )
        add_claim(
            claim_key="current_inventory_candidate_disposition",
            claim_value=_candidate_status_value(current, include_inventory=True),
            claim_kind=ClaimKind.DIAGNOSTIC,
            member_id=candidate_id,
            authority=declaration.authority_ceiling,
            provenance=provenance,
        )
        for claim_key, label, features in (
            (
                "candidate_matched_recognizer",
                "recognizer",
                ideal.matched_recognizers,
            ),
            (
                "candidate_matched_temporal_role",
                "temporal_role",
                ideal.matched_temporal_roles,
            ),
            (
                "candidate_matched_spatial_role",
                "spatial_role",
                ideal.matched_spatial_roles,
            ),
            (
                "candidate_matched_functional_role",
                "functional_role",
                ideal.matched_functional_roles,
            ),
        ):
            for feature in features:
                add_claim(
                    claim_key=claim_key,
                    claim_value=f"candidate_id={candidate_id}; {label}={feature}",
                    claim_kind=ClaimKind.HYPOTHESIS,
                    member_id=_stable_identifier(claim_key, candidate_id, feature),
                    authority=declaration.authority_ceiling,
                    provenance=provenance,
                )
        for alternative_id in ideal.omission_alternatives:
            add_claim(
                claim_key="candidate_omission_alternative",
                claim_value=(
                    f"candidate_id={candidate_id}; "
                    f"alternative_candidate_id={alternative_id}; "
                    "structural_coverage_only=true; sensory_equivalence=false"
                ),
                claim_kind=ClaimKind.HYPOTHESIS,
                member_id=_stable_identifier(
                    "candidate-omission-alternative",
                    candidate_id,
                    alternative_id,
                ),
                authority=declaration.authority_ceiling,
                provenance=provenance,
            )
        for feature in ideal.nonredundant_features:
            add_claim(
                claim_key="candidate_nonredundant_feature",
                claim_value=f"candidate_id={candidate_id}; feature={feature}",
                claim_kind=ClaimKind.HYPOTHESIS,
                member_id=_stable_identifier(
                    "candidate-nonredundant-feature", candidate_id, feature
                ),
                authority=declaration.authority_ceiling,
                provenance=provenance,
            )
        for dominator_id in ideal.dominated_by:
            add_claim(
                claim_key="candidate_structural_dominator",
                claim_value=(
                    f"candidate_id={candidate_id}; dominator_candidate_id={dominator_id}"
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                member_id=_stable_identifier(
                    "candidate-structural-dominator", candidate_id, dominator_id
                ),
                authority=declaration.authority_ceiling,
                provenance=provenance,
            )

    unknowns: list[UnknownFact] = []
    for view_name, assessments in (
        ("ideal", selection_result.ideal_assessments),
        (
            "current_inventory_build",
            selection_result.current_inventory_assessments,
        ),
    ):
        for assessment in assessments:
            if assessment.disposition is not CandidateDisposition.HOLD:
                continue
            candidate_provenance = provenance_by_candidate[assessment.candidate_id]
            unknowns.append(
                UnknownFact(
                    unknown_id=_stable_identifier(
                        "candidate-selection-unknown",
                        view_name,
                        assessment.candidate_id,
                    ),
                    field_key=f"{view_name}.{assessment.candidate_id}",
                    reason=", ".join(assessment.hold_reasons),
                    needed_evidence=(
                        "an exact identity and complete capability declaration"
                        if view_name == "ideal"
                        else "an exact current stock reference and execution-readiness declaration"
                    ),
                    provenance_refs=candidate_provenance,
                )
            )
    for field_key, evidence in (
        ("observed_smell", "direct sensory observation at the exact conditions"),
        ("scoped_liking", "participant-linked criterion-specific preference data"),
        ("safety", "current exact-formula safety assessment"),
        ("stability", "current exact-formula stability evidence"),
        ("release", "all required independent release evidence"),
        (
            "physical_compounding_authority",
            "an authorized exact formula and controlled compounding protocol",
        ),
    ):
        unknowns.append(
            UnknownFact(
                unknown_id=_stable_identifier(
                    "candidate-selection-endpoint-unknown",
                    requirement.target_id,
                    field_key,
                ),
                field_key=field_key,
                reason="structural candidate selection does not observe this endpoint",
                needed_evidence=evidence,
                provenance_refs=requirement_provenance,
            )
        )

    claim_authorities = (
        AuthorityCeiling.STRUCTURAL_ONLY,
        *(item.authority_ceiling for item in claims),
    )
    assessment_authority = max(claim_authorities, key=lambda item: item.rank)
    all_provenance = (
        *requirement_provenance,
        *(
            item
            for candidate_provenance in provenance_by_candidate.values()
            for item in candidate_provenance
        ),
    )
    assessment_digest = sha256(
        _canonical_json_bytes(
            {
                "requirement_sha256": requirement.content_sha256,
                "selection_result_sha256": selection_result.content_sha256,
                "declaration_sha256s": tuple(
                    item.content_sha256 for item in ordered
                ),
            }
        )
    ).hexdigest()
    return PlaneAssessment(
        assessment_id=f"candidate-selector-function/{assessment_digest}",
        module_id="candidate-selector-function-adapter-v1",
        plane_id=PlaneId.FUNCTION,
        scope=AssessmentScope(
            target_scope=requirement.target_id,
            temporal_scope="declared-temporal-role-scope",
            matrix_scope="ideal-and-current-inventory-views",
        ),
        claims=tuple(claims),
        support_intervals=(),
        conflicts=(),
        unknowns=tuple(unknowns),
        failure_modes=(
            "inventory state rewrites the semantic ideal",
            "pareto criteria collapse into scalar utility",
            "structural alternative is treated as sensory equivalence",
            "declaration is promoted to observed smell",
            "missing exact identity or stock is guessed",
        ),
        proposed_experiments=tuple(
            f"resolve {item.field_key} with {item.needed_evidence}"
            for item in unknowns
            if item.field_key.startswith(("ideal.", "current_inventory_build."))
        ),
        provenance_refs=all_provenance,
        authority_ceiling=assessment_authority,
        freshness_hashes=(
            requirement.content_sha256,
            selection_result.content_sha256,
            *(item.content_sha256 for item in ordered),
        ),
        native_criteria=(),
    )


__all__ = [
    "CandidateAssessment",
    "CandidateDisposition",
    "CandidateRequirement",
    "CandidateSelectionReport",
    "InventoryState",
    "MaterialCapabilityDeclaration",
    "SelectionView",
    "select_candidates",
    "selection_to_function_plane_assessment",
]
