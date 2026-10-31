"""Identity and physics corrections flagged by the Dior Homme Intense reparse (31 Oct 2026).

Each value was re-checked against the producer or Kenny's supplier page before loading.
"""

import json
from pathlib import Path

import yaml

from engine.ifra_standards import evaluate_ifra
from engine.ingredient_intelligence import _PROFILES

ROOT = Path(__file__).resolve().parents[1]

# name in material_properties.json -> CAS, with the page that prints it
CAS = {
    "HABANOLIDE": "111879-80-2",  # dsm-firmenich 947303 and PerfumersWorld 3XA09821; 34902-57-3 is Globalide
    "VETIVAL": "4927-39-3",  # Symrise datasheet and PerfumersWorld 4WL15944; not vetiveryl acetate
    "VERTOFIX COEUR": "32388-55-9",  # TGSC methyl cedryl ketone; 19870-74-7 is Cedramber
    "METHYL PAMPLEMOUSSE": "67674-46-8",  # Givaudan
    "SCENTENAL": "86803-90-9",  # TGSC ocean carboxaldehyde
    "MAPLE LACTONE": "80-71-7",  # PerfumersWorld 1VE00286 (cyclotene); not sotolon
    "Leafovert": "67633-96-9",  # RIFM lists Leafovert as a synonym; was "proprietary"
}


def test_material_properties_carry_the_checked_cas():
    rows = {r["name"]: r for r in json.loads((ROOT / "data/knowledge_graph/material_properties.json").read_text())}
    assert {name: rows[name]["cas"] for name in CAS} == CAS


def test_ingredient_catalog_carries_the_checked_cas():
    catalog = json.loads((ROOT / "data/knowledge_graph/ingredient_catalog.json").read_text())
    by_name = {i["name"].upper(): i["properties"] for i in catalog["ingredients"]}
    for name, cas in CAS.items():
        if name == "VERTOFIX COEUR":
            continue  # not a catalog row
        assert by_name[name.upper()]["cas"] == cas, name


def test_habanolide_material_record_uses_the_producer_cas():
    rows = yaml.safe_load((ROOT / "data/materials/H.yaml").read_text())
    habanolide = next(r for r in rows if r["canonical_name"] == "Habanolide")
    assert habanolide["cas"] == "111879-80-2"
    assert "dsm-firmenich" in habanolide["provenance"]["cas"]


def test_producer_vapour_pressures_replace_unsourced_profile_values():
    assert _PROFILES["Ebanol"]["vp"] == 0.13
    assert "Givaudan" in _PROFILES["Ebanol"]["vp_source"]
    assert _PROFILES["Methyl Pamplemousse"]["vp"] == 29.0
    assert _PROFILES["Methyl Pamplemousse"]["mw"] == 186.3
    assert "Givaudan" in _PROFILES["Methyl Pamplemousse"]["vp_source"]


def test_methyl_ionone_stock_already_counts_in_the_ifra_methyl_ionone_group():
    # The reparse flagged it as missing; the alias "Methyl Ionone" -> "Methyl Ionone Pure" puts it in.
    group = next(g for g in evaluate_ifra({"Methyl Ionone": 20.0}).group_checks if g.id == "methyl_ionones_total")
    assert group.member_pcts == {"Methyl Ionone Pure": 20.0}
