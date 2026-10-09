"""classify_note always answers top, heart or base, so note tallies never break."""

from types import SimpleNamespace

import engine.ingredient_intelligence as ingredient_intelligence
import engine.optimizer.models as models


def test_a_profile_note_that_is_not_a_tier_falls_back_to_a_tier(monkeypatch) -> None:
    monkeypatch.setattr(models, "_lookup_material", lambda _name: None)
    monkeypatch.setattr(
        ingredient_intelligence, "get_profile", lambda _name: SimpleNamespace(note="unassigned")
    )

    assert models.classify_note("Received Absolute With No Review") == "heart"


def test_a_formula_with_an_identity_only_material_gets_a_note_distribution() -> None:
    # Ambrette Seed Absolute was received on 2026-10-07 as identity-only intake,
    # so its profile note is "unassigned" and its cache row carries no physics.
    vector = models.FormulaVector({"Ambrette Seed Absolute": 10.0, "Linalool": 90.0})

    assert set(vector.note_distribution()) == {"top", "heart", "base"}
