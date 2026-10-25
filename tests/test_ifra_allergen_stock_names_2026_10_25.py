"""EU allergen and sensitiser checks see stock names (25 Oct 2026 ingredient audit).

The declaration check compared the row name with the allergen name letter for letter, so
14 owned allergen stocks such as "Geraniol (neat)" and "Coumarin 10%" were never declared.
The check now strips the stock suffix the way the IFRA check does, and maps three stock
names whose extra word is not a suffix.
"""

from __future__ import annotations

import pytest

from engine.ifra_safety import eu_allergen_rows, score_ifra_compliance

OWNED_ALLERGEN_STOCKS = {
    "Benzyl Alcohol 50% in DPG": "Benzyl Alcohol",
    "Coumarin (neat)": "Coumarin",
    "Coumarin Powder": "Coumarin",
    "Coumarin 10%": "Coumarin",
    "Cinnamaldehyde 1%": "Cinnamaldehyde",
    "Citral Natural": "Citral",
    "Citronellol (neat)": "Citronellol",
    "Ethyl Vanillin 10%": "Ethyl Vanillin",
    "Ethyl Vanillin (neat)": "Ethyl Vanillin",
    "Eugenol 10%": "Eugenol",
    "Geraniol 10%": "Geraniol",
    "Geraniol (neat)": "Geraniol",
    "Isoeugenol (neat)": "Isoeugenol",
    "Amyl Cinnamic Aldehyde (ACA)": "Amyl Cinnamal",
}


@pytest.mark.parametrize("stock, allergen", sorted(OWNED_ALLERGEN_STOCKS.items()))
def test_owned_allergen_stock_is_declared(stock: str, allergen: str) -> None:
    rows = eu_allergen_rows({stock: 0.5})
    assert [r["allergen"] for r in rows] == [allergen]


@pytest.mark.parametrize("stock, allergen", sorted(OWNED_ALLERGEN_STOCKS.items()))
def test_gate_declares_owned_allergen_stock(stock: str, allergen: str) -> None:
    report = score_ifra_compliance({stock: 1.0}, finished_pct_w_w={stock: 0.5})
    assert allergen in report.allergen_declarations


def test_same_allergen_under_two_stock_names_is_summed() -> None:
    # Each row alone is under the leave-on line; together they are over it.
    rows = eu_allergen_rows({"Coumarin 10%": 0.0006, "Coumarin (neat)": 0.0006})
    assert [r["allergen"] for r in rows] == ["Coumarin"]
    assert rows[0]["pct"] == pytest.approx(0.0012)


@pytest.mark.parametrize("name", ["Linalool Oxide", "Hedione", "Aldehyde C10", "Rose Otto 10%"])
def test_names_that_only_contain_an_allergen_word_are_not_declared(name: str) -> None:
    assert eu_allergen_rows({name: 0.5}) == []


@pytest.mark.parametrize(
    "stock",
    ["Geraniol (neat)", "Geraniol 10%", "Isoeugenol (neat)", "Eugenol 10%", "Cinnamaldehyde 1%"],
)
def test_sensitiser_flag_follows_the_stock_name(stock: str) -> None:
    report = score_ifra_compliance({stock: 1.0}, finished_pct_w_w={stock: 0.5})
    assert [f["material"] for f in report.sensitizer_flags] == [stock]
