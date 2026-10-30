"""Kenny's three ylang oils (30 Oct 2026: "I have 3 ylangs EO in my inventory")."""

from __future__ import annotations

import pytest

from engine.ifra_safety import get_ifra_limit
from engine.inventory_parser import parse_current_inventory
from engine.pipeline import natural_absolute_decomposition as nad

COMPLETE = "Ylang Comoros Complete EO F3255"
III = "Ylang Comoros III EO F3295"
MADAGASCAR = "Ylang Madagascar Complete Organic EO"
EFSA = "ylang ylang oil comoros efsa 2022 five-batch profile"
GRADE_III = "ylang ylang oil grade iii benveniste azzo 1992 profile"


def _stocks() -> dict[str, object]:
    return {
        stock.name: stock
        for stock in parse_current_inventory()
        if "ylang" in stock.name.casefold()
    }


def test_three_ylang_oils_are_owned_neat_and_ready() -> None:
    stocks = _stocks()
    assert set(stocks) == {COMPLETE, III, MADAGASCAR}
    for stock in stocks.values():
        assert stock.status == "owned"
        assert stock.dilution == 1.0
        assert stock.fraction_basis == "neat"
        assert stock.execution_ready is True
    # V5 row 251 "Ylang-Ylang EO" (HAVE - COMOROS COMPLETE + III) now resolves to Complete.
    assert stocks[COMPLETE].source_rows == (251,)


@pytest.mark.parametrize(
    ("name", "key"),
    [(COMPLETE, EFSA), (MADAGASCAR, EFSA), (III, GRADE_III), ("Ylang III", GRADE_III)],
)
def test_each_grade_takes_its_sourced_profile(name: str, key: str) -> None:
    metadata = nad.get_composite_metadata(name)
    assert metadata is not None
    assert metadata.profile_key == key
    assert metadata.resolution == "literature_proxy"


def test_complete_profile_is_the_efsa_five_batch_mean() -> None:
    rows = {row[0]: row[1] for row in nad._ABSOLUTE_CONSTITUENTS[EFSA]}
    assert (rows["germacrene d"], rows["alpha farnesene"], rows["benzyl acetate"]) == (
        0.175,
        0.134,
        0.064,
    )
    assert round(sum(rows.values()), 4) == 0.6989
    unresolved = nad._PARTIAL_PROFILE_EVIDENCE[EFSA]["unresolved_constituents"]
    assert round(sum(row["reported_fraction"] for row in unresolved), 4) == 0.2554
    assert nad._PROFILE_SOURCES[EFSA][0] == "https://doi.org/10.2903/j.efsa.2022.7159"


def test_grade_iii_is_sesquiterpene_rich_with_little_ester() -> None:
    rows = {row[0]: row[1] for row in nad._ABSOLUTE_CONSTITUENTS[GRADE_III]}
    assert rows["alpha farnesene"] == 0.2375
    assert rows["benzyl acetate"] < 0.01
    assert rows["methyl benzoate"] < 0.01
    assert round(sum(rows.values()), 4) == 0.6997
    assert nad._PROFILE_SOURCES[GRADE_III][0] == (
        "https://www.thegoodscentscompany.com/gca/gc1001792.html"
    )


def test_madagascar_is_labelled_as_a_comoros_proxy() -> None:
    metadata = nad.get_composite_metadata(MADAGASCAR)
    assert any("closest-identity proxy" in text for text in metadata.limitations)
    complete = nad.get_composite_metadata(COMPLETE)
    assert not any("closest-identity proxy" in text for text in complete.limitations)


@pytest.mark.parametrize("name", [COMPLETE, III, MADAGASCAR])
def test_ifra_standard_84_applies_to_every_ylang(name: str) -> None:
    assert get_ifra_limit(name) == pytest.approx(0.73)
