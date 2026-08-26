from __future__ import annotations

import json
from pathlib import Path

from engine.solforge.conclusions import ConclusionLevel
from engine.solforge.programs import (
    PROGRAM_AUTHORITY_FLAGS,
    ProgramEndpointV1,
    ProgramProtocolRequirementV1,
    ScientificProgramV1,
    evaluate_program_readiness,
    load_scientific_programs,
)

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ROOT / "configs/solforge/scientific_programs_v1.json"


def test_all_ten_scientific_programs_are_complete_and_nonpromoting() -> None:
    programs = load_scientific_programs(PROGRAMS)
    assert len(programs) == 10
    assert {program.program_id for program in programs} == {
        "ARCHITECTURAL_DELTA",
        "TEMPORAL_LEDGER",
        "PREFERENCE_LEARNER",
        "PERCEPTUAL_TOPOLOGY",
        "ART_COMPOSITION_TOPOLOGY",
        "WOOD_DEPTH",
        "CITRUS_ARCHITECTURE",
        "MUSK_ARCHITECTURE",
        "FLORAL_ORRIS_ARCHITECTURE",
        "AMBER_RESIN_INCENSE_ARCHITECTURE",
    }
    for program in programs:
        assert evaluate_program_readiness(program) == ()
        assert program.as_dict()["authority_flags"] == PROGRAM_AUTHORITY_FLAGS
        assert program.required_conclusion_level in ConclusionLevel
        assert len(program.controls) >= 1
        assert len(program.failure_criteria) >= 1
        assert len(program.protocol_requirements) >= 5


def test_liking_is_a_separate_endpoint_when_present() -> None:
    programs = load_scientific_programs(PROGRAMS)
    for program in programs:
        liking = [endpoint for endpoint in program.endpoints if endpoint.criterion == "LIKING"]
        if liking:
            assert all(endpoint.endpoint_id != program.primary_endpoint_id for endpoint in liking)
            assert program.primary_endpoint.criterion != "LIKING"


def test_endpoint_and_requirement_round_trip() -> None:
    endpoint = ProgramEndpointV1(
        endpoint_id="E1",
        criterion="DEPTH",
        measure="blinded paired depth judgment",
        primary=True,
        physical_observation_required=True,
    )
    requirement = ProgramProtocolRequirementV1(
        requirement_id="BLINDING",
        requirement="Opaque blind codes with concealed condition labels.",
    )
    assert ProgramEndpointV1.from_dict(endpoint.as_dict()) == endpoint
    assert ProgramProtocolRequirementV1.from_dict(requirement.as_dict()) == requirement


def test_count_and_proxy_endpoints_fail_readiness() -> None:
    program = load_scientific_programs(PROGRAMS)[0]
    payload = program.as_dict()
    payload["endpoints"][0]["measure"] = "ingredient count and OAV sum"
    broken = ScientificProgramV1.from_dict(payload)
    issues = " ".join(evaluate_program_readiness(broken)).casefold()
    assert "ingredient count" in issues
    assert "oav sum" in issues


def test_every_program_forbids_the_full_proxy_set() -> None:
    expected = {
        "ingredient count",
        "formula frequency",
        "supplier prose",
        "price",
        "prestige",
        "oav sum",
        "modeled volatility",
        "darkness",
        "loudness",
        "complexity jargon",
    }
    for program in load_scientific_programs(PROGRAMS):
        assert set(program.forbidden_proxies) == expected


def test_closed_program_schema_rejects_true_authority() -> None:
    payload = json.loads(PROGRAMS.read_text(encoding="utf-8"))["programs"][0]
    payload["authority_flags"]["hedonic"] = True
    try:
        ScientificProgramV1.from_dict(payload)
    except ValueError as exc:
        assert "authority_flags" in str(exc)
    else:
        raise AssertionError("true authority flag was accepted")
