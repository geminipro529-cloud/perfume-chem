"""Preflight-backed gates report HOLD for missing data and keep FAIL for real problems."""

from engine.pipeline.gates import _gate_pipeline_preflight, _gate_preflight_contract
from engine.pipeline.preflight import resolve_inventory_stock_contract


def _stock_check(*issues: dict) -> dict:
    return {
        "check_name": "inventory_stock_contract",
        "status": "FAIL",
        "detail": f"{len(issues)} material stock contract failure(s)",
        "data": {"issues": list(issues), "resolved_stock_specs": {}},
    }


def _metadata_incomplete(material: str, *, matches: bool = True, holds=(), clears: bool = True) -> dict:
    return {
        "material": material,
        "reason": "inventory_stock_non_executable" if holds else "inventory_stock_metadata_incomplete",
        "statuses": ["owned"],
        "execution_holds": list(holds),
        # What preflight reports: would a complete Stock page entry clear it.
        "stock_page_entry_clears": clears,
        "fraction_matches_formula": matches,
    }


def _natural_check(*materials: str) -> dict:
    return {
        "check_name": "natural_composite_coverage",
        "status": "FAIL",
        "detail": "Natural mixtures lack a required constituent decomposition: " + ", ".join(materials),
        "data": {"materials": list(materials)},
    }


def _receipt_check(*abstained: str, mismatches: bool = False, blockers=("stock_id_not_bound",)) -> dict:
    data = {
        "status": "ABSTAINED",
        "lines": [
            {"material_name": name, "status": "ABSTAINED", "blockers": list(blockers)}
            for name in abstained
        ]
        + [{"material_name": "Bound Material", "status": "BOUND", "blockers": []}],
    }
    if mismatches:
        data["state_mismatches"] = ["Bound Material:raw_ul"]
    return {
        "check_name": "formula_dose_receipt",
        "status": "FAIL",
        "detail": "Formula stock/dose receipt abstained and cannot support release-mode analysis.",
        "data": data,
    }


def _preflight(*checks: dict) -> dict:
    return {"status": "FAIL", "checks": list(checks), "warnings": []}


def _stock_gate(*issues: dict):
    return _gate_preflight_contract(_preflight(_stock_check(*issues)), "inventory_stock_contract")


def test_only_metadata_incomplete_stock_holds_and_names_the_data_to_supply():
    gate = _stock_gate(_metadata_incomplete("Kephalis"))
    assert gate.status == "HOLD"
    assert "needs data: Kephalis (on the Lab app's Stock page, fill in the strength, basis and carrier" in gate.detail
    assert [issue["material"] for issue in gate.data["needs_data"]] == ["Kephalis"]
    assert gate.data["fail_issues"] == []


def test_execution_holds_that_only_miss_data_hold():
    gate = _stock_gate(
        _metadata_incomplete("Ambrofix", holds=["STOCK_INTAKE_IDENTITY_ONLY"]),
        _metadata_incomplete("Bacdanol", holds=["FRACTION_BASIS_UNSPECIFIED"]),
        _metadata_incomplete("Iso E Super", holds=["BOTTLE_LOT_AND_LABEL_RECEIPT_MISSING"]),
    )
    assert gate.status == "HOLD"
    assert "on the Lab app's Stock page, fill in the strength, basis and carrier of the Bacdanol stock" in gate.detail


def test_not_in_inventory_or_fraction_mismatch_still_fail_and_list_needs_data_after():
    gate = _stock_gate(
        _metadata_incomplete("Geraniol"),
        {"material": "Bergamot FCF", "reason": "not_in_inventory"},
        {
            "material": "Evernyl",
            "reason": "stock_fraction_mismatch",
            "formula_dilution": 1.0,
            "inventory_dilutions": [0.1],
        },
    )
    assert gate.status == "FAIL"
    assert gate.detail.index("Bergamot FCF (not_in_inventory)") < gate.detail.index("needs data: Geraniol")
    assert "Evernyl (stock_fraction_mismatch: formula 1.0 vs stock 0.1)" in gate.detail

    assert _stock_gate({"material": "Evernyl", "reason": "stock_fraction_mismatch"}).status == "FAIL"
    assert _stock_gate({"material": "Vertofix", "reason": "not_in_inventory"}).status == "FAIL"


def test_real_problems_and_unknown_reasons_fail_closed():
    for issue in (
        {"material": "Petitgrain EO", "reason": "inventory_gap"},
        {"material": "Romandolide", "reason": "inventory_stock_unavailable"},
        {"material": "Lemonile", "reason": "preparation_required"},
        {"material": "X", "reason": "some_new_reason"},
        # Held stock at another strength is a wrong strength, not only missing data.
        _metadata_incomplete("Coumarin", matches=False),
        _metadata_incomplete("Coumarin", matches=False, holds=["CARRIER_UNSPECIFIED"]),
        # The issue predates the strength-match field: fail closed.
        {"material": "Old", "reason": "inventory_stock_metadata_incomplete"},
        _metadata_incomplete("Held", holds=["USER_COMPOUNDING_HOLD"]),
        _metadata_incomplete("Held", holds=["CARRIER_UNSPECIFIED|USER_COMPOUNDING_HOLD"]),
        _metadata_incomplete("Odd", holds=["SOME_UNKNOWN_HOLD"]),
        {"material": "Empty", "reason": "inventory_stock_non_executable", "execution_holds": []},
    ):
        assert _stock_gate(issue).status == "FAIL", issue


def test_unknown_strength_holds_even_when_the_recorded_strength_differs():
    gate = _stock_gate(_metadata_incomplete("Tincture", matches=False, holds=["STOCK_FRACTION_UNSPECIFIED"]))
    assert gate.status == "HOLD"


def test_live_inventory_metadata_gap_holds_but_wrong_strength_fails():
    # Geraniol is owned at 10% with no recorded carrier, and neat.
    held = resolve_inventory_stock_contract({"ingredients_ul": {"Geraniol": 100.0}, "dilutions": {"Geraniol": 0.1}})
    assert held.status == "FAIL"  # the preflight check itself is unchanged
    assert [issue["reason"] for issue in held.data["issues"]] == ["inventory_stock_metadata_incomplete"]
    gate = _gate_preflight_contract({"checks": [held.as_dict()]}, "inventory_stock_contract")
    assert gate.status == "HOLD"
    assert "needs data: Geraniol" in gate.detail

    wrong = resolve_inventory_stock_contract({"ingredients_ul": {"Evernyl": 100.0}, "dilutions": {"Evernyl": 1.0}})
    assert [issue["reason"] for issue in wrong.data["issues"]] == ["stock_fraction_mismatch"]
    assert _gate_preflight_contract({"checks": [wrong.as_dict()]}, "inventory_stock_contract").status == "FAIL"


def test_missing_natural_decomposition_holds_with_naturals_in_data():
    gate = _gate_preflight_contract(_preflight(_natural_check("Petitgrain EO")), "natural_composite_coverage")
    assert gate.status == "HOLD"
    assert gate.data["materials"] == ["Petitgrain EO"]
    assert gate.data["needs_data"] == ["Petitgrain EO"]


def test_rollup_holds_when_every_failing_check_is_missing_data():
    gate = _gate_pipeline_preflight(
        _preflight(
            _stock_check(_metadata_incomplete("Geraniol")),
            _receipt_check("Geraniol"),
            _natural_check("Petitgrain EO"),
        )
    )
    assert gate.status == "HOLD"
    assert gate.data["failing_checks"] == []
    assert gate.data["needs_data_checks"] == [
        "inventory_stock_contract",
        "formula_dose_receipt",
        "natural_composite_coverage",
    ]


def test_rollup_fails_on_any_real_or_unknown_failure():
    real_stock = _preflight(
        _stock_check({"material": "Bergamot FCF", "reason": "not_in_inventory"}),
        _receipt_check("Bergamot FCF"),
        _natural_check("Petitgrain EO"),
    )
    gate = _gate_pipeline_preflight(real_stock)
    assert gate.status == "FAIL"
    assert gate.data["failing_checks"] == ["inventory_stock_contract", "formula_dose_receipt"]
    assert gate.data["needs_data_checks"] == ["natural_composite_coverage"]

    other = {"check_name": "input_normalization", "status": "FAIL", "detail": "No ingredient volumes found."}
    assert _gate_pipeline_preflight(_preflight(_natural_check("Petitgrain EO"), other)).status == "FAIL"

    # A receipt that fails for its own reasons is a real failure.
    mismatched = _preflight(_stock_check(_metadata_incomplete("Geraniol")), _receipt_check("Geraniol", mismatches=True))
    assert _gate_pipeline_preflight(mismatched).status == "FAIL"
    unrelated = _preflight(_stock_check(_metadata_incomplete("Geraniol")), _receipt_check("Geraniol", "Linalool"))
    assert _gate_pipeline_preflight(unrelated).status == "FAIL"

    # A FAIL preflight with no failing check named still fails closed.
    assert _gate_pipeline_preflight({"status": "FAIL", "checks": []}).status == "FAIL"


def _held_at(material: str, hold: str, *, formula: float, stock: float | None, matches: bool) -> dict:
    return {
        **_metadata_incomplete(material, matches=matches, holds=[hold]),
        "formula_dilution": formula,
        "held_stock_strengths": [{"execution_hold": hold, "fraction": stock}],
    }


def test_tincture_above_its_starting_charge_fails_and_at_or_below_holds():
    hold = "FINAL_DISSOLVED_FRACTION_UNMEASURED"
    assert _stock_gate(_held_at("Storax", hold, formula=0.4, stock=0.2, matches=False)).status == "FAIL"
    assert _stock_gate(_held_at("Storax", hold, formula=0.2, stock=0.2, matches=True)).status == "HOLD"
    assert _stock_gate(_held_at("Storax", hold, formula=0.1, stock=0.2, matches=False)).status == "HOLD"
    # No recorded charge: only the measurement is missing.
    assert _stock_gate(_held_at("Storax", hold, formula=0.4, stock=None, matches=False)).status == "HOLD"
    # The fields the comparison needs are missing: fail closed.
    assert _stock_gate(_metadata_incomplete("Storax", matches=False, holds=[hold])).status == "FAIL"
    no_fraction = _held_at("Storax", hold, formula=0.1, stock=0.2, matches=False)
    no_fraction["held_stock_strengths"] = [{"execution_hold": hold}]
    assert _stock_gate(no_fraction).status == "FAIL"


def test_live_storax_tincture_above_its_charge_fails_and_at_or_below_it_holds():
    # Turkish Storax Tincture is held with a 20% starting charge.
    def gate(fraction: float):
        check = resolve_inventory_stock_contract(
            {"ingredients_ul": {"Turkish Storax Tincture": 100.0}, "dilutions": {"Turkish Storax Tincture": fraction}}
        )
        return _gate_preflight_contract({"checks": [check.as_dict()]}, "inventory_stock_contract")

    assert gate(0.4).status == "FAIL"
    held = gate(0.2)
    assert held.status == "HOLD"
    assert "measure the final dissolved fraction" in held.detail
    # Below the charge the unmeasured final strength could still match, so the
    # live contract must carry the charge through for the gate to hold it.
    assert gate(0.1).status == "HOLD"


def test_approximate_stock_used_at_another_strength_fails_and_at_its_nominal_strength_holds():
    hold = "APPROXIMATE_STOCK_FRACTION"
    assert _stock_gate(_held_at("Approx", hold, formula=0.01, stock=0.1, matches=False)).status == "FAIL"
    held = _stock_gate(_held_at("Approx", hold, formula=0.1, stock=0.1, matches=True))
    assert held.status == "HOLD"
    assert "on the Lab app's Stock page, fill in the strength, basis and carrier" in held.detail


def test_receipt_line_with_a_non_stock_blocker_fails_the_rollup():
    for blockers in (
        ["inventory_stock_metadata_incomplete", "stock_fraction_not_bound"],
        ["inventory_stock_metadata_incomplete", "some_new_blocker"],
        # A stock reason that is not this material's own issue.
        ["not_in_inventory"],
        [],
    ):
        gate = _gate_pipeline_preflight(
            _preflight(_stock_check(_metadata_incomplete("Geraniol")), _receipt_check("Geraniol", blockers=blockers))
        )
        assert gate.status == "FAIL", blockers
        assert "formula_dose_receipt" in gate.data["failing_checks"]

    # A binding blocker is a stock consequence only when the contract resolved
    # no stock for that material.
    stock = _stock_check(_metadata_incomplete("Geraniol"))
    stock["data"]["resolved_stock_specs"] = {"Geraniol": {"stock_id": "x"}}
    gate = _gate_pipeline_preflight(
        _preflight(stock, _receipt_check("Geraniol", blockers=["stock_authority_not_bound"]))
    )
    assert gate.status == "FAIL"

    # Without the resolved-stock field the receipt cannot be traced: fail closed.
    stock = _stock_check(_metadata_incomplete("Geraniol"))
    stock["data"].pop("resolved_stock_specs")
    assert _gate_pipeline_preflight(_preflight(stock, _receipt_check("Geraniol"))).status == "FAIL"

    # The stock issue's own reason plus binding blockers still follow the stock contract.
    gate = _gate_pipeline_preflight(
        _preflight(
            _stock_check(_metadata_incomplete("Geraniol")),
            _receipt_check("Geraniol", blockers=["inventory_stock_metadata_incomplete", "stock_authority_not_bound"]),
        )
    )
    assert gate.status == "HOLD"


def test_abstained_receipt_without_unbound_lines_fails_the_rollup():
    receipt = _receipt_check()
    assert [line["status"] for line in receipt["data"]["lines"]] == ["BOUND"]
    gate = _gate_pipeline_preflight(_preflight(_stock_check(_metadata_incomplete("Geraniol")), receipt))
    assert gate.status == "FAIL"
    assert gate.data["failing_checks"] == ["formula_dose_receipt"]


def test_rollup_passes_non_fail_status_through():
    assert _gate_pipeline_preflight({"status": "WARN", "checks": [], "warnings": ["w"]}).status == "WARN"
    assert _gate_pipeline_preflight({"status": "PASS", "checks": []}).status == "PASS"
