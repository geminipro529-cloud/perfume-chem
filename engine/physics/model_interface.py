"""Immutable Build C3 model-interface and applicability contracts.

This module evaluates no scientific equation and selects no production caller.
It binds explicit model identity, version, domain, context, and claim authority.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash
from engine.physics.matrix_environment import (
    ApplicationEnvironmentKind,
    MatrixStage,
)
from engine.physics.properties import (
    CanonicalScope,
    ThermophysicalProperty,
)


class ModelInterfaceContractError(ValueError):
    """A malformed C3 contract or unsupported closed-schema payload."""


class ModelOperation(str, Enum):
    PREDICT_EQUILIBRIUM_HEADSPACE = "predict_equilibrium_headspace"
    PREDICT_DYNAMIC_RELEASE = "predict_dynamic_release"
    ESTIMATE_PARTITION_COEFFICIENT = "estimate_partition_coefficient"
    EVALUATE_APPLICABILITY = "evaluate_applicability"
    PROPAGATE_UNCERTAINTY = "propagate_uncertainty"
    COMPARE_MODELS = "compare_models"


class ModelFamily(str, Enum):
    IDEAL_RAOULT_BASELINE = "IDEAL_RAOULT_BASELINE"
    HENRY_LAW_DILUTE_BASELINE = "HENRY_LAW_DILUTE_BASELINE"
    MEASURED_LOOKUP_INTERPOLATION = "MEASURED_LOOKUP_INTERPOLATION"
    EMPIRICAL_MATRIX_CORRECTION = "EMPIRICAL_MATRIX_CORRECTION"
    UNIFAC_OR_MODIFIED_UNIFAC = "UNIFAC_OR_MODIFIED_UNIFAC"
    IMPORTED_COSMO_RS = "IMPORTED_COSMO_RS"
    MEASURED_PARTITION_MODEL = "MEASURED_PARTITION_MODEL"
    DYNAMIC_SEMI_EMPIRICAL_MODEL = "DYNAMIC_SEMI_EMPIRICAL_MODEL"
    LEGACY_HEURISTIC_ADAPTER = "LEGACY_HEURISTIC_ADAPTER"


class ApplicabilityState(str, Enum):
    IN_DOMAIN = "IN_DOMAIN"
    NEAR_DOMAIN_WITH_WARNING = "NEAR_DOMAIN_WITH_WARNING"
    OUTSIDE_APPLICABILITY_DOMAIN = "OUTSIDE_APPLICABILITY_DOMAIN"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    MODEL_NOT_VALIDATED = "MODEL_NOT_VALIDATED"


class ModelAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class ModelResultStatus(str, Enum):
    COMPUTED = "COMPUTED"
    ABSTAINED = "ABSTAINED"


class ModelEvidenceClass(str, Enum):
    THEORETICAL_BASELINE = "THEORETICAL_BASELINE"
    MEASURED = "MEASURED"
    EMPIRICAL = "EMPIRICAL"
    COMPUTATIONAL_IMPORT = "COMPUTATIONAL_IMPORT"
    LITERATURE_DERIVED = "LITERATURE_DERIVED"
    LEGACY_HEURISTIC = "LEGACY_HEURISTIC"
    UNVALIDATED = "UNVALIDATED"


_EnumT = TypeVar("_EnumT", bound=Enum)
_COMPUTATION_OPERATIONS = frozenset(
    {
        ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
        ModelOperation.PREDICT_DYNAMIC_RELEASE,
        ModelOperation.ESTIMATE_PARTITION_COEFFICIENT,
        ModelOperation.PROPAGATE_UNCERTAINTY,
    }
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelInterfaceContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ModelInterfaceContractError(f"{field_name} keys must be strings")
    return dict(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ModelInterfaceContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ModelInterfaceContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelInterfaceContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ModelInterfaceContractError(f"{field_name} must be finite")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ModelInterfaceContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(normalized):
        raise ModelInterfaceContractError(f"{field_name} must be finite")
    return normalized


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ModelInterfaceContractError(f"{field_name} must be a boolean")
    return value


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ModelInterfaceContractError(f"{field_name} must be a lowercase 64-character SHA-256")
    return value


def _optional_sha256(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, field_name)


def _git_commit(value: object) -> str:
    if not isinstance(value, str) or _GIT_COMMIT_PATTERN.fullmatch(value) is None:
        raise ModelInterfaceContractError(
            "code_commit must be a lowercase 40- or 64-character hexadecimal commit"
        )
    return value


def _enum_value(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ModelInterfaceContractError(f"{field_name} is not supported") from exc


def _direct_enum(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    if not isinstance(value, enum_type):
        raise ModelInterfaceContractError(f"{field_name} must be a {enum_type.__name__}")
    return value


def _strings(
    values: object,
    field_name: str,
    *,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ModelInterfaceContractError(f"{field_name} must be a sequence")
    normalized = tuple(_nonblank(value, field_name) for value in values)
    if require_nonempty and not normalized:
        raise ModelInterfaceContractError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ModelInterfaceContractError(f"{field_name} contains duplicate entries")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _enums(
    values: object,
    enum_type: type[_EnumT],
    field_name: str,
    *,
    require_nonempty: bool = False,
) -> tuple[_EnumT, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ModelInterfaceContractError(f"{field_name} must be a sequence")
    normalized = tuple(_direct_enum(enum_type, value, field_name) for value in values)
    if require_nonempty and not normalized:
        raise ModelInterfaceContractError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ModelInterfaceContractError(f"{field_name} contains duplicate entries")
    return tuple(sorted(normalized, key=lambda item: str(item.value)))


def _parsed_enums(
    values: object,
    enum_type: type[_EnumT],
    field_name: str,
) -> tuple[_EnumT, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ModelInterfaceContractError(f"{field_name} must be a sequence")
    return tuple(_enum_value(enum_type, value, field_name) for value in values)


def _scope(value: object, field_name: str) -> CanonicalScope:
    if not isinstance(value, CanonicalScope):
        raise ModelInterfaceContractError(f"{field_name} must be a CanonicalScope")
    return value


def _uncertainty_free_hash(payload: Mapping[str, object]) -> str:
    return stable_json_hash(dict(payload))


@dataclass(frozen=True, slots=True)
class ModelSelector:
    family: ModelFamily
    model_version: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        family = _direct_enum(ModelFamily, self.family, "family")
        version = _nonblank(self.model_version, "model_version")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "model_version", version)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-model-selector-v1",
            "family": self.family.value,
            "model_version": self.model_version,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ModelSelector:
        normalized = _mapping(payload, "model selector")
        _exact_keys(
            normalized,
            {"schema", "family", "model_version", "content_sha256"},
            "model selector",
        )
        if normalized["schema"] != "c3-model-selector-v1":
            raise ModelInterfaceContractError("model selector schema must be c3-model-selector-v1")
        result = cls(
            family=_enum_value(ModelFamily, normalized["family"], "family"),
            model_version=normalized["model_version"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "model selector content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class DomainRange:
    lower: float
    upper: float
    unit: str
    lower_inclusive: bool
    upper_inclusive: bool
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        lower = _finite(self.lower, "lower")
        upper = _finite(self.upper, "upper")
        if lower > upper:
            raise ModelInterfaceContractError("lower must not exceed upper")
        unit = _nonblank(self.unit, "unit")
        lower_inclusive = _boolean(self.lower_inclusive, "lower_inclusive")
        upper_inclusive = _boolean(self.upper_inclusive, "upper_inclusive")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "lower_inclusive", lower_inclusive)
        object.__setattr__(self, "upper_inclusive", upper_inclusive)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-domain-range-v1",
            "lower": self.lower,
            "upper": self.upper,
            "unit": self.unit,
            "lower_inclusive": self.lower_inclusive,
            "upper_inclusive": self.upper_inclusive,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DomainRange:
        normalized = _mapping(payload, "domain range")
        _exact_keys(
            normalized,
            {
                "schema",
                "lower",
                "upper",
                "unit",
                "lower_inclusive",
                "upper_inclusive",
                "content_sha256",
            },
            "domain range",
        )
        if normalized["schema"] != "c3-domain-range-v1":
            raise ModelInterfaceContractError("domain range schema must be c3-domain-range-v1")
        result = cls(
            lower=normalized["lower"],
            upper=normalized["upper"],
            unit=normalized["unit"],
            lower_inclusive=normalized["lower_inclusive"],
            upper_inclusive=normalized["upper_inclusive"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "domain range content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ApplicabilityDomain:
    domain_id: str
    domain_version: str
    supported_identity_ids: tuple[str, ...]
    supported_chemical_classes: tuple[str, ...]
    supported_functional_groups: tuple[str, ...]
    supported_matrix_stages: tuple[MatrixStage, ...]
    matrix_range: CanonicalScope
    concentration_range: DomainRange | None
    temperature_range: DomainRange | None
    pressure_range: DomainRange | None
    supported_phase_behaviors: tuple[str, ...]
    supported_environment_kinds: tuple[ApplicationEnvironmentKind, ...]
    required_properties: tuple[ThermophysicalProperty, ...]
    training_calibration_domain: CanonicalScope
    known_failure_modes: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "domain_id", _nonblank(self.domain_id, "domain_id"))
        object.__setattr__(
            self,
            "domain_version",
            _nonblank(self.domain_version, "domain_version"),
        )
        object.__setattr__(
            self,
            "supported_identity_ids",
            _strings(self.supported_identity_ids, "supported_identity_ids"),
        )
        object.__setattr__(
            self,
            "supported_chemical_classes",
            _strings(
                self.supported_chemical_classes,
                "supported_chemical_classes",
            ),
        )
        object.__setattr__(
            self,
            "supported_functional_groups",
            _strings(
                self.supported_functional_groups,
                "supported_functional_groups",
            ),
        )
        object.__setattr__(
            self,
            "supported_matrix_stages",
            _enums(
                self.supported_matrix_stages,
                MatrixStage,
                "supported_matrix_stages",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "matrix_range",
            _scope(self.matrix_range, "matrix_range"),
        )
        for name in (
            "concentration_range",
            "temperature_range",
            "pressure_range",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, DomainRange):
                raise ModelInterfaceContractError(f"{name} must be a DomainRange or None")
        object.__setattr__(
            self,
            "supported_phase_behaviors",
            _strings(
                self.supported_phase_behaviors,
                "supported_phase_behaviors",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "supported_environment_kinds",
            _enums(
                self.supported_environment_kinds,
                ApplicationEnvironmentKind,
                "supported_environment_kinds",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "required_properties",
            _enums(
                self.required_properties,
                ThermophysicalProperty,
                "required_properties",
            ),
        )
        object.__setattr__(
            self,
            "training_calibration_domain",
            _scope(
                self.training_calibration_domain,
                "training_calibration_domain",
            ),
        )
        object.__setattr__(
            self,
            "known_failure_modes",
            _strings(
                self.known_failure_modes,
                "known_failure_modes",
                require_nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-applicability-domain-v1",
            "domain_id": self.domain_id,
            "domain_version": self.domain_version,
            "supported_identity_ids": list(self.supported_identity_ids),
            "supported_chemical_classes": list(self.supported_chemical_classes),
            "supported_functional_groups": list(self.supported_functional_groups),
            "supported_matrix_stages": [item.value for item in self.supported_matrix_stages],
            "matrix_range": self.matrix_range.to_mapping(),
            "concentration_range": (
                None if self.concentration_range is None else self.concentration_range.to_mapping()
            ),
            "temperature_range": (
                None if self.temperature_range is None else self.temperature_range.to_mapping()
            ),
            "pressure_range": (
                None if self.pressure_range is None else self.pressure_range.to_mapping()
            ),
            "supported_phase_behaviors": list(self.supported_phase_behaviors),
            "supported_environment_kinds": [
                item.value for item in self.supported_environment_kinds
            ],
            "required_properties": [item.value for item in self.required_properties],
            "training_calibration_domain": (self.training_calibration_domain.to_mapping()),
            "known_failure_modes": list(self.known_failure_modes),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ApplicabilityDomain:
        normalized = _mapping(payload, "applicability domain")
        _exact_keys(
            normalized,
            {
                "schema",
                "domain_id",
                "domain_version",
                "supported_identity_ids",
                "supported_chemical_classes",
                "supported_functional_groups",
                "supported_matrix_stages",
                "matrix_range",
                "concentration_range",
                "temperature_range",
                "pressure_range",
                "supported_phase_behaviors",
                "supported_environment_kinds",
                "required_properties",
                "training_calibration_domain",
                "known_failure_modes",
                "content_sha256",
            },
            "applicability domain",
        )
        if normalized["schema"] != "c3-applicability-domain-v1":
            raise ModelInterfaceContractError(
                "applicability domain schema must be c3-applicability-domain-v1"
            )

        def optional_range(name: str) -> DomainRange | None:
            value = normalized[name]
            if value is None:
                return None
            return DomainRange.from_mapping(_mapping(value, name))

        result = cls(
            domain_id=normalized["domain_id"],
            domain_version=normalized["domain_version"],
            supported_identity_ids=tuple(normalized["supported_identity_ids"]),
            supported_chemical_classes=tuple(normalized["supported_chemical_classes"]),
            supported_functional_groups=tuple(normalized["supported_functional_groups"]),
            supported_matrix_stages=_parsed_enums(
                normalized["supported_matrix_stages"],
                MatrixStage,
                "supported_matrix_stages",
            ),
            matrix_range=CanonicalScope.from_mapping(
                _mapping(normalized["matrix_range"], "matrix_range")
            ),
            concentration_range=optional_range("concentration_range"),
            temperature_range=optional_range("temperature_range"),
            pressure_range=optional_range("pressure_range"),
            supported_phase_behaviors=tuple(normalized["supported_phase_behaviors"]),
            supported_environment_kinds=_parsed_enums(
                normalized["supported_environment_kinds"],
                ApplicationEnvironmentKind,
                "supported_environment_kinds",
            ),
            required_properties=_parsed_enums(
                normalized["required_properties"],
                ThermophysicalProperty,
                "required_properties",
            ),
            training_calibration_domain=CanonicalScope.from_mapping(
                _mapping(
                    normalized["training_calibration_domain"],
                    "training_calibration_domain",
                )
            ),
            known_failure_modes=tuple(normalized["known_failure_modes"]),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "applicability domain content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelRelease:
    selector: ModelSelector
    parameter_set_version: str
    code_commit: str
    implementation_sha256: str
    parameter_set_sha256: str
    coefficient_set_sha256: str | None
    decomposition_sha256: str | None
    training_data_sha256: str | None
    applicability_domain: ApplicabilityDomain
    supported_operations: tuple[ModelOperation, ...]
    availability: ModelAvailability
    unavailable_reason: str | None
    evidence_class: ModelEvidenceClass
    may_feed_oav_screening: bool
    permitted_claim_wording: tuple[str, ...]
    forbidden_claim_wording: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.selector, ModelSelector):
            raise ModelInterfaceContractError("selector must be a ModelSelector")
        parameter_version = _nonblank(
            self.parameter_set_version,
            "parameter_set_version",
        )
        code_commit = _git_commit(self.code_commit)
        implementation_sha256 = _sha256(
            self.implementation_sha256,
            "implementation_sha256",
        )
        parameter_set_sha256 = _sha256(
            self.parameter_set_sha256,
            "parameter_set_sha256",
        )
        coefficient_set_sha256 = _optional_sha256(
            self.coefficient_set_sha256,
            "coefficient_set_sha256",
        )
        decomposition_sha256 = _optional_sha256(
            self.decomposition_sha256,
            "decomposition_sha256",
        )
        training_data_sha256 = _optional_sha256(
            self.training_data_sha256,
            "training_data_sha256",
        )
        if not isinstance(self.applicability_domain, ApplicabilityDomain):
            raise ModelInterfaceContractError("applicability_domain must be an ApplicabilityDomain")
        supported_operations = _enums(
            self.supported_operations,
            ModelOperation,
            "supported_operations",
            require_nonempty=True,
        )
        if any(operation not in _COMPUTATION_OPERATIONS for operation in supported_operations):
            raise ModelInterfaceContractError(
                "supported_operations may contain only answer-producing operations"
            )
        availability = _direct_enum(
            ModelAvailability,
            self.availability,
            "availability",
        )
        evidence_class = _direct_enum(
            ModelEvidenceClass,
            self.evidence_class,
            "evidence_class",
        )
        may_feed_oav = _boolean(
            self.may_feed_oav_screening,
            "may_feed_oav_screening",
        )
        unavailable_reason = self.unavailable_reason
        if availability is ModelAvailability.AVAILABLE:
            if unavailable_reason is not None:
                raise ModelInterfaceContractError(
                    "unavailable_reason must be None for an available release"
                )
        else:
            if unavailable_reason is None:
                raise ModelInterfaceContractError(
                    "unavailable_reason is required for an unavailable release"
                )
            unavailable_reason = _nonblank(
                unavailable_reason,
                "unavailable_reason",
            )
            if evidence_class is not ModelEvidenceClass.UNVALIDATED:
                raise ModelInterfaceContractError(
                    "an unavailable release must use UNVALIDATED evidence"
                )
            if may_feed_oav:
                raise ModelInterfaceContractError(
                    "an unavailable release cannot feed OAV screening"
                )
        permitted = _strings(
            self.permitted_claim_wording,
            "permitted_claim_wording",
            require_nonempty=True,
        )
        forbidden = _strings(
            self.forbidden_claim_wording,
            "forbidden_claim_wording",
            require_nonempty=True,
        )
        if set(permitted) & set(forbidden):
            raise ModelInterfaceContractError(
                "permitted and forbidden claim wording must not overlap"
            )

        object.__setattr__(
            self,
            "parameter_set_version",
            parameter_version,
        )
        object.__setattr__(self, "code_commit", code_commit)
        object.__setattr__(
            self,
            "implementation_sha256",
            implementation_sha256,
        )
        object.__setattr__(
            self,
            "parameter_set_sha256",
            parameter_set_sha256,
        )
        object.__setattr__(
            self,
            "coefficient_set_sha256",
            coefficient_set_sha256,
        )
        object.__setattr__(
            self,
            "decomposition_sha256",
            decomposition_sha256,
        )
        object.__setattr__(
            self,
            "training_data_sha256",
            training_data_sha256,
        )
        object.__setattr__(
            self,
            "supported_operations",
            supported_operations,
        )
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "unavailable_reason", unavailable_reason)
        object.__setattr__(self, "evidence_class", evidence_class)
        object.__setattr__(self, "may_feed_oav_screening", may_feed_oav)
        object.__setattr__(self, "permitted_claim_wording", permitted)
        object.__setattr__(self, "forbidden_claim_wording", forbidden)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-model-release-v1",
            "selector": self.selector.to_mapping(),
            "parameter_set_version": self.parameter_set_version,
            "code_commit": self.code_commit,
            "implementation_sha256": self.implementation_sha256,
            "parameter_set_sha256": self.parameter_set_sha256,
            "coefficient_set_sha256": self.coefficient_set_sha256,
            "decomposition_sha256": self.decomposition_sha256,
            "training_data_sha256": self.training_data_sha256,
            "applicability_domain": self.applicability_domain.to_mapping(),
            "supported_operations": [item.value for item in self.supported_operations],
            "availability": self.availability.value,
            "unavailable_reason": self.unavailable_reason,
            "evidence_class": self.evidence_class.value,
            "may_feed_oav_screening": self.may_feed_oav_screening,
            "permitted_claim_wording": list(self.permitted_claim_wording),
            "forbidden_claim_wording": list(self.forbidden_claim_wording),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ModelRelease:
        normalized = _mapping(payload, "model release")
        _exact_keys(
            normalized,
            {
                "schema",
                "selector",
                "parameter_set_version",
                "code_commit",
                "implementation_sha256",
                "parameter_set_sha256",
                "coefficient_set_sha256",
                "decomposition_sha256",
                "training_data_sha256",
                "applicability_domain",
                "supported_operations",
                "availability",
                "unavailable_reason",
                "evidence_class",
                "may_feed_oav_screening",
                "permitted_claim_wording",
                "forbidden_claim_wording",
                "content_sha256",
            },
            "model release",
        )
        if normalized["schema"] != "c3-model-release-v1":
            raise ModelInterfaceContractError("model release schema must be c3-model-release-v1")
        result = cls(
            selector=ModelSelector.from_mapping(_mapping(normalized["selector"], "selector")),
            parameter_set_version=normalized["parameter_set_version"],
            code_commit=normalized["code_commit"],
            implementation_sha256=normalized["implementation_sha256"],
            parameter_set_sha256=normalized["parameter_set_sha256"],
            coefficient_set_sha256=normalized["coefficient_set_sha256"],
            decomposition_sha256=normalized["decomposition_sha256"],
            training_data_sha256=normalized["training_data_sha256"],
            applicability_domain=ApplicabilityDomain.from_mapping(
                _mapping(
                    normalized["applicability_domain"],
                    "applicability_domain",
                )
            ),
            supported_operations=_parsed_enums(
                normalized["supported_operations"],
                ModelOperation,
                "supported_operations",
            ),
            availability=_enum_value(
                ModelAvailability,
                normalized["availability"],
                "availability",
            ),
            unavailable_reason=normalized["unavailable_reason"],
            evidence_class=_enum_value(
                ModelEvidenceClass,
                normalized["evidence_class"],
                "evidence_class",
            ),
            may_feed_oav_screening=normalized["may_feed_oav_screening"],
            permitted_claim_wording=tuple(normalized["permitted_claim_wording"]),
            forbidden_claim_wording=tuple(normalized["forbidden_claim_wording"]),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "model release content_sha256 does not match canonical content"
            )
        return result


__all__ = [
    "ApplicabilityDomain",
    "ApplicabilityState",
    "DomainRange",
    "ModelAvailability",
    "ModelEvidenceClass",
    "ModelFamily",
    "ModelInterfaceContractError",
    "ModelOperation",
    "ModelRelease",
    "ModelResultStatus",
    "ModelSelector",
]
