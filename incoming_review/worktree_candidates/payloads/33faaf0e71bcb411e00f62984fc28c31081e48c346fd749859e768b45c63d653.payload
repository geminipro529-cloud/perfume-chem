from decimal import Decimal
import unittest

from perfume_chem_v20_guardrails.canonical import CanonicalizationError
from perfume_chem_v20_guardrails.formula_artifact import (
    ArtifactBinding,
    DriftClass,
    FormulaArtifactError,
    FormulaPartLine,
    classify_reviewed_change,
    recompute_dose_export,
    rebind_preflight,
    validate_binding,
)


PARENT = "a" * 64


class FormulaArtifactTests(unittest.TestCase):
    def lines(self):
        return [
            FormulaPartLine.create(line_id="A", parts_per_1000="333.3333"),
            FormulaPartLine.create(line_id="B", parts_per_1000="333.3333"),
            FormulaPartLine.create(line_id="C", parts_per_1000="333.3334"),
        ]

    def test_binary_float_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            FormulaPartLine.create(line_id="A", parts_per_1000=1.1)  # type: ignore[arg-type]

    def test_formula_must_total_exactly_1000(self) -> None:
        with self.assertRaises(FormulaArtifactError):
            recompute_dose_export(
                formula_id="F",
                parent_formula_hash=PARENT,
                lines=[FormulaPartLine.create(line_id="A", parts_per_1000="999.9")],
                concentrate_ul="4500",
            )

    def test_exact_export_closes_without_rounding(self) -> None:
        result = recompute_dose_export(
            formula_id="F",
            parent_formula_hash=PARENT,
            lines=self.lines(),
            concentrate_ul="4500",
        )
        self.assertEqual(result.exact_total_ul, Decimal("4500"))
        self.assertEqual(result.exported_total_ul, Decimal("4500"))
        self.assertTrue(result.canonical_parts_unchanged)
        self.assertIsNone(result.balance_line_id)

    def test_display_export_uses_explicit_balance_and_closes(self) -> None:
        result = recompute_dose_export(
            formula_id="F",
            parent_formula_hash=PARENT,
            lines=self.lines(),
            concentrate_ul="4500",
            display_places=4,
            balance_line_id="C",
        )
        self.assertEqual(result.exported_total_ul, Decimal("4500"))
        self.assertEqual(result.balance_line_id, "C")
        adjustments = {line.line_id: line.rounding_adjustment_ul for line in result.lines}
        self.assertNotEqual(adjustments["C"], Decimal("0"))
        self.assertEqual(len(result.successor_hash), 64)

    def test_formula_parts_are_never_mutated(self) -> None:
        original = [(line.line_id, line.parts_per_1000) for line in self.lines()]
        result = recompute_dose_export(
            formula_id="F",
            parent_formula_hash=PARENT,
            lines=self.lines(),
            concentrate_ul="7500",
            display_places=4,
        )
        observed = [(line.line_id, line.parts_per_1000) for line in result.lines]
        self.assertEqual(original, observed)
        self.assertTrue(result.canonical_parts_unchanged)

    def binding(self, **changes):
        values = dict(
            canonical_record_id="F-v1",
            canonical_content_hash="1" * 64,
            renderer_version="renderer-1",
            analysis_input_hash="2" * 64,
            generated_analysis_hash="3" * 64,
            source_file_hash="4" * 64,
            parent_artifact_hash="5" * 64,
        )
        values.update(changes)
        return ArtifactBinding(**values)

    def test_binding_match(self) -> None:
        result = validate_binding(self.binding(), self.binding())
        self.assertEqual(result.state, "PASS")
        self.assertEqual(result.drift_class, DriftClass.MATCH)

    def test_source_and_content_hash_drift_classified(self) -> None:
        result = validate_binding(
            self.binding(), self.binding(source_file_hash="a" * 64, canonical_content_hash="b" * 64)
        )
        self.assertEqual(result.drift_class, DriftClass.UNINTENDED_SOURCE_MUTATION)
        self.assertFalse(result.rebind_allowed)

    def test_generated_analysis_drift_classified(self) -> None:
        result = validate_binding(
            self.binding(), self.binding(generated_analysis_hash="a" * 64)
        )
        self.assertEqual(result.drift_class, DriftClass.STALE_GENERATED_ANALYSIS)

    def test_reviewed_intentional_change_classification(self) -> None:
        drift = classify_reviewed_change(
            source_semantic_change=True,
            change_intentional=True,
            generated_only_change=False,
            renderer_changed=False,
            dependency_missing=False,
            metadata_malformed=False,
        )
        self.assertEqual(drift, DriftClass.INTENTIONAL_SOURCE_MUTATION_NOT_REBOUND)

    def test_rebind_blocked_without_exact_parent_bytes(self) -> None:
        allowed, reasons = rebind_preflight(
            clean_or_intentionally_staged=True,
            semantic_diff_reviewed=True,
            change_unambiguous=True,
            parent_source_bytes_available=False,
            drift_class=DriftClass.STALE_GENERATED_ANALYSIS,
        )
        self.assertFalse(allowed)
        self.assertTrue(any("parent" in reason for reason in reasons))

    def test_rebind_only_after_full_preflight(self) -> None:
        allowed, reasons = rebind_preflight(
            clean_or_intentionally_staged=True,
            semantic_diff_reviewed=True,
            change_unambiguous=True,
            parent_source_bytes_available=True,
            drift_class=DriftClass.STALE_GENERATED_ANALYSIS,
        )
        self.assertTrue(allowed)
        self.assertEqual(reasons, ())


if __name__ == "__main__":
    unittest.main()
