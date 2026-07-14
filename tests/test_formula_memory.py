# allow: SIZE_OK — integration test suite

"""Tests for :mod:`engine.formula_memory`."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from engine.kb_schema import create_database
from engine import formula_memory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = str(PROJECT_ROOT / "formulas" / "L_Homme_Luxe_30mL_EdP.md")


@pytest.fixture(autouse=True)
def _temp_db() -> None:
    """Replace the module-level DB path with a temporary DB before each test.

    The temp DB is created with the full schema so all tables exist.
    The file is cleaned up after the test.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        create_database(tmp.name)
        # Point the module at our temp database
        formula_memory._DB_PATH = tmp.name  # noqa: SLF001
        yield
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFormulaCRUD:
    """Formula save / get / list / search."""

    def test_save_and_get_formula(self) -> None:
        """Save L_Homme_Luxe and verify retrieval returns 22 materials."""
        fid = formula_memory.save_formula(FORMULA_PATH)
        assert isinstance(fid, int) and fid > 0

        formula = formula_memory.get_formula(fid)
        assert formula is not None
        assert formula["name"] == "L'Homme Luxe - 30mL EdP 20%"
        assert formula["date"] == "2026-07-09"
        assert formula["family_archetype"] == "ysl_lhomme"
        assert formula["batch_size_ml"] == 30.0
        assert formula["concentrate_ul"] == 6000
        assert formula["file_path"] == FORMULA_PATH
        assert (
            "Super-luxury" in formula["rationale"]
            or "super-luxury" in formula["rationale"].lower()
        )

        materials = formula["materials"]
        assert len(materials) == 22, f"Expected 22 materials, got {len(materials)}"

        # Spot-check a couple of materials
        iso_e = [m for m in materials if "Iso E Super" in m["material_name"]]
        assert len(iso_e) == 1
        assert iso_e[0]["amount_ul"] == 900.0
        assert iso_e[0]["dilution"] == "1.0"

        basil = [m for m in materials if "Basil EO" in m["material_name"]]
        assert len(basil) == 1
        assert basil[0]["amount_ul"] == 8.0

    def test_get_formula_not_found(self) -> None:
        """get_formula returns None for a non-existent ID."""
        assert formula_memory.get_formula(99999) is None

    def test_list_formulas(self) -> None:
        """After saving a formula, list returns at least one."""
        formula_memory.save_formula(FORMULA_PATH)
        all_f = formula_memory.list_formulas()
        assert len(all_f) >= 1

    def test_list_formulas_filtered(self) -> None:
        """list_formulas with a family filter returns only matches."""
        formula_memory.save_formula(FORMULA_PATH)
        # No other formula with this family
        matches = formula_memory.list_formulas(family="nonexistent")
        assert len(matches) == 0

        matches = formula_memory.list_formulas(family="ysl_lhomme")
        assert len(matches) >= 1

    def test_search_by_material(self) -> None:
        """Searching for 'Hedione' returns the formula."""
        formula_memory.save_formula(FORMULA_PATH)
        results = formula_memory.search_formulas(material="Hedione")
        assert len(results) >= 1
        # Hedione HC should also match
        any("Hedione HC" in str(r) for r in results) or any(
            "Hedione" in m.get("material_name", "")
            for r in results
            for m in formula_memory.get_formula(r["id"]).get("materials", [])
        )

    def test_search_by_family(self) -> None:
        """Search by family archetype."""
        formula_memory.save_formula(FORMULA_PATH)
        results = formula_memory.search_formulas(family="ysl_lhomme")
        assert len(results) >= 1

    def test_search_by_material_and_family(self) -> None:
        """Combined material + family search."""
        formula_memory.save_formula(FORMULA_PATH)
        results = formula_memory.search_formulas(
            material="Iso E Super", family="ysl_lhomme"
        )
        assert len(results) >= 1

    def test_search_by_rating(self) -> None:
        """Search with rating_min filters correctly."""
        fid = formula_memory.save_formula(FORMULA_PATH)
        formula_memory.save_evaluation(fid, 8, "Great!", ["floral", "woody"])
        formula_memory.save_evaluation(fid, 3, "Meh", ["weak"])

        results_ge5 = formula_memory.search_formulas(rating_min=5)
        assert len(results_ge5) >= 1

        results_ge9 = formula_memory.search_formulas(rating_min=9)
        assert len(results_ge9) == 0


class TestPipelineResults:
    """Pipeline result save / get."""

    def test_save_pipeline_result(self) -> None:
        """Save minimal pipeline JSON and verify retrieval."""
        fid = formula_memory.save_formula(FORMULA_PATH)

        # Write a minimal pipeline JSON file
        pipeline = {
            "formulas": [
                {
                    "gates": [
                        {
                            "gate": "preflight",
                            "status": "PASS",
                            "detail": "All checks passed",
                        },
                        {"gate": "ifra", "status": "WARN", "detail": {"violations": 1}},
                        {
                            "gate": "pyramid",
                            "status": "FAIL",
                            "detail": "T/H/B ratio off",
                        },
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(pipeline, fh)
            json_path = fh.name

        try:
            count = formula_memory.save_pipeline_result(fid, json_path)
            assert count == 3

            results = formula_memory.get_pipeline_result(fid)
            assert len(results) == 3

            gate_names = {r["gate_name"] for r in results}
            assert "preflight" in gate_names
            assert "ifra" in gate_names
            assert "pyramid" in gate_names

            # Detail is stored as string (JSON-serialised if needed)
            ifra_result = [r for r in results if r["gate_name"] == "ifra"][0]
            assert '"violations": 1' in ifra_result["detail"]
        finally:
            os.unlink(json_path)

    def test_get_pipeline_result_empty(self) -> None:
        """get_pipeline_result returns empty list when nothing saved."""
        assert formula_memory.get_pipeline_result(1) == []


class TestEvaluations:
    """Evaluation save / get."""

    def test_save_evaluation(self) -> None:
        """Save an evaluation and verify retrieval."""
        fid = formula_memory.save_formula(FORMULA_PATH)
        eid = formula_memory.save_evaluation(
            fid, 9, "Beautiful composition", ["iris", "powdery", "long-lasting"]
        )
        assert isinstance(eid, int) and eid > 0

        evals = formula_memory.get_evaluations(fid)
        assert len(evals) == 1
        assert evals[0]["rating"] == 9
        assert "Beautiful" in evals[0]["feedback_text"]
        assert evals[0]["feedback_tags"] == ["iris", "powdery", "long-lasting"]

    def test_get_evaluations_empty(self) -> None:
        """get_evaluations returns empty list when nothing saved."""
        assert formula_memory.get_evaluations(1) == []

    def test_multiple_evaluations(self) -> None:
        """Multiple evaluations for the same formula are all returned."""
        fid = formula_memory.save_formula(FORMULA_PATH)
        formula_memory.save_evaluation(fid, 7, "Good", ["woody"])
        formula_memory.save_evaluation(fid, 8, "Better", ["floral"])
        formula_memory.save_evaluation(fid, 9, "Best", ["balanced"])

        evals = formula_memory.get_evaluations(fid)
        assert len(evals) == 3
        assert [e["rating"] for e in evals] == [7, 8, 9]


class TestFailures:
    """Failure add / get / filter."""

    def test_add_failure(self) -> None:
        """Add a failure and verify retrieval."""
        fid = formula_memory.save_formula(FORMULA_PATH)
        f_id = formula_memory.add_failure(
            fid,
            symptom="Oakmoss OAV too low",
            root_cause="Missing degradation pathway in composite model",
            fix="Expand to 10 constituents",
            learning="Natural OAV models are perceptual floors",
            applicable_materials=["Oakmoss Absolute", "Labdanum"],
        )
        assert isinstance(f_id, int) and f_id > 0

        failures = formula_memory.get_failures(fid)
        assert len(failures) == 1
        assert "Oakmoss" in failures[0]["symptom"]
        assert failures[0]["applicable_materials"] == ["Oakmoss Absolute", "Labdanum"]

    def test_get_all_failures(self) -> None:
        """get_failures() without filter returns all."""
        fid_a = formula_memory.save_formula(FORMULA_PATH)
        formula_memory.save_formula(FORMULA_PATH)  # fid_b = fid_a + 1

        formula_memory.add_failure(
            fid_a, "Symptom A", "Cause A", "Fix A", "Learn A", ["Mat A"]
        )
        # We need a second formula
        # Since the first fixture creates a fresh DB, let's just add a second
        # formula and second failure
        all_f = formula_memory.get_failures()
        assert len(all_f) >= 1

    def test_get_failures_filtered(self) -> None:
        """Add 2 failures to different formulas, filter by formula_id."""
        fid_a = formula_memory.save_formula(FORMULA_PATH)
        fid_b = formula_memory.save_formula(FORMULA_PATH)

        formula_memory.add_failure(
            fid_a, "Symptom A", "Cause A", "Fix A", "Learn A", ["Mat A"]
        )
        formula_memory.add_failure(
            fid_b, "Symptom B", "Cause B", "Fix B", "Learn B", ["Mat B"]
        )

        # Filter by formula A
        failures_a = formula_memory.get_failures(formula_id=fid_a)
        assert len(failures_a) == 1
        assert failures_a[0]["symptom"] == "Symptom A"

        # Filter by formula B
        failures_b = formula_memory.get_failures(formula_id=fid_b)
        assert len(failures_b) == 1
        assert failures_b[0]["symptom"] == "Symptom B"

        # All failures
        all_f = formula_memory.get_failures()
        assert len(all_f) == 2
