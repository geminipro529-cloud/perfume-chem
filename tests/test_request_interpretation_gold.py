from __future__ import annotations

import json
from pathlib import Path

from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "governance" / "request_interpretation_gold_v1.json"


def test_reviewed_request_interpretation_gold_corpus() -> None:
    payload = json.loads(GOLD.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "request-interpretation-gold-v1"
    cases = payload["cases"]
    assert len(cases) >= 12
    explicit_fact_checks = 0
    explicit_fact_passes = 0
    semantic_checks = 0
    semantic_passes = 0
    ambiguous_cases = 0
    ambiguous_passes = 0

    for case in cases:
        inputs = case["input"]
        expected = case["expected"]
        result = interpret_request(
            RequestInterpretationInputV1(
                original_request=inputs["original_request"],
                known_materials=tuple(inputs["known_materials"]),
                known_references=tuple(inputs["known_references"]),
            )
        )
        actual_quantities = [
            {
                "amount_decimal": row["amount_decimal"],
                "unit": row["unit"],
                "material": row["material"],
            }
            for row in result["explicit_quantities"]
        ]
        for actual, wanted in (
            (result["explicit_materials"], expected["materials"]),
            (actual_quantities, expected["quantities"]),
            (result["must_preserve"], expected["must_preserve"]),
            (result["must_avoid"], expected["must_avoid"]),
            (result["execution_strategy"], expected["execution_strategy"]),
        ):
            explicit_fact_checks += 1
            explicit_fact_passes += actual == wanted
        for actual, wanted in (
            (result["desired_changes"][0]["direction"], expected["direction"]),
            (
                [row["label"] for row in result["evaluation_windows"]],
                expected["window_labels"],
            ),
            (
                result["reference_scope"]["named_references"],
                expected["named_references"],
            ),
            (result["appeal_mode"], expected["appeal_mode"]),
        ):
            semantic_checks += 1
            semantic_passes += actual == wanted
        if expected["status"] == "WITHHELD_REQUEST_AMBIGUOUS":
            ambiguous_cases += 1
            ambiguous_passes += (
                result["status"] == expected["status"]
                and result["confirmation_required"] is True
                and result["action_generated"] is False
            )
        else:
            assert result["status"] == expected["status"], case["case_id"]

    assert explicit_fact_passes == explicit_fact_checks
    assert semantic_passes / semantic_checks >= 0.95
    assert ambiguous_passes == ambiguous_cases
