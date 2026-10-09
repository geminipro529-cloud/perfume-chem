"""Labelled proxy constituent profiles for owned naturals (batch A).

Basil, Tagetes and Helichrysum EO resolve to partial literature/supplier
proxies. Anise, Sandalwood, Pine and Lemon Terpeneless stay unmapped: no
defensible composition with runtime headspace inputs exists for them.
"""

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_BASIL = "ocimum basilicum oil india estragole type supplier gc profile"
_TAGETES = "tagetes minuta whole plant oil india bansal 1999 profile"
_HELICHRYSUM = "helichrysum italicum oil corsica bianchini 2001 profile"

_MAPPED = {
    "Basil EO (India, Ocimum Basilicum)": (_BASIL, 0.2045),
    "Basil EO": (_BASIL, 0.2045),
    "Basil EO ct. Methyl Chavicol": (_BASIL, 0.2045),
    "Tagetes EO (10% in DPG)": (_TAGETES, 0.114),
    "Tagetes EO": (_TAGETES, 0.114),
    "Helichrysum EO": (_HELICHRYSUM, 0.583),
}


@pytest.mark.parametrize("label", sorted(_MAPPED))
def test_stock_label_resolves_to_a_partial_labelled_proxy(label):
    key, characterized = _MAPPED[label]
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
    assert meta.sources and all(s.startswith("https://") for s in meta.sources)
    for row in meta.unresolved_constituents:
        assert row["odor_contribution"] == "UNCOMPUTED"


def test_basil_is_the_indian_estragole_gc_with_estragole_unresolved():
    meta = get_composite_metadata("Basil EO (India, Ocimum Basilicum)")
    rows = {row[0]: row for row in get_constituents("Basil EO")}
    assert rows["linalool"][1] == pytest.approx(0.1813)
    assert "estragole" not in rows
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert unresolved["estragole"]["reported_fraction"] == pytest.approx(0.7516)
    assert unresolved["estragole"]["missing_input"] == "NO_RUNTIME_HEADSPACE_INPUT"
    composition = meta.input_authority["composition"]
    assert composition["iso_11043_used"] is False
    assert any("ISO 11043" in text for text in meta.limitations)


def test_tagetes_character_ketones_stay_unresolved():
    meta = get_composite_metadata("Tagetes EO")
    names = {row[0] for row in get_constituents("Tagetes EO")}
    assert names == {"ocimene", "limonene"}
    unresolved = {u["name"]: u["reported_fraction"] for u in meta.unresolved_constituents}
    assert unresolved["dihydrotagetone"] == pytest.approx(0.487)
    assert {"(Z)-tagetone", "(E)-tagetone", "(Z)-tagetenone", "ocimenone"} <= set(unresolved)


def test_helichrysum_uses_corsica_and_records_the_croatian_conflict():
    meta = get_composite_metadata("Helichrysum EO")
    rows = {row[0]: row for row in get_constituents("Helichrysum EO")}
    assert rows["neryl acetate"][1] == pytest.approx(0.326)
    # Reuses the immortelle absolute gamma-curcumene inputs.
    absolute = {row[0]: row for row in get_constituents("immortelle absolute")}
    assert rows["gamma-curcumene"][2:] == absolute["gamma-curcumene"][2:]
    conflict = meta.input_authority["composition"]["conflicting_origin_profile"]
    assert conflict["used"] is False
    assert conflict["reported_pct"]["neryl acetate"] == pytest.approx(8.0)
    assert any("Croatian" in text for text in meta.limitations)
    assert meta.profile_key != get_composite_metadata("immortelle absolute").profile_key


@pytest.mark.parametrize(
    "label",
    ["Anise EO", "Sandalwood EO", "Pine EO", "Lemon Terpeneless Oil Sicilian"],
)
def test_materials_without_a_defensible_profile_stay_unmapped(label):
    assert get_composite_metadata(label) is None


@pytest.mark.parametrize(
    "label, ul, dilution",
    [
        ("Basil EO (India, Ocimum Basilicum)", 20.0, 1.0),
        ("Tagetes EO (10% in DPG)", 50.0, 0.1),
        ("Helichrysum EO", 20.0, 1.0),
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
