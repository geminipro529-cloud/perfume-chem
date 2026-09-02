import unittest

from stock_basis_repair_and_admission import (
    RepairRule, RowStock, apply_repair, choose_first_pilot, definition_receipt,
    physical_formula_dose_receipt_state, planned_active_equivalent,
    stock_basis_state, validate_v5_sha256,
)


class RepairTests(unittest.TestCase):
    def test_diluted_stock_is_not_neat_after_repair(self):
        row = RowStock("Tonalide 10%", 10.0, 1.0, "neat/as supplied", None, "HOLD")
        rule = RepairRule("Tonalide 10%", 0.1, "10% supplied stock", "DPG")
        fixed = apply_repair(row, rule)
        self.assertEqual(fixed.fraction, 0.1)
        self.assertEqual(fixed.carrier, "DPG")

    def test_ambrox_33_fraction_repair(self):
        row = RowStock("Ambrox Super 33%", 9.0, 1.0, "neat/as supplied", None, "HOLD")
        fixed = apply_repair(row, RepairRule("Ambrox Super 33%", 0.33, "33% supplied stock", None))
        self.assertEqual(fixed.fraction, 0.33)
        self.assertEqual(stock_basis_state(fixed), "PASS_ACTIVE_EQUIVALENCE__HOLD_CARRIER_LINEAGE")

    def test_bourgeonal_tec_repair(self):
        row = RowStock("Bourgeonal 20% in TEC", 4.0, 1.0, "neat/as supplied", None, "HOLD")
        fixed = apply_repair(row, RepairRule("Bourgeonal 20% in TEC", 0.2, "20% w/w", "TEC"))
        self.assertEqual(stock_basis_state(fixed), "PASS_COMPLETE")

    def test_no_rule_preserves_row(self):
        row = RowStock("Iso E Super", 20.0, 1.0, "neat/as supplied", None, "HOLD")
        self.assertEqual(apply_repair(row, None), row)


class ActiveEquivalenceTests(unittest.TestCase):
    def test_planned_active_equivalence(self):
        row = RowStock("X", 25.0, 0.1, "10% supplied stock", "DPG", "HOLD")
        self.assertAlmostEqual(planned_active_equivalent(row), 2.5)

    def test_unknown_carrier_does_not_invalidate_fraction_arithmetic(self):
        row = RowStock("X", 25.0, 0.3, "30% supplied stock", None, "HOLD")
        self.assertAlmostEqual(planned_active_equivalent(row), 7.5)
        self.assertEqual(stock_basis_state(row), "PASS_ACTIVE_EQUIVALENCE__HOLD_CARRIER_LINEAGE")

    def test_invalid_fraction_fails(self):
        row = RowStock("X", 25.0, 0.0, "unknown", None, "HOLD")
        with self.assertRaisesRegex(ValueError, "INVALID_STOCK_FRACTION"):
            planned_active_equivalent(row)

    def test_product_basis_abstains(self):
        row = RowStock("Opaque", 10.0, 1.0, "product basis", None, "HOLD", product_basis=True)
        with self.assertRaisesRegex(ValueError, "PRODUCT_BASIS_ACTIVE_EQUIVALENCE_WITHHELD"):
            planned_active_equivalent(row)

    def test_product_basis_inference_fails(self):
        row = RowStock(
            "Opaque", 10.0, 1.0, "product basis", None, "HOLD",
            product_basis=True, active_equivalent_fraction=0.5
        )
        with self.assertRaisesRegex(ValueError, "PRODUCT_BASIS_ACTIVE_EQUIVALENT_INFERRED"):
            planned_active_equivalent(row)


class ReceiptTests(unittest.TestCase):
    def test_definition_receipt_is_deterministic(self):
        payload = {"formula_id": "CF-01", "rows": [{"material": "A", "share": 1}]}
        self.assertEqual(definition_receipt(payload), definition_receipt(payload))

    def test_missing_exact_stock_ref_holds_physical_fdr(self):
        rows = [RowStock("A", 10, 1, "neat", None, "HOLD_EXACTSTOCKREF")]
        self.assertEqual(physical_formula_dose_receipt_state(rows), "HOLD_EXACTSTOCKREF")

    def test_all_exact_stock_refs_can_become_eligible_not_released(self):
        rows = [RowStock("A", 10, 1, "neat", None, "PASS")]
        self.assertEqual(
            physical_formula_dose_receipt_state(rows),
            "ELIGIBLE_FOR_PHYSICAL_FDR_CONSTRUCTION__NOT_RELEASE",
        )


class PilotSelectionTests(unittest.TestCase):
    def test_cf01_selected_by_readiness(self):
        formulas = [
            {"formula_id": "CF-02", "carrier_open_rows": 3, "corrected_row_uses": 3},
            {"formula_id": "CF-01", "carrier_open_rows": 0, "corrected_row_uses": 0},
            {"formula_id": "CF-10", "carrier_open_rows": 3, "corrected_row_uses": 3},
        ]
        self.assertEqual(choose_first_pilot(formulas), "CF-01")

    def test_selection_is_not_quality_score(self):
        formulas = [
            {"formula_id": "CF-01", "carrier_open_rows": 0, "corrected_row_uses": 0, "quality_score": 0},
            {"formula_id": "CF-02", "carrier_open_rows": 1, "corrected_row_uses": 0, "quality_score": 999},
        ]
        self.assertEqual(choose_first_pilot(formulas), "CF-01")


class GovernanceTests(unittest.TestCase):
    def test_exact_v5_passes(self):
        validate_v5_sha256("e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331")

    def test_wrong_v5_fails(self):
        with self.assertRaisesRegex(ValueError, "CURRENT_V5_SHA256_MISMATCH"):
            validate_v5_sha256("0" * 64)

    def test_physical_authority_is_not_created_by_active_arithmetic(self):
        row = RowStock("X", 10, 0.1, "10% supplied stock", "DPG", "HOLD_EXACTSTOCKREF")
        self.assertEqual(planned_active_equivalent(row), 1.0)
        self.assertEqual(physical_formula_dose_receipt_state([row]), "HOLD_EXACTSTOCKREF")

    def test_unknown_carrier_cannot_be_silently_named(self):
        row = RowStock("Ambrox Super 33%", 10, 0.33, "33% supplied stock", None, "HOLD_EXACTSTOCKREF")
        self.assertEqual(stock_basis_state(row), "PASS_ACTIVE_EQUIVALENCE__HOLD_CARRIER_LINEAGE")
        self.assertIsNone(row.carrier)


if __name__ == "__main__":
    unittest.main()
