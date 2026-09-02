from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path

import pytest

from engine.formulation_intelligence.benchmark import (
    FORBIDDEN_PUBLIC_KEY_NAMES,
    MANDATORY_CHALLENGE_TAGS,
    MANDATORY_FAMILY_KEYS,
    ArmPromptReceipt,
    BenchmarkRunReceipt,
    BlindLabelAssignment,
    BlindLabelMapping,
    CorpusPartition,
    GateDomain,
    HardGateRequirement,
    JudgeReceipt,
    NonCompensatoryGateContract,
    PerformanceComparator,
    PerformanceMetric,
    PerformanceMetricRequirement,
    PerformanceObservation,
    ReceiptStatus,
    RecursiveClosureReceiptRef,
    ResourcePerformanceContract,
    ResourcePerformanceReceipt,
    RunStatus,
    load_sealed_public_corpus,
    validate_arm_prompt_receipt,
    validate_blind_label_mapping,
)

FIXTURES = Path(__file__).parent / "fixtures"
_A = "a" * 64
_B = "b" * 64
_C = "c" * 64
_D = "d" * 64


def _corpus():
    return load_sealed_public_corpus(
        FIXTURES / "formulation_intelligence_benchmark_v1.json",
        FIXTURES / "formulation_intelligence_benchmark_v1.sha256",
    )


def _closure() -> RecursiveClosureReceiptRef:
    return RecursiveClosureReceiptRef(
        receipt_id="closure:benchmark:v1",
        receipt_sha256=_A,
        closure_manifest_sha256=_B,
    )


def _arm_prompt_receipt() -> ArmPromptReceipt:
    corpus = _corpus()
    case = corpus.cases[0]
    arm = corpus.anonymized_arms[0]
    return ArmPromptReceipt(
        receipt_id="arm-prompt:case-01:arm-01",
        corpus_sha256=corpus.content_sha256,
        case_id=case.case_id,
        arm_id=arm.arm_id,
        case_prompt_sha256=case.prompt_sha256,
        arm_instruction_sha256=_C,
        rendered_prompt_sha256=_D,
        recursive_closure=_closure(),
    )


def _mapping(corpus) -> BlindLabelMapping:
    assignments = tuple(
        BlindLabelAssignment(blind_label=f"label-{index:02d}", arm_id=arm.arm_id)
        for index, arm in enumerate(corpus.anonymized_arms, start=1)
    )
    mapping_payload = [item.as_dict() for item in assignments]
    mapping_sha256 = sha256(
        json.dumps(
            mapping_payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return BlindLabelMapping(
        mapping_id="scorer-map:wp13:v1",
        assignments=assignments,
        mapping_sha256=mapping_sha256,
    )


def _run_receipt(
    *,
    provider_id: str = "openai",
    status: RunStatus = RunStatus.COMPLETED,
    output_sha256: str | None = _C,
    started_at_utc: str = "2026-09-01T01:00:00Z",
    finished_at_utc: str = "2026-09-01T01:00:01Z",
) -> BenchmarkRunReceipt:
    return BenchmarkRunReceipt(
        run_id="run:wp13:0002",
        arm_prompt_receipt_sha256=_A,
        execution_config_sha256=_B,
        provider_id=provider_id,
        model_id="gpt-5.6-sol",
        reasoning_level="ultra",
        status=status,
        output_sha256=output_sha256,
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
        input_tokens=1,
        output_tokens=1,
        recursive_closure=_closure(),
    )


def test_public_corpus_fixture_is_hash_verified_and_sealed() -> None:
    corpus = _corpus()

    assert corpus.sealed is True
    assert corpus.benchmark_execution_authorized is False
    assert corpus.empirical_authority is False
    assert {item.partition for item in corpus.cases} == set(CorpusPartition)
    assert MANDATORY_FAMILY_KEYS <= {item.family_key for item in corpus.cases}
    assert MANDATORY_CHALLENGE_TAGS <= {tag for item in corpus.cases for tag in item.challenge_tags}
    assert len(corpus.anonymized_arms) == 5
    assert all(
        set(item.as_dict()) == {"schema_version", "arm_id"} for item in corpus.anonymized_arms
    )
    assert all(
        sha256(item.prompt_text.encode("utf-8")).hexdigest() == item.prompt_sha256
        for item in corpus.cases
    )


def test_public_fixture_contains_invariant_keys_but_no_scorer_solutions() -> None:
    payload = json.loads(
        (FIXTURES / "formulation_intelligence_benchmark_v1.json").read_text(encoding="utf-8")
    )

    def all_keys(value):
        if isinstance(value, dict):
            return set(value) | {key for item in value.values() for key in all_keys(item)}
        if isinstance(value, list):
            return {key for item in value for key in all_keys(item)}
        return set()

    keys = all_keys(payload)
    assert keys.isdisjoint(FORBIDDEN_PUBLIC_KEY_NAMES)
    for case in payload["cases"]:
        assert set(case["invariants"]) == {
            "schema_version",
            "required_evidence_keys",
            "authority_keys",
            "inventory_keys",
            "protocol_keys",
        }


def test_fixture_byte_tampering_and_scorer_key_injection_fail_closed(tmp_path: Path) -> None:
    original = (FIXTURES / "formulation_intelligence_benchmark_v1.json").read_bytes()
    digest = FIXTURES / "formulation_intelligence_benchmark_v1.sha256"
    tampered = tmp_path / "tampered.json"
    tampered.write_bytes(original.replace(b'"sealed": true', b'"sealed": false', 1))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_sealed_public_corpus(tampered, digest)

    payload = json.loads(original)
    payload["answer_key"] = {"leaked": True}
    injected_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    injected = tmp_path / "injected.json"
    injected_sha = tmp_path / "injected.sha256"
    injected.write_bytes(injected_bytes)
    injected_sha.write_text(sha256(injected_bytes).hexdigest(), encoding="ascii")
    with pytest.raises(ValueError, match="scorer-only keys"):
        load_sealed_public_corpus(injected, injected_sha)


def test_arm_prompt_run_and_judge_receipts_are_strict_hash_only_records() -> None:
    corpus = _corpus()
    arm_prompt = _arm_prompt_receipt()
    validate_arm_prompt_receipt(corpus, arm_prompt)
    run = BenchmarkRunReceipt(
        run_id="run:wp13:0001",
        arm_prompt_receipt_sha256=arm_prompt.content_sha256,
        execution_config_sha256=_A,
        provider_id="openai",
        model_id="gpt-5.6-sol",
        reasoning_level="ultra",
        status=RunStatus.COMPLETED,
        output_sha256=_B,
        started_at_utc="2026-09-01T01:00:00Z",
        finished_at_utc="2026-09-01T01:00:01Z",
        input_tokens=100,
        output_tokens=40,
        recursive_closure=_closure(),
    )
    judge = JudgeReceipt(
        judge_receipt_id="judge:wp13:0001",
        blinded_bundle_sha256=_A,
        rubric_sha256=_B,
        scorer_provider_id="openai",
        scorer_identity="independent-scorer-01",
        scorer_config_sha256=_C,
        score_artifact_sha256=_D,
        observed_at_utc="2026-09-01T02:00:00Z",
        blind_mapping_embedded=False,
        recursive_closure=_closure(),
    )

    assert ArmPromptReceipt.from_dict(arm_prompt.as_dict()) == arm_prompt
    assert BenchmarkRunReceipt.from_dict(run.as_dict()) == run
    assert JudgeReceipt.from_dict(judge.as_dict()) == judge
    assert "condition" not in arm_prompt.as_dict()
    assert "output" not in run.as_dict()
    assert "blind_label_mapping" not in judge.as_dict()
    payload = run.as_dict()
    payload["extra"] = True
    with pytest.raises(ValueError, match="closed schema"):
        BenchmarkRunReceipt.from_dict(payload)
    with pytest.raises(FrozenInstanceError):
        run.model_id = "mutated"  # type: ignore[misc]


def test_receipts_fail_closed_on_external_provider_invalid_time_or_output_state() -> None:
    with pytest.raises(ValueError, match="OpenAI-only"):
        _run_receipt(provider_id="external-provider")
    with pytest.raises(ValueError, match="require output_sha256"):
        _run_receipt(output_sha256=None)
    with pytest.raises(ValueError, match="must not claim"):
        _run_receipt(status=RunStatus.FAILED)
    with pytest.raises(ValueError, match="must not precede"):
        _run_receipt(
            started_at_utc="2026-09-01T01:00:02Z",
            finished_at_utc="2026-09-01T01:00:01Z",
        )


def test_blind_mapping_is_separate_scorer_input_and_exactly_covers_arms() -> None:
    corpus = _corpus()
    mapping = _mapping(corpus)

    validate_blind_label_mapping(corpus, scorer_mapping=mapping)
    assert BlindLabelMapping.from_dict(mapping.as_dict()) == mapping
    assert "mapping" not in corpus.as_dict()
    assert "mapping" not in _arm_prompt_receipt().as_dict()
    incomplete_assignments = mapping.assignments[:-1]
    incomplete_hash = sha256(
        json.dumps(
            [item.as_dict() for item in incomplete_assignments],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    incomplete = BlindLabelMapping(
        mapping_id="scorer-map:incomplete",
        assignments=incomplete_assignments,
        mapping_sha256=incomplete_hash,
    )
    with pytest.raises(ValueError, match="cover every anonymized arm"):
        validate_blind_label_mapping(corpus, scorer_mapping=incomplete)
    with pytest.raises(ValueError, match="must not embed"):
        JudgeReceipt(
            judge_receipt_id="judge:bad",
            blinded_bundle_sha256=_A,
            rubric_sha256=_B,
            scorer_provider_id="openai",
            scorer_identity="judge",
            scorer_config_sha256=_C,
            score_artifact_sha256=_D,
            observed_at_utc="2026-09-01T02:00:00Z",
            blind_mapping_embedded=True,
            recursive_closure=_closure(),
        )


def _noncompensatory_contract() -> NonCompensatoryGateContract:
    return NonCompensatoryGateContract(
        contract_id="wp13.noncompensatory.v1",
        hard_gates=tuple(
            HardGateRequirement(
                gate_key=f"critical.{domain.value}",
                domain=domain,
                maximum_critical_errors=0,
                compensable_by_prose_quality=False,
            )
            for domain in GateDomain
        ),
        required_superiority_endpoint_keys=(
            "blinded_usefulness",
            "calibration",
            "efficiency",
            "plain_superiority",
            "placebo_superiority",
            "stability",
        ),
        exact_keyed_correctness_compensable=False,
        safe_no_change_required=True,
        held_out_family_required=True,
        seed_order_stability_required=True,
        admission_authorized=False,
    )


def test_noncompensatory_gate_contract_covers_all_critical_domains() -> None:
    contract = _noncompensatory_contract()

    assert NonCompensatoryGateContract.from_dict(contract.as_dict()) == contract
    assert {item.domain for item in contract.hard_gates} == set(GateDomain)
    assert all(item.maximum_critical_errors == 0 for item in contract.hard_gates)
    assert all(not item.compensable_by_prose_quality for item in contract.hard_gates)
    assert contract.exact_keyed_correctness_compensable is False
    assert contract.admission_authorized is False
    with pytest.raises(ValueError, match="every critical gate domain"):
        NonCompensatoryGateContract(
            **{
                **{
                    item.name: getattr(contract, item.name)
                    for item in __import__("dataclasses").fields(contract)
                },
                "hard_gates": contract.hard_gates[:-1],
            }
        )
    with pytest.raises(ValueError, match="zero errors"):
        HardGateRequirement(
            gate_key="critical.authority",
            domain=GateDomain.AUTHORITY,
            maximum_critical_errors=1,
            compensable_by_prose_quality=False,
        )


def _performance_contract() -> ResourcePerformanceContract:
    requirements = tuple(
        PerformanceMetricRequirement(
            metric=metric,
            unit=(
                "ms"
                if metric.value.endswith("_ms")
                else "mib"
                if metric is PerformanceMetric.PEAK_MEMORY_MIB
                else "ratio"
            ),
            comparator=PerformanceComparator.AT_MOST,
            bound=1000.0,
        )
        for metric in PerformanceMetric
    )
    return ResourcePerformanceContract(
        contract_id="wp13.performance.v1",
        requirements=requirements,
        predecessor_receipt_sha256=_A,
        recursive_closure_required=True,
        unsafe_quality_tradeoff_allowed=False,
        admission_authorized=False,
    )


def test_resource_performance_contract_and_receipt_bind_recursive_closure() -> None:
    contract = _performance_contract()
    observations = tuple(
        PerformanceObservation(
            metric=requirement.metric,
            unit=requirement.unit,
            value=10.0,
            sample_count=3,
            conditions_sha256=_B,
        )
        for requirement in contract.requirements
    )
    receipt = ResourcePerformanceReceipt(
        receipt_id="wp13.performance.receipt.0001",
        contract=contract,
        run_receipt_sha256s=(_C,),
        observations=observations,
        status=ReceiptStatus.PASS,
        observed_at_utc="2026-09-01T03:00:00Z",
        recursive_closure=_closure(),
        admission_authorized=False,
    )

    assert ResourcePerformanceContract.from_dict(contract.as_dict()) == contract
    assert ResourcePerformanceReceipt.from_dict(receipt.as_dict()) == receipt
    assert {item.metric for item in receipt.observations} == set(PerformanceMetric)
    assert receipt.recursive_closure.receipt_sha256 == _A
    assert receipt.admission_authorized is False
    with pytest.raises(ValueError, match="every performance metric"):
        ResourcePerformanceContract(
            contract_id="wp13.performance.incomplete",
            requirements=contract.requirements[:-1],
            predecessor_receipt_sha256=_A,
            recursive_closure_required=True,
            unsafe_quality_tradeoff_allowed=False,
            admission_authorized=False,
        )


def test_resource_performance_status_is_derived_from_bound_contract() -> None:
    contract = _performance_contract()
    violating = tuple(
        PerformanceObservation(
            metric=requirement.metric,
            unit=requirement.unit,
            value=requirement.bound + 1.0,
            sample_count=3,
            conditions_sha256=_B,
        )
        for requirement in contract.requirements
    )

    with pytest.raises(ValueError, match="status does not match contract observations"):
        ResourcePerformanceReceipt(
            receipt_id="wp13.performance.false-pass",
            contract=contract,
            run_receipt_sha256s=(_C,),
            observations=violating,
            status=ReceiptStatus.PASS,
            observed_at_utc="2026-09-01T03:00:00Z",
            recursive_closure=_closure(),
            admission_authorized=False,
        )

    failed = ResourcePerformanceReceipt(
        receipt_id="wp13.performance.derived-fail",
        contract=contract,
        run_receipt_sha256s=(_C,),
        observations=violating,
        status=ReceiptStatus.FAIL,
        observed_at_utc="2026-09-01T03:00:00Z",
        recursive_closure=_closure(),
        admission_authorized=False,
    )
    assert failed.status is ReceiptStatus.FAIL


def test_benchmark_module_import_is_standard_library_only() -> None:
    script = (
        "import sys; import engine.formulation_intelligence.benchmark; "
        "blocked=('torch','faiss','sentence_transformers','matplotlib','engine.pipeline'); "
        "print(','.join(name for name in blocked if name in sys.modules))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
    )
    assert completed.stdout.strip() == ""
