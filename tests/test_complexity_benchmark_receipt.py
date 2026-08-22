from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from engine.calibration.hashing import stable_json_hash
from engine.perception.complexity_benchmark import (
    FamilyDecision,
    build_benchmark_receipt,
    build_blocked_benchmark_receipt,
    decide_paired_benchmark,
)
from tests.complexity_benchmark_fixtures import (
    benchmark_evidence,
    telemetry_summary,
)

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = (
    ROOT
    / "docs/research/PERFUME_CHEM_COMPLEXITY_XHIGH_BENCHMARK_RUNBOOK_2026-08-22.md"
)


def _receipt(*, repair_count: int = 0, deletion_paths: tuple[str, ...] = ()) -> dict:
    telemetry = telemetry_summary(state="NOT_EXPOSED")
    decision = decide_paired_benchmark(
        benchmark_evidence(wins=12, median_delta=5), telemetry=telemetry
    )
    return build_benchmark_receipt(
        registry_sha256="a" * 64,
        corpus_sha256="b" * 64,
        rubric_sha256="c" * 64,
        request_receipts=(
            {
                "request_id": "cxreq-1",
                "prompt_sha256": "d" * 64,
                "response_sha256": "e" * 64,
                "execution_state": "PASS",
            },
        ),
        pair_scores=(
            {
                "case_id": "CX-A01",
                "control_total": 70,
                "treatment_total": 78,
            },
        ),
        decision=decision,
        telemetry=telemetry,
        ablation_decisions=(
            FamilyDecision(
                family_id="construction_profile",
                state="RETAIN",
                median_delta=Decimal("4"),
                win_rate=Decimal("0.75"),
                prevented_critical_failures=0,
                reasons=("median gain passed",),
            ),
        ),
        repair_count=repair_count,
        holdout_results=(),
        registry_transitions=(),
        preserved_paths=("engine/perception/construction_complexity.py",),
        deletion_paths=deletion_paths,
    )


def test_receipt_is_semantically_hashed_and_grants_no_authority() -> None:
    receipt = _receipt()
    semantic_hash = receipt.pop("semantic_receipt_sha256")
    assert stable_json_hash(receipt) == semantic_hash
    assert receipt["deletion_paths"] == []
    assert receipt["authority_flags"] == {
        "source_admission": False,
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "sensory": False,
        "safety": False,
        "release": False,
    }


def test_receipt_refuses_second_repair_or_any_deletion_path() -> None:
    with pytest.raises(ValueError, match="one repair cycle"):
        _receipt(repair_count=2)
    with pytest.raises(ValueError, match="deletion paths"):
        _receipt(deletion_paths=("engine/perception/construction_complexity.py",))


def test_blocked_receipt_records_zero_transmissions_without_retiring_modules() -> None:
    receipt = build_blocked_benchmark_receipt(
        registry_sha256="a" * 64,
        corpus_sha256="b" * 64,
        rubric_sha256="c" * 64,
        run_id="CXB-20260822T120000Z-0123abcd",
        blocker_code="BENCHMARK_BLOCKED_UNVERIFIED_XHIGH",
        blocker=(
            "available cloud task interface cannot attest xhigh model and "
            "projectless isolation"
        ),
        advisory_worker_chat_ids=("worker-1", "worker-2"),
    )
    semantic_hash = receipt.pop("semantic_receipt_sha256")
    assert stable_json_hash(receipt) == semantic_hash
    assert receipt["provider_transmissions"] == 0
    assert receipt["module_disposition"] == "NO_RETIREMENT_WITHOUT_VALID_BENCHMARK"
    assert receipt["benchmark_decision"] == "BENCHMARK_BLOCKED_UNVERIFIED_XHIGH"
    assert not any(receipt["authority_flags"].values())


def test_runbook_is_nonfast_no_duplicate_and_authority_safe() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for required in (
        "ChatGPT Pro work chats are advisory workers only",
        "plain ChatGPT xhigh",
        "one clean projectless conversation per request",
        "do not retry an ambiguous request",
        "RETIRED_BENCHMARK_UNDERPERFORMER",
        "physical liking remains NOT TESTED",
        "no DeepLuna provider transmission",
    ):
        assert required in text
    assert "[Globalization.CultureInfo]::InvariantCulture" in text
    assert "DeepLuna Fast fallback" not in text
