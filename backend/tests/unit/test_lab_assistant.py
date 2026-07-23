import json

import pytest

from app.services.lab_assistant import (
    AssistantRequest,
    build_assistant_packet,
    classify_chat_intent,
)


def test_supported_assistant_packet_is_byte_stable_and_complete():
    first = build_assistant_packet(
        AssistantRequest(
            intent="bottle_status",
            subject_id="bottle-1",
            facts={"stock_masses_g": {"B": 0.2, "A": 0.1}, "total_mass_g": 1.2},
            calculations={"active_ppm_w_w": 123.4567894},
            evidence={"mass": {"classification": "EXACT", "source": "ledger"}},
            assumptions=("Ledger replay is complete.",),
            limitations=("No direct density measurement.",),
        )
    )
    second = build_assistant_packet(
        AssistantRequest(
            intent="bottle_status",
            subject_id="bottle-1",
            facts={"total_mass_g": 1.2, "stock_masses_g": {"A": 0.1, "B": 0.2}},
            calculations={"active_ppm_w_w": 123.4567894},
            evidence={"mass": {"source": "ledger", "classification": "EXACT"}},
            assumptions=("Ledger replay is complete.",),
            limitations=("No direct density measurement.",),
        )
    )

    assert first.status == "ready"
    assert first.tool_plan == ("LabService.reconstruct_bottle",)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.payload_sha256 == second.payload_sha256
    payload = json.loads(first.canonical_bytes())
    assert payload["canonicalization"]["revision"] == "lab-packet-v1"
    assert payload["facts"]["total_mass_g"] == "1.200000"
    assert payload["calculations"]["active_ppm_w_w"] == "123.456789"
    assert payload["next_action"]
    assert "generated_at" not in payload


def test_assistant_requires_subject_for_subject_intent():
    packet = build_assistant_packet(AssistantRequest(intent="formula_analysis"))

    assert packet.status == "needs_input"
    assert packet.tool_plan == ()
    assert packet.evidence["assistant_claim"]["classification"] == "UNKNOWN"


def test_assistant_refuses_unsupported_scientific_claim():
    packet = build_assistant_packet(
        AssistantRequest(
            intent="prove_this_is_safe_and_will_last_12_hours",
            facts={"marketing_claim": "12 hours"},
        )
    )

    assert packet.status == "refused"
    assert packet.facts == {}
    assert packet.calculations == {}
    assert packet.evidence["assistant_claim"]["classification"] == "UNKNOWN"
    assert "supported intent" in packet.next_action


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Make Prada L'Homme with my current materials", "reference_formulation"),
        ("Design a luxury orris version of this fragrance", "reference_formulation"),
        ("Can you reconstruct a classic aromatic fougere?", "reference_formulation"),
        ("I want something inspired by Eau Sauvage", "reference_formulation"),
        ("What ingredient should I buy next?", "purchase_gap_analysis"),
        ("Which materials should I purchase to extend my range?", "purchase_gap_analysis"),
        ("What are the next best ingredients?", "purchase_gap_analysis"),
        ("Which perfume families have I not made?", "family_gap_analysis"),
        ("What types of perfume are missing from my collection?", "family_gap_analysis"),
        ("What family should I try next?", "family_gap_analysis"),
        ("This perfume is weak and has no projection", "performance_diagnosis"),
        ("Why doesn't this fragrance last?", "performance_diagnosis"),
        ("The sillage fades too fast", "performance_diagnosis"),
        ("How do I save this finished batch?", "finished_batch_rescue"),
        ("How much should I add to fix my perfume?", "finished_batch_rescue"),
        ("Additions only to an already mixed fragrance", "finished_batch_rescue"),
        ("Rescue the source bottle without reformulating", "finished_batch_rescue"),
        ("Is this perfume safe for skin use?", "safety_assessment"),
        ("Check IFRA and allergens", "safety_assessment"),
        ("Analyze what is wrong with this formula", "formula_analysis"),
        ("Diagnose why did my formula fail", "formula_analysis"),
        ("What does OAV mean in perfume?", "perfume_knowledge_question"),
        ("Tell me about fragrance evaporation", "perfume_knowledge_question"),
    ],
)
def test_chat_prompts_route_deterministically(prompt, expected):
    route = classify_chat_intent(prompt)

    assert route is not None
    assert route.intent == expected


def test_chat_request_is_preserved_as_input_not_promoted_to_a_claim():
    prompt = "What does OAV mean in perfume?"
    packet = build_assistant_packet(AssistantRequest(intent=prompt))

    assert packet.status == "ready"
    assert packet.intent == "perfume_knowledge_question"
    assert packet.facts["chat_request"] == prompt
    assert packet.evidence["intent_routing"]["classification"] == "EXACT"
