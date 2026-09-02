"""Immutable, exact-scope alternatives for mixture-perception experiments.

The records in this module are structural hypothesis packets.  They do not turn
headspace, OAV, model fit, or repeated heuristic agreement into observed smell,
pleasantness, perceived contribution, emergence, or mixture beauty.  They also
do not generate formulas or authorize any physical or runtime action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    SupportMeasure,
    UnitInterval,
    UnknownFact,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _payload,
)

_MODULE_ID = "formulation_intelligence.mixture_hypotheses"
_ALTERNATIVE_CLAIM_KEY = "mixture.explanatory_alternative"


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _unique_texts(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda item: (item.casefold(), item)))


class MixtureHypothesisKind(str, Enum):
    """Mutually testable alternatives; none is a default sensory truth."""

    WEIGHTED_COMPONENT = "weighted_component"
    STRONGEST_COMPONENT = "strongest_component"
    DOMINANCE = "dominance"
    MASKING = "masking"
    SUPPRESSION = "suppression"
    UNMASKING = "unmasking"
    CONFIGURAL_RESIDUAL = "configural_residual"


@dataclass(frozen=True, slots=True)
class MixtureHypothesisScope(_CanonicalRecord):
    """Exact target, concentration, time, and matrix key for one alternative."""

    SCHEMA_VERSION = "mixture_hypothesis_scope_v2"

    target_scope: str
    subject_scope: str
    concentration_scope: str
    temporal_scope: str
    matrix_scope: str
    condition_scope: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_scope",
            "subject_scope",
            "concentration_scope",
            "temporal_scope",
            "matrix_scope",
            "condition_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.target_scope,
            self.subject_scope,
            self.concentration_scope,
            self.temporal_scope,
            self.matrix_scope,
            self.condition_scope,
        )

    @property
    def plane_matrix_scope(self) -> str:
        """Losslessly bind concentration into the existing three-part plane scope."""

        subject = self.subject_scope
        matrix = self.matrix_scope
        concentration = self.concentration_scope
        condition = self.condition_scope
        return (
            f"subject[{len(subject)}]={subject};matrix[{len(matrix)}]={matrix};"
            f"concentration[{len(concentration)}]={concentration};"
            f"condition[{len(condition)}]={condition}"
        )

    @property
    def assessment_scope(self) -> AssessmentScope:
        return AssessmentScope(
            target_scope=self.target_scope,
            temporal_scope=self.temporal_scope,
            matrix_scope=self.plane_matrix_scope,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MixtureHypothesisScope:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            target_scope=data["target_scope"],
            subject_scope=data["subject_scope"],
            concentration_scope=data["concentration_scope"],
            temporal_scope=data["temporal_scope"],
            matrix_scope=data["matrix_scope"],
            condition_scope=data["condition_scope"],
        )


@dataclass(frozen=True, slots=True)
class MixtureHypothesis(_CanonicalRecord):
    """One provenance-bound alternative with its own falsification contract."""

    SCHEMA_VERSION = "mixture_hypothesis_v2"

    hypothesis_id: str
    kind: MixtureHypothesisKind
    scope: MixtureHypothesisScope
    statement: str
    component_provenance: tuple[ProvenanceRef, ...]
    mixture_provenance: tuple[ProvenanceRef, ...]
    support: UnitInterval
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str
    causal_emergence_inferred: bool = field(default=False, init=False)
    oav_as_observed_perception: bool = field(default=False, init=False)
    pleasantness_inferred: bool = field(default=False, init=False)
    percent_perceived_contribution_inferred: bool = field(
        default=False,
        init=False,
    )
    mixture_beauty_inferred: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_id",
            _normalized_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        object.__setattr__(self, "kind", MixtureHypothesisKind(self.kind))
        if not isinstance(self.scope, MixtureHypothesisScope):
            raise TypeError("scope must be a MixtureHypothesisScope")
        object.__setattr__(
            self,
            "statement",
            _normalized_text(self.statement, "statement"),
        )
        component = _merged_provenance(self.component_provenance)
        mixture = _merged_provenance(self.mixture_provenance)
        if not component:
            raise ValueError("component_provenance must not be empty")
        if not mixture:
            raise ValueError("mixture_provenance must not be empty")
        object.__setattr__(self, "component_provenance", component)
        object.__setattr__(self, "mixture_provenance", mixture)
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be a UnitInterval")
        if self.support.lower == 1.0:
            raise ValueError("mixture hypotheses cannot declare empirical certainty")
        for field_name in (
            "uncertainty",
            "counterfactual",
            "failure_mode",
            "minimum_resolving_experiment",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @property
    def provenance_refs(self) -> tuple[ProvenanceRef, ...]:
        return _merged_provenance((*self.component_provenance, *self.mixture_provenance))

    @property
    def claim_value(self) -> str:
        return f"{self.kind.value}: {self.statement}"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MixtureHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        authority_flags = (
            "causal_emergence_inferred",
            "oav_as_observed_perception",
            "pleasantness_inferred",
            "percent_perceived_contribution_inferred",
            "mixture_beauty_inferred",
        )
        if any(data.get(flag) is not False for flag in authority_flags):
            raise ValueError("mixture hypothesis authority flags must all remain false")
        return cls(
            hypothesis_id=data["hypothesis_id"],
            kind=MixtureHypothesisKind(data["kind"]),
            scope=MixtureHypothesisScope.from_dict(data["scope"]),
            statement=data["statement"],
            component_provenance=tuple(
                ProvenanceRef.from_dict(item) for item in data["component_provenance"]
            ),
            mixture_provenance=tuple(
                ProvenanceRef.from_dict(item) for item in data["mixture_provenance"]
            ),
            support=UnitInterval.from_dict(data["support"]),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


def _canonical_hypotheses(
    hypotheses: Iterable[MixtureHypothesis],
) -> tuple[MixtureHypothesis, ...]:
    by_hash: dict[str, MixtureHypothesis] = {}
    by_id: dict[str, MixtureHypothesis] = {}
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, MixtureHypothesis):
            raise TypeError("hypotheses must contain MixtureHypothesis values")
        previous = by_id.get(hypothesis.hypothesis_id)
        if previous is not None and previous != hypothesis:
            raise ValueError(f"hypothesis_id {hypothesis.hypothesis_id!r} has conflicting records")
        by_id[hypothesis.hypothesis_id] = hypothesis
        by_hash[hypothesis.content_sha256] = hypothesis
    if not by_hash:
        raise ValueError("at least one mixture hypothesis is required")
    canonical = tuple(by_hash[digest] for digest in sorted(by_hash))
    if len({item.kind for item in canonical}) < 2:
        raise ValueError("mixture assessments require at least two distinct competing alternatives")
    return canonical


def _bounded_authority(requested: AuthorityCeiling) -> AuthorityCeiling:
    return AuthorityCeiling.minimum((AuthorityCeiling(requested), AuthorityCeiling.HYPOTHESIS_ONLY))


def _competing_alternative_conflict(
    hypotheses: tuple[MixtureHypothesis, ...],
) -> tuple[PlaneConflict, ...]:
    payload = {
        "scope": hypotheses[0].scope.as_dict(),
        "hypothesis_ids": sorted(item.hypothesis_id for item in hypotheses),
    }
    return (
        PlaneConflict(
            conflict_id=_stable_id("mixture-alternative-conflict", payload),
            claim_key=_ALTERNATIVE_CLAIM_KEY,
            alternatives=tuple(item.claim_value for item in hypotheses),
            reason=(
                "all supplied exact-scope mixture explanations remain explicit "
                "competing alternatives; none is selected and repetition is not a vote"
            ),
            claim_ids=tuple(item.hypothesis_id for item in hypotheses),
            provenance_refs=_merged_provenance(
                ref for item in hypotheses for ref in item.provenance_refs
            ),
        ),
    )


def build_mixture_plane_assessment(
    hypotheses: Iterable[MixtureHypothesis],
    *,
    assessment_id: str | None = None,
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.HYPOTHESIS_ONLY,
) -> PlaneAssessment:
    """Emit one exact-scope MIXTURE packet without choosing an alternative.

    Scope-mismatched hypotheses fail closed so callers must emit separate packets;
    compatible packets can later be passed to ``plane_synthesis``.  Exact duplicate
    records are canonicalized and therefore cannot amplify support.
    """

    canonical = _canonical_hypotheses(hypotheses)
    scope_keys = {item.scope.key for item in canonical}
    if len(scope_keys) != 1:
        raise ValueError("mixture hypothesis scope mismatch; emit separate PlaneAssessment packets")
    scope = canonical[0].scope
    authority = _bounded_authority(authority_ceiling)
    provenance = _merged_provenance(ref for item in canonical for ref in item.provenance_refs)
    claims = tuple(
        ScopedClaim(
            claim_id=item.hypothesis_id,
            claim_key=_ALTERNATIVE_CLAIM_KEY,
            claim_value=item.claim_value,
            claim_kind=ClaimKind.HYPOTHESIS,
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
        )
        for item in canonical
    )
    intervals = tuple(
        SupportInterval(
            interval_id=f"support:{item.hypothesis_id}",
            claim_id=item.hypothesis_id,
            lower=item.support.lower,
            upper=item.support.upper,
            provenance_refs=item.provenance_refs,
            support_measure=SupportMeasure.EVIDENCE_SUPPORT,
        )
        for item in canonical
    )
    unknowns = tuple(
        UnknownFact(
            unknown_id=f"uncertainty:{item.hypothesis_id}",
            field_key=f"mixture.{item.kind.value}.resolution",
            reason=item.uncertainty,
            needed_evidence=item.minimum_resolving_experiment,
            provenance_refs=item.provenance_refs,
        )
        for item in canonical
    )
    criterion = ParetoCriterion(
        criterion_id="mixture_explanatory_uncertainty",
        direction=CriterionDirection.MINIMIZE,
        value=CriterionValue.unknown(
            "no exact-scope controlled evidence discriminates every alternative"
        ),
        unit="unresolved exact-scope alternative",
        authority_ceiling=authority,
        provenance_refs=provenance,
    )
    resolved_assessment_id = assessment_id or _stable_id(
        "mixture-assessment",
        {
            "scope": scope.as_dict(),
            "hypotheses": [item.content_sha256 for item in canonical],
        },
    )
    return PlaneAssessment(
        assessment_id=resolved_assessment_id,
        module_id=_MODULE_ID,
        plane_id=PlaneId.MIXTURE,
        scope=scope.assessment_scope,
        claims=claims,
        support_intervals=intervals,
        conflicts=_competing_alternative_conflict(canonical),
        unknowns=unknowns,
        failure_modes=_unique_texts(tuple(item.failure_mode for item in canonical)),
        proposed_experiments=_unique_texts(
            tuple(item.minimum_resolving_experiment for item in canonical)
        ),
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=tuple(item.content_sha256 for item in canonical),
        native_criteria=(criterion,),
    )


__all__ = [
    "MixtureHypothesis",
    "MixtureHypothesisKind",
    "MixtureHypothesisScope",
    "build_mixture_plane_assessment",
]
