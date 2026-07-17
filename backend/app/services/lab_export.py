"""Deterministic laboratory workspace export and idempotent import."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class ImportConflictError(ValueError):
    """Raised when an exported UUID already exists with different content."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    inserted: int
    skipped: int

    def as_dict(self) -> dict[str, int]:
        return {"inserted": self.inserted, "skipped": self.skipped}


_FORMAT_REVISION = "lab-export-v1"
_TABLE_ORDER = (
    "lab_evidence_records",
    "lab_materials",
    "lab_material_aliases",
    "lab_material_properties",
    "lab_restrictions",
    "lab_constituents",
    "lab_stock_solutions",
    "lab_formulas",
    "lab_formula_versions",
    "lab_formula_components",
    "lab_batches",
    "lab_bottles",
    "lab_bottle_events",
    "lab_bottle_event_effects",
    "lab_inventory_movements",
    "lab_bottle_measurements",
    "lab_experiments",
    "lab_samples",
    "lab_applications",
    "lab_observations",
    "lab_pairwise_comparisons",
    "lab_predictions",
    "lab_outcomes",
)


class LabExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export_workspace(self) -> dict[str, Any]:
        tables: dict[str, list[dict[str, Any]]] = {}
        for table_name in _TABLE_ORDER:
            table = Base.metadata.tables[table_name]
            ordering = _ordering_columns(table_name, table)
            result = await self.session.execute(select(table).order_by(*ordering))
            tables[table_name] = [
                _serialize_row(dict(row._mapping)) for row in result
            ]
        return {
            "format_revision": _FORMAT_REVISION,
            "schema_revision": await self._schema_revision(),
            "ordering_contract": {
                "formula_versions": ["formula_id", "version_number", "id"],
                "bottle_events": ["bottle_id", "stream_sequence", "id"],
                "default": ["id"],
            },
            "unit_contract": {
                "mass_g": "g",
                "measured_volume_ul": "uL",
                "elapsed_seconds": "s",
                "density_g_ml": "g/mL",
                "concentration_fraction": "dimensionless_with_explicit_basis",
            },
            "provenance_contract": {
                "evidence": "lab_evidence_records",
                "formula_source": "lab_formula_versions.source_json",
                "prediction_version": ["model_key", "model_version"],
            },
            "tables": tables,
        }

    async def canonical_bytes(self) -> bytes:
        return json.dumps(
            await self.export_workspace(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    async def import_workspace(self, packet: Mapping[str, Any]) -> ImportResult:
        if packet.get("format_revision") != _FORMAT_REVISION:
            raise ValueError("unsupported laboratory export revision")
        incoming_tables = packet.get("tables")
        if not isinstance(incoming_tables, Mapping):
            raise ValueError("laboratory export tables must be an object")
        unknown = set(incoming_tables).difference(_TABLE_ORDER)
        if unknown:
            raise ValueError("laboratory export contains unknown tables")

        owns_transaction = not self.session.in_transaction()
        if owns_transaction:
            await self.session.begin()
        inserted = 0
        skipped = 0
        try:
            for table_name in _TABLE_ORDER:
                rows = incoming_tables.get(table_name, [])
                if not isinstance(rows, list):
                    raise ValueError(f"export table {table_name} must be an array")
                table = Base.metadata.tables[table_name]
                for incoming in rows:
                    if not isinstance(incoming, Mapping) or not incoming.get("id"):
                        raise ValueError(f"export table {table_name} contains an invalid row")
                    row_id = str(incoming["id"])
                    existing = (
                        await self.session.execute(
                            select(table).where(table.c.id == row_id)
                        )
                    ).first()
                    normalized_incoming = _serialize_row(dict(incoming))
                    if existing is not None:
                        normalized_existing = _serialize_row(dict(existing._mapping))
                        if normalized_existing != normalized_incoming:
                            raise ImportConflictError(
                                f"UUID conflict in {table_name}: {row_id}"
                            )
                        skipped += 1
                        continue
                    values = _deserialize_row(table, incoming)
                    await self.session.execute(table.insert().values(**values))
                    inserted += 1
            if owns_transaction:
                await self.session.commit()
        except BaseException:
            if owns_transaction:
                await self.session.rollback()
            raise
        return ImportResult(inserted=inserted, skipped=skipped)

    async def _schema_revision(self) -> str:
        bind = self.session.get_bind()
        if bind.dialect.name != "sqlite":
            return "unknown"
        exists = await self.session.scalar(
            text(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name='alembic_version'"
            )
        )
        if not exists:
            return "unversioned"
        revision = await self.session.scalar(text("SELECT version_num FROM alembic_version"))
        return str(revision or "unversioned")


def _ordering_columns(table_name: str, table):
    if table_name == "lab_formula_versions":
        return (table.c.formula_id, table.c.version_number, table.c.id)
    if table_name == "lab_formula_components":
        return (table.c.formula_version_id, table.c.position, table.c.id)
    if table_name == "lab_bottle_events":
        return (table.c.bottle_id, table.c.stream_sequence, table.c.id)
    if table_name == "lab_observations":
        return (table.c.application_id, table.c.elapsed_seconds, table.c.id)
    return (table.c.id,)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            serialized[str(key)] = value.astimezone(timezone.utc).isoformat()
        else:
            serialized[str(key)] = value
    return serialized


def _deserialize_row(table, row: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in table.columns:
        if column.name not in row:
            continue
        value = row[column.name]
        if value is not None and column.name in {"created_at", "applied_at"}:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            value = parsed
        values[column.name] = value
    return values


__all__ = ["ImportConflictError", "ImportResult", "LabExportService"]
