"""Read-only Checkpoint 4 audit for the R5-derived AIMI design successor.

The evaluator applies one governed row delta to the immutable R5 comparator,
binds the selected owned stock, and preserves every scientific and physical
authority ceiling.  It never creates a build plan, reservation, mixer command,
transfer, prepared-stock receipt, inventory mutation, or physical formula.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.experiments.checkpoint3_readiness import (
    evaluate_r5_checkpoint3_readiness,
)
from engine.inventory_parser import (
    CurrentInventoryMaterialization,
    InventoryMaterial,
    materialize_current_inventory,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUCCESSOR_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_aimi_design_successor_20260926.json"
)
DEFAULT_INVENTORY_TEXT_PATH = REPOSITORY_ROOT / "inventory.txt"


class Checkpoint4ContractError(ValueError):
    """Raised when the Checkpoint 4 successor contract is unusable."""


def _file_sha256(path: Path) -> str:
    return stable_portable_file_hash(path)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Checkpoint4ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint4ContractError(f"{label} must be a JSON object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint4ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint4ContractError(f"{label} must be a list")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise Checkpoint4ContractError(f"{label} must be an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise Checkpoint4ContractError(f"{label} must be an integer") from exc


def _pinned_bytes_match(path: Path, expected_sha256: str) -> bool:
    """Exact bytes, or the same bytes after only CRLF->LF or LF->CRLF conversion.

    Git stores some pinned text in LF while a Windows checkout materializes
    CRLF, so a pin taken on one platform must verify on the other. Any other
    byte difference (including bare carriage returns) is still drift.
    """
    payload = path.read_bytes()
    candidates = [payload]
    lf_form = payload.replace(b"\r\n", b"\n")
    if b"\r" not in lf_form:
        candidates.append(lf_form)
        candidates.append(lf_form.replace(b"\n", b"\r\n"))
    return any(hashlib.sha256(item).hexdigest() == expected_sha256 for item in candidates)


def _resolve_pinned_file(reference: Mapping[str, Any], label: str) -> Path:
    relative = str(reference.get("path") or "")
    expected_sha256 = str(reference.get("sha256") or "")
    path = (REPOSITORY_ROOT / relative).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint4ContractError(f"{label} escapes repository")
    if not path.is_file() or not _pinned_bytes_match(path, expected_sha256):
        raise Checkpoint4ContractError(f"{label} hash drift")
    return path


def _stock_payload(stock: InventoryMaterial) -> dict[str, object]:
    return {
        "stock_id": stock.stock_id,
        "name": stock.name,
        "identity_name": stock.identity_name,
        "dilution_decimal": str(Decimal(str(stock.dilution)).normalize()),
        "fraction_basis": stock.fraction_basis,
        "carrier": stock.carrier,
        "status": stock.status,
        "execution_ready": stock.execution_ready,
        "nominal_property_model_ready": stock.nominal_property_model_ready,
        "authority": stock.authority,
        "source_ref": stock.source_ref,
    }


def _quantities(rows: list[dict[str, Any]]) -> dict[str, object]:
    liquids = [row for row in rows if row.get("unit") == "µL"]
    solids = [row for row in rows if row.get("unit") == "mg"]
    return {
        "row_count": len(rows),
        "liquid_row_count": len(liquids),
        "liquid_total_ul": str(
            sum((Decimal(str(row.get("dose"))) for row in liquids), Decimal(0))
        ),
        "solid_row_count": len(solids),
        "solid_total_mg": str(
            sum((Decimal(str(row.get("dose"))) for row in solids), Decimal(0))
        ),
        "mass_volume_never_summed": True,
    }


def evaluate_r6_aimi_checkpoint4_readiness(
    *,
    successor_path: Path = DEFAULT_SUCCESSOR_PATH,
    inventory_text_path: Path = DEFAULT_INVENTORY_TEXT_PATH,
    inventory: CurrentInventoryMaterialization | None = None,
) -> dict[str, object]:
    """Return the deterministic, fail-closed Checkpoint 4 successor report."""

    successor = _load_object(successor_path, "Checkpoint 4 successor manifest")
    if successor.get("schema_version") != (
        "lavande-ambre-profond-design-successor-delta-v1"
    ):
        raise Checkpoint4ContractError("unsupported Checkpoint 4 schema")

    parent_ref = _require_mapping(successor.get("parent"), "parent reference")
    checkpoint3_ref = _require_mapping(
        successor.get("checkpoint3_protocol"),
        "Checkpoint 3 protocol reference",
    )
    decision_ref = _require_mapping(
        successor.get("user_decision"),
        "user decision reference",
    )
    inventory_ref = _require_mapping(
        successor.get("inventory_binding_candidate"),
        "inventory binding candidate",
    )
    product_ref = _require_mapping(
        successor.get("nominal_product_reference"),
        "nominal product reference",
    )
    replacement = _require_mapping(
        successor.get("row_replacement"),
        "row replacement",
    )
    invariants = _require_mapping(
        successor.get("successor_invariants"),
        "successor invariants",
    )
    applicability = _require_mapping(
        successor.get("model_applicability"),
        "model applicability",
    )
    checkpoint4_contract = _require_mapping(
        successor.get("checkpoint4_contract"),
        "Checkpoint 4 contract",
    )
    authority = dict(_require_mapping(successor.get("authority"), "authority"))
    if authority.get("design_successor_record_authorized") is not True or any(
        value is not False
        for key, value in authority.items()
        if key != "design_successor_record_authorized"
    ):
        raise Checkpoint4ContractError(
            "Checkpoint 4 successor has an invalid authority boundary"
        )

    parent_path = _resolve_pinned_file(parent_ref, "R5 parent comparator")
    checkpoint3_path = _resolve_pinned_file(
        checkpoint3_ref,
        "Checkpoint 3 protocol",
    )
    decision_path = _resolve_pinned_file(decision_ref, "AIMI user decision")
    authority_record_path = _resolve_pinned_file(
        {
            "path": inventory_ref.get("authority_record_path"),
            "sha256": inventory_ref.get("authority_record_sha256"),
        },
        "AIMI inventory authority record",
    )
    product_page_path = _resolve_pinned_file(
        {
            "path": product_ref.get("product_page_path"),
            "sha256": product_ref.get("product_page_sha256"),
        },
        "nominal AIMI product page",
    )
    coa_path = _resolve_pinned_file(
        {
            "path": product_ref.get("coa_path"),
            "sha256": product_ref.get("coa_sha256"),
        },
        "nominal AIMI certificate",
    )

    parent = _load_object(parent_path, "R5 parent comparator")
    decision = _load_object(decision_path, "AIMI user decision")
    parent_rows = [
        dict(_require_mapping(row, "R5 parent row"))
        for row in _require_list(parent.get("rows"), "R5 parent rows")
    ]
    parent_rows_sha256 = _canonical_sha256(parent_rows)
    if parent_rows_sha256 != parent_ref.get("canonical_rows_sha256"):
        raise Checkpoint4ContractError("R5 parent row hash drift")
    if decision.get("message_fact", {}).get("normalized_decision") != (
        "USE_OWNED_GIVAUDAN_AIMI_IN_A_SEPARATELY_IDENTIFIED_R5_SUCCESSOR"
    ):
        raise Checkpoint4ContractError("AIMI user decision scope drift")

    current_inventory = inventory or materialize_current_inventory()
    checkpoint3 = evaluate_r5_checkpoint3_readiness(
        protocol_path=checkpoint3_path,
        inventory_text_path=inventory_text_path,
        inventory=current_inventory,
    )
    dynamic_blockers: list[str] = []
    if (
        checkpoint3.get("input_integrity_state") != "VERIFIED"
        or checkpoint3.get("baseline_state")
        != "R5_STANDALONE_BASELINE_ACCEPTED"
        or checkpoint3.get("parent_equivalence_state")
        != "NOT_CLAIMED_STANDALONE_BASELINE"
    ):
        dynamic_blockers.append("HOLD_CHECKPOINT3_BASELINE_DRIFT")

    if (
        _file_sha256(inventory_text_path)
        != inventory_ref.get("inventory_text_sha256")
        or current_inventory.snapshot_sha256
        != inventory_ref.get("materialized_inventory_snapshot_sha256")
        or current_inventory.overlay_sha256
        != inventory_ref.get("materialized_inventory_overlay_sha256")
    ):
        dynamic_blockers.append("HOLD_INVENTORY_FINGERPRINT_DRIFT")

    stock_id = str(inventory_ref.get("stock_id") or "")
    stock = next(
        (candidate for candidate in current_inventory.stocks if candidate.stock_id == stock_id),
        None,
    )
    if stock is None:
        stock_payload = None
        dynamic_blockers.append("HOLD_AIMI_STOCK_MISSING")
    else:
        stock_payload = _stock_payload(stock)
        if (
            stock.name != "Givaudan AIMI"
            or stock.identity_name != "Givaudan AIMI"
            or Decimal(str(stock.dilution)) != Decimal("1")
            or stock.fraction_basis != "neat"
            or stock.carrier != ""
            or stock.status != "owned"
            or stock.execution_ready is not True
        ):
            dynamic_blockers.append("HOLD_AIMI_STOCK_AUTHORITY_DRIFT")

    source_row = _integer(replacement.get("source_row"), "replacement source row")
    expected_parent_row = dict(
        _require_mapping(replacement.get("parent_row"), "replacement parent row")
    )
    successor_row = dict(
        _require_mapping(replacement.get("successor_row"), "replacement successor row")
    )
    matching_parent_rows = [
        row for row in parent_rows if _integer(row.get("source_row"), "source row") == source_row
    ]
    if matching_parent_rows != [expected_parent_row]:
        dynamic_blockers.append("HOLD_SUCCESSOR_PARENT_ROW_DRIFT")

    successor_rows = [
        successor_row if row == expected_parent_row else dict(row)
        for row in parent_rows
    ]
    changed_rows = [
        _integer(child.get("source_row"), "successor source row")
        for original, child in zip(parent_rows, successor_rows, strict=True)
        if original != child
    ]
    unchanged_rows = [
        row
        for row in parent_rows
        if _integer(row.get("source_row"), "unchanged source row") != source_row
    ]
    successor_rows_sha256 = _canonical_sha256(successor_rows)
    if (
        changed_rows != list(invariants.get("changed_source_rows", []))
        or _canonical_sha256(unchanged_rows)
        != invariants.get("parent_unchanged_rows_sha256")
        or successor_rows_sha256
        != invariants.get("successor_canonical_rows_sha256")
    ):
        dynamic_blockers.append("HOLD_SUCCESSOR_ROWSET_DRIFT")

    quantities = _quantities(successor_rows)
    expected_quantities = {
        "row_count": invariants.get("row_count"),
        "liquid_row_count": invariants.get("liquid_row_count"),
        "liquid_total_ul": invariants.get("liquid_total_ul"),
        "solid_row_count": invariants.get("solid_row_count"),
        "solid_total_mg": invariants.get("solid_total_mg"),
        "mass_volume_never_summed": invariants.get("mass_volume_never_summed"),
    }
    if quantities != expected_quantities:
        dynamic_blockers.append("HOLD_SUCCESSOR_QUANTITY_DRIFT")

    lavender_rows = {
        str(row.get("material")): Decimal(str(row.get("dose")))
        for row in successor_rows
        if row.get("material")
        in {"Lavender EO, Bontoux", "Lavender 40/42, Aroma&More"}
    }
    if lavender_rows != {
        "Lavender EO, Bontoux": Decimal("700"),
        "Lavender 40/42, Aroma&More": Decimal("300"),
    }:
        dynamic_blockers.append("HOLD_LAVENDER_BLOCK_DRIFT")

    if (
        successor_row.get("material") != "Givaudan AIMI"
        or successor_row.get("dose") != 50
        or successor_row.get("unit") != "µL"
        or replacement.get("nominal_transfer_preserved") is not True
        or replacement.get("stock_fraction_preserved") is not True
        or replacement.get("chemical_active_equivalence_claimed") is not False
        or replacement.get("sensory_equivalence_claimed") is not False
        or replacement.get("oav_equivalence_claimed") is not False
    ):
        dynamic_blockers.append("HOLD_AIMI_SUBSTITUTION_CONTRACT_DRIFT")

    if (
        product_ref.get("scope") != "REFERENCE_COMPATIBLE_NOT_BOTTLE_MATCHED"
        or product_ref.get("owned_bottle_identity_proven_by_reference") is not False
        or applicability.get("chemical_identity_state")
        != "HOLD_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED"
    ):
        dynamic_blockers.append("HOLD_AIMI_APPLICABILITY_CONTRACT_DRIFT")

    blockers = list(
        dict.fromkeys(
            dynamic_blockers
            + [
                str(value)
                for value in _require_list(
                    successor.get("blocker_order"),
                    "Checkpoint 4 blocker order",
                )
            ]
        )
    )
    side_effects = {
        "build_plan_created": False,
        "reservation_created": False,
        "mixer_command_created": False,
        "transfer_record_created": False,
        "prepared_stock_receipt_created": False,
        "inventory_modified": False,
        "physical_formula_modified": False,
        "physical_build_instruction_created": False,
    }
    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r6-aimi-cp4-report-v1",
        "status": "HOLD",
        "checkpoint4_state": checkpoint4_contract.get("state"),
        "input_integrity_state": (
            "VERIFIED" if not dynamic_blockers else "HOLD_DRIFT_DETECTED"
        ),
        "successor_id": successor.get("successor_id"),
        "design_successor_state": successor.get("state"),
        "parent_lineage_state": "EXACT_R5_STANDALONE_BASELINE_BOUND",
        "baseline_state": checkpoint3.get("baseline_state"),
        "parent_equivalence_state": checkpoint3.get("parent_equivalence_state"),
        "substitution_state": "AIMI_SELECTED_NOMINAL_50_UL_TRANSFER",
        "active_equivalence_state": "NOT_CLAIMED_INTENDED_MATERIAL_CHANGE",
        "stock_binding_state": "READ_ONLY_AIMI_CANDIDATE_BOUND_BUILD_PLAN_HOLD",
        "physical_build_state": checkpoint4_contract.get("physical_build_state"),
        "formula_action": checkpoint4_contract.get("formula_action"),
        "successor_rows_sha256": successor_rows_sha256,
        "changed_source_rows": changed_rows,
        "row_replacement": dict(replacement),
        "quantities": quantities,
        "aimi_stock": stock_payload,
        "model_applicability": dict(applicability),
        "nominal_product_reference": {
            "scope": product_ref.get("scope"),
            "supplier": product_ref.get("supplier"),
            "product_name": product_ref.get("product_name"),
            "sku": product_ref.get("sku"),
            "cas": product_ref.get("cas"),
            "owned_bottle_identity_proven_by_reference": False,
        },
        "fingerprints": {
            "successor_manifest_sha256": _file_sha256(successor_path),
            "parent_manifest_sha256": _file_sha256(parent_path),
            "parent_rows_sha256": parent_rows_sha256,
            "checkpoint3_protocol_sha256": _file_sha256(checkpoint3_path),
            "user_decision_sha256": _file_sha256(decision_path),
            "inventory_text_sha256": _file_sha256(inventory_text_path),
            "inventory_snapshot_sha256": current_inventory.snapshot_sha256,
            "inventory_overlay_sha256": current_inventory.overlay_sha256,
            "aimi_authority_record_sha256": _file_sha256(authority_record_path),
            "nominal_product_page_sha256": _file_sha256(product_page_path),
            "nominal_coa_sha256": _file_sha256(coa_path),
        },
        "blockers": blockers,
        "authority": authority,
        "side_effects": side_effects,
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint4ContractError",
    "DEFAULT_INVENTORY_TEXT_PATH",
    "DEFAULT_SUCCESSOR_PATH",
    "evaluate_r6_aimi_checkpoint4_readiness",
]
