"""Grapefruit FCF modeled from the ISO 3053:2004 expressed-oil range midpoints."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_GRAPEFRUIT_KEY = "citrus paradisi expressed oil iso 3053 midpoint profile"


@pytest.mark.parametrize("name", ["Grapefruit FCF oil Sicilian", "Grapefruit FCF"])
def test_grapefruit_uses_iso_3053_midpoints_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {
            "limonene": 0.940,
            "myrcene": 0.020,
            "octanal": 0.005,
            "nootkatone": 0.00405,
            "alpha pinene": 0.004,
            "sabinene": 0.0035,
            "beta caryophyllene": 0.0035,
            "beta pinene": 0.00125,
            "neral": 0.0003,
        }
    )
    # Linalool is not in the ISO 3053 profile.
    assert "linalool" not in {row[0] for row in constituents}
    assert sum(row[1] for row in constituents) == pytest.approx(0.9816)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _GRAPEFRUIT_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.9816)
    assert metadata.unresolved_fraction == pytest.approx(0.0184)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"]: row["reported_fraction"] for row in metadata.unresolved_constituents}
    assert unresolved == pytest.approx({"decanal": 0.0035, "nonanal": 0.0007})


def test_owned_stock_label_carries_the_supplier_proxy_limitations():
    joined = " ".join(get_composite_metadata("Grapefruit FCF oil Sicilian").limitations)
    assert "7CA24030" in joined
    assert "ISO 3053" in joined
    assert "68917-32-8" in joined and "not used as identity evidence" in joined
    assert "furocoumarin" in joined


def test_grapefruit_is_modeled_from_the_iso_profile():
    state = build_formula_state({"Grapefruit FCF oil Sicilian": 300.0, "Hedione": 900.0})
    row = next(r for r in state.materials if r.name == "Grapefruit FCF oil Sicilian")
    assert row.oav is not None and row.oav > 0.0
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert row.natural_composite_metadata["profile_key"] == _GRAPEFRUIT_KEY
