"""Narrow admitted runtime for the benchmarked CYP-02 architecture scope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from engine.perception.cypress_harmonic_program import (
    CypressHarmonicProgramResultV1,
    build_default_cypress_harmonic_program,
)
from engine.perception.harmonic_request_router import (
    HarmonicRequestDomain,
    HarmonicRouteRequestV1,
    HarmonicRouteResultV1,
    route_harmonic_request,
)
from engine.perception.harmonic_runtime_registry import (
    V6_ADMITTED_ARCHITECTURE_MODULE_IDS,
    load_harmonic_runtime_registry,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ADMITTED_REQUEST_TARGET = "CYP-02 Cypress subject architecture"
_PROGRAM_TARGET_IDENTITY = (
    "A luxurious Cypress-subject perfume in which high-quality French Cypress "
    "EO is made more beautiful by a relational floral heart, rooted depth, "
    "controlled contrast, and temporal reveal rather than by botanical literalism"
)


class HarmonicRuntimeAdmissionError(RuntimeError):
    """The exact V6 evidence, bytes, route, or target scope failed closed."""


@dataclass(frozen=True, slots=True)
class AdmittedCypressHarmonicRunV1:
    registry_sha256: str
    admitted_module_ids: tuple[str, ...]
    route: HarmonicRouteResultV1
    program: CypressHarmonicProgramResultV1
    authority_flags: Mapping[str, bool]


def run_admitted_cypress_harmonic(
    request: HarmonicRouteRequestV1,
    *,
    project_root: Path | None = None,
) -> AdmittedCypressHarmonicRunV1:
    """Execute only the exact admitted CYP-02 computational architecture.

    Evidence-only and mixed requests remain blocked because the frozen
    admission receipt explicitly excludes evidence-only routing.  This route
    produces a computational design receipt; it cannot mutate a formula or
    authorize physical, sensory, hedonic, safety, stability, purchase, or
    release actions.
    """

    root = (project_root or _PROJECT_ROOT).resolve()
    try:
        registry = load_harmonic_runtime_registry(root)
    except (OSError, ValueError) as exc:
        raise HarmonicRuntimeAdmissionError(
            f"HARMONIC_RUNTIME_GATE_FAILED: {exc}"
        ) from exc

    if request.domains != (HarmonicRequestDomain.ARCHITECTURE,):
        raise HarmonicRuntimeAdmissionError(
            "EVIDENCE_ONLY_REQUEST_ROUTING_NOT_ADMITTED: V6 accepts one exact "
            "ARCHITECTURE domain only"
        )
    if request.target_identity != _ADMITTED_REQUEST_TARGET:
        raise HarmonicRuntimeAdmissionError(
            "TARGET_IDENTITY_OUTSIDE_ADMITTED_RUNTIME_SCOPE: only the exact "
            "CYP-02 Cypress subject architecture is executable"
        )

    route = route_harmonic_request(request)
    if route.vote_counting_used or not route.target_architecture_required:
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: deterministic architecture route invalid"
        )
    if registry.admitted_architecture_module_ids != (
        V6_ADMITTED_ARCHITECTURE_MODULE_IDS
    ):
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: admitted module set drift"
        )
    if registry.guardrail_module_ids != ("harmonic-request-router",):
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: request router guardrail missing"
        )
    if registry.admitted_scope.get("evidence_only_request_routing") is not False:
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: evidence-only scope widened"
        )

    program = build_default_cypress_harmonic_program()
    program_authority_values = (
        program.formula_mutation_authorized,
        program.physical_execution_authorized,
        program.compounding_authorized,
        program.purchase_authority,
        program.sensory_authority,
        program.hedonic_authority,
        program.similarity_authority,
        program.performance_authority,
        program.safety_authority,
        program.stability_authority,
        program.release_authority,
    )
    if any(registry.authority_flags.values()) or any(program_authority_values):
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: downstream authority must remain false"
        )
    if program.frontier_result.target.target_identity != _PROGRAM_TARGET_IDENTITY:
        raise HarmonicRuntimeAdmissionError(
            "HARMONIC_RUNTIME_GATE_FAILED: program target identity drift"
        )

    return AdmittedCypressHarmonicRunV1(
        registry_sha256=registry.registry_sha256,
        admitted_module_ids=registry.admitted_architecture_module_ids,
        route=route,
        program=program,
        authority_flags=dict(registry.authority_flags),
    )


__all__ = [
    "AdmittedCypressHarmonicRunV1",
    "HarmonicRuntimeAdmissionError",
    "run_admitted_cypress_harmonic",
]
