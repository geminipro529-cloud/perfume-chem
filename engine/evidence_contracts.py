"""Shared canonical primitives for evidence-gated scientific records."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from math import isfinite
from typing import Any, Mapping

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EvidenceBasis(str, Enum):
    """Origin class for one quantitative evidence value."""

    MEASURED = "MEASURED"
    MODELED = "MODELED"
    TRANSFERRED = "TRANSFERRED"
    UNKNOWN = "UNKNOWN"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    return " ".join(value.split())


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    digest = value.strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return digest


@dataclass(frozen=True, slots=True)
class EvidenceSourceRef:
    """Stable source identity for a measured, modeled, or transferred value."""

    source_id: str
    source_uri: str
    retrieved_on: str
    source_sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_id", _required_text(self.source_id, "source_id")
        )
        object.__setattr__(
            self, "source_uri", _required_text(self.source_uri, "source_uri")
        )
        retrieved = _required_text(self.retrieved_on, "retrieved_on")
        if not _ISO_DATE_RE.fullmatch(retrieved):
            raise ValueError("retrieved_on must use YYYY-MM-DD")
        try:
            date.fromisoformat(retrieved)
        except ValueError as exc:
            raise ValueError("retrieved_on must be a valid ISO date") from exc
        object.__setattr__(self, "retrieved_on", retrieved)
        if self.source_sha256 is not None:
            object.__setattr__(
                self,
                "source_sha256",
                _sha256(self.source_sha256, "source_sha256"),
            )

    def as_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "retrieved_on": self.retrieved_on,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class QuantitativeEvidence:
    """One value with explicit units, context, method, origin, and uncertainty."""

    value: float | None
    unit: str
    context: str
    method: str
    basis: EvidenceBasis
    source: EvidenceSourceRef | None
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "basis", EvidenceBasis(self.basis))
        object.__setattr__(self, "unit", _optional_text(self.unit, "unit"))
        object.__setattr__(
            self, "context", _optional_text(self.context, "context")
        )
        object.__setattr__(self, "method", _optional_text(self.method, "method"))

        if self.basis is EvidenceBasis.UNKNOWN:
            if self.value is not None:
                raise ValueError("UNKNOWN evidence requires value=None")
        else:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise TypeError("value must be a real number for known evidence")
            numeric_value = float(self.value)
            if not isfinite(numeric_value):
                raise ValueError("value must be finite")
            object.__setattr__(self, "value", numeric_value)
            for field_name in ("unit", "context", "method"):
                if not getattr(self, field_name):
                    raise ValueError(
                        f"{field_name} must be nonblank for known evidence"
                    )
            if not isinstance(self.source, EvidenceSourceRef):
                raise ValueError("source is required for known evidence")

        if self.source is not None and not isinstance(self.source, EvidenceSourceRef):
            raise TypeError("source must be an EvidenceSourceRef or None")
        if self.uncertainty is not None:
            if isinstance(self.uncertainty, bool) or not isinstance(
                self.uncertainty, (int, float)
            ):
                raise TypeError("uncertainty must be a real number")
            uncertainty = float(self.uncertainty)
            if not isfinite(uncertainty) or uncertainty < 0:
                raise ValueError("uncertainty must be finite and nonnegative")
            object.__setattr__(self, "uncertainty", uncertainty)

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "context": self.context,
            "method": self.method,
            "basis": self.basis.value,
            "source": None if self.source is None else self.source.as_dict(),
            "uncertainty": self.uncertainty,
        }


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _json_value(value.as_dict())
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            normalized[key] = _json_value(item)
        return normalized
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"value of type {type(value).__name__} is not JSON-compatible")


def canonical_json_bytes(value: object) -> bytes:
    """Serialize a JSON-compatible value to deterministic UTF-8 bytes."""

    try:
        payload = json.dumps(
            _json_value(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as exc:
        raise ValueError(f"value is not valid canonical JSON: {exc}") from exc
    return payload.encode("utf-8")


def sha256_hex(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for exact bytes."""

    if not isinstance(value, bytes):
        raise TypeError("sha256_hex requires bytes")
    return hashlib.sha256(value).hexdigest()


__all__ = [
    "EvidenceBasis",
    "EvidenceSourceRef",
    "QuantitativeEvidence",
    "canonical_json_bytes",
    "sha256_hex",
]
