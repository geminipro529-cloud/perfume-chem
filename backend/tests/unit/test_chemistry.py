"""Test chemistry calculations"""

import pytest

from app.domain.ingredients.chemistry import (
    DilutionCalculationError,
    FormulaBalanceError,
    calculate_dilution,
    calculate_drops_to_ml,
    calculate_ml_to_drops,
    calculate_note_distribution,
    estimate_longevity,
    estimate_sillage,
    validate_formula_balance,
)


def test_calculate_dilution():
    """Test dilution calculation"""
    result = calculate_dilution(
        concentrate_volume=10.0,
        concentrate_percent=100.0,
        target_percent=10.0
    )

    assert result["total_volume"] == 100.0
    assert result["solvent_to_add"] == 90.0
    assert result["final_concentration"] == 10.0


def test_calculate_dilution_invalid():
    """Test dilution with invalid parameters"""
    with pytest.raises(DilutionCalculationError):
        calculate_dilution(
            concentrate_volume=10.0,
            concentrate_percent=10.0,
            target_percent=50.0  # Higher than concentrate
        )


def test_drops_to_ml():
    """Test drops to ml conversion"""
    ml = calculate_drops_to_ml(drops=20, drop_size=0.05)
    assert ml == pytest.approx(1.0)


def test_ml_to_drops():
    """Test ml to drops conversion"""
    drops = calculate_ml_to_drops(volume_ml=1.0, drop_size=0.05)
    assert drops == 20


def test_validate_formula_balance_valid():
    """Test formula balance validation with valid formula"""
    ingredients = [
        {"percentage": 50.0},
        {"percentage": 30.0},
        {"percentage": 20.0}
    ]
    assert validate_formula_balance(ingredients) is True


def test_validate_formula_balance_invalid():
    """Test formula balance validation with invalid formula"""
    ingredients = [
        {"percentage": 50.0},
        {"percentage": 30.0}
    ]
    with pytest.raises(FormulaBalanceError):
        validate_formula_balance(ingredients)


def test_calculate_note_distribution():
    """Test note distribution calculation"""
    ingredients = [
        {"name": "Lemon", "volatility": "top", "percentage": 20.0},
        {"name": "Rose", "volatility": "heart", "percentage": 30.0},
        {"name": "Sandalwood", "volatility": "base", "percentage": 50.0}
    ]

    distribution = calculate_note_distribution(ingredients)

    assert distribution["top"] == 20.0
    assert distribution["heart"] == 30.0
    assert distribution["base"] == 50.0


def test_estimate_longevity():
    """Test longevity estimation"""
    note_dist = {"top": 20.0, "heart": 30.0, "base": 50.0}
    longevity = estimate_longevity(note_dist)

    assert 1.0 <= longevity <= 24.0
    assert longevity > 6.0  # Should be long-lasting with high base notes


def test_estimate_sillage():
    """Test sillage estimation"""
    sillage = estimate_sillage(top_percent=30.0, concentration=15.0)

    assert sillage in ["intimate", "moderate", "strong", "enormous"]
