"""Numeric character evidence is explicit and never inferred from prose."""

from __future__ import annotations

import math

import pytest

from engine.ingredient_intelligence import (
    CharacterEvidenceStatus,
    MaterialProfile,
    NumericCharacterUnavailable,
    character_distance,
    find_similar,
    find_similar_with_evidence,
    get_profile,
)


def test_prose_is_preserved_without_becoming_a_numeric_vector():
    profile = get_profile("nerolidol")
    assert profile is not None
    assert profile.character_description == "woody-floral balsamic sesquiterpene alcohol"
    assert profile.character is None
    assert profile.numeric_character is None
    assert profile.character_status is CharacterEvidenceStatus.PROSE_ONLY
    with pytest.raises(NumericCharacterUnavailable, match="PROSE_ONLY"):
        profile.dimension_vector()
    with pytest.raises(NumericCharacterUnavailable, match="PROSE_ONLY"):
        profile.dominant_character()
    with pytest.raises(NumericCharacterUnavailable, match="PROSE_ONLY"):
        profile.character_tags()


def test_sparse_numeric_mapping_and_legitimate_zero_are_preserved():
    profile = MaterialProfile(name="sparse", character={"freshness": 0, "floral": 7})
    assert profile.character_status is CharacterEvidenceStatus.AVAILABLE
    assert profile.numeric_character == {"freshness": 0.0, "floral": 7.0}
    assert profile.dimension_vector()[2] == 0.0
    assert profile.dominant_character() == "floral"


@pytest.mark.parametrize(
    "value",
    [
        {"freshness": True},
        {"freshness": math.nan},
        {"freshness": math.inf},
        {"freshness": -0.1},
        {"freshness": 10.1},
        {"not_a_dimension": 1.0},
        [1.0],
    ],
)
def test_invalid_numeric_character_fails_closed(value):
    profile = MaterialProfile(name="invalid", character=value)
    assert profile.character_status is CharacterEvidenceStatus.INVALID_NUMERIC
    assert profile.numeric_character is None
    with pytest.raises(NumericCharacterUnavailable, match="INVALID_NUMERIC"):
        profile.dimension_vector()


def test_missing_numeric_character_is_distinct_from_unknown_identity():
    profile = MaterialProfile(name="known-without-character")
    assert profile.character_status is CharacterEvidenceStatus.MISSING
    assert get_profile("definitely-not-a-material") is None


def test_similarity_reports_unavailable_candidates_and_never_ranks_prose_source():
    result = find_similar_with_evidence("nerolidol")
    assert result.ranked == ()
    assert result.source_status is CharacterEvidenceStatus.PROSE_ONLY
    assert find_similar("nerolidol") == []

    hedione = get_profile("Hedione")
    iso_e = get_profile("Iso E Super")
    assert hedione is not None and iso_e is not None
    assert character_distance(hedione, iso_e) >= 0.0
    ranked = find_similar_with_evidence("Hedione", n=3)
    assert len(ranked.ranked) == 3
    assert "nerolidol" in ranked.unavailable


def test_alias_cache_preserves_canonical_evidence_status():
    canonical = get_profile("Jasmine Sambac")
    alias = get_profile("Jasmine Sambac (10% in DPG)")
    assert canonical is not None and alias is not None
    assert canonical.character_status is alias.character_status
    assert canonical.numeric_character == alias.numeric_character
