"""Wave 1A schema-registry framework tests (IMP-001A).

Covers the full positive/negative matrix from the Wave-1A amendment. All fixture
schemas are SYNTHETIC_TEST_FIXTURE / NON_CANONICAL / NO_PROGRAM_AUTHORITY and
live under tests/fixtures/pcv3/ (never engine/schema_registry/schemas/).
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.schema_registry import (
    SchemaRegistry,
    SchemaByteMissing,
    SchemaVersionConflict,
    SchemaValidationFail,
    SchemaValidatorUnavailable,
    SchemaHashMismatch,
    InvalidSha256,
    PointerIsNotSchemaBytes,
    SummaryIsNotSchemaBytes,
    AuthorityRequiresExactBytes,
    CanonicalizerAuthorityUnresolved,
    RegistryLocked,
    IngestionScopeViolation,
    UnknownMetadataValue,
)

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "pcv3")
FIXTURE_LABEL = ("SYNTHETIC_TEST_FIXTURE", "NON_CANONICAL", "NO_PROGRAM_AUTHORITY")


def load_fixture(name):
    p = os.path.join(FIXTURE_DIR, name)
    with open(p, "rb") as f:
        data = f.read()
    return data, hashlib.sha256(data).hexdigest()


def reg(**kw):
    r = SchemaRegistry()
    defaults = dict(
        schema_id="synthetic.a",
        version="1.0",
        schema_bytes=b"{}",
        declared_sha256=hashlib.sha256(b"{}").hexdigest(),
        source_kind="EXACT_FILE_BYTES",
        byte_closure_state="EXACT_BYTES_VERIFIED",
        authority_state="REFERENCE",
        fixture_label=FIXTURE_LABEL,
    )
    defaults.update(kw)
    return r, defaults


# ---------------- POSITIVE ----------------
def test_register_exact_bytes_with_exact_hash():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    e = r.register(**d)
    assert e.schema_id == "synthetic.a" and e.version == "1.0"
    assert e.declared_sha256 == h and len(e.schema_bytes) == len(data)


def test_retrieve_by_id_and_version():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    e = r.get("synthetic.a", "1.0")
    assert e is not None and e.declared_sha256 == h


def test_preserve_metadata():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(
        schema_bytes=data,
        declared_sha256=h,
        exact_source_reference="tests/fixtures/pcv3/synthetic_fixture_a.json",
        supersession_ref=None,
        provenance_ref="pcv3-t1-fixture",
    )
    e = r.register(**d)
    assert e.source_kind == "EXACT_FILE_BYTES" and e.byte_closure_state == "EXACT_BYTES_VERIFIED"
    assert e.authority_state == "REFERENCE" and e.provenance_ref == "pcv3-t1-fixture"
    assert e.fixture_label == FIXTURE_LABEL


def test_retrieve_immutable_data():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    e = r.register(**d)
    # frozen dataclass + bytes => immutable; mutation attempt must fail
    with pytest.raises(Exception):
        e.schema_bytes = b"x"  # type: ignore[misc]


def test_lock_entry_then_mutation_impossible():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    locked = r.lock("synthetic.a", "1.0")
    assert locked.locked is True
    # re-register same id/version with different bytes => version conflict (not silent mutation)
    with pytest.raises(SchemaVersionConflict):
        r.register(
            **{
                **d,
                "schema_bytes": b'{"other": 1}',
                "declared_sha256": hashlib.sha256(b'{"other": 1}').hexdigest(),
            }
        )


def test_reproduce_exact_individual_file_sha256():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, _ = reg()
    assert r.verify_file_sha256(data, h) is True
    assert r.verify_file_sha256(data + b"x", h) is False


def test_idempotent_reregistration():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    e1 = r.register(**d)
    e2 = r.register(**d)
    assert e1 is e2


def test_same_id_different_version_allowed():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    e2 = r.register(
        **{
            **d,
            "version": "2.0",
            "schema_bytes": data + b"\n",
            "declared_sha256": hashlib.sha256(data + b"\n").hexdigest(),
        }
    )
    assert e2.version == "2.0"
    assert r.get("synthetic.a", "1.0") is not None and r.get("synthetic.a", "2.0") is not None


def test_zero_side_effect_import():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys; sys.path.insert(0, %r); "
        "import engine.schema_registry as m; "
        "print('ok', hasattr(m, 'SchemaRegistry'))" % repo_root
    )
    env = dict(os.environ)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "ok True" in r.stdout


# ---------------- NEGATIVE ----------------
def test_missing_schema_bytes():
    r, d = reg(schema_bytes=None)
    with pytest.raises(SchemaByteMissing):
        r.register(**d)


def test_invalid_sha256_syntax():
    r, d = reg(declared_sha256="not-a-sha")
    with pytest.raises(InvalidSha256):
        r.register(**d)


def test_declared_hash_mismatch():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=hashlib.sha256(b"other").hexdigest())
    with pytest.raises(SchemaHashMismatch):
        r.register(**d)


def test_same_id_version_different_hash():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    with pytest.raises(SchemaVersionConflict):
        r.register(
            **{
                **d,
                "schema_bytes": data + b" ",
                "declared_sha256": hashlib.sha256(data + b" ").hexdigest(),
            }
        )


def test_mutation_after_lock_via_direct_store():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    r.lock("synthetic.a", "1.0")
    with pytest.raises(SchemaVersionConflict):
        r.register(
            **{
                **d,
                "schema_bytes": b'{"tampered": true}',
                "declared_sha256": hashlib.sha256(b'{"tampered": true}').hexdigest(),
            }
        )


def test_pointer_supplied_as_bytes():
    r, d = reg(source_kind="FILE_LIBRARY_POINTER")
    with pytest.raises(PointerIsNotSchemaBytes):
        r.register(**d)


def test_pointer_closure_state():
    r, d = reg(byte_closure_state="POINTER_RECORD_ONLY")
    with pytest.raises(PointerIsNotSchemaBytes):
        r.register(**d)


def test_summary_supplied_as_bytes():
    r, d = reg(source_kind="SUMMARY")
    with pytest.raises(SummaryIsNotSchemaBytes):
        r.register(**d)


def test_summary_closure_state():
    r, d = reg(byte_closure_state="SUMMARY_ONLY")
    with pytest.raises(SummaryIsNotSchemaBytes):
        r.register(**d)


def test_unverified_bytes_claiming_current_canonical():
    r, d = reg(authority_state="CURRENT_CANONICAL", byte_closure_state="MISSING")
    with pytest.raises(AuthorityRequiresExactBytes):
        r.register(**d)


def test_hash_mismatch_byte_state():
    r, d = reg(byte_closure_state="HASH_MISMATCH")
    with pytest.raises(SchemaHashMismatch):
        r.register(**d)


def test_unknown_source_kind():
    r, d = reg(source_kind="UNKNOWN_KIND")
    with pytest.raises(UnknownMetadataValue):
        r.register(**d)


def test_unknown_byte_closure_state():
    r, d = reg(byte_closure_state="UNKNOWN_STATE")
    with pytest.raises(UnknownMetadataValue):
        r.register(**d)


def test_aggregate_registry_hash_abstention():
    r, _ = reg()
    with pytest.raises(CanonicalizerAuthorityUnresolved):
        r.aggregate_registry_hash()


def test_validator_unavailable():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)
    with pytest.raises(SchemaValidatorUnavailable):
        r.validate("synthetic.a", "1.0", validator=None)


def test_malformed_json_validation_fail():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=b"{not-json", declared_sha256=h)
    with pytest.raises(SchemaHashMismatch):
        r.register(**d)
    # valid hash but malformed JSON bytes
    malformed = b"{not-json"
    r2, d2 = reg(schema_bytes=malformed, declared_sha256=hashlib.sha256(malformed).hexdigest())
    e = r2.register(**d2)

    def validator(obj):
        pass

    with pytest.raises(SchemaValidationFail):
        r2.validate("synthetic.a", "1.0", validator=validator)


def test_structurally_invalid_schema_when_validator_exists():
    data, h = load_fixture("synthetic_fixture_a.json")
    r, d = reg(schema_bytes=data, declared_sha256=h)
    r.register(**d)

    def strict_validator(obj):
        if obj.get("type") != "object":
            raise SchemaValidationFail("type must be object")

    bad = json.dumps({"type": "string", "properties": {}}).encode()
    r2, d2 = reg(schema_bytes=bad, declared_sha256=hashlib.sha256(bad).hexdigest())
    r2.register(**d2)
    with pytest.raises(SchemaValidationFail):
        r2.validate("synthetic.a", "1.0", validator=strict_validator)


def test_ingestion_transform_capability_violation():
    r, _ = reg()
    cap = r.manifest_capability()
    assert "ingestion behavior" in cap.does_not_own
    from engine.schema_registry import assert_not_ingestion_transformer

    with pytest.raises(IngestionScopeViolation):
        assert_not_ingestion_transformer()
