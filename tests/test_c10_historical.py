from __future__ import annotations

from dataclasses import replace

from engine.optimization import (
    HISTORICAL_SEARCH_CLAIM,
    HistoricalRegressionReceipt,
    HistoricalRegressionStatus,
    assess_historical_regression,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64


def _receipt() -> HistoricalRegressionReceipt:
    return HistoricalRegressionReceipt(
        implementation_sha256=HASH_A,
        input_sha256=HASH_B,
        result_sha256=HASH_C,
        verifier_sha256=HASH_D,
        replay_command=("python", "historical_search.py", "--input", "input.json"),
        replay_exit_code=0,
        candidate_count=30_000,
        guardrail_count=35,
        guardrails_passed=35,
        dna_threshold=97.5,
        winner_dna_score=97.76,
        fragrance_family="La Nuit de L'Homme",
    )


def test_historical_numbers_are_reported_unverified_not_canonical() -> None:
    assert HISTORICAL_SEARCH_CLAIM.status is HistoricalRegressionStatus.REPORTED_UNVERIFIED
    assert HISTORICAL_SEARCH_CLAIM.approximate_candidate_count == 30_000
    assert HISTORICAL_SEARCH_CLAIM.guardrail_count == 35
    assert HISTORICAL_SEARCH_CLAIM.dna_threshold == 97.5
    assert HISTORICAL_SEARCH_CLAIM.reported_guardrails_passed == 35
    assert HISTORICAL_SEARCH_CLAIM.reported_winner_dna_score == 97.76


def test_missing_historical_implementation_inputs_and_results_fail_closed() -> None:
    assessment = assess_historical_regression(None)

    assert assessment.status is HistoricalRegressionStatus.BLOCKED_MISSING_ARTIFACTS
    assert assessment.canonical is False
    assert assessment.receipt_sha256 is None
    assert assessment.reason_codes == ("MISSING_REPRODUCIBLE_ARTIFACT_BUNDLE",)


def test_exact_replay_receipt_can_match_report_but_does_not_replace_c11_replay() -> None:
    assessment = assess_historical_regression(_receipt())

    assert assessment.status is HistoricalRegressionStatus.RECEIPT_MATCHES_REPORTED_RESULT
    assert assessment.canonical is False
    assert assessment.receipt_sha256 is not None
    assert assessment.reason_codes == ("C11_INDEPENDENT_REPLAY_REQUIRED",)


def test_mismatched_counts_guardrails_score_or_family_cannot_pass() -> None:
    receipt = _receipt()
    mismatches = (
        replace(receipt, candidate_count=29_999),
        replace(receipt, guardrail_count=36),
        replace(receipt, guardrails_passed=34),
        replace(receipt, dna_threshold=97.4),
        replace(receipt, winner_dna_score=97.75),
        replace(receipt, fragrance_family="unrelated family"),
        replace(receipt, replay_exit_code=1),
    )

    for mismatch in mismatches:
        assessment = assess_historical_regression(mismatch)
        assert assessment.status is HistoricalRegressionStatus.MISMATCH
        assert assessment.canonical is False
        assert assessment.reason_codes
