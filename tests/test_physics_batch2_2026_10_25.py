"""Physics data batch 2 (Kenny, 25 Oct 2026, stock thread: "find the next missing information").

Lemon Terpeneless Oil Sicilian gets a labelled partial profile (citral at the British
Pharmacopoeia grade midpoint). Rum Ether takes its density from the owned lot's COA.
Ginger Lily Oil gets the identity record the gate was missing, with its physics still held.
Mate Absolute stays held, with what was checked written down. These pin the data and its
sources; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.material_resolver import resolve_material
from engine.pipeline import gates
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_LEMON = "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile"


@pytest.mark.parametrize(
    "label", ["Lemon Terpeneless Oil Sicilian", "Lemon Terpeneless Oil Sicilian (neat / as supplied)"]
)
def test_lemon_terpeneless_is_citral_at_the_bp_grade_midpoint(label):
    assert {row[0]: row[1] for row in get_constituents(label)} == pytest.approx({"citral": 0.45})
    meta = get_composite_metadata(label)
    assert meta is not None
    assert meta.profile_key == _LEMON
    assert meta.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert meta.characterized_fraction == pytest.approx(0.45)
    assert meta.unresolved_fraction == pytest.approx(0.55)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert "https://www.sciencedirect.com/topics/medicine-and-dentistry/lemon-oil" in meta.sources
    assert "https://www.perfumersworld.com/document-list.php?pro_id=7CC24027" in meta.sources
    assert all(source.startswith("https://") for source in meta.sources)


def test_lemon_terpeneless_records_the_ifra_certificate_conflict_and_keeps_the_ifra_hold():
    from engine.pipeline.natural_absolute_decomposition import _PARTIAL_PROFILE_EVIDENCE

    composition = _PARTIAL_PROFILE_EVIDENCE[_LEMON]["input_authority"]["composition"]
    assert composition["reported_range_pct"] == {"citral": (40.0, 50.0)}
    assert composition["pharmacopoeia_read_directly"] is False
    assert "25%" in composition["supplier_ifra_certificate_conflict"]
    state = build_formula_state({"Lemon Terpeneless Oil Sicilian": 80.0, "Hedione": 920.0})
    assert gates._gate_safety(state, gates.ReleaseGateConfig()).status == "HOLD"


def test_lemon_terpeneless_passes_the_physics_gate_and_uses_pw_density():
    state = build_formula_state({"Lemon Terpeneless Oil Sicilian": 1000.0})
    material = state.materials[0]
    assert material.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert material.oav is not None
    assert gates._gate_data_coverage(state).status == "PASS"
    registry = resolve_material("Lemon Terpeneless Oil Sicilian").registry_material
    assert registry.density_25c_g_ml == pytest.approx(0.891 * 0.99705, abs=5e-4)
    assert "7CC24027 MSDS" in registry.provenance["density_25c_g_ml"]


def test_rum_ether_density_is_the_owned_lot_coa_midpoint_and_composition_stays_held():
    registry = resolve_material("Rum Ether").registry_material
    assert registry.density_25c_g_ml == pytest.approx((0.8644 + 0.8804) / 2, abs=5e-4)
    assert "QI71T6" in registry.provenance["density_25c_g_ml"]
    assert registry.mw_g_mol is None and registry.vp_25c_pa is None
    assert get_composite_metadata("Rum Ether") is None
    state = build_formula_state({"Rum Ether": 1000.0})
    assert gates._gate_data_coverage(state).status == "FAIL"


def test_ginger_lily_has_an_identity_record_and_its_physics_stay_held():
    identity = resolve_material("Ginger Lily Oil")
    assert identity.registry_name == "Ginger Lily Oil"
    registry = identity.registry_material
    assert registry.supplier.perfumersworld_sku == "7NS25173"
    assert registry.cas is None and registry.mw_g_mol is None and registry.vp_25c_pa is None
    assert "Proprietary Perfume Compound" in registry.notes
    assert get_composite_metadata("Ginger Lily Oil") is None
    state = build_formula_state({"Ginger Lily Oil": 1000.0})
    assert gates._gate_material_coverage(state).status == "PASS"
    assert gates._gate_data_coverage(state).status == "FAIL"
    mixed = build_formula_state({"Ginger Lily Oil": 80.0, "Hedione": 920.0})
    assert gates._gate_safety(mixed, gates.ReleaseGateConfig()).status == "HOLD"


def test_mate_absolute_stays_held_with_the_checked_sources_written_down():
    registry = resolve_material("Mate Absolute").registry_material
    assert "US 9434908" in registry.notes and "1604-28-0" in registry.notes
    assert get_composite_metadata("Mate Absolute") is None
    state = build_formula_state({"Mate Absolute": 1000.0}, {"Mate Absolute": 0.1})
    assert gates._gate_data_coverage(state).status == "FAIL"
