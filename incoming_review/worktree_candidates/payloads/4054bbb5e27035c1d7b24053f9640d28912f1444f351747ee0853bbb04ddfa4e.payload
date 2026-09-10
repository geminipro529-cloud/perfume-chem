"""Operation-scoped source-use firewall.

Hash verification establishes byte identity. It does not establish source
rights or authorize importing, executing, or promoting the content.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceRights(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    PROHIBITED = "PROHIBITED"


class SourceOperation(str, Enum):
    VERIFY_BYTES = "VERIFY_BYTES"
    READ_MANIFEST_FOR_QUARANTINE = "READ_MANIFEST_FOR_QUARANTINE"
    IMPORT_MODULE = "IMPORT_MODULE"
    IMPORT_SCHEMA = "IMPORT_SCHEMA"
    IMPORT_REGISTRY = "IMPORT_REGISTRY"
    IMPORT_FORMULA = "IMPORT_FORMULA"
    IMPORT_EVIDENCE_LEDGER = "IMPORT_EVIDENCE_LEDGER"
    EXECUTE = "EXECUTE"
    PROMOTE = "PROMOTE"


@dataclass(frozen=True)
class SourceUseRequest:
    source_id: str
    rights: SourceRights
    operation: SourceOperation
    exact_bytes_present: bool
    hash_verified: bool
    quarantine_manifest_read_allowed: bool = True
    operation_explicitly_approved: bool = False


@dataclass(frozen=True)
class SourceUseDecision:
    allowed: bool
    state: str
    reason: str
    authority_promoted: bool = False


def decide_source_use(request: SourceUseRequest) -> SourceUseDecision:
    if not request.source_id.strip():
        return SourceUseDecision(False, "DENY", "source ID is required")

    if request.rights is SourceRights.PROHIBITED:
        return SourceUseDecision(False, "DENY_RIGHTS_PROHIBITED", "source use is prohibited")

    if request.operation is SourceOperation.VERIFY_BYTES:
        if not request.exact_bytes_present:
            return SourceUseDecision(False, "HOLD_SOURCE_BYTES", "exact bytes are not present")
        return SourceUseDecision(
            True,
            "ALLOW_VERIFY_BYTES_ONLY",
            "byte verification is allowed without scientific or installation promotion",
        )

    if request.operation is SourceOperation.READ_MANIFEST_FOR_QUARANTINE:
        if not request.exact_bytes_present:
            return SourceUseDecision(False, "HOLD_SOURCE_BYTES", "exact bytes are not present")
        if not request.quarantine_manifest_read_allowed:
            return SourceUseDecision(False, "DENY_MANIFEST_READ", "policy forbids manifest inspection")
        return SourceUseDecision(
            True,
            "ALLOW_QUARANTINE_MANIFEST_READ_ONLY",
            "manifest inspection does not admit package contents",
        )

    if request.rights is SourceRights.UNRESOLVED:
        return SourceUseDecision(
            False,
            "DENY_UNRESOLVED_SOURCE_RIGHTS",
            "unresolved source rights deny import, execution, and promotion even when SHA-256 matches",
        )

    if not request.hash_verified:
        return SourceUseDecision(
            False,
            "HOLD_HASH_UNVERIFIED",
            "resolved rights do not bypass exact-byte verification",
        )

    if not request.operation_explicitly_approved:
        return SourceUseDecision(
            False,
            "DENY_OPERATION_NOT_APPROVED",
            "source admission is operation-scoped and requires explicit approval",
        )

    return SourceUseDecision(
        True,
        "ALLOW_SCOPED_OPERATION",
        "operation is approved for resolved, exact, hash-verified source bytes",
        authority_promoted=False,
    )
