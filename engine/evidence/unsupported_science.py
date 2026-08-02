"""Fail-closed C9 evidence and unsupported-science quarantine contracts.

The module records whether evidence can support a narrow claim. It does not
calculate receptor response, adaptation, aging, shelf life, performance, or
preference, and it never promotes a legacy numerical score by import alone.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SURFACE_ID_PATTERN = re.compile(r"C0-PM-[0-9]{3}")
_EnumT = TypeVar("_EnumT", bound=Enum)


class C9ContractError(ValueError):
    """Malformed, ambiguous, or authority-ineligible C9 record."""


class C9AssessmentStatus(str, Enum):
    SUPPORTED_NARROW_SCOPE = "SUPPORTED_NARROW_SCOPE"
    WITHHELD = "WITHHELD"
    QUARANTINED = "QUARANTINED"


class ReceptorClaim(str, Enum):
    RECORDED_HUMAN_ASSAY_RESPONSE = "RECORDED_HUMAN_ASSAY_RESPONSE"
    HUMAN_REPERTOIRE_MODEL = "HUMAN_REPERTOIRE_MODEL"
    PERFUME_PERCEPTION = "PERFUME_PERCEPTION"


class AssayAction(str, Enum):
    AGONIST = "AGONIST"
    PARTIAL_AGONIST = "PARTIAL_AGONIST"
    ANTAGONIST = "ANTAGONIST"
    INVERSE_AGONIST = "INVERSE_AGONIST"
    OTHER = "OTHER"


class AssayParameterRole(str, Enum):
    POTENCY = "POTENCY"
    EFFICACY = "EFFICACY"
    OTHER = "OTHER"


class AdaptationClaim(str, Enum):
    RECORDED_CONTEXT_RESPONSE = "RECORDED_CONTEXT_RESPONSE"
    HUMAN_FINE_FRAGRANCE_ADAPTATION = "HUMAN_FINE_FRAGRANCE_ADAPTATION"


class AgingProcess(str, Enum):
    CHEMICAL_TRANSFORMATION = "CHEMICAL_TRANSFORMATION"
    DISSOLUTION_PHYSICAL_EQUILIBRATION = "DISSOLUTION_PHYSICAL_EQUILIBRATION"
    PRECIPITATION_PHASE_BEHAVIOR = "PRECIPITATION_PHASE_BEHAVIOR"
    OXIDATION = "OXIDATION"
    SENSORY_MATURATION = "SENSORY_MATURATION"


class AgingClaim(str, Enum):
    PROCESS_SPECIFIC_CHANGE = "PROCESS_SPECIFIC_CHANGE"
    UNIVERSAL_AGING = "UNIVERSAL_AGING"
    SHELF_LIFE = "SHELF_LIFE"
    GENERIC_SENSORY_MATURATION = "GENERIC_SENSORY_MATURATION"


class UnsupportedOutcome(str, Enum):
    LONGEVITY = "LONGEVITY"
    SILLAGE = "SILLAGE"
    PROJECTION = "PROJECTION"
    EMOTION = "EMOTION"
    HEDONIC = "HEDONIC"


class MetricComparator(str, Enum):
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class LegacyDisposition(str, Enum):
    CAPABILITY_BOUNDARY = "CAPABILITY_BOUNDARY"
    NARROW_ARITHMETIC_ONLY = "NARROW_ARITHMETIC_ONLY"
    QUARANTINED_EXPLORATORY = "QUARANTINED_EXPLORATORY"
    CANONICAL_ABSTENTION = "CANONICAL_ABSTENTION"
    QUARANTINED_LEGACY_FIXTURE = "QUARANTINED_LEGACY_FIXTURE"


class C10Use(str, Enum):
    CAPABILITY_BOUNDARY_ONLY = "CAPABILITY_BOUNDARY_ONLY"
    CALIBRATED_MODEL_REQUIRED = "CALIBRATED_MODEL_REQUIRED"
    ABSTENTION_ONLY = "ABSTENTION_ONLY"
    FORBIDDEN_NUMERIC_AUTHORITY = "FORBIDDEN_NUMERIC_AUTHORITY"


C9_AGING_PROCESSES = (
    AgingProcess.CHEMICAL_TRANSFORMATION,
    AgingProcess.DISSOLUTION_PHYSICAL_EQUILIBRATION,
    AgingProcess.PRECIPITATION_PHASE_BEHAVIOR,
    AgingProcess.OXIDATION,
    AgingProcess.SENSORY_MATURATION,
)

C9_UNSUPPORTED_OUTCOMES = (
    UnsupportedOutcome.LONGEVITY,
    UnsupportedOutcome.SILLAGE,
    UnsupportedOutcome.PROJECTION,
    UnsupportedOutcome.EMOTION,
    UnsupportedOutcome.HEDONIC,
)


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise C9ContractError(f"{field_name} must not be blank")
    return value.strip()


def _optional_nonblank(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, field_name)


def _finite(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise C9ContractError(f"{field_name} must be finite")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise C9ContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise C9ContractError(f"{field_name} must be finite")
    return result


def _positive(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0.0:
        raise C9ContractError(f"{field_name} must be positive")
    return result


def _enum(value: object, enum_type: type[_EnumT], field_name: str) -> _EnumT:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise C9ContractError(f"{field_name} must be a valid {enum_type.__name__}") from exc


def _sha256(value: object, field_name: str) -> str:
    text = _nonblank(value, field_name)
    if _SHA256_PATTERN.fullmatch(text) is None:
        raise C9ContractError(f"{field_name} must be a lowercase SHA-256")
    return text


def _strict_mapping(value: object, expected: set[str], field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise C9ContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise C9ContractError(f"{field_name} keys must be strings")
    payload = dict(value)
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise C9ContractError(f"{field_name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise C9ContractError(f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}")
    return payload


def _string_tuple(value: object, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise C9ContractError(f"{field_name} must be a sequence")
    result = tuple(_nonblank(item, field_name) for item in value)
    if not allow_empty and not result:
        raise C9ContractError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise C9ContractError(f"{field_name} must not contain duplicates")
    return result


def _content_hash(payload: Mapping[str, Any]) -> str:
    return stable_json_hash(dict(payload))


@dataclass(frozen=True, slots=True)
class C9EvidenceReference:
    source_id: str
    locator: str
    title: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _nonblank(self.source_id, "source_id"))
        object.__setattr__(self, "locator", _nonblank(self.locator, "locator"))
        object.__setattr__(self, "title", _nonblank(self.title, "title"))

    def _payload(self) -> dict[str, str]:
        return {
            "schema": "c9-evidence-reference-v1",
            "source_id": self.source_id,
            "locator": self.locator,
            "title": self.title,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class ConcentrationResponsePoint:
    concentration: float
    concentration_unit: str
    response: float
    response_unit: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "concentration",
            _positive(self.concentration, "concentration"),
        )
        object.__setattr__(
            self,
            "concentration_unit",
            _nonblank(self.concentration_unit, "concentration_unit"),
        )
        object.__setattr__(self, "response", _finite(self.response, "response"))
        object.__setattr__(
            self,
            "response_unit",
            _nonblank(self.response_unit, "response_unit"),
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "concentration": self.concentration,
            "concentration_unit": self.concentration_unit,
            "response": self.response,
            "response_unit": self.response_unit,
        }


@dataclass(frozen=True, slots=True)
class AssayParameter:
    role: AssayParameterRole
    name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _enum(self.role, AssayParameterRole, "role"))
        object.__setattr__(self, "name", _nonblank(self.name, "name"))
        object.__setattr__(self, "value", _finite(self.value, "value"))
        object.__setattr__(self, "unit", _nonblank(self.unit, "unit"))

    def as_mapping(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class ReceptorAssayEvidence:
    tested_material: str
    receptor_identity: str
    receptor_species: str
    cell_system: str
    concentration_response: tuple[ConcentrationResponsePoint, ...]
    parameters: tuple[AssayParameter, ...]
    assay_action: AssayAction
    source: C9EvidenceReference
    applicability: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "tested_material",
            _nonblank(self.tested_material, "tested_material"),
        )
        object.__setattr__(
            self,
            "receptor_identity",
            _nonblank(self.receptor_identity, "receptor_identity"),
        )
        object.__setattr__(
            self,
            "receptor_species",
            _nonblank(self.receptor_species, "receptor_species"),
        )
        object.__setattr__(self, "cell_system", _nonblank(self.cell_system, "cell_system"))
        curve = tuple(self.concentration_response)
        if len(curve) < 3 or any(
            not isinstance(point, ConcentrationResponsePoint) for point in curve
        ):
            raise C9ContractError(
                "concentration_response must contain at least three response points"
            )
        concentrations = tuple(point.concentration for point in curve)
        if any(right <= left for left, right in zip(concentrations, concentrations[1:])):
            raise C9ContractError("concentration_response must be strictly increasing")
        if len({point.concentration_unit for point in curve}) != 1:
            raise C9ContractError("concentration_response concentration units must match")
        if len({point.response_unit for point in curve}) != 1:
            raise C9ContractError("concentration_response response units must match")
        object.__setattr__(self, "concentration_response", curve)

        parameters = tuple(self.parameters)
        if not parameters or any(
            not isinstance(parameter, AssayParameter) for parameter in parameters
        ):
            raise C9ContractError("parameters must contain typed assay parameters")
        roles = {parameter.role for parameter in parameters}
        if AssayParameterRole.POTENCY not in roles:
            raise C9ContractError("parameters must include a potency parameter")
        if AssayParameterRole.EFFICACY not in roles:
            raise C9ContractError("parameters must include an efficacy parameter")
        names = tuple(parameter.name.casefold() for parameter in parameters)
        if len(names) != len(set(names)):
            raise C9ContractError("parameters must not contain duplicate names")
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(
            self,
            "assay_action",
            _enum(self.assay_action, AssayAction, "assay_action"),
        )
        if not isinstance(self.source, C9EvidenceReference):
            raise C9ContractError("source must be a C9EvidenceReference")
        object.__setattr__(
            self,
            "applicability",
            _nonblank(self.applicability, "applicability"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-receptor-assay-evidence-v1",
            "tested_material": self.tested_material,
            "receptor_identity": self.receptor_identity,
            "receptor_species": self.receptor_species,
            "cell_system": self.cell_system,
            "concentration_response": [point.as_mapping() for point in self.concentration_response],
            "parameters": [parameter.as_mapping() for parameter in self.parameters],
            "assay_action": self.assay_action.value,
            "source": self.source.as_mapping(),
            "applicability": self.applicability,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class AdaptationContext:
    species: str
    preparation: str
    nervous_system_level: str
    stimulus_protocol: str
    timescale_seconds: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "species", _nonblank(self.species, "species"))
        object.__setattr__(
            self,
            "preparation",
            _nonblank(self.preparation, "preparation"),
        )
        object.__setattr__(
            self,
            "nervous_system_level",
            _nonblank(self.nervous_system_level, "nervous_system_level"),
        )
        object.__setattr__(
            self,
            "stimulus_protocol",
            _nonblank(self.stimulus_protocol, "stimulus_protocol"),
        )
        object.__setattr__(
            self,
            "timescale_seconds",
            _positive(self.timescale_seconds, "timescale_seconds"),
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "species": self.species,
            "preparation": self.preparation,
            "nervous_system_level": self.nervous_system_level,
            "stimulus_protocol": self.stimulus_protocol,
            "timescale_seconds": self.timescale_seconds,
        }


@dataclass(frozen=True, slots=True)
class AdaptationEvidence:
    context: AdaptationContext
    stimulus: str
    endpoint: str
    source: C9EvidenceReference
    applicability: str

    def __post_init__(self) -> None:
        if not isinstance(self.context, AdaptationContext):
            raise C9ContractError("context must be an AdaptationContext")
        object.__setattr__(self, "stimulus", _nonblank(self.stimulus, "stimulus"))
        object.__setattr__(self, "endpoint", _nonblank(self.endpoint, "endpoint"))
        if not isinstance(self.source, C9EvidenceReference):
            raise C9ContractError("source must be a C9EvidenceReference")
        object.__setattr__(
            self,
            "applicability",
            _nonblank(self.applicability, "applicability"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-adaptation-evidence-v1",
            "context": self.context.as_mapping(),
            "stimulus": self.stimulus,
            "endpoint": self.endpoint,
            "source": self.source.as_mapping(),
            "applicability": self.applicability,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class AgingEvidence:
    process: AgingProcess
    subject_identity: str
    matrix: str
    temperature_k: float
    duration_days: float
    protocol: str
    endpoint: str
    source: C9EvidenceReference
    applicability: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "process", _enum(self.process, AgingProcess, "process"))
        object.__setattr__(
            self,
            "subject_identity",
            _nonblank(self.subject_identity, "subject_identity"),
        )
        object.__setattr__(self, "matrix", _nonblank(self.matrix, "matrix"))
        object.__setattr__(
            self,
            "temperature_k",
            _positive(self.temperature_k, "temperature_k"),
        )
        object.__setattr__(
            self,
            "duration_days",
            _positive(self.duration_days, "duration_days"),
        )
        object.__setattr__(self, "protocol", _nonblank(self.protocol, "protocol"))
        object.__setattr__(self, "endpoint", _nonblank(self.endpoint, "endpoint"))
        if not isinstance(self.source, C9EvidenceReference):
            raise C9ContractError("source must be a C9EvidenceReference")
        object.__setattr__(
            self,
            "applicability",
            _nonblank(self.applicability, "applicability"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-aging-evidence-v1",
            "process": self.process.value,
            "subject_identity": self.subject_identity,
            "matrix": self.matrix,
            "temperature_k": self.temperature_k,
            "duration_days": self.duration_days,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
            "source": self.source.as_mapping(),
            "applicability": self.applicability,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class ValidationMetric:
    name: str
    value: float
    threshold: float
    comparator: MetricComparator

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _nonblank(self.name, "name"))
        object.__setattr__(self, "value", _finite(self.value, "value"))
        object.__setattr__(self, "threshold", _finite(self.threshold, "threshold"))
        object.__setattr__(
            self,
            "comparator",
            _enum(self.comparator, MetricComparator, "comparator"),
        )

    @property
    def passed(self) -> bool:
        if self.comparator is MetricComparator.LESS_THAN_OR_EQUAL:
            return self.value <= self.threshold
        return self.value >= self.threshold

    def as_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "comparator": self.comparator.value,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class BuildDValidationReceipt:
    outcome: UnsupportedOutcome
    model_id: str
    model_version: str
    release_sha256: str
    endpoint: str
    scope: str
    held_out_dataset_id: str
    comparator_id: str
    metrics: tuple[ValidationMetric, ...]
    status: ValidationStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", _enum(self.outcome, UnsupportedOutcome, "outcome"))
        object.__setattr__(self, "model_id", _nonblank(self.model_id, "model_id"))
        object.__setattr__(
            self,
            "model_version",
            _nonblank(self.model_version, "model_version"),
        )
        object.__setattr__(
            self,
            "release_sha256",
            _sha256(self.release_sha256, "release_sha256"),
        )
        object.__setattr__(self, "endpoint", _nonblank(self.endpoint, "endpoint"))
        object.__setattr__(self, "scope", _nonblank(self.scope, "scope"))
        object.__setattr__(
            self,
            "held_out_dataset_id",
            _nonblank(self.held_out_dataset_id, "held_out_dataset_id"),
        )
        object.__setattr__(
            self,
            "comparator_id",
            _nonblank(self.comparator_id, "comparator_id"),
        )
        metrics = tuple(self.metrics)
        if not metrics or any(not isinstance(metric, ValidationMetric) for metric in metrics):
            raise C9ContractError("metrics must contain validation metrics")
        names = tuple(metric.name.casefold() for metric in metrics)
        if len(names) != len(set(names)):
            raise C9ContractError("metrics must not contain duplicate names")
        object.__setattr__(self, "metrics", metrics)
        status = _enum(self.status, ValidationStatus, "status")
        object.__setattr__(self, "status", status)
        if status is ValidationStatus.PASS and not all(metric.passed for metric in metrics):
            raise C9ContractError("PASS status requires all passing metrics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-build-d-validation-receipt-v1",
            "outcome": self.outcome.value,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "release_sha256": self.release_sha256,
            "endpoint": self.endpoint,
            "scope": self.scope,
            "held_out_dataset_id": self.held_out_dataset_id,
            "comparator_id": self.comparator_id,
            "metrics": [metric.as_mapping() for metric in self.metrics],
            "status": self.status.value,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class C9ClaimDecision:
    status: C9AssessmentStatus
    claim: str
    claim_authorized: bool
    support_scope: str | None
    evidence_sha256: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        status = _enum(self.status, C9AssessmentStatus, "status")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "claim", _nonblank(self.claim, "claim"))
        if not isinstance(self.claim_authorized, bool):
            raise C9ContractError("claim_authorized must be boolean")
        scope = _optional_nonblank(self.support_scope, "support_scope")
        object.__setattr__(self, "support_scope", scope)
        hashes = tuple(_sha256(item, "evidence_sha256") for item in self.evidence_sha256)
        if len(hashes) != len(set(hashes)):
            raise C9ContractError("evidence_sha256 must not contain duplicates")
        object.__setattr__(self, "evidence_sha256", hashes)
        reasons = _string_tuple(self.reasons, "reasons")
        object.__setattr__(self, "reasons", reasons)

        supported = status is C9AssessmentStatus.SUPPORTED_NARROW_SCOPE
        if supported != self.claim_authorized:
            raise C9ContractError("SUPPORTED_NARROW_SCOPE and claim_authorized must agree")
        if self.claim_authorized and scope is None:
            raise C9ContractError("authorized decisions require support_scope")
        if not self.claim_authorized and scope is not None:
            raise C9ContractError("withheld decisions cannot contain support_scope")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-claim-decision-v1",
            "status": self.status.value,
            "claim": self.claim,
            "claim_authorized": self.claim_authorized,
            "support_scope": self.support_scope,
            "evidence_sha256": list(self.evidence_sha256),
            "reasons": list(self.reasons),
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> C9ClaimDecision:
        payload = _strict_mapping(
            value,
            {
                "schema",
                "status",
                "claim",
                "claim_authorized",
                "support_scope",
                "evidence_sha256",
                "reasons",
                "content_sha256",
            },
            "C9ClaimDecision",
        )
        if payload["schema"] != "c9-claim-decision-v1":
            raise C9ContractError("C9ClaimDecision schema must be c9-claim-decision-v1")
        if not isinstance(payload["claim_authorized"], bool):
            raise C9ContractError("claim_authorized must be boolean")
        decision = cls(
            status=_enum(payload["status"], C9AssessmentStatus, "status"),
            claim=_nonblank(payload["claim"], "claim"),
            claim_authorized=payload["claim_authorized"],
            support_scope=_optional_nonblank(payload["support_scope"], "support_scope"),
            evidence_sha256=_string_tuple(
                payload["evidence_sha256"],
                "evidence_sha256",
                allow_empty=True,
            ),
            reasons=_string_tuple(payload["reasons"], "reasons"),
        )
        supplied_hash = _sha256(payload["content_sha256"], "content_sha256")
        if supplied_hash != decision.content_sha256:
            raise C9ContractError("C9ClaimDecision content_sha256 mismatch")
        return decision


def _withheld(
    claim: Enum | str,
    reasons: Sequence[str],
    evidence_hashes: Sequence[str] = (),
) -> C9ClaimDecision:
    claim_text = claim.value if isinstance(claim, Enum) else claim
    return C9ClaimDecision(
        status=C9AssessmentStatus.WITHHELD,
        claim=claim_text,
        claim_authorized=False,
        support_scope=None,
        evidence_sha256=tuple(evidence_hashes),
        reasons=tuple(reasons),
    )


def _supported(
    claim: Enum | str,
    scope: str,
    reasons: Sequence[str],
    evidence_hashes: Sequence[str],
) -> C9ClaimDecision:
    claim_text = claim.value if isinstance(claim, Enum) else claim
    return C9ClaimDecision(
        status=C9AssessmentStatus.SUPPORTED_NARROW_SCOPE,
        claim=claim_text,
        claim_authorized=True,
        support_scope=scope,
        evidence_sha256=tuple(evidence_hashes),
        reasons=tuple(reasons),
    )


def assess_receptor_claim(
    claim: ReceptorClaim,
    evidence: ReceptorAssayEvidence | None,
) -> C9ClaimDecision:
    claim = _enum(claim, ReceptorClaim, "claim")
    if evidence is None:
        return _withheld(claim, ("complete human receptor assay evidence is required",))
    if not isinstance(evidence, ReceptorAssayEvidence):
        raise C9ContractError("evidence must be ReceptorAssayEvidence or None")

    evidence_hashes = (evidence.content_sha256,)
    if claim is ReceptorClaim.HUMAN_REPERTOIRE_MODEL:
        return _withheld(
            claim,
            ("one or a few receptor assays cannot validate the human olfactory repertoire",),
            evidence_hashes,
        )
    if claim is ReceptorClaim.PERFUME_PERCEPTION:
        return _withheld(
            claim,
            ("a receptor assay does not establish whole-perfume perception",),
            evidence_hashes,
        )
    if evidence.receptor_species.casefold() != "homo sapiens":
        return _withheld(
            claim,
            ("recorded human assay support requires receptor_species Homo sapiens",),
            evidence_hashes,
        )
    scope = (
        f"{evidence.tested_material} response at Homo sapiens "
        f"{evidence.receptor_identity} in {evidence.cell_system}; {evidence.applicability}"
    )
    return _supported(
        claim,
        scope,
        ("complete concentration-response, parameter, action, source, and applicability evidence",),
        evidence_hashes,
    )


def assess_adaptation_claim(
    claim: AdaptationClaim,
    evidence: AdaptationEvidence | None,
    *,
    requested_context: AdaptationContext | None,
) -> C9ClaimDecision:
    claim = _enum(claim, AdaptationClaim, "claim")
    if evidence is None:
        return _withheld(claim, ("complete adaptation evidence is required",))
    if not isinstance(evidence, AdaptationEvidence):
        raise C9ContractError("evidence must be AdaptationEvidence or None")
    evidence_hashes = (evidence.content_sha256,)
    if requested_context is None:
        return _withheld(claim, ("requested adaptation context is required",), evidence_hashes)
    if not isinstance(requested_context, AdaptationContext):
        raise C9ContractError("requested_context must be AdaptationContext or None")
    if claim is AdaptationClaim.HUMAN_FINE_FRAGRANCE_ADAPTATION:
        return _withheld(
            claim,
            ("recorded adaptation evidence cannot be generalized to human fine fragrance",),
            evidence_hashes,
        )
    if requested_context != evidence.context:
        return _withheld(
            claim,
            (
                "adaptation species, preparation, nervous-system, protocol, and timescale context must match",
            ),
            evidence_hashes,
        )
    context = evidence.context
    scope = (
        f"{evidence.stimulus}; {context.species}; {context.preparation}; "
        f"{context.nervous_system_level}; {context.stimulus_protocol}; "
        f"{context.timescale_seconds:g} seconds"
    )
    return _supported(
        claim,
        scope,
        ("adaptation evidence matches every requested C9 context field",),
        evidence_hashes,
    )


def assess_aging_claim(
    claim: AgingClaim,
    evidence: Sequence[AgingEvidence] = (),
    *,
    requested_process: AgingProcess | None = None,
) -> C9ClaimDecision:
    claim = _enum(claim, AgingClaim, "claim")
    records = tuple(evidence)
    if any(not isinstance(record, AgingEvidence) for record in records):
        raise C9ContractError("evidence must contain AgingEvidence records")
    evidence_hashes = tuple(record.content_sha256 for record in records)

    if claim is not AgingClaim.PROCESS_SPECIFIC_CHANGE:
        return _withheld(
            claim,
            (
                "process-specific evidence does not authorize universal aging, shelf life, "
                "or generic sensory maturation",
            ),
            evidence_hashes,
        )
    if requested_process is None:
        return _withheld(
            claim,
            ("requested_process is required for a process-specific claim",),
            evidence_hashes,
        )
    requested_process = _enum(requested_process, AgingProcess, "requested_process")
    matching = tuple(record for record in records if record.process is requested_process)
    if len(matching) != 1:
        return _withheld(
            claim,
            ("exactly one evidence record must match the requested aging process",),
            evidence_hashes,
        )
    record = matching[0]
    scope = (
        f"{record.process.value} for {record.subject_identity} in {record.matrix} at "
        f"{record.temperature_k:g} K for {record.duration_days:g} days; {record.applicability}"
    )
    return _supported(
        claim,
        scope,
        ("one process-specific record supports only its recorded process and scope",),
        (record.content_sha256,),
    )


def assess_unsupported_outcome(
    outcome: UnsupportedOutcome,
    *,
    receipt: BuildDValidationReceipt | None,
    requested_scope: str,
) -> C9ClaimDecision:
    outcome = _enum(outcome, UnsupportedOutcome, "outcome")
    requested_scope = _nonblank(requested_scope, "requested_scope")
    if receipt is None:
        return _withheld(
            outcome,
            ("a passing exact-scope Build D validation receipt is required",),
        )
    if not isinstance(receipt, BuildDValidationReceipt):
        raise C9ContractError("receipt must be BuildDValidationReceipt or None")
    evidence_hashes = (receipt.content_sha256,)
    if receipt.status is not ValidationStatus.PASS:
        return _withheld(outcome, ("Build D validation receipt did not pass",), evidence_hashes)
    if receipt.outcome is not outcome:
        return _withheld(
            outcome,
            ("Build D receipt outcome does not match the requested outcome",),
            evidence_hashes,
        )
    if receipt.scope != requested_scope:
        return _withheld(
            outcome,
            ("Build D receipt scope does not exactly match the requested scope",),
            evidence_hashes,
        )
    return _supported(
        outcome,
        receipt.scope,
        ("passing held-out Build D receipt authorizes only the exact recorded scope",),
        evidence_hashes,
    )


@dataclass(frozen=True, slots=True)
class C9LegacySurfaceRecord:
    surface_id: str
    legacy_name: str
    source_paths: tuple[str, ...]
    disposition: LegacyDisposition
    c10_use: C10Use
    numeric_claim_authority: bool
    reason: str

    def __post_init__(self) -> None:
        surface_id = _nonblank(self.surface_id, "surface_id")
        if _SURFACE_ID_PATTERN.fullmatch(surface_id) is None:
            raise C9ContractError("surface_id must use C0-PM-NNN")
        object.__setattr__(self, "surface_id", surface_id)
        object.__setattr__(
            self,
            "legacy_name",
            _nonblank(self.legacy_name, "legacy_name"),
        )
        object.__setattr__(
            self,
            "source_paths",
            _string_tuple(self.source_paths, "source_paths"),
        )
        object.__setattr__(
            self,
            "disposition",
            _enum(self.disposition, LegacyDisposition, "disposition"),
        )
        object.__setattr__(self, "c10_use", _enum(self.c10_use, C10Use, "c10_use"))
        if self.numeric_claim_authority is not False:
            raise C9ContractError("numeric_claim_authority must remain false")
        object.__setattr__(self, "reason", _nonblank(self.reason, "reason"))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "c9-legacy-surface-v1",
            "surface_id": self.surface_id,
            "legacy_name": self.legacy_name,
            "source_paths": list(self.source_paths),
            "disposition": self.disposition.value,
            "c10_use": self.c10_use.value,
            "numeric_claim_authority": self.numeric_claim_authority,
            "reason": self.reason,
        }

    @property
    def content_sha256(self) -> str:
        return _content_hash(self._payload())

    def as_mapping(self) -> dict[str, Any]:
        return {**self._payload(), "content_sha256": self.content_sha256}


def _surface(
    surface_id: str,
    legacy_name: str,
    source_paths: tuple[str, ...],
    disposition: LegacyDisposition,
    c10_use: C10Use,
    reason: str,
) -> C9LegacySurfaceRecord:
    return C9LegacySurfaceRecord(
        surface_id=surface_id,
        legacy_name=legacy_name,
        source_paths=source_paths,
        disposition=disposition,
        c10_use=c10_use,
        numeric_claim_authority=False,
        reason=reason,
    )


C9_LEGACY_SURFACES = (
    _surface(
        "C0-PM-022",
        "UNIFAC activity-model capability boundary",
        ("engine/thermo/activity.py",),
        LegacyDisposition.CAPABILITY_BOUNDARY,
        C10Use.CAPABILITY_BOUNDARY_ONLY,
        "The active model remains a Hansen heuristic; UNIFAC is an inactive capability boundary.",
    ),
    _surface(
        "C0-PM-023",
        "Science-KB UNIFAC group catalogue",
        ("engine/science_kb.py",),
        LegacyDisposition.CAPABILITY_BOUNDARY,
        C10Use.CAPABILITY_BOUNDARY_ONLY,
        "A group catalogue is not subgroup assignment, parameterization, or an active UNIFAC model.",
    ),
    _surface(
        "C0-PM-032",
        "Arrhenius rate arithmetic",
        ("engine/chemistry/maturation.py",),
        LegacyDisposition.NARROW_ARITHMETIC_ONLY,
        C10Use.CALIBRATED_MODEL_REQUIRED,
        "Exact arithmetic does not validate reaction parameters or formula applicability.",
    ),
    _surface(
        "C0-PM-033",
        "Maturation reaction and shelf-life predictor",
        ("engine/chemistry/maturation.py", "engine/pipeline/gates.py"),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Generic kinetics cannot authorize formula shelf life or universal maturation.",
    ),
    _surface(
        "C0-PM-034",
        "Odor-family-prior receptor occupancy",
        ("engine/receptor/binding.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Family priors are not material-specific human receptor assay evidence.",
    ),
    _surface(
        "C0-PM-035",
        "Glomerular vector, novelty, and configural blur transforms",
        ("engine/receptor/bulb.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Numerical transforms do not validate human repertoire or perfume perception.",
    ),
    _surface(
        "C0-PM-036",
        "Fixed-timescale receptor adaptation",
        ("engine/receptor/adaptation.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "The fixed timescale lacks species, preparation, protocol, and transfer evidence.",
    ),
    _surface(
        "C0-PM-037",
        "Material-name adaptation penalty",
        ("engine/science_data.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "A name-indexed penalty is not a context-matched adaptation measurement.",
    ),
    _surface(
        "C0-PM-038",
        "Fixed-valence hedonic scorer",
        ("engine/hedonic_model.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Fixed valence is not held-out human hedonic validation.",
    ),
    _surface(
        "C0-PM-039",
        "Kaw/MW diffusion-field and sillage scorer",
        ("engine/diffusion_model.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "A heuristic field score is not measured sillage or projection.",
    ),
    _surface(
        "C0-PM-040",
        "Skin reservoir and fabric substantivity scorer",
        ("engine/skin_interaction.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "A heuristic reservoir score is not a validated skin performance outcome.",
    ),
    _surface(
        "C0-PM-041",
        "Potts-Guy skin partition and depot release helper",
        ("engine/skin_compartments.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Literature-derived arithmetic lacks perfume-specific held-out endpoint validation.",
    ),
    _surface(
        "C0-PM-042",
        "Legacy backend note-weighted longevity estimate",
        ("backend/app/domain/ingredients/chemistry.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Note weights are not measured or validated longevity hours.",
    ),
    _surface(
        "C0-PM-043",
        "Legacy backend note-weighted sillage estimate",
        ("backend/app/domain/ingredients/chemistry.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "A categorical note heuristic is not measured sillage.",
    ),
    _surface(
        "C0-PM-044",
        "Canonical workbench longevity/sillage/receptor abstention",
        ("engine/workbench.py",),
        LegacyDisposition.CANONICAL_ABSTENTION,
        C10Use.ABSTENTION_ONLY,
        "The canonical UNKNOWN/null behavior is the authority until narrow validation passes.",
    ),
    _surface(
        "C0-PM-045",
        "Unified release impact/tenacity/diffusion scoring",
        ("engine/pipeline/release_scoring.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "Diagnostic release scores have no physical or sensory endpoint authority.",
    ),
    _surface(
        "C0-PM-046",
        "In-sample linear score calibration pipeline",
        ("engine/calibration.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "In-sample fit cannot replace preregistered held-out validation.",
    ),
    _surface(
        "C0-PM-047",
        "Standalone formula simulator score bundle",
        ("scripts/formula_simulator.py",),
        LegacyDisposition.QUARANTINED_LEGACY_FIXTURE,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "The disconnected simulator is preserved only as legacy regression evidence.",
    ),
    _surface(
        "C0-PM-048",
        "Optimizer composite physical and sensory scoring runtime",
        ("engine/optimizer/scoring.py",),
        LegacyDisposition.QUARANTINED_EXPLORATORY,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY,
        "C10 must not optimize unsupported sensory or performance numbers as experimental truth.",
    ),
)

C9_LEGACY_SURFACE_IDS = tuple(record.surface_id for record in C9_LEGACY_SURFACES)


def get_c9_legacy_surface(surface_id: str) -> C9LegacySurfaceRecord:
    surface_id = _nonblank(surface_id, "surface_id")
    for record in C9_LEGACY_SURFACES:
        if record.surface_id == surface_id:
            return record
    raise C9ContractError(f"unknown legacy surface: {surface_id}")


__all__ = (
    "C9_AGING_PROCESSES",
    "C9_LEGACY_SURFACE_IDS",
    "C9_LEGACY_SURFACES",
    "C9_UNSUPPORTED_OUTCOMES",
    "AdaptationClaim",
    "AdaptationContext",
    "AdaptationEvidence",
    "AgingClaim",
    "AgingEvidence",
    "AgingProcess",
    "AssayAction",
    "AssayParameter",
    "AssayParameterRole",
    "BuildDValidationReceipt",
    "C10Use",
    "C9AssessmentStatus",
    "C9ClaimDecision",
    "C9ContractError",
    "C9EvidenceReference",
    "C9LegacySurfaceRecord",
    "ConcentrationResponsePoint",
    "LegacyDisposition",
    "MetricComparator",
    "ReceptorAssayEvidence",
    "ReceptorClaim",
    "UnsupportedOutcome",
    "ValidationMetric",
    "ValidationStatus",
    "assess_adaptation_claim",
    "assess_aging_claim",
    "assess_receptor_claim",
    "assess_unsupported_outcome",
    "get_c9_legacy_surface",
)
