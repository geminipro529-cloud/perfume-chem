from __future__ import annotations

from dataclasses import replace

import pytest

from engine.pipeline.preflight import FormulaDoseLineReceipt, FormulaDoseReceipt
from engine.pipeline.state_authorization import build_authorized_formula_state
from engine.pipeline.stock_authority_spine import (
    ExactStockRef,
    PreparedRun,
    StockAuthorityError,
)


def _receipt(*, status: str = "BOUND") -> FormulaDoseReceipt:
    if status == "BOUND":
        line = FormulaDoseLineReceipt(
            material_name="Hedione",
            raw_ul=20.0,
            active_ul=20.0,
            stock_fraction=1.0,
            fraction_basis="neat",
            carrier="",
            stock_id="v5row:test",
            stock_authority="V5_INVENTORY_ROW",
            inventory_authority="v5@test",
            source_rows=(1,),
            status="BOUND",
        )
        reasons = ()
    else:
        line = FormulaDoseLineReceipt(
            material_name="Hedione",
            raw_ul=20.0,
            active_ul=None,
            stock_fraction=None,
            fraction_basis="unspecified",
            carrier="",
            stock_id=None,
            stock_authority=None,
            inventory_authority="v5@test",
            source_rows=(),
            status="ABSTAINED",
            blockers=("stock_fraction_unknown",),
        )
        reasons = ("Hedione:stock_fraction_unknown",)
    return FormulaDoseReceipt(
        formula_name="x",
        formula_input_sha256="1" * 64,
        legacy_formula_hash="2" * 64,
        inventory_snapshot_sha256="3" * 64,
        inventory_source_workbook_sha256="4" * 64,
        inventory_authority_sheet="Ingredient Master",
        lines=(line,),
        status=status,
        reasons=reasons,
    )


class SpyBuilder:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return {"args": args, "kwargs": kwargs}


def test_abstained_receipt_never_calls_formula_state_builder():
    spy = SpyBuilder()
    with pytest.raises(StockAuthorityError):
        build_authorized_formula_state(
            _receipt(status="ABSTAINED"),
            spy,
            1,
            scope="CURRENT_INVENTORY_BUILD",
        )
    assert spy.calls == 0


def test_bound_current_receipt_calls_formula_state_builder_once():
    spy = SpyBuilder()
    result = build_authorized_formula_state(
        _receipt(),
        spy,
        1,
        scope="CURRENT_INVENTORY_BUILD",
        flag=True,
    )
    assert spy.calls == 1
    assert result["args"] == (1,)
    assert result["kwargs"] == {"flag": True}


def test_physical_scope_without_prepared_run_never_calls_builder():
    spy = SpyBuilder()
    with pytest.raises(StockAuthorityError):
        build_authorized_formula_state(
            _receipt(),
            spy,
            scope="PHYSICAL_EXECUTION",
        )
    assert spy.calls == 0


def test_physical_scope_with_matching_prepared_run_calls_builder_once():
    spy = SpyBuilder()
    receipt = _receipt()
    ref = ExactStockRef(
        ref_id="stock:hedione:001",
        inventory_stock_id="v5row:test",
        material="Hedione",
        inventory_snapshot_sha256=receipt.inventory_snapshot_sha256,
        source_row=1,
        stock_description="Hedione neat",
        active_fraction=1.0,
        fraction_basis="neat",
        carrier="",
    )
    prepared = PreparedRun(
        run_id="run-1",
        formula_receipt_sha256=receipt.receipt_sha256,
        inventory_snapshot_sha256=receipt.inventory_snapshot_sha256,
        exact_stock_refs=(ref,),
    )
    result = build_authorized_formula_state(
        receipt,
        spy,
        scope="PHYSICAL_EXECUTION",
        prepared_run=prepared,
    )
    assert spy.calls == 1
    assert result["args"] == ()
