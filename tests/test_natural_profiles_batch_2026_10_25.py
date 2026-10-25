"""Natural profiles batch (Kenny, 25 Oct 2026, stock thread: "parse all the information
that is missing into the engine").

Four unsourced natural profiles (Black Pepper EO, Lime Distilled EO, Rose Essential Oil,
Rose de Mai Absolute) are replaced by published or certificate compositions, and four owned
stocks with no profile (Cabreuva, Pine, Sandalwood, Tuberlia) get labelled partial ones.
Every composition was re-opened by a second reader. These pin the data and its sources;
they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_CABREUVA = "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile"
_PINE = "pine oil perfumersworld 7kq07511 ifra declaration profile"
_SANDALWOOD = "santalum album oil iso 3518 midpoint profile"
_TUBERLIA = "tuberalia base perfumersworld 6nd09663 declaration profile"

_LABELS = {
    "Black Pepper EO": ("black pepper eo", 0.7301, "direct_identity"),
    "Lime Distilled EO": ("lime distilled eo", 0.851856, "direct_identity"),
    "Rose Essential Oil (Rosa Damascena, India)": ("rose essential oil", 0.8179, "normalized_identity"),
    "Rose de Mai Absolute": ("rose de mai absolute", 0.4804, "direct_identity"),
    "Cabreuva EO 50% in DPG": (_CABREUVA, 0.070497, "literature_proxy"),
    "Cabreuva EO": (_CABREUVA, 0.070497, "literature_proxy"),
    "Pine EO": (_PINE, 0.028407, "literature_proxy"),
    "Sandalwood EO": (_SANDALWOOD, 0.68, "literature_proxy"),
    "Sandalwood EO (10% in DPG)": (_SANDALWOOD, 0.68, "literature_proxy"),
    "Tuberlia Base": (_TUBERLIA, 0.236503, "literature_proxy"),
}

_SOURCES = {
    "Black Pepper EO": "https://doi.org/10.1016/j.talanta.2014.01.007",
    "Lime Distilled EO": "https://www.tomsic.co.jp/wp-content/themes/tomsic/images/product/mega/32.pdf",
    "Rose Essential Oil (Rosa Damascena, India)": (
        "https://asianpubs.org/index.php/ajchem/article/download/18212/18162/18291"
    ),
    "Rose de Mai Absolute": "https://www.planttherapy.com/cdn/shop/files/Rose_R30111.pdf",
    "Cabreuva EO": "https://www.perfumersworld.com/document-list.php?pro_id=7LW00863",
    "Pine EO": "https://www.perfumersworld.com/document-list.php?pro_id=7KQ07511",
    "Sandalwood EO": (
        "https://cdn.standards.iteh.ai/sist-preview/88588/1b7516dd3de5489a8752a4f51f66838c/"
        "ISO-3518-2025.pdf"
    ),
    "Tuberlia Base": "https://www.perfumersworld.com/document-list.php?pro_id=6ND09663",
}


def _rows(label):
    return {row[0]: row for row in get_constituents(label)}


@pytest.mark.parametrize("label", sorted(_LABELS))
def test_owned_label_resolves_to_a_sourced_partial_profile(label):
    key, characterized, resolution = _LABELS[label]
    meta = get_composite_metadata(label)
    assert meta is not None
    assert meta.profile_key == key
    assert meta.resolution == resolution
    assert meta.characterized_fraction == pytest.approx(characterized)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert meta.input_authority["composition"]["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
    assert all(source.startswith("https://") for source in meta.sources)
    assert "repository:legacy_literature_profile" not in meta.sources


@pytest.mark.parametrize("label", sorted(_SOURCES))
def test_profile_cites_its_composition_source(label):
    meta = get_composite_metadata(label)
    assert meta.sources[0] == _SOURCES[label]
    assert meta.input_authority["composition"]["source"] == _SOURCES[label]


def test_black_pepper_is_the_hydrodistilled_bagheri_oil():
    rows = {name: row[1] for name, row in _rows("Black Pepper EO").items()}
    assert rows == pytest.approx({
        "beta-caryophyllene": 0.1864,
        "limonene": 0.1495,
        "sabinene": 0.1319,
        "beta pinene": 0.0971,
        "delta-3-carene": 0.0856,
        "alpha pinene": 0.0796,
    })
    declared = get_composite_metadata("Black Pepper EO").input_authority["composition"][
        "supplier_declaration_not_modeled"
    ]
    assert declared["declared_pct"]["d-limonene"] == pytest.approx(20.816)


def test_lime_uses_mexican_midpoints_and_the_owned_sku_citral():
    rows = _rows("Lime Distilled EO")
    assert rows["limonene"][1] == pytest.approx(0.41365)
    assert rows["gamma terpinene"][1] == pytest.approx(0.09725)
    assert rows["1,8-cineole"][1] == pytest.approx(0.073)
    assert rows["citral"][1] == pytest.approx(0.007556)
    # alpha-terpinene: NIST mass, FMA 66.66 Pa at 20 C converted to 25 C, Cometto-Muniz 1998.
    assert rows["alpha-terpinene"][1:] == pytest.approx((0.01885, 136.234, 96.6, 1418.0, 3.0))
    assert "neral" not in rows and "geranial" not in rows
    meta = get_composite_metadata("Lime Distilled EO")
    unresolved = {u["name"]: u.get("reported_fraction") for u in meta.unresolved_constituents}
    assert unresolved["1,4-cineole"] == pytest.approx(0.02825)
    assert unresolved["(E,E)-alpha-farnesene"] == pytest.approx(0.0178)
    assert len(unresolved) == 8


def test_rose_oil_india_uses_north_indian_midpoints():
    rows = _rows("Rose Essential Oil (Rosa Damascena, India)")
    assert rows["geraniol"][1] == pytest.approx(0.2561)
    assert rows["citronellol"][1] == pytest.approx(0.21975)
    assert rows["nerol"][1] == pytest.approx(0.10315)
    # Stearoptene alkanes carry mass only.
    for alkane, mw in (("nonadecane", 268.5), ("heneicosane", 296.58), ("eicosane", 282.55)):
        assert rows[alkane][2:4] == (mw, 0.0)
    assert rows["rose oxide"][1] == pytest.approx(0.00405)
    meta = get_composite_metadata("Rose Essential Oil (Rosa Damascena, India)")
    assert [u["name"] for u in meta.unresolved_constituents] == ["alpha-humulene"]


def test_rose_de_mai_is_the_phytochemia_mass_fraction_certificate():
    rows = _rows("Rose de Mai Absolute")
    assert rows["phenylethyl alcohol"][1:] == pytest.approx((0.3068, 122.16, 11.57, 26.0, 0.7))
    assert rows["citronellol"][1] == pytest.approx(0.086)
    assert rows["methyl eugenol"][1] == pytest.approx(0.0011)
    assert "beta-damascenone" not in rows and "linalool" not in rows
    meta = get_composite_metadata("Rose de Mai Absolute")
    composition = meta.input_authority["composition"]
    assert composition["consolidated_total_pct_m_m"] == pytest.approx(53.42)
    assert composition["basis_to_mass_conversion"] == "REPORTED_AS_MASS_FRACTION"
    assert {u["name"] for u in meta.unresolved_constituents} == {
        "docosene isomer",
        "unknown oxygenated triterpene",
        "tetradecyl nonanoate",
        "nonadecene (9Z)",
        "pentadecyl octanoate",
    }


def test_cabreuva_keeps_nerolidol_unresolved():
    rows = {name: row[1] for name, row in _rows("Cabreuva EO 50% in DPG").items()}
    assert rows["alpha-bisabolol"] == pytest.approx(0.046708)
    assert rows["farnesol"] == pytest.approx(0.021867)
    assert "nerolidol" not in rows and "(E)-nerolidol" not in rows
    meta = get_composite_metadata("Cabreuva EO 50% in DPG")
    nerolidol = meta.unresolved_constituents[0]
    assert nerolidol["name"] == "(E)-nerolidol"
    assert nerolidol["reported_fraction"] == pytest.approx(0.6454)


def test_pine_is_the_owned_batch_declaration_only():
    assert {name: row[1] for name, row in _rows("Pine EO").items()} == pytest.approx(
        {"limonene": 0.028407}
    )
    meta = get_composite_metadata("Pine EO")
    assert meta.unresolved_constituents[0]["name"] == "longifolene"
    assert meta.unresolved_constituents[0]["reported_fraction"] == pytest.approx(0.088795)
    assert meta.input_authority["composition"]["supplier_species_stated"] is False


def test_sandalwood_santalols_carry_their_cited_physics():
    rows = _rows("Sandalwood EO")
    assert rows["(Z)-alpha-santalol"][1:] == pytest.approx((0.48, 220.35, 0.004506, 0.8211, 0.5))
    assert rows["(Z)-beta-santalol"][1:] == pytest.approx((0.2, 220.35, 0.009826, 0.05992, 0.5))
    meta = get_composite_metadata("Sandalwood EO")
    authority = meta.input_authority["(Z)-beta-santalol"]
    assert authority["vp_status"] == "ESTIMATE_EPI_SUITE_V4_11_AS_PRINTED_BY_RIFM"
    ranges = {u["name"]: u.get("reported_fraction_range") for u in meta.unresolved_constituents}
    assert ranges["(Z)-lanceol"] == (0.0, 0.05)
    assert ranges["(E,E)-farnesol"] == (0.0, 0.01)


def test_tuberlia_models_declared_levels_and_leaves_sds_bands_unresolved():
    rows = {name: row[1] for name, row in _rows("Tuberlia Base").items()}
    assert rows == pytest.approx({
        "linalool": 0.087605,
        "hydroxycitronellal": 0.067878,
        "benzyl salicylate": 0.049065,
        "eugenol": 0.016008,
        "benzyl benzoate": 0.009623,
        "benzyl alcohol": 0.006324,
    })
    meta = get_composite_metadata("Tuberlia Base")
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert unresolved["benzyl acetate"]["missing_input"] == "SDS_BAND_ONLY_NO_NOMINAL_FRACTION"
    assert unresolved["hexyl salicylate"]["reported_fraction"] == pytest.approx(0.006406)


def test_nothing_is_renormalized():
    for label, (_key, characterized, _resolution) in _LABELS.items():
        assert sum(row[1] for row in get_constituents(label)) == pytest.approx(characterized)
        assert characterized < 1.0


@pytest.mark.parametrize(
    "name, dilution",
    [
        ("Cabreuva EO", 0.5),
        ("Pine EO", 1.0),
        ("Sandalwood EO", 0.1),
        ("Tuberlia Base", 1.0),
    ],
)
def test_new_profiles_make_the_stock_oav_available(name, dilution):
    state = build_formula_state({name: 100.0, "Hedione": 900.0}, {name: dilution})
    material = next(row for row in state.materials if row.name == name)
    assert material.oav is not None
    assert material.natural_composite_metadata["quantitative_evaluability"] == "PARTIAL_INPUT_COVERAGE"
