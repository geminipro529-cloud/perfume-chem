"""Literature air-threshold batch, 25 Oct 2026 (stock thread). Kenny: "parse all the
information that is missing into the engine". Each value's source was re-opened by a
second reader before loading; estimates say so in their provenance."""

from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import (
    _LITERATURE_ODT_2026_10_25,
    ODT_DATA,
    ODT_VERIFICATION,
    lookup_odt_raw_name,
)
from engine.pipeline.formula_state import lookup_odt_air_ppb

# batch key: (spine record, ppb, vfy)
LOADED = {
    'iso e super': ('Iso E Super', 0.0184, 'PEER_EST'),
    'undecavertol': ('Undecavertol', 0.2934, 'PEER_SINGLE'),
    'adoxal': ('Adoxal', 0.6252, 'PEER_CROSS'),
    'aldehyde c11 undecylenic': ('Aldehyde C11 Undecylenic', 0.4146, 'PEER_CROSS'),
    'aldehyde c11': ('Aldehyde C11', 0.8796, 'PEER_EST'),
    'benzaldehyde': ('Benzaldehyde', 140.5, 'PEER_SINGLE'),
    'cyclamen aldehyde': ('Cyclamen Aldehyde', 0.3237, 'PEER_CROSS'),
    'maple lactone': ('Maple Lactone', 5.669, 'PEER_CROSS'),
    'neryl acetate': ('Neryl Acetate', 38.88, 'PEER_EST'),
    'skatole': ('Skatole', 0.0056, 'PEER_SINGLE'),
    'aldehyde c-12 lauric dodecanal': ('Aldehyde C-12 Lauric Dodecanal', 0.2916, 'PEER_EST'),
    'alpha irone': ('Alpha Irone', 0.81, 'PEER_EST'),
    'amberwood f': ('Amberwood F', 0.04947, 'PEER_EST'),
    'ambrox super': ('Ambrox Super', 0.02146, 'PEER_SINGLE'),
    'ambrofix crystals (solid)': ('ambrofix crystals (solid)', 0.02146, 'PEER_SINGLE'),
    'berry hexanoate (berryflor)': ('Berry Hexanoate (berryflor)', 4.087, 'PEER_SINGLE'),
    'cashmeran': ('Cashmeran', 0.04128, 'PEER_EST'),
    'cyclogalbanate': ('Cyclogalbanate', 0.07514, 'PEER_EST'),
    'dupical': ('Dupical', 0.04308, 'PEER_SINGLE'),
    'geosmin': ('Geosmin', 0.0065, 'PEER_SINGLE'),
    'geraniol (10% in dpg)': ('geraniol (10% in dpg)', 2.219, 'PEER_SINGLE'),
    'hedione': ('Hedione', 0.03025, 'PEER_SINGLE'),
    'hedione hc': ('Hedione HC', 0.003997, 'PEER_SINGLE'),
    'helional': ('Helional', 0.14, 'PEER_SINGLE'),
    'melonal': ('Melonal', 0.1018, 'PEER_EST'),
    'paradisamide': ('Paradisamide', 0.1371, 'PEER_SINGLE'),
    'phenyl ethyl acetate': ('phenyl ethyl acetate', 1.996, 'PEER_SINGLE'),
    'safraleine': ('Safraleine', 0.7915, 'PEER_SINGLE'),
    'triplal': ('Triplal', 0.582, 'PEER_SINGLE'),
    'verdox': ('Verdox', 10.88, 'PEER_SINGLE'),
    'vetival': ('Vetival', 13.41, 'PEER_SINGLE'),
    'citral': ('Citral', 4.337, 'PEER_CROSS'),
    'guaiacol': ('Guaiacol', 0.01654, 'PEER_SINGLE'),
    'velvione': ('Velvione', 0.052, 'PEER_SINGLE'),
    'bourgeonal': ('Bourgeonal', 0.05187, 'PEER_CROSS'),
    'florhydral': ('Florhydral', 0.008995, 'PEER_CROSS'),
    'magnolan': ('Magnolan', 1.508, 'PEER_SINGLE'),
    'methyl pamplemousse': ('Methyl Pamplemousse', 6.575, 'PEER_CROSS'),
    'nympheal': ('Nympheal', 0.007184, 'PEER_CROSS'),
    'vetikon': ('Vetikon', 87.53, 'PEER_SINGLE'),
    'allyl cyclohexyl propionate': ('Allyl Cyclohexyl Propionate', 1.268, 'PEER_EST'),
    'aurantiol': ('Aurantiol', 0.01845, 'PEER_SINGLE'),
    'calone': ('Calone', 0.004254, 'PEER_SINGLE'),
    'champignol': ('Champignol', 0.5149, 'PEER_SINGLE'),
    'citronellyl acetate': ('Citronellyl Acetate', 14.49, 'PEER_EST'),
    'decatone': ('Decatone', 4.183, 'PEER_SINGLE'),
    'ethyl maltol': ('Ethyl Maltol', 0.0059, 'PEER_SINGLE'),
    'habanolide': ('Habanolide', 17.0, 'PEER_SINGLE'),
    'linalool': ('Linalool', 0.5072, 'PEER_SINGLE'),
    'methyl diantilis': ('Methyl Diantilis', 0.2287, 'PEER_SINGLE'),
    'terpinyl acetate': ('Terpinyl Acetate', 16.93, 'PEER_EST'),
    'ultralia': ('Ultralia', 0.1737, 'PEER_EST'),
    'zenolide': ('Zenolide', 10.02, 'PEER_SINGLE'),
    'leafovert': ('Leafovert', 7.744, 'PEER_SINGLE'),
    'timberol': ('Timberol', 13.6, 'PEER_SINGLE'),
}

# Iso E Super keeps its older ethanol evidence (0.05 ppm against the runtime 0.01), and
# that conflict still marks the threshold unverified.
LABEL = {"iso e super": "unverified"}


def test_the_table_covers_the_whole_batch():
    assert set(LOADED) == set(_LITERATURE_ODT_2026_10_25)


@pytest.mark.parametrize("key", sorted(LOADED))
def test_air_threshold_reaches_the_gate_with_its_sources(key):
    record, ppb, vfy = LOADED[key]
    raw = lookup_odt_raw_name(key)
    assert ODT_DATA[raw]["odt_air"] == pytest.approx(ppb)
    assert ODT_VERIFICATION[raw]["vfy"] == vfy
    assert len(ODT_VERIFICATION[raw]["sources"]) >= 2
    value, source = lookup_odt_air_ppb(record, get_profile(record))
    assert value == pytest.approx(ppb)
    assert source.startswith(LABEL.get(key) or ("estimated" if vfy == "PEER_EST" else "literature"))
    spine = load_registry().get(record)
    assert spine.odt_air_ppb == pytest.approx(ppb)
    provenance = spine.provenance["odt_air_ppb"]
    assert "2026-10-25" in provenance
    assert provenance.startswith("ESTIMATE") == (vfy == "PEER_EST")


def test_no_source_is_a_b_grade_page():
    for _, _, sources in _LITERATURE_ODT_2026_10_25.values():
        text = " ".join(sources).lower()
        for host in ("thegoodscents", "scentree", "fragrantica", "wikipedia"):
            assert host not in text


def test_the_two_aldehyde_c11_records_keep_their_own_molecules():
    # Undecanal (112-44-7) and undecylenic aldehyde (112-45-8) differ; the diluted
    # stocks resolve to undecanal, the neat one to undecylenic.
    assert lookup_odt_air_ppb("Aldehyde C11", get_profile("Aldehyde C11"))[0] == pytest.approx(0.8796)
    assert lookup_odt_air_ppb(
        "Aldehyde C11 Undecylenic", get_profile("Aldehyde C11 Undecylenic")
    )[0] == pytest.approx(0.4146)


def test_conflicting_values_were_left_as_they_were():
    # Symrise's 186 ppb for Phenoxy Ethyl Isobutyrate disagrees with the Givaudan
    # patent value the fruit batch loaded; the fruit value stays.
    assert ODT_DATA["phenoxy ethyl isobutyrate"]["odt_air"] == pytest.approx(2.88)
    assert "indole" not in _LITERATURE_ODT_2026_10_25
