from __future__ import annotations

from engine.pipeline.v5_execution_authority import (
    CURRENT_INVENTORY_BUILD,
    PHYSICAL_EXECUTION,
    TARGET_IDEAL,
    evaluate_formula_stock_specs,
    evaluate_reconciliation_row,
)


def _row(**overrides):
    row = {
        "Material": "Test Material",
        "Uses": "1",
        "Workbook Inventory Status": "HAVE",
        "Workbook Stock Description": "10% in DPG",
        "Workbook Active Fraction": 0.1,
        "Workbook Carrier": "DPG",
        "Workbook ExactStockRef": "UNRESOLVED",
        "Workbook Physical Gate": "HOLD",
        "V5 Match Method": "EXACT_CANONICAL",
        "V5 Canonical Material": "Test Material",
        "V5 Status": "HAVE",
        "V5 Actual Stock(s)": "10% in DPG",
        "V5 Can Prepare": "",
        "V5 Formula-Use Policy": "Use only at the listed supplied-stock strength.",
        "V5 User Note": "",
        "Final Execution State": "HOLD — EXACTSTOCKREF UNRESOLVED",
    }
    row.update(overrides)
    return row


def test_hold_means_have_not_inventory_gap():
    result = evaluate_reconciliation_row(_row())

    assert result.inventory_owned is True
    assert result.hold_means_have is True
    assert result.current_inventory_build_allowed is True
    assert result.design_allowed is True
    assert result.physical_execution_allowed is False
    assert "HOLD_PRESERVES_HAVE" in result.reasons
    assert "V5_STATUS_UNAVAILABLE" not in result.reasons


def test_unresolved_exact_stock_ref_blocks_only_physical_execution():
    result = evaluate_reconciliation_row(_row())

    assert result.inventory_owned is True
    assert result.current_inventory_build_allowed is True
    assert result.physical_execution_allowed is False
    assert "EXACTSTOCKREF_UNRESOLVED" in result.reasons
    assert "PHYSICAL_GATE_NOT_READY" in result.reasons
    assert "FINAL_EXECUTION_NOT_READY" in result.reasons


def test_hold_have_survives_missing_v5_canonical_mapping():
    result = evaluate_reconciliation_row(
        _row(
            Material="Turkish Storax Tincture 20%",
            **{
                "Workbook Inventory Status": "HAVE — HISTORY CONFIRMED",
                "V5 Match Method": "NO_EXACT_V5_MATCH",
                "V5 Canonical Material": "",
                "V5 Status": "",
                "V5 Actual Stock(s)": "",
            },
        )
    )

    assert result.inventory_owned is True
    assert result.current_inventory_build_allowed is True
    assert result.design_allowed is True
    assert result.physical_execution_allowed is False
    assert "V5_MAPPING_UNRESOLVED" in result.reasons
    assert "HOLD_PRESERVES_HAVE" in result.reasons


def test_target_ideal_is_not_redefined_by_v5_gap():
    result = evaluate_reconciliation_row(
        _row(
            Material="Guaiacwood EO",
            **{
                "Workbook Inventory Status": "HAVE — PHOTO VERIFIED / ESSENTIAL OIL",
                "V5 Canonical Material": "Guaiacwood EO",
                "V5 Status": "GAP",
                "V5 Actual Stock(s)": "",
                "V5 Formula-Use Policy": "Do not substitute silently; target-required material is not in stock.",
            },
        )
    )

    assert result.design_allowed is True
    assert result.inventory_owned is False
    assert result.current_inventory_build_allowed is False
    assert result.physical_execution_allowed is False
    assert "V5_STATUS_UNAVAILABLE" in result.reasons


def test_planned_ambrettolide_remains_target_design_available_only():
    result = evaluate_reconciliation_row(
        _row(
            Material="Ambrettolide 10%",
            **{
                "V5 Canonical Material": "Ambrettolide 10%",
                "V5 Status": "PLANNED ACQUISITION • DESIGN-AVAILABLE",
                "V5 Actual Stock(s)": "Ambrettolide 10% in DPG planned; physical receipt pending",
                "V5 Formula-Use Policy": (
                    "Usable in computational formula design, accord architecture and screen planning. "
                    "A physical batch may not claim Ambrettolide use until receipt and ExactStockRef are recorded."
                ),
                "Final Execution State": "HOLD — PROCUREMENT PENDING + EXACTSTOCKREF UNRESOLVED",
            },
        )
    )

    assert result.v5_status_class == "PLANNED_DESIGN_AVAILABLE"
    assert result.design_allowed is True
    assert result.inventory_owned is False
    assert result.current_inventory_build_allowed is False
    assert result.physical_execution_allowed is False


def test_orris_product_basis_is_not_forced_into_guessed_active_equivalent():
    result = evaluate_reconciliation_row(
        _row(
            Material="Orris Liquid",
            **{
                "Workbook Stock Description": (
                    "PerfumersWorld Orris Liquid, as supplied; proprietary/product composition not converted to a single active fraction"
                ),
                "Workbook Active Fraction": 1,
                "Workbook Carrier": "AS SUPPLIED / NOT RESTATED",
                "V5 Match Method": "ACTUAL_STOCK_TEXT_CONTAINS",
                "V5 Canonical Material": "Orris Liquid — PerfumersWorld product basis",
                "V5 Status": "HAVE — PRODUCT BASIS",
                "V5 Actual Stock(s)": (
                    "PerfumersWorld Orris Liquid, as supplied; proprietary/product composition not converted to a single active fraction"
                ),
                "V5 Formula-Use Policy": (
                    "Use only as a named product-basis material. Do not calculate active-equivalent concentration from a guessed 30%."
                ),
            },
        )
    )

    assert result.product_basis is True
    assert result.inventory_owned is True
    assert result.current_inventory_build_allowed is True
    assert result.quantitative_design_allowed is True


def test_stock_policy_conflict_blocks_quantitative_current_build_not_ownership():
    result = evaluate_reconciliation_row(
        _row(
            Material="Sandalwood EO 10% in DPG",
            **{
                "Workbook Stock Description": "Sandalwood EO 10% in DPG",
                "Workbook Active Fraction": 1,
                "Workbook Carrier": "DPG",
                "V5 Match Method": "EXACT_ACTUAL_STOCK",
                "V5 Canonical Material": "Sandalwood EO",
                "V5 Status": "HAVE — 10% IN DPG ONLY",
                "V5 Actual Stock(s)": "Sandalwood EO 10% in DPG",
                "V5 Formula-Use Policy": "Do not dose or model as neat Sandalwood EO.",
            },
        )
    )

    assert result.inventory_owned is True
    assert result.current_inventory_build_allowed is True
    assert result.quantitative_design_allowed is False
    assert "ACTIVE_FRACTION_CONFLICT_WITH_V5_POLICY" in result.reasons


def test_resolved_ready_stock_can_become_physical_ready():
    result = evaluate_reconciliation_row(
        _row(
            **{
                "Workbook ExactStockRef": "stock:test-material:2026-08-25:001",
                "Workbook Physical Gate": "PASS",
                "Final Execution State": "READY",
            }
        )
    )

    assert result.inventory_owned is True
    assert result.current_inventory_build_allowed is True
    assert result.quantitative_design_allowed is True
    assert result.physical_execution_allowed is True


def test_formula_target_scope_never_lets_inventory_redefine_target():
    formula = {
        "ingredients_ul": {"Missing Target Material": 20.0},
        "dilutions": {"Missing Target Material": 0.1},
        "stock_specs": {
            "Missing Target Material": {
                "fraction": 0.1,
                "v5_status": "GAP",
                "v5_canonical_material": "Missing Target Material",
                "physical_gate": "HOLD",
                "exact_stock_ref": "UNRESOLVED",
            }
        },
    }

    target = evaluate_formula_stock_specs(
        formula,
        mode="RECONSTRUCTION",
        scope=TARGET_IDEAL,
    )
    current = evaluate_formula_stock_specs(
        formula,
        mode="INVENTORY_MAPPING",
        scope=CURRENT_INVENTORY_BUILD,
    )

    assert target.allowed is True
    assert target.status == "TARGET_IDEAL_ALLOWED"
    assert current.allowed is False
    assert current.status == "CURRENT_BUILD_HOLD"


def test_formula_adapter_never_assumes_neat_when_fraction_is_missing():
    formula = {
        "ingredients_ul": {"Hedione": 100.0},
        "dilutions": {},
        "stock_specs": {
            "Hedione": {
                "workbook_inventory_status": "HAVE",
                "v5_status": "HAVE",
                "v5_canonical_material": "Hedione",
                "stock_description": "neat / as supplied",
                "physical_gate": "HOLD",
                "exact_stock_ref": "UNRESOLVED",
            }
        },
    }

    target = evaluate_formula_stock_specs(
        formula,
        mode="RECONSTRUCTION",
        scope=TARGET_IDEAL,
    )
    current = evaluate_formula_stock_specs(
        formula,
        mode="INVENTORY_MAPPING",
        scope=CURRENT_INVENTORY_BUILD,
    )

    row = target.rows[0]
    assert row.inventory_owned is True
    assert row.active_fraction is None
    assert row.quantitative_design_allowed is False
    assert "ACTIVE_FRACTION_NOT_STRUCTURED" in row.reasons
    assert target.allowed is True
    assert current.allowed is False


def test_physical_scope_requires_exact_binding_even_when_hold_means_have():
    formula = {
        "ingredients_ul": {"Hedione": 100.0},
        "dilutions": {"Hedione": 1.0},
        "stock_specs": {
            "Hedione": {
                "fraction": 1.0,
                "workbook_inventory_status": "HAVE",
                "v5_status": "HAVE",
                "v5_canonical_material": "Hedione",
                "physical_gate": "HOLD",
                "exact_stock_ref": "UNRESOLVED",
                "final_execution_state": "HOLD — EXACTSTOCKREF UNRESOLVED",
            }
        },
    }

    physical = evaluate_formula_stock_specs(
        formula,
        mode="LIVE_BATCH",
        scope=PHYSICAL_EXECUTION,
    )

    assert physical.rows[0].inventory_owned is True
    assert physical.rows[0].hold_means_have is True
    assert physical.allowed is False
    assert physical.status == "PHYSICAL_HOLD"
