"""Tests for the LegacyFormulaAdapter."""

import pytest

from app.adapters.legacy_formula import LegacyFormulaAdapter


class TestToLabComponents:
    """Tests for LegacyFormulaAdapter.to_lab_components."""

    def test_basic_conversion(self):
        """Convert simple ingredient list, verify component dict structure."""
        ingredients = [
            {"name": "Linalool", "percentage": 30.0, "role": "heart"},
            {"name": "Bergamot", "percentage": 70.0, "role": "top"},
        ]
        result = LegacyFormulaAdapter.to_lab_components(ingredients)
        assert len(result) == 2
        assert result[0]["material_name"] == "Linalool"
        assert result[0]["active_fraction"] == 1.0
        assert result[0]["role"] == "heart"
        assert result[0]["position"] == 1
        assert result[1]["material_name"] == "Bergamot"
        assert result[1]["position"] == 2

    def test_with_grams(self):
        """Grams field is preserved as mass_g."""
        ingredients = [
            {"name": "Hedione", "percentage": 60.0, "grams": 0.6, "role": "heart"},
        ]
        result = LegacyFormulaAdapter.to_lab_components(ingredients)
        assert result[0]["mass_g"] == 0.6

    def test_with_active_fraction(self):
        """Stock active fraction is preserved."""
        ingredients = [
            {"name": "Coumarin", "percentage": 5.0, "stock_active_fraction": 0.2, "role": "base"},
        ]
        result = LegacyFormulaAdapter.to_lab_components(ingredients)
        assert result[0]["active_fraction"] == 0.2

    def test_empty_raises(self):
        """Empty list raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            LegacyFormulaAdapter.to_lab_components([])

    def test_missing_name_raises(self):
        """Ingredient without name raises ValueError."""
        with pytest.raises(ValueError, match="must have a non-empty name"):
            LegacyFormulaAdapter.to_lab_components([{"percentage": 100.0}])

    def test_duplicate_names_combined(self):
        """Duplicate material names are combined."""
        ingredients = [
            {"name": "Linalool", "percentage": 30.0, "role": "heart"},
            {"name": "Linalool", "percentage": 20.0, "role": "heart"},
        ]
        result = LegacyFormulaAdapter.to_lab_components(ingredients)
        assert len(result) == 1
        assert result[0]["mass_g"] is None
        assert result[0]["percentage"] == 50.0


class TestFromLabComponents:
    """Tests for LegacyFormulaAdapter.from_lab_components."""

    def test_basic_reconstruction(self):
        """Reconstruct legacy format from lab components."""
        components = [
            {"material_name": "Linalool", "mass_g": 0.3, "role": "heart"},
            {"material_name": "Bergamot", "mass_g": 0.7, "role": "top"},
        ]
        result = LegacyFormulaAdapter.from_lab_components(components)
        assert len(result) == 2
        assert result[0]["name"] == "Linalool"
        assert result[0]["percentage"] == pytest.approx(30.0, abs=0.01)
        assert result[0]["role"] == "heart"

    def test_empty_raises(self):
        """Empty component list raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            LegacyFormulaAdapter.from_lab_components([])

    def test_percentage_only_components_do_not_require_fabricated_grams(self):
        components = [
            {"material_name": "Linalool", "mass_g": None, "percentage": 30.0},
            {"material_name": "Bergamot", "mass_g": None, "percentage": 70.0},
        ]

        result = LegacyFormulaAdapter.from_lab_components(components)

        assert [row["percentage"] for row in result] == [30.0, 70.0]

    def test_components_without_positive_mass_or_percentage_are_rejected(self):
        components = [{"material_name": "Linalool", "mass_g": 0.0}]

        with pytest.raises(ValueError, match="positive mass_g or percentage"):
            LegacyFormulaAdapter.from_lab_components(components)


class TestRoundTrip:
    """Tests for LegacyFormulaAdapter.round_trip."""

    def test_round_trip_preserves_proportions(self):
        """Round-trip preserves ingredient proportions."""
        ingredients = [
            {"name": "Alpha Irone", "percentage": 15.0, "role": "heart"},
            {"name": "Iso E Super", "percentage": 45.0, "role": "base"},
            {"name": "Hedione", "percentage": 40.0, "role": "heart"},
        ]
        result = LegacyFormulaAdapter.round_trip(ingredients)
        assert len(result) == 3
        # Percentages should be preserved within tolerance
        by_name = {r["name"]: r for r in result}
        assert by_name["Alpha Irone"]["percentage"] == pytest.approx(15.0, abs=0.1)
        assert by_name["Iso E Super"]["percentage"] == pytest.approx(45.0, abs=0.1)
        assert by_name["Hedione"]["percentage"] == pytest.approx(40.0, abs=0.1)

    def test_round_trip_with_grams(self):
        """Round-trip with grams preserves proportions."""
        ingredients = [
            {"name": "Vanillin", "percentage": 10.0, "grams": 0.1, "role": "base"},
            {"name": "Ethanol", "percentage": 90.0, "grams": 0.9, "role": "solvent"},
        ]
        result = LegacyFormulaAdapter.round_trip(ingredients)
        by_name = {r["name"]: r for r in result}
        assert by_name["Vanillin"]["percentage"] == pytest.approx(10.0, abs=0.1)
