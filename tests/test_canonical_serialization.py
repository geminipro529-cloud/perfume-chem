from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

import pytest

from engine.canonical_serialization import (
    CanonicalTypeRegistry,
    deserialize_record,
    serialize_record,
)
from engine.quantities import (
    Concentration,
    ConcentrationBasis,
    Mass,
    StandardUncertainty,
)


class RecordKind(str, Enum):
    TARGET = "target"
    BUILD = "build"


@dataclass(frozen=True, slots=True)
class NestedRecord:
    identity: UUID
    kind: RecordKind
    observed_on: date
    generated_at: datetime
    exact_amount: Decimal
    labels: tuple[str, ...]
    evidence_ids: frozenset[str]
    mass: Mass
    concentration: Concentration
    uncertainty: StandardUncertainty


def _registry() -> CanonicalTypeRegistry:
    registry = CanonicalTypeRegistry()
    registry.register_enum("record-kind", RecordKind)
    registry.register_record("nested-record", NestedRecord)
    registry.register_record("mass", Mass)
    registry.register_record("concentration", Concentration)
    registry.register_record("standard-uncertainty", StandardUncertainty)
    registry.register_enum("concentration-basis", ConcentrationBasis)
    return registry


def test_nested_runtime_types_round_trip_through_one_registered_boundary():
    record = NestedRecord(
        identity=UUID("01234567-89ab-cdef-0123-456789abcdef"),
        kind=RecordKind.TARGET,
        observed_on=date(2026, 7, 30),
        generated_at=datetime(2026, 7, 30, 6, 0, tzinfo=timezone.utc),
        exact_amount=Decimal("0.100000000000000001"),
        labels=("heart", "diffusion"),
        evidence_ids=frozenset({"evidence-b", "evidence-a"}),
        mass=Mass.from_g(1.25),
        concentration=Concentration(
            0.1,
            ConcentrationBasis.MASS_FRACTION,
            "stock solution",
        ),
        uncertainty=StandardUncertainty(1.25, 0.01, "g"),
    )

    encoded = serialize_record(
        record,
        registry=_registry(),
        extensions={"org.perfumechem.audit": {"reviewed": False}},
    )
    decoded = deserialize_record(encoded, registry=_registry())

    assert decoded.record == record
    assert isinstance(decoded.record.identity, UUID)
    assert isinstance(decoded.record.kind, RecordKind)
    assert isinstance(decoded.record.observed_on, date)
    assert isinstance(decoded.record.generated_at, datetime)
    assert decoded.record.generated_at.tzinfo is not None
    assert isinstance(decoded.record.exact_amount, Decimal)
    assert isinstance(decoded.record.labels, tuple)
    assert isinstance(decoded.record.evidence_ids, frozenset)
    assert isinstance(decoded.record.mass, Mass)
    assert isinstance(decoded.record.concentration, Concentration)
    assert isinstance(decoded.record.uncertainty, StandardUncertainty)
    assert decoded.record.uncertainty.unit == "g"
    assert decoded.extensions == {
        "org.perfumechem.audit": {"reviewed": False}
    }


def test_serialization_rejects_naive_time_unknown_record_and_future_schema():
    registry = _registry()
    with pytest.raises(ValueError, match="timezone-aware"):
        serialize_record(
            NestedRecord(
                identity=UUID(int=1),
                kind=RecordKind.BUILD,
                observed_on=date(2026, 7, 30),
                generated_at=datetime(2026, 7, 30, 6, 0),
                exact_amount=Decimal("1"),
                labels=(),
                evidence_ids=frozenset(),
                mass=Mass.from_g(1),
                concentration=Concentration(
                    1,
                    ConcentrationBasis.MASS_FRACTION,
                    "neat",
                ),
                uncertainty=StandardUncertainty(1, 0, "g"),
            ),
            registry=registry,
        )

    encoded = serialize_record(
        Mass.from_g(1),
        registry=registry,
    )
    with pytest.raises(ValueError, match="future canonical schema"):
        deserialize_record(
            encoded.replace(
                b'"canonical-envelope-v1"',
                b'"canonical-envelope-v99"',
            ),
            registry=registry,
        )

    empty_registry = CanonicalTypeRegistry()
    with pytest.raises(ValueError, match="unregistered record type"):
        deserialize_record(encoded, registry=empty_registry)


def test_extensions_require_a_documented_namespace():
    with pytest.raises(ValueError, match="extension namespace"):
        serialize_record(
            Mass.from_g(1),
            registry=_registry(),
            extensions={"unscoped": {"unsafe": True}},
        )
