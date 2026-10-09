"""Stock-page completions count at the release gate (Kenny, 2026-10-09).

Every test writes to a temporary completion log through the environment
variable the app and the gate both read, never to the real data/user log.
"""

import pytest

from engine.inventory_completions import (
    COMPLETION_CLEARABLE_HOLDS,
    COMPLETION_HOLD_DISPOSITIONS,
    FALSE_ACTION_AUTHORITY,
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


def _stock(materialized, identity: str):
    return next(stock for stock in materialized.stocks if stock.identity_name == identity)


def _complete(identity: str, key: str, **overrides):
    baseline = materialize_current_inventory()
    stock = _stock(baseline, identity)
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
    return receipt, _stock(completed, identity)


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
    assert stock.execution_hold_reason == "STOCK_INTAKE_IDENTITY_ONLY"
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

    # Apritone's unnamed hold is its unstated basis and carrier.
    _receipt, apritone = _complete(
        "Apritone",
        "apritone-10-dpg",
        fraction_decimal="0.1",
        fraction_basis="mass_fraction",
        carrier="DPG",
        physical_form="solution",
        homogeneity="HOMOGENEOUS",
        source_kind="USER_LABEL_OR_RECIPE",
    )
    assert apritone.execution_ready is True
    assert _stock_issue_reasons("Apritone", 0.1) == []


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
        "fraction_matches_formula": True,
    }
    request = _stock_issue_data_request(issue)
    assert request == "on the Lab app's Stock page, fill in the strength, basis and carrier"
    kept = _stock_issue_data_request(
        {**issue, "execution_holds": ["TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED"]}
    )
    assert kept == "record the tincture percentage basis and extracted solids"
