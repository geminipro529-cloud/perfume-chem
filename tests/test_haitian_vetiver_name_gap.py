"""The inventory name "Haitian Vetiver EO" must reach the same physics as "Vetiver EO (Haiti)".

Before the alias, a formula that used the inventory's own spelling had no molecular weight,
vapour pressure or air odor threshold for that row, so the simulator could not smell it.
The Oman frankincense tincture is a different product with no data of its own; it must stay
a hold and must not borrow a resinoid's or an essential oil's numbers.
"""

from __future__ import annotations

from engine.pipeline import simulator


def _material(name: str):
    frame = simulator.simulate_formula({name: 100.0, "Linalool": 100.0}, {name: 1.0, "Linalool": 1.0})[0]
    return next(m for m in frame.state.materials if m.name == name)


def test_haitian_vetiver_inventory_name_has_the_physics_of_its_other_spelling():
    inventory_spelling = _material("Haitian Vetiver EO")
    other_spelling = _material("Vetiver EO (Haiti)")
    for field in ("mw_g_mol", "vp_pure_pa", "odt_air_ppm"):
        assert getattr(inventory_spelling, field) is not None, field
        assert getattr(inventory_spelling, field) == getattr(other_spelling, field), field
    assert not {"mw", "vp", "odt_air_ppm"} & set(inventory_spelling.missing_fields)


def test_oman_frankincense_tincture_stays_a_hold():
    tincture = _material("Oman Frankincense Ethanol Tincture")
    assert tincture.mw_g_mol is None
    assert tincture.vp_pure_pa is None
    assert tincture.odt_air_ppm is None
