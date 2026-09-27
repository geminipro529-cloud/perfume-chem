import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint3_readiness import (
    DEFAULT_COMPARATOR_PATH,
    DEFAULT_INVENTORY_TEXT_PATH,
    DEFAULT_PROTOCOL_PATH,
    Checkpoint3ContractError,
    evaluate_r5_checkpoint3_readiness,
)

EXPECTED_BLOCKERS = [
    "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
    "HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR",
    "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
    "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING",
    "HOLD_EXACT_CURVE_APPLICABILITY",
    "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED",
    "PLEASANTNESS_NOT_ESTABLISHED",
    "PHYSICAL_LIKING_NOT_TESTED",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report():
    return evaluate_r5_checkpoint3_readiness()


def test_current_checkpoint3_state_is_truthful_hold(report):
    assert report["status"] == "HOLD"
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["design_comparator_state"] == "ADMITTED_DESIGN_ONLY"
    assert report["baseline_state"] == "R5_STANDALONE_BASELINE_ACCEPTED"
    assert report["parent_equivalence_state"] == (
        "NOT_CLAIMED_STANDALONE_BASELINE"
    )
    assert report["revision_state"] == (
        "REVISED_SUCCESSOR_REQUIRED_SPECIFIC_CHANGE_UNRESOLVED"
    )
    assert report["stock_binding_state"] == "HOLD_STOCK_BINDING"
    assert report["constant_total_basis_state"] == (
        "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING"
    )
    assert report["constant_total_basis"]["selected_basis"] == "active_mass_g"
    assert report["constant_total_basis"]["legacy_stock_basis_present"] == (
        "mass_per_volume_w_v"
    )
    assert report["intensity_state"] == "HOLD_EXACT_CURVE_APPLICABILITY"
    assert report["measurement_protocol_state"] == (
        "FROZEN_SCHEMA_HOLD_EXECUTION_PARAMETERS"
    )
    assert report["pleasantness_state"] == "NOT_ESTABLISHED"
    assert report["physical_liking_state"] == "NOT_TESTED"
    assert report["formula_action"] == "NO_CHANGE"
    assert report["blockers"] == EXPECTED_BLOCKERS


def test_mass_and_volume_are_separate_and_parent_is_not_reconstructed(report):
    assert report["quantities"] == {
        "row_count": 63,
        "liquid_row_count": 62,
        "liquid_total_ul": "5600",
        "solid_row_count": 1,
        "solid_materials": ["Ambrox Super"],
        "solid_total_mg": "300",
        "mass_volume_never_summed": True,
    }
    assert "combined_total" not in report["quantities"]
    assert report["parent"] == {
        "expected_sha256": (
            "5b0a012b88ca5c1cea45ea8a704cf3b9e5d799d66e9f9d28b2a5d21efa9f4129"
        ),
        "bytes_present": False,
        "reconstruction_allowed": False,
        "search_state": "NOT_CLAIMED_STANDALONE_BASELINE",
        "historical_search_state": "HOLD_PARENT_BYTES_MISSING",
        "required_for_standalone_baseline": False,
        "equivalence_claimed": False,
        "improvement_claimed": False,
    }


def test_standalone_baseline_does_not_fabricate_parent_or_formula_authority(report):
    assert report["baseline_decision"] == {
        "state": "R5_STANDALONE_BASELINE_ACCEPTED",
        "baseline_id": "lavande-ambre-profond-r5-design-comparator-20260923",
        "parent_bytes_required_for_baseline": False,
        "parent_equivalence_state": "NOT_CLAIMED_STANDALONE_BASELINE",
        "r4_equivalence_claimed": False,
        "r4_improvement_claimed": False,
        "r4_reference_disposition": (
            "HISTORICAL_REFERENCE_ONLY_BYTES_UNAVAILABLE"
        ),
    }
    assert report["revision_decision"]["material"] == (
        "Methyl Ionone Gamma Coeur"
    )
    assert report["revision_decision"]["specific_substitute_selected"] is False
    assert report["revision_decision"]["omission_selected"] is False
    assert report["revision_decision"]["formula_mutation_authorized"] is False
    assert "HOLD_PARENT_BYTES_MISSING" not in report["blockers"]


def test_clarified_stocks_are_candidates_without_binding_authority(report):
    assert report["stock_conflicts"] == [
        {
            "code": "METHYL_IONONE_GAMMA_COEUR_DEPLETED",
            "source_row": 47,
            "material": "Methyl Ionone Gamma Coeur",
            "required_stock": "Exact Methyl Ionone Gamma Coeur product",
            "expected_stock_id": None,
            "binding_authority": False,
            "observed_stock": None,
            "verification_state": "CONFIRMED_NO_EXACT_LIVE_STOCK",
        }
    ]
    ambrox = next(
        item
        for item in report["row_candidate_audit"]
        if item["source_row"] == 69
    )
    assert ambrox["observed_stock"] == {
        "stock_id": "inventory:user-20260924:36e0e28366f34673a242",
        "name": "Ambrox Super",
        "identity_name": "Ambrox Super",
        "dilution_decimal": "1",
        "fraction_basis": "neat",
        "carrier": "",
        "physical_form": "crystals",
        "execution_ready": True,
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260924",
        "source_ref": (
            "data/governance/"
            "inventory_user_authority_overlay_20260924_r5_stock_clarifications.json"
            "#INV-USER-20260924-R5-001"
        ),
    }
    assert ambrox["candidate_state"] == "CANDIDATE_FORM_MATCH"
    norlimbanol = next(
        stock
        for stock in report["row_candidate_audit"]
        if stock["material"] == "Norlimbanol Dextro"
    )
    assert norlimbanol["observed_stock"]["carrier"] == "dpg"
    assert norlimbanol["observed_stock"]["physical_form"] == "solution"
    assert norlimbanol["observed_stock"]["fraction_basis"] == "mass_fraction"
    assert norlimbanol["observed_stock"]["execution_ready"] is False
    assert report["stock_binding_coverage"] == {
        "required_row_count": 63,
        "build_plan_bound_row_count": 0,
        "read_only_candidate_row_count": 62,
        "candidate_state_counts": {
            "CANDIDATE_FORM_MATCH": 45,
            "CANDIDATE_PREPARATION_REQUIRED": 3,
            "CANDIDATE_RECEIPT_INCOMPLETE": 14,
            "REQUIRED_STOCK_DEPLETED": 1,
        },
        "binding_candidates_are_execution_authority": False,
    }


def test_previous_ambrox_solution_is_preserved_as_a_separate_stock():
    from engine.inventory_parser import materialize_current_inventory

    ambrox_stocks = [
        stock
        for stock in materialize_current_inventory().stocks
        if stock.identity_name == "Ambrox Super"
    ]
    assert len(ambrox_stocks) == 2
    solution = next(stock for stock in ambrox_stocks if stock.dilution == 0.25)
    assert solution.stock_id == "inventory:user-20260902:9e69f9db20c45cfe37e6"
    assert solution.fraction_basis == "mass_fraction"
    assert solution.carrier == "dpg + ipm + ethanol"


def test_current_crystal_stock_replaces_the_ambrox_form_conflict(report):
    conflicts = {item["code"] for item in report["stock_conflicts"]}
    assert "AMBROX_FORM_CONFLICT" not in conflicts
    assert "VETIVERYL_STRENGTH_CONFLICT" not in conflicts
    by_row = {row["source_row"]: row for row in report["row_candidate_audit"]}
    assert by_row[9]["candidate_state"] == "CANDIDATE_FORM_MATCH"
    assert by_row[9]["observed_stock"]["dilution_decimal"] == "1"
    assert by_row[9]["observed_stock"]["fraction_basis"] == "neat"


def test_resolved_basis_does_not_overstate_physical_lineage_readiness(report):
    by_row = {row["source_row"]: row for row in report["row_candidate_audit"]}
    assert by_row[16]["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert by_row[16]["observed_stock"]["carrier"] == "dpg"
    assert by_row[16]["observed_stock"]["fraction_basis"] == "mass_fraction"
    assert by_row[16]["observed_stock"]["execution_ready"] is False
    assert by_row[30]["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert by_row[30]["observed_stock"]["carrier"] == "dpg"
    assert by_row[30]["observed_stock"]["fraction_basis"] == "mass_fraction"
    assert by_row[30]["observed_stock"]["execution_ready"] is False


def test_supplier_lookup_plus_direct_ownership_still_needs_lineage_receipt(report):
    by_row = {row["source_row"]: row for row in report["row_candidate_audit"]}
    aroma_more = by_row[36]
    assert aroma_more["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert aroma_more["candidate_stock_id"] == (
        "inventory:user-20260924:38a9eff2ae4d6803f3ba"
    )
    assert aroma_more["observed_stock"]["dilution_decimal"] == "1"
    assert aroma_more["observed_stock"]["execution_ready"] is False
    assert aroma_more["binding_authority"] is False


def test_every_r5_row_has_one_non_executable_candidate_audit_state(report):
    rows = report["row_candidate_audit"]
    assert len(rows) == 63
    assert len({row["source_row"] for row in rows}) == 63
    assert all(row["binding_authority"] is False for row in rows)
    assert not [
        row
        for row in rows
        if row["verification_state"].startswith("DRIFT")
    ]

    by_row = {row["source_row"]: row for row in rows}
    assert by_row[36]["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert by_row[42]["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert by_row[47]["candidate_state"] == "REQUIRED_STOCK_DEPLETED"
    assert by_row[47]["candidate_stock_id"] is None
    assert by_row[58]["candidate_state"] == "CANDIDATE_RECEIPT_INCOMPLETE"
    assert by_row[59]["candidate_state"] == "CANDIDATE_PREPARATION_REQUIRED"
    assert by_row[69]["candidate_state"] == "CANDIDATE_FORM_MATCH"


def test_repeated_audit_is_deterministic_and_read_only(report):
    tracked = (
        DEFAULT_COMPARATOR_PATH,
        DEFAULT_PROTOCOL_PATH,
        DEFAULT_INVENTORY_TEXT_PATH,
    )
    before = {path: _sha256(path) for path in tracked}
    repeated = evaluate_r5_checkpoint3_readiness()
    after = {path: _sha256(path) for path in tracked}

    assert repeated == report
    assert before == after
    assert all(value is False for value in report["authority"].values())
    assert all(value is False for value in report["side_effects"].values())


def test_comparator_byte_drift_fails_closed(tmp_path):
    changed = json.loads(DEFAULT_COMPARATOR_PATH.read_text(encoding="utf-8"))
    changed["title"] = "Unadmitted changed title"
    changed_path = tmp_path / "changed-comparator.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    drifted = evaluate_r5_checkpoint3_readiness(comparator_path=changed_path)
    assert drifted["status"] == "HOLD"
    assert drifted["input_integrity_state"] == "HOLD_DRIFT_DETECTED"
    assert drifted["blockers"][0] == "HOLD_INPUT_FINGERPRINT_DRIFT"
    assert drifted["formula_action"] == "NO_CHANGE"
    assert all(value is False for value in drifted["side_effects"].values())


def test_protocol_cannot_grant_authority(tmp_path):
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"]["compounding_authorized"] = True
    changed_path = tmp_path / "authority-escalation.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        Checkpoint3ContractError,
        match="cannot grant authority",
    ):
        evaluate_r5_checkpoint3_readiness(protocol_path=changed_path)


def test_measurement_protocol_is_frozen_but_non_executable():
    protocol = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert protocol["state"] == "FROZEN_NONEXECUTABLE_CONTRACT"
    original = protocol
    while "predecessor" in original:
        predecessor_path = (
            DEFAULT_PROTOCOL_PATH.parents[2] / original["predecessor"]["path"]
        )
        original = json.loads(predecessor_path.read_text(encoding="utf-8"))
    measurement = original["measurement_protocol_contract"]
    assert measurement["state"] == "FROZEN_SCHEMA_HOLD_EXECUTION_PARAMETERS"
    assert measurement["execution_ready"] is False
    assert measurement["unresolved_execution_parameters"]
    assert "beauty" in measurement["endpoints"]
    assert measurement["endpoints"]["beauty"] == (
        "PROHIBITED_DERIVED_ENDPOINT"
    )
    assert "mixer_command" in original["forbidden_outputs"]
    assert "physical_experiment_authorization" in original["forbidden_outputs"]
