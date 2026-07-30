"""Fail-closed B3 contextual threshold and OAV authority commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import TYPE_CHECKING, Any

from engine.calibration.hashing import stable_json_hash

from app.models.lab_properties import (
    LabPropertyObservation,
    LabSelectedAssertion,
)
from app.models.lab_thresholds import (
    LEGACY_THRESHOLD_AUTHORITY,
    THRESHOLD_CONCENTRATION_BASES,
    THRESHOLD_ENDPOINTS,
    THRESHOLD_MATRIX_STATES,
    THRESHOLD_ROUTES,
    THRESHOLD_TRAINING_STATES,
    LabLegacyThresholdRecord,
    LabOAVAssessment,
    LabThresholdObservationContext,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.lab import LabRepository


OAV_MISMATCH_CODES = (
    "MISSING_THRESHOLD",
    "IDENTITY_SCOPE_MISMATCH",
    "THRESHOLD_MEDIUM_MISMATCH",
    "THRESHOLD_ENDPOINT_MISMATCH",
    "THRESHOLD_ROUTE_MISMATCH",
    "THRESHOLD_UNIT_INCOMPARABLE",
    "THRESHOLD_MATRIX_UNSPECIFIED",
    "THRESHOLD_AUTHORITY_TOO_LOW",
    "CONCENTRATION_NOT_COMPARABLE",
    "MODEL_OUTSIDE_APPLICABILITY_DOMAIN",
)
OAV_SCREENING_USES = (
    "SCREENING_PRIORITY",
    "GC_O_PRIORITY",
    "RECOMBINATION_TEST_PRIORITY",
    "OMISSION_TEST_PRIORITY",
    "ADDITION_TEST_PRIORITY",
    "GROSS_ANOMALY_CHECK",
    "SAME_ASSUMPTION_COMPARISON",
)
OAV_PROHIBITED_CLAIMS = (
    "EXACT_INTENSITY",
    "PERCENTAGE_CONTRIBUTION",
    "PLEASANTNESS",
    "SIMILARITY",
    "FAMILY_ASSIGNMENT",
    "LONGEVITY",
    "SILLAGE",
    "SKIN_PERFORMANCE",
    "RELEASE",
    "DELETE_BELOW_OAV_ONE",
)
_HIGH_AUTHORITY_EVIDENCE = {
    "MEASURED",
    "LITERATURE_DERIVED",
    "EMPIRICALLY_CALIBRATED",
}
_ACCEPTED_REVIEW_STATES = {"ACCEPTED_FOR_SCOPED_USE"}
_UNIT_CONVENTIONS = {
    "fraction": ("DIMENSIONLESS_FRACTION", 1.0),
    "ppm": ("DIMENSIONLESS_FRACTION", 1e-6),
    "ppb": ("DIMENSIONLESS_FRACTION", 1e-9),
    "ppt": ("DIMENSIONLESS_FRACTION", 1e-12),
    "mg/m3": ("MASS_CONCENTRATION", 1.0),
    "ug/m3": ("MASS_CONCENTRATION", 1e-3),
}
_IDENTITY_DETAILS = ("grade", "purity", "stereochemistry")


class ThresholdAuthorityError(ValueError):
    """A stable B3 validation failure."""

    code = "THRESHOLD_AUTHORITY_ERROR"


class ThresholdAuthorityConflictError(ThresholdAuthorityError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ThresholdAuthorityError(f"{field} must not be blank")
    return normalized


def _choice(
    value: str,
    field: str,
    allowed: tuple[str, ...],
) -> str:
    normalized = _text(value, field)
    if normalized not in allowed:
        raise ThresholdAuthorityError(f"{field} must be one of {', '.join(allowed)}")
    return normalized


def _finite(value: float, field: str) -> float:
    normalized = float(value)
    if not isfinite(normalized):
        raise ThresholdAuthorityError(f"{field} must be finite")
    return normalized


@dataclass(frozen=True, slots=True)
class ThresholdContextInput:
    context_id: str
    observation_id: str
    schema_version: str
    endpoint: str
    route: str
    medium: str
    matrix_specification_state: str
    matrix_composition: dict[str, Any]
    concentration_basis: str
    apparatus: dict[str, Any]
    population: dict[str, Any]
    training_state: str
    sample_size: int
    psychophysical_procedure: str

    def __post_init__(self) -> None:
        for field in (
            "context_id",
            "observation_id",
            "schema_version",
            "medium",
            "psychophysical_procedure",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self,
            "endpoint",
            _choice(self.endpoint, "endpoint", THRESHOLD_ENDPOINTS),
        )
        object.__setattr__(
            self,
            "route",
            _choice(self.route, "route", THRESHOLD_ROUTES),
        )
        object.__setattr__(
            self,
            "matrix_specification_state",
            _choice(
                self.matrix_specification_state,
                "matrix_specification_state",
                THRESHOLD_MATRIX_STATES,
            ),
        )
        object.__setattr__(
            self,
            "concentration_basis",
            _choice(
                self.concentration_basis,
                "concentration_basis",
                THRESHOLD_CONCENTRATION_BASES,
            ),
        )
        object.__setattr__(
            self,
            "training_state",
            _choice(
                self.training_state,
                "training_state",
                THRESHOLD_TRAINING_STATES,
            ),
        )
        matrix = dict(self.matrix_composition)
        apparatus = dict(self.apparatus)
        population = dict(self.population)
        if self.matrix_specification_state == "SPECIFIED" and not matrix:
            raise ThresholdAuthorityError("matrix_composition must not be empty when specified")
        if self.matrix_specification_state == "UNSPECIFIED" and matrix:
            raise ThresholdAuthorityError("matrix_composition must be empty when unspecified")
        if not apparatus:
            raise ThresholdAuthorityError("apparatus must not be empty")
        if not population:
            raise ThresholdAuthorityError("population must not be empty")
        sample_size = int(self.sample_size)
        if sample_size < 1 or sample_size != self.sample_size:
            raise ThresholdAuthorityError("sample_size must be a positive integer")
        object.__setattr__(self, "matrix_composition", matrix)
        object.__setattr__(self, "apparatus", apparatus)
        object.__setattr__(self, "population", population)
        object.__setattr__(self, "sample_size", sample_size)


@dataclass(frozen=True, slots=True)
class OAVAssessmentInput:
    assessment_id: str
    schema_version: str
    concentration_observation_id: str
    threshold_assertion_id: str | None
    requested_endpoint: str
    requested_route: str
    strict_science_mode: bool
    conversion_prerequisites: dict[str, Any]

    def __post_init__(self) -> None:
        for field in (
            "assessment_id",
            "schema_version",
            "concentration_observation_id",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        assertion_id = (
            _text(self.threshold_assertion_id, "threshold_assertion_id")
            if self.threshold_assertion_id is not None
            else None
        )
        object.__setattr__(self, "threshold_assertion_id", assertion_id)
        object.__setattr__(
            self,
            "requested_endpoint",
            _choice(
                self.requested_endpoint,
                "requested_endpoint",
                THRESHOLD_ENDPOINTS,
            ),
        )
        object.__setattr__(
            self,
            "requested_route",
            _choice(
                self.requested_route,
                "requested_route",
                THRESHOLD_ROUTES,
            ),
        )
        if self.strict_science_mode is not True:
            raise ThresholdAuthorityError("strict_science_mode must be true for canonical OAV")
        object.__setattr__(
            self,
            "conversion_prerequisites",
            dict(self.conversion_prerequisites),
        )


@dataclass(frozen=True, slots=True)
class LegacyThresholdInput:
    record_id: str
    schema_version: str
    material_key: str
    medium: str
    numeric_value: float
    original_unit: str
    verification_status: str
    source_payload: dict[str, Any]
    authority_state: str = LEGACY_THRESHOLD_AUTHORITY

    def __post_init__(self) -> None:
        for field in (
            "record_id",
            "schema_version",
            "material_key",
            "medium",
            "original_unit",
            "verification_status",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        value = _finite(self.numeric_value, "numeric_value")
        if value <= 0:
            raise ThresholdAuthorityError("numeric_value must be greater than zero")
        if self.authority_state != LEGACY_THRESHOLD_AUTHORITY:
            raise ThresholdAuthorityError(
                "legacy threshold authority must remain context incomplete"
            )
        object.__setattr__(self, "numeric_value", value)
        object.__setattr__(self, "source_payload", dict(self.source_payload))


@dataclass(frozen=True, slots=True)
class OAVCompatibilityInput:
    threshold_available: bool
    concentration_identity_scope: str
    concentration_identity_sha256: str
    threshold_identity_scope: str
    threshold_identity_sha256: str
    concentration_value: float | None
    concentration_unit: str
    concentration_basis: str
    concentration_medium: str
    concentration_matrix_specification_state: str
    concentration_matrix_composition: dict[str, Any]
    concentration_route: str
    concentration_temperature_k: float | None
    concentration_pressure_pa: float | None
    concentration_relative_humidity_percent: float | None
    concentration_evidence_class: str
    concentration_review_state: str
    threshold_value: float | None
    threshold_unit: str
    threshold_basis: str
    threshold_medium: str
    threshold_matrix_specification_state: str
    threshold_matrix_composition: dict[str, Any]
    threshold_endpoint: str
    threshold_route: str
    threshold_temperature_k: float | None
    threshold_pressure_pa: float | None
    threshold_relative_humidity_percent: float | None
    threshold_evidence_class: str
    threshold_review_state: str
    threshold_authority_state: str
    threshold_selection_kind: str
    threshold_interpolation_state: str
    requested_endpoint: str
    requested_route: str
    strict_science_mode: bool
    concentration_model_context: dict[str, Any] | None = None
    conversion_prerequisites: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class OAVDecision:
    status: str
    oav_value: float | None
    mismatch_codes: tuple[str, ...]
    permitted_uses: tuple[str, ...] = OAV_SCREENING_USES
    prohibited_claims: tuple[str, ...] = OAV_PROHIBITED_CLAIMS


def _same_condition(
    concentration_value: float | None,
    threshold_value: float | None,
    *,
    tolerance: float,
) -> bool:
    if concentration_value is None or threshold_value is None:
        return False
    return abs(float(concentration_value) - float(threshold_value)) <= tolerance


def _unit_value(value: float | None, unit: str) -> tuple[str, float] | None:
    if value is None:
        return None
    numeric = float(value)
    convention = _UNIT_CONVENTIONS.get(str(unit).strip().lower())
    if convention is None or not isfinite(numeric) or numeric < 0:
        return None
    family, scale = convention
    return family, numeric * scale


def evaluate_oav_compatibility(
    command: OAVCompatibilityInput,
) -> OAVDecision:
    """Return a ratio only when every B3 compatibility dimension passes."""

    failures: set[str] = set()
    threshold_numeric = _unit_value(
        command.threshold_value,
        command.threshold_unit,
    )
    concentration_numeric = _unit_value(
        command.concentration_value,
        command.concentration_unit,
    )
    if not command.threshold_available or (
        command.threshold_selection_kind != "MODEL"
        and (threshold_numeric is None or threshold_numeric[1] <= 0)
    ):
        failures.add("MISSING_THRESHOLD")

    if command.threshold_available:
        if (
            command.concentration_identity_scope != command.threshold_identity_scope
            or command.concentration_identity_sha256 != command.threshold_identity_sha256
        ):
            failures.add("IDENTITY_SCOPE_MISMATCH")
        if command.concentration_medium != command.threshold_medium or (
            command.concentration_matrix_specification_state == "SPECIFIED"
            and command.threshold_matrix_specification_state == "SPECIFIED"
            and command.concentration_matrix_composition != command.threshold_matrix_composition
        ):
            failures.add("THRESHOLD_MEDIUM_MISMATCH")
        if command.requested_endpoint != command.threshold_endpoint:
            failures.add("THRESHOLD_ENDPOINT_MISMATCH")
        if (
            command.requested_route != command.threshold_route
            or command.concentration_route != command.threshold_route
        ):
            failures.add("THRESHOLD_ROUTE_MISMATCH")
        if (
            concentration_numeric is None
            or threshold_numeric is None
            or concentration_numeric[0] != threshold_numeric[0]
            or command.concentration_basis != command.threshold_basis
        ):
            failures.add("THRESHOLD_UNIT_INCOMPARABLE")
        if command.threshold_matrix_specification_state != "SPECIFIED":
            failures.add("THRESHOLD_MATRIX_UNSPECIFIED")
        if (
            command.strict_science_mode is not True
            or command.threshold_authority_state != "AUTHORIZED_FOR_SCOPED_PROPERTY"
            or command.threshold_evidence_class not in _HIGH_AUTHORITY_EVIDENCE
            or command.threshold_review_state not in _ACCEPTED_REVIEW_STATES
        ):
            failures.add("THRESHOLD_AUTHORITY_TOO_LOW")

    comparable_concentration = (
        concentration_numeric is not None
        and concentration_numeric[1] >= 0
        and command.concentration_evidence_class in _HIGH_AUTHORITY_EVIDENCE
        and command.concentration_review_state in _ACCEPTED_REVIEW_STATES
        and command.concentration_matrix_specification_state == "SPECIFIED"
        and bool(command.concentration_model_context)
        and _same_condition(
            command.concentration_temperature_k,
            command.threshold_temperature_k,
            tolerance=1e-9,
        )
        and _same_condition(
            command.concentration_pressure_pa,
            command.threshold_pressure_pa,
            tolerance=1e-6,
        )
        and _same_condition(
            command.concentration_relative_humidity_percent,
            command.threshold_relative_humidity_percent,
            tolerance=1e-9,
        )
    )
    if not comparable_concentration:
        failures.add("CONCENTRATION_NOT_COMPARABLE")
    if (
        command.threshold_selection_kind != "OBSERVATION"
        or command.threshold_interpolation_state not in {"EXACT", "NOT_APPLICABLE"}
    ):
        failures.add("MODEL_OUTSIDE_APPLICABILITY_DOMAIN")

    mismatch_codes = tuple(code for code in OAV_MISMATCH_CODES if code in failures)
    if mismatch_codes:
        return OAVDecision(
            status="WITHHELD",
            oav_value=None,
            mismatch_codes=mismatch_codes,
        )
    assert concentration_numeric is not None
    assert threshold_numeric is not None
    return OAVDecision(
        status="COMPUTED",
        oav_value=concentration_numeric[1] / threshold_numeric[1],
        mismatch_codes=(),
    )


def _observation_value(observation: LabPropertyObservation) -> float | None:
    if observation.value_kind != "NUMERIC":
        return None
    return observation.numeric_value


def _identity_is_b3_exact(observation: LabPropertyObservation) -> None:
    missing = tuple(
        field
        for field in _IDENTITY_DETAILS
        if field not in observation.subject_identity_json
        or observation.subject_identity_json[field] is None
        or (
            isinstance(observation.subject_identity_json[field], str)
            and not observation.subject_identity_json[field].strip()
        )
    )
    if missing:
        raise ThresholdAuthorityError(
            "threshold identity is missing required dimensions: " + ", ".join(missing)
        )


class LabThresholdServiceMixin:
    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def record_threshold_context(
        self,
        command: ThresholdContextInput,
    ) -> LabThresholdObservationContext:
        async with self._transaction():
            if await self.repository.get_threshold_context(command.context_id) is not None:
                raise ThresholdAuthorityConflictError(
                    "THRESHOLD_CONTEXT_ALREADY_EXISTS",
                    "The immutable threshold context identifier already exists.",
                )
            observation = await self.repository.get_property_observation(command.observation_id)
            if observation is None:
                raise ThresholdAuthorityConflictError(
                    "THRESHOLD_OBSERVATION_NOT_FOUND",
                    "The linked B2 property observation does not exist.",
                )
            if observation.property_type != "ODOR_THRESHOLD":
                raise ThresholdAuthorityError(
                    "threshold context requires property_type ODOR_THRESHOLD"
                )
            _identity_is_b3_exact(observation)
            numeric = _observation_value(observation)
            if numeric is not None and (not isfinite(float(numeric)) or float(numeric) <= 0):
                raise ThresholdAuthorityError("numeric odor thresholds must be positive and finite")
            payload = {
                "schema": "lab-threshold-context-v1",
                **asdict(command),
                "observation_content_sha256": observation.content_sha256,
            }
            content_sha256 = stable_json_hash(payload)
            if (
                await self.repository.threshold_context_for_observation(observation.id) is not None
                or await self.repository.threshold_context_by_hash(content_sha256) is not None
            ):
                raise ThresholdAuthorityConflictError(
                    "THRESHOLD_CONTEXT_ALREADY_EXISTS",
                    "The observation already has a contextual threshold record.",
                )
            return await self.repository.add(
                LabThresholdObservationContext(
                    id=command.context_id,
                    observation_id=observation.id,
                    schema_version=command.schema_version,
                    endpoint=command.endpoint,
                    route=command.route,
                    medium=command.medium,
                    matrix_specification_state=(command.matrix_specification_state),
                    matrix_composition_json=dict(command.matrix_composition),
                    concentration_basis=command.concentration_basis,
                    apparatus_json=dict(command.apparatus),
                    population_json=dict(command.population),
                    training_state=command.training_state,
                    sample_size=command.sample_size,
                    psychophysical_procedure=(command.psychophysical_procedure),
                    content_sha256=content_sha256,
                )
            )

    async def _oav_compatibility_input(
        self,
        command: OAVAssessmentInput,
        concentration: LabPropertyObservation,
        assertion: LabSelectedAssertion | None,
    ) -> OAVCompatibilityInput:
        concentration_context = dict(concentration.applicability_domain_json or {})
        threshold = None
        context = None
        if assertion is not None and assertion.selected_observation_id:
            threshold = await self.repository.get_property_observation(
                assertion.selected_observation_id
            )
            if threshold is not None:
                context = await self.repository.threshold_context_for_observation(threshold.id)
        threshold_available = (
            assertion is not None
            and assertion.requested_property_type == "ODOR_THRESHOLD"
            and threshold is not None
            and threshold.property_type == "ODOR_THRESHOLD"
            and context is not None
        )
        assertion_context_matches = (
            assertion is not None
            and context is not None
            and assertion.requested_conditions_json.get("context_id")
            == context.id
            and assertion.applicability_json.get("context_id") == context.id
        )
        identity_scope = concentration.identity_scope
        identity_sha256 = concentration.subject_identity_sha256
        threshold_identity_scope = (
            threshold.identity_scope if threshold is not None else identity_scope
        )
        threshold_identity_sha256 = (
            threshold.subject_identity_sha256 if threshold is not None else identity_sha256
        )
        if (
            assertion is not None
            and threshold is not None
            and assertion.requested_identity_sha256 != threshold.subject_identity_sha256
        ):
            threshold_identity_sha256 = assertion.requested_identity_sha256
        return OAVCompatibilityInput(
            threshold_available=threshold_available,
            concentration_identity_scope=identity_scope,
            concentration_identity_sha256=identity_sha256,
            threshold_identity_scope=threshold_identity_scope,
            threshold_identity_sha256=threshold_identity_sha256,
            concentration_value=_observation_value(concentration),
            concentration_unit=concentration.canonical_unit,
            concentration_basis=str(concentration_context.get("concentration_basis", "")),
            concentration_medium=str(concentration_context.get("medium", "")),
            concentration_matrix_specification_state=str(
                concentration_context.get(
                    "matrix_specification_state",
                    "UNSPECIFIED",
                )
            ),
            concentration_matrix_composition=dict(
                concentration_context.get("matrix_composition") or {}
            ),
            concentration_route=str(concentration_context.get("route", "")),
            concentration_temperature_k=concentration.temperature_k,
            concentration_pressure_pa=concentration.pressure_pa,
            concentration_relative_humidity_percent=(concentration.relative_humidity_percent),
            concentration_evidence_class=concentration.evidence_class,
            concentration_review_state=concentration.review_state,
            threshold_value=(_observation_value(threshold) if threshold is not None else None),
            threshold_unit=(threshold.canonical_unit if threshold is not None else ""),
            threshold_basis=(context.concentration_basis if context is not None else ""),
            threshold_medium=(context.medium if context is not None else ""),
            threshold_matrix_specification_state=(
                context.matrix_specification_state if context is not None else "UNSPECIFIED"
            ),
            threshold_matrix_composition=(
                dict(context.matrix_composition_json) if context is not None else {}
            ),
            threshold_endpoint=(
                context.endpoint if context is not None else command.requested_endpoint
            ),
            threshold_route=(context.route if context is not None else command.requested_route),
            threshold_temperature_k=(threshold.temperature_k if threshold is not None else None),
            threshold_pressure_pa=(threshold.pressure_pa if threshold is not None else None),
            threshold_relative_humidity_percent=(
                threshold.relative_humidity_percent if threshold is not None else None
            ),
            threshold_evidence_class=(
                threshold.evidence_class if threshold is not None else "UNKNOWN"
            ),
            threshold_review_state=(threshold.review_state if threshold is not None else "STAGED"),
            threshold_authority_state=(
                assertion.authority_state
                if assertion is not None and assertion_context_matches
                else "WITHHELD_UNKNOWN"
            ),
            threshold_selection_kind=(
                assertion.selection_kind if assertion is not None else "NONE"
            ),
            threshold_interpolation_state=(
                assertion.interpolation_state if assertion is not None else "NOT_APPLICABLE"
            ),
            requested_endpoint=command.requested_endpoint,
            requested_route=command.requested_route,
            strict_science_mode=command.strict_science_mode,
            concentration_model_context=(dict(concentration_context.get("model_context") or {})),
            conversion_prerequisites=dict(command.conversion_prerequisites),
        )

    async def record_oav_assessment(
        self,
        command: OAVAssessmentInput,
    ) -> LabOAVAssessment:
        async with self._transaction():
            if await self.repository.get_oav_assessment(command.assessment_id) is not None:
                raise ThresholdAuthorityConflictError(
                    "OAV_ASSESSMENT_ALREADY_EXISTS",
                    "The immutable OAV assessment identifier already exists.",
                )
            concentration = await self.repository.get_property_observation(
                command.concentration_observation_id
            )
            if concentration is None:
                raise ThresholdAuthorityConflictError(
                    "OAV_CONCENTRATION_NOT_FOUND",
                    "The concentration observation does not exist.",
                )
            if concentration.property_type != "CONCENTRATION":
                raise ThresholdAuthorityError(
                    "OAV concentration requires property_type CONCENTRATION"
                )
            assertion = (
                await self.repository.get_selected_assertion(command.threshold_assertion_id)
                if command.threshold_assertion_id is not None
                else None
            )
            if command.threshold_assertion_id is not None and assertion is None:
                raise ThresholdAuthorityConflictError(
                    "OAV_THRESHOLD_ASSERTION_NOT_FOUND",
                    "The requested threshold assertion does not exist.",
                )
            compatibility = await self._oav_compatibility_input(
                command,
                concentration,
                assertion,
            )
            decision = evaluate_oav_compatibility(compatibility)
            input_snapshot = asdict(compatibility)
            payload = {
                "schema": "lab-oav-assessment-v1",
                **asdict(command),
                "input_snapshot": input_snapshot,
                "decision": asdict(decision),
            }
            content_sha256 = stable_json_hash(payload)
            if await self.repository.oav_assessment_by_hash(content_sha256) is not None:
                raise ThresholdAuthorityConflictError(
                    "OAV_ASSESSMENT_ALREADY_EXISTS",
                    "An identical immutable OAV assessment already exists.",
                )
            return await self.repository.add(
                LabOAVAssessment(
                    id=command.assessment_id,
                    schema_version=command.schema_version,
                    concentration_observation_id=concentration.id,
                    threshold_assertion_id=(assertion.id if assertion is not None else None),
                    requested_endpoint=command.requested_endpoint,
                    requested_route=command.requested_route,
                    strict_science_mode=True,
                    status=decision.status,
                    oav_value=decision.oav_value,
                    mismatch_count=len(decision.mismatch_codes),
                    mismatch_codes_json=list(decision.mismatch_codes),
                    conversion_prerequisites_json=dict(command.conversion_prerequisites),
                    input_snapshot_json=input_snapshot,
                    permitted_uses_json=list(decision.permitted_uses),
                    prohibited_claims_json=list(decision.prohibited_claims),
                    content_sha256=content_sha256,
                )
            )

    async def record_legacy_threshold(
        self,
        command: LegacyThresholdInput,
    ) -> LabLegacyThresholdRecord:
        payload = {
            "schema": "lab-legacy-threshold-v1",
            **asdict(command),
        }
        content_sha256 = stable_json_hash(payload)
        async with self._transaction():
            if (
                await self.repository.get_legacy_threshold_record(command.record_id) is not None
                or await self.repository.legacy_threshold_by_hash(content_sha256) is not None
            ):
                raise ThresholdAuthorityConflictError(
                    "LEGACY_THRESHOLD_ALREADY_EXISTS",
                    "The immutable legacy threshold record already exists.",
                )
            return await self.repository.add(
                LabLegacyThresholdRecord(
                    id=command.record_id,
                    schema_version=command.schema_version,
                    material_key=command.material_key,
                    medium=command.medium,
                    numeric_value=command.numeric_value,
                    original_unit=command.original_unit,
                    verification_status=command.verification_status,
                    authority_state=LEGACY_THRESHOLD_AUTHORITY,
                    source_payload_json=dict(command.source_payload),
                    content_sha256=content_sha256,
                )
            )


__all__ = [
    "OAV_MISMATCH_CODES",
    "OAV_PROHIBITED_CLAIMS",
    "OAV_SCREENING_USES",
    "LegacyThresholdInput",
    "OAVAssessmentInput",
    "OAVCompatibilityInput",
    "OAVDecision",
    "ThresholdAuthorityConflictError",
    "ThresholdAuthorityError",
    "ThresholdContextInput",
    "evaluate_oav_compatibility",
]
