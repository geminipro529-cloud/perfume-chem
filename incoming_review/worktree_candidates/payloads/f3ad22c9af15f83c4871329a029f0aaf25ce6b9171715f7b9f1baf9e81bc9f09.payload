from decimal import Decimal
import unittest

from perfume_chem_v20_guardrails.canonical import CanonicalizationError
from perfume_chem_v20_guardrails.exact_quantities import (
    AmountKind,
    ConcentrationBasis,
    DensityEvidence,
    DoseLine,
    QuantityHold,
    StockLifecycle,
    StockSpec,
    build_formula_dose_receipt,
    physical_stock_gate,
    resolve_active_amount,
    screening_claim_boundary,
)


INV_SHA = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"


def stock(**overrides):
    values = dict(
        stock_id="STK-1",
        material_id="MAT-1",
        active_fraction="0.10",
        concentration_basis=ConcentrationBasis.MASS_FRACTION,
        carrier="DPG",
        product_basis=False,
        lifecycle=StockLifecycle.OWNED,
        exact_stock_ref="EXACT-STOCK-1",
    )
    values.update(overrides)
    return StockSpec.create(**values)


class ExactQuantityTests(unittest.TestCase):
    def test_binary_float_is_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            StockSpec.create(
                stock_id="S",
                material_id="M",
                active_fraction=0.1,  # type: ignore[arg-type]
                concentration_basis=ConcentrationBasis.MASS_FRACTION,
                carrier="DPG",
                product_basis=False,
                lifecycle=StockLifecycle.OWNED,
                exact_stock_ref="E",
            )

    def test_missing_strength_never_becomes_neat(self) -> None:
        s = stock(
            active_fraction=None,
            concentration_basis=ConcentrationBasis.UNKNOWN,
            carrier=None,
        )
        line = DoseLine.create(line_id="L", raw_amount="1", raw_kind=AmountKind.MASS, stock=s)
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "MISSING_ACTIVE_FRACTION")

    def test_unknown_carrier_stays_unknown(self) -> None:
        s = stock(carrier=None)
        line = DoseLine.create(line_id="L", raw_amount="1", raw_kind=AmountKind.MASS, stock=s)
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "UNKNOWN_DILUENT")

    def test_opaque_product_basis_cannot_receive_fraction(self) -> None:
        with self.assertRaises(QuantityHold) as ctx:
            stock(product_basis=True)
        self.assertEqual(ctx.exception.code, "OPAQUE_PRODUCT_BASIS")

    def test_opaque_product_basis_remains_opaque(self) -> None:
        s = stock(
            product_basis=True,
            active_fraction=None,
            concentration_basis=ConcentrationBasis.UNKNOWN,
            carrier=None,
        )
        line = DoseLine.create(line_id="L", raw_amount="1", raw_kind=AmountKind.MASS, stock=s)
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "OPAQUE_PRODUCT_BASIS")

    def test_mass_and_volume_fraction_not_interchangeable(self) -> None:
        s = stock(concentration_basis=ConcentrationBasis.VOLUME_FRACTION)
        line = DoseLine.create(line_id="L", raw_amount="1", raw_kind=AmountKind.MASS, stock=s)
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "BASIS_MISMATCH")

    def test_cross_basis_requires_density(self) -> None:
        s = stock()
        line = DoseLine.create(line_id="L", raw_amount="1", raw_kind=AmountKind.VOLUME, stock=s)
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "MISSING_DENSITY")

    def test_conditioned_density_allows_volume_to_mass(self) -> None:
        density = DensityEvidence.create(
            value_g_per_ml="0.95",
            temperature_c="25",
            pressure_kpa="101.325",
            source_ref="lot-specific SDS",
            measured_or_authoritative=True,
        )
        line = DoseLine.create(
            line_id="L", raw_amount="2", raw_kind=AmountKind.VOLUME, stock=stock(), density=density
        )
        active = resolve_active_amount(line)
        self.assertEqual(active.value, Decimal("0.190"))
        self.assertEqual(active.kind, AmountKind.MASS)

    def test_advisory_density_cannot_authorize_conversion(self) -> None:
        density = DensityEvidence.create(
            value_g_per_ml="0.95",
            temperature_c="25",
            pressure_kpa=None,
            source_ref="generic estimate",
            measured_or_authoritative=False,
        )
        line = DoseLine.create(
            line_id="L", raw_amount="2", raw_kind=AmountKind.VOLUME, stock=stock(), density=density
        )
        with self.assertRaises(QuantityHold) as ctx:
            resolve_active_amount(line)
        self.assertEqual(ctx.exception.code, "DENSITY_NOT_AUTHORITATIVE")

    def test_planned_acquisition_is_not_physically_owned(self) -> None:
        s = stock(lifecycle=StockLifecycle.PLANNED_ACQUISITION, exact_stock_ref=None)
        with self.assertRaises(QuantityHold) as ctx:
            physical_stock_gate(s)
        self.assertEqual(ctx.exception.code, "PLANNED_NOT_PHYSICAL")

    def test_preparable_is_not_prepared(self) -> None:
        s = stock(lifecycle=StockLifecycle.PREPARABLE, exact_stock_ref=None)
        with self.assertRaises(QuantityHold) as ctx:
            physical_stock_gate(s)
        self.assertEqual(ctx.exception.code, "PREPARATION_RECEIPT_REQUIRED")

    def test_exact_owned_stock_resolves_dose_accounting(self) -> None:
        line = DoseLine.create(line_id="L", raw_amount="2", raw_kind=AmountKind.MASS, stock=stock())
        receipt = build_formula_dose_receipt(
            formula_id="F", inventory_source_sha256=INV_SHA, lines=[line]
        )
        self.assertEqual(receipt.state, "RESOLVED_FOR_DOSE_ACCOUNTING")
        self.assertFalse(receipt.physical_execution_authorized)
        self.assertFalse(receipt.release_authority)
        self.assertEqual(receipt.lines[0].active_amount.value, Decimal("0.20"))  # type: ignore[union-attr]

    def test_hold_receipt_preserves_false_authority(self) -> None:
        s = stock(active_fraction=None, concentration_basis=ConcentrationBasis.UNKNOWN, carrier=None)
        line = DoseLine.create(line_id="L", raw_amount="2", raw_kind=AmountKind.MASS, stock=s)
        receipt = build_formula_dose_receipt(
            formula_id="F", inventory_source_sha256=INV_SHA, lines=[line]
        )
        self.assertEqual(receipt.state, "HOLD")
        self.assertFalse(receipt.physical_execution_authorized)
        self.assertEqual(receipt.lines[0].hold_code, "MISSING_ACTIVE_FRACTION")

    def test_screening_cannot_become_release_or_sensory_authority(self) -> None:
        boundary = screening_claim_boundary()
        self.assertFalse(boundary["formula_release_authority"])
        self.assertFalse(boundary["sensory_authority"])
        self.assertFalse(boundary["physical_authority"])
        self.assertFalse(boundary["strict_empirical_oav_authority"])


if __name__ == "__main__":
    unittest.main()
