"""Manifest-gated staging for external scientific source bytes.

This module verifies source identity, rights, paths, byte counts, and SHA-256
digests, then emits deterministic *candidates* for the backend B1 source layer.
It never imports backend services, promotes observations, or writes canonical
material, inventory, formula, safety, database, or generated-artifact state.
"""

from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from engine.calibration.hashing import stable_file_hash, stable_json_hash

SCIENTIFIC_SOURCE_SCHEMA_VERSION = "scientific_source_manifest_v1"
SCIENTIFIC_STAGING_VERSION = "scientific-source-staging-v1"

_REVISION_KINDS = {"git_commit", "doi_version", "release", "content_digest"}
_REUSE_STATES = {"PERMITTED", "RESTRICTED", "UNKNOWN"}
_REVIEW_STATES = {"UNREVIEWED", "REVIEWED", "REJECTED", "SUPERSEDED"}
_ARTIFACT_ROLES = {
    "PRIMARY_DATA",
    "RAW_DATA",
    "DERIVED_DATA",
    "LICENSE",
    "DOCUMENTATION",
    "CODE",
}
_MUTABLE_URL_SEGMENT = re.compile(r"/(?:main|master|latest)(?:/|$)", re.IGNORECASE)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CAS_NUMBER = re.compile(r"^\d{2,7}-\d{2}-\d$")
_PUBCHEM_CID = re.compile(r"^[1-9]\d*$")
_COMPTOX_DTXSID = re.compile(r"^DTXSID\d{7}$")
_INCHI_KEY = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")
_SOURCE_DERIVATION_RELATIONS = {
    "DERIVED_FROM",
    "REPRODUCES",
    "CITES",
    "INCORPORATES",
}
_STAGING_SOURCE_RELATIONS = {"CITES"}

_DREAM_ADAPTER_VERSION = "dream_psychophysics_intensity_v1"
_DREAM_REQUIRED_COLUMNS = (
    "Compound Identifier",
    "Odor",
    "Replicate",
    "Intensity",
    "Dilution",
    "subject #",
    "INTENSITY/STRENGTH",
)
_DREAM_VALUE_LINEAGE_ADAPTER_VERSION = "keller_vosshall_xlsx_to_dream_v1"
_DREAM_VALUE_LINEAGE_KEY_FIELD_MAP = {
    "Compound Identifier": "CID",
    "Odor": "Odor",
    "Dilution": "Odor dilution",
    "subject #": "Subject # (DREAM challenge)",
}
_DREAM_VALUE_LINEAGE_RESPONSE_FIELD_MAP = {
    "INTENSITY/STRENGTH": "HOW STRONG IS THE SMELL?",
    "VALENCE/PLEASANTNESS": "HOW PLEASANT IS THE SMELL?",
    "BAKERY": "BAKERY",
    "SWEET": "SWEET",
    "FRUIT": "FRUIT",
    "FISH": "FISH",
    "GARLIC": "GARLIC",
    "SPICES": "SPICES",
    "COLD": "COLD",
    "SOUR": "SOUR",
    "BURNT": "BURNT",
    "ACID": "ACID",
    "WARM": "WARM",
    "MUSKY": "MUSKY",
    "SWEATY": "SWEATY",
    "AMMONIA/URINOUS": "AMMONIA/URINOUS",
    "DECAYED": "DECAYED",
    "WOOD": "WOOD",
    "GRASS": "GRASS",
    "FLOWER": "FLOWER",
    "CHEMICAL": "CHEMICAL",
}
_DREAM_VALUE_LINEAGE_TARGET_COLUMNS = (
    *_DREAM_REQUIRED_COLUMNS,
    "VALENCE/PLEASANTNESS",
    *tuple(
        field
        for field in _DREAM_VALUE_LINEAGE_RESPONSE_FIELD_MAP
        if field not in _DREAM_REQUIRED_COLUMNS
        and field != "VALENCE/PLEASANTNESS"
    ),
)
_DREAM_VALUE_LINEAGE_EXPECTED_COUNT_FIELDS = (
    "matched_rows",
    "compared_cells",
    "exact_numeric",
    "source_blank_to_target_zero",
    "source_blank_to_target_blank",
    "deterministic_trailing_zero_restoration",
    "published_derivative_one_to_ten",
    "published_derivative_one_to_hundred",
    "incompatible",
)
_DREAM_VALUE_LINEAGE_FULL_CORPUS_COUNT_FIELDS = (
    *_DREAM_VALUE_LINEAGE_EXPECTED_COUNT_FIELDS,
    "parent_keyed_rows",
    "parent_rows_outside_child_corpus",
)
_DREAM_VALUE_LINEAGE_SCOPES = {"SELECTED_TRANCHE", "FULL_CORPUS"}
_DREAM_VALUE_LINEAGE_DEFAULT_DETAIL_LIMIT = 50
_DREAM_VALUE_LINEAGE_MAX_DETAIL_LIMIT = 100
_DREAM_VALUE_LINEAGE_STATE = (
    "PARTIALLY_DETERMINISTIC_PUBLISHED_DERIVATIVE_DISAMBIGUATION_REQUIRED"
)
_XLSX_MAIN_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_DOCUMENT_REL_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
_XLSX_PACKAGE_REL_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
_XLSX_CELL_REFERENCE = re.compile(r"^([A-Z]{1,3})([1-9]\d*)$")
_XLSX_MAX_ARCHIVE_MEMBERS = 64
_XLSX_MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
_XLSX_MAX_MEMBER_BYTES = 96 * 1024 * 1024
_XLSX_MAX_COMPRESSION_RATIO = 100
_XLSX_MAX_SHARED_STRINGS = 100_000
_XLSX_MAX_ROWS = 100_000
_XLSX_MAX_CELLS_PER_ROW = 256
_RATING_QUANTUM = Decimal("0.000000000001")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROTECTED_DIRS = (
    _PROJECT_ROOT / "backend",
    _PROJECT_ROOT / "data" / "materials",
    _PROJECT_ROOT / "data" / "knowledge_graph",
    _PROJECT_ROOT / "data" / "embeddings",
)
_PROTECTED_FILES = (
    _PROJECT_ROOT / "inventory.txt",
    _PROJECT_ROOT / "data" / "perfumery_kb.db",
)
_ALLOWED_STAGING_DIRS = (
    _PROJECT_ROOT / "output",
    _PROJECT_ROOT / "verification_runs",
    _PROJECT_ROOT / "archive",
)
_ALLOWED_FETCH_DIRS = (
    _PROJECT_ROOT / "data" / "external",
    *_ALLOWED_STAGING_DIRS,
)


class UnsafeIngestionPathError(ValueError):
    """Raised before a source fetch or report write can touch a protected path."""


@dataclass(frozen=True, slots=True)
class SourceRejection:
    code: str
    detail: str
    field: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "detail": self.detail, "field": self.field}


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _assert_not_protected(path: Path, *, purpose: str) -> None:
    resolved = path.resolve()
    if resolved == _PROJECT_ROOT:
        raise UnsafeIngestionPathError(f"{purpose} cannot be the project root")
    for protected in _PROTECTED_FILES:
        if resolved == protected.resolve():
            raise UnsafeIngestionPathError(f"{purpose} targets protected file: {protected}")
    for protected in _PROTECTED_DIRS:
        protected_resolved = protected.resolve()
        if resolved == protected_resolved or _is_within(resolved, protected_resolved):
            raise UnsafeIngestionPathError(f"{purpose} targets protected path: {protected}")


def _assert_output_path(path: Path) -> None:
    resolved = path.resolve()
    _assert_not_protected(resolved, purpose="staging output")
    if _is_within(resolved, _PROJECT_ROOT) and not any(
        resolved == allowed.resolve() or _is_within(resolved, allowed.resolve())
        for allowed in _ALLOWED_STAGING_DIRS
    ):
        raise UnsafeIngestionPathError(
            "staging output inside the project must be under output/, "
            "verification_runs/, or archive/"
        )


def _assert_source_root(path: Path, *, allow_fetch: bool) -> None:
    resolved = path.resolve()
    _assert_not_protected(resolved, purpose="external source root")
    if resolved.exists() and not resolved.is_dir():
        raise UnsafeIngestionPathError("external source root must be a directory")
    if allow_fetch and _is_within(resolved, _PROJECT_ROOT) and not any(
        resolved == allowed.resolve() or _is_within(resolved, allowed.resolve())
        for allowed in _ALLOWED_FETCH_DIRS
    ):
        raise UnsafeIngestionPathError(
            "network fetch inside the project must target data/external/, output/, "
            "verification_runs/, or archive/"
        )


def _text(value: Any, field: str, rejections: list[SourceRejection]) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        rejections.append(SourceRejection("MISSING_FIELD", f"{field} is required", field))
    return normalized


def _relative_path(
    value: Any,
    field: str,
    rejections: list[SourceRejection],
) -> str | None:
    normalized = str(value or "").strip().replace("\\", "/")
    if not normalized:
        rejections.append(SourceRejection("MISSING_FIELD", f"{field} is required", field))
        return None
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(normalized)
    if posix.is_absolute() or windows.is_absolute() or ".." in posix.parts:
        rejections.append(
            SourceRejection(
                "ARTIFACT_PATH_ESCAPE",
                f"{field} must be a relative non-traversing path: {normalized}",
                field,
            )
        )
        return None
    return posix.as_posix()


def _immutable_url(
    value: Any,
    field: str,
    rejections: list[SourceRejection],
) -> str:
    normalized = _text(value, field, rejections)
    if not normalized:
        return normalized
    parsed = urlparse(normalized)
    if parsed.scheme not in {"https", "doi"}:
        rejections.append(
            SourceRejection(
                "INVALID_SOURCE_URL",
                f"{field} must use https or doi: {normalized}",
                field,
            )
        )
    if _MUTABLE_URL_SEGMENT.search(parsed.path):
        rejections.append(
            SourceRejection(
                "MUTABLE_SOURCE_URL",
                f"{field} contains a mutable main/master/latest selector: {normalized}",
                field,
            )
        )
    return normalized


def _parse_timestamp(
    value: Any,
    field: str,
    rejections: list[SourceRejection],
) -> str:
    normalized = _text(value, field, rejections)
    if not normalized:
        return normalized
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        rejections.append(
            SourceRejection(
                "INVALID_RETRIEVAL_TIMESTAMP",
                f"{field} must be ISO 8601: {normalized}",
                field,
            )
        )
        return normalized
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        rejections.append(
            SourceRejection(
                "INVALID_RETRIEVAL_TIMESTAMP",
                f"{field} must include a timezone offset",
                field,
            )
        )
    return normalized


def _validate_revision(
    raw: Any,
    rejections: list[SourceRejection],
) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        rejections.append(
            SourceRejection("MISSING_REVISION", "revision must be an object", "revision")
        )
        return {"kind": "", "value": ""}
    kind = str(raw.get("kind", "")).strip()
    raw_value = str(raw.get("value", "")).strip()
    value = raw_value.casefold() if kind in {"git_commit", "content_digest"} else raw_value
    if kind not in _REVISION_KINDS:
        rejections.append(
            SourceRejection(
                "MISSING_REVISION",
                f"revision.kind must be one of {sorted(_REVISION_KINDS)}",
                "revision.kind",
            )
        )
    if not value or value in {"main", "master", "latest", "head", "unknown"}:
        rejections.append(
            SourceRejection(
                "MISSING_REVISION",
                "revision.value must identify an immutable revision",
                "revision.value",
            )
        )
    elif kind == "git_commit" and not _GIT_COMMIT.fullmatch(value):
        rejections.append(
            SourceRejection(
                "INVALID_REVISION",
                "git_commit revision must be a full 40-character hexadecimal commit",
                "revision.value",
            )
        )
    elif kind == "content_digest" and not _SHA256.fullmatch(value):
        rejections.append(
            SourceRejection(
                "INVALID_REVISION",
                "content_digest revision must be a lowercase SHA-256 digest",
                "revision.value",
            )
        )
    return {"kind": kind, "value": value}


def _validate_rights(
    raw: Any,
    rejections: list[SourceRejection],
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        rejections.append(
            SourceRejection("RIGHTS_UNRESOLVED", "rights must be an object", "rights")
        )
        return {
            "reuse_status": "UNKNOWN",
            "license_or_reuse_restriction": "",
            "license_url": "",
            "redistribution_allowed": False,
        }
    status = str(raw.get("reuse_status", "UNKNOWN")).strip().upper()
    restriction = str(raw.get("license_or_reuse_restriction", "")).strip()
    license_url = _immutable_url(raw.get("license_url"), "rights.license_url", rejections)
    redistribution = raw.get("redistribution_allowed")
    if status not in _REUSE_STATES or status == "UNKNOWN":
        rejections.append(
            SourceRejection(
                "RIGHTS_UNRESOLVED",
                "rights.reuse_status must be PERMITTED or RESTRICTED",
                "rights.reuse_status",
            )
        )
    if not restriction:
        rejections.append(
            SourceRejection(
                "RIGHTS_UNRESOLVED",
                "rights.license_or_reuse_restriction is required",
                "rights.license_or_reuse_restriction",
            )
        )
    if not isinstance(redistribution, bool):
        rejections.append(
            SourceRejection(
                "RIGHTS_UNRESOLVED",
                "rights.redistribution_allowed must be a boolean",
                "rights.redistribution_allowed",
            )
        )
        redistribution = False
    return {
        "reuse_status": status,
        "license_or_reuse_restriction": restriction,
        "license_url": license_url,
        "redistribution_allowed": redistribution,
        "spdx_identifier": str(raw.get("spdx_identifier") or "").strip() or None,
        "notes": str(raw.get("notes") or "").strip() or None,
    }


def _fetch_with_pooch(
    *,
    destination: Path,
    source_url: str,
    sha256: str,
) -> None:
    try:
        import pooch
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise RuntimeError(
            "Pooch is required for --fetch; install the root data extra"
        ) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    fetched = Path(
        pooch.retrieve(
            url=source_url,
            known_hash=f"sha256:{sha256}",
            path=destination.parent,
            fname=destination.name,
            progressbar=False,
        )
    ).resolve()
    if fetched != destination.resolve():  # pragma: no cover - defensive Pooch contract
        raise RuntimeError(f"fetcher returned unexpected path: {fetched}")


def _artifact_records(
    artifacts_raw: Any,
    *,
    source_root: Path,
    allow_fetch: bool,
    rejections: list[SourceRejection],
) -> list[dict[str, Any]]:
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        rejections.append(
            SourceRejection(
                "MISSING_ARTIFACTS",
                "artifacts must be a non-empty list",
                "artifacts",
            )
        )
        return []

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    records: list[dict[str, Any]] = []
    for index, raw in enumerate(artifacts_raw):
        field = f"artifacts[{index}]"
        if not isinstance(raw, Mapping):
            rejections.append(
                SourceRejection("INVALID_ARTIFACT", f"{field} must be an object", field)
            )
            continue
        artifact_id = _text(raw.get("artifact_id"), f"{field}.artifact_id", rejections)
        relative = _relative_path(raw.get("path"), f"{field}.path", rejections)
        role = str(raw.get("role", "")).strip().upper()
        media_type = _text(raw.get("media_type"), f"{field}.media_type", rejections)
        source_url = _immutable_url(raw.get("source_url"), f"{field}.source_url", rejections)
        sha256 = str(raw.get("sha256", "")).strip().casefold()
        byte_size = raw.get("byte_size")
        preserved = _relative_path(
            raw.get("preserved_artifact_path"),
            f"{field}.preserved_artifact_path",
            rejections,
        )
        if artifact_id in seen_ids:
            rejections.append(
                SourceRejection(
                    "DUPLICATE_ARTIFACT",
                    f"duplicate artifact_id: {artifact_id}",
                    f"{field}.artifact_id",
                )
            )
        seen_ids.add(artifact_id)
        path_identity = relative.casefold() if relative is not None else None
        if path_identity is not None and path_identity in seen_paths:
            rejections.append(
                SourceRejection(
                    "DUPLICATE_ARTIFACT",
                    f"duplicate artifact path: {relative}",
                    f"{field}.path",
                )
            )
        if path_identity is not None:
            seen_paths.add(path_identity)
        if role not in _ARTIFACT_ROLES:
            rejections.append(
                SourceRejection(
                    "INVALID_ARTIFACT_ROLE",
                    f"{field}.role must be one of {sorted(_ARTIFACT_ROLES)}",
                    f"{field}.role",
                )
            )
        if not _SHA256.fullmatch(sha256):
            rejections.append(
                SourceRejection(
                    "INVALID_ARTIFACT_HASH",
                    f"{field}.sha256 must be a lowercase SHA-256 digest",
                    f"{field}.sha256",
                )
            )
        if not isinstance(byte_size, int) or isinstance(byte_size, bool) or byte_size < 0:
            rejections.append(
                SourceRejection(
                    "INVALID_ARTIFACT_SIZE",
                    f"{field}.byte_size must be a non-negative integer",
                    f"{field}.byte_size",
                )
            )

        actual_size: int | None = None
        actual_hash: str | None = None
        status = "UNVERIFIED"
        if relative is not None:
            local_path = (source_root / Path(relative)).resolve()
            if not _is_within(local_path, source_root):
                rejections.append(
                    SourceRejection(
                        "ARTIFACT_PATH_ESCAPE",
                        f"resolved artifact escapes source root: {relative}",
                        f"{field}.path",
                    )
                )
            else:
                if not local_path.exists() and allow_fetch and source_url and _SHA256.fullmatch(sha256):
                    try:
                        _fetch_with_pooch(
                            destination=local_path,
                            source_url=source_url,
                            sha256=sha256,
                        )
                    except Exception as exc:  # noqa: BLE001
                        rejections.append(
                            SourceRejection(
                                "FETCH_FAILED",
                                f"failed to fetch {artifact_id}: {exc}",
                                f"{field}.source_url",
                            )
                        )
                if not local_path.is_file():
                    rejections.append(
                        SourceRejection(
                            "ARTIFACT_MISSING",
                            f"artifact is missing: {relative}",
                            f"{field}.path",
                        )
                    )
                    status = "MISSING"
                else:
                    actual_size = local_path.stat().st_size
                    actual_hash = stable_file_hash(local_path)
                    if isinstance(byte_size, int) and actual_size != byte_size:
                        rejections.append(
                            SourceRejection(
                                "ARTIFACT_SIZE_MISMATCH",
                                f"{artifact_id} expected {byte_size} bytes, found {actual_size}",
                                f"{field}.byte_size",
                            )
                        )
                    if _SHA256.fullmatch(sha256) and actual_hash != sha256:
                        rejections.append(
                            SourceRejection(
                                "ARTIFACT_HASH_MISMATCH",
                                f"{artifact_id} expected {sha256}, found {actual_hash}",
                                f"{field}.sha256",
                            )
                        )
                    status = (
                        "VERIFIED"
                        if actual_size == byte_size and actual_hash == sha256
                        else "MISMATCH"
                    )

        records.append(
            {
                "artifact_id": artifact_id,
                "path": relative,
                "preserved_artifact_path": preserved,
                "role": role,
                "media_type": media_type,
                "source_url": source_url,
                "declared_byte_size": byte_size,
                "actual_byte_size": actual_size,
                "declared_sha256": sha256,
                "actual_sha256": actual_hash,
                "verification_status": status,
            }
        )

    records.sort(key=lambda item: (str(item["artifact_id"]), str(item["path"])))
    if not any(record["role"] == "PRIMARY_DATA" for record in records):
        rejections.append(
            SourceRejection(
                "MISSING_PRIMARY_DATA",
                "at least one artifact must have role PRIMARY_DATA",
                "artifacts",
            )
        )
    return records


def _normalize_manifest(
    manifest: Mapping[str, Any],
    *,
    artifacts: list[dict[str, Any]],
    revision: dict[str, str],
    rights: dict[str, Any],
    retrieved_at: str,
) -> dict[str, Any]:
    normalized = deepcopy(dict(manifest))
    normalized["schema_version"] = SCIENTIFIC_SOURCE_SCHEMA_VERSION
    normalized["revision"] = revision
    normalized["retrieved_at"] = retrieved_at
    normalized["rights"] = rights
    normalized["artifacts"] = [
        {
            "artifact_id": record["artifact_id"],
            "path": record["path"],
            "preserved_artifact_path": record["preserved_artifact_path"],
            "role": record["role"],
            "media_type": record["media_type"],
            "source_url": record["source_url"],
            "byte_size": record["declared_byte_size"],
            "sha256": record["declared_sha256"],
        }
        for record in artifacts
    ]
    return normalized


def _validate_revision_urls(
    records: list[dict[str, Any]],
    *,
    revision: Mapping[str, str],
    rejections: list[SourceRejection],
) -> None:
    """Bind Git-backed artifact URLs to the declared immutable commit."""
    if revision.get("kind") != "git_commit" or not revision.get("value"):
        return
    commit = str(revision["value"]).casefold()
    for index, record in enumerate(records):
        source_url = str(record.get("source_url") or "")
        if commit not in source_url.casefold():
            rejections.append(
                SourceRejection(
                    "REVISION_URL_MISMATCH",
                    f"artifact URL does not contain declared Git commit: {record['artifact_id']}",
                    f"artifacts[{index}].source_url",
                )
            )


def _source_candidates(
    manifest: Mapping[str, Any],
    *,
    artifacts: list[dict[str, Any]],
    manifest_hash: str,
) -> list[dict[str, Any]]:
    retrieved_at = str(manifest["retrieved_at"])
    retrieval_date = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00")).date().isoformat()
    revision = dict(manifest["revision"])
    rights = dict(manifest["rights"])
    identifiers = dict(manifest.get("identifiers") or {})
    identifiers["source_revision_kind"] = revision["kind"]
    identifiers["source_revision"] = revision["value"]
    candidates: list[dict[str, Any]] = []
    for artifact in artifacts:
        if artifact["role"] != "PRIMARY_DATA":
            continue
        artifact_identifiers = dict(identifiers)
        artifact_identifiers["artifact_id"] = str(artifact["artifact_id"])
        candidates.append(
            _hashed_candidate(
                {
                    "candidate_schema_version": "b1_source_document_candidate_v1",
                    "schema_version": str(manifest.get("schema_version", "")),
                    "source_id": f"{manifest['source_id']}:{artifact['artifact_id']}",
                    "source_type": str(manifest["source_type"]),
                    "title": str(manifest["title"]),
                    "artifact_sha256": str(artifact["actual_sha256"]),
                    "language": str(manifest["language"]),
                    "review_state": str(manifest["review_state"]),
                    "independence_group": str(manifest["independence_group"]),
                    "authors": list(manifest.get("authors") or []),
                    "issuing_organization": manifest.get("issuing_organization"),
                    "container_title": manifest.get("container_title"),
                    "publisher_or_authority": manifest.get("publisher_or_authority"),
                    "identifiers": artifact_identifiers,
                    "publication_date": manifest.get("publication_date"),
                    "revision_date": manifest.get("revision_date"),
                    "effective_date": manifest.get("effective_date"),
                    "retrieval_date": retrieval_date,
                    "edition_or_amendment": manifest.get("edition_or_amendment"),
                    "default_locator": {
                        "artifact_id": artifact["artifact_id"],
                        "artifact_path": artifact["preserved_artifact_path"],
                        "source_url": artifact["source_url"],
                        "revision": revision,
                        "manifest_sha256": manifest_hash,
                    },
                    "license_or_reuse_restriction": rights[
                        "license_or_reuse_restriction"
                    ],
                    # Preserve the complete normalized object. The scalar above
                    # remains a compatibility projection only and must agree
                    # with this hash-bound authority record downstream.
                    "rights": rights,
                    "preserved_artifact_path": artifact[
                        "preserved_artifact_path"
                    ],
                    "workflow_state": "STAGED",
                    "authority_state": "CANDIDATE_ONLY",
                },
                hash_field="candidate_sha256",
            )
        )
    return candidates


def _nonblank(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _decimal_from_value(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _dilution_fraction(value: Any) -> Decimal | None:
    normalized = str(value or "").strip().replace(" ", "")
    match = re.fullmatch(r"1/([\d,]+)", normalized)
    if match is None:
        return None
    try:
        denominator = int(match.group(1).replace(",", ""))
    except ValueError:
        return None
    if denominator <= 0:
        return None
    return Decimal(1) / Decimal(denominator)


def _rounded_decimal(value: Decimal) -> float:
    return float(value.quantize(_RATING_QUANTUM))


def _json_rating(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    return _rounded_decimal(value)


def _distribution_summary(values: list[Decimal]) -> dict[str, float | int]:
    if len(values) < 2:
        raise ValueError("a distribution requires at least two ratings")
    with localcontext() as context:
        context.prec = 50
        count = Decimal(len(values))
        mean = sum(values, Decimal(0)) / count
        variance = sum((value - mean) ** 2 for value in values) / (count - 1)
        sample_standard_deviation = variance.sqrt()
        standard_error = sample_standard_deviation / count.sqrt()
    return {
        "count": len(values),
        "mean": _rounded_decimal(mean),
        "sample_standard_deviation": _rounded_decimal(
            sample_standard_deviation
        ),
        "standard_error_of_mean": _rounded_decimal(standard_error),
        "minimum": _json_rating(min(values)),
        "maximum": _json_rating(max(values)),
    }


def _hashed_candidate(
    payload: Mapping[str, Any],
    *,
    hash_field: str = "content_sha256",
) -> dict[str, Any]:
    candidate = dict(payload)
    candidate[hash_field] = stable_json_hash(candidate)
    return candidate


class _XlsxLineageError(ValueError):
    """Raised when a lineage workbook violates the bounded OOXML contract."""


def _xlsx_column_number(reference: str) -> int:
    match = _XLSX_CELL_REFERENCE.fullmatch(reference)
    if match is None:
        raise _XlsxLineageError(f"invalid worksheet cell reference: {reference!r}")
    result = 0
    for character in match.group(1):
        result = result * 26 + (ord(character) - ord("A") + 1)
    return result


def _validated_xlsx_members(archive: ZipFile) -> dict[str, Any]:
    infos = archive.infolist()
    if not infos or len(infos) > _XLSX_MAX_ARCHIVE_MEMBERS:
        raise _XlsxLineageError("OOXML archive member count is outside the limit")
    members: dict[str, Any] = {}
    casefolded_names: set[str] = set()
    total_uncompressed = 0
    for info in infos:
        name = str(info.filename)
        posix = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or posix.is_absolute()
            or PureWindowsPath(name).drive
            or any(part in {"", ".", ".."} for part in posix.parts)
        ):
            raise _XlsxLineageError(f"unsafe OOXML archive member: {name!r}")
        folded = name.casefold()
        if name in members or folded in casefolded_names:
            raise _XlsxLineageError(f"duplicate OOXML archive member: {name!r}")
        if info.flag_bits & 0x1:
            raise _XlsxLineageError("encrypted OOXML members are unsupported")
        if info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
            raise _XlsxLineageError("unsupported OOXML compression method")
        if info.file_size > _XLSX_MAX_MEMBER_BYTES:
            raise _XlsxLineageError("OOXML member exceeds the uncompressed size limit")
        if info.file_size and (
            info.file_size / max(1, info.compress_size)
        ) > _XLSX_MAX_COMPRESSION_RATIO:
            raise _XlsxLineageError("OOXML member exceeds the compression-ratio limit")
        total_uncompressed += info.file_size
        if total_uncompressed > _XLSX_MAX_UNCOMPRESSED_BYTES:
            raise _XlsxLineageError("OOXML archive exceeds the uncompressed size limit")
        members[name] = info
        casefolded_names.add(folded)
    for required in (
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/_rels/workbook.xml.rels",
    ):
        if required not in members:
            raise _XlsxLineageError(f"OOXML archive is missing {required}")
    return members


def _xlsx_xml_root(
    archive: ZipFile,
    members: Mapping[str, Any],
    name: str,
) -> ElementTree.Element:
    if name not in members:
        raise _XlsxLineageError(f"OOXML archive is missing {name}")
    try:
        with archive.open(name) as handle:
            payload = handle.read(_XLSX_MAX_MEMBER_BYTES + 1)
        if len(payload) > _XLSX_MAX_MEMBER_BYTES:
            raise _XlsxLineageError(f"OOXML XML member is too large: {name}")
        return ElementTree.fromstring(payload)
    except (ElementTree.ParseError, OSError, RuntimeError) as exc:
        raise _XlsxLineageError(f"failed to parse OOXML member {name}: {exc}") from exc


def _xlsx_worksheet_member(
    archive: ZipFile,
    members: Mapping[str, Any],
    worksheet_name: str,
) -> str:
    workbook = _xlsx_xml_root(archive, members, "xl/workbook.xml")
    sheets = [
        element
        for element in workbook.iter(f"{{{_XLSX_MAIN_NAMESPACE}}}sheet")
        if str(element.get("name") or "").strip() == worksheet_name
    ]
    if len(sheets) != 1:
        raise _XlsxLineageError(
            f"expected one worksheet named {worksheet_name!r}, found {len(sheets)}"
        )
    relationship_id = str(
        sheets[0].get(f"{{{_XLSX_DOCUMENT_REL_NAMESPACE}}}id") or ""
    ).strip()
    if not relationship_id:
        raise _XlsxLineageError("worksheet is missing its relationship identifier")
    relationships = _xlsx_xml_root(
        archive,
        members,
        "xl/_rels/workbook.xml.rels",
    )
    matches = [
        element
        for element in relationships.iter(
            f"{{{_XLSX_PACKAGE_REL_NAMESPACE}}}Relationship"
        )
        if str(element.get("Id") or "").strip() == relationship_id
    ]
    if len(matches) != 1:
        raise _XlsxLineageError("worksheet relationship is missing or duplicated")
    relationship = matches[0]
    if str(relationship.get("TargetMode") or "").strip().casefold() == "external":
        raise _XlsxLineageError("external worksheet relationships are unsupported")
    if not str(relationship.get("Type") or "").endswith("/worksheet"):
        raise _XlsxLineageError("worksheet relationship has the wrong type")
    target = str(relationship.get("Target") or "").strip()
    target_path = PurePosixPath(target)
    if (
        not target
        or "\\" in target
        or target_path.is_absolute()
        or PureWindowsPath(target).drive
        or any(part in {"", ".", ".."} for part in target_path.parts)
    ):
        raise _XlsxLineageError("worksheet relationship target is unsafe")
    member = (PurePosixPath("xl") / target_path).as_posix()
    if member not in members:
        raise _XlsxLineageError("worksheet relationship target is not in the archive")
    return member


def _xlsx_shared_strings(
    archive: ZipFile,
    members: Mapping[str, Any],
) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in members:
        return []
    root = _xlsx_xml_root(archive, members, name)
    strings: list[str] = []
    for item in root.iter(f"{{{_XLSX_MAIN_NAMESPACE}}}si"):
        strings.append(
            "".join(
                str(node.text or "")
                for node in item.iter(f"{{{_XLSX_MAIN_NAMESPACE}}}t")
            )
        )
        if len(strings) > _XLSX_MAX_SHARED_STRINGS:
            raise _XlsxLineageError("shared-string table exceeds the count limit")
    return strings


def _xlsx_cell_value(
    cell: ElementTree.Element,
    shared_strings: list[str],
) -> str | None:
    if cell.find(f"{{{_XLSX_MAIN_NAMESPACE}}}f") is not None:
        raise _XlsxLineageError("formulas are unsupported in lineage fields")
    cell_type = str(cell.get("t") or "").strip()
    if cell_type == "inlineStr":
        return "".join(
            str(node.text or "")
            for node in cell.iter(f"{{{_XLSX_MAIN_NAMESPACE}}}t")
        )
    value = cell.find(f"{{{_XLSX_MAIN_NAMESPACE}}}v")
    if value is None or value.text is None:
        return None
    raw = str(value.text)
    if cell_type == "s":
        try:
            index = int(raw)
        except ValueError as exc:
            raise _XlsxLineageError("shared-string index is not an integer") from exc
        if index < 0 or index >= len(shared_strings):
            raise _XlsxLineageError("shared-string index is outside the table")
        return shared_strings[index]
    if cell_type == "e":
        raise _XlsxLineageError("error-valued cells are unsupported in lineage fields")
    return raw


def _lineage_integer_key(value: Any) -> str | None:
    decimal = _decimal_from_value(value)
    if decimal is None or decimal != decimal.to_integral_value():
        return None
    return str(int(decimal))


def _lineage_row_key(
    values: Mapping[str, Any],
    *,
    field_map: Mapping[str, str] | None = None,
) -> tuple[str, str, str, str] | None:
    mapping = field_map or {field: field for field in _DREAM_VALUE_LINEAGE_KEY_FIELD_MAP}
    cid = _lineage_integer_key(values.get(mapping["Compound Identifier"]))
    subject_id = _lineage_integer_key(values.get(mapping["subject #"]))
    odor = str(values.get(mapping["Odor"]) or "").strip().casefold()
    dilution = str(values.get(mapping["Dilution"]) or "").strip()
    if not cid or not subject_id or not odor or not dilution:
        return None
    return cid, odor, dilution, subject_id


def _xlsx_lineage_rows(
    source_path: Path,
    *,
    worksheet_name: str,
    header_row: int,
    required_headers: set[str],
    source_cid: str,
    source_odor_label: str,
    selected_keys: set[tuple[str, str, str, str]] | None = None,
) -> tuple[list[str], list[dict[str, Any]], int]:
    try:
        with ZipFile(source_path) as archive:
            members = _validated_xlsx_members(archive)
            worksheet_member = _xlsx_worksheet_member(
                archive,
                members,
                worksheet_name,
            )
            shared_strings = _xlsx_shared_strings(archive, members)
            headers_by_column: dict[int, str] = {}
            selected_rows: list[dict[str, Any]] = []
            prior_row_number = 0
            row_count = 0
            keyed_row_count = 0
            with archive.open(worksheet_member) as worksheet:
                iterator = ElementTree.iterparse(worksheet, events=("end",))
                for _, element in iterator:
                    if element.tag != f"{{{_XLSX_MAIN_NAMESPACE}}}row":
                        continue
                    row_count += 1
                    if row_count > _XLSX_MAX_ROWS:
                        raise _XlsxLineageError("worksheet exceeds the row-count limit")
                    try:
                        row_number = int(str(element.get("r") or ""))
                    except ValueError as exc:
                        raise _XlsxLineageError(
                            "worksheet row is missing a numeric row identifier"
                        ) from exc
                    if row_number <= prior_row_number:
                        raise _XlsxLineageError(
                            "worksheet row identifiers are not strictly increasing"
                        )
                    prior_row_number = row_number
                    cells = list(element.findall(f"{{{_XLSX_MAIN_NAMESPACE}}}c"))
                    if len(cells) > _XLSX_MAX_CELLS_PER_ROW:
                        raise _XlsxLineageError(
                            "worksheet row exceeds the cell-count limit"
                        )
                    if row_number == header_row:
                        seen_headers: set[str] = set()
                        for cell in cells:
                            reference = str(cell.get("r") or "")
                            match = _XLSX_CELL_REFERENCE.fullmatch(reference)
                            if match is None or int(match.group(2)) != row_number:
                                raise _XlsxLineageError(
                                    "header cell reference does not match its row"
                                )
                            column = _xlsx_column_number(reference)
                            value = _xlsx_cell_value(cell, shared_strings)
                            header = str(value or "").strip()
                            if not header:
                                continue
                            if header in seen_headers:
                                raise _XlsxLineageError(
                                    f"duplicate normalized worksheet header: {header}"
                                )
                            seen_headers.add(header)
                            headers_by_column[column] = header
                        missing = sorted(required_headers - seen_headers)
                        if missing:
                            raise _XlsxLineageError(
                                "worksheet is missing required headers: "
                                + ", ".join(missing)
                            )
                    elif row_number > header_row:
                        if not headers_by_column:
                            raise _XlsxLineageError(
                                "worksheet data appeared before the declared header row"
                            )
                        values: dict[str, Any] = {
                            header: None for header in required_headers
                        }
                        for cell in cells:
                            reference = str(cell.get("r") or "")
                            match = _XLSX_CELL_REFERENCE.fullmatch(reference)
                            if match is None or int(match.group(2)) != row_number:
                                raise _XlsxLineageError(
                                    "worksheet cell reference does not match its row"
                                )
                            column = _xlsx_column_number(reference)
                            header = headers_by_column.get(column)
                            if header in required_headers:
                                values[header] = _xlsx_cell_value(cell, shared_strings)
                        parent_key = _lineage_row_key(
                            values,
                            field_map=_DREAM_VALUE_LINEAGE_KEY_FIELD_MAP,
                        )
                        if parent_key is not None:
                            keyed_row_count += 1
                        selected = (
                            parent_key in selected_keys
                            if selected_keys is not None and parent_key is not None
                            else (
                                parent_key is not None
                                and parent_key[0] == source_cid
                                and parent_key[1] == source_odor_label.casefold()
                            )
                        )
                        if selected:
                            selected_rows.append(
                                {"row_number": row_number, "values": values}
                            )
                    element.clear()
            if not headers_by_column:
                raise _XlsxLineageError("declared worksheet header row was not found")
            return (
                [headers_by_column[index] for index in sorted(headers_by_column)],
                selected_rows,
                keyed_row_count,
            )
    except (BadZipFile, OSError, RuntimeError) as exc:
        raise _XlsxLineageError(f"failed to read lineage workbook: {exc}") from exc


def _dream_value_lineage_candidate(
    raw: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    child_artifact: Mapping[str, Any],
    child_rows: list[dict[str, Any]],
    source_cid: str,
    source_odor_label: str,
    manifest_hash: str,
    related_sources: Iterable[ScientificSourceResult] | None,
    rejections: list[SourceRejection],
) -> dict[str, Any] | None:
    field = "observation_tranche.value_lineage_validation"
    required_text = (
        "adapter",
        "parent_source_id",
        "parent_manifest_sha256",
        "parent_bundle_sha256",
        "parent_artifact_id",
        "parent_artifact_sha256",
        "worksheet_name",
        "source_detection_field",
        "cannot_smell_value",
        "lineage_state",
        "authority_limit",
    )
    if any(not _nonblank(raw.get(name)) for name in required_text):
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_CONTRACT_INVALID",
                "value-lineage validation is missing required fields",
                field,
            )
        )
        return None
    adapter = str(raw["adapter"]).strip()
    parent_source_id = str(raw["parent_source_id"]).strip()
    parent_manifest_hash = str(raw["parent_manifest_sha256"]).strip().casefold()
    parent_bundle_hash = str(raw["parent_bundle_sha256"]).strip().casefold()
    parent_artifact_id = str(raw["parent_artifact_id"]).strip()
    parent_artifact_hash = str(raw["parent_artifact_sha256"]).strip().casefold()
    worksheet_name = str(raw["worksheet_name"]).strip()
    detection_field = str(raw["source_detection_field"]).strip()
    cannot_smell_value = str(raw["cannot_smell_value"]).strip()
    lineage_state = str(raw["lineage_state"]).strip()
    authority_limit = str(raw["authority_limit"]).strip()
    validation_scope = str(
        raw.get("validation_scope") or "SELECTED_TRANCHE"
    ).strip()
    detail_limit = raw.get(
        "detail_limit",
        _DREAM_VALUE_LINEAGE_DEFAULT_DETAIL_LIMIT,
    )
    header_row = raw.get("header_row")
    key_field_map_raw = raw.get("key_field_map")
    response_field_map_raw = raw.get("response_field_map")
    expected_counts_raw = raw.get("expected_counts")
    key_field_map = (
        {str(key): str(value).strip() for key, value in key_field_map_raw.items()}
        if isinstance(key_field_map_raw, Mapping)
        else {}
    )
    response_field_map = (
        {
            str(key): str(value).strip()
            for key, value in response_field_map_raw.items()
        }
        if isinstance(response_field_map_raw, Mapping)
        else {}
    )
    expected_counts = (
        dict(expected_counts_raw) if isinstance(expected_counts_raw, Mapping) else {}
    )
    expected_count_fields = (
        _DREAM_VALUE_LINEAGE_FULL_CORPUS_COUNT_FIELDS
        if validation_scope == "FULL_CORPUS"
        else _DREAM_VALUE_LINEAGE_EXPECTED_COUNT_FIELDS
    )
    expected_counts_valid = (
        set(expected_counts) == set(expected_count_fields)
        and all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in expected_counts.values()
        )
    )
    contract_invalid = (
        adapter != _DREAM_VALUE_LINEAGE_ADAPTER_VERSION
        or not isinstance(header_row, int)
        or isinstance(header_row, bool)
        or header_row < 1
        or key_field_map != _DREAM_VALUE_LINEAGE_KEY_FIELD_MAP
        or response_field_map != _DREAM_VALUE_LINEAGE_RESPONSE_FIELD_MAP
        or lineage_state != _DREAM_VALUE_LINEAGE_STATE
        or validation_scope not in _DREAM_VALUE_LINEAGE_SCOPES
        or not isinstance(detail_limit, int)
        or isinstance(detail_limit, bool)
        or not 0 <= detail_limit <= _DREAM_VALUE_LINEAGE_MAX_DETAIL_LIMIT
        or not _SHA256.fullmatch(parent_manifest_hash)
        or not _SHA256.fullmatch(parent_bundle_hash)
        or not _SHA256.fullmatch(parent_artifact_hash)
        or not expected_counts_valid
    )
    if contract_invalid:
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_CONTRACT_INVALID",
                "value-lineage validation does not match the fixed adapter contract",
                field,
            )
        )
        return None

    parent_matches: list[tuple[dict[str, Any], ScientificSourceResult]] = []
    for result in tuple(related_sources or ()):
        if not result.accepted:
            continue
        for candidate_raw in result.reports.get("b1_source_candidates.json", []):
            if not isinstance(candidate_raw, Mapping):
                continue
            candidate = dict(candidate_raw)
            if str(candidate.get("source_id") or "").strip() != parent_source_id:
                continue
            if _verified_candidate_hash(
                candidate,
                hash_field="candidate_sha256",
            ) is None:
                continue
            parent_matches.append((candidate, result))
    if len(parent_matches) != 1:
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_PARENT_UNVERIFIED",
                "exactly one accepted, self-hashed related parent source is required",
                f"{field}.parent_source_id",
            )
        )
        return None
    parent_candidate, parent_result = parent_matches[0]
    parent_candidate_artifact_id = str(
        (parent_candidate.get("identifiers") or {}).get("artifact_id") or ""
    ).strip()
    parent_candidate_manifest_hash = str(
        (parent_candidate.get("default_locator") or {}).get("manifest_sha256") or ""
    ).strip().casefold()
    integrity_mismatch = (
        parent_result.manifest_hash != parent_manifest_hash
        or parent_result.bundle_hash != parent_bundle_hash
        or parent_candidate_manifest_hash != parent_manifest_hash
        or parent_candidate_artifact_id != parent_artifact_id
        or str(parent_candidate.get("artifact_sha256") or "").casefold()
        != parent_artifact_hash
    )
    parent_inventory = parent_result.reports.get("artifact_inventory.json") or {}
    parent_artifacts = (
        parent_inventory.get("artifacts", [])
        if isinstance(parent_inventory, Mapping)
        else []
    )
    matching_parent_artifacts = [
        dict(artifact)
        for artifact in parent_artifacts
        if isinstance(artifact, Mapping)
        and str(artifact.get("artifact_id") or "").strip() == parent_artifact_id
    ]
    if len(matching_parent_artifacts) != 1:
        integrity_mismatch = True
        parent_artifact: dict[str, Any] = {}
    else:
        parent_artifact = matching_parent_artifacts[0]
        integrity_mismatch = integrity_mismatch or (
            str(parent_artifact.get("verification_status") or "") != "VERIFIED"
            or str(parent_artifact.get("actual_sha256") or "").casefold()
            != parent_artifact_hash
        )
    parent_root = parent_result.source_root.resolve()
    parent_path = (parent_root / str(parent_artifact.get("path") or "")).resolve()
    if (
        integrity_mismatch
        or not _is_within(parent_path, parent_root)
        or not parent_path.is_file()
        or stable_file_hash(parent_path) != parent_artifact_hash
    ):
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_PARENT_INTEGRITY_MISMATCH",
                "related workbook identity, manifest, bundle, path, or bytes drifted",
                field,
            )
        )
        return None

    child_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for child_row in child_rows:
        key = _lineage_row_key(child_row["lineage_values"])
        if key is None or key in child_by_key:
            rejections.append(
                SourceRejection(
                    "VALUE_LINEAGE_ROW_KEY_MISMATCH",
                    "DREAM scope contains a missing or duplicate row key",
                    field,
                )
            )
            return None
        child_by_key[key] = child_row

    required_parent_headers = {
        *key_field_map.values(),
        *response_field_map.values(),
        detection_field,
    }
    try:
        parent_headers, parent_rows, parent_keyed_row_count = _xlsx_lineage_rows(
            parent_path,
            worksheet_name=worksheet_name,
            header_row=header_row,
            required_headers=required_parent_headers,
            source_cid=source_cid,
            source_odor_label=source_odor_label,
            selected_keys=(
                set(child_by_key) if validation_scope == "FULL_CORPUS" else None
            ),
        )
    except _XlsxLineageError as exc:
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_WORKBOOK_INVALID",
                str(exc),
                field,
            )
        )
        return None

    parent_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for parent_row in parent_rows:
        key = _lineage_row_key(
            parent_row["values"],
            field_map=key_field_map,
        )
        if key is None:
            continue
        if key in parent_by_key:
            rejections.append(
                SourceRejection(
                    "VALUE_LINEAGE_ROW_KEY_MISMATCH",
                    "related workbook contains a duplicate selected row key",
                    field,
                )
            )
            return None
        parent_by_key[key] = parent_row
    if set(parent_by_key) != set(child_by_key):
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_ROW_KEY_MISMATCH",
                "related workbook and DREAM validation-scope row keys differ",
                field,
            )
        )
        return None

    classification_counts = {
        name: 0
        for name in _DREAM_VALUE_LINEAGE_EXPECTED_COUNT_FIELDS
        if name not in {"matched_rows", "compared_cells"}
    }
    deterministic_recodings: list[dict[str, Any]] = []
    derivative_disambiguations: list[dict[str, Any]] = []
    incompatible_cells: list[dict[str, Any]] = []
    descriptor_fields = {
        field_name
        for field_name in response_field_map
        if field_name not in {"INTENSITY/STRENGTH", "VALENCE/PLEASANTNESS"}
    }
    for key in sorted(child_by_key):
        child_row = child_by_key[key]
        parent_row = parent_by_key[key]
        parent_values = parent_row["values"]
        child_values = child_row["lineage_values"]
        parent_strength = _decimal_from_value(
            parent_values.get(response_field_map["INTENSITY/STRENGTH"])
        )
        detection = str(parent_values.get(detection_field) or "").strip()
        for target_field, parent_field in response_field_map.items():
            parent_value = _decimal_from_value(parent_values.get(parent_field))
            child_value = _decimal_from_value(child_values.get(target_field))
            classification = "incompatible"
            if target_field == "INTENSITY/STRENGTH":
                if (
                    parent_value is None
                    and detection == cannot_smell_value
                    and child_value == Decimal(0)
                ):
                    classification = "source_blank_to_target_zero"
                elif parent_value is not None and child_value == parent_value:
                    classification = "exact_numeric"
            elif target_field == "VALENCE/PLEASANTNESS":
                if parent_value is None and child_value is None:
                    classification = "source_blank_to_target_blank"
                elif parent_value is not None and child_value == parent_value:
                    classification = "exact_numeric"
            elif target_field in descriptor_fields:
                if parent_value is None:
                    if parent_strength is None and child_value is None:
                        classification = "source_blank_to_target_blank"
                    elif parent_strength is not None and child_value == Decimal(0):
                        classification = "source_blank_to_target_zero"
                elif child_value == parent_value:
                    classification = "exact_numeric"
                elif (
                    Decimal(2) <= parent_value <= Decimal(9)
                    and parent_value == parent_value.to_integral_value()
                    and child_value == parent_value * 10
                ):
                    classification = "deterministic_trailing_zero_restoration"
                elif parent_value == Decimal(1) and child_value == Decimal(10):
                    classification = "published_derivative_one_to_ten"
                elif parent_value == Decimal(1) and child_value == Decimal(100):
                    classification = "published_derivative_one_to_hundred"
            classification_counts[classification] += 1
            detail = {
                "compound_identifier": key[0],
                "odor": key[1],
                "dilution": key[2],
                "subject_id": key[3],
                "target_field": target_field,
                "parent_field": parent_field,
                "parent_row_number": int(parent_row["row_number"]),
                "child_row_number": int(child_row["row_number"]),
                "parent_value": (
                    None if parent_value is None else _json_rating(parent_value)
                ),
                "child_value": (
                    None if child_value is None else _json_rating(child_value)
                ),
                "classification": classification,
            }
            if classification == "deterministic_trailing_zero_restoration":
                if len(deterministic_recodings) < detail_limit:
                    deterministic_recodings.append(detail)
            elif classification.startswith("published_derivative_"):
                if len(derivative_disambiguations) < detail_limit:
                    derivative_disambiguations.append(detail)
            elif classification == "incompatible":
                if not incompatible_cells:
                    incompatible_cells.append(detail)
    if incompatible_cells:
        first = incompatible_cells[0]
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_CELL_MISMATCH",
                "workbook-to-DREAM value is outside the fixed transform contract: "
                f"{first['target_field']} at child row {first['child_row_number']}",
                field,
            )
        )
        return None

    matched_rows = len(child_by_key)
    compared_cells = matched_rows * len(response_field_map)
    actual_counts = {
        "matched_rows": matched_rows,
        "compared_cells": compared_cells,
        **classification_counts,
    }
    parent_rows_outside_child_corpus = max(
        0,
        parent_keyed_row_count - matched_rows,
    )
    if validation_scope == "FULL_CORPUS":
        actual_counts.update(
            {
                "parent_keyed_rows": parent_keyed_row_count,
                "parent_rows_outside_child_corpus": (
                    parent_rows_outside_child_corpus
                ),
            }
        )
    if actual_counts != expected_counts:
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_EXPECTATION_MISMATCH",
                "recomputed value-lineage counts differ from the manifest contract",
                field,
            )
        )
        return None

    transform_contract = {
        "validation_scope": validation_scope,
        "detail_limit": detail_limit,
        "key_field_map": key_field_map,
        "response_field_map": response_field_map,
        "rules": [
            "trim keys; case-fold odor labels; compare integer CID and subject IDs",
            "missing strength plus declared cannot-smell response maps to intensity zero",
            "missing valence remains missing",
            "descriptor blanks remain missing when source strength is missing",
            "descriptor blanks map to zero when source strength is present",
            "descriptor digits two through nine map deterministically to twenty through ninety",
            "descriptor value one may map to ten or one hundred only as a published-derivative disambiguation",
        ],
    }
    transform_sha256 = stable_json_hash(transform_contract)
    identity_seed = {
        "child_manifest_sha256": manifest_hash,
        "child_artifact_sha256": child_artifact["actual_sha256"],
        "parent_manifest_sha256": parent_manifest_hash,
        "parent_bundle_sha256": parent_bundle_hash,
        "parent_artifact_sha256": parent_artifact_hash,
        "validation_scope": validation_scope,
        "observation_source_compound_identifier": source_cid,
        "transform_contract_sha256": transform_sha256,
    }
    validation_id = "lin-" + stable_json_hash(
        {"kind": "b1_value_lineage_validation_candidate", **identity_seed}
    )[:32]
    output_payload = {
        "actual_counts": actual_counts,
        "classification_counts": classification_counts,
        "deterministic_recodings": deterministic_recodings,
        "published_derivative_disambiguations": derivative_disambiguations,
        "deterministic_details_truncated": (
            classification_counts["deterministic_trailing_zero_restoration"]
            > len(deterministic_recodings)
        ),
        "published_derivative_details_truncated": (
            classification_counts["published_derivative_one_to_ten"]
            + classification_counts["published_derivative_one_to_hundred"]
            > len(derivative_disambiguations)
        ),
    }
    candidate_payload = {
        "candidate_schema_version": (
            "b1_value_lineage_validation_candidate_v2"
            if validation_scope == "FULL_CORPUS"
            else "b1_value_lineage_validation_candidate_v1"
        ),
        "validation_id": validation_id,
        "adapter": adapter,
        "child_source_id": f"{manifest['source_id']}:{child_artifact['artifact_id']}",
        "child_manifest_sha256": manifest_hash,
        "child_artifact_id": child_artifact["artifact_id"],
        "child_artifact_sha256": child_artifact["actual_sha256"],
        "parent_source_id": parent_source_id,
        "parent_source_candidate_sha256": parent_candidate["candidate_sha256"],
        "parent_manifest_sha256": parent_manifest_hash,
        "parent_bundle_sha256": parent_bundle_hash,
        "parent_artifact_id": parent_artifact_id,
        "parent_artifact_sha256": parent_artifact_hash,
        "parent_artifact_path": parent_artifact["path"],
        "parent_preserved_artifact_path": parent_artifact[
            "preserved_artifact_path"
        ],
        "parent_source_root_binding": "RUNTIME_CONTAINMENT_AND_FRESH_HASH_VERIFIED",
        "worksheet_name": worksheet_name,
        "header_row": header_row,
        "worksheet_headers": parent_headers,
        "scope": {
            "validation_scope": validation_scope,
            "source_compound_identifier": source_cid,
            "source_odor_label": source_odor_label,
        },
        "transform_contract": transform_contract,
        "transform_contract_sha256": transform_sha256,
        "matched_row_count": matched_rows,
        "compared_cell_count": compared_cells,
        "parent_keyed_row_count": parent_keyed_row_count,
        "parent_rows_outside_child_corpus": parent_rows_outside_child_corpus,
        "classification_counts": classification_counts,
        "detail_limit": detail_limit,
        "deterministic_recodings": deterministic_recodings,
        "published_derivative_disambiguations": derivative_disambiguations,
        "deterministic_details_truncated": output_payload[
            "deterministic_details_truncated"
        ],
        "published_derivative_details_truncated": output_payload[
            "published_derivative_details_truncated"
        ],
        "exact_reconstruction_without_published_derivative": not bool(
            classification_counts["published_derivative_one_to_ten"]
            + classification_counts["published_derivative_one_to_hundred"]
        ),
        "source_level_derivation_relation_allowed": False,
        "lineage_state": lineage_state,
        "authority_limit": authority_limit,
        "review_state": "UNREVIEWED",
        "workflow_state": "STAGED",
        "authority_state": "WITHHELD_UNKNOWN",
        "canonical_rows_written": 0,
        "promotion_allowed": False,
        "input_sha256": stable_json_hash(
            {**identity_seed, "transform_contract": transform_contract}
        ),
        "output_sha256": stable_json_hash(output_payload),
    }
    return _hashed_candidate(candidate_payload, hash_field="record_sha256")


def _dream_observation_reports(
    raw: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    source_root: Path,
    manifest_hash: str,
    related_sources: Iterable[ScientificSourceResult] | None,
    rejections: list[SourceRejection],
) -> dict[str, Any]:
    required_top = (
        "artifact_id",
        "source_compound_identifier",
        "source_odor_label",
        "identity_scope",
        "property_type",
        "value_kind",
        "original_unit",
        "canonical_unit",
        "authority_limit",
    )
    missing_context = [field for field in required_top if not _nonblank(raw.get(field))]
    identity = raw.get("subject_identity")
    identity_evidence = raw.get("identity_evidence")
    method_context = raw.get("method_context")
    conditions_raw = raw.get("conditions")
    if not isinstance(identity, Mapping):
        missing_context.append("subject_identity")
        identity = {}
    if not isinstance(identity_evidence, Mapping):
        missing_context.append("identity_evidence")
        identity_evidence = {}
    if not isinstance(method_context, Mapping):
        missing_context.append("method_context")
        method_context = {}
    if not isinstance(conditions_raw, list) or len(conditions_raw) != 2:
        missing_context.append("conditions[exactly_two]")
        conditions_raw = []

    identity_fields = (
        "chemical_name",
        "cas",
        "pubchem_cid",
        "comptox_dtxsid",
        "inchi_key",
    )
    missing_context.extend(
        f"subject_identity.{field}"
        for field in identity_fields
        if not _nonblank(identity.get(field))
    )
    identity_evidence_fields = (
        "pubchem_url",
        "comptox_url",
        "verification_state",
    )
    missing_context.extend(
        f"identity_evidence.{field}"
        for field in identity_evidence_fields
        if not _nonblank(identity_evidence.get(field))
    )
    method_fields = (
        "matrix",
        "phase",
        "stimulus_volume_ml",
        "method",
        "endpoint",
    )
    missing_context.extend(
        f"method_context.{field}"
        for field in method_fields
        if not _nonblank(method_context.get(field))
    )
    rating_scale = method_context.get("rating_scale")
    methods_source = method_context.get("methods_source")
    if not isinstance(rating_scale, Mapping):
        missing_context.append("method_context.rating_scale")
        rating_scale = {}
    if not isinstance(methods_source, Mapping):
        missing_context.append("method_context.methods_source")
        methods_source = {}
    missing_context.extend(
        f"method_context.rating_scale.{field}"
        for field in ("minimum", "maximum", "interface")
        if not _nonblank(rating_scale.get(field))
    )
    missing_context.extend(
        f"method_context.methods_source.{field}"
        for field in ("doi", "pmcid", "locator", "lineage_state")
        if not methods_source.get(field)
    )
    if missing_context:
        rejections.append(
            SourceRejection(
                "OBSERVATION_CONTEXT_INCOMPLETE",
                "observation tranche is missing required context: "
                + ", ".join(sorted(set(missing_context))),
                "observation_tranche",
            )
        )
        return {}

    identity_scope = str(raw["identity_scope"]).strip()
    property_type = str(raw["property_type"]).strip()
    value_kind = str(raw["value_kind"]).strip()
    source_cid = str(raw["source_compound_identifier"]).strip()
    chemical_name = str(identity["chemical_name"]).strip()
    cas_number = str(identity["cas"]).strip()
    pubchem_cid = str(identity["pubchem_cid"]).strip()
    comptox_dtxsid = str(identity["comptox_dtxsid"]).strip()
    inchi_key = str(identity["inchi_key"]).strip()
    source_odor_label = str(raw["source_odor_label"]).strip()
    invalid_identity = (
        identity_scope != "CHEMICAL_ENTITY"
        or property_type != "HUMAN_ODOR_INTENSITY_RATING"
        or value_kind != "DISTRIBUTION"
        or not _PUBCHEM_CID.fullmatch(pubchem_cid)
        or source_cid != pubchem_cid
        or not _CAS_NUMBER.fullmatch(cas_number)
        or not _COMPTOX_DTXSID.fullmatch(comptox_dtxsid)
        or not _INCHI_KEY.fullmatch(inchi_key)
        or source_odor_label.casefold() != chemical_name.casefold()
    )
    if invalid_identity:
        rejections.append(
            SourceRejection(
                "OBSERVATION_IDENTITY_MISMATCH",
                "DREAM target identity must be one exact CHEMICAL_ENTITY whose "
                "source identifier equals its PubChem CID",
                "observation_tranche.subject_identity",
            )
        )
        return {}

    scale_minimum = _decimal_from_value(rating_scale["minimum"])
    scale_maximum = _decimal_from_value(rating_scale["maximum"])
    stimulus_volume = _decimal_from_value(method_context["stimulus_volume_ml"])
    if (
        scale_minimum != Decimal(0)
        or scale_maximum != Decimal(100)
        or stimulus_volume is None
        or stimulus_volume <= 0
    ):
        rejections.append(
            SourceRejection(
                "OBSERVATION_CONTEXT_INCOMPLETE",
                "DREAM intensity staging requires a 0-100 scale and positive "
                "stimulus volume",
                "observation_tranche.method_context",
            )
        )
        return {}

    conditions: list[dict[str, Any]] = []
    condition_keys: set[tuple[str, str]] = set()
    for index, condition_raw in enumerate(conditions_raw):
        if not isinstance(condition_raw, Mapping):
            rejections.append(
                SourceRejection(
                    "OBSERVATION_CONTEXT_INCOMPLETE",
                    f"conditions[{index}] must be an object",
                    f"observation_tranche.conditions[{index}]",
                )
            )
            continue
        required = (
            "source_intensity_label",
            "source_dilution",
            "nominal_volume_fraction",
            "expected_replicate_count",
        )
        if any(not _nonblank(condition_raw.get(field)) for field in required):
            rejections.append(
                SourceRejection(
                    "OBSERVATION_CONTEXT_INCOMPLETE",
                    f"conditions[{index}] is missing a required field",
                    f"observation_tranche.conditions[{index}]",
                )
            )
            continue
        label = str(condition_raw["source_intensity_label"]).strip()
        dilution = str(condition_raw["source_dilution"]).strip()
        declared_fraction = _decimal_from_value(
            condition_raw["nominal_volume_fraction"]
        )
        parsed_fraction = _dilution_fraction(dilution)
        expected_count = condition_raw["expected_replicate_count"]
        valid_count = (
            isinstance(expected_count, int)
            and not isinstance(expected_count, bool)
            and expected_count >= 2
        )
        key = (label, dilution)
        if (
            declared_fraction is None
            or parsed_fraction is None
            or declared_fraction != parsed_fraction
            or not valid_count
            or key in condition_keys
        ):
            rejections.append(
                SourceRejection(
                    "OBSERVATION_CONTEXT_INCOMPLETE",
                    f"conditions[{index}] has an invalid or duplicate dilution contract",
                    f"observation_tranche.conditions[{index}]",
                )
            )
            continue
        condition_keys.add(key)
        conditions.append(
            {
                "source_intensity_label": label,
                "source_dilution": dilution,
                "nominal_volume_fraction": float(declared_fraction),
                "expected_replicate_count": expected_count,
            }
        )
    if rejections:
        return {}

    artifact_id = str(raw["artifact_id"]).strip()
    matching_artifacts = [
        artifact for artifact in artifacts if artifact["artifact_id"] == artifact_id
    ]
    if (
        len(matching_artifacts) != 1
        or matching_artifacts[0]["role"] != "PRIMARY_DATA"
        or matching_artifacts[0]["verification_status"] != "VERIFIED"
    ):
        rejections.append(
            SourceRejection(
                "OBSERVATION_ARTIFACT_INVALID",
                "observation adapter requires one verified PRIMARY_DATA artifact",
                "observation_tranche.artifact_id",
            )
        )
        return {}
    artifact = matching_artifacts[0]
    source_path = (source_root / str(artifact["path"])).resolve()
    if not _is_within(source_path, source_root) or not source_path.is_file():
        rejections.append(
            SourceRejection(
                "OBSERVATION_ARTIFACT_INVALID",
                "observation artifact is unavailable inside the verified source root",
                "observation_tranche.artifact_id",
            )
        )
        return {}

    value_lineage_raw = raw.get("value_lineage_validation")
    if value_lineage_raw is not None and not isinstance(value_lineage_raw, Mapping):
        rejections.append(
            SourceRejection(
                "VALUE_LINEAGE_CONTRACT_INVALID",
                "value_lineage_validation must be an object",
                "observation_tranche.value_lineage_validation",
            )
        )
        return {}
    required_columns = set(_DREAM_REQUIRED_COLUMNS)
    if value_lineage_raw is not None:
        required_columns.update(_DREAM_VALUE_LINEAGE_TARGET_COLUMNS)
    validation_scope = (
        str(value_lineage_raw.get("validation_scope") or "SELECTED_TRANCHE").strip()
        if isinstance(value_lineage_raw, Mapping)
        else "SELECTED_TRANCHE"
    )
    full_corpus_lineage_rows: list[dict[str, Any]] = []
    rows_by_condition: dict[tuple[str, str], list[dict[str, Any]]] = {
        (condition["source_intensity_label"], condition["source_dilution"]): []
        for condition in conditions
    }
    fieldnames: list[str] = []
    unexpected_conditions: set[tuple[str, str]] = set()
    source_labels: set[str] = set()
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = list(reader.fieldnames or [])
            if len(fieldnames) != len(set(fieldnames)):
                rejections.append(
                    SourceRejection(
                        "OBSERVATION_COLUMNS_INVALID",
                        "observation artifact contains duplicate column headings",
                        "observation_tranche.artifact_id",
                    )
                )
            missing_columns = sorted(required_columns - set(fieldnames))
            if missing_columns:
                rejections.append(
                    SourceRejection(
                        "OBSERVATION_COLUMNS_INVALID",
                        "observation artifact is missing columns: "
                        + ", ".join(missing_columns),
                        "observation_tranche.artifact_id",
                    )
                )
            if rejections:
                return {}
            for row in reader:
                if validation_scope == "FULL_CORPUS":
                    full_corpus_lineage_rows.append(
                        {
                            "row_number": reader.line_num,
                            "lineage_values": {
                                field: row.get(field)
                                for field in _DREAM_VALUE_LINEAGE_TARGET_COLUMNS
                            },
                        }
                    )
                if str(row.get("Compound Identifier") or "").strip() != source_cid:
                    continue
                label_in_source = str(row.get("Odor") or "").strip()
                source_labels.add(label_in_source)
                key = (
                    str(row.get("Intensity") or "").strip(),
                    str(row.get("Dilution") or "").strip(),
                )
                if key not in rows_by_condition:
                    unexpected_conditions.add(key)
                    continue
                subject_id = str(row.get("subject #") or "").strip()
                rating_raw = str(row.get("INTENSITY/STRENGTH") or "").strip()
                rating = _decimal_from_value(rating_raw)
                if (
                    not subject_id
                    or rating is None
                    or rating < scale_minimum
                    or rating > scale_maximum
                ):
                    rejections.append(
                        SourceRejection(
                            "OBSERVATION_ROW_INVALID",
                            f"invalid target rating at physical row {reader.line_num}",
                            "observation_tranche.artifact_id",
                        )
                    )
                    continue
                rows_by_condition[key].append(
                    {
                        "row_number": reader.line_num,
                        "subject_id": subject_id,
                        "rating_raw": rating_raw,
                        "rating": rating,
                        "lineage_values": {
                            field: row.get(field)
                            for field in _DREAM_VALUE_LINEAGE_TARGET_COLUMNS
                        },
                    }
                )
    except (OSError, csv.Error, UnicodeError) as exc:
        rejections.append(
            SourceRejection(
                "OBSERVATION_PARSE_FAILED",
                f"failed to parse target observation rows: {exc}",
                "observation_tranche.artifact_id",
            )
        )
        return {}

    if source_labels and {
        label.casefold() for label in source_labels
    } != {source_odor_label.casefold()}:
        rejections.append(
            SourceRejection(
                "OBSERVATION_IDENTITY_MISMATCH",
                "target source rows do not use the declared odor identity label",
                "observation_tranche.source_odor_label",
            )
        )
    if unexpected_conditions:
        rejections.append(
            SourceRejection(
                "OBSERVATION_CONDITION_MISMATCH",
                "target source rows contain undeclared conditions: "
                + repr(sorted(unexpected_conditions)),
                "observation_tranche.conditions",
            )
        )
    for condition in conditions:
        key = (
            condition["source_intensity_label"],
            condition["source_dilution"],
        )
        rows = rows_by_condition[key]
        expected_count = condition["expected_replicate_count"]
        if len(rows) != expected_count:
            rejections.append(
                SourceRejection(
                    "OBSERVATION_REPLICATE_COUNT_MISMATCH",
                    f"{key} expected {expected_count} rows, found {len(rows)}",
                    "observation_tranche.conditions",
                )
            )
        subjects = [row["subject_id"] for row in rows]
        if len(subjects) != len(set(subjects)):
            rejections.append(
                SourceRejection(
                    "OBSERVATION_DUPLICATE_SUBJECT",
                    f"{key} contains duplicate subject identifiers",
                    "observation_tranche.conditions",
                )
            )
    if rejections:
        return {}

    value_lineage_candidate: dict[str, Any] | None = None
    value_lineage_binding: dict[str, str] | None = None
    if isinstance(value_lineage_raw, Mapping):
        value_lineage_candidate = _dream_value_lineage_candidate(
            value_lineage_raw,
            manifest=manifest,
            child_artifact=artifact,
            child_rows=[
                *(
                    full_corpus_lineage_rows
                    if validation_scope == "FULL_CORPUS"
                    else [
                        row
                        for rows in rows_by_condition.values()
                        for row in rows
                    ]
                )
            ],
            source_cid=source_cid,
            source_odor_label=source_odor_label,
            manifest_hash=manifest_hash,
            related_sources=related_sources,
            rejections=rejections,
        )
        if rejections or value_lineage_candidate is None:
            return {}
        value_lineage_binding = {
            "validation_id": str(value_lineage_candidate["validation_id"]),
            "record_sha256": str(value_lineage_candidate["record_sha256"]),
        }

    conditions.sort(
        key=lambda item: (-float(item["nominal_volume_fraction"]), item["source_dilution"])
    )
    subject_identity = {str(key): value for key, value in identity.items()}
    subject_identity_sha256 = stable_json_hash(
        {
            "schema": "lab-property-identity-v1",
            "identity_scope": identity_scope,
            "subject_identity": subject_identity,
        }
    )
    source_version_candidate_id = f"{manifest['source_id']}:{artifact_id}"
    quality_flags = [
        "LIQUID_DILUTION_IS_NOT_AIRBORNE_CONCENTRATION",
        "TWO_DILUTION_LEVELS_DO_NOT_ESTABLISH_ODT_OR_DOSE_RESPONSE",
        "MOLECULE_SPECIFIC_PURITY_NOT_REPORTED_IN_TRAINSET",
        "TEMPERATURE_PRESSURE_HUMIDITY_NOT_REPORTED",
        "IDENTITY_CROSSWALK_CITED_NOT_BYTE_PINNED",
        "METHOD_CONTEXT_CITED_NOT_BYTE_PINNED",
        "NOT_VALID_FOR_OAV_SAFETY_SIMILARITY_OR_FORMULA_RELEASE",
    ]
    if value_lineage_binding is not None:
        quality_flags.extend(
            [
                "RELATED_WORKBOOK_VALUE_COMPATIBILITY_VERIFIED",
                "FULL_RECONSTRUCTION_REQUIRES_PUBLISHED_DERIVATIVE_DISAMBIGUATION",
                "SOURCE_LEVEL_DERIVATION_RELATION_WITHHELD",
            ]
        )
    extraction_candidates: list[dict[str, Any]] = []
    observation_candidates: list[dict[str, Any]] = []
    workflow_events: list[dict[str, Any]] = []
    for condition in conditions:
        key = (
            condition["source_intensity_label"],
            condition["source_dilution"],
        )
        rows = rows_by_condition[key]
        values = [row["rating"] for row in rows]
        summary = _distribution_summary(values)
        row_numbers = [int(row["row_number"]) for row in rows]
        raw_observations = [
            {
                "row_number": int(row["row_number"]),
                "subject_id": str(row["subject_id"]),
                "rating_raw": str(row["rating_raw"]),
                "rating": _json_rating(row["rating"]),
            }
            for row in rows
        ]
        locator = {
            "artifact_id": artifact_id,
            "artifact_path": artifact["preserved_artifact_path"],
            "artifact_sha256": artifact["actual_sha256"],
            "table": "TrainSet.txt",
            "row_numbers": row_numbers,
            "columns": list(_DREAM_REQUIRED_COLUMNS),
            "heading_context": fieldnames,
            "footnote_context": "NONE_PRESENT_IN_TSV",
            "filter": {
                "Compound Identifier": source_cid,
                "Odor": source_odor_label,
                "Intensity": condition["source_intensity_label"],
                "Dilution": condition["source_dilution"],
            },
        }
        condition_payload = {
            "source_intensity_label": condition["source_intensity_label"],
            "source_dilution": condition["source_dilution"],
            "nominal_volume_fraction": condition["nominal_volume_fraction"],
            "dilution_basis": "volume_fraction_as_reported_by_source",
        }
        identity_seed = {
            "manifest_sha256": manifest_hash,
            "artifact_sha256": artifact["actual_sha256"],
            "subject_identity_sha256": subject_identity_sha256,
            "property_type": property_type,
            "condition": condition_payload,
        }
        observation_id = "obs-" + stable_json_hash(
            {"kind": "b2_observation_candidate", **identity_seed}
        )[:32]
        extraction_id = "ext-" + stable_json_hash(
            {"kind": "b1_extraction_candidate", **identity_seed}
        )[:32]
        original_value = {
            "column": "INTENSITY/STRENGTH",
            "unit": str(raw["original_unit"]).strip(),
            "observations": raw_observations,
        }
        parsed_value = {
            "value_kind": value_kind,
            "unit": str(raw["canonical_unit"]).strip(),
            "summary": summary,
            "condition": condition_payload,
        }
        input_sha256 = stable_json_hash(
            {
                "artifact_sha256": artifact["actual_sha256"],
                "locator": locator,
                "original_value": original_value,
            }
        )
        output_sha256 = stable_json_hash(parsed_value)
        extraction_payload = {
            "candidate_schema_version": "b1_extraction_record_candidate_v1",
            "extraction_candidate_id": extraction_id,
            "source_version_candidate_id": source_version_candidate_id,
            "canonical_source_version_id": None,
            "source_manifest_sha256": manifest_hash,
            "locator": locator,
            "structure_context": {
                "media_type": artifact["media_type"],
                "delimiter": "tab",
                "header": fieldnames,
                "methods_source": dict(methods_source),
                **(
                    {"value_lineage_validation": value_lineage_binding}
                    if value_lineage_binding is not None
                    else {}
                ),
            },
            "original_wording": "INTENSITY/STRENGTH",
            "original_value": original_value,
            "parsed_value": parsed_value,
            "normalization": {
                "whitespace": "trimmed",
                "dilution": "parsed from source ratio to nominal volume fraction",
                "statistics": (
                    "arithmetic mean; sample standard deviation with n-1; "
                    "standard error of mean = sample SD / sqrt(n)"
                ),
                "unit_conversion": "none",
            },
            "parser_or_model_version": _DREAM_ADAPTER_VERSION,
            "reviewer_pseudonym": None,
            "review_state": "STAGED",
            "workflow_state": "PARSED",
            "uncertainty": {
                "sample_standard_deviation": summary[
                    "sample_standard_deviation"
                ],
                "standard_error_of_mean": summary["standard_error_of_mean"],
                "unit": str(raw["canonical_unit"]).strip(),
            },
            "ambiguity": quality_flags,
            "output_observation_id": observation_id,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "authority_state": "CANDIDATE_ONLY",
        }
        extraction_candidate = _hashed_candidate(
            extraction_payload,
            hash_field="record_sha256",
        )
        distribution = {
            "encoding": "subject_rating_distribution_v1",
            "rating_scale": {
                "minimum": 0,
                "maximum": 100,
                "unit": str(raw["canonical_unit"]).strip(),
            },
            "observations": raw_observations,
            "summary": summary,
        }
        observation_payload = {
            "candidate_schema_version": "b2_property_observation_candidate_v1",
            "observation_id": observation_id,
            "schema_version": "lab-property-observation-v1",
            "identity_scope": identity_scope,
            "subject_identity": subject_identity,
            "subject_identity_sha256": subject_identity_sha256,
            "identity_evidence": dict(identity_evidence),
            "property_type": property_type,
            "value_kind": value_kind,
            "numeric_value": None,
            "categorical_value": None,
            "interval_lower": None,
            "interval_upper": None,
            "distribution": distribution,
            "censoring_qualifier": None,
            "censoring_limit": None,
            "original_unit": str(raw["original_unit"]).strip(),
            "canonical_unit": str(raw["canonical_unit"]).strip(),
            "temperature_k": None,
            "pressure_pa": None,
            "relative_humidity_percent": None,
            "matrix": str(method_context["matrix"]).strip(),
            "phase": str(method_context["phase"]).strip(),
            "purity_fraction": None,
            "method": str(method_context["method"]).strip(),
            "endpoint": str(method_context["endpoint"]).strip(),
            "condition": condition_payload,
            "source_version_candidate_id": source_version_candidate_id,
            "canonical_source_version_id": None,
            "extraction_record_candidate_id": extraction_id,
            "canonical_extraction_record_id": None,
            "source_locator": locator,
            "replicate_count": len(values),
            "statistic": "subject_distribution_with_arithmetic_mean",
            "standard_uncertainty": summary["standard_error_of_mean"],
            "uncertainty_interval": {
                "kind": "STANDARD_ERROR_OF_MEAN",
                "confidence_interval": None,
            },
            "evidence_class": "LITERATURE_DERIVED",
            "review_state": "STAGED",
            "quality_flags": quality_flags,
            "applicability_domain": {
                "matrix": str(method_context["matrix"]).strip(),
                "presentation": str(method_context["phase"]).strip(),
                "stimulus_volume_ml": float(stimulus_volume),
                "nominal_liquid_dilution_only": condition_payload,
                "methods_source": dict(methods_source),
            },
            "provenance_activity": {
                "activity": "deterministic source-row aggregation",
                "parser_or_model_version": _DREAM_ADAPTER_VERSION,
                "source_manifest_sha256": manifest_hash,
                **(
                    {"value_lineage_validation": value_lineage_binding}
                    if value_lineage_binding is not None
                    else {}
                ),
            },
            "supersedes_observation_id": None,
            "required_scope": "property:human_odor_intensity_rating",
            "authority_state": "CANDIDATE_ONLY",
            "authority_limit": str(raw["authority_limit"]).strip(),
            "canonicalization_blockers": [
                "B1 source and extraction candidates lack canonical IDs",
                "B1 extraction has not been human reviewed or accepted for scope",
                "identity crosswalk evidence URLs are not pinned in this source bundle",
                "method citation bytes are not pinned in this source bundle",
                "no B2 selected assertion has been authorized",
                *(
                    [
                        "workbook-to-DREAM reconstruction requires published-derivative disambiguation"
                    ]
                    if value_lineage_binding is not None
                    else []
                ),
            ],
        }
        observation_candidate = _hashed_candidate(observation_payload)
        extraction_candidates.append(extraction_candidate)
        observation_candidates.append(observation_candidate)
        for sequence, (from_state, to_state, reason) in enumerate(
            (
                (None, "STAGED", "deterministic candidate created"),
                ("STAGED", "PARSED", "declared rows parsed without promotion"),
            ),
            start=1,
        ):
            event_payload = {
                "candidate_schema_version": "b1_workflow_event_candidate_v1",
                "target_kind": "EXTRACTION_CANDIDATE",
                "target_id": extraction_id,
                "sequence": sequence,
                "from_state": from_state,
                "to_state": to_state,
                "reviewer_pseudonym": None,
                "scoped_use": None,
                "reason": reason,
                "source_manifest_sha256": manifest_hash,
            }
            workflow_events.append(_hashed_candidate(event_payload))

    pairwise_assessments: list[dict[str, Any]] = []
    for left_index, left in enumerate(observation_candidates):
        for right in observation_candidates[left_index + 1 :]:
            pairwise_assessments.append(
                {
                    "left_observation_candidate_id": left["observation_id"],
                    "right_observation_candidate_id": right["observation_id"],
                    "state": "NOT_A_CONFLICT_DIFFERENT_CONDITIONS",
                    "differing_dimensions": [
                        "source_dilution",
                        "nominal_volume_fraction",
                    ],
                    "reason": (
                        "intensity distributions measured at different declared "
                        "liquid dilutions are separate conditions and are not averaged"
                    ),
                }
            )
    selection_seed = {
        "subject_identity_sha256": subject_identity_sha256,
        "property_type": property_type,
        "observation_candidate_ids": [
            candidate["observation_id"] for candidate in observation_candidates
        ],
    }
    selected_assertion = {
        "selected_assertion_candidate_id": "assert-none-"
        + stable_json_hash(selection_seed)[:24],
        "selection_policy_version": "staging-no-selection-v1",
        "selection_kind": "NONE",
        "selected_observation_candidate_id": None,
        "selected_model_candidate_id": None,
        "interpolation_state": "NOT_APPLICABLE",
        "authority_state": "WITHHELD_UNKNOWN",
        "authority_reason": (
            "candidates are condition-specific, unreviewed, and not linked to "
            "accepted canonical B1 records"
        ),
        "permitted_wording": (
            "Source-linked human odor-intensity rating distributions staged for "
            "review only; no ODT, OAV, safety, similarity, or release inference."
        ),
        "candidate_decisions": [
            {
                "observation_candidate_id": candidate["observation_id"],
                "decision": "EXCLUDE",
                "rationale": "not eligible for authority before scoped human review",
            }
            for candidate in observation_candidates
        ],
    }
    review_payload = {
        "candidate_schema_version": "b2_conflict_selection_review_v1",
        **selection_seed,
        "condition_partition": "nominal_liquid_volume_fraction",
        "pairwise_assessments": pairwise_assessments,
        "conflict_set_candidate": None,
        "selected_assertion_candidate": selected_assertion,
        "authority_changed": False,
        "canonical_rows_written": 0,
        "promotion_allowed": False,
    }
    reports = {
        "b1_extraction_candidates.json": extraction_candidates,
        "b1_extraction_workflow_event_candidates.json": workflow_events,
        "b2_observation_candidates.json": observation_candidates,
        "b2_conflict_selection_review.json": _hashed_candidate(review_payload),
    }
    if value_lineage_candidate is not None:
        reports["b1_value_lineage_validation_candidates.json"] = [
            value_lineage_candidate
        ]
    return reports


def _observation_tranche_reports(
    manifest: Mapping[str, Any],
    *,
    artifacts: list[dict[str, Any]],
    source_root: Path,
    manifest_hash: str,
    related_sources: Iterable[ScientificSourceResult] | None,
    rejections: list[SourceRejection],
) -> dict[str, Any]:
    raw = manifest.get("observation_tranche")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        rejections.append(
            SourceRejection(
                "OBSERVATION_TRANCHE_INVALID",
                "observation_tranche must be an object",
                "observation_tranche",
            )
        )
        return {}
    adapter = str(raw.get("adapter") or "").strip()
    if adapter != _DREAM_ADAPTER_VERSION:
        rejections.append(
            SourceRejection(
                "UNSUPPORTED_OBSERVATION_ADAPTER",
                f"unsupported observation adapter: {adapter or 'missing'}",
                "observation_tranche.adapter",
            )
        )
        return {}
    return _dream_observation_reports(
        raw,
        manifest=manifest,
        artifacts=artifacts,
        source_root=source_root,
        manifest_hash=manifest_hash,
        related_sources=related_sources,
        rejections=rejections,
    )


class ScientificSourceResult:
    def __init__(
        self,
        *,
        accepted: bool,
        status: str,
        source_id: str,
        source_root: Path,
        output_dir: Path,
        manifest_hash: str,
        bundle_hash: str,
        reports: Mapping[str, Any],
        rejections: list[SourceRejection],
    ) -> None:
        self.accepted = accepted
        self.status = status
        self.source_id = source_id
        self.source_root = source_root
        self.output_dir = output_dir
        self.manifest_hash = manifest_hash
        self.bundle_hash = bundle_hash
        self.reports = dict(reports)
        self.rejections = list(rejections)

    def write(self) -> dict[str, str]:
        """Write deterministic reports without overwriting non-identical bytes."""
        _assert_output_path(self.output_dir)
        prepared: list[tuple[str, Path, bytes]] = []
        for name, payload in sorted(self.reports.items()):
            target = (self.output_dir / name).resolve()
            if not _is_within(target, self.output_dir.resolve()):
                raise UnsafeIngestionPathError(f"report path escapes output directory: {name}")
            encoded = (
                json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            prepared.append((name, target, encoded))

        # Preflight every target before creating the directory or any report so
        # a late conflict cannot leave a partial staging bundle behind.
        for _, target, encoded in prepared:
            if target.exists() and target.read_bytes() != encoded:
                raise FileExistsError(
                    f"refusing to overwrite non-identical staging report: {target}"
                )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}
        for name, target, encoded in prepared:
            if not target.exists():
                target.write_bytes(encoded)
            written[name] = str(target)
        return written


def _source_relation_would_cycle(
    edges: Mapping[str, set[str]],
    *,
    child_source_id: str,
    parent_source_id: str,
) -> bool:
    frontier = [parent_source_id]
    visited: set[str] = set()
    while frontier:
        current = frontier.pop()
        if current == child_source_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        frontier.extend(edges.get(current, set()))
    return False


def _verified_candidate_hash(
    candidate: Mapping[str, Any],
    *,
    hash_field: str,
) -> str | None:
    declared = str(candidate.get(hash_field) or "").strip().casefold()
    if not _SHA256.fullmatch(declared):
        return None
    unhashed = dict(candidate)
    unhashed.pop(hash_field, None)
    return declared if stable_json_hash(unhashed) == declared else None


def _source_relation_reports(
    manifest: Mapping[str, Any],
    *,
    source_candidates: list[dict[str, Any]],
    manifest_hash: str,
    related_sources: Iterable[ScientificSourceResult] | None,
    rejections: list[SourceRejection],
) -> dict[str, Any]:
    raw_relations = manifest.get("source_relations")
    if raw_relations is None:
        return {}
    if not isinstance(raw_relations, list) or not raw_relations:
        rejections.append(
            SourceRejection(
                "SOURCE_RELATIONS_INVALID",
                "source_relations must be a non-empty list",
                "source_relations",
            )
        )
        return {}

    child_candidates: dict[str, dict[str, Any]] = {}
    for candidate in source_candidates:
        artifact_id = str(
            (candidate.get("identifiers") or {}).get("artifact_id") or ""
        ).strip()
        candidate_hash = _verified_candidate_hash(
            candidate,
            hash_field="candidate_sha256",
        )
        if not artifact_id or candidate_hash is None:
            rejections.append(
                SourceRejection(
                    "SOURCE_CANDIDATE_INTEGRITY_INVALID",
                    "child source candidate is missing an artifact ID or valid self-hash",
                    "b1_source_candidates",
                )
            )
            continue
        child_candidates[artifact_id] = candidate

    parent_candidates: dict[
        str,
        tuple[dict[str, Any], ScientificSourceResult],
    ] = {}
    graph: dict[str, set[str]] = {}
    for result in tuple(related_sources or ()):
        if not result.accepted:
            continue
        for candidate in result.reports.get("b1_source_candidates.json", []):
            if not isinstance(candidate, Mapping):
                continue
            normalized_candidate = dict(candidate)
            candidate_hash = _verified_candidate_hash(
                normalized_candidate,
                hash_field="candidate_sha256",
            )
            source_id = str(normalized_candidate.get("source_id") or "").strip()
            if not source_id or candidate_hash is None:
                continue
            if source_id in parent_candidates:
                rejections.append(
                    SourceRejection(
                        "SOURCE_RELATION_PARENT_AMBIGUOUS",
                        f"related source candidate is duplicated: {source_id}",
                        "source_relations",
                    )
                )
                continue
            parent_candidates[source_id] = (normalized_candidate, result)
        for relation in result.reports.get(
            "b1_source_derivation_candidates.json",
            [],
        ):
            if not isinstance(relation, Mapping):
                continue
            child_id = str(relation.get("child_source_id") or "").strip()
            parent_id = str(relation.get("parent_source_id") or "").strip()
            if child_id and parent_id:
                graph.setdefault(child_id, set()).add(parent_id)

    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for index, raw_relation in enumerate(raw_relations):
        field = f"source_relations[{index}]"
        if not isinstance(raw_relation, Mapping):
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_INVALID",
                    "source relation must be an object",
                    field,
                )
            )
            continue
        child_artifact_id = str(
            raw_relation.get("child_artifact_id") or ""
        ).strip()
        parent_source_id = str(
            raw_relation.get("parent_source_id") or ""
        ).strip()
        relation = str(raw_relation.get("relation") or "").strip().upper()
        support_scope = str(
            raw_relation.get("support_scope") or ""
        ).strip().upper()
        supported_claim_path = str(
            raw_relation.get("supported_claim_path") or ""
        ).strip()
        rationale = str(raw_relation.get("rationale") or "").strip()
        if not child_artifact_id or not parent_source_id or not rationale:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_INVALID",
                    "child_artifact_id, parent_source_id, and rationale are required",
                    field,
                )
            )
            continue
        if not support_scope or not supported_claim_path:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_SCOPE_REQUIRED",
                    "support_scope and supported_claim_path are required",
                    field,
                )
            )
            continue
        if relation not in _SOURCE_DERIVATION_RELATIONS:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_INVALID",
                    f"unsupported canonical source relation: {relation or 'missing'}",
                    f"{field}.relation",
                )
            )
            continue
        if relation not in _STAGING_SOURCE_RELATIONS:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_SEMANTICS_UNSUPPORTED",
                    "this staging slice permits CITES only; derivation requires separate evidence",
                    f"{field}.relation",
                )
            )
            continue
        child_candidate = child_candidates.get(child_artifact_id)
        if child_candidate is None:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_CHILD_NOT_FOUND",
                    f"primary child artifact is not staged: {child_artifact_id}",
                    f"{field}.child_artifact_id",
                )
            )
            continue
        parent_entry = parent_candidates.get(parent_source_id)
        if parent_entry is None:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_PARENT_NOT_STAGED",
                    f"verified related source candidate not found: {parent_source_id}",
                    f"{field}.parent_source_id",
                )
            )
            continue
        parent_candidate, parent_result = parent_entry
        child_source_id = str(child_candidate["source_id"])
        if child_source_id == parent_source_id:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_SELF_LINK",
                    "a source candidate cannot cite itself",
                    field,
                )
            )
            continue
        identity = (
            child_source_id,
            parent_source_id,
            relation,
            support_scope,
            supported_claim_path,
        )
        if identity in seen:
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_DUPLICATE",
                    "duplicate source relation candidate",
                    field,
                )
            )
            continue
        if _source_relation_would_cycle(
            graph,
            child_source_id=child_source_id,
            parent_source_id=parent_source_id,
        ):
            rejections.append(
                SourceRejection(
                    "SOURCE_RELATION_CYCLE",
                    "source relation candidate would create a cycle",
                    field,
                )
            )
            continue
        seen.add(identity)
        graph.setdefault(child_source_id, set()).add(parent_source_id)
        candidates.append(
            _hashed_candidate(
                {
                    "candidate_schema_version": (
                        "b1_source_derivation_candidate_v1"
                    ),
                    "child_source_id": child_source_id,
                    "child_source_candidate_sha256": child_candidate[
                        "candidate_sha256"
                    ],
                    "child_artifact_sha256": child_candidate["artifact_sha256"],
                    "child_manifest_sha256": manifest_hash,
                    "parent_source_id": parent_source_id,
                    "parent_source_candidate_sha256": parent_candidate[
                        "candidate_sha256"
                    ],
                    "parent_artifact_sha256": parent_candidate[
                        "artifact_sha256"
                    ],
                    "parent_manifest_sha256": parent_candidate[
                        "default_locator"
                    ]["manifest_sha256"],
                    "parent_bundle_sha256": parent_result.bundle_hash,
                    "relation": relation,
                    "support_scope": support_scope,
                    "supported_claim_path": supported_claim_path,
                    "rationale": rationale,
                    "review_state": "UNREVIEWED",
                    "workflow_state": "STAGED",
                    "authority_state": "CANDIDATE_ONLY",
                },
                hash_field="record_sha256",
            )
        )

    if rejections:
        return {}
    candidates.sort(
        key=lambda item: (
            item["child_source_id"],
            item["parent_source_id"],
            item["relation"],
            item["support_scope"],
            item["supported_claim_path"],
        )
    )
    return {"b1_source_derivation_candidates.json": candidates}


def load_scientific_source_manifest(path: str | Path) -> dict[str, Any]:
    """Load one JSON manifest as an object; validation occurs during staging."""
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("scientific source manifest must be a JSON object")
    return payload


def stage_scientific_source(
    manifest: Mapping[str, Any],
    *,
    source_root: str | Path,
    output_dir: str | Path,
    allow_fetch: bool = False,
    related_sources: Iterable[ScientificSourceResult] | None = None,
) -> ScientificSourceResult:
    """Verify exact source bytes and build deterministic staging reports.

    ``accepted`` means the source bundle is safe to stage. It never means that
    a property, threshold, regulatory rule, or scientific claim is accepted.
    """

    root = _resolved(source_root)
    output = _resolved(output_dir)
    related_source_results = tuple(related_sources or ())
    _assert_source_root(root, allow_fetch=allow_fetch)
    if output == root or _is_within(output, root):
        raise UnsafeIngestionPathError("staging output must not be inside the raw source root")

    rejections: list[SourceRejection] = []
    schema_version = str(manifest.get("schema_version", "")).strip()
    if schema_version != SCIENTIFIC_SOURCE_SCHEMA_VERSION:
        rejections.append(
            SourceRejection(
                "UNSUPPORTED_SCHEMA_VERSION",
                f"expected {SCIENTIFIC_SOURCE_SCHEMA_VERSION}, found {schema_version or 'missing'}",
                "schema_version",
            )
        )
    source_id = _text(manifest.get("source_id"), "source_id", rejections) or "UNKNOWN"
    for field in (
        "source_type",
        "title",
        "language",
        "independence_group",
    ):
        _text(manifest.get(field), field, rejections)
    review_state = str(manifest.get("review_state", "")).strip().upper()
    if review_state not in _REVIEW_STATES:
        rejections.append(
            SourceRejection(
                "INVALID_REVIEW_STATE",
                f"review_state must be one of {sorted(_REVIEW_STATES)}",
                "review_state",
            )
        )
    authors = manifest.get("authors") or []
    organization = str(manifest.get("issuing_organization") or "").strip()
    if not isinstance(authors, list) or any(not str(item).strip() for item in authors):
        rejections.append(
            SourceRejection(
                "INVALID_SOURCE_CREATOR",
                "authors must be a list of non-blank names",
                "authors",
            )
        )
        normalized_authors: list[str] = []
    else:
        normalized_authors = [str(item).strip() for item in authors]
        if len({item.casefold() for item in normalized_authors}) != len(normalized_authors):
            rejections.append(
                SourceRejection(
                    "INVALID_SOURCE_CREATOR",
                    "authors must not contain duplicates",
                    "authors",
                )
            )
    if not normalized_authors and not organization:
        rejections.append(
            SourceRejection(
                "INVALID_SOURCE_CREATOR",
                "authors or issuing_organization is required",
                "issuing_organization",
            )
        )
    identifiers = manifest.get("identifiers") or {}
    if not isinstance(identifiers, Mapping) or any(
        not str(key).strip() or not str(value).strip()
        for key, value in (
            identifiers.items() if isinstance(identifiers, Mapping) else ()
        )
    ):
        rejections.append(
            SourceRejection(
                "INVALID_IDENTIFIERS",
                "identifiers must be an object of non-blank string keys and values",
                "identifiers",
            )
        )
        normalized_identifiers: dict[str, str] = {}
    else:
        normalized_identifiers = {
            str(key).strip(): str(value).strip() for key, value in identifiers.items()
        }
    revision = _validate_revision(manifest.get("revision"), rejections)
    retrieved_at = _parse_timestamp(manifest.get("retrieved_at"), "retrieved_at", rejections)
    rights = _validate_rights(manifest.get("rights"), rejections)

    transformation = manifest.get("transformation")
    if not isinstance(transformation, Mapping):
        rejections.append(
            SourceRejection(
                "MISSING_TRANSFORMATION",
                "transformation must declare module, version, and mode",
                "transformation",
            )
        )
    else:
        for field in ("module", "version", "mode"):
            _text(
                transformation.get(field),
                f"transformation.{field}",
                rejections,
            )

    records = _artifact_records(
        manifest.get("artifacts"),
        source_root=root,
        allow_fetch=allow_fetch,
        rejections=rejections,
    )
    _validate_revision_urls(records, revision=revision, rejections=rejections)
    normalized = _normalize_manifest(
        manifest,
        artifacts=records,
        revision=revision,
        rights=rights,
        retrieved_at=retrieved_at,
    )
    normalized["review_state"] = review_state
    normalized["authors"] = normalized_authors
    normalized["issuing_organization"] = organization or None
    normalized["identifiers"] = normalized_identifiers
    try:
        manifest_hash = stable_json_hash(normalized)
    except (TypeError, ValueError):
        manifest_hash = ""
        rejections.append(
            SourceRejection(
                "NON_CANONICAL_MANIFEST",
                "manifest contains a value outside the canonical JSON contract",
                None,
            )
        )

    source_candidates: list[dict[str, Any]] = []
    observation_reports: dict[str, Any] = {}
    relation_reports: dict[str, Any] = {}
    if not rejections:
        source_candidates = _source_candidates(
            normalized,
            artifacts=records,
            manifest_hash=manifest_hash,
        )
        observation_reports = _observation_tranche_reports(
            normalized,
            artifacts=records,
            source_root=root,
            manifest_hash=manifest_hash,
            related_sources=related_source_results,
            rejections=rejections,
        )
        relation_reports = _source_relation_reports(
            normalized,
            source_candidates=source_candidates,
            manifest_hash=manifest_hash,
            related_sources=related_source_results,
            rejections=rejections,
        )
    accepted = not rejections
    reports: dict[str, Any]
    bundle_hash = ""
    if accepted:
        transformation_hash = stable_json_hash(dict(transformation or {}))
        candidate_reports = {
            "b1_source_candidates.json": source_candidates,
            **observation_reports,
            **relation_reports,
        }
        candidate_report_hashes = {
            name: stable_json_hash(payload)
            for name, payload in sorted(candidate_reports.items())
        }
        bundle_payload = {
            "schema_version": SCIENTIFIC_SOURCE_SCHEMA_VERSION,
            "manifest_sha256": manifest_hash,
            "artifact_sha256s": [
                str(record["actual_sha256"])
                for record in records
                if record["verification_status"] == "VERIFIED"
            ],
            "transformation_sha256": transformation_hash,
            "candidate_report_sha256s": candidate_report_hashes,
        }
        bundle_hash = stable_json_hash(bundle_payload)
        restricted = (
            rights["reuse_status"] == "RESTRICTED"
            or not rights["redistribution_allowed"]
        )
        status = "VERIFIED_RESTRICTED" if restricted else "VERIFIED_STAGED"
        reports = {
            "source_manifest.normalized.json": normalized,
            "artifact_inventory.json": {
                "source_id": source_id,
                "manifest_sha256": manifest_hash,
                "artifacts": records,
            },
            **candidate_reports,
            "workflow_event_candidates.json": [
                {
                    "source_id": candidate["source_id"],
                    "workflow_state": "STAGED",
                    "manifest_sha256": manifest_hash,
                    "bundle_sha256": bundle_hash,
                    "review_required": True,
                }
                for candidate in source_candidates
            ],
            "ingestion_receipt.json": {
                "schema_version": SCIENTIFIC_SOURCE_SCHEMA_VERSION,
                "source_id": source_id,
                "accepted": True,
                "status": status,
                "manifest_sha256": manifest_hash,
                "bundle_sha256": bundle_hash,
                "transformation_sha256": transformation_hash,
                "artifact_count": len(records),
                "primary_candidate_count": len(source_candidates),
                "source_relation_candidate_count": len(
                    relation_reports.get(
                        "b1_source_derivation_candidates.json",
                        [],
                    )
                ),
                "extraction_candidate_count": len(
                    observation_reports.get("b1_extraction_candidates.json", [])
                ),
                "observation_candidate_count": len(
                    observation_reports.get("b2_observation_candidates.json", [])
                ),
                "value_lineage_validation_candidate_count": len(
                    observation_reports.get(
                        "b1_value_lineage_validation_candidates.json",
                        [],
                    )
                ),
                "reuse_status": rights["reuse_status"],
                "redistribution_allowed": rights["redistribution_allowed"],
                "authority_changed": False,
                "canonical_rows_written": 0,
                "promotion_allowed": False,
                "review_required": True,
                "retrieved_at": retrieved_at,
            },
            "deterministic_hash.json": {
                "source_id": source_id,
                "manifest_sha256": manifest_hash,
                "bundle_sha256": bundle_hash,
                "candidate_report_sha256s": candidate_report_hashes,
            },
        }
    else:
        status = "REJECTED"
        reports = {
            "rejection.json": {
                "schema_version": SCIENTIFIC_SOURCE_SCHEMA_VERSION,
                "source_id": source_id,
                "accepted": False,
                "status": status,
                "authority_changed": False,
                "canonical_rows_written": 0,
                "promotion_allowed": False,
                "manifest_sha256": manifest_hash,
                "rejections": [item.to_dict() for item in rejections],
            }
        }

    return ScientificSourceResult(
        accepted=accepted,
        status=status,
        source_id=source_id,
        source_root=root,
        output_dir=output,
        manifest_hash=manifest_hash,
        bundle_hash=bundle_hash,
        reports=reports,
        rejections=rejections,
    )


__all__ = [
    "SCIENTIFIC_SOURCE_SCHEMA_VERSION",
    "SCIENTIFIC_STAGING_VERSION",
    "ScientificSourceResult",
    "SourceRejection",
    "UnsafeIngestionPathError",
    "load_scientific_source_manifest",
    "stage_scientific_source",
]
