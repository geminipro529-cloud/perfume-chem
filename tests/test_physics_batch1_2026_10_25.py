"""Physics data batch 1 (Kenny, 25 Oct 2026, stock thread: "Plan a fix for the physics data").

Five owned stocks the release gate could not judge, or judged on wrong numbers:
Orange Flower Absolute, Frangipani Absolute and Fir EO get constituent profiles; Rhodinol
and Bacdanol get their own molecular weight, vapour pressure and log P. These pin the data
and its sources; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import _gate_data_coverage
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_ORANGE = "orange flower absolute perfumersworld 8nc00338 declaration profile"
_FRANG = "frangipani absolute perfumersworld 8on00534 declaration profile"
_FIR = "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile"

_LABELS = {
    "Orange Flower Absolute": (_ORANGE, 0.1514),
    "Orange Flower Absolute 10% in DPG": (_ORANGE, 0.1514),
    "Frangipani Absolute": (_FRANG, 0.122353),
    "Frangipani Absolute (10% in DPG)": (_FRANG, 0.122353),
    "Fir Essential Oil": (_FIR, 0.779023),
    "Fir EO 10%": (_FIR, 0.779023),
}


@pytest.mark.parametrize("label", sorted(_LABELS))
def test_owned_label_resolves_to_a_partial_labelled_profile(label):
    key, characterized = _LABELS[label]
    meta = get_composite_metadata(label)
    assert meta is not None
    assert meta.profile_key == key
    assert meta.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert meta.characterized_fraction == pytest.approx(characterized)
    assert meta.unresolved_fraction == pytest.approx(1.0 - characterized)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert all(source.startswith("https://") for source in meta.sources)


def test_orange_flower_is_pw_declared_levels_only():
    rows = {row[0]: row[1] for row in get_constituents("Orange Flower Absolute")}
    assert rows == pytest.approx({"linalool": 0.142295, "geraniol": 0.007383, "limonene": 0.001722})
    meta = get_composite_metadata("Orange Flower Absolute")
    unresolved = {u["name"]: u["reported_fraction"] for u in meta.unresolved_constituents}
    assert unresolved["benzyl cyanide"] == pytest.approx(0.004962)
    assert unresolved["7-methoxycoumarin"] == pytest.approx(0.000017)
    assert "farnesol" not in rows and "indole" not in rows


def test_frangipani_is_pw_declared_levels_only():
    rows = {row[0]: row[1] for row in get_constituents("Frangipani Absolute (10% in DPG)")}
    assert set(rows) == {
        "benzyl salicylate", "benzyl benzoate", "linalool", "citronellol", "benzyl alcohol", "citral",
    }
    assert rows["benzyl salicylate"] == pytest.approx(0.090958)
    assert rows["benzyl benzoate"] == pytest.approx(0.016552)


def test_fir_keeps_pw_limonene_and_takes_producer_midpoints_for_the_main_terpenes():
    rows = {row[0]: row[1] for row in get_constituents("Fir Essential Oil")}
    assert rows["limonene"] == pytest.approx(0.063682)
    assert rows["beta pinene"] == pytest.approx(0.33)
    assert rows["alpha pinene"] == pytest.approx(0.165)
    assert rows["delta-3-carene"] == pytest.approx(0.09)
    assert rows["bornyl acetate"] == pytest.approx(0.07)
    composition = get_composite_metadata("Fir Essential Oil").input_authority["composition"]
    assert composition["species_asserted_by_supplier"] is False


@pytest.mark.parametrize(
    "name, mw, logp",
    [("Bacdanol", 208.34, 4.54), ("Rhodinol", 156.27, 3.63)],
)
def test_single_molecules_carry_their_own_physics(name, mw, logp):
    material = build_formula_state({name: 1000.0}, {name: 1.0}).materials[0]
    assert material.mw_g_mol == pytest.approx(mw)
    assert material.logp == pytest.approx(logp)
    assert material.vp_pure_pa is not None
    assert not {"mw", "vp", "logp"} & set(material.missing_fields)


@pytest.mark.parametrize(
    "name, dilution",
    [
        ("Orange Flower Absolute", 0.1),
        ("Frangipani Absolute", 0.1),
        ("Fir Essential Oil", 0.1),
        ("Rhodinol", 1.0),
        ("Bacdanol", 1.0),
    ],
)
def test_the_physics_data_gate_no_longer_fails(name, dilution):
    state = build_formula_state({name: 1000.0}, {name: dilution})
    assert _gate_data_coverage(state).status != "FAIL"
