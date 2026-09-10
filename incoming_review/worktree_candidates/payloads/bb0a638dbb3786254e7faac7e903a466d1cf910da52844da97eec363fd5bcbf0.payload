from __future__ import annotations

from pathlib import Path

import pytest

from engine.range_gap_analysis import analyze_range_coverage


@pytest.fixture(scope="module")
def live_report():
    return analyze_range_coverage()


def test_live_range_report_uses_inventory_and_explicit_formula_evidence(live_report):
    assert live_report.inventory_available_count == 230
    by_key = {row.key: row for row in live_report.registered_archetypes}
    prada = by_key["iris_amber_woody.prada_lhomme_reference"]
    assert prada.buildability_status == "BUILDABLE_FROM_AVAILABLE_STOCK_IDENTITIES"
    assert prada.formula_record_status == "DECLARED_FORMULA_PRESENT"
    assert {
        "Prada_LHomme_Architecture_Control_30mL_EdT.md",
        "Prada_LHomme_Luxury_Orris_30mL_EdT.md",
    }.issubset(set(prada.formula_files))


def test_unmodeled_taxonomy_is_unknown_not_unbuildable(live_report):
    by_subfamily = {row.subfamily: row for row in live_report.taxonomy}
    assert len(by_subfamily) == 71
    assert by_subfamily["gourmand_coffee"].status == "UNMODELED_NO_BUILDABILITY_CLAIM"
    assert by_subfamily["gourmand_coffee"].formula_record_status == "UNMODELED_FORMULA_MAPPING"


def test_not_made_means_no_explicit_repository_declaration_only(live_report):
    assert "iris_ambrox_amber.dhi2025" in live_report.buildable_without_formula_record
    assert any(
        "does not prove that a physical batch was compounded" in limitation
        for limitation in live_report.limitations
    )


def test_missing_anchor_groups_are_reported_without_guessing(tmp_path: Path):
    inventory = tmp_path / "inventory.txt"
    inventory.write_text(
        "--- FLORAL MATERIALS ---\n- Neroli EO\n",
        encoding="utf-8",
    )
    formulas = tmp_path / "formulas"
    formulas.mkdir()
    report = analyze_range_coverage(inventory, formulas)
    by_key = {row.key: row for row in report.registered_archetypes}
    prada = by_key["iris_amber_woody.prada_lhomme_reference"]
    assert prada.buildability_status == "PARTIAL_MISSING_ANCHOR_GROUPS"
    assert "violet_iris_core" in prada.missing_anchor_groups
    assert prada.formula_record_status == "NO_DECLARED_FORMULA_RECORD"


def test_only_explicit_family_archetype_metadata_counts(tmp_path: Path):
    inventory = tmp_path / "inventory.txt"
    inventory.write_text("--- CITRUS / TOP ---\n- Bergamot FCF\n", encoding="utf-8")
    formulas = tmp_path / "formulas"
    formulas.mkdir()
    (formulas / "filename_says_prada_lhomme.md").write_text(
        "# Prada L'Homme in a filename only\n",
        encoding="utf-8",
    )
    (formulas / "declared.md").write_text(
        "**Family archetype:** `iris_amber_woody.prada_lhomme_reference`\n",
        encoding="utf-8",
    )
    report = analyze_range_coverage(inventory, formulas)
    by_key = {row.key: row for row in report.registered_archetypes}
    prada = by_key["iris_amber_woody.prada_lhomme_reference"]
    assert prada.formula_files == ("declared.md",)
