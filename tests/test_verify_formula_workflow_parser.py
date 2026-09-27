
import pytest

from engine.chemical_life_graph import build_chemical_life_graph
from engine.formula_metadata import _extract_material_names
from engine.mixer.instructions import build_formula_compounding_protocol
from scripts.format_pipeline_analysis import cli_transport_text
from scripts.verify_formula_workflow import (
    _format_life_graph_lines,
    parse_formula_markdown,
)


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


def test_metadata_preflight_extracts_only_dose_bearing_formula_tables(tmp_path):
    formula_path = tmp_path / "osmanthus_like.md"
    formula_path.write_text(
        """# Osmanthus Study

## Formula

| # | Ingredient | Dilution | Amount (uL) | Active ppm w/w |
|---|---|---:|---:|---:|
| 1 | Osmanthus Absolute | 10% in DPG | 300 | UNAVAILABLE |
| 2 | Hedione | neat | 350 | UNAVAILABLE |

## Accord architecture

| Layer | Function |
|---|---|
| Osmanthus + Hedione | Transparent apricot-floral heart |

<!-- PIPELINE_ANALYSIS_START -->
| Material | OAV |
|---|---:|
| Fake generated row | 999 |
""",
        encoding="utf-8",
    )

    assert _extract_material_names(str(formula_path)) == [
        "Osmanthus Absolute",
        "Hedione",
    ]


def test_chemical_life_graph_does_not_claim_uncalibrated_longevity():
    graph = build_chemical_life_graph(
        "truth probe",
        {
            "Bergamot EO FCF": 100.0,
            "Hedione": 300.0,
            "Iso E Super": 300.0,
        },
    )

    assert graph.temporal.longevity_hours is None
    assert graph.temporal.authority == "HEURISTIC_UNCALIBRATED"
    assert graph.temporal.release_authority is False

    lines = _format_life_graph_lines(
        {
            "temporal": {
                "longevity_hours": graph.temporal.longevity_hours,
                "top_dominance_model_minutes": (
                    graph.temporal.top_dominance_model_minutes
                ),
                "base_dominance_model_hours": (
                    graph.temporal.base_dominance_model_hours
                ),
                "linear_score": graph.temporal.linear_score,
                "authority": graph.temporal.authority,
            }
        }
    )
    report = "\n".join(lines)
    assert "Estimated longevity" not in report
    assert "Absolute longevity: unavailable" in report
    assert "model window" in report


def test_cli_transport_text_preserves_saved_unicode_but_stabilizes_piped_output():
    source = "Headspace OAV — Raw µL | γ | Bangkok ×2.2 | β-ionone → drydown"

    assert cli_transport_text(source, ascii_only=False) == source
    assert cli_transport_text(source, ascii_only=True) == (
        "Headspace OAV -- Raw uL | gamma | Bangkok x2.2 | "
        "beta-ionone -> drydown"
    )


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


def test_parser_keeps_small_explicit_ul_rows_when_total_is_known(tmp_path):
    formula_path = tmp_path / "small_volume_table.md"
    formula_path.write_text(
        """# Small Volume Formula

Concentrate target: 1000 uL

| Ingredient | Dilution | Amount (uL) |
|---|---|---:|
| Trace material | neat | 80 |
| Another trace | neat | 5 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["ingredients_ul"] == {
        "Trace material": 80.0,
        "Another trace": 5.0,
    }


def test_parser_keeps_volume_only_rows_when_total_is_absent(tmp_path):
    formula_path = tmp_path / "volume_only_table.md"
    formula_path.write_text(
        """# Volume Only Formula

| Ingredient | Dilution | Amount (uL) |
|---|---|---:|
| Trace material | neat | 80 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["ingredients_ul"] == {"Trace material": 80.0}


def test_parser_requires_total_for_explicit_percent_amount_rows(tmp_path):
    formula_path = tmp_path / "percent_without_total.md"
    formula_path.write_text(
        """# Formula Percent Without Total

| Ingredient | % |
|---|---:|
| Hedione | 50 |
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="percentage amount rows require"):
        parse_formula_markdown(formula_path)


def test_parser_does_not_treat_percentage_total_row_as_volume(tmp_path):
    formula_path = tmp_path / "percent_total_without_volume.md"
    formula_path.write_text(
        """# Formula Percentage Total Without Volume

| Ingredient | % |
|---|---:|
| Hedione | 50 |
| Iso E Super | 50 |
| **Total** | **100** |
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="percentage amount rows require"):
        parse_formula_markdown(formula_path)


@pytest.mark.parametrize(
    ("label", "expected_ul"),
    [
        ("Concentrate target: 6 mL", 6000.0),
        ("Concentrate total: 6 mL", 6000.0),
        ("Concentrate total: 6000 uL", 6000.0),
        ("Concentrate target: 6000 µL", 6000.0),
        ("Concentrate Volume: 6 mL", 6000.0),
        ("Total Concentrate: 6000 uL", 6000.0),
        ("Target Concentrate: 6 mL", 6000.0),
        ("Concentrate Volume (µL): 6000", 6000.0),
        ("Concentrate Volume (mL): 6", 6000.0),
        ("Total Concentrate (µL): 6000", 6000.0),
        ("Target Concentrate (mL): 6", 6000.0),
        ("Batch total: 6 mL", 6000.0),
    ],
)
def test_parser_accepts_explicit_unit_bearing_concentrate_totals(label, expected_ul):
    body = f"""# Explicit Total Formula

{label}

| Ingredient | % |
|---|---:|
| Hedione | 10 |
"""

    from scripts.verify_formula_workflow import _parse_formula_rows

    ingredients_ul, _, _ = _parse_formula_rows(body)

    assert ingredients_ul == {"Hedione": expected_ul / 10.0}


@pytest.mark.parametrize("label", [
    "Concentrate target: 0 uL",
    "Concentrate total: 0 mL",
    "Concentrate target: -100 uL",
    "Batch total: -1 mL",
])
def test_parser_rejects_nonpositive_explicit_concentrate_totals(label):
    body = f"""# Invalid Total Formula

{label}

| Ingredient | % |
|---|---:|
| Hedione | 10 |
"""

    from scripts.verify_formula_workflow import _parse_formula_rows

    with pytest.raises(ValueError, match="total volume must be positive"):
        _parse_formula_rows(body)


def test_parser_ignores_oav_share_table_even_when_volume_target_exists(tmp_path):
    formula_path = tmp_path / "oav_share_report.md"
    formula_path.write_text(
        """# OAV Share Report

Concentrate target: 1000 uL

## Headspace OAV

| Material | OAV | % of Total |
|---|---:|---:|
| Hedione | 999 | 50 |
""",
        encoding="utf-8",
    )

    assert parse_formula_markdown(formula_path) == []


def test_parser_recombines_mixed_explicit_volume_and_percent_rows(tmp_path):
    formula_path = tmp_path / "mixed_amount_table.md"
    formula_path.write_text(
        """# Mixed Amount Formula

Concentrate target: 1000 uL

| Ingredient | Dilution | Amount (uL) | Percent |
|---|---|---:|---:|
| Hedione | neat | 5 | |
| Iso E Super | neat | | 10 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["ingredients_ul"] == {
        "Hedione": 5.0,
        "Iso E Super": 100.0,
    }


def test_parser_documents_volume_precedence_when_both_amount_columns_are_populated(tmp_path):
    formula_path = tmp_path / "volume_precedence.md"
    formula_path.write_text(
        """# Volume Precedence Formula

Concentrate target: 1000 uL

| Ingredient | Amount (uL) | Percent |
|---|---:|---:|
| Hedione | 5 | 10 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["ingredients_ul"] == {"Hedione": 5.0}


def test_parser_ignores_diagnostic_percent_columns(tmp_path):
    formula_path = tmp_path / "diagnostic_percent_table.md"
    formula_path.write_text(
        """# Diagnostic Percent Table

| Material | Active Percent | Concentration |
|---|---:|---:|
| Hedione | 50 | 10%
""",
        encoding="utf-8",
    )

    assert parse_formula_markdown(formula_path) == []


def test_parser_ignores_percent_table_without_formula_dosing_context(tmp_path):
    formula_path = tmp_path / "parts_percent_report.md"
    formula_path.write_text(
        """# GC-MS Report

Concentrate target: 6000 uL

## Solvents

| Material | Parts | % | Note |
|---|---:|---:|---|
| DPG | 72.8 | 7.28% | Carrier solvent |
""",
        encoding="utf-8",
    )

    assert parse_formula_markdown(formula_path) == []


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


def test_parser_preserves_explicit_physical_rows_and_basket_contract(tmp_path):
    formula_path = tmp_path / "basket_formula.md"
    formula_path.write_text(
        """# Basket Formula

| Row ID | Ingredient | Dilution | Amount (uL) | Basket | Operation | Prepared Dilution ID |
|---|---|---|---:|---:|---|---|
| h1 | Hedione | neat | 60 | 7 | direct add | |
| h2 | Hedione | neat | 40 | 7 | direct add | |
| i1 | Iso E Super | neat | 200 | 3 | direct add | |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["ingredients_ul"] == {"Hedione": 100.0, "Iso E Super": 200.0}
    assert formula["compounding_row_status"] == "COMPLETE"
    assert formula["compounding_row_blockers"] == []
    assert [row["row_id"] for row in formula["compounding_rows"]] == [
        "h1",
        "h2",
        "i1",
    ]
    assert [row["basket"] for row in formula["compounding_rows"]] == [7, 7, 3]
    assert formula["compounding_rows"][0]["physical_stock_label"] == "Hedione [neat]"
    protocol = build_formula_compounding_protocol(
        formula,
        prebond_analysis={
            "must_prebond": [],
            "benefits": [],
            "keep_separate": [],
            "crystalline": [],
        },
    )
    assert protocol["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in protocol["authority_blockers"]
    )
    assert [
        instruction.split(" [row ", 1)[1].split("]", 1)[0]
        for phase in protocol["phases"]
        for instruction in phase["instructions"]
        if " [row " in instruction
    ] == ["i1", "h1", "h2"]


def test_parser_accepts_explicit_basket_heading_without_inference(tmp_path):
    formula_path = tmp_path / "basket_heading_formula.md"
    formula_path.write_text(
        """# Heading Basket Formula

## Basket 7 - Muguet and lavender

| Ingredient | Dilution | Amount (uL) |
|---|---|---:|
| Hedione | neat | 100 |

## Basket 3 - Woods

| Ingredient | Dilution | Amount (uL) |
|---|---|---:|
| Iso E Super | neat | 200 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["compounding_row_status"] == "COMPLETE"
    assert [row["basket"] for row in formula["compounding_rows"]] == [7, 3]


def test_parser_withholds_compounding_authority_without_explicit_baskets(tmp_path):
    formula_path = tmp_path / "unassigned_formula.md"
    formula_path.write_text(
        """# Unassigned Formula

| Ingredient | Dilution | Amount (uL) |
|---|---|---:|
| Hedione | neat | 100 |
""",
        encoding="utf-8",
    )

    formula = parse_formula_markdown(formula_path)[0]

    assert formula["compounding_rows"] == []
    assert formula["compounding_row_status"] == "UNAVAILABLE"
    assert formula["compounding_row_blockers"] == [
        "EXPLICIT_BASKET_ASSIGNMENTS_NOT_DECLARED"
    ]


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
