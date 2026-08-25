from __future__ import annotations

import hashlib

import pytest

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
    canonical_json_bytes,
    sha256_hex,
)


def _source() -> EvidenceSourceRef:
    return EvidenceSourceRef(
        source_id="doi:10.1000/example",
        source_uri="https://doi.org/10.1000/example",
        retrieved_on="2026-08-26",
        source_sha256="a" * 64,
    )


def test_quantitative_evidence_requires_explicit_units_context_and_source() -> None:
    with pytest.raises(ValueError, match="unit"):
        QuantitativeEvidence(
            value=1.2,
            unit="",
            context="air threshold",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=_source(),
        )
    with pytest.raises(ValueError, match="context"):
        QuantitativeEvidence(
            value=1.2,
            unit="ppm",
            context="",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=_source(),
        )
    with pytest.raises(ValueError, match="method"):
        QuantitativeEvidence(
            value=1.2,
            unit="ppm",
            context="air threshold",
            method="",
            basis=EvidenceBasis.MEASURED,
            source=_source(),
        )
    with pytest.raises(ValueError, match="source"):
        QuantitativeEvidence(
            value=1.2,
            unit="ppm",
            context="air threshold",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=None,
        )


def test_unknown_evidence_cannot_smuggle_a_value_or_neutral_default() -> None:
    unknown = QuantitativeEvidence(
        value=None,
        unit="",
        context="",
        method="",
        basis=EvidenceBasis.UNKNOWN,
        source=None,
    )
    assert unknown.as_dict() == {
        "value": None,
        "unit": "",
        "context": "",
        "method": "",
        "basis": "UNKNOWN",
        "source": None,
        "uncertainty": None,
    }
    with pytest.raises(ValueError, match="UNKNOWN evidence requires value=None"):
        QuantitativeEvidence(
            value=0.0,
            unit="ppm",
            context="air threshold",
            method="unknown",
            basis=EvidenceBasis.UNKNOWN,
            source=None,
        )


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
def test_known_evidence_rejects_boolean_and_nonfinite_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="value"):
        QuantitativeEvidence(
            value=value,  # type: ignore[arg-type]
            unit="ppm",
            context="air threshold",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=_source(),
        )


@pytest.mark.parametrize("uncertainty", [True, -0.1, float("nan"), float("inf")])
def test_uncertainty_must_be_finite_nonnegative_and_not_boolean(
    uncertainty: object,
) -> None:
    with pytest.raises((TypeError, ValueError), match="uncertainty"):
        QuantitativeEvidence(
            value=1.2,
            unit="ppm",
            context="air threshold",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=_source(),
            uncertainty=uncertainty,  # type: ignore[arg-type]
        )


def test_source_reference_requires_iso_date_and_valid_optional_sha256() -> None:
    with pytest.raises(ValueError, match="retrieved_on"):
        EvidenceSourceRef(
            source_id="paper",
            source_uri="https://example.test/paper",
            retrieved_on="26/08/2026",
            source_sha256="a" * 64,
        )
    with pytest.raises(ValueError, match="source_sha256"):
        EvidenceSourceRef(
            source_id="paper",
            source_uri="https://example.test/paper",
            retrieved_on="2026-08-26",
            source_sha256="not-a-digest",
        )
    source = EvidenceSourceRef(
        source_id="paper",
        source_uri="https://example.test/paper",
        retrieved_on="2026-08-26",
        source_sha256=None,
    )
    assert source.as_dict()["source_sha256"] is None


def test_canonical_bytes_are_order_independent_and_hash_stable() -> None:
    left = canonical_json_bytes({"b": 2, "a": 1})
    right = canonical_json_bytes({"a": 1, "b": 2})
    assert left == right == b'{"a":1,"b":2}'
    assert sha256_hex(left) == hashlib.sha256(left).hexdigest()


def test_canonical_bytes_normalize_enums_and_tuples_without_nan() -> None:
    assert canonical_json_bytes(
        {"basis": EvidenceBasis.MODELED, "values": (2, 1)}
    ) == b'{"basis":"MODELED","values":[2,1]}'
    with pytest.raises(ValueError, match="JSON"):
        canonical_json_bytes({"value": float("nan")})


def test_sha256_hex_accepts_bytes_only() -> None:
    with pytest.raises(TypeError, match="bytes"):
        sha256_hex("not bytes")  # type: ignore[arg-type]
