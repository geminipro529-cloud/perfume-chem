"""Plan item A4: every HOLD on a formula says what is missing and where to supply it.

Expectations are read from the inventory itself (not hard-coded stock names), so the
tests keep holding as Kenny confirms stocks and the stock list grows.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import hold_reasons as hr
from engine.formulation_intelligence.hold_reasons import TEXT_ONLY_ACTION, explain_holds
from engine.inventory_completions import (
    completion_clears_execution_hold,
    inventory_completion_requirements,
)
from engine.inventory_parser import materialize_current_inventory
from engine.name_utils import normalize_name
from engine.personal_inventory import materialize_personal_inventory


@pytest.fixture(scope="module")
def projection():
    return materialize_personal_inventory()


@pytest.fixture(scope="module")
def governed():
    return materialize_current_inventory().stocks


def _owned(projection):
    return [s for s in projection.stocks if str(s.status).casefold() == "owned"]


def _row(stock, amount="300"):
    return {
        "material": stock.identity_name or stock.name,
        "stock_id": stock.stock_id,
        "amount_ul": amount,
        "fraction": format(stock.dilution, "g") if stock.dilution else "1",
        "basis": stock.fraction_basis or "",
        "carrier": stock.carrier or "",
    }


def _items_for(result, material):
    return [item for item in result["items"] if item["material"] == material]


def test_a_stock_with_missing_details_names_them_and_opens_its_stock_page_entry(projection):
    stock = next(
        s for s in _owned(projection)
        if s.stock_id in projection.canonical_stock_ids
        and not s.execution_ready
        and [f for f in inventory_completion_requirements(s) if f != "USER_COMPOUNDING_HOLD"]
        and "USER_COMPOUNDING_HOLD" not in inventory_completion_requirements(s)
    )
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["reason"].startswith("Its details are not complete: ")
    assert item["open"] == {"kind": "stock_page", "stock_id": stock.stock_id}
    assert item["action"] == "Open it on the Stock page and fill those in."
    assert result["inventory_modified"] is False and result["formula_modified"] is False


def _receipt_only(stock):
    holds = [h for h in str(stock.execution_hold_reason or "").split("|") if h]
    return bool(holds) and all("RECEIPT" in h for h in holds)


def test_a_stock_held_only_for_a_receipt_says_mixing_does_not_need_one(projection):
    # Kenny's bottle and strength are on record; only a lot or receipt is marked missing
    # (Rule 6). The form's own "confirm you own it" tick is not asked as a missing detail.
    candidates = [
        s for s in _owned(projection)
        if s.stock_id in projection.canonical_stock_ids
        and not s.execution_ready
        and set(inventory_completion_requirements(s)) <= {"possession_confirmation"}
        and completion_clears_execution_hold(s)
        and _receipt_only(s)
        and str(s.fraction_basis) != "mass_fraction_starting_charge"
    ]
    if not candidates:
        pytest.skip("no receipt-held stock in the current inventory")
    for stock in candidates[:3]:
        result = explain_holds([_row(stock)])

        (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
        assert "which mixing doesn't need (Rule 6)" in item["reason"]
        assert not item["reason"].startswith("Its details are not complete")
        assert item["open"] == {"kind": "stock_page", "stock_id": stock.stock_id}
        assert item["owner"] == "you"


def test_a_tincture_from_a_starting_charge_asks_about_its_built_strength_not_the_form(projection):
    candidates = [
        s for s in _owned(projection)
        if s.stock_id in projection.canonical_stock_ids
        and not s.execution_ready
        and str(s.fraction_basis) == "mass_fraction_starting_charge"
    ]
    if not candidates:
        pytest.skip("no starting-charge tincture in the current inventory")
    stock = candidates[0]
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["reason"].startswith("How much of it actually dissolved was never measured")
    assert f"the strength it was made at ({hr._percent_text(float(stock.dilution))})" in item["action"]
    assert item["open"] is None and item["owner"] == "you"


def _text_only(projection):
    return [s for s in _owned(projection) if s.stock_id not in projection.canonical_stock_ids and s.dilution]


def test_a_stock_only_inventory_txt_lists_is_claudes_to_add_when_the_checks_have_no_bottle(projection, governed):
    stock = next(s for s in _text_only(projection) if not hr._governed_twins(s, governed))
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["action"] == TEXT_ONLY_ACTION
    assert "stock workbook" not in item["reason"]
    assert item["open"] is None and item["owner"] == "claude"


def test_a_bottle_the_checks_list_under_an_overlay_alias_is_named_not_asked_for(projection, governed):
    # Kenny's overlays give a canonical name and its aliases ("Haitian Vetiver EO" is
    # "Vetiver EO (Haiti)"): the same bottle is named, and nothing is asked of him.
    aliases = hr._overlay_aliases()
    candidates = [
        s for s in _text_only(projection)
        if normalize_name(str(s.identity_name or s.name)) in aliases
        and any(abs(float(t.dilution or 0) - float(s.dilution)) < 1e-9 for t in hr._governed_twins(s, governed))
    ]
    if not candidates:
        pytest.skip("no text-only stock is an overlay alias of a checked bottle")
    stock = candidates[0]
    twins = hr._governed_twins(stock, governed)
    canonical = aliases[normalize_name(str(stock.identity_name or stock.name))]
    assert {normalize_name(str(t.identity_name or t.name)) for t in twins} == {normalize_name(canonical)}
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["action"] == hr.LINK_ACTION
    assert any(f'"{t.name}"' in item["reason"] for t in twins)
    assert item["owner"] == "claude"


def test_a_strength_the_two_lists_disagree_on_is_asked_once():
    target = SimpleNamespace(identity_name="Aurantiol", name="Aurantiol", dilution=1.0, carrier="",
                             status="owned", stock_id="t-1")
    twin = SimpleNamespace(identity_name="Aurantiol", name="Aurantiol 10% in DPG", dilution=0.1, carrier="dpg",
                           status="owned", stock_id="g-1", execution_ready=True)
    item = hr._text_only_item({"material": "Aurantiol"}, target, [twin])

    assert item["reason"] == "Your inventory list says neat; the checks' stock list has only 10% in DPG."
    assert item["owner"] == "you" and "which you have" in item["action"]


def test_two_named_origins_are_never_taken_for_one_bottle():
    target = SimpleNamespace(identity_name="Lavender EO (BONTAUX SAS)", name="Lavender EO (BONTAUX SAS)",
                             dilution=1.0, carrier="", status="owned", stock_id="t-1")
    other = SimpleNamespace(identity_name="Lavender EO (Bulgaria)", name="Lavender EO (Bulgaria)", dilution=1.0,
                            carrier="", status="owned", stock_id="g-1", execution_ready=True)
    bare = SimpleNamespace(identity_name="Rosemary EO", name="Rosemary EO (neat)", dilution=1.0, carrier="",
                           status="owned", stock_id="g-2", execution_ready=True)
    noted = SimpleNamespace(identity_name="Rosemary EO (French leaf oil)", name="Rosemary EO (French leaf oil) (neat)",
                            dilution=1.0, carrier="", status="owned", stock_id="t-2")

    assert hr._governed_twins(target, [other]) == []
    assert hr._governed_twins(noted, [bare, other]) == [bare]
    # Two different materials sharing the base name make the match ambiguous.
    cedar = SimpleNamespace(identity_name="Cedarwood EO", name="Cedarwood EO", dilution=1.0, carrier="",
                            status="owned", stock_id="t-3")
    china = SimpleNamespace(identity_name="Cedarwood EO (China)", name="Cedarwood EO (China)", dilution=1.0,
                            carrier="", status="owned", stock_id="g-3", execution_ready=False)
    atlas = SimpleNamespace(identity_name="Cedarwood EO (Atlas)", name="Cedarwood EO (Atlas)", dilution=1.0,
                            carrier="", status="owned", stock_id="g-4", execution_ready=True)
    assert hr._governed_twins(cedar, [china]) == [china]
    assert hr._governed_twins(cedar, [china, atlas]) == []


def test_a_material_not_owned_says_buy_or_swap_and_ifra_says_why_it_cannot_check():
    result = explain_holds([{"material": "Zzyzx Moonflower Absolute", "amount_ul": "200", "fraction": "1"}])

    stock = [i for i in result["items"] if i["check"] == "stock"]
    ifra = [i for i in result["items"] if i["check"] == "ifra"]
    assert [i["reason"] for i in stock] == ["It is not in your stock."]
    assert stock[0]["action"] == "Buy it, or swap the row for a similar stock you own."
    assert stock[0]["owner"] == "you"
    assert ifra and ifra[0]["reason"].startswith("IFRA's Category 4 table does not know it by this name")
    # Claude matches the name to the IFRA table; Kenny is not sent for a CAS number.
    assert ifra[0]["action"] == hr.IFRA_NAME_ACTION and ifra[0]["owner"] == "claude"
    assert all(i["reason"] and i["action"] for i in result["items"])


def test_every_item_has_a_reason_an_action_and_a_unique_id(projection):
    rows = [_row(s, "150") for s in _owned(projection)[:25]]
    result = explain_holds(rows)

    ids = [item["id"] for item in result["items"]]
    assert len(ids) == len(set(ids))
    owners = [item["owner"] for item in result["items"]]
    assert owners == sorted(owners, key=lambda owner: owner != "you"), "items needing Kenny come first"
    for item in result["items"]:
        assert item["check"] in {"stock", "ifra"}
        assert item["owner"] in {"you", "claude"}
        assert item["reason"][:1].isupper() and item["reason"].endswith(".")
        assert item["action"]
        assert "CAS" not in item["action"]
        # A supplier IFRA certificate is never asked for to mix at the bench (Rule 6).
        if "IFRA certificate" in item["action"]:
            assert item["action"] == hr.IFRA_LABEL_ACTION
        assert item["open"] is None or item["open"]["kind"] == "stock_page"
    you = owners.count("you")
    if you and len(owners) - you:
        assert result["summary"].startswith(f"{you} item")


def test_no_rows_and_a_clean_summary():
    assert explain_holds([])["summary"] == "Add rows with amounts to check them."
    assert explain_holds([{"material": "Hedione", "amount_ul": "0"}])["items"] == []
