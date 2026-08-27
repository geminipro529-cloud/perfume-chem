"""PCV3 schema registry framework (Wave 1A, IMP-001A).

Framework only. Zero side effects on import: no filesystem scan, no schema
registration, no ingestion/calibration/telemetry/protobuf imports, no writes.
"""

from .errors import (
    AuthorityRequiresExactBytes,
    CanonicalizerAuthorityUnresolved,
    IngestionScopeViolation,
    InvalidSha256,
    PointerIsNotSchemaBytes,
    RegistryLocked,
    SchemaByteMissing,
    SchemaHashMismatch,
    SchemaRegistryError,
    SchemaValidationFail,
    SchemaValidatorUnavailable,
    SchemaVersionConflict,
    SummaryIsNotSchemaBytes,
    UnknownMetadataValue,
)
from .manifest import RegistryManifest, declared_manifest_capability
from .registry import SchemaEntry, SchemaRegistry, assert_not_ingestion_transformer, sha256_of

__all__ = [
    "SchemaRegistry",
    "SchemaEntry",
    "RegistryManifest",
    "declared_manifest_capability",
    "assert_not_ingestion_transformer",
    "sha256_of",
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
