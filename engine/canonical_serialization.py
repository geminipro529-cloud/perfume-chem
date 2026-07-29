"""Typed, versioned serialization for canonical perfume-chem records.

Only explicitly registered dataclasses and enums may cross this boundary.
Runtime type reconstruction never imports a type named by the payload.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

from engine.calibration.hashing import canonical_json_bytes

CANONICAL_ENVELOPE_SCHEMA = "canonical-envelope-v1"
_EXTENSION_NAMESPACE = re.compile(
    r"^[a-z0-9](?:[a-z0-9_-]*\.)+[a-z0-9][a-z0-9_-]*$"
)


@dataclass(frozen=True, slots=True)
class DecodedEnvelope:
    """A reconstructed canonical record and its namespaced extensions."""

    record: Any
    extensions: dict[str, Any]


class CanonicalTypeRegistry:
    """Closed registry for records and enums accepted by the boundary."""

    def __init__(self) -> None:
        self._record_by_name: dict[str, type[Any]] = {}
        self._record_by_type: dict[type[Any], str] = {}
        self._enum_by_name: dict[str, type[Enum]] = {}
        self._enum_by_type: dict[type[Enum], str] = {}

    def register_record(self, name: str, record_type: type[Any]) -> None:
        key = _type_key(name)
        if not is_dataclass(record_type):
            raise TypeError("canonical record types must be dataclasses")
        _register_pair(
            key,
            record_type,
            self._record_by_name,
            self._record_by_type,
        )

    def register_enum(self, name: str, enum_type: type[Enum]) -> None:
        key = _type_key(name)
        if not issubclass(enum_type, Enum):
            raise TypeError("canonical enum types must derive from Enum")
        _register_pair(
            key,
            enum_type,
            self._enum_by_name,
            self._enum_by_type,
        )

    def record_name(self, value_type: type[Any]) -> str:
        try:
            return self._record_by_type[value_type]
        except KeyError as exc:
            raise ValueError(
                f"unregistered record type: {value_type.__name__}"
            ) from exc

    def record_type(self, name: str) -> type[Any]:
        try:
            return self._record_by_name[name]
        except KeyError as exc:
            raise ValueError(f"unregistered record type: {name}") from exc

    def enum_name(self, value_type: type[Enum]) -> str:
        try:
            return self._enum_by_type[value_type]
        except KeyError as exc:
            raise ValueError(
                f"unregistered enum type: {value_type.__name__}"
            ) from exc

    def enum_type(self, name: str) -> type[Enum]:
        try:
            return self._enum_by_name[name]
        except KeyError as exc:
            raise ValueError(f"unregistered enum type: {name}") from exc


def serialize_record(
    record: Any,
    *,
    registry: CanonicalTypeRegistry,
    extensions: Mapping[str, Any] | None = None,
) -> bytes:
    """Serialize a registered record into deterministic canonical bytes."""

    normalized_extensions = _validate_extensions(extensions or {})
    envelope = {
        "schema_version": CANONICAL_ENVELOPE_SCHEMA,
        "record": _encode_value(record, registry),
        "extensions": _encode_value(normalized_extensions, registry),
    }
    return canonical_json_bytes(envelope)


def deserialize_record(
    payload: bytes | str | Mapping[str, Any],
    *,
    registry: CanonicalTypeRegistry,
) -> DecodedEnvelope:
    """Restore a canonical record without dynamic imports or type guessing."""

    if isinstance(payload, bytes):
        decoded = json.loads(payload.decode("utf-8"))
    elif isinstance(payload, str):
        decoded = json.loads(payload)
    elif isinstance(payload, Mapping):
        decoded = dict(payload)
    else:
        raise TypeError("canonical payload must be bytes, text, or an object")
    if not isinstance(decoded, Mapping):
        raise ValueError("canonical payload must contain an object")
    schema_version = decoded.get("schema_version")
    if schema_version != CANONICAL_ENVELOPE_SCHEMA:
        if isinstance(schema_version, str) and schema_version.startswith(
            "canonical-envelope-v"
        ):
            raise ValueError(
                f"future canonical schema is not supported: {schema_version}"
            )
        raise ValueError("unsupported canonical schema")
    unknown = set(decoded).difference(
        {"schema_version", "record", "extensions"}
    )
    if unknown:
        raise ValueError("canonical envelope contains unknown fields")
    raw_extensions = decoded.get("extensions", {})
    extensions = _decode_value(raw_extensions, registry)
    if not isinstance(extensions, dict):
        raise ValueError("canonical extensions must be an object")
    return DecodedEnvelope(
        record=_decode_value(decoded.get("record"), registry),
        extensions=_validate_extensions(extensions),
    )


def _encode_value(value: Any, registry: CanonicalTypeRegistry) -> Any:
    if isinstance(value, Enum):
        return {
            "@type": "enum",
            "enum": registry.enum_name(type(value)),
            "value": _encode_value(value.value, registry),
        }
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
            raise ValueError("decimal values must be finite")
        return {"@type": "decimal", "value": str(value)}
    if isinstance(value, UUID):
        return {"@type": "uuid", "value": str(value)}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "@type": "record",
            "record": registry.record_name(type(value)),
            "fields": {
                item.name: _encode_value(getattr(value, item.name), registry)
                for item in fields(value)
            },
        }
    if isinstance(value, tuple):
        return {
            "@type": "tuple",
            "items": [_encode_value(item, registry) for item in value],
        }
    if isinstance(value, frozenset):
        return {
            "@type": "frozenset",
            "items": _sorted_encoded(value, registry),
        }
    if isinstance(value, set):
        return {
            "@type": "set",
            "items": _sorted_encoded(value, registry),
        }
    if isinstance(value, list):
        return [_encode_value(item, registry) for item in value]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical object keys must be strings")
        return {
            key: _encode_value(item, registry)
            for key, item in value.items()
        }
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(
        f"unsupported canonical value type: {type(value).__name__}"
    )


def _decode_value(value: Any, registry: CanonicalTypeRegistry) -> Any:
    if isinstance(value, list):
        return [_decode_value(item, registry) for item in value]
    if not isinstance(value, Mapping):
        return value
    type_tag = value.get("@type")
    if type_tag is None:
        return {
            str(key): _decode_value(item, registry)
            for key, item in value.items()
        }
    if type_tag == "datetime":
        parsed = datetime.fromisoformat(
            str(value["value"]).replace("Z", "+00:00")
        )
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("datetime values must be timezone-aware")
        return parsed
    if type_tag == "date":
        return date.fromisoformat(str(value["value"]))
    if type_tag == "decimal":
        parsed_decimal = Decimal(str(value["value"]))
        if not parsed_decimal.is_finite():
            raise ValueError("decimal values must be finite")
        return parsed_decimal
    if type_tag == "uuid":
        return UUID(str(value["value"]))
    if type_tag == "enum":
        enum_type = registry.enum_type(str(value["enum"]))
        return enum_type(_decode_value(value["value"], registry))
    if type_tag == "tuple":
        return tuple(_decode_value(item, registry) for item in value["items"])
    if type_tag == "frozenset":
        return frozenset(
            _decode_value(item, registry) for item in value["items"]
        )
    if type_tag == "set":
        return set(_decode_value(item, registry) for item in value["items"])
    if type_tag == "record":
        record_type = registry.record_type(str(value["record"]))
        raw_fields = value.get("fields")
        if not isinstance(raw_fields, Mapping):
            raise ValueError("canonical record fields must be an object")
        allowed = {item.name for item in fields(record_type)}
        unknown = set(raw_fields).difference(allowed)
        if unknown:
            raise ValueError("canonical record contains unknown fields")
        field_values = {
            item.name: _decode_value(raw_fields[item.name], registry)
            for item in fields(record_type)
            if item.name in raw_fields
        }
        return record_type(**field_values)
    raise ValueError(f"unknown canonical type tag: {type_tag}")


def _sorted_encoded(
    values: set[Any] | frozenset[Any],
    registry: CanonicalTypeRegistry,
) -> list[Any]:
    encoded = [_encode_value(item, registry) for item in values]
    return sorted(encoded, key=canonical_json_bytes)


def _type_key(name: str) -> str:
    key = str(name).strip()
    if not key or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", key):
        raise ValueError("canonical type key is invalid")
    return key


def _register_pair(
    name: str,
    value_type: type[Any],
    by_name: dict[str, type[Any]],
    by_type: dict[type[Any], str],
) -> None:
    existing_type = by_name.get(name)
    existing_name = by_type.get(value_type)
    if existing_type not in (None, value_type) or existing_name not in (
        None,
        name,
    ):
        raise ValueError("canonical type registration conflicts")
    by_name[name] = value_type
    by_type[value_type] = name


def _validate_extensions(
    extensions: Mapping[str, Any],
) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    for namespace, value in extensions.items():
        if not isinstance(namespace, str) or not _EXTENSION_NAMESPACE.fullmatch(
            namespace
        ):
            raise ValueError(
                "extension namespace must be a reverse-domain-style key"
            )
        validated[namespace] = value
    return validated


__all__ = [
    "CANONICAL_ENVELOPE_SCHEMA",
    "CanonicalTypeRegistry",
    "DecodedEnvelope",
    "deserialize_record",
    "serialize_record",
]
