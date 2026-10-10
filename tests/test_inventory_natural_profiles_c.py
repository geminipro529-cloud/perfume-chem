"""Labelled literature proxy profiles for owned naturals (batch C)."""

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_GUAIACWOOD_KEY = "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile"
_GUAIACWOOD_LABELS = (
    "Guaiacwood EO",
    "Guaiacwood EO (exactly 1/3 w/w in ethanol + DEP; components are 1/3 "
    "Guaiacwood EO + 1/3 ethanol + 1/3 DEP by mass)",
)


@pytest.mark.parametrize("label", _GUAIACWOOD_LABELS)
def test_guaiacwood_stock_label_resolves_to_a_partial_labelled_proxy(label):
    meta = get_composite_metadata(label)
    assert meta is not None
    assert meta.profile_key == _GUAIACWOOD_KEY
    assert meta.resolution == "literature_proxy"
    assert meta.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert meta.batch_specific is False
    assert meta.characterized_fraction == pytest.approx(0.0125)
    assert meta.unresolved_fraction == pytest.approx(0.9875)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    composition = meta.input_authority["composition"]
    assert composition["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
    assert composition["reported_sum_pct"] == pytest.approx(99.39)
    assert any("redalyc.org" in source for source in meta.sources)


def test_guaiacwood_keeps_the_sesquiterpene_alcohols_unresolved_not_renormalized():
    meta = get_composite_metadata("Guaiacwood EO")
    rows = {row[0]: row for row in get_constituents("Guaiacwood EO")}
    assert set(rows) == {"alpha guaiene", "beta caryophyllene"}
    assert rows["alpha guaiene"][1] == pytest.approx(0.0067)
    assert rows["beta caryophyllene"][1] == pytest.approx(0.0058)
    # Reused tuples: the module's existing alpha-guaiene and caryophyllene inputs.
    assert rows["alpha guaiene"][2:] == (204.35, 1.00, 3.00, 1.2)
    assert rows["beta caryophyllene"][2:] == (204.35, 1.0, 10.0, 1.2)
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert set(unresolved) == {"bulnesol", "guaiol", "elemol", "alpha-gurjunene"}
    assert unresolved["bulnesol"]["reported_fraction"] == pytest.approx(0.5818)
    assert all(u["odor_contribution"] == "UNCOMPUTED" for u in unresolved.values())
    assert any("does not represent guaiacwood character" in t for t in meta.limitations)


def test_guaiacwood_headspace_model_uses_the_composite():
    from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest

    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="t",
            ingredients_ul={"Guaiacwood EO": 300.0, "Iso E Super": 500.0},
            batch_volume_ml=30.0,
            dilutions={"Guaiacwood EO": 1 / 3},
        )
    )
    states = [m for m in result.formula_state.materials if m.name == "Guaiacwood EO"]
    assert len(states) == 1
    assert states[0].sources.get("oav_model") == "modeled:natural_constituent_composite"
    assert states[0].oav is not None and states[0].oav > 0
