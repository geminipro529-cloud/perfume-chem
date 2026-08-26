"""Generic external reconstruction candidate ingestion adapter (library).

Entrypoint: `python -m engine.ingestion <candidate.json> [--inventory-snapshot <id>] [--expected-total <n>] [--output-dir <dir>]`
or import: `from engine.ingestion import ingest_external_candidate`.

AGENTS.md Rule 2 compliant: this is an importable canonical library module, NOT a
new top-level pipeline script. No XLSX is used as the internal interface.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from . import normalize
from .schema import (
    REJECTION_CODES,
    SCHEMA_VERSION,
    StructuredRejection,
    compute_total_parts,
    validate_candidate,
    validate_totals,
)

__all__ = ["IngestionResult", "ingest_external_candidate", "canonical_json", "deterministic_hash"]


def _sort_key(x: Any) -> Any:
    return (0, str(x)) if isinstance(x, str) else (1, str(x))


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, stable float repr, compact separators."""

    def _norm(o: Any) -> Any:
        if isinstance(o, dict):
            return {k: _norm(o[k]) for k in sorted(o, key=_sort_key)}
        if isinstance(o, list):
            return [_norm(x) for x in o]
        if isinstance(o, float):
            return repr(o)
        return o

    return json.dumps(_norm(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def deterministic_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


class IngestionResult:
    def __init__(
        self,
        accepted: bool,
        candidate_id: str,
        output_dir: str,
        reports: Mapping[str, Any],
        rejections: list[StructuredRejection],
        candidate_hash: str | None,
    ):
        self.accepted = accepted
        self.candidate_id = candidate_id
        self.output_dir = output_dir
        self.reports = reports
        self.rejections = rejections
        self.candidate_hash = candidate_hash

    def write(self) -> dict[str, str]:
        written = {}
        for name, payload in self.reports.items():
            if self.accepted and name == "rejection.json":
                continue
            p = os.path.join(self.output_dir, name)
            with open(p, "w", encoding="utf-8") as f:
                if name.endswith(".jsonl"):
                    for row in payload:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                else:
                    json.dump(payload, f, indent=1, ensure_ascii=False)
            written[name] = p
        return written


def ingest_external_candidate(
    candidate: dict[str, Any],
    *,
    expected_total: float | None = None,
    alias_map: Mapping[str, str] | None = None,
    stock_resolver=None,
    output_dir: str,
    candidate_id_override: str | None = None,
) -> IngestionResult:
    """Validate and normalize an external reconstruction candidate. Fail-closed.

    Returns an IngestionResult; when rejected, writes rejection.json (structured).
    """
    os.makedirs(output_dir, exist_ok=True)
    candidate_id = candidate_id_override or str(candidate.get("candidate_id", "UNKNOWN"))

    rejections: list[StructuredRejection] = []
    rejections.extend(validate_candidate(candidate))

    if candidate.get("formula_rows") and not rejections:
        rejections.extend(validate_totals(candidate, expected_total))

    # note-name -> material guard: a canonical material that is itself a note name
    for row in candidate.get("formula_rows", []):
        canon = row.get("canonical_material_name")
        if (
            canon
            and canon.lower()
            in {"jasmine", "rose", "osmanthus", "muguet", "tuberose", "iris", "orris"}
            and row.get("exact_supplied_stock", "").lower() == canon
        ):
            rejections.append(
                StructuredRejection(
                    "NOTE_NAME_TO_MATERIAL",
                    f"note name used directly as material: {canon}",
                    f"formula_rows[].canonical_material_name",
                )
            )

    normalized_rows: list[dict[str, Any]] = []
    alias_report: list[dict[str, Any]] = []
    row_notes: list[str] = []
    if not rejections:
        for row in candidate.get("formula_rows", []):
            nrow, notes = normalize.normalize_row(row, alias_map, stock_resolver)
            normalized_rows.append(nrow)
            row_notes.extend(notes)
            alias_report.append(
                {
                    "row_number": nrow.get("row_number"),
                    "raw": nrow.get("raw_material_name"),
                    "canonical": nrow.get("canonical_material_name"),
                    "alias_resolved": nrow.get("_alias_resolved"),
                    "stock_resolved": nrow.get("_stock_resolved", True),
                }
            )
        unresolved_alias = [a for a in alias_report if not a["alias_resolved"]]
        unresolved_stock = [a for a in alias_report if not a["stock_resolved"]]
        if unresolved_alias:
            rejections.append(
                StructuredRejection(
                    "AMBIGUOUS_ALIAS", f"{len(unresolved_alias)} unresolved aliases", "formula_rows"
                )
            )
        if unresolved_stock:
            rejections.append(
                StructuredRejection(
                    "UNRESOLVED_EXACT_STOCK",
                    f"{len(unresolved_stock)} unresolved stocks",
                    "formula_rows",
                )
            )

    accepted = not rejections

    total = compute_total_parts(candidate)
    reports: dict[str, Any] = {}
    if accepted:
        reports["validated_candidate.json"] = {**candidate, "schema_version": SCHEMA_VERSION}
        reports["formula_rows.jsonl"] = normalized_rows
        reports["arithmetic_report.json"] = {
            "candidate_id": candidate_id,
            "total_parts": round(total, 6),
            "expected_total": expected_total,
            "row_count": len(normalized_rows),
            "active_ul_total": round(
                sum(r.get("active_ul_estimate", 0.0) for r in normalized_rows), 6
            ),
            "balance": "PASS"
            if (expected_total is None or abs(total - expected_total) <= 1e-6)
            else "FAIL",
        }
        reports["alias_report.json"] = alias_report
        reports["inventory_crosswalk.json"] = normalize.inventory_crosswalk(normalized_rows)
        reports["carrier_ledger.json"] = normalize.carrier_ledger(normalized_rows)
        reports["evidence_integrity_report.json"] = {
            "source_artifact_hashes": candidate.get("source_artifact_hashes", []),
            "evidence_refs": candidate.get("evidence_refs", []),
            "all_source_hashes_present": bool(candidate.get("source_artifact_hashes")),
        }
        reports["gate_dispatch_input.json"] = {
            "candidate_id": candidate_id,
            "target_id": candidate.get("target_id"),
            "formula_uid": candidate.get("formula_uid"),
            "formula_state": candidate.get("formula_state"),
            "empirical_state": candidate.get("empirical_state"),
            "inventory_snapshot_id": candidate.get("inventory_snapshot_id"),
            "row_count": len(normalized_rows),
            "total_parts": round(total, 6),
        }
        candidate_hash = deterministic_hash({**candidate, "schema_version": SCHEMA_VERSION})
        reports["ingestion_receipt.json"] = {
            "candidate_id": candidate_id,
            "accepted": True,
            "deterministic_hash": candidate_hash,
            "schema_version": SCHEMA_VERSION,
            "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        reports["deterministic_hash.json"] = {
            "candidate_id": candidate_id,
            "sha256": candidate_hash,
        }
    else:
        reports["rejection.json"] = {
            "candidate_id": candidate_id,
            "accepted": False,
            "rejections": [r.to_dict() for r in rejections],
            "row_notes": row_notes,
            "schema_version": SCHEMA_VERSION,
            "rejected_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    return IngestionResult(
        accepted,
        candidate_id,
        output_dir,
        reports,
        rejections,
        reports.get("deterministic_hash.json", {}).get("sha256") if accepted else None,
    )
