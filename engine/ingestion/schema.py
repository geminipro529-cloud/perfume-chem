"""Canonical external-candidate interchange schema for the generic ingestion adapter.

Deterministic, schema-versioned, XLSX-free. Mirrors EXTERNAL_CANDIDATE_INGESTION_SCHEMA.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "external_candidate_v1"

FORMULA_STATES = {
    "COMPUTATIONAL_RECONSTRUCTION_CANDIDATE",
    "INVENTORY_MAPPED",
    "CANDIDATE",
    "PENDING_PHYSICAL_TEST",
    "UNKNOWN",
}
EMPIRICAL_STATES = {"NOT_EMPIRICALLY_VERIFIED", "PENDING", "UNKNOWN"}

REJECTION_CODES = {
    "UNRESOLVED_TARGET_IDENTITY",
    "INVALID_FORMULA_TOTALS",
    "UNRESOLVED_EXACT_STOCK",
    "INVENTED_ACTIVE_FRACTION",
    "EXPANDED_PRODUCT_BASIS",
    "AMBIGUOUS_ALIAS",
    "MISSING_SOURCE_ARTIFACT_HASH",
    "FORMULA_EMPIRICAL_CONFLATED",
    "NOTE_NAME_TO_MATERIAL",
    "ABSENT_INVENTORY_SNAPSHOT",
    "UNREPRESENTABLE_FORMULA_ROWS",
}

PRODUCT_BASIS = "PRODUCT_BASIS"

REQUIRED_ROW_FIELDS = [
    "row_number",
    "raw_material_name",
    "canonical_material_name",
    "exact_supplied_stock",
    "parts",
    "active_fraction_or_PRODUCT_BASIS",
    "declared_carrier",
    "perceptual_function",
    "structural_function",
    "phase_roles",
    "evidence_class",
    "evidence_refs",
    "dose_rationale",
    "plausible_alternatives",
    "inventory_status",
    "confidence",
    "uncertainty",
]

REQUIRED_CANDIDATE_FIELDS = [
    "candidate_id",
    "target_id",
    "target_name",
    "target_version",
    "concentration",
    "region_or_jurisdiction",
    "formula_uid",
    "parent_formula_uid",
    "formula_state",
    "empirical_state",
    "source_artifact_paths",
    "source_artifact_hashes",
    "inventory_snapshot_id",
    "inventory_snapshot_hash",
    "formula_rows",
    "evidence_refs",
    "provenance",
]


@dataclass(frozen=True, slots=True)
class StructuredRejection:
    code: str
    detail: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail, "field": self.field}


def _require(candidate: dict[str, Any]) -> list[StructuredRejection]:
    out = []
    for f in REQUIRED_CANDIDATE_FIELDS:
        if f not in candidate:
            out.append(
                StructuredRejection(
                    "UNREPRESENTABLE_FORMULA_ROWS", f"missing candidate field: {f}", f
                )
            )
    return out


def validate_candidate(candidate: dict[str, Any]) -> list[StructuredRejection]:
    """Structural validation of the canonical candidate envelope. Fail-closed."""
    rejections: list[StructuredRejection] = []
    rejections.extend(_require(candidate))
    if rejections:
        return rejections

    if candidate.get("formula_state") not in FORMULA_STATES:
        rejections.append(
            StructuredRejection(
                "UNRESOLVED_TARGET_IDENTITY",
                f"unrecognized formula_state: {candidate.get('formula_state')}",
                "formula_state",
            )
        )
    if candidate.get("empirical_state") not in EMPIRICAL_STATES:
        rejections.append(
            StructuredRejection(
                "FORMULA_EMPIRICAL_CONFLATED",
                f"unrecognized empirical_state: {candidate.get('empirical_state')}",
                "empirical_state",
            )
        )

    if (
        candidate.get("formula_state") in FORMULA_STATES
        and candidate.get("empirical_state") in EMPIRICAL_STATES
    ):
        if candidate["formula_state"] == candidate["empirical_state"]:
            rejections.append(
                StructuredRejection(
                    "FORMULA_EMPIRICAL_CONFLATED",
                    "formula_state and empirical_state are conflated (identical values)",
                    "empirical_state",
                )
            )

    if not candidate.get("inventory_snapshot_id") or not candidate.get("inventory_snapshot_hash"):
        rejections.append(
            StructuredRejection(
                "ABSENT_INVENTORY_SNAPSHOT",
                "inventory_snapshot_id and inventory_snapshot_hash are required",
                "inventory_snapshot_id",
            )
        )

    if not candidate.get("source_artifact_hashes"):
        rejections.append(
            StructuredRejection(
                "MISSING_SOURCE_ARTIFACT_HASH",
                "source_artifact_hashes must be non-empty",
                "source_artifact_hashes",
            )
        )

    rows = candidate.get("formula_rows", [])
    if not isinstance(rows, list) or not rows:
        rejections.append(
            StructuredRejection(
                "UNREPRESENTABLE_FORMULA_ROWS",
                "formula_rows must be a non-empty list",
                "formula_rows",
            )
        )
        return rejections

    for row in rows:
        if not isinstance(row, dict):
            rejections.append(
                StructuredRejection(
                    "UNREPRESENTABLE_FORMULA_ROWS", "formula row is not an object", "formula_rows"
                )
            )
            continue
        for f in REQUIRED_ROW_FIELDS:
            if f not in row:
                rejections.append(
                    StructuredRejection(
                        "UNREPRESENTABLE_FORMULA_ROWS",
                        f"missing row field: {f}",
                        f"formula_rows[].{f}",
                    )
                )
        # exact stock must resolve (non-empty); PRODUCT_BASIS is explicit, not expanded
        if not row.get("exact_supplied_stock"):
            rejections.append(
                StructuredRejection(
                    "UNRESOLVED_EXACT_STOCK",
                    f"row {row.get('row_number')}: exact_supplied_stock unresolved",
                    f"formula_rows[].exact_supplied_stock",
                )
            )
        af = row.get("active_fraction_or_PRODUCT_BASIS")
        if af is None or af == "":
            rejections.append(
                StructuredRejection(
                    "INVENTED_ACTIVE_FRACTION",
                    f"row {row.get('row_number')}: active fraction or PRODUCT_BASIS required",
                    "formula_rows[].active_fraction_or_PRODUCT_BASIS",
                )
            )
        if af not in (PRODUCT_BASIS,) and not (
            isinstance(af, (int, float)) and 0.0 <= float(af) <= 1.0
        ):
            rejections.append(
                StructuredRejection(
                    "INVENTED_ACTIVE_FRACTION",
                    f"row {row.get('row_number')}: active fraction must be 0..1 or PRODUCT_BASIS",
                    "formula_rows[].active_fraction_or_PRODUCT_BASIS",
                )
            )

    return rejections


def compute_total_parts(candidate: dict[str, Any]) -> float:
    return sum(float(r.get("parts", 0.0)) for r in candidate.get("formula_rows", []))


def validate_totals(
    candidate: dict[str, Any], expected_total: float | None = None
) -> list[StructuredRejection]:
    total = compute_total_parts(candidate)
    if expected_total is not None and abs(total - expected_total) > 1e-6:
        return [
            StructuredRejection(
                "INVALID_FORMULA_TOTALS",
                f"formula total {total} != expected {expected_total}",
                "formula_rows",
            )
        ]
    return []
