import copy

import pytest

from engine.research.controlled_omission import plan_controlled_omission, verify_controlled_omission


def inputs():
    def row(identity, dose):
        return dict(stock_id=identity, identity_name=identity, amount_decimal=dose,
                    amount_unit="mg", stock_fraction_decimal="0.1", fraction_basis="w/w", carrier="DPG")
    return dict(control_rows=[row("protected_flower", "120.00"), row("mobile_hay", "15.25")],
                omit_stock_ids=["mobile_hay"], protected_stock_ids=["protected_flower"],
                carrier_blanks={"DPG": {"stock_id": "measured_DPG_blank", "carrier": "DPG"}})


def test_fixed_background_and_equal_total_mass_not_resolve():
    data = inputs()
    original = copy.deepcopy(data)
    result = plan_controlled_omission(**data)
    assert data == original
    assert result["state"] == "CONTROLLED_OMISSION_DESIGN_READY"
    assert result["candidate_rows"][0] == data["control_rows"][0]
    assert result["candidate_rows"][1]["amount_decimal"] == "15.25"
    assert result["total_mass_mg"] == "135.25"
    assert result["active_total_preserved"] is False
    assert result["inventory_binding_verified"] is False
    assert verify_controlled_omission(result, **data)
    assert all(v is False for v in result["authority"].values())


def test_exact_sum_exceeds_default_decimal_precision_without_rounding():
    data = inputs()
    data["control_rows"][0]["amount_decimal"] = "1234567890123456789012345678901234567890"
    data["control_rows"][1]["amount_decimal"] = "0.00000000000000000000000000000000000001"
    result = plan_controlled_omission(**data)
    assert result["state"] == "CONTROLLED_OMISSION_DESIGN_READY"
    assert result["total_mass_mg"] == "1234567890123456789012345678901234567890.00000000000000000000000000000000000001"


def test_blank_stock_cannot_be_two_carriers():
    data = inputs()
    data["carrier_blanks"]["ethanol"] = {"stock_id": "measured_DPG_blank", "carrier": "ethanol"}
    assert plan_controlled_omission(**data)["state"] == "INVALID_INPUT"


@pytest.mark.parametrize("mutation", ["retained_dose", "identity", "carrier", "omitted", "unit", "self_hash"])
def test_receipt_mutations_cannot_be_self_certified(mutation):
    data = inputs()
    result = plan_controlled_omission(**data)
    if mutation == "retained_dose":
        result["candidate_rows"][0]["amount_decimal"] = "119.00"
        result["candidate_rows"][1]["amount_decimal"] = "16.25"
    elif mutation == "identity":
        result["candidate_rows"][0]["stock_id"] = "substitute"
    elif mutation == "carrier":
        result["candidate_rows"][1]["carrier"] = "ethanol"
    elif mutation == "omitted":
        result["omitted_stock_ids"] = []
    elif mutation == "unit":
        result["candidate_rows"][0]["amount_unit"] = "uL"
    else:
        result["plan_sha256"] = "0" * 64
    assert not verify_controlled_omission(result, **data)


@pytest.mark.parametrize("mutation,state,reason", [
    ("uL", "WITHHOLD_UNKNOWN", "HOLD_EXACT_COMMON_MASS_BASIS_REQUIRED"),
    ("w/v", "WITHHOLD_UNKNOWN", "HOLD_EXACT_COMMON_MASS_BASIS_REQUIRED"),
    ("blank", "WITHHOLD_UNKNOWN", "HOLD_MATCHED_CARRIER_BLANK_REQUIRED"),
    ("carrier", "WITHHOLD_UNKNOWN", "HOLD_MATCHED_CARRIER_BLANK_REQUIRED"),
    ("protect", "WITHHOLD_UNKNOWN", "PROTECTED_STOCK_OMISSION_FORBIDDEN"),
    ("NaN", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
    ("-1", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
    ("boolean", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
    ("all", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
    ("none", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
    ("duplicate", "INVALID_INPUT", "INVALID_OMISSION_INPUT"),
])
def test_missing_quantitative_inputs_are_not_defaults(mutation, state, reason):
    data = inputs()
    if mutation == "uL":
        data["control_rows"][0]["amount_unit"] = "uL"
    elif mutation == "w/v":
        data["control_rows"][0]["fraction_basis"] = "w/v"
    elif mutation == "blank":
        data["carrier_blanks"] = {}
    elif mutation == "carrier":
        data["carrier_blanks"]["DPG"]["carrier"] = "ethanol"
    elif mutation == "protect":
        data["omit_stock_ids"] = ["protected_flower"]
    elif mutation == "all":
        data["omit_stock_ids"] = ["protected_flower", "mobile_hay"]
    elif mutation == "none":
        data["omit_stock_ids"] = []
    elif mutation == "duplicate":
        data["omit_stock_ids"] *= 2
    else:
        data["control_rows"][0]["amount_decimal"] = True if mutation == "boolean" else mutation
    result = plan_controlled_omission(**data)
    assert result["state"] == state and result["reason_codes"] == [reason]
    assert result["formula_action"] == "NO_CHANGE" and not result["candidate_rows"]
