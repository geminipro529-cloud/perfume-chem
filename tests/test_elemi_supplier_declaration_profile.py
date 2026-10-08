"""Elemi EO modeled from the PerfumersWorld 7QC00902 allergen declaration."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.pipeline.preflight import _natural_composite_coverage_check

_ELEMI_KEY = "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile"


@pytest.mark.parametrize("name", ["Elemi EO", "Elemi Essential Oil"])
def test_elemi_uses_declared_concentrations_without_rescaling(name):
    constituents = get_constituents(name)
    assert constituents is not None
    fractions = {row[0]: row[1] for row in constituents}
    assert fractions["limonene"] == pytest.approx(0.450869)
    assert fractions["alpha terpineol"] == pytest.approx(0.030843)
    assert sum(fractions.values()) == pytest.approx(0.495001)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _ELEMI_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.495001)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"] for row in metadata.unresolved_constituents}
    assert {"carvone", "elemol", "elemicin", "alpha-phellandrene"} <= unresolved


def test_elemi_gum_is_not_mapped_to_the_oil_declaration():
    assert get_constituents("Elemi Gum") is None


def test_elemi_is_modeled_but_still_warns_as_partial():
    state = build_formula_state({"Elemi EO": 15.0, "Hedione": 900.0})
    elemi = next(row for row in state.materials if row.name == "Elemi EO")
    assert elemi.oav is not None
    assert elemi.sources["oav_model"] == "modeled:natural_constituent_composite"
    check = _natural_composite_coverage_check(state)
    assert check.status == "WARN"
