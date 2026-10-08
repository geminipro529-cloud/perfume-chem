"""Strength and amount cells in formula rows: ratios, unreadable cells, units, edits."""

import pytest

from scripts.verify_formula_workflow import _parse_formula_rows, parse_formula_markdown


def _one_row(
    strength: str, amount: str = "100", unit: str = "µL", header: str = "Dilution"
):
    body = f"""# Cell Formula

## Formula

| Ingredient | {header} | Amount ({unit}) |
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


@pytest.mark.parametrize(
    "cell", ["banana", "oil Sicilian", "premade accord", "powder", "15g/10mL in EtOH"]
)
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
        "| Rose Oxide | banana | 100 |\n| Hedione | neat | 200 |\n",
        encoding="utf-8",
    )
    formula = parse_formula_markdown(path)[0]
    messages = formula_row_parse_blocker_messages(formula)
    assert messages and "'banana'" in messages[0]
    with pytest.raises(ValueError, match="banana"):
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


@pytest.mark.parametrize(
    "cell",
    [
        "neat (w/w)",
        "neat/as supplied; product basis",
        "neat EO",
        "neat carrier",
        "Neat, ownership to reconfirm",
        "as supplied",
        "As supplied; strength/species/part unrecorded",
        "NEAT",
    ],
)
def test_neat_and_as_supplied_variants_read_exactly_like_neat(cell):
    assert _one_row(cell) == _one_row("neat")


def _agree(cell, header):
    ingredients, dilutions, specs, blockers = _one_row(cell, header=header)
    if blockers:
        return None, specs, blockers
    assert dilutions["Rose Oxide"] == specs["Rose Oxide"]["fraction"]
    return dilutions["Rose Oxide"], specs["Rose Oxide"], blockers


@pytest.mark.parametrize(
    ("cell", "fraction"),
    [("1.0", 1.0), ("0.20", 0.2), ("0.01", 0.01), ("0.1 in DPG", 0.1), ("1", 1.0)],
)
def test_bare_fraction_in_dilution_column(cell, fraction):
    value, spec, blockers = _agree(cell, "Dilution")
    assert blockers == []
    assert value == pytest.approx(fraction)


def test_bare_number_basis_follows_equivalent_percent_cell():
    _, spec, _ = _agree("0.1 w/w in DPG", "Dilution")
    _, expected, _ = _agree("10% w/w in DPG", "Dilution")
    for key in ("fraction", "declared", "fraction_basis", "carrier"):
        assert spec[key] == pytest.approx(expected[key])
    assert spec["declared"] is True
    _, bare, _ = _agree("0.20", "Dilution")
    assert bare["declared"] is False


@pytest.mark.parametrize("cell", ["10", "1.5", "50 in DPG", "0"])
def test_bare_number_above_one_is_refused_with_percent_hint(cell):
    ingredients, dilutions, specs, blockers = _one_row(cell, header="Dilution")
    assert dilutions["Rose Oxide"] is None
    assert specs["Rose Oxide"]["fraction"] is None
    assert "Rose Oxide" not in ingredients
    assert len(blockers) == 1
    if cell != "0":
        assert "10% w/w in DPG" in blockers[0]["message"]


@pytest.mark.parametrize(
    ("cell", "fraction"), [("10", 0.1), ("0.5", 0.005), ("100", 1.0), ("10 in DPG", 0.1)]
)
def test_bare_number_in_percent_column_is_percent(cell, fraction):
    for header in ("Dilution %", "Dilution (%)"):
        value, _, blockers = _agree(cell, header)
        assert blockers == []
        assert value == pytest.approx(fraction)


def test_bare_number_above_100_in_percent_column_is_refused():
    _, dilutions, specs, blockers = _one_row("150", header="Dilution %")
    assert dilutions["Rose Oxide"] is None and len(blockers) == 1


# --- Shared with backend/tests/unit/test_formula_import.py: keep both identical.
# Each strength cell reads as the given fraction, or None when it is refused.
SHARED_STRENGTH_CASES = [
    ("neat (solid; pre-dil. 10% in DPG)", None),
    ("neat 10% in DPG", None),
    ("as supplied 1:10", None),
    ("1/10/2024", None),
    ("1:10,5", None),
    ("1:10 (5%)", None),
    ("1:10 (10%)", "0.1"),
    ("1:10 in DPG", "0.1"),
    ("neat (w/w)", "1"),
]
# Each amount cell in a uL column reads as the given number, or None when refused.
SHARED_AMOUNT_CASES = [
    ("50 60", None),
    ("1,5", None),
    ("1,500", "1500"),
    ("60 (was 50)", "60"),
]


@pytest.mark.parametrize(("cell", "expected"), SHARED_STRENGTH_CASES)
def test_shared_strength_cases(cell, expected):
    ingredients, dilutions, specs, blockers = _one_row(cell)
    if expected is None:
        assert dilutions["Rose Oxide"] is None
        assert "Rose Oxide" not in ingredients
        assert len(blockers) == 1 and blockers[0]["field"] == "strength"
        assert f"'{cell}'" in blockers[0]["message"]
    else:
        assert blockers == []
        assert dilutions["Rose Oxide"] == pytest.approx(float(expected))


@pytest.mark.parametrize(("amount", "expected"), SHARED_AMOUNT_CASES)
def test_shared_amount_cases(amount, expected):
    ingredients, _, _, blockers = _one_row("10% in DPG", amount)
    if expected is None:
        assert "Rose Oxide" not in ingredients
        assert len(blockers) == 1 and blockers[0]["field"] == "amount"
        assert f"'{amount}'" in blockers[0]["message"]
    else:
        assert blockers == []
        assert ingredients["Rose Oxide"] == float(expected)


def _rows(header: str, rows: list[str]):
    lines = ["# Header Formula", "", "Total concentrate (µL): 1000", "", "## Formula", ""]
    lines += [header, "|" + "---|" * (header.count("|") - 1)] + rows
    blockers: list = []
    _, dilutions, _ = _parse_formula_rows("\n".join(lines) + "\n", blockers)
    return dilutions, blockers


def test_formula_percent_column_does_not_hide_dilution_column():
    dilutions, blockers = _rows(
        "| Material | Formula % | Dilution |",
        ["| Rose Oxide | 10 | 10% in DPG |", "| Hedione | 20 | 1:10 in DPG |"],
    )
    assert blockers == []
    assert dilutions == {"Rose Oxide": pytest.approx(0.1), "Hedione": pytest.approx(0.1)}


def test_stock_amount_column_does_not_hide_dilution_column():
    dilutions, blockers = _rows(
        "| Material | Amount (uL stock) | Dilution |",
        ["| Rose Oxide | 100 | 10% in DPG |", "| Hedione | 200 | 1:10 in DPG |"],
    )
    assert blockers == []
    assert dilutions == {"Rose Oxide": pytest.approx(0.1), "Hedione": pytest.approx(0.1)}


def test_dilution_column_wins_over_earlier_stock_column():
    dilutions, blockers = _rows(
        "| Material | Stock | Dilution | Amount (uL) |",
        ["| Rose Oxide | DEP lot 3 | 10% in DPG | 100 |"],
    )
    assert blockers == []
    assert dilutions == {"Rose Oxide": pytest.approx(0.1)}
