"""Exact-domain router for the integrated Perfume-Chem module stack.

The router prevents an architecture-specific program from leaking into a
temporal or preference-only request.  Routing is explicit, deterministic, and
non-voting: the caller declares domains, and each domain activates only its
own modules.  Architecture requests retain the empirical modules as claim
boundaries, but absent empirical evidence never acquires sensory or hedonic
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.evidence_contracts import canonical_json_bytes, sha256_hex


class HarmonicRequestDomain(str, Enum):
    ARCHITECTURE = "ARCHITECTURE"
    TEMPORAL_EVIDENCE = "TEMPORAL_EVIDENCE"
    PREFERENCE_EVIDENCE = "PREFERENCE_EVIDENCE"


@dataclass(frozen=True, slots=True)
class HarmonicRouteRequestV1:
    request_id: str
    domains: tuple[HarmonicRequestDomain, ...]
    target_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request ID must be non-empty")
        normalized: list[HarmonicRequestDomain] = []
        for domain in self.domains:
            parsed = HarmonicRequestDomain(domain)
            if parsed not in normalized:
                normalized.append(parsed)
        if not normalized:
            raise ValueError("at least one request domain is required")
        object.__setattr__(self, "domains", tuple(normalized))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "harmonic_route_request_v1",
            "request_id": self.request_id,
            "domains": [domain.value for domain in self.domains],
            "target_identity": self.target_identity,
        }


@dataclass(frozen=True, slots=True)
class HarmonicRouteResultV1:
    request_id: str
    domains: tuple[HarmonicRequestDomain, ...]
    module_ids: tuple[str, ...]
    architecture_expansion_allowed: bool
    target_architecture_required: bool
    empirical_modules_are_claim_boundaries: bool
    vote_counting_used: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "harmonic_route_result_v1",
            "request_id": self.request_id,
            "domains": [domain.value for domain in self.domains],
            "module_ids": list(self.module_ids),
            "architecture_expansion_allowed": self.architecture_expansion_allowed,
            "target_architecture_required": self.target_architecture_required,
            "empirical_modules_are_claim_boundaries": (
                self.empirical_modules_are_claim_boundaries
            ),
            "vote_counting_used": self.vote_counting_used,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "hedonic_authority": self.hedonic_authority,
            "release_authority": self.release_authority,
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


def route_harmonic_request(request: HarmonicRouteRequestV1) -> HarmonicRouteResultV1:
    architecture = HarmonicRequestDomain.ARCHITECTURE in request.domains
    if architecture and not (request.target_identity or "").strip():
        raise ValueError("architecture requests require an explicit target identity")

    if architecture:
        module_ids = (
            "material-capability-atlas",
            "cypress-heart-frontier",
            "family-depth",
            "architecture-compiler",
            "architectural-delta",
            "temporal-ledger",
            "hedonic-preference",
        )
    else:
        selected: list[str] = []
        if HarmonicRequestDomain.TEMPORAL_EVIDENCE in request.domains:
            selected.append("temporal-ledger")
        if HarmonicRequestDomain.PREFERENCE_EVIDENCE in request.domains:
            selected.append("hedonic-preference")
        module_ids = tuple(selected)

    return HarmonicRouteResultV1(
        request_id=request.request_id,
        domains=request.domains,
        module_ids=module_ids,
        architecture_expansion_allowed=architecture,
        target_architecture_required=architecture,
        empirical_modules_are_claim_boundaries=architecture,
    )


__all__ = [
    "HarmonicRequestDomain",
    "HarmonicRouteRequestV1",
    "HarmonicRouteResultV1",
    "route_harmonic_request",
]
