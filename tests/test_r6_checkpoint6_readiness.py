import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint6_readiness import (
    DEFAULT_PROTOCOL_PATH,
    Checkpoint6ContractError,
    evaluate_r6_checkpoint6_readiness,
)

EXPECTED_BLOCKERS = [
    "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
    "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return evaluate_r6_checkpoint6_readiness()


def test_checkpoint6_completes_software_intake_but_holds_physical_readiness(
    report,
) -> None:
    assert report["status"] == "HOLD"
    assert report["checkpoint6_state"] == (
        "SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD"
    )
    assert report["documentary_input_completion_state"] == (
        "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE"
    )
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["formula_action"] == "DESIGN_SUCCESSOR_UNCHANGED"
    assert report["physical_binding_state"] == "NOT_CREATED"
    assert report["reservation_state"] == "NOT_CREATED"
    assert report["compounding_state"] == "NOT_STARTED"


def test_checkpoint6_has_complete_candidate_coverage_but_zero_bindable_rows(
    report,
) -> None:
    census = report["documentary_census"]
    assert census == {
        "row_count": 63,
        "candidate_stock_row_count": 63,
        "unique_candidate_stock_count": 63,
        "bottle_lot_receipt_complete_row_count": 0,
        "bottle_lot_receipt_missing_row_count": 63,
        "backend_stock_mapping_complete_row_count": 0,
        "backend_stock_mapping_missing_row_count": 63,
        "liquid_conversion_complete_row_count": 0,
        "liquid_conversion_missing_row_count": 62,
        "solid_direct_mass_row_count": 1,
        "child_stock_preparation_complete_row_count": 0,
        "child_stock_preparation_missing_row_count": 3,
        "sub_10_ul_route_complete_row_count": 0,
        "sub_10_ul_route_missing_row_count": 3,
        "row_documentary_preconditions_complete_count": 0,
        "physical_binding_eligible_row_count": 0,
        "build_plan_binding_count": 0,
        "inventory_reservation_count": 0,
    }
    rows = report["row_documentary_intake"]
    assert len(rows) == 63
    assert len({row["source_row"] for row in rows}) == 63
    assert report["all_line_documentary_preconditions_complete"] is False
    assert report["physical_binding_eligible_rows"] == 0
    assert all(row["physical_binding_eligible"] is False for row in rows)


def test_checkpoint6_keeps_candidate_ids_outside_backend_authority(report) -> None:
    boundary = report["candidate_identity_boundary"]
    assert boundary["candidate_field"] == "intended_stock_id"
    assert boundary["candidate_is_backend_stock_solution_id"] is False
    assert boundary["candidate_is_bottle_lot_receipt"] is False
    assert boundary["candidate_is_preparation_receipt"] is False
    assert boundary["candidate_is_physical_binding"] is False
    assert boundary["automatic_namespace_translation_allowed"] is False
    assert boundary["required_bridge"] == (
        "ADJUDICATED_INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_RECEIPT"
    )
    assert all(
        row["candidate_stock_id"] and row["backend_stock_solution_id"] is None
        for row in report["row_documentary_intake"]
    )


def test_checkpoint6_records_exact_required_child_preparations(report) -> None:
    assert report["required_child_stock_preparations"] == [
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
    ]
    rows = {
        row["source_row"]: row for row in report["row_documentary_intake"]
    }
    for source_row in (31, 59, 63):
        assert rows[source_row]["child_stock_preparation_receipt_ref"] is None
        assert (
            "CHILD_STOCK_PREPARATION_RECEIPT_MISSING"
            in rows[source_row]["holds"]
        )


def test_checkpoint6_records_exact_sub_10_ul_routes(report) -> None:
    assert [
        (row["source_row"], row["material"], row["nominal_amount_ul"])
        for row in report["required_sub_10_ul_routes"]
    ] == [
        (20, "Haitian Vetiver EO", "5"),
        (43, "Linalool Oxide", "5"),
        (68, "Rosemary EO", "5"),
    ]
    rows = {
        row["source_row"]: row for row in report["row_documentary_intake"]
    }
    for source_row in (20, 43, 68):
        assert rows[source_row]["sub_10_ul_route_receipt_ref"] is None
        assert "SUB_10_UL_ROUTE_RECEIPT_MISSING" in rows[source_row]["holds"]


def test_checkpoint6_keeps_liquid_conversion_and_solid_mass_separate(report) -> None:
    rows = report["row_documentary_intake"]
    liquid_rows = [row for row in rows if row["amount_unit"] == "µL"]
    solid_rows = [row for row in rows if row["amount_unit"] == "mg"]
    assert len(liquid_rows) == 62
    assert all(row["liquid_conversion_receipt_ref"] is None for row in liquid_rows)
    assert len(solid_rows) == 1
    assert solid_rows[0]["material"] == "Ambrox Super"
    assert solid_rows[0]["amount_decimal"] == "300"
    assert "LIQUID_MASS_CONVERSION_RECEIPT_MISSING" not in solid_rows[0]["holds"]
    schema = report["documentary_evidence_schema"]
    assert schema["generic_density_allowed"] is False
    assert schema["mass_volume_never_summed"] is True


def test_checkpoint6_exposes_backend_admission_gaps_without_calling_it(report) -> None:
    audit = report["operational_interface_audit"]
    assert audit["operational_service_calls_allowed_in_checkpoint6"] is False
    assert audit["persistent_api_changes_allowed_in_checkpoint6"] is False
    assert set(audit["admission_gaps"]) == {
        "INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_UNRESOLVED",
        "PLAN_LEVEL_LINEAGE_RECEIPTS_ARE_UNVERIFIED_STRINGS",
        "PREPARATION_RECEIPT_OPTIONAL_AT_BINDER_BOUNDARY",
        "PER_ROW_BOTTLE_LOT_RECEIPT_NOT_REPRESENTED",
        "CARRIER_PROVENANCE_NOT_CANONICALLY_RESOLVED",
        "DENSITY_PROVENANCE_IS_TEXT_NOT_RECEIPT_BOUND",
        "EXACT_TARGET_WEIGHED_MASS_ROUTE_NOT_ACCEPTED_BY_VOLUME_BINDER",
        "NEXT_COMMAND_IS_STATE_CHANGING_NOT_DOCUMENTARY",
    }
    assert report["blockers"] == EXPECTED_BLOCKERS


def test_checkpoint6_is_deterministic_read_only_and_authority_safe(report) -> None:
    before = _sha256(DEFAULT_PROTOCOL_PATH)
    repeated = evaluate_r6_checkpoint6_readiness()
    after = _sha256(DEFAULT_PROTOCOL_PATH)
    assert repeated == report
    assert before == after
    authority = report["authority"]
    assert authority["checkpoint6_intake_contract_record_authorized"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key != "checkpoint6_intake_contract_record_authorized"
    )
    assert all(value is False for value in report["side_effects"].values())
    assert report["report_sha256"] == (
        evaluate_r6_checkpoint6_readiness()["report_sha256"]
    )


def test_checkpoint6_rejects_authority_escalation(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"]["compounding_authorized"] = True
    path = tmp_path / "authority-escalation.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint6ContractError, match="authority boundary"):
        evaluate_r6_checkpoint6_readiness(protocol_path=path)


def test_checkpoint6_rejects_injected_canonical_evidence(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["canonical_current_evidence"]["bottle_lot_receipts"] = [
        {"unreviewed": True}
    ]
    path = tmp_path / "injected-evidence.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint6ContractError, match="must remain empty"):
        evaluate_r6_checkpoint6_readiness(protocol_path=path)


def test_checkpoint6_rejects_pinned_implementation_drift(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["implementation_surface"]["physical_lineage_service"]["sha256"] = (
        "0" * 64
    )
    path = tmp_path / "implementation-drift.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint6ContractError, match="service hash drift"):
        evaluate_r6_checkpoint6_readiness(protocol_path=path)
