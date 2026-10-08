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


# --- FormulaAnalysisImportParser: amount column headers -------------------

import pytest  # noqa: E402

from app.services.formula_import import (  # noqa: E402
    FormulaAnalysisImportParser,
    FormulaAnalysisLibrary,
)


def _analysis_rows(table: str):
    result = FormulaAnalysisImportParser.parse_text(
        f"# Test\n\n{table}\n", default_name="test", source_sha256="0" * 64
    )
    return result, [
        (row.material, row.amount_decimal, row.amount_unit, row.concentration_fraction_decimal)
        for row in result.rows
    ]


@pytest.mark.parametrize(
    ("unit_header", "expected_unit"),
    [("µL", "uL"), ("μL", "uL"), ("uL", "uL"), ("ul", "uL"), ("mL", "mL"), ("mg", "mg"), ("g", "g"),
     ("Raw µL", "uL"), ("Raw uL", "uL"), ("Stock µL", "uL")],
)
def test_unit_only_header_is_an_amount_column(unit_header, expected_unit):
    result, rows = _analysis_rows(
        f"| # | Material | Dilution | {unit_header} | Role |\n|---|---|---|---|---|\n"
        "| 1 | Hedione | neat | 120 | heart |\n| 2 | Iso E Super | 10% | 45 | base |"
    )
    assert result.errors == []
    assert rows == [("Hedione", "120", expected_unit, "1"), ("Iso E Super", "45", expected_unit, "0.1")]
    assert {row.amount_header for row in result.rows} == {unit_header}


def test_add_column_reads_unit_from_cells_or_header():
    _, cell_rows = _analysis_rows(
        "| # | Material | Add | Notes |\n|---|---|---|---|\n| 1 | Linalool | 648 µL | top |"
    )
    _, header_rows = _analysis_rows(
        "| # | Material | Dilution | Add (µL) | Role |\n|---|---|---|---|---|\n| 1 | Helional | neat | 25 | air |"
    )
    assert cell_rows == [("Linalool", "648", "uL", None)]
    assert header_rows == [("Helional", "25", "uL", "1")]


def test_add_column_without_a_known_unit_is_rejected():
    result, rows = _analysis_rows(
        "| # | Material | Add | Notes |\n|---|---|---|---|\n| 1 | Linalool | 648 | top |"
    )
    assert rows == []
    assert "Linalool" in result.warnings[0]
    assert result.errors


def test_raw_amount_is_read_and_active_amount_is_not():
    result, rows = _analysis_rows(
        "| # | Role | Material | Dilution | Active µL | Raw µL |\n|---|---|---|---|---|---|\n"
        "| 1 | base | Ambrox | 10% | 12 | 120 |"
    )
    assert rows == [("Ambrox", "120", "uL", "0.1")]
    assert result.rows[0].amount_header == "Raw µL"


def test_active_only_table_is_rejected_with_reason():
    result, rows = _analysis_rows(
        "| # | Material | Dilution | Active µL |\n|---|---|---|---|\n| 1 | Ambrox | 10% | 12 |"
    )
    assert rows == []
    assert result.errors == [
        "Found columns #, Material, Dilution, Active µL but the only amount column is an active "
        "amount. Active amounts are not stock amounts; add the stock amount as a Raw µL column."
    ]


def test_missing_amount_column_error_names_found_columns():
    result, rows = _analysis_rows(
        "| # | Material | Category | Notes |\n|---|---|---|---|\n| 1 | Hedione | floral | airy |"
    )
    assert rows == []
    assert result.errors == [
        "Found columns #, Material, Category, Notes but no amount column. "
        "Use a column named µL, mg, g, Raw µL or Amount."
    ]


def test_restated_table_and_pipeline_report_are_not_counted_twice():
    table = "| # | Material | Dilution | µL |\n|---|---|---|---|\n| 1 | Hedione | neat | 120 |\n"
    result, rows = _analysis_rows(
        f"{table}\n## Bench sheet\n\n{table}\n## Pipeline Analysis\n\n"
        "| Material | Dil | Raw µL | Act µL | OAV |\n|---|---|---|---|---|\n| Linalool | neat | 9 | 9 | 3 |"
    )
    assert rows == [("Hedione", "120", "uL", "1")]


_BUILD = (
    "| # | Material | Dilution | µL |\n|---|---|---|---|\n"
    "| 1 | Hedione | neat | 120 |\n| 2 | Ambrettolide | 10% in DPG | 100 |\n"
)


def test_summary_table_with_dilution_note_in_name_is_skipped_with_warning():
    summary = (
        "| Axis | Material | Dose |\n|---|---|---|\n"
        "| Depth | **Ambrettolide 10%** | 90 µL |\n| Lift | hedione (neat) | 120 µL |"
    )
    result, rows = _analysis_rows(f"{_BUILD}\n## The musk chord\n\n{summary}")
    assert [row[:2] for row in rows] == [("Hedione", "120"), ("Ambrettolide", "100")]
    assert result.errors == []
    assert any('under "The musk chord"' in warning for warning in result.warnings)


def test_partially_overlapping_table_refuses_the_import():
    later = "| Material | Dose |\n|---|---|\n| Hedione | 80 µL |\n| Linalool | 40 µL |"
    result, _ = _analysis_rows(f"{_BUILD}\n## Summary\n\n{later}")
    assert len(result.errors) == 1
    assert "Hedione (line 3)" in result.errors[0]
    assert 'under "Summary" (line 10)' in result.errors[0]


def test_table_breaking_down_one_row_is_not_summed():
    chord = "| Material | Dose |\n|---|---|\n| Aurantiol | 70 µL |\n| Nerol | 30 µL |"
    result, rows = _analysis_rows(f"{_BUILD}\n## Chord explained\n\n{chord}")
    assert [row[0] for row in rows] == ["Hedione", "Ambrettolide"]
    assert any("breaks that row down" in warning for warning in result.warnings)


def test_active_only_table_after_raw_table_is_not_read_as_stock():
    _, rows = _analysis_rows(
        "| Material | Dilution | Raw µL |\n|---|---|---|\n| Hedione | neat | 120 |\n\n"
        "| Material | Dilution | Active µL |\n|---|---|---|\n| Iso E Super | 10% | 12 |"
    )
    assert rows == [("Hedione", "120", "uL", "1")]


def test_add_column_and_existing_bottle_rows_warn_that_total_is_additions():
    result, rows = _analysis_rows(
        "| Material | Add (µL) |\n|---|---|\n| Linalool | 250 |\n\n"
        "## v5c — Add to Existing Bottle\n\n### What to Add\n\n"
        "| Material | µL |\n|---|---|\n| Linalool | 50 |\n| Irotyl | 650 |"
    )
    assert len(rows) == 3
    assert result.errors == []
    assert any("additions to an existing bottle" in warning for warning in result.warnings)


def test_ethanol_row_is_skipped_but_carrier_rows_stay():
    result, rows = _analysis_rows(
        "| Material | µL |\n|---|---|\n| Hedione | 600 |\n| DPG | 100 |\n| Ethanol 96% | 24,222 |"
    )
    assert [row[0] for row in rows] == ["Hedione", "DPG"]
    assert any("Ethanol 96% is the final dilution" in warning for warning in result.warnings)


# Tracked formula files that parsed: 209 of 543 before unit-only headers were
# read, then 469.  Files whose later tables partly repeat materials already
# read now refuse instead of double counting (a deliberate spec change), so
# the floor counts imports without errors and pins the count measured then.
LIBRARY_PARSE_FLOOR = 429


def test_project_formula_library_parse_coverage():
    library = FormulaAnalysisLibrary()
    sources = library.list_sources()
    parsed = 0
    for source in sources:
        text = (library.root / source["source_path"]).read_text(encoding="utf-8")
        result = FormulaAnalysisImportParser.parse_text(
            text, default_name="x", source_sha256="0" * 64
        )
        if result.rows and not result.errors:
            parsed += 1
        for row in result.rows:
            assert "active" not in row.amount_header.casefold(), source["source_path"]
            assert not row.amount_header.casefold().startswith("act "), source["source_path"]
    print(f"formula library: {parsed} of {len(sources)} files parsed")
    assert parsed >= LIBRARY_PARSE_FLOOR
