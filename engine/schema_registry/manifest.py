"""Manifest capability declaration for the PCV3 schema registry (Wave 1A).

Declares the registry's scope boundary explicitly. Used to enforce that the
registry is NOT an ingestion transformer (INGESTION_SCOPE_VIOLATION).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import IngestionScopeViolation


@dataclass(frozen=True, slots=True)
class RegistryManifest:
    """Immutable declaration of the registry's scope."""

    module: str = "engine.schema_registry"
    version: str = "0.1.0-wave1a"
    owns: tuple[str, ...] = (
        "schema identity",
        "schema version",
        "exact source-byte reference",
        "exact SHA-256 reference",
        "byte-closure state",
        "authority state",
        "supersession state",
        "provenance reference",
        "registration",
        "lookup",
        "locking",
        "validation when exact bytes + validator available",
    )
    does_not_own: tuple[str, ...] = (
        "candidate interchange",
        "ingestion behavior",
        "inventory parsing/transformation",
        "canonical aggregate serialization",
        "canonical aggregate registry hash",
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "version": self.version,
            "owns": list(self.owns),
            "does_not_own": list(self.does_not_own),
        }


def declared_manifest_capability() -> RegistryManifest:
    """Return the declared manifest capability (immutable)."""
    return RegistryManifest()


def assert_no_ingestion_transformer_use() -> None:
    """Fail closed when the registry is asked to behave as an ingestion transformer."""
    raise IngestionScopeViolation(
        "engine.schema_registry declares schema identity/version/byte-state scope only; "
        "candidate interchange and ingestion behavior belong to engine.ingestion"
    )


__all__ = [
    "RegistryManifest",
    "declared_manifest_capability",
    "assert_no_ingestion_transformer_use",
]
