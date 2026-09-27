import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint5_readiness import (
    DEFAULT_INVENTORY_TEXT_PATH,
    DEFAULT_PROTOCOL_PATH,
    Checkpoint5ContractError,
    evaluate_r6_checkpoint5_readiness,
)

EXPECTED_OWNERSHIP = {
    "checkpoint5": [
        "HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED",
        "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING",
        "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED",
    ],
    "checkpoint6": [
        "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
        "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
        "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
    ],
    "checkpoint7": ["HOLD_EXACT_CURVE_APPLICABILITY"],
    "checkpoint8": [
        "PLEASANTNESS_NOT_ESTABLISHED",
        "PHYSICAL_LIKING_NOT_TESTED",
    ],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return evaluate_r6_checkpoint5_readiness()


def test_checkpoint5_freezes_a_nonexecuting_input_collection_contract(report) -> None:
    assert report["status"] == "HOLD"
    assert report["checkpoint5_state"] == (
        "SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD"
    )
    assert report["input_completion_state"] == "HOLD_CP5_INPUTS_INCOMPLETE"
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["successor_id"] == (
        "lavande-ambre-profond-r6-aimi-design-successor-20260926"
    )
    assert report["formula_action"] == "DESIGN_SUCCESSOR_UNCHANGED"
    assert report["successor_rows_sha256"] == (
        "40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b"
    )


def test_checkpoint5_census_is_complete_but_no_row_is_physically_bindable(
    report,
) -> None:
    summary = report["census_summary"]
    assert summary == {
        "row_count": 63,
        "candidate_stock_row_count": 63,
        "candidate_state_counts": {
            "CANDIDATE_BOTTLE_SPECIFIC_REFERENCE_WITHHELD": 1,
            "CANDIDATE_FORM_MATCH": 45,
            "CANDIDATE_PREPARATION_REQUIRED": 3,
            "CANDIDATE_RECEIPT_INCOMPLETE": 14,
        },
        "liquid_row_count": 62,
        "solid_mass_row_count": 1,
        "mass_conversion_input_missing_row_count": 62,
        "required_working_stock_preparation_row_count": 3,
        "sub_10_ul_unresolved_row_count": 3,
        "receipt_evidence_unverified_row_count": 63,
        "physical_binding_eligible_row_count": 0,
    }
    rows = report["row_gap_census"]
    assert len(rows) == 63
    assert len({row["source_row"] for row in rows}) == 63
    assert all(row["intended_stock_id"] for row in rows)
    assert all(row["physical_binding_eligible"] is False for row in rows)


def test_checkpoint5_uses_aimi_only_as_bottle_specific_empirical_scope(report) -> None:
    scope = report["aimi_scope"]
    assert scope["scope_state"] == "BOTTLE_SPECIFIC_EMPIRICAL_REQUIRED"
    assert scope["reference_disposition"] == (
        "REFERENCE_NOT_USED_FOR_QUANTITATIVE_APPLICABILITY"
    )
    assert scope["reference_linked_properties_allowed"] is False
    assert scope["family_or_description_equivalence_allowed"] is False
    assert scope["supplier_reference_proves_owned_bottle_identity"] is False

    rows = report["row_gap_census"]
    aimi = next(row for row in rows if row["source_row"] == 47)
    assert aimi["material"] == "Givaudan AIMI"
    assert aimi["amount_decimal"] == "50"
    assert aimi["amount_unit"] == "µL"
    assert aimi["candidate_state"] == (
        "CANDIDATE_BOTTLE_SPECIFIC_REFERENCE_WITHHELD"
    )
    assert "Methyl Ionone Gamma Coeur" not in {
        str(row["material"]) for row in rows
    }


def test_checkpoint5_preserves_mass_volume_separation_and_missing_conversions(
    report,
) -> None:
    basis = report["constant_total_basis"]
    assert basis["selected_basis"] == "active_mass_g"
    assert basis["constant_total_amount_decimal"] is None
    assert basis["conversion_inputs_complete"] is False
    assert basis["generic_density_allowed"] is False
    assert basis["solid_mass_kept_separate"] is True
    assert basis["mass_volume_never_summed"] is True

    rows = report["row_gap_census"]
    liquid_rows = [row for row in rows if row["amount_unit"] == "µL"]
    assert len(liquid_rows) == 62
    assert all(
        row["density_or_weighed_mass_state"]
        == "MISSING_DENSITY_OR_TARGET_WEIGHED_MASS"
        for row in liquid_rows
    )
    solid_rows = [row for row in rows if row["amount_unit"] == "mg"]
    assert [(row["material"], row["amount_decimal"]) for row in solid_rows] == [
        ("Ambrox Super", "300")
    ]
    assert solid_rows[0]["dimensional_conversion_state"] == "DIRECT_MASS_DIMENSION"


def test_checkpoint5_identifies_only_the_known_preparations_and_microtransfers(
    report,
) -> None:
    rows = report["row_gap_census"]
    preparation_rows = [
        row
        for row in rows
        if row["candidate_state"] == "CANDIDATE_PREPARATION_REQUIRED"
    ]
    assert [(row["source_row"], row["material"]) for row in preparation_rows] == [
        (31, "Heliotropal / piperonal"),
        (59, "Black Pepper EO"),
        (63, "Nutmeg EO"),
    ]
    assert all(
        row["preparation_receipt_state"] == "MISSING_REQUIRED_CHILD_PREPARATION"
        for row in preparation_rows
    )

    micro_rows = [
        row
        for row in rows
        if row["sub_10_ul_route_state"]
        == "UNRESOLVED_PREPARED_DILUTION_OR_QUALIFIED_DIRECT_MEASUREMENT"
    ]
    assert [
        (row["source_row"], row["material"], row["amount_decimal"])
        for row in micro_rows
    ] == [
        (20, "Haitian Vetiver EO", "5"),
        (43, "Linalool Oxide", "5"),
        (68, "Rosemary EO", "5"),
    ]


def test_checkpoint5_measurement_schema_keeps_endpoints_separate(report) -> None:
    measurement = report["measurement_protocol"]
    assert measurement["execution_ready"] is False
    assert measurement["documentary_r5_is_physical_comparator"] is False
    assert measurement["domains_must_remain_separate"] == ["BLOTTER", "SKIN"]
    assert len(measurement["unresolved_execution_parameters"]) == 25
    assert measurement["endpoints"] == {
        "physical_release": "SEPARATE_ENDPOINT",
        "sensory_intensity": "SEPARATE_ENDPOINT",
        "character": "SEPARATE_ENDPOINT",
        "pleasantness": "NOT_ESTABLISHED",
        "personal_liking": "NOT_TESTED",
        "population_liking": "NOT_TESTED",
        "beauty": "PROHIBITED_DERIVED_ENDPOINT",
    }


def test_checkpoint5_assigns_each_inherited_blocker_to_one_later_checkpoint(
    report,
) -> None:
    assert report["blocker_ownership"] == EXPECTED_OWNERSHIP
    owned = [
        blocker
        for blockers in report["blocker_ownership"].values()
        for blocker in blockers
    ]
    assert len(owned) == len(set(owned)) == 9
    assert report["checkpoint5_owned_blocker_dispositions"] == {
        "HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED": (
            "REFRAMED_REFERENCE_NOT_USED_BOTTLE_SPECIFIC_SCOPE"
        ),
        "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING": (
            "UNRESOLVED_ROW_INPUTS_AND_DERIVED_TOTAL_MISSING"
        ),
        "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED": (
            "UNRESOLVED_R6_PROTOCOL_PARAMETERS"
        ),
    }


def test_checkpoint5_is_deterministic_read_only_and_authority_safe(report) -> None:
    tracked = (DEFAULT_PROTOCOL_PATH, DEFAULT_INVENTORY_TEXT_PATH)
    before = {path: _sha256(path) for path in tracked}
    repeated = evaluate_r6_checkpoint5_readiness()
    after = {path: _sha256(path) for path in tracked}

    assert repeated == report
    assert before == after
    assert report["authority"]["checkpoint5_input_contract_record_authorized"] is True
    assert all(
        value is False
        for key, value in report["authority"].items()
        if key != "checkpoint5_input_contract_record_authorized"
    )
    assert all(value is False for value in report["side_effects"].values())


def test_checkpoint5_rejects_reference_property_promotion(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["aimi_scope_contract"]["reference_linked_properties_allowed"] = True
    changed_path = tmp_path / "authority-escalation.json"
    changed_path.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Checkpoint5ContractError, match="AIMI bottle-specific"):
        evaluate_r6_checkpoint5_readiness(protocol_path=changed_path)
