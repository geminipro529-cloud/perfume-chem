"""Tests for the interaction graph query API (:mod:`engine.interaction_graph`).

Verifies query, insert, analysis, and F11 chemical-incompatibility
functions against an isolated copy of ``data/perfumery_kb.db``.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from shutil import copy2

import pytest

import engine.interaction_graph as interaction_graph
from engine.interaction_graph import (
    F11_INCOMPATIBILITIES,
    _ensure_f11_seeded,
    add_interaction,
    check_chemical_compatibility,
    get_all_interactions,
    get_clashes,
    get_coverage_stats,
    get_incompatible_naturals,
    get_interaction,
    get_replacements,
    get_synergies,
)

_REPOSITORY_DATABASE = (
    Path(__file__).resolve().parents[1] / "data" / "perfumery_kb.db"
)


@pytest.fixture(autouse=True)
def _isolated_interaction_database(tmp_path, monkeypatch):
    baseline_sha256 = sha256(_REPOSITORY_DATABASE.read_bytes()).hexdigest()
    isolated_database = tmp_path / "perfumery_kb.db"
    copy2(_REPOSITORY_DATABASE, isolated_database)
    monkeypatch.setattr(interaction_graph, "_DB_PATH", isolated_database)
    yield
    assert sha256(_REPOSITORY_DATABASE.read_bytes()).hexdigest() == baseline_sha256


def test_mutation_tests_do_not_target_repository_database() -> None:
    assert interaction_graph._DB_PATH.resolve() != _REPOSITORY_DATABASE.resolve()


# ── Query tests ────────────────────────────────────────────────────────


class TestGetInteraction:
    """Tests for ``interaction_graph.get_interaction``."""

    def test_known_pair(self) -> None:
        """Hedione and BERGAMOT FCF have a known pairing entry."""
        results = get_interaction("Hedione", "BERGAMOT FCF")
        assert len(results) >= 1
        expected_lower = {"hedione", "bergamot fcf"}
        for r in results:
            assert r["material_a"].lower() in expected_lower
            assert r["material_b"].lower() in expected_lower

    def test_reverse_direction_returns_same(self) -> None:
        """Swapping A/B must return the same rows (bidirectional query)."""
        forward = get_interaction("Hedione", "BERGAMOT FCF")
        reverse = get_interaction("BERGAMOT FCF", "Hedione")
        assert len(forward) == len(reverse)
        # IDs should match (same rows)
        fwd_ids = {r["id"] for r in forward}
        rev_ids = {r["id"] for r in reverse}
        assert fwd_ids == rev_ids

    def test_unknown_pair_returns_empty(self) -> None:
        """A pair that does not exist returns an empty list."""
        results = get_interaction("__nonexistent_a__", "__nonexistent_b__")
        assert results == []


class TestGetAllInteractions:
    """Tests for ``interaction_graph.get_all_interactions``."""

    def test_known_material_returns_results(self) -> None:
        """Hedione must have at least some interactions."""
        results = get_all_interactions("Hedione")
        assert len(results) >= 3

    def test_unknown_material_returns_empty(self) -> None:
        """Unknown material returns empty list."""
        results = get_all_interactions("__nonexistent__")
        assert results == []


class TestGetSynergies:
    """Tests for ``interaction_graph.get_synergies``."""

    def test_hedione_synergies(self) -> None:
        """Hedione must have multiple synergy entries."""
        results = get_synergies("Hedione")
        assert len(results) >= 1
        for r in results:
            assert r["type"] == "synergy"

    def test_unknown_returns_empty(self) -> None:
        """Unknown material returns empty list."""
        results = get_synergies("__nonexistent__")
        assert results == []


class TestGetClashes:
    """Tests for ``interaction_graph.get_clashes``."""

    def test_aldehyde_c10_has_conflicts(self) -> None:
        """ALDEHYDE C10 must have at least one conflict entry."""
        results = get_clashes("ALDEHYDE C10")
        assert len(results) >= 1
        for r in results:
            assert r["type"] in ("conflict", "clash")

    def test_unknown_returns_empty(self) -> None:
        """Unknown material returns empty list."""
        results = get_clashes("__nonexistent__")
        assert results == []


class TestGetReplacements:
    """Tests for ``interaction_graph.get_replacements``."""

    def test_dynascone_has_rejections(self) -> None:
        """Dynascone (10%) must have replacement/rejection entries."""
        results = get_replacements("Dynascone (10%)")
        assert len(results) >= 1
        for r in results:
            assert r["type"] == "rejection"

    def test_unknown_returns_empty(self) -> None:
        """Unknown material returns empty list."""
        results = get_replacements("__nonexistent__")
        assert results == []


# ── Mutation tests ─────────────────────────────────────────────────────


class TestAddInteraction:
    """Tests for ``interaction_graph.add_interaction``."""

    def test_add_and_retrieve(self) -> None:
        """Adding a new interaction must persist it and return a valid id."""
        row_id = add_interaction(
            material_a="TestMaterialA",
            material_b="TestMaterialB",
            type_="synergy",
            effect="Test synergy for testing",
            magnitude=5.0,
            source="test",
            context="test_context",
        )
        assert row_id > 0, "add_interaction must return a positive id"

        # Verify it's retrievable
        results = get_interaction("TestMaterialA", "TestMaterialB")
        assert len(results) >= 1
        assert any(r["id"] == row_id for r in results)

    def test_add_duplicate_allowed(self) -> None:
        """Adding the same interaction twice must produce two rows (no UNIQUE constraint on pair)."""
        row_id_1 = add_interaction(
            material_a="TestDupA",
            material_b="TestDupB",
            type_="pairing",
            effect="Duplicate test",
            magnitude=1.0,
            source="test_dup",
            context="",
        )
        row_id_2 = add_interaction(
            material_a="TestDupA",
            material_b="TestDupB",
            type_="pairing",
            effect="Duplicate test",
            magnitude=1.0,
            source="test_dup",
            context="",
        )
        assert row_id_2 > row_id_1
        results = get_interaction("TestDupA", "TestDupB")
        assert len(results) >= 2


# ── Coverage statistics tests ──────────────────────────────────────────


class TestCoverageStats:
    """Tests for ``interaction_graph.get_coverage_stats``."""

    def test_stats_have_expected_keys(self) -> None:
        """Coverage stats must contain all required keys."""
        stats = get_coverage_stats()
        expected_keys = {
            "total_possible_pairs",
            "covered_pairs",
            "coverage_pct",
            "distinct_materials",
            "total_interactions",
            "by_type",
        }
        assert expected_keys.issubset(stats.keys())

    def test_stats_plausible_values(self) -> None:
        """Coverage values must be internally consistent."""
        stats = get_coverage_stats()
        assert stats["distinct_materials"] >= 100
        assert stats["covered_pairs"] >= 1000
        assert stats["total_interactions"] >= 3350
        assert 0.0 <= stats["coverage_pct"] <= 100.0

    def test_by_type_has_expected_types(self) -> None:
        """by_type must contain synergy, conflict, pairing, etc."""
        stats = get_coverage_stats()
        by_type = stats["by_type"]
        assert "synergy" in by_type
        assert by_type["synergy"] >= 500
        assert "pairing" in by_type
        assert by_type["pairing"] >= 2000


# ── F11 Incompatibility tests ──────────────────────────────────────────


class TestF11Incompatibilities:
    """Tests for the AGENTS.md F11 chemical incompatibility rules."""

    def test_f11_rules_in_db(self) -> None:
        """F11 rules must have been seeded into the database."""
        # Ensure seeded (idempotent)
        _ensure_f11_seeded()
        results = get_incompatible_naturals()
        assert len(results) >= 3
        sources = {r["source"] for r in results}
        assert "AGENTS.md F11" in sources

    def test_blue_chamomile_rose_clash(self) -> None:
        """Blue Chamomile EO and Rose EO must be marked as clash."""
        results = get_incompatible_naturals()
        clash_pairs = {
            (r["material_a"].lower(), r["material_b"].lower())
            for r in results
            if r["type"] == "clash"
        }
        assert (
            "blue chamomile eo",
            "rose eo",
        ) in clash_pairs or (
            "rose eo",
            "blue chamomile eo",
        ) in clash_pairs

    def test_osmanthus_clove_clash(self) -> None:
        """Osmanthus Absolute and Clove EO must be marked as clash."""
        results = get_incompatible_naturals()
        clash_pairs = {
            (r["material_a"].lower(), r["material_b"].lower())
            for r in results
            if r["type"] == "clash"
        }
        assert (
            "osmanthus absolute",
            "clove eo",
        ) in clash_pairs or (
            "clove eo",
            "osmanthus absolute",
        ) in clash_pairs

    def test_geranium_violet_leaf_clash(self) -> None:
        """Geranium EO and Violet Leaf must be marked as clash."""
        results = get_incompatible_naturals()
        clash_pairs = {
            (r["material_a"].lower(), r["material_b"].lower())
            for r in results
            if r["type"] == "clash"
        }
        assert (
            "geranium eo",
            "violet leaf",
        ) in clash_pairs or (
            "violet leaf",
            "geranium eo",
        ) in clash_pairs


# ── Chemical compatibility tests ───────────────────────────────────────


class TestCheckChemicalCompatibility:
    """Tests for ``interaction_graph.check_chemical_compatibility``."""

    def test_incompatible_naturals(self) -> None:
        """Blue Chamomile EO and Rose EO must be detected as incompatible."""
        result = check_chemical_compatibility("Blue Chamomile EO", "Rose EO")
        assert result["compatible"] is False
        assert result["reason"] is not None
        assert result["source"] == "AGENTS.md F11"

    def test_incompatible_reverse_order(self) -> None:
        """Reversed order must still detect incompatibility."""
        result = check_chemical_compatibility("Rose EO", "Blue Chamomile EO")
        assert result["compatible"] is False

    def test_compatible_pair(self) -> None:
        """Hedione and Iso E Super should have no known clash."""
        result = check_chemical_compatibility("Hedione", "Iso E Super")
        assert result["compatible"] is True
        assert result["reason"] is None

    def test_compatible_unknown_materials(self) -> None:
        """Unknown materials should be treated as compatible (no clash data)."""
        result = check_chemical_compatibility("__nonexistent_x__", "__nonexistent_y__")
        assert result["compatible"] is True
        assert result["reason"] is None

    def test_hardcoded_rules_match_f11_constant(self) -> None:
        """Every rule in F11_INCOMPATIBILITIES must be detected."""
        for rule in F11_INCOMPATIBILITIES:
            result = check_chemical_compatibility(
                str(rule["material_a"]), str(rule["material_b"])
            )
            assert result["compatible"] is False, (
                f"{rule['material_a']} \u00d7 {rule['material_b']} "
                f"should be incompatible"
            )
            assert result["source"] == "AGENTS.md F11"
