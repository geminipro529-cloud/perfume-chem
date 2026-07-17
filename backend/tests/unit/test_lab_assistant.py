import json

from app.services.lab_assistant import AssistantRequest, build_assistant_packet


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
