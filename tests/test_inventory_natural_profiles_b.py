"""Proxy constituent profiles for owned florals and Peru balsam (batch B)."""

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_MAG = "michelia alba flower oil zhu 1993 literature profile"
_CHA = "champaca flower oil perfumersworld 7nj07740 ifra declaration profile"
_PERU = "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile"

_NEW_PROXIES = {
    "Magnolia EO": (_MAG, 0.8586),
    "Champaca Flower EO": (_CHA, 0.569473),
    "Peru Balsam Resinoid": (_PERU, 0.268851),
    "Peru Balsam Resinoid (50% w/w in DEP)": (_PERU, 0.268851),
    "Peru Balsam 10%": (_PERU, 0.268851),
}


@pytest.mark.parametrize("label", sorted(_NEW_PROXIES))
def test_stock_label_resolves_to_a_partial_labelled_proxy(label):
    key, characterized = _NEW_PROXIES[label]
    meta = get_composite_metadata(label)
    assert meta is not None
    assert meta.profile_key == key
    assert meta.resolution == "literature_proxy"
    assert meta.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert meta.batch_specific is False
    assert meta.characterized_fraction == pytest.approx(characterized)
    assert meta.unresolved_fraction == pytest.approx(1.0 - characterized)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert meta.input_authority["composition"]["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
    assert all(s.startswith("https://") for s in meta.sources)


def test_magnolia_is_michelia_alba_with_doubtful_sample_type_and_minors_unresolved():
    meta = get_composite_metadata("Magnolia EO")
    rows = {row[0]: row for row in get_constituents("Magnolia EO")}
    assert rows["linalool"][1] == pytest.approx(0.7629)
    assert rows["phenylethyl alcohol"][3] == pytest.approx(11.57)
    assert meta.input_authority["composition"]["sample_type_status"].startswith("DOUBTFUL")
    unresolved = {u["name"]: u["reported_fraction"] for u in meta.unresolved_constituents}
    assert len(unresolved) == 11
    assert sum(unresolved.values()) == pytest.approx(0.0617)
    assert all(u["odor_contribution"] == "UNCOMPUTED" for u in meta.unresolved_constituents)


def test_champaca_is_a_declaration_not_a_true_champaca_absolute():
    meta = get_composite_metadata("Champaca Flower EO")
    names = {row[0] for row in get_constituents("Champaca Flower EO")}
    assert "phenylethyl alcohol" not in names and "methyl anthranilate" not in names
    composition = meta.input_authority["composition"]
    assert composition["true_champaca_absolute_rows_used"] is False
    assert composition["owned_bottle_sku_verified"] is False
    assert {u["name"] for u in meta.unresolved_constituents} == {"safrole", "L-carvone"}
    assert any("declared levels" in text for text in meta.limitations)


def test_peru_balsam_keeps_benzyl_cinnamate_unresolved_and_flags_unverified_values():
    meta = get_composite_metadata("Peru Balsam Resinoid")
    rows = {row[0]: row[1] for row in get_constituents("Peru Balsam Resinoid")}
    assert rows == pytest.approx({"benzyl benzoate": 0.268389, "eugenol": 0.0003, "coumarin": 0.000162})
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert unresolved["benzyl cinnamate"]["reported_fraction"] == pytest.approx(0.167053)
    assert meta.input_authority["composition"]["document_reverified"] is False


@pytest.mark.parametrize(
    "label",
    ["Myrrh EO", "Himalayan Cedarwood EO", "Cedarwood Himalayan EO", "Orange Blossom Absolute 10%"],
)
def test_materials_without_defensible_runtime_data_stay_unmapped(label):
    assert get_composite_metadata(label) is None


@pytest.mark.parametrize(
    "label, ul, dilution",
    [
        ("Magnolia EO", 20.0, 1.0),
        ("Champaca Flower EO", 20.0, 1.0),
        ("Peru Balsam Resinoid", 200.0, 0.5),
    ],
)
def test_headspace_model_uses_the_composite(label, ul, dilution):
    from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest

    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="t",
            ingredients_ul={label: ul, "Iso E Super": 500.0},
            batch_volume_ml=30.0,
            dilutions={label: dilution},
        )
    )
    states = [m for m in result.formula_state.materials if m.name == label]
    assert len(states) == 1
    assert states[0].sources.get("oav_model") == "modeled:natural_constituent_composite"
    assert states[0].oav is not None and states[0].oav > 0
