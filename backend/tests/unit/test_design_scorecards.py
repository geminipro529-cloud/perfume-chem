"""Create several: a FORMULA_DESIGN job can carry the yardstick's floors per alternative.

The floors are the Opus duel's (engine/formulation_intelligence/yardstick.py):
owned stock, IFRA, the pre-mix guard, the 30 mL bottle, pours of at least
10 uL and the default-omitted musks. Only status and detail travel; no OAV,
name or liking number is attached.
"""

import pytest
from pydantic import ValidationError

from app.services import engine_job_executor
from app.services.engine_job_registry import ENGINE_JOB_REGISTRY, FormulaDesignPayloadV2


def _row(name: str, amount: str) -> dict[str, str]:
    return {
        "identity_name": name,
        "amount_decimal": amount,
        "amount_unit": "uL",
        "stock_fraction_decimal": "1",
        "fraction_basis": "neat",
        "carrier": "",
        "stock_id": "",
    }


def _report() -> dict:
    return {
        "formula_name": "Scorecard Check",
        "design_variants": [
            {"variant_id": "v1", "formula": {"rows": [
                _row("Iso E Super", "3000"), _row("Hedione", "2995"), _row("Tonalide", "5"),
            ]}},
            {"variant_id": "v2", "duplicate_of_variant_id": "v1", "formula": None},
            {"variant_id": "v3", "formula": {"rows": [_row("Iso E Super", "3000"), _row("Hedione", "3000")]}},
        ],
    }


def test_scorecard_is_opt_in_and_strict() -> None:
    assert FormulaDesignPayloadV2(message="a dry lavender amber").scorecard is False
    assert FormulaDesignPayloadV2(message="a dry lavender amber", scorecard=True).scorecard is True
    with pytest.raises(ValidationError):
        FormulaDesignPayloadV2(message="a dry lavender amber", scorecard="yes")


def test_design_job_fingerprint_includes_the_yardstick() -> None:
    paths = ENGINE_JOB_REGISTRY["FORMULA_DESIGN"].implementation_paths
    assert "engine/formulation_intelligence/yardstick.py" in paths


def test_each_composed_alternative_gets_the_floors() -> None:
    cards = engine_job_executor._design_scorecards(_report())

    assert [card["variant_id"] for card in cards] == ["v1", "v3"]  # no formula, no card
    first, second = (card["floors"] for card in cards)
    assert set(first) == {
        "F1_owned_stock", "F2_ifra", "F3_pre_mix_guard", "F4_bottle", "F5_pours", "F6_musks",
    }
    assert all(set(floor) == {"status", "detail"} for floor in first.values())
    assert first["F5_pours"]["status"] == "FAIL"
    assert "Tonalide 5 uL" in first["F5_pours"]["detail"]
    assert first["F6_musks"]["status"] == "FAIL"
    assert first["F3_pre_mix_guard"]["status"] == "NOT_APPLICABLE"
    assert second["F5_pours"]["status"] == "PASS"
    assert second["F6_musks"]["status"] == "PASS"
    assert second["F4_bottle"]["status"] == "PASS"


def test_a_scorer_error_leaves_the_design_alone(monkeypatch) -> None:
    from engine.formulation_intelligence import yardstick

    def broken(formula, brief):
        raise KeyError("missing")

    monkeypatch.setattr(yardstick, "score_formula", broken)
    cards = engine_job_executor._design_scorecards(_report())

    assert cards == [{"variant_id": "v1", "error": "KeyError"}, {"variant_id": "v3", "error": "KeyError"}]
