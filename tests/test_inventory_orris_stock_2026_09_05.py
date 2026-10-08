"""User-confirmed Orris stock correction; no fragrance-release assertions."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, replace
from decimal import Decimal

import pytest
import yaml

import engine.inventory_parser as inventory_parser
from engine.pipeline.preflight import _dilution_consistency_check


def _stock_check(fraction=0.09, basis="mass_fraction", carrier="dep"):
    return _dilution_consistency_check(
        {
            "ingredients_ul": {"Orris Liquid": 100.0},
            "dilutions": {"Orris Liquid": fraction},
            "stock_specs": {
                "Orris Liquid": {
                    "fraction": fraction,
                    "fraction_basis": basis,
                    "carrier": carrier,
                    "declared": True,
                }
            },
        }
    )


def test_orris_current_stock_is_unique_nine_percent_mass_fraction_in_dep():
    materialized = inventory_parser.materialize_current_inventory()
    stocks = [s for s in materialized.stocks if s.identity_name == "Orris Liquid"]
    assert len(stocks) == 1
    stock = stocks[0]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (
        0.09, "mass_fraction", "dep"
    )
    assert stock.source_rows == (195,)
    assert stock.stock_id.startswith("inventory:user-20260905:")
    assert stock.source_ref.endswith(
        "inventory_user_authority_overlay_20260905.json#INV-USER-20260905-001"
    )
    assert stock.execution_ready is False
    assert "USER_COMPOUNDING_HOLD" in stock.execution_hold_reason
    assert len(materialized.requirements) == 280
    requirement = next(r for r in materialized.requirements if r.source_row == 195)
    assert requirement.disposition == "OWNED"
    assert requirement.requested_fraction is None
    assert requirement.fraction_basis == "unspecified"
    assert requirement.carrier == ""


def test_orris_current_text_and_yaml_agree_without_rewriting_material_density():
    parsed = inventory_parser.parse_inventory()
    stock = next(s for s in parsed if s.name == "Orris Liquid")
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (
        0.09, "mass_fraction", "dep"
    )
    path = inventory_parser.PROJECT_ROOT / "data/materials/O.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload["materials"]
    record = next(r for r in records if r["canonical_name"] == "Orris Liquid")
    assert record["user_stock_dilution"] == "9% w/w in DEP"
    assert record["supplier"]["other"]["user_dilution_solvent"] == "DEP"
    assert record["density_25c_g_ml"] == 0.93
    assert "Orris Liquid (30%)" in record["aliases"]
    assert "Orris Liquid (9% w/w in DEP)" in record["aliases"]


def test_orris_stock_binding_receipt_is_preserved_during_the_user_hold():
    check = _stock_check()
    assert check.status == "FAIL"
    assert "Orris Liquid" not in check.data.get("resolved_stock_specs", {})
    payload = inventory_parser.load_current_user_inventory_overlay()
    record = next(r for r in payload["records"] if r["canonical_name"] == "Orris Liquid")
    # The historical binding remains readable but cannot override the new hold.
    # It never validated a volume-to-mass conversion.
    assert record["stock"]["execution_scope"] == "STOCK_IDENTITY_AND_FRACTION_BINDING_ONLY"
    limits = record["authority_limits"]
    assert limits["product_mass_from_weighed_stock_known"] is True
    for key in (
        "stock_solution_density_asserted",
        "exact_active_mass_from_raw_volume_authorized",
        "literal_active_volume_asserted",
        "carrier_displacement_volume_authorized",
        "pure_irone_assay_asserted",
        "formula_rebase_authorized",
        "formula_compounding_authorized",
        "safety_asserted",
        "stability_asserted",
        "sensory_equivalence_asserted",
        "release_success_asserted",
    ):
        assert limits[key] is False
    assert Decimal("1.000") * Decimal(str(record["stock"]["fraction"])) == Decimal("0.090")
    assert Decimal("1.000") * (1 - Decimal("0.09")) == Decimal("0.910")


@pytest.mark.parametrize(
    ("fraction", "basis", "carrier"),
    [
        (0.30, "mass_fraction", "dep"),
        (0.09, "volume_fraction", "dep"),
        (0.09, "mass_fraction", "dpg"),
    ],
)
def test_orris_old_strength_wrong_basis_and_wrong_carrier_are_rejected(
    fraction, basis, carrier
):
    check = _stock_check(fraction, basis, carrier)
    assert check.status == "FAIL"
    assert "Orris Liquid" not in check.data.get("resolved_stock_specs", {})


def test_successor_preserves_all_inherited_stock_ids_and_quantities():
    parent = inventory_parser.materialize_current_inventory(apply_user_overlay=False)
    previous = inventory_parser.load_current_user_inventory_overlay(
        inventory_parser.PREVIOUS_USER_INVENTORY_OVERLAY_PATH
    )
    before = inventory_parser._apply_current_user_inventory_overlay(parent, previous)
    successor = inventory_parser.load_current_user_inventory_overlay(
        inventory_parser.ORRIS_USER_INVENTORY_OVERLAY_PATH
    )
    after = inventory_parser._apply_current_user_inventory_overlay(parent, successor)
    old_stocks = {s.stock_id: asdict(s) for s in before.stocks}
    inherited = {s.stock_id: asdict(s) for s in after.stocks if s.name != "Orris Liquid"}
    assert inherited == old_stocks
    assert len(after.stocks) == len(before.stocks) + 1
    old_requirements = {r.source_row: asdict(r) for r in before.requirements if r.source_row != 195}
    new_requirements = {r.source_row: asdict(r) for r in after.requirements if r.source_row != 195}
    assert new_requirements == old_requirements
    assert next(s for s in after.stocks if s.name == "Irotyl").dilution == 1.0


def test_historical_predecessor_keeps_frozen_text_receipt_and_bytes():
    path = inventory_parser.PREVIOUS_USER_INVENTORY_OVERLAY_PATH
    digest = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert digest == inventory_parser.PREVIOUS_USER_INVENTORY_OVERLAY_SHA256
    payload = inventory_parser.load_current_user_inventory_overlay(path)
    assert payload["effective_date"] == "2026-09-04"
    assert payload["source"]["inventory_text_size_bytes"] == 20906
    assert payload["source"]["inventory_text_sha256"] == (
        "f5c1c046f4654c76c94e0aa77c39976cae6b7bba263f9654e20b92881ecdfb14"
    )


@pytest.mark.parametrize("field", ["predecessor", "source", "stock"])
def test_successor_rejects_pin_source_or_stock_drift(field):
    payload = copy.deepcopy(inventory_parser.load_current_user_inventory_overlay(
        inventory_parser.ORRIS_USER_INVENTORY_OVERLAY_PATH
    ))
    payload["records"] = payload["delta_records"]
    payload["policy"] = payload["head_policy"]
    if field == "predecessor":
        payload["predecessor"]["normalized_text_sha256"] = "0" * 64
    elif field == "source":
        payload["source"]["inventory_text_sha256"] = "0" * 64
    else:
        payload["records"][0]["stock"]["fraction"] = 0.30
    with pytest.raises(inventory_parser.InventoryAuthorityError):
        inventory_parser._load_20260905_user_inventory_successor(payload)


def test_successor_rejects_changed_predecessor_bytes(tmp_path, monkeypatch):
    original = inventory_parser.PREVIOUS_USER_INVENTORY_OVERLAY_PATH
    altered = tmp_path / original.name
    altered.write_bytes(original.read_bytes() + b" ")
    monkeypatch.setattr(inventory_parser, "PREVIOUS_USER_INVENTORY_OVERLAY_PATH", altered)
    with pytest.raises(inventory_parser.InventoryAuthorityError, match="hash drift"):
        inventory_parser.load_current_user_inventory_overlay()


def test_user_compounding_hold_preserves_ownership_and_stock_binding():
    materialized = inventory_parser.materialize_current_inventory()
    stock = next(s for s in materialized.stocks if s.identity_name == "Orris Liquid")
    assert stock.status == "owned"
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (
        0.09, "mass_fraction", "dep"
    )
    assert stock.execution_ready is False
    assert stock.design_ready is False
    assert "USER_COMPOUNDING_HOLD" in stock.execution_hold_reason
    assert stock.stock_id.startswith("inventory:user-20260905:")
    check = _stock_check()
    assert check.status == "FAIL"
    assert "Orris Liquid" not in check.data.get("resolved_stock_specs", {})


def test_hold_does_not_mutate_stock_identity_or_unrelated_iris_materials():
    materialized = inventory_parser.materialize_current_inventory()
    held = next(s for s in materialized.stocks if s.identity_name == "Orris Liquid")
    historical = replace(
        held, execution_ready=True, execution_hold_reason="", design_ready=None,
        design_hold_reason="",
    )
    other = replace(historical, name="Orris Butter", identity_name="Orris Butter")
    stronger = replace(historical, dilution=0.30, stock_id="test:another-orris-strength")
    result, digest = inventory_parser.apply_user_compounding_holds(
        (historical, other, stronger)
    )
    assert len(digest) == 64
    assert result[1] == other
    assert not result[0].execution_ready
    assert not result[2].execution_ready
    changed = {
        key for key, value in asdict(historical).items()
        if asdict(result[0])[key] != value
    }
    assert changed == {
        "execution_ready", "execution_hold_reason", "design_ready", "design_hold_reason"
    }


def test_stock_detail_completion_cannot_clear_user_hold(tmp_path, monkeypatch):
    from engine.inventory_completions import effective_design_ready, record_inventory_completion

    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "details.jsonl"))
    baseline = inventory_parser.materialize_current_inventory()
    stock = next(s for s in baseline.stocks if s.identity_name == "Orris Liquid")
    _receipt, completed = record_inventory_completion(
        stock_id=stock.stock_id,
        expected_effective_inventory_sha256=baseline.effective_inventory_sha256,
        idempotency_key="details-do-not-clear-user-hold",
        fraction_decimal="0.09",
        fraction_basis="mass_fraction",
        carrier="DEP",
        physical_form="solution",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=True,
        source_kind="USER_LABEL_OR_RECIPE",
        user_note="Stock details are not permission to use this product.",
    )
    updated = next(s for s in completed.stocks if s.stock_id == stock.stock_id)
    assert not updated.execution_ready
    assert not effective_design_ready(updated)
    assert updated.design_ready is False
    assert inventory_parser.is_user_compounding_held(updated)


def test_hold_applies_to_legacy_and_personal_design_views(tmp_path):
    from engine.inventory_completions import effective_design_ready
    from engine.personal_inventory import materialize_personal_inventory
    from engine.research.composition_planner import _load_candidates

    for stocks in (
        inventory_parser.parse_inventory(),
        materialize_personal_inventory(addition_path=tmp_path / "unused.jsonl").stocks,
    ):
        held = [s for s in stocks if s.identity_name == "Orris Liquid"]
        assert held and all(s.status == "owned" for s in held)
        assert all(not effective_design_ready(s) for s in held)
    candidates, _inventory, _known = _load_candidates(("Orris Liquid",))
    assert all(c.stock.identity_name != "Orris Liquid" for c in candidates)


def test_hold_source_drift_invalidates_cached_inventory(tmp_path, monkeypatch):
    path = tmp_path / "holds.json"
    path.write_bytes(inventory_parser.USER_COMPOUNDING_HOLDS_PATH.read_bytes())
    monkeypatch.setattr(inventory_parser, "USER_COMPOUNDING_HOLDS_PATH", path)
    before = inventory_parser.materialize_current_inventory()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source"]["request"] += " Additional information remains pending."
    path.write_text(json.dumps(payload), encoding="utf-8")
    after = inventory_parser.materialize_current_inventory()
    assert before.effective_inventory_sha256 != after.effective_inventory_sha256
    assert before.stocks == after.stocks
    assert before.snapshot_sha256 == after.snapshot_sha256
    assert before.overlay_sha256 == after.overlay_sha256


@pytest.mark.parametrize("bad_content", [None, "{", "[]", '{"records": []}'])
def test_missing_or_malformed_hold_policy_fails_closed(tmp_path, monkeypatch, bad_content):
    path = tmp_path / "invalid-holds.json"
    if bad_content is not None:
        path.write_text(bad_content, encoding="utf-8")
    monkeypatch.setattr(inventory_parser, "USER_COMPOUNDING_HOLDS_PATH", path)
    with pytest.raises(inventory_parser.InventoryAuthorityError, match="compounding hold"):
        inventory_parser.materialize_current_inventory()
