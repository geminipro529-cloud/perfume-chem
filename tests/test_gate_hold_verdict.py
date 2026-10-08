"""HOLD verdict: missing data blocks release without being reported as a formula error."""

import pytest

from engine.pipeline.gates import (
    ADVISORY_FAILURE_GATES,
    BLOCKING_STATUSES,
    GATE_STATUSES,
    GateResult,
    _apply_guideline_policy,
    _result,
    _status_from_gates,
)


def _gates(*statuses: str) -> list[GateResult]:
    return [GateResult(gate=f"g{i}", status=status) for i, status in enumerate(statuses)]


def test_hold_is_a_valid_gate_status_and_blocks_like_fail():
    assert GATE_STATUSES == ("PASS", "WARN", "HOLD", "FAIL")
    assert BLOCKING_STATUSES == {"HOLD", "FAIL"}
    assert _result("exact_subtotal", "HOLD", "needs data").status == "HOLD"
    with pytest.raises(ValueError):
        _result("exact_subtotal", "MAYBE")


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (("PASS", "WARN", "HOLD", "FAIL"), "FAIL"),
        (("PASS", "WARN", "HOLD"), "HOLD"),
        (("HOLD", "PASS"), "HOLD"),
        (("PASS", "WARN"), "WARN"),
        (("PASS", "SKIP"), "PASS"),
        (("SKIP", "HOLD", "SKIP"), "HOLD"),
    ],
)
def test_verdict_order_is_fail_then_hold_then_warn_then_pass(statuses, expected):
    assert _status_from_gates(_gates(*statuses)) == expected


def test_screening_diagnostic_hold_is_demoted_to_warn():
    result = _result("oav_legibility", "HOLD", "threshold missing")

    assert result.status == "WARN"
    assert result.data["original_status"] == "HOLD"
    assert result.data["gate_policy"] == "screening_oav_failures_demoted_to_warn"


def test_advisory_hold_is_demoted_but_a_blocking_gate_keeps_hold():
    advisory = sorted(ADVISORY_FAILURE_GATES - {"oav_legibility"})[0]
    demoted = _apply_guideline_policy(GateResult(gate=advisory, status="HOLD", detail="no data"))
    kept = _apply_guideline_policy(GateResult(gate="phase_compatibility", status="HOLD", detail="no data"))

    assert demoted.status == "WARN"
    assert demoted.data["original_status"] == "HOLD"
    assert kept.status == "HOLD"
