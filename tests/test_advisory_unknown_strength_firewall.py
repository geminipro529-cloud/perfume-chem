from __future__ import annotations

import pytest

import scripts.verify_formula_workflow as verification_workflow
from engine.formula_analyzer import (
    FormulaInfo,
    formula_to_vector,
)
from engine.formula_analyzer import (
    _parse_dilution as parse_analyzer_dilution,
)
from scripts.intervention_recommend import (
    SourceFormula,
    _build_formula_vector,
)
from scripts.intervention_recommend import (
    _parse_dilution as parse_intervention_dilution,
)
from scripts.score_collection_formulas import parse_additions
from scripts.score_designer_prestige_18 import (
    parse_dilution as parse_designer_dilution,
)
from scripts.score_designer_prestige_18 import (
    parse_formula_rows as parse_designer_formula_rows,
)


@pytest.mark.parametrize(
    "parser",
    [parse_analyzer_dilution, parse_intervention_dilution, parse_designer_dilution],
)
@pytest.mark.parametrize("value", ["", "-", "—", "N/A", "one percent"])
def test_legacy_advisory_parsers_never_invent_neat(parser, value):
    with pytest.raises(ValueError, match="cannot default to neat"):
        parser(value)


@pytest.mark.parametrize(
    "parser",
    [parse_analyzer_dilution, parse_intervention_dilution, parse_designer_dilution],
)
def test_legacy_advisory_parsers_accept_explicit_neat_and_percent(parser):
    assert parser("neat") == 1.0
    assert parser("10% in DPG") == 0.1


def test_formula_analyzer_abstains_when_formula_vector_strength_is_missing():
    info = FormulaInfo(number=1, name="Unknown strength", ingredients={"Hedione": 100.0})

    with pytest.raises(ValueError, match="advisory analysis abstained"):
        formula_to_vector(info)


def test_intervention_report_abstains_when_bundle_strength_is_missing():
    source = SourceFormula(
        number=1,
        name="Unknown strength",
        ingredients_pct={"Hedione": 100.0},
        dilutions={},
        body="",
        source_kind="verification_bundle",
    )

    with pytest.raises(ValueError, match="intervention analysis abstained"):
        _build_formula_vector(source)


def test_designer_formula_requires_a_dilution_column():
    rows = [["Material", "uL"], ["Hedione", "100"]]

    with pytest.raises(ValueError, match="explicit dilution column"):
        parse_designer_formula_rows(rows)


def test_collection_additions_require_a_dilution_column(tmp_path):
    additions = tmp_path / "additions.md"
    additions.write_text(
        """## 1. Trial

| Addition | uL |
|---|---:|
| Hedione | 10 |
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="explicit dilution column"):
        parse_additions(additions)


@pytest.mark.parametrize(
    ("dilutions", "stock_spec"),
    [
        ({}, {"declared": False, "fraction": 1.0}),
        ({"Hedione": 1.0}, {"declared": True, "fraction": 0.1}),
        (
            {"Hedione": 1.0},
            {"declared": True, "fraction": 1.0, "conflict": True},
        ),
    ],
)
def test_verification_bundle_abstains_before_formula_vector_scoring(
    monkeypatch,
    dilutions,
    stock_spec,
):
    formula = {
        "ingredients_pct": {"Hedione": 100.0},
        "dilutions": dilutions,
        "stock_specs": {"Hedione": stock_spec},
    }

    def unexpected_formula_vector(**kwargs):
        pytest.fail(f"FormulaVector must not be constructed: {kwargs}")

    monkeypatch.setattr(verification_workflow, "FormulaVector", unexpected_formula_vector)
    with pytest.raises(ValueError, match="advisory scoring abstained"):
        verification_workflow.build_verification_bundle(formula)


def test_verification_bundle_accepts_bound_neat_and_ten_percent(monkeypatch):
    formula = {
        "ingredients_pct": {"Hedione": 60.0, "Vanillin": 40.0},
        "dilutions": {"Hedione": 1.0, "Vanillin": 0.1},
        "stock_specs": {
            "Hedione": {"declared": True, "fraction": 1.0},
            "Vanillin": {"declared": True, "fraction": 0.1},
        },
    }
    captured = {}

    class StopAfterFormulaVectorError(Exception):
        pass

    def capture_formula_vector(**kwargs):
        captured.update(kwargs)
        raise StopAfterFormulaVectorError

    monkeypatch.setattr(verification_workflow, "FormulaVector", capture_formula_vector)
    with pytest.raises(StopAfterFormulaVectorError):
        verification_workflow.build_verification_bundle(formula)

    assert captured["dilutions"] == {"Hedione": 1.0, "Vanillin": 0.1}
