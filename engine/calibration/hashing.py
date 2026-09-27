"""Stable identity helpers for empirical calibration records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import UUID

CANONICAL_HASH_ALGORITHM = "sha256-rfc8785-profile-v1"
PORTABLE_FILE_HASH_MATCH_ALGORITHM = (
    "sha256-exact-or-utf8-text-eol-equivalent-v1"
)
UTF8_TEXT_FILE_HASH_ALGORITHM = "sha256-utf8-lf-normalized-v1"
PORTABLE_ARTIFACT_HASH_ALGORITHM = (
    "sha256-binary-exact-or-utf8-lf-normalized-v1"
)
_PORTABLE_TEXT_SUFFIXES = frozenset(
    {".json", ".md", ".py", ".txt", ".toml", ".yaml", ".yml"}
)


@dataclass(frozen=True, slots=True)
class CanonicalHashRecord:
    """A deterministic content-addressed record with derivation metadata."""

    algorithm: str
    digest_sha256: str
    canonical_payload_sha256: str
    schema_version: str
    stable_identity_ids: tuple[str, ...]
    canonical_units: dict[str, str]
    ordered_line_ids: tuple[str, ...]
    parent_hash: str | None
    source_digests: tuple[str, ...]
    transformation_version: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "digest_sha256": self.digest_sha256,
            "canonical_payload_sha256": self.canonical_payload_sha256,
            "schema_version": self.schema_version,
            "stable_identity_ids": list(self.stable_identity_ids),
            "canonical_units": dict(self.canonical_units),
            "ordered_line_ids": list(self.ordered_line_ids),
            "parent_hash": self.parent_hash,
            "source_digests": list(self.source_digests),
            "transformation_version": self.transformation_version,
        }


def stable_formula_hash(
    formula_name: str,
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
) -> str:
    """Hash formula identity from name, raw uL rows, and dilution rows.

    Row order is intentionally ignored. Amounts are rounded to 6 decimals so
    parser float noise does not create a different identity.
    """
    dilutions = dilutions or {}
    payload = {
        "name": _norm_text(formula_name),
        "rows": [
            {
                "material": _norm_text(material),
                "raw_ul": round(float(amount or 0.0), 6),
                "dilution": round(float(dilutions.get(material, 1.0) or 1.0), 6),
            }
            for material, amount in sorted(
                ingredients_ul.items(),
                key=lambda item: _norm_text(item[0]),
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def formula_hash_from_record(formula: Mapping) -> str:
    """Hash a parsed formula record from `scripts.verify_formula_workflow`."""
    return stable_formula_hash(
        str(formula.get("name", "")),
        formula.get("ingredients_ul", {}) or {},
        formula.get("dilutions", {}) or {},
    )


def _canonical_json_value(value: Any) -> Any:
    """Normalize the JSON subset used by run manifests before hashing.

    This follows the RFC 8785 invariants relevant to repository payloads:
    deterministic object ordering, UTF-8 text, no NaN/Infinity, and integral
    floats serialized as integers.  Repository manifests do not use the edge
    numeric forms that require an ECMAScript-specific number formatter.
    """

    if isinstance(value, Enum):
        return _canonical_json_value(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime values must be timezone-aware")
        return {
            "@type": "datetime",
            "value": value.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }
    if isinstance(value, date):
        return {"@type": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Canonical JSON does not permit non-finite Decimal")
        return {"@type": "decimal", "value": str(value)}
    if isinstance(value, UUID):
        return {"@type": "uuid", "value": str(value)}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Canonical JSON object keys must be strings")
        return {
            str(key): _canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized_items = [_canonical_json_value(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )
    if isinstance(value, Path):
        raise TypeError("Canonical JSON does not permit filesystem paths")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical JSON does not permit NaN or Infinity")
        return int(value) if value.is_integer() else value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(
        f"Canonical JSON does not support {type(value).__name__}"
    )


def canonical_json_bytes(payload: Any) -> bytes:
    normalized = _canonical_json_value(payload)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_json_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


_RESULT_VOLATILE_KEYS = frozenset(
    {
        "completed_at",
        "duration_seconds",
        "elapsed_seconds",
        "generated_at",
        "generated_at_utc",
        "request_id",
        "run_id",
        "runtime_seconds",
        "started_at",
        "timestamp",
    }
)


def _scientific_result_payload(
    value: Any,
    path: tuple[str, ...] = (),
) -> Any:
    """Remove execution-only fields from one formula-gate result.

    This intentionally preserves scientific time axes and every authority
    field.  The batch runner uses it only to prove serial/parallel result
    equivalence; it does not promote the result's scientific authority.
    """

    if isinstance(value, Mapping):
        return {
            str(key): _scientific_result_payload(item, (*path, str(key)))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _RESULT_VOLATILE_KEYS
            and str(key) != "runtime_observability"
            and not (
                path
                and path[-1] == "run_evidence_contract"
                and str(key) == "artifact_sha256"
            )
        }
    if isinstance(value, (list, tuple)):
        return [
            _scientific_result_payload(item, (*path, str(index)))
            for index, item in enumerate(value)
        ]
    return value


def _result_json_bytes(value: Any) -> bytes:
    """Keep the established batch-result hash encoding byte-compatible."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def scientific_and_authority_payload_hashes(
    gate_output: Mapping[str, Any],
) -> tuple[str, str]:
    """Return both deterministic batch-result hashes from one normalization.

    Formula results are large.  Normalizing the same nested payload separately
    for the scientific and authority hashes made the parent batch process a
    serial CPU bottleneck.  Reusing the normalized object preserves the prior
    hash contract while allowing a persistent worker to calculate both hashes
    before returning its receipt.
    """

    normalized = _scientific_result_payload(gate_output)
    scientific_hash = hashlib.sha256(_result_json_bytes(normalized)).hexdigest()
    authority_fields: list[dict[str, Any]] = []

    def visit(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, Mapping):
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
                text_key = str(key)
                child_path = (*path, text_key)
                lowered = text_key.lower()
                if (
                    "authority" in lowered
                    or lowered.endswith("_state")
                    or lowered in {"status", "selection_status", "validation_state"}
                ):
                    authority_fields.append(
                        {
                            "path": ".".join(child_path),
                            "value": item,
                        }
                    )
                visit(item, child_path)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                visit(item, (*path, str(index)))

    visit(normalized)
    authority_hash = hashlib.sha256(
        _result_json_bytes(authority_fields)
    ).hexdigest()
    return scientific_hash, authority_hash


def scientific_payload_sha256(gate_output: Mapping[str, Any]) -> str:
    """Return the deterministic scientific result digest."""

    return scientific_and_authority_payload_hashes(gate_output)[0]


def authority_payload_sha256(gate_output: Mapping[str, Any]) -> str:
    """Return the deterministic authority-state result digest."""

    return scientific_and_authority_payload_hashes(gate_output)[1]


def canonical_hash_record(
    payload: Any,
    *,
    schema_version: str,
    stable_identity_ids: Iterable[str],
    canonical_units: Mapping[str, str],
    ordered_line_ids: Iterable[str],
    parent_hash: str | None,
    source_digests: Iterable[str],
    transformation_version: str,
) -> CanonicalHashRecord:
    """Hash canonical content together with its stable derivation contract."""

    identity_ids = tuple(str(item).strip() for item in stable_identity_ids)
    if not identity_ids or any(not item for item in identity_ids):
        raise ValueError("stable identity IDs must not be empty")
    sources = tuple(sorted(str(item).lower() for item in source_digests))
    for name, digest in (
        *((f"source_digests[{index}]", item) for index, item in enumerate(sources)),
        ("parent_hash", parent_hash),
    ):
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    schema = str(schema_version).strip()
    transformation = str(transformation_version).strip()
    if not schema or not transformation:
        raise ValueError(
            "schema_version and transformation_version must not be empty"
        )
    units = {
        str(name).strip(): str(unit).strip()
        for name, unit in canonical_units.items()
    }
    if not units or any(not name or not unit for name, unit in units.items()):
        raise ValueError("canonical units must contain non-empty names and units")
    line_ids = tuple(str(item).strip() for item in ordered_line_ids)
    if any(not item for item in line_ids):
        raise ValueError("ordered line IDs must not be empty")
    payload_digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    manifest = {
        "algorithm": CANONICAL_HASH_ALGORITHM,
        "schema_version": schema,
        "stable_identity_ids": list(identity_ids),
        "canonical_units": units,
        "ordered_line_ids": list(line_ids),
        "parent_hash": parent_hash,
        "source_digests": list(sources),
        "transformation_version": transformation,
        "canonical_payload_sha256": payload_digest,
    }
    digest = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    return CanonicalHashRecord(
        algorithm=CANONICAL_HASH_ALGORITHM,
        digest_sha256=digest,
        canonical_payload_sha256=payload_digest,
        schema_version=schema,
        stable_identity_ids=identity_ids,
        canonical_units=units,
        ordered_line_ids=line_ids,
        parent_hash=parent_hash,
        source_digests=sources,
        transformation_version=transformation,
    )


def stable_text_hash(value: str) -> str:
    normalized = str(value).replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stable_file_hash(path: str | Path) -> str:
    in_path = Path(path)
    with in_path.open("rb") as handle:
        file_digest = getattr(hashlib, "file_digest", None)
        if file_digest is not None:
            return file_digest(handle, "sha256").hexdigest()
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def stable_utf8_text_file_hash(path: str | Path) -> str:
    """Hash UTF-8 text after normalizing CRLF materialization to LF.

    This is for versioned text-source manifests that must reproduce across Git
    checkouts. Bare carriage returns and invalid UTF-8 fail closed; all other
    bytes, including spaces and the final-newline state, remain significant.
    """

    payload = Path(path).read_bytes()
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("text hash input must be valid UTF-8") from exc
    normalized_lf = payload.replace(b"\r\n", b"\n")
    if b"\r" in normalized_lf:
        raise ValueError("text hash input contains a bare carriage return")
    return hashlib.sha256(normalized_lf).hexdigest()


def stable_portable_file_hash(path: str | Path) -> str:
    """Hash governed artifacts reproducibly across Git text checkouts."""

    in_path = Path(path)
    if in_path.suffix.lower() in _PORTABLE_TEXT_SUFFIXES:
        return stable_utf8_text_file_hash(in_path)
    return stable_file_hash(in_path)


def portable_file_hash_matches(path: str | Path, expected_sha256: str) -> bool:
    """Match exact bytes, allowing only LF/CRLF equivalence for text files.

    Git may materialize the same normalized text blob with LF or CRLF depending
    on checkout settings. Authority manifests should remain clone-reproducible
    without treating whitespace, encoding, or content changes as equivalent.
    Binary files therefore receive exact-byte matching only; recognized UTF-8
    text extensions additionally accept the LF- and CRLF-materialized digests.
    """

    expected = str(expected_sha256).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return False
    in_path = Path(path)
    payload = in_path.read_bytes()
    candidates = {hashlib.sha256(payload).hexdigest()}
    if in_path.suffix.lower() in _PORTABLE_TEXT_SUFFIXES:
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError:
            return expected in candidates
        normalized_lf = payload.replace(b"\r\n", b"\n")
        if b"\r" in normalized_lf:
            return expected in candidates
        candidates.add(hashlib.sha256(normalized_lf).hexdigest())
        candidates.add(
            hashlib.sha256(normalized_lf.replace(b"\n", b"\r\n")).hexdigest()
        )
    return expected in candidates


def stable_files_hash(paths: Iterable[str | Path], *, root: str | Path) -> str:
    root_path = Path(root).resolve()
    manifest: list[dict[str, str]] = []
    for raw_path in sorted((Path(path) for path in paths), key=lambda p: p.as_posix()):
        path = raw_path if raw_path.is_absolute() else root_path / raw_path
        resolved = path.resolve()
        try:
            label = resolved.relative_to(root_path).as_posix()
        except ValueError:
            label = resolved.as_posix()
        manifest.append(
            {
                "path": label,
                "sha256": stable_file_hash(resolved) if resolved.is_file() else "MISSING",
            }
        )
    return stable_json_hash(manifest)


def stable_formula_definition_hash(formula: Mapping) -> str:
    """V2 formula identity including semantic prose and stock-basis declarations.

    The v1 calibration hash above intentionally remains unchanged so existing
    wear-test records keep their identity.
    """

    ingredients = formula.get("ingredients_ul", {}) or {}
    dilutions = formula.get("dilutions", {}) or {}
    stock_specs = formula.get("stock_specs", {}) or {}
    rows = []
    for material, amount in sorted(
        ingredients.items(), key=lambda item: _norm_text(item[0])
    ):
        spec = dict(stock_specs.get(material, {}) or {})
        rows.append(
            {
                "material": _norm_text(material),
                "raw_ul": round(float(amount or 0.0), 6),
                "dilution": round(float(dilutions.get(material, 1.0) or 1.0), 6),
                "stock": {
                    "fraction": round(float(spec.get("fraction", dilutions.get(material, 1.0)) or 0.0), 6),
                    "fraction_basis": str(spec.get("fraction_basis", "unspecified")),
                    "carrier": _norm_text(str(spec.get("carrier", ""))),
                    "approximate": bool(spec.get("approximate", False)),
                    "declared": bool(spec.get("declared", material in dilutions)),
                    "conflict": bool(spec.get("conflict", False)),
                },
            }
        )
    body = str(formula.get("body", "") or "").replace("\r\n", "\n").replace("\r", "\n")
    body = "\n".join(line.rstrip() for line in body.strip().splitlines())
    return stable_json_hash(
        {
            "schema": "perfume_formula_definition_v2",
            "name": _norm_text(str(formula.get("name", ""))),
            "number": int(formula.get("number", 1) or 1),
            "family_archetype": str(formula.get("family_archetype", "") or ""),
            "body": body,
            "rows": rows,
        }
    )


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())
