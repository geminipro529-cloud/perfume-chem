"""Validated runtime provider for normalized V5 inventory snapshots.

This provider intentionally does not parse free-text inventory descriptions or
workbook prose. It accepts only a normalized, provenance-bearing packet and
constructs the canonical :class:`V5InventorySnapshot` used by the stock
authority spine.

The private workbook bytes do not need to be committed to the repository. A
local/tunnel ingestion step may export a normalized JSON packet, but the packet
must bind the exact V5 filename, SHA-256, sheet, and typed record fields.

ExactStockRef is deliberately rejected here because physical bottle/preparation
binding is downstream of the immutable V5 inventory snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from engine.pipeline.stock_authority_spine import (
    V5_AUTHORITY_FILENAME,
    V5_AUTHORITY_SHA256,
    StockAuthorityError,
    V5InventorySnapshot,
    V5StockRecord,
)


SNAPSHOT_INPUT_SCHEMA = "v5-inventory-snapshot-input-v1"

_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "authority_filename",
        "authority_sha256",
        "authority_sheet",
        "records",
    }
)

_RECORD_FIELDS = frozenset(
    {
        "material",
        "stock_description",
        "active_fraction",
        "fraction_basis",
        "carrier",
        "inventory_owned",
        "product_basis",
        "source_row",
    }
)

_REQUIRED_RECORD_FIELDS = _RECORD_FIELDS


class V5SnapshotProviderError(ValueError):
    """Raised when a runtime V5 snapshot packet is not authority-safe."""


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V5SnapshotProviderError(f"{label} must be a mapping")
    return value


def _require_exact_fields(
    mapping: Mapping[str, Any],
    *,
    allowed: frozenset[str],
    required: frozenset[str],
    label: str,
) -> None:
    keys = {str(key) for key in mapping.keys()}
    missing = sorted(required - keys)
    unknown = sorted(keys - allowed)
    if missing:
        raise V5SnapshotProviderError(
            f"{label} missing required field(s): " + ", ".join(missing)
        )
    if unknown:
        raise V5SnapshotProviderError(
            f"{label} contains unsupported field(s): " + ", ".join(unknown)
        )


def _record_from_mapping(raw: object, *, index: int) -> V5StockRecord:
    row = _mapping(raw, label=f"records[{index}]")
    _require_exact_fields(
        row,
        allowed=_RECORD_FIELDS,
        required=_REQUIRED_RECORD_FIELDS,
        label=f"records[{index}]",
    )

    owned = row.get("inventory_owned")
    product_basis = row.get("product_basis")
    if not isinstance(owned, bool):
        raise V5SnapshotProviderError(
            f"records[{index}].inventory_owned must be an explicit boolean"
        )
    if not isinstance(product_basis, bool):
        raise V5SnapshotProviderError(
            f"records[{index}].product_basis must be an explicit boolean"
        )

    try:
        source_row = int(row.get("source_row"))
    except (TypeError, ValueError) as exc:
        raise V5SnapshotProviderError(
            f"records[{index}].source_row must be a positive integer"
        ) from exc
    if source_row <= 0 or isinstance(row.get("source_row"), bool):
        raise V5SnapshotProviderError(
            f"records[{index}].source_row must be a positive integer"
        )

    try:
        return V5StockRecord(
            material=str(row.get("material") or "").strip(),
            stock_description=str(row.get("stock_description") or "").strip(),
            active_fraction=row.get("active_fraction"),
            fraction_basis=str(row.get("fraction_basis") or "").strip(),
            carrier=str(row.get("carrier") or "").strip(),
            inventory_owned=owned,
            product_basis=product_basis,
            source_row=source_row,
        )
    except StockAuthorityError as exc:
        raise V5SnapshotProviderError(
            f"records[{index}] failed V5 stock validation: {exc}"
        ) from exc


def snapshot_from_mapping(payload: Mapping[str, Any]) -> V5InventorySnapshot:
    """Validate one normalized packet and return an immutable V5 snapshot."""

    root = _mapping(payload, label="snapshot payload")
    _require_exact_fields(
        root,
        allowed=_TOP_LEVEL_FIELDS,
        required=_TOP_LEVEL_FIELDS,
        label="snapshot payload",
    )

    if str(root.get("schema") or "").strip() != SNAPSHOT_INPUT_SCHEMA:
        raise V5SnapshotProviderError(
            f"snapshot schema must be {SNAPSHOT_INPUT_SCHEMA}"
        )
    if str(root.get("authority_filename") or "").strip() != V5_AUTHORITY_FILENAME:
        raise V5SnapshotProviderError(
            "snapshot authority_filename does not match canonical V5 workbook"
        )
    if str(root.get("authority_sha256") or "").strip().lower() != V5_AUTHORITY_SHA256:
        raise V5SnapshotProviderError(
            "snapshot authority_sha256 does not match canonical V5 workbook"
        )
    authority_sheet = str(root.get("authority_sheet") or "").strip()
    if not authority_sheet:
        raise V5SnapshotProviderError("snapshot authority_sheet must not be blank")

    raw_records = root.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise V5SnapshotProviderError("snapshot records must be a non-empty list")

    records = tuple(
        _record_from_mapping(raw, index=index)
        for index, raw in enumerate(raw_records)
    )
    try:
        return V5InventorySnapshot.build(
            authority_filename=V5_AUTHORITY_FILENAME,
            authority_sha256=V5_AUTHORITY_SHA256,
            authority_sheet=authority_sheet,
            records=records,
        )
    except StockAuthorityError as exc:
        raise V5SnapshotProviderError(
            f"snapshot failed V5 authority validation: {exc}"
        ) from exc


def load_v5_snapshot_json(path: str | Path) -> V5InventorySnapshot:
    """Load a normalized V5 JSON packet from disk and apply full validation."""

    source = Path(path)
    try:
        raw_text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise V5SnapshotProviderError(
            f"unable to read V5 snapshot JSON: {source}"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise V5SnapshotProviderError(
            f"invalid V5 snapshot JSON: {source}"
        ) from exc
    return snapshot_from_mapping(_mapping(payload, label="snapshot JSON root"))
