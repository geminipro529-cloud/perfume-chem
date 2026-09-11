"""Evidence-registry tests for the Deep Architecture capability (Phase 1)."""
from __future__ import annotations

from engine.knowledge.deep_architecture import (
    AUTHORITY_PREDICTED_PHYSICAL,
    AUTHORITY_STRUCTURAL,
    DIMENSIONS,
    MIN_DIMENSION_REFS,
    archetype_citations,
    dimension_authority,
    dimension_citations,
    evidence_coverage,
    family_citations,
    load_collected_evidence,
    validate_deep_architecture,
)


def test_registry_validates_and_reports_coverage():
    coverage = validate_deep_architecture()
    assert set(coverage["dimension_refs"]) == set(DIMENSIONS)


def test_every_dimension_has_minimum_peer_reviewed_refs():
    for dim in DIMENSIONS:
        assert len(dimension_citations(dim)) >= MIN_DIMENSION_REFS, dim


def test_spatial_projection_is_predicted_physical_only():
    assert dimension_authority("spatial_projection") == AUTHORITY_PREDICTED_PHYSICAL
    for dim in DIMENSIONS:
        if dim != "spatial_projection":
            assert dimension_authority(dim) == AUTHORITY_STRUCTURAL


def test_all_thirteen_families_have_evidence():
    coverage = evidence_coverage()
    assert len(coverage["families"]) == 13
    for family in coverage["families"]:
        assert family_citations(family), family


def test_gaps_are_documented_not_silent():
    hits = load_collected_evidence().get("gaps", {})
    # Subfamilies are largely practitioner terms; archetype GC-MS is rare.
    assert "subfamilies" in hits
    assert "archetypes" in hits


def test_dois_are_all_verified():
    verification = load_collected_evidence().get("doi_verification", {})
    assert verification.get("checked", 0) > 0
    assert verification.get("failed_dois") == []
    assert verification["resolved"] == verification["checked"]


def test_curated_registries_are_merged_into_dimensions():
    keys = {ref["key"] for ref in dimension_citations("depth_stacking")}
    assert any(k.startswith("curated:") for k in keys)
    assert any(k.startswith("doi:") for k in keys)


def test_archetype_citations_are_optional_but_safe():
    # Archetype GC-MS coverage is a documented gap; the API must not raise.
    assert isinstance(archetype_citations("iris_coumarin_amber.dhi2011"), tuple)
