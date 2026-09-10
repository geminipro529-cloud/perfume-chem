import unittest

from perfume_chem_v20_guardrails.nary_interactions import (
    DerivationMethod,
    EvidenceState,
    InteractionContractError,
    Participant,
    PhysicalState,
    build_nary_interaction,
)


FORMULA_HASH = "a" * 64


def participant(pid, role, ratio):
    return Participant.create(participant_id=pid, role=role, member=pid, ratio=ratio)


class NaryInteractionTests(unittest.TestCase):
    def build(self, **overrides):
        values = dict(
            record_id="N1",
            participants=[
                participant("A", "source_system", "0.2"),
                participant("B", "bridge_material", "0.3"),
                participant("C", "target_system", "0.5"),
            ],
            matrix="ethanol-water",
            phase="heart_to_drydown",
            context="formula-signature triad",
            evidence_state=EvidenceState.DESIGNED,
            physical_state=PhysicalState.NOT_TESTED,
            derivation_method=DerivationMethod.EXACT_FORMULA_PARTS,
            source_formula_hash=FORMULA_HASH,
        )
        values.update(overrides)
        return build_nary_interaction(**values)

    def test_valid_designed_record_remains_not_tested(self) -> None:
        record = self.build()
        self.assertEqual(record.physical_state, PhysicalState.NOT_TESTED)
        self.assertEqual(record.authority, "FORMULA_SIGNATURE_SUPPORT_ONLY")
        self.assertEqual(len(record.record_hash), 64)

    def test_arity_below_two_rejected(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(participants=[participant("A", "source", "1")])
        self.assertEqual(ctx.exception.code, "ARITY_BELOW_TWO")

    def test_missing_role_rejected(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            Participant.create(participant_id="A", role="", member="x", ratio="1")
        self.assertEqual(ctx.exception.code, "MISSING_PARTICIPANT_ROLE")

    def test_nonclosing_ratio_rejected(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(
                participants=[participant("A", "source", "0.4"), participant("B", "target", "0.5")]
            )
        self.assertEqual(ctx.exception.code, "NONCLOSING_RATIO_VECTOR")

    def test_missing_matrix_phase_or_context_rejected(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(matrix="")
        self.assertEqual(ctx.exception.code, "MISSING_CONTEXT")

    def test_pair_score_multiplication_cannot_create_nary_authority(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(derivation_method=DerivationMethod.PAIR_SCORE_MULTIPLICATION)
        self.assertEqual(ctx.exception.code, "PAIR_SCORE_SYNTHESIS_PROHIBITED")

    def test_designed_record_cannot_be_labeled_observed(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(physical_state=PhysicalState.OBSERVED)
        self.assertEqual(ctx.exception.code, "DESIGNED_CANNOT_BE_OBSERVED")

    def test_exact_parts_require_source_formula_hash(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(source_formula_hash=None)
        self.assertEqual(ctx.exception.code, "MISSING_SOURCE_FORMULA_HASH")

    def test_duplicate_participant_ids_rejected(self) -> None:
        with self.assertRaises(InteractionContractError) as ctx:
            self.build(
                participants=[participant("A", "source", "0.5"), participant("A", "target", "0.5")]
            )
        self.assertEqual(ctx.exception.code, "DUPLICATE_PARTICIPANT")


if __name__ == "__main__":
    unittest.main()
