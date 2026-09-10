from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.schemas.lab_reporting import SCIENCE_SECTION_KEYS
from app.services.c0_semantic_readback import (
    C0SemanticReadbackState,
    revalidate_c0_lab_persistence_graph,
)

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "c0_lab_persistence_projection_v1.json"
)


def _graph() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _rehash_observation(record: dict) -> None:
    payload = record["observations_json"]
    payload["panel_observation_sha256"] = _stable_hash(payload["panel_observation"])


def test_valid_c0_readback_replays_deterministically_and_grants_no_authority() -> None:
    graph = _graph()

    first = revalidate_c0_lab_persistence_graph(graph)
    second = revalidate_c0_lab_persistence_graph(copy.deepcopy(graph))

    assert first == second
    assert first.state is C0SemanticReadbackState.PASS
    assert first.semantic_revalidation_passed is True
    assert first.expected_cell_count == first.observed_cell_count == 24
    assert first.blockers == ()
    assert first.receipt_sha256 == second.receipt_sha256
    assert all(
        first.as_dict()[key] is False
        for key in (
            "human_execution_authorized",
            "scientific_authority",
            "study_authority",
            "calibration_authority",
            "release_authority",
        )
    )


def test_nested_hash_tamper_returns_typed_hold() -> None:
    graph = _graph()
    graph["experiment_protocol"]["lexicon"]["attributes"][0][
        "display_name"
    ] = "Tampered"

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert "LEXICON_HASH_MISMATCH" in receipt.blockers


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("participant_token_sha256", "1" * 64, "OBSERVATION_QUALIFICATION_MISMATCH"),
        ("session_token_sha256", "2" * 64, "OBSERVATION_CELLS_UNEXPECTED:1"),
        ("repeat_index", 3, "OBSERVATION_REPEAT_OUTSIDE_PROTOCOL"),
        ("sniff_time_seconds", 999, "OBSERVATION_TIMEPOINT_OUTSIDE_PROTOCOL"),
    ],
)
def test_participant_session_repeat_and_timepoint_tamper_hold(
    field: str,
    value: object,
    expected: str,
) -> None:
    graph = _graph()
    record = graph["observation_records"][0]
    observation = record["observations_json"]["panel_observation"]
    observation[field] = value
    if field == "sniff_time_seconds":
        record["elapsed_seconds"] = value
    _rehash_observation(record)

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert expected in receipt.blockers


@pytest.mark.parametrize("mutation,expected", [
    ("missing", "OBSERVATION_CELLS_MISSING:1"),
    ("duplicate", "OBSERVATION_CELL_DUPLICATE"),
    ("unexpected", "OBSERVATION_CELLS_UNEXPECTED:1"),
])
def test_missing_duplicate_and_unexpected_cells_hold(
    mutation: str,
    expected: str,
) -> None:
    graph = _graph()
    if mutation == "missing":
        graph["observation_records"].pop()
    elif mutation == "duplicate":
        graph["observation_records"].append(
            copy.deepcopy(graph["observation_records"][0])
        )
    else:
        record = copy.deepcopy(graph["observation_records"][0])
        observation = record["observations_json"]["panel_observation"]
        observation["session_token_sha256"] = "3" * 64
        _rehash_observation(record)
        graph["observation_records"].append(record)

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert expected in receipt.blockers


def test_qualification_and_stale_protocol_lexicon_bindings_hold() -> None:
    graph = _graph()
    record = graph["observation_records"][0]
    observation = record["observations_json"]["panel_observation"]
    observation["qualification_receipt_sha256"] = "4" * 64
    observation["protocol_sha256"] = "5" * 64
    observation["lexicon_sha256"] = "6" * 64
    _rehash_observation(record)

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert "OBSERVATION_QUALIFICATION_MISMATCH" in receipt.blockers
    assert "OBSERVATION_PROTOCOL_MISMATCH" in receipt.blockers
    assert "OBSERVATION_LEXICON_MISMATCH" in receipt.blockers


def test_performance_and_exit_semantics_tamper_hold() -> None:
    graph = _graph()
    outcome = graph["outcome"]
    outcome["panel_performance_results"][0]["observed_value"] = "0"
    outcome["panel_performance_results_sha256"] = _stable_hash(
        outcome["panel_performance_results"]
    )
    outcome["c0_exit_report"]["decision"] = "hold"
    outcome["c0_exit_report_sha256"] = _stable_hash(outcome["c0_exit_report"])

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert "PERFORMANCE_OUTCOME_MISMATCH" in receipt.blockers
    assert "EXIT_REPORT_SEMANTICS_MISMATCH" in receipt.blockers


def test_any_authority_bit_flip_holds_and_b9_remains_unexposed() -> None:
    graph = _graph()
    graph["outcome"]["release_authority"] = True

    receipt = revalidate_c0_lab_persistence_graph(graph)

    assert receipt.state is C0SemanticReadbackState.HOLD
    assert any(item.startswith("AUTHORITY_BIT_NOT_FALSE:") for item in receipt.blockers)
    assert all("c0" not in key for key in SCIENCE_SECTION_KEYS)
