"""Fail-closed receipts for external ZIP packages that are not source-admitted.

This module freezes transport identity and provenance without turning package
possession into scientific, formula, inventory, safety, or release authority.
It performs read-only ZIP verification and never extracts package members,
creates B1 candidates, or writes repository state.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile, ZipInfo

from engine.calibration.hashing import stable_file_hash, stable_json_hash

EXTERNAL_PACKAGE_RECEIPT_SCHEMA_VERSION = "external_package_receipt_v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LOCATOR_SCOPES = {"WORKSPACE_RELATIVE", "EXTERNAL_LOCAL_PATH"}
_SOURCE_TYPES = {"SECONDARY_RECONSTRUCTION", "AI_GENERATED_HYPOTHESIS"}
_REUSE_STATES = {"PERMITTED", "RESTRICTED", "UNKNOWN"}
_AUTHORITY_FIELDS = (
    "source_authority",
    "formula_authority",
    "inventory_authority",
    "oav_authority",
    "headspace_authority",
    "sensory_authority",
    "safety_authority",
    "procurement_authority",
    "compounding_authority",
    "release_authority",
)
_ADMISSION_BOOLEAN_FIELDS = (
    "b1_promotion_allowed",
    "canonical_import_allowed",
    "repository_content_import_allowed",
    "row_projection_allowed",
)
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_ARCHIVE_MEMBER_BYTES = 512 * 1024 * 1024
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 1_000


class ExternalPackageReceiptError(ValueError):
    """Raised when a package receipt could permit loss or authority leakage."""


@dataclass(frozen=True, slots=True)
class ExternalPackageVerification:
    """Read-only verification result; promotion remains false by construction."""

    integrity_verified: bool
    status: str
    receipt_sha256: str
    package_sha256: str
    archive_entry_count: int
    archive_file_count: int
    verified_embedded_records: tuple[str, ...]
    promotion_allowed: bool
    errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "integrity_verified": self.integrity_verified,
            "status": self.status,
            "receipt_sha256": self.receipt_sha256,
            "package_sha256": self.package_sha256,
            "archive_entry_count": self.archive_entry_count,
            "archive_file_count": self.archive_file_count,
            "verified_embedded_records": list(self.verified_embedded_records),
            "promotion_allowed": self.promotion_allowed,
            "errors": list(self.errors),
        }


def _exact_keys(raw: Mapping[str, Any], expected: set[str], field: str) -> None:
    actual = set(raw)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ExternalPackageReceiptError(
            f"{field} keys differ; missing={missing}, extra={extra}"
        )


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalPackageReceiptError(f"{field} must be an object")
    return value


def _nonblank(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ExternalPackageReceiptError(f"{field} must be non-blank")
    return text


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExternalPackageReceiptError(f"{field} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ExternalPackageReceiptError(f"{field} must be >= {minimum}")
    return value


def _digest(value: Any, field: str) -> str:
    digest = str(value or "").strip()
    if not _SHA256.fullmatch(digest):
        raise ExternalPackageReceiptError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return digest


def _safe_archive_member(value: Any, field: str) -> str:
    member = _nonblank(value, field)
    if "\\" in member or "\x00" in member:
        raise ExternalPackageReceiptError(f"{field} is not a safe POSIX path")
    trimmed = member[:-1] if member.endswith("/") else member
    windows = PureWindowsPath(trimmed)
    posix = PurePosixPath(trimmed)
    if (
        windows.is_absolute()
        or windows.drive
        or posix.is_absolute()
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise ExternalPackageReceiptError(f"{field} is not a safe archive path")
    return member


def _archive_collision_key(member: str) -> str:
    """Return the Windows-safe identity used to reject archive path aliases."""

    trimmed = member[:-1] if member.endswith("/") else member
    normalized_parts = []
    for part in PurePosixPath(trimmed).parts:
        normalized = unicodedata.normalize("NFC", part)
        if normalized.endswith((" ", ".")):
            raise ExternalPackageReceiptError(
                "archive member contains a Windows-ambiguous trailing character"
            )
        normalized_parts.append(normalized.casefold())
    return "/".join(normalized_parts)


def _optional_nonblank(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, field)


def _validate_rights(raw: Any) -> dict[str, Any]:
    rights = _mapping(raw, "provenance.rights")
    _exact_keys(
        rights,
        {
            "reuse_status",
            "license_or_reuse_restriction",
            "license_url",
            "redistribution_allowed",
            "spdx_identifier",
            "notes",
        },
        "provenance.rights",
    )
    status = _nonblank(
        rights.get("reuse_status"), "provenance.rights.reuse_status"
    ).upper()
    if status not in _REUSE_STATES:
        raise ExternalPackageReceiptError("unsupported rights reuse_status")
    restriction = _nonblank(
        rights.get("license_or_reuse_restriction"),
        "provenance.rights.license_or_reuse_restriction",
    )
    redistribution = rights.get("redistribution_allowed")
    if not isinstance(redistribution, bool):
        raise ExternalPackageReceiptError(
            "provenance.rights.redistribution_allowed must be a boolean"
        )
    license_url = _optional_nonblank(
        rights.get("license_url"), "provenance.rights.license_url"
    )
    spdx_identifier = _optional_nonblank(
        rights.get("spdx_identifier"), "provenance.rights.spdx_identifier"
    )
    notes = _optional_nonblank(rights.get("notes"), "provenance.rights.notes")
    if status == "UNKNOWN" and (
        redistribution or license_url is not None or spdx_identifier is not None
    ):
        raise ExternalPackageReceiptError(
            "UNKNOWN rights require redistribution=false and null license identifiers"
        )
    return {
        "reuse_status": status,
        "license_or_reuse_restriction": restriction,
        "license_url": license_url,
        "redistribution_allowed": redistribution,
        "spdx_identifier": spdx_identifier,
        "notes": notes,
    }


def load_external_package_receipt(path: str | Path) -> dict[str, Any]:
    """Load one receipt JSON object; semantic validation is separate."""

    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ExternalPackageReceiptError("external package receipt must be an object")
    return payload


def validate_external_package_receipt(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and self-hash one authority-false external package receipt."""

    if not isinstance(receipt, Mapping):
        raise ExternalPackageReceiptError("external package receipt must be an object")
    normalized = deepcopy(dict(receipt))
    _exact_keys(
        normalized,
        {
            "schema_version",
            "receipt_id",
            "recorded_at",
            "package",
            "provenance",
            "admission",
            "authority",
            "parents",
            "evidence_summary",
            "receipt_sha256",
        },
        "receipt",
    )
    if normalized["schema_version"] != EXTERNAL_PACKAGE_RECEIPT_SCHEMA_VERSION:
        raise ExternalPackageReceiptError("unsupported external package receipt schema")
    _nonblank(normalized["receipt_id"], "receipt_id")
    recorded_at = _nonblank(normalized["recorded_at"], "recorded_at")
    try:
        timestamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalPackageReceiptError("recorded_at must be ISO-8601") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ExternalPackageReceiptError("recorded_at must include a timezone")

    package = _mapping(normalized["package"], "package")
    _exact_keys(
        package,
        {
            "file_name",
            "locator",
            "locator_scope",
            "byte_size",
            "sha256",
            "media_type",
            "archive_entry_count",
            "archive_file_count",
            "declared_payload_count",
            "package_root",
            "embedded_integrity_records",
        },
        "package",
    )
    file_name = _nonblank(package["file_name"], "package.file_name")
    if file_name != Path(file_name).name or any(mark in file_name for mark in "/\\"):
        raise ExternalPackageReceiptError("package.file_name must be a basename")
    _nonblank(package["locator"], "package.locator")
    locator_scope = _nonblank(package["locator_scope"], "package.locator_scope")
    if locator_scope not in _LOCATOR_SCOPES:
        raise ExternalPackageReceiptError("unsupported package.locator_scope")
    _positive_int(package["byte_size"], "package.byte_size")
    _digest(package["sha256"], "package.sha256")
    if package["media_type"] != "application/zip":
        raise ExternalPackageReceiptError("package.media_type must be application/zip")
    entry_count = _positive_int(
        package["archive_entry_count"], "package.archive_entry_count"
    )
    file_count = _positive_int(
        package["archive_file_count"], "package.archive_file_count"
    )
    payload_count = _positive_int(
        package["declared_payload_count"], "package.declared_payload_count"
    )
    if file_count > entry_count or payload_count > file_count:
        raise ExternalPackageReceiptError("package archive counts are inconsistent")
    package_root = package["package_root"]
    if package_root is not None:
        root = _safe_archive_member(package_root, "package.package_root").rstrip("/")
        if "/" in root:
            raise ExternalPackageReceiptError("package.package_root must be one component")

    embedded = package["embedded_integrity_records"]
    if not isinstance(embedded, list) or not embedded:
        raise ExternalPackageReceiptError(
            "package.embedded_integrity_records must be a non-empty list"
        )
    embedded_paths: set[str] = set()
    for index, record_raw in enumerate(embedded):
        field = f"package.embedded_integrity_records[{index}]"
        record = _mapping(record_raw, field)
        _exact_keys(record, {"path", "byte_size", "sha256", "role"}, field)
        path = _safe_archive_member(record["path"], f"{field}.path")
        if path in embedded_paths:
            raise ExternalPackageReceiptError("embedded integrity paths must be unique")
        embedded_paths.add(path)
        _positive_int(record["byte_size"], f"{field}.byte_size", allow_zero=True)
        _digest(record["sha256"], f"{field}.sha256")
        if _nonblank(record["role"], f"{field}.role") not in {
            "MANIFEST",
            "CHECKSUM_LEDGER",
        }:
            raise ExternalPackageReceiptError(f"{field}.role is unsupported")

    provenance = _mapping(normalized["provenance"], "provenance")
    _exact_keys(
        provenance,
        {
            "source_type",
            "independence_group",
            "conversation_id",
            "turn_id",
            "message_id",
            "lineage_resolution",
            "rights",
        },
        "provenance",
    )
    if provenance["source_type"] not in _SOURCE_TYPES:
        raise ExternalPackageReceiptError("unsupported provenance.source_type")
    _nonblank(provenance["independence_group"], "provenance.independence_group")
    _nonblank(provenance["conversation_id"], "provenance.conversation_id")
    _optional_nonblank(provenance["turn_id"], "provenance.turn_id")
    _optional_nonblank(provenance["message_id"], "provenance.message_id")
    _nonblank(provenance["lineage_resolution"], "provenance.lineage_resolution")
    rights = _validate_rights(provenance["rights"])

    admission = _mapping(normalized["admission"], "admission")
    _exact_keys(
        admission,
        {"state", "blockers", *_ADMISSION_BOOLEAN_FIELDS},
        "admission",
    )
    _nonblank(admission["state"], "admission.state")
    blockers = admission["blockers"]
    if not isinstance(blockers, list) or not blockers:
        raise ExternalPackageReceiptError("admission.blockers must be non-empty")
    normalized_blockers = [
        _nonblank(item, f"admission.blockers[{index}]")
        for index, item in enumerate(blockers)
    ]
    if len(set(normalized_blockers)) != len(normalized_blockers):
        raise ExternalPackageReceiptError("admission.blockers must be unique")
    for field in _ADMISSION_BOOLEAN_FIELDS:
        if admission[field] is not False:
            raise ExternalPackageReceiptError(f"admission.{field} must remain false")
    if rights["redistribution_allowed"] is not False:
        raise ExternalPackageReceiptError(
            "quarantined package receipts require redistribution_allowed=false"
        )

    authority = _mapping(normalized["authority"], "authority")
    _exact_keys(authority, set(_AUTHORITY_FIELDS), "authority")
    for field in _AUTHORITY_FIELDS:
        if authority[field] is not False:
            raise ExternalPackageReceiptError(f"authority.{field} must remain false")

    parents = normalized["parents"]
    if not isinstance(parents, list):
        raise ExternalPackageReceiptError("parents must be a list")
    parent_hashes: set[str] = set()
    for index, parent_raw in enumerate(parents):
        field = f"parents[{index}]"
        parent = _mapping(parent_raw, field)
        _exact_keys(
            parent,
            {
                "artifact_name",
                "byte_size",
                "sha256",
                "relation",
                "support_scope",
                "authority_state",
            },
            field,
        )
        _nonblank(parent["artifact_name"], f"{field}.artifact_name")
        _positive_int(parent["byte_size"], f"{field}.byte_size")
        parent_hash = _digest(parent["sha256"], f"{field}.sha256")
        if parent_hash in parent_hashes:
            raise ExternalPackageReceiptError("parent hashes must be unique")
        parent_hashes.add(parent_hash)
        _nonblank(parent["relation"], f"{field}.relation")
        _nonblank(parent["support_scope"], f"{field}.support_scope")
        if parent["authority_state"] != "POINTER_ONLY":
            raise ExternalPackageReceiptError(
                f"{field}.authority_state must remain POINTER_ONLY"
            )
    _mapping(normalized["evidence_summary"], "evidence_summary")

    declared_receipt_hash = _digest(
        normalized["receipt_sha256"], "receipt.receipt_sha256"
    )
    unhashed = deepcopy(normalized)
    unhashed.pop("receipt_sha256")
    if stable_json_hash(unhashed) != declared_receipt_hash:
        raise ExternalPackageReceiptError("receipt.receipt_sha256 does not match")
    return normalized


def verify_external_package_bytes(
    receipt: Mapping[str, Any],
    *,
    package_path: str | Path,
) -> ExternalPackageVerification:
    """Verify exact ZIP bytes and embedded ledgers without extracting content."""

    normalized = validate_external_package_receipt(receipt)
    declared_receipt_hash = str(normalized["receipt_sha256"])
    declared_package = dict(normalized["package"])
    path = Path(package_path)

    def failed(
        detail: str,
        *,
        actual_hash: str = "",
        entry_count: int = 0,
        file_count: int = 0,
        verified: tuple[str, ...] = (),
    ) -> ExternalPackageVerification:
        return ExternalPackageVerification(
            integrity_verified=False,
            status="INTEGRITY_HOLD",
            receipt_sha256=declared_receipt_hash,
            package_sha256=actual_hash,
            archive_entry_count=entry_count,
            archive_file_count=file_count,
            verified_embedded_records=verified,
            promotion_allowed=False,
            errors=(detail,),
        )

    if not path.is_file():
        return failed(f"package bytes are missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != declared_package["byte_size"]:
        return failed(
            "package byte size differs from receipt",
            actual_hash=stable_file_hash(path),
        )
    actual_hash = stable_file_hash(path)
    if actual_hash != declared_package["sha256"]:
        return failed("package SHA-256 differs from receipt", actual_hash=actual_hash)

    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > _MAX_ARCHIVE_ENTRIES:
                return failed(
                    "archive entry count is outside the safety bound",
                    actual_hash=actual_hash,
                    entry_count=len(infos),
                )
            seen: dict[str, str] = {}
            file_infos: dict[str, ZipInfo] = {}
            total_uncompressed = 0
            package_root = declared_package["package_root"]
            root_prefix = f"{package_root}/" if package_root else None
            for index, info in enumerate(infos):
                try:
                    member = _safe_archive_member(
                        info.filename,
                        f"archive.entries[{index}]",
                    )
                except ExternalPackageReceiptError as exc:
                    return failed(
                        str(exc),
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                try:
                    collision_key = _archive_collision_key(member)
                except ExternalPackageReceiptError as exc:
                    return failed(
                        str(exc),
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                prior_member = seen.get(collision_key)
                if prior_member is not None:
                    return failed(
                        "duplicate normalized archive member: "
                        f"{member} conflicts with {prior_member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                seen[collision_key] = member
                if root_prefix and member.rstrip("/") != package_root and not member.startswith(
                    root_prefix
                ):
                    return failed(
                        f"archive member escapes declared package root: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    return failed(
                        f"archive symlink is forbidden: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                if info.flag_bits & 0x1:
                    return failed(
                        f"encrypted archive member is unsupported: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                if info.is_dir():
                    continue
                if info.file_size > _MAX_ARCHIVE_MEMBER_BYTES:
                    return failed(
                        f"archive member exceeds size limit: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                total_uncompressed += info.file_size
                if total_uncompressed > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    return failed(
                        "archive exceeds total uncompressed size limit",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                if info.file_size and (
                    info.compress_size == 0
                    or info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
                ):
                    return failed(
                        f"archive member exceeds compression-ratio limit: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                    )
                file_infos[member] = info

            if len(infos) != declared_package["archive_entry_count"]:
                return failed(
                    "archive entry count differs from receipt",
                    actual_hash=actual_hash,
                    entry_count=len(infos),
                    file_count=len(file_infos),
                )
            if len(file_infos) != declared_package["archive_file_count"]:
                return failed(
                    "archive file count differs from receipt",
                    actual_hash=actual_hash,
                    entry_count=len(infos),
                    file_count=len(file_infos),
                )

            verified: list[str] = []
            for record in declared_package["embedded_integrity_records"]:
                member = str(record["path"])
                embedded_info = file_infos.get(member)
                if embedded_info is None:
                    return failed(
                        f"embedded integrity record is missing: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                        verified=tuple(verified),
                    )
                payload = archive.read(embedded_info)
                if len(payload) != record["byte_size"]:
                    return failed(
                        f"embedded record size differs: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                        verified=tuple(verified),
                    )
                if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    return failed(
                        f"embedded record SHA-256 differs: {member}",
                        actual_hash=actual_hash,
                        entry_count=len(infos),
                        file_count=len(file_infos),
                        verified=tuple(verified),
                    )
                verified.append(member)
    except (BadZipFile, OSError, RuntimeError) as exc:
        return failed(f"archive verification failed: {exc}", actual_hash=actual_hash)

    return ExternalPackageVerification(
        integrity_verified=True,
        status="VERIFIED_QUARANTINED",
        receipt_sha256=declared_receipt_hash,
        package_sha256=actual_hash,
        archive_entry_count=int(declared_package["archive_entry_count"]),
        archive_file_count=int(declared_package["archive_file_count"]),
        verified_embedded_records=tuple(verified),
        promotion_allowed=False,
        errors=(),
    )


__all__ = [
    "EXTERNAL_PACKAGE_RECEIPT_SCHEMA_VERSION",
    "ExternalPackageReceiptError",
    "ExternalPackageVerification",
    "load_external_package_receipt",
    "validate_external_package_receipt",
    "verify_external_package_bytes",
]
