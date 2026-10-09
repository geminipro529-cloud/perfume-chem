"""Deterministic laboratory workspace export and idempotent import."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine import user_records
from sqlalchemy import Date, DateTime, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class ImportConflictError(ValueError):
    """Raised when an exported UUID or stock record already exists with different content."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    inserted: int
    skipped: int
    records_written: int = 0
    records_already_present: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "inserted": self.inserted,
            "skipped": self.skipped,
            "records_written": self.records_written,
            "records_already_present": self.records_already_present,
        }


RecordPaths = Callable[[], Mapping[str, Path]]
_RECORD_NAMES = (
    user_records.ADDITION_LOG_NAME,
    user_records.COMPLETION_LOG_NAME,
    user_records.BASKET_LOG_NAME,
    user_records.DILUTION_LOG_NAME,
)
_RECORD_TEMP_SUFFIX = ".import-tmp"


_PLANNING_FORMAT_REVISION = "lab-export-v2"
_SCIENCE_FORMAT_REVISION = "lab-export-v3"
_FORMAT_REVISION = "lab-export-v4"
_EXTERNAL_VALIDATION_FORMAT_REVISION = "lab-export-v5"
CURRENT_WRITE_REVISION = _EXTERNAL_VALIDATION_FORMAT_REVISION
_SUPPORTED_REVISIONS = {
    "lab-export-v1",
    _PLANNING_FORMAT_REVISION,
    _SCIENCE_FORMAT_REVISION,
    _FORMAT_REVISION,
    _EXTERNAL_VALIDATION_FORMAT_REVISION,
}
_V1_TABLE_ORDER = (
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
_PLANNING_TABLE_ORDER = (
    "lab_target_hypothesis_versions",
    "lab_target_lines",
    "lab_target_evidence_links",
    "lab_accepted_target_versions",
    "lab_formula_version_edges",
    "lab_inventory_mapping_versions",
    "lab_inventory_mapping_evidence_links",
    "lab_build_plan_versions",
    "lab_build_plan_lines",
    "lab_build_plan_evidence_links",
    "lab_inventory_reservation_events",
)
_SCIENCE_AUTHORITY_TABLE_ORDER = (
    "lab_analytical_method_versions",
    "lab_analytical_runs",
    "lab_analytical_peaks",
    "lab_analytical_qc_records",
    "lab_analytical_attachments",
    "lab_gco_events",
    "lab_regulatory_assessment_versions",
    "lab_regulatory_findings",
    "lab_claim_assessment_versions",
    "lab_claim_assessment_evidence_links",
)
_V2_TABLE_ORDER = _V1_TABLE_ORDER + _PLANNING_TABLE_ORDER
_V3_TABLE_ORDER = _V2_TABLE_ORDER + _SCIENCE_AUTHORITY_TABLE_ORDER
_EXECUTION_PREFIX_TABLE_ORDER = (
    "lab_bottle_action_proposals",
    "lab_bottle_action_confirmations",
)
_EXECUTION_SUFFIX_TABLE_ORDER = ("lab_bottle_action_commits",)
_V4_TABLE_ORDER = (
    tuple(
        table_name
        for table_name in _V1_TABLE_ORDER
        if table_name != "lab_bottle_measurements"
    )
    + _PLANNING_TABLE_ORDER
    + _EXECUTION_PREFIX_TABLE_ORDER
    + ("lab_bottle_measurements",)
    + _EXECUTION_SUFFIX_TABLE_ORDER
    + _SCIENCE_AUTHORITY_TABLE_ORDER
)
_POST_V4_DURABILITY_TABLE_ORDER = (
    "lab_build_plan_physical_bindings",
    "lab_stock_preparation_receipts",
    "lab_build_plan_line_physical_bindings",
    "lab_compounding_runs",
    "lab_compounding_command_receipts",
    "lab_engine_jobs",
    "lab_engine_job_events",
    "lab_engine_job_results",
    "lab_external_validation_records",
)
_V5_TABLE_ORDER = _V4_TABLE_ORDER + _POST_V4_DURABILITY_TABLE_ORDER
_TABLES_BY_REVISION = {
    "lab-export-v1": _V1_TABLE_ORDER,
    _PLANNING_FORMAT_REVISION: _V2_TABLE_ORDER,
    _SCIENCE_FORMAT_REVISION: _V3_TABLE_ORDER,
    _FORMAT_REVISION: _V4_TABLE_ORDER,
    _EXTERNAL_VALIDATION_FORMAT_REVISION: _V5_TABLE_ORDER,
}
_NEXT_REVISION = {
    "lab-export-v1": _PLANNING_FORMAT_REVISION,
    _PLANNING_FORMAT_REVISION: _SCIENCE_FORMAT_REVISION,
    _SCIENCE_FORMAT_REVISION: _FORMAT_REVISION,
    _FORMAT_REVISION: _EXTERNAL_VALIDATION_FORMAT_REVISION,
}
_ALLOWED_TOP_LEVEL_FIELDS = {
    "format_revision",
    "schema_revision",
    "ordering_contract",
    "unit_contract",
    "provenance_contract",
    "tables",
    "extensions",
    "records",
}


def migrate_export_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate every supported export through explicit sequential revisions."""

    unknown_fields = set(packet).difference(_ALLOWED_TOP_LEVEL_FIELDS)
    if unknown_fields:
        raise ValueError("unknown top-level export field")
    revision = packet.get("format_revision")
    if revision not in _SUPPORTED_REVISIONS:
        if isinstance(revision, str) and revision.startswith("lab-export-v"):
            raise ValueError(
                f"unknown future laboratory export revision: {revision}"
            )
        raise ValueError("unsupported laboratory export revision")
    migrated = deepcopy(dict(packet))
    tables = migrated.get("tables")
    if not isinstance(tables, Mapping):
        raise ValueError("laboratory export tables must be an object")
    allowed_source_tables = _TABLES_BY_REVISION[str(revision)]
    if set(tables).difference(allowed_source_tables):
        raise ValueError("laboratory export contains unknown tables")
    migrated["tables"] = {
        str(name): deepcopy(rows) for name, rows in tables.items()
    }
    while revision != CURRENT_WRITE_REVISION:
        next_revision = _NEXT_REVISION[str(revision)]
        for table_name in _TABLES_BY_REVISION[next_revision]:
            migrated["tables"].setdefault(table_name, [])
        revision = next_revision
        migrated["format_revision"] = revision
    migrated["tables"] = {
        table_name: migrated["tables"].get(table_name, [])
        for table_name in _V5_TABLE_ORDER
    }
    return migrated


class LabExportService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        record_paths: RecordPaths = user_records.record_files,
    ) -> None:
        self.session = session
        self.record_paths = record_paths

    async def export_workspace(
        self,
        *,
        format_revision: str = "lab-export-v1",
        include_records: bool = True,
    ) -> dict[str, Any]:
        """Write the database tables and, by default, the personal stock records.

        ``records`` holds each standard record file by name: null when the file
        does not exist, otherwise its sha256, byte size and base64 content.  The
        partial exports below leave the records out.
        """

        if format_revision not in _SUPPORTED_REVISIONS:
            raise ValueError("unsupported laboratory export revision")
        table_order: tuple[str, ...]
        if format_revision == "lab-export-v1":
            table_order = _V1_TABLE_ORDER
        elif format_revision == _PLANNING_FORMAT_REVISION:
            table_order = _V2_TABLE_ORDER
        elif format_revision == _SCIENCE_FORMAT_REVISION:
            table_order = _V3_TABLE_ORDER
        elif format_revision == _FORMAT_REVISION:
            table_order = _V4_TABLE_ORDER
        else:
            table_order = _V5_TABLE_ORDER
        tables: dict[str, list[dict[str, Any]]] = {}
        for table_name in table_order:
            table = Base.metadata.tables[table_name]
            ordering = _ordering_columns(table_name, table)
            statement = select(table)
            if (
                table_name == "lab_bottle_measurements"
                and format_revision
                not in {_FORMAT_REVISION, _EXTERNAL_VALIDATION_FORMAT_REVISION}
            ):
                statement = statement.where(table.c.proposal_id.is_(None))
            result = await self.session.execute(
                statement.order_by(*ordering)
            )
            rows = [_serialize_row(dict(row._mapping)) for row in result]
            if (
                table_name == "lab_bottle_measurements"
                and format_revision
                not in {_FORMAT_REVISION, _EXTERNAL_VALIDATION_FORMAT_REVISION}
            ):
                for row in rows:
                    for field in (
                        "proposal_id",
                        "method",
                        "measured_at",
                        "actor",
                    ):
                        row.pop(field, None)
            tables[table_name] = rows
        packet: dict[str, Any] = {
            "format_revision": format_revision,
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
        if format_revision in {
            _PLANNING_FORMAT_REVISION,
            _SCIENCE_FORMAT_REVISION,
            _FORMAT_REVISION,
            _EXTERNAL_VALIDATION_FORMAT_REVISION,
        }:
            packet["ordering_contract"].update(
                {
                    "target_versions": [
                        "target_id",
                        "version_number",
                        "id",
                    ],
                    "target_lines": [
                        "target_hypothesis_version_id",
                        "position",
                        "id",
                    ],
                    "mapping_versions": [
                        "mapping_id",
                        "version_number",
                        "id",
                    ],
                    "build_plan_versions": [
                        "plan_id",
                        "version_number",
                        "id",
                    ],
                    "build_plan_lines": [
                        "build_plan_version_id",
                        "position",
                        "id",
                    ],
                    "reservation_events": [
                        "reservation_id",
                        "sequence",
                        "id",
                    ],
                }
            )
            packet["unit_contract"].update(
                {
                    "planning_quantity": (
                        "explicit_unit_and_concentration_basis"
                    ),
                    "reservation_mass_g": "g",
                }
            )
            packet["provenance_contract"].update(
                {
                    "target_evidence": "lab_target_evidence_links",
                    "mapping_evidence": (
                        "lab_inventory_mapping_evidence_links"
                    ),
                    "build_plan_evidence": (
                        "lab_build_plan_evidence_links"
                    ),
                    "inventory_snapshot": (
                        "lab_build_plan_versions.inventory_snapshot_ref"
                    ),
                    "content_hashes": "stable_json_hash",
                }
            )
        if format_revision in {
            _SCIENCE_FORMAT_REVISION,
            _FORMAT_REVISION,
            _EXTERNAL_VALIDATION_FORMAT_REVISION,
        }:
            packet["ordering_contract"].update(
                {
                    "analytical_method_versions": [
                        "method_id",
                        "version_number",
                        "id",
                    ],
                    "analytical_runs": ["run_id", "id"],
                    "analytical_peaks": [
                        "analytical_run_id",
                        "retention_time_minutes",
                        "peak_key",
                        "id",
                    ],
                    "analytical_qc_records": [
                        "analytical_run_id",
                        "qc_key",
                        "id",
                    ],
                    "gco_events": [
                        "analytical_run_id",
                        "retention_time_minutes",
                        "event_key",
                        "id",
                    ],
                    "regulatory_assessment_versions": [
                        "assessment_id",
                        "version_number",
                        "id",
                    ],
                    "regulatory_findings": [
                        "regulatory_assessment_version_id",
                        "finding_key",
                        "id",
                    ],
                    "claim_assessment_versions": [
                        "claim_id",
                        "version_number",
                        "id",
                    ],
                    "claim_evidence_links": [
                        "claim_assessment_version_id",
                        "role",
                        "evidence_record_id",
                        "id",
                    ],
                }
            )
            packet["unit_contract"].update(
                {
                    "retention_time_minutes": "min",
                    "retention_index": "dimensionless",
                    "analytical_quantity": "explicit_quantity_unit_and_basis",
                    "finished_product_concentration": (
                        "explicit_concentration_basis"
                    ),
                }
            )
            packet["provenance_contract"].update(
                {
                    "analytical_method_evidence": (
                        "lab_analytical_method_versions.evidence_record_id"
                    ),
                    "analytical_attachments": (
                        "digest_metadata_only_no_embedded_bytes"
                    ),
                    "regulatory_source_evidence": (
                        "lab_regulatory_assessment_versions."
                        "source_evidence_record_id"
                    ),
                    "claim_evidence": (
                        "lab_claim_assessment_evidence_links"
                    ),
                    "legacy_authority_vector": "not_canonical_not_exported",
                }
            )
        if format_revision in {
            _FORMAT_REVISION,
            _EXTERNAL_VALIDATION_FORMAT_REVISION,
        }:
            packet["ordering_contract"].update(
                {
                    "bottle_action_proposals": [
                        "reservation_id",
                        "created_at",
                        "id",
                    ],
                    "bottle_action_confirmations": ["proposal_id", "id"],
                    "bottle_action_measurements": [
                        "proposal_id",
                        "quantity_kind",
                        "id",
                    ],
                    "bottle_action_commits": ["proposal_id", "id"],
                }
            )
            packet["unit_contract"]["action_mass"] = "g"
            packet["provenance_contract"].update(
                {
                    "physical_action": "lab_bottle_action_proposals",
                    "human_confirmation": (
                        "lab_bottle_action_confirmations"
                    ),
                    "physical_measurement": "lab_bottle_measurements",
                    "atomic_commit": "lab_bottle_action_commits",
                }
            )
        if format_revision == _EXTERNAL_VALIDATION_FORMAT_REVISION:
            packet["ordering_contract"].update(
                {
                    "physical_bindings": ["build_plan_version_id", "id"],
                    "stock_preparation_receipts": [
                        "build_plan_version_id",
                        "created_at",
                        "id",
                    ],
                    "physical_line_bindings": [
                        "build_plan_physical_binding_id",
                        "command_sequence",
                        "id",
                    ],
                    "compounding_runs": [
                        "build_plan_version_id",
                        "created_at",
                        "id",
                    ],
                    "compounding_command_receipts": [
                        "compounding_run_id",
                        "sequence",
                        "id",
                    ],
                    "engine_jobs": ["created_at", "job_type", "id"],
                    "engine_job_events": ["job_id", "sequence", "id"],
                    "engine_job_results": ["job_id", "id"],
                    "external_validation_records": [
                        "experiment_id",
                        "record_kind",
                        "created_at",
                        "id",
                    ],
                }
            )
            packet["unit_contract"].update(
                {
                    "exact_physical_quantities": "canonical_decimal_strings",
                    "external_validation_time_seconds": (
                        "canonical_plain_decimal_seconds"
                    ),
                    "external_validation_value": (
                        "canonical_plain_decimal_on_locked_endpoint_scale"
                    ),
                }
            )
            packet["provenance_contract"].update(
                {
                    "physical_lineage": (
                        "lab_build_plan_physical_bindings_and_receipts"
                    ),
                    "durable_engine_jobs": (
                        "fingerprinted_append_only_job_event_result_chain"
                    ),
                    "external_validation": (
                        "immutable_scope_snapshots_with_false_authority"
                    ),
                }
            )
        if include_records:
            packet["records"] = _export_records(self.record_paths())
        return packet

    async def export_planning_workspace(self) -> dict[str, Any]:
        """Write the complete v2 graph while the legacy endpoint stays v1."""

        return await self.export_workspace(
            format_revision=_PLANNING_FORMAT_REVISION, include_records=False
        )

    async def export_science_workspace(self) -> dict[str, Any]:
        """Write the complete v3 science-authority graph."""

        return await self.export_workspace(
            format_revision=_SCIENCE_FORMAT_REVISION, include_records=False
        )

    async def export_execution_workspace(self) -> dict[str, Any]:
        """Write the complete v4 canonical execution graph."""

        return await self.export_workspace(
            format_revision=_FORMAT_REVISION, include_records=False
        )

    async def export_external_validation_workspace(self) -> dict[str, Any]:
        """Write the complete v5 durable laboratory and validation graph."""

        return await self.export_workspace(
            format_revision=_EXTERNAL_VALIDATION_FORMAT_REVISION,
            include_records=False,
        )

    async def canonical_bytes(self) -> bytes:
        """Preserve the v3 byte contract for existing callers."""

        return json.dumps(
            await self.export_science_workspace(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    async def canonical_execution_bytes(self) -> bytes:
        return json.dumps(
            await self.export_execution_workspace(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    async def canonical_external_validation_bytes(self) -> bytes:
        return json.dumps(
            await self.export_external_validation_workspace(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    async def import_workspace(self, packet: Mapping[str, Any]) -> ImportResult:
        format_revision = packet.get("format_revision")
        if format_revision not in _SUPPORTED_REVISIONS:
            raise ValueError("unsupported laboratory export revision")
        incoming_tables = packet.get("tables")
        if not isinstance(incoming_tables, Mapping):
            raise ValueError("laboratory export tables must be an object")
        allowed_tables: tuple[str, ...]
        if format_revision == "lab-export-v1":
            allowed_tables = _V1_TABLE_ORDER
        elif format_revision == _PLANNING_FORMAT_REVISION:
            allowed_tables = _V2_TABLE_ORDER
        elif format_revision == _SCIENCE_FORMAT_REVISION:
            allowed_tables = _V3_TABLE_ORDER
        elif format_revision == _FORMAT_REVISION:
            allowed_tables = _V4_TABLE_ORDER
        else:
            allowed_tables = _V5_TABLE_ORDER
        unknown = set(incoming_tables).difference(allowed_tables)
        if unknown:
            raise ValueError("laboratory export contains unknown tables")
        records: dict[str, bytes] = {}
        record_paths: Mapping[str, Path] = {}
        if packet.get("records") is not None:
            records = _verified_records(packet["records"])
            record_paths = self.record_paths()
            for name, content in records.items():
                if _live_record_conflicts(record_paths[name], content):
                    raise ImportConflictError(
                        f"Stock record conflict: {record_paths[name]} already exists "
                        f"with different content than {name} in the export"
                    )

        owns_transaction = not self.session.in_transaction()
        if owns_transaction:
            await self.session.begin()
        inserted = 0
        skipped = 0
        try:
            for table_name in allowed_tables:
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
            records_written = 0
            records_already_present = 0
            for name, content in records.items():
                destination = record_paths[name]
                if _publish_record(destination, content):
                    records_written += 1
                elif _live_record_conflicts(destination, content):
                    raise ImportConflictError(
                        f"Stock record conflict: {destination} already exists "
                        f"with different content than {name} in the export"
                    )
                else:
                    records_already_present += 1
            if owns_transaction:
                await self.session.commit()
        except BaseException:
            if owns_transaction:
                await self.session.rollback()
            raise
        return ImportResult(
            inserted=inserted,
            skipped=skipped,
            records_written=records_written,
            records_already_present=records_already_present,
        )

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
    if table_name == "lab_target_hypothesis_versions":
        return (table.c.target_id, table.c.version_number, table.c.id)
    if table_name == "lab_target_lines":
        return (
            table.c.target_hypothesis_version_id,
            table.c.position,
            table.c.id,
        )
    if table_name == "lab_inventory_mapping_versions":
        return (table.c.mapping_id, table.c.version_number, table.c.id)
    if table_name == "lab_build_plan_versions":
        return (table.c.plan_id, table.c.version_number, table.c.id)
    if table_name == "lab_build_plan_lines":
        return (
            table.c.build_plan_version_id,
            table.c.position,
            table.c.id,
        )
    if table_name == "lab_inventory_reservation_events":
        return (table.c.reservation_id, table.c.sequence, table.c.id)
    if table_name == "lab_bottle_action_proposals":
        return (table.c.reservation_id, table.c.created_at, table.c.id)
    if table_name == "lab_bottle_action_confirmations":
        return (table.c.proposal_id, table.c.id)
    if table_name == "lab_bottle_measurements":
        return (
            table.c.proposal_id,
            table.c.quantity_kind,
            table.c.id,
        )
    if table_name == "lab_bottle_action_commits":
        return (table.c.proposal_id, table.c.id)
    if table_name == "lab_analytical_method_versions":
        return (table.c.method_id, table.c.version_number, table.c.id)
    if table_name == "lab_analytical_runs":
        return (table.c.run_id, table.c.id)
    if table_name == "lab_analytical_peaks":
        return (
            table.c.analytical_run_id,
            table.c.retention_time_minutes,
            table.c.peak_key,
            table.c.id,
        )
    if table_name == "lab_analytical_qc_records":
        return (table.c.analytical_run_id, table.c.qc_key, table.c.id)
    if table_name == "lab_analytical_attachments":
        return (
            table.c.analytical_run_id,
            table.c.attachment_kind,
            table.c.content_sha256,
            table.c.id,
        )
    if table_name == "lab_gco_events":
        return (
            table.c.analytical_run_id,
            table.c.retention_time_minutes,
            table.c.event_key,
            table.c.id,
        )
    if table_name == "lab_regulatory_assessment_versions":
        return (table.c.assessment_id, table.c.version_number, table.c.id)
    if table_name == "lab_regulatory_findings":
        return (
            table.c.regulatory_assessment_version_id,
            table.c.finding_key,
            table.c.id,
        )
    if table_name == "lab_claim_assessment_versions":
        return (table.c.claim_id, table.c.version_number, table.c.id)
    if table_name == "lab_claim_assessment_evidence_links":
        return (
            table.c.claim_assessment_version_id,
            table.c.role,
            table.c.evidence_record_id,
            table.c.id,
        )
    if table_name == "lab_build_plan_physical_bindings":
        return (table.c.build_plan_version_id, table.c.id)
    if table_name == "lab_stock_preparation_receipts":
        return (table.c.build_plan_version_id, table.c.created_at, table.c.id)
    if table_name == "lab_build_plan_line_physical_bindings":
        return (
            table.c.build_plan_physical_binding_id,
            table.c.command_sequence,
            table.c.id,
        )
    if table_name == "lab_compounding_runs":
        return (table.c.build_plan_version_id, table.c.created_at, table.c.id)
    if table_name == "lab_compounding_command_receipts":
        return (table.c.compounding_run_id, table.c.sequence, table.c.id)
    if table_name == "lab_engine_jobs":
        return (table.c.created_at, table.c.job_type, table.c.id)
    if table_name == "lab_engine_job_events":
        return (table.c.job_id, table.c.sequence, table.c.id)
    if table_name == "lab_engine_job_results":
        return (table.c.job_id, table.c.id)
    if table_name == "lab_external_validation_records":
        return (
            table.c.experiment_id,
            table.c.record_kind,
            table.c.created_at,
            table.c.id,
        )
    return (table.c.id,)


def _export_records(paths: Mapping[str, Path]) -> dict[str, Any]:
    exported: dict[str, Any] = {}
    for name in _RECORD_NAMES:
        try:
            content = paths[name].read_bytes()
        except FileNotFoundError:
            exported[name] = None
            continue
        exported[name] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    return exported


def _verified_records(records: Any) -> dict[str, bytes]:
    """Decode every exported record, refusing the packet if any fails its hash."""

    if not isinstance(records, Mapping):
        raise ValueError("laboratory export records must be an object")
    if set(records).difference(_RECORD_NAMES):
        raise ValueError("laboratory export contains unknown stock records")
    verified: dict[str, bytes] = {}
    for name in _RECORD_NAMES:
        entry = records.get(name)
        if entry is None:
            continue
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("content_base64"), str
        ):
            raise ValueError(f"export stock record {name} is malformed")
        try:
            content = base64.b64decode(entry["content_base64"], validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError(f"export stock record {name} is malformed") from error
        if (
            entry.get("size_bytes") != len(content)
            or entry.get("sha256") != hashlib.sha256(content).hexdigest()
        ):
            raise ValueError(
                f"export stock record {name} does not match its recorded hash"
            )
        verified[name] = content
    return verified


def _live_record_conflicts(path: Path, content: bytes) -> bool:
    """True when the live record holds events the exported one does not.

    The records are append-only logs, so a live record that begins with the
    exported bytes (an older export of this PC) already holds every exported
    event and is left as it is.
    """

    try:
        return not path.read_bytes().startswith(content)
    except FileNotFoundError:
        return False


def _publish_record(destination: Path, content: bytes) -> bool:
    """Write ``destination`` only if it does not exist; True when this call wrote it."""

    if destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=_RECORD_TEMP_SUFFIX,
        dir=destination.parent,
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(handle, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        return user_records._publish(temp, destination)
    finally:
        temp.unlink(missing_ok=True)


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            serialized[str(key)] = value.astimezone(timezone.utc).isoformat()
        elif isinstance(value, date):
            serialized[str(key)] = value.isoformat()
        else:
            serialized[str(key)] = value
    return serialized


def _deserialize_row(table, row: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for column in table.columns:
        if column.name not in row:
            continue
        value = row[column.name]
        column_type = column.type
        implementation = getattr(column_type, "impl", None)
        is_datetime = isinstance(column_type, DateTime) or isinstance(
            implementation,
            DateTime,
        )
        is_date = isinstance(column_type, Date) or isinstance(
            implementation,
            Date,
        )
        if value is not None and is_datetime:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            value = parsed
        elif value is not None and is_date:
            value = date.fromisoformat(str(value))
        values[column.name] = value
    return values


__all__ = [
    "CURRENT_WRITE_REVISION",
    "ImportConflictError",
    "ImportResult",
    "LabExportService",
    "migrate_export_packet",
]
