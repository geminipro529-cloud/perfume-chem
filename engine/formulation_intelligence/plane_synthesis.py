"""Scope-aware, non-voting synthesis for generic plane assessments.

This module is a future adapter boundary, not a runtime integration point.  A
module-specific adapter may eventually implement :class:`PlaneAssessmentAdapter`,
but synthesis itself imports no formula, inventory, Cypress, sensory, optimizer,
or provider code and grants no authority in those domains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    ScopedNativeCriterion,
    ScopedUnknown,
    SupportInterval,
    UnitInterval,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _normalized_text_tuple,
    _payload,
)


@runtime_checkable
class PlaneAssessmentAdapter(Protocol):
    """Read-only future boundary for translating a module into one plane packet."""

    def to_plane_assessment(self) -> PlaneAssessment:
        """Return a structural packet without granting or performing runtime actions."""


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _sorted_unique_records(values: Iterable[_CanonicalRecord]) -> tuple[Any, ...]:
    by_hash = {value.content_sha256: value for value in values}
    return tuple(by_hash[key] for key in sorted(by_hash))


def _sorted_plane_ids(values: Iterable[PlaneId]) -> tuple[PlaneId, ...]:
    return tuple(sorted({PlaneId(value) for value in values}, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class HarmonizedClaimMember(_CanonicalRecord):
    """One source claim with its exact assessment identity and uncombined support."""

    SCHEMA_VERSION = "harmonized_plane_claim_member_v2"

    assessment_id: str
    module_id: str
    plane_id: PlaneId
    scope: AssessmentScope
    claim: ScopedClaim
    support_intervals: tuple[SupportInterval, ...]
    assessment_authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _normalized_identifier(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "module_id",
            _normalized_identifier(self.module_id, "module_id"),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        if not isinstance(self.claim, ScopedClaim):
            raise TypeError("claim must be a ScopedClaim")
        intervals = _sorted_unique_records(self.support_intervals)
        if any(not isinstance(item, SupportInterval) for item in intervals):
            raise TypeError("support_intervals must contain SupportInterval values")
        if any(item.claim_id != self.claim.claim_id for item in intervals):
            raise ValueError("member support intervals must reference the member claim")
        object.__setattr__(self, "support_intervals", intervals)
        authority = AuthorityCeiling(self.assessment_authority_ceiling)
        if not self.claim.authority_ceiling.is_no_stronger_than(authority):
            raise ValueError("member claim exceeds its assessment authority ceiling")
        object.__setattr__(self, "assessment_authority_ceiling", authority)

    @property
    def claim_id(self) -> str:
        return self.claim.claim_id

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HarmonizedClaimMember:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            assessment_id=data["assessment_id"],
            module_id=data["module_id"],
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            claim=ScopedClaim.from_dict(data["claim"]),
            support_intervals=tuple(
                SupportInterval.from_dict(item) for item in data["support_intervals"]
            ),
            assessment_authority_ceiling=AuthorityCeiling(
                data["assessment_authority_ceiling"]
            ),
        )


@dataclass(frozen=True, slots=True)
class HarmonizedClaim(_CanonicalRecord):
    """One exact-scope compatible claim with typed, uncombined support."""

    SCHEMA_VERSION = "harmonized_plane_claim_v2"

    harmonized_id: str
    scope: AssessmentScope
    claim_key: str
    claim_value: str
    claim_kind: ClaimKind
    members: tuple[HarmonizedClaimMember, ...]
    support_intervals: tuple[SupportInterval, ...]
    conservative_support: UnitInterval | None
    source_claim_ids: tuple[str, ...]
    assessment_ids: tuple[str, ...]
    module_ids: tuple[str, ...]
    plane_ids: tuple[PlaneId, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "harmonized_id",
            _normalized_identifier(self.harmonized_id, "harmonized_id"),
        )
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        object.__setattr__(
            self,
            "claim_key",
            _normalized_identifier(self.claim_key, "claim_key"),
        )
        object.__setattr__(
            self,
            "claim_value",
            _normalized_text(self.claim_value, "claim_value"),
        )
        object.__setattr__(self, "claim_kind", ClaimKind(self.claim_kind))

        members_by_identity: dict[tuple[str, str], HarmonizedClaimMember] = {}
        for member in self.members:
            if not isinstance(member, HarmonizedClaimMember):
                raise TypeError("members must contain HarmonizedClaimMember values")
            identity = (member.assessment_id, member.claim_id)
            if identity in members_by_identity:
                raise ValueError("members must preserve unique claim member identity")
            members_by_identity[identity] = member
        members = tuple(
            sorted(
                members_by_identity.values(),
                key=lambda item: (
                    item.assessment_id,
                    item.claim_id,
                    item.content_sha256,
                ),
            )
        )
        if not members:
            raise ValueError("harmonized claims require at least one member")
        if any(member.scope != self.scope for member in members):
            raise ValueError("harmonized members must share the harmonized scope")
        if any(member.claim.claim_key != self.claim_key for member in members):
            raise ValueError("harmonized members must share the harmonized claim key")
        if any(member.claim.claim_kind is not self.claim_kind for member in members):
            raise ValueError("harmonized members must share the harmonized claim kind")
        if any(
            member.claim.slot_key != members[0].claim.slot_key for member in members
        ):
            raise ValueError("harmonized members must share one cardinality slot")
        if any(
            member.claim.claim_value.casefold() != self.claim_value.casefold()
            for member in members
        ):
            raise ValueError("harmonized members must share the harmonized claim value")
        object.__setattr__(self, "members", members)

        intervals = _sorted_unique_records(self.support_intervals)
        if any(not isinstance(item, SupportInterval) for item in intervals):
            raise TypeError("support_intervals must contain SupportInterval values")
        expected_intervals = _sorted_unique_records(
            interval for member in members for interval in member.support_intervals
        )
        if intervals != expected_intervals:
            raise ValueError("support_intervals must be the canonical member support set")
        object.__setattr__(self, "support_intervals", intervals)
        if self.conservative_support is not None:
            raise ValueError(
                "support intervals remain uncombined without a registered typed rule"
            )
        derived_identifiers = {
            "source_claim_ids": tuple(sorted({item.claim_id for item in members})),
            "assessment_ids": tuple(sorted({item.assessment_id for item in members})),
            "module_ids": tuple(sorted({item.module_id for item in members})),
        }
        for field_name, expected_identifiers in derived_identifiers.items():
            declared_identifiers = _normalized_text_tuple(
                getattr(self, field_name),
                field_name,
                allow_empty=False,
                identifiers=True,
            )
            if declared_identifiers != expected_identifiers:
                raise ValueError(f"{field_name} does not match canonical member identity")
            object.__setattr__(self, field_name, declared_identifiers)
        plane_ids = _sorted_plane_ids(self.plane_ids)
        expected_plane_ids = _sorted_plane_ids(item.plane_id for item in members)
        if plane_ids != expected_plane_ids:
            raise ValueError("plane_ids does not match canonical member identity")
        object.__setattr__(self, "plane_ids", plane_ids)
        nested = (item for interval in intervals for item in interval.provenance_refs)
        expected_provenance = _merged_provenance(
            (
                *(item for member in members for item in member.claim.provenance_refs),
                *nested,
            )
        )
        provenance = _merged_provenance(self.provenance_refs)
        if provenance != expected_provenance:
            raise ValueError("provenance_refs must match canonical member provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        authority = AuthorityCeiling(self.authority_ceiling)
        member_ceiling = AuthorityCeiling.minimum(
            (
                *(item.assessment_authority_ceiling for item in members),
                *(item.claim.authority_ceiling for item in members),
            )
        )
        if not authority.is_no_stronger_than(member_ceiling):
            raise ValueError("harmonized authority exceeds its canonical member meet")
        object.__setattr__(self, "authority_ceiling", authority)
        expected_id = _stable_id(
            "harmonized",
            {
                "scope": self.scope.as_dict(),
                "claim_key": self.claim_key,
                "claim_value": self.claim_value.casefold(),
                "claim_kind": self.claim_kind.value,
                "cardinality": members[0].claim.cardinality.value,
                "member_id": members[0].claim.member_id,
                "order_index": members[0].claim.order_index,
            },
        )
        if self.harmonized_id != expected_id:
            raise ValueError("harmonized_id does not match the canonical derived ID")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HarmonizedClaim:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            harmonized_id=data["harmonized_id"],
            scope=AssessmentScope.from_dict(data["scope"]),
            claim_key=data["claim_key"],
            claim_value=data["claim_value"],
            claim_kind=ClaimKind(data["claim_kind"]),
            members=tuple(
                HarmonizedClaimMember.from_dict(item) for item in data["members"]
            ),
            support_intervals=tuple(
                SupportInterval.from_dict(item) for item in data["support_intervals"]
            ),
            conservative_support=(
                UnitInterval.from_dict(data["conservative_support"])
                if data.get("conservative_support") is not None
                else None
            ),
            source_claim_ids=tuple(data["source_claim_ids"]),
            assessment_ids=tuple(data["assessment_ids"]),
            module_ids=tuple(data["module_ids"]),
            plane_ids=tuple(PlaneId(item) for item in data["plane_ids"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )


@dataclass(frozen=True, slots=True)
class SynthesisConflict(_CanonicalRecord):
    """An explicit or derived exact-scope tension; alternatives are never averaged."""

    SCHEMA_VERSION = "plane_synthesis_conflict_v1"

    conflict_id: str
    scope: AssessmentScope
    claim_key: str
    alternatives: tuple[str, ...]
    reason: str
    claim_ids: tuple[str, ...]
    assessment_ids: tuple[str, ...]
    module_ids: tuple[str, ...]
    plane_ids: tuple[PlaneId, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    explicit_conflict_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "conflict_id",
            _normalized_identifier(self.conflict_id, "conflict_id"),
        )
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        object.__setattr__(
            self,
            "claim_key",
            _normalized_identifier(self.claim_key, "claim_key"),
        )
        alternatives = _normalized_text_tuple(
            self.alternatives,
            "alternatives",
            allow_empty=False,
        )
        if len(alternatives) < 2:
            raise ValueError("synthesis conflicts require at least two alternatives")
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))
        for field_name in (
            "claim_ids",
            "assessment_ids",
            "module_ids",
            "explicit_conflict_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text_tuple(
                    getattr(self, field_name),
                    field_name,
                    identifiers=True,
                ),
            )
        object.__setattr__(self, "plane_ids", _sorted_plane_ids(self.plane_ids))
        if not self.plane_ids:
            raise ValueError("plane_ids must not be empty")
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SynthesisConflict:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            conflict_id=data["conflict_id"],
            scope=AssessmentScope.from_dict(data["scope"]),
            claim_key=data["claim_key"],
            alternatives=tuple(data["alternatives"]),
            reason=data["reason"],
            claim_ids=tuple(data["claim_ids"]),
            assessment_ids=tuple(data["assessment_ids"]),
            module_ids=tuple(data["module_ids"]),
            plane_ids=tuple(PlaneId(item) for item in data["plane_ids"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            explicit_conflict_ids=tuple(data.get("explicit_conflict_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class PlaneSynthesisResult(_CanonicalRecord):
    """Deterministic structural receipt retaining planes, criteria, and uncertainty."""

    SCHEMA_VERSION = "plane_synthesis_result_v2"

    assessments: tuple[PlaneAssessment, ...]
    harmonized_claims: tuple[HarmonizedClaim, ...]
    conflicts: tuple[SynthesisConflict, ...]
    unknowns: tuple[ScopedUnknown, ...]
    native_criteria: tuple[ScopedNativeCriterion, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    authority_ceiling: AuthorityCeiling
    vote_counting_used: bool = field(default=False, init=False)
    formula_generation_authorized: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    inventory_mutation_authorized: bool = field(default=False, init=False)
    runtime_integration_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    pass_fail_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    beauty_authority: bool = field(default=False, init=False)
    hedonic_score_authorized: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        assessments = _sorted_unique_records(self.assessments)
        if any(not isinstance(item, PlaneAssessment) for item in assessments):
            raise TypeError("assessments must contain PlaneAssessment values")
        if not assessments:
            raise ValueError("plane synthesis requires at least one assessment")
        assessment_ids: dict[str, PlaneAssessment] = {}
        for assessment in assessments:
            previous = assessment_ids.get(assessment.assessment_id)
            if previous is not None and previous != assessment:
                raise ValueError(
                    f"assessment_id {assessment.assessment_id!r} has conflicting records"
                )
            assessment_ids[assessment.assessment_id] = assessment
        object.__setattr__(self, "assessments", assessments)

        harmonized = _sorted_unique_records(self.harmonized_claims)
        conflicts = _sorted_unique_records(self.conflicts)
        unknowns = _sorted_unique_records(self.unknowns)
        criteria = _sorted_unique_records(self.native_criteria)
        if any(not isinstance(item, HarmonizedClaim) for item in harmonized):
            raise TypeError("harmonized_claims must contain HarmonizedClaim values")
        if any(not isinstance(item, SynthesisConflict) for item in conflicts):
            raise TypeError("conflicts must contain SynthesisConflict values")
        if any(not isinstance(item, ScopedUnknown) for item in unknowns):
            raise TypeError("unknowns must contain ScopedUnknown values")
        if any(not isinstance(item, ScopedNativeCriterion) for item in criteria):
            raise TypeError("native_criteria must contain ScopedNativeCriterion values")
        object.__setattr__(self, "harmonized_claims", harmonized)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "unknowns", unknowns)
        object.__setattr__(self, "native_criteria", criteria)

        authority = AuthorityCeiling(self.authority_ceiling)
        if any(
            not authority.is_no_stronger_than(item.authority_ceiling)
            for item in assessments
        ):
            raise ValueError("synthesis authority exceeds an input assessment ceiling")
        if any(
            not item.authority_ceiling.is_no_stronger_than(authority)
            for item in harmonized
        ):
            raise ValueError("harmonized claim authority exceeds synthesis authority")
        object.__setattr__(self, "authority_ceiling", authority)
        nested_provenance = (
            *(item for assessment in assessments for item in assessment.provenance_refs),
            *(item for claim in harmonized for item in claim.provenance_refs),
            *(item for conflict in conflicts for item in conflict.provenance_refs),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance((*self.provenance_refs, *nested_provenance)),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlaneSynthesisResult:
        data = _payload(payload, cls.SCHEMA_VERSION)
        forbidden_flags = (
            "vote_counting_used",
            "formula_generation_authorized",
            "formula_mutation_authorized",
            "inventory_mutation_authorized",
            "runtime_integration_authorized",
            "physical_execution_authorized",
            "compounding_authorized",
            "purchase_authority",
            "pass_fail_authority",
            "sensory_authority",
            "beauty_authority",
            "hedonic_score_authorized",
            "similarity_authority",
            "performance_authority",
            "safety_authority",
            "stability_authority",
            "release_authority",
        )
        if any(data.get(field_name) is not False for field_name in forbidden_flags):
            raise ValueError("plane synthesis authority flags must all remain false")
        candidate = cls(
            assessments=tuple(
                PlaneAssessment.from_dict(item) for item in data["assessments"]
            ),
            harmonized_claims=tuple(
                HarmonizedClaim.from_dict(item) for item in data["harmonized_claims"]
            ),
            conflicts=tuple(
                SynthesisConflict.from_dict(item) for item in data["conflicts"]
            ),
            unknowns=tuple(ScopedUnknown.from_dict(item) for item in data["unknowns"]),
            native_criteria=tuple(
                ScopedNativeCriterion.from_dict(item)
                for item in data["native_criteria"]
            ),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )
        expected = synthesize_plane_assessments(
            candidate.assessments,
            authority_ceiling=candidate.authority_ceiling,
        )
        if candidate != expected:
            raise ValueError("plane synthesis receipt is not canonical for its assessments")
        return candidate


@dataclass(frozen=True, slots=True)
class _ClaimInput:
    assessment: PlaneAssessment
    claim: ScopedClaim
    intervals: tuple[SupportInterval, ...]


def _canonical_assessments(
    assessments: Iterable[PlaneAssessment],
) -> tuple[PlaneAssessment, ...]:
    by_hash: dict[str, PlaneAssessment] = {}
    by_id: dict[str, PlaneAssessment] = {}
    for assessment in assessments:
        if not isinstance(assessment, PlaneAssessment):
            raise TypeError("assessments must contain PlaneAssessment values")
        previous = by_id.get(assessment.assessment_id)
        if previous is not None and previous != assessment:
            raise ValueError(
                f"assessment_id {assessment.assessment_id!r} has conflicting records"
            )
        by_id[assessment.assessment_id] = assessment
        by_hash[assessment.content_sha256] = assessment
    if not by_hash:
        raise ValueError("plane synthesis requires at least one assessment")
    return tuple(
        sorted(
            by_hash.values(),
            key=lambda item: (
                item.scope.key,
                item.plane_id.value,
                item.module_id,
                item.assessment_id,
                item.content_sha256,
            ),
        )
    )


def _semantic_conflict(
    scope: AssessmentScope,
    claim_key: str,
    inputs: tuple[_ClaimInput, ...],
) -> SynthesisConflict:
    signatures = {
        item.claim.compatibility_key: item.claim for item in inputs
    }
    values = {item.claim.claim_value for item in inputs}
    alternatives = (
        tuple(values)
        if len(values) > 1
        else tuple(
            f"{kind}:{value}" for kind, value in sorted(signatures)
        )
    )
    payload = {
        "scope": scope.as_dict(),
        "claim_key": claim_key,
        "alternatives": sorted(alternatives),
        "claim_ids": sorted(item.claim.claim_id for item in inputs),
    }
    return SynthesisConflict(
        conflict_id=_stable_id("claim-conflict", payload),
        scope=scope,
        claim_key=claim_key,
        alternatives=tuple(alternatives),
        reason=(
            "exact-scope claim alternatives remain incompatible; repetition is not a vote"
        ),
        claim_ids=tuple(sorted({item.claim.claim_id for item in inputs})),
        assessment_ids=tuple(
            sorted({item.assessment.assessment_id for item in inputs})
        ),
        module_ids=tuple(sorted({item.assessment.module_id for item in inputs})),
        plane_ids=tuple(item.assessment.plane_id for item in inputs),
        provenance_refs=_merged_provenance(
            item
            for source in inputs
            for item in source.claim.provenance_refs
        ),
    )


def _harmonized_claim(
    scope: AssessmentScope,
    claim_key: str,
    inputs: tuple[_ClaimInput, ...],
    synthesis_ceiling: AuthorityCeiling,
) -> HarmonizedClaim:
    representative = min(
        (item.claim for item in inputs),
        key=lambda claim: (
            claim.claim_value.casefold(),
            claim.claim_value,
            claim.claim_kind.value,
            claim.claim_id,
        ),
    )
    intervals = _sorted_unique_records(
        interval for item in inputs for interval in item.intervals
    )
    authority = AuthorityCeiling.minimum(
        (
            synthesis_ceiling,
            *(item.assessment.authority_ceiling for item in inputs),
            *(item.claim.authority_ceiling for item in inputs),
        )
    )
    payload = {
        "scope": scope.as_dict(),
        "claim_key": claim_key,
        "claim_value": representative.claim_value.casefold(),
        "claim_kind": representative.claim_kind.value,
        "cardinality": representative.cardinality.value,
        "member_id": representative.member_id,
        "order_index": representative.order_index,
    }
    members = tuple(
        HarmonizedClaimMember(
            assessment_id=item.assessment.assessment_id,
            module_id=item.assessment.module_id,
            plane_id=item.assessment.plane_id,
            scope=item.assessment.scope,
            claim=item.claim,
            support_intervals=item.intervals,
            assessment_authority_ceiling=item.assessment.authority_ceiling,
        )
        for item in inputs
    )
    return HarmonizedClaim(
        harmonized_id=_stable_id("harmonized", payload),
        scope=scope,
        claim_key=claim_key,
        claim_value=representative.claim_value,
        claim_kind=representative.claim_kind,
        members=members,
        support_intervals=intervals,
        conservative_support=None,
        source_claim_ids=tuple(sorted({item.claim.claim_id for item in inputs})),
        assessment_ids=tuple(
            sorted({item.assessment.assessment_id for item in inputs})
        ),
        module_ids=tuple(sorted({item.assessment.module_id for item in inputs})),
        plane_ids=tuple(item.assessment.plane_id for item in inputs),
        provenance_refs=_merged_provenance(
            (
                *(ref for item in inputs for ref in item.claim.provenance_refs),
                *(ref for interval in intervals for ref in interval.provenance_refs),
            )
        ),
        authority_ceiling=authority,
    )


def _explicit_conflicts(
    assessments: tuple[PlaneAssessment, ...],
) -> tuple[SynthesisConflict, ...]:
    result: list[SynthesisConflict] = []
    for assessment in assessments:
        for conflict in assessment.conflicts:
            payload = {
                "assessment_id": assessment.assessment_id,
                "conflict": conflict.as_dict(),
                "scope": assessment.scope.as_dict(),
            }
            result.append(
                SynthesisConflict(
                    conflict_id=_stable_id("explicit-conflict", payload),
                    scope=assessment.scope,
                    claim_key=conflict.claim_key,
                    alternatives=conflict.alternatives,
                    reason=conflict.reason,
                    claim_ids=conflict.claim_ids,
                    assessment_ids=(assessment.assessment_id,),
                    module_ids=(assessment.module_id,),
                    plane_ids=(assessment.plane_id,),
                    provenance_refs=conflict.provenance_refs,
                    explicit_conflict_ids=(conflict.conflict_id,),
                )
            )
    return tuple(result)


def _ordered_collection_conflicts(
    assessments: tuple[PlaneAssessment, ...],
) -> tuple[tuple[SynthesisConflict, ...], frozenset[tuple[tuple[str, str, str], str]]]:
    """Retain ordering contradictions as conflicts instead of parallel facts."""

    grouped: dict[
        tuple[tuple[str, str, str], str],
        list[tuple[PlaneAssessment, ScopedClaim]],
    ] = {}
    scopes: dict[tuple[str, str, str], AssessmentScope] = {}
    for assessment in assessments:
        scopes[assessment.scope.key] = assessment.scope
        for claim in assessment.claims:
            if claim.cardinality is ClaimCardinality.ORDERED_MEMBER:
                grouped.setdefault(
                    (assessment.scope.key, claim.claim_key), []
                ).append((assessment, claim))

    conflicts: list[SynthesisConflict] = []
    conflicted: set[tuple[tuple[str, str, str], str]] = set()
    for collection_key, entries in sorted(grouped.items(), key=lambda item: repr(item[0])):
        member_positions: dict[str, set[int]] = {}
        position_members: dict[int, set[str]] = {}
        for _, claim in entries:
            assert claim.member_id is not None
            assert claim.order_index is not None
            member_positions.setdefault(claim.member_id, set()).add(claim.order_index)
            position_members.setdefault(claim.order_index, set()).add(claim.member_id)
        if not (
            any(len(positions) > 1 for positions in member_positions.values())
            or any(len(members) > 1 for members in position_members.values())
        ):
            continue

        conflicted.add(collection_key)
        scope_key, claim_key = collection_key
        alternatives = tuple(
            sorted(
                {
                    f"{claim.member_id}@{claim.order_index}:{claim.claim_value}"
                    for _, claim in entries
                }
            )
        )
        payload = {
            "scope": scopes[scope_key].as_dict(),
            "claim_key": claim_key,
            "alternatives": alternatives,
            "claim_ids": sorted(claim.claim_id for _, claim in entries),
        }
        conflicts.append(
            SynthesisConflict(
                conflict_id=_stable_id("ordered-collection-conflict", payload),
                scope=scopes[scope_key],
                claim_key=claim_key,
                alternatives=alternatives,
                reason=(
                    "exact-scope ordered collection assigns a member to multiple "
                    "positions or multiple members to one position"
                ),
                claim_ids=tuple(sorted({claim.claim_id for _, claim in entries})),
                assessment_ids=tuple(
                    sorted({assessment.assessment_id for assessment, _ in entries})
                ),
                module_ids=tuple(
                    sorted({assessment.module_id for assessment, _ in entries})
                ),
                plane_ids=tuple(assessment.plane_id for assessment, _ in entries),
                provenance_refs=_merged_provenance(
                    ref
                    for _, claim in entries
                    for ref in claim.provenance_refs
                ),
            )
        )
    return tuple(conflicts), frozenset(conflicted)


def synthesize_plane_assessments(
    assessments: Iterable[PlaneAssessment],
    *,
    authority_ceiling: AuthorityCeiling | None = None,
) -> PlaneSynthesisResult:
    """Harmonize exact-scope claims without voting, averaging, or authority gain.

    Mismatched target, temporal, or matrix scopes form separate groups.  Exact
    duplicates are canonicalized.  Typed support atoms remain uncombined, so
    repeated heuristic agreement cannot raise an evidence bound.
    """

    canonical = _canonical_assessments(assessments)
    requested = (
        AuthorityCeiling(authority_ceiling)
        if authority_ceiling is not None
        else AuthorityCeiling.EVIDENCE_LIMITED
    )
    synthesis_ceiling = AuthorityCeiling.minimum(
        (requested, *(item.authority_ceiling for item in canonical))
    )

    grouped: dict[
        tuple[tuple[str, str, str], tuple[str, str, str, int | None]],
        list[_ClaimInput],
    ] = {}
    for assessment in canonical:
        intervals_by_claim: dict[str, list[SupportInterval]] = {}
        for interval in assessment.support_intervals:
            intervals_by_claim.setdefault(interval.claim_id, []).append(interval)
        for claim in assessment.claims:
            grouped.setdefault((assessment.scope.key, claim.slot_key), []).append(
                _ClaimInput(
                    assessment=assessment,
                    claim=claim,
                    intervals=tuple(intervals_by_claim.get(claim.claim_id, ())),
                )
            )

    harmonized: list[HarmonizedClaim] = []
    ordered_conflicts, conflicted_ordered_collections = (
        _ordered_collection_conflicts(canonical)
    )
    conflicts: list[SynthesisConflict] = [
        *_explicit_conflicts(canonical),
        *ordered_conflicts,
    ]
    scopes = {assessment.scope.key: assessment.scope for assessment in canonical}
    for (scope_key, slot_key), raw_inputs in sorted(
        grouped.items(), key=lambda item: repr(item[0])
    ):
        inputs = tuple(
            sorted(
                raw_inputs,
                key=lambda item: (
                    item.assessment.assessment_id,
                    item.claim.claim_id,
                ),
            )
        )
        scope = scopes[scope_key]
        claim_key = slot_key[0]
        if (
            slot_key[1] == ClaimCardinality.ORDERED_MEMBER.value
            and (scope_key, claim_key) in conflicted_ordered_collections
        ):
            continue
        signatures = {item.claim.compatibility_key for item in inputs}
        if len(signatures) > 1:
            conflicts.append(_semantic_conflict(scope, claim_key, inputs))
            continue
        harmonized.append(
            _harmonized_claim(scope, claim_key, inputs, synthesis_ceiling)
        )

    unknowns = tuple(
        ScopedUnknown(
            assessment_id=assessment.assessment_id,
            module_id=assessment.module_id,
            plane_id=assessment.plane_id,
            scope=assessment.scope,
            unknown=unknown,
        )
        for assessment in canonical
        for unknown in assessment.unknowns
    )
    criteria = tuple(
        ScopedNativeCriterion(
            assessment_id=assessment.assessment_id,
            module_id=assessment.module_id,
            plane_id=assessment.plane_id,
            scope=assessment.scope,
            criterion=criterion,
        )
        for assessment in canonical
        for criterion in assessment.native_criteria
    )
    provenance = _merged_provenance(
        item for assessment in canonical for item in assessment.provenance_refs
    )
    return PlaneSynthesisResult(
        assessments=canonical,
        harmonized_claims=tuple(harmonized),
        conflicts=tuple(conflicts),
        unknowns=unknowns,
        native_criteria=criteria,
        provenance_refs=provenance,
        authority_ceiling=synthesis_ceiling,
    )


# A compact alias supports later call sites without widening this module's scope.
synthesize_planes = synthesize_plane_assessments


__all__ = [
    "HarmonizedClaim",
    "HarmonizedClaimMember",
    "PlaneAssessmentAdapter",
    "PlaneSynthesisResult",
    "SynthesisConflict",
    "synthesize_plane_assessments",
    "synthesize_planes",
]
