"""The buy list's needs: what the saved cards call for that Kenny owns on neither stock list."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from engine.buy_needs import card_needs, material_key
from engine.formulation_intelligence import hold_reasons as hr

_NOT_OWNED = {"check": "stock", "code": "not_in_inventory", "stock_state": hr.STOCK_NOT_OWNED,
              "reason": "It is not in your stock."}
_DISAGREE = {"check": "stock", "code": "not_in_inventory", "stock_state": hr.STOCK_LISTS_DISAGREE,
             "reason": "It is on your inventory list, but the checks could not match it to a bottle."}
_WRONG_STRENGTH = {"check": "stock", "code": "stock_fraction_mismatch", "stock_state": hr.STOCK_OWNED,
                   "reason": "The formula uses it at 10%; your bottle is 1%."}
_IFRA = {"check": "ifra", "code": "ifra_name_not_recognised", "reason": "IFRA's table does not know it."}


class _Registry:
    def __init__(self, names):
        self._names = {alias.casefold(): canonical for alias, canonical in names.items()}

    def get(self, name):
        canonical = self._names.get(name.casefold())
        return SimpleNamespace(canonical_name=canonical) if canonical else None


_REGISTRY = _Registry({"Ambroxan": "Ambroxan", "Ambrox": "Ambroxan"})


def _holds(states, calls=None):
    """A stand-in for explain_holds: per material, the items given in ``states``."""

    def holds(rows, *, bottle_ml):
        if calls is not None:
            calls.append((rows, bottle_ml))
        items = []
        for row in rows:
            for item in states.get(row["material"], []):
                if item == "raise":
                    raise RuntimeError("the gate could not read this card")
                items.append({"material": row["material"], **item})
        return {"items": items}

    return holds


def _row(material, amount, fraction="", solid=False, stock_id=None):
    return {"material": material, "stock_id": stock_id, "fraction": fraction, "basis": "", "carrier": None,
            "solid": solid, "amount": amount, "note": ""}


def _card(name, rows, bottle_ml="30", formula_id=None):
    return {"formula_id": formula_id or f"id-{name}", "version": 2, "name": name, "bottle_ml": bottle_ml, "rows": rows}


def test_a_material_in_two_cards_is_one_need_naming_both_cards():
    cards = [
        _card("Zest", [_row("Ambroxan", "100"), _row("Ethanol", "23900")]),
        _card("Iris", [_row("Iso E Super", "300"), _row("Hedione", "700")]),
        _card("Amber", [_row("Ambrox", "50"), _row("Hedione", "150")]),
    ]
    states = {"Ambroxan": [_NOT_OWNED], "Ambrox": [_NOT_OWNED], "Iso E Super": [_NOT_OWNED, _IFRA]}
    result = card_needs(cards, registry=_REGISTRY, holds=_holds(states))

    assert [(n["material_key"], n["material"]) for n in result["needs"]] == [
        ("ambroxan", "Ambroxan"), ("iso e super", "Iso E Super"),
    ]
    ambroxan = result["needs"][0]
    assert ambroxan["cards"] == [
        {"formula_id": "id-Amber", "version": 2, "name": "Amber", "neat_fraction": Decimal("0.25")},
        {"formula_id": "id-Zest", "version": 2, "name": "Zest", "neat_fraction": Decimal("1")},
    ]
    assert result["needs"][1]["cards"][0]["neat_fraction"] == Decimal("0.3")
    assert result["disagreements"] == [] and result["unreadable"] == []


def test_neat_fraction_is_exact_active_over_the_concentrate():
    calls = []
    rows = [
        _row("Ambroxan", "1000/3"),  # blank strength: neat
        _row("Hedione", "600", "0.1"),
        _row("Vanillin", "200", "0.5", solid=True),  # mg counts as uL
        _row("Hedione", "100", ".2"),  # a second row of one material adds up
        _row("Perfumer's Alcohol", "20000"),
        _row("", "50"),
        _row("Cashmeran", ""),
    ]
    states = {m: [_NOT_OWNED] for m in ("Ambroxan", "Hedione", "Vanillin")}
    result = card_needs([_card("Exact", rows, bottle_ml="")], registry=_REGISTRY, holds=_holds(states, calls))

    # The concentrate is 1000/3 + 600 + 200 + 100 = 3700/3 uL; ethanol is not in it.
    got = {n["material"]: n["cards"][0]["neat_fraction"] for n in result["needs"]}
    assert got["Ambroxan"] == Decimal(1000) / Decimal(3700)  # (1000/3) / (3700/3), exactly
    assert got["Hedione"] == Decimal(240) / Decimal(3700)  # (60 + 20) uL active
    assert got["Vanillin"] == Decimal(300) / Decimal(3700)
    # The holds rows are the editor's: no ethanol, no unnamed or empty rows, six decimals,
    # strength "1" when blank, and a blank bottle is 30 mL.
    ((sent, bottle_ml),) = calls
    assert bottle_ml == 30.0
    assert sent == [
        {"material": "Ambroxan", "stock_id": "", "amount_ul": "333.333333", "fraction": "1", "basis": "", "carrier": ""},
        {"material": "Hedione", "stock_id": "", "amount_ul": "600", "fraction": "0.1", "basis": "", "carrier": ""},
        {"material": "Vanillin", "stock_id": "", "amount_ul": "200", "fraction": "0.5", "basis": "", "carrier": ""},
        {"material": "Hedione", "stock_id": "", "amount_ul": "100", "fraction": "0.2", "basis": "", "carrier": ""},
    ]


def test_a_strength_the_editor_cannot_read_is_neat_as_the_editor_reads_it():
    # editorNumber reads decimals only: "1/10" and "15" (above 1) are sent as neat.
    calls = []
    rows = [_row("Ambroxan", "100", "1/10"), _row("Hedione", "100", "15"), _row("Ethanol", "5000")]
    result = card_needs([_card("Odd", rows, bottle_ml="50")], registry=_REGISTRY,
                        holds=_holds({"Ambroxan": [_NOT_OWNED]}, calls))

    ((sent, bottle_ml),) = calls
    assert bottle_ml == 50.0 and [r["fraction"] for r in sent] == ["1", "1"]
    assert [r["material"] for r in sent] == ["Ambroxan", "Hedione"]
    assert result["needs"][0]["cards"][0]["neat_fraction"] == Decimal("0.5")


def test_a_disagreement_is_kept_apart_and_names_both_lists():
    cards = [
        _card("One", [_row("Ambroxan", "100"), _row("Cedarwood EO", "100")]),
        _card("Two", [_row("Cedarwood EO", "300"), _row("Hedione", "100")]),
    ]
    states = {"Ambroxan": [_NOT_OWNED], "Cedarwood EO": [_DISAGREE]}
    result = card_needs(cards, registry=_REGISTRY, holds=_holds(states))

    assert [n["material"] for n in result["needs"]] == ["Ambroxan"]
    (disagreement,) = result["disagreements"]
    assert disagreement["material_key"] == "cedarwood eo" and disagreement["code"] == "not_in_inventory"
    assert disagreement["reason"] == _DISAGREE["reason"]
    assert [(c["name"], c["neat_fraction"]) for c in disagreement["cards"]] == [
        ("One", Decimal("0.5")), ("Two", Decimal("0.75")),
    ]


def test_a_disagreement_in_any_card_is_never_a_need():
    cards = [_card("A", [_row("Cedarwood EO", "100")]), _card("B", [_row("Cedarwood EO", "100")])]
    states_by_card = iter([[_NOT_OWNED], [_DISAGREE]])

    def holds(rows, *, bottle_ml):
        return {"items": [{"material": "Cedarwood EO", **item} for item in next(states_by_card)]}

    result = card_needs(cards, registry=_REGISTRY, holds=holds)
    assert result["needs"] == []
    assert [c["name"] for c in result["disagreements"][0]["cards"]] == ["A", "B"]


def test_an_owned_material_at_another_strength_is_not_a_need():
    cards = [
        _card("A", [_row("Aurantiol", "100", "0.1"), _row("Hedione", "100")]),
        _card("B", [_row("Hedione", "100")]),
    ]
    states_by_card = iter([
        [{"material": "Aurantiol", **_WRONG_STRENGTH}, {"material": "Hedione", **_WRONG_STRENGTH}],
        [{"material": "Hedione", **_NOT_OWNED}],
    ])

    def holds(rows, *, bottle_ml):
        return {"items": next(states_by_card)}

    result = card_needs(cards, registry=_REGISTRY, holds=holds)
    # Owned (in card A) is owned: Hedione never appears, even where card B's check missed it.
    assert result == {"needs": [], "disagreements": [], "unreadable": []}


def test_a_card_whose_check_fails_is_unreadable_and_the_rest_still_count():
    cards = [
        _card("Broken", [_row("Mystery", "100")], formula_id="f-broken"),
        _card("Fine", [_row("Ambroxan", "100")]),
        _card("Bad bottle", [_row("Ambroxan", "100")], bottle_ml="thirty"),
    ]
    result = card_needs(cards, registry=_REGISTRY, holds=_holds({"Mystery": ["raise"], "Ambroxan": [_NOT_OWNED]}))

    assert result["unreadable"][0] == {
        "formula_id": "f-broken", "name": "Broken", "error": "the gate could not read this card",
    }
    assert [u["name"] for u in result["unreadable"]] == ["Broken", "Bad bottle"]
    assert [(n["material"], [c["name"] for c in n["cards"]]) for n in result["needs"]] == [("Ambroxan", ["Fine"])]


def test_material_key_uses_the_registry_name_or_evens_the_spacing_and_case():
    assert material_key("AMBROX", registry=_REGISTRY) == "ambroxan"
    assert material_key("  Iso   E\tSuper ", registry=_REGISTRY) == "iso e super"


def test_a_material_kenny_does_not_own_is_a_need_with_the_real_checks():
    name = "Nootkatone"
    card = _card("Smoke", [_row(name, "20"), _row("Ethanol", "24000")])
    result = card_needs([card])

    assert [(n["material"], [c["neat_fraction"] for c in n["cards"]]) for n in result["needs"]] == [
        (name, [Decimal("1")]),
    ]
    assert result["disagreements"] == [] and result["unreadable"] == []
