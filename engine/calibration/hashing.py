"""Stable identity helpers for empirical calibration records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


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

    if isinstance(value, Mapping):
        return {
            str(key): _canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical JSON does not permit NaN or Infinity")
        return int(value) if value.is_integer() else value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


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


def stable_text_hash(value: str) -> str:
    normalized = str(value).replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stable_file_hash(path: str | Path) -> str:
    in_path = Path(path)
    digest = hashlib.sha256()
    with in_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
