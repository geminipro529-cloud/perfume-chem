"""Proxy constituent profiles for owned naturals used by the Dior Homme Parfum work."""

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_NEW_PROXIES = {
    "Cinnamon Bark EO - Telvada USDA Organic (neat)": (
        "cinnamomum zeylanicum bark oil sri lanka supplier coa profile",
        0.9235,
    ),
    "Cinnamon Bark EO (Telvada)": (
        "cinnamomum zeylanicum bark oil sri lanka supplier coa profile",
        0.9235,
    ),
    "Lavandin Absolute (neat / as supplied)": (
        "lavandula x intermedia supercritical co2 extract pellerin 1991 profile",
        0.523,
    ),
    "Ambrette Seed Absolute (10% in DPG)": (
        "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile",
        0.1881,
    ),
    "Orris Concrete Orris Butter (10% in DPG)": (
        "iris rhizome concrete 8 pct irone low grade scenario profile",
        0.805,
    ),
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
    assert all(s.startswith(("http", "amrita.net", "Pellerin")) for s in meta.sources)


def test_siam_benzoin_stock_label_reaches_the_existing_siam_profile():
    for label in ("Siam Benzoin", "Siam Benzoin (50% w/w in DPG)"):
        meta = get_composite_metadata(label)
        assert meta is not None and meta.profile_key == "benzoin siam resinoid"
        assert get_constituents(label) == get_constituents("benzoin siam resinoid")


def test_cinnamon_is_a_bark_profile_with_cinnamyl_acetate_unresolved():
    meta = get_composite_metadata("Cinnamon Bark EO (Telvada)")
    names = {row[0]: row[1] for row in get_constituents("Cinnamon Bark EO (Telvada)")}
    assert names["cinnamaldehyde"] == pytest.approx(0.7971)
    assert names["eugenol"] == pytest.approx(0.06)
    assert meta.input_authority["composition"]["leaf_oil_rows_used"] is False
    assert [u["name"] for u in meta.unresolved_constituents] == ["(E)-cinnamyl acetate"]


def test_lavandin_keeps_unknown_remainder_and_states_co2_non_equivalence():
    meta = get_composite_metadata("Lavandin Absolute")
    names = {row[0] for row in get_constituents("Lavandin Absolute")}
    assert {"linalyl acetate", "linalool", "coumarin"} <= names
    assert "herniarin" not in names
    unresolved = {u["name"] for u in meta.unresolved_constituents}
    assert unresolved == {"herniarin", "beta-caryophyllene + alpha-humulene"}
    assert any("CO2" in text and "non-equivalent" in text for text in meta.limitations)
    assert meta.input_authority["composition"]["owned_extraction_matches_source"] is False


def test_ambrette_models_ambrettolide_and_leaves_farnesyl_acetate_unresolved():
    meta = get_composite_metadata("Ambrette Seed Absolute")
    rows = {row[0]: row for row in get_constituents("Ambrette Seed Absolute")}
    assert rows["ambrettolide"][1] == pytest.approx(0.1296)
    assert rows["linoleic acid"][3] == 0.0  # non-volatile mass row
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert unresolved["farnesyl acetate"]["reported_fraction"] == pytest.approx(0.5145)
    assert unresolved["farnesyl acetate"]["odor_contribution"] == "UNCOMPUTED"
    assert any("seed OIL" in text for text in meta.limitations)
    assert any("isomer" in text for text in meta.limitations)


def test_orris_butter_is_the_low_irone_scenario_on_the_existing_irone_input():
    rows = {row[0]: row for row in get_constituents("Orris Concrete Orris Butter")}
    liquid = {row[0]: row for row in get_constituents("orris liquid")}
    irone = rows["irone pool (alpha-equivalent)"]
    assert irone[1] == pytest.approx(0.08)
    assert irone[2:] == liquid["irone pool (alpha-equivalent)"][2:]
    assert rows["myristic acid"][1] == pytest.approx(0.725)
    assert rows["myristic acid"][3] == 0.0
    meta = get_composite_metadata("Orris Concrete Orris Butter")
    assert meta.input_authority["composition"]["owned_grade_irone_pct_known"] is False
    assert any("conservative scenario" in text for text in meta.limitations)


@pytest.mark.parametrize(
    "label, ul, dilution",
    [
        ("Cinnamon Bark EO (Telvada)", 20.0, 1.0),
        ("Lavandin Absolute", 40.0, 1.0),
        ("Ambrette Seed Absolute", 100.0, 0.1),
        ("Orris Concrete Orris Butter", 700.0, 0.1),
        ("Siam Benzoin", 100.0, 0.5),
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
