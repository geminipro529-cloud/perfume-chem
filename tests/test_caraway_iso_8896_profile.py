"""Caraway seed oil modeled from the ISO 8896:2016 range midpoints."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_CARAWAY_KEY = "carum carvi fruit oil iso 8896 midpoint profile"


@pytest.mark.parametrize(
    "name", ["Caraway Seed Oil (10% w/w in DPG)", "Caraway Seed Oil", "Caraway Seed EO"]
)
def test_caraway_uses_iso_8896_midpoints_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {"limonene": 0.390, "myrcene": 0.0045}
    )
    assert sum(row[1] for row in constituents) == pytest.approx(0.3945)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _CARAWAY_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.3945)
    assert metadata.unresolved_fraction == pytest.approx(0.6055)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"]: row["reported_fraction"] for row in metadata.unresolved_constituents}
    # Carvone has no runtime tuple: it stays listed as unresolved, not odorless.
    # trans-Carveol "traces (<0.01)" to 0.5% takes its midpoint from 0.
    assert unresolved == pytest.approx(
        {
            "carvone": 0.565,
            "cis-dihydrocarvone": 0.008,
            "cis-carveol": 0.0035,
            "trans-carveol": 0.0025,
        }
    )
    assert all(row["odor_contribution"] == "UNCOMPUTED" for row in metadata.unresolved_constituents)
    joined = " ".join(metadata.limitations)
    assert "ISO 8896" in joined and "not an analysis of the owned bottle" in joined


def test_caraway_stock_is_modeled_from_the_iso_profile():
    state = build_formula_state({"Caraway Seed Oil (10% w/w in DPG)": 100.0, "Hedione": 900.0})
    row = next(r for r in state.materials if r.name == "Caraway Seed Oil (10% w/w in DPG)")
    assert row.oav is not None and row.oav > 0.0
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert row.natural_composite_metadata["profile_key"] == _CARAWAY_KEY
