"""Labels that resolve to one material identity get that identity's ODT."""

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
