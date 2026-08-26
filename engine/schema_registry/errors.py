"""Typed errors for the PCV3 schema registry framework (Wave 1A, IMP-001A).

Every registry failure is a typed exception carrying a stable machine code.
ID_COLLISION is deliberately NOT implemented in Wave 1A (deferred).
"""

from __future__ import annotations


class SchemaRegistryError(Exception):
    """Base class for all schema-registry errors."""

    code = "SCHEMA_REGISTRY_ERROR"

    def __init__(self, message: str, *, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class SchemaByteMissing(SchemaRegistryError):
    code = "SCHEMA_BYTE_MISSING"


class SchemaVersionConflict(SchemaRegistryError):
    code = "SCHEMA_VERSION_CONFLICT"


class SchemaValidationFail(SchemaRegistryError):
    code = "SCHEMA_VALIDATION_FAIL"


class SchemaValidatorUnavailable(SchemaRegistryError):
    code = "SCHEMA_VALIDATOR_UNAVAILABLE"


class SchemaHashMismatch(SchemaRegistryError):
    code = "SCHEMA_HASH_MISMATCH"


class InvalidSha256(SchemaRegistryError):
    code = "INVALID_SHA256"


class PointerIsNotSchemaBytes(SchemaRegistryError):
    code = "POINTER_IS_NOT_SCHEMA_BYTES"


class SummaryIsNotSchemaBytes(SchemaRegistryError):
    code = "SUMMARY_IS_NOT_SCHEMA_BYTES"


class AuthorityRequiresExactBytes(SchemaRegistryError):
    code = "AUTHORITY_REQUIRES_EXACT_BYTES"


class CanonicalizerAuthorityUnresolved(SchemaRegistryError):
    code = "CANONICALIZER_AUTHORITY_UNRESOLVED"


class RegistryLocked(SchemaRegistryError):
    code = "REGISTRY_LOCKED"


class IngestionScopeViolation(SchemaRegistryError):
    code = "INGESTION_SCOPE_VIOLATION"


class UnknownMetadataValue(ValueError):
    """Fail-closed error for unknown source_kind / byte_closure_state values.

    Deliberately outside the required Wave-1A failure-code list: unknown values
    are rejected, never coerced into exact-byte states.
    """

    pass


__all__ = [
    "SchemaRegistryError",
    "SchemaByteMissing",
    "SchemaVersionConflict",
    "SchemaValidationFail",
    "SchemaValidatorUnavailable",
    "SchemaHashMismatch",
    "InvalidSha256",
    "PointerIsNotSchemaBytes",
    "SummaryIsNotSchemaBytes",
    "AuthorityRequiresExactBytes",
    "CanonicalizerAuthorityUnresolved",
    "RegistryLocked",
    "IngestionScopeViolation",
    "UnknownMetadataValue",
]
