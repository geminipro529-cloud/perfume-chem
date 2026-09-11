"""Tests for the per-flower peer-reviewed evidence layer.

Ensures every soliflore flower (and the mixed-florals bouquet group) carries a
verified, well-formed peer-reviewed citation set, and that documented hedonics
gaps stay explicit rather than silently missing.
"""
from __future__ import annotations

from engine.knowledge.floral_hedonic_evidence import (
    FLORAL_EVIDENCE_CATEGORIES,
    MIN_REFS_PER_FLOWER,
    MIXED_FLORALS_KEY,
    all_floral_evidence,
    floral_evidence_coverage,
    flower_evidence_keys,
    get_floral_evidence,
    load_floral_hedonics_gaps,
    soliflore_evidence_for,
    validate_floral_evidence,
)
from engine.knowledge.perfume_taxonomy import SolifloreType


def test_validation_passes():
    validate_floral_evidence()


def test_every_soliflore_type_has_evidence_with_minimum_refs():
    for soliflore in SolifloreType:
        evidence = soliflore_evidence_for(soliflore)
        assert evidence is not None, soliflore
        assert evidence.citation_count >= MIN_REFS_PER_FLOWER, (
            soliflore,
            evidence.citation_count,
        )


def test_mixed_florals_group_present_and_sourced():
    evidence = get_floral_evidence(MIXED_FLORALS_KEY)
    assert evidence is not None
    assert evidence.citation_count >= MIN_REFS_PER_FLOWER
    assert evidence.hedonics_refs  # bouquet hedonics covered
    assert "mixture_perception" in evidence.categories or "olfactory_white" in evidence.categories


def test_refs_are_well_formed_https_dois_or_urls():
    for evidence in all_floral_evidence():
        for ref in evidence.refs:
            assert ref.title
            assert ref.authors
            assert ref.journal
            assert ref.year > 1900
            assert ref.category in FLORAL_EVIDENCE_CATEGORIES
            assert ref.url.startswith("https://")
            assert ref.used_for


def test_coverage_counts_and_documented_gaps_are_consistent():
    coverage = floral_evidence_coverage()
    assert coverage["flowers"] == len(list(SolifloreType)) + 1  # + mixed_florals
    assert coverage["below_minimum"] == []
    gaps = load_floral_hedonics_gaps()
    assert set(coverage["flowers_missing_hedonics"]) == set(gaps)
    # These four are the honest, documented gaps (no dedicated hedonic study found).
    assert set(gaps) == {"champaca", "mimosa", "hyacinth", "linden"}
    # Every other flower must carry a hedonic citation.
    for flower in flower_evidence_keys():
        if flower in gaps:
            continue
        assert get_floral_evidence(flower).hedonics_refs, flower
