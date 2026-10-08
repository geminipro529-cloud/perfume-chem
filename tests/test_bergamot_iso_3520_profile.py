"""Bergamot FCF modeled from the ISO 3520:2022 Calabrian whole-oil range midpoints."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_BERGAMOT_KEY = "citrus bergamia calabrian type iso 3520 midpoint profile"


@pytest.mark.parametrize("name", ["Bergamot FCF oil Sicilian", "Bergamot FCF", "Bergamot EO"])
def test_bergamot_uses_iso_3520_midpoints_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {
            "limonene": 0.395,
            "linalyl acetate": 0.290,
            "linalool": 0.090,
            "gamma terpinene": 0.080,
            "beta pinene": 0.0625,
            "geranial": 0.00375,
        }
    )
    assert sum(row[1] for row in constituents) == pytest.approx(0.92125)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _BERGAMOT_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.92125)
    assert metadata.unresolved_fraction == pytest.approx(0.07875)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"]: row["reported_fraction"] for row in metadata.unresolved_constituents}
    assert unresolved == pytest.approx({"beta-bisabolene": 0.005})


def test_owned_fcf_stock_label_carries_the_proxy_limitations():
    joined = " ".join(get_composite_metadata("Bergamot FCF oil Sicilian").limitations)
    assert "ISO 3520" in joined
    assert "Calabrian" in joined
    assert "removes bergaptene" in joined
    assert "not an analysis of the owned" in joined


def test_bergamot_fcf_stock_is_modeled_from_the_iso_profile():
    state = build_formula_state({"Bergamot FCF oil Sicilian": 300.0, "Hedione": 900.0})
    row = next(r for r in state.materials if r.name == "Bergamot FCF oil Sicilian")
    assert row.oav is not None and row.oav > 0.0
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert row.natural_composite_metadata["profile_key"] == _BERGAMOT_KEY
