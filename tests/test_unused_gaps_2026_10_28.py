"""Group 1 of the least-used report (28 Oct 2026): sourced fixes, labelled threshold estimates and
Kenny's bottle answers from the "Fix gaps in unused materials" thread. Every source was re-opened
before loading. These pin the data and its sources; they make no sensory claim."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.ifra_standards import load_natural_constituents
from engine.inventory_parser import parse_current_inventory
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION, lookup_odt_raw_name
from engine.skin_interaction import SKIN_PHYSCHEM


@pytest.fixture(scope="module")
def records():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["record_id"]: r for r in overlay["delta_records"]}


@pytest.fixture(scope="module")
def stocks():
    return parse_current_inventory(unique=False)


def test_undecavertol_is_owned_neat_and_at_one_percent(records, stocks):
    record = records["INV-USER-20261014-STK-189"]
    assert record["source_quote"] == "I have both neat and 1%"
    rows = {s.name: s for s in stocks if s.name.startswith("Undecavertol")}
    assert (rows["Undecavertol"].dilution, rows["Undecavertol"].execution_ready) == (1.0, True)
    assert (rows["Undecavertol 1%"].dilution, rows["Undecavertol 1%"].carrier) == (0.01, "dpg")


def test_cedryl_acetate_leaves_its_intake_hold_as_a_neat_liquid(records, stocks):
    record = records["INV-USER-20261014-STK-190"]
    assert record["source_quote"] == "Liquid"
    assert record["stock"]["execution_basis"].startswith("INV-USER-20261007-PW-034_INTAKE_HOLD_CLEARED")
    (stock,) = [s for s in stocks if s.name == "Cedryl Acetate"]
    assert (stock.dilution, stock.execution_ready) == (1.0, True)


def test_kenyan_myrrh_tincture_doses_at_its_starting_charge(records, stocks):
    record = records["INV-USER-20261014-STK-191"]
    assert record["source_quote"] == "ye"
    assert record["authority_limits"]["final_filtrate_assayed"] is False
    (stock,) = [s for s in stocks if s.name == "Kenyan Myrrh Ethanol Tincture"]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.2, "mass_fraction", "ethanol")
    assert stock.execution_ready is True


@pytest.mark.parametrize(
    ("name", "odt"),
    [("Cedroxyde", 8.0), ("Cedryl Acetate", 20.0), ("Anisyl Acetate", 9.0)],
)
def test_analogue_thresholds_are_tagged_unverified_with_their_inputs(name, odt):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == odt
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == "UNVERIFIED"
    assert any("Analogue estimate" in s for s in meta["sources"])
    assert any("PW Relative Odor Impact" in s for s in meta["sources"])
    spine = load_registry().get(name)
    assert spine.odt_air_ppb == odt
    assert spine.provenance["odt_air_ppb"].startswith("UNVERIFIED analogue estimate")


@pytest.mark.parametrize("name", ["Glycolierral", "Fructone B"])
def test_materials_with_no_measured_analogue_get_no_threshold(name):
    assert ODT_DATA[lookup_odt_raw_name(name)]["odt_air"] is None


def test_cabreuva_threshold_is_labelled_constituent_derived():
    assert ODT_VERIFICATION["cabreuva eo"]["vfy"] == "DERIVED"


def test_cedroxyde_skin_model_uses_the_producer_logp_and_formula_mass():
    assert SKIN_PHYSCHEM["Cedroxyde"]["logP"] == 4.88
    assert SKIN_PHYSCHEM["Cedroxyde"]["MW"] == 220.35


@pytest.mark.parametrize(
    ("name", "field", "value", "provenance_start"),
    [
        ("Glycolierral", "vp_25c_pa", 0.24, "Givaudan, Glycolierral"),
        ("Glycolierral", "density_25c_g_ml", 1.007, "Vigon SDS 500894"),
        ("Fructone B", "density_25c_g_ml", 1.039, "PerfumersWorld 3FG00196"),
        ("Anisyl Acetate", "vp_25c_pa", 1.33, "Givaudan, Anisyl Acetate"),
        ("Anisyl Acetate", "logp", 1.9, "RIFM 2024"),
    ],
)
def test_loaded_values_carry_a_dated_provenance(name, field, value, provenance_start):
    spine = load_registry().get(name)
    assert getattr(spine, field) == pytest.approx(value)
    assert spine.provenance[field].startswith(provenance_start)
    assert "Loaded 2026-10-28" in spine.provenance[field]


@pytest.mark.parametrize(
    ("name", "producer"),
    [("Glycolierral", "Givaudan"), ("Fructone B", "IFF"), ("Cedryl Acetate", "IFF")],
)
def test_producer_odour_text(name, producer):
    spine = load_registry().get(name)
    assert spine.character
    assert spine.provenance["character"].startswith(producer)


def test_undecavertol_records_rifms_measured_20c_vapour_pressure_without_replacing_the_25c_field():
    spine = load_registry().get("Undecavertol")
    assert spine.vp_25c_pa == pytest.approx(2.93)
    assert "1.1 Pa at 20 C" in spine.notes
    assert "Loaded 2026-10-25" in spine.provenance["logp"]
    assert "3.9 at 30 C (RIFM, 1996)" in spine.provenance["logp"]


def test_magnolia_eo_counts_the_higher_published_methyl_eugenol():
    levels = load_natural_constituents().stocks["Magnolia EO"]
    assert levels["IFRA_STD_100"][0] == pytest.approx(3.59)
    assert levels["IFRA_STD_037"][0] == pytest.approx(0.4)
