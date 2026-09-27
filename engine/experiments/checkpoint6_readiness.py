"""Read-only Checkpoint 6 documentary lineage intake for the R6 successor.

Checkpoint 6 is deliberately non-operational.  It verifies the frozen
Checkpoint 5 report, the physical-lineage implementation bytes, and the
documentary schema needed before an inventory candidate may become a backend
stock binding.  Missing evidence is reported as missing; this module never
creates a build plan, stock preparation, reservation, compounding run, mixer
command, transfer receipt, inventory mutation, or formula mutation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.experiments.checkpoint5_readiness import (
    Checkpoint5ContractError,
    evaluate_r6_checkpoint5_readiness,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
)

_SCHEMA_VERSION = "lavande-ambre-profond-r6-cp6-physical-lineage-intake-v1"
_PROTOCOL_STATE = "FROZEN_NONEXECUTING_DOCUMENTARY_INTAKE_CONTRACT"
_CHECKPOINT6_BLOCKERS = [
    "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
    "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
]
_CANONICAL_EVIDENCE_KEYS = (
    "bottle_lot_receipts",
    "backend_stock_mapping_receipts",
    "liquid_conversion_receipts",
    "child_stock_preparation_receipts",
    "sub_10_ul_route_receipts",
    "build_plan_bindings",
    "inventory_reservations",
)
_EXPECTED_REQUIRED_FIELDS = {
    "required_bottle_lot_fields": [
        "source_row",
        "candidate_stock_id",
        "bottle_id",
        "lot_or_batch_id",
        "label_evidence_sha256",
        "supplier_or_preparer",
        "captured_at",
        "reviewer",
        "admission_receipt_id",
    ],
    "required_backend_stock_mapping_fields": [
        "source_row",
        "candidate_stock_id",
        "backend_stock_solution_id",
        "identity_evidence_sha256",
        "admission_receipt_id",
    ],
    "required_density_fields": [
        "source_row",
        "candidate_stock_id",
        "density_g_ml_decimal",
        "temperature_c_decimal",
        "method",
        "standard_uncertainty_decimal",
        "provenance_sha256",
        "admission_receipt_id",
    ],
    "required_weighed_mass_fields": [
        "source_row",
        "candidate_stock_id",
        "target_weighed_stock_mass_g_decimal",
        "method",
        "standard_uncertainty_g_decimal",
        "measurement_receipt_sha256",
        "admission_receipt_id",
    ],
}
_SUPPORTED_INVARIANTS = [
    "FINITE_DECIMAL_QUANTITIES",
    "W_W_REQUIRES_MASS",
    "V_V_REQUIRES_VOLUME",
    "PREPARATION_CONSERVATION",
    "EXACT_STOCK_FRACTION_AND_BASIS_MATCH",
    "DENSITY_AND_PROVENANCE_REQUIRED_FOR_VOLUME_BINDING",
    "EXACT_FORMULA_COMPONENT_MASS_MATCH",
    "COMPLETE_ALL_LINE_BINDING",
    "BASKET_FIRST_DESCENDING_LIQUID_ORDER",
    "APPEND_ONLY_FALSE_AUTHORITY_RECORDS",
]
_ADMISSION_GAPS = [
    "INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_UNRESOLVED",
    "PLAN_LEVEL_LINEAGE_RECEIPTS_ARE_UNVERIFIED_STRINGS",
    "PREPARATION_RECEIPT_OPTIONAL_AT_BINDER_BOUNDARY",
    "PER_ROW_BOTTLE_LOT_RECEIPT_NOT_REPRESENTED",
    "CARRIER_PROVENANCE_NOT_CANONICALLY_RESOLVED",
    "DENSITY_PROVENANCE_IS_TEXT_NOT_RECEIPT_BOUND",
    "EXACT_TARGET_WEIGHED_MASS_ROUTE_NOT_ACCEPTED_BY_VOLUME_BINDER",
    "NEXT_COMMAND_IS_STATE_CHANGING_NOT_DOCUMENTARY",
]
_EXPECTED_PREPARATIONS = (
    {
        "source_row": 31,
        "material": "Heliotropal / piperonal",
        "parent_candidate_stock_id": "inventory:v5:593f575b080f30401f9b",
        "target_fraction_decimal": "0.1",
        "target_basis": "W_W",
        "target_carrier": "DPG",
        "receipt_state": "MISSING",
    },
    {
        "source_row": 59,
        "material": "Black Pepper EO",
        "parent_candidate_stock_id": "inventory:v5:4bb69da9b62fe8fbd8bb",
        "target_fraction_decimal": "0.1",
        "target_basis": "V_V",
        "target_carrier": "ethanol",
        "receipt_state": "MISSING",
    },
    {
        "source_row": 63,
        "material": "Nutmeg EO",
        "parent_candidate_stock_id": (
            "inventory:user-20260830:caa7c7f7418d43c86660"
        ),
        "target_fraction_decimal": "0.1",
        "target_basis": "V_V",
        "target_carrier": "ethanol",
        "receipt_state": "MISSING",
    },
)
_EXPECTED_SUB_10_ROUTES = (
    {
        "source_row": 20,
        "material": "Haitian Vetiver EO",
        "nominal_amount_ul": "5",
        "route_receipt_state": "MISSING",
    },
    {
        "source_row": 43,
        "material": "Linalool Oxide",
        "nominal_amount_ul": "5",
        "route_receipt_state": "MISSING",
    },
    {
        "source_row": 68,
        "material": "Rosemary EO",
        "nominal_amount_ul": "5",
        "route_receipt_state": "MISSING",
    },
)


class Checkpoint6ContractError(ValueError):
    """Raised when the Checkpoint 6 intake contract cannot be trusted."""


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
        raise Checkpoint6ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint6ContractError(f"{label} must be a JSON object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint6ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint6ContractError(f"{label} must be a list")
    return value


def _resolve_pinned_path(
    path_text: object,
    expected_sha256: object,
    *,
    label: str,
) -> Path:
    path = (REPOSITORY_ROOT / str(path_text or "")).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint6ContractError(f"{label} escapes repository")
    if not path.is_file() or _file_sha256(path) != expected_sha256:
        raise Checkpoint6ContractError(f"{label} hash drift")
    return path


def _validate_protocol_contract(protocol: Mapping[str, Any]) -> None:
    if protocol.get("schema_version") != _SCHEMA_VERSION:
        raise Checkpoint6ContractError("unsupported Checkpoint 6 schema")
    if protocol.get("state") != _PROTOCOL_STATE:
        raise Checkpoint6ContractError("Checkpoint 6 protocol state drift")

    authority = _require_mapping(protocol.get("authority"), "Checkpoint 6 authority")
    if authority.get("checkpoint6_intake_contract_record_authorized") is not True:
        raise Checkpoint6ContractError("Checkpoint 6 record authority missing")
    if any(
        value is not False
        for key, value in authority.items()
        if key != "checkpoint6_intake_contract_record_authorized"
    ):
        raise Checkpoint6ContractError("Checkpoint 6 authority boundary drift")

    side_effects = _require_mapping(protocol.get("side_effects"), "side effects")
    if not side_effects or any(value is not False for value in side_effects.values()):
        raise Checkpoint6ContractError("Checkpoint 6 side-effect boundary drift")

    evidence = _require_mapping(
        protocol.get("canonical_current_evidence"), "canonical current evidence"
    )
    if set(evidence) != set(_CANONICAL_EVIDENCE_KEYS) or any(
        _require_list(evidence.get(key), f"canonical evidence {key}")
        for key in _CANONICAL_EVIDENCE_KEYS
    ):
        raise Checkpoint6ContractError(
            "Checkpoint 6 canonical evidence must remain empty"
        )

    prerequisite = _require_mapping(
        protocol.get("checkpoint5_prerequisite"), "Checkpoint 5 prerequisite"
    )
    if prerequisite != {
        "required_state": "PASS_CP5_INPUTS_FROZEN_NONEXECUTABLE",
        "observed_state": "HOLD_CP5_INPUTS_INCOMPLETE",
        "satisfied": False,
        "bypass_allowed": False,
    }:
        raise Checkpoint6ContractError("Checkpoint 5 prerequisite drift")

    boundary = _require_mapping(
        protocol.get("candidate_identity_boundary"), "candidate identity boundary"
    )
    if (
        boundary.get("candidate_field") != "intended_stock_id"
        or boundary.get("required_bridge")
        != "ADJUDICATED_INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_RECEIPT"
        or boundary.get("automatic_namespace_translation_allowed") is not False
        or any(
            boundary.get(key) is not False
            for key in (
                "candidate_is_backend_stock_solution_id",
                "candidate_is_bottle_lot_receipt",
                "candidate_is_preparation_receipt",
                "candidate_is_physical_binding",
            )
        )
    ):
        raise Checkpoint6ContractError("candidate identity boundary drift")

    evidence_schema = _require_mapping(
        protocol.get("documentary_evidence_schema"), "documentary evidence schema"
    )
    if (
        evidence_schema.get("required_source_row_count") != 63
        or evidence_schema.get("bottle_lot_receipt_required_for_every_row")
        is not True
        or evidence_schema.get("backend_stock_mapping_required_for_every_row")
        is not True
        or evidence_schema.get("liquid_conversion_evidence_required_row_count")
        != 62
        or evidence_schema.get("solid_direct_mass_row_count") != 1
        or evidence_schema.get("allowed_liquid_conversion_routes")
        != [
            "LOT_SPECIFIC_DENSITY_WITH_IMMUTABLE_PROVENANCE",
            "EXACT_TARGET_WEIGHED_STOCK_MASS",
        ]
        or evidence_schema.get("generic_density_allowed") is not False
        or evidence_schema.get("mass_volume_never_summed") is not True
        or evidence_schema.get("missing_values_are_never_imputed") is not True
        or evidence_schema.get("documentary_completion_is_not_execution_authority")
        is not True
        or any(
            evidence_schema.get(key) != value
            for key, value in _EXPECTED_REQUIRED_FIELDS.items()
        )
    ):
        raise Checkpoint6ContractError("documentary evidence schema drift")

    preparations = [
        dict(_require_mapping(value, "required child preparation"))
        for value in _require_list(
            protocol.get("required_child_stock_preparations"),
            "required child stock preparations",
        )
    ]
    if preparations != list(_EXPECTED_PREPARATIONS):
        raise Checkpoint6ContractError("required child preparation drift")
    sub_10_routes = [
        dict(_require_mapping(value, "required sub-10 uL route"))
        for value in _require_list(
            protocol.get("required_sub_10_ul_routes"), "required sub-10 uL routes"
        )
    ]
    if sub_10_routes != list(_EXPECTED_SUB_10_ROUTES):
        raise Checkpoint6ContractError("required sub-10 uL route drift")

    audit = _require_mapping(
        protocol.get("operational_interface_audit"), "operational interface audit"
    )
    if (
        audit.get("operational_service_calls_allowed_in_checkpoint6") is not False
        or audit.get("persistent_api_changes_allowed_in_checkpoint6") is not False
        or _require_list(audit.get("supported_invariants"), "supported invariants")
        != _SUPPORTED_INVARIANTS
        or _require_list(audit.get("admission_gaps"), "admission gaps")
        != _ADMISSION_GAPS
    ):
        raise Checkpoint6ContractError("operational interface audit drift")

    blockers = _require_list(protocol.get("checkpoint6_blockers"), "blockers")
    if blockers != _CHECKPOINT6_BLOCKERS:
        raise Checkpoint6ContractError("Checkpoint 6 blocker set drift")

    contract = _require_mapping(
        protocol.get("checkpoint6_contract"), "Checkpoint 6 contract"
    )
    if contract != {
        "state": "SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD",
        "hold_state": "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE",
        "future_pass_state": "PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED",
        "formula_action": "DESIGN_SUCCESSOR_UNCHANGED",
        "all_line_documentary_preconditions_complete": False,
        "physical_binding_state": "NOT_CREATED",
        "reservation_state": "NOT_CREATED",
        "compounding_state": "NOT_STARTED",
        "formula_modified": False,
        "inventory_modified": False,
    }:
        raise Checkpoint6ContractError("Checkpoint 6 outcome contract drift")


def evaluate_r6_checkpoint6_readiness(
    *,
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
) -> dict[str, object]:
    """Return the deterministic, fail-closed Checkpoint 6 documentary census."""

    protocol = _load_object(protocol_path, "Checkpoint 6 protocol")
    _validate_protocol_contract(protocol)
    inputs = _require_mapping(protocol.get("inputs"), "Checkpoint 6 inputs")
    cp5_protocol_path = _resolve_pinned_path(
        inputs.get("checkpoint5_protocol_path"),
        inputs.get("checkpoint5_protocol_sha256"),
        label="Checkpoint 5 protocol",
    )
    _resolve_pinned_path(
        inputs.get("checkpoint5_evaluator_path"),
        inputs.get("checkpoint5_evaluator_sha256"),
        label="Checkpoint 5 evaluator",
    )

    implementation = _require_mapping(
        protocol.get("implementation_surface"), "implementation surface"
    )
    implementation_fingerprints: dict[str, dict[str, str]] = {}
    for key in (
        "physical_lineage_service",
        "physical_lineage_schema",
        "physical_lineage_model",
        "physical_lineage_migration",
    ):
        record = _require_mapping(implementation.get(key), key)
        path = _resolve_pinned_path(
            record.get("path"), record.get("sha256"), label=key
        )
        implementation_fingerprints[key] = {
            "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
            "sha256": _file_sha256(path),
        }

    try:
        checkpoint5 = evaluate_r6_checkpoint5_readiness(
            protocol_path=cp5_protocol_path
        )
    except Checkpoint5ContractError as exc:
        raise Checkpoint6ContractError(
            "Checkpoint 5 evaluation failed closed"
        ) from exc

    if checkpoint5.get("report_sha256") != inputs.get("checkpoint5_report_sha256"):
        raise Checkpoint6ContractError("Checkpoint 5 report hash drift")
    if (
        checkpoint5.get("input_integrity_state") != "VERIFIED"
        or checkpoint5.get("checkpoint5_state")
        != "SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD"
        or checkpoint5.get("input_completion_state") != "HOLD_CP5_INPUTS_INCOMPLETE"
        or checkpoint5.get("successor_rows_sha256")
        != inputs.get("r6_successor_rows_sha256")
    ):
        raise Checkpoint6ContractError("Checkpoint 5 prerequisite report drift")
    cp5_fingerprints = _require_mapping(
        checkpoint5.get("fingerprints"), "Checkpoint 5 fingerprints"
    )
    for key in (
        "inventory_text_sha256",
        "inventory_snapshot_sha256",
        "inventory_overlay_sha256",
    ):
        if cp5_fingerprints.get(key) != inputs.get(key):
            raise Checkpoint6ContractError(f"Checkpoint 5 {key} drift")

    rows = [
        _require_mapping(value, "Checkpoint 5 row")
        for value in _require_list(
            checkpoint5.get("row_gap_census"), "Checkpoint 5 row census"
        )
    ]
    if len(rows) != 63 or len({row.get("source_row") for row in rows}) != 63:
        raise Checkpoint6ContractError("Checkpoint 5 row coverage drift")

    preparation_rows = {item["source_row"] for item in _EXPECTED_PREPARATIONS}
    sub_10_rows = {item["source_row"] for item in _EXPECTED_SUB_10_ROUTES}
    row_intake: list[dict[str, object]] = []
    for row in rows:
        source_row = int(row["source_row"])
        amount_unit = str(row.get("amount_unit") or "")
        is_liquid = amount_unit == "µL"
        reasons = [
            "INVENTORY_ID_IS_CANDIDATE_NOT_BACKEND_STOCK_BINDING",
            "BACKEND_STOCK_MAPPING_RECEIPT_MISSING",
            "BOTTLE_LOT_RECEIPT_MISSING",
        ]
        if is_liquid:
            reasons.append("LIQUID_MASS_CONVERSION_RECEIPT_MISSING")
        if source_row in preparation_rows:
            reasons.append("CHILD_STOCK_PREPARATION_RECEIPT_MISSING")
        if source_row in sub_10_rows:
            reasons.append("SUB_10_UL_ROUTE_RECEIPT_MISSING")
        if source_row == 47:
            reasons.append("AIMI_BOTTLE_SPECIFIC_EVIDENCE_MISSING")

        row_intake.append(
            {
                "source_row": source_row,
                "basket": row.get("basket"),
                "material": row.get("material"),
                "amount_decimal": row.get("amount_decimal"),
                "amount_unit": amount_unit,
                "candidate_stock_id": row.get("intended_stock_id"),
                "candidate_state": row.get("candidate_state"),
                "concentration_fraction_decimal": row.get(
                    "concentration_fraction_decimal"
                ),
                "concentration_basis": row.get("concentration_basis"),
                "carrier": row.get("carrier"),
                "physical_form": row.get("physical_form"),
                "backend_stock_solution_id": None,
                "bottle_lot_receipt_ref": None,
                "liquid_conversion_receipt_ref": None,
                "child_stock_preparation_receipt_ref": None,
                "sub_10_ul_route_receipt_ref": None,
                "row_documentary_preconditions_complete": False,
                "physical_binding_eligible": False,
                "holds": reasons,
            }
        )

    candidate_ids = {
        str(row["candidate_stock_id"])
        for row in row_intake
        if row["candidate_stock_id"]
    }
    liquid_count = sum(row["amount_unit"] == "µL" for row in row_intake)
    solid_count = sum(row["amount_unit"] == "mg" for row in row_intake)
    if len(candidate_ids) != 63 or liquid_count != 62 or solid_count != 1:
        raise Checkpoint6ContractError("Checkpoint 6 dimensional census drift")

    contract = _require_mapping(
        protocol.get("checkpoint6_contract"), "Checkpoint 6 contract"
    )
    prerequisite = _require_mapping(
        protocol.get("checkpoint5_prerequisite"), "Checkpoint 5 prerequisite"
    )
    evidence_schema = _require_mapping(
        protocol.get("documentary_evidence_schema"), "documentary evidence schema"
    )
    identity_boundary = _require_mapping(
        protocol.get("candidate_identity_boundary"), "candidate identity boundary"
    )
    audit = _require_mapping(
        protocol.get("operational_interface_audit"), "operational interface audit"
    )
    authority = dict(_require_mapping(protocol.get("authority"), "authority"))
    side_effects = dict(
        _require_mapping(protocol.get("side_effects"), "side effects")
    )

    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r6-cp6-readiness-report-v1",
        "status": "HOLD",
        "checkpoint6_state": contract.get("state"),
        "documentary_input_completion_state": contract.get("hold_state"),
        "input_integrity_state": "VERIFIED",
        "checkpoint5_prerequisite": dict(prerequisite),
        "candidate_identity_boundary": dict(identity_boundary),
        "documentary_evidence_schema": dict(evidence_schema),
        "required_child_stock_preparations": [
            dict(item) for item in _EXPECTED_PREPARATIONS
        ],
        "required_sub_10_ul_routes": [
            dict(item) for item in _EXPECTED_SUB_10_ROUTES
        ],
        "documentary_census": {
            "row_count": len(row_intake),
            "candidate_stock_row_count": sum(
                bool(row["candidate_stock_id"]) for row in row_intake
            ),
            "unique_candidate_stock_count": len(candidate_ids),
            "bottle_lot_receipt_complete_row_count": 0,
            "bottle_lot_receipt_missing_row_count": len(row_intake),
            "backend_stock_mapping_complete_row_count": 0,
            "backend_stock_mapping_missing_row_count": len(row_intake),
            "liquid_conversion_complete_row_count": 0,
            "liquid_conversion_missing_row_count": liquid_count,
            "solid_direct_mass_row_count": solid_count,
            "child_stock_preparation_complete_row_count": 0,
            "child_stock_preparation_missing_row_count": len(preparation_rows),
            "sub_10_ul_route_complete_row_count": 0,
            "sub_10_ul_route_missing_row_count": len(sub_10_rows),
            "row_documentary_preconditions_complete_count": 0,
            "physical_binding_eligible_row_count": 0,
            "build_plan_binding_count": 0,
            "inventory_reservation_count": 0,
        },
        "row_documentary_intake": row_intake,
        "all_line_documentary_preconditions_complete": False,
        "physical_binding_eligible_rows": 0,
        "operational_interface_audit": {
            "supported_invariants": list(
                _require_list(audit.get("supported_invariants"), "supported invariants")
            ),
            "admission_gaps": list(
                _require_list(audit.get("admission_gaps"), "admission gaps")
            ),
            "operational_service_calls_allowed_in_checkpoint6": False,
            "persistent_api_changes_allowed_in_checkpoint6": False,
        },
        "blockers": list(_CHECKPOINT6_BLOCKERS),
        "formula_action": contract.get("formula_action"),
        "physical_binding_state": contract.get("physical_binding_state"),
        "reservation_state": contract.get("reservation_state"),
        "compounding_state": contract.get("compounding_state"),
        "authority": authority,
        "side_effects": side_effects,
        "fingerprints": {
            "checkpoint6_protocol_sha256": _file_sha256(protocol_path),
            "checkpoint5_protocol_sha256": _file_sha256(cp5_protocol_path),
            "checkpoint5_report_sha256": checkpoint5["report_sha256"],
            "r6_successor_rows_sha256": checkpoint5["successor_rows_sha256"],
            "inventory_text_sha256": cp5_fingerprints["inventory_text_sha256"],
            "inventory_snapshot_sha256": cp5_fingerprints[
                "inventory_snapshot_sha256"
            ],
            "inventory_overlay_sha256": cp5_fingerprints[
                "inventory_overlay_sha256"
            ],
            "implementation_surface": implementation_fingerprints,
        },
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint6ContractError",
    "DEFAULT_PROTOCOL_PATH",
    "evaluate_r6_checkpoint6_readiness",
]
