"""Condition-bound physicochemical evidence packets.

This module records caller-supplied physicochemical values without promoting
them into perfume, sensory, safety, performance, or release conclusions.  OAV
is checked only as concentration ppm divided by a source-bound ODT normalized
to ppm.  Headspace values are explicitly computational predictions; instrument
observations remain separate records.  Naturals can use only a source-bound
composite decomposition and can never fall back to monomolecular OAV.
"""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, TypeVar, cast

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    UnknownFact,
)

_RecordT = TypeVar("_RecordT", bound="_Record")
_MODULE_ID = "formulation_intelligence.physicochemical_plane"
_PHYSICOCHEMICAL_CEILING = AuthorityCeiling.EVIDENCE_LIMITED
_PREDICTION_CEILING = AuthorityCeiling.HYPOTHESIS_ONLY


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _optional_text(
    value: object | None,
    field_name: str,
    *,
    identifier: bool = False,
) -> str | None:
    if value is None:
        return None
    return _text(value, field_name, identifier=identifier)


def _finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")
    return normalized


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _Record):
        return value.as_dict()
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return value.as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not permit non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _closed_payload(
    payload: Mapping[str, Any],
    record_type: type[_RecordT],
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("canonical payload must be a mapping")
    expected = {"schema_version", *(item.name for item in fields(cast(Any, record_type)))}
    received = set(payload)
    if received != expected:
        raise ValueError(
            f"{record_type.SCHEMA_VERSION} payload does not match the closed schema; "
            f"missing={sorted(expected - received)!r}, extra={sorted(received - expected)!r}"
        )
    if payload["schema_version"] != record_type.SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {record_type.SCHEMA_VERSION!r}, "
            f"received {payload['schema_version']!r}"
        )
    return payload


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _primitive(getattr(self, item.name)) for item in fields(cast(Any, self))},
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_bytes(self.as_dict())).hexdigest()


def _provenance(values: Iterable[ProvenanceRef]) -> tuple[ProvenanceRef, ...]:
    by_id: dict[str, ProvenanceRef] = {}
    for value in values:
        if not isinstance(value, ProvenanceRef):
            raise TypeError("provenance_refs must contain ProvenanceRef values")
        current = by_id.get(value.provenance_id)
        if current is not None and current != value:
            raise ValueError(f"provenance_id {value.provenance_id!r} has conflicting definitions")
        by_id[value.provenance_id] = value
    return tuple(by_id[key] for key in sorted(by_id))


def _unique_records(
    values: Iterable[_RecordT],
    *,
    record_type: type[_RecordT],
    id_attribute: str,
    field_name: str,
) -> tuple[_RecordT, ...]:
    by_id: dict[str, _RecordT] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = cast(str, getattr(value, id_attribute))
        if identifier in by_id:
            raise ValueError(f"{field_name} repeats {id_attribute} {identifier!r}")
        by_id[identifier] = value
    return tuple(by_id[key] for key in sorted(by_id))


class MaterialKind(str, Enum):
    EXACT_MOLECULE = "exact_molecule"
    NATURAL_MIXTURE = "natural_mixture"
    OPAQUE_MIXTURE = "opaque_mixture"


class ConcentrationBasis(str, Enum):
    PPM_W_W_CONCENTRATE = "ppm w/w in concentrate"


class ODTUnit(str, Enum):
    PPM = "ppm"
    PPB = "ppb"


class ODTKind(str, Enum):
    MONOMOLECULAR = "monomolecular"
    COMPOSITE_EFFECTIVE = "composite_effective"
    BULK_MIXTURE = "bulk_mixture"


class OAVMethod(str, Enum):
    MONOMOLECULAR = "monomolecular"
    NATURAL_COMPOSITE = "natural_composite"
    BULK_MIXTURE_REFERENCE = "bulk_mixture_reference"


class QuantitativeState(str, Enum):
    READY = "ready"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class PhysicochemicalScope(_Record):
    """Exact target, sample, material, matrix, condition, temperature, and time."""

    SCHEMA_VERSION = "physicochemical_scope_v1"

    target_scope: str
    sample_id: str
    material_identity_id: str
    matrix_id: str
    condition_id: str
    temperature_c: float
    elapsed_seconds: float
    temporal_scope: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_scope",
            "sample_id",
            "material_identity_id",
            "matrix_id",
            "condition_id",
            "temporal_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        temperature = _finite(self.temperature_c, "temperature_c")
        if temperature <= -273.15:
            raise ValueError("temperature_c must be above absolute zero")
        elapsed = _finite(self.elapsed_seconds, "elapsed_seconds")
        if elapsed < 0.0:
            raise ValueError("elapsed_seconds must be nonnegative")
        object.__setattr__(self, "temperature_c", temperature)
        object.__setattr__(self, "elapsed_seconds", elapsed)

    @property
    def key(self) -> tuple[str, str, str, str, str, float, float, str]:
        return (
            self.target_scope,
            self.sample_id,
            self.material_identity_id,
            self.matrix_id,
            self.condition_id,
            self.temperature_c,
            self.elapsed_seconds,
            self.temporal_scope,
        )

    @property
    def assessment_scope(self) -> AssessmentScope:
        sample = self.sample_id
        material = self.material_identity_id
        matrix = self.matrix_id
        condition = self.condition_id
        return AssessmentScope(
            target_scope=self.target_scope,
            temporal_scope=(f"{self.temporal_scope};elapsed_seconds={self.elapsed_seconds:.12g}"),
            matrix_scope=(
                f"matrix[{len(matrix)}]={matrix};sample[{len(sample)}]={sample};"
                f"material[{len(material)}]={material};"
                f"condition[{len(condition)}]={condition};"
                f"temperature_c={self.temperature_c:.12g}"
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PhysicochemicalScope:
        data = _closed_payload(payload, cls)
        return cls(
            target_scope=data["target_scope"],
            sample_id=data["sample_id"],
            material_identity_id=data["material_identity_id"],
            matrix_id=data["matrix_id"],
            condition_id=data["condition_id"],
            temperature_c=data["temperature_c"],
            elapsed_seconds=data["elapsed_seconds"],
            temporal_scope=data["temporal_scope"],
        )


@dataclass(frozen=True, slots=True)
class PhysicochemicalMaterialIdentity(_Record):
    """Exact material/lot identity plus explicitly nullable stock preparation facts."""

    SCHEMA_VERSION = "physicochemical_material_identity_v1"

    material_id: str
    kind: MaterialKind
    material_label: str
    exact_identity_key: str
    source_name: str | None
    lot_id: str | None
    stock_fraction: float | None
    fraction_basis: str | None
    carrier_identity: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "material_id", _text(self.material_id, "material_id", identifier=True)
        )
        object.__setattr__(self, "kind", MaterialKind(self.kind))
        object.__setattr__(self, "material_label", _text(self.material_label, "material_label"))
        object.__setattr__(
            self,
            "exact_identity_key",
            _text(self.exact_identity_key, "exact_identity_key", identifier=True),
        )
        object.__setattr__(self, "source_name", _optional_text(self.source_name, "source_name"))
        object.__setattr__(self, "lot_id", _optional_text(self.lot_id, "lot_id", identifier=True))
        if self.stock_fraction is not None:
            fraction = _finite(self.stock_fraction, "stock_fraction")
            if not 0.0 < fraction <= 1.0:
                raise ValueError("stock_fraction must be within (0, 1]")
            object.__setattr__(self, "stock_fraction", fraction)
        object.__setattr__(
            self,
            "fraction_basis",
            _optional_text(self.fraction_basis, "fraction_basis", identifier=True),
        )
        object.__setattr__(
            self,
            "carrier_identity",
            _optional_text(self.carrier_identity, "carrier_identity", identifier=True),
        )

    @property
    def stock_facts_complete(self) -> bool:
        return (
            self.stock_fraction is not None
            and self.fraction_basis is not None
            and self.carrier_identity is not None
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PhysicochemicalMaterialIdentity:
        data = _closed_payload(payload, cls)
        return cls(
            material_id=data["material_id"],
            kind=MaterialKind(data["kind"]),
            material_label=data["material_label"],
            exact_identity_key=data["exact_identity_key"],
            source_name=data["source_name"],
            lot_id=data["lot_id"],
            stock_fraction=data["stock_fraction"],
            fraction_basis=data["fraction_basis"],
            carrier_identity=data["carrier_identity"],
        )


@dataclass(frozen=True, slots=True)
class OdorThresholdReference(_Record):
    """Positive, medium-bound, unit-declared, source-bound odor threshold."""

    SCHEMA_VERSION = "physicochemical_odt_reference_v1"

    threshold_id: str
    value: float
    unit: ODTUnit
    medium_id: str
    threshold_kind: ODTKind
    source: ProvenanceRef

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "threshold_id",
            _text(self.threshold_id, "threshold_id", identifier=True),
        )
        value = _finite(self.value, "value")
        if value <= 0.0:
            raise ValueError("ODT value must be positive")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", ODTUnit(self.unit))
        object.__setattr__(self, "medium_id", _text(self.medium_id, "medium_id", identifier=True))
        object.__setattr__(self, "threshold_kind", ODTKind(self.threshold_kind))
        if not isinstance(self.source, ProvenanceRef):
            raise TypeError("source must be a ProvenanceRef")

    @property
    def value_ppm(self) -> float:
        return self.value if self.unit is ODTUnit.PPM else self.value / 1_000.0

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OdorThresholdReference:
        data = _closed_payload(payload, cls)
        return cls(
            threshold_id=data["threshold_id"],
            value=data["value"],
            unit=ODTUnit(data["unit"]),
            medium_id=data["medium_id"],
            threshold_kind=ODTKind(data["threshold_kind"]),
            source=ProvenanceRef.from_dict(data["source"]),
        )


@dataclass(frozen=True, slots=True)
class CompositeConstituent(_Record):
    """One exact constituent in a natural composite decomposition."""

    SCHEMA_VERSION = "physicochemical_composite_constituent_v1"

    constituent_id: str
    exact_identity_key: str
    fraction: float
    fraction_basis: str
    odt: OdorThresholdReference | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "constituent_id",
            _text(self.constituent_id, "constituent_id", identifier=True),
        )
        object.__setattr__(
            self,
            "exact_identity_key",
            _text(self.exact_identity_key, "exact_identity_key", identifier=True),
        )
        fraction = _finite(self.fraction, "fraction")
        if not 0.0 < fraction <= 1.0:
            raise ValueError("constituent fraction must be within (0, 1]")
        object.__setattr__(self, "fraction", fraction)
        object.__setattr__(
            self,
            "fraction_basis",
            _text(self.fraction_basis, "fraction_basis", identifier=True),
        )
        if self.odt is not None:
            if not isinstance(self.odt, OdorThresholdReference):
                raise TypeError("odt must be an OdorThresholdReference or None")
            if self.odt.threshold_kind is not ODTKind.MONOMOLECULAR:
                raise ValueError("constituent ODT must be monomolecular")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CompositeConstituent:
        data = _closed_payload(payload, cls)
        return cls(
            constituent_id=data["constituent_id"],
            exact_identity_key=data["exact_identity_key"],
            fraction=data["fraction"],
            fraction_basis=data["fraction_basis"],
            odt=(
                OdorThresholdReference.from_dict(data["odt"]) if data["odt"] is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class NaturalCompositeDecomposition(_Record):
    """Source-bound decomposition for one exact natural material identity."""

    SCHEMA_VERSION = "physicochemical_natural_composite_v1"

    decomposition_id: str
    material_identity_id: str
    method_version: str
    constituents: tuple[CompositeConstituent, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decomposition_id",
            _text(self.decomposition_id, "decomposition_id", identifier=True),
        )
        object.__setattr__(
            self,
            "material_identity_id",
            _text(self.material_identity_id, "material_identity_id", identifier=True),
        )
        object.__setattr__(self, "method_version", _text(self.method_version, "method_version"))
        constituents = _unique_records(
            self.constituents,
            record_type=CompositeConstituent,
            id_attribute="constituent_id",
            field_name="constituents",
        )
        if not constituents:
            raise ValueError("natural composite decomposition requires constituents")
        if sum(item.fraction for item in constituents) > 1.0 + 1e-12:
            raise ValueError("natural constituent fractions must not exceed 1.0")
        object.__setattr__(self, "constituents", constituents)
        provenance = _provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("natural composite decomposition requires provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @property
    def is_quantitatively_complete(self) -> bool:
        return all(item.odt is not None for item in self.constituents)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NaturalCompositeDecomposition:
        data = _closed_payload(payload, cls)
        return cls(
            decomposition_id=data["decomposition_id"],
            material_identity_id=data["material_identity_id"],
            method_version=data["method_version"],
            constituents=tuple(
                CompositeConstituent.from_dict(item) for item in data["constituents"]
            ),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class HeadspacePrediction(_Record):
    """A computational prediction; never an observed headspace value."""

    SCHEMA_VERSION = "physicochemical_headspace_prediction_v1"

    prediction_id: str
    scope: PhysicochemicalScope
    variable_key: str
    value: float
    unit: str
    model_id: str
    model_version: str
    support: SupportInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prediction_id",
            _text(self.prediction_id, "prediction_id", identifier=True),
        )
        if not isinstance(self.scope, PhysicochemicalScope):
            raise TypeError("scope must be a PhysicochemicalScope")
        object.__setattr__(
            self, "variable_key", _text(self.variable_key, "variable_key", identifier=True)
        )
        object.__setattr__(self, "value", _finite(self.value, "value"))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id", identifier=True))
        object.__setattr__(self, "model_version", _text(self.model_version, "model_version"))
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        expected_claim_id = f"physchem.prediction:{self.prediction_id}"
        if self.support.claim_id != expected_claim_id:
            raise ValueError(f"prediction support claim_id must be {expected_claim_id!r}")
        provenance = _provenance(self.provenance_refs)
        if not provenance or not any(
            item.evidence_class is EvidenceClass.COMPUTATIONAL_MODEL for item in provenance
        ):
            raise ValueError("headspace predictions require computational_model provenance")
        if any(
            item.evidence_class
            in {EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.INSTRUMENTAL_OBSERVATION}
            for item in provenance
        ):
            raise ValueError("headspace predictions cannot carry observation provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HeadspacePrediction:
        data = _closed_payload(payload, cls)
        return cls(
            prediction_id=data["prediction_id"],
            scope=PhysicochemicalScope.from_dict(data["scope"]),
            variable_key=data["variable_key"],
            value=data["value"],
            unit=data["unit"],
            model_id=data["model_id"],
            model_version=data["model_version"],
            support=SupportInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class InstrumentalObservation(_Record):
    """A protocol-bound instrument observation, separate from predictions."""

    SCHEMA_VERSION = "physicochemical_instrumental_observation_v1"

    observation_id: str
    scope: PhysicochemicalScope
    endpoint_key: str
    value: float
    unit: str
    instrument_id: str
    protocol_id: str
    support: SupportInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _text(self.observation_id, "observation_id", identifier=True),
        )
        if not isinstance(self.scope, PhysicochemicalScope):
            raise TypeError("scope must be a PhysicochemicalScope")
        object.__setattr__(
            self, "endpoint_key", _text(self.endpoint_key, "endpoint_key", identifier=True)
        )
        object.__setattr__(self, "value", _finite(self.value, "value"))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        object.__setattr__(
            self, "instrument_id", _text(self.instrument_id, "instrument_id", identifier=True)
        )
        object.__setattr__(
            self, "protocol_id", _text(self.protocol_id, "protocol_id", identifier=True)
        )
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        expected_claim_id = f"physchem.observation:{self.observation_id}"
        if self.support.claim_id != expected_claim_id:
            raise ValueError(f"observation support claim_id must be {expected_claim_id!r}")
        provenance = _provenance(self.provenance_refs)
        if not provenance or not any(
            item.evidence_class
            in {EvidenceClass.INSTRUMENTAL_OBSERVATION, EvidenceClass.DIRECT_OBSERVATION}
            for item in provenance
        ):
            raise ValueError("instrumental observations require observation provenance")
        if any(item.evidence_class is EvidenceClass.COMPUTATIONAL_MODEL for item in provenance):
            raise ValueError("instrumental observations cannot be model predictions")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> InstrumentalObservation:
        data = _closed_payload(payload, cls)
        return cls(
            observation_id=data["observation_id"],
            scope=PhysicochemicalScope.from_dict(data["scope"]),
            endpoint_key=data["endpoint_key"],
            value=data["value"],
            unit=data["unit"],
            instrument_id=data["instrument_id"],
            protocol_id=data["protocol_id"],
            support=SupportInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class PhysicochemicalPacket(_Record):
    """One immutable exact-scope packet; missing quantitative facts cause HOLD."""

    SCHEMA_VERSION = "physicochemical_packet_v1"

    packet_id: str
    scope: PhysicochemicalScope
    material: PhysicochemicalMaterialIdentity
    concentration_ppm: float | None
    concentration_basis: ConcentrationBasis | None
    odt: OdorThresholdReference | None
    oav: float | None
    oav_method: OAVMethod | None
    composite_decomposition: NaturalCompositeDecomposition | None
    quantitative_support: SupportInterval | None
    headspace_predictions: tuple[HeadspacePrediction, ...]
    instrumental_observations: tuple[InstrumentalObservation, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _text(self.packet_id, "packet_id", identifier=True))
        if not isinstance(self.scope, PhysicochemicalScope):
            raise TypeError("scope must be a PhysicochemicalScope")
        if not isinstance(self.material, PhysicochemicalMaterialIdentity):
            raise TypeError("material must be a PhysicochemicalMaterialIdentity")
        if self.scope.material_identity_id != self.material.material_id:
            raise ValueError("scope material identity must equal packet material identity")

        if self.concentration_ppm is not None:
            concentration = _finite(self.concentration_ppm, "concentration_ppm")
            if concentration < 0.0:
                raise ValueError("concentration_ppm must be nonnegative")
            object.__setattr__(self, "concentration_ppm", concentration)
        if self.concentration_basis is not None:
            object.__setattr__(
                self, "concentration_basis", ConcentrationBasis(self.concentration_basis)
            )
        if self.odt is not None and not isinstance(self.odt, OdorThresholdReference):
            raise TypeError("odt must be an OdorThresholdReference or None")
        if self.oav is not None:
            oav = _finite(self.oav, "oav")
            if oav < 0.0:
                raise ValueError("oav must be nonnegative")
            object.__setattr__(self, "oav", oav)
        if self.oav_method is not None:
            object.__setattr__(self, "oav_method", OAVMethod(self.oav_method))
        if self.composite_decomposition is not None and not isinstance(
            self.composite_decomposition, NaturalCompositeDecomposition
        ):
            raise TypeError(
                "composite_decomposition must be a NaturalCompositeDecomposition or None"
            )
        if self.quantitative_support is not None and not isinstance(
            self.quantitative_support, SupportInterval
        ):
            raise TypeError("quantitative_support must be a SupportInterval or None")

        predictions = _unique_records(
            self.headspace_predictions,
            record_type=HeadspacePrediction,
            id_attribute="prediction_id",
            field_name="headspace_predictions",
        )
        observations = _unique_records(
            self.instrumental_observations,
            record_type=InstrumentalObservation,
            id_attribute="observation_id",
            field_name="instrumental_observations",
        )
        if any(item.scope.key != self.scope.key for item in predictions) or any(
            item.scope.key != self.scope.key for item in observations
        ):
            raise ValueError("predictions and observations must use the packet's exact scope")
        object.__setattr__(self, "headspace_predictions", predictions)
        object.__setattr__(self, "instrumental_observations", observations)
        provenance = _provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("physicochemical packets require provenance")
        object.__setattr__(self, "provenance_refs", provenance)

        self._validate_material_method()
        self._validate_oav()

    def _validate_material_method(self) -> None:
        kind = self.material.kind
        method = self.oav_method
        threshold_kind = self.odt.threshold_kind if self.odt is not None else None
        decomposition = self.composite_decomposition

        if kind is MaterialKind.NATURAL_MIXTURE:
            if method is OAVMethod.MONOMOLECULAR:
                raise ValueError("natural mixtures cannot use monomolecular OAV")
            if threshold_kind is ODTKind.MONOMOLECULAR:
                raise ValueError("natural mixtures cannot use a monomolecular bulk ODT")
            if decomposition is not None and (
                decomposition.material_identity_id != self.material.material_id
            ):
                raise ValueError("decomposition material identity does not match packet material")
            if self.oav is not None:
                if method is not OAVMethod.NATURAL_COMPOSITE:
                    raise ValueError("natural OAV requires natural_composite method")
                if threshold_kind is not ODTKind.COMPOSITE_EFFECTIVE:
                    raise ValueError("natural OAV requires a composite_effective ODT")
                if decomposition is None or not decomposition.is_quantitatively_complete:
                    raise ValueError("natural OAV requires a complete composite decomposition")
            return

        if decomposition is not None:
            raise ValueError("only natural mixtures may carry a natural decomposition")
        if kind is MaterialKind.EXACT_MOLECULE:
            if method is OAVMethod.NATURAL_COMPOSITE:
                raise ValueError("exact molecules cannot use natural composite OAV")
            if threshold_kind is ODTKind.COMPOSITE_EFFECTIVE:
                raise ValueError("exact molecules cannot use composite_effective ODT")
            if self.oav is not None and method is not OAVMethod.MONOMOLECULAR:
                raise ValueError("exact molecule OAV requires monomolecular method")
        elif self.oav is not None:
            if method is not OAVMethod.BULK_MIXTURE_REFERENCE:
                raise ValueError("opaque mixture OAV requires bulk_mixture_reference method")
            if threshold_kind is not ODTKind.BULK_MIXTURE:
                raise ValueError("opaque mixture OAV requires a bulk_mixture ODT")

    def _validate_oav(self) -> None:
        if self.oav is None:
            if self.quantitative_support is not None:
                raise ValueError("quantitative_support requires an OAV value")
            return
        if self.concentration_ppm is None:
            raise ValueError("OAV requires concentration_ppm")
        if self.concentration_basis is None:
            raise ValueError("OAV requires concentration_basis")
        if self.odt is None:
            raise ValueError("OAV requires ODT")
        if self.oav_method is None:
            raise ValueError("OAV requires oav_method")
        if self.quantitative_support is None:
            raise ValueError("OAV requires quantitative_support")
        expected_claim_id = f"physchem.oav:{self.packet_id}"
        if self.quantitative_support.claim_id != expected_claim_id:
            raise ValueError(f"quantitative support claim_id must be {expected_claim_id!r}")
        expected = self.concentration_ppm / self.odt.value_ppm
        if not math.isclose(self.oav, expected, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(
                "OAV must equal concentration_ppm / ODT_ppm; "
                f"expected {expected:.15g}, received {self.oav:.15g}"
            )

    @property
    def calculated_oav(self) -> float | None:
        if (
            not self.material.stock_facts_complete
            or self.concentration_ppm is None
            or self.concentration_basis is None
            or self.odt is None
        ):
            return None
        if self.material.kind is MaterialKind.NATURAL_MIXTURE and (
            self.composite_decomposition is None
            or not self.composite_decomposition.is_quantitatively_complete
        ):
            return None
        return self.concentration_ppm / self.odt.value_ppm

    @property
    def blocking_fields(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.material.stock_fraction is None:
            blockers.append("stock_fraction")
        if self.material.fraction_basis is None:
            blockers.append("fraction_basis")
        if self.material.carrier_identity is None:
            blockers.append("carrier_identity")
        if self.concentration_ppm is None:
            blockers.append("concentration_ppm")
        if self.concentration_basis is None:
            blockers.append("concentration_basis")
        if self.odt is None:
            blockers.append("odt")
        if self.oav_method is None:
            blockers.append("oav_method")
        if self.oav is None:
            blockers.append("oav")
        if self.material.kind is MaterialKind.NATURAL_MIXTURE:
            if self.composite_decomposition is None:
                blockers.append("natural_composite_decomposition")
            elif not self.composite_decomposition.is_quantitatively_complete:
                blockers.append("natural_composite_constituent_odt")
        return tuple(sorted(set(blockers)))

    @property
    def quantitative_state(self) -> QuantitativeState:
        return QuantitativeState.HOLD if self.blocking_fields else QuantitativeState.READY

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PhysicochemicalPacket:
        data = _closed_payload(payload, cls)
        return cls(
            packet_id=data["packet_id"],
            scope=PhysicochemicalScope.from_dict(data["scope"]),
            material=PhysicochemicalMaterialIdentity.from_dict(data["material"]),
            concentration_ppm=data["concentration_ppm"],
            concentration_basis=(
                ConcentrationBasis(data["concentration_basis"])
                if data["concentration_basis"] is not None
                else None
            ),
            odt=(
                OdorThresholdReference.from_dict(data["odt"]) if data["odt"] is not None else None
            ),
            oav=data["oav"],
            oav_method=(OAVMethod(data["oav_method"]) if data["oav_method"] is not None else None),
            composite_decomposition=(
                NaturalCompositeDecomposition.from_dict(data["composite_decomposition"])
                if data["composite_decomposition"] is not None
                else None
            ),
            quantitative_support=(
                SupportInterval.from_dict(data["quantitative_support"])
                if data["quantitative_support"] is not None
                else None
            ),
            headspace_predictions=tuple(
                HeadspacePrediction.from_dict(item) for item in data["headspace_predictions"]
            ),
            instrumental_observations=tuple(
                InstrumentalObservation.from_dict(item)
                for item in data["instrumental_observations"]
            ),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


_BLOCKER_EVIDENCE: dict[str, tuple[str, str]] = {
    "stock_fraction": (
        "stock fraction is missing; no active amount may be inferred",
        "Bind the exact stock fraction for this material identity and lot.",
    ),
    "fraction_basis": (
        "stock fraction basis is missing; w/w and v/v are not interchangeable",
        "Bind the declared stock fraction basis.",
    ),
    "carrier_identity": (
        "carrier identity is missing; carrier displacement is not executable",
        "Bind the exact carrier, including an explicit neat/as-supplied declaration.",
    ),
    "concentration_ppm": (
        "concentration is missing; UNKNOWN is not numeric zero",
        "Supply concentration in ppm w/w in concentrate for the exact sample.",
    ),
    "concentration_basis": (
        "concentration basis is missing",
        "Declare ppm w/w in concentrate explicitly.",
    ),
    "odt": (
        "a medium-, unit-, and source-bound ODT is missing",
        "Supply an ODT with medium, unit, kind, and provenance.",
    ),
    "oav_method": (
        "the OAV method is missing",
        "Declare a material-kind-compatible OAV method.",
    ),
    "oav": (
        "OAV is unresolved; it must not be replaced by a dummy value",
        "Resolve concentration, ODT, method, and support, then compute ppm / ODT_ppm.",
    ),
    "natural_composite_decomposition": (
        "natural composite decomposition identity and constituents are missing",
        "Bind a source-backed exact-lot composite decomposition.",
    ),
    "natural_composite_constituent_odt": (
        "one or more exact composite constituents lacks a source-bound ODT",
        "Resolve every constituent ODT used by the composite calculation.",
    ),
}

_DOWNSTREAM_HOLDS: tuple[tuple[str, str, str], ...] = (
    (
        "downstream.perceived_contribution",
        "physicochemical values are not percent perceived contribution",
        "Obtain a target- and condition-matched sensory mixture study.",
    ),
    (
        "downstream.target_fit",
        "physicochemical values do not establish target fit",
        "Run a named-target comparison with an explicit target model.",
    ),
    (
        "downstream.observed_smell",
        "model values and instrument values do not establish observed smell",
        "Collect blinded participant-linked sensory observations.",
    ),
    (
        "downstream.liking",
        "no participant liking evidence is present",
        "Run a preregistered blinded hedonic study.",
    ),
    (
        "downstream.performance",
        "physicochemical screening does not prove performance",
        "Run condition-matched wear and headspace performance tests.",
    ),
    (
        "downstream.safety",
        "this plane has no safety authority",
        "Complete the applicable safety assessment and compliance review.",
    ),
    (
        "downstream.release",
        "this plane has no release authority",
        "Complete independent release gates after physical and sensory validation.",
    ),
)


def _all_packet_provenance(packet: PhysicochemicalPacket) -> tuple[ProvenanceRef, ...]:
    nested: list[ProvenanceRef] = list(packet.provenance_refs)
    if packet.odt is not None:
        nested.append(packet.odt.source)
    if packet.quantitative_support is not None:
        nested.extend(packet.quantitative_support.provenance_refs)
    if packet.composite_decomposition is not None:
        nested.extend(packet.composite_decomposition.provenance_refs)
        for constituent in packet.composite_decomposition.constituents:
            if constituent.odt is not None:
                nested.append(constituent.odt.source)
    for prediction in packet.headspace_predictions:
        nested.extend(prediction.provenance_refs)
        nested.extend(prediction.support.provenance_refs)
    for observation in packet.instrumental_observations:
        nested.extend(observation.provenance_refs)
        nested.extend(observation.support.provenance_refs)
    return _provenance(nested)


def build_physicochemical_plane_assessment(
    packet: PhysicochemicalPacket,
    *,
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.EVIDENCE_LIMITED,
) -> PlaneAssessment:
    """Adapt one packet without converting predictions into observations."""

    if not isinstance(packet, PhysicochemicalPacket):
        raise TypeError("packet must be a PhysicochemicalPacket")
    packet_limit = (
        _PHYSICOCHEMICAL_CEILING if packet.instrumental_observations else _PREDICTION_CEILING
    )
    authority = AuthorityCeiling.minimum((AuthorityCeiling(authority_ceiling), packet_limit))
    prediction_authority = AuthorityCeiling.minimum((authority, _PREDICTION_CEILING))
    provenance = _all_packet_provenance(packet)

    claims: list[ScopedClaim] = [
        ScopedClaim(
            claim_id=f"physchem.state:{packet.packet_id}",
            claim_key="physicochemical.quantitative_state",
            claim_value=packet.quantitative_state.value,
            claim_kind=ClaimKind.DIAGNOSTIC,
            authority_ceiling=prediction_authority,
            provenance_refs=packet.provenance_refs,
        )
    ]
    if packet.concentration_ppm is not None and packet.concentration_basis is not None:
        claims.append(
            ScopedClaim(
                claim_id=f"physchem.concentration:{packet.packet_id}",
                claim_key="physicochemical.concentration_ppm",
                claim_value=(
                    f"{packet.concentration_ppm:.15g} ppm; basis={packet.concentration_basis.value}"
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                authority_ceiling=prediction_authority,
                provenance_refs=packet.provenance_refs,
            )
        )
    if packet.odt is not None:
        claims.append(
            ScopedClaim(
                claim_id=f"physchem.odt:{packet.packet_id}",
                claim_key="physicochemical.odt",
                claim_value=(
                    f"{packet.odt.value:.15g} {packet.odt.unit.value}; "
                    f"medium={packet.odt.medium_id}; kind={packet.odt.threshold_kind.value}; "
                    f"source={packet.odt.source.source_ref}"
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                authority_ceiling=prediction_authority,
                provenance_refs=(packet.odt.source,),
            )
        )
    if packet.oav is not None:
        assert packet.quantitative_support is not None
        claims.append(
            ScopedClaim(
                claim_id=f"physchem.oav:{packet.packet_id}",
                claim_key="physicochemical.oav",
                claim_value=(
                    f"{packet.oav:.15g}; method={cast(OAVMethod, packet.oav_method).value}; "
                    "screening only, not perceived contribution"
                ),
                claim_kind=ClaimKind.DIAGNOSTIC,
                authority_ceiling=prediction_authority,
                provenance_refs=_provenance(
                    (*packet.provenance_refs, *packet.quantitative_support.provenance_refs)
                ),
            )
        )
    claims.extend(
        ScopedClaim(
            claim_id=f"physchem.prediction:{item.prediction_id}",
            claim_key=f"physicochemical.prediction.{item.variable_key}",
            claim_value=(
                f"computational prediction: {item.value:.15g} {item.unit}; "
                f"model={item.model_id}; version={item.model_version}"
            ),
            claim_kind=ClaimKind.DIAGNOSTIC,
            authority_ceiling=prediction_authority,
            provenance_refs=item.provenance_refs,
            cardinality=ClaimCardinality.SET_MEMBER,
            member_id=item.prediction_id,
        )
        for item in packet.headspace_predictions
    )
    claims.extend(
        ScopedClaim(
            claim_id=f"physchem.observation:{item.observation_id}",
            claim_key=f"physicochemical.observation.{item.endpoint_key}",
            claim_value=(
                f"instrumental observation: {item.value:.15g} {item.unit}; "
                f"instrument={item.instrument_id}; protocol={item.protocol_id}"
            ),
            claim_kind=ClaimKind.OBSERVATION,
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
            cardinality=ClaimCardinality.SET_MEMBER,
            member_id=item.observation_id,
        )
        for item in packet.instrumental_observations
    )

    unknowns = [
        UnknownFact(
            unknown_id=f"physchem.missing:{field_key}:{packet.packet_id}",
            field_key=f"physicochemical.{field_key}",
            reason=_BLOCKER_EVIDENCE[field_key][0],
            needed_evidence=_BLOCKER_EVIDENCE[field_key][1],
            provenance_refs=packet.provenance_refs,
        )
        for field_key in packet.blocking_fields
    ]
    unknowns.extend(
        UnknownFact(
            unknown_id=f"physchem.{field_key}:{packet.packet_id}",
            field_key=field_key,
            reason=reason,
            needed_evidence=needed,
            provenance_refs=provenance,
        )
        for field_key, reason, needed in _DOWNSTREAM_HOLDS
    )

    concentration_known = (
        packet.concentration_ppm is not None and packet.concentration_basis is not None
    )
    criteria = (
        ParetoCriterion(
            criterion_id="physicochemical_concentration_ppm",
            direction=CriterionDirection.PRESERVE,
            value=(
                CriterionValue.known(cast(float, packet.concentration_ppm))
                if concentration_known
                else CriterionValue.unknown(
                    "exact-scope ppm w/w concentration or its basis is missing"
                )
            ),
            unit="ppm w/w in concentrate",
            authority_ceiling=prediction_authority,
            provenance_refs=packet.provenance_refs,
        ),
        ParetoCriterion(
            criterion_id="physicochemical_odt_ppm",
            direction=CriterionDirection.PRESERVE,
            value=(
                CriterionValue.known(packet.odt.value_ppm)
                if packet.odt is not None
                else CriterionValue.unknown("source- and medium-bound ODT is missing")
            ),
            unit="ODT ppm normalized from declared unit",
            authority_ceiling=prediction_authority,
            provenance_refs=(packet.odt.source,)
            if packet.odt is not None
            else packet.provenance_refs,
        ),
        ParetoCriterion(
            criterion_id="physicochemical_oav",
            direction=CriterionDirection.PRESERVE,
            value=(
                CriterionValue.known(cast(float, packet.oav))
                if packet.oav is not None
                else CriterionValue.unknown(
                    "OAV remains unknown until concentration, ODT, method, and support are bound"
                )
            ),
            unit="dimensionless screening ratio, not perceived contribution",
            authority_ceiling=prediction_authority,
            provenance_refs=provenance,
        ),
    )
    support_intervals = (
        *((packet.quantitative_support,) if packet.quantitative_support is not None else ()),
        *(item.support for item in packet.headspace_predictions),
        *(item.support for item in packet.instrumental_observations),
    )
    failure_modes = (
        "matrix, activity-coefficient, temperature, or time transfer invalidates the packet",
        "an ODT source or medium is applied outside its declared scope",
        "a computational prediction is mistaken for measured headspace or observed smell",
        "OAV is mistaken for percent perceived contribution or target fit",
        "stock fraction, fraction basis, or carrier uncertainty is silently defaulted",
        "a natural mixture is treated as a monomolecular odorant",
    )
    proposed_experiments = (
        "Measure the exact sample under the declared matrix, temperature, and time protocol.",
        "Compare model predictions with protocol-matched instrumental observations.",
        "For naturals, obtain exact-lot compositional and GC-O lineage before quantitative use.",
        "Use separate blinded sensory work for smell, target fit, liking, and performance.",
    )
    return PlaneAssessment(
        assessment_id=f"physchem-assessment:{packet.packet_id}:{packet.content_sha256}",
        module_id=_MODULE_ID,
        plane_id=PlaneId.PHYSICOCHEMICAL,
        scope=packet.scope.assessment_scope,
        claims=tuple(claims),
        support_intervals=support_intervals,
        conflicts=(),
        unknowns=tuple(unknowns),
        failure_modes=failure_modes,
        proposed_experiments=proposed_experiments,
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=(packet.content_sha256,),
        native_criteria=criteria,
    )


@dataclass(frozen=True, slots=True)
class PhysicochemicalPlaneAdapter:
    """Deterministic adapter for the shared multi-plane assessment contract."""

    packet: PhysicochemicalPacket
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.EVIDENCE_LIMITED

    def __post_init__(self) -> None:
        if not isinstance(self.packet, PhysicochemicalPacket):
            raise TypeError("packet must be a PhysicochemicalPacket")
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling.minimum(
                (AuthorityCeiling(self.authority_ceiling), _PHYSICOCHEMICAL_CEILING)
            ),
        )

    def to_plane_assessment(self) -> PlaneAssessment:
        return build_physicochemical_plane_assessment(
            self.packet,
            authority_ceiling=self.authority_ceiling,
        )


__all__ = [
    "CompositeConstituent",
    "ConcentrationBasis",
    "HeadspacePrediction",
    "InstrumentalObservation",
    "MaterialKind",
    "NaturalCompositeDecomposition",
    "OAVMethod",
    "ODTKind",
    "ODTUnit",
    "OdorThresholdReference",
    "PhysicochemicalMaterialIdentity",
    "PhysicochemicalPacket",
    "PhysicochemicalPlaneAdapter",
    "PhysicochemicalScope",
    "QuantitativeState",
    "build_physicochemical_plane_assessment",
]
