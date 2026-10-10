"""Proxy constituent profiles for Rose Otto, Haitian vetiver and hay absolute (batch D)."""

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_ROSE = "rosa x damascena bulgarian oil iso 9842 midpoint profile"
_VET = "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile"
_HAY = "hay absolute perfumersworld 8ny00523 allergen declaration profile"

_NEW_PROXIES = {
    "Rose Otto Bulgarian": (_ROSE, 0.715),
    "Rose Otto Bulgarian (10% in DPG)": (_ROSE, 0.715),
    "Haitian Vetiver EO": (_VET, 0.3468),
    "Haitian Vetiver EO (neat / as supplied)": (_VET, 0.3468),
    "Hay Absolute": (_HAY, 0.017775),
    "Hay Absolute (10% w/w in DPG; homogeneous)": (_HAY, 0.017775),
    "Hay Absolute 10%": (_HAY, 0.017775),
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


def test_rose_otto_uses_iso_midpoints_and_keeps_upper_bound_only_rows_unresolved():
    meta = get_composite_metadata("Rose Otto Bulgarian")
    rows = {row[0]: row for row in get_constituents("Rose Otto Bulgarian")}
    assert {name: row[1] for name, row in rows.items()} == pytest.approx({
        "citronellol": 0.27,
        "geraniol": 0.185,
        "nerol": 0.085,
        "nonadecane": 0.115,
        "heneicosane": 0.0425,
        "heptadecane": 0.0175,
    })
    assert all(rows[a][3] == 0.0 for a in ("nonadecane", "heneicosane", "heptadecane"))
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert {"beta-phenylethanol", "ethanol"} <= set(unresolved)
    assert "reported_fraction" not in unresolved["beta-phenylethanol"]
    assert "phenylethyl alcohol" not in rows
    assert any("damascenone" in text for text in meta.limitations)
    assert get_composite_metadata("rose essential oil").profile_key != _ROSE


def test_haitian_vetiver_reuses_khusimol_and_isovalencenol_and_leaves_existing_profile():
    meta = get_composite_metadata("Haitian Vetiver EO")
    rows = {row[0]: row[1] for row in get_constituents("Haitian Vetiver EO")}
    assert rows == pytest.approx({"khusimol": 0.198, "isovalencenol": 0.1488})
    assert {u["name"] for u in meta.unresolved_constituents} == {
        "vetiselinenol", "cyclocopacamphenol", "beta-vetivenene",
    }
    assert any("Weyerstahl" in text for text in meta.limitations)
    assert get_composite_metadata("Vetiver EO").profile_key == "vetiver eo"


def test_hay_absolute_is_declared_levels_with_terpineol_as_alpha_terpineol():
    meta = get_composite_metadata("Hay Absolute")
    rows = {row[0]: row[1] for row in get_constituents("Hay Absolute")}
    assert rows == pytest.approx({
        "vanillin": 0.010262,
        "linalyl acetate": 0.005326,
        "alpha terpineol": 0.001609,
        "coumarin": 0.000578,
    })
    composition = meta.input_authority["composition"]
    assert composition["terpineol_mapping"].endswith("ALPHA_TERPINEOL_ROW")
    assert composition["owned_bottle_sku_verified"] is False
    assert any("declared levels" in text for text in meta.limitations)


def test_opoponax_stays_unmapped():
    assert get_composite_metadata("Opoponax Resinoid") is None


@pytest.mark.parametrize(
    "label, ul, dilution",
    [
        ("Rose Otto Bulgarian", 50.0, 0.1),
        ("Haitian Vetiver EO", 20.0, 1.0),
        ("Hay Absolute", 200.0, 0.1),
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
