import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint4_readiness import (
    DEFAULT_INVENTORY_TEXT_PATH,
    DEFAULT_SUCCESSOR_PATH,
    Checkpoint4ContractError,
    evaluate_r6_aimi_checkpoint4_readiness,
)

EXPECTED_BLOCKERS = [
    "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
    "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
    "HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED",
    "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING",
    "HOLD_EXACT_CURVE_APPLICABILITY",
    "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED",
    "PLEASANTNESS_NOT_ESTABLISHED",
    "PHYSICAL_LIKING_NOT_TESTED",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return evaluate_r6_aimi_checkpoint4_readiness()


def test_checkpoint4_records_the_single_user_selected_successor(report) -> None:
    assert report["status"] == "HOLD"
    assert report["checkpoint4_state"] == (
        "SOFTWARE_COMPLETE_DESIGN_SUCCESSOR_ADMITTED_PHYSICAL_READINESS_HOLD"
    )
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["design_successor_state"] == "ADMITTED_DESIGN_SUCCESSOR_ONLY"
    assert report["parent_lineage_state"] == (
        "EXACT_R5_STANDALONE_BASELINE_BOUND"
    )
    assert report["baseline_state"] == "R5_STANDALONE_BASELINE_ACCEPTED"
    assert report["parent_equivalence_state"] == (
        "NOT_CLAIMED_STANDALONE_BASELINE"
    )
    assert report["substitution_state"] == (
        "AIMI_SELECTED_NOMINAL_50_UL_TRANSFER"
    )
    assert report["active_equivalence_state"] == (
        "NOT_CLAIMED_INTENDED_MATERIAL_CHANGE"
    )
    assert report["formula_action"] == "DESIGN_SUCCESSOR_RECORDED"
    assert report["changed_source_rows"] == [47]
    assert report["successor_rows_sha256"] == (
        "40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b"
    )


def test_checkpoint4_replaces_only_the_depleted_row_and_preserves_totals(report) -> None:
    replacement = report["row_replacement"]
    assert replacement["parent_row"] == {
        "source_row": 47,
        "basket": "B5",
        "material": "Methyl Ionone Gamma Coeur",
        "required_stock": "Same neat IFF stock used in the iris formula",
        "dose": 50,
        "unit": "µL",
        "evidence": "S01",
    }
    assert replacement["successor_row"] == {
        "source_row": 47,
        "basket": "B5",
        "material": "Givaudan AIMI",
        "required_stock": "Owned Givaudan AIMI, neat / as supplied",
        "dose": 50,
        "unit": "µL",
        "evidence": "USER-R6-AIMI-20260926",
    }
    assert replacement["nominal_transfer_preserved"] is True
    assert replacement["chemical_active_equivalence_claimed"] is False
    assert replacement["sensory_equivalence_claimed"] is False
    assert replacement["oav_equivalence_claimed"] is False
    assert report["quantities"] == {
        "row_count": 63,
        "liquid_row_count": 62,
        "liquid_total_ul": "5600",
        "solid_row_count": 1,
        "solid_total_mg": "300",
        "mass_volume_never_summed": True,
    }


def test_checkpoint4_binds_the_owned_aimi_stock_without_model_promotion(report) -> None:
    assert report["aimi_stock"] == {
        "stock_id": "inventory:user-20260904:a45ff6250b56cec5bbad",
        "name": "Givaudan AIMI",
        "identity_name": "Givaudan AIMI",
        "dilution_decimal": "1",
        "fraction_basis": "neat",
        "carrier": "",
        "status": "owned",
        "execution_ready": True,
        "nominal_property_model_ready": False,
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260907",
        "source_ref": (
            "data/governance/inventory_user_authority_overlay_20260904.json"
            "#INV-USER-20260904-003"
        ),
    }
    applicability = report["model_applicability"]
    assert applicability["chemical_identity_state"] == (
        "HOLD_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED"
    )
    assert applicability["odt_oav_state"] == (
        "HOLD_EXACT_PRODUCT_THRESHOLD_APPLICABILITY"
    )
    assert applicability["intensity_state"] == "HOLD_EXACT_CURVE_APPLICABILITY"
    assert report["nominal_product_reference"] == {
        "scope": "REFERENCE_COMPATIBLE_NOT_BOTTLE_MATCHED",
        "supplier": "PerfumersWorld",
        "product_name": "Alpha Isomethyl Ionone",
        "sku": "3IW00300",
        "cas": "127-51-5",
        "owned_bottle_identity_proven_by_reference": False,
    }


def test_checkpoint4_retires_only_the_depleted_material_blocker(report) -> None:
    assert report["blockers"] == EXPECTED_BLOCKERS
    assert (
        "HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR"
        not in report["blockers"]
    )
    assert report["physical_build_state"] == (
        "HOLD_STOCK_BINDING_AND_PREPARATION_LINEAGE"
    )


def test_checkpoint4_is_deterministic_and_has_no_physical_side_effects(report) -> None:
    tracked = (DEFAULT_SUCCESSOR_PATH, DEFAULT_INVENTORY_TEXT_PATH)
    before = {path: _sha256(path) for path in tracked}
    repeated = evaluate_r6_aimi_checkpoint4_readiness()
    after = {path: _sha256(path) for path in tracked}

    assert repeated == report
    assert before == after
    assert report["authority"]["design_successor_record_authorized"] is True
    assert all(
        value is False
        for key, value in report["authority"].items()
        if key != "design_successor_record_authorized"
    )
    assert all(value is False for value in report["side_effects"].values())


def test_checkpoint4_successor_drift_fails_closed(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_SUCCESSOR_PATH.read_text(encoding="utf-8"))
    changed["row_replacement"]["successor_row"]["dose"] = 55
    changed_path = tmp_path / "changed-successor.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    drifted = evaluate_r6_aimi_checkpoint4_readiness(successor_path=changed_path)
    assert drifted["status"] == "HOLD"
    assert drifted["input_integrity_state"] == "HOLD_DRIFT_DETECTED"
    assert "HOLD_SUCCESSOR_ROWSET_DRIFT" in drifted["blockers"]
    assert "HOLD_SUCCESSOR_QUANTITY_DRIFT" in drifted["blockers"]
    assert "HOLD_AIMI_SUBSTITUTION_CONTRACT_DRIFT" in drifted["blockers"]
    assert all(value is False for value in drifted["side_effects"].values())


def test_checkpoint4_cannot_grant_physical_authority(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_SUCCESSOR_PATH.read_text(encoding="utf-8"))
    changed["authority"]["compounding_authorized"] = True
    changed_path = tmp_path / "authority-escalation.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        Checkpoint4ContractError,
        match="invalid authority boundary",
    ):
        evaluate_r6_aimi_checkpoint4_readiness(successor_path=changed_path)


def test_checkpoint4_parent_hash_drift_is_rejected(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_SUCCESSOR_PATH.read_text(encoding="utf-8"))
    changed["parent"]["sha256"] = "0" * 64
    changed_path = tmp_path / "parent-drift.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Checkpoint4ContractError, match="parent comparator hash drift"):
        evaluate_r6_aimi_checkpoint4_readiness(successor_path=changed_path)
