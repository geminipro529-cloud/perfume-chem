"""Tests for FormulaImportParser."""

from pathlib import Path

from app.services.formula_import import (
    FormulaImportParser,
    ImportResult,
    ParsedComponent,
)

SAMPLE_FORMULA = """# Test Formula

## Top
| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|------------|----------|-------------|-------------|
| 1 | Bergamot FCF | neat | 200 | 0.20 |
| 2 | Lemon FCF | neat | 100 | 0.10 |

## Heart
| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|------------|----------|-------------|-------------|
| 3 | Hedione | neat | 300 | 0.30 |
| 4 | Alpha Irone | 10% | 50 | 0.05 |

## Base
| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|------------|----------|-------------|-------------|
| 5 | Iso E Super | neat | 400 | 0.40 |

Accord notes here.
"""

FORMULA_WITH_EMOJI_SECTIONS = """# Osmanthus Apricot-Suede Chypre

## Formula

| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|-----------|----------|-------------|-------------|
| **🌅 Top** |
| 1 | Bergamot FCF | neat | 25 | 0.025 |
| 2 | Ethyl Linalool | neat | 25 | 0.025 |
| **💕 Heart** |
| 3 | Hedione HC | neat | 800 | 0.800 |
| 4 | Osmanthus Absolute | 10% in DPG | 700 | 0.700 |
| **🪵 Base** |
| 5 | Iso E Super | neat | 450 | 0.450 |
| 6 | Benzyl Salicylate | neat | 600 | 0.600 |
"""

FORMULA_WITH_MATERIAL_COLUMN = """# Vetiver Classique

## Top
| # | Material | Dilution | Amount (uL) | Amount (mL) | Role |
|---|----------|----------|-------------|-------------|------|
| 1 | Bergamot FCF | neat | 200 | 0.200 | Bright controlled citrus |
| 2 | Petitgrain EO | neat | 100 | 0.100 | Green-woody bridge |

## Heart
| # | Material | Dilution | Amount (uL) | Amount (mL) | Role |
|---|----------|----------|-------------|-------------|------|
| 3 | Geraniol | 10% in DPG | 500 | 0.500 | Rosy-geranium heart |

## Base
| # | Material | Dilution | Amount (uL) | Amount (mL) | Role |
|---|----------|----------|-------------|-------------|------|
| 4 | Vetiver EO | neat | 1700 | 1.700 | STAR |
"""

FLAT_FORMULA_NO_SECTIONS = """# Simple Formula

| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|------------|----------|-------------|-------------|
| 1 | Bergamot | neat | 100 | 0.10 |
| 2 | Hedione | neat | 200 | 0.20 |
| 3 | Iso E Super | neat | 300 | 0.30 |
"""


class TestFormulaImportParser:
    def test_parse_basic_formula(self):
        result = FormulaImportParser.parse_text(SAMPLE_FORMULA)
        assert result.formula_name == "Test Formula"
        assert len(result.components) == 5
        assert not result.errors

    def test_component_roles(self):
        result = FormulaImportParser.parse_text(SAMPLE_FORMULA)
        roles = {c.role for c in result.components}
        assert "top" in roles
        assert "heart" in roles
        assert "base" in roles

    def test_dilution_parsing(self):
        result = FormulaImportParser.parse_text(SAMPLE_FORMULA)
        neat_components = [c for c in result.components if c.dilution == 1.0]
        diluted = [c for c in result.components if c.dilution < 1.0]
        assert len(neat_components) == 4  # 2 top + 1 heart + 1 base
        assert len(diluted) == 1  # Alpha Irone 10%
        assert diluted[0].dilution == 0.1

    def test_volume_parsing(self):
        result = FormulaImportParser.parse_text(SAMPLE_FORMULA)
        volumes = {c.material_name: c.volume_ul for c in result.components}
        assert volumes["Bergamot FCF"] == 200
        assert volumes["Hedione"] == 300
        assert volumes["Alpha Irone"] == 50

    def test_empty_file(self):
        result = FormulaImportParser.parse_text("", "empty")
        assert result.formula_name == "empty"
        assert result.errors

    def test_file_not_found(self):
        result = FormulaImportParser.parse_file(Path("/nonexistent/formula.md"))
        assert result.errors

    def test_emoji_section_headers(self):
        """Test formulas with emoji section headers inside tables."""
        result = FormulaImportParser.parse_text(FORMULA_WITH_EMOJI_SECTIONS)
        assert result.formula_name == "Osmanthus Apricot-Suede Chypre"
        assert len(result.components) == 6
        assert not result.errors

        # Check roles are correctly assigned from emoji headers
        roles_by_material = {c.material_name: c.role for c in result.components}
        assert roles_by_material["Bergamot FCF"] == "top"
        assert roles_by_material["Osmanthus Absolute"] == "heart"
        assert roles_by_material["Iso E Super"] == "base"

    def test_material_column_name(self):
        """Test formulas using 'Material' column header instead of 'Ingredient'."""
        result = FormulaImportParser.parse_text(FORMULA_WITH_MATERIAL_COLUMN)
        assert result.formula_name == "Vetiver Classique"
        assert len(result.components) == 4
        assert not result.errors
        materials = [c.material_name for c in result.components]
        assert "Bergamot FCF" in materials
        assert "Geraniol" in materials
        assert "Vetiver EO" in materials

    def test_flat_table_no_sections(self):
        """Test formulas with a single flat table and no ## section headers."""
        result = FormulaImportParser.parse_text(FLAT_FORMULA_NO_SECTIONS)
        assert result.formula_name == "Simple Formula"
        assert len(result.components) == 3
        assert not result.errors
        # All should have None role since there are no section headers
        assert all(c.role is None for c in result.components)

    def test_parsed_component_dataclass(self):
        """Verify ParsedComponent struct fields."""
        pc = ParsedComponent(
            material_name="Test Material",
            dilution=0.5,
            volume_ul=100.0,
            role="heart",
        )
        assert pc.material_name == "Test Material"
        assert pc.dilution == 0.5
        assert pc.volume_ul == 100.0
        assert pc.role == "heart"

    def test_import_result_dataclass(self):
        """Verify ImportResult struct fields."""
        pc = ParsedComponent("Test", 1.0, 50.0, None)
        result = ImportResult(
            formula_name="Test",
            components=[pc],
            warnings=["warning 1"],
            errors=[],
        )
        assert result.formula_name == "Test"
        assert len(result.components) == 1
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    def test_unknown_dilution_is_skipped_instead_of_assumed_neat(self):
        text = """# Unsafe Dilution

| # | Ingredient | Dilution | Amount (uL) |
|---|------------|----------|-------------|
| 1 | Alpha Irone | one percent | 100 |
"""

        result = FormulaImportParser.parse_text(text)

        assert result.components == []
        assert any("could not parse dilution" in warning for warning in result.warnings)
        assert result.errors == ["No ingredient table rows found in the file"]
