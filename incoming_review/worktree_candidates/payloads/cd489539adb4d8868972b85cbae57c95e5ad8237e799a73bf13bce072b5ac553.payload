"""Deterministic, exact-decimal serialization helpers.

This module deliberately supports a restricted canonical JSON subset. Decimal
values are encoded as canonical strings so binary floating-point cannot cross
an authority boundary unnoticed.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot enter the exact authority boundary."""


def parse_decimal(value: Decimal | str | int) -> Decimal:
    """Parse an exact decimal and reject binary floats and booleans.

    Integers are accepted because their decimal representation is exact.
    """

    if isinstance(value, bool):
        raise CanonicalizationError("boolean is not an exact numeric quantity")
    if isinstance(value, float):
        raise CanonicalizationError(
            "binary float rejected at authority boundary; provide a decimal string"
        )
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except (InvalidOperation, ValueError) as exc:
            raise CanonicalizationError(f"invalid decimal string: {value!r}") from exc
    else:
        raise CanonicalizationError(f"unsupported exact numeric type: {type(value)!r}")
    if not result.is_finite():
        raise CanonicalizationError("non-finite decimal is prohibited")
    return result


def canonical_decimal(value: Decimal | str | int) -> str:
    """Return a stable non-exponent decimal representation."""

    number = parse_decimal(value)
    if number == 0:
        return "0"
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def canonicalize(value: Any) -> Any:
    """Convert supported values into a deterministically serializable tree."""

    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if is_dataclass(value):
        return canonicalize(asdict(value))
    if isinstance(value, dict):
        return {str(key): canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, float):
        raise CanonicalizationError(
            "binary float rejected during canonicalization; use Decimal or string"
        )
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise CanonicalizationError(f"unsupported canonical type: {type(value)!r}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a canonical tree using stable UTF-8 JSON."""

    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_payload(value: Any, *, domain: str) -> str:
    """Hash a payload under an explicit domain separator."""

    if not domain.strip():
        raise CanonicalizationError("hash domain must be non-empty")
    digest = hashlib.sha256()
    digest.update(domain.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(canonical_json_bytes(value))
    return digest.hexdigest()


def sha256_file(path: str | Path) -> str:
    """Hash a file without interpreting its contents."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
