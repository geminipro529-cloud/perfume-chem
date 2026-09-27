import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest

import engine.calibration.hashing as hashing
from engine.calibration.hashing import (
    CANONICAL_HASH_ALGORITHM,
    PORTABLE_ARTIFACT_HASH_ALGORITHM,
    PORTABLE_FILE_HASH_MATCH_ALGORITHM,
    UTF8_TEXT_FILE_HASH_ALGORITHM,
    canonical_hash_record,
    canonical_json_bytes,
    portable_file_hash_matches,
    stable_file_hash,
    stable_files_hash,
    stable_json_hash,
    stable_portable_file_hash,
    stable_utf8_text_file_hash,
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


def test_stable_files_hash_matches_content_manifest_and_missing_sentinel(tmp_path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_bytes(b"first\r\n")
    second.write_bytes(b"second")
    assert stable_file_hash(first) == hashlib.sha256(b"first\r\n").hexdigest()
    expected_manifest = [
        {"path": "a.txt", "sha256": stable_file_hash(first)},
        {"path": "b.txt", "sha256": stable_file_hash(second)},
        {"path": "missing.txt", "sha256": "MISSING"},
    ]

    assert stable_files_hash(("missing.txt", "b.txt", "a.txt"), root=tmp_path) == (
        stable_json_hash(expected_manifest)
    )

    first.write_bytes(b"updated")
    assert stable_files_hash(("missing.txt", "b.txt", "a.txt"), root=tmp_path) != (
        stable_json_hash(expected_manifest)
    )


def test_stable_files_hash_propagates_first_sorted_content_error(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "b.txt").write_bytes(b"b")

    def fail(path):
        raise OSError(f"cannot read {Path(path).name}")

    monkeypatch.setattr(hashing, "stable_file_hash", fail)
    with pytest.raises(OSError, match="cannot read a.txt"):
        hashing.stable_files_hash(("b.txt", "a.txt"), root=tmp_path)


def test_portable_file_hash_matches_only_text_line_ending_variants(tmp_path):
    assert PORTABLE_FILE_HASH_MATCH_ALGORITHM == (
        "sha256-exact-or-utf8-text-eol-equivalent-v1"
    )
    lf_text = tmp_path / "record.json"
    crlf_text = tmp_path / "record-copy.json"
    changed_text = tmp_path / "changed.json"
    bare_cr_text = tmp_path / "bare-cr.json"
    invalid_utf8_text = tmp_path / "invalid.json"
    binary = tmp_path / "record.pdf"
    lf_payload = b'{"state":"HOLD"}\n'
    crlf_payload = b'{"state":"HOLD"}\r\n'
    lf_text.write_bytes(lf_payload)
    crlf_text.write_bytes(crlf_payload)
    changed_text.write_bytes(b'{"state":"PASS"}\n')
    bare_cr_text.write_bytes(b'{"state":"HOLD"}\r')
    invalid_utf8_text.write_bytes(b'{"state":"HOLD"}\xff\n')
    binary.write_bytes(crlf_payload)

    expected_lf = hashlib.sha256(lf_payload).hexdigest()
    expected_crlf = hashlib.sha256(crlf_payload).hexdigest()
    assert portable_file_hash_matches(lf_text, expected_lf)
    assert portable_file_hash_matches(lf_text, expected_crlf)
    assert portable_file_hash_matches(crlf_text, expected_lf)
    assert not portable_file_hash_matches(changed_text, expected_lf)
    assert not portable_file_hash_matches(bare_cr_text, expected_lf)
    assert not portable_file_hash_matches(invalid_utf8_text, expected_lf)
    assert not portable_file_hash_matches(binary, expected_lf)


def test_stable_utf8_text_file_hash_is_checkout_portable_and_fail_closed(tmp_path):
    assert UTF8_TEXT_FILE_HASH_ALGORITHM == "sha256-utf8-lf-normalized-v1"
    lf_text = tmp_path / "lf.yaml"
    crlf_text = tmp_path / "crlf.yaml"
    bare_cr_text = tmp_path / "bare-cr.yaml"
    invalid_utf8_text = tmp_path / "invalid.yaml"
    lf_text.write_bytes(b"- canonical_name: Lavender\n")
    crlf_text.write_bytes(b"- canonical_name: Lavender\r\n")
    bare_cr_text.write_bytes(b"- canonical_name: Lavender\r")
    invalid_utf8_text.write_bytes(b"- canonical_name: \xff\n")

    expected = hashlib.sha256(lf_text.read_bytes()).hexdigest()
    assert stable_utf8_text_file_hash(lf_text) == expected
    assert stable_utf8_text_file_hash(crlf_text) == expected
    with pytest.raises(ValueError, match="bare carriage return"):
        stable_utf8_text_file_hash(bare_cr_text)
    with pytest.raises(ValueError, match="valid UTF-8"):
        stable_utf8_text_file_hash(invalid_utf8_text)


def test_stable_portable_file_hash_normalizes_text_but_not_binary(tmp_path):
    assert PORTABLE_ARTIFACT_HASH_ALGORITHM == (
        "sha256-binary-exact-or-utf8-lf-normalized-v1"
    )
    text_path = tmp_path / "protocol.json"
    binary_path = tmp_path / "source.pdf"
    text_path.write_bytes(b'{"state":"HOLD"}\r\n')
    binary_path.write_bytes(b"PDF\r\n")

    assert stable_portable_file_hash(text_path) == hashlib.sha256(
        b'{"state":"HOLD"}\n'
    ).hexdigest()
    assert stable_portable_file_hash(binary_path) == hashlib.sha256(
        b"PDF\r\n"
    ).hexdigest()
