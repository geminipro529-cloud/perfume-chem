"""Checkpoint 11 canonical identity, stock, unit, and authority contracts."""

from __future__ import annotations

import math

import pytest

from engine.research.accounting import account_formula_snapshot
from engine.research.contracts import (
    EndpointEstimateV1,
    FormulaComponentV1,
    FormulaSnapshotV1,
    ProductIdentityV1,
    StockLotV1,
    ValidationEnvelopeV2,
    decimal_text,
)


def _product(product_id: str, material_id: str) -> ProductIdentityV1:
    return ProductIdentityV1(
        product_id=product_id,
        material_id=material_id,
        product_name=product_id,
    )


def test_decimal_contract_rejects_boolean_nonfinite_and_negative_values() -> None:
    for value in (True, math.nan, math.inf, -1):
        with pytest.raises(ValueError):
            decimal_text(value, "dose", nonnegative=True)


def test_snapshot_preserves_mass_and_volume_as_separate_totals() -> None:
    snapshot = FormulaSnapshotV1(
        formula_id="r5-design",
        formula_name="Lavande Ambre Profond R5",
        components=(
            FormulaComponentV1("liquids", "lavender-product", None, "5600", "uL"),
            FormulaComponentV1(
                "crystal", "ambrox-crystal-product", None, "300", "mg", operation="MASS_ADD"
            ),
        ),
    )
    result = account_formula_snapshot(
        snapshot,
        products=(
            _product("lavender-product", "lavender-mixture"),
            _product("ambrox-crystal-product", "ambroxide"),
        ),
        stocks=(),
    )

    assert result["physical_totals"] == {"mg": "300", "uL": "5600"}
    assert result["total_active_mass_g_decimal"] is None
    assert result["common_active_mass_basis_available"] is False
    assert result["validation_state"] == "WITHHOLD_UNKNOWN"


def test_w_w_volume_conversion_requires_explicit_stock_density() -> None:
    snapshot = FormulaSnapshotV1(
        formula_id="formula",
        formula_name="Formula",
        components=(FormulaComponentV1("r1", "p1", "s1", "100", "uL"),),
    )
    product = _product("p1", "m1")
    unresolved = account_formula_snapshot(
        snapshot,
        products=(product,),
        stocks=(StockLotV1("s1", "p1", "0.1", "W_W"),),
    )
    assert unresolved["total_active_mass_g_decimal"] is None
    assert unresolved["rows"][0]["reason_codes"] == (
        "STOCK_DENSITY_REQUIRED_FOR_VOLUME_TO_MASS",
    )

    resolved = account_formula_snapshot(
        snapshot,
        products=(product,),
        stocks=(
            StockLotV1(
                "s1",
                "p1",
                "0.1",
                "W_W",
                density_g_ml_decimal="0.8",
                density_provenance="measured-lot-density",
            ),
        ),
    )
    assert resolved["total_active_mass_g_decimal"] == "0.008"
    assert resolved["rows"][0]["carrier_mass_g_decimal"] == "0.072"


def test_equivalent_split_rows_preserve_aggregated_active_mass() -> None:
    product = _product("p1", "m1")
    stock = StockLotV1("s1", "p1", "1", "NEAT")
    one = FormulaSnapshotV1(
        "one", "one", (FormulaComponentV1("r1", "p1", "s1", "100", "mg"),)
    )
    split = FormulaSnapshotV1(
        "split",
        "split",
        (
            FormulaComponentV1("r1a", "p1", "s1", "40", "mg"),
            FormulaComponentV1("r1b", "p1", "s1", "60", "mg"),
        ),
    )
    one_result = account_formula_snapshot(one, products=(product,), stocks=(stock,))
    split_result = account_formula_snapshot(split, products=(product,), stocks=(stock,))
    assert one_result["active_mass_by_material_g"] == split_result["active_mass_by_material_g"]
    assert one_result["total_active_mass_g_decimal"] == "0.1"


def test_formula_hash_binds_order_while_aggregated_exposure_does_not() -> None:
    rows = (
        FormulaComponentV1("r1", "p1", "s1", "40", "mg"),
        FormulaComponentV1("r2", "p1", "s1", "60", "mg"),
    )
    forward = FormulaSnapshotV1("f", "f", rows)
    reverse = FormulaSnapshotV1("f", "f", tuple(reversed(rows)))
    assert forward.sha256 != reverse.sha256
    product = _product("p1", "m1")
    stock = StockLotV1("s1", "p1", "1", "NEAT")
    assert account_formula_snapshot(
        forward, products=(product,), stocks=(stock,)
    )["active_mass_by_material_g"] == account_formula_snapshot(
        reverse, products=(product,), stocks=(stock,)
    )["active_mass_by_material_g"]


def test_endpoint_and_validation_contracts_cannot_grant_action_authority() -> None:
    with pytest.raises(ValueError, match="cannot grant"):
        EndpointEstimateV1(
            endpoint="INTENSITY",
            value=1.0,
            unit="source-scale",
            coverage_decimal="1",
            applicability_state="APPLICABLE",
            uncertainty_interval=None,
            provenance_ids=("capability",),
            authority={"release_authority": True},
        )
    with pytest.raises(ValueError, match="cannot grant"):
        ValidationEnvelopeV2(
            state="ADVISORY_COMPLETE",
            applicability_state="APPLICABLE",
            authority={"compounding_authority": True},
        )


def test_missing_information_never_becomes_neutral_or_zero() -> None:
    estimate = EndpointEstimateV1(
        endpoint="PLEASANTNESS",
        value=None,
        unit=None,
        coverage_decimal="0",
        applicability_state="UNAVAILABLE",
        uncertainty_interval=None,
        provenance_ids=(),
        reason_codes=("NO_HUMAN_LABEL_CAPABILITY",),
    )
    assert estimate.value is None
    assert estimate.applicability_state == "UNAVAILABLE"
    assert estimate.coverage_decimal == "0"
