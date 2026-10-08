"""Nutmeg EO modeled from the ISO 3215:1998 Indonesian-type range midpoints."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.pipeline.preflight import _natural_composite_coverage_check

_NUTMEG_KEY = "myristica fragrans indonesian type iso 3215 midpoint profile"


@pytest.mark.parametrize("name", ["Nutmeg EO", "Nutmeg Essential Oil"])
def test_nutmeg_uses_iso_3215_midpoints_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    assert {row[0]: row[1] for row in constituents} == pytest.approx(
        {
            "alpha pinene": 0.215,
            "sabinene": 0.215,
            "beta pinene": 0.155,
            "limonene": 0.045,
            "gamma terpinene": 0.040,
            "terpinen-4-ol": 0.040,
            "delta-3-carene": 0.0125,
        }
    )
    assert sum(row[1] for row in constituents) == pytest.approx(0.7225)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _NUTMEG_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.7225)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"]: row["reported_fraction"] for row in metadata.unresolved_constituents}
    assert unresolved == pytest.approx({"myristicin": 0.085, "safrole": 0.0175})


@pytest.mark.parametrize("name", ["Mace EO", "Mace Absolute", "Nutmeg Absolute"])
def test_mace_and_nutmeg_absolute_are_not_mapped_to_the_seed_oil(name):
    assert get_constituents(name) is None


def test_nutmeg_is_modeled_but_still_warns_as_partial():
    state = build_formula_state({"Nutmeg EO": 20.0, "Hedione": 900.0})
    nutmeg = next(row for row in state.materials if row.name == "Nutmeg EO")
    assert nutmeg.oav is not None
    assert nutmeg.sources["oav_model"] == "modeled:natural_constituent_composite"
    check = _natural_composite_coverage_check(state)
    assert check.status == "WARN"
