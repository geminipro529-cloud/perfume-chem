"""Pure Build B assertion adapter and fail-closed C1 property selector."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.physics.properties import (
    CanonicalScope,
    ClaimGrade,
    PropertyConditions,
    PropertyDatum,
    PropertyIdentity,
    SelectionStatus,
    SourceReference,
    ThermophysicalContractError,
    ThermophysicalProperty,
    UncertaintyDescriptor,
    UncertaintyKind,
    _exact_keys,
    _mapping,
    _nonblank,
)
from engine.physics.vapor_pressure import (
    ExtrapolationPolicy,
    VaporPressureRepresentation,
)


class SelectionKind(str, Enum):
    OBSERVATION = "OBSERVATION"
    MODEL = "MODEL"
    NONE = "NONE"


class InterpolationState(str, Enum):
    EXACT = "EXACT"
    INTERPOLATED = "INTERPOLATED"
    EXTRAPOLATED = "EXTRAPOLATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AuthorityState(str, Enum):
    AUTHORIZED_FOR_SCOPED_PROPERTY = "AUTHORIZED_FOR_SCOPED_PROPERTY"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    WITHHELD_CONFLICT = "WITHHELD_CONFLICT"
    WITHHELD_UNKNOWN = "WITHHELD_UNKNOWN"


class MissingDataReason(str, Enum):
    ASSERTION_ABSENT = "ASSERTION_ABSENT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    PROPERTY_MISMATCH = "PROPERTY_MISMATCH"
    CONDITIONS_MISMATCH = "CONDITIONS_MISMATCH"
    NO_SELECTION = "NO_SELECTION"
    WITHHELD_AUTHORITY = "WITHHELD_AUTHORITY"
    ADVISORY_NOT_ALLOWED = "ADVISORY_NOT_ALLOWED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SELECTED_OBSERVATION_MISSING = "SELECTED_OBSERVATION_MISSING"
    SOURCE_MISSING = "SOURCE_MISSING"
    UNIT_MISSING = "UNIT_MISSING"
    UNSUPPORTED_MODEL_SCHEMA = "UNSUPPORTED_MODEL_SCHEMA"
    INTERPOLATION_UNCERTAINTY_MISSING = (
        "INTERPOLATION_UNCERTAINTY_MISSING"
    )
    EXTRAPOLATION_FORBIDDEN = "EXTRAPOLATION_FORBIDDEN"
    MODEL_OUTSIDE_VALID_RANGE = "MODEL_OUTSIDE_VALID_RANGE"


def _enum_value(enum_type, value: object, field_name: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ThermophysicalContractError(
            f"{field_name} is not supported"
        ) from exc


def _content_sha256(value: object, field_name: str) -> str:
    normalized = _nonblank(value, field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ThermophysicalContractError(
            f"{field_name} must be a 64-character hexadecimal SHA-256"
        )
    return normalized


def _closed_uncertainty(value: object) -> UncertaintyDescriptor | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("schema") != "c1-uncertainty-v1":
        return None
    try:
        return UncertaintyDescriptor.from_mapping(value)
    except ThermophysicalContractError:
        return None


@dataclass(frozen=True, slots=True)
class SelectedPropertyAssertion:
    """Persistence-neutral snapshot of one explicit B2 selected assertion."""

    assertion_id: str
    requested_identity: PropertyIdentity
    property_type: ThermophysicalProperty
    requested_conditions: PropertyConditions
    selection_policy_version: str
    selection_kind: SelectionKind
    selected_observation_id: str | None
    candidate_observation_ids: tuple[str, ...]
    observation_identity: PropertyIdentity | None
    observation_conditions: PropertyConditions | None
    observation_property: ThermophysicalProperty | None
    datum: PropertyDatum | None
    source: SourceReference | None
    model: VaporPressureRepresentation | None
    adaptation_missing_reason: MissingDataReason | None
    interpolation_state: InterpolationState
    uncertainty: UncertaintyDescriptor
    applicability: CanonicalScope
    authority_state: AuthorityState
    permitted_claim_wording: str
    conflict_visible: bool
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assertion_id",
            _nonblank(self.assertion_id, "assertion id"),
        )
        object.__setattr__(
            self,
            "selection_policy_version",
            _nonblank(
                self.selection_policy_version, "selection_policy_version"
            ),
        )
        object.__setattr__(
            self,
            "permitted_claim_wording",
            _nonblank(
                self.permitted_claim_wording, "permitted_claim_wording"
            ),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _content_sha256(self.content_sha256, "assertion content_sha256"),
        )


@dataclass(frozen=True, slots=True)
class PropertyRequest:
    identity: PropertyIdentity
    property_type: ThermophysicalProperty
    conditions: PropertyConditions
    claim_grade: ClaimGrade
    allow_advisory: bool = False
    allow_extrapolation: bool = False
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(
                {
                    "schema": "c1-property-request-v1",
                    "identity": self.identity.to_mapping(),
                    "property_type": self.property_type.value,
                    "conditions": self.conditions.to_mapping(),
                    "claim_grade": self.claim_grade.value,
                    "allow_advisory": self.allow_advisory,
                    "allow_extrapolation": self.allow_extrapolation,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class PropertySelectionResult:
    status: SelectionStatus
    datum: PropertyDatum | None
    model: VaporPressureRepresentation | None
    canonical_unit: str | None
    source: SourceReference | None
    conditions: PropertyConditions
    uncertainty: UncertaintyDescriptor
    interpolation_state: InterpolationState | None
    applicability: CanonicalScope
    authority_state: AuthorityState | None
    missing_reason: MissingDataReason | None
    warnings: tuple[str, ...]
    request_sha256: str
    assertion_sha256: str | None


def _observation_conditions(observation: Mapping[str, Any]) -> PropertyConditions:
    names = (
        "temperature_k",
        "pressure_pa",
        "relative_humidity_percent",
        "matrix",
        "phase",
        "purity_fraction",
    )
    return PropertyConditions.from_mapping(
        {name: observation[name] for name in names if observation.get(name) is not None}
    )


def _candidate_ids(candidates: list[dict[str, Any]]) -> tuple[str, ...]:
    identifiers: list[str] = []
    for candidate in candidates:
        observation = _mapping(candidate.get("observation"), "candidate observation")
        identifiers.append(_nonblank(observation.get("id"), "observation id"))
    if len(identifiers) != len(set(identifiers)):
        raise ThermophysicalContractError(
            "B2 reconstruction candidate observation ids must be unique"
        )
    return tuple(identifiers)


def selected_assertion_from_b2_reconstruction(
    payload: Mapping[str, Any],
) -> SelectedPropertyAssertion | None:
    """Adapt the closed B2 reconstruction schema without querying persistence."""

    reconstruction = _mapping(payload, "B2 reconstruction top-level")
    _exact_keys(
        reconstruction,
        {"schema", "assertion", "candidates", "conflict", "complete"},
        "B2 reconstruction top-level",
    )
    if reconstruction["schema"] != "lab-selected-assertion-reconstruction-v1":
        raise ThermophysicalContractError(
            "B2 reconstruction schema is not supported"
        )
    if reconstruction["assertion"] is None:
        return None

    assertion = _mapping(reconstruction["assertion"], "B2 assertion")
    _exact_keys(
        assertion,
        {
            "id",
            "requested_identity",
            "requested_property_type",
            "requested_conditions",
            "selection_policy_version",
            "selection_kind",
            "selected_observation_id",
            "selected_model",
            "interpolation_state",
            "propagated_uncertainty",
            "applicability",
            "authority_state",
            "permitted_claim_wording",
            "content_sha256",
        },
        "B2 assertion",
    )
    raw_candidates = reconstruction["candidates"]
    if not isinstance(raw_candidates, list):
        raise ThermophysicalContractError(
            "B2 reconstruction candidates must be a list"
        )
    candidates = [
        _mapping(candidate, "B2 candidate") for candidate in raw_candidates
    ]
    for candidate in candidates:
        _exact_keys(
            candidate,
            {"observation", "decision", "rationale", "derivation"},
            "B2 candidate",
        )
    candidate_observation_ids = _candidate_ids(candidates)

    requested_identity = PropertyIdentity.from_mapping(
        _mapping(assertion["requested_identity"], "requested_identity")
    )
    property_type = _enum_value(
        ThermophysicalProperty,
        assertion["requested_property_type"],
        "requested_property_type",
    )
    requested_conditions = PropertyConditions.from_mapping(
        _mapping(assertion["requested_conditions"], "requested_conditions")
    )
    selection_kind = _enum_value(
        SelectionKind, assertion["selection_kind"], "selection_kind"
    )
    interpolation_state = _enum_value(
        InterpolationState,
        assertion["interpolation_state"],
        "interpolation_state",
    )
    authority_state = _enum_value(
        AuthorityState, assertion["authority_state"], "authority_state"
    )
    applicability = CanonicalScope.from_mapping(
        _mapping(assertion["applicability"], "applicability")
    )
    selected_observation_id = assertion["selected_observation_id"]
    if selected_observation_id is not None:
        selected_observation_id = _nonblank(
            selected_observation_id, "selected_observation_id"
        )
    selected_model_payload = assertion["selected_model"]
    valid_selection_shape = (
        selection_kind is SelectionKind.OBSERVATION
        and selected_observation_id is not None
        and selected_model_payload is None
    ) or (
        selection_kind is SelectionKind.MODEL
        and selected_observation_id is None
        and isinstance(selected_model_payload, Mapping)
    ) or (
        selection_kind is SelectionKind.NONE
        and selected_observation_id is None
        and selected_model_payload is None
    )
    if not valid_selection_shape:
        raise ThermophysicalContractError(
            "B2 assertion selection shape is inconsistent"
        )

    observation_identity = None
    observation_conditions = None
    observation_property = None
    datum = None
    source = None
    model = None
    adaptation_missing_reason = None
    uncertainty = UncertaintyDescriptor.unknown(
        "selected assertion has no explicit uncertainty"
    )

    if selection_kind is SelectionKind.OBSERVATION:
        selected_candidate = next(
            (
                candidate
                for candidate in candidates
                if _mapping(
                    candidate["observation"], "candidate observation"
                ).get("id")
                == selected_observation_id
            ),
            None,
        )
        if selected_candidate is None or selected_candidate["decision"] != "INCLUDE":
            adaptation_missing_reason = (
                MissingDataReason.SELECTED_OBSERVATION_MISSING
            )
        else:
            observation = _mapping(
                selected_candidate["observation"], "selected observation"
            )
            observation_identity = PropertyIdentity.from_mapping(
                {
                    "identity_scope": observation.get("identity_scope"),
                    "subject_identity": _mapping(
                        observation.get("subject_identity"),
                        "observation subject_identity",
                    ),
                }
            )
            observation_property = _enum_value(
                ThermophysicalProperty,
                observation.get("property_type"),
                "observation property_type",
            )
            observation_conditions = _observation_conditions(observation)
            canonical_unit = observation.get("canonical_unit")
            if not isinstance(canonical_unit, str) or not canonical_unit.strip():
                adaptation_missing_reason = MissingDataReason.UNIT_MISSING
            else:
                try:
                    datum = PropertyDatum.from_b2(observation)
                except ThermophysicalContractError:
                    adaptation_missing_reason = MissingDataReason.UNIT_MISSING
            if adaptation_missing_reason is None:
                try:
                    source = SourceReference.from_b2_observation(observation)
                except ThermophysicalContractError:
                    adaptation_missing_reason = MissingDataReason.SOURCE_MISSING
            derivation = _mapping(
                selected_candidate["derivation"], "selected derivation"
            )
            if (
                adaptation_missing_reason is None
                and (
                    reconstruction["complete"] is not True
                    or derivation.get("complete") is not True
                )
            ):
                adaptation_missing_reason = MissingDataReason.SOURCE_MISSING

            propagated = _closed_uncertainty(
                assertion["propagated_uncertainty"]
            )
            if interpolation_state is InterpolationState.EXACT:
                standard_uncertainty = observation.get("standard_uncertainty")
                if standard_uncertainty is not None and datum is not None:
                    try:
                        uncertainty = UncertaintyDescriptor.from_mapping(
                            {
                                "schema": "c1-uncertainty-v1",
                                "kind": "STANDARD_UNCERTAINTY",
                                "value": standard_uncertainty,
                                "unit": datum.canonical_unit,
                            }
                        )
                    except ThermophysicalContractError:
                        uncertainty = UncertaintyDescriptor.unknown(
                            "selected observation uncertainty is malformed"
                        )
                elif propagated is not None:
                    uncertainty = propagated
            elif propagated is not None:
                uncertainty = propagated

    elif selection_kind is SelectionKind.MODEL:
        selected_model = selected_model_payload
        if (
            property_type is not ThermophysicalProperty.VAPOR_PRESSURE
            or not isinstance(selected_model, Mapping)
            or selected_model.get("schema")
            != "c1-vapor-pressure-representation-v1"
        ):
            adaptation_missing_reason = MissingDataReason.UNSUPPORTED_MODEL_SCHEMA
        else:
            try:
                model = VaporPressureRepresentation.from_mapping(selected_model)
            except ThermophysicalContractError:
                adaptation_missing_reason = (
                    MissingDataReason.UNSUPPORTED_MODEL_SCHEMA
                )
            if model is not None:
                source = model.source
                propagated = _closed_uncertainty(
                    assertion["propagated_uncertainty"]
                )
                if propagated is not None:
                    uncertainty = propagated
                elif interpolation_state is InterpolationState.EXACT:
                    uncertainty = model.uncertainty

    return SelectedPropertyAssertion(
        assertion_id=assertion["id"],
        requested_identity=requested_identity,
        property_type=property_type,
        requested_conditions=requested_conditions,
        selection_policy_version=assertion["selection_policy_version"],
        selection_kind=selection_kind,
        selected_observation_id=selected_observation_id,
        candidate_observation_ids=candidate_observation_ids,
        observation_identity=observation_identity,
        observation_conditions=observation_conditions,
        observation_property=observation_property,
        datum=datum,
        source=source,
        model=model,
        adaptation_missing_reason=adaptation_missing_reason,
        interpolation_state=interpolation_state,
        uncertainty=uncertainty,
        applicability=applicability,
        authority_state=authority_state,
        permitted_claim_wording=assertion["permitted_claim_wording"],
        conflict_visible=reconstruction["conflict"] is not None,
        content_sha256=assertion["content_sha256"],
    )


def _withheld(
    request: PropertyRequest,
    assertion: SelectedPropertyAssertion | None,
    reason: MissingDataReason,
) -> PropertySelectionResult:
    return PropertySelectionResult(
        status=SelectionStatus.WITHHELD,
        datum=None,
        model=None,
        canonical_unit=None,
        source=None,
        conditions=(
            request.conditions
            if assertion is None
            else assertion.requested_conditions
        ),
        uncertainty=(
            UncertaintyDescriptor.unknown("selected assertion is absent")
            if assertion is None
            else assertion.uncertainty
        ),
        interpolation_state=(
            None if assertion is None else assertion.interpolation_state
        ),
        applicability=(
            CanonicalScope.from_mapping({})
            if assertion is None
            else assertion.applicability
        ),
        authority_state=(None if assertion is None else assertion.authority_state),
        missing_reason=reason,
        warnings=(),
        request_sha256=request.content_sha256,
        assertion_sha256=(
            None if assertion is None else assertion.content_sha256
        ),
    )


class PropertySelectionService:
    """Select one explicit assertion or return an exact withholding reason."""

    @staticmethod
    def select(
        request: PropertyRequest,
        assertion: SelectedPropertyAssertion | None,
    ) -> PropertySelectionResult:
        if assertion is None:
            return _withheld(
                request, assertion, MissingDataReason.ASSERTION_ABSENT
            )
        if request.identity.content_sha256 != assertion.requested_identity.content_sha256:
            return _withheld(
                request, assertion, MissingDataReason.IDENTITY_MISMATCH
            )
        if request.property_type is not assertion.property_type:
            return _withheld(
                request, assertion, MissingDataReason.PROPERTY_MISMATCH
            )
        if request.conditions.scope != assertion.requested_conditions.scope:
            return _withheld(
                request, assertion, MissingDataReason.CONDITIONS_MISMATCH
            )
        if assertion.selection_kind is SelectionKind.NONE:
            return _withheld(request, assertion, MissingDataReason.NO_SELECTION)
        if assertion.authority_state in {
            AuthorityState.WITHHELD_CONFLICT,
            AuthorityState.WITHHELD_UNKNOWN,
        }:
            return _withheld(
                request, assertion, MissingDataReason.WITHHELD_AUTHORITY
            )
        if (
            assertion.interpolation_state is InterpolationState.NOT_APPLICABLE
            or assertion.applicability.to_mapping().get("applicable") is False
        ):
            return _withheld(
                request, assertion, MissingDataReason.NOT_APPLICABLE
            )
        if assertion.adaptation_missing_reason is not None:
            return _withheld(
                request, assertion, assertion.adaptation_missing_reason
            )

        warnings: list[str] = []
        status = SelectionStatus.SELECTED
        if assertion.authority_state is AuthorityState.ADVISORY_ONLY:
            if (
                request.claim_grade is ClaimGrade.RELEASE_GRADE
                or not request.allow_advisory
            ):
                return _withheld(
                    request, assertion, MissingDataReason.ADVISORY_NOT_ALLOWED
                )
            status = SelectionStatus.ADVISORY
            warnings.append("B2_ADVISORY_ONLY")

        if assertion.selection_kind is SelectionKind.OBSERVATION:
            if assertion.observation_identity is None or assertion.datum is None:
                return _withheld(
                    request,
                    assertion,
                    MissingDataReason.SELECTED_OBSERVATION_MISSING,
                )
            if (
                assertion.observation_identity.content_sha256
                != request.identity.content_sha256
            ):
                return _withheld(
                    request, assertion, MissingDataReason.IDENTITY_MISMATCH
                )
            if assertion.observation_property is not request.property_type:
                return _withheld(
                    request, assertion, MissingDataReason.PROPERTY_MISMATCH
                )
            if (
                assertion.observation_conditions is None
                or not assertion.observation_conditions.supports(
                    request.conditions
                )
            ):
                return _withheld(
                    request, assertion, MissingDataReason.CONDITIONS_MISMATCH
                )
        else:
            if assertion.model is None:
                return _withheld(
                    request,
                    assertion,
                    MissingDataReason.UNSUPPORTED_MODEL_SCHEMA,
                )
            if (
                assertion.model.identity.content_sha256
                != request.identity.content_sha256
            ):
                return _withheld(
                    request, assertion, MissingDataReason.IDENTITY_MISMATCH
                )

        outside_model_range = False
        if assertion.model is not None and request.conditions.temperature_k is not None:
            outside_model_range = not assertion.model.valid_temperature_range.contains(
                request.conditions.temperature_k
            )
        extrapolated = (
            assertion.interpolation_state is InterpolationState.EXTRAPOLATED
            or outside_model_range
        )
        if extrapolated:
            outside_reason = (
                MissingDataReason.MODEL_OUTSIDE_VALID_RANGE
                if outside_model_range
                and assertion.interpolation_state is not InterpolationState.EXTRAPOLATED
                else MissingDataReason.EXTRAPOLATION_FORBIDDEN
            )
            if request.claim_grade is ClaimGrade.RELEASE_GRADE:
                return _withheld(request, assertion, outside_reason)
            if (
                assertion.model is None
                or not request.allow_extrapolation
                or assertion.model.extrapolation_policy
                is not ExtrapolationPolicy.ADVISORY_ONLY_WITH_WARNING
            ):
                return _withheld(
                    request,
                    assertion,
                    MissingDataReason.EXTRAPOLATION_FORBIDDEN,
                )
            status = SelectionStatus.ADVISORY
            warnings.append("EXTRAPOLATION_ADVISORY_ONLY")

        if (
            assertion.interpolation_state is InterpolationState.INTERPOLATED
            and assertion.uncertainty.kind is UncertaintyKind.UNKNOWN
        ):
            return _withheld(
                request,
                assertion,
                MissingDataReason.INTERPOLATION_UNCERTAINTY_MISSING,
            )
        if assertion.source is None:
            return _withheld(request, assertion, MissingDataReason.SOURCE_MISSING)

        datum = assertion.datum
        model = assertion.model
        if datum is not None:
            canonical_unit = datum.canonical_unit
        elif model is not None:
            canonical_unit = model.pressure_unit
        else:
            return _withheld(
                request,
                assertion,
                MissingDataReason.UNSUPPORTED_MODEL_SCHEMA,
            )
        return PropertySelectionResult(
            status=status,
            datum=datum,
            model=model,
            canonical_unit=canonical_unit,
            source=assertion.source,
            conditions=assertion.requested_conditions,
            uncertainty=assertion.uncertainty,
            interpolation_state=assertion.interpolation_state,
            applicability=assertion.applicability,
            authority_state=assertion.authority_state,
            missing_reason=None,
            warnings=tuple(warnings),
            request_sha256=request.content_sha256,
            assertion_sha256=assertion.content_sha256,
        )


__all__ = [
    "AuthorityState",
    "InterpolationState",
    "MissingDataReason",
    "PropertyRequest",
    "PropertySelectionResult",
    "PropertySelectionService",
    "SelectedPropertyAssertion",
    "SelectionKind",
    "selected_assertion_from_b2_reconstruction",
]
