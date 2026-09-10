"""Source-bound AHSEE stock repair preserves preparations, history and claim limits."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

EXPECTED = [
    ("Phenyl Ethyl Dimethyl Carbinol", 1.0, "neat", ""),
    ("Neroli EO", 0.1, "volume_fraction", "ethanol"),
    ("Peppermint EO", 0.1, "volume_fraction", "ethanol"),
    ("Lilyreal ND", 1.0, "neat", ""),
    ("Nympheal", 1.0, "neat", ""),
    ("Lavender EO (BONTAUX SAS)", 1.0, "neat", ""),
    ("Tonka Bean Absolute", 0.1, "volume_fraction", "dpg"),
    ("Vanillin", 0.1, "volume_fraction", "ethanol"),
    ("Aldehyde C10", 0.01, "volume_fraction", "ethanol"),
    ("Aldehyde C12 MNA", 0.01, "volume_fraction", "ethanol"),
]
REPLACED_ROWS = {9, 13, 232, 239}
OVERRIDDEN_ROWS = REPLACED_ROWS | {160, 185}


def _check(name, fraction, basis, carrier, stock_id=""):
    return resolve_inventory_stock_contract({
        "ingredients_ul": {name: 100.0},
        "dilutions": {name: fraction},
        "stock_specs": {name: {
            "fraction": fraction, "fraction_basis": basis,
            "carrier": carrier, "declared": True, "stock_id": stock_id,
        }},
    })


def _raw_head():
    return json.loads(inventory.AHSEE_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,fraction,basis,carrier", EXPECTED)
def test_corrected_stocks_bind_exactly_without_density_or_release(name, fraction, basis, carrier):
    check = _check(name, fraction, basis, carrier)
    assert check.status == "PASS", check.data.get("issues")
    resolved = check.data["resolved_stock_specs"][name]
    assert (resolved["fraction"], resolved["fraction_basis"], resolved["carrier"]) == (
        fraction, basis, carrier,
    )
    head = inventory.load_current_user_inventory_overlay(inventory.AHSEE_USER_INVENTORY_OVERLAY_PATH)
    record = next(r for r in head["delta_records"] if r["canonical_name"] == name)
    assert record["stock"]["density_g_ml"] is None
    assert record["stock"]["execution_scope"] == "DECLARED_RAW_STOCK_TRANSFER_BINDING_ONLY"
    assert not any(record["authority_limits"].values())


def test_prepared_ethanol_stocks_do_not_revive_retired_dpg_or_replace_neat():
    for name in ("Neroli EO", "Peppermint EO"):
        stocks = [s for s in inventory.materialize_current_inventory().stocks
                  if s.identity_name == name]
        assert {(s.dilution, s.fraction_basis, s.carrier) for s in stocks} == {
            (1.0, "neat", ""), (0.1, "volume_fraction", "ethanol"),
        }
        assert _check(name, 1.0, "neat", "").status == "PASS"
    assert _check("Neroli EO", 0.1, "volume_fraction", "dpg").status == "FAIL"
    assert _check("Neroli EO", 0.1, "volume_fraction", "ethanol",
                  "inventory:v5:ea88f93dcf37406d817c").status == "FAIL"


def test_successor_preserves_unaffected_stock_objects_variants_and_requirements():
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    predecessor_path = inventory.PROJECT_ROOT / "data/governance/inventory_user_authority_overlay_20260908.json"
    before = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(predecessor_path),
    )
    after = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(inventory.AHSEE_USER_INVENTORY_OVERLAY_PATH),
    )
    untouched = {s.stock_id: asdict(s) for s in before.stocks
                 if not set(s.source_rows).intersection(REPLACED_ROWS)}
    observed = {s.stock_id: asdict(s) for s in after.stocks if s.stock_id in untouched}
    assert observed == untouched
    assert len(after.stocks) == len(before.stocks) + 6
    old_requirements = {r.source_row: asdict(r) for r in before.requirements
                        if r.source_row not in OVERRIDDEN_ROWS}
    assert {r.source_row: asdict(r) for r in after.requirements
            if r.source_row not in OVERRIDDEN_ROWS} == old_requirements
    assert len(after.requirements) == len(before.requirements)
    assert {row for s in after.stocks for row in s.source_rows}.issuperset({10, 14, 267, 269})
    assert not any("high altitude" in s.identity_name.casefold() for s in after.stocks)


def test_source_specific_receipt_does_not_turn_convention_into_measurement():
    head = _raw_head()
    receipt = json.loads((inventory.PROJECT_ROOT / head["source"]["confirmed_receipt"]).read_text(encoding="utf-8"))
    assert receipt["new_direct_confirmation"] == {
        "question": "For the stock check: have you prepared the separate 10% v/v ethanol working stocks of neroli and peppermint, and is your neat PEDMC currently a clear liquid? Please say which are ready.",
        "answer": "yes all",
    }
    records = {r["canonical_name"]: r for r in head["records"]}
    assert records["Lavender EO (BONTAUX SAS)"]["stock"]["fraction_authority"] == "BARE_INVENTORY_ROW_NEAT_CONVENTION_NOT_DIRECT_NEAT_QUOTE"
    for name in ("Tonka Bean Absolute", "Vanillin", "Aldehyde C10", "Aldehyde C12 MNA"):
        assert records[name]["stock"]["fraction_authority"] == "USER_NOMINAL_VOLUMETRIC_CONVENTION_NOT_MEASURED_STOCK_DENSITY"
    assert records["Tonka Bean Absolute"]["stock"]["carrier"] == "dpg"
    assert records["Phenyl Ethyl Dimethyl Carbinol"]["stock"]["phase"] == "USER_CONFIRMED_CLEAR_LIQUID"


def test_lilyreal_owned_fraction_is_supplied_product_and_never_constituent_purity():
    record = next(r for r in _raw_head()["records"] if r["canonical_name"] == "Lilyreal ND")
    stock = record["stock"]
    assert stock["fraction_meaning"] == "UNDILUTED_SUPPLIED_PRODUCT_NOT_IDENTIFIED_ODORANT_PURITY"
    assert stock["material_kind"] == "OPAQUE_PREBLEND"
    assert stock["constituent_fractions"] is None
    assert stock["monomolecular_oav_authority"] is False
    assert stock["fraction"] == 1.0

    from engine.pipeline.formula_state import build_formula_state

    check = _check("Lilyreal ND", 1.0, "neat", "")
    build_formula_state.cache_clear()
    state = build_formula_state(
        {"Lilyreal ND": 360.0}, {"Lilyreal ND": 1.0},
        stock_specs=check.data["resolved_stock_specs"],
    )
    lilyreal = state.materials[0]
    assert lilyreal.is_opaque_preblend is True
    assert lilyreal.oav is None
    assert lilyreal.sources["oav_model"] == "unknown:composite_decomposition_missing"


@pytest.mark.parametrize("field", [
    "predecessor", "live_source", "receipt", "extra_record", "duplicate_record",
    "fraction", "basis", "carrier", "selector", "override", "density", "authority",
    "lilyreal_purity", "bontaux_authority", "prepared_evidence", "inherited_retirement",
])
def test_successor_rejects_semantic_drift_even_when_outer_pin_is_not_the_check(field):
    payload = _raw_head()
    if field == "predecessor":
        payload["predecessor"]["normalized_text_sha256"] = "0" * 64
    elif field == "live_source":
        payload["source"]["inventory_text_sha256"] = "0" * 64
    elif field == "receipt":
        payload["source"]["confirmed_receipt_sha256"] = "0" * 64
    elif field == "extra_record":
        payload["records"].append(copy.deepcopy(payload["records"][0]))
    elif field == "duplicate_record":
        payload["records"][1]["record_id"] = payload["records"][0]["record_id"]
    elif field == "fraction":
        payload["records"][1]["stock"]["fraction"] = 1.0
    elif field == "basis":
        payload["records"][1]["stock"]["fraction_basis"] = "mass_fraction"
    elif field == "carrier":
        payload["records"][1]["stock"]["carrier"] = "dpg"
    elif field == "selector":
        payload["records"][8]["supersedes_parent_stocks"][0]["source_row"] = 10
    elif field == "override":
        payload["records"][4]["requirement_overrides"][0]["disposition"] = "GAP"
    elif field == "density":
        payload["records"][1]["stock"]["density_g_ml"] = 1.0
    elif field == "authority":
        payload["records"][0]["authority_limits"]["safety_asserted"] = True
    elif field == "lilyreal_purity":
        payload["records"][3]["stock"]["constituent_fractions"] = {"lilial": 1.0}
    elif field == "bontaux_authority":
        payload["records"][5]["stock"]["fraction_authority"] = "DIRECT_USER_NEAT_QUOTE"
    elif field == "prepared_evidence":
        payload["records"][1]["evidence_refs"] = []
    else:
        payload["superseded_record_ids"] = ["INV-USER-20260906-001"]
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20260908_ahsee_inventory_successor(payload)


def test_successor_rejects_live_inventory_byte_drift(tmp_path, monkeypatch):
    path = tmp_path / "inventory.txt"
    path.write_bytes(inventory.INVENTORY_PATH.read_bytes() + b" ")
    monkeypatch.setattr(inventory, "INVENTORY_PATH", path)
    with pytest.raises(inventory.InventoryAuthorityError, match="source binding drift"):
        inventory.load_current_user_inventory_overlay()


def test_successor_rejects_confirmation_receipt_byte_drift(tmp_path, monkeypatch):
    payload = _raw_head()
    relative = payload["source"]["confirmed_receipt"]
    altered = tmp_path / relative
    altered.parent.mkdir(parents=True)
    altered.write_bytes((inventory.PROJECT_ROOT / relative).read_bytes() + b" ")
    monkeypatch.setattr(inventory, "PROJECT_ROOT", tmp_path)
    with pytest.raises(inventory.InventoryAuthorityError, match="receipt drift"):
        inventory._load_20260908_ahsee_inventory_successor(payload)


def test_previous_overlays_remain_unchanged_and_historically_loadable():
    for name, expected in (
        ("inventory_user_authority_overlay_20260908.json", "1e5d1cedeeeaa7adef9116f8e4896b5e3e68e10f817fd0ce0338c30187548419"),
        ("inventory_user_authority_overlay_20260907.json", "4868678b5e742b309c929d4021530912630ef7ff172c6a7124a08baa07db7f77"),
        ("inventory_user_authority_overlay_20260906.json", "b06024fdef65355c354a4c5a2618d482f215df42a21c2d56aed896bbfb8c305f"),
    ):
        path = inventory.PROJECT_ROOT / "data/governance" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        assert inventory.load_current_user_inventory_overlay(path)["records"]


def test_calone_keeps_known_dpg_and_only_confirmed_givaudan_aimi_stock_remains():
    assert _check("Calone", 0.01, "volume_fraction", "dpg").status == "PASS"
    assert _check("Calone", 0.01, "volume_fraction", "ethanol").status == "FAIL"
    check = _check("Givaudan AIMI", 1.0, "neat", "")
    assert check.status == "PASS"
    assert check.data["resolved_stock_specs"]["Givaudan AIMI"]["stock_id"] == "inventory:user-20260904:a45ff6250b56cec5bbad"
    assert not any(r["canonical_name"] in {"Givaudan AIMI", "Methyl Ionone Pure", "Alpha Isomethyl Ionone"}
                   for r in _raw_head()["records"])
    current_labels = {r.identity_name for r in inventory.parse_inventory(unique=False)}
    assert "Givaudan AIMI" in current_labels
    assert "Alpha Isomethyl Ionone (Methyl Ionone Pure)" not in current_labels
    receipt_path = inventory.PROJECT_ROOT / _raw_head()["source"]["confirmed_receipt"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["identity_confirmation"]["answer"] == "i only have gividuan AIMI now"
    assert receipt["identity_confirmation"]["new_stock_or_chemical_equivalence_asserted"] is False
