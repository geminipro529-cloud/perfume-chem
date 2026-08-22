from __future__ import annotations

from dataclasses import replace

from engine.perception.complexity_ensemble import ComplexityCasePacket
from engine.perception.complexity_xhigh import (
    BenchmarkArm,
    anonymize_response_pair,
    prepare_xhigh_request,
    validate_xhigh_execution,
)
from tests.complexity_benchmark_fixtures import (
    valid_bundle,
    valid_case_mapping,
    valid_execution_receipt,
)


def test_control_excludes_module_bundle_and_treatment_includes_only_bundle_delta() -> None:
    case = ComplexityCasePacket.from_mapping(valid_case_mapping())
    bundle = valid_bundle(case)
    control = prepare_xhigh_request(case, BenchmarkArm.CONTROL, bundle=None)
    treatment = prepare_xhigh_request(case, BenchmarkArm.TREATMENT, bundle=bundle)
    assert "module_bundle" not in control.prompt_payload
    assert treatment.prompt_payload["module_bundle"] == bundle.as_dict()
    assert control.common_input_sha256 == treatment.common_input_sha256
    assert control.nonce != treatment.nonce
    assert control.prompt_payload["complexity_definition"] == (
        treatment.prompt_payload["complexity_definition"]
    )
    assert control.prompt_payload["complexity_definition"]["claim_ceiling"] == (
        "DESIGN_HYPOTHESIS_NOT_TESTED"
    )
    assert "ingredient count" in control.prompt_payload["complexity_definition"][
        "invalid_proxies"
    ]
    assert "expected_invariants" not in control.prompt_payload
    assert "construction_profile" not in str(control.prompt_payload)


def test_unverified_model_effort_context_or_duplicate_nonce_blocks() -> None:
    request = prepare_xhigh_request(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        BenchmarkArm.CONTROL,
        bundle=None,
    )
    for field, bad in (
        ("reasoning_effort", "high"),
        ("context_clean", False),
        ("completion_state", "AMBIGUOUS"),
    ):
        receipt = replace(valid_execution_receipt(request), **{field: bad})
        result = validate_xhigh_execution(
            request, receipt, seen_nonces=frozenset()
        )
        assert result.state.startswith("BENCHMARK_BLOCKED")
    duplicate = validate_xhigh_execution(
        request,
        valid_execution_receipt(request),
        seen_nonces=frozenset({request.nonce}),
    )
    assert duplicate.state == "BENCHMARK_BLOCKED_DUPLICATE_NONCE"


def test_response_bytes_must_match_execution_receipt() -> None:
    request = prepare_xhigh_request(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        BenchmarkArm.CONTROL,
        bundle=None,
    )
    receipt = valid_execution_receipt(request, response_bytes=b'{"ok":true}')
    assert validate_xhigh_execution(
        request,
        receipt,
        seen_nonces=frozenset(),
        response_bytes=b'{"ok":true}',
    ).state == "PASS"
    assert validate_xhigh_execution(
        request,
        receipt,
        seen_nonces=frozenset(),
        response_bytes=b'{"ok":false}',
    ).state == "BENCHMARK_BLOCKED_RESPONSE_HASH_MISMATCH"


def test_product_telemetry_is_not_estimated_when_absent() -> None:
    request = prepare_xhigh_request(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        BenchmarkArm.CONTROL,
        bundle=None,
    )
    receipt = replace(
        valid_execution_receipt(request),
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
        price_usd=None,
    )
    assert receipt.telemetry_state == "NOT_EXPOSED"


def test_anonymization_is_deterministic_and_exposes_no_arm_or_request_id() -> None:
    packets = anonymize_response_pair(
        "f" * 64,
        "CX-A01",
        {
            BenchmarkArm.CONTROL: b'{"answer_markdown":"one"}',
            BenchmarkArm.TREATMENT: b'{"answer_markdown":"two"}',
        },
    )
    assert len(packets) == 2
    assert len({packet.anonymous_label for packet in packets}) == 2
    assert all(len(packet.response_sha256) == 64 for packet in packets)
    assert all("CONTROL" not in repr(packet) for packet in packets)
    assert all("TREATMENT" not in repr(packet) for packet in packets)
    assert packets == anonymize_response_pair(
        "f" * 64,
        "CX-A01",
        {
            BenchmarkArm.CONTROL: b'{"answer_markdown":"one"}',
            BenchmarkArm.TREATMENT: b'{"answer_markdown":"two"}',
        },
    )
