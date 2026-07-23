
import pytest

from scripts.verify_formula_workflow import parse_formula_markdown


def test_parse_formula_markdown_handles_neat_inline_dilutions_and_thousands(tmp_path):
    formula_path = tmp_path / "iris_cacao_like.md"
    formula_path.write_text(
        """# Iris Cacao

| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|-----------|----------|-------------|-------------|
| 1 | Alpha Isomethyl Ionone (AIMI) | neat | 1,400 | 1.40 |
| 2 | Alpha Irone | 30% in DEP | 500 | 0.50 |
| 3 | Coumarin | 20 % in DPG | 1 168 | 1.168 |
| 4 | Musk Ketone | pre-dilute 10% in DPG | 300 | 0.30 |
| 5 | Ambrettolide | 10% in DPG | 350 | 0.35 |
| 6 | Ethanol 96% | — | — | 40.37 |
| | **TOTAL** | | | **50.00** |
""",
        encoding="utf-8",
    )

    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    formula = formulas[0]
    assert formula["ingredients_ul"]["Alpha Isomethyl Ionone (AIMI)"] == 1400.0
    assert formula["ingredients_ul"]["Alpha Irone"] == 500.0
    assert formula["ingredients_ul"]["Coumarin"] == 1168.0
    assert formula["ingredients_ul"]["Musk Ketone"] == 300.0
    assert formula["dilutions"]["Alpha Isomethyl Ionone (AIMI)"] == 1.0
    assert formula["dilutions"]["Alpha Irone"] == 0.3
    assert formula["dilutions"]["Coumarin"] == 0.2
    assert formula["dilutions"]["Musk Ketone"] == 0.1
    assert "Ethanol 96%" not in formula["ingredients_ul"]


def test_parse_formula_markdown_ignores_architecture_and_section_marker_rows(tmp_path):
    formula_path = tmp_path / "eclipse_like.md"
    formula_path.write_text(
        """# Eclipse I

| Layer | Function | Materials |
|---|---|---|
| Base | Structure | Iso E Super, Ambrox Super |

| # | Ingredient | Dilution | Amount (µL) | Amount (mL) |
|---|-----------|----------|------------|------------|
| | **— TOP: Corona Flash —** | | | |
| 1 | Aldehyde C11 | 1% | 80 | 0.08 |
| 2 | Bergamot FCF oil Sicilian | neat | 120 | 0.12 |
| | **— BASE: Cosmic Void —** | | | |
| 3 | Galaxolide | 80% | 250 | 0.25 |
| 4 | Iso E Super | neat | 350 | 0.35 |
| 5 | **Ethanol 96%** | — | — | **7.95** |
| | **TOTAL** | | | **10.00** |
""",
        encoding="utf-8",
    )

    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    formula = formulas[0]
    assert set(formula["ingredients_ul"]) == {
        "Aldehyde C11",
        "Bergamot FCF oil Sicilian",
        "Galaxolide",
        "Iso E Super",
    }
    assert formula["dilutions"]["Aldehyde C11"] == 0.01
    assert formula["dilutions"]["Galaxolide"] == 0.8


def test_parse_formula_markdown_converts_percentage_tables_when_total_is_known(tmp_path):
    formula_path = tmp_path / "percentage_table.md"
    formula_path.write_text(
        """# Percentage Formula

Concentrate target: 6000 uL

| Ingredient | % |
|---|---:|
| Hedione | 50 |
| Iso E Super | 30 |
| Habanolide | 20 |
| **Total** | **100** |
""",
        encoding="utf-8",
    )

    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    formula = formulas[0]
    assert formula["ingredients_ul"]["Hedione"] == 3000.0
    assert formula["ingredients_ul"]["Iso E Super"] == 1800.0
    assert formula["ingredients_ul"]["Habanolide"] == 1200.0
    assert formula["dilutions"]["Hedione"] == 1.0


def test_parse_formula_markdown_extracts_family_archetype(tmp_path):
    formula_path = tmp_path / "study_formula.md"
    formula_path.write_text(
        """# Study Formula

**Historical reference:** Example Reference
**Family archetype:** `chypre_classical.coty_reference`

| # | Ingredient | Dilution | Amount (µL) |
|---|---|---|---:|
| 1 | Bergamot FCF oil Sicilian | neat | 800 |
| 2 | Patchouli EO | neat | 600 |
| 3 | Evernyl | neat | 120 |
| 4 | Iso E Super | neat | 480 |
""",
        encoding="utf-8",
    )

    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    assert formulas[0]["family_archetype"] == "chypre_classical.coty_reference"


def test_parse_formula_markdown_ignores_historical_and_aggregate_rows(tmp_path):
    formula_path = tmp_path / "edited_batch.md"
    formula_path.write_text(
        """# Edited Batch

| Ingredient | Dilution | Amount (uL) |
|---|---:|---:|
| ~~Romandolide~~ | ~~neat~~ | ~~300~~ |
| Zero-dose placeholder | neat | 0 |
| 450 | neat | 450 |
| Iris Accord Total | | 900 |
| Additions Total | | 120 |
| Fragrance sub-total | | 6000 |
| Final bottle total | | 30000 |
| Alpha Irone | 30% w/w in IPM | 100 |
| Ethylene Brassylate | neat | 350 |
""",
        encoding="utf-8",
    )

    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    assert formulas[0]["ingredients_ul"] == {
        "Alpha Irone": 100.0,
        "Ethylene Brassylate": 350.0,
    }


def test_parser_reads_only_explicit_finished_matrix_section(tmp_path):
    path = tmp_path / "matrix_formula.md"
    path.write_text(
        """# Matrix Formula

## Formula

| Ingredient | Dilution | Amount (uL) |
|---|---:|---:|
| Hedione | neat | 1000 |

## Finished Matrix Inputs

**Matrix authority:** `explicit`

| Component | Volume uL | Density g/mL | MW g/mol | Source |
|---|---:|---:|---:|---|
| Ethanol | 4000 | 0.785 | 46.0684 | NIST Chemistry WebBook CAS 64-17-5 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(path)[0]

    assert formula["ingredients_ul"] == {"Hedione": 1000.0}
    assert formula["matrix_source"] == "explicit"
    assert formula["matrix_mass_g"] == pytest.approx(3.14)
    assert formula["matrix_moles"]["Ethanol"] == pytest.approx(3.14 / 46.0684)


def test_parser_marks_matrix_partial_when_stock_carrier_is_unresolved(tmp_path):
    path = tmp_path / "partial_matrix_formula.md"
    path.write_text(
        """# Partial Matrix Formula

## Formula

| Ingredient | Dilution | Amount (uL) |
|---|---:|---:|
| Ambrettolide | 10% in DPG | 100 |

## Finished Matrix Inputs

| Component | Volume uL | Density g/mL | MW g/mol | Source |
|---|---:|---:|---:|---|
| Ethanol | 4000 | 0.785 | 46.0684 | NIST Chemistry WebBook CAS 64-17-5 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(path)[0]

    assert formula["matrix_source"] == "incomplete_stock_carrier"
