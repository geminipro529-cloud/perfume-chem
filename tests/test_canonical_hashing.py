from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest

from engine.calibration.hashing import (
    CANONICAL_HASH_ALGORITHM,
    canonical_hash_record,
    canonical_json_bytes,
)


class Kind(str, Enum):
    TARGET = "target"


def test_canonical_hash_has_reviewed_cross_platform_golden_bytes():
    payload = {
        "schema_version": "target-v1",
        "identity": UUID("01234567-89ab-cdef-0123-456789abcdef"),
        "kind": Kind.TARGET,
        "exact": Decimal("0.100000000000000001"),
        "observed_on": date(2026, 7, 30),
        "generated_at": datetime(
            2026,
            7,
            30,
            7,
            0,
            tzinfo=timezone.utc,
        ),
        "ordered_line_ids": ("line-1", "line-2"),
        "source_digests": {"b" * 64, "a" * 64},
    }
    expected = (
        b'{"exact":{"@type":"decimal","value":"0.100000000000000001"},'
        b'"generated_at":{"@type":"datetime","value":"2026-07-30T07:00:00Z"},'
        b'"identity":{"@type":"uuid","value":"01234567-89ab-cdef-0123-456789abcdef"},'
        b'"kind":"target","observed_on":{"@type":"date","value":"2026-07-30"},'
        b'"ordered_line_ids":["line-1","line-2"],"schema_version":"target-v1",'
        b'"source_digests":["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        b'"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]}'
    )
    assert canonical_json_bytes(payload) == expected

    record = canonical_hash_record(
        payload,
        schema_version="target-v1",
        stable_identity_ids=("01234567-89ab-cdef-0123-456789abcdef",),
        canonical_units={"mass": "g", "volume": "uL"},
        ordered_line_ids=("line-1", "line-2"),
        parent_hash=None,
        source_digests=("a" * 64, "b" * 64),
        transformation_version="target-transform-v1",
    )
    assert record.algorithm == CANONICAL_HASH_ALGORITHM
    assert len(record.digest_sha256) == 64
    assert record.canonical_payload_sha256 != record.digest_sha256
    assert record.canonical_units == {"mass": "g", "volume": "uL"}
    assert record.ordered_line_ids == ("line-1", "line-2")


def test_canonical_hash_rejects_naive_time_nonfinite_float_and_paths():
    with pytest.raises(ValueError, match="timezone-aware"):
        canonical_json_bytes({"when": datetime(2026, 7, 30, 7, 0)})
    with pytest.raises(ValueError, match="NaN or Infinity"):
        canonical_json_bytes({"value": float("nan")})
    with pytest.raises(TypeError, match="filesystem paths"):
        canonical_json_bytes({"path": Path("unstable/local/path")})
