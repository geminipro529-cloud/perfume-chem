from __future__ import annotations

import pytest

from engine.perception.harmonic_request_router import (
    HarmonicRequestDomain,
    HarmonicRouteRequestV1,
    route_harmonic_request,
)


def test_evidence_only_route_never_injects_cypress_architecture() -> None:
    result = route_harmonic_request(
        HarmonicRouteRequestV1(
            request_id="ORDER-CONFOUNDING-1",
            domains=(
                HarmonicRequestDomain.TEMPORAL_EVIDENCE,
                HarmonicRequestDomain.PREFERENCE_EVIDENCE,
            ),
        )
    )

    assert result.module_ids == ("temporal-ledger", "hedonic-preference")
    assert result.architecture_expansion_allowed is False
    assert result.target_architecture_required is False
    assert "cypress-heart-frontier" not in result.module_ids
    assert "architecture-compiler" not in result.module_ids


def test_architecture_route_retains_empirical_claim_boundaries() -> None:
    result = route_harmonic_request(
        HarmonicRouteRequestV1(
            request_id="CYP-02-DESIGN-1",
            domains=(HarmonicRequestDomain.ARCHITECTURE,),
            target_identity="CYP-02 Cypress subject architecture",
        )
    )

    assert result.module_ids == (
        "material-capability-atlas",
        "cypress-heart-frontier",
        "family-depth",
        "architecture-compiler",
        "architectural-delta",
        "temporal-ledger",
        "hedonic-preference",
    )
    assert result.architecture_expansion_allowed is True
    assert result.target_architecture_required is True
    assert result.empirical_modules_are_claim_boundaries is True


def test_router_deduplicates_domains_without_vote_counting() -> None:
    result = route_harmonic_request(
        HarmonicRouteRequestV1(
            request_id="TEMPORAL-REPEAT",
            domains=(
                HarmonicRequestDomain.TEMPORAL_EVIDENCE,
                HarmonicRequestDomain.TEMPORAL_EVIDENCE,
            ),
        )
    )

    assert result.module_ids == ("temporal-ledger",)
    assert result.vote_counting_used is False


def test_router_requires_an_explicit_domain_and_architecture_target() -> None:
    with pytest.raises(ValueError, match="at least one request domain"):
        HarmonicRouteRequestV1(request_id="EMPTY", domains=())

    with pytest.raises(ValueError, match="target identity"):
        route_harmonic_request(
            HarmonicRouteRequestV1(
                request_id="ARCH-NO-TARGET",
                domains=(HarmonicRequestDomain.ARCHITECTURE,),
            )
        )


def test_router_never_grants_downstream_authority() -> None:
    result = route_harmonic_request(
        HarmonicRouteRequestV1(
            request_id="PREFERENCE-ONLY",
            domains=(HarmonicRequestDomain.PREFERENCE_EVIDENCE,),
        )
    )

    assert result.formula_mutation_authorized is False
    assert result.physical_execution_authorized is False
    assert result.hedonic_authority is False
    assert result.release_authority is False
