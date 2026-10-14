"""Stock names whose strength sits inside brackets keep a whole identity name.

"Aldehyde C-18 (Gamma Nonalactone, 10% in ethanol)" used to come out as
"Aldehyde C-18 (Gamma Nonalactone," because the strength strip cut the bracket
in half, so the stock had no physics. PerfumersWorld also sells Safranal under
the spelling "Saffranal"; that stock had an empty entry of its own.
"""

from __future__ import annotations

import pytest

from engine.inventory_parser import _identity_name
from engine.pipeline import simulator


@pytest.mark.parametrize(
    ("raw", "identity"),
    [
        ("Aldehyde C-18 (Gamma Nonalactone, 10% in ethanol)  # note", "Aldehyde C-18 (Gamma Nonalactone)"),
        ("Aldehyde C-18 (Gamma Nonalactone, neat)", "Aldehyde C-18 (Gamma Nonalactone)"),
        ("Jasmine Absolute (Jasminum grandiflorum, 10% in DPG)", "Jasmine Absolute (Jasminum grandiflorum)"),
        ("Olibanum Resinoid (viscous, 50% w/w in DPG)", "Olibanum Resinoid (viscous)"),
        ("Aldehyde C10 (1% v/v nominal in ethanol)", "Aldehyde C10"),
        ("Hexyl Acetate 1% v/v in DPG", "Hexyl Acetate"),
        ("Rosemary EO (French Rosmarinus Officinalis leaf oil)", "Rosemary EO (French Rosmarinus Officinalis leaf oil)"),
    ],
)
def test_identity_name_drops_only_the_stock_part_of_a_bracket(raw, identity):
    assert _identity_name(raw) == identity


def _material(name: str):
    frame = simulator.simulate_formula({name: 100.0, "Linalool": 100.0}, {name: 1.0, "Linalool": 1.0})[0]
    return next(m for m in frame.state.materials if m.name == name)


def test_bracketed_gamma_nonalactone_name_has_physics():
    material = _material("Aldehyde C-18 (Gamma Nonalactone)")
    reference = _material("Aldehyde C-18")
    for field in ("mw_g_mol", "vp_pure_pa", "logp"):
        assert getattr(material, field) is not None, field
        assert getattr(material, field) == getattr(reference, field), field


def test_saffranal_is_safranal():
    saffranal = _material("Saffranal")
    safranal = _material("Safranal")
    assert saffranal.registry_name == "Safranal"
    for field in ("mw_g_mol", "vp_pure_pa", "logp"):
        assert getattr(saffranal, field) is not None, field
        assert getattr(saffranal, field) == getattr(safranal, field), field
