from __future__ import annotations

import pytest

from engine.research.goal_analysis import (
    GoalAnalysisRequestV1,
    GoalFormulaRowV1,
    analyze_formula_for_goal,
)
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)


def test_interpretation_preserves_material_quantity_constraints_and_modes() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "In the current bottle add 15 UL of Hedione for clearer lavender "
                "at 30 minutes; preserve dry amber and avoid added sweetness; "
                "compare with YSL Libre."
            ),
            known_materials=("Hedione", "Ambrox Super Crystals"),
            known_references=("YSL Libre",),
            appeal_mode="GLOBAL_CROWD_PLEASING",
        )
    )

    assert result["status"] == "REQUEST_INTERPRETATION_READY"
    assert result["execution_strategy"] == "EVOLVING_BOTTLE"
    assert result["appeal_mode"] == "GLOBAL_CROWD_PLEASING"
    assert result["explicit_quantities"] == [
        {
            "amount_decimal": "15",
            "unit": "uL",
            "material": "Hedione",
            "source_text": "15 UL",
            "scope": "MATERIAL_DOSE",
        }
    ]
    assert result["must_preserve"] == ["dry amber"]
    assert result["must_avoid"] == ["added sweetness"]
    assert result["reference_scope"]["named_references"] == ["YSL Libre"]
    assert result["evaluation_windows"][0]["time_seconds"] == 1800
    assert result["action_generated"] is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Do not increase Ambrox", "PRESERVE_OR_DECREASE"),
        ("Do not reduce Ambrox", "PRESERVE_OR_INCREASE"),
        ("Make the lavender less harsh", "DECREASE"),
        ("Make the lavender brighter", "INCREASE"),
    ],
)
def test_interpretation_handles_direction_and_negation(text: str, expected: str) -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=text,
            known_materials=("Ambrox", "lavender"),
        )
    )
    assert result["desired_changes"][0]["direction"] == expected


def test_interpretation_abstains_on_materialless_quantity_and_conflicting_strategy() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request="Put 12 mL in this current bottle and make a new bottle too",
            known_materials=("Hedione",),
        )
    )
    assert result["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert result["confirmation_required"] is True
    assert "QUANTITY_WITHOUT_EXACT_MATERIAL_BINDING" in result["ambiguities"]
    assert "CONTRADICTORY_EXECUTION_STRATEGY" in result["ambiguities"]


def test_interpretation_separates_exclusions_from_positive_materials() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Create dry lavender and vetiver. Do not use Hedione, Iso E Super "
                "or vanilla."
            ),
            known_materials=(
                "Lavender EO (BONTAUX SAS)",
                "Vetiver EO (Haiti)",
                "Hedione",
                "Iso E Super",
                "Vanillin",
            ),
        )
    )

    assert result["explicit_materials"] == [
        "Lavender EO (BONTAUX SAS)",
        "Vetiver EO (Haiti)",
    ]
    assert set(result["prohibited_materials"]) == {"Hedione", "Iso E Super"}
    assert result["confirmation_required"] is False


def test_interpretation_recognizes_inline_no_constraint() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request="A metallic pear and violet perfume, no vanilla.",
            known_materials=("Vanillin",),
        )
    )

    assert result["must_avoid"] == ["vanilla"]
    assert result["explicit_materials"] == []


def test_interpretation_detects_true_semantic_contradictions() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Create one uniform perfume that is intensely hot and completely cold "
                "at the same time, and must contain Ambrox Super but must contain no "
                "Ambrox material."
            ),
            known_materials=("Ambrox Super", "Ambrox Super Crystals"),
        )
    )

    assert result["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert "MUTUALLY_EXCLUSIVE_SENSORY_REQUIREMENTS" in result["ambiguities"]
    assert "REQUIRED_MATERIAL_IS_ALSO_PROHIBITED" in result["ambiguities"]


def test_interpretation_recognizes_formula_total_without_binding_it_to_a_material() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Use exactly 180 mg of crystal Ambrox and keep the liquid concentrate "
                "exactly 6000 microlitres."
            ),
            known_materials=("Ambrox Super Crystals",),
        )
    )

    assert result["status"] == "REQUEST_INTERPRETATION_READY"
    assert [row["scope"] for row in result["explicit_quantities"]] == [
        "MATERIAL_DOSE",
        "LIQUID_TOTAL",
    ]


@pytest.mark.parametrize("unit", ("uL", "µL", "μL"))
def test_interpretation_accepts_all_microlitre_spellings(unit: str) -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=f"Use exactly 15 {unit} of Hedione.",
            known_materials=("Hedione",),
        )
    )

    assert result["status"] == "REQUEST_INTERPRETATION_READY"
    assert result["explicit_quantities"] == [
        {
            "amount_decimal": "15",
            "unit": "uL",
            "material": "Hedione",
            "source_text": f"15 {unit}",
            "scope": "MATERIAL_DOSE",
        }
    ]


def test_unknown_request_modes_fail_instead_of_defaulting() -> None:
    with pytest.raises(ValueError, match="execution_strategy"):
        RequestInterpretationInputV1(
            original_request="make it brighter",
            execution_strategy="maybe-current",
        )


def test_interpretation_withholds_contradictory_material_counts() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Create exactly six materials but use at least twelve materials."
            )
        )
    )

    assert result["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert "EXACT_MATERIAL_COUNT_OUTSIDE_REQUESTED_RANGE" in result["ambiguities"]
    assert result["material_count_constraints"] == [
        {"kind": "MINIMUM", "count": 12, "source_text": "at least twelve materials"},
        {"kind": "EXACT", "count": 6, "source_text": "exactly six materials"},
    ]
    with pytest.raises(ValueError, match="intervention mode"):
        GoalAnalysisRequestV1(
            formula_id="f",
            formula_name="F",
            rows=(GoalFormulaRowV1("r", "Hedione", "10", "uL"),),
            goals=("make it brighter",),
            mode="mystery",
        )
    with pytest.raises(ValueError, match="one to three"):
        GoalAnalysisRequestV1(
            formula_id="f",
            formula_name="F",
            rows=(GoalFormulaRowV1("r", "Hedione", "10", "uL"),),
            goals=("make it brighter",),
            max_hypotheses=4,
        )


def test_interpretation_treats_material_ceiling_as_maximum() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Under a thirty-material ceiling, create an aquatic and stop "
                "when every distinct role is covered."
            ),
        )
    )

    assert result["material_count_constraints"] == [
        {
            "kind": "MAXIMUM",
            "count": 30,
            "source_text": "Under a thirty-material ceiling",
        }
    ]
    assert result["confirmation_required"] is False


def test_interpretation_treats_material_range_as_minimum_and_maximum() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request="Create a green iris perfume with 18 to 30 materials.",
        )
    )

    assert result["material_count_constraints"] == [
        {
            "kind": "MINIMUM",
            "count": 18,
            "source_text": "18 to 30 materials",
        },
        {
            "kind": "MAXIMUM",
            "count": 30,
            "source_text": "18 to 30 materials",
        },
    ]
    assert result["confirmation_required"] is False


def test_interpretation_separates_material_from_avoided_facet_phrase() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request="Use exactly 20 uL Coumarin in a dry fougere.",
            known_materials=("Coumarin",),
            must_avoid=("sweet coumarin cloud",),
        )
    )

    assert result["mandatory_materials"] == ["Coumarin"]
    assert result["prohibited_materials"] == []
    assert "REQUIRED_MATERIAL_IS_ALSO_PROHIBITED" not in result["ambiguities"]


def test_interpretation_detects_positive_and_prohibited_same_material() -> None:
    result = interpret_request(
        RequestInterpretationInputV1(
            original_request=(
                "Create a perfume that contains Ambrox Super and contains no "
                "Ambrox material; is intensely sweet and completely unsweetened."
            ),
            known_materials=("Ambrox Super",),
        )
    )

    assert "EXPLICIT_MATERIAL_IS_ALSO_PROHIBITED" in result["ambiguities"]
    assert "MUTUALLY_EXCLUSIVE_SENSORY_REQUIREMENTS" in result["ambiguities"]


def test_evolving_bottle_produces_positive_mg_delta_without_constant_total_offset() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="current-bottle",
            formula_name="Lavender Amber",
            rows=(
                GoalFormulaRowV1("lav", "Lavender EO", "700", "uL"),
                GoalFormulaRowV1("ambrox", "Ambrox Super Crystals", "300", "mg"),
            ),
            goals=("Use more Ambrox",),
            original_request="Add more Ambrox to this current bottle",
            active_bottle_id="bottle-1",
        )
    )

    hypothesis = result["modification_hypotheses"][0]
    assert result["request_interpretation"]["execution_strategy"] == "EVOLVING_BOTTLE"
    assert hypothesis["action"] == "INCREASE_EXISTING_BLOCK"
    assert hypothesis["trial"]["negative_delta_allowed"] is False
    assert hypothesis["trial"]["constant_total_policy"] == (
        "NOT_APPLICABLE_EVOLVING_BOTTLE_TOTAL_INCREASES"
    )
    low = hypothesis["trial"]["low_variant"]["row_targets"][0]
    assert low["unit"] == "mg"
    assert float(low["delta_amount_decimal"]) > 0
    assert result["selection"]["status"] == "UNORDERED_HYPOTHESES"


def test_evolving_bottle_refuses_subtraction_dependent_repair() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="current-bottle",
            formula_name="Lavender Amber",
            rows=(GoalFormulaRowV1("ambrox", "Ambrox Super Crystals", "300", "mg"),),
            goals=("Use less Ambrox",),
            original_request="Use less Ambrox in this current bottle",
            active_bottle_id="bottle-1",
        )
    )
    assert result["status"] == "ADDITIVE_REPAIR_NOT_FEASIBLE"
    assert result["modification_hypotheses"] == []
    assert result["selection"]["formula_action"] == "NO_CHANGE"
    assert [row["kind"] for row in result["additive_repair_alternatives"]] == [
        "COUNTERBALANCING_ADDITIVE_HYPOTHESIS",
        "DILUTION",
        "NEW_FORMULA",
    ]


def test_crowd_mode_never_silently_uses_an_unrelated_commercial_panel() -> None:
    result = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="rose-study",
            formula_name="Transparent Rose Study",
            rows=(GoalFormulaRowV1("rose", "Rose Absolute", "20", "uL"),),
            goals=("Make the rose clearer",),
            appeal_mode="GLOBAL_CROWD_PLEASING",
        )
    )
    assert result["commercial_reference_panel"] is None
    assert result["commercial_reference_panel_state"] == (
        "WITHHELD_NO_APPLICABLE_CURRENT_PANEL"
    )
    assert "NO_APPLICABLE_CURRENT_COMMERCIAL_REFERENCE_PANEL" in (
        result["selection"]["reason_codes"]
    )
