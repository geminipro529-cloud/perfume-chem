from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.verify_formula_workflow import (
    _formula_bound_mixing_protocol,
    parse_formula_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "formulas" / "CYP-02_Cypress_Magnolia_Orris_30mL_Parfum.md"


def test_cyp02_is_a_full_exact_current_inventory_formula() -> None:
    formulas = parse_formula_markdown(FORMULA)

    assert len(formulas) == 1
    formula = formulas[0]
    ingredients = formula["ingredients_ul"]
    dilutions = formula["dilutions"]

    assert len(ingredients) == 32
    assert sum(ingredients.values()) == pytest.approx(6000.0)
    assert all(raw_ul >= 10.0 for raw_ul in ingredients.values())

    assert ingredients["Cypress EO"] == 650.0
    assert ingredients["Magnolia EO"] == 150.0
    assert ingredients["Orris Liquid"] == 120.0
    assert dilutions["Orris Liquid"] == pytest.approx(0.30)
    assert ingredients["Alpha Irone"] == 50.0
    assert dilutions["Alpha Irone"] == pytest.approx(0.10)
    assert ingredients["Ambrettolide"] == 320.0
    assert dilutions["Ambrettolide"] == pytest.approx(0.10)


def test_cyp02_keeps_cypress_as_subject_and_uses_one_precise_musk() -> None:
    text = FORMULA.read_text(encoding="utf-8")
    formula = parse_formula_markdown(FORMULA)[0]
    ingredients = formula["ingredients_ul"]

    assert "Cypress is the sole named and continuous subject" in text
    assert "ingredient count earns no complexity credit" in text
    assert "Magnolia petal-light" in text
    assert "Orris rhizome-shadow" in text

    musk_names = {
        "Ambrettolide",
        "Romandolide",
        "Habanolide",
        "Ethylene Brassylate",
        "Exaltolide",
        "Zenolide",
        "Tonalide",
        "Macrolide",
        "Musk Ketone",
    }
    assert musk_names.intersection(ingredients) == {"Ambrettolide"}


def test_cyp02_excludes_held_and_target_redefining_materials() -> None:
    ingredients = parse_formula_markdown(FORMULA)[0]["ingredients_ul"]
    excluded = {
        "Benzyl Salicylate",
        "Bacdanol",
        "Guaiacwood EO",
        "Ambrofix",
        "Liffarome",
        "Cis-3-Hexenyl Salicylate",
        "Caryophyllene Acetate",
        "Cedarwood oil Virginia",
    }
    assert excluded.isdisjoint(ingredients)


def test_cyp02_preserves_target_current_separation_and_authority_ceiling() -> None:
    text = FORMULA.read_text(encoding="utf-8")

    assert "## 3. TARGET / IDEAL FORMULA" in text
    assert "## 4. CURRENT-INVENTORY BUILD — parser-visible formula" in text
    assert "Physical state:** `NOT COMPOUNDED`" in text
    assert "Sensory / liking / depth / performance / stability:** `NOT TESTED`" in text
    assert "Safety / IFRA / skin-use / release:** `HOLD`" in text
    assert "observed hedonism: false" in text
    assert "compounding authority: false" in text


def test_cyp02_uses_the_user_basket_sequence_and_descending_raw_doses() -> None:
    text = FORMULA.read_text(encoding="utf-8")
    current = text.split(
        "## 4. CURRENT-INVENTORY BUILD — parser-visible formula", 1
    )[1].split("## 5. Missing-chemical impact gate", 1)[0]

    headings = re.findall(r"^\*\*BASKET (\d+) —", current, flags=re.MULTILINE)
    assert headings == [str(number) for number in range(1, 18)]

    for basket in range(1, 18):
        start = current.index(f"**BASKET {basket} —")
        if basket < 17:
            end = current.index(f"**BASKET {basket + 1} —", start)
        else:
            end = current.index("**CARRIER / TECHNICAL", start)
        section = current[start:end]
        raw_values = [
            float(value.replace(",", ""))
            for value in re.findall(
                r"^\|\s*\d+\s*\|[^\n]*?\|\s*([\d,]+(?:\.\d+)?)\s*\|",
                section,
                flags=re.MULTILINE,
            )
        ]
        assert raw_values == sorted(raw_values, reverse=True)


def test_cyp02_binds_verification_output_to_the_declared_basket_protocol() -> None:
    formula = parse_formula_markdown(FORMULA)[0]
    protocol = _formula_bound_mixing_protocol(
        formula["body"],
        formula_name=formula["name"],
        total_materials=len(formula["ingredients_ul"]),
        total_pct=sum(formula["ingredients_pct"].values()),
    )

    assert protocol is not None
    rendered = protocol["full_text"]
    assert "Use a fresh tip whenever moving to a new material" in rendered
    assert "1. **Always used:** Iso E Super 900; Hedione 880." in rendered
    assert "17. **Green smelling things:** Parmavert 80" in rendered
    assert "PHASE 1: PRE-BONDING" not in rendered
    assert "Add Orris Liquid (2.0%)" not in rendered
