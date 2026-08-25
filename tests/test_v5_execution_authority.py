from __future__ import annotations

from engine.pipeline.v5_execution_authority import (
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


def test_unresolved_exact_stock_ref_is_physical_hold():
    result = evaluate_reconciliation_row(_row())

    assert result.design_allowed is True
    assert result.current_inventory_build_allowed is True
    assert result.physical_execution_allowed is False
    assert "EXACTSTOCKREF_UNRESOLVED" in result.reasons
    assert "PHYSICAL_GATE_HOLD" in result.reasons


def test_ambrettolide_is_design_available_but_not_current_physical_stock():
    result = evaluate_reconciliation_row(
        _row(
            Material="Ambrettolide 10%",
            **{
                "V5 Canonical Material": "Ambrettolide 10%",
                "V5 Status": "PLANNED ACQUISITION • DESIGN-AVAILABLE",
                "V5 Actual Stock(s)": "Ambrettolide 10% in DPG planned; physical receipt pending",
                "V5 Can Prepare": "Create or verify exact 10% in DPG stock after acquisition.",
                "V5 Formula-Use Policy": (
                    "Usable in computational formula design, accord architecture and screen planning. "
                    "A physical batch may not claim Ambrettolide use until receipt and ExactStockRef are recorded."
                ),
                "V5 User Note": (
                    "User instructed on 2026-08-07 to treat Ambrettolide as available for design because purchase is planned."
                ),
                "Final Execution State": "HOLD — PROCUREMENT PENDING + EXACTSTOCKREF UNRESOLVED",
            },
        )
    )

    assert result.v5_status_class == "PLANNED_DESIGN_AVAILABLE"
    assert result.design_allowed is True
    assert result.current_inventory_build_allowed is False
    assert result.physical_execution_allowed is False
    assert "PLANNED_MATERIAL_NOT_PHYSICALLY_OWNED" in result.reasons


def test_orris_product_basis_does_not_require_molecular_active_fraction():
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
    assert result.design_allowed is True
    assert result.quantitative_design_allowed is True
    assert result.physical_execution_allowed is False


def test_v5_gap_overrides_workbook_have_for_current_inventory_use():
    result = evaluate_reconciliation_row(
        _row(
            Material="Guaiacwood EO",
            **{
                "Workbook Inventory Status": "HAVE — PHOTO VERIFIED / ESSENTIAL OIL",
                "Workbook Stock Description": "PerfumersWorld Guaiacwood Essential Oil; as supplied",
                "Workbook Active Fraction": 1,
                "Workbook Carrier": "DEP",
                "V5 Canonical Material": "Guaiacwood EO",
                "V5 Status": "GAP",
                "V5 Actual Stock(s)": "",
                "V5 Formula-Use Policy": "Do not substitute silently; target-required material is not in stock.",
            },
        )
    )

    assert result.v5_status_class == "UNAVAILABLE"
    assert result.design_allowed is False
    assert result.current_inventory_build_allowed is False
    assert result.physical_execution_allowed is False
    assert "V5_STATUS_UNAVAILABLE" in result.reasons


def test_v5_policy_conflict_prevents_neat_quantitative_model():
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

    assert result.design_allowed is True
    assert result.quantitative_design_allowed is False
    assert result.physical_execution_allowed is False
    assert "ACTIVE_FRACTION_CONFLICT_WITH_V5_POLICY" in result.reasons


def test_hypothetical_resolved_stock_can_become_physical_ready():
    result = evaluate_reconciliation_row(
        _row(
            **{
                "Workbook ExactStockRef": "stock:test-material:2026-08-25:001",
                "Workbook Physical Gate": "PASS",
                "Final Execution State": "READY",
            }
        )
    )

    assert result.current_inventory_build_allowed is True
    assert result.quantitative_design_allowed is True
    assert result.physical_execution_allowed is True


def test_formula_adapter_never_assumes_neat_when_fraction_is_missing():
    formula = {
        "ingredients_ul": {"Hedione": 100.0},
        "dilutions": {},
        "stock_specs": {
            "Hedione": {
                "v5_status": "HAVE",
                "v5_canonical_material": "Hedione",
                "stock_description": "neat / as supplied",
                "physical_gate": "HOLD",
                "exact_stock_ref": "UNRESOLVED",
            }
        },
    }

    report = evaluate_formula_stock_specs(formula, mode="RECONSTRUCTION")
    row = report.rows[0]

    assert row.active_fraction is None
    assert row.quantitative_design_allowed is False
    assert "ACTIVE_FRACTION_NOT_STRUCTURED" in row.reasons
    assert report.allowed is True
    assert "Hedione:QUANTITATIVE_DESIGN_HOLD" in report.warnings


def test_formula_adapter_preserves_planned_design_availability():
    formula = {
        "ingredients_ul": {"Ambrettolide 10%": 20.0},
        "dilutions": {"Ambrettolide 10%": 0.1},
        "stock_specs": {
            "Ambrettolide 10%": {
                "fraction": 0.1,
                "carrier": "DPG",
                "v5_status": "PLANNED ACQUISITION / DESIGN-AVAILABLE",
                "v5_canonical_material": "Ambrettolide 10%",
                "v5_actual_stocks": "Ambrettolide 10% in DPG planned; physical receipt pending",
                "v5_formula_use_policy": "Usable in computational formula design only until receipt and ExactStockRef exist.",
                "physical_gate": "HOLD",
                "exact_stock_ref": "UNRESOLVED",
                "final_execution_state": "HOLD — PROCUREMENT PENDING + EXACTSTOCKREF UNRESOLVED",
            }
        },
    }

    design = evaluate_formula_stock_specs(formula, mode="RECONSTRUCTION")
    physical = evaluate_formula_stock_specs(formula, mode="LIVE_BATCH")

    assert design.allowed is True
    assert design.status == "DESIGN_ALLOWED"
    assert design.physical_execution_allowed is False
    assert physical.allowed is False
    assert physical.status == "HOLD"
