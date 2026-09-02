"""Exact-identity structural contracts for biological sensitivity evidence.

The records in this leaf module quarantine receptor, genotype, assay, model,
specific-anosmia, and participant evidence by exact identity and study scope.
They never promote receptor diversity or coverage into perceptual
nonredundancy, mixture quality, target fit, liking, sensuality, projection,
longevity, safety, or release authority.  Opaque products, naturals, and blends
cannot inherit an isolated molecule or stereoisomer mechanism.
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
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    UnknownFact,
    ValueState,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _payload,
)

_MODULE_ID = "formulation_intelligence.biological_sensitivity"
_BIOLOGICAL_CEILING = AuthorityCeiling.EVIDENCE_LIMITED
_DOWNSTREAM_AUTHORITY_FLAGS = (
    "physical_authority",
    "sensory_authority",
    "hedonic_authority",
    "perceptual_nonredundancy_authority",
    "mixture_quality_authority",
    "target_fit_authority",
    "liking_authority",
    "sensuality_authority",
    "projection_authority",
    "longevity_authority",
    "safety_authority",
    "release_authority",
)


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _false_authority_payload(data: Mapping[str, Any]) -> None:
    if any(data.get(name) is not False for name in _DOWNSTREAM_AUTHORITY_FLAGS):
        raise ValueError("biological downstream authority flags must all remain false")


def _condition_bound(
    provenance_refs: tuple[ProvenanceRef, ...],
    condition_id: str,
) -> tuple[ProvenanceRef, ...]:
    provenance = _merged_provenance(provenance_refs)
    if not provenance:
        raise ValueError("condition-bound biological provenance must not be empty")
    if any(item.independence_key != condition_id for item in provenance):
        raise ValueError(
            "every biological provenance independence_key must equal the exact condition_id"
        )
    return provenance


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalized_text(value, field_name)


def _optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalized_identifier(value, field_name)


def _canonical_by_id(
    values: Iterable[Any],
    *,
    record_type: type[Any],
    id_attribute: str,
    field_name: str,
) -> tuple[Any, ...]:
    by_id: dict[str, Any] = {}
    by_hash: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = getattr(value, id_attribute)
        previous = by_id.get(identifier)
        if previous is not None and previous != value:
            raise ValueError(f"{field_name} has conflicting ID {identifier!r}")
        by_id[identifier] = value
        by_hash[value.content_sha256] = value
    return tuple(by_hash[digest] for digest in sorted(by_hash))


def _unique_texts(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda item: (item.casefold(), item)))


class BiologicalIdentityKind(str, Enum):
    EXACT_MOLECULE = "exact_molecule"
    OPAQUE_TRADE_PRODUCT = "opaque_trade_product"
    NATURAL_MIXTURE = "natural_mixture"
    BLEND = "blend"


class BiologicalObservationEndpoint(str, Enum):
    """Participant endpoints this module may represent without hedonic promotion."""

    DETECTION = "detection"
    DISCRIMINATION = "discrimination"
    INTENSITY = "intensity"
    QUALITY_DESCRIPTOR = "quality_descriptor"
    SPECIFIC_ANOSMIA = "specific_anosmia"


@dataclass(frozen=True, slots=True)
class BiologicalIdentity(_CanonicalRecord):
    """Exact or explicitly non-exact product identity, never an inferred bridge."""

    SCHEMA_VERSION = "biological_identity_v1"

    identity_id: str
    kind: BiologicalIdentityKind
    identity_label: str
    exact_molecule_id: str | None
    stereochemistry: str | None
    grade_product_basis: str | None
    source_name: str | None = None
    lot_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identity_id",
            _normalized_identifier(self.identity_id, "identity_id"),
        )
        kind = BiologicalIdentityKind(self.kind)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "identity_label",
            _normalized_text(self.identity_label, "identity_label"),
        )
        object.__setattr__(
            self,
            "exact_molecule_id",
            _optional_identifier(self.exact_molecule_id, "exact_molecule_id"),
        )
        object.__setattr__(
            self,
            "stereochemistry",
            _optional_text(self.stereochemistry, "stereochemistry"),
        )
        object.__setattr__(
            self,
            "grade_product_basis",
            _optional_text(self.grade_product_basis, "grade_product_basis"),
        )
        object.__setattr__(self, "source_name", _optional_text(self.source_name, "source_name"))
        object.__setattr__(self, "lot_id", _optional_identifier(self.lot_id, "lot_id"))
        if kind is BiologicalIdentityKind.EXACT_MOLECULE:
            if self.exact_molecule_id is None:
                raise ValueError("exact molecule identity requires exact_molecule_id")
            if self.stereochemistry is None:
                raise ValueError(
                    "exact molecule identity requires explicit stereochemistry or achiral status"
                )
            if self.grade_product_basis is None:
                raise ValueError("exact molecule identity requires grade/product basis")
        elif self.exact_molecule_id is not None or self.stereochemistry is not None:
            raise ValueError(
                "opaque products, naturals, and blends must not masquerade as exact molecules"
            )

    @property
    def is_exact_isolated_molecule(self) -> bool:
        return self.kind is BiologicalIdentityKind.EXACT_MOLECULE

    @property
    def mechanism_identity_key(
        self,
    ) -> tuple[str, str, str, str | None, str | None]:
        if not self.is_exact_isolated_molecule:
            raise ValueError("non-exact identities have no isolated mechanism key")
        assert self.exact_molecule_id is not None
        assert self.stereochemistry is not None
        assert self.grade_product_basis is not None
        return (
            self.exact_molecule_id,
            self.stereochemistry,
            self.grade_product_basis,
            self.source_name,
            self.lot_id,
        )

    @property
    def scope_identity_key(self) -> str:
        """Content-bound material identity used by exact study scopes."""

        if self.is_exact_isolated_molecule:
            payload: object = {
                "kind": self.kind.value,
                "mechanism_identity_key": self.mechanism_identity_key,
            }
        else:
            payload = self.as_dict()
        return _stable_id("biological-material-identity", payload)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BiologicalIdentity:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            identity_id=data["identity_id"],
            kind=BiologicalIdentityKind(data["kind"]),
            identity_label=data["identity_label"],
            exact_molecule_id=data.get("exact_molecule_id"),
            stereochemistry=data.get("stereochemistry"),
            grade_product_basis=data.get("grade_product_basis"),
            source_name=data.get("source_name"),
            lot_id=data.get("lot_id"),
        )


@dataclass(frozen=True, slots=True)
class BiologicalStudyScope(_CanonicalRecord):
    """Exact subject, material, condition, assay, population, and protocol scope."""

    SCHEMA_VERSION = "biological_study_scope_v2"

    target_scope: str
    subject_scope: str
    material_identity_key: str
    condition_id: str
    assay_task: str
    population_scope: str
    matrix_scope: str
    concentration_scope: str
    temporal_scope: str
    protocol_scope: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_scope",
            "subject_scope",
            "material_identity_key",
            "condition_id",
            "assay_task",
            "population_scope",
            "matrix_scope",
            "concentration_scope",
            "temporal_scope",
            "protocol_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )

    @property
    def key(self) -> tuple[str, str, str, str, str, str, str, str, str, str]:
        return (
            self.target_scope,
            self.subject_scope,
            self.material_identity_key,
            self.condition_id,
            self.assay_task,
            self.population_scope,
            self.matrix_scope,
            self.concentration_scope,
            self.temporal_scope,
            self.protocol_scope,
        )

    @property
    def assessment_scope(self) -> AssessmentScope:
        subject = self.subject_scope
        material = self.material_identity_key
        condition = self.condition_id
        assay = self.assay_task
        population = self.population_scope
        matrix = self.matrix_scope
        concentration = self.concentration_scope
        protocol = self.protocol_scope
        return AssessmentScope(
            target_scope=self.target_scope,
            temporal_scope=self.temporal_scope,
            matrix_scope=(
                f"matrix[{len(matrix)}]={matrix};"
                f"subject[{len(subject)}]={subject};"
                f"material[{len(material)}]={material};"
                f"condition[{len(condition)}]={condition};"
                f"concentration[{len(concentration)}]={concentration};"
                f"assay[{len(assay)}]={assay};"
                f"population[{len(population)}]={population};"
                f"protocol[{len(protocol)}]={protocol}"
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BiologicalStudyScope:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            target_scope=data["target_scope"],
            subject_scope=data["subject_scope"],
            material_identity_key=data["material_identity_key"],
            condition_id=data["condition_id"],
            assay_task=data["assay_task"],
            population_scope=data["population_scope"],
            matrix_scope=data["matrix_scope"],
            concentration_scope=data["concentration_scope"],
            temporal_scope=data["temporal_scope"],
            protocol_scope=data["protocol_scope"],
        )


@dataclass(frozen=True, slots=True)
class BiologicalMechanismHypothesis(_CanonicalRecord):
    """One exact-identity assay/model hypothesis with bounded authority."""

    SCHEMA_VERSION = "biological_mechanism_hypothesis_v2"

    hypothesis_id: str
    claimed_identity: BiologicalIdentity
    tested_identity: BiologicalIdentity
    scope: BiologicalStudyScope
    receptor_id: str | None
    genotype_id: str | None
    sensitivity_claim: str
    evidence_class: EvidenceClass
    support: SupportInterval
    uncertainty: str
    specific_anosmia_risk: CriterionValue
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str
    physical_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    perceptual_nonredundancy_authority: bool = field(default=False, init=False)
    mixture_quality_authority: bool = field(default=False, init=False)
    target_fit_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    sensuality_authority: bool = field(default=False, init=False)
    projection_authority: bool = field(default=False, init=False)
    longevity_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_id",
            _normalized_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        for field_name in ("claimed_identity", "tested_identity"):
            identity = getattr(self, field_name)
            if not isinstance(identity, BiologicalIdentity):
                raise TypeError(f"{field_name} must be a BiologicalIdentity")
            if not identity.is_exact_isolated_molecule:
                raise ValueError(
                    "opaque products/naturals/blends cannot inherit an isolated "
                    "exact-molecule mechanism"
                )
        if (
            self.claimed_identity.mechanism_identity_key
            != self.tested_identity.mechanism_identity_key
        ):
            raise ValueError("tested and claimed exact identities must match")
        if not isinstance(self.scope, BiologicalStudyScope):
            raise TypeError("scope must be a BiologicalStudyScope")
        if self.claimed_identity.scope_identity_key != self.scope.material_identity_key:
            raise ValueError(
                "claimed material identity must match the exact BiologicalStudyScope material identity"
            )
        object.__setattr__(
            self,
            "receptor_id",
            _optional_identifier(self.receptor_id, "receptor_id"),
        )
        object.__setattr__(
            self,
            "genotype_id",
            _optional_identifier(self.genotype_id, "genotype_id"),
        )
        if self.receptor_id is None and self.genotype_id is None:
            raise ValueError("a mechanism requires a receptor_id or genotype_id")
        object.__setattr__(
            self,
            "sensitivity_claim",
            _normalized_text(self.sensitivity_claim, "sensitivity_claim"),
        )
        evidence_class = EvidenceClass(self.evidence_class)
        object.__setattr__(self, "evidence_class", evidence_class)
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        condition_provenance = _condition_bound(
            self.support.provenance_refs,
            self.scope.condition_id,
        )
        if any(item.evidence_class is not evidence_class for item in condition_provenance):
            raise ValueError(
                "support provenance evidence_class must match the bound evidence_class"
            )
        if not isinstance(self.specific_anosmia_risk, CriterionValue):
            raise TypeError("specific_anosmia_risk must be a CriterionValue")
        if (
            self.specific_anosmia_risk.state is ValueState.KNOWN
            and self.specific_anosmia_risk.value is not None
            and not 0.0 <= self.specific_anosmia_risk.value <= 1.0
        ):
            raise ValueError("known specific_anosmia_risk must be within [0, 1]")
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
        return self.support.provenance_refs

    @property
    def compatibility_key(self) -> str:
        receptor = self.receptor_id or "receptor-unknown"
        genotype = self.genotype_id or "genotype-unknown"
        exact_identity_key = _stable_id(
            "exact-identity",
            self.claimed_identity.mechanism_identity_key,
        )
        return f"biological.mechanism.{exact_identity_key}.{receptor}.{genotype}"

    @property
    def sensitivity_claim_with_scope(self) -> str:
        identity = self.claimed_identity
        return (
            f"{self.sensitivity_claim} Exact identity={identity.exact_molecule_id}; "
            f"stereochemistry={identity.stereochemistry}; "
            f"grade/product basis={identity.grade_product_basis}; "
            f"subject={self.scope.subject_scope}; "
            f"condition={self.scope.condition_id}; "
            f"assay/task={self.scope.assay_task}; "
            f"population={self.scope.population_scope}; "
            f"matrix={self.scope.matrix_scope}; "
            f"concentration={self.scope.concentration_scope}; "
            f"temporal scope={self.scope.temporal_scope}; "
            f"protocol={self.scope.protocol_scope}."
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BiologicalMechanismHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(data)
        return cls(
            hypothesis_id=data["hypothesis_id"],
            claimed_identity=BiologicalIdentity.from_dict(data["claimed_identity"]),
            tested_identity=BiologicalIdentity.from_dict(data["tested_identity"]),
            scope=BiologicalStudyScope.from_dict(data["scope"]),
            receptor_id=data.get("receptor_id"),
            genotype_id=data.get("genotype_id"),
            sensitivity_claim=data["sensitivity_claim"],
            evidence_class=EvidenceClass(data["evidence_class"]),
            support=SupportInterval.from_dict(data["support"]),
            uncertainty=data["uncertainty"],
            specific_anosmia_risk=CriterionValue.from_dict(data["specific_anosmia_risk"]),
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class ParticipantSensitivityObservation(_CanonicalRecord):
    """One participant-linked task observation, never an assay mechanism."""

    SCHEMA_VERSION = "participant_sensitivity_observation_v2"

    observation_id: str
    identity: BiologicalIdentity
    scope: BiologicalStudyScope
    participant_id: str
    repeat_id: str
    endpoint_id: str
    endpoint_kind: BiologicalObservationEndpoint
    observed_state: str
    provenance_refs: tuple[ProvenanceRef, ...]
    interpolated: bool = field(default=False, init=False)
    mechanism_authority: bool = field(default=False, init=False)
    physical_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    perceptual_nonredundancy_authority: bool = field(default=False, init=False)
    mixture_quality_authority: bool = field(default=False, init=False)
    target_fit_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    sensuality_authority: bool = field(default=False, init=False)
    projection_authority: bool = field(default=False, init=False)
    longevity_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "observation_id",
            "participant_id",
            "repeat_id",
            "endpoint_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.identity, BiologicalIdentity):
            raise TypeError("identity must be a BiologicalIdentity")
        if not self.identity.is_exact_isolated_molecule:
            raise ValueError(
                "participant sensitivity evidence requires an exact molecule/product basis"
            )
        if not isinstance(self.scope, BiologicalStudyScope):
            raise TypeError("scope must be a BiologicalStudyScope")
        if self.identity.scope_identity_key != self.scope.material_identity_key:
            raise ValueError(
                "participant material identity must match the exact BiologicalStudyScope material identity"
            )
        object.__setattr__(
            self,
            "endpoint_kind",
            BiologicalObservationEndpoint(self.endpoint_kind),
        )
        object.__setattr__(
            self,
            "observed_state",
            _normalized_text(self.observed_state, "observed_state"),
        )
        provenance = _condition_bound(
            self.provenance_refs,
            self.scope.condition_id,
        )
        allowed = {EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.USER_REPORT}
        if any(item.evidence_class not in allowed for item in provenance):
            raise ValueError("participant sensitivity observations require direct/user provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParticipantSensitivityObservation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data.get("interpolated") is not False:
            raise ValueError("participant sensitivity interpolation must remain false")
        if data.get("mechanism_authority") is not False:
            raise ValueError("participant sensitivity mechanism authority must remain false")
        _false_authority_payload(data)
        return cls(
            observation_id=data["observation_id"],
            identity=BiologicalIdentity.from_dict(data["identity"]),
            scope=BiologicalStudyScope.from_dict(data["scope"]),
            participant_id=data["participant_id"],
            repeat_id=data["repeat_id"],
            endpoint_id=data["endpoint_id"],
            endpoint_kind=BiologicalObservationEndpoint(data["endpoint_kind"]),
            observed_state=data["observed_state"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class BiologicalSensitivityArchitecture(_CanonicalRecord):
    """One exact-scope library of mechanisms and participant observations."""

    SCHEMA_VERSION = "biological_sensitivity_architecture_v2"

    assessment_id: str
    scope: BiologicalStudyScope
    mechanism_hypotheses: tuple[BiologicalMechanismHypothesis, ...] = ()
    participant_observations: tuple[ParticipantSensitivityObservation, ...] = ()
    physical_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    perceptual_nonredundancy_authority: bool = field(default=False, init=False)
    mixture_quality_authority: bool = field(default=False, init=False)
    target_fit_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    sensuality_authority: bool = field(default=False, init=False)
    projection_authority: bool = field(default=False, init=False)
    longevity_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _normalized_identifier(self.assessment_id, "assessment_id"),
        )
        if not isinstance(self.scope, BiologicalStudyScope):
            raise TypeError("scope must be a BiologicalStudyScope")
        mechanisms = _canonical_by_id(
            self.mechanism_hypotheses,
            record_type=BiologicalMechanismHypothesis,
            id_attribute="hypothesis_id",
            field_name="mechanism_hypotheses",
        )
        observations = _canonical_by_id(
            self.participant_observations,
            record_type=ParticipantSensitivityObservation,
            id_attribute="observation_id",
            field_name="participant_observations",
        )
        if not mechanisms and not observations:
            raise ValueError("at least one biological hypothesis or observation is required")
        mismatches = [
            item for item in (*mechanisms, *observations) if item.scope.key != self.scope.key
        ]
        if mismatches:
            raise ValueError(
                "biological record scope mismatch; emit separate PlaneAssessment packets"
            )
        object.__setattr__(self, "mechanism_hypotheses", mechanisms)
        object.__setattr__(self, "participant_observations", observations)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BiologicalSensitivityArchitecture:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(data)
        return cls(
            assessment_id=data["assessment_id"],
            scope=BiologicalStudyScope.from_dict(data["scope"]),
            mechanism_hypotheses=tuple(
                BiologicalMechanismHypothesis.from_dict(item)
                for item in data.get("mechanism_hypotheses", ())
            ),
            participant_observations=tuple(
                ParticipantSensitivityObservation.from_dict(item)
                for item in data.get("participant_observations", ())
            ),
        )


def _biological_conflicts(
    mechanisms: tuple[BiologicalMechanismHypothesis, ...],
) -> tuple[PlaneConflict, ...]:
    grouped: dict[str, list[BiologicalMechanismHypothesis]] = {}
    for mechanism in mechanisms:
        grouped.setdefault(mechanism.compatibility_key, []).append(mechanism)
    conflicts: list[PlaneConflict] = []
    for key, records in sorted(grouped.items()):
        alternatives = _unique_texts(item.sensitivity_claim_with_scope for item in records)
        if len(alternatives) < 2:
            continue
        conflicts.append(
            PlaneConflict(
                conflict_id=_stable_id(
                    "biological-evidence-conflict",
                    {
                        "compatibility_key": key,
                        "records": [item.content_sha256 for item in records],
                    },
                ),
                claim_key=key,
                alternatives=alternatives,
                reason=(
                    "exact-identity, exact-scope mechanism evidence conflicts; "
                    "repetition is not a vote and all alternatives remain"
                ),
                claim_ids=tuple(item.support.claim_id for item in records),
                provenance_refs=_merged_provenance(
                    ref for item in records for ref in item.provenance_refs
                ),
            )
        )
    return tuple(conflicts)


def _biological_unknowns(
    architecture: BiologicalSensitivityArchitecture,
) -> tuple[UnknownFact, ...]:
    unknowns: list[UnknownFact] = []
    seen_identity_fields: set[tuple[str, str]] = set()
    for mechanism in architecture.mechanism_hypotheses:
        if mechanism.specific_anosmia_risk.state is ValueState.UNKNOWN:
            unknowns.append(
                UnknownFact(
                    unknown_id=f"specific-anosmia-risk:{mechanism.hypothesis_id}",
                    field_key=(f"biological.{mechanism.hypothesis_id}.specific_anosmia_risk"),
                    reason=mechanism.specific_anosmia_risk.reason
                    or "specific-anosmia risk is unknown",
                    needed_evidence=mechanism.minimum_resolving_experiment,
                    provenance_refs=mechanism.provenance_refs,
                )
            )
    identities = (
        *(item.claimed_identity for item in architecture.mechanism_hypotheses),
        *(item.identity for item in architecture.participant_observations),
    )
    identity_provenance: dict[str, tuple[ProvenanceRef, ...]] = {}
    for mechanism in architecture.mechanism_hypotheses:
        identity_provenance.setdefault(
            mechanism.claimed_identity.identity_id, mechanism.provenance_refs
        )
    for observation in architecture.participant_observations:
        identity_provenance.setdefault(
            observation.identity.identity_id, observation.provenance_refs
        )
    for identity in identities:
        for field_name, value in (
            ("source_name", identity.source_name),
            ("lot_id", identity.lot_id),
        ):
            key = (identity.identity_id, field_name)
            if value is not None or key in seen_identity_fields:
                continue
            seen_identity_fields.add(key)
            unknowns.append(
                UnknownFact(
                    unknown_id=f"identity-{field_name}:{identity.identity_id}",
                    field_key=f"biological.identity.{identity.identity_id}.{field_name}",
                    reason=f"{field_name} was not supplied and remains UNKNOWN",
                    needed_evidence="Provide the source/lot identity record if known.",
                    provenance_refs=identity_provenance.get(identity.identity_id, ()),
                )
            )
    provenance = _merged_provenance(
        (
            *(ref for item in architecture.mechanism_hypotheses for ref in item.provenance_refs),
            *(
                ref
                for item in architecture.participant_observations
                for ref in item.provenance_refs
            ),
        )
    )
    unknowns.extend(
        (
            UnknownFact(
                unknown_id="biological-downstream-universal-liking-hold",
                field_key="biological.downstream.universal_liking",
                reason=(
                    "HOLD: receptor, genotype, specific-anosmia, and participant "
                    "sensitivity evidence does not establish universal liking, "
                    "sensuality, beauty, or target fit"
                ),
                needed_evidence=(
                    "Collect criterion-specific, blinded, participant-linked hedonic "
                    "observations and preserve stable opposing clusters."
                ),
                provenance_refs=provenance,
            ),
            UnknownFact(
                unknown_id="biological-downstream-mixture-performance-hold",
                field_key="biological.downstream.mixture_performance",
                reason=(
                    "HOLD: exact-molecule biological sensitivity does not establish "
                    "mixture nonredundancy, quality, projection, or longevity"
                ),
                needed_evidence=(
                    "Run exact-mixture, exact-condition perceptual and physical "
                    "experiments under separately governed contracts."
                ),
                provenance_refs=provenance,
            ),
            UnknownFact(
                unknown_id="biological-downstream-safety-release-hold",
                field_key="biological.downstream.safety_release",
                reason=(
                    "HOLD: receptor or sensitivity evidence has no toxicological, "
                    "regulatory, stability, compounding, or release authority"
                ),
                needed_evidence=(
                    "Use independent exact-build toxicology, regulatory, stability, "
                    "execution, and release-governance evidence."
                ),
                provenance_refs=provenance,
            ),
        )
    )
    return tuple(unknowns)


def build_biological_sensitivity_plane_assessment(
    architecture: BiologicalSensitivityArchitecture,
    *,
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.EVIDENCE_LIMITED,
) -> PlaneAssessment:
    """Emit one exact-scope BIOLOGICAL_SENSITIVITY packet."""

    if not isinstance(architecture, BiologicalSensitivityArchitecture):
        raise TypeError("architecture must be a BiologicalSensitivityArchitecture")
    authority = AuthorityCeiling.minimum((AuthorityCeiling(authority_ceiling), _BIOLOGICAL_CEILING))
    mechanism_authority = AuthorityCeiling.minimum((authority, AuthorityCeiling.HYPOTHESIS_ONLY))
    mechanism_claims = tuple(
        ScopedClaim(
            claim_id=item.support.claim_id,
            claim_key=item.compatibility_key,
            claim_value=item.sensitivity_claim_with_scope,
            claim_kind=ClaimKind.HYPOTHESIS,
            authority_ceiling=mechanism_authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.mechanism_hypotheses
    )
    observed_claims = tuple(
        ScopedClaim(
            claim_id=item.observation_id,
            claim_key=(
                "biological.observed_participant."
                f"{item.identity.scope_identity_key}.{item.participant_id}."
                f"{item.repeat_id}.{item.endpoint_id}.{architecture.scope.condition_id}"
            ),
            claim_value=(
                f"endpoint={item.endpoint_kind.value}; subject={item.participant_id}; "
                f"repeat={item.repeat_id}; condition={architecture.scope.condition_id}; "
                f"observation={item.observed_state}"
            ),
            claim_kind=ClaimKind.OBSERVATION,
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.participant_observations
    )
    criteria = tuple(
        ParetoCriterion(
            criterion_id=f"specific_anosmia_risk_{item.hypothesis_id}",
            direction=CriterionDirection.PRESERVE,
            value=item.specific_anosmia_risk,
            unit="condition-bound participant fraction, not inferred perception",
            authority_ceiling=mechanism_authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.mechanism_hypotheses
    )
    provenance = _merged_provenance(
        (
            *(ref for item in architecture.mechanism_hypotheses for ref in item.provenance_refs),
            *(
                ref
                for item in architecture.participant_observations
                for ref in item.provenance_refs
            ),
        )
    )
    return PlaneAssessment(
        assessment_id=architecture.assessment_id,
        module_id=_MODULE_ID,
        plane_id=PlaneId.BIOLOGICAL_SENSITIVITY,
        scope=architecture.scope.assessment_scope,
        claims=(*mechanism_claims, *observed_claims),
        support_intervals=tuple(item.support for item in architecture.mechanism_hypotheses),
        conflicts=_biological_conflicts(architecture.mechanism_hypotheses),
        unknowns=_biological_unknowns(architecture),
        failure_modes=_unique_texts(
            item.failure_mode for item in architecture.mechanism_hypotheses
        ),
        proposed_experiments=_unique_texts(
            item.minimum_resolving_experiment for item in architecture.mechanism_hypotheses
        ),
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=(architecture.content_sha256,),
        native_criteria=criteria,
    )


@dataclass(frozen=True, slots=True)
class BiologicalSensitivityPlaneAdapter:
    """Structural adapter for consumers that accept ``to_plane_assessment``."""

    architecture: BiologicalSensitivityArchitecture
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.EVIDENCE_LIMITED

    def __post_init__(self) -> None:
        if not isinstance(self.architecture, BiologicalSensitivityArchitecture):
            raise TypeError("architecture must be a BiologicalSensitivityArchitecture")
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling.minimum(
                (AuthorityCeiling(self.authority_ceiling), _BIOLOGICAL_CEILING)
            ),
        )

    def to_plane_assessment(self) -> PlaneAssessment:
        return build_biological_sensitivity_plane_assessment(
            self.architecture,
            authority_ceiling=self.authority_ceiling,
        )


__all__ = [
    "BiologicalIdentity",
    "BiologicalIdentityKind",
    "BiologicalObservationEndpoint",
    "BiologicalMechanismHypothesis",
    "BiologicalSensitivityArchitecture",
    "BiologicalSensitivityPlaneAdapter",
    "BiologicalStudyScope",
    "ParticipantSensitivityObservation",
    "build_biological_sensitivity_plane_assessment",
]
