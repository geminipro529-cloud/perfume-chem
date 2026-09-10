from __future__ import annotations

import json
from pathlib import Path
import unittest

from perfume_chem_v20_guardrails.complexity_dispatch import (
    ClassificationState,
    ComplexityClass,
    ComplexityProfile,
    CurrentComplexityDispatcher,
)


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "reference/meaningful_complexity_v3/COMPLEXITY_CLASSIFICATION_RULES.json"
CASES = ROOT / "reference/meaningful_complexity_v3/COMPLEXITY_MODEL_TEST_CASES.json"


class ComplexityDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dispatcher = CurrentComplexityDispatcher.from_rules_file(RULES)
        cls.cases = json.loads(CASES.read_text(encoding="utf-8"))["test_cases"]

    def case(self, case_id: str) -> dict:
        return next(item for item in self.cases if item["test_case_id"] == case_id)

    def test_legitimate_compact(self) -> None:
        case = self.case("MCV3-TC-001")
        decision = self.dispatcher.classify(ComplexityProfile.from_mapping(case["input_profile"]))
        self.assertEqual(decision.assigned_class, ComplexityClass.COMPACT)
        self.assertEqual(decision.classification_state, ClassificationState.PASS_FOR_DECLARED_SCOPE)
        self.assertNotIn("G14", decision.current_failed_gates)
        self.assertEqual(decision.current_gate_states["G14"], "NON_GOVERNING")

    def test_padded_long_formula_rebuilds(self) -> None:
        case = self.case("MCV3-TC-002")
        decision = self.dispatcher.classify(ComplexityProfile.from_mapping(case["input_profile"]))
        self.assertEqual(decision.assigned_class, ComplexityClass.UNCLASSIFIED_HOLD)
        self.assertEqual(decision.classification_state, ClassificationState.REBUILD_REQUIRED)
        self.assertTrue(decision.padding_review_required)

    def test_high_row_low_interaction_is_layered(self) -> None:
        case = self.case("MCV3-TC-003")
        decision = self.dispatcher.classify(ComplexityProfile.from_mapping(case["input_profile"]))
        self.assertEqual(decision.assigned_class, ComplexityClass.LAYERED)
        self.assertEqual(decision.classification_state, ClassificationState.CONDITIONAL)

    def test_lower_row_deeply_transformed_is_high_design(self) -> None:
        case = self.case("MCV3-TC-004")
        decision = self.dispatcher.classify(ComplexityProfile.from_mapping(case["input_profile"]))
        self.assertEqual(decision.assigned_class, ComplexityClass.HIGH_COMPLEXITY)
        self.assertEqual(decision.classification_state, ClassificationState.CONDITIONAL)
        self.assertTrue(decision.compression_review_required)

    def test_orchestral_without_physical_data_stays_conditional(self) -> None:
        case = self.case("MCV3-TC-007")
        profile = ComplexityProfile.from_mapping({
            **case["input_profile"],
            "total_rows": 75,
            "distinct_canonical_odor_identities": 73,
            "technical_rows": 2,
            "duplicate_strength_rows": 0,
            "proposed_microtexture_rows": 2,
            "functional_row_ratio": 0.96,
            "single_point_dependencies": 0,
            "requested_claim": "ORCHESTRAL",
            "resilience_control_paths": 2,
        })
        decision = self.dispatcher.classify(profile)
        self.assertEqual(decision.assigned_class, ComplexityClass.ORCHESTRAL)
        self.assertEqual(decision.classification_state, ClassificationState.CONDITIONAL)

    def test_49_rows_do_not_fail_by_count_alone(self) -> None:
        profile = ComplexityProfile(
            formula_scope="FULL_PERFUME",
            total_rows=49,
            distinct_canonical_odor_identities=47,
            effective_post_ablation_rows=42,
            technical_rows=2,
            duplicate_strength_rows=0,
            proposed_microtexture_rows=2,
            functional_row_ratio=0.96,
            recognizer_paths=2,
            single_point_dependencies=0,
            sensory_systems=6,
            time_windows=4,
            transitions=3,
            interaction_edges=9,
            interaction_effect_types=4,
            texture_axes=4,
            contrast_axes=3,
            resilience_control_paths=2,
            requested_claim="HIGH_COMPLEXITY",
        )
        decision = self.dispatcher.classify(profile)
        self.assertEqual(decision.assigned_class, ComplexityClass.HIGH_COMPLEXITY)
        self.assertNotEqual(decision.classification_state, ClassificationState.REBUILD_REQUIRED)
        self.assertNotIn("ROW_COUNT", " ".join(decision.current_failed_gates))

    def test_65_row_padding_cannot_pass(self) -> None:
        profile = ComplexityProfile(
            total_rows=65,
            distinct_canonical_odor_identities=50,
            effective_post_ablation_rows=25,
            technical_rows=5,
            duplicate_strength_rows=10,
            proposed_microtexture_rows=8,
            functional_row_ratio=0.61,
            recognizer_paths=1,
            sensory_systems=4,
            time_windows=3,
            transitions=1,
            interaction_edges=2,
            interaction_effect_types=1,
            texture_axes=6,
            contrast_axes=1,
            requested_claim="HIGH_COMPLEXITY",
        )
        decision = self.dispatcher.classify(profile)
        self.assertEqual(decision.classification_state, ClassificationState.REBUILD_REQUIRED)

    def test_quality_score_has_no_effect(self) -> None:
        base = dict(
            total_rows=20,
            distinct_canonical_odor_identities=18,
            effective_post_ablation_rows=17,
            technical_rows=2,
            functional_row_ratio=0.95,
            recognizer_paths=1,
            sensory_systems=3,
            time_windows=3,
            transitions=2,
            interaction_edges=3,
            interaction_effect_types=2,
            texture_axes=2,
            contrast_axes=1,
            requested_claim="COMPACT",
        )
        low = self.dispatcher.classify(ComplexityProfile(**base, legacy_quality_score=1))
        high = self.dispatcher.classify(ComplexityProfile(**base, legacy_quality_score=100))
        self.assertEqual(low.assigned_class, high.assigned_class)
        self.assertEqual(low.classification_state, high.classification_state)
        self.assertEqual(low.current_failed_gates, high.current_failed_gates)

    def test_missing_current_policy_never_falls_back(self) -> None:
        legacy = {"quality_score": 99, "meaningful_row_minimum": 65}
        decision = self.dispatcher.classify(
            ComplexityProfile(), current_policy_available=False, legacy_payload=legacy
        )
        self.assertEqual(decision.classification_state, ClassificationState.HOLD)
        self.assertEqual(decision.assigned_class, ComplexityClass.UNCLASSIFIED_HOLD)
        self.assertEqual(decision.legacy_payload_preserved, legacy)

    def test_target_specific_floor_is_enforced_only_when_authoritative(self) -> None:
        profile = ComplexityProfile(
            total_rows=40,
            distinct_canonical_odor_identities=38,
            effective_post_ablation_rows=35,
            functional_row_ratio=0.95,
            recognizer_paths=2,
            sensory_systems=5,
            time_windows=3,
            transitions=2,
            interaction_edges=7,
            interaction_effect_types=3,
            texture_axes=3,
            contrast_axes=2,
            resilience_control_paths=2,
            requested_claim="HIGH_COMPLEXITY",
            target_identity_floor=45,
            target_floor_authoritative=True,
        )
        decision = self.dispatcher.classify(profile)
        self.assertEqual(decision.classification_state, ClassificationState.REBUILD_REQUIRED)
        self.assertIn("TARGET_SPECIFIC_IDENTITY_FLOOR", decision.current_failed_gates)

    def test_legacy_payload_round_trips_without_decision_authority(self) -> None:
        legacy = {"gate_results": [{"gate_id": "G14", "score": 99}], "quality_score": 99}
        profile = ComplexityProfile(
            total_rows=18,
            distinct_canonical_odor_identities=16,
            effective_post_ablation_rows=15,
            technical_rows=2,
            functional_row_ratio=0.94,
            recognizer_paths=1,
            sensory_systems=3,
            time_windows=3,
            transitions=2,
            interaction_edges=3,
            interaction_effect_types=2,
            texture_axes=2,
            contrast_axes=1,
            requested_claim="COMPACT",
        )
        decision = self.dispatcher.classify(profile, legacy_payload=legacy)
        self.assertEqual(decision.legacy_payload_preserved, legacy)
        self.assertEqual(decision.current_gate_states["G14"], "NON_GOVERNING")


if __name__ == "__main__":
    unittest.main()
