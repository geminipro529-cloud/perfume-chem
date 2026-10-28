"""Fruit data batch, 25 Oct 2026: air thresholds, physics and odour descriptions for
owned fruity materials (Kenny: "There are many missing information regarding the fruit
molecule"). Every value's source was re-opened before loading."""

from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import (
    _INVENTORY_ODT_UNAVAILABLE_20261007,
    ODT_DATA,
    ODT_VERIFICATION,
)
from engine.pipeline.formula_state import lookup_odt_air_ppb

ODT = {
    # key: (record, ppb, vfy, label prefix)
    "cis-3 hexenyl acetate": ("Cis-3 Hexenyl Acetate", 2.67, "PEER_SINGLE", "literature"),
    "manzanate": ("Manzanate", 0.0515, "PEER_SINGLE", "literature"),
    "ethyl 2-methylbutyrate": ("Ethyl 2-Methylbutyrate", 0.676, "PEER_SINGLE", "literature"),
    "phenoxy ethyl isobutyrate": ("Phenoxy Ethyl Isobutyrate", 2.88, "PEER_SINGLE", "literature"),
    "hexyl acetate": ("Hexyl Acetate", 2.9, "PEER_CROSS", "literature"),
    "allyl amyl glycolate": ("Allyl Amyl Glycolate", 0.172, "PEER_EST", "estimated"),
    "verdyl acetate": ("Verdyl Acetate", 0.134, "PEER_EST", "estimated"),
    "delta damascone": ("Delta Damascone", 0.00267, "PEER_SINGLE", "literature"),
    "alpha damascone": ("Alpha Damascone", 0.0178, "PEER_SINGLE", "literature"),
}


@pytest.mark.parametrize("key", sorted(ODT))
def test_fruit_air_thresholds_reach_the_gate_with_their_sources(key):
    record, ppb, vfy, label = ODT[key]
    assert ODT_DATA[key]["odt_air"] == pytest.approx(ppb)
    assert ODT_VERIFICATION[key]["vfy"] == vfy
    assert ODT_VERIFICATION[key]["sources"]
    value, source = lookup_odt_air_ppb(record, get_profile(record))
    assert value == pytest.approx(ppb)
    assert source.startswith(label)
    spine = load_registry().get(record)
    assert spine.odt_air_ppb == pytest.approx(ppb)
    assert "2026-10-25" in spine.provenance["odt_air_ppb"]


def test_estimates_say_so_in_their_provenance():
    for record in ("Allyl Amyl Glycolate", "Verdyl Acetate"):
        assert load_registry().get(record).provenance["odt_air_ppb"].startswith("ESTIMATE")


def test_intake_receipt_rows_stay_as_recorded():
    for key in ("cis-3 hexenyl acetate", "manzanate"):
        assert _INVENTORY_ODT_UNAVAILABLE_20261007[key]["odt_air"] is None
        assert ODT_DATA[key] is not _INVENTORY_ODT_UNAVAILABLE_20261007[key]


PHYSICS = [
    ("Verdyl Acetate", "mw_g_mol", 192.26),
    ("Verdyl Acetate", "logp", 3.8),
    ("Verdyl Acetate", "vp_25c_pa", 2.84),
    ("Dimethyl Benzyl Carbinyl Acetate", "mw_g_mol", 192.25),
    ("Dimethyl Benzyl Carbinyl Acetate", "logp", 3.4),
    # The literature fill (same day) replaced the EPI values with converted measured ones.
    ("Dimethyl Benzyl Carbinyl Acetate", "vp_25c_pa", 2.12),
    ("Melonal", "logp", 3.4),
    ("Verdox", "logp", 4.75),
    ("Verdox", "vp_25c_pa", 10.2),
    ("Hexyl Acetate", "vp_25c_pa", 176.0),
    ("Styralyl Acetate", "logp", 2.5),
    ("Styralyl Acetate", "density_25c_g_ml", 1.0215),
    # (Damascol logp left this list on 2026-10-28: ECHA OECD 117 3.5 replaced the IFF SDS 3.215.)
]


@pytest.mark.parametrize(("record", "field", "value"), PHYSICS)
def test_fruit_physics_values_carry_a_dated_provenance(record, field, value):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    provenance = spine.provenance[field]
    assert "2026-10-25" in provenance
    assert "thegoodscents" not in provenance.lower()
    if field == "vp_25c_pa" and provenance.startswith("ESTIMATE"):
        assert spine.vp_source == "EPI"


DESCRIBED = [
    "Pear Valerate",
    "Peach Ketone",
    "Phenoxy Ethyl Isobutyrate",
    "Aldehyde C-16 Ethyl Methyl Phenyl Glycidate",
    "Aldehyde C-18 Gamma Nonalactone",
    "Gamma Nonalactone",
    "Delta Damascone",
    "Beta Damascone",
    "Damascone Beta",
    "Dimethyl Benzyl Carbinyl Acetate",
    "Ethyl 2-Methylbutyrate",
]


@pytest.mark.parametrize("record", DESCRIBED)
def test_fruit_odour_descriptions_come_from_producer_or_rifm_text(record):
    spine = load_registry().get(record)
    assert spine.character
    provenance = spine.provenance["character"]
    assert "2026-10-25" in provenance
    assert any(s in provenance for s in ("givaudan.com", "iff.com", "kao.com", "fragrancematerialsafetyresource"))


def test_rum_ether_keeps_its_own_lot_density():
    # Sigma's 0.825 "(lit.)" is not Kenny's MSR lot; his COA range stays.
    assert load_registry().get("Rum Ether").density_25c_g_ml == pytest.approx(0.872)
