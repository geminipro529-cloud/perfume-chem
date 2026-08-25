from __future__ import annotations

from dataclasses import replace

import pytest

from engine.pipeline.stock_authority_spine import (
    StockAuthorityError,
    V5InventorySnapshot,
    V5StockRecord,
    bind_exact_stock_ref,
    build_formula_dose_receipt_from_snapshot,
    prepare_run,
    require_formula_state_authority,
)

V5_SHA = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"


def rec(
    name,
    *,
    frac=1.0,
    basis="neat",
    carrier="",
    owned=True,
    product_basis=False,
    source_row=1,
):
    return V5StockRecord(
        material=name,
        stock_description=name,
        active_fraction=frac,
        fraction_basis=basis,
        carrier=carrier,
        inventory_owned=owned,
        product_basis=product_basis,
        source_row=source_row,
    )


def snap(*records):
    return V5InventorySnapshot.build(
        authority_filename="Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx",
        authority_sha256=V5_SHA,
        authority_sheet="Ingredient Master",
        records=records,
    )


def test_10pct_volume_stock_yields_two_ul_active():
    snapshot = snap(rec("Test 10%", frac=0.1, basis="volume_fraction", carrier="DPG"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Test 10%": 20.0}}, snapshot
    )
    assert receipt.status == "BOUND"
    assert receipt.lines[0].active_ul == 2.0


def test_missing_fraction_never_becomes_neat():
    snapshot = snap(rec("Unknown", frac=None, basis="unspecified"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Unknown": 20.0}}, snapshot
    )
    assert receipt.status == "ABSTAINED"
    assert receipt.lines[0].active_ul is None
    assert "stock_fraction_unknown" in receipt.lines[0].blockers


def test_mass_fraction_is_not_labeled_active_ul():
    snapshot = snap(
        rec("Alpha Irone 30%", frac=0.3, basis="mass_fraction", carrier="IPM")
    )
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Alpha Irone 30%": 20.0}}, snapshot
    )
    assert receipt.status == "ABSTAINED"
    assert receipt.lines[0].active_ul is None
    assert "mass_basis_requires_mass_quantity_model" in receipt.lines[0].blockers


def test_product_basis_never_gets_fictional_active_equivalent():
    snapshot = snap(
        rec(
            "Orris Liquid",
            frac=None,
            basis="product_basis",
            product_basis=True,
        )
    )
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Orris Liquid": 20.0}}, snapshot
    )
    assert receipt.status == "ABSTAINED"
    assert receipt.lines[0].active_ul is None
    assert "product_basis_active_equivalent_not_defined" in receipt.lines[0].blockers


def test_owned_hold_semantics_are_compatible_with_current_build_receipt():
    # HOLD is represented by owned=True, never by an inventory-absence state.
    snapshot = snap(rec("Hedione", frac=1.0, basis="neat", owned=True))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    assert receipt.status == "BOUND"


def test_inventory_gap_abstains():
    snapshot = snap(rec("Gap", frac=1.0, basis="neat", owned=False))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Gap": 20.0}}, snapshot
    )
    assert receipt.status == "ABSTAINED"
    assert "inventory_not_owned" in receipt.lines[0].blockers


def test_snapshot_rejects_duplicate_canonical_rows():
    with pytest.raises(StockAuthorityError):
        snap(rec("Hedione", source_row=1), rec("hedione", source_row=2))


def test_zero_active_fraction_does_not_construct_invalid_bound_receipt():
    snapshot = snap(rec("DPG", frac=0.0, basis="volume_fraction", carrier="DPG"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"DPG": 20.0}}, snapshot
    )
    assert receipt.status == "ABSTAINED"
    assert receipt.lines[0].stock_fraction is None
    assert "zero_active_fraction_requires_carrier_quantity_model" in receipt.lines[0].blockers


def test_prepared_run_requires_exact_ref_for_every_bound_line():
    snapshot = snap(rec("Hedione"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    with pytest.raises(StockAuthorityError):
        prepare_run("run-1", receipt, snapshot, exact_stock_refs=())


def test_exact_stock_ref_is_downstream_of_v5_snapshot():
    snapshot = snap(rec("Hedione"))
    ref = bind_exact_stock_ref(snapshot, "Hedione", ref_id="stock:hedione:001")
    assert ref.ref_id == "stock:hedione:001"
    assert ref.inventory_snapshot_sha256 == snapshot.snapshot_sha256
    assert ref.inventory_stock_id == snapshot.stock_id(snapshot.resolve("Hedione"))


def test_prepared_run_binds_explicit_exact_ref():
    snapshot = snap(rec("Hedione"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    ref = bind_exact_stock_ref(snapshot, "Hedione", ref_id="stock:hedione:001")
    prepared = prepare_run(
        "run-1", receipt, snapshot, exact_stock_refs=(ref,)
    )
    assert prepared.status == "BOUND"
    assert prepared.formula_receipt_sha256 == receipt.receipt_sha256
    assert prepared.exact_stock_refs[0].ref_id == "stock:hedione:001"


def test_explicit_stock_binding_survives_into_prepared_run():
    snapshot = snap(
        rec("Heliotropal 10%", frac=0.1, basis="volume_fraction", source_row=2)
    )
    receipt = build_formula_dose_receipt_from_snapshot(
        {
            "name": "x",
            "ingredients_ul": {"Heliotropal": 20.0},
            "stock_bindings": {"Heliotropal": "Heliotropal 10%"},
        },
        snapshot,
    )
    ref = bind_exact_stock_ref(
        snapshot, "Heliotropal 10%", ref_id="stock:heliotropal10:001"
    )
    prepared = prepare_run(
        "run-1", receipt, snapshot, exact_stock_refs=(ref,)
    )
    assert prepared.status == "BOUND"
    assert prepared.exact_stock_refs[0].inventory_stock_id == receipt.lines[0].stock_id


def test_formula_state_authority_current_vs_physical():
    snapshot = snap(rec("Hedione"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    assert (
        require_formula_state_authority(
            receipt, scope="CURRENT_INVENTORY_BUILD"
        )
        is True
    )
    with pytest.raises(StockAuthorityError):
        require_formula_state_authority(receipt, scope="PHYSICAL_EXECUTION")


def test_prepared_run_never_grants_sensory_or_release_authority():
    snapshot = snap(rec("Hedione"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    ref = bind_exact_stock_ref(snapshot, "Hedione", ref_id="stock:hedione:001")
    payload = prepare_run(
        "run-1", receipt, snapshot, exact_stock_refs=(ref,)
    ).as_dict()
    assert payload["sensory_authority"] is False
    assert payload["liking_authority"] is False
    assert payload["safety_authority"] is False
    assert payload["release_authority"] is False


def test_prepared_run_rejects_forged_exact_ref_metadata():
    snapshot = snap(rec("Hedione"))
    receipt = build_formula_dose_receipt_from_snapshot(
        {"name": "x", "ingredients_ul": {"Hedione": 20.0}}, snapshot
    )
    ref = bind_exact_stock_ref(snapshot, "Hedione", ref_id="stock:hedione:001")
    forged = replace(ref, material="Not Hedione")
    with pytest.raises(StockAuthorityError):
        prepare_run(
            "run-1", receipt, snapshot, exact_stock_refs=(forged,)
        )
