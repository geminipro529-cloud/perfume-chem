"""Fail-closed C5 experimental calibration and held-out evaluation contracts.

This module supplies a reproducible protocol/schema/analysis harness.  It does
not contain instrument measurements, import the legacy feedback calibration
pipeline, or grant empirical authority to simulated smoke-test values.
"""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash

C5_INVENTORY_SHA256 = "9d778721db1f5a0a10d1f278eeef9b7fab0bc73ce7f0d58b26c501be70fe0eb8"
LEAKAGE_DIMENSIONS = (
    "chemical_identity_group",
    "close_analog_group",
    "formula_id",
    "supplier_lot",
    "matrix_batch_id",
    "measurement_session_id",
)
REQUIRED_GROUP_DIMENSIONS = ("material_class", "matrix", "condition")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_CLOSURE_TOLERANCE = 1e-12


class CalibrationProgramContractError(ValueError):
    """A malformed, unbound, leaky, or authority-ineligible C5 record."""


class EmpiricalStatus(str, Enum):
    BLOCKED_PENDING_DATA = "BLOCKED_PENDING_DATA"
    READY_FOR_EVALUATION = "READY_FOR_EVALUATION"


class EvidenceOrigin(str, Enum):
    REAL_INSTRUMENT = "REAL_INSTRUMENT"
    SIMULATED_SMOKE = "SIMULATED_SMOKE"


class MatrixAvailability(str, Enum):
    OWNED_DECLARED = "OWNED_DECLARED"
    REQUIRES_DECLARED_SOURCE = "REQUIRES_DECLARED_SOURCE"


class Partition(str, Enum):
    CALIBRATION = "CALIBRATION"
    VALIDATION = "VALIDATION"
    HELD_OUT_TEST = "HELD_OUT_TEST"


class MetricScale(str, Enum):
    LINEAR = "LINEAR"
    LOG10 = "LOG10"


class MetricName(str, Enum):
    BIAS = "bias"
    MAE = "mae"
    RMSE = "rmse"
    MEDIAN_ABSOLUTE_FOLD_ERROR = "median_absolute_fold_error"
    RANK_AGREEMENT = "rank_agreement"
    CALIBRATION_SLOPE = "calibration_slope"
    CALIBRATION_INTERCEPT = "calibration_intercept"
    PREDICTION_INTERVAL_COVERAGE = "prediction_interval_coverage"
    CATASTROPHIC_OUTLIER_RATE = "catastrophic_outlier_rate"
    MISSING_DOMAIN_RATE = "missing_domain_rate"
    ABSTENTION_RATE = "abstention_rate"
    RMSE_IMPROVEMENT_VS_BASELINE = "rmse_improvement_vs_baseline"


REQUIRED_METRICS = tuple(MetricName)


class Comparator(str, Enum):
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"


class ObservationState(str, Enum):
    VALUE = "VALUE"
    ABSTAINED = "ABSTAINED"
    MISSING = "MISSING"


class ReportAuthority(str, Enum):
    REAL_INSTRUMENT_ONLY = "REAL_INSTRUMENT_ONLY"
    SIMULATION_ONLY = "SIMULATION_ONLY"


class EvaluationDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CalibrationProgramContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise CalibrationProgramContractError(f"{field_name} keys must be strings")
    return dict(value)


def _sequence(value: object, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CalibrationProgramContractError(f"{field_name} must be a sequence")
    return tuple(value)


def _exact_keys(payload: Mapping[str, Any], expected: set[str], field_name: str) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise CalibrationProgramContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise CalibrationProgramContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationProgramContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise CalibrationProgramContractError(f"{field_name} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise CalibrationProgramContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise CalibrationProgramContractError(f"{field_name} must be finite")
    return result


def _positive(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0.0:
        raise CalibrationProgramContractError(f"{field_name} must be positive")
    return result


def _nonnegative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CalibrationProgramContractError(f"{field_name} must be a nonnegative integer")
    return value


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise CalibrationProgramContractError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _aware_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CalibrationProgramContractError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _datetime_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, field_name: str) -> datetime:
    text = _nonblank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalibrationProgramContractError(f"{field_name} must be ISO-8601") from exc
    return _aware_datetime(parsed, field_name)


def _sorted_unique_strings(value: object, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    items = tuple(_nonblank(item, field_name) for item in _sequence(value, field_name))
    if not allow_empty and not items:
        raise CalibrationProgramContractError(f"{field_name} must not be empty")
    if len(items) != len(set(items)):
        raise CalibrationProgramContractError(f"{field_name} must not contain duplicates")
    return tuple(sorted(items, key=lambda item: (item.casefold(), item)))


@dataclass(frozen=True, slots=True)
class MaterialPanelEntry:
    inventory_name: str
    chemical_class: str
    stock_fraction: float
    stock_fraction_basis: str
    carrier: str
    coverage_tags: tuple[str, ...]
    feasibility_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "inventory_name", _nonblank(self.inventory_name, "inventory_name"))
        object.__setattr__(self, "chemical_class", _nonblank(self.chemical_class, "chemical_class"))
        fraction = _positive(self.stock_fraction, "stock_fraction")
        if fraction > 1.0:
            raise CalibrationProgramContractError("stock_fraction must not exceed one")
        object.__setattr__(self, "stock_fraction", fraction)
        object.__setattr__(self, "stock_fraction_basis", _nonblank(self.stock_fraction_basis, "stock_fraction_basis"))
        if not isinstance(self.carrier, str):
            raise CalibrationProgramContractError("carrier must be a string")
        object.__setattr__(self, "carrier", self.carrier.strip())
        object.__setattr__(self, "coverage_tags", _sorted_unique_strings(self.coverage_tags, "coverage_tags"))
        object.__setattr__(
            self,
            "feasibility_notes",
            _sorted_unique_strings(self.feasibility_notes, "feasibility_notes", allow_empty=True),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "inventory_name": self.inventory_name,
            "chemical_class": self.chemical_class,
            "stock_fraction": self.stock_fraction,
            "stock_fraction_basis": self.stock_fraction_basis,
            "carrier": self.carrier,
            "coverage_tags": list(self.coverage_tags),
            "feasibility_notes": list(self.feasibility_notes),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MaterialPanelEntry:
        normalized = _mapping(payload, "material panel entry")
        _exact_keys(
            normalized,
            {
                "inventory_name",
                "chemical_class",
                "stock_fraction",
                "stock_fraction_basis",
                "carrier",
                "coverage_tags",
                "feasibility_notes",
            },
            "material panel entry",
        )
        return cls(
            inventory_name=normalized["inventory_name"],
            chemical_class=normalized["chemical_class"],
            stock_fraction=normalized["stock_fraction"],
            stock_fraction_basis=normalized["stock_fraction_basis"],
            carrier=normalized["carrier"],
            coverage_tags=_sequence(normalized["coverage_tags"], "coverage_tags"),
            feasibility_notes=_sequence(normalized["feasibility_notes"], "feasibility_notes"),
        )


@dataclass(frozen=True, slots=True)
class MatrixComponent:
    component_id: str
    fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _nonblank(self.component_id, "component_id"))
        object.__setattr__(self, "fraction", _positive(self.fraction, "fraction"))

    def to_mapping(self) -> dict[str, object]:
        return {"component_id": self.component_id, "fraction": self.fraction}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MatrixComponent:
        normalized = _mapping(payload, "matrix component")
        _exact_keys(normalized, {"component_id", "fraction"}, "matrix component")
        return cls(component_id=normalized["component_id"], fraction=normalized["fraction"])


@dataclass(frozen=True, slots=True)
class MatrixPanelEntry:
    matrix_id: str
    label: str
    components: tuple[MatrixComponent, ...]
    availability: MatrixAvailability
    missing_sources: tuple[str, ...]
    coverage_tags: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "matrix_id", _nonblank(self.matrix_id, "matrix_id"))
        object.__setattr__(self, "label", _nonblank(self.label, "label"))
        components = _sequence(self.components, "components")
        if not components or any(not isinstance(item, MatrixComponent) for item in components):
            raise CalibrationProgramContractError("components must contain MatrixComponent values")
        identifiers = [item.component_id for item in components]
        if len(identifiers) != len(set(identifiers)):
            raise CalibrationProgramContractError("components contains duplicate component_id values")
        if abs(math.fsum(item.fraction for item in components) - 1.0) > _CLOSURE_TOLERANCE:
            raise CalibrationProgramContractError("matrix component fractions must sum to one")
        components = tuple(sorted(components, key=lambda item: (item.component_id.casefold(), item.component_id)))
        object.__setattr__(self, "components", components)
        try:
            availability = MatrixAvailability(self.availability)
        except ValueError as exc:
            raise CalibrationProgramContractError("availability is invalid") from exc
        object.__setattr__(self, "availability", availability)
        missing = _sorted_unique_strings(self.missing_sources, "missing_sources", allow_empty=True)
        if availability is MatrixAvailability.REQUIRES_DECLARED_SOURCE and not missing:
            raise CalibrationProgramContractError("missing_sources is required for unavailable matrix")
        if availability is MatrixAvailability.OWNED_DECLARED and missing:
            raise CalibrationProgramContractError("owned matrix must not declare missing_sources")
        object.__setattr__(self, "missing_sources", missing)
        object.__setattr__(self, "coverage_tags", _sorted_unique_strings(self.coverage_tags, "coverage_tags"))

    def to_mapping(self) -> dict[str, object]:
        return {
            "matrix_id": self.matrix_id,
            "label": self.label,
            "composition_basis": "mass_fraction",
            "components": [item.to_mapping() for item in self.components],
            "availability": self.availability.value,
            "missing_sources": list(self.missing_sources),
            "coverage_tags": list(self.coverage_tags),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MatrixPanelEntry:
        normalized = _mapping(payload, "matrix panel entry")
        _exact_keys(
            normalized,
            {
                "matrix_id",
                "label",
                "composition_basis",
                "components",
                "availability",
                "missing_sources",
                "coverage_tags",
            },
            "matrix panel entry",
        )
        if normalized["composition_basis"] != "mass_fraction":
            raise CalibrationProgramContractError("composition_basis must be mass_fraction")
        return cls(
            matrix_id=normalized["matrix_id"],
            label=normalized["label"],
            components=tuple(
                MatrixComponent.from_mapping(_mapping(item, "matrix component"))
                for item in _sequence(normalized["components"], "components")
            ),
            availability=MatrixAvailability(normalized["availability"]),
            missing_sources=_sequence(normalized["missing_sources"], "missing_sources"),
            coverage_tags=_sequence(normalized["coverage_tags"], "coverage_tags"),
        )


@dataclass(frozen=True, slots=True)
class CalibrationProgram:
    program_id: str
    inventory_sha256: str
    materials: tuple[MaterialPanelEntry, ...]
    matrices: tuple[MatrixPanelEntry, ...]
    empirical_status: EmpiricalStatus
    actual_instrument_record_count: int
    status_reasons: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "program_id", _nonblank(self.program_id, "program_id"))
        object.__setattr__(self, "inventory_sha256", _sha256(self.inventory_sha256, "inventory_sha256"))
        materials = _sequence(self.materials, "materials")
        if not materials or any(not isinstance(item, MaterialPanelEntry) for item in materials):
            raise CalibrationProgramContractError("materials must contain MaterialPanelEntry values")
        material_names = [item.inventory_name for item in materials]
        if len(material_names) != len(set(material_names)):
            raise CalibrationProgramContractError("materials contains duplicate inventory names")
        matrices = _sequence(self.matrices, "matrices")
        if not matrices or any(not isinstance(item, MatrixPanelEntry) for item in matrices):
            raise CalibrationProgramContractError("matrices must contain MatrixPanelEntry values")
        matrix_ids = [item.matrix_id for item in matrices]
        if len(matrix_ids) != len(set(matrix_ids)):
            raise CalibrationProgramContractError("matrices contains duplicate matrix_id values")
        object.__setattr__(self, "materials", tuple(sorted(materials, key=lambda item: (item.inventory_name.casefold(), item.inventory_name))))
        object.__setattr__(self, "matrices", tuple(sorted(matrices, key=lambda item: item.matrix_id)))
        try:
            status = EmpiricalStatus(self.empirical_status)
        except ValueError as exc:
            raise CalibrationProgramContractError("empirical_status is invalid") from exc
        object.__setattr__(self, "empirical_status", status)
        count = _nonnegative_integer(self.actual_instrument_record_count, "actual_instrument_record_count")
        object.__setattr__(self, "actual_instrument_record_count", count)
        reasons = _sorted_unique_strings(self.status_reasons, "status_reasons", allow_empty=True)
        if status is EmpiricalStatus.BLOCKED_PENDING_DATA and not reasons:
            raise CalibrationProgramContractError("blocked program requires status_reasons")
        if status is EmpiricalStatus.BLOCKED_PENDING_DATA and count != 0:
            raise CalibrationProgramContractError("blocked no-data program must have zero records")
        object.__setattr__(self, "status_reasons", reasons)
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-calibration-program-v1",
            "program_id": self.program_id,
            "inventory_sha256": self.inventory_sha256,
            "materials": [item.to_mapping() for item in self.materials],
            "matrices": [item.to_mapping() for item in self.matrices],
            "empirical_status": self.empirical_status.value,
            "actual_instrument_record_count": self.actual_instrument_record_count,
            "status_reasons": list(self.status_reasons),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CalibrationProgram:
        normalized = _mapping(payload, "calibration program")
        _exact_keys(
            normalized,
            {
                "schema",
                "program_id",
                "inventory_sha256",
                "materials",
                "matrices",
                "empirical_status",
                "actual_instrument_record_count",
                "status_reasons",
                "content_sha256",
            },
            "calibration program",
        )
        if normalized["schema"] != "c5-calibration-program-v1":
            raise CalibrationProgramContractError("calibration program schema is invalid")
        result = cls(
            program_id=normalized["program_id"],
            inventory_sha256=normalized["inventory_sha256"],
            materials=tuple(
                MaterialPanelEntry.from_mapping(_mapping(item, "material panel entry"))
                for item in _sequence(normalized["materials"], "materials")
            ),
            matrices=tuple(
                MatrixPanelEntry.from_mapping(_mapping(item, "matrix panel entry"))
                for item in _sequence(normalized["matrices"], "matrices")
            ),
            empirical_status=EmpiricalStatus(normalized["empirical_status"]),
            actual_instrument_record_count=normalized["actual_instrument_record_count"],
            status_reasons=_sequence(normalized["status_reasons"], "status_reasons"),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError("program content_sha256 does not match canonical content")
        return result


def _material(
    name: str,
    chemical_class: str,
    fraction: float,
    basis: str,
    carrier: str,
    *tags: str,
    notes: tuple[str, ...] = (),
) -> MaterialPanelEntry:
    return MaterialPanelEntry(name, chemical_class, fraction, basis, carrier, tags, notes)


def _matrix(
    matrix_id: str,
    label: str,
    components: tuple[tuple[str, float], ...],
    *tags: str,
    missing: tuple[str, ...] = (),
) -> MatrixPanelEntry:
    return MatrixPanelEntry(
        matrix_id=matrix_id,
        label=label,
        components=tuple(MatrixComponent(name, fraction) for name, fraction in components),
        availability=(
            MatrixAvailability.REQUIRES_DECLARED_SOURCE
            if missing
            else MatrixAvailability.OWNED_DECLARED
        ),
        missing_sources=missing,
        coverage_tags=tags,
    )


def build_c5_program() -> CalibrationProgram:
    """Return the frozen inventory-derived C5 design with no empirical promotion."""

    materials = (
        _material("D-Limonene", "HYDROCARBON_TERPENE", 1.0, "neat", "", "HIGH_VAPOR_PRESSURE", "LOW_POLARITY", "BULK_STRUCTURAL"),
        _material("Linalool", "ALCOHOL", 1.0, "neat", "", "HIGH_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR"),
        _material("Phenethyl Alcohol", "ALCOHOL", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR", "BULK_STRUCTURAL"),
        _material("Citral", "ALDEHYDE", 1.0, "neat", "", "HIGH_VAPOR_PRESSURE", "H_BOND_ACCEPTOR"),
        _material("Aldehyde C10", "ALDEHYDE", 0.01, "unspecified", "", "HIGH_VAPOR_PRESSURE", "H_BOND_ACCEPTOR", "TRACE_POTENT", notes=("stock fraction basis and carrier require declaration",)),
        _material("Alpha Ionone", "KETONE_IONONE", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR"),
        _material("Raspberry Ketone", "KETONE_IONONE", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR"),
        _material("Linalyl Acetate", "ESTER", 1.0, "neat", "", "HIGH_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR", "BULK_STRUCTURAL"),
        _material("Ethyl 2-Methylbutyrate", "ESTER", 0.001, "unspecified", "", "HIGH_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR", "TRACE_POTENT", notes=("stock fraction basis and carrier require declaration",)),
        _material("Gamma Decalactone", "LACTONE", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "H_BOND_ACCEPTOR"),
        _material("Eugenol", "PHENOL", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR"),
        _material("Myristic Acid Powder", "ACID", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR", notes=("solid low-volatility feasibility and abstention control",)),
        _material("Galaxolide", "MUSK", 0.5, "unspecified", "dep", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "BULK_STRUCTURAL", notes=("stock fraction basis requires declaration",)),
        _material("Ambrettolide", "MUSK", 0.1, "unspecified", "dpg", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR", notes=("stock fraction basis requires declaration",)),
        _material("Iso E Super", "WOODY_AMBER", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "BULK_STRUCTURAL"),
        _material("Ambermax", "WOODY_AMBER", 0.5, "unspecified", "", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "TRACE_POTENT", notes=("stock fraction basis and carrier require declaration",)),
        _material("Hedione", "ESTER", 1.0, "neat", "", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR", "BULK_STRUCTURAL"),
        _material("Damascenone", "KETONE_IONONE", 0.01, "unspecified", "", "LOW_VAPOR_PRESSURE", "LOW_POLARITY", "H_BOND_ACCEPTOR", "TRACE_POTENT", notes=("stock fraction basis and carrier require declaration",)),
        _material("Geosmin", "ALCOHOL", 0.01, "unspecified", "tec", "LOW_VAPOR_PRESSURE", "HIGH_POLARITY", "H_BOND_DONOR", "H_BOND_ACCEPTOR", "TRACE_POTENT", notes=("stock fraction basis requires declaration",)),
    )
    matrices = (
        _matrix("CURRENT_DECLARED_STOCK", "current declared stock as held", (("CURRENT_DECLARED_STOCK", 1.0),), "NEAT_OR_CONCENTRATE_LIKE"),
        _matrix("FINISHED_10_PERCENT", "10 percent finished-strength target", (("PERFUME_CONCENTRATE", 0.10), ("ETHANOL_96_PERCENT", 0.82), ("WATER", 0.08)), "FINISHED_STRENGTH", missing=("WATER",)),
        _matrix("FINISHED_20_PERCENT", "20 percent finished-strength target", (("PERFUME_CONCENTRATE", 0.20), ("ETHANOL_96_PERCENT", 0.72), ("WATER", 0.08)), "FINISHED_STRENGTH", missing=("WATER",)),
        _matrix("HIGH_ETHANOL_STOCK", "high-ethanol one-percent stock", (("TEST_MATERIAL", 0.01), ("ETHANOL_96_PERCENT", 0.99)), "HIGH_ETHANOL_STOCK"),
        _matrix("DPG_HEAVY", "DPG-heavy carrier", (("TEST_MATERIAL", 0.01), ("DIPROPYLENE_GLYCOL", 0.90), ("ETHANOL_96_PERCENT", 0.09)), "DPG_HEAVY"),
        _matrix("TEC_HEAVY", "TEC-heavy carrier", (("TEST_MATERIAL", 0.01), ("TRIETHYL_CITRATE", 0.90), ("ETHANOL_96_PERCENT", 0.09)), "TEC_HEAVY"),
        _matrix("DEP_HEAVY", "DEP-heavy carrier", (("TEST_MATERIAL", 0.01), ("DIETHYL_PHTHALATE", 0.90), ("ETHANOL_96_PERCENT", 0.09)), "DEP_HEAVY", missing=("DEP",)),
        _matrix("IPM_OIL", "IPM oil carrier", (("TEST_MATERIAL", 0.01), ("ISOPROPYL_MYRISTATE", 0.90), ("ETHANOL_96_PERCENT", 0.09)), "IPM_OR_OIL"),
    )
    return CalibrationProgram(
        program_id="c5-calibration-program-inventory-20260803-v1",
        inventory_sha256=C5_INVENTORY_SHA256,
        materials=materials,
        matrices=matrices,
        empirical_status=EmpiricalStatus.BLOCKED_PENDING_DATA,
        actual_instrument_record_count=0,
        status_reasons=(
            "NO_B5_BOUND_PROTOCOL",
            "NO_LOCKED_LEAK_RESISTANT_SPLIT",
            "NO_PRE_HELD_OUT_MODEL_LOCK",
            "NO_REAL_INSTRUMENT_OBSERVATIONS",
        ),
    )


@dataclass(frozen=True, slots=True)
class B5MethodBinding:
    method_authority_id: str
    method_authority_sha256: str
    method_validation_id: str
    method_validation_sha256: str
    validation_scope_sha256: str
    technique: str
    validation_decision: str

    def __post_init__(self) -> None:
        for name in ("method_authority_id", "method_validation_id"):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        for name in (
            "method_authority_sha256",
            "method_validation_sha256",
            "validation_scope_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        technique = _nonblank(self.technique, "technique")
        if technique != "HS_SPME_GCMS":
            raise CalibrationProgramContractError(
                "technique must be HS_SPME_GCMS for the C5 headspace protocol"
            )
        object.__setattr__(self, "technique", technique)
        decision = _nonblank(self.validation_decision, "validation_decision")
        if decision != "PASS":
            raise CalibrationProgramContractError("validation_decision must be PASS")
        object.__setattr__(self, "validation_decision", decision)

    def to_mapping(self) -> dict[str, object]:
        return {
            "method_authority_id": self.method_authority_id,
            "method_authority_sha256": self.method_authority_sha256,
            "method_validation_id": self.method_validation_id,
            "method_validation_sha256": self.method_validation_sha256,
            "validation_scope_sha256": self.validation_scope_sha256,
            "technique": self.technique,
            "validation_decision": self.validation_decision,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> B5MethodBinding:
        normalized = _mapping(payload, "B5 method binding")
        _exact_keys(
            normalized,
            {
                "method_authority_id",
                "method_authority_sha256",
                "method_validation_id",
                "method_validation_sha256",
                "validation_scope_sha256",
                "technique",
                "validation_decision",
            },
            "B5 method binding",
        )
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class ExperimentalProtocol:
    protocol_id: str
    program_sha256: str
    matrix_id: str
    matrix_batch_id: str
    method_binding: B5MethodBinding
    sample_mass_value: float
    sample_mass_unit: str
    sample_volume_value: float
    sample_volume_unit: str
    vial_volume_ml: float
    headspace_volume_ml: float
    temperature_k: float
    equilibration_seconds: float
    extraction_sampling: str
    spme_fiber: str
    spme_conditioning: str
    spme_fiber_age_injections: int
    agitation: str
    desorption: str
    internal_standard: str
    calibration_plan: str
    blanks: str
    carryover_control: str
    qc_plan: str
    replicate_count: int
    randomization_algorithm: str
    randomization_seed: str
    instrument_drift_control: str
    reviewed_at: datetime
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("protocol_id", "matrix_id", "matrix_batch_id"):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        object.__setattr__(self, "program_sha256", _sha256(self.program_sha256, "program_sha256"))
        if not isinstance(self.method_binding, B5MethodBinding):
            raise CalibrationProgramContractError("method_binding must be a B5MethodBinding")
        for name in ("sample_mass_value", "sample_volume_value", "vial_volume_ml", "headspace_volume_ml", "temperature_k", "equilibration_seconds"):
            object.__setattr__(self, name, _positive(getattr(self, name), name))
        if self.headspace_volume_ml >= self.vial_volume_ml:
            raise CalibrationProgramContractError(
                "headspace_volume_ml must be smaller than vial_volume_ml"
            )
        for name in (
            "sample_mass_unit",
            "sample_volume_unit",
            "extraction_sampling",
            "spme_fiber",
            "spme_conditioning",
            "agitation",
            "desorption",
            "internal_standard",
            "calibration_plan",
            "blanks",
            "carryover_control",
            "qc_plan",
            "randomization_algorithm",
            "randomization_seed",
            "instrument_drift_control",
        ):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        age = _nonnegative_integer(self.spme_fiber_age_injections, "spme_fiber_age_injections")
        object.__setattr__(self, "spme_fiber_age_injections", age)
        replicate_count = _nonnegative_integer(self.replicate_count, "replicate_count")
        if replicate_count < 2:
            raise CalibrationProgramContractError("replicate_count must be at least two")
        object.__setattr__(self, "replicate_count", replicate_count)
        object.__setattr__(self, "reviewed_at", _aware_datetime(self.reviewed_at, "reviewed_at"))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-experimental-protocol-v1",
            "protocol_id": self.protocol_id,
            "program_sha256": self.program_sha256,
            "matrix_id": self.matrix_id,
            "matrix_batch_id": self.matrix_batch_id,
            "method_binding": self.method_binding.to_mapping(),
            "sample_mass_value": self.sample_mass_value,
            "sample_mass_unit": self.sample_mass_unit,
            "sample_volume_value": self.sample_volume_value,
            "sample_volume_unit": self.sample_volume_unit,
            "vial_volume_ml": self.vial_volume_ml,
            "headspace_volume_ml": self.headspace_volume_ml,
            "temperature_k": self.temperature_k,
            "equilibration_seconds": self.equilibration_seconds,
            "extraction_sampling": self.extraction_sampling,
            "spme_fiber": self.spme_fiber,
            "spme_conditioning": self.spme_conditioning,
            "spme_fiber_age_injections": self.spme_fiber_age_injections,
            "agitation": self.agitation,
            "desorption": self.desorption,
            "internal_standard": self.internal_standard,
            "calibration_plan": self.calibration_plan,
            "blanks": self.blanks,
            "carryover_control": self.carryover_control,
            "qc_plan": self.qc_plan,
            "replicate_count": self.replicate_count,
            "randomization_algorithm": self.randomization_algorithm,
            "randomization_seed": self.randomization_seed,
            "instrument_drift_control": self.instrument_drift_control,
            "reviewed_at": _datetime_text(self.reviewed_at),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ExperimentalProtocol:
        normalized = _mapping(payload, "experimental protocol")
        expected = {
            "schema",
            "protocol_id",
            "program_sha256",
            "matrix_id",
            "matrix_batch_id",
            "method_binding",
            "sample_mass_value",
            "sample_mass_unit",
            "sample_volume_value",
            "sample_volume_unit",
            "vial_volume_ml",
            "headspace_volume_ml",
            "temperature_k",
            "equilibration_seconds",
            "extraction_sampling",
            "spme_fiber",
            "spme_conditioning",
            "spme_fiber_age_injections",
            "agitation",
            "desorption",
            "internal_standard",
            "calibration_plan",
            "blanks",
            "carryover_control",
            "qc_plan",
            "replicate_count",
            "randomization_algorithm",
            "randomization_seed",
            "instrument_drift_control",
            "reviewed_at",
            "content_sha256",
        }
        _exact_keys(normalized, expected, "experimental protocol")
        if normalized["schema"] != "c5-experimental-protocol-v1":
            raise CalibrationProgramContractError("experimental protocol schema is invalid")
        result = cls(
            protocol_id=normalized["protocol_id"],
            program_sha256=normalized["program_sha256"],
            matrix_id=normalized["matrix_id"],
            matrix_batch_id=normalized["matrix_batch_id"],
            method_binding=B5MethodBinding.from_mapping(_mapping(normalized["method_binding"], "method_binding")),
            sample_mass_value=normalized["sample_mass_value"],
            sample_mass_unit=normalized["sample_mass_unit"],
            sample_volume_value=normalized["sample_volume_value"],
            sample_volume_unit=normalized["sample_volume_unit"],
            vial_volume_ml=normalized["vial_volume_ml"],
            headspace_volume_ml=normalized["headspace_volume_ml"],
            temperature_k=normalized["temperature_k"],
            equilibration_seconds=normalized["equilibration_seconds"],
            extraction_sampling=normalized["extraction_sampling"],
            spme_fiber=normalized["spme_fiber"],
            spme_conditioning=normalized["spme_conditioning"],
            spme_fiber_age_injections=normalized["spme_fiber_age_injections"],
            agitation=normalized["agitation"],
            desorption=normalized["desorption"],
            internal_standard=normalized["internal_standard"],
            calibration_plan=normalized["calibration_plan"],
            blanks=normalized["blanks"],
            carryover_control=normalized["carryover_control"],
            qc_plan=normalized["qc_plan"],
            replicate_count=normalized["replicate_count"],
            randomization_algorithm=normalized["randomization_algorithm"],
            randomization_seed=normalized["randomization_seed"],
            instrument_drift_control=normalized["instrument_drift_control"],
            reviewed_at=_parse_datetime(normalized["reviewed_at"], "reviewed_at"),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError("protocol content_sha256 does not match canonical content")
        return result


@dataclass(frozen=True, slots=True)
class ObservationDescriptor:
    observation_id: str
    protocol_sha256: str
    material_id: str
    matrix_id: str
    condition_id: str
    chemical_identity_group: str
    close_analog_group: str
    formula_id: str
    supplier_lot: str
    matrix_batch_id: str
    measurement_session_id: str
    replicate_id: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "material_id",
            "matrix_id",
            "condition_id",
            *LEAKAGE_DIMENSIONS,
            "replicate_id",
        ):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        object.__setattr__(self, "protocol_sha256", _sha256(self.protocol_sha256, "protocol_sha256"))

    def to_mapping(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "protocol_sha256": self.protocol_sha256,
            "material_id": self.material_id,
            "matrix_id": self.matrix_id,
            "condition_id": self.condition_id,
            "chemical_identity_group": self.chemical_identity_group,
            "close_analog_group": self.close_analog_group,
            "formula_id": self.formula_id,
            "supplier_lot": self.supplier_lot,
            "matrix_batch_id": self.matrix_batch_id,
            "measurement_session_id": self.measurement_session_id,
            "replicate_id": self.replicate_id,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ObservationDescriptor:
        normalized = _mapping(payload, "observation descriptor")
        _exact_keys(
            normalized,
            {
                "observation_id",
                "protocol_sha256",
                "material_id",
                "matrix_id",
                "condition_id",
                "chemical_identity_group",
                "close_analog_group",
                "formula_id",
                "supplier_lot",
                "matrix_batch_id",
                "measurement_session_id",
                "replicate_id",
            },
            "observation descriptor",
        )
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class B5AuthorityReceipt:
    method_authority_id: str
    method_authority_sha256: str
    method_validation_id: str
    method_validation_sha256: str
    validation_scope_sha256: str
    run_authority_id: str
    run_authority_sha256: str
    peak_authority_id: str
    peak_authority_sha256: str
    claim_assessment_id: str
    claim_assessment_sha256: str
    claim_decision: str
    matrix_calibration_id: str
    analyte_calibration_id: str
    method_calibration_id: str
    raw_vendor_sha256: str
    open_export_sha256: str
    blocking_qc_clear: bool
    measurement_uncertainty_declared: bool

    def __post_init__(self) -> None:
        for name in (
            "method_authority_id",
            "method_validation_id",
            "run_authority_id",
            "peak_authority_id",
            "claim_assessment_id",
            "matrix_calibration_id",
            "analyte_calibration_id",
            "method_calibration_id",
        ):
            object.__setattr__(self, name, _nonblank(getattr(self, name), name))
        for name in (
            "method_authority_sha256",
            "method_validation_sha256",
            "validation_scope_sha256",
            "run_authority_sha256",
            "peak_authority_sha256",
            "claim_assessment_sha256",
            "raw_vendor_sha256",
            "open_export_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        if self.raw_vendor_sha256 == self.open_export_sha256:
            raise CalibrationProgramContractError("vendor raw and open export digests must differ")
        decision = _nonblank(self.claim_decision, "claim_decision")
        if decision != "SUPPORTED_FOR_SCOPE":
            raise CalibrationProgramContractError("claim_decision must be SUPPORTED_FOR_SCOPE")
        object.__setattr__(self, "claim_decision", decision)
        if self.blocking_qc_clear is not True:
            raise CalibrationProgramContractError("blocking_qc_clear must be true")
        if self.measurement_uncertainty_declared is not True:
            raise CalibrationProgramContractError("measurement_uncertainty_declared must be true")

    def to_mapping(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> B5AuthorityReceipt:
        normalized = _mapping(payload, "B5 authority receipt")
        expected = {item for item in cls.__dataclass_fields__}
        _exact_keys(normalized, expected, "B5 authority receipt")
        return cls(**normalized)


@dataclass(frozen=True, slots=True)
class ObservationOutcome:
    origin: EvidenceOrigin
    state: ObservationState
    observed_value: float | None
    predicted_value: float | None
    baseline_prediction: float | None
    prediction_interval_lower: float | None
    prediction_interval_upper: float | None
    value_unit: str
    observed_standard_uncertainty: float | None
    disposition_reason: str | None

    def __post_init__(self) -> None:
        try:
            origin = EvidenceOrigin(self.origin)
            state = ObservationState(self.state)
        except ValueError as exc:
            raise CalibrationProgramContractError("observation origin or state is invalid") from exc
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "value_unit", _nonblank(self.value_unit, "value_unit"))
        if state is ObservationState.MISSING:
            for name in (
                "observed_value",
                "predicted_value",
                "baseline_prediction",
                "prediction_interval_lower",
                "prediction_interval_upper",
                "observed_standard_uncertainty",
            ):
                if getattr(self, name) is not None:
                    raise CalibrationProgramContractError(
                        f"{name} must be absent for a missing observation"
                    )
            object.__setattr__(self, "disposition_reason", _nonblank(self.disposition_reason, "disposition_reason"))
            return
        observed = _positive(self.observed_value, "observed_value")
        baseline = _positive(self.baseline_prediction, "baseline_prediction")
        uncertainty = _positive(self.observed_standard_uncertainty, "observed_standard_uncertainty")
        object.__setattr__(self, "observed_value", observed)
        object.__setattr__(self, "baseline_prediction", baseline)
        object.__setattr__(self, "observed_standard_uncertainty", uncertainty)
        if state is ObservationState.ABSTAINED:
            for name in ("predicted_value", "prediction_interval_lower", "prediction_interval_upper"):
                if getattr(self, name) is not None:
                    raise CalibrationProgramContractError(f"{name} must be absent for abstention")
            object.__setattr__(self, "disposition_reason", _nonblank(self.disposition_reason, "disposition_reason"))
            return
        predicted = _positive(self.predicted_value, "predicted_value")
        lower = _positive(self.prediction_interval_lower, "prediction_interval_lower")
        upper = _positive(self.prediction_interval_upper, "prediction_interval_upper")
        if lower > predicted or predicted > upper:
            raise CalibrationProgramContractError(
                "prediction interval must contain predicted_value"
            )
        object.__setattr__(self, "predicted_value", predicted)
        object.__setattr__(self, "prediction_interval_lower", lower)
        object.__setattr__(self, "prediction_interval_upper", upper)
        if self.disposition_reason is not None:
            raise CalibrationProgramContractError(
                "disposition_reason must be absent for a scored value"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "origin": self.origin.value,
            "state": self.state.value,
            "observed_value": self.observed_value,
            "predicted_value": self.predicted_value,
            "baseline_prediction": self.baseline_prediction,
            "prediction_interval_lower": self.prediction_interval_lower,
            "prediction_interval_upper": self.prediction_interval_upper,
            "value_unit": self.value_unit,
            "observed_standard_uncertainty": self.observed_standard_uncertainty,
            "disposition_reason": self.disposition_reason,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ObservationOutcome:
        normalized = _mapping(payload, "observation outcome")
        _exact_keys(normalized, {item for item in cls.__dataclass_fields__}, "observation outcome")
        return cls(
            origin=EvidenceOrigin(normalized["origin"]),
            state=ObservationState(normalized["state"]),
            observed_value=normalized["observed_value"],
            predicted_value=normalized["predicted_value"],
            baseline_prediction=normalized["baseline_prediction"],
            prediction_interval_lower=normalized["prediction_interval_lower"],
            prediction_interval_upper=normalized["prediction_interval_upper"],
            value_unit=normalized["value_unit"],
            observed_standard_uncertainty=normalized["observed_standard_uncertainty"],
            disposition_reason=normalized["disposition_reason"],
        )


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    descriptor: ObservationDescriptor
    outcome: ObservationOutcome
    b5_receipt: B5AuthorityReceipt | None
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ObservationDescriptor):
            raise CalibrationProgramContractError("descriptor must be an ObservationDescriptor")
        if not isinstance(self.outcome, ObservationOutcome):
            raise CalibrationProgramContractError("outcome must be an ObservationOutcome")
        if self.outcome.origin is EvidenceOrigin.REAL_INSTRUMENT:
            if not isinstance(self.b5_receipt, B5AuthorityReceipt):
                raise CalibrationProgramContractError(
                    "REAL_INSTRUMENT observations require a B5 authority receipt"
                )
        elif self.b5_receipt is not None:
            raise CalibrationProgramContractError(
                "SIMULATED_SMOKE observations must not carry B5 authority"
            )
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-calibration-observation-v1",
            "descriptor": self.descriptor.to_mapping(),
            "outcome": self.outcome.to_mapping(),
            "b5_receipt": None if self.b5_receipt is None else self.b5_receipt.to_mapping(),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CalibrationObservation:
        normalized = _mapping(payload, "calibration observation")
        _exact_keys(
            normalized,
            {"schema", "descriptor", "outcome", "b5_receipt", "content_sha256"},
            "calibration observation",
        )
        if normalized["schema"] != "c5-calibration-observation-v1":
            raise CalibrationProgramContractError("calibration observation schema is invalid")
        receipt_payload = normalized["b5_receipt"]
        result = cls(
            descriptor=ObservationDescriptor.from_mapping(_mapping(normalized["descriptor"], "descriptor")),
            outcome=ObservationOutcome.from_mapping(_mapping(normalized["outcome"], "outcome")),
            b5_receipt=(
                None
                if receipt_payload is None
                else B5AuthorityReceipt.from_mapping(_mapping(receipt_payload, "b5_receipt"))
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError(
                "observation content_sha256 does not match canonical content"
            )
        return result


def _validate_observation_binding(
    observation: CalibrationObservation,
    *,
    program: CalibrationProgram,
    protocols_by_hash: Mapping[str, ExperimentalProtocol],
) -> None:
    descriptor = observation.descriptor
    material_ids = {item.inventory_name for item in program.materials}
    matrix_ids = {item.matrix_id for item in program.matrices}
    if descriptor.material_id not in material_ids:
        raise CalibrationProgramContractError("observation material_id is outside the C5 panel")
    if descriptor.matrix_id not in matrix_ids:
        raise CalibrationProgramContractError("observation matrix_id is outside the C5 panel")
    protocol = protocols_by_hash.get(descriptor.protocol_sha256)
    if protocol is None:
        raise CalibrationProgramContractError("observation protocol_sha256 is not declared")
    if protocol.program_sha256 != program.content_sha256:
        raise CalibrationProgramContractError("protocol does not bind the exact C5 program")
    if protocol.matrix_id != descriptor.matrix_id:
        raise CalibrationProgramContractError("observation matrix does not match protocol")
    receipt = observation.b5_receipt
    if receipt is None:
        raise CalibrationProgramContractError("REAL_INSTRUMENT observation lacks B5 receipt")
    binding = protocol.method_binding
    for name in (
        "method_authority_id",
        "method_authority_sha256",
        "method_validation_id",
        "method_validation_sha256",
        "validation_scope_sha256",
    ):
        if getattr(receipt, name) != getattr(binding, name):
            raise CalibrationProgramContractError(f"B5 {name} does not match protocol")
    if receipt.matrix_calibration_id != binding.validation_scope_sha256:
        raise CalibrationProgramContractError("matrix calibration does not match B5 scope")
    if receipt.analyte_calibration_id != descriptor.material_id:
        raise CalibrationProgramContractError("analyte calibration does not match material")
    if receipt.method_calibration_id != binding.method_authority_id:
        raise CalibrationProgramContractError("method calibration does not match authority")


def import_real_measurements_jsonl(
    text: str,
    *,
    program: CalibrationProgram,
    protocols: Sequence[ExperimentalProtocol],
) -> tuple[CalibrationObservation, ...]:
    """Strictly parse real observations; simulation has a separate entry point."""

    if not isinstance(text, str):
        raise CalibrationProgramContractError("JSONL input must be text")
    if not isinstance(program, CalibrationProgram):
        raise CalibrationProgramContractError("program must be a CalibrationProgram")
    protocol_items = _sequence(protocols, "protocols")
    if not protocol_items or any(not isinstance(item, ExperimentalProtocol) for item in protocol_items):
        raise CalibrationProgramContractError("protocols must contain ExperimentalProtocol values")
    protocols_by_hash = {item.content_sha256: item for item in protocol_items}
    if len(protocols_by_hash) != len(protocol_items):
        raise CalibrationProgramContractError("protocols contains duplicate hashes")
    observations: list[CalibrationObservation] = []
    identifiers: set[str] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise CalibrationProgramContractError(
                f"invalid JSON on line {line_number}"
            ) from exc
        try:
            observation = CalibrationObservation.from_mapping(
                _mapping(payload, f"JSONL line {line_number}")
            )
        except CalibrationProgramContractError as exc:
            raise CalibrationProgramContractError(
                f"JSONL line {line_number}: {exc}"
            ) from exc
        if observation.outcome.origin is not EvidenceOrigin.REAL_INSTRUMENT:
            raise CalibrationProgramContractError(
                f"JSONL line {line_number}: origin must be REAL_INSTRUMENT"
            )
        identifier = observation.descriptor.observation_id
        if identifier in identifiers:
            raise CalibrationProgramContractError(f"duplicate observation_id: {identifier}")
        _validate_observation_binding(
            observation,
            program=program,
            protocols_by_hash=protocols_by_hash,
        )
        identifiers.add(identifier)
        observations.append(observation)
    if not observations:
        raise CalibrationProgramContractError("JSONL contains no observations")
    return tuple(sorted(observations, key=lambda item: item.descriptor.observation_id))


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    partition: Partition
    descriptor: ObservationDescriptor

    def __post_init__(self) -> None:
        try:
            partition = Partition(self.partition)
        except ValueError as exc:
            raise CalibrationProgramContractError("partition is invalid") from exc
        object.__setattr__(self, "partition", partition)
        if not isinstance(self.descriptor, ObservationDescriptor):
            raise CalibrationProgramContractError("descriptor must be an ObservationDescriptor")

    def to_mapping(self) -> dict[str, object]:
        return {
            "partition": self.partition.value,
            "descriptor": self.descriptor.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SplitAssignment:
        normalized = _mapping(payload, "split assignment")
        _exact_keys(normalized, {"partition", "descriptor"}, "split assignment")
        return cls(
            partition=Partition(normalized["partition"]),
            descriptor=ObservationDescriptor.from_mapping(
                _mapping(normalized["descriptor"], "descriptor")
            ),
        )


@dataclass(frozen=True, slots=True)
class SplitManifest:
    manifest_id: str
    assignments: tuple[SplitAssignment, ...]
    locked_at: datetime
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest_id", _nonblank(self.manifest_id, "manifest_id"))
        assignments = _sequence(self.assignments, "assignments")
        if not assignments or any(not isinstance(item, SplitAssignment) for item in assignments):
            raise CalibrationProgramContractError("assignments must contain SplitAssignment values")
        identifiers = [item.descriptor.observation_id for item in assignments]
        if len(identifiers) != len(set(identifiers)):
            raise CalibrationProgramContractError("assignments contains duplicate observation_id values")
        present = {item.partition for item in assignments}
        for required in Partition:
            if required not in present:
                raise CalibrationProgramContractError(
                    f"split manifest requires nonempty {required.value} partition"
                )
        for dimension in LEAKAGE_DIMENSIONS:
            partitions_by_group: dict[str, set[Partition]] = defaultdict(set)
            for assignment in assignments:
                partitions_by_group[getattr(assignment.descriptor, dimension)].add(
                    assignment.partition
                )
            leaking = sorted(
                group
                for group, partitions in partitions_by_group.items()
                if len(partitions) > 1
            )
            if leaking:
                raise CalibrationProgramContractError(
                    f"cross-partition leakage in {dimension}: {', '.join(leaking)}"
                )
        assignments = tuple(
            sorted(assignments, key=lambda item: item.descriptor.observation_id)
        )
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "locked_at", _aware_datetime(self.locked_at, "locked_at"))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-split-manifest-v1",
            "manifest_id": self.manifest_id,
            "assignments": [item.to_mapping() for item in self.assignments],
            "locked_at": _datetime_text(self.locked_at),
            "leakage_dimensions": list(LEAKAGE_DIMENSIONS),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SplitManifest:
        normalized = _mapping(payload, "split manifest")
        _exact_keys(
            normalized,
            {
                "schema",
                "manifest_id",
                "assignments",
                "locked_at",
                "leakage_dimensions",
                "content_sha256",
            },
            "split manifest",
        )
        if normalized["schema"] != "c5-split-manifest-v1":
            raise CalibrationProgramContractError("split manifest schema is invalid")
        if tuple(normalized["leakage_dimensions"]) != LEAKAGE_DIMENSIONS:
            raise CalibrationProgramContractError("split manifest leakage dimensions are incomplete")
        result = cls(
            manifest_id=normalized["manifest_id"],
            assignments=tuple(
                SplitAssignment.from_mapping(_mapping(item, "split assignment"))
                for item in _sequence(normalized["assignments"], "assignments")
            ),
            locked_at=_parse_datetime(normalized["locked_at"], "locked_at"),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError(
                "split content_sha256 does not match canonical content"
            )
        return result

    def partition_for(self, observation_id: str) -> Partition:
        identifier = _nonblank(observation_id, "observation_id")
        for assignment in self.assignments:
            if assignment.descriptor.observation_id == identifier:
                return assignment.partition
        raise CalibrationProgramContractError(
            f"observation_id is absent from split manifest: {identifier}"
        )


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    criterion_id: str
    metric: MetricName
    comparator: Comparator
    threshold: float
    group_dimension: str | None
    group_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion_id", _nonblank(self.criterion_id, "criterion_id"))
        try:
            metric = MetricName(self.metric)
            comparator = Comparator(self.comparator)
        except ValueError as exc:
            raise CalibrationProgramContractError("criterion metric or comparator is invalid") from exc
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "comparator", comparator)
        object.__setattr__(self, "threshold", _finite(self.threshold, "threshold"))
        if (self.group_dimension is None) != (self.group_id is None):
            raise CalibrationProgramContractError(
                "group_dimension and group_id must both be set or both be absent"
            )
        if self.group_dimension is not None:
            dimension = _nonblank(self.group_dimension, "group_dimension")
            if dimension not in REQUIRED_GROUP_DIMENSIONS:
                raise CalibrationProgramContractError("group_dimension is not prespecified")
            object.__setattr__(self, "group_dimension", dimension)
            object.__setattr__(self, "group_id", _nonblank(self.group_id, "group_id"))

    def to_mapping(self) -> dict[str, object]:
        return {
            "criterion_id": self.criterion_id,
            "metric": self.metric.value,
            "comparator": self.comparator.value,
            "threshold": self.threshold,
            "group_dimension": self.group_dimension,
            "group_id": self.group_id,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AcceptanceCriterion:
        normalized = _mapping(payload, "acceptance criterion")
        _exact_keys(normalized, {item for item in cls.__dataclass_fields__}, "acceptance criterion")
        return cls(
            criterion_id=normalized["criterion_id"],
            metric=MetricName(normalized["metric"]),
            comparator=Comparator(normalized["comparator"]),
            threshold=normalized["threshold"],
            group_dimension=normalized["group_dimension"],
            group_id=normalized["group_id"],
        )


@dataclass(frozen=True, slots=True)
class EvaluationPlan:
    plan_id: str
    scale: MetricScale
    metric_names: tuple[MetricName, ...]
    group_dimensions: tuple[str, ...]
    catastrophic_fold_threshold: float
    criteria: tuple[AcceptanceCriterion, ...]
    locked_at: datetime
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _nonblank(self.plan_id, "plan_id"))
        try:
            scale = MetricScale(self.scale)
        except ValueError as exc:
            raise CalibrationProgramContractError("scale is invalid") from exc
        object.__setattr__(self, "scale", scale)
        try:
            metrics = tuple(MetricName(item) for item in _sequence(self.metric_names, "metric_names"))
        except ValueError as exc:
            raise CalibrationProgramContractError("metric_names contains an unknown metric") from exc
        missing = set(REQUIRED_METRICS) - set(metrics)
        extras = set(metrics) - set(REQUIRED_METRICS)
        if missing:
            labels = ", ".join(sorted(item.name for item in missing))
            raise CalibrationProgramContractError(f"metric_names missing required metrics: {labels}")
        if extras or len(metrics) != len(set(metrics)):
            raise CalibrationProgramContractError("metric_names must contain each required metric once")
        object.__setattr__(self, "metric_names", tuple(sorted(metrics, key=lambda item: item.value)))
        dimensions = _sorted_unique_strings(self.group_dimensions, "group_dimensions")
        missing_dimensions = set(REQUIRED_GROUP_DIMENSIONS) - set(dimensions)
        if missing_dimensions:
            raise CalibrationProgramContractError(
                "group_dimensions missing required dimensions: "
                + ", ".join(sorted(missing_dimensions))
            )
        if set(dimensions) != set(REQUIRED_GROUP_DIMENSIONS):
            raise CalibrationProgramContractError("group_dimensions contains unknown dimensions")
        object.__setattr__(self, "group_dimensions", tuple(sorted(dimensions)))
        catastrophic = _positive(
            self.catastrophic_fold_threshold,
            "catastrophic_fold_threshold",
        )
        if catastrophic <= 1.0:
            raise CalibrationProgramContractError(
                "catastrophic_fold_threshold must exceed one"
            )
        object.__setattr__(self, "catastrophic_fold_threshold", catastrophic)
        criteria = _sequence(self.criteria, "criteria")
        if not criteria or any(not isinstance(item, AcceptanceCriterion) for item in criteria):
            raise CalibrationProgramContractError("criteria must contain AcceptanceCriterion values")
        identifiers = [item.criterion_id for item in criteria]
        if len(identifiers) != len(set(identifiers)):
            raise CalibrationProgramContractError("criteria contains duplicate criterion_id values")
        object.__setattr__(self, "criteria", tuple(sorted(criteria, key=lambda item: item.criterion_id)))
        object.__setattr__(self, "locked_at", _aware_datetime(self.locked_at, "locked_at"))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-evaluation-plan-v1",
            "plan_id": self.plan_id,
            "scale": self.scale.value,
            "metric_names": [item.value for item in self.metric_names],
            "group_dimensions": list(self.group_dimensions),
            "catastrophic_fold_threshold": self.catastrophic_fold_threshold,
            "criteria": [item.to_mapping() for item in self.criteria],
            "locked_at": _datetime_text(self.locked_at),
            "r_squared_is_acceptance_metric": False,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> EvaluationPlan:
        normalized = _mapping(payload, "evaluation plan")
        _exact_keys(
            normalized,
            {
                "schema",
                "plan_id",
                "scale",
                "metric_names",
                "group_dimensions",
                "catastrophic_fold_threshold",
                "criteria",
                "locked_at",
                "r_squared_is_acceptance_metric",
                "content_sha256",
            },
            "evaluation plan",
        )
        if normalized["schema"] != "c5-evaluation-plan-v1":
            raise CalibrationProgramContractError("evaluation plan schema is invalid")
        if normalized["r_squared_is_acceptance_metric"] is not False:
            raise CalibrationProgramContractError("R-squared cannot be an acceptance metric")
        result = cls(
            plan_id=normalized["plan_id"],
            scale=MetricScale(normalized["scale"]),
            metric_names=tuple(MetricName(item) for item in normalized["metric_names"]),
            group_dimensions=tuple(normalized["group_dimensions"]),
            catastrophic_fold_threshold=normalized["catastrophic_fold_threshold"],
            criteria=tuple(
                AcceptanceCriterion.from_mapping(_mapping(item, "acceptance criterion"))
                for item in normalized["criteria"]
            ),
            locked_at=_parse_datetime(normalized["locked_at"], "locked_at"),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError(
                "evaluation-plan content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelLockReceipt:
    model_id: str
    model_sha256: str
    split_manifest_sha256: str
    evaluation_plan_sha256: str
    validation_observation_sha256s: tuple[str, ...]
    validation_dataset_sha256: str
    locked_at: datetime
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _nonblank(self.model_id, "model_id"))
        for name in (
            "model_sha256",
            "split_manifest_sha256",
            "evaluation_plan_sha256",
            "validation_dataset_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        hashes = tuple(_sha256(item, "validation_observation_sha256s") for item in _sequence(self.validation_observation_sha256s, "validation_observation_sha256s"))
        if not hashes or len(hashes) != len(set(hashes)):
            raise CalibrationProgramContractError(
                "validation_observation_sha256s must be nonempty and unique"
            )
        hashes = tuple(sorted(hashes))
        if stable_json_hash(list(hashes)) != self.validation_dataset_sha256:
            raise CalibrationProgramContractError(
                "validation_dataset_sha256 does not match observation hashes"
            )
        object.__setattr__(self, "validation_observation_sha256s", hashes)
        object.__setattr__(self, "locked_at", _aware_datetime(self.locked_at, "locked_at"))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-model-lock-receipt-v1",
            "model_id": self.model_id,
            "model_sha256": self.model_sha256,
            "split_manifest_sha256": self.split_manifest_sha256,
            "evaluation_plan_sha256": self.evaluation_plan_sha256,
            "validation_observation_sha256s": list(self.validation_observation_sha256s),
            "validation_dataset_sha256": self.validation_dataset_sha256,
            "locked_at": _datetime_text(self.locked_at),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ModelLockReceipt:
        normalized = _mapping(payload, "model lock receipt")
        _exact_keys(
            normalized,
            {
                "schema",
                "model_id",
                "model_sha256",
                "split_manifest_sha256",
                "evaluation_plan_sha256",
                "validation_observation_sha256s",
                "validation_dataset_sha256",
                "locked_at",
                "content_sha256",
            },
            "model lock receipt",
        )
        if normalized["schema"] != "c5-model-lock-receipt-v1":
            raise CalibrationProgramContractError("model lock schema is invalid")
        result = cls(
            model_id=normalized["model_id"],
            model_sha256=normalized["model_sha256"],
            split_manifest_sha256=normalized["split_manifest_sha256"],
            evaluation_plan_sha256=normalized["evaluation_plan_sha256"],
            validation_observation_sha256s=tuple(normalized["validation_observation_sha256s"]),
            validation_dataset_sha256=normalized["validation_dataset_sha256"],
            locked_at=_parse_datetime(normalized["locked_at"], "locked_at"),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise CalibrationProgramContractError(
                "model-lock content_sha256 does not match canonical content"
            )
        return result


def lock_model(
    *,
    model_id: str,
    model_sha256: str,
    split_manifest: SplitManifest,
    evaluation_plan: EvaluationPlan,
    validation_observations: Sequence[CalibrationObservation],
    locked_at: datetime,
) -> ModelLockReceipt:
    """Lock model and plan after validation, before held-out outcomes are released."""

    if not isinstance(split_manifest, SplitManifest):
        raise CalibrationProgramContractError("split_manifest must be a SplitManifest")
    if not isinstance(evaluation_plan, EvaluationPlan):
        raise CalibrationProgramContractError("evaluation_plan must be an EvaluationPlan")
    timestamp = _aware_datetime(locked_at, "locked_at")
    if timestamp <= split_manifest.locked_at or timestamp <= evaluation_plan.locked_at:
        raise CalibrationProgramContractError(
            "model lock must occur after split and evaluation-plan locks"
        )
    observations = _sequence(validation_observations, "validation_observations")
    if not observations or any(not isinstance(item, CalibrationObservation) for item in observations):
        raise CalibrationProgramContractError(
            "validation_observations must contain CalibrationObservation values"
        )
    expected_ids = {
        item.descriptor.observation_id
        for item in split_manifest.assignments
        if item.partition is Partition.VALIDATION
    }
    actual_ids = {item.descriptor.observation_id for item in observations}
    if actual_ids != expected_ids:
        raise CalibrationProgramContractError(
            "model lock observations must exactly match the validation partition"
        )
    if any(item.outcome.origin is not EvidenceOrigin.REAL_INSTRUMENT for item in observations):
        raise CalibrationProgramContractError(
            "model lock requires REAL_INSTRUMENT validation observations"
        )
    observation_hashes = tuple(sorted(item.content_sha256 for item in observations))
    return ModelLockReceipt(
        model_id=model_id,
        model_sha256=model_sha256,
        split_manifest_sha256=split_manifest.content_sha256,
        evaluation_plan_sha256=evaluation_plan.content_sha256,
        validation_observation_sha256s=observation_hashes,
        validation_dataset_sha256=stable_json_hash(list(observation_hashes)),
        locked_at=timestamp,
    )


@dataclass(frozen=True, slots=True)
class HeldOutRelease:
    release_id: str
    observations: tuple[CalibrationObservation, ...]
    split_manifest_sha256: str
    model_lock_sha256: str
    released_at: datetime
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_id", _nonblank(self.release_id, "release_id"))
        observations = _sequence(self.observations, "observations")
        if not observations or any(not isinstance(item, CalibrationObservation) for item in observations):
            raise CalibrationProgramContractError("held-out observations must not be empty")
        identifiers = [item.descriptor.observation_id for item in observations]
        if len(identifiers) != len(set(identifiers)):
            raise CalibrationProgramContractError("held-out observations contain duplicate IDs")
        if any(item.outcome.origin is not EvidenceOrigin.REAL_INSTRUMENT for item in observations):
            raise CalibrationProgramContractError(
                "held-out release requires REAL_INSTRUMENT observations"
            )
        object.__setattr__(self, "observations", tuple(sorted(observations, key=lambda item: item.descriptor.observation_id)))
        object.__setattr__(self, "split_manifest_sha256", _sha256(self.split_manifest_sha256, "split_manifest_sha256"))
        object.__setattr__(self, "model_lock_sha256", _sha256(self.model_lock_sha256, "model_lock_sha256"))
        object.__setattr__(self, "released_at", _aware_datetime(self.released_at, "released_at"))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-held-out-release-v1",
            "release_id": self.release_id,
            "observations": [item.to_mapping() for item in self.observations],
            "split_manifest_sha256": self.split_manifest_sha256,
            "model_lock_sha256": self.model_lock_sha256,
            "released_at": _datetime_text(self.released_at),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


def release_held_out(
    *,
    release_id: str,
    observations: Sequence[CalibrationObservation],
    split_manifest: SplitManifest,
    model_lock: ModelLockReceipt,
    released_at: datetime,
) -> HeldOutRelease:
    """Release only the exact held-out partition after the matching model lock."""

    if not isinstance(split_manifest, SplitManifest):
        raise CalibrationProgramContractError("split_manifest must be a SplitManifest")
    if not isinstance(model_lock, ModelLockReceipt):
        raise CalibrationProgramContractError("model_lock must be a ModelLockReceipt")
    if model_lock.split_manifest_sha256 != split_manifest.content_sha256:
        raise CalibrationProgramContractError("model lock does not match split manifest")
    timestamp = _aware_datetime(released_at, "released_at")
    if timestamp <= model_lock.locked_at:
        raise CalibrationProgramContractError("held-out release must occur after model lock")
    items = _sequence(observations, "observations")
    expected_ids = {
        item.descriptor.observation_id
        for item in split_manifest.assignments
        if item.partition is Partition.HELD_OUT_TEST
    }
    actual_ids = {item.descriptor.observation_id for item in items}
    if actual_ids != expected_ids:
        raise CalibrationProgramContractError(
            "held-out observations must exactly match held-out partition"
        )
    return HeldOutRelease(
        release_id=release_id,
        observations=tuple(items),
        split_manifest_sha256=split_manifest.content_sha256,
        model_lock_sha256=model_lock.content_sha256,
        released_at=timestamp,
    )


@dataclass(frozen=True, slots=True)
class MetricSummary:
    total_count: int
    scored_count: int
    bias: float | None
    mae: float | None
    rmse: float | None
    median_absolute_fold_error: float | None
    rank_agreement: float | None
    calibration_slope: float | None
    calibration_intercept: float | None
    prediction_interval_coverage: float | None
    catastrophic_outlier_count: int
    catastrophic_outlier_rate: float | None
    missing_domain_count: int
    missing_domain_rate: float
    abstention_count: int
    abstention_rate: float
    baseline_mae: float | None
    baseline_rmse: float | None
    baseline_median_absolute_fold_error: float | None
    mae_improvement_vs_baseline: float | None
    rmse_improvement_vs_baseline: float | None

    def to_mapping(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class GroupedMetricSummary:
    dimension: str
    group_id: str
    summary: MetricSummary

    def to_mapping(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "group_id": self.group_id,
            "summary": self.summary.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    authority: ReportAuthority
    decision: EvaluationDecision
    promotion_allowed: bool
    plan_sha256: str
    observation_sha256s: tuple[str, ...]
    overall: MetricSummary
    groups: tuple[GroupedMetricSummary, ...]
    failed_criteria: tuple[str, ...]
    warnings: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_sha256", _sha256(self.plan_sha256, "plan_sha256"))
        hashes = tuple(sorted(_sha256(item, "observation_sha256s") for item in self.observation_sha256s))
        if not hashes:
            raise CalibrationProgramContractError("observation_sha256s must not be empty")
        object.__setattr__(self, "observation_sha256s", hashes)
        object.__setattr__(self, "failed_criteria", tuple(sorted(self.failed_criteria)))
        object.__setattr__(self, "warnings", tuple(sorted(self.warnings)))
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c5-evaluation-report-v1",
            "authority": self.authority.value,
            "decision": self.decision.value,
            "promotion_allowed": self.promotion_allowed,
            "plan_sha256": self.plan_sha256,
            "observation_sha256s": list(self.observation_sha256s),
            "overall": self.overall.to_mapping(),
            "groups": [item.to_mapping() for item in self.groups],
            "failed_criteria": list(self.failed_criteria),
            "warnings": list(self.warnings),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class EmpiricalAssessment:
    status: EmpiricalStatus
    metrics: EvaluationReport | None
    promotion_allowed: bool
    reasons: tuple[str, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(sorted(self.reasons)))
        payload = {
            "schema": "c5-empirical-assessment-v1",
            "status": self.status.value,
            "metrics": None if self.metrics is None else self.metrics.to_mapping(),
            "promotion_allowed": self.promotion_allowed,
            "reasons": list(self.reasons),
        }
        object.__setattr__(self, "content_sha256", stable_json_hash(payload))


def _average_ranks(values: Sequence[float]) -> tuple[float, ...]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average = (start + 1 + end) / 2.0
        for offset in range(start, end):
            ranks[ordered[offset][0]] = average
        start = end
    return tuple(ranks)


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    left_delta = tuple(value - left_mean for value in left)
    right_delta = tuple(value - right_mean for value in right)
    denominator = math.sqrt(
        math.fsum(value * value for value in left_delta)
        * math.fsum(value * value for value in right_delta)
    )
    if denominator == 0.0:
        return None
    return math.fsum(
        left_value * right_value
        for left_value, right_value in zip(left_delta, right_delta, strict=True)
    ) / denominator


def _transform(value: float, scale: MetricScale) -> float:
    return math.log10(value) if scale is MetricScale.LOG10 else value


def _metric_summary(
    observations: Sequence[CalibrationObservation],
    *,
    plan: EvaluationPlan,
) -> MetricSummary:
    items = tuple(observations)
    total = len(items)
    if total == 0:
        raise CalibrationProgramContractError("metric group must not be empty")
    scored = tuple(item for item in items if item.outcome.state is ObservationState.VALUE)
    abstention_count = sum(item.outcome.state is ObservationState.ABSTAINED for item in items)
    missing_count = sum(item.outcome.state is ObservationState.MISSING for item in items)
    if not scored:
        return MetricSummary(
            total_count=total,
            scored_count=0,
            bias=None,
            mae=None,
            rmse=None,
            median_absolute_fold_error=None,
            rank_agreement=None,
            calibration_slope=None,
            calibration_intercept=None,
            prediction_interval_coverage=None,
            catastrophic_outlier_count=0,
            catastrophic_outlier_rate=None,
            missing_domain_count=missing_count,
            missing_domain_rate=missing_count / total,
            abstention_count=abstention_count,
            abstention_rate=abstention_count / total,
            baseline_mae=None,
            baseline_rmse=None,
            baseline_median_absolute_fold_error=None,
            mae_improvement_vs_baseline=None,
            rmse_improvement_vs_baseline=None,
        )
    observed_values: list[float] = []
    predicted_values: list[float] = []
    baseline_values: list[float] = []
    for item in scored:
        outcome = item.outcome
        if (
            outcome.observed_value is None
            or outcome.predicted_value is None
            or outcome.baseline_prediction is None
        ):
            raise CalibrationProgramContractError(
                "scored observations require observed, predicted, and baseline values"
            )
        observed_values.append(outcome.observed_value)
        predicted_values.append(outcome.predicted_value)
        baseline_values.append(outcome.baseline_prediction)
    observed = tuple(observed_values)
    predicted = tuple(predicted_values)
    baseline = tuple(baseline_values)
    observed_scale = tuple(_transform(value, plan.scale) for value in observed)
    predicted_scale = tuple(_transform(value, plan.scale) for value in predicted)
    baseline_scale = tuple(_transform(value, plan.scale) for value in baseline)
    errors = tuple(
        prediction - truth
        for prediction, truth in zip(predicted_scale, observed_scale, strict=True)
    )
    baseline_errors = tuple(
        prediction - truth
        for prediction, truth in zip(baseline_scale, observed_scale, strict=True)
    )
    mae = statistics.fmean(abs(value) for value in errors)
    rmse = math.sqrt(statistics.fmean(value * value for value in errors))
    baseline_mae = statistics.fmean(abs(value) for value in baseline_errors)
    baseline_rmse = math.sqrt(
        statistics.fmean(value * value for value in baseline_errors)
    )
    fold_errors = tuple(
        max(prediction / truth, truth / prediction)
        for prediction, truth in zip(predicted, observed, strict=True)
    )
    baseline_folds = tuple(
        max(prediction / truth, truth / prediction)
        for prediction, truth in zip(baseline, observed, strict=True)
    )
    rank = _correlation(_average_ranks(predicted), _average_ranks(observed))
    predicted_mean = statistics.fmean(predicted_scale)
    observed_mean = statistics.fmean(observed_scale)
    denominator = math.fsum(
        (value - predicted_mean) ** 2 for value in predicted_scale
    )
    if len(scored) < 2 or denominator == 0.0:
        slope = None
        intercept = None
    else:
        slope = math.fsum(
            (prediction - predicted_mean) * (truth - observed_mean)
            for prediction, truth in zip(predicted_scale, observed_scale, strict=True)
        ) / denominator
        intercept = observed_mean - slope * predicted_mean
    covered = 0
    for item in scored:
        outcome = item.outcome
        if (
            outcome.prediction_interval_lower is None
            or outcome.observed_value is None
            or outcome.prediction_interval_upper is None
        ):
            raise CalibrationProgramContractError(
                "scored observations require a complete prediction interval"
            )
        if (
            outcome.prediction_interval_lower
            <= outcome.observed_value
            <= outcome.prediction_interval_upper
        ):
            covered += 1
    catastrophic = sum(
        fold >= plan.catastrophic_fold_threshold for fold in fold_errors
    )
    return MetricSummary(
        total_count=total,
        scored_count=len(scored),
        bias=statistics.fmean(errors),
        mae=mae,
        rmse=rmse,
        median_absolute_fold_error=statistics.median(fold_errors),
        rank_agreement=rank,
        calibration_slope=slope,
        calibration_intercept=intercept,
        prediction_interval_coverage=covered / len(scored),
        catastrophic_outlier_count=catastrophic,
        catastrophic_outlier_rate=catastrophic / len(scored),
        missing_domain_count=missing_count,
        missing_domain_rate=missing_count / total,
        abstention_count=abstention_count,
        abstention_rate=abstention_count / total,
        baseline_mae=baseline_mae,
        baseline_rmse=baseline_rmse,
        baseline_median_absolute_fold_error=statistics.median(baseline_folds),
        mae_improvement_vs_baseline=baseline_mae - mae,
        rmse_improvement_vs_baseline=baseline_rmse - rmse,
    )


def _group_id(
    observation: CalibrationObservation,
    dimension: str,
    material_classes: Mapping[str, str],
) -> str:
    if dimension == "material_class":
        try:
            return material_classes[observation.descriptor.material_id]
        except KeyError as exc:
            raise CalibrationProgramContractError(
                "observation material is absent from program panel"
            ) from exc
    if dimension == "matrix":
        return observation.descriptor.matrix_id
    if dimension == "condition":
        return observation.descriptor.condition_id
    raise CalibrationProgramContractError(f"unknown grouping dimension: {dimension}")


def _group_metrics(
    observations: Sequence[CalibrationObservation],
    *,
    program: CalibrationProgram,
    plan: EvaluationPlan,
) -> tuple[GroupedMetricSummary, ...]:
    classes = {item.inventory_name: item.chemical_class for item in program.materials}
    result: list[GroupedMetricSummary] = []
    for dimension in plan.group_dimensions:
        groups: dict[str, list[CalibrationObservation]] = defaultdict(list)
        for observation in observations:
            groups[_group_id(observation, dimension, classes)].append(observation)
        for group_id, group_observations in sorted(groups.items()):
            result.append(
                GroupedMetricSummary(
                    dimension=dimension,
                    group_id=group_id,
                    summary=_metric_summary(group_observations, plan=plan),
                )
            )
    return tuple(result)


def _metric_value(summary: MetricSummary, metric: MetricName) -> float | None:
    values: dict[MetricName, float | None] = {
        MetricName.BIAS: summary.bias,
        MetricName.MAE: summary.mae,
        MetricName.RMSE: summary.rmse,
        MetricName.MEDIAN_ABSOLUTE_FOLD_ERROR: summary.median_absolute_fold_error,
        MetricName.RANK_AGREEMENT: summary.rank_agreement,
        MetricName.CALIBRATION_SLOPE: summary.calibration_slope,
        MetricName.CALIBRATION_INTERCEPT: summary.calibration_intercept,
        MetricName.PREDICTION_INTERVAL_COVERAGE: summary.prediction_interval_coverage,
        MetricName.CATASTROPHIC_OUTLIER_RATE: summary.catastrophic_outlier_rate,
        MetricName.MISSING_DOMAIN_RATE: summary.missing_domain_rate,
        MetricName.ABSTENTION_RATE: summary.abstention_rate,
        MetricName.RMSE_IMPROVEMENT_VS_BASELINE: summary.rmse_improvement_vs_baseline,
    }
    return values[metric]


def _failed_criteria(
    plan: EvaluationPlan,
    overall: MetricSummary,
    groups: Sequence[GroupedMetricSummary],
) -> tuple[str, ...]:
    group_map = {(item.dimension, item.group_id): item.summary for item in groups}
    failed: list[str] = []
    for criterion in plan.criteria:
        summary = (
            overall
            if criterion.group_dimension is None
            else group_map.get((criterion.group_dimension, str(criterion.group_id)))
        )
        value = None if summary is None else _metric_value(summary, criterion.metric)
        if value is None:
            failed.append(criterion.criterion_id)
            continue
        passed = (
            value <= criterion.threshold
            if criterion.comparator is Comparator.LESS_THAN_OR_EQUAL
            else value >= criterion.threshold
        )
        if not passed:
            failed.append(criterion.criterion_id)
    return tuple(sorted(failed))


def _evaluate(
    observations: Sequence[CalibrationObservation],
    *,
    program: CalibrationProgram,
    plan: EvaluationPlan,
    authority: ReportAuthority,
) -> EvaluationReport:
    items = _sequence(observations, "observations")
    if not items or any(not isinstance(item, CalibrationObservation) for item in items):
        raise CalibrationProgramContractError(
            "observations must contain CalibrationObservation values"
        )
    expected_origin = (
        EvidenceOrigin.REAL_INSTRUMENT
        if authority is ReportAuthority.REAL_INSTRUMENT_ONLY
        else EvidenceOrigin.SIMULATED_SMOKE
    )
    if any(item.outcome.origin is not expected_origin for item in items):
        raise CalibrationProgramContractError(
            f"evaluation requires {expected_origin.value} observations"
        )
    overall = _metric_summary(items, plan=plan)
    groups = _group_metrics(items, program=program, plan=plan)
    failed = _failed_criteria(plan, overall, groups)
    warnings: tuple[str, ...]
    if authority is ReportAuthority.SIMULATION_ONLY:
        decision = EvaluationDecision.NOT_ELIGIBLE
        promotion_allowed = False
        warnings = (
            "SIMULATION_ONLY_NO_EMPIRICAL_AUTHORITY",
            "BLOCKED_PENDING_REAL_INSTRUMENT_DATA",
        )
    else:
        decision = EvaluationDecision.FAIL if failed else EvaluationDecision.PASS
        promotion_allowed = not failed
        warnings = ()
    return EvaluationReport(
        authority=authority,
        decision=decision,
        promotion_allowed=promotion_allowed,
        plan_sha256=plan.content_sha256,
        observation_sha256s=tuple(item.content_sha256 for item in items),
        overall=overall,
        groups=groups,
        failed_criteria=failed,
        warnings=warnings,
    )


def evaluate_simulation_smoke(
    observations: Sequence[CalibrationObservation],
    *,
    program: CalibrationProgram,
    plan: EvaluationPlan,
) -> EvaluationReport:
    """Exercise metric formulas without creating empirical calibration evidence."""

    return _evaluate(
        observations,
        program=program,
        plan=plan,
        authority=ReportAuthority.SIMULATION_ONLY,
    )


def evaluate_real_held_out(
    release: HeldOutRelease,
    *,
    program: CalibrationProgram,
    plan: EvaluationPlan,
    model_lock: ModelLockReceipt,
) -> EvaluationReport:
    """Evaluate real held-out outcomes only after exact plan/model lock binding."""

    if not isinstance(release, HeldOutRelease):
        raise CalibrationProgramContractError("release must be a HeldOutRelease")
    if release.model_lock_sha256 != model_lock.content_sha256:
        raise CalibrationProgramContractError("held-out release does not match model lock")
    if model_lock.evaluation_plan_sha256 != plan.content_sha256:
        raise CalibrationProgramContractError("model lock does not match evaluation plan")
    if release.released_at <= model_lock.locked_at:
        raise CalibrationProgramContractError("held-out outcomes were not released after model lock")
    return _evaluate(
        release.observations,
        program=program,
        plan=plan,
        authority=ReportAuthority.REAL_INSTRUMENT_ONLY,
    )


def assess_empirical_readiness(
    *,
    program: CalibrationProgram,
    protocols: Sequence[ExperimentalProtocol] = (),
    observations: Sequence[CalibrationObservation] = (),
    split_manifest: SplitManifest | None = None,
    evaluation_plan: EvaluationPlan | None = None,
    model_lock: ModelLockReceipt | None = None,
) -> EmpiricalAssessment:
    """Return an honest no-metrics readiness assessment until all gates exist."""

    reasons: list[str] = []
    if not protocols:
        reasons.append("NO_B5_BOUND_PROTOCOL")
    real_observations = tuple(
        item
        for item in observations
        if isinstance(item, CalibrationObservation)
        and item.outcome.origin is EvidenceOrigin.REAL_INSTRUMENT
    )
    if not real_observations:
        reasons.append("NO_REAL_INSTRUMENT_OBSERVATIONS")
    if split_manifest is None:
        reasons.append("NO_LOCKED_LEAK_RESISTANT_SPLIT")
    if evaluation_plan is None:
        reasons.append("NO_PRESPECIFIED_EVALUATION_PLAN")
    if model_lock is None:
        reasons.append("NO_PRE_HELD_OUT_MODEL_LOCK")
    status = (
        EmpiricalStatus.BLOCKED_PENDING_DATA
        if reasons
        else EmpiricalStatus.READY_FOR_EVALUATION
    )
    return EmpiricalAssessment(
        status=status,
        metrics=None,
        promotion_allowed=False,
        reasons=tuple(reasons),
    )


__all__ = [
    "C5_INVENTORY_SHA256",
    "LEAKAGE_DIMENSIONS",
    "REQUIRED_GROUP_DIMENSIONS",
    "REQUIRED_METRICS",
    "AcceptanceCriterion",
    "B5AuthorityReceipt",
    "B5MethodBinding",
    "CalibrationObservation",
    "CalibrationProgram",
    "CalibrationProgramContractError",
    "Comparator",
    "EmpiricalAssessment",
    "EmpiricalStatus",
    "EvaluationDecision",
    "EvaluationPlan",
    "EvaluationReport",
    "EvidenceOrigin",
    "ExperimentalProtocol",
    "GroupedMetricSummary",
    "HeldOutRelease",
    "MaterialPanelEntry",
    "MatrixAvailability",
    "MatrixComponent",
    "MatrixPanelEntry",
    "MetricName",
    "MetricScale",
    "MetricSummary",
    "ModelLockReceipt",
    "ObservationDescriptor",
    "ObservationOutcome",
    "ObservationState",
    "Partition",
    "ReportAuthority",
    "SplitAssignment",
    "SplitManifest",
    "assess_empirical_readiness",
    "build_c5_program",
    "evaluate_real_held_out",
    "evaluate_simulation_smoke",
    "import_real_measurements_jsonl",
    "lock_model",
    "release_held_out",
]
