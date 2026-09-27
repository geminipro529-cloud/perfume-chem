from __future__ import annotations

import pytest

from engine.research.goal_analysis import (
    GoalAnalysisRequestV1,
    GoalFormulaRowV1,
    analyze_formula_for_goal,
)
from scripts.intervention_recommend import _parse_formula_markdown, build_report


def _r6_rows() -> tuple[GoalFormulaRowV1, ...]:
    return (
        GoalFormulaRowV1("lav-1", "Lavender EO Bontoux", "700", "uL"),
        GoalFormulaRowV1("lav-2", "Lavender EO Aroma More", "300", "uL"),
        GoalFormulaRowV1("ambrox", "Ambrox Super Crystals", "300", "mg"),
        GoalFormulaRowV1("hedione", "Hedione", "500", "uL"),
    )


def test_named_formula_block_becomes_small_ratio_preserving_trial() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="r6",
            formula_name="Lavande Ambre Profond R6",
            rows=_r6_rows(),
            goals=("Make the lavender clearer at two hours while preserving the dry amber",),
            must_preserve=("dry amber",),
            available_materials=(
                "Lavender EO Bontoux",
                "Lavender EO Aroma More",
                "Ambrox Super Crystals",
                "Hedione",
            ),
        )
    )

    direct = next(
        row
        for row in result["modification_hypotheses"]
        if row["evidence_class"] == "EXPLICIT_GOAL_PLUS_FORMULA_FACT"
    )
    assert direct["action"] == "TEST_EXISTING_BLOCK_LEVEL"
    assert direct["target_row_ids"] == ["lav-1", "lav-2"]
    assert direct["trial"]["low_variant"]["current_block_total_decimal"] == "1000"
    assert direct["trial"]["low_variant"]["target_block_total_decimal"] == "925"
    assert direct["trial"]["low_variant"]["unit"] == "uL"
    assert [
        row["target_amount_decimal"]
        for row in direct["trial"]["low_variant"]["row_targets"]
    ] == ["647.5", "277.5"]
    assert direct["trial"]["high_variant"]["target_block_total_decimal"] == "1075"
    assert direct["trial"]["internal_ratio_policy"] == "PRESERVE_CURRENT_BLOCK_RATIO"
    assert direct["success_criteria"]["must_preserve"] == ["dry amber"]
    assert result["evaluation_windows"] == [
        {
            "label": "TWO_HOURS",
            "time_seconds": 7200,
            "source": "USER_STATED_GOAL",
        }
    ]
    assert result["selection"]["ranked_candidates"] == []
    assert result["selection"]["status"] == "UNORDERED_CONTROLLED_HYPOTHESES"
    assert result["formula_modified"] is False
    assert result["compounding_authority"] is False


def test_generic_goal_uses_current_inventory_but_remains_a_hypothesis() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="white-floral",
            formula_name="White Floral Study",
            rows=(GoalFormulaRowV1("jasmine", "Jasmine Absolute", "12", "percent_concentrate"),),
            goals=("Give it more diffusion without making it indolic",),
            must_avoid=("indolic",),
            family="white_floral",
            available_materials=("Hedione", "Benzyl Salicylate", "Romandolide"),
            max_hypotheses=3,
        )
    )

    assert result["status"] == "GOAL_DIRECTED_HYPOTHESES_READY"
    assert result["modification_hypotheses"]
    assert all(
        row["material_or_block"] in {"Hedione", "Benzyl Salicylate", "Romandolide"}
        for row in result["modification_hypotheses"]
    )
    assert all(
        row["evidence_class"] == "RULE_BASED_PERFUMERY_HYPOTHESIS"
        for row in result["modification_hypotheses"]
    )
    assert all(row["compounding_action_authority"] is False for row in result["modification_hypotheses"])
    assert result["beauty_score"] is None


def test_role_labeled_lavender_modifier_is_held_out_of_core_block_trial() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="parallel-a",
            formula_name="Lavande Ambre Profond Parallel A",
            rows=(
                GoalFormulaRowV1(
                    "bontoux",
                    "Lavender EO Bontoux",
                    "1150",
                    "uL",
                    role="Fine natural lavender lead",
                ),
                GoalFormulaRowV1(
                    "aroma-more",
                    "Lavender 40/42 Aroma More",
                    "450",
                    "uL",
                    role="Classical lavender profile and recognizable identity",
                ),
                GoalFormulaRowV1(
                    "spike",
                    "Spike Lavender EO",
                    "30",
                    "uL",
                    role="Camphoraceous edge that keeps the lavender legible",
                ),
                GoalFormulaRowV1("hedione", "Hedione", "500", "uL"),
            ),
            goals=("Make the lavender clearer at two hours",),
        )
    )

    direct = result["modification_hypotheses"][0]
    assert direct["target_row_ids"] == ["bontoux", "aroma-more"]
    assert direct["held_constant_row_ids"] == ["spike"]
    assert direct["trial"]["low_variant"]["current_block_total_decimal"] == "1600"
    formula_clue = next(
        clue
        for clue in result["clues"]
        if clue["evidence_class"] == "FORMULA_COMPOSITION_FACT"
    )
    assert formula_clue["held_constant_row_ids"] == ["spike"]
    assert "remain fixed" in formula_clue["statement"]


def test_photos_lots_and_density_are_not_prerequisites_for_hypothesis_generation() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="r6",
            formula_name="Lavande Ambre Profond R6",
            rows=_r6_rows(),
            goals=("Use less Ambrox",),
        )
    )

    hypothesis = result["modification_hypotheses"][0]
    assert hypothesis["action"] == "DECREASE_EXISTING_BLOCK"
    assert hypothesis["trial"]["low_variant"]["relative_block_change_percent"] == "-7.5"
    optional = " ".join(result["not_required_for_hypothesis_generation"]).casefold()
    assert "photograph" in optional
    assert "lot" in optional
    assert "density" in optional
    assert result["validation_state"] == "ADVISORY_FINDINGS"


def test_applicable_endpoint_is_kept_separate_from_pleasantness_and_beauty() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="r6",
            formula_name="Lavande Ambre Profond R6",
            rows=_r6_rows(),
            goals=("Make lavender clearer",),
            endpoint_results=(
                {
                    "endpoint": "CHARACTER",
                    "value": {"lavender": 0.7, "amber": 0.4},
                    "unit": "descriptor-profile",
                    "coverage": "0.75",
                    "applicability_state": "PARTIAL",
                    "provenance": ["character-capability-v1"],
                },
                {
                    "endpoint": "PLEASANTNESS",
                    "value": None,
                    "applicability_state": "UNAVAILABLE",
                },
            ),
        )
    )

    assert result["evidence_summary"]["applicable_endpoint_count"] == 1
    endpoint_clues = [
        clue for clue in result["clues"] if clue["evidence_class"] == "APPLICABLE_ENDPOINT_ESTIMATE"
    ]
    assert [clue["endpoint"] for clue in endpoint_clues] == ["CHARACTER"]
    assert result["pleasantness"] is None
    assert result["personal_liking"] is None
    assert result["beauty_score"] is None


def test_invalid_formula_quantities_and_empty_goals_fail_early() -> None:
    with pytest.raises(ValueError):
        GoalFormulaRowV1("bad", "Material", "nan", "uL")
    with pytest.raises(TypeError):
        GoalFormulaRowV1("bad", "Material", True, "uL")
    with pytest.raises(ValueError, match="analysis goal"):
        GoalAnalysisRequestV1(
            formula_id="f",
            formula_name="F",
            rows=(GoalFormulaRowV1("r", "Material", "1", "uL"),),
            goals=(),
        )


def test_modern_markdown_parser_preserves_liquid_and_crystal_rows(tmp_path) -> None:
    formula = tmp_path / "Lavender_Amber_Test.md"
    formula.write_text(
        """# Lavender Amber Test

| # | Basket | Ingredient | Form | Amount (uL) | Role |
|---:|:---:|---|---|---:|---|
| 1 | B4 | Lavender EO Bontoux | neat | 700 | lavender |
| 2 | B4 | Lavender EO Aroma More | neat | 300 | lavender |
| 3 | B3 | Hedione | neat | 500 | diffusion |

| # | Basket | Ingredient | Form | Amount (mg) | Role |
|---:|:---:|---|---|---:|---|
| 4 | B5 | Ambrox Super Crystals | neat solid | 300 | dry amber |
""",
        encoding="utf-8",
    )

    parsed = _parse_formula_markdown(formula)

    assert len(parsed) == 1
    assert parsed[0].ingredients_pct == {
        "Lavender EO Bontoux": pytest.approx(46.6667),
        "Lavender EO Aroma More": pytest.approx(20.0),
        "Hedione": pytest.approx(33.3333),
    }
    assert [(row["material"], row["amount_decimal"], row["unit"]) for row in parsed[0].raw_rows] == [
        ("Lavender EO Bontoux", "700.0", "uL"),
        ("Lavender EO Aroma More", "300.0", "uL"),
        ("Hedione", "500.0", "uL"),
        ("Ambrox Super Crystals", "300.0", "mg"),
    ]
    assert parsed[0].raw_rows[0]["role"] == "lavender"
    assert parsed[0].raw_rows[-1]["role"] == "dry amber"


def test_goal_first_markdown_is_concise_and_does_not_emit_legacy_score_dump(tmp_path) -> None:
    formula = tmp_path / "Lavender_Amber_Test.md"
    formula.write_text(
        """# Lavender Amber Test

| # | Ingredient | Form | Amount (uL) |
|---:|---|---|---:|
| 1 | Lavender EO Bontoux | neat | 700 |
| 2 | Lavender EO Aroma More | neat | 300 |
| 3 | Hedione | neat | 500 |
""",
        encoding="utf-8",
    )
    source = _parse_formula_markdown(formula)[0]

    report = build_report(
        source,
        goals=["Make the lavender clearer while preserving the dry amber"],
        must_preserve=["dry amber"],
        output_format="markdown",
        top_n=3,
    )

    assert "# Goal-Directed Perfume Analysis" in report
    assert "Lavender EO Bontoux + Lavender EO Aroma More" in report
    assert "unchanged control" in report.casefold()
    assert "# Detailed Legacy Diagnostics" not in report
    assert "## Scores" not in report
    assert "photos, purchase receipts, exact lots" in report.casefold()
