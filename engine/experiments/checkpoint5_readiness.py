"""Read-only Checkpoint 5 input census for the R6 AIMI successor.

The evaluator joins the immutable R6 row delta, the Checkpoint 3 stock
candidate audit, the live materialized inventory, and the frozen R6
measurement contract.  It records missing physical inputs without preparing a
stock, binding a build plan, reserving inventory, emitting a mixer command, or
promoting any scientific, sensory, safety, compounding, or release claim.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.experiments.checkpoint3_readiness import (
    evaluate_r5_checkpoint3_readiness,
)
from engine.experiments.checkpoint4_readiness import (
    evaluate_r6_aimi_checkpoint4_readiness,
)
from engine.inventory_parser import (
    CurrentInventoryMaterialization,
    InventoryMaterial,
    materialize_current_inventory,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
)
DEFAULT_INVENTORY_TEXT_PATH = REPOSITORY_ROOT / "inventory.txt"


class Checkpoint5ContractError(ValueError):
    """Raised when the Checkpoint 5 input contract is structurally unusable."""


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
        raise Checkpoint5ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint5ContractError(f"{label} must be a JSON object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint5ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint5ContractError(f"{label} must be a list")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise Checkpoint5ContractError(f"{label} must be an integer")
    try:
        return int(value)
    except ValueError as exc:
        raise Checkpoint5ContractError(f"{label} must be an integer") from exc


def _resolve_pinned_path(
    inputs: Mapping[str, Any],
    *,
    path_key: str,
    hash_key: str,
    label: str,
) -> Path:
    relative = str(inputs.get(path_key) or "")
    expected = str(inputs.get(hash_key) or "")
    path = (REPOSITORY_ROOT / relative).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint5ContractError(f"{label} escapes repository")
    if not path.is_file() or _file_sha256(path) != expected:
        raise Checkpoint5ContractError(f"{label} hash drift")
    return path


def _decimal_text(value: object) -> str:
    normalized = Decimal(str(value)).normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _stock_payload(stock: InventoryMaterial) -> dict[str, object]:
    return {
        "stock_id": stock.stock_id,
        "name": stock.name,
        "identity_name": stock.identity_name,
        "concentration_fraction_decimal": _decimal_text(stock.dilution),
        "concentration_basis": stock.fraction_basis,
        "carrier": stock.carrier,
        "physical_form": stock.physical_form,
        "status": stock.status,
        "execution_ready": stock.execution_ready,
        "authority": stock.authority,
        "source_ref": stock.source_ref,
    }


def _successor_rows(
    successor: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], Path]:
    parent_ref = _require_mapping(successor.get("parent"), "R6 parent reference")
    parent_path = (REPOSITORY_ROOT / str(parent_ref.get("path") or "")).resolve()
    if not parent_path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint5ContractError("R6 parent reference escapes repository")
    if not parent_path.is_file() or _file_sha256(parent_path) != parent_ref.get(
        "sha256"
    ):
        raise Checkpoint5ContractError("R6 parent comparator hash drift")
    parent = _load_object(parent_path, "R5 parent comparator")
    parent_rows = [
        dict(_require_mapping(row, "R5 parent row"))
        for row in _require_list(parent.get("rows"), "R5 parent rows")
    ]
    if _canonical_sha256(parent_rows) != parent_ref.get("canonical_rows_sha256"):
        raise Checkpoint5ContractError("R5 parent row hash drift")

    replacement = _require_mapping(successor.get("row_replacement"), "R6 replacement")
    parent_row = dict(
        _require_mapping(replacement.get("parent_row"), "R6 replacement parent row")
    )
    successor_row = dict(
        _require_mapping(
            replacement.get("successor_row"), "R6 replacement successor row"
        )
    )
    rows = [successor_row if row == parent_row else dict(row) for row in parent_rows]
    invariants = _require_mapping(
        successor.get("successor_invariants"), "R6 successor invariants"
    )
    if _canonical_sha256(rows) != invariants.get("successor_canonical_rows_sha256"):
        raise Checkpoint5ContractError("R6 successor row hash drift")
    return rows, parent_path


def _receipt_states(
    *,
    candidate_state: str,
    source_row: int,
    stock: InventoryMaterial,
) -> tuple[str, str]:
    if source_row == 47:
        return (
            "LABEL_AND_STOCK_ID_BOUND_LOT_RECEIPT_MISSING",
            "NOT_APPLICABLE_DIRECT_NEAT_STOCK",
        )
    if candidate_state == "CANDIDATE_PREPARATION_REQUIRED":
        return (
            "PARENT_STOCK_PRESENT_CHILD_RECEIPT_MISSING",
            "MISSING_REQUIRED_CHILD_PREPARATION",
        )
    if candidate_state == "CANDIDATE_RECEIPT_INCOMPLETE":
        return (
            "KNOWN_INCOMPLETE",
            (
                "MISSING_OR_INCOMPLETE_EXISTING_STOCK_RECEIPT"
                if Decimal(str(stock.dilution)) < Decimal(1)
                else "NOT_APPLICABLE_DIRECT_STOCK_PREPARATION"
            ),
        )
    return (
        "NOT_ASSERTED_COMPLETE_IN_CP5_INPUTS",
        (
            "EXISTING_STOCK_RECEIPT_NOT_ADJUDICATED"
            if Decimal(str(stock.dilution)) < Decimal(1)
            else "NOT_APPLICABLE_DIRECT_STOCK_PREPARATION"
        ),
    )


def _validate_protocol_contract(protocol: Mapping[str, Any]) -> None:
    if protocol.get("schema_version") != (
        "lavande-ambre-profond-r6-cp5-execution-input-protocol-v1"
    ):
        raise Checkpoint5ContractError("unsupported Checkpoint 5 schema")
    if protocol.get("state") != "FROZEN_NONEXECUTABLE_INPUT_COLLECTION_CONTRACT":
        raise Checkpoint5ContractError("Checkpoint 5 protocol state drift")

    authority = _require_mapping(protocol.get("authority"), "Checkpoint 5 authority")
    if authority.get("checkpoint5_input_contract_record_authorized") is not True or any(
        value is not False
        for key, value in authority.items()
        if key != "checkpoint5_input_contract_record_authorized"
    ):
        raise Checkpoint5ContractError("Checkpoint 5 authority boundary drift")

    aimi = _require_mapping(protocol.get("aimi_scope_contract"), "AIMI scope")
    if (
        aimi.get("scope_state") != "BOTTLE_SPECIFIC_EMPIRICAL_REQUIRED"
        or aimi.get("reference_disposition")
        != "REFERENCE_NOT_USED_FOR_QUANTITATIVE_APPLICABILITY"
        or aimi.get("reference_linked_properties_allowed") is not False
        or aimi.get("family_or_description_equivalence_allowed") is not False
        or aimi.get("supplier_reference_proves_owned_bottle_identity") is not False
    ):
        raise Checkpoint5ContractError("AIMI bottle-specific scope drift")

    constant_total = _require_mapping(
        protocol.get("constant_total_basis_contract"), "constant-total contract"
    )
    if (
        constant_total.get("selected_basis") != "active_mass_g"
        or constant_total.get("constant_total_amount_decimal") is not None
        or constant_total.get("conversion_inputs_complete") is not False
        or constant_total.get("generic_density_allowed") is not False
        or constant_total.get("solid_mass_kept_separate") is not True
        or constant_total.get("mass_volume_never_summed") is not True
    ):
        raise Checkpoint5ContractError("constant-total authority drift")

    measurement = _require_mapping(
        protocol.get("measurement_protocol_contract"), "measurement protocol"
    )
    if (
        measurement.get("execution_ready") is not False
        or measurement.get("documentary_r5_is_physical_comparator") is not False
        or measurement.get("resolved_execution_parameters") != {}
        or _require_mapping(measurement.get("endpoints"), "measurement endpoints").get(
            "beauty"
        )
        != "PROHIBITED_DERIVED_ENDPOINT"
    ):
        raise Checkpoint5ContractError("measurement authority drift")


def evaluate_r6_checkpoint5_readiness(
    *,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    inventory_text_path: Path = DEFAULT_INVENTORY_TEXT_PATH,
    inventory: CurrentInventoryMaterialization | None = None,
) -> dict[str, object]:
    """Return the deterministic, fail-closed R6 Checkpoint 5 input census."""

    protocol = _load_object(protocol_path, "Checkpoint 5 protocol")
    _validate_protocol_contract(protocol)
    inputs = _require_mapping(protocol.get("inputs"), "Checkpoint 5 inputs")
    successor_path = _resolve_pinned_path(
        inputs,
        path_key="r6_successor_path",
        hash_key="r6_successor_sha256",
        label="R6 successor",
    )
    checkpoint3_path = _resolve_pinned_path(
        inputs,
        path_key="checkpoint3_protocol_path",
        hash_key="checkpoint3_protocol_sha256",
        label="Checkpoint 3 protocol",
    )
    measurement_schema_path = _resolve_pinned_path(
        inputs,
        path_key="measurement_schema_path",
        hash_key="measurement_schema_sha256",
        label="measurement schema",
    )
    pinned_inventory_path = _resolve_pinned_path(
        inputs,
        path_key="inventory_text_path",
        hash_key="inventory_text_sha256",
        label="inventory text",
    )
    if pinned_inventory_path != inventory_text_path.resolve():
        raise Checkpoint5ContractError("inventory path differs from pinned input")

    current_inventory = inventory or materialize_current_inventory()
    dynamic_blockers: list[str] = []
    if (
        current_inventory.snapshot_sha256 != inputs.get("inventory_snapshot_sha256")
        or current_inventory.overlay_sha256 != inputs.get("inventory_overlay_sha256")
    ):
        dynamic_blockers.append("HOLD_CP5_INVENTORY_FINGERPRINT_DRIFT")

    checkpoint4 = evaluate_r6_aimi_checkpoint4_readiness(
        successor_path=successor_path,
        inventory_text_path=inventory_text_path,
        inventory=current_inventory,
    )
    if checkpoint4.get("input_integrity_state") != "VERIFIED":
        dynamic_blockers.append("HOLD_CP5_CHECKPOINT4_DRIFT")

    checkpoint3 = evaluate_r5_checkpoint3_readiness(
        protocol_path=checkpoint3_path,
        inventory_text_path=inventory_text_path,
        inventory=current_inventory,
    )
    if checkpoint3.get("input_integrity_state") != "VERIFIED":
        dynamic_blockers.append("HOLD_CP5_CHECKPOINT3_DRIFT")

    successor = _load_object(successor_path, "R6 successor")
    successor_rows, parent_path = _successor_rows(successor)
    if _canonical_sha256(successor_rows) != inputs.get("r6_successor_rows_sha256"):
        dynamic_blockers.append("HOLD_CP5_SUCCESSOR_ROWSET_DRIFT")
    if len(successor_rows) != 63:
        dynamic_blockers.append("HOLD_CP5_ROW_COUNT_DRIFT")

    measurement_schema = _load_object(measurement_schema_path, "measurement schema")
    base_measurement = _require_mapping(
        measurement_schema.get("measurement_protocol_contract"),
        "base measurement protocol",
    )
    measurement = _require_mapping(
        protocol.get("measurement_protocol_contract"),
        "Checkpoint 5 measurement protocol",
    )
    if (
        base_measurement.get("domains_must_remain_separate")
        != measurement.get("domains_must_remain_separate")
        or _require_mapping(
            base_measurement.get("endpoints"), "base measurement endpoints"
        ).get("beauty")
        != "PROHIBITED_DERIVED_ENDPOINT"
    ):
        dynamic_blockers.append("HOLD_CP5_MEASUREMENT_SCHEMA_DRIFT")

    cp3_candidates = {
        _integer(item.get("source_row"), "Checkpoint 3 candidate source row"): item
        for raw in _require_list(
            checkpoint3.get("row_candidate_audit"), "Checkpoint 3 row audit"
        )
        for item in [_require_mapping(raw, "Checkpoint 3 row candidate")]
    }
    stock_by_id = {stock.stock_id: stock for stock in current_inventory.stocks}
    aimi_scope = _require_mapping(protocol.get("aimi_scope_contract"), "AIMI scope")
    aimi_stock_id = str(aimi_scope.get("stock_id") or "")

    sub_10_contract = _require_mapping(
        protocol.get("sub_10_ul_contract"), "sub-10 uL contract"
    )
    sub_10_rows = {
        _integer(item.get("source_row"), "sub-10 uL source row"): item
        for raw in _require_list(sub_10_contract.get("rows"), "sub-10 uL rows")
        for item in [_require_mapping(raw, "sub-10 uL row")]
    }

    row_census: list[dict[str, object]] = []
    for raw_row in successor_rows:
        row = _require_mapping(raw_row, "R6 successor row")
        source_row = _integer(row.get("source_row"), "R6 source row")
        candidate = cp3_candidates.get(source_row)
        if candidate is None:
            raise Checkpoint5ContractError(
                f"R6 row {source_row} lacks a Checkpoint 3 candidate"
            )
        if source_row == 47:
            intended_stock_id = aimi_stock_id
            candidate_state = "CANDIDATE_BOTTLE_SPECIFIC_REFERENCE_WITHHELD"
        else:
            intended_stock_id = str(candidate.get("candidate_stock_id") or "")
            candidate_state = str(candidate.get("candidate_state") or "")
        stock = stock_by_id.get(intended_stock_id)
        if stock is None:
            raise Checkpoint5ContractError(
                f"R6 row {source_row} intended stock is unavailable"
            )

        stock_data = _stock_payload(stock)
        bottle_state, preparation_state = _receipt_states(
            candidate_state=candidate_state,
            source_row=source_row,
            stock=stock,
        )
        amount = Decimal(str(row.get("dose")))
        unit = str(row.get("unit") or "")
        is_liquid = unit == "µL"
        is_sub_10 = is_liquid and amount < Decimal("10")
        route = sub_10_rows.get(source_row)
        if is_sub_10:
            if (
                route is None
                or str(route.get("material")) != str(row.get("material"))
                or Decimal(str(route.get("nominal_amount_ul"))) != amount
                or route.get("route_state") != "UNRESOLVED"
            ):
                raise Checkpoint5ContractError(
                    f"R6 row {source_row} sub-10 uL route drift"
                )
            sub_10_state = (
                "UNRESOLVED_PREPARED_DILUTION_OR_QUALIFIED_DIRECT_MEASUREMENT"
            )
        else:
            if route is not None:
                raise Checkpoint5ContractError(
                    f"R6 row {source_row} has a spurious sub-10 uL route"
                )
            sub_10_state = "NOT_APPLICABLE"

        row_holds = ["ALL_LINE_BUILD_BINDING_NOT_AUTHORIZED"]
        if is_liquid:
            density_state = "MISSING_DENSITY_OR_TARGET_WEIGHED_MASS"
            conversion_state = "HOLD_ACTIVE_MASS_CONVERSION_INPUT_MISSING"
            row_holds.append("MASS_CONVERSION_INPUT_MISSING")
        else:
            density_state = "NOT_REQUIRED_DIRECT_MASS"
            conversion_state = "DIRECT_MASS_DIMENSION"
        if candidate_state == "CANDIDATE_PREPARATION_REQUIRED":
            row_holds.append("REQUIRED_WORKING_STOCK_NOT_PREPARED")
        if bottle_state != "COMPLETE":
            row_holds.append("BOTTLE_LOT_OR_PREPARATION_EVIDENCE_UNVERIFIED")
        if is_sub_10:
            row_holds.append("SUB_10_UL_ROUTE_UNRESOLVED")
        if source_row == 47:
            row_holds.append("AIMI_BOTTLE_SPECIFIC_MEASUREMENT_PENDING")

        row_census.append(
            {
                "source_row": source_row,
                "basket": row.get("basket"),
                "material": row.get("material"),
                "amount_decimal": _decimal_text(amount),
                "amount_unit": unit,
                "intended_stock_id": intended_stock_id,
                "candidate_state": candidate_state,
                **stock_data,
                "bottle_lot_evidence_state": bottle_state,
                "preparation_receipt_state": preparation_state,
                "density_or_weighed_mass_state": density_state,
                "dimensional_conversion_state": conversion_state,
                "sub_10_ul_route_state": sub_10_state,
                "physical_binding_eligible": False,
                "row_holds": list(dict.fromkeys(row_holds)),
            }
        )

    if {item["source_row"] for item in row_census} != {
        _integer(row.get("source_row"), "R6 source row") for row in successor_rows
    }:
        dynamic_blockers.append("HOLD_CP5_ROW_CENSUS_COVERAGE_DRIFT")

    gap_fields = set(
        str(value)
        for value in _require_list(
            _require_mapping(
                protocol.get("gap_matrix_contract"), "gap matrix contract"
            ).get("required_fields"),
            "required gap fields",
        )
    )
    if any(not gap_fields.issubset(item) for item in row_census):
        dynamic_blockers.append("HOLD_CP5_GAP_MATRIX_FIELD_DRIFT")

    physical_parameters = [
        str(value)
        for value in _require_list(
            measurement.get("required_physical_parameters"),
            "required physical parameters",
        )
    ]
    sensory_controls = [
        str(value)
        for value in _require_list(
            measurement.get("required_sensory_controls"),
            "required sensory controls",
        )
    ]
    resolved_parameters = _require_mapping(
        measurement.get("resolved_execution_parameters"),
        "resolved execution parameters",
    )
    unresolved_parameters = [
        value
        for value in physical_parameters + sensory_controls
        if value not in resolved_parameters
    ]

    blocker_ownership = _require_mapping(
        protocol.get("blocker_ownership"), "blocker ownership"
    )
    owned_blockers = [
        str(value)
        for checkpoint in ("checkpoint5", "checkpoint6", "checkpoint7", "checkpoint8")
        for value in _require_list(
            blocker_ownership.get(checkpoint), f"{checkpoint} blockers"
        )
    ]
    if len(owned_blockers) != 9 or len(set(owned_blockers)) != 9 or set(
        owned_blockers
    ) != set(
        str(value)
        for value in _require_list(
            checkpoint4.get("blockers"), "Checkpoint 4 blockers"
        )
    ):
        dynamic_blockers.append("HOLD_CP5_BLOCKER_OWNERSHIP_DRIFT")

    candidate_counts = Counter(str(item["candidate_state"]) for item in row_census)
    census_summary = {
        "row_count": len(row_census),
        "candidate_stock_row_count": sum(
            bool(item["intended_stock_id"]) for item in row_census
        ),
        "candidate_state_counts": dict(sorted(candidate_counts.items())),
        "liquid_row_count": sum(item["amount_unit"] == "µL" for item in row_census),
        "solid_mass_row_count": sum(item["amount_unit"] == "mg" for item in row_census),
        "mass_conversion_input_missing_row_count": sum(
            item["density_or_weighed_mass_state"]
            == "MISSING_DENSITY_OR_TARGET_WEIGHED_MASS"
            for item in row_census
        ),
        "required_working_stock_preparation_row_count": sum(
            item["candidate_state"] == "CANDIDATE_PREPARATION_REQUIRED"
            for item in row_census
        ),
        "sub_10_ul_unresolved_row_count": sum(
            item["sub_10_ul_route_state"]
            == "UNRESOLVED_PREPARED_DILUTION_OR_QUALIFIED_DIRECT_MEASUREMENT"
            for item in row_census
        ),
        "receipt_evidence_unverified_row_count": sum(
            item["bottle_lot_evidence_state"] != "COMPLETE"
            for item in row_census
        ),
        "physical_binding_eligible_row_count": sum(
            item["physical_binding_eligible"] is True for item in row_census
        ),
    }

    contract = _require_mapping(
        protocol.get("checkpoint5_contract"), "Checkpoint 5 contract"
    )
    authority = dict(_require_mapping(protocol.get("authority"), "authority"))
    blockers = list(
        dict.fromkeys(
            dynamic_blockers
            + [
                "HOLD_CP5_BOTTLE_LOT_EVIDENCE_INCOMPLETE",
                "HOLD_CP5_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
                "HOLD_CP5_ROW_MASS_CONVERSION_INPUTS_MISSING",
                "HOLD_CP5_CONSTANT_ACTIVE_MASS_TOTAL_UNDERIVED",
                "HOLD_CP5_SUB_10_UL_ROUTES_UNRESOLVED",
                "HOLD_CP5_MEASUREMENT_EXECUTION_PARAMETERS_UNRESOLVED",
                "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
                "HOLD_EXACT_CURVE_APPLICABILITY",
                "PLEASANTNESS_NOT_ESTABLISHED",
                "PHYSICAL_LIKING_NOT_TESTED",
            ]
        )
    )
    side_effects = {
        "build_plan_created": False,
        "physical_binding_created": False,
        "reservation_created": False,
        "mixer_command_created": False,
        "transfer_record_created": False,
        "prepared_stock_receipt_created": False,
        "inventory_modified": False,
        "physical_formula_modified": False,
        "measurement_executed": False,
        "sensory_evaluation_executed": False,
    }
    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r6-cp5-readiness-report-v1",
        "status": "HOLD",
        "checkpoint5_state": contract.get("state"),
        "input_completion_state": contract.get("hold_state"),
        "input_integrity_state": (
            "VERIFIED" if not dynamic_blockers else "HOLD_DRIFT_DETECTED"
        ),
        "successor_id": checkpoint4.get("successor_id"),
        "formula_action": contract.get("formula_action"),
        "successor_rows_sha256": _canonical_sha256(successor_rows),
        "quantities": checkpoint4.get("quantities"),
        "aimi_scope": dict(aimi_scope),
        "constant_total_basis": dict(
            _require_mapping(
                protocol.get("constant_total_basis_contract"),
                "constant-total contract",
            )
        ),
        "sub_10_ul_contract": dict(sub_10_contract),
        "measurement_protocol": {
            **dict(measurement),
            "unresolved_execution_parameters": unresolved_parameters,
        },
        "blocker_ownership": {
            key: list(_require_list(value, f"{key} blocker ownership"))
            for key, value in blocker_ownership.items()
        },
        "checkpoint5_owned_blocker_dispositions": {
            "HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED": (
                "REFRAMED_REFERENCE_NOT_USED_BOTTLE_SPECIFIC_SCOPE"
            ),
            "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING": (
                "UNRESOLVED_ROW_INPUTS_AND_DERIVED_TOTAL_MISSING"
            ),
            "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED": (
                "UNRESOLVED_R6_PROTOCOL_PARAMETERS"
            ),
        },
        "census_summary": census_summary,
        "row_gap_census": row_census,
        "blockers": blockers,
        "authority": authority,
        "side_effects": side_effects,
        "fingerprints": {
            "checkpoint5_protocol_sha256": _file_sha256(protocol_path),
            "r6_successor_sha256": _file_sha256(successor_path),
            "r5_parent_sha256": _file_sha256(parent_path),
            "checkpoint3_protocol_sha256": _file_sha256(checkpoint3_path),
            "measurement_schema_sha256": _file_sha256(measurement_schema_path),
            "inventory_text_sha256": _file_sha256(inventory_text_path),
            "inventory_snapshot_sha256": current_inventory.snapshot_sha256,
            "inventory_overlay_sha256": current_inventory.overlay_sha256,
        },
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint5ContractError",
    "DEFAULT_INVENTORY_TEXT_PATH",
    "DEFAULT_PROTOCOL_PATH",
    "evaluate_r6_checkpoint5_readiness",
]
