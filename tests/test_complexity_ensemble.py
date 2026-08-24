from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from engine.calibration.hashing import canonical_json_bytes
from engine.perception.complexity_adapters import DEFAULT_COMPLEXITY_ADAPTERS
from engine.perception.complexity_ensemble import (
    ComplexityCasePacket,
    ablate_complexity_case,
    evaluate_complexity_case,
)
from engine.perception.complexity_registry import ModuleState, load_complexity_registry
from tests.complexity_benchmark_fixtures import valid_case_mapping

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/fixtures/complexity_xhigh_cases_v1.json"
SIDECAR = ROOT / "tests/fixtures/complexity_xhigh_cases_v1.sha256"
REGISTRY = load_complexity_registry(
    ROOT,
    ROOT / "configs/complexity/complexity_module_registry_v2.json",
)
_PRERETIREMENT_RUNTIME = {
    "construction-profile": (
        ModuleState.ACTIVE_CANDIDATE,
        "engine.perception.construction_complexity",
    ),
    "complexity-expansion-frontier": (
        ModuleState.ACTIVE_CANDIDATE,
        "engine.perception.complexity_expansion",
    ),
    "musk-design-restraint": (
        ModuleState.ACTIVE_CANDIDATE,
        "engine.perception.musk_design",
    ),
    "complexity-model-admission": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.scientific_validation.complexity_model_admission",
    ),
    "complexity-model-lifecycle": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.physics.model_lifecycle",
    ),
    "within-sniff-observation-contract": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.sensory.within_sniff",
    ),
    "temporal-observation-contract": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.sensory.temporal_observations",
    ),
    "order-balance-contract": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.sensory.order_balance",
    ),
    "sensory-panel-contract": (
        ModuleState.MANDATORY_GUARDRAIL,
        "engine.sensory.panel_contract",
    ),
}


def _restore_preretirement_runtime(module):
    override = _PRERETIREMENT_RUNTIME.get(module.module_id)
    if override is None:
        return module
    state, import_path = override
    return replace(module, state=state, import_path=import_path)


UNIT_REGISTRY = replace(
    REGISTRY,
    modules=tuple(_restore_preretirement_runtime(module) for module in REGISTRY.modules),
)


def _corpus_payload() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))


def _cases() -> list[dict]:
    payload = _corpus_payload()
    shared = payload["shared_module_inputs"]
    shared_invariants = payload["shared_invariants"]
    resolved = []
    for raw in payload["cases"]:
        case = dict(raw)
        refs = case.pop("module_input_refs")
        case["module_inputs"] = {
            family: shared[reference] for family, reference in refs.items()
        }
        expected = dict(case["expected_invariants"])
        definition_ref = expected.pop("complexity_definition_ref")
        response_ref = expected.pop("valid_response_ref")
        expected["complexity_definition"] = shared_invariants[definition_ref]
        expected["valid_response"] = payload["rubric"][response_ref]
        expected["required_depth_fields"] = shared_invariants[
            "required_depth_fields"
        ]
        expected["required_claim_states"] = shared_invariants[
            "required_claim_states"
        ]
        expected["forbidden_claims"] = shared_invariants["forbidden_claims"]
        expected["required_sections"] = shared_invariants["required_sections"]
        case["expected_invariants"] = expected
        resolved.append(case)
    return resolved


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
        UNIT_REGISTRY,
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
    result = evaluate_complexity_case(packet, UNIT_REGISTRY, adapters={})
    assert result.state == "HOLD"
    assert "missing input" in " ".join(result.blockers)
    with pytest.raises(ValueError, match="mandatory guardrail"):
        ablate_complexity_case(
            packet,
            UNIT_REGISTRY,
            omitted_family="admission_lifecycle",
            adapters={},
        )


def test_adapter_failure_or_aggregate_score_fails_closed() -> None:
    packet = ComplexityCasePacket.from_mapping(valid_case_mapping())

    def broken(_payload):
        raise RuntimeError("adapter exploded")

    failed = evaluate_complexity_case(
        packet,
        UNIT_REGISTRY,
        adapters={"construction_profile": broken},
    )
    assert failed.state == "HOLD"
    assert "adapter exploded" in " ".join(failed.blockers)

    scored = evaluate_complexity_case(
        packet,
        UNIT_REGISTRY,
        adapters={"construction_profile": lambda _payload: {"overall_score": 99}},
    )
    assert scored.state == "HOLD"
    assert "aggregate score" in " ".join(scored.blockers)


def test_frozen_corpus_has_four_cases_per_category_and_exact_hash() -> None:
    payload = _corpus_payload()
    assert payload["schema_version"] == "complexity_xhigh_cases_v1"
    assert len(payload["cases"]) == 16
    counts = Counter(case["category"] for case in payload["cases"])
    assert counts == {
        "TARGET_ARCHITECTURE": 4,
        "RECONSTRUCTION_REVISION": 4,
        "MISSING_CHEMICAL_IMPACT": 4,
        "EXPERIMENTAL_EVIDENCE_DESIGN": 4,
    }
    assert sum(
        bool(case["expected_invariants"]["critical_traps"])
        for case in payload["cases"]
    ) >= 4
    assert sum(
        bool(case["expected_invariants"]["anti_complication_case"])
        for case in payload["cases"]
    ) >= 8
    assert (
        hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        == SIDECAR.read_text(encoding="utf-8").split()[0]
    )


def test_every_case_binds_current_inventory_and_declares_relevance() -> None:
    for raw in _cases():
        case = ComplexityCasePacket.from_mapping(raw)
        assert (
            case.inventory_authority_sha256
            == "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
        )
        assert (
            case.local_inventory_sha256
            == "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
        )
        assert case.relevant_families
        definition = case.expected_invariants["complexity_definition"]
        assert definition["claim_ceiling"] == "DESIGN_HYPOTHESIS_NOT_TESTED"
        assert "ingredient count" in definition["invalid_proxies"]


def test_every_frozen_case_executes_its_relevant_module_bundle() -> None:
    for mapping in _cases():
        bundle = evaluate_complexity_case(
            ComplexityCasePacket.from_mapping(mapping),
            UNIT_REGISTRY,
            adapters=DEFAULT_COMPLEXITY_ADAPTERS,
        )
        assert bundle.state == "PASS", (mapping["case_id"], bundle.blockers)
        assert not bundle.blockers


def test_live_registry_fails_closed_for_a_retired_family() -> None:
    bundle = evaluate_complexity_case(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        REGISTRY,
        adapters=DEFAULT_COMPLEXITY_ADAPTERS,
    )
    assert bundle.state == "HOLD"
    assert bundle.blockers == (
        "construction_profile: no runtime-eligible module",
    )


def test_anti_complication_cases_cover_required_failure_modes() -> None:
    cases = [
        case
        for case in _cases()
        if case["expected_invariants"]["anti_complication_case"]
    ]
    covered = {
        mode
        for case in cases
        for mode in case["expected_invariants"]["complication_failure_modes"]
    }
    assert {
        "BLOAT",
        "REDUNDANCY",
        "MUD",
        "SUPERFICIAL_DIVERSITY",
        "FLAT_DEVELOPMENT",
        "INCOHERENT_NOVELTY",
        "NEEDED_SUBTRACTION",
    }.issubset(covered)


def test_musk_cases_cover_sparse_layered_and_all_named_exceptions() -> None:
    cases = [
        case
        for case in _cases()
        if "musk_design_restraint" in case["relevant_families"]
    ]
    assert len(cases) >= 4
    modes = {case["expected_invariants"]["musk_case_mode"] for case in cases}
    assert {
        "SPARSE",
        "LAYERED",
        "EXCEPTION_BLOCK",
        "EXCEPTION_TARGET_ONLY",
    }.issubset(modes)
    materials = {
        material
        for case in cases
        for material in case["expected_invariants"].get("exception_materials", [])
    }
    assert materials == {"Tonalide", "Macrolide", "Musk Ketone"}


def test_contrastive_case_pairs_change_one_decisive_fact() -> None:
    payload = _corpus_payload()
    pairs = payload["contrastive_pairs"]
    assert len(pairs) == 8
    assert {case_id for pair in pairs for case_id in pair["case_ids"]} == {
        case["case_id"] for case in payload["cases"]
    }
    assert all(pair["single_changed_fact"].strip() for pair in pairs)
