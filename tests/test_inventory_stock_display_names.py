"""One stock name means one bottle, and its stated strength is the stored one."""

from __future__ import annotations

import re
from collections import Counter

from engine.inventory_parser import materialize_current_inventory
from engine.personal_inventory import materialize_personal_inventory
from engine.research.composition_planner import _load_candidates

_PERCENT = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%")
_TWO_STRENGTH_BIRCH_LABEL = "Birch Tar 1% and Birch Tar 10%"


def _owned_stocks():
    return [
        stock
        for stock in materialize_current_inventory().stocks
        if stock.status.casefold() == "owned"
    ]


def test_no_two_owned_stocks_share_a_display_name() -> None:
    counts = Counter(stock.name.casefold() for stock in _owned_stocks())
    assert [name for name, count in counts.items() if count > 1] == []
    # The Stock page and the composer read the personal projection, which adds
    # inventory.txt lines and personal additions to the governed stocks.
    personal = Counter(
        stock.name.casefold()
        for stock in materialize_personal_inventory().stocks
        if stock.status.casefold() == "owned"
    )
    assert [name for name, count in personal.items() if count > 1] == []


def test_stock_label_check_reads_the_label_as_written() -> None:
    by_id = {stock.stock_id: stock for stock in materialize_personal_inventory().stocks}
    # V5 names "Allyl Ionone 10%" a neat bottle and inventory.txt has no
    # Allyl Ionone line, so the governed stock stays out of the projection.
    assert "inventory:v5:629b084e9d9542accfb7" not in by_id
    # V5 names "Isoeugenol 10%" a neat bottle, but inventory.txt lists
    # Isoeugenol (neat), which confirms the stored strength.
    isoeugenol = by_id["inventory:v5:1395228f45438ea9fe58"]
    assert (isoeugenol.name, isoeugenol.dilution) == ("Isoeugenol (neat)", 1.0)
    assert isoeugenol.execution_ready is True


def test_every_percentage_in_a_stock_name_equals_its_stored_dilution() -> None:
    mismatches = [
        (stock.name, stock.dilution, stock.stock_id)
        for stock in _owned_stocks()
        for value in _PERCENT.findall(stock.name)
        if abs(float(value.replace(",", ".")) / 100.0 - stock.dilution) > 1e-9
    ]
    assert mismatches == []


def test_neat_bottle_no_longer_carries_the_ten_percent_name() -> None:
    by_name = {stock.name: stock for stock in _owned_stocks()}
    assert by_name["Geraniol 10%"].dilution == 0.1
    assert by_name["Geraniol (neat)"].dilution == 1.0
    assert by_name["Isoeugenol (neat)"].dilution == 1.0
    assert "Isoeugenol 10%" not in by_name
    assert by_name["Birch Tar 10%"].dilution == 0.1
    assert by_name["Birch Tar 1%"].dilution == 0.01
    assert by_name["Beta Ionone 0.1%"].dilution == 0.001


def test_ethyl_maltol_one_and_ten_percent_are_separate_stocks() -> None:
    by_name = {stock.name: stock for stock in _owned_stocks()}
    one, ten = by_name["Ethyl Maltol 1%"], by_name["Ethyl Maltol 10%"]
    assert (one.dilution, ten.dilution) == (0.01, 0.1)
    assert one.stock_id != ten.stock_id
    assert "Ethyl Maltol 1% + 10%" not in by_name
    # The 10% bottle's basis and carrier are still unconfirmed.
    assert ten.execution_ready is False


def test_composer_refuses_a_stock_whose_label_names_two_strengths() -> None:
    personal = materialize_personal_inventory()
    assert any(
        stock.raw_name.startswith(_TWO_STRENGTH_BIRCH_LABEL) for stock in personal.stocks
    ), "fixture drift: the two-strength Birch Tar row is no longer in the inventory"

    candidates, _inventory, _known = _load_candidates(("Birch Tar",))

    assert not any(
        candidate.stock.raw_name.startswith(_TWO_STRENGTH_BIRCH_LABEL)
        for candidate in candidates
    )
    birch = [
        candidate.stock
        for candidate in candidates
        if "birch tar" in (candidate.stock.identity_name or candidate.stock.name).casefold()
    ]
    assert birch and {stock.dilution for stock in birch} == {0.1}


def test_composer_keeps_two_strength_bottles_inventory_txt_confirms() -> None:
    # inventory.txt lists Cashmeran neat and Cashmeran 20%, so the V5 row
    # "Cashmeran neat and Cashmeran 20% in DPG" names two real bottles.
    candidates, _inventory, _known = _load_candidates(("Cashmeran",))
    strengths = {
        candidate.stock.dilution
        for candidate in candidates
        if (candidate.stock.identity_name or candidate.stock.name)
        .casefold()
        .startswith("cashmeran")
    }
    assert strengths and strengths <= {1.0, 0.2}
