"""Regression tests for semantic labels in the required analysis formatter."""

from scripts.format_pipeline_analysis import build_oav_structural


def test_structural_balance_does_not_relabel_every_heart_material_as_floral() -> None:
    materials = [
        {"name": "Coriander", "note": "top", "family": "aromatic", "oav": 20.0},
        {"name": "Juniper", "note": "heart", "family": "aromatic", "oav": 80.0},
        {"name": "Hedione", "note": "heart", "family": "floral", "oav": 10.0},
        {"name": "Vetiver", "note": "base", "family": "woody", "oav": 30.0},
    ]
    formula = {"formula_state": {"batch_volume_ml": 30.0}}

    rendered = "\n".join(build_oav_structural(materials, formula))

    assert "### Note-Tier OAV Balance" in rendered
    assert "**Top**" in rendered
    assert "**Heart**" in rendered
    assert "**Base**" in rendered
    assert "**Floral**" not in rendered
