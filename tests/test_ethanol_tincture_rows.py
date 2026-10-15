"""A formula row naming an ethanol tincture is a material, not the ethanol vehicle.

Kenny's Oman Frankincense Ethanol Tincture is dosable at built strength (15 Oct
2026), so the checks must see its row instead of skipping it as solvent.
"""

from pathlib import Path

import pytest

from engine.formula_metadata import _extract_material_names, is_ethanol_vehicle_name
from scripts.verify_formula_workflow import parse_formula_markdown

CARD = """# Tincture probe

**Reference claim:** none

| # | Material | Dilution | Amount (uL) | Drops |
|---|---|---|---|---|
| 1 | Oman Frankincense Ethanol Tincture | 33% w/w in ethanol | 200 | 0 |
| 2 | Turkish Storax Liquidambar Orientalis resin ethanol tincture | 20% | 30 | 0 |
| 3 | Iso E Super | neat | 300 | 0 |
| 4 | Ethanol 96% | - | 5500 | 0 |
"""


@pytest.mark.parametrize(
    ("name", "vehicle"),
    [
        ("Ethanol 96%", True),
        ("**Ethanol 96%**", True),
        ("Perfumer's ethanol ≥ 96 %", True),
        ("Ethanol 96% (bottle fill)", True),
        ("Oman Frankincense Ethanol Tincture", False),
        ("Oman Frankincense resin ethanol tincture", False),
        ("Vietnamese Benzoin Styrax Tonkinensis resin ethanol tincture", False),
        ("Iso E Super", False),
    ],
)
def test_only_the_ethanol_vehicle_is_a_solvent_row(name: str, vehicle: bool) -> None:
    assert is_ethanol_vehicle_name(name) is vehicle


def test_the_gate_parser_keeps_tincture_rows_and_drops_the_vehicle(tmp_path: Path) -> None:
    card = tmp_path / "card.md"
    card.write_text(CARD, encoding="utf-8")

    (formula,) = parse_formula_markdown(card)

    assert formula["ingredients_ul"] == {
        "Oman Frankincense Ethanol Tincture": 200.0,
        "Turkish Storax Liquidambar Orientalis resin ethanol tincture": 30.0,
        "Iso E Super": 300.0,
    }
    assert formula["stock_specs"]["Oman Frankincense Ethanol Tincture"]["fraction"] == pytest.approx(0.33)


def test_the_preflight_name_list_keeps_tincture_rows(tmp_path: Path) -> None:
    card = tmp_path / "card.md"
    card.write_text(CARD, encoding="utf-8")

    names = _extract_material_names(str(card))

    assert "Oman Frankincense Ethanol Tincture" in names
    assert "Turkish Storax Liquidambar Orientalis resin ethanol tincture" in names
    assert not any(is_ethanol_vehicle_name(name) for name in names)
