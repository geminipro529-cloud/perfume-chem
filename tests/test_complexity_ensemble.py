from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.perception.complexity_ensemble import (
    ComplexityCasePacket,
    ablate_complexity_case,
    evaluate_complexity_case,
)
from engine.perception.complexity_registry import load_complexity_registry
from tests.complexity_benchmark_fixtures import valid_case_mapping

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_complexity_registry(
    ROOT,
    ROOT / "configs/complexity/complexity_module_registry_v1.json",
)


def test_case_packet_requires_exact_hashes_and_unique_relevance() -> None:
    packet = ComplexityCasePacket.from_mapping(valid_case_mapping())
    assert packet.case_id == "CX-A01"
    with pytest.raises(ValueError, match="relevant family"):
        ComplexityCasePacket.from_mapping(
            {
                **valid_case_mapping(),
                "relevant_families": [
                    "construction_profile",
                    "construction_profile",
                ],
            }
        )
    with pytest.raises(ValueError, match="inventory authority"):
        ComplexityCasePacket.from_mapping(
            {**valid_case_mapping(), "inventory_authority_sha256": "0" * 64}
        )


def test_case_packet_deep_copies_and_freezes_nested_input() -> None:
    source = valid_case_mapping()
    packet = ComplexityCasePacket.from_mapping(source)
    source["module_inputs"]["construction_profile"]["materials"][0]["name"] = "MUTATED"
    assert packet.module_inputs["construction_profile"]["materials"][0]["name"] == "A"
    with pytest.raises(TypeError):
        packet.module_inputs["construction_profile"]["new"] = "not allowed"


def test_ensemble_keeps_family_outputs_separate_and_has_no_overall_score() -> None:
    bundle = evaluate_complexity_case(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        REGISTRY,
        adapters={
            "construction_profile": lambda _payload: {
                "axes": {"formula_structure": {"status": "AVAILABLE"}}
            }
        },
    )
    encoded = json.dumps(bundle.as_dict(), sort_keys=True)
    assert bundle.state == "PASS"
    assert set(bundle.family_outputs) == {"construction_profile"}
    assert "overall_score" not in encoded
    assert bundle.formula_authority is False
    assert bundle.release_authority is False


def test_relevant_missing_input_and_omitted_guardrail_fail_closed() -> None:
    packet = ComplexityCasePacket.from_mapping(
        valid_case_mapping(
            relevant_families=("admission_lifecycle",),
            module_inputs={},
        )
    )
    result = evaluate_complexity_case(packet, REGISTRY, adapters={})
    assert result.state == "HOLD"
    assert "missing input" in " ".join(result.blockers)
    with pytest.raises(ValueError, match="mandatory guardrail"):
        ablate_complexity_case(
            packet,
            REGISTRY,
            omitted_family="admission_lifecycle",
            adapters={},
        )


def test_adapter_failure_or_aggregate_score_fails_closed() -> None:
    packet = ComplexityCasePacket.from_mapping(valid_case_mapping())

    def broken(_payload):
        raise RuntimeError("adapter exploded")

    failed = evaluate_complexity_case(
        packet,
        REGISTRY,
        adapters={"construction_profile": broken},
    )
    assert failed.state == "HOLD"
    assert "adapter exploded" in " ".join(failed.blockers)

    scored = evaluate_complexity_case(
        packet,
        REGISTRY,
        adapters={"construction_profile": lambda _payload: {"overall_score": 99}},
    )
    assert scored.state == "HOLD"
    assert "aggregate score" in " ".join(scored.blockers)
