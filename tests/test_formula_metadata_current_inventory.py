"""Regression coverage for the preliminary formula inventory warning."""

from __future__ import annotations

from pathlib import Path

from engine.formula_metadata import _load_inventory_names, pipeline_preflight_guard
from engine.name_utils import normalize_name


ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "formulas" / "Gin_Vetiver_Cypress_Air_Haitian_Grapefruit100_AddOnly_20260910.md"


def test_default_inventory_names_come_from_current_authority_overlay() -> None:
    normalized = {normalize_name(name) for name in _load_inventory_names()}

    assert normalize_name("Vetiver EO (Haiti)") in normalized
    assert normalize_name("Cedarwood Virginia") in normalized
    assert normalize_name("Coriander Essential Oil") in normalized
    assert normalize_name("Cinnamyl Alcohol") in normalized


def test_current_gin_vetiver_candidate_has_no_false_inventory_warning() -> None:
    result = pipeline_preflight_guard(str(FORMULA), brief="vetiver_woody")

    assert not any(
        warning.startswith("INVENTORY_MISSING:") for warning in result.warnings
    )
