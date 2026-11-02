"""Elemi EO: the PerfumersWorld 7QC00902 allergen declaration and, since 31 Oct 2026, the
three-lot C. luzonicum GC/MS median that owned Elemi EO resolves to."""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.pipeline.preflight import _natural_composite_coverage_check

_ELEMI_KEY = "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile"
_ELEMI_MEDIAN_KEY = "canarium luzonicum oil three-lot gc-ms median profile"


def test_elemi_declaration_profile_keeps_declared_concentrations_without_rescaling():
    # The declaration profile is unchanged; since 31 Oct 2026 it is the median profile's
    # supplier cross-check rather than the profile owned Elemi EO resolves to.
    import engine.pipeline.natural_absolute_decomposition as nad

    fractions = {row[0]: row[1] for row in nad._ABSOLUTE_CONSTITUENTS[_ELEMI_KEY]}
    assert fractions["limonene"] == pytest.approx(0.450869)
    assert fractions["alpha terpineol"] == pytest.approx(0.030843)
    assert fractions["(R)-carvone"] == pytest.approx(0.00123)
    assert fractions["alpha-terpinene"] == pytest.approx(0.000545)
    assert sum(fractions.values()) == pytest.approx(0.496776)
    unresolved = {row["name"] for row in nad._PARTIAL_PROFILE_EVIDENCE[_ELEMI_KEY]["unresolved_constituents"]}
    assert {"elemol", "elemicin", "alpha-phellandrene"} <= unresolved


@pytest.mark.parametrize("name", ["Elemi EO", "Elemi Essential Oil"])
def test_elemi_uses_the_three_lot_median_without_rescaling(name):
    # Changed 2026-10-31 because of the new sourced profile (Acqua di Gio Luxe research, R7,
    # second-read): the owned oil resolves to the median of three full C. luzonicum GC/MS
    # tables (77.7% modeled) instead of the 49.7% allergen declaration.
    constituents = get_constituents(name)
    assert constituents is not None
    fractions = {row[0]: row[1] for row in constituents}
    assert fractions["limonene"] == pytest.approx(0.5077)
    assert fractions["alpha phellandrene"] == pytest.approx(0.1437)
    assert fractions["sabinene"] == pytest.approx(0.0452)
    assert fractions["(R)-carvone"] == pytest.approx(0.00035)
    assert fractions["alpha-terpinene"] == pytest.approx(0.0045)
    assert sum(fractions.values()) == pytest.approx(0.77735)

    metadata = get_composite_metadata(name)
    assert metadata.profile_key == _ELEMI_MEDIAN_KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.characterized_fraction == pytest.approx(0.77735)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert metadata.batch_specific is False
    assert metadata.sources and all(src.startswith("http") for src in metadata.sources)
    unresolved = {row["name"]: row for row in metadata.unresolved_constituents}
    assert set(unresolved) == {"elemol", "elemicin"}
    assert unresolved["elemol"]["reported_fraction"] == pytest.approx(0.1175)
    assert unresolved["elemicin"]["reported_fraction"] == pytest.approx(0.0404)
    declared = metadata.input_authority["composition"]["supplier_declaration_cross_check"]
    assert declared["declared_pct"]["limonene"] == pytest.approx(45.0869)


def test_elemi_gum_is_not_mapped_to_the_oil_declaration():
    assert get_constituents("Elemi Gum") is None


def test_elemi_is_modeled_but_still_warns_as_partial():
    state = build_formula_state({"Elemi EO": 15.0, "Hedione": 900.0})
    elemi = next(row for row in state.materials if row.name == "Elemi EO")
    assert elemi.oav is not None
    assert elemi.sources["oav_model"] == "modeled:natural_constituent_composite"
    check = _natural_composite_coverage_check(state)
    assert check.status == "WARN"
