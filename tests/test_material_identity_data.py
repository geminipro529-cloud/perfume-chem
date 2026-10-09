"""Labels that resolve to one material identity get that identity's ODT."""

from pathlib import Path

import pytest

from engine.material_resolver import resolve_material
from engine.pipeline.formula_state import _lookup_odt


def _gate_odt(label: str) -> tuple[float | None, str]:
    identity = resolve_material(label)
    return _lookup_odt(label, identity.profile, identity.registry_material)


@pytest.mark.parametrize("label", ["Vertofix", "Vertofix Coeur", "vertofix coeur"])
def test_vertofix_labels_share_the_sourced_methyl_cedryl_ketone_odt(label: str) -> None:
    assert resolve_material(label).registry_name == "Vertofix Coeur"
    odt_ppm, source = _gate_odt(label)
    assert odt_ppm == pytest.approx(6.3 / 1000.0)
    # The value comes from the identity's sourced ODT entry, not a profile copy.
    assert source == "literature:peer_reviewed.odt_air"


@pytest.mark.parametrize("label", ["Vertofix Coeur (neat)", "Vertofix (neat)"])
def test_vertofix_stock_labels_get_the_same_odt(label: str) -> None:
    odt_ppm, _source = _gate_odt(label)
    assert odt_ppm == pytest.approx(6.3 / 1000.0)


def test_stock_label_with_dilution_suffix_uses_its_identity_odt() -> None:
    assert resolve_material("Anisaldehyde 10%").registry_name == "Anisaldehyde"
    assert _gate_odt("Anisaldehyde 10%") == _gate_odt("Anisaldehyde")


def test_aldehyde_c12_mna_vapour_pressure_is_the_cited_value():
    # Merck states 1.0 Pa at 20 C for 2-methylundecanal; the registry keeps it adjusted
    # to 25 C. The old 0.01 Pa placeholder made this diffusive aldehyde a base note.
    import yaml

    from engine.ingredient_intelligence import _PROFILES
    from engine.pipeline.formula_state import build_formula_state

    registry = Path(__file__).resolve().parents[1] / "data" / "materials" / "A.yaml"
    rows = yaml.safe_load(registry.read_text(encoding="utf-8"))
    [row] = [r for r in rows if r.get("canonical_name") == "Aldehyde C12 MNA"]
    assert row["vp_25c_pa"] == 1.5
    assert row["vp_source"] == "supplier_physical_data_20c_adjusted"
    assert _PROFILES["Aldehyde C12 MNA"]["vp"] == row["vp_25c_pa"]

    ingredients = {"Aldehyde C12 MNA": 10.0, "Hedione": 500.0}
    state = build_formula_state(ingredients, {n: 1.0 for n in ingredients}, batch_volume_ml=30.0)
    [mna] = [m for m in state.materials if m.name == "Aldehyde C12 MNA"]
    assert mna.vp_pure_pa / mna.vp_temperature_factor == pytest.approx(1.5)
