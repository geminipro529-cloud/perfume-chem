"""Current full-system reconciliation, preserving history and uncertainty."""

import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.data_spine.reconciliation import reconcile
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import (
    ODT_DATA, _INVENTORY_ODT_UNAVAILABLE_20261007, oav_reliability, verify_odt,
)

ROOT = Path(__file__).resolve().parents[1]


def test_successor_preserves_unaffected_stock_bytes_and_all_requirement_rows():
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    prior = inventory._apply_current_user_inventory_overlay(
        base,
        inventory.load_current_user_inventory_overlay(inventory.NEROLI_USER_INVENTORY_OVERLAY_PATH),
    )
    # This test characterizes the September 7 transition; newer stock changes
    # have their own preservation tests and must not rewrite this predecessor.
    september7 = inventory.load_current_user_inventory_overlay(
        inventory.RECONCILED_USER_INVENTORY_OVERLAY_PATH
    )
    current = inventory._apply_current_user_inventory_overlay(base, september7)
    delta = september7["delta_records"]
    retired_rows = {s["source_row"] for r in delta for s in r["supersedes_parent_stocks"]}
    before = {s.stock_id: s for s in prior.stocks if not retired_rows.intersection(s.source_rows)}
    after = {s.stock_id: s for s in current.stocks if s.stock_id in before}
    assert before == after
    assert len(prior.requirements) == len(current.requirements) == 280
    assert {r.source_row: r for r in prior.requirements if r.source_row not in retired_rows} == {
        r.source_row: r for r in current.requirements if r.source_row not in retired_rows
    }


@pytest.mark.parametrize(
    "name,fraction,basis,carrier,ready",
    [
        ("Coumarin", 0.1, "mass_fraction", "dpg", True),
        ("Vetiveryl Acetate", 1, "neat", "", True),
        ("Methyl Laitone", 0.2, "volume_fraction", "ethanol", True),
        ("Guaiacwood EO", 1 / 3, "mass_fraction", "ethanol + dep", True),
        ("Bacdanol", 1, "neat", "", True),
    ],
)
def test_current_stock_contract(name, fraction, basis, carrier, ready):
    stocks = [
        s for s in inventory.materialize_current_inventory().stocks
        if s.identity_name == name and s.dilution == fraction
        and s.fraction_basis == basis and s.carrier == carrier
    ]
    assert len(stocks) == 1
    s = stocks[0]
    assert (s.dilution, s.fraction_basis, s.carrier, s.execution_ready) == (
        fraction,
        basis,
        carrier,
        ready,
    )


def test_retired_liquids_and_depleted_stocks_do_not_reappear():
    names = {s.identity_name for s in inventory.materialize_current_inventory().stocks}
    assert not names.intersection(
        {"Ambrofix", "Tonalide", "Musk Ketone", "Polysantol", "Nagamortha Oil"}
    )
    assert "Ambrofix Crystals" in names
    kephalis = next(s for s in inventory.materialize_current_inventory().stocks
                    if s.identity_name == "Kephalis")
    assert kephalis.authority == "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261007"
    assert kephalis.execution_ready is False
    old = inventory.load_current_user_inventory_overlay()["retired_records"][0]
    assert old["mass_balance"]["ambrofix_g"] == 0.192


def test_bottle_identity_is_not_a_chemical_alias():
    assert get_profile("Hydroxycitronellal").cas == "107-75-5"
    assert get_profile("Hydroxycitronellol").cas == "107-74-4"
    text = inventory.parse_inventory(include_unavailable=False)
    assert any(s.name == "Hydroxycitronellal" for s in text)
    assert not any(s.name == "Hydroxycitronellol" for s in text)


def test_legacy_parser_keeps_rows_and_prefers_owned_stock():
    rows = inventory.parse_inventory(unique=False)
    assert len(rows) == len(inventory.parse_inventory(unique=False))
    assert len(rows) > 287  # The October receipt is additive, not a historical rewrite.
    assert all(s.source_rows and s.stock_id for s in rows)
    agar = next(s for s in inventory.parse_inventory() if s.name == "Black Agarwood Artificial")
    assert agar.status == "owned" and agar.dilution == 0.1
    kephalis = next(s for s in inventory.parse_inventory() if s.name == "Kephalis")
    assert kephalis.status == "owned"
    assert next(s for s in rows if s.name == "Methyl Laitone").execution_ready is True


@pytest.mark.parametrize("name", ["tuberose abs", "jasmine blossoms", "galbanum EO"])
def test_odt_metadata_never_uses_fuzzy_prefix_identity(name):
    assert verify_odt(name) is None


def test_conflicting_thresholds_are_not_promoted():
    # Exact metadata exists for Tonka Absolute and must not be discarded.
    assert verify_odt("tonka absolute")["vfy"] == "DERIVED"
    for name in ("Iso E Super", "Linalool"):
        assert verify_odt(name)["vfy"] == "UNVERIFIED"
    assert "numeric_conflicts" in verify_odt("Iso E Super")
    for name in ODT_DATA:
        assert isinstance(oav_reliability(name), str)


def test_runtime_odt_numeric_map_is_unchanged():
    values = {
        k: {"odt_air": v.get("odt_air"), "odt_eth": v.get("odt_eth")}
        for k, v in ODT_DATA.items() if k not in _INVENTORY_ODT_UNAVAILABLE_20261007
    }
    digest = hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == "2505240fe7beeb73f9448cdfa47fdd75e14651190d4244b8f065ac9f79908bb5"
    # The receipt adds explicit unknowns; none is a measured threshold.
    assert all(row["odt_air"] is None and row["odt_eth"] is None
               for row in _INVENTORY_ODT_UNAVAILABLE_20261007.values())


def test_new_profiles_do_not_invent_unknown_physics():
    ml = get_profile("Methyl Laitone")
    assert ml.mw == 168.23 and ml.vp is None and ml.odt is None
    guaiac = get_profile("Guaiacwood EO")
    assert guaiac.material_kind == "NATURAL_MIXTURE"
    assert guaiac.mw is None and guaiac.vp is None and guaiac.odt is None
    assert load_registry().get("Methyl Laitone 10% DPG").user_in_inventory is False
    assert load_registry().get("Methyl Laitone").user_in_inventory is True


def test_generator_import_does_not_write_or_request_network(monkeypatch):
    import requests

    def forbidden(*args, **kwargs):
        raise AssertionError("Import must not request network or write files")

    monkeypatch.setattr(requests, "get", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    importlib.import_module("_generate_material_properties")


def test_offline_rebuild_is_lossless_and_idempotent(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("Network prohibited"))
    old = [
        {
            "name": "Florol",
            "mw": 138.21,
            "cas": "68039-49-6",
            "pubchem_cid": 93375,
            "odor_profile": "Keep the full authored description.",
            "bespoke": {"all": [1, 2, 3]},
        },
        {"name": "FLOROL", "distinct_history": "Do not collapse this record."},
        {"name": "Bacdanol", "oav_dose_pct": 3, "oav_typical": 375000},
    ]
    original = copy.deepcopy(old)
    first, report = reconcile(old)
    second, _ = reconcile(first)
    assert old == original and first == second
    assert [r["name"] for r in first[:3]] == [r["name"] for r in old]
    assert first[0]["mw"] == 172.26 and first[0]["pubchem_cid"] == 3017432
    assert (
        first[0]["odor_profile"] == old[0]["odor_profile"]
        and first[0]["bespoke"] == old[0]["bespoke"]
    )
    assert first[2]["oav_typical"] is None  # unresolved product class is not a pure-entity proof
    assert report["counts"]["inventory_text_rows"] == len(
        inventory.parse_inventory(unique=False)
    )


def test_physical_stock_identity_and_mixture_firewall():
    rows, _ = reconcile(
        [
            {"name": n, "oav_dose_pct": 2}
            for n in (
                "Geranium Flower EO",
                "Geranium EO",
                "Jasmine Absolute",
                "Jasmine Sambac Absolute",
                "Bergamot FCF oil Sicilian",
                "BERGAMOT FCF",
                "Black Agarwood Artificial",
                "Castoreum Synthetic",
                "Tonka Bean FO",
                "Tobacco Absolute",
                "Exaltolide",
            )
        ]
    )
    by_name = {r["name"]: r for r in rows}
    assert by_name["Geranium Flower EO"]["current_stocks"] == []
    for name in ("Jasmine Absolute", "Jasmine Sambac Absolute"):
        assert all(s["identity_name"] == name for s in by_name[name]["current_stocks"])
    for name in (
        "Bergamot FCF oil Sicilian",
        "BERGAMOT FCF",
        "Black Agarwood Artificial",
        "Castoreum Synthetic",
        "Tonka Bean FO",
    ):
        assert by_name[name]["oav_typical"] is None
    # 2026-10-08 overlay retires the duplicate Tobacco row: one stock remains.
    assert by_name["Tobacco Absolute"]["dilution_pct"] == 0.1
    assert by_name["Tobacco Absolute"]["quantitative_stock_ready"] is True
    for name in ("Exaltolide",):
        assert by_name[name]["dilution_pct"] is None
        assert by_name[name]["quantitative_stock_ready"] is False
