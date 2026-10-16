"""MySkinRecipes order 2199302 stocks linked to existing engine data (2026-10-16).

Kenny chose "Link them" on the card: the Isoraldeines join the methyl ionone IFRA
group, Cedarwood Texas, Geranium Bourbon and Sweet Orange use the engine's existing
data, and the Methyl Ionone catalogue CAS is corrected. Each link keeps the stock's
own name; none of them becomes an alias of another stock.
"""

import json
from pathlib import Path

import pytest

from engine.identity.resolver import _NON_EQUIVALENT_PAIRS
from engine.ifra_standards import load_ifra_table
from engine.ingredient_intelligence import get_profile
from engine.material_resolver import resolve_material
from engine.odor_thresholds import lookup_odt_entry, lookup_odt_raw_name
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_safety
from engine.pipeline.natural_absolute_decomposition import _resolve_profile_key

ROOT = Path(__file__).resolve().parents[1]
TABLE = load_ifra_table()
LINKED = (
    "Isoraldeine 95",
    "Isoraldeine 70",
    "Cedarwood Texas EO",
    "Geranium Bourbon Essential Oil",
    "Sweet Orange Essential Oil",
)


def _gate(ingredients):
    state = build_formula_state(
        ingredients, {name: 1.0 for name in ingredients}, batch_volume_ml=30.0
    )
    return _gate_safety(state, ReleaseGateConfig(batch_volume_source="title"))


@pytest.mark.parametrize("name", LINKED)
def test_each_linked_stock_has_its_own_ifra_row(name):
    material = TABLE.lookup(name)
    assert material is not None
    assert material.name == name


@pytest.mark.parametrize("name", ("Isoraldeine 95", "Isoraldeine 70"))
def test_isoraldeines_are_methyl_ionones_but_not_aimi(name):
    material = TABLE.lookup(name)
    assert material.status == "restricted"
    assert material.standard == "IFRA_STD_063"
    assert material is not TABLE.lookup("Alpha Isomethyl Ionone")


def test_isoraldeines_count_toward_the_methyl_ionone_group_total():
    gate = _gate({"Isoraldeine 95": 10.0, "Isoraldeine 70": 10.0, "Methyl Ionone Pure": 10.0})
    assert gate.status != "HOLD"
    group = next(g for g in gate.data["groups"] if "methyl_ionones_total" in g["message"])
    for name in ("Isoraldeine 95", "Isoraldeine 70", "Methyl Ionone Pure"):
        assert name in group["message"]


@pytest.mark.parametrize(
    "name,ncs,substance",
    [
        ("Cedarwood Texas EO", "Cedarwood oil, Texas", "Cedrene"),
        ("Geranium Bourbon Essential Oil", "Geranium oil", "Geraniol"),
        ("Geranium Bourbon Essential Oil", "Geranium oil", "Citronellol"),
        ("Sweet Orange Essential Oil", "Orange peel, sweet oil", "Citral"),
    ],
)
def test_naturals_count_their_annex_constituents(name, ncs, substance):
    gate = _gate({name: 10.0})
    assert gate.status != "HOLD"
    total = next(t for t in gate.data["constituent_totals"] if t["substance"] == substance)
    assert any(c["material"] == name and c["ncs_name"] == ncs for c in total["contributors"])


@pytest.mark.parametrize(
    "name,proxy",
    [
        ("Geranium Bourbon Essential Oil", "geranium eo"),
        ("Sweet Orange Essential Oil", "orange peel eo"),
        ("Cedarwood Texas EO", "cedarwood eo"),
    ],
)
def test_naturals_use_the_existing_composition_profile_as_a_proxy(name, proxy):
    assert _resolve_profile_key(name) == (proxy, "literature_proxy")


@pytest.mark.parametrize("name", ("Isoraldeine 95", "Isoraldeine 70"))
def test_isoraldeines_share_the_methyl_ionone_gamma_odt_row(name):
    assert lookup_odt_entry(name) is not None
    assert lookup_odt_raw_name(name) == lookup_odt_raw_name("Methyl Ionone Gamma")


@pytest.mark.parametrize("name", ("Isoraldeine 95", "Isoraldeine 70", "Cedarwood Texas EO"))
def test_linked_stocks_have_their_own_physics_profile(name):
    assert resolve_material(name).is_known
    profile = get_profile(name)
    assert profile is not None
    assert profile.name == name
    assert profile.mw and profile.vp and profile.clogp


def test_isoraldeine_95_uses_the_givaudan_vapour_pressure():
    assert get_profile("Isoraldeine 95").vp == pytest.approx(0.80)


def test_isoraldeine_stays_apart_from_aimi_in_the_identity_resolver():
    assert ("isoraldeine 95", "alpha-isomethyl ionone") in _NON_EQUIVALENT_PAIRS
    assert get_profile("Isoraldeine 95").name != get_profile("Alpha-Isomethyl Ionone").name


def test_methyl_ionone_catalogue_cas_no_longer_calls_beta_n_gamma():
    catalog = (ROOT / "data/knowledge_graph/ingredient_catalog.json").read_text(encoding="utf-8")
    assert "127-43-5 (gamma)" not in catalog
    props = json.loads(
        (ROOT / "data/knowledge_graph/material_properties.json").read_text(encoding="utf-8")
    )
    text = json.dumps(props)
    assert "127-43-5 (gamma)" not in text
    assert "127-43-5 (beta); 127-51-5 (gamma)" in text
