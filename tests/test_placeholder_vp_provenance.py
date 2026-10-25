"""Unsourced round registry VPs are reported as estimates, not registry data."""

import pytest

from engine.material_resolver import resolve_material, resolved_vp_25c_pa
from engine.pipeline.formula_state import _lookup_odt, build_formula_state


# Helional and Benzyl Salicylate were the examples here until 23 Oct 2026, when
# their VPs got sources (RIFM/EPI and ECHA via PubChem), and Bacdanol until
# 25 Oct 2026 (RIFM 2023 EPI estimate); the rows below are still placeholders.
@pytest.mark.parametrize(
    ("label", "value"),
    [("Amber Core", 0.001), ("Ambermax", 0.001), ("Dipropylene Glycol", 0.01)],
)
def test_placeholder_vp_keeps_its_value_but_reads_as_estimated(label, value):
    vp, source = resolved_vp_25c_pa(resolve_material(label))
    assert vp == pytest.approx(value)
    assert source.startswith("estimated:")
    assert "registry" not in source and "data_spine" not in source


@pytest.mark.parametrize(
    ("label", "value"),
    [("Cinnamaldehyde", 3.85), ("Helional", 0.1073), ("Benzyl Salicylate", 0.0104)],
)
def test_sourced_registry_vp_still_reads_as_registry_data(label, value):
    vp, source = resolved_vp_25c_pa(resolve_material(label))
    assert vp == pytest.approx(value)
    assert source == "registry:data_spine.vp_25c"


def test_formula_state_labels_placeholder_and_sourced_vps_apart():
    build_formula_state.cache_clear()
    # At the 25 C reference temperature the VP is the registry value itself.
    state = build_formula_state(
        {"Ambermax": 100.0, "Cinnamaldehyde": 100.0}, temperature_K=298.15
    )
    by_name = {material.name: material for material in state.materials}
    ambermax = by_name["Ambermax"]
    assert ambermax.vp_pure_pa == pytest.approx(0.001)
    assert ambermax.sources["vp"].startswith("estimated:")
    # Labelled, not withheld: the OAV is still computed.
    assert ambermax.oav is not None
    assert by_name["Cinnamaldehyde"].sources["vp"] == "registry:data_spine.vp_25c"


def test_supplier_spelling_couer_resolves_to_the_sourced_vertofix_coeur():
    identity = resolve_material("Vertofix Couer")
    assert identity.registry_name == "Vertofix Coeur"
    odt_ppm, source = _lookup_odt("Vertofix Couer", identity.profile, identity.registry_material)
    assert odt_ppm == pytest.approx(6.3 / 1000.0)
    assert source == "literature:peer_reviewed.odt_air"
