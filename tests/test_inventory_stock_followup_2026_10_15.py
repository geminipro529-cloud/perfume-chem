"""Kenny's 15 Oct evening stock answers and his w/w-in-DPG rule (v26 records STK-035 to STK-106).

At 19:27 UTC he chose "Load the rule" on the card "Load your 'w/w in DPG' rule for the
72 dilutions with nothing recorded?": a dilution with no recorded basis is w/w, in DPG
unless his inventory line names another solvent. He then answered the neat-bottle
questions one at a time, and said the Tonka Bean Absolute 10% is PerfumersWorld's own
dilution.
"""

from __future__ import annotations

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract


def _owned():
    return [s for s in inventory.materialize_current_inventory().stocks if s.status.casefold() == "owned"]


def _by_name():
    return {s.name: s for s in _owned()}


def _check(name: str, fraction: float, basis: str, carrier: str):
    return resolve_inventory_stock_contract({
        "ingredients_ul": {name: 100.0},
        "dilutions": {name: fraction},
        "stock_specs": {name: {
            "fraction": fraction, "fraction_basis": basis,
            "carrier": carrier, "declared": True, "stock_id": "",
        }},
    })


@pytest.mark.parametrize(
    "name,fraction,carrier",
    [
        ("Adoxal 10% in DPG", 0.1, "dpg"),
        ("Aldehyde C11 1%", 0.01, "dpg"),
        ("Beta Ionone 0.1%", 0.001, "tec"),
        ("Calone 1% in DPG", 0.01, "dpg"),
        ("Galaxolide 50%", 0.5, "dep"),
        ("Geosmin 0.1%", 0.001, "tec"),
        ("Rose Oxide 1%", 0.01, "dpg"),
        ("Tuberose Absolute 10%", 0.1, "dpg"),
        ("Saffranal", 0.1, "dpg"),
        ("Phenyl Acetaldehyde", 0.85, "pea"),
        ("Rose de Mai Absolute", 0.1, "dpg"),
        ("Cis-3-Hexenyl Salicylate", 0.2, "dpg"),
    ],
)
def test_rule_stocks_are_ww_ready_and_keep_their_names(name, fraction, carrier):
    stock = _by_name()[name]
    assert stock.dilution == pytest.approx(fraction)
    assert (stock.fraction_basis, stock.carrier) == ("mass_fraction", carrier)
    assert stock.execution_ready is True
    assert stock.source_ref.endswith(tuple(f"STK-{n:03d}" for n in range(35, 107)))


def test_cis_3_hexenol_is_one_percent_in_ethanol_not_dpg():
    stock = _by_name()["cis-3-Hexenol 1%"]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.01, "mass_fraction", "ethanol")
    assert _check("cis-3-Hexenol", 0.01, "mass_fraction", "ethanol").status == "PASS"
    assert _check("cis-3-Hexenol", 0.01, "mass_fraction", "dpg").status == "FAIL"


@pytest.mark.parametrize(
    "name",
    ["Eugenol", "Anisaldehyde", "Cassis Base 345B", "Cocoa Absolute", "Dihydrojasmone",
     "Jessemal", "Pamzest", "Rhodinol ex Citronella"],
)
def test_confirmed_neat_bottles_are_owned_and_ready(name):
    stock = _by_name()[name]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.execution_ready is True


def test_new_inventory_text_dilutions_do_not_rename_the_neat_bottles():
    names = _by_name()
    for neat, dilution in (("Eugenol", "Eugenol 10%"), ("Anisaldehyde", "Anisaldehyde 10%"),
                           ("Lemonile", "Lemonile 1% in DPG"), ("Benzaldehyde", "Benzaldehyde 1% in DPG")):
        assert names[neat].dilution == 1.0
        assert names[dilution].dilution < 1.0
    assert names["Nerolin Bromelia 10% in DPG"].carrier == "dpg"


def test_tonka_is_the_perfumersworld_dilution_and_ready():
    (stock,) = [s for s in _owned() if s.identity_name == "Tonka Bean Absolute"]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.1, "mass_fraction", "dpg")
    assert stock.execution_ready is True and stock.execution_hold_reason == ""
    record = next(
        r for r in inventory.load_current_user_inventory_overlay()["records"]
        if r["canonical_name"] == "Tonka Bean Absolute"
    )
    assert record["supplier_product"]["supplier"] == "PerfumersWorld"
    assert record["authority_limits"]["sku_from_catalogue_match_not_user"] is True


def test_rows_left_out_of_the_rule_stay_held():
    # Birch Tar 1% and 10% (V5 row 46) are not in inventory.txt, which lists only PW's Birch Tar
    # Rectified 10% in DPG; they held until Kenny kept both older bottles on 2026-10-28 ("ye",
    # STK-230/231, w/w in DPG by his rule). Aldehyde C16 EMPG 10% left on 2026-10-28 ("hye",
    # v26 STK-194); once its identity was settled, Apritone 10% took the w/w rule (STK-226). Aldehyde
    # C11 10% was never a bottle (Kenny, 21 Oct: "Aldehyde C11 neat + 1%"); STK-036 retires the row.
    names = _by_name()
    for name in ("Birch Tar 1%", "Birch Tar 10%"):
        assert (names[name].fraction_basis, names[name].carrier) == ("mass_fraction", "dpg")
        assert names[name].execution_ready is True
    apritone = names["Apritone 10%"]
    assert (apritone.fraction_basis, apritone.carrier, apritone.execution_ready) == ("mass_fraction", "dpg", True)
    assert "Aldehyde C11 10%" not in names


def test_no_display_name_was_taken_twice():
    counts = {}
    for stock in _owned():
        counts[stock.name.casefold()] = counts.get(stock.name.casefold(), 0) + 1
    assert [name for name, count in counts.items() if count > 1] == []


def test_tuberlia_base_is_the_perfumersworld_tuberalia_base_as_supplied():
    (stock,) = [s for s in _owned() if s.identity_name == "Tuberlia Base"]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.execution_ready is True
    record = next(
        r for r in inventory.load_current_user_inventory_overlay()["records"]
        if r["canonical_name"] == "Tuberlia Base"
    )
    assert record["supplier_product"] == {
        "supplier": "PerfumersWorld", "product_name": "Tuberalia Base", "sku": "6ND09663",
    }
    assert record["aliases"] == ["Tuberalia Base"]


def test_cassis_base_345b_is_from_simple_scents_diy():
    record = next(
        r for r in inventory.load_current_user_inventory_overlay()["records"]
        if r["canonical_name"] == "Cassis Base 345B"
    )
    assert record["supplier_product"]["supplier"] == "Simple Scents DIY"
    assert record["authority_limits"]["supplier_asserted"] is True


@pytest.mark.parametrize("name", ["Leather FO", "Tuberose Base"])
def test_lines_kenny_says_are_not_stock_leave_the_design_list(name):
    from engine.personal_inventory import materialize_personal_inventory

    record = next(
        r for r in inventory.load_current_user_inventory_overlay()["records"]
        if r["canonical_name"] == name
    )
    assert record["state"] == "NOT_OWNED" and record["stock"] is None
    design = materialize_personal_inventory().stocks
    assert not any(s.name.casefold() == name.casefold() for s in design)


def test_tuberlia_line_and_the_record_are_one_design_entry():
    from engine.personal_inventory import materialize_personal_inventory

    names = [s.name for s in materialize_personal_inventory().stocks if "tuberlia" in s.name.casefold()
             or "tuberalia" in s.name.casefold()]
    assert names == ["Tuberlia Base"]
