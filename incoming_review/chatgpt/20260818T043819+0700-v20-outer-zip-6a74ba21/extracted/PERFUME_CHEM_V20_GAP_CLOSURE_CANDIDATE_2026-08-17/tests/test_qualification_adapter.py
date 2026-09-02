from __future__ import annotations

import json
from pathlib import Path
import unittest

from perfume_chem_v20_guardrails.qualification_adapter import adapt_legacy_qualification


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "reference/legacy_qualification/engine_qualification_fixtures.json"
RESULTS = ROOT / "reference/legacy_qualification/ENGINE_QUALIFICATION_REFERENCE_RESULTS.json"


class QualificationAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))["fixtures"]
        result_payload = json.loads(RESULTS.read_text(encoding="utf-8"))
        cls.results = result_payload.get("results", result_payload)

    def fixture(self, fixture_id):
        return next(item for item in self.fixtures if item["fixture_id"] == fixture_id)

    def result(self, fixture_id):
        return next(item for item in self.results if item["fixture_id"] == fixture_id)

    def test_eq02_g14_only_difference_is_non_governing_currently(self) -> None:
        fixture = self.fixture("EQ-02-KNOWN-INVALID")
        result = self.result("EQ-02-KNOWN-INVALID")
        adapted = adapt_legacy_qualification(
            fixture_id=fixture["fixture_id"],
            expected_state=fixture["expected_state"],
            observed_state=result["observed_state"],
            expected_failed_gates=fixture["expected_failed_gates"],
            observed_failed_gates=result["observed_failed_gates"],
            raw_record={"fixture": fixture, "result": result},
        )
        self.assertTrue(adapted.current_policy_gate_sets_match)
        self.assertEqual(
            adapted.current_policy_state,
            "CURRENT_POLICY_COMPATIBLE__LEGACY_G14_NON_GOVERNING",
        )
        self.assertTrue(adapted.legacy_fixture_still_quarantined)
        self.assertFalse(adapted.authority_promoted)
        self.assertNotIn("G14", adapted.normalized_expected_failed_gates)

    def test_raw_legacy_result_is_preserved(self) -> None:
        fixture = self.fixture("EQ-02-KNOWN-INVALID")
        result = self.result("EQ-02-KNOWN-INVALID")
        raw = {"fixture": fixture, "result": result}
        adapted = adapt_legacy_qualification(
            fixture_id=fixture["fixture_id"],
            expected_state=fixture["expected_state"],
            observed_state=result["observed_state"],
            expected_failed_gates=fixture["expected_failed_gates"],
            observed_failed_gates=result["observed_failed_gates"],
            raw_record=raw,
        )
        self.assertEqual(adapted.legacy_raw_preserved, raw)

    def test_low_quality_score_fixture_cannot_drive_current_status(self) -> None:
        fixture = self.fixture("EQ-16-LOW-QUALITY-SCORE")
        result = self.result("EQ-16-LOW-QUALITY-SCORE")
        adapted = adapt_legacy_qualification(
            fixture_id=fixture["fixture_id"],
            expected_state=fixture["expected_state"],
            observed_state=result["observed_state"],
            expected_failed_gates=fixture["expected_failed_gates"],
            observed_failed_gates=result["observed_failed_gates"],
            raw_record={"fixture": fixture, "result": result},
        )
        self.assertEqual(adapted.normalized_expected_failed_gates, ())
        self.assertEqual(adapted.normalized_observed_failed_gates, ())
        self.assertFalse(adapted.authority_promoted)

    def test_non_g14_mismatch_remains_hold(self) -> None:
        adapted = adapt_legacy_qualification(
            fixture_id="X",
            expected_state="REBUILD",
            observed_state="REBUILD",
            expected_failed_gates=["G3", "G5"],
            observed_failed_gates=["G3"],
            raw_record={"x": 1},
        )
        self.assertFalse(adapted.current_policy_gate_sets_match)
        self.assertEqual(adapted.current_policy_state, "HOLD_CURRENT_POLICY_GATE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
