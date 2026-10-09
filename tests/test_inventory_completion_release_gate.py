"""Stock-page completions count at the release gate (Kenny, 2026-10-09).

Every test writes to a temporary completion log through the environment
variable the app and the gate both read, never to the real data/user log.
"""

from types import SimpleNamespace

import pytest

from engine.inventory_completions import (
    COMPLETION_CLEARABLE_HOLDS,
    COMPLETION_HOLD_DISPOSITIONS,
    FALSE_ACTION_AUTHORITY,
    STOCK_PAGE_ENTRY_INCOMPLETE,
    completion_clears_execution_hold,
    inventory_completion_requirements,
    record_inventory_completion,
)
from engine.inventory_parser import is_user_compounding_held, materialize_current_inventory
from engine.pipeline.gates import _stock_issue_data_request
from engine.pipeline.preflight import resolve_inventory_stock_contract


@pytest.fixture
def completion_log(tmp_path, monkeypatch):
    path = tmp_path / "inventory-completions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(path))
    return path


def _stock(materialized, identity: str, stock_id: str = ""):
    return next(
        stock
        for stock in materialized.stocks
        if stock.identity_name == identity and (not stock_id or stock.stock_id == stock_id)
    )


def _complete(identity: str, key: str, *, held: bool = False, **overrides):
    """Complete the identity's first stock (its first held stock when ``held``)."""
    baseline = materialize_current_inventory()
    stock = next(
        stock
        for stock in baseline.stocks
        if stock.identity_name == identity and not (held and stock.execution_ready)
    )
    command = {
        "stock_id": stock.stock_id,
        "expected_effective_inventory_sha256": baseline.effective_inventory_sha256,
        "idempotency_key": key,
        "fraction_decimal": "1",
        "fraction_basis": "neat",
        "carrier": "",
        "physical_form": "liquid",
        "possession_confirmed": True,
        "homogeneity": "NOT_APPLICABLE",
        "final_fraction_known": True,
        "source_kind": "SUPPLIER_LABEL",
        "user_note": "",
        **overrides,
    }
    receipt, completed = record_inventory_completion(**command)
    return receipt, _stock(completed, identity, stock.stock_id)


def _stock_issue_reasons(material: str, fraction: float) -> list[str]:
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {material: 100.0}, "dilutions": {material: fraction}}
    )
    return [issue["reason"] for issue in check.data["issues"]]


def test_identity_only_intake_completed_on_stock_page_passes_preflight(completion_log) -> None:
    assert _stock_issue_reasons("Vertofix Coeur", 1.0) == ["inventory_stock_non_executable"]

    receipt, stock = _complete("Vertofix Coeur", "vertofix-coeur-neat")

    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert all(receipt[field] is False for field in FALSE_ACTION_AUTHORITY)
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {"Vertofix Coeur": 100.0}, "dilutions": {"Vertofix Coeur": 1.0}}
    )
    assert check.data["issues"] == []
    (matched,) = check.data["matched_stocks"]
    assert matched["stock_facts_source"]["kind"] == "LAB_STOCK_PAGE_COMPLETION"
    assert matched["stock_facts_source"]["event_sha256"] == receipt["event_sha256"]


def test_completion_with_unspecified_basis_leaves_stock_held(completion_log) -> None:
    _receipt, stock = _complete(
        "Vertofix Coeur",
        "vertofix-coeur-unspecified",
        fraction_decimal="0.1",
        fraction_basis="unspecified",
        carrier="DPG",
        physical_form="solution",
        homogeneity="HOMOGENEOUS",
    )

    assert stock.design_ready is False
    assert stock.execution_ready is False
    assert stock.execution_hold_reason == "STOCK_PAGE_ENTRY_INCOMPLETE|STOCK_INTAKE_IDENTITY_ONLY"
    assert _stock_issue_reasons("Vertofix Coeur", 0.1) == ["inventory_stock_non_executable"]


def test_lot_receipt_hold_clears_with_a_complete_stock_page_entry(completion_log) -> None:
    # AGENTS.md RULE 6: a lot or label receipt is not needed to compute a formula.
    assert _stock_issue_reasons("Cedrat FCF Sicilian", 1.0) == ["inventory_stock_non_executable"]

    _receipt, stock = _complete("Cedrat FCF Sicilian", "cedrat-neat")

    assert stock.design_ready is True
    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert _stock_issue_reasons("Cedrat FCF Sicilian", 1.0) == []


def test_unnamed_hold_clears_only_when_basis_or_carrier_was_missing(completion_log) -> None:
    # Cedarwood EO (China) already had neat facts; its hold is the unresolved species.
    _receipt, cedarwood = _complete(
        "Cedarwood EO (China; species unspecified)", "cedarwood-china-neat"
    )
    assert cedarwood.design_ready is True
    assert cedarwood.execution_ready is False

    # Aldehyde C10's unnamed hold is only its unstated basis and carrier.
    _receipt, c10 = _complete("Aldehyde C10", "aldehyde-c10-10-dpg", held=True, **_TEN_PERCENT_DPG)
    assert c10.execution_ready is True
    assert _stock_issue_reasons("Aldehyde C10", 0.1) == []


_TEN_PERCENT_DPG = {
    "fraction_decimal": "0.1",
    "fraction_basis": "mass_fraction",
    "carrier": "DPG",
    "physical_form": "solution",
    "homogeneity": "HOMOGENEOUS",
    "source_kind": "USER_LABEL_OR_RECIPE",
}


@pytest.mark.parametrize("identity", ["Apritone", "Aldehyde C16 EMPG"])
def test_identity_kept_separate_row_stays_held_after_a_complete_entry(completion_log, identity) -> None:
    # Their V5 rows read "IDENTITY KEPT SEPARATE": the carrier is missing too,
    # but the form's strength, basis and carrier do not settle which product it is.
    _receipt, stock = _complete(identity, f"{identity}-10-dpg", held=True, **_TEN_PERCENT_DPG)
    assert stock.design_ready is True
    assert stock.execution_ready is False
    assert completion_clears_execution_hold(stock) is False
    assert _stock_issue_reasons(identity, 0.1) == ["inventory_stock_metadata_incomplete"]


def test_incomplete_entry_on_a_ready_stock_holds_it_until_a_complete_entry(completion_log) -> None:
    assert _stock_issue_reasons("Hedione", 1.0) == []
    _receipt, hedione = _complete(
        "Hedione",
        "hedione-incomplete",
        fraction_decimal="0.1",
        fraction_basis="unspecified",
        carrier="",
        physical_form="liquid",
        possession_confirmed=False,
        homogeneity="UNKNOWN",
    )
    assert hedione.design_ready is False
    assert hedione.execution_ready is False
    assert hedione.execution_hold_reason == STOCK_PAGE_ENTRY_INCOMPLETE
    assert _stock_issue_reasons("Hedione", 0.1) == ["inventory_stock_non_executable"]
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {"Hedione": 100.0}, "dilutions": {"Hedione": 0.1}}
    )
    issue = check.data["issues"][0]
    assert issue["stock_page_entry_clears"] is True
    assert "Lab app's Stock page" in _stock_issue_data_request(issue)

    _receipt, hedione = _complete("Hedione", "hedione-complete-neat")
    assert hedione.execution_ready is True
    assert hedione.execution_hold_reason == ""
    assert _stock_issue_reasons("Hedione", 1.0) == []


def test_complete_entry_that_changes_the_strength_wins_and_shows_the_authority(completion_log) -> None:
    _receipt, hedione = _complete("Hedione", "hedione-50-dpg", **{**_TEN_PERCENT_DPG, "fraction_decimal": "0.5"})
    assert hedione.execution_ready is True
    assert hedione.dilution == 0.5
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {"Hedione": 100.0}, "dilutions": {"Hedione": 0.5}}
    )
    assert check.data["issues"] == []
    (matched,) = check.data["matched_stocks"]
    assert matched["stock_facts_source"]["kind"] == "LAB_STOCK_PAGE_COMPLETION"
    assert matched["authority_facts_differ"] == {
        "dilution": 1.0,
        "fraction_basis": "neat",
        "carrier": "",
    }


def test_complete_entry_that_only_fills_gaps_reports_no_disagreement(completion_log) -> None:
    _receipt, c10 = _complete("Aldehyde C10", "aldehyde-c10-gap-fill", held=True, **_TEN_PERCENT_DPG)
    assert c10.authority_facts_differ == ()


def _held(reason: str, **extra):
    return SimpleNamespace(execution_hold_reason=reason, row_unresolved_tokens="", **extra)


def test_mixed_clearable_and_non_clearable_holds_are_kept() -> None:
    assert completion_clears_execution_hold(_held("STOCK_INTAKE_IDENTITY_ONLY|BOTTLE_LOT_AND_LABEL_RECEIPT_MISSING"))
    assert not completion_clears_execution_hold(_held("STOCK_INTAKE_IDENTITY_ONLY|USER_COMPOUNDING_HOLD"))
    assert not completion_clears_execution_hold(
        _held("TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED|FRACTION_BASIS_UNSPECIFIED")
    )


def test_tincture_safeguard_applies_within_a_combined_hold_reason() -> None:
    stock = _held(
        "FINAL_DISSOLVED_FRACTION_UNMEASURED|BOTTLE_LOT_AND_LABEL_RECEIPT_MISSING",
        execution_ready=False,
        design_ready=None,
        design_hold_reason="",
        dilution=0.2,
        fraction_basis="mass_fraction",
        carrier="ethanol",
        physical_form="liquid",
    )
    assert "final_usable_fraction_confirmation" in inventory_completion_requirements(stock)


def test_user_compounding_hold_still_applies_after_a_completion(completion_log) -> None:
    _receipt, orris = _complete(
        "Orris Liquid",
        "orris-liquid-details",
        fraction_decimal="0.09",
        fraction_basis="mass_fraction",
        carrier="DEP",
        physical_form="solution",
        homogeneity="HOMOGENEOUS",
        source_kind="USER_LABEL_OR_RECIPE",
    )

    assert orris.execution_ready is False
    assert is_user_compounding_held(orris)
    assert _stock_issue_reasons("Orris Liquid", 0.09) == ["inventory_stock_non_executable"]


def test_every_current_hold_reason_has_a_disposition(completion_log) -> None:
    reasons = {
        reason
        for stock in materialize_current_inventory().stocks
        if not stock.execution_ready
        for reason in (stock.execution_hold_reason.split("|") or [""])
    }
    assert reasons <= set(COMPLETION_HOLD_DISPOSITIONS)
    assert "USER_COMPOUNDING_HOLD" not in COMPLETION_CLEARABLE_HOLDS


def test_hold_text_for_clearable_reasons_points_to_the_stock_page() -> None:
    issue = {
        "reason": "inventory_stock_non_executable",
        "execution_holds": ["STOCK_INTAKE_IDENTITY_ONLY"],
        "stock_page_entry_clears": True,
        "fraction_matches_formula": True,
    }
    request = _stock_issue_data_request(issue)
    assert request == "on the Lab app's Stock page, fill in the strength, basis and carrier"
    kept = _stock_issue_data_request(
        {
            **issue,
            "execution_holds": [
                "STOCK_INTAKE_IDENTITY_ONLY",
                "TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED",
            ],
            "stock_page_entry_clears": False,
        }
    )
    assert "Stock page" not in kept
    assert kept.endswith("record the tincture percentage basis and extracted solids")


def test_hold_text_for_an_unclearable_unnamed_hold_does_not_name_the_stock_page(completion_log) -> None:
    # Cedarwood EO (China)'s hold is its unresolved species, not a form field.
    check = resolve_inventory_stock_contract(
        {
            "ingredients_ul": {"Cedarwood EO (China; species unspecified)": 100.0},
            "dilutions": {"Cedarwood EO (China; species unspecified)": 1.0},
        }
    )
    (issue,) = check.data["issues"]
    assert issue["stock_page_entry_clears"] is False
    assert "Stock page" not in str(_stock_issue_data_request(issue))
