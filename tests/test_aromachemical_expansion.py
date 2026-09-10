from __future__ import annotations

import pytest

from engine.aromachemical_expansion import (
    _score_cross_adaptation,
    analyze_expansion,
)
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import parse_inventory
from engine.odor_thresholds import ODT_DATA


def _current_owned_identity_count() -> int:
    """Count owned identities from the current inventory authority.

    Uses the public parser with the same authority selection as
    ``analyze_expansion`` instead of a hard-coded count, so a growing inventory
    cannot silently invalidate the assertion.
    """
    records = parse_inventory(
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    return len({record.identity_name or record.name for record in records})


@pytest.fixture(scope="module")
def range_report():
    return analyze_expansion(top_n=200)


def test_purchase_identity_excludes_owned_aliases_and_stock_preparations(range_report):
    names = {candidate.name for candidate in range_report.candidates}
    assert names.isdisjoint(
        {
            "Cinnamyl alcohol",
            "PEDMC",
            "Alpha-Isomethyl Ionone",
            "Ambrox Super 33% DEP/EtOH",
            "Cedamber",
            "Heliotropin",
            "Myristic Acid",
            "Jasmine Sambac Absolute",
        }
    )


def test_range_extension_excludes_existing_unavailable_stock_by_default(range_report):
    names = {candidate.name for candidate in range_report.candidates}
    records = parse_inventory(unique=False, include_unavailable=True)
    explicitly_unavailable = {
        record.identity_name or record.name
        for record in records
        if record.status != "owned"
    }
    owned = {
        record.identity_name or record.name
        for record in parse_inventory(
            unique=True,
            include_solvents=False,
            include_unavailable=False,
        )
    }

    # Depleted stock is not a range extension, and owned materials are never
    # recommended back to the user.
    assert names.isdisjoint(explicitly_unavailable)
    assert names.isdisjoint(owned)
    # The report must still contain genuine range extensions.
    assert names
    assert range_report.ranking_authority == "MODELLED_RANGE_GAP_NOT_PURCHASE_ORDER"
    assert range_report.inventory_size == _current_owned_identity_count()


def test_inventory_size_counts_owned_identities_exactly(tmp_path):
    """A small deterministic authority proves the count is exact, not vacuous."""
    fixture = tmp_path / "inventory_fixture.txt"
    fixture.write_text(
        "--- CITRUS / TOP ---\n"
        "- Citral\n"
        "- Hexyl Acetate\n"
        "--- MUSKS / BASE ---\n"
        "- Habanolide\n"
        "- Romandolide  # DEPLETED 2026-09-08\n",
        encoding="utf-8",
    )

    report = analyze_expansion(inventory_path=str(fixture), top_n=5)

    assert report.inventory_size == 3


def test_replenishment_is_an_explicit_separate_mode():
    report = analyze_expansion(top_n=200, include_replenishment=True)
    by_name = {candidate.name: candidate for candidate in report.candidates}
    replenishment = {
        name
        for name, candidate in by_name.items()
        if candidate.purchase_mode == "replenishment"
    }
    range_extension = {
        name
        for name, candidate in by_name.items()
        if candidate.purchase_mode == "range_extension"
    }
    owned = {
        record.identity_name or record.name
        for record in parse_inventory(
            unique=True,
            include_solvents=False,
            include_unavailable=False,
        )
    }

    # Depleted stock appears only through the explicit replenishment mode, and
    # no identity is offered in both modes at once.
    assert replenishment
    assert range_extension
    assert replenishment.isdisjoint(range_extension)
    assert range_extension.isdisjoint(owned)
    # Named depleted stock is a replenishment candidate, not a range extension.
    for depleted_name in ("Romandolide", "Tonalide"):
        assert by_name[depleted_name].purchase_mode == "replenishment"
    assert "Myristic Acid" not in by_name


def test_missing_cross_adaptation_annotation_does_not_imply_novel_receptors():
    score, groups = _score_cross_adaptation(
        "Unannotated Material",
        set(),
        {},
    )
    assert score == 0.0
    assert groups == []


def test_opaque_blends_and_unresolved_naturals_are_discounted(range_report):
    by_name = {candidate.name: candidate for candidate in range_report.candidates}
    assert by_name["Orris F-TEC"].modelling_authority == "OPAQUE_MIXTURE_PROXY"
    assert by_name["Orris F-TEC"].modelling_authority_multiplier < 1.0
    assert by_name["Rum Absolute"].modelling_authority == "NATURAL_COMPOSITE_UNRESOLVED"
    assert by_name["Benzoin Resinoid"].modelling_authority == "NATURAL_LITERATURE_COMPOSITE"


def test_heliotropin_piperonal_identity_has_one_numeric_odt_authority():
    assert get_profile("Heliotropin").name == "Heliotropal"
    assert get_profile("Piperonal").name == "Heliotropal"
    assert ODT_DATA["heliotropal"]["odt_air"] == pytest.approx(0.006)
    assert "heliotropin" not in ODT_DATA
    assert "piperonal" not in ODT_DATA


def test_purchase_synergy_axis_is_not_saturated_by_inferred_edges(range_report):
    scores = {round(candidate.synergy_unlock_score, 6) for candidate in range_report.candidates}
    assert len(scores) > 1
    assert any(score < 100.0 for score in scores)
