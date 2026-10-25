"""Lavender 40/42, Aroma&More gets its own 40/42-grade composition (Kenny, 25 Oct 2026, stock thread).

He asked why the engine never uses it and to differentiate it from his BONTAUX lavender; Aroma&More
publish no GC, so his answer was "You estimate". The estimate is the midpoint of two published 40/42
GC reports (Shay & Company lot 13282; Amphora Aromatics typical). Both carry the lavandin admixture
Aroma&More describe: camphor and 1,8-cineole near 3% each, little lavandulyl acetate.
"""
from __future__ import annotations

import pytest

from engine.ingredient_intelligence import get_profile
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata, get_constituents

NAME = "Lavender 40/42, Aroma&More"
BONTAUX = "Lavender EO (BONTAUX SAS)"
KEY = "lavender 40/42 grade two published gc midpoint profile"


def _fractions(name: str) -> dict[str, float]:
    rows = get_constituents(name)
    assert rows is not None
    return {row[0]: row[1] for row in rows}


def test_lavender_40_42_uses_the_two_report_midpoints_without_rescaling():
    assert _fractions(NAME) == pytest.approx(
        {
            "linalyl acetate": 0.3953,
            "linalool": 0.3733,
            "terpinen-4-ol": 0.035,
            "camphor": 0.033,
            "1,8-cineole": 0.03065,
            "limonene": 0.01975,
            "beta-caryophyllene": 0.0161,
            "borneol": 0.0151,
            "lavandulyl acetate": 0.00885,
            "ocimene": 0.00715,
        }
    )
    metadata = get_composite_metadata(NAME)
    assert metadata.profile_key == KEY
    assert metadata.resolution == "literature_proxy"
    assert metadata.batch_specific is False
    assert metadata.characterized_fraction == pytest.approx(0.9342)
    assert metadata.unresolved_fraction == pytest.approx(0.0658)
    assert metadata.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert any("Lot13282" in src for src in metadata.sources)
    assert any("amphora-aromatics" in src for src in metadata.sources)
    assert "not an analysis of the owned" in " ".join(metadata.limitations)


def test_lavender_40_42_carries_the_lavandin_signature_the_bontaux_oil_lacks():
    grade, bontaux = _fractions(NAME), _fractions(BONTAUX)
    assert grade["camphor"] >= 2 * bontaux["camphor"]
    assert grade["1,8-cineole"] > 0.025 and "1,8-cineole" not in bontaux
    assert grade["borneol"] > 0.01 and "borneol" not in bontaux
    assert grade["lavandulyl acetate"] < bontaux["lavandulyl acetate"]
    assert grade["linalyl acetate"] > bontaux["linalyl acetate"]


def test_lavender_40_42_character_reads_fresher_and_less_floral_than_bontaux():
    grade, bontaux = get_profile(NAME), get_profile(BONTAUX)
    assert grade.character != bontaux.character
    assert grade.character["floral"] < bontaux.character["floral"]
    assert grade.character["green"] > bontaux.character["green"]
    assert grade.character["woody"] > bontaux.character["woody"]


def test_lavender_40_42_is_modeled_in_a_formula():
    state = build_formula_state({NAME: 200.0, "Hedione": 800.0})
    row = next(material for material in state.materials if material.name == NAME)
    assert row.oav is not None
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
