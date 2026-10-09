"""Bench cards weighed in grams or mg are read, held or failed, never crashed.

GATE-01: a card whose amounts were "Add for 10 g trial, g" or "Weigh stock g"
gave no rows, and the release gate stopped with a Python traceback.
"""

import json
from pathlib import Path

import pytest

import scripts.verify_formula_workflow as workflow
from engine.ifra_standards import CARRIER_DENSITY_G_ML, ETHANOL_DENSITY_G_ML
from scripts import formula_release_gate
from scripts.verify_formula_workflow import parse_formula_markdown

DENSITIES = {"Hedione": 0.9, "Coumarin": 1.2}


@pytest.fixture(autouse=True)
def _known_densities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(workflow, "_registry_density_g_ml", DENSITIES.get, raising=False)


def _card(tmp_path: Path, table: str, name: str = "bench_card.md") -> Path:
    path = tmp_path / name
    path.write_text("# Bench card\n\n" + table, encoding="utf-8")
    return path


def test_gram_table_converts_each_stock_by_its_density(tmp_path: Path) -> None:
    path = _card(
        tmp_path,
        "| # | Named product | Stock to weigh | Add for 10 g trial, g |\n"
        "|---|---|---|---:|\n"
        "| 1 | Hedione | Undiluted | 0.900 |\n"
        "| 2 | Coumarin | 10% w/w in DPG | 1.000 |\n"
        "| | **Working-stock blend** | | **1.900** |\n",
    )
    [formula] = parse_formula_markdown(path)

    assert formula["row_parse_blockers"] == []
    assert formula["ingredients_ul"]["Hedione"] == pytest.approx(1000.0)
    expected = (0.1 / 1.2 + 0.9 / CARRIER_DENSITY_G_ML["dpg"]) * 1000.0
    assert formula["ingredients_ul"]["Coumarin"] == pytest.approx(expected)
    assert formula["dilutions"]["Coumarin"] == pytest.approx(0.1)
    card = formula["mass_card"]
    assert card["stock_mass_g"] == pytest.approx(1.9)
    assert card["stated_batch_mass_g"] == pytest.approx(10.0)
    # The stated 10 g batch is the stocks plus the rest as ethanol.
    volume, source = formula_release_gate.mass_card_batch_volume(formula)
    assert source == "mass_card_stated_batch"
    assert volume == pytest.approx((1000.0 + expected) / 1000.0 + 8.1 / ETHANOL_DENSITY_G_ML)


def test_mg_table_reads_milligrams(tmp_path: Path) -> None:
    path = _card(
        tmp_path,
        "| Ingredient | Dilution | mg |\n|---|---|---:|\n| Hedione | neat | 450 |\n",
    )
    [formula] = parse_formula_markdown(path)

    assert formula["ingredients_ul"] == {"Hedione": pytest.approx(500.0)}
    assert formula["mass_card"]["amount_unit"] == "mg"
    # No batch stated: the card is read as the whole product.
    assert formula_release_gate.mass_card_batch_volume(formula) == (
        pytest.approx(0.5),
        "mass_card_concentrate_only",
    )


def test_unknown_density_is_a_named_hold_not_a_crash(tmp_path: Path) -> None:
    path = _card(
        tmp_path,
        "| Material | Required stock | Weigh stock g |\n|---|---|---:|\n"
        "| Hedione | Neat | 0.900 |\n| Mystery Oil | Neat | 0.100 |\n",
    )
    [formula] = parse_formula_markdown(path)

    [blocker] = formula["row_parse_blockers"]
    assert blocker["material"] == "Mystery Oil"
    assert blocker["field"] == "density"
    assert blocker["reason"] == "no density on record for the material"
    assert "Mystery Oil" not in formula["ingredients_ul"]
    assert formula_release_gate.mass_card_batch_volume(formula) is None


def test_card_with_no_amount_column_fails_naming_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _card(
        tmp_path,
        "| Material | Stock | Drops |\n|---|---|---:|\n| Hedione | Neat | 4 |\n",
        name="drops_card.md",
    )
    code = formula_release_gate.main(
        [
            "--formula-file", str(path),
            "--expected-concentrate-ul", "1000",
            "--json", "--no-append-analysis", "--no-audit",
        ]
    )

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"] == "FAIL"
    [gate] = payload["formulas"][0]["gates"]
    assert gate["status"] == "FAIL"
    assert str(path) in gate["message"]
    assert "'Drops'" in gate["message"]


def test_volume_table_ignores_a_gram_preparation_table(tmp_path: Path) -> None:
    path = _card(
        tmp_path,
        "| # | Ingredient | Dilution | uL |\n|---|---|---|---|\n"
        "| 1 | Hedione | neat | 300 |\n\n"
        "| Material | Source product g | DPG g |\n|---|---:|---:|\n"
        "| Coumarin | 1.000 | 9.000 |\n",
    )
    [formula] = parse_formula_markdown(path)

    assert formula["ingredients_ul"] == {"Hedione": 300.0}
    assert "mass_card" not in formula
