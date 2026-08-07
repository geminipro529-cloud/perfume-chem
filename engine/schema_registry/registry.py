"""Versioned schema-registry framework (Wave 1A, IMP-001A).

Framework only: registration, lookup, per-entry immutable locking, exact
individual-file SHA-256 verification, source-kind / byte-closure enforcement,
and validation only when exact bytes + an existing validator are available.

Deliberately does NOT implement:
- canonical schema population;
- aggregate canonical registry hashing (CANONICALIZER_AUTHORITY_UNRESOLVED);
- ID_COLLISION (deferred);
- ingestion transformation (INGESTION_SCOPE_VIOLATION via manifest);
- any dependency on engine.ingestion or the existing canonical-JSON roots.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .errors import (
    AuthorityRequiresExactBytes,
    CanonicalizerAuthorityUnresolved,
    InvalidSha256,
    PointerIsNotSchemaBytes,
    RegistryLocked,
    SchemaByteMissing,
    SchemaHashMismatch,
    SchemaValidationFail,
    SchemaValidatorUnavailable,
    SchemaVersionConflict,
    SummaryIsNotSchemaBytes,
    UnknownMetadataValue,
)
from .manifest import RegistryManifest, declared_manifest_capability

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Allowed metadata vocabularies (fail closed on unknown values)
SOURCE_KINDS = frozenset(
    {"EXACT_FILE_BYTES", "FILE_LIBRARY_POINTER", "SUMMARY", "SYNTHETIC_TEST_FIXTURE"}
)
BYTE_CLOSURE_STATES = frozenset(
    {"EXACT_BYTES_VERIFIED", "POINTER_RECORD_ONLY", "SUMMARY_ONLY", "MISSING", "HASH_MISMATCH"}
)
AUTHORITY_STATES = frozenset({"REFERENCE", "CURRENT_CANONICAL", "ADVISORY", "HOLD"})


@dataclass(frozen=True, slots=True)
class SchemaEntry:
    """Immutable per-entry registry record. No mutable internal references."""

    schema_id: str
    version: str
    schema_bytes: bytes
    declared_sha256: str
    exact_source_reference: str | None
    source_kind: str
    byte_closure_state: str
    authority_state: str
    supersession_ref: str | None
    provenance_ref: str | None
    locked: bool = False
    fixture_label: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "version": self.version,
            "sha256": self.declared_sha256,
            "byte_size": len(self.schema_bytes),
            "exact_source_reference": self.exact_source_reference,
            "source_kind": self.source_kind,
            "byte_closure_state": self.byte_closure_state,
            "authority_state": self.authority_state,
            "supersession_ref": self.supersession_ref,
            "provenance_ref": self.provenance_ref,
            "locked": self.locked,
            "fixture_label": list(self.fixture_label),
        }


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_sha(declared: str) -> None:
    if not isinstance(declared, str) or not _SHA256_RE.match(declared):
        raise InvalidSha256(f"declared SHA-256 is not a 64-hex digest: {declared!r}")


class SchemaRegistry:
    """Framework registry. Collision behavior and enforcement per the amendment."""

    def __init__(self) -> None:
        # keyed by (schema_id, version) -> immutable SchemaEntry
        self._entries: dict[tuple[str, str], SchemaEntry] = {}

    # -- capability / scope -----------------------------------------------
    def manifest_capability(self) -> RegistryManifest:
        return declared_manifest_capability()

    # -- registration ------------------------------------------------------
    def register(
        self,
        *,
        schema_id: str,
        version: str,
        schema_bytes: bytes | None,
        declared_sha256: str,
        source_kind: str,
        byte_closure_state: str,
        authority_state: str = "REFERENCE",
        exact_source_reference: str | None = None,
        supersession_ref: str | None = None,
        provenance_ref: str | None = None,
        fixture_label: tuple[str, ...] = (),
    ) -> SchemaEntry:
        if schema_bytes is None or not isinstance(schema_bytes, bytes) or len(schema_bytes) == 0:
            raise SchemaByteMissing("schema_bytes are required and must be non-empty")
        if source_kind not in SOURCE_KINDS:
            raise UnknownMetadataValue(f"unknown source_kind: {source_kind!r}")
        if byte_closure_state not in BYTE_CLOSURE_STATES:
            raise UnknownMetadataValue(f"unknown byte_closure_state: {byte_closure_state!r}")
        if authority_state not in AUTHORITY_STATES:
            raise UnknownMetadataValue(f"unknown authority_state: {authority_state!r}")

        _validate_sha(declared_sha256)

        # source-kind / byte-closure enforcement (metadata, not filename guessing)
        if source_kind == "FILE_LIBRARY_POINTER" or byte_closure_state == "POINTER_RECORD_ONLY":
            raise PointerIsNotSchemaBytes("pointer records are provenance, not schema bytes")
        if source_kind == "SUMMARY" or byte_closure_state == "SUMMARY_ONLY":
            raise SummaryIsNotSchemaBytes("summaries are not schema bytes")
        if byte_closure_state == "HASH_MISMATCH":
            raise SchemaHashMismatch("byte_closure_state declares HASH_MISMATCH")
        if authority_state == "CURRENT_CANONICAL" and byte_closure_state != "EXACT_BYTES_VERIFIED":
            raise AuthorityRequiresExactBytes(
                "CURRENT_CANONICAL authority requires verified exact bytes"
            )

        actual = sha256_of(schema_bytes)
        if actual != declared_sha256:
            raise SchemaHashMismatch(
                f"declared hash {declared_sha256} does not match supplied bytes ({actual})"
            )

        key = (schema_id, version)
        existing = self._entries.get(key)
        if existing is not None:
            if existing.declared_sha256 == declared_sha256:
                return existing  # IDEMPOTENT_SUCCESS
            raise SchemaVersionConflict(
                f"same schema_id + version but different hash: {schema_id} v{version}"
            )

        entry = SchemaEntry(
            schema_id=schema_id,
            version=version,
            schema_bytes=schema_bytes,
            declared_sha256=declared_sha256,
            exact_source_reference=exact_source_reference,
            source_kind=source_kind,
            byte_closure_state=byte_closure_state,
            authority_state=authority_state,
            supersession_ref=supersession_ref,
            provenance_ref=provenance_ref,
            locked=False,
            fixture_label=tuple(fixture_label),
        )
        self._entries[key] = entry
        return entry

    # -- lookup ------------------------------------------------------------
    def get(self, schema_id: str, version: str | None = None) -> SchemaEntry | None:
        """Return an immutable entry view. Never exposes mutable internal state."""
        if version is not None:
            return self._entries.get((schema_id, version))
        best = None
        best_key = None
        for (sid, ver), entry in self._entries.items():
            if sid == schema_id:
                key = self._version_key(ver)
                if best_key is None or key > best_key:
                    best = entry
                    best_key = key
        return best

    @staticmethod
    def _version_key(version: str) -> tuple[int, ...]:
        """Numeric version key (e.g. '10.0' > '2.0'). Falls back to a sentinel-safe tuple."""
        parts = version.split(".")
        out = []
        for p in parts:
            try:
                out.append(int(p))
            except ValueError:
                out.append(0)
        return tuple(out)

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    # -- locking (immutable per-entry) -------------------------------------
    def lock(self, schema_id: str, version: str) -> SchemaEntry:
        key = (schema_id, version)
        entry = self._entries.get(key)
        if entry is None:
            raise SchemaByteMissing(f"no entry for {schema_id} v{version}")
        if entry.locked:
            return entry
        locked = SchemaEntry(
            schema_id=entry.schema_id,
            version=entry.version,
            schema_bytes=entry.schema_bytes,
            declared_sha256=entry.declared_sha256,
            exact_source_reference=entry.exact_source_reference,
            source_kind=entry.source_kind,
            byte_closure_state=entry.byte_closure_state,
            authority_state=entry.authority_state,
            supersession_ref=entry.supersession_ref,
            provenance_ref=entry.provenance_ref,
            locked=True,
            fixture_label=entry.fixture_label,
        )
        self._entries[key] = locked
        return locked

    # -- exact individual-file hash (allowed) ------------------------------
    @staticmethod
    def verify_file_sha256(data: bytes, declared: str) -> bool:
        _validate_sha(declared)
        return sha256_of(data) == declared

    # -- aggregate hash abstention (NOT implemented in Wave 1A) ------------
    def aggregate_registry_hash(self) -> str:
        raise CanonicalizerAuthorityUnresolved(
            "canonical aggregate registry hash is unavailable until IMP-004 resolves "
            "canonicalization authority (two canonical-JSON roots exist; Wave 1A must not create a third)"
        )

    # -- validation (only when exact bytes + existing validator) -----------
    def validate(
        self,
        schema_id: str,
        version: str,
        validator: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        entry = self.get(schema_id, version)
        if entry is None:
            raise SchemaByteMissing(f"no entry for {schema_id} v{version}")
        if validator is None:
            raise SchemaValidatorUnavailable(
                "no existing JSON Schema validator is available; validation not performed"
            )
        try:
            parsed = json.loads(entry.schema_bytes.decode("utf-8"))
        except Exception as exc:
            raise SchemaValidationFail(f"malformed JSON schema bytes: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SchemaValidationFail("schema bytes must parse to a JSON object")
        try:
            validator(parsed)
        except SchemaValidationFail:
            raise
        except Exception as exc:
            raise SchemaValidationFail(f"structural schema validation failed: {exc}") from exc


def assert_not_ingestion_transformer() -> None:
    """Manifest-scope guard: registry is not an ingestion transformer."""
    from .errors import IngestionScopeViolation

    raise IngestionScopeViolation(
        "schema_registry declares schema identity/version/byte-state scope only; "
        "candidate interchange and ingestion behavior belong to engine.ingestion"
    )


__all__ = ["SchemaRegistry", "SchemaEntry", "sha256_of", "assert_not_ingestion_transformer"]
