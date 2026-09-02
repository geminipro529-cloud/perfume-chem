"""DeepLuna Chat exact-project runtime policy guard."""

from __future__ import annotations

from dataclasses import dataclass


EXPECTED_PROJECT = "perfume-chem-cheapluna-isolated"
EXPECTED_PROFILE = "cheapluna-chat"
EXPECTED_ROUTE = "DIRECT_PRO"
EXPECTED_LUNA_MODE = "NO_LUNA"


@dataclass(frozen=True)
class RuntimeRequest:
    project_id: str
    profile: str
    route: str
    luna_mode: str
    deep_luna_fast_enabled: bool
    alternate_fallbacks_enabled: bool


@dataclass(frozen=True)
class RuntimeDecision:
    allowed: bool
    state: str
    reasons: tuple[str, ...]
    fallback_used: bool = False


def validate_runtime_request(request: RuntimeRequest) -> RuntimeDecision:
    reasons: list[str] = []
    if request.project_id != EXPECTED_PROJECT:
        reasons.append("project-id mismatch")
    if request.profile != EXPECTED_PROFILE:
        reasons.append("profile mismatch")
    if request.route != EXPECTED_ROUTE:
        reasons.append("unapproved route")
    if request.luna_mode != EXPECTED_LUNA_MODE:
        reasons.append("luna mode mismatch")
    if request.deep_luna_fast_enabled:
        reasons.append("DeepLuna Fast is disabled")
    if request.alternate_fallbacks_enabled:
        reasons.append("alternate fallbacks are disabled")
    return RuntimeDecision(
        allowed=not reasons,
        state=("READY_POLICY_MATCH" if not reasons else "DENY_RUNTIME_POLICY"),
        reasons=tuple(reasons),
        fallback_used=False,
    )


def provider_outcome(*, request: RuntimeRequest, provider_succeeded: bool) -> RuntimeDecision:
    policy = validate_runtime_request(request)
    if not policy.allowed:
        return policy
    if provider_succeeded:
        return RuntimeDecision(True, "PROVIDER_SUCCESS", (), fallback_used=False)
    return RuntimeDecision(
        False,
        "PROVIDER_FAILURE_NO_FALLBACK",
        ("provider failure remains failure; silent reroute is prohibited",),
        fallback_used=False,
    )
