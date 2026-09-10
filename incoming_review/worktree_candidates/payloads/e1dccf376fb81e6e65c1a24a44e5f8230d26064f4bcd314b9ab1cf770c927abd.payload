from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from engine.evidence.augmentation import EvidenceAugmentationState
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.project_verification import build_check_specs, engine_test_shards
from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    BenchmarkPhase,
    ConditionKind,
    freeze_sol_output,
)
from engine.solforge.protected_evidence import (
    ProtectedEvidenceBenchmarkCaseV1,
    ProtectedEvidenceModule,
    build_protected_evidence_capsule_from_execution,
    compile_protected_evidence_conditions,
    score_protected_evidence_invariants,
)
from engine.solforge.protected_evidence_corpus import (
    ProtectedEvidenceBenchmarkCorpusV1,
    build_protected_evidence_benchmark_corpus_v1,
    build_protected_evidence_benchmark_manifest_v1,
)

ROOT = Path(__file__).resolve().parents[1]
FROZEN_CORPUS = ROOT / "tests/fixtures/solforge/protected_evidence_benchmark_v1.json"
FROZEN_CORPUS_SHA = FROZEN_CORPUS.with_suffix(".sha256")
BENCHMARK_ROOT = ROOT / "data/benchmarks/solforge/protected_evidence_v1"


def test_protected_corpus_has_three_screen_and_confirmation_cases_per_module() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()
    counts = Counter((item.module, item.case.phase) for item in corpus.cases)

    assert len(corpus.cases) == 12
    for module in ProtectedEvidenceModule:
        assert counts[(module, BenchmarkPhase.SCREEN)] == 3
        assert counts[(module, BenchmarkPhase.CONFIRMATION)] == 3
        for phase in BenchmarkPhase:
            roles = {
                item.case.input_payload["benchmark_role"]
                for item in corpus.cases
                if item.module is module and item.case.phase is phase
            }
            assert roles == {"POSITIVE", "SAFE_COUNTERCASE", "CRITICAL_TRAP"}


def test_public_decision_invariant_matches_each_execution_derived_answer() -> None:
    """Catch a public prompt that tells the blind control the wrong decision."""

    corpus = build_protected_evidence_benchmark_corpus_v1()
    for item in corpus.cases:
        decisions = item.case.sealed_answer_key["allowed_decisions"]
        assert len(decisions) == 1
        expected = f"correct_{decisions[0].casefold()}"
        observed = tuple(
            invariant
            for invariant in item.case.public_invariants
            if invariant.startswith("correct_")
        )
        assert observed == (expected,)


def test_temporal_positive_and_static_roles_use_observed_balanced_sequences() -> None:
    """Catch a design-balanced schedule paired with only one executed order."""

    corpus = build_protected_evidence_benchmark_corpus_v1()
    expected_states = {
        "PE-TEM-S01": "AUGMENT",
        "PE-TEM-S02": "NO_AUGMENTATION",
        "PE-TEM-C01": "AUGMENT",
    }
    by_id = {item.case.case_id: item for item in corpus.cases}
    for case_id, expected_state in expected_states.items():
        capsule = build_protected_evidence_capsule_from_execution(
            by_id[case_id].case,
            by_id[case_id].execution,
        )
        assert capsule.objective_receipt.state.value == expected_state


def test_protected_corpus_recomputes_every_sealed_receipt_from_public_execution() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()

    for item in corpus.cases:
        capsule = build_protected_evidence_capsule_from_execution(
            item.case,
            item.execution,
        )
        answer = item.case.sealed_answer_key
        assert capsule.objective_receipt.state.value == answer["expected_objective_state"]
        assert list(capsule.objective_receipt.reason_codes) == answer[
            "expected_reason_codes"
        ]
        assert item.case.input_payload["execution_receipt"] == item.execution.as_dict()
        assert (
            item.case.input_payload["execution_receipt_sha256"]
            == item.execution.record_sha256
        )
        assert set(capsule.objective_receipt.authority.values()) == {False}
        assert item.case.as_public_dict()["authority_flags"] == BENCHMARK_AUTHORITY_FLAGS


def test_protected_corpus_is_byte_deterministic_and_strict_on_tampering() -> None:
    first = build_protected_evidence_benchmark_corpus_v1()
    second = build_protected_evidence_benchmark_corpus_v1()

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.record_sha256 == second.record_sha256
    assert ProtectedEvidenceBenchmarkCorpusV1.from_dict(first.as_dict()) == first

    tampered = first.as_dict()
    tampered["cases"][0]["input_payload"]["execution_receipt_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="derived benchmark fields"):
        ProtectedEvidenceBenchmarkCorpusV1.from_dict(tampered)


def test_corpus_covers_required_fail_closed_states_without_false_promotion() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()
    observed: dict[str, EvidenceAugmentationState] = {}
    reason_codes: set[str] = set()
    blockers: set[str] = set()
    for item in corpus.cases:
        receipt = build_protected_evidence_capsule_from_execution(
            item.case,
            item.execution,
        ).objective_receipt
        observed[item.case.case_id] = receipt.state
        reason_codes.update(receipt.reason_codes)
        blockers.update(receipt.blockers)

    assert set(observed.values()) == {
        EvidenceAugmentationState.AUGMENT,
        EvidenceAugmentationState.NO_AUGMENTATION,
        EvidenceAugmentationState.HOLD,
    }
    assert "CANONICAL_CELL_CONFLICT" in reason_codes
    assert "ONE_MISSING_CELL_SELECTED" in reason_codes
    assert "FAILED_HELDOUT_BASELINE" in reason_codes
    assert "ORDER_CONFOUNDED" in blockers
    assert any("criterion_id" in blocker for blocker in blockers)
    assert any("INFLUENTIAL_CLUSTER" in blocker for blocker in blockers)


def test_each_case_rehydrates_as_a_protected_benchmark_case() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()

    for item in corpus.cases:
        assert ProtectedEvidenceBenchmarkCaseV1.from_dict(item.as_dict()) == item


def test_frozen_corpus_matches_generator_and_sha256_sidecar() -> None:
    frozen_bytes = FROZEN_CORPUS.read_bytes()
    expected_sidecar = (
        f"{hashlib.sha256(frozen_bytes).hexdigest()}  {FROZEN_CORPUS.name}\n"
    )
    assert FROZEN_CORPUS_SHA.read_text(encoding="ascii") == expected_sidecar
    payload = json.loads(frozen_bytes)
    frozen = ProtectedEvidenceBenchmarkCorpusV1.from_dict(payload)
    generated = build_protected_evidence_benchmark_corpus_v1()

    assert frozen == generated
    assert frozen_bytes == generated.canonical_bytes() + b"\n"


def test_dispatch_manifests_are_public_hash_bound_and_phase_separated() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()
    screen = build_protected_evidence_benchmark_manifest_v1(
        corpus,
        phase=BenchmarkPhase.SCREEN,
        run_nonce="protected-evidence-screen-v1-20260827",
    )
    confirmation = build_protected_evidence_benchmark_manifest_v1(
        corpus,
        phase=BenchmarkPhase.CONFIRMATION,
        run_nonce="protected-evidence-confirmation-v1-20260827",
    )

    assert screen["request_count"] == confirmation["request_count"] == 6
    assert screen["model_identity"] == "GPT-5.6 Sol"
    assert screen["reasoning_setting"] == "xhigh"
    assert {row["case_id"] for row in screen["requests"]}.isdisjoint(
        row["case_id"] for row in confirmation["requests"]
    )
    assert "sealed_answer_key" not in json.dumps(screen, sort_keys=True)
    for manifest in (screen, confirmation):
        core = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        assert manifest["manifest_sha256"] == sha256_hex(canonical_json_bytes(core))
        for request in manifest["requests"]:
            request_core = {
                key: value for key, value in request.items() if key != "request_sha256"
            }
            assert request["request_sha256"] == sha256_hex(
                canonical_json_bytes(request_core)
            )

    screen["requests"][0]["public_case"]["input_payload"]["criterion"] = "RICHNESS"
    assert all(
        item.case.input_payload["criterion"] == "DEPTH"
        for item in corpus.cases
        if item.module is ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER
    )


@pytest.mark.parametrize(
    ("phase", "nonce", "filename"),
    (
        (
            BenchmarkPhase.SCREEN,
            "protected-evidence-screen-v1-20260827",
            "screen_manifest.json",
        ),
        (
            BenchmarkPhase.CONFIRMATION,
            "protected-evidence-confirmation-v1-20260827",
            "confirmation_manifest.json",
        ),
    ),
)
def test_frozen_dispatch_manifest_matches_generator(
    phase: BenchmarkPhase,
    nonce: str,
    filename: str,
) -> None:
    path = BENCHMARK_ROOT / filename
    frozen_bytes = path.read_bytes()
    sidecar = path.with_suffix(".sha256")
    assert sidecar.read_text(encoding="ascii") == (
        f"{hashlib.sha256(frozen_bytes).hexdigest()}  {path.name}\n"
    )
    expected = build_protected_evidence_benchmark_manifest_v1(
        build_protected_evidence_benchmark_corpus_v1(),
        phase=phase,
        run_nonce=nonce,
    )
    assert frozen_bytes == canonical_json_bytes(expected) + b"\n"


def test_every_frozen_case_compiles_one_full_credit_protected_condition() -> None:
    corpus = build_protected_evidence_benchmark_corpus_v1()
    for item in corpus.cases:
        output_text = json.dumps(
            {
                "decision": "PROPOSED",
                "interventions": [{"kind": "MODEL_GUESS"}],
                "criterion": item.case.input_payload["criterion"],
                "next_comparison": "Model-selected comparison.",
                "explanation": "One nonauthoritative model explanation.",
                "authority_flags": BENCHMARK_AUTHORITY_FLAGS,
            },
            sort_keys=True,
        )
        frozen = freeze_sol_output(
            item.case,
            {
                "case_id": item.case.case_id,
                "phase": item.case.phase.value,
                "model_identity": "GPT-5.6 Sol",
                "reasoning_setting": "xhigh",
                "conversation_id": f"fresh-{item.case.case_id.casefold()}",
                "output_text": output_text,
            },
        )
        capsule = build_protected_evidence_capsule_from_execution(
            item.case,
            item.execution,
        )
        condition_set = compile_protected_evidence_conditions(
            item.case,
            frozen,
            capsule,
        )
        scores = score_protected_evidence_invariants(item, condition_set)
        treatment = next(
            score for score in scores if score.condition is ConditionKind.SOLFORGE
        )
        by_kind = {
            condition.condition: condition for condition in condition_set.conditions
        }

        assert treatment.score == 100
        assert treatment.critical_errors == ()
        assert len(
            by_kind[ConditionKind.SOLFORGE].output_text.encode("utf-8")
        ) == len(
            by_kind[ConditionKind.NO_OP_LENGTH_MATCHED].output_text.encode("utf-8")
        )


def test_protected_evidence_tests_are_in_canonical_verification() -> None:
    shard = engine_test_shards()["complexity-solforge"]
    checks = {item.name: item for item in build_check_specs(ROOT)}

    assert "tests/test_solforge_protected_evidence.py" in shard
    assert "tests/test_solforge_protected_evidence_corpus.py" in shard
    for check_name in ("engine-lint", "engine-typecheck"):
        command = checks[check_name].command
        assert "engine/solforge/protected_evidence.py" in command
        assert "engine/solforge/protected_evidence_corpus.py" in command
