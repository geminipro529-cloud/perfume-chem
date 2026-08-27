"""Fail-closed C7 lot-aware natural-material contracts.

The module preserves exact lot identity, analytical basis, unresolved
composition, provenance, and projection family. It does not convert normalized
chromatographic area to concentration, calculate headspace/OAV, authorize a
regulatory claim, infer adulteration, or read legacy, backend, or database
state.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_EnumT = TypeVar("_EnumT", bound=Enum)


class NaturalLotContractError(ValueError):
    """Malformed, ambiguous, unbound, or authority-ineligible C7 record."""


class SourceDocumentKind(str, Enum):
    COA = "COA"
    SDS = "SDS"
    SPECIFICATION = "SPECIFICATION"
    ANALYTICAL_REPORT = "ANALYTICAL_REPORT"
    SUPPLIER_BATCH_PROFILE = "SUPPLIER_BATCH_PROFILE"
    LITERATURE = "LITERATURE"


class IdentityConfidence(str, Enum):
    TENTATIVE = "TENTATIVE"
    PROBABLE = "PROBABLE"
    CONFIRMED = "CONFIRMED"


class ObservationOrigin(str, Enum):
    EXACT_LOT_MEASURED = "EXACT_LOT_MEASURED"
    SUPPLIER_BATCH_REPORTED = "SUPPLIER_BATCH_REPORTED"
    LITERATURE_REPORTED = "LITERATURE_REPORTED"
    GENERIC_PROXY = "GENERIC_PROXY"


class ConstituentBasis(str, Enum):
    CALIBRATED_MASS_FRACTION = "CALIBRATED_MASS_FRACTION"
    CALIBRATED_MOLAR_FRACTION = "CALIBRATED_MOLAR_FRACTION"
    ESTIMATED_MASS_FRACTION = "ESTIMATED_MASS_FRACTION"
    RESPONSE_CORRECTED_RELATIVE_FRACTION = "RESPONSE_CORRECTED_RELATIVE_FRACTION"
    NORMALIZED_AREA_PERCENT = "NORMALIZED_AREA_PERCENT"
    RELATIVE_RESPONSE = "RELATIVE_RESPONSE"
    PRESENCE_ONLY = "PRESENCE_ONLY"
    LITERATURE_RANGE = "LITERATURE_RANGE"
    UNKNOWN = "UNKNOWN"


PERMITTED_CONSTITUENT_BASES = tuple(ConstituentBasis)


class CalibrationState(str, Enum):
    CALIBRATED = "CALIBRATED"
    RESPONSE_CORRECTED = "RESPONSE_CORRECTED"
    UNCALIBRATED = "UNCALIBRATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class CensoringState(str, Enum):
    NONE = "NONE"
    BELOW_LOD = "BELOW_LOD"
    BELOW_LOQ = "BELOW_LOQ"
    NOT_DETECTED = "NOT_DETECTED"


class ReviewState(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    REJECTED = "REJECTED"


class CompositionAuthority(str, Enum):
    EXACT_LOT_QUANTIFIED = "EXACT_LOT_QUANTIFIED"
    EXACT_LOT_RELATIVE_PROFILE = "EXACT_LOT_RELATIVE_PROFILE"
    SUPPLIER_BATCH_SPECIFIC = "SUPPLIER_BATCH_SPECIFIC"
    SPECIFIC_LITERATURE_PROXY = "SPECIFIC_LITERATURE_PROXY"
    GENERIC_MATERIAL_PROXY = "GENERIC_MATERIAL_PROXY"
    UNKNOWN = "UNKNOWN"


C7_COMPOSITION_PRECEDENCE = tuple(CompositionAuthority)


class NaturalCompositionCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class UnresolvedFractionKind(str, Enum):
    UNKNOWN_PEAK = "UNKNOWN_PEAK"
    COELUTION = "COELUTION"
    UNRESOLVED_GROUP = "UNRESOLVED_GROUP"
    UNIDENTIFIED_GC_O_EVENT = "UNIDENTIFIED_GC_O_EVENT"
    BELOW_QUANTITATION = "BELOW_QUANTITATION"
    UNASSIGNED_MASS = "UNASSIGNED_MASS"
    UNASSIGNED_AREA = "UNASSIGNED_AREA"


class UnresolvedDisclosureState(str, Enum):
    PRESENT = "PRESENT"
    NOT_REPORTED = "NOT_REPORTED"
    REVIEWED_NONE_OBSERVED = "REVIEWED_NONE_OBSERVED"


class SelectionStatus(str, Enum):
    SELECTED = "SELECTED"
    AMBIGUOUS = "AMBIGUOUS"
    ABSTAINED = "ABSTAINED"


class ProjectionFamily(str, Enum):
    OLFACTORY_HEADSPACE = "OLFACTORY_HEADSPACE"
    REGULATORY_ALLERGEN = "REGULATORY_ALLERGEN"
    IDENTITY_AUTHENTICITY = "IDENTITY_AUTHENTICITY"


class ProjectionStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    WITHHELD = "WITHHELD"


class AuthenticityDecision(str, Enum):
    CONSISTENT_WITH_REFERENCE = "CONSISTENT_WITH_REFERENCE"
    OUTSIDE_REFERENCE_PROFILE = "OUTSIDE_REFERENCE_PROFILE"
    CHEMOTYPE_MISMATCH = "CHEMOTYPE_MISMATCH"
    POSSIBLE_ADULTERATION_INDICATORS = "POSSIBLE_ADULTERATION_INDICATORS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


_FRACTION_BASES = frozenset(
    {
        ConstituentBasis.CALIBRATED_MASS_FRACTION,
        ConstituentBasis.CALIBRATED_MOLAR_FRACTION,
        ConstituentBasis.ESTIMATED_MASS_FRACTION,
        ConstituentBasis.RESPONSE_CORRECTED_RELATIVE_FRACTION,
    }
)
_ABSOLUTE_BASES = frozenset(
    {
        ConstituentBasis.CALIBRATED_MASS_FRACTION,
        ConstituentBasis.CALIBRATED_MOLAR_FRACTION,
    }
)
_RELATIVE_BASES = frozenset(
    {
        ConstituentBasis.RESPONSE_CORRECTED_RELATIVE_FRACTION,
        ConstituentBasis.NORMALIZED_AREA_PERCENT,
        ConstituentBasis.RELATIVE_RESPONSE,
        ConstituentBasis.PRESENCE_ONLY,
        ConstituentBasis.LITERATURE_RANGE,
    }
)
_LOT_UNKNOWN_FIELDS = frozenset(
    {
        "botanical_species",
        "variety_or_chemotype",
        "plant_part",
        "geographic_origin",
        "harvest_or_production_date",
        "extraction_method",
        "processing",
    }
)


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NaturalLotContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise NaturalLotContractError(f"{field_name} keys must be strings")
    return dict(value)


def _sequence(value: object, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NaturalLotContractError(f"{field_name} must be a sequence")
    return tuple(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise NaturalLotContractError(f"{field_name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise NaturalLotContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NaturalLotContractError(f"{field_name} must not be blank")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, field_name)


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise NaturalLotContractError(f"{field_name} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise NaturalLotContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise NaturalLotContractError(f"{field_name} must be finite")
    return result


def _optional_nonnegative(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    result = _finite(value, field_name)
    if result < 0.0:
        raise NaturalLotContractError(f"{field_name} must be nonnegative")
    return result


def _positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise NaturalLotContractError(f"{field_name} must be a positive integer")
    return value


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise NaturalLotContractError(f"{field_name} must be a lowercase 64-character SHA-256")
    return value


def _optional_sha256(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, field_name)


def _direct_enum(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    if not isinstance(value, enum_type):
        raise NaturalLotContractError(f"{field_name} must be a {enum_type.__name__}")
    return value


def _enum_value(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise NaturalLotContractError(
            f"{field_name} is not a supported {enum_type.__name__}"
        ) from exc


def _strings(
    value: object,
    field_name: str,
    *,
    allow_empty: bool = True,
    ordered: bool = False,
) -> tuple[str, ...]:
    values = tuple(_nonblank(item, field_name) for item in _sequence(value, field_name))
    if not allow_empty and not values:
        raise NaturalLotContractError(f"{field_name} must not be empty")
    if len(values) != len(set(values)):
        raise NaturalLotContractError(f"{field_name} contains duplicate values")
    if ordered:
        return values
    return tuple(sorted(values, key=lambda item: (item.casefold(), item)))


def _optional_date(value: object, field_name: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise NaturalLotContractError(f"{field_name} must be a date")
    return value


def _date_value(value: object, field_name: str) -> date:
    result = _optional_date(value, field_name)
    if result is None:
        raise NaturalLotContractError(f"{field_name} must be a date")
    return result


def _parse_optional_date(value: object, field_name: str) -> date | None:
    if value is None:
        return None
    text = _nonblank(value, field_name)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise NaturalLotContractError(f"{field_name} must be ISO-8601") from exc


def _parse_date(value: object, field_name: str) -> date:
    parsed = _parse_optional_date(value, field_name)
    if parsed is None:
        raise NaturalLotContractError(f"{field_name} must be an ISO-8601 date")
    return parsed


def _aware_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise NaturalLotContractError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _datetime_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, field_name: str) -> datetime:
    text = _nonblank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NaturalLotContractError(f"{field_name} must be ISO-8601") from exc
    return _aware_datetime(parsed, field_name)


def _hash(schema: str, payload: Mapping[str, object]) -> str:
    return stable_json_hash({"schema": schema, **payload})


def _verify_content_hash(expected: object, actual: str, field_name: str) -> None:
    if _sha256(expected, field_name) != actual:
        raise NaturalLotContractError(f"{field_name} does not match canonical content")


def _validate_numeric_for_basis(
    value: float,
    basis: ConstituentBasis,
    field_name: str,
) -> float:
    result = _finite(value, field_name)
    if basis in _FRACTION_BASES and not 0.0 <= result <= 1.0:
        raise NaturalLotContractError(f"{field_name} must be between 0 and 1")
    if basis is ConstituentBasis.NORMALIZED_AREA_PERCENT and not 0.0 <= result <= 100.0:
        raise NaturalLotContractError(f"{field_name} must be between 0 and 100")
    if basis is ConstituentBasis.RELATIVE_RESPONSE and result < 0.0:
        raise NaturalLotContractError(f"{field_name} must be nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class SourceDocumentReference:
    document_id: str
    document_kind: SourceDocumentKind
    source_id: str
    subject_lot_id: str | None
    document_sha256: str
    version: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", _nonblank(self.document_id, "document_id"))
        object.__setattr__(
            self,
            "document_kind",
            _direct_enum(SourceDocumentKind, self.document_kind, "document_kind"),
        )
        object.__setattr__(self, "source_id", _nonblank(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "subject_lot_id",
            _optional_text(self.subject_lot_id, "subject_lot_id"),
        )
        object.__setattr__(
            self,
            "document_sha256",
            _sha256(self.document_sha256, "document_sha256"),
        )
        object.__setattr__(self, "version", _nonblank(self.version, "version"))
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-source-document-reference-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "document_kind": self.document_kind.value,
            "source_id": self.source_id,
            "subject_lot_id": self.subject_lot_id,
            "document_sha256": self.document_sha256,
            "version": self.version,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> SourceDocumentReference:
        payload = _mapping(value, "source document")
        _exact_keys(
            payload,
            {
                "document_id",
                "document_kind",
                "source_id",
                "subject_lot_id",
                "document_sha256",
                "version",
                "content_sha256",
            },
            "source document",
        )
        item = cls(
            document_id=payload["document_id"],
            document_kind=_enum_value(
                SourceDocumentKind,
                payload["document_kind"],
                "document_kind",
            ),
            source_id=payload["source_id"],
            subject_lot_id=payload["subject_lot_id"],
            document_sha256=payload["document_sha256"],
            version=payload["version"],
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class AnalyticalRunReference:
    analytical_run_id: str
    run_authority_id: str
    subject_lot_id: str
    method_id: str
    run_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "analytical_run_id",
            "run_authority_id",
            "subject_lot_id",
            "method_id",
        ):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(self, "run_sha256", _sha256(self.run_sha256, "run_sha256"))
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-analytical-run-reference-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "analytical_run_id": self.analytical_run_id,
            "run_authority_id": self.run_authority_id,
            "subject_lot_id": self.subject_lot_id,
            "method_id": self.method_id,
            "run_sha256": self.run_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> AnalyticalRunReference:
        payload = _mapping(value, "analytical run")
        _exact_keys(
            payload,
            {
                "analytical_run_id",
                "run_authority_id",
                "subject_lot_id",
                "method_id",
                "run_sha256",
                "content_sha256",
            },
            "analytical run",
        )
        item = cls(
            analytical_run_id=payload["analytical_run_id"],
            run_authority_id=payload["run_authority_id"],
            subject_lot_id=payload["subject_lot_id"],
            method_id=payload["method_id"],
            run_sha256=payload["run_sha256"],
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class NaturalMaterialLot:
    lot_id: str
    material_id: str
    material_name: str
    botanical_species: str | None
    variety_or_chemotype: str | None
    plant_part: str | None
    geographic_origin: str | None
    harvest_or_production_date: date | None
    extraction_method: str | None
    processing: tuple[str, ...]
    supplier_id: str
    supplier_product: str
    supplier_lot: str
    received_on: date
    opened_on: date | None
    storage_conditions: tuple[str, ...]
    oxidation_stability_observations: tuple[str, ...]
    source_documents: tuple[SourceDocumentReference, ...]
    analytical_runs: tuple[AnalyticalRunReference, ...]
    authenticity_status: AuthenticityDecision
    unknown_identity_fields: tuple[str, ...] = ()
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "lot_id",
            "material_id",
            "material_name",
            "supplier_id",
            "supplier_product",
            "supplier_lot",
        ):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        for field_name in (
            "botanical_species",
            "variety_or_chemotype",
            "plant_part",
            "geographic_origin",
            "extraction_method",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "harvest_or_production_date",
            _optional_date(
                self.harvest_or_production_date,
                "harvest_or_production_date",
            ),
        )
        object.__setattr__(self, "received_on", _date_value(self.received_on, "received_on"))
        object.__setattr__(self, "opened_on", _optional_date(self.opened_on, "opened_on"))
        if (
            self.harvest_or_production_date is not None
            and self.harvest_or_production_date > self.received_on
        ):
            raise NaturalLotContractError(
                "harvest_or_production_date must not be after received_on"
            )
        if self.opened_on is not None and self.opened_on < self.received_on:
            raise NaturalLotContractError("opened_on must not be before received_on")
        object.__setattr__(
            self,
            "processing",
            _strings(self.processing, "processing", ordered=True),
        )
        object.__setattr__(
            self,
            "storage_conditions",
            _strings(self.storage_conditions, "storage_conditions", allow_empty=False),
        )
        object.__setattr__(
            self,
            "oxidation_stability_observations",
            _strings(
                self.oxidation_stability_observations,
                "oxidation_stability_observations",
            ),
        )
        object.__setattr__(
            self,
            "authenticity_status",
            _direct_enum(
                AuthenticityDecision,
                self.authenticity_status,
                "authenticity_status",
            ),
        )
        unknown_fields = _strings(
            self.unknown_identity_fields,
            "unknown_identity_fields",
        )
        invalid_unknown = set(unknown_fields) - _LOT_UNKNOWN_FIELDS
        if invalid_unknown:
            raise NaturalLotContractError(
                "unknown_identity_fields contains unsupported fields: "
                + ", ".join(sorted(invalid_unknown))
            )
        actually_unknown = {
            field_name
            for field_name in _LOT_UNKNOWN_FIELDS
            if (
                not self.processing
                if field_name == "processing"
                else getattr(self, field_name) is None
            )
        }
        if set(unknown_fields) != actually_unknown:
            raise NaturalLotContractError(
                "unknown_identity_fields must exactly match absent identity fields; "
                "a populated field cannot be declared unknown"
            )
        object.__setattr__(self, "unknown_identity_fields", unknown_fields)

        documents = tuple(self.source_documents)
        if any(not isinstance(item, SourceDocumentReference) for item in documents):
            raise NaturalLotContractError(
                "source_documents must contain SourceDocumentReference values"
            )
        document_ids = tuple(item.document_id for item in documents)
        if len(document_ids) != len(set(document_ids)):
            raise NaturalLotContractError("source_documents contains duplicate document IDs")
        if any(item.subject_lot_id != self.lot_id for item in documents):
            raise NaturalLotContractError("every source document must bind the exact natural lot")
        object.__setattr__(
            self,
            "source_documents",
            tuple(sorted(documents, key=lambda item: item.document_id)),
        )

        runs = tuple(self.analytical_runs)
        if any(not isinstance(item, AnalyticalRunReference) for item in runs):
            raise NaturalLotContractError(
                "analytical_runs must contain AnalyticalRunReference values"
            )
        run_ids = tuple(item.analytical_run_id for item in runs)
        if len(run_ids) != len(set(run_ids)):
            raise NaturalLotContractError("analytical_runs contains duplicate run IDs")
        if any(item.subject_lot_id != self.lot_id for item in runs):
            raise NaturalLotContractError("every analytical run must bind the exact natural lot")
        object.__setattr__(
            self,
            "analytical_runs",
            tuple(sorted(runs, key=lambda item: item.analytical_run_id)),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-natural-material-lot-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "lot_id": self.lot_id,
            "material_id": self.material_id,
            "material_name": self.material_name,
            "botanical_species": self.botanical_species,
            "variety_or_chemotype": self.variety_or_chemotype,
            "plant_part": self.plant_part,
            "geographic_origin": self.geographic_origin,
            "harvest_or_production_date": (
                self.harvest_or_production_date.isoformat()
                if self.harvest_or_production_date is not None
                else None
            ),
            "extraction_method": self.extraction_method,
            "processing": list(self.processing),
            "supplier_id": self.supplier_id,
            "supplier_product": self.supplier_product,
            "supplier_lot": self.supplier_lot,
            "received_on": self.received_on.isoformat(),
            "opened_on": self.opened_on.isoformat() if self.opened_on is not None else None,
            "storage_conditions": list(self.storage_conditions),
            "oxidation_stability_observations": list(self.oxidation_stability_observations),
            "source_documents": [item.to_mapping() for item in self.source_documents],
            "analytical_runs": [item.to_mapping() for item in self.analytical_runs],
            "authenticity_status": self.authenticity_status.value,
            "unknown_identity_fields": list(self.unknown_identity_fields),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> NaturalMaterialLot:
        payload = _mapping(value, "natural material lot")
        expected = {
            "lot_id",
            "material_id",
            "material_name",
            "botanical_species",
            "variety_or_chemotype",
            "plant_part",
            "geographic_origin",
            "harvest_or_production_date",
            "extraction_method",
            "processing",
            "supplier_id",
            "supplier_product",
            "supplier_lot",
            "received_on",
            "opened_on",
            "storage_conditions",
            "oxidation_stability_observations",
            "source_documents",
            "analytical_runs",
            "authenticity_status",
            "unknown_identity_fields",
            "content_sha256",
        }
        _exact_keys(payload, expected, "natural material lot")
        item = cls(
            lot_id=payload["lot_id"],
            material_id=payload["material_id"],
            material_name=payload["material_name"],
            botanical_species=payload["botanical_species"],
            variety_or_chemotype=payload["variety_or_chemotype"],
            plant_part=payload["plant_part"],
            geographic_origin=payload["geographic_origin"],
            harvest_or_production_date=_parse_optional_date(
                payload["harvest_or_production_date"],
                "harvest_or_production_date",
            ),
            extraction_method=payload["extraction_method"],
            processing=_sequence(payload["processing"], "processing"),
            supplier_id=payload["supplier_id"],
            supplier_product=payload["supplier_product"],
            supplier_lot=payload["supplier_lot"],
            received_on=_parse_date(payload["received_on"], "received_on"),
            opened_on=_parse_optional_date(payload["opened_on"], "opened_on"),
            storage_conditions=_sequence(
                payload["storage_conditions"],
                "storage_conditions",
            ),
            oxidation_stability_observations=_sequence(
                payload["oxidation_stability_observations"],
                "oxidation_stability_observations",
            ),
            source_documents=tuple(
                SourceDocumentReference.from_mapping(row)
                for row in _sequence(payload["source_documents"], "source_documents")
            ),
            analytical_runs=tuple(
                AnalyticalRunReference.from_mapping(row)
                for row in _sequence(payload["analytical_runs"], "analytical_runs")
            ),
            authenticity_status=_enum_value(
                AuthenticityDecision,
                payload["authenticity_status"],
                "authenticity_status",
            ),
            unknown_identity_fields=_sequence(
                payload["unknown_identity_fields"],
                "unknown_identity_fields",
            ),
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class ConstituentObservation:
    observation_id: str
    source_lot_id: str | None
    chemical_id: str
    chemical_name: str
    identity_confidence: IdentityConfidence
    origin: ObservationOrigin
    value: float | None
    lower_bound: float | None
    upper_bound: float | None
    basis: ConstituentBasis
    method_id: str
    calibration_state: CalibrationState
    response_model_id: str | None
    standard_uncertainty: float | None
    uncertainty_note: str
    lod: float | None
    loq: float | None
    censoring: CensoringState
    source_id: str
    source_sha256: str
    analytical_run_id: str | None
    review_state: ReviewState
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "observation_id",
            "chemical_id",
            "chemical_name",
            "method_id",
            "source_id",
            "uncertainty_note",
        ):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "source_lot_id",
            _optional_text(self.source_lot_id, "source_lot_id"),
        )
        object.__setattr__(
            self,
            "analytical_run_id",
            _optional_text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(
            self,
            "response_model_id",
            _optional_text(self.response_model_id, "response_model_id"),
        )
        object.__setattr__(
            self,
            "identity_confidence",
            _direct_enum(
                IdentityConfidence,
                self.identity_confidence,
                "identity_confidence",
            ),
        )
        object.__setattr__(
            self,
            "origin",
            _direct_enum(ObservationOrigin, self.origin, "origin"),
        )
        object.__setattr__(
            self,
            "basis",
            _direct_enum(ConstituentBasis, self.basis, "basis"),
        )
        object.__setattr__(
            self,
            "calibration_state",
            _direct_enum(
                CalibrationState,
                self.calibration_state,
                "calibration_state",
            ),
        )
        object.__setattr__(
            self,
            "censoring",
            _direct_enum(CensoringState, self.censoring, "censoring"),
        )
        object.__setattr__(
            self,
            "review_state",
            _direct_enum(ReviewState, self.review_state, "review_state"),
        )
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(
            self,
            "standard_uncertainty",
            _optional_nonnegative(
                self.standard_uncertainty,
                "standard_uncertainty",
            ),
        )
        object.__setattr__(self, "lod", _optional_nonnegative(self.lod, "LOD"))
        object.__setattr__(self, "loq", _optional_nonnegative(self.loq, "LOQ"))
        if self.lod is not None and self.loq is not None and self.lod > self.loq:
            raise NaturalLotContractError("LOD must not exceed LOQ")

        if self.basis in _ABSOLUTE_BASES:
            if self.calibration_state is not CalibrationState.CALIBRATED:
                raise NaturalLotContractError("calibrated fraction bases require CALIBRATED state")
            if self.response_model_id is None:
                raise NaturalLotContractError("calibrated fraction bases require response_model_id")
            if self.standard_uncertainty is None:
                raise NaturalLotContractError(
                    "calibrated fraction bases require standard_uncertainty"
                )
        elif self.basis is ConstituentBasis.RESPONSE_CORRECTED_RELATIVE_FRACTION:
            if self.calibration_state is not CalibrationState.RESPONSE_CORRECTED:
                raise NaturalLotContractError(
                    "response-corrected relative fractions require RESPONSE_CORRECTED state"
                )
            if self.response_model_id is None:
                raise NaturalLotContractError(
                    "response-corrected relative fractions require response_model_id"
                )
        elif self.calibration_state in {
            CalibrationState.CALIBRATED,
            CalibrationState.RESPONSE_CORRECTED,
        }:
            raise NaturalLotContractError(
                "declared basis is incompatible with calibrated response authority"
            )
        elif self.response_model_id is not None:
            raise NaturalLotContractError(
                "response_model_id is only valid for calibrated or response-corrected bases"
            )

        object.__setattr__(
            self,
            "lower_bound",
            _optional_nonnegative(self.lower_bound, "lower_bound"),
        )
        object.__setattr__(
            self,
            "upper_bound",
            _optional_nonnegative(self.upper_bound, "upper_bound"),
        )
        if self.basis is ConstituentBasis.LITERATURE_RANGE:
            if self.value is not None:
                raise NaturalLotContractError(
                    "LITERATURE_RANGE cannot carry a fabricated point value"
                )
            if self.lower_bound is None or self.upper_bound is None:
                raise NaturalLotContractError(
                    "LITERATURE_RANGE requires lower_bound and upper_bound"
                )
            if self.lower_bound > self.upper_bound:
                raise NaturalLotContractError("lower_bound must not exceed upper_bound")
            object.__setattr__(self, "value", None)
        elif self.basis in {
            ConstituentBasis.PRESENCE_ONLY,
            ConstituentBasis.UNKNOWN,
        }:
            if (
                self.value is not None
                or self.lower_bound is not None
                or self.upper_bound is not None
            ):
                raise NaturalLotContractError(f"{self.basis.value} cannot carry numeric values")
            object.__setattr__(self, "value", None)
        else:
            if self.lower_bound is not None or self.upper_bound is not None:
                raise NaturalLotContractError(
                    "quantitative point observations cannot carry range bounds"
                )
            if self.censoring is CensoringState.NONE:
                if self.value is None:
                    raise NaturalLotContractError(
                        "uncensored quantitative observations require value"
                    )
                object.__setattr__(
                    self,
                    "value",
                    _validate_numeric_for_basis(self.value, self.basis, "value"),
                )
            elif self.value is not None:
                raise NaturalLotContractError("censored observations cannot carry a detected value")

        if self.censoring is CensoringState.BELOW_LOD and self.lod is None:
            raise NaturalLotContractError("BELOW_LOD requires LOD")
        if self.censoring is CensoringState.BELOW_LOQ and self.loq is None:
            raise NaturalLotContractError("BELOW_LOQ requires LOQ")
        if self.censoring is CensoringState.NOT_DETECTED and self.lod is None and self.loq is None:
            raise NaturalLotContractError("NOT_DETECTED requires LOD or LOQ")
        if (
            self.basis
            in {
                ConstituentBasis.PRESENCE_ONLY,
                ConstituentBasis.LITERATURE_RANGE,
                ConstituentBasis.UNKNOWN,
            }
            and self.censoring is not CensoringState.NONE
        ):
            raise NaturalLotContractError(
                "non-point observation bases cannot carry censoring state"
            )
        if self.origin is ObservationOrigin.EXACT_LOT_MEASURED:
            if self.source_lot_id is None:
                raise NaturalLotContractError("EXACT_LOT_MEASURED requires source_lot_id")
            if self.analytical_run_id is None:
                raise NaturalLotContractError("EXACT_LOT_MEASURED requires analytical_run_id")
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-constituent-observation-v1", self._payload()),
        )

    @property
    def supports_absolute_composition(self) -> bool:
        return self.basis in _ABSOLUTE_BASES

    def _payload(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "source_lot_id": self.source_lot_id,
            "chemical_id": self.chemical_id,
            "chemical_name": self.chemical_name,
            "identity_confidence": self.identity_confidence.value,
            "origin": self.origin.value,
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "basis": self.basis.value,
            "method_id": self.method_id,
            "calibration_state": self.calibration_state.value,
            "response_model_id": self.response_model_id,
            "standard_uncertainty": self.standard_uncertainty,
            "uncertainty_note": self.uncertainty_note,
            "lod": self.lod,
            "loq": self.loq,
            "censoring": self.censoring.value,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "analytical_run_id": self.analytical_run_id,
            "review_state": self.review_state.value,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> ConstituentObservation:
        payload = _mapping(value, "constituent observation")
        expected = {
            "observation_id",
            "source_lot_id",
            "chemical_id",
            "chemical_name",
            "identity_confidence",
            "origin",
            "value",
            "lower_bound",
            "upper_bound",
            "basis",
            "method_id",
            "calibration_state",
            "response_model_id",
            "standard_uncertainty",
            "uncertainty_note",
            "lod",
            "loq",
            "censoring",
            "source_id",
            "source_sha256",
            "analytical_run_id",
            "review_state",
            "content_sha256",
        }
        _exact_keys(payload, expected, "constituent observation")
        item = cls(
            observation_id=payload["observation_id"],
            source_lot_id=payload["source_lot_id"],
            chemical_id=payload["chemical_id"],
            chemical_name=payload["chemical_name"],
            identity_confidence=_enum_value(
                IdentityConfidence,
                payload["identity_confidence"],
                "identity_confidence",
            ),
            origin=_enum_value(ObservationOrigin, payload["origin"], "origin"),
            value=payload["value"],
            lower_bound=payload["lower_bound"],
            upper_bound=payload["upper_bound"],
            basis=_enum_value(ConstituentBasis, payload["basis"], "basis"),
            method_id=payload["method_id"],
            calibration_state=_enum_value(
                CalibrationState,
                payload["calibration_state"],
                "calibration_state",
            ),
            response_model_id=payload["response_model_id"],
            standard_uncertainty=payload["standard_uncertainty"],
            uncertainty_note=payload["uncertainty_note"],
            lod=payload["lod"],
            loq=payload["loq"],
            censoring=_enum_value(
                CensoringState,
                payload["censoring"],
                "censoring",
            ),
            source_id=payload["source_id"],
            source_sha256=payload["source_sha256"],
            analytical_run_id=payload["analytical_run_id"],
            review_state=_enum_value(
                ReviewState,
                payload["review_state"],
                "review_state",
            ),
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class UnresolvedFractionObservation:
    observation_id: str
    source_lot_id: str | None
    kind: UnresolvedFractionKind
    value: float | None
    basis: ConstituentBasis
    limit_value: float | None
    method_id: str
    source_id: str
    source_sha256: str
    analytical_run_id: str | None
    notes: tuple[str, ...]
    review_state: ReviewState
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "method_id", "source_id"):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "source_lot_id",
            _optional_text(self.source_lot_id, "source_lot_id"),
        )
        object.__setattr__(
            self,
            "analytical_run_id",
            _optional_text(self.analytical_run_id, "analytical_run_id"),
        )
        object.__setattr__(
            self,
            "kind",
            _direct_enum(UnresolvedFractionKind, self.kind, "kind"),
        )
        object.__setattr__(
            self,
            "basis",
            _direct_enum(ConstituentBasis, self.basis, "basis"),
        )
        object.__setattr__(
            self,
            "review_state",
            _direct_enum(ReviewState, self.review_state, "review_state"),
        )
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(self, "notes", _strings(self.notes, "notes"))
        object.__setattr__(
            self,
            "limit_value",
            _optional_nonnegative(self.limit_value, "limit_value"),
        )

        if self.kind is UnresolvedFractionKind.BELOW_QUANTITATION:
            if self.value is not None or self.limit_value is None:
                raise NaturalLotContractError(
                    "BELOW_QUANTITATION requires limit_value and no detected value"
                )
            object.__setattr__(self, "value", None)
        elif self.kind is UnresolvedFractionKind.UNIDENTIFIED_GC_O_EVENT:
            if self.basis is not ConstituentBasis.PRESENCE_ONLY or self.value is not None:
                raise NaturalLotContractError(
                    "UNIDENTIFIED_GC_O_EVENT requires PRESENCE_ONLY and no value"
                )
            if self.limit_value is not None:
                raise NaturalLotContractError("UNIDENTIFIED_GC_O_EVENT cannot carry limit_value")
            object.__setattr__(self, "value", None)
        else:
            if self.value is None:
                raise NaturalLotContractError("quantified unresolved composition requires value")
            if self.basis in {
                ConstituentBasis.PRESENCE_ONLY,
                ConstituentBasis.LITERATURE_RANGE,
                ConstituentBasis.UNKNOWN,
            }:
                raise NaturalLotContractError(
                    "unresolved quantitative value requires a quantitative basis"
                )
            object.__setattr__(
                self,
                "value",
                _validate_numeric_for_basis(self.value, self.basis, "value"),
            )
            if self.limit_value is not None:
                raise NaturalLotContractError(
                    "non-censored unresolved observations cannot carry limit_value"
                )
        if self.kind is UnresolvedFractionKind.UNASSIGNED_MASS and self.basis not in {
            ConstituentBasis.CALIBRATED_MASS_FRACTION,
            ConstituentBasis.ESTIMATED_MASS_FRACTION,
        }:
            raise NaturalLotContractError("UNASSIGNED_MASS requires a mass-fraction basis")
        if (
            self.kind is UnresolvedFractionKind.UNASSIGNED_AREA
            and self.basis is not ConstituentBasis.NORMALIZED_AREA_PERCENT
        ):
            raise NaturalLotContractError("UNASSIGNED_AREA requires NORMALIZED_AREA_PERCENT")
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-unresolved-fraction-observation-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "source_lot_id": self.source_lot_id,
            "kind": self.kind.value,
            "value": self.value,
            "basis": self.basis.value,
            "limit_value": self.limit_value,
            "method_id": self.method_id,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "analytical_run_id": self.analytical_run_id,
            "notes": list(self.notes),
            "review_state": self.review_state.value,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> UnresolvedFractionObservation:
        payload = _mapping(value, "unresolved fraction observation")
        expected = {
            "observation_id",
            "source_lot_id",
            "kind",
            "value",
            "basis",
            "limit_value",
            "method_id",
            "source_id",
            "source_sha256",
            "analytical_run_id",
            "notes",
            "review_state",
            "content_sha256",
        }
        _exact_keys(payload, expected, "unresolved fraction observation")
        item = cls(
            observation_id=payload["observation_id"],
            source_lot_id=payload["source_lot_id"],
            kind=_enum_value(UnresolvedFractionKind, payload["kind"], "kind"),
            value=payload["value"],
            basis=_enum_value(ConstituentBasis, payload["basis"], "basis"),
            limit_value=payload["limit_value"],
            method_id=payload["method_id"],
            source_id=payload["source_id"],
            source_sha256=payload["source_sha256"],
            analytical_run_id=payload["analytical_run_id"],
            notes=_sequence(payload["notes"], "notes"),
            review_state=_enum_value(
                ReviewState,
                payload["review_state"],
                "review_state",
            ),
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class UnresolvedFractionDisclosure:
    state: UnresolvedDisclosureState
    observations: tuple[UnresolvedFractionObservation, ...]
    review_method_id: str | None
    source_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "state",
            _direct_enum(UnresolvedDisclosureState, self.state, "state"),
        )
        object.__setattr__(
            self,
            "review_method_id",
            _optional_text(self.review_method_id, "review_method_id"),
        )
        object.__setattr__(self, "source_ids", _strings(self.source_ids, "source_ids"))
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "limitations"),
        )
        observations = tuple(self.observations)
        if any(not isinstance(item, UnresolvedFractionObservation) for item in observations):
            raise NaturalLotContractError(
                "observations must contain UnresolvedFractionObservation values"
            )
        ids = tuple(item.observation_id for item in observations)
        if len(ids) != len(set(ids)):
            raise NaturalLotContractError(
                "unresolved disclosure contains duplicate observation IDs"
            )
        object.__setattr__(
            self,
            "observations",
            tuple(sorted(observations, key=lambda item: item.observation_id)),
        )
        if self.state is UnresolvedDisclosureState.PRESENT:
            if not observations:
                raise NaturalLotContractError("PRESENT unresolved disclosure requires observations")
            if self.review_method_id is None:
                raise NaturalLotContractError(
                    "PRESENT unresolved disclosure requires review_method_id"
                )
        elif self.state is UnresolvedDisclosureState.NOT_REPORTED:
            if observations or self.review_method_id is not None:
                raise NaturalLotContractError(
                    "NOT_REPORTED unresolved disclosure has no observations or review method"
                )
        else:
            if observations:
                raise NaturalLotContractError("REVIEWED_NONE_OBSERVED cannot contain observations")
            if self.review_method_id is None:
                raise NaturalLotContractError("REVIEWED_NONE_OBSERVED requires review_method_id")
            if not self.source_ids:
                raise NaturalLotContractError("REVIEWED_NONE_OBSERVED requires source_ids")
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-unresolved-fraction-disclosure-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "observations": [item.to_mapping() for item in self.observations],
            "review_method_id": self.review_method_id,
            "source_ids": list(self.source_ids),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> UnresolvedFractionDisclosure:
        payload = _mapping(value, "unresolved fraction disclosure")
        _exact_keys(
            payload,
            {
                "state",
                "observations",
                "review_method_id",
                "source_ids",
                "limitations",
                "content_sha256",
            },
            "unresolved fraction disclosure",
        )
        item = cls(
            state=_enum_value(
                UnresolvedDisclosureState,
                payload["state"],
                "state",
            ),
            observations=tuple(
                UnresolvedFractionObservation.from_mapping(row)
                for row in _sequence(payload["observations"], "observations")
            ),
            review_method_id=payload["review_method_id"],
            source_ids=_sequence(payload["source_ids"], "source_ids"),
            limitations=_sequence(payload["limitations"], "limitations"),
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class NaturalCompositionProfile:
    profile_id: str
    schema_version: str
    profile_version: int
    parent_profile_sha256: str | None
    material_id: str
    lot_id: str | None
    supplier_product: str | None
    supplier_lot: str | None
    botanical_species: str | None
    variety_or_chemotype: str | None
    geographic_origin: str | None
    extraction_method: str | None
    authority: CompositionAuthority
    completeness: NaturalCompositionCompleteness
    observations: tuple[ConstituentObservation, ...]
    unresolved: UnresolvedFractionDisclosure
    source_documents: tuple[SourceDocumentReference, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in ("profile_id", "schema_version", "material_id"):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        if self.schema_version != "c7-natural-composition-v1":
            raise NaturalLotContractError("schema_version must be c7-natural-composition-v1")
        object.__setattr__(
            self,
            "profile_version",
            _positive_integer(self.profile_version, "profile_version"),
        )
        object.__setattr__(
            self,
            "parent_profile_sha256",
            _optional_sha256(
                self.parent_profile_sha256,
                "parent_profile_sha256",
            ),
        )
        if self.profile_version == 1 and self.parent_profile_sha256 is not None:
            raise NaturalLotContractError("first profile version cannot have parent_profile_sha256")
        if self.profile_version > 1 and self.parent_profile_sha256 is None:
            raise NaturalLotContractError("later profile versions require parent_profile_sha256")
        for field_name in (
            "lot_id",
            "supplier_product",
            "supplier_lot",
            "botanical_species",
            "variety_or_chemotype",
            "geographic_origin",
            "extraction_method",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "authority",
            _direct_enum(CompositionAuthority, self.authority, "authority"),
        )
        object.__setattr__(
            self,
            "completeness",
            _direct_enum(
                NaturalCompositionCompleteness,
                self.completeness,
                "completeness",
            ),
        )
        if not isinstance(self.unresolved, UnresolvedFractionDisclosure):
            raise NaturalLotContractError("unresolved must be an UnresolvedFractionDisclosure")
        observations = tuple(self.observations)
        if any(not isinstance(item, ConstituentObservation) for item in observations):
            raise NaturalLotContractError("observations must contain ConstituentObservation values")
        observation_ids = tuple(item.observation_id for item in observations)
        if len(observation_ids) != len(set(observation_ids)):
            raise NaturalLotContractError("observations contains duplicate IDs")
        object.__setattr__(
            self,
            "observations",
            tuple(sorted(observations, key=lambda item: item.observation_id)),
        )
        documents = tuple(self.source_documents)
        if any(not isinstance(item, SourceDocumentReference) for item in documents):
            raise NaturalLotContractError(
                "source_documents must contain SourceDocumentReference values"
            )
        document_ids = tuple(item.document_id for item in documents)
        if len(document_ids) != len(set(document_ids)):
            raise NaturalLotContractError("source_documents contains duplicate IDs")
        object.__setattr__(
            self,
            "source_documents",
            tuple(sorted(documents, key=lambda item: item.document_id)),
        )
        object.__setattr__(self, "assumptions", _strings(self.assumptions, "assumptions"))
        object.__setattr__(self, "limitations", _strings(self.limitations, "limitations"))

        if self.authority in {
            CompositionAuthority.EXACT_LOT_QUANTIFIED,
            CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
        }:
            if self.lot_id is None:
                raise NaturalLotContractError("exact lot authority requires lot_id")
            if not observations:
                raise NaturalLotContractError("exact lot authority requires observations")
            if any(item.source_lot_id != self.lot_id for item in observations):
                raise NaturalLotContractError(
                    "every exact lot observation must match the exact lot"
                )
            if any(item.subject_lot_id != self.lot_id for item in documents):
                raise NaturalLotContractError(
                    "every exact lot source document must match the exact lot"
                )
            if self.authority is CompositionAuthority.EXACT_LOT_QUANTIFIED:
                if not any(item.supports_absolute_composition for item in observations):
                    raise NaturalLotContractError(
                        "EXACT_LOT_QUANTIFIED requires quantified calibrated composition"
                    )
            elif any(item.supports_absolute_composition for item in observations) or not any(
                item.basis in _RELATIVE_BASES for item in observations
            ):
                raise NaturalLotContractError(
                    "EXACT_LOT_RELATIVE_PROFILE requires relative observations only"
                )
        elif self.authority is CompositionAuthority.SUPPLIER_BATCH_SPECIFIC:
            if self.lot_id is not None:
                raise NaturalLotContractError(
                    "supplier batch profile must not claim an exact repository lot"
                )
            if self.supplier_product is None or self.supplier_lot is None:
                raise NaturalLotContractError(
                    "supplier batch authority requires supplier product and supplier lot"
                )
            if not observations:
                raise NaturalLotContractError("supplier batch authority requires observations")
            if any(
                item.origin is not ObservationOrigin.SUPPLIER_BATCH_REPORTED
                or item.source_lot_id != self.supplier_lot
                for item in observations
            ):
                raise NaturalLotContractError(
                    "supplier batch observations must match supplier lot and origin"
                )
            if any(item.subject_lot_id != self.supplier_lot for item in documents):
                raise NaturalLotContractError(
                    "supplier batch source documents must match supplier lot"
                )
        elif self.authority is CompositionAuthority.SPECIFIC_LITERATURE_PROXY:
            if self.lot_id is not None or self.supplier_lot is not None:
                raise NaturalLotContractError(
                    "specific proxy cannot claim exact lot or supplier batch authority"
                )
            if self.botanical_species is None or self.extraction_method is None:
                raise NaturalLotContractError(
                    "specific proxy requires botanical_species and extraction_method"
                )
            if not observations or any(
                item.origin is not ObservationOrigin.LITERATURE_REPORTED for item in observations
            ):
                raise NaturalLotContractError(
                    "specific proxy requires literature-reported observations"
                )
        elif self.authority is CompositionAuthority.GENERIC_MATERIAL_PROXY:
            if any(
                value is not None
                for value in (
                    self.lot_id,
                    self.supplier_product,
                    self.supplier_lot,
                    self.botanical_species,
                    self.variety_or_chemotype,
                    self.geographic_origin,
                    self.extraction_method,
                )
            ):
                raise NaturalLotContractError(
                    "generic proxy cannot claim lot, batch, or specific botanical scope"
                )
            if not observations or any(
                item.origin is not ObservationOrigin.GENERIC_PROXY for item in observations
            ):
                raise NaturalLotContractError("generic proxy requires generic-proxy observations")
        else:
            if observations:
                raise NaturalLotContractError(
                    "UNKNOWN composition cannot contain answer-bearing observations"
                )
            if self.completeness is not NaturalCompositionCompleteness.UNKNOWN:
                raise NaturalLotContractError("UNKNOWN composition requires UNKNOWN completeness")
        if (
            self.authority is not CompositionAuthority.UNKNOWN
            and self.completeness is NaturalCompositionCompleteness.UNKNOWN
        ):
            raise NaturalLotContractError(
                "known composition authority requires COMPLETE or PARTIAL completeness"
            )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-natural-composition-profile-v1", self._payload()),
        )

    @property
    def named_totals_by_basis(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for observation in self.observations:
            if observation.value is None:
                continue
            key = observation.basis.value
            totals[key] = totals.get(key, 0.0) + observation.value
        return dict(sorted(totals.items()))

    def _payload(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "schema_version": self.schema_version,
            "profile_version": self.profile_version,
            "parent_profile_sha256": self.parent_profile_sha256,
            "material_id": self.material_id,
            "lot_id": self.lot_id,
            "supplier_product": self.supplier_product,
            "supplier_lot": self.supplier_lot,
            "botanical_species": self.botanical_species,
            "variety_or_chemotype": self.variety_or_chemotype,
            "geographic_origin": self.geographic_origin,
            "extraction_method": self.extraction_method,
            "authority": self.authority.value,
            "completeness": self.completeness.value,
            "observations": [item.to_mapping() for item in self.observations],
            "unresolved": self.unresolved.to_mapping(),
            "source_documents": [item.to_mapping() for item in self.source_documents],
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> NaturalCompositionProfile:
        payload = _mapping(value, "natural composition profile")
        expected = {
            "profile_id",
            "schema_version",
            "profile_version",
            "parent_profile_sha256",
            "material_id",
            "lot_id",
            "supplier_product",
            "supplier_lot",
            "botanical_species",
            "variety_or_chemotype",
            "geographic_origin",
            "extraction_method",
            "authority",
            "completeness",
            "observations",
            "unresolved",
            "source_documents",
            "assumptions",
            "limitations",
            "content_sha256",
        }
        _exact_keys(payload, expected, "natural composition profile")
        item = cls(
            profile_id=payload["profile_id"],
            schema_version=payload["schema_version"],
            profile_version=payload["profile_version"],
            parent_profile_sha256=payload["parent_profile_sha256"],
            material_id=payload["material_id"],
            lot_id=payload["lot_id"],
            supplier_product=payload["supplier_product"],
            supplier_lot=payload["supplier_lot"],
            botanical_species=payload["botanical_species"],
            variety_or_chemotype=payload["variety_or_chemotype"],
            geographic_origin=payload["geographic_origin"],
            extraction_method=payload["extraction_method"],
            authority=_enum_value(
                CompositionAuthority,
                payload["authority"],
                "authority",
            ),
            completeness=_enum_value(
                NaturalCompositionCompleteness,
                payload["completeness"],
                "completeness",
            ),
            observations=tuple(
                ConstituentObservation.from_mapping(row)
                for row in _sequence(payload["observations"], "observations")
            ),
            unresolved=UnresolvedFractionDisclosure.from_mapping(payload["unresolved"]),
            source_documents=tuple(
                SourceDocumentReference.from_mapping(row)
                for row in _sequence(payload["source_documents"], "source_documents")
            ),
            assumptions=_sequence(payload["assumptions"], "assumptions"),
            limitations=_sequence(payload["limitations"], "limitations"),
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


@dataclass(frozen=True, slots=True)
class NaturalCompositionRequest:
    material_id: str
    requested_lot_id: str
    supplier_product: str
    supplier_lot: str
    botanical_species: str | None
    variety_or_chemotype: str | None
    geographic_origin: str | None
    extraction_method: str | None
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "material_id",
            "requested_lot_id",
            "supplier_product",
            "supplier_lot",
        ):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        for field_name in (
            "botanical_species",
            "variety_or_chemotype",
            "geographic_origin",
            "extraction_method",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-natural-composition-request-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "material_id": self.material_id,
            "requested_lot_id": self.requested_lot_id,
            "supplier_product": self.supplier_product,
            "supplier_lot": self.supplier_lot,
            "botanical_species": self.botanical_species,
            "variety_or_chemotype": self.variety_or_chemotype,
            "geographic_origin": self.geographic_origin,
            "extraction_method": self.extraction_method,
        }

    @classmethod
    def from_lot(cls, lot: NaturalMaterialLot) -> NaturalCompositionRequest:
        if not isinstance(lot, NaturalMaterialLot):
            raise NaturalLotContractError("lot must be a NaturalMaterialLot")
        return cls(
            material_id=lot.material_id,
            requested_lot_id=lot.lot_id,
            supplier_product=lot.supplier_product,
            supplier_lot=lot.supplier_lot,
            botanical_species=lot.botanical_species,
            variety_or_chemotype=lot.variety_or_chemotype,
            geographic_origin=lot.geographic_origin,
            extraction_method=lot.extraction_method,
        )


@dataclass(frozen=True, slots=True)
class NaturalCompositionSelection:
    request_sha256: str
    status: SelectionStatus
    selected_profile: NaturalCompositionProfile | None
    selected_authority: CompositionAuthority
    precedence_rank: int
    fallback_steps: int
    uncertainty_widened: bool
    warnings: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_sha256",
            _sha256(self.request_sha256, "request_sha256"),
        )
        object.__setattr__(
            self,
            "status",
            _direct_enum(SelectionStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "selected_authority",
            _direct_enum(
                CompositionAuthority,
                self.selected_authority,
                "selected_authority",
            ),
        )
        object.__setattr__(
            self,
            "precedence_rank",
            _positive_integer(self.precedence_rank, "precedence_rank"),
        )
        if isinstance(self.fallback_steps, bool) or not isinstance(self.fallback_steps, int):
            raise NaturalLotContractError("fallback_steps must be an integer")
        if self.fallback_steps < 0:
            raise NaturalLotContractError("fallback_steps must be nonnegative")
        object.__setattr__(self, "warnings", _strings(self.warnings, "warnings"))
        if self.status is SelectionStatus.SELECTED:
            if not isinstance(self.selected_profile, NaturalCompositionProfile):
                raise NaturalLotContractError("SELECTED requires selected_profile")
            if self.selected_authority is not self.selected_profile.authority:
                raise NaturalLotContractError("selected_authority must match selected_profile")
            expected_rank = C7_COMPOSITION_PRECEDENCE.index(self.selected_authority) + 1
            if self.precedence_rank != expected_rank:
                raise NaturalLotContractError("precedence_rank does not match authority")
            if self.fallback_steps != expected_rank - 1:
                raise NaturalLotContractError("fallback_steps does not match authority loss")
            if self.uncertainty_widened is not (expected_rank > 1):
                raise NaturalLotContractError(
                    "uncertainty_widened must disclose fallback authority loss"
                )
            if expected_rank > 1 and not self.warnings:
                raise NaturalLotContractError("fallback selection requires warnings")
        else:
            if self.selected_profile is not None:
                raise NaturalLotContractError("non-selected result cannot contain selected_profile")
            if self.selected_authority is not CompositionAuthority.UNKNOWN:
                raise NaturalLotContractError("non-selected result must use UNKNOWN authority")
            if self.precedence_rank != len(C7_COMPOSITION_PRECEDENCE):
                raise NaturalLotContractError(
                    "non-selected result must use UNKNOWN precedence rank"
                )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-natural-composition-selection-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "request_sha256": self.request_sha256,
            "status": self.status.value,
            "selected_profile": (
                self.selected_profile.to_mapping() if self.selected_profile is not None else None
            ),
            "selected_authority": self.selected_authority.value,
            "precedence_rank": self.precedence_rank,
            "fallback_steps": self.fallback_steps,
            "uncertainty_widened": self.uncertainty_widened,
            "warnings": list(self.warnings),
        }


def _profile_matches(
    request: NaturalCompositionRequest,
    profile: NaturalCompositionProfile,
) -> bool:
    if profile.material_id != request.material_id:
        return False
    if profile.authority in {
        CompositionAuthority.EXACT_LOT_QUANTIFIED,
        CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
    }:
        return profile.lot_id == request.requested_lot_id
    if profile.authority is CompositionAuthority.SUPPLIER_BATCH_SPECIFIC:
        return (
            profile.supplier_product == request.supplier_product
            and profile.supplier_lot == request.supplier_lot
        )
    if profile.authority is CompositionAuthority.SPECIFIC_LITERATURE_PROXY:
        fields = (
            "botanical_species",
            "variety_or_chemotype",
            "geographic_origin",
            "extraction_method",
        )
        return all(
            getattr(profile, field_name) is None
            or getattr(profile, field_name) == getattr(request, field_name)
            for field_name in fields
        )
    return profile.authority is CompositionAuthority.GENERIC_MATERIAL_PROXY


def select_natural_composition(
    request: NaturalCompositionRequest,
    profiles: Sequence[NaturalCompositionProfile],
) -> NaturalCompositionSelection:
    """Select one exact profile by fixed authority, or abstain on ambiguity."""

    if not isinstance(request, NaturalCompositionRequest):
        raise NaturalLotContractError("request must be a NaturalCompositionRequest")
    candidates = tuple(profiles)
    if any(not isinstance(item, NaturalCompositionProfile) for item in candidates):
        raise NaturalLotContractError("profiles must contain NaturalCompositionProfile values")
    matching = tuple(
        item
        for item in candidates
        if item.authority is not CompositionAuthority.UNKNOWN and _profile_matches(request, item)
    )
    if not matching:
        return NaturalCompositionSelection(
            request_sha256=request.content_sha256,
            status=SelectionStatus.ABSTAINED,
            selected_profile=None,
            selected_authority=CompositionAuthority.UNKNOWN,
            precedence_rank=len(C7_COMPOSITION_PRECEDENCE),
            fallback_steps=len(C7_COMPOSITION_PRECEDENCE) - 1,
            uncertainty_widened=True,
            warnings=("No admissible composition profile; authority is UNKNOWN.",),
        )
    best_rank = min(C7_COMPOSITION_PRECEDENCE.index(item.authority) for item in matching)
    best = tuple(
        sorted(
            (
                item
                for item in matching
                if C7_COMPOSITION_PRECEDENCE.index(item.authority) == best_rank
            ),
            key=lambda item: (item.profile_id, item.content_sha256),
        )
    )
    if len(best) != 1:
        return NaturalCompositionSelection(
            request_sha256=request.content_sha256,
            status=SelectionStatus.AMBIGUOUS,
            selected_profile=None,
            selected_authority=CompositionAuthority.UNKNOWN,
            precedence_rank=len(C7_COMPOSITION_PRECEDENCE),
            fallback_steps=len(C7_COMPOSITION_PRECEDENCE) - 1,
            uncertainty_widened=True,
            warnings=("Multiple equal-authority profiles disagree; selection abstained.",),
        )
    selected = best[0]
    rank = best_rank + 1
    warnings = (
        ()
        if rank == 1
        else (
            f"Fallback to {selected.authority.value} lowered authority by {rank - 1} level(s).",
            "Uncertainty category is widened; no numerical coverage is implied.",
        )
    )
    return NaturalCompositionSelection(
        request_sha256=request.content_sha256,
        status=SelectionStatus.SELECTED,
        selected_profile=selected,
        selected_authority=selected.authority,
        precedence_rank=rank,
        fallback_steps=rank - 1,
        uncertainty_widened=rank > 1,
        warnings=warnings,
    )


@dataclass(frozen=True, slots=True)
class ProjectionEntry:
    observation_id: str
    source_observation_sha256: str
    source_basis: ConstituentBasis
    source_lot_id: str | None
    chemical_id: str
    chemical_name: str
    value: float | None
    lower_bound: float | None
    upper_bound: float | None
    basis: ConstituentBasis
    source_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "chemical_id", "chemical_name"):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "source_observation_sha256",
            _sha256(
                self.source_observation_sha256,
                "source_observation_sha256",
            ),
        )
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(
            self,
            "source_lot_id",
            _optional_text(self.source_lot_id, "source_lot_id"),
        )
        object.__setattr__(
            self,
            "source_basis",
            _direct_enum(ConstituentBasis, self.source_basis, "source_basis"),
        )
        object.__setattr__(
            self,
            "basis",
            _direct_enum(ConstituentBasis, self.basis, "basis"),
        )
        if self.basis is not self.source_basis:
            raise NaturalLotContractError("projection basis must match source observation basis")
        for field_name in ("value", "lower_bound", "upper_bound"):
            raw = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                _finite(raw, field_name) if raw is not None else None,
            )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-projection-entry-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "source_observation_sha256": self.source_observation_sha256,
            "source_basis": self.source_basis.value,
            "source_lot_id": self.source_lot_id,
            "chemical_id": self.chemical_id,
            "chemical_name": self.chemical_name,
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "basis": self.basis.value,
            "source_sha256": self.source_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class NaturalProjection:
    projection_version: str
    family: ProjectionFamily
    status: ProjectionStatus
    profile_id: str
    profile_sha256: str
    authority: CompositionAuthority
    entries: tuple[ProjectionEntry, ...]
    unresolved_disclosure_sha256: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "projection_version",
            _nonblank(self.projection_version, "projection_version"),
        )
        object.__setattr__(self, "profile_id", _nonblank(self.profile_id, "profile_id"))
        object.__setattr__(self, "profile_sha256", _sha256(self.profile_sha256, "profile_sha256"))
        object.__setattr__(
            self,
            "unresolved_disclosure_sha256",
            _sha256(
                self.unresolved_disclosure_sha256,
                "unresolved_disclosure_sha256",
            ),
        )
        object.__setattr__(
            self,
            "family",
            _direct_enum(ProjectionFamily, self.family, "family"),
        )
        object.__setattr__(
            self,
            "status",
            _direct_enum(ProjectionStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "authority",
            _direct_enum(CompositionAuthority, self.authority, "authority"),
        )
        entries = tuple(self.entries)
        if any(not isinstance(item, ProjectionEntry) for item in entries):
            raise NaturalLotContractError("entries must contain ProjectionEntry values")
        ids = tuple(item.observation_id for item in entries)
        if len(ids) != len(set(ids)):
            raise NaturalLotContractError("projection entries contains duplicate IDs")
        object.__setattr__(
            self,
            "entries",
            tuple(sorted(entries, key=lambda item: item.observation_id)),
        )
        object.__setattr__(
            self,
            "assumptions",
            _strings(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "limitations"),
        )
        if self.status is ProjectionStatus.AVAILABLE and not entries:
            raise NaturalLotContractError("AVAILABLE projection requires entries")
        if self.status is ProjectionStatus.WITHHELD and entries:
            raise NaturalLotContractError("WITHHELD projection cannot contain entries")
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-natural-projection-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "projection_version": self.projection_version,
            "family": self.family.value,
            "status": self.status.value,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "authority": self.authority.value,
            "entries": [item.to_mapping() for item in self.entries],
            "unresolved_disclosure_sha256": self.unresolved_disclosure_sha256,
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }


def _projection_entry(observation: ConstituentObservation) -> ProjectionEntry:
    return ProjectionEntry(
        observation_id=observation.observation_id,
        source_observation_sha256=observation.content_sha256,
        source_basis=observation.basis,
        source_lot_id=observation.source_lot_id,
        chemical_id=observation.chemical_id,
        chemical_name=observation.chemical_name,
        value=observation.value,
        lower_bound=observation.lower_bound,
        upper_bound=observation.upper_bound,
        basis=observation.basis,
        source_sha256=observation.source_sha256,
    )


def build_natural_projection(
    profile: NaturalCompositionProfile,
    family: ProjectionFamily,
    *,
    projection_version: str = "c7-natural-projection-v1",
) -> NaturalProjection:
    """Build one family-specific projection without changing any basis."""

    if not isinstance(profile, NaturalCompositionProfile):
        raise NaturalLotContractError("profile must be a NaturalCompositionProfile")
    family = _direct_enum(ProjectionFamily, family, "family")
    limitations = list(profile.limitations)
    assumptions = [*profile.assumptions, "NO_BASIS_CONVERSION"]
    observations: tuple[ConstituentObservation, ...]
    status = ProjectionStatus.AVAILABLE
    if family is ProjectionFamily.REGULATORY_ALLERGEN:
        eligible_authority = profile.authority in {
            CompositionAuthority.EXACT_LOT_QUANTIFIED,
            CompositionAuthority.SUPPLIER_BATCH_SPECIFIC,
        }
        eligible = (
            eligible_authority
            and profile.completeness is NaturalCompositionCompleteness.COMPLETE
            and profile.unresolved.state is UnresolvedDisclosureState.REVIEWED_NONE_OBSERVED
            and bool(profile.observations)
            and all(
                item.basis is ConstituentBasis.CALIBRATED_MASS_FRACTION
                for item in profile.observations
            )
        )
        if eligible:
            observations = profile.observations
        else:
            observations = ()
            status = ProjectionStatus.WITHHELD
            limitations.append(
                "Regulatory projection requires complete exact-lot or supplier-batch calibrated mass fractions with reviewed unresolved composition."
            )
    else:
        observations = tuple(
            item for item in profile.observations if item.basis is not ConstituentBasis.UNKNOWN
        )
        if not observations:
            status = ProjectionStatus.WITHHELD
            limitations.append("No basis-compatible observations are available.")
    entries = tuple(_projection_entry(item) for item in observations)
    return NaturalProjection(
        projection_version=projection_version,
        family=family,
        status=status,
        profile_id=profile.profile_id,
        profile_sha256=profile.content_sha256,
        authority=profile.authority,
        entries=entries,
        unresolved_disclosure_sha256=profile.unresolved.content_sha256,
        assumptions=tuple(assumptions),
        limitations=tuple(limitations),
    )


@dataclass(frozen=True, slots=True)
class AuthenticityReferenceRange:
    reference_id: str
    chemical_id: str
    basis: ConstituentBasis
    lower_bound: float
    upper_bound: float
    source_id: str
    source_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in ("reference_id", "chemical_id", "source_id"):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "basis",
            _direct_enum(ConstituentBasis, self.basis, "basis"),
        )
        if self.basis in {
            ConstituentBasis.PRESENCE_ONLY,
            ConstituentBasis.LITERATURE_RANGE,
            ConstituentBasis.UNKNOWN,
        }:
            raise NaturalLotContractError(
                "authenticity reference requires a quantitative comparison basis"
            )
        lower = _validate_numeric_for_basis(self.lower_bound, self.basis, "lower_bound")
        upper = _validate_numeric_for_basis(self.upper_bound, self.basis, "upper_bound")
        if lower > upper:
            raise NaturalLotContractError("lower_bound must not exceed upper_bound")
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-authenticity-reference-range-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "reference_id": self.reference_id,
            "chemical_id": self.chemical_id,
            "basis": self.basis.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class AuthenticityDeviation:
    chemical_id: str
    basis: ConstituentBasis
    observed_value: float
    lower_bound: float
    upper_bound: float
    direction: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chemical_id", _nonblank(self.chemical_id, "chemical_id"))
        object.__setattr__(
            self,
            "basis",
            _direct_enum(ConstituentBasis, self.basis, "basis"),
        )
        for field_name in ("observed_value", "lower_bound", "upper_bound"):
            object.__setattr__(
                self,
                field_name,
                _validate_numeric_for_basis(
                    getattr(self, field_name),
                    self.basis,
                    field_name,
                ),
            )
        if self.lower_bound > self.upper_bound:
            raise NaturalLotContractError("lower_bound must not exceed upper_bound")
        direction = _nonblank(self.direction, "direction")
        if direction not in {"BELOW", "ABOVE"}:
            raise NaturalLotContractError("direction must be BELOW or ABOVE")
        object.__setattr__(self, "direction", direction)
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-authenticity-deviation-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "chemical_id": self.chemical_id,
            "basis": self.basis.value,
            "observed_value": self.observed_value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "direction": self.direction,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class AuthenticityAssessment:
    profile_id: str
    profile_sha256: str
    decision: AuthenticityDecision
    reference_ranges: tuple[AuthenticityReferenceRange, ...]
    deviations: tuple[AuthenticityDeviation, ...]
    compared_observation_count: int
    expected_chemotype: str | None
    observed_chemotype: str | None
    possible_adulteration_indicators: tuple[str, ...]
    unresolved_disclosure_sha256: str
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _nonblank(self.profile_id, "profile_id"))
        object.__setattr__(self, "profile_sha256", _sha256(self.profile_sha256, "profile_sha256"))
        object.__setattr__(
            self,
            "unresolved_disclosure_sha256",
            _sha256(
                self.unresolved_disclosure_sha256,
                "unresolved_disclosure_sha256",
            ),
        )
        object.__setattr__(
            self,
            "decision",
            _direct_enum(AuthenticityDecision, self.decision, "decision"),
        )
        references = tuple(self.reference_ranges)
        deviations = tuple(self.deviations)
        if any(not isinstance(item, AuthenticityReferenceRange) for item in references):
            raise NaturalLotContractError(
                "reference_ranges must contain AuthenticityReferenceRange values"
            )
        if any(not isinstance(item, AuthenticityDeviation) for item in deviations):
            raise NaturalLotContractError("deviations must contain AuthenticityDeviation values")
        object.__setattr__(
            self,
            "reference_ranges",
            tuple(sorted(references, key=lambda item: item.reference_id)),
        )
        object.__setattr__(
            self,
            "deviations",
            tuple(sorted(deviations, key=lambda item: (item.chemical_id, item.basis.value))),
        )
        if (
            isinstance(self.compared_observation_count, bool)
            or not isinstance(self.compared_observation_count, int)
            or self.compared_observation_count < 0
        ):
            raise NaturalLotContractError(
                "compared_observation_count must be a nonnegative integer"
            )
        object.__setattr__(
            self,
            "expected_chemotype",
            _optional_text(self.expected_chemotype, "expected_chemotype"),
        )
        object.__setattr__(
            self,
            "observed_chemotype",
            _optional_text(self.observed_chemotype, "observed_chemotype"),
        )
        object.__setattr__(
            self,
            "possible_adulteration_indicators",
            _strings(
                self.possible_adulteration_indicators,
                "possible_adulteration_indicators",
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _strings(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-authenticity-assessment-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "decision": self.decision.value,
            "reference_ranges": [item.to_mapping() for item in self.reference_ranges],
            "deviations": [item.to_mapping() for item in self.deviations],
            "compared_observation_count": self.compared_observation_count,
            "expected_chemotype": self.expected_chemotype,
            "observed_chemotype": self.observed_chemotype,
            "possible_adulteration_indicators": list(self.possible_adulteration_indicators),
            "unresolved_disclosure_sha256": self.unresolved_disclosure_sha256,
            "limitations": list(self.limitations),
        }


def assess_authenticity_profile(
    profile: NaturalCompositionProfile,
    reference_ranges: Sequence[AuthenticityReferenceRange],
    *,
    expected_chemotype: str | None,
    observed_chemotype: str | None,
    possible_adulteration_indicators: Sequence[str],
    limitations: Sequence[str],
) -> AuthenticityAssessment:
    """Compare basis-compatible exact values without concentration conversion."""

    if not isinstance(profile, NaturalCompositionProfile):
        raise NaturalLotContractError("profile must be a NaturalCompositionProfile")
    references = tuple(reference_ranges)
    if any(not isinstance(item, AuthenticityReferenceRange) for item in references):
        raise NaturalLotContractError(
            "reference_ranges must contain AuthenticityReferenceRange values"
        )
    reference_ids = tuple(item.reference_id for item in references)
    if len(reference_ids) != len(set(reference_ids)):
        raise NaturalLotContractError("reference_ranges contains duplicate IDs")
    indicators = _strings(
        possible_adulteration_indicators,
        "possible_adulteration_indicators",
    )
    expected = _optional_text(expected_chemotype, "expected_chemotype")
    observed = _optional_text(observed_chemotype, "observed_chemotype")
    deviations: list[AuthenticityDeviation] = []
    compared = 0
    observations = {
        (item.chemical_id, item.basis): item
        for item in profile.observations
        if item.value is not None
    }
    for reference in references:
        observation = observations.get((reference.chemical_id, reference.basis))
        if observation is None or observation.value is None:
            continue
        compared += 1
        if observation.value < reference.lower_bound:
            deviations.append(
                AuthenticityDeviation(
                    chemical_id=observation.chemical_id,
                    basis=observation.basis,
                    observed_value=observation.value,
                    lower_bound=reference.lower_bound,
                    upper_bound=reference.upper_bound,
                    direction="BELOW",
                )
            )
        elif observation.value > reference.upper_bound:
            deviations.append(
                AuthenticityDeviation(
                    chemical_id=observation.chemical_id,
                    basis=observation.basis,
                    observed_value=observation.value,
                    lower_bound=reference.lower_bound,
                    upper_bound=reference.upper_bound,
                    direction="ABOVE",
                )
            )
    if indicators:
        decision = AuthenticityDecision.POSSIBLE_ADULTERATION_INDICATORS
    elif (
        expected is not None and observed is not None and expected.casefold() != observed.casefold()
    ):
        decision = AuthenticityDecision.CHEMOTYPE_MISMATCH
    elif deviations:
        decision = AuthenticityDecision.OUTSIDE_REFERENCE_PROFILE
    elif compared:
        decision = AuthenticityDecision.CONSISTENT_WITH_REFERENCE
    else:
        decision = AuthenticityDecision.INSUFFICIENT_EVIDENCE
    assessment_limitations = [
        *limitations,
        "Reference comparison preserves basis and does not establish absolute concentration or authenticity by itself.",
    ]
    if profile.authority not in {
        CompositionAuthority.EXACT_LOT_QUANTIFIED,
        CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
    }:
        decision = AuthenticityDecision.INSUFFICIENT_EVIDENCE
        assessment_limitations.append(
            "Authenticity assessment requires an exact-lot composition profile."
        )
    return AuthenticityAssessment(
        profile_id=profile.profile_id,
        profile_sha256=profile.content_sha256,
        decision=decision,
        reference_ranges=references,
        deviations=tuple(deviations),
        compared_observation_count=compared,
        expected_chemotype=expected,
        observed_chemotype=observed,
        possible_adulteration_indicators=indicators,
        unresolved_disclosure_sha256=profile.unresolved.content_sha256,
        limitations=tuple(assessment_limitations),
    )


@dataclass(frozen=True, slots=True)
class LotAgingObservation:
    observation_id: str
    lot_id: str
    sequence_number: int
    observed_at: datetime
    storage_conditions: tuple[str, ...]
    oxidation_stability_observations: tuple[str, ...]
    source_document_ids: tuple[str, ...]
    analytical_run_ids: tuple[str, ...]
    previous_observation_sha256: str | None
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _nonblank(self.observation_id, "observation_id"),
        )
        object.__setattr__(self, "lot_id", _nonblank(self.lot_id, "lot_id"))
        object.__setattr__(
            self,
            "sequence_number",
            _positive_integer(self.sequence_number, "sequence_number"),
        )
        object.__setattr__(
            self,
            "observed_at",
            _aware_datetime(self.observed_at, "observed_at"),
        )
        object.__setattr__(
            self,
            "storage_conditions",
            _strings(self.storage_conditions, "storage_conditions", allow_empty=False),
        )
        object.__setattr__(
            self,
            "oxidation_stability_observations",
            _strings(
                self.oxidation_stability_observations,
                "oxidation_stability_observations",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "source_document_ids",
            _strings(
                self.source_document_ids,
                "source_document_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "analytical_run_ids",
            _strings(
                self.analytical_run_ids,
                "analytical_run_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "previous_observation_sha256",
            _optional_sha256(
                self.previous_observation_sha256,
                "previous_observation_sha256",
            ),
        )
        if self.sequence_number == 1 and self.previous_observation_sha256 is not None:
            raise NaturalLotContractError(
                "first aging observation cannot have previous_observation_sha256"
            )
        if self.sequence_number > 1 and self.previous_observation_sha256 is None:
            raise NaturalLotContractError(
                "later aging observations require previous_observation_sha256"
            )
        object.__setattr__(
            self,
            "content_sha256",
            _hash("c7-lot-aging-observation-v1", self._payload()),
        )

    def _payload(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "lot_id": self.lot_id,
            "sequence_number": self.sequence_number,
            "observed_at": _datetime_text(self.observed_at),
            "storage_conditions": list(self.storage_conditions),
            "oxidation_stability_observations": list(self.oxidation_stability_observations),
            "source_document_ids": list(self.source_document_ids),
            "analytical_run_ids": list(self.analytical_run_ids),
            "previous_observation_sha256": self.previous_observation_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> LotAgingObservation:
        payload = _mapping(value, "lot aging observation")
        _exact_keys(
            payload,
            {
                "observation_id",
                "lot_id",
                "sequence_number",
                "observed_at",
                "storage_conditions",
                "oxidation_stability_observations",
                "source_document_ids",
                "analytical_run_ids",
                "previous_observation_sha256",
                "content_sha256",
            },
            "lot aging observation",
        )
        item = cls(
            observation_id=payload["observation_id"],
            lot_id=payload["lot_id"],
            sequence_number=payload["sequence_number"],
            observed_at=_parse_datetime(payload["observed_at"], "observed_at"),
            storage_conditions=_sequence(
                payload["storage_conditions"],
                "storage_conditions",
            ),
            oxidation_stability_observations=_sequence(
                payload["oxidation_stability_observations"],
                "oxidation_stability_observations",
            ),
            source_document_ids=_sequence(
                payload["source_document_ids"],
                "source_document_ids",
            ),
            analytical_run_ids=_sequence(
                payload["analytical_run_ids"],
                "analytical_run_ids",
            ),
            previous_observation_sha256=payload["previous_observation_sha256"],
        )
        _verify_content_hash(
            payload["content_sha256"],
            item.content_sha256,
            "content_sha256",
        )
        return item


def validate_aging_series(
    lot: NaturalMaterialLot,
    observations: Sequence[LotAgingObservation],
) -> tuple[LotAgingObservation, ...]:
    """Validate one chronological, hash-linked state series for an immutable lot."""

    if not isinstance(lot, NaturalMaterialLot):
        raise NaturalLotContractError("lot must be a NaturalMaterialLot")
    series = tuple(observations)
    if not series:
        raise NaturalLotContractError("aging series must not be empty")
    if any(not isinstance(item, LotAgingObservation) for item in series):
        raise NaturalLotContractError("observations must contain LotAgingObservation values")
    if any(item.lot_id != lot.lot_id for item in series):
        raise NaturalLotContractError("aging series cannot change lot identity")
    expected_sequences = tuple(range(1, len(series) + 1))
    if tuple(item.sequence_number for item in series) != expected_sequences:
        raise NaturalLotContractError("aging sequence numbers must be contiguous from one")
    if len({item.observation_id for item in series}) != len(series):
        raise NaturalLotContractError("aging series contains duplicate observation IDs")
    for previous, current in zip(series, series[1:]):
        if current.observed_at <= previous.observed_at:
            raise NaturalLotContractError("aging observation times must be strictly increasing")
        if current.previous_observation_sha256 != previous.content_sha256:
            raise NaturalLotContractError(
                "previous observation SHA-256 does not match the prior state"
            )
    return series


__all__ = [
    "C7_COMPOSITION_PRECEDENCE",
    "PERMITTED_CONSTITUENT_BASES",
    "AnalyticalRunReference",
    "AuthenticityAssessment",
    "AuthenticityDecision",
    "AuthenticityDeviation",
    "AuthenticityReferenceRange",
    "CalibrationState",
    "CensoringState",
    "CompositionAuthority",
    "ConstituentBasis",
    "ConstituentObservation",
    "IdentityConfidence",
    "LotAgingObservation",
    "NaturalCompositionCompleteness",
    "NaturalCompositionProfile",
    "NaturalCompositionRequest",
    "NaturalCompositionSelection",
    "NaturalLotContractError",
    "NaturalMaterialLot",
    "NaturalProjection",
    "ObservationOrigin",
    "ProjectionEntry",
    "ProjectionFamily",
    "ProjectionStatus",
    "ReviewState",
    "SelectionStatus",
    "SourceDocumentKind",
    "SourceDocumentReference",
    "UnresolvedDisclosureState",
    "UnresolvedFractionDisclosure",
    "UnresolvedFractionKind",
    "UnresolvedFractionObservation",
    "assess_authenticity_profile",
    "build_natural_projection",
    "select_natural_composition",
    "validate_aging_series",
]
