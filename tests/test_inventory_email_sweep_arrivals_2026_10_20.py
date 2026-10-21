"""Fifteen stocks from Kenny's 20 Oct 2026 answers on his email-order sweep ("Check new ingredients in code").

22:08:35 "decatone neat and 10%, fir EO 10%, cashmeran is neat, exaltolide is both neat and 10%, hedione HC is
neat, magnolia flower extract is 5% in DPG, cabbage rose extract is 1% in DPG"; 22:09:29 "I have DMBC";
22:10:22 "neat"; 22:10:43 "both" (the PW 261015-033902088 and MSR 2199505 parcels have arrived); 22:11:56 "yes"
to recording the other arrived lines as ordered; 22:12:11 "5% in DPG" for the Iris Florentina root extract.
Cashmeran, Exaltolide (neat and 10%) and Hedione HC were already recorded, so only his statement is added.
"""
from __future__ import annotations

import pytest

import engine.inventory_parser as inventory
from engine.material_resolver import resolve_material

EXPECTED = {
    # name: (record id, fraction, basis, carrier, supplier)
    "Fir Essential Oil": ("INV-USER-20261014-STK-122", 0.10, "mass_fraction", "dpg", "PerfumersWorld"),
    "Dimethyl Benzyl Carbinol": ("INV-USER-20261014-STK-123", 1.0, "neat", "", "PerfumersWorld"),
    "Decatone": ("INV-USER-20261014-STK-124", 1.0, "neat", "", "PerfumersWorld"),
    "Decatone 10% in DPG": ("INV-USER-20261014-STK-125", 0.10, "mass_fraction", "dpg", "user dilution of the PerfumersWorld neat stock"),
    "Magnolia Flower Extract": ("INV-USER-20261014-STK-126", 0.05, "mass_fraction", "dpg", "MySkinRecipes"),
    "Cabbage Rose Extract": ("INV-USER-20261014-STK-127", 0.01, "mass_fraction", "dpg", "MySkinRecipes"),
    "Velvione": ("INV-USER-20261014-STK-128", 1.0, "neat", "", "PerfumersWorld"),
    "Para-Cresyl Phenyl Acetate": ("INV-USER-20261014-STK-129", 1.0, "neat", "", "PerfumersWorld"),
    "Phenoxy Ethyl Isobutyrate": ("INV-USER-20261014-STK-130", 1.0, "neat", "", "PerfumersWorld"),
    "Dupical 10% in DPG": ("INV-USER-20261014-STK-131", 0.10, "mass_fraction", "dpg", "PerfumersWorld"),
    "Pear Valerate": ("INV-USER-20261014-STK-132", 1.0, "neat", "", "MySkinRecipes"),
    "Cyclogalbanate": ("INV-USER-20261014-STK-133", 1.0, "neat", "", "MySkinRecipes"),
    "Peach Ketone": ("INV-USER-20261014-STK-134", 1.0, "neat", "", "MySkinRecipes"),
    "Canthoxal": ("INV-USER-20261014-STK-135", 1.0, "neat", "", "MySkinRecipes"),
    "Iris Florentina Root Extract": ("INV-USER-20261014-STK-136", 0.05, "mass_fraction", "dpg", "MySkinRecipes"),
}


@pytest.fixture(scope="module")
def materialized():
    return inventory.materialize_current_inventory()


@pytest.fixture(scope="module")
def records():
    payload = inventory.load_current_user_inventory_overlay()
    return {r["canonical_name"]: r for r in payload["delta_records"]}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_arrival_is_recorded_as_kenny_said(name, materialized, records):
    record_id, fraction, basis, carrier, supplier = EXPECTED[name]
    record = records[name]
    assert record["record_id"] == record_id
    assert record["stock"]["fraction"] == pytest.approx(fraction)
    assert record["stock"]["fraction_basis"] == basis
    assert record["stock"]["carrier"] == carrier
    assert record["supplier_product"]["supplier"] == supplier
    assert record["authority_limits"]["availability_confirmed"] is True
    assert record["authority_limits"]["purity_assay_asserted"] is False
    stocks = [s for s in materialized.stocks if s.name == name]
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.dilution == pytest.approx(fraction)
    assert (stock.fraction_basis, stock.carrier) == (basis, carrier)
    assert stock.execution_ready is True
    assert resolve_material(name).is_known


def test_decatone_neat_and_ten_percent_are_two_stocks_of_one_identity(materialized):
    stocks = [s for s in materialized.stocks if s.identity_name == "Decatone"]
    assert sorted((s.dilution, s.carrier) for s in stocks) == [(0.10, "dpg"), (1.0, "")]


def test_dmbc_is_not_the_acetate_and_the_iris_extract_is_not_an_orris_alias(materialized):
    by_identity = {s.identity_name for s in materialized.stocks}
    assert "Dimethyl Benzyl Carbinol" in by_identity
    assert "Dimethyl Benzyl Carbinyl Acetate" in by_identity
    assert resolve_material("Dimethyl Benzyl Carbinol").canonical_name != resolve_material("Dimethyl Benzyl Carbinyl Acetate").canonical_name
    iris = resolve_material("Iris Florentina Root Extract").canonical_name
    assert iris not in {resolve_material(n).canonical_name for n in ("Orris Liquid", "Orris Concrete Orris Butter", "Orris Butter 50% in EtOH", "Alpha Irone")}


def test_already_owned_strengths_are_unchanged(materialized):
    by = {s.name: s for s in materialized.stocks}
    assert by["Cashmeran (neat)"].dilution == 1.0
    assert by["Exaltolide"].dilution == 1.0
    assert by["Exaltolide 10% in DPG"].dilution == pytest.approx(0.10)
    assert by["Hedione HC"].dilution == 1.0


def test_the_statements_are_on_record(records):
    payload = inventory.load_current_user_inventory_overlay()
    texts = {s["text"] for s in payload["source"]["verbatim_user_statements"]}
    assert {"I have DMBC", "neaat", "both", "ye", "5% in DPG"} <= texts
    assert any(t.startswith("decatone neat and 10%, fir EO 10%") for t in texts)


@pytest.mark.parametrize(
    ("name", "cas", "mw", "vp_source"),
    (
        ("Peach Ketone", "95962-14-4", 220.36, "ECHA_measured_20C_not_corrected"),
        ("Pear Valerate", "90397-38-9", 200.32, "EPI"),
        ("Decatone", "34131-98-1", 194.32, "EPI"),
        ("Velvione", "37609-25-9", 236.40, "ECHA_measured_20C_not_corrected"),
        ("Canthoxal", "5462-06-6", 178.23, "ECHA_measured_24C_not_corrected"),
        ("Phenoxy Ethyl Isobutyrate", "103-60-6", 208.26, "ECHA_measured"),
        ("Dimethyl Benzyl Carbinol", "100-86-7", 150.22, "EPI"),
    ),
)
def test_researched_identity_and_physics_are_loaded(name, cas, mw, vp_source):
    # Kenny chose "Load all" on 21 Oct 2026 for /mnt/project-files/missing-data-20261021;
    # the PC lookups there (PC_LOOKUPS_RESULTS.md) replaced estimates with ECHA measured
    # vapour pressures where they agree, and kept the estimate where ECHA is disputed.
    material = resolve_material(name).registry_material
    assert (material.cas, material.mw_g_mol) == (cas, mw)
    assert material.density_25c_g_ml is not None
    assert material.vp_source == vp_source


@pytest.mark.parametrize(
    ("name", "density", "vp"),
    (
        ("Velvione", 0.93, 0.02),
        ("Canthoxal", 1.065, 0.3),
        ("Peach Ketone", 0.963, 0.009),
        ("Phenoxy Ethyl Isobutyrate", 1.05, 0.77),
        ("Dupical", 1.008, 0.11),
        ("Cyclogalbanate", 1.02, 0.4),
        ("Dimethyl Benzyl Carbinol", 0.979, 3.94),
        ("Pear Valerate", 0.8564, 13.9),
    ),
)
def test_pc_lookup_echa_density_and_vapour_pressure(name, density, vp):
    material = resolve_material(name).registry_material
    assert (material.density_25c_g_ml, material.vp_25c_pa) == (density, vp)


def test_myskinrecipes_peach_ketone_is_nectaryl():
    assert resolve_material("Nectaryl").registry_name == "Peach Ketone"
