"""Data fixes from the 6 Nov 2026 engine-fault report (section 8), asked for by the
"Give thin-data materials real odour profiles" thread after Kenny chose "All six, in order".
These pin the data and its sources; they make no sensory claim."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.research.composition_planner import _is_solid
from engine.data_spine.loader import load_registry
from engine.ifra_standards import partly_declared_base
from engine.inventory_parser import parse_current_inventory
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION, lookup_odt_raw_name


@pytest.fixture(scope="module")
def records():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["record_id"]: r for r in overlay["delta_records"]}


def test_maple_lactone_is_a_weighed_solid(records):
    record = records["INV-USER-20261014-STK-162"]
    assert record["canonical_name"] == "Maple Lactone"
    assert record["stock"]["physical_form"] == "solid_as_supplied"
    assert record["stock"]["execution_scope"] == "WEIGHED_SOLID_OR_PREPARED_SOLUTION_ONLY"
    assert "crystalline powder" in record["note"]
    (stock,) = [s for s in parse_current_inventory(unique=False) if s.name == "Maple Lactone"]
    assert _is_solid(stock)


@pytest.mark.parametrize(
    ("name", "odt", "vfy", "source_word"),
    [
        ("Gamma Octalactone", 0.31, "PEER_SINGLE", "Buhr (2006)"),
        ("Ethyl Acetoacetate", 3.4, "PEER_SINGLE", "Backman"),
        ("Glycolierral", 0.78, "UNVERIFIED", "Analogues"),
    ],
)
def test_air_thresholds_are_loaded_with_their_sources(name, odt, vfy, source_word):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == odt
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == vfy
    assert any(source_word in s for s in meta["sources"])
    spine = load_registry().get(name)
    assert spine.odt_air_ppb == odt
    assert spine.provenance["odt_air_ppb"]


def test_fixative_505_is_a_partly_declared_firmenich_proxy():
    base = partly_declared_base(["Fixative 505"])
    assert base is not None and base.sku == "4UY07514"
    assert base.undeclared_pct == (49.4867, 64.8867)
    assert base.allergens_pct == {"Alpha Isomethyl Ionone": 0.3333, "Benzyl Benzoate": 0.0131, "Coumarin": 0.0002}
    assert "PROXY_IDENTITY_UNCONFIRMED" in base.undeclared_note


def test_fixative_505_warns_on_its_undeclared_part_instead_of_failing_physics():
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula

    rows = {"Iso E Super": 2000.0, "Hedione": 2000.0, "Fixative 505": 300.0}
    total = sum(rows.values())
    formula = {
        "number": 1,
        "name": "Fixative",
        "ingredients_ul": rows,
        "dilutions": {},
        "ingredients_pct": {k: v / total * 100 for k, v in rows.items()},
        "body": "Fixative",
    }
    report = gate_formula(formula, ReleaseGateConfig(expected_concentrate_ul=total, brief="generic"))
    gates = {g.gate: g for g in report.gates}
    for gate in ("physics_data_coverage", "odt_coverage"):
        assert gates[gate].status == "WARN", (gate, gates[gate].detail)
    assert "Fixative 505" in gates["physics_data_coverage"].detail
    allergens = gates["safety_ifra_allergen"].data["partly_declared_base_allergens"]
    assert {a["allergen"] for a in allergens if a["base"] == "Fixative 505"} == {
        "Alpha Isomethyl Ionone", "Benzyl Benzoate", "Coumarin",
    }
