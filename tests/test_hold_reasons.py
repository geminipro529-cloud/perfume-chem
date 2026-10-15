"""Plan item A4: every HOLD on a formula says what is missing and where to supply it.

Expectations are read from the inventory itself (not hard-coded stock names), so the
tests keep holding as Kenny confirms stocks and the stock list grows.
"""

from __future__ import annotations

import os
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
    assert item["reason"].startswith("How much of the resin actually dissolved was never measured")
    assert f"the strength it was made at ({hr._percent_text(float(stock.dilution))})" in item["action"]
    # The form refuses the recipe as a source but takes Kenny's own confirmation.
    assert "as your own confirmation" in item["action"] and "recipe" not in item["action"]
    assert item["open"] == {"kind": "stock_page", "stock_id": stock.stock_id} and item["owner"] == "you"


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

    def checked(stock):
        canonical = normalize_name(aliases[normalize_name(str(stock.identity_name or stock.name))])
        return [
            g for g in governed
            if str(g.status).casefold() == "owned" and normalize_name(str(g.identity_name or g.name)) == canonical
        ]

    candidates = [
        s for s in _text_only(projection)
        if normalize_name(str(s.identity_name or s.name)) in aliases
        and any(
            abs(float(t.dilution or 0) - float(s.dilution)) < 1e-9 and hr._same_form(t, s) and t.execution_ready
            for t in checked(s)
        )
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


def test_a_text_only_bottle_whose_checked_record_is_held_says_what_holds_that_record(projection, governed):
    # The tinctures Kenny built from resin (benzoin 40%, frankincense 33%) are on his
    # inventory list under longer names: linking the names would not let them be mixed,
    # so the question about the strength they were made at must still reach him.
    candidates = [
        s for s in _text_only(projection)
        if any(
            abs(float(t.dilution or 0) - float(s.dilution)) < 1e-9 and hr._same_form(t, s)
            and str(t.fraction_basis) == "mass_fraction_starting_charge" and not t.execution_ready
            for t in hr._governed_twins(s, governed)
        )
    ]
    if not candidates:
        pytest.skip("no text-only tincture whose checked record is held")
    for stock in candidates:
        item = hr._text_only_item({"material": stock.name, "open": None}, stock, governed)

        assert item["reason"].startswith("The checks' stock list has this bottle as \"")
        assert "How much of the resin actually dissolved was never measured" in item["reason"]
        assert f"the strength it was made at ({hr._percent_text(float(stock.dilution))})" in item["action"]
        assert item["owner"] == "you" and item["action"] != hr.LINK_ACTION


def _stock(name, dilution, carrier="", basis="", identity=None, ready=True, stock_id="g-1",
           authority="CURRENT_INVENTORY_MASTER_V5_EXTERNAL_SNAPSHOT"):
    return SimpleNamespace(identity_name=identity or name, name=name, dilution=dilution, carrier=carrier,
                           fraction_basis=basis, status="owned", stock_id=stock_id, execution_ready=ready,
                           authority=authority)


def test_a_held_record_the_stock_page_does_not_list_is_not_sent_to_its_form(projection, governed):
    # The Stock page shows inventory.txt's line for the bottle, not the checks' record, so a
    # button to that record would open nothing; Claude completes it from the inventory line.
    listed = {s.stock_id for s in projection.stocks}
    candidates = [
        (s, t) for s in _text_only(projection) for t in hr._governed_twins(s, governed)
        if abs(float(t.dilution or 0) - float(s.dilution)) < 1e-9 and hr._same_form(t, s)
        and not t.execution_ready and t.stock_id not in listed
        and str(t.fraction_basis) != "mass_fraction_starting_charge"
        and not str(getattr(t, "row_unresolved_tokens", "") or "")
    ]
    if not candidates:
        pytest.skip("no text-only bottle whose held record is off the Stock page")
    for stock, twin in candidates:
        item = hr._text_only_item({"material": stock.name, "open": None}, stock, governed, listed)

        assert item["open"] is None, stock.name
        assert item["owner"] == "claude" and item["action"] == hr.OFF_PAGE_ACTION
        assert f'this bottle as "{twin.name}"' in item["reason"]
    # Every Stock page button in a real formula's list opens a stock the page shows.
    result = explain_holds([_row(s, "150") for s in _text_only(projection)[:40]])
    for entry in result["items"]:
        assert entry["open"] is None or entry["open"]["stock_id"] in listed, entry["material"]


def test_a_strength_inventory_txt_also_lists_is_another_bottle_not_a_disagreement():
    target = _stock("Alpha Damascone 10%", 0.1, identity="Alpha Damascone", stock_id="t-1")
    neat = _stock("Alpha Damascone", 1.0)
    both = {normalize_name("Alpha Damascone"): {0.1, 1.0}}
    item = hr._text_only_item({"material": "Alpha Damascone 10%"}, target, [neat], None, both)

    assert item["owner"] == "claude" and item["action"] == TEXT_ONLY_ACTION
    assert item["reason"] == (
        'Your inventory list has it at 10% as well as "Alpha Damascone" (neat); the checks\' stock list has '
        "only the other, so this bottle isn't on it yet."
    )
    # inventory.txt lists only the 10%: the two lists disagree, so Kenny is asked.
    only = {normalize_name("Alpha Damascone"): {0.1}}
    item = hr._text_only_item({"material": "Alpha Damascone 10%"}, target, [neat], None, only)
    assert item["owner"] == "you" and item["action"] == hr.STRENGTH_ACTION


def test_a_plainer_named_record_at_the_same_strength_is_asked_about_not_hidden():
    # "Aldehyde C11 undecylenic 1%" matches "Aldehyde C11 neat"; the checks also list
    # "Aldehyde C11 1%", which may be undecylenic or undecylic, so the Lab asks.
    target = _stock("Aldehyde C11 undecylenic", 0.01, stock_id="t-1")
    neat = _stock("Aldehyde C11 neat", 1.0, identity="Aldehyde C11 neat")
    one = _stock("Aldehyde C11 1%", 0.01, identity="Aldehyde C11", stock_id="g-2")
    assert hr._twin_match(target, [neat, one])[0] == [neat]
    item = hr._text_only_item({"material": "Aldehyde C11 undecylenic"}, target, [neat, one])

    assert item["owner"] == "you" and item["action"] == hr.SAME_BOTTLE_ACTION
    assert item["reason"].startswith('The checks\' stock list has "Aldehyde C11 1%", which may be this bottle (1%)')


def test_a_record_the_stock_page_cannot_settle_names_what_is_unresolved(governed):
    unresolved = [
        s for s in governed
        if str(s.status).casefold() == "owned" and not s.execution_ready
        and str(getattr(s, "row_unresolved_tokens", "") or "")
        and str(s.fraction_basis) != "mass_fraction_starting_charge"
    ]
    if not unresolved:
        pytest.skip("no stock with an unresolved workbook row")
    for stock in unresolved:
        item = hr._canonical_hold({"material": stock.name}, stock)

        assert item["reason"].startswith("The Stock page form cannot settle this one: "), stock.name
        assert "_" not in item["reason"] and item["open"] is None and item["owner"] == "you"
    assert hr._canonical_hold({}, SimpleNamespace(
        execution_hold_reason="", row_unresolved_tokens="SPECIES UNRESOLVED", execution_ready=False,
        design_ready=None, design_hold_reason="", dilution=1.0, fraction_basis="neat", carrier="",
        physical_form="liquid", status="owned", stock_id="g-9",
    ))["reason"] == "The Stock page form cannot settle this one: its species is not known."


def test_small_wording_rules():
    assert not hr._qualified("Evernyl (crystals)") and hr._qualified("Jasmine Absolute (Jasminum grandiflorum)")
    assert hr._carrier_text("jojoba oil") == "jojoba oil" and hr._carrier_text("ethanol + dep") == "ethanol + DEP"
    assert not hr._same_form(_stock("A", 0), _stock("A", 0))
    item = hr._text_only_item({"material": "A"}, _stock("A", 0, stock_id="t-1"), [_stock("A 10%", 0.1, identity="A")])
    assert item["reason"] == 'Your inventory list gives no strength; the checks\' stock list has "A 10%".'
    assert hr._FIELD_SENTENCES["fraction_percent"] == "write down its strength"
    # A grade only one name carries makes a display-name match a guess.
    tuberose = _stock("Tuberose Absolute", 1.0, identity="Tuberose Absolute (volume grade)", stock_id="t-2")
    assert hr._twin_match(tuberose, [_stock("Tuberose Absolute 10%", 0.1, "dpg", identity="Tuberose Absolute")])[1] == "probable"


def test_a_strength_the_two_lists_disagree_on_names_the_checked_entry_and_asks_once():
    target = _stock("Aurantiol", 1.0, stock_id="t-1")
    twin = _stock("Aurantiol 10% in DPG", 0.1, "dpg", identity="Aurantiol")
    item = hr._text_only_item({"material": "Aurantiol"}, target, [twin])

    assert item["reason"] == 'Your inventory list says neat; the checks\' stock list has "Aurantiol 10% in DPG".'
    assert item["owner"] == "you" and item["action"] == hr.STRENGTH_ACTION
    # A name that doesn't carry its strength gets it in brackets.
    item = hr._text_only_item({"material": "Anise EO"}, target, [_stock("Aurantiol", 0.01, "dpg")])
    assert item["reason"].endswith('has "Aurantiol" (1% in DPG).')


def test_another_solvent_at_one_strength_is_never_called_the_same_bottle():
    # inventory.txt: Neroli EO 10% in ethanol; the checks: Aroma & More's 10% in jojoba.
    target = _stock("Neroli EO", 0.1, "ethanol", "volume_fraction", stock_id="t-1")
    jojoba = _stock("Neroli EO 10%", 0.1, "jojoba", "mass_fraction", identity="Neroli EO",
                    authority="USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261014")
    item = hr._text_only_item({"material": "Neroli EO"}, target, [jojoba])

    # The checked record quotes Kenny's own word (a dated overlay): Claude corrects inventory.txt.
    assert item["action"] == hr.FORM_ACTION and item["owner"] == "claude"
    assert item["reason"] == (
        'The checks\' stock list has "Neroli EO 10%" at 10% in jojoba, from what you told Claude; '
        "your inventory list says 10% in ethanol."
    )
    assert "this bottle" not in item["reason"]
    # A stock workbook record is not his word on record: he is asked (Rule 0).
    workbook = _stock("Neroli EO 10%", 0.1, "jojoba", "mass_fraction", identity="Neroli EO")
    item = hr._text_only_item({"material": "Neroli EO"}, target, [workbook])
    assert item["action"] == hr.FORM_ASK_ACTION and item["owner"] == "you"
    assert item["reason"].endswith("but your inventory list says 10% in ethanol, so the Lab keeps the two apart.")
    # Only the basis differs: the words say which is by weight and which by volume.
    by_volume = _stock("Neroli EO", 0.1, "jojoba", "volume_fraction", stock_id="t-2")
    item = hr._text_only_item({"material": "Neroli EO"}, by_volume, [jojoba])
    assert "at 10% in jojoba by weight, from what you told Claude; your inventory list says 10% in jojoba by volume" in item["reason"]
    # The same solvent written two ways, or an unknown one, is one bottle.
    same = _stock("Neroli EO", 0.1, "Jojoba w/w", "", stock_id="t-3")
    assert hr._text_only_item({"material": "Neroli EO"}, same, [jojoba])["action"] == hr.LINK_ACTION
    assert hr._same_form(_stock("Benzoin", 0.4, "", "mass_fraction"),
                         _stock("Benzoin Tincture", 0.4, "ethanol", "mass_fraction_starting_charge"))


def test_a_name_match_on_a_guess_is_asked_not_claimed():
    cedar = _stock("Cedarwood EO", 1.0, stock_id="t-1")
    china = _stock("Cedarwood EO (China; species unspecified)", 1.0)
    item = hr._text_only_item({"material": "Cedarwood EO"}, cedar, [china])

    assert item["owner"] == "you" and item["action"] == hr.SAME_BOTTLE_ACTION
    assert "may be this bottle (neat)" in item["reason"] and "this bottle as" not in item["reason"]
    diluted = _stock("Cedarwood EO", 0.1, "dpg", stock_id="t-2")
    item = hr._text_only_item({"material": "Cedarwood EO"}, diluted, [china])
    assert item["action"] == hr.SAME_MATERIAL_ACTION and "the same material as this one" in item["reason"]
    # Square brackets are notes too, and a CAS number in brackets is not an origin.
    assert hr._qualified("Vetiver EO [Haiti]") and not hr._qualified("Vetikon (7403-42-1) (neat)")
    assert hr._governed_twins(_stock("Vetiver EO [Haiti]", 1.0), [_stock("Vetiver EO [Java]", 1.0)]) == []
    assert hr._twin_match(_stock("Vetikon (7403-42-1) (neat)", 1.0), [_stock("Vetikon", 1.0)])[1] == "name"


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
    # Kenny's item comes first and the ids follow the order shown.
    assert [i["owner"] for i in result["items"]][:2] == ["you", "claude"]
    assert [i["id"] for i in result["items"]] == [f"hold-{n}" for n in range(1, len(result["items"]) + 1)]
    yours = sum(1 for i in result["items"] if i["owner"] == "you")
    assert result["summary"].startswith(f"{yours} item{'' if yours == 1 else 's'} need")
    assert "Claude's part, with nothing for you to do" in result["summary"]


def test_kenny_s_items_come_first_and_the_ids_follow_what_is_shown(projection, governed):
    # The checks list the text-only stock (Claude's part) before the one not owned (his).
    stock = next(s for s in _text_only(projection) if not hr._governed_twins(s, governed))
    result = explain_holds([_row(stock), {"material": "Zzyzx Moonflower Absolute", "amount_ul": "200", "fraction": "1"}])

    owners = [i["owner"] for i in result["items"]]
    assert owners[0] == "you" and "claude" in owners
    assert owners == sorted(owners, key=lambda owner: owner != "you")
    assert [i["id"] for i in result["items"]] == [f"hold-{n}" for n in range(1, len(owners) + 1)]


def test_the_summary_says_when_nothing_needs_kenny():
    claude = {"owner": "claude"}
    assert hr._summary([claude, claude]) == "Nothing here needs you: 2 items are Claude's part. Each says what happens next."
    assert hr._summary([{"owner": "you"}, claude]) == (
        "1 item needs you; 1 is Claude's part, with nothing for you to do. Each says what to do."
    )
    assert hr._summary([{"owner": "you"}] * 2) == "2 items need you. Each says what to do."
    assert hr._summary([]).startswith("Nothing is missing")


def test_a_restricted_material_with_no_recorded_limit_is_claudes_table_work():
    (item,) = hr._ifra_items({"holds": [{
        "material": "Some Restricted Material", "matched_name": "Some Restricted Material", "verdict": "hold",
        "ifra_status": "restricted_unverified", "standard": "STD_123",
        "message": "Some Restricted Material at 0.2 % is restricted by STD_123 but its Category 4 limit is not recorded.",
    }]})

    assert item["action"] == hr.IFRA_LIMIT_ACTION and item["owner"] == "claude"
    assert item["reason"].startswith("IFRA restricts it (STD_123), but the Lab's IFRA table has no Category 4 limit")
    assert "supplier" not in item["action"] and "certificate" not in item["action"]


def test_an_overlay_written_while_the_app_runs_is_read_again(tmp_path, monkeypatch):
    monkeypatch.setattr(hr, "_GOVERNANCE", tmp_path)
    overlay = tmp_path / "inventory_user_authority_overlay_20991231.json"
    overlay.write_text('{"records": [{"canonical_name": "Vetiver EO (Haiti)", "aliases": ["Haitian Vetiver EO"]}]}')
    assert hr._overlay_aliases() == {normalize_name("Haitian Vetiver EO"): "Vetiver EO (Haiti)"}

    overlay.write_text('{"records": [{"canonical_name": "Vetiver EO (Haiti)", "aliases": ["Vetiver Haiti"]}]}')
    stamp = overlay.stat().st_mtime_ns + 1_000_000_000
    os.utime(overlay, ns=(stamp, stamp))
    assert hr._overlay_aliases() == {normalize_name("Vetiver Haiti"): "Vetiver EO (Haiti)"}


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


def test_each_stock_item_says_whether_the_two_lists_own_it():
    # The buy list reads stock_state: only "not_owned" is bought, "lists_disagree" picks neither.
    nothing = SimpleNamespace(stocks=[], canonical_stock_ids=set())
    issue = {"material": "Zzyzx Moonflower Absolute", "reason": "not_in_inventory"}
    assert hr._stock_item(issue, {}, {}, nothing, False)["stock_state"] == hr.STOCK_NOT_OWNED
    assert hr._stock_item(issue, {}, {}, nothing, True)["stock_state"] == hr.STOCK_LISTS_DISAGREE
    wrong = {"material": "Aurantiol", "reason": "stock_fraction_mismatch", "held_stock_strengths": [0.1]}
    assert hr._stock_item(wrong, {}, {}, nothing, False)["stock_state"] == hr.STOCK_OWNED
    # Stocks only inventory.txt lists: no bottle, or a match on a guess, is a disagreement;
    # another strength on the checks' list is owned on both lists.
    target = _stock("Aurantiol", 1.0, stock_id="t-1")
    assert hr._text_only_item({}, target, [])["stock_state"] == hr.STOCK_LISTS_DISAGREE
    cedar = _stock("Cedarwood EO", 1.0, stock_id="t-2")
    china = _stock("Cedarwood EO (China)", 1.0)
    assert hr._text_only_item({}, cedar, [china])["stock_state"] == hr.STOCK_LISTS_DISAGREE
    c11 = _stock("Aldehyde C11 undecylenic", 0.01, stock_id="t-3")
    neat = _stock("Aldehyde C11 neat", 1.0)
    one = _stock("Aldehyde C11 1%", 0.01, identity="Aldehyde C11", stock_id="g-2")
    assert hr._text_only_item({}, c11, [neat, one])["stock_state"] == hr.STOCK_LISTS_DISAGREE
    twin = _stock("Aurantiol 10% in DPG", 0.1, "dpg", identity="Aurantiol")
    assert hr._text_only_item({"stock_state": hr.STOCK_OWNED}, target, [twin])["stock_state"] == hr.STOCK_OWNED
    result = explain_holds([{"material": "Zzyzx Moonflower Absolute", "amount_ul": "200", "fraction": "1"}])
    assert [i["stock_state"] for i in result["items"] if i["check"] == "stock"] == [hr.STOCK_NOT_OWNED]
    assert all("stock_state" not in i for i in result["items"] if i["check"] == "ifra")


def test_no_rows_and_a_clean_summary():
    assert explain_holds([])["summary"] == "Add rows with amounts to check them."
    assert explain_holds([{"material": "Hedione", "amount_ul": "0"}])["items"] == []
