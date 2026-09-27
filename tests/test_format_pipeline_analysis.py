"""Regression tests for semantic labels in the required analysis formatter."""

from scripts.format_pipeline_analysis import (
    build_oav_headspace_table,
    build_oav_structural,
    build_perfumer,
    build_temporal,
)


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


def test_unknown_vapor_remains_unknown_in_tables_and_perfumer_text() -> None:
    materials = [
        {
            "name": "Unknown VP material",
            "dilution": 1.0,
            "raw_ul": 10.0,
            "active_ul": 10.0,
            "mw_g_mol": 200.0,
            "mole_fraction": 1.0,
            "vp_pure_pa": None,
            "gamma": 1.0,
            "vapor_ppm": None,
            "odt_air_ppm": 0.1,
            "oav": None,
            "note": "heart",
            "role": "character",
            "family": "floral",
        }
    ]
    state = {
        "materials": materials,
        "note_distribution": {"top": 0.0, "heart": 100.0, "base": 0.0},
        "total_raw_ul": 10.0,
        "total_vapor_ppm": None,
    }
    formula = {
        "formula_state": state,
        "time_series": [
            {
                "label": "opening",
                "t_seconds": 0.0,
                "state": state,
                "dominant_oav": [],
            }
        ],
    }

    headspace = "\n".join(build_oav_headspace_table(materials))
    temporal = "\n".join(build_temporal(formula))
    perfumer = "\n".join(build_perfumer(formula))

    assert "**Total vapor:** UNKNOWN" in headspace
    assert "Vapor:UNKNOWN" in temporal
    assert "Total vapor: UNKNOWN" in perfumer
    assert "Total vapor: 0" not in headspace
    assert "Total vapor: 0" not in perfumer
