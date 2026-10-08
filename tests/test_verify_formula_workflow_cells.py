"""Strength and amount cells in formula rows: ratios, unreadable cells, units, edits."""

import pytest

from scripts.verify_formula_workflow import _parse_formula_rows, parse_formula_markdown


def _one_row(strength: str, amount: str = "100", unit: str = "µL"):
    body = f"""# Cell Formula

## Formula

| Ingredient | Dilution | Amount ({unit}) |
|---|---|---:|
| Rose Oxide | {strength} | {amount} |
| Hedione | neat | 200 |
"""
    blockers: list = []
    ingredients, dilutions, specs = _parse_formula_rows(body, blockers)
    return ingredients, dilutions, specs, blockers


@pytest.mark.parametrize(
    ("ratio_cell", "percent_cell"),
    [
        ("1:10 in DPG", "10% in DPG"),
        ("1/10 in DPG", "10% in DPG"),
        ("1:10 w/w in DPG", "10% w/w in DPG"),
        ("1 / 10 w/w in DPG", "10% w/w in DPG"),
    ],
)
def test_ratio_strength_matches_equivalent_percent_cell(ratio_cell, percent_cell):
    ingredients, dilutions, specs, blockers = _one_row(ratio_cell)
    _, _, percent_specs, _ = _one_row(percent_cell)

    assert blockers == []
    assert ingredients["Rose Oxide"] == 100.0
    assert dilutions["Rose Oxide"] == pytest.approx(0.1)
    assert specs["Rose Oxide"]["fraction"] == pytest.approx(0.1)
    for key in ("declared", "fraction_basis", "carrier"):
        assert specs["Rose Oxide"][key] == percent_specs["Rose Oxide"][key]
    assert specs["Rose Oxide"]["declared"] is True


@pytest.mark.parametrize("cell", ["0.1 in DPG", "banana"])
def test_unreadable_strength_is_none_held_out_and_blocking(cell):
    ingredients, dilutions, specs, blockers = _one_row(cell)

    assert dilutions["Rose Oxide"] is None
    assert specs["Rose Oxide"]["fraction"] is None
    assert specs["Rose Oxide"]["declared"] is False
    # Held out of every physics input: no row, so no 1.0 strength can reach OAV/IFRA.
    assert "Rose Oxide" not in ingredients
    assert ingredients == {"Hedione": 200.0}
    assert len(blockers) == 1
    message = blockers[0]["message"]
    assert f"'{cell}'" in message and "Rose Oxide" in message


@pytest.mark.parametrize(
    ("cell", "fraction", "declared"),
    [("", 1.0, False), ("neat", 1.0, True), ("100%", 1.0, True)],
)
def test_blank_neat_and_100_percent_strength_unchanged(cell, fraction, declared):
    ingredients, dilutions, specs, blockers = _one_row(cell)

    assert blockers == []
    assert ingredients["Rose Oxide"] == 100.0
    assert dilutions["Rose Oxide"] == fraction
    assert specs["Rose Oxide"]["fraction"] == fraction
    assert specs["Rose Oxide"]["declared"] is declared


def test_unreadable_strength_reaches_formula_record_and_release_block(tmp_path):
    from engine.pipeline.preflight import resolve_inventory_stock_contract
    from scripts.verify_formula_workflow import (
        build_verification_bundle,
        formula_row_parse_blocker_messages,
    )

    path = tmp_path / "f.md"
    path.write_text(
        "# F\n\n## Formula\n\n| Ingredient | Dilution | Amount (µL) |\n|---|---|---:|\n"
        "| Rose Oxide | 0.1 in DPG | 100 |\n| Hedione | neat | 200 |\n",
        encoding="utf-8",
    )
    formula = parse_formula_markdown(path)[0]
    messages = formula_row_parse_blocker_messages(formula)
    assert messages and "'0.1 in DPG'" in messages[0]
    with pytest.raises(ValueError, match="0.1 in DPG"):
        build_verification_bundle(formula)
    contract = resolve_inventory_stock_contract(formula)
    assert contract.status == "FAIL"
    assert any(
        issue["reason"] == "formula_row_unreadable" for issue in contract.data["issues"]
    )


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("0.5 mL", 500.0), ("20 µL", 20.0), ("1,500", 1500.0), ("60 (was 50)", 60.0)],
)
def test_amount_cells_read_units_thousands_and_notes(amount, expected):
    ingredients, _, _, blockers = _one_row("10% in DPG", amount)

    assert blockers == []
    assert ingredients["Rose Oxide"] == expected


def test_amount_in_ml_column_converts_written_microlitres():
    ingredients, _, _, blockers = _one_row("10% in DPG", "500 µL", unit="mL")

    assert blockers == []
    assert ingredients["Rose Oxide"] == 500.0


@pytest.mark.parametrize("amount", ["1,5", "50 → 60", "50->60", "50 / 60", "0.2 g"])
def test_refused_amount_holds_row_out_with_message(amount):
    ingredients, _, _, blockers = _one_row("10% in DPG", amount)

    assert "Rose Oxide" not in ingredients
    assert ingredients == {"Hedione": 200.0}
    assert len(blockers) == 1
    assert blockers[0]["field"] == "amount"
    assert f"'{amount}'" in blockers[0]["message"]
    assert "Rose Oxide" in blockers[0]["message"]
