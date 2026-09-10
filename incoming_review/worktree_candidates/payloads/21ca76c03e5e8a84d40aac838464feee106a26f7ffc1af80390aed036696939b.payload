from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    BenchmarkCaseV1,
    BenchmarkPhase,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "solforge"
SCREEN = FIXTURES / "benchmark_screen_v1.json"
CONFIRMATION = FIXTURES / "benchmark_confirmation_v1.json"

SCREEN_CATEGORIES = {
    "citrus-free target/no-change",
    "primary bergamot with Neroli support",
    "orange-blossom target with central Neroli",
    "ingredient-count complexity trap",
    "Ambrettolide design/procurement mismatch",
    "Ethylene Brassylate inventory mismatch",
    "one precise Habanolide design",
    "Habanolide x Romandolide complete factorial",
    "unjustified restricted-musk exception",
    "missing evidence requiring hold",
    "order-confounded preference evidence",
    "amber-resin architecture without liking evidence",
}

CONFIRMATION_CATEGORIES = {
    "lemon-lime heart-echo alternative",
    "bitter-orange target with floral bridge",
    "zero-musk target",
    "single Romandolide target",
    "unavailable musk-layering proposal",
    "sweet orris versus generic floral powder",
    "two-flower identity relation",
    "selected three-flower interaction",
    "selected four-flower count trap",
    "wood depth separated from darkness",
    "incomplete temporal cells with disagreement",
    "non-liking criteria offered as liking",
}


def _load(path: Path) -> tuple[dict[str, object], tuple[BenchmarkCaseV1, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(BenchmarkCaseV1.from_dict(item) for item in payload["cases"])
    return payload, cases


def test_corpora_have_exact_balanced_categories_and_closed_authority() -> None:
    screen_payload, screen = _load(SCREEN)
    confirmation_payload, confirmation = _load(CONFIRMATION)
    assert len(screen) == len(confirmation) == 12
    assert {case.category for case in screen} == SCREEN_CATEGORIES
    assert {case.category for case in confirmation} == CONFIRMATION_CATEGORIES
    assert {case.phase for case in screen} == {BenchmarkPhase.SCREEN}
    assert {case.phase for case in confirmation} == {BenchmarkPhase.CONFIRMATION}
    assert screen_payload["authority_flags"] == BENCHMARK_AUTHORITY_FLAGS
    assert confirmation_payload["authority_flags"] == BENCHMARK_AUTHORITY_FLAGS
    assert all(
        case.as_public_dict()["authority_flags"] == BENCHMARK_AUTHORITY_FLAGS
        for case in (*screen, *confirmation)
    )


def test_screen_and_confirmation_are_hash_disjoint() -> None:
    _, screen = _load(SCREEN)
    _, confirmation = _load(CONFIRMATION)
    all_cases = (*screen, *confirmation)
    assert len({case.case_id for case in all_cases}) == 24
    assert len({case.input_sha256 for case in all_cases}) == 24
    assert len({case.prompt_sha256 for case in all_cases}) == 24
    assert not {case.input_sha256 for case in screen}.intersection(
        case.input_sha256 for case in confirmation
    )


def test_answer_keys_are_machine_readable_and_absent_from_public_packets() -> None:
    for path in (SCREEN, CONFIRMATION):
        _, cases = _load(path)
        for case in cases:
            answer = case.sealed_answer_key
            assert answer["allowed_decisions"]
            assert isinstance(answer["max_interventions"], int)
            assert answer["require_authority_false"] is True
            public = json.dumps(case.as_public_dict(), sort_keys=True)
            assert "sealed_answer_key" not in public
            assert "human_rationale" not in public


def test_every_case_covers_core_governance_invariants() -> None:
    for path in (SCREEN, CONFIRMATION):
        _, cases = _load(path)
        for case in cases:
            invariants = set(case.public_invariants)
            assert "authority_false" in invariants
            assert "target_inventory_separation" in invariants
            assert "next_comparison" in invariants
            assert invariants.intersection(
                {"correct_no_change", "zero_one_intervention", "required_hold"}
            )


def test_fixture_hash_sidecars_match_exact_bytes() -> None:
    for path in (SCREEN, CONFIRMATION):
        expected = path.with_suffix(".sha256").read_text(encoding="ascii").strip()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
