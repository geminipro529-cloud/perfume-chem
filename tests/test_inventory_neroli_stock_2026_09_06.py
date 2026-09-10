"""Neroli neat-only successor; stock binding is not formula or release authority."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import asdict

import pytest
import yaml

import engine.inventory_parser as inventory_parser
from engine.pipeline.preflight import _dilution_consistency_check


def _stock_check(fraction=1.0, basis="neat", carrier="", stock_id=""):
    spec = {
        "fraction": fraction,
        "fraction_basis": basis,
        "carrier": carrier,
        "declared": True,
    }
    if stock_id:
        spec["stock_id"] = stock_id
    return _dilution_consistency_check(
        {
            "ingredients_ul": {"Neroli EO": 10.0},
            "dilutions": {"Neroli EO": fraction},
            "stock_specs": {"Neroli EO": spec},
        }
    )


def test_september_6_neroli_is_neat_only_and_retired_stock_is_absent():
    materialized = inventory_parser._apply_current_user_inventory_overlay(
        inventory_parser.materialize_current_inventory(apply_user_overlay=False),
        inventory_parser.load_current_user_inventory_overlay(inventory_parser.NEROLI_USER_INVENTORY_OVERLAY_PATH),
    )
    stocks = [s for s in materialized.stocks if s.identity_name == "Neroli EO"]
    assert len(stocks) == 1
    stock = stocks[0]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (1.0, "neat", "")
    assert stock.stock_id.startswith("inventory:user-20260906:")
    assert stock.source_rows == (180,)
    assert stock.execution_ready is True
    assert all(s.stock_id != "inventory:v5:ea88f93dcf37406d817c" for s in materialized.stocks)
    requirement = next(r for r in materialized.requirements if r.source_row == 180)
    assert requirement.disposition == "OWNED"
    assert "NEAT ONLY" in requirement.status
    # The old request remains history, not another owned 10% stock.
    assert requirement.requested_fraction == 0.1
    assert len(materialized.requirements) == 280


def test_neroli_text_keeps_prepared_ethanol_distinct_from_legacy_neat_yaml():
    stocks = [s for s in inventory_parser.parse_inventory(unique=False) if s.name == "Neroli EO"]
    assert {(s.dilution, s.carrier) for s in stocks} == {(1.0, ""), (0.1, "ethanol")}
    assert not any(s.carrier == "dpg" for s in stocks)
    path = inventory_parser.PROJECT_ROOT / "data/materials/N.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload["materials"]
    neroli = [r for r in records if r["canonical_name"] == "Neroli EO"]
    assert len(neroli) == 3
    assert all(r["user_stock_dilution"] == "neat" for r in neroli)
    assert all("neroli eo (neat)" in r["aliases"] for r in neroli)
    assert all("neroli eo (10% in dpg)" in r["aliases"] for r in neroli[1:])
    assert [r["density_25c_g_ml"] for r in neroli] == [None, 0.87, None]


def test_neat_stock_binding_passes_without_promoting_equivalence_or_safety():
    check = _stock_check()
    assert check.status == "PASS"
    spec = check.data["resolved_stock_specs"]["Neroli EO"]
    assert spec["fraction"] == 1.0
    assert spec["fraction_basis"] == "neat"
    payload = inventory_parser.load_current_user_inventory_overlay()
    record = next(r for r in payload["records"] if r["canonical_name"] == "Neroli EO")
    assert record["source_quote"] == "I only have neroli EO neat"
    for key in (
        "stock_solution_density_asserted",
        "exact_active_mass_from_raw_volume_authorized",
        "formula_rebase_authorized",
        "formula_compounding_authorized",
        "safety_asserted",
        "stability_asserted",
        "sensory_equivalence_asserted",
        "release_success_asserted",
    ):
        assert record["authority_limits"][key] is False


@pytest.mark.parametrize("explicit_id", ["", "inventory:v5:ea88f93dcf37406d817c"])
def test_retired_ten_percent_neroli_cannot_bind(explicit_id):
    check = _stock_check(0.1, "unspecified", "dpg", explicit_id)
    assert check.status == "FAIL"
    assert "Neroli EO" not in check.data.get("resolved_stock_specs", {})


def test_all_non_neroli_stocks_and_requirements_are_preserved():
    parent = inventory_parser.materialize_current_inventory(apply_user_overlay=False)
    previous = inventory_parser.load_current_user_inventory_overlay(
        inventory_parser.ORRIS_USER_INVENTORY_OVERLAY_PATH
    )
    before = inventory_parser._apply_current_user_inventory_overlay(parent, previous)
    after = inventory_parser._apply_current_user_inventory_overlay(
        parent, inventory_parser.load_current_user_inventory_overlay(
            inventory_parser.NEROLI_USER_INVENTORY_OVERLAY_PATH
        )
    )
    assert len(before.stocks) == len(after.stocks)
    assert {s.stock_id: asdict(s) for s in before.stocks if s.identity_name != "Neroli EO"} == {
        s.stock_id: asdict(s) for s in after.stocks if s.identity_name != "Neroli EO"
    }
    assert {r.source_row: asdict(r) for r in before.requirements if r.source_row != 180} == {
        r.source_row: asdict(r) for r in after.requirements if r.source_row != 180
    }


def test_orris_predecessor_remains_byte_pinned_and_historically_loadable():
    path = inventory_parser.ORRIS_USER_INVENTORY_OVERLAY_PATH
    assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == (
        "08d0f0e41f90741200b3e915789ddd044cbbf7b0ce1b1aa266053452781bb17f"
    )
    payload = inventory_parser.load_current_user_inventory_overlay(path)
    assert payload["source"]["inventory_text_size_bytes"] == 20884
    assert payload["source"]["inventory_text_sha256"] == (
        "146f74d7cd40ea7b8b8d57285625cc36c2ab84a3663309d8ef0c903860b97fbc"
    )


@pytest.mark.parametrize("field", ["predecessor", "source", "stock", "selector", "policy"])
def test_neroli_successor_rejects_contract_drift(field):
    payload = copy.deepcopy(inventory_parser.load_current_user_inventory_overlay(
        inventory_parser.NEROLI_USER_INVENTORY_OVERLAY_PATH
    ))
    payload["records"] = payload["delta_records"]
    payload["policy"] = payload["head_policy"]
    if field == "predecessor":
        payload["predecessor"]["normalized_text_sha256"] = "0" * 64
    elif field == "source":
        payload["source"]["inventory_text_sha256"] = "0" * 64
    elif field == "stock":
        payload["records"][0]["stock"]["fraction"] = 0.1
    elif field == "selector":
        payload["records"][0]["supersedes_parent_stocks"][0]["source_row"] = 181
    else:
        payload["policy"]["formula_rebase_authorized"] = True
    with pytest.raises(inventory_parser.InventoryAuthorityError):
        inventory_parser._load_20260906_user_inventory_successor(payload)


def test_new_head_rejects_live_text_drift(tmp_path, monkeypatch):
    path = tmp_path / "inventory.txt"
    path.write_bytes(inventory_parser.INVENTORY_PATH.read_bytes() + b" ")
    monkeypatch.setattr(inventory_parser, "INVENTORY_PATH", path)
    with pytest.raises(inventory_parser.InventoryAuthorityError, match="source binding drift"):
        inventory_parser.load_current_user_inventory_overlay()


def test_new_head_rejects_predecessor_byte_drift(tmp_path, monkeypatch):
    original = inventory_parser.ORRIS_USER_INVENTORY_OVERLAY_PATH
    altered = tmp_path / original.name
    altered.write_bytes(original.read_bytes() + b" ")
    monkeypatch.setattr(inventory_parser, "ORRIS_USER_INVENTORY_OVERLAY_PATH", altered)
    with pytest.raises(inventory_parser.InventoryAuthorityError, match="hash drift"):
        inventory_parser.load_current_user_inventory_overlay()


def test_ahs_child_changes_only_neroli_and_explicit_carrier_with_parent_guard():
    from engine.fuckups.pre_mix_guard import evaluate_pre_mix_guard
    from scripts.verify_formula_workflow import parse_formula_markdown

    base = inventory_parser.PROJECT_ROOT / "formulas"
    parent_path = base / "AHS_2004_Reference_First_From_Zero_30mL_EDT_v1.md"
    child_path = base / "AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md"
    assert hashlib.sha256(parent_path.read_bytes()).hexdigest() == (
        "9f96499bc64f4e574e1b91e4e8d194e80d81390fd150fda70019645588f7edde"
    )
    parent = parse_formula_markdown(parent_path)[0]
    child = parse_formula_markdown(child_path)[0]
    assert len(parent["ingredients_ul"]) == 26
    assert len(child["ingredients_ul"]) == 27
    assert sum(parent["ingredients_ul"].values()) == 5000.0
    assert sum(child["ingredients_ul"].values()) == 5000.0
    assert child["ingredients_ul"]["Neroli EO"] == 10.0
    assert child["ingredients_ul"]["DPG"] == 90.0
    assert child["dilutions"]["Neroli EO"] == 1.0
    for name in parent["ingredients_ul"]:
        if name == "Neroli EO":
            continue
        for field in ("ingredients_ul", "dilutions", "stock_specs"):
            assert child[field][name] == parent[field][name]
    guard = evaluate_pre_mix_guard(
        child_ingredients_ul=child["ingredients_ul"],
        child_dilutions=child["dilutions"],
        parent_ingredients_ul=parent["ingredients_ul"],
        parent_dilutions=parent["dilutions"],
    )
    assert guard.status == "PASS"
    assert guard.parent_comparison_available is True
    assert guard.temporal_comparison_available is False


def test_ahs_neroli_and_separate_dpg_bind_to_exact_current_stocks():
    from scripts.verify_formula_workflow import parse_formula_markdown

    path = inventory_parser.PROJECT_ROOT / (
        "formulas/AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md"
    )
    child = parse_formula_markdown(path)[0]
    selected = {
        field: {name: child[field][name] for name in ("Neroli EO", "DPG")}
        for field in ("ingredients_ul", "dilutions", "stock_specs")
    }
    assert _dilution_consistency_check(selected).status == "PASS"
