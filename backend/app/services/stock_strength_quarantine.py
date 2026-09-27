"""Repository-native V5 STOCK-STRENGTH RECALC quarantine authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.inventory_authority import CURRENT_INVENTORY_AUTHORITY

_QUARANTINE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "governance"
    / "stock_strength_recalc_quarantine_v5.json"
)
_REQUIRED_RECEIPT_FIELDS = {
    "target_id",
    "formula_uid",
    "inventory_v5_sha256",
    "stock_lineage_receipt_sha256",
    "build_plan_validation_sha256",
    "verified_by",
    "verified_at_utc",
}


class StockStrengthQuarantineError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _load_quarantine() -> dict[str, Any]:
    try:
        payload = json.loads(_QUARANTINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StockStrengthQuarantineError(
            "STOCK_STRENGTH_QUARANTINE_AUTHORITY_UNAVAILABLE",
            "V5 stock-strength quarantine authority is unavailable or invalid.",
        ) from error
    if not isinstance(payload, dict):
        raise StockStrengthQuarantineError(
            "STOCK_STRENGTH_QUARANTINE_AUTHORITY_INVALID",
            "V5 stock-strength quarantine authority must be a JSON object.",
        )
    source = payload.get("source_triage", {})
    authority = payload.get("inventory_authority", {})
    if (
        not isinstance(source, dict)
        or not isinstance(authority, dict)
        or payload.get("state") != "QUARANTINED_UNTIL_LINEAGE_RECEIPTS_CLEAR"
        or source.get("rows") != 261
        or source.get("targets") != 104
        or source.get("compounding_authorized_rows") != 0
        or authority.get("sha256") != CURRENT_INVENTORY_AUTHORITY.sha256
    ):
        raise StockStrengthQuarantineError(
            "STOCK_STRENGTH_QUARANTINE_AUTHORITY_INVALID",
            "V5 stock-strength quarantine metadata does not match the immutable incident contract.",
        )
    return payload


def _valid_clearance_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or not _REQUIRED_RECEIPT_FIELDS.issubset(receipt):
        return False
    if receipt.get("inventory_v5_sha256") != CURRENT_INVENTORY_AUTHORITY.sha256:
        return False
    for field in ("stock_lineage_receipt_sha256", "build_plan_validation_sha256"):
        value = str(receipt.get(field, "")).strip().lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            return False
    return bool(str(receipt.get("verified_by", "")).strip()) and bool(
        str(receipt.get("verified_at_utc", "")).strip()
    )


def quarantine_record_for_product_key(product_key: str) -> dict[str, Any] | None:
    """Return the blocking incident record unless an explicit valid receipt clears it."""

    payload = _load_quarantine()
    key = str(product_key).strip().upper()
    target_ids = {str(value).upper() for value in payload.get("target_ids", [])}
    formula_uids = {str(value).upper() for value in payload.get("formula_uids", [])}
    target_id = next(
        (
            candidate
            for candidate in target_ids
            if key == candidate or key.endswith(f":{candidate}") or key.endswith(f"/{candidate}")
        ),
        None,
    )
    formula_uid = key if key in formula_uids else None
    if target_id is None and formula_uid is None:
        return None

    for receipt in payload.get("clearance_receipts", []):
        if not _valid_clearance_receipt(receipt):
            continue
        receipt_target = str(receipt.get("target_id", "")).strip().upper()
        receipt_formula = str(receipt.get("formula_uid", "")).strip().upper()
        if target_id is not None and receipt_target == target_id:
            return None
        if formula_uid is not None and receipt_formula == formula_uid:
            return None

    return {
        "state": payload["state"],
        "target_id": target_id,
        "formula_uid": formula_uid,
        "source_triage_sha256": payload["source_triage"]["sha256"],
    }


__all__ = [
    "StockStrengthQuarantineError",
    "quarantine_record_for_product_key",
]
