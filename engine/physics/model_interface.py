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
from types import MappingProxyType
from typing import Any, Protocol, TypeVar, runtime_checkable

from engine.calibration.hashing import stable_json_hash
from engine.physics.matrix_environment import (
    ApplicationEnvironmentKind,
    DeclaredQuantity,
    MatrixAwareModelRequest,
    MatrixStage,
)
from engine.physics.properties import (
    CanonicalScope,
    ThermophysicalProperty,
    UncertaintyDescriptor,
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


@dataclass(frozen=True, slots=True)
class ApplicabilityContext:
    identity_ids: tuple[str, ...]
    chemical_classes: tuple[str, ...]
    functional_groups: tuple[str, ...]
    concentration: DeclaredQuantity | None
    phase_behavior: str | None
    available_properties: tuple[ThermophysicalProperty, ...]
    training_calibration_tags: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identity_ids",
            _strings(self.identity_ids, "identity_ids"),
        )
        object.__setattr__(
            self,
            "chemical_classes",
            _strings(self.chemical_classes, "chemical_classes"),
        )
        object.__setattr__(
            self,
            "functional_groups",
            _strings(self.functional_groups, "functional_groups"),
        )
        if self.concentration is not None and not isinstance(self.concentration, DeclaredQuantity):
            raise ModelInterfaceContractError("concentration must be a DeclaredQuantity or None")
        phase_behavior = self.phase_behavior
        if phase_behavior is not None:
            phase_behavior = _nonblank(phase_behavior, "phase_behavior")
        object.__setattr__(self, "phase_behavior", phase_behavior)
        object.__setattr__(
            self,
            "available_properties",
            _enums(
                self.available_properties,
                ThermophysicalProperty,
                "available_properties",
            ),
        )
        object.__setattr__(
            self,
            "training_calibration_tags",
            _strings(
                self.training_calibration_tags,
                "training_calibration_tags",
            ),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-applicability-context-v1",
            "identity_ids": list(self.identity_ids),
            "chemical_classes": list(self.chemical_classes),
            "functional_groups": list(self.functional_groups),
            "concentration": (
                None if self.concentration is None else self.concentration.to_mapping()
            ),
            "phase_behavior": self.phase_behavior,
            "available_properties": [item.value for item in self.available_properties],
            "training_calibration_tags": list(self.training_calibration_tags),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ApplicabilityContext:
        normalized = _mapping(payload, "applicability context")
        _exact_keys(
            normalized,
            {
                "schema",
                "identity_ids",
                "chemical_classes",
                "functional_groups",
                "concentration",
                "phase_behavior",
                "available_properties",
                "training_calibration_tags",
                "content_sha256",
            },
            "applicability context",
        )
        if normalized["schema"] != "c3-applicability-context-v1":
            raise ModelInterfaceContractError(
                "applicability context schema must be c3-applicability-context-v1"
            )
        raw_concentration = normalized["concentration"]
        result = cls(
            identity_ids=tuple(normalized["identity_ids"]),
            chemical_classes=tuple(normalized["chemical_classes"]),
            functional_groups=tuple(normalized["functional_groups"]),
            concentration=(
                None
                if raw_concentration is None
                else DeclaredQuantity.from_mapping(_mapping(raw_concentration, "concentration"))
            ),
            phase_behavior=normalized["phase_behavior"],
            available_properties=_parsed_enums(
                normalized["available_properties"],
                ThermophysicalProperty,
                "available_properties",
            ),
            training_calibration_tags=tuple(normalized["training_calibration_tags"]),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "applicability context content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ApplicabilityResult:
    state: ApplicabilityState
    domain_sha256: str
    request_sha256: str
    reasons: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    warnings: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        state = _direct_enum(ApplicabilityState, self.state, "state")
        domain_sha256 = _sha256(self.domain_sha256, "domain_sha256")
        request_sha256 = _sha256(self.request_sha256, "request_sha256")
        reasons = _strings(self.reasons, "reasons")
        missing_inputs = _strings(self.missing_inputs, "missing_inputs")
        warnings = _strings(self.warnings, "warnings")
        if state is ApplicabilityState.NEAR_DOMAIN_WITH_WARNING and not warnings:
            raise ModelInterfaceContractError("NEAR_DOMAIN_WITH_WARNING requires a warning")
        if (
            state
            in {
                ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
                ApplicabilityState.MODEL_NOT_VALIDATED,
            }
            and not reasons
        ):
            raise ModelInterfaceContractError(f"{state.value} requires a reason")
        if state is ApplicabilityState.INSUFFICIENT_INPUT and not missing_inputs:
            raise ModelInterfaceContractError("INSUFFICIENT_INPUT requires missing_inputs")
        if (
            state
            in {
                ApplicabilityState.IN_DOMAIN,
                ApplicabilityState.NEAR_DOMAIN_WITH_WARNING,
            }
            and missing_inputs
        ):
            raise ModelInterfaceContractError(f"{state.value} cannot declare missing_inputs")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "domain_sha256", domain_sha256)
        object.__setattr__(self, "request_sha256", request_sha256)
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "missing_inputs", missing_inputs)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-applicability-result-v1",
            "state": self.state.value,
            "domain_sha256": self.domain_sha256,
            "request_sha256": self.request_sha256,
            "reasons": list(self.reasons),
            "missing_inputs": list(self.missing_inputs),
            "warnings": list(self.warnings),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ApplicabilityResult:
        normalized = _mapping(payload, "applicability result")
        _exact_keys(
            normalized,
            {
                "schema",
                "state",
                "domain_sha256",
                "request_sha256",
                "reasons",
                "missing_inputs",
                "warnings",
                "content_sha256",
            },
            "applicability result",
        )
        if normalized["schema"] != "c3-applicability-result-v1":
            raise ModelInterfaceContractError(
                "applicability result schema must be c3-applicability-result-v1"
            )
        result = cls(
            state=_enum_value(
                ApplicabilityState,
                normalized["state"],
                "state",
            ),
            domain_sha256=normalized["domain_sha256"],
            request_sha256=normalized["request_sha256"],
            reasons=tuple(normalized["reasons"]),
            missing_inputs=tuple(normalized["missing_inputs"]),
            warnings=tuple(normalized["warnings"]),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "applicability result content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelInputReference:
    role: str
    input_id: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _nonblank(self.role, "role"))
        object.__setattr__(
            self,
            "input_id",
            _nonblank(self.input_id, "input_id"),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _sha256(self.content_sha256, "content_sha256"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-model-input-reference-v1",
            "role": self.role,
            "input_id": self.input_id,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ModelInputReference:
        normalized = _mapping(payload, "model input reference")
        _exact_keys(
            normalized,
            {"schema", "role", "input_id", "content_sha256"},
            "model input reference",
        )
        if normalized["schema"] != "c3-model-input-reference-v1":
            raise ModelInterfaceContractError(
                "model input reference schema must be c3-model-input-reference-v1"
            )
        return cls(
            role=normalized["role"],
            input_id=normalized["input_id"],
            content_sha256=normalized["content_sha256"],
        )


@dataclass(frozen=True, slots=True)
class VersionedModelRequest:
    request_id: str
    operation: ModelOperation
    requested_model: ModelSelector
    context: MatrixAwareModelRequest
    applicability_context: ApplicabilityContext
    input_references: tuple[ModelInputReference, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _nonblank(self.request_id, "request_id"),
        )
        operation = _direct_enum(ModelOperation, self.operation, "operation")
        if operation in {
            ModelOperation.EVALUATE_APPLICABILITY,
            ModelOperation.COMPARE_MODELS,
        }:
            raise ModelInterfaceContractError(
                "a versioned model request must name an answer-producing operation"
            )
        if not isinstance(self.requested_model, ModelSelector):
            raise ModelInterfaceContractError("requested_model must be a ModelSelector")
        if not isinstance(self.context, MatrixAwareModelRequest):
            raise ModelInterfaceContractError("context must be a MatrixAwareModelRequest")
        if not isinstance(self.applicability_context, ApplicabilityContext):
            raise ModelInterfaceContractError(
                "applicability_context must be an ApplicabilityContext"
            )
        if not isinstance(self.input_references, Sequence):
            raise ModelInterfaceContractError("input_references must be a sequence")
        references = tuple(self.input_references)
        if not references:
            raise ModelInterfaceContractError("input_references must not be empty")
        if any(not isinstance(item, ModelInputReference) for item in references):
            raise ModelInterfaceContractError(
                "input_references must contain ModelInputReference values"
            )
        keys = tuple((item.role, item.input_id) for item in references)
        if len(keys) != len(set(keys)):
            raise ModelInterfaceContractError(
                "input_references contains duplicate role/input_id entries"
            )
        references = tuple(
            sorted(
                references,
                key=lambda item: (
                    item.role.casefold(),
                    item.role,
                    item.input_id.casefold(),
                    item.input_id,
                ),
            )
        )
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "input_references", references)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-versioned-model-request-v1",
            "request_id": self.request_id,
            "operation": self.operation.value,
            "requested_model": self.requested_model.to_mapping(),
            "context": self.context.to_mapping(),
            "applicability_context": self.applicability_context.to_mapping(),
            "input_references": [item.to_mapping() for item in self.input_references],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> VersionedModelRequest:
        normalized = _mapping(payload, "versioned model request")
        _exact_keys(
            normalized,
            {
                "schema",
                "request_id",
                "operation",
                "requested_model",
                "context",
                "applicability_context",
                "input_references",
                "content_sha256",
            },
            "versioned model request",
        )
        if normalized["schema"] != "c3-versioned-model-request-v1":
            raise ModelInterfaceContractError(
                "versioned model request schema must be c3-versioned-model-request-v1"
            )
        raw_references = normalized["input_references"]
        if isinstance(raw_references, (str, bytes)) or not isinstance(raw_references, Sequence):
            raise ModelInterfaceContractError("input_references must be a sequence")
        result = cls(
            request_id=normalized["request_id"],
            operation=_enum_value(
                ModelOperation,
                normalized["operation"],
                "operation",
            ),
            requested_model=ModelSelector.from_mapping(
                _mapping(normalized["requested_model"], "requested_model")
            ),
            context=MatrixAwareModelRequest.from_mapping(
                _mapping(normalized["context"], "context")
            ),
            applicability_context=ApplicabilityContext.from_mapping(
                _mapping(
                    normalized["applicability_context"],
                    "applicability_context",
                )
            ),
            input_references=tuple(
                ModelInputReference.from_mapping(_mapping(item, "input reference"))
                for item in raw_references
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "versioned model request content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelOutput:
    quantity: str
    unit: str
    payload: CanonicalScope
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "quantity",
            _nonblank(self.quantity, "quantity"),
        )
        object.__setattr__(self, "unit", _nonblank(self.unit, "unit"))
        object.__setattr__(self, "payload", _scope(self.payload, "payload"))
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-model-output-v1",
            "quantity": self.quantity,
            "unit": self.unit,
            "payload": self.payload.to_mapping(),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ModelOutput:
        normalized = _mapping(payload, "model output")
        _exact_keys(
            normalized,
            {"schema", "quantity", "unit", "payload", "content_sha256"},
            "model output",
        )
        if normalized["schema"] != "c3-model-output-v1":
            raise ModelInterfaceContractError("model output schema must be c3-model-output-v1")
        result = cls(
            quantity=normalized["quantity"],
            unit=normalized["unit"],
            payload=CanonicalScope.from_mapping(_mapping(normalized["payload"], "payload")),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "model output content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class FallbackDisclosure:
    requested_model: ModelSelector
    reason_unavailable: str
    fallback_model: ModelSelector
    authority_downgrade: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.requested_model, ModelSelector):
            raise ModelInterfaceContractError("requested_model must be a ModelSelector")
        if not isinstance(self.fallback_model, ModelSelector):
            raise ModelInterfaceContractError("fallback_model must be a ModelSelector")
        if self.requested_model == self.fallback_model:
            raise ModelInterfaceContractError("requested and fallback model selectors must differ")
        object.__setattr__(
            self,
            "reason_unavailable",
            _nonblank(self.reason_unavailable, "reason_unavailable"),
        )
        object.__setattr__(
            self,
            "authority_downgrade",
            _nonblank(self.authority_downgrade, "authority_downgrade"),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-fallback-disclosure-v1",
            "requested_model": self.requested_model.to_mapping(),
            "reason_unavailable": self.reason_unavailable,
            "fallback_model": self.fallback_model.to_mapping(),
            "authority_downgrade": self.authority_downgrade,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> FallbackDisclosure:
        normalized = _mapping(payload, "fallback disclosure")
        _exact_keys(
            normalized,
            {
                "schema",
                "requested_model",
                "reason_unavailable",
                "fallback_model",
                "authority_downgrade",
                "content_sha256",
            },
            "fallback disclosure",
        )
        if normalized["schema"] != "c3-fallback-disclosure-v1":
            raise ModelInterfaceContractError(
                "fallback disclosure schema must be c3-fallback-disclosure-v1"
            )
        result = cls(
            requested_model=ModelSelector.from_mapping(
                _mapping(normalized["requested_model"], "requested_model")
            ),
            reason_unavailable=normalized["reason_unavailable"],
            fallback_model=ModelSelector.from_mapping(
                _mapping(normalized["fallback_model"], "fallback_model")
            ),
            authority_downgrade=normalized["authority_downgrade"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "fallback disclosure content_sha256 does not match canonical content"
            )
        return result


def _uncertainty_mapping(value: UncertaintyDescriptor) -> dict[str, Any]:
    if not isinstance(value, UncertaintyDescriptor):
        raise ModelInterfaceContractError("uncertainty must be an UncertaintyDescriptor")
    return value.payload.to_mapping()


@dataclass(frozen=True, slots=True)
class VersionedModelResult:
    status: ModelResultStatus
    operation: ModelOperation
    requested_model: ModelSelector
    bound_model: ModelRelease
    request: VersionedModelRequest
    output: ModelOutput | None
    uncertainty: UncertaintyDescriptor
    applicability: ApplicabilityResult
    missing_inputs: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_class: ModelEvidenceClass
    may_feed_oav_screening: bool
    permitted_claim_wording: tuple[str, ...]
    forbidden_claim_wording: tuple[str, ...]
    fallback: FallbackDisclosure | None
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        status = _direct_enum(ModelResultStatus, self.status, "status")
        operation = _direct_enum(ModelOperation, self.operation, "operation")
        if not isinstance(self.requested_model, ModelSelector):
            raise ModelInterfaceContractError("requested_model must be a ModelSelector")
        if not isinstance(self.bound_model, ModelRelease):
            raise ModelInterfaceContractError("bound_model must be a ModelRelease")
        if not isinstance(self.request, VersionedModelRequest):
            raise ModelInterfaceContractError("request must be a VersionedModelRequest")
        if operation is not self.request.operation:
            raise ModelInterfaceContractError("result operation must match the request operation")
        if self.requested_model != self.request.requested_model:
            raise ModelInterfaceContractError("result requested_model must match the request")
        if self.output is not None and not isinstance(self.output, ModelOutput):
            raise ModelInterfaceContractError("output must be a ModelOutput or None")
        uncertainty_mapping = _uncertainty_mapping(self.uncertainty)
        if not isinstance(self.applicability, ApplicabilityResult):
            raise ModelInterfaceContractError("applicability must be an ApplicabilityResult")
        if self.applicability.request_sha256 != self.request.content_sha256:
            raise ModelInterfaceContractError(
                "applicability request hash must match the result request"
            )
        if self.applicability.domain_sha256 != self.bound_model.applicability_domain.content_sha256:
            raise ModelInterfaceContractError(
                "applicability domain hash must match the bound model domain"
            )
        missing_inputs = _strings(self.missing_inputs, "missing_inputs")
        warnings = _strings(self.warnings, "warnings")
        if missing_inputs != self.applicability.missing_inputs:
            raise ModelInterfaceContractError(
                "result missing_inputs must match applicability missing_inputs"
            )
        if not set(self.applicability.warnings).issubset(warnings):
            raise ModelInterfaceContractError("result warnings must include applicability warnings")
        evidence_class = _direct_enum(
            ModelEvidenceClass,
            self.evidence_class,
            "evidence_class",
        )
        if evidence_class is not self.bound_model.evidence_class:
            raise ModelInterfaceContractError("result evidence_class must match the bound model")
        may_feed_oav = _boolean(
            self.may_feed_oav_screening,
            "may_feed_oav_screening",
        )
        if may_feed_oav and not self.bound_model.may_feed_oav_screening:
            raise ModelInterfaceContractError("result cannot exceed the bound model OAV authority")
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
        if permitted != self.bound_model.permitted_claim_wording:
            raise ModelInterfaceContractError("permitted claim wording must match the bound model")
        if forbidden != self.bound_model.forbidden_claim_wording:
            raise ModelInterfaceContractError("forbidden claim wording must match the bound model")
        if self.fallback is not None and not isinstance(self.fallback, FallbackDisclosure):
            raise ModelInterfaceContractError("fallback must be a FallbackDisclosure or None")
        if self.bound_model.selector == self.requested_model:
            if self.fallback is not None:
                raise ModelInterfaceContractError(
                    "fallback must be absent when the requested model is bound"
                )
        else:
            if self.fallback is None:
                raise ModelInterfaceContractError(
                    "a changed bound model requires fallback disclosure"
                )
            if self.fallback.requested_model != self.requested_model:
                raise ModelInterfaceContractError(
                    "fallback requested model must match the result requested model"
                )
            if self.fallback.fallback_model != self.bound_model.selector:
                raise ModelInterfaceContractError(
                    "fallback model must match the bound model selector"
                )
        noncomputable_states = {
            ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
            ApplicabilityState.INSUFFICIENT_INPUT,
            ApplicabilityState.MODEL_NOT_VALIDATED,
        }
        if status is ModelResultStatus.COMPUTED:
            if self.output is None:
                raise ModelInterfaceContractError("a COMPUTED result requires output")
            if self.applicability.state in noncomputable_states:
                raise ModelInterfaceContractError(
                    f"a COMPUTED result cannot use {self.applicability.state.value}"
                )
            if self.bound_model.availability is ModelAvailability.UNAVAILABLE:
                raise ModelInterfaceContractError(
                    "a COMPUTED result requires an available bound model"
                )
        else:
            if self.output is not None:
                raise ModelInterfaceContractError("an ABSTAINED result must not contain output")
            if may_feed_oav:
                raise ModelInterfaceContractError("an ABSTAINED result cannot feed OAV screening")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "missing_inputs", missing_inputs)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "evidence_class", evidence_class)
        object.__setattr__(self, "may_feed_oav_screening", may_feed_oav)
        object.__setattr__(self, "permitted_claim_wording", permitted)
        object.__setattr__(self, "forbidden_claim_wording", forbidden)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping(uncertainty_mapping)),
        )

    def _content_mapping(
        self,
        uncertainty_mapping: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        return {
            "schema": "c3-versioned-model-result-v1",
            "status": self.status.value,
            "operation": self.operation.value,
            "requested_model": self.requested_model.to_mapping(),
            "bound_model": self.bound_model.to_mapping(),
            "request": self.request.to_mapping(),
            "output": None if self.output is None else self.output.to_mapping(),
            "uncertainty": (
                _uncertainty_mapping(self.uncertainty)
                if uncertainty_mapping is None
                else dict(uncertainty_mapping)
            ),
            "applicability": self.applicability.to_mapping(),
            "missing_inputs": list(self.missing_inputs),
            "warnings": list(self.warnings),
            "evidence_class": self.evidence_class.value,
            "may_feed_oav_screening": self.may_feed_oav_screening,
            "permitted_claim_wording": list(self.permitted_claim_wording),
            "forbidden_claim_wording": list(self.forbidden_claim_wording),
            "fallback": (None if self.fallback is None else self.fallback.to_mapping()),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> VersionedModelResult:
        normalized = _mapping(payload, "versioned model result")
        _exact_keys(
            normalized,
            {
                "schema",
                "status",
                "operation",
                "requested_model",
                "bound_model",
                "request",
                "output",
                "uncertainty",
                "applicability",
                "missing_inputs",
                "warnings",
                "evidence_class",
                "may_feed_oav_screening",
                "permitted_claim_wording",
                "forbidden_claim_wording",
                "fallback",
                "content_sha256",
            },
            "versioned model result",
        )
        if normalized["schema"] != "c3-versioned-model-result-v1":
            raise ModelInterfaceContractError(
                "versioned model result schema must be c3-versioned-model-result-v1"
            )
        raw_output = normalized["output"]
        raw_fallback = normalized["fallback"]
        result = cls(
            status=_enum_value(
                ModelResultStatus,
                normalized["status"],
                "status",
            ),
            operation=_enum_value(
                ModelOperation,
                normalized["operation"],
                "operation",
            ),
            requested_model=ModelSelector.from_mapping(
                _mapping(normalized["requested_model"], "requested_model")
            ),
            bound_model=ModelRelease.from_mapping(
                _mapping(normalized["bound_model"], "bound_model")
            ),
            request=VersionedModelRequest.from_mapping(_mapping(normalized["request"], "request")),
            output=(
                None
                if raw_output is None
                else ModelOutput.from_mapping(_mapping(raw_output, "output"))
            ),
            uncertainty=UncertaintyDescriptor.from_mapping(
                _mapping(normalized["uncertainty"], "uncertainty")
            ),
            applicability=ApplicabilityResult.from_mapping(
                _mapping(normalized["applicability"], "applicability")
            ),
            missing_inputs=tuple(normalized["missing_inputs"]),
            warnings=tuple(normalized["warnings"]),
            evidence_class=_enum_value(
                ModelEvidenceClass,
                normalized["evidence_class"],
                "evidence_class",
            ),
            may_feed_oav_screening=normalized["may_feed_oav_screening"],
            permitted_claim_wording=tuple(normalized["permitted_claim_wording"]),
            forbidden_claim_wording=tuple(normalized["forbidden_claim_wording"]),
            fallback=(
                None
                if raw_fallback is None
                else FallbackDisclosure.from_mapping(_mapping(raw_fallback, "fallback"))
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "versioned model result content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelComputation:
    """Typed adapter output with no routing or scientific authority."""

    output: ModelOutput
    uncertainty: UncertaintyDescriptor
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.output, ModelOutput):
            raise ModelInterfaceContractError("output must be a ModelOutput")
        _uncertainty_mapping(self.uncertainty)
        object.__setattr__(
            self,
            "warnings",
            _strings(self.warnings, "warnings"),
        )


@runtime_checkable
class VersionedModelAdapter(Protocol):
    """Runtime boundary for one exact immutable model release."""

    @property
    def release(self) -> ModelRelease: ...

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult: ...

    def compute(
        self,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> ModelComputation: ...


@dataclass(frozen=True, slots=True)
class ModelComparisonResult:
    comparison_id: str
    compared_operation: ModelOperation
    results: tuple[VersionedModelResult, ...]
    operation: ModelOperation = field(
        init=False,
        default=ModelOperation.COMPARE_MODELS,
    )
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        comparison_id = _nonblank(self.comparison_id, "comparison_id")
        compared_operation = _direct_enum(
            ModelOperation,
            self.compared_operation,
            "compared_operation",
        )
        if compared_operation not in _COMPUTATION_OPERATIONS:
            raise ModelInterfaceContractError(
                "compared_operation must be an answer-producing operation"
            )
        if not isinstance(self.results, Sequence):
            raise ModelInterfaceContractError("results must be a sequence")
        results = tuple(self.results)
        if len(results) < 2:
            raise ModelInterfaceContractError("model comparison requires at least two results")
        if any(not isinstance(item, VersionedModelResult) for item in results):
            raise ModelInterfaceContractError("results must contain VersionedModelResult values")
        if any(item.operation is not compared_operation for item in results):
            raise ModelInterfaceContractError(
                "model comparison results must use the same operation"
            )
        if any(
            item.fallback is not None or item.requested_model != item.bound_model.selector
            for item in results
        ):
            raise ModelInterfaceContractError(
                "model comparison requires explicit exact model bindings"
            )
        selectors = tuple(item.requested_model for item in results)
        if len(selectors) != len(set(selectors)):
            raise ModelInterfaceContractError("model comparison requires unique explicit selectors")
        context_hashes = {item.request.context.content_sha256 for item in results}
        if len(context_hashes) != 1:
            raise ModelInterfaceContractError(
                "model comparison results must share the same C2 context hash"
            )
        results = tuple(
            sorted(
                results,
                key=lambda item: (
                    item.requested_model.family.value,
                    item.requested_model.model_version.casefold(),
                    item.requested_model.model_version,
                    item.requested_model.content_sha256,
                ),
            )
        )
        object.__setattr__(self, "comparison_id", comparison_id)
        object.__setattr__(self, "compared_operation", compared_operation)
        object.__setattr__(self, "results", results)
        object.__setattr__(self, "operation", ModelOperation.COMPARE_MODELS)
        object.__setattr__(
            self,
            "content_sha256",
            _uncertainty_free_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c3-model-comparison-result-v1",
            "comparison_id": self.comparison_id,
            "operation": self.operation.value,
            "compared_operation": self.compared_operation.value,
            "results": [item.to_mapping() for item in self.results],
        }

    def to_mapping(self) -> dict[str, object]:
        return {
            **self._content_mapping(),
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> ModelComparisonResult:
        normalized = _mapping(payload, "model comparison result")
        _exact_keys(
            normalized,
            {
                "schema",
                "comparison_id",
                "operation",
                "compared_operation",
                "results",
                "content_sha256",
            },
            "model comparison result",
        )
        if normalized["schema"] != "c3-model-comparison-result-v1":
            raise ModelInterfaceContractError(
                "model comparison result schema must be c3-model-comparison-result-v1"
            )
        if (
            _enum_value(
                ModelOperation,
                normalized["operation"],
                "operation",
            )
            is not ModelOperation.COMPARE_MODELS
        ):
            raise ModelInterfaceContractError(
                "model comparison result operation must be compare_models"
            )
        raw_results = normalized["results"]
        if isinstance(raw_results, (str, bytes)) or not isinstance(
            raw_results,
            Sequence,
        ):
            raise ModelInterfaceContractError("results must be a sequence")
        result = cls(
            comparison_id=normalized["comparison_id"],
            compared_operation=_enum_value(
                ModelOperation,
                normalized["compared_operation"],
                "compared_operation",
            ),
            results=tuple(
                VersionedModelResult.from_mapping(_mapping(item, "comparison result"))
                for item in raw_results
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise ModelInterfaceContractError(
                "model comparison result content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class _RegisteredAdapter:
    adapter: VersionedModelAdapter
    release: ModelRelease


class VersionedModelRouter:
    """Exact-selector router with mandatory applicability abstention."""

    __slots__ = ("_registrations",)

    _registrations: Mapping[ModelSelector, _RegisteredAdapter]

    def __init__(
        self,
        adapters: Sequence[VersionedModelAdapter],
    ) -> None:
        if isinstance(adapters, (str, bytes)) or not isinstance(
            adapters,
            Sequence,
        ):
            raise ModelInterfaceContractError("adapters must be a sequence")
        if not adapters:
            raise ModelInterfaceContractError("adapters must not be empty")
        registrations: dict[ModelSelector, _RegisteredAdapter] = {}
        for adapter in adapters:
            if not isinstance(adapter, VersionedModelAdapter):
                raise ModelInterfaceContractError("adapters must implement VersionedModelAdapter")
            model_release = adapter.release
            if not isinstance(model_release, ModelRelease):
                raise ModelInterfaceContractError("adapter release must be a ModelRelease")
            if model_release.selector in registrations:
                raise ModelInterfaceContractError(
                    "duplicate model selector registration is forbidden"
                )
            registrations[model_release.selector] = _RegisteredAdapter(
                adapter=adapter,
                release=model_release,
            )
        self._registrations = MappingProxyType(registrations)

    @staticmethod
    def _request(value: object) -> VersionedModelRequest:
        if not isinstance(value, VersionedModelRequest):
            raise ModelInterfaceContractError("request must be a VersionedModelRequest")
        return value

    def _resolve(
        self,
        selector: ModelSelector,
    ) -> _RegisteredAdapter:
        registration = self._registrations.get(selector)
        if registration is None:
            raise ModelInterfaceContractError("requested model selector is not registered")
        if registration.adapter.release != registration.release:
            raise ModelInterfaceContractError("adapter release drift detected after registration")
        return registration

    @staticmethod
    def _ensure_supported(
        model_release: ModelRelease,
        operation: ModelOperation,
    ) -> None:
        if operation not in model_release.supported_operations:
            raise ModelInterfaceContractError(f"model release does not support {operation.value}")

    @staticmethod
    def _not_validated(
        model_release: ModelRelease,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        return ApplicabilityResult(
            state=ApplicabilityState.MODEL_NOT_VALIDATED,
            domain_sha256=model_release.applicability_domain.content_sha256,
            request_sha256=request.content_sha256,
            reasons=(model_release.unavailable_reason or "model release is unavailable",),
            missing_inputs=(),
            warnings=(),
        )

    @staticmethod
    def _validate_applicability_binding(
        applicability: object,
        model_release: ModelRelease,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        if not isinstance(applicability, ApplicabilityResult):
            raise ModelInterfaceContractError(
                "adapter applicability must be an ApplicabilityResult"
            )
        if applicability.request_sha256 != request.content_sha256:
            raise ModelInterfaceContractError(
                "adapter applicability request hash does not match the request"
            )
        if applicability.domain_sha256 != model_release.applicability_domain.content_sha256:
            raise ModelInterfaceContractError(
                "adapter applicability domain hash does not match the release"
            )
        return applicability

    def _evaluate_registered(
        self,
        registration: _RegisteredAdapter,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        model_release = registration.release
        if model_release.availability is ModelAvailability.UNAVAILABLE:
            return self._not_validated(model_release, request)
        self._ensure_supported(model_release, request.operation)
        return self._validate_applicability_binding(
            registration.adapter.evaluate_applicability(request),
            model_release,
            request,
        )

    @staticmethod
    def _abstained_result(
        model_release: ModelRelease,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> VersionedModelResult:
        return VersionedModelResult(
            status=ModelResultStatus.ABSTAINED,
            operation=request.operation,
            requested_model=request.requested_model,
            bound_model=model_release,
            request=request,
            output=None,
            uncertainty=UncertaintyDescriptor.unknown(
                f"computation abstained: {applicability.state.value}"
            ),
            applicability=applicability,
            missing_inputs=applicability.missing_inputs,
            warnings=applicability.warnings,
            evidence_class=model_release.evidence_class,
            may_feed_oav_screening=False,
            permitted_claim_wording=model_release.permitted_claim_wording,
            forbidden_claim_wording=model_release.forbidden_claim_wording,
            fallback=None,
        )

    @staticmethod
    def _computed_result(
        model_release: ModelRelease,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
        computation: ModelComputation,
    ) -> VersionedModelResult:
        warnings = tuple(
            sorted(
                set(applicability.warnings) | set(computation.warnings),
                key=lambda item: (item.casefold(), item),
            )
        )
        return VersionedModelResult(
            status=ModelResultStatus.COMPUTED,
            operation=request.operation,
            requested_model=request.requested_model,
            bound_model=model_release,
            request=request,
            output=computation.output,
            uncertainty=computation.uncertainty,
            applicability=applicability,
            missing_inputs=applicability.missing_inputs,
            warnings=warnings,
            evidence_class=model_release.evidence_class,
            may_feed_oav_screening=model_release.may_feed_oav_screening,
            permitted_claim_wording=model_release.permitted_claim_wording,
            forbidden_claim_wording=model_release.forbidden_claim_wording,
            fallback=None,
        )

    def _execute(
        self,
        expected_operation: ModelOperation,
        request: VersionedModelRequest,
    ) -> VersionedModelResult:
        request = self._request(request)
        if request.operation is not expected_operation:
            raise ModelInterfaceContractError(
                f"request operation must be {expected_operation.value}"
            )
        registration = self._resolve(request.requested_model)
        applicability = self._evaluate_registered(registration, request)
        if applicability.state in {
            ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
            ApplicabilityState.INSUFFICIENT_INPUT,
            ApplicabilityState.MODEL_NOT_VALIDATED,
        }:
            return self._abstained_result(
                registration.release,
                request,
                applicability,
            )
        computation = registration.adapter.compute(request, applicability)
        if not isinstance(computation, ModelComputation):
            raise ModelInterfaceContractError("adapter compute must return a ModelComputation")
        return self._computed_result(
            registration.release,
            request,
            applicability,
            computation,
        )

    def predict_equilibrium_headspace(
        self,
        request: VersionedModelRequest,
    ) -> VersionedModelResult:
        return self._execute(
            ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
            request,
        )

    def predict_dynamic_release(
        self,
        request: VersionedModelRequest,
    ) -> VersionedModelResult:
        return self._execute(
            ModelOperation.PREDICT_DYNAMIC_RELEASE,
            request,
        )

    def estimate_partition_coefficient(
        self,
        request: VersionedModelRequest,
    ) -> VersionedModelResult:
        return self._execute(
            ModelOperation.ESTIMATE_PARTITION_COEFFICIENT,
            request,
        )

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        request = self._request(request)
        registration = self._resolve(request.requested_model)
        return self._evaluate_registered(registration, request)

    def propagate_uncertainty(
        self,
        request: VersionedModelRequest,
    ) -> VersionedModelResult:
        return self._execute(
            ModelOperation.PROPAGATE_UNCERTAINTY,
            request,
        )

    def compare_models(
        self,
        comparison_id: str,
        results: Sequence[VersionedModelResult],
    ) -> ModelComparisonResult:
        return ModelComparisonResult(
            comparison_id=comparison_id,
            compared_operation=(
                results[0].operation
                if results and isinstance(results[0], VersionedModelResult)
                else ModelOperation.COMPARE_MODELS
            ),
            results=tuple(results),
        )


__all__ = [
    "ApplicabilityContext",
    "ApplicabilityDomain",
    "ApplicabilityResult",
    "ApplicabilityState",
    "DomainRange",
    "FallbackDisclosure",
    "ModelAvailability",
    "ModelComparisonResult",
    "ModelComputation",
    "ModelEvidenceClass",
    "ModelFamily",
    "ModelInputReference",
    "ModelInterfaceContractError",
    "ModelOperation",
    "ModelOutput",
    "ModelRelease",
    "ModelResultStatus",
    "ModelSelector",
    "VersionedModelRequest",
    "VersionedModelResult",
    "VersionedModelAdapter",
    "VersionedModelRouter",
]
