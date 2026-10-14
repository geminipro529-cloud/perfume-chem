"""Pomelo EO modeled from a limonene-dominant literature peel-oil midpoint profile."""

import pytest

from engine.material_resolver import resolve_material
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_POMELO_KEY = "citrus maxima peel oil limonene-dominant literature midpoint profile"


@pytest.mark.parametrize("name", ["Pomelo EO", "Pomelo Essential Oil", "Pomelo Oil"])
def test_pomelo_uses_literature_midpoints_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {
            "limonene": 0.946,
            "myrcene": 0.0203,
            "alpha phellandrene": 0.00793,
            "alpha pinene": 0.0063,
            "beta pinene": 0.00248,
            "ocimene": 0.0021,
        }
    )
    # Hydrodistilled-only oxygenates stay out of the limonene-dominant profile.
    names = {row[0] for row in constituents}
    assert not names & {"linalool", "citral", "neral", "geranial", "nootkatone"}
    # The unidentified remainder is kept, not renormalized away.
    assert sum(row[1] for row in constituents) == pytest.approx(0.98511)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _POMELO_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert metadata.characterized_fraction == pytest.approx(0.98511)
    assert metadata.unresolved_fraction == pytest.approx(0.01489)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)


def test_owned_stock_label_carries_identity_and_furocoumarin_limits():
    metadata = get_composite_metadata("Pomelo EO")
    joined = " ".join(metadata.limitations)
    assert "not an analysis of the owned" in joined
    assert "Citrus maxima" in joined and "C. grandis" in joined
    assert "8016-20-4" in joined and "grapefruit, not pomelo" in joined
    assert "90045-43-5" in joined
    assert "Linalool" in joined and "citral" in joined and "nootkatone" in joined
    assert "isoimperatorin" in joined and "bergapten not detected" in joined
    assert "no safety or IFRA-compliance claim" in joined

    composition = metadata.input_authority["composition"]
    assert composition["owned_species_recorded"] is False
    assert composition["owned_extraction_method_recorded"] is False
    assert composition["owned_furocoumarin_content_recorded"] is False
    assert composition["excluded_hydrodistilled_oxygenates_pct"] == {
        "linalool": 6.5,
        "citral (neral + geranial)": 6.0,
        "nootkatone": 3.4,
    }


def test_pomelo_registry_record_resolves_from_the_stock_label():
    material = resolve_material("Pomelo EO").registry_material
    assert material is not None
    assert material.canonical_name == "Pomelo Essential Oil"


def test_pomelo_is_modeled_from_the_literature_profile():
    state = build_formula_state({"Pomelo EO": 300.0, "Hedione": 900.0})
    row = next(r for r in state.materials if r.name == "Pomelo EO")
    assert row.oav is not None and row.oav > 0.0
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert row.natural_composite_metadata["profile_key"] == _POMELO_KEY
    assert row.natural_composite_metadata["resolution"] == "literature_proxy"


@pytest.mark.parametrize("different_material", ["Pomelo Grandis", "Grapefruit Oil"])
def test_pomelo_proxy_does_not_swallow_the_fraterworks_compound_or_grapefruit(
    different_material,
):
    assert get_composite_metadata(different_material) is None
