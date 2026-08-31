from __future__ import annotations

from engine.ingredient_intelligence import get_all_profiles, get_profile
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

TEXT_ONLY_INTAKE_PROFILES = {
    "Cypress EO": "dry conifer-woody-aromatic natural",
    "Elemi EO": "elemi pine-citrus-balsamic resin oil",
    "Nerolidol": "woody-floral balsamic sesquiterpene alcohol",
}


def test_every_material_profile_exposes_numeric_character_mapping() -> None:
    profiles = get_all_profiles()

    assert profiles
    assert all(isinstance(profile.character, dict) for profile in profiles.values())


def test_text_only_intake_profiles_preserve_prose_without_inventing_dimensions() -> None:
    for name, expected_description in TEXT_ONLY_INTAKE_PROFILES.items():
        profile = get_profile(name)

        assert profile is not None
        assert profile.character == {}
        assert profile.character_description == expected_description


def test_character_radar_excludes_unscored_text_profiles_from_denominator() -> None:
    scorer = FormulaScorer()
    scored_only = FormulaVector(
        ingredients={"Hedione": 100.0},
        dilutions={"Hedione": 1.0},
    )
    with_unscored_text_profiles = FormulaVector(
        ingredients={"Hedione": 50.0, "Cypress EO": 40.0, "Elemi EO": 10.0},
        dilutions={"Hedione": 1.0, "Cypress EO": 1.0, "Elemi EO": 1.0},
    )

    assert scorer.formula_character_radar(
        with_unscored_text_profiles
    ) == scorer.formula_character_radar(scored_only)
