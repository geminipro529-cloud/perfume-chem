"""Deterministic, claim-bounded assistant packets for the local lab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256
from math import isfinite
from typing import Any, Mapping, cast

_REVISION = "lab-packet-v1"
_DECIMAL_QUANTUM = Decimal("0.000001")
_INTENTS: dict[str, tuple[tuple[str, ...], bool, str]] = {
    "dashboard": (("LabRepository.dashboard_counts",), False, "Review the surfaced warnings."),
    "bottle_status": (("LabService.reconstruct_bottle",), True, "Review the replayed bottle state."),
    "formula_analysis": (("PerfumeWorkbench.analyze",), True, "Review evidence and missing matrix inputs."),
    "safety_assessment": (("PerfumeWorkbench.assess_safety",), True, "Resolve every unverified safety input before use."),
    "rank_interventions": (("PerfumeWorkbench.rank_interventions",), True, "Smell-test the nondominated feasible candidates."),
    "preference_status": (("engine.preference.fit_preference_model",), True, "Collect gated held-out comparisons if not validated."),
    "backup_status": (("BackupService.inspect",), False, "Create or verify a current snapshot."),
}


@dataclass(frozen=True, slots=True)
class AssistantRequest:
    intent: str
    subject_id: str | None = None
    facts: Mapping[str, Any] = field(default_factory=dict)
    calculations: Mapping[str, Any] = field(default_factory=dict)
    evidence: Mapping[str, Any] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssistantPacket:
    intent: str
    subject_id: str | None
    status: str
    tool_plan: tuple[str, ...]
    facts: Mapping[str, Any]
    calculations: Mapping[str, Any]
    evidence: Mapping[str, Any]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    next_action: str

    def canonical_bytes(self) -> bytes:
        payload = {
            "assumptions": list(self.assumptions),
            "calculations": self.calculations,
            "canonicalization": {
                "array_order": "preserved",
                "decimal_places": 6,
                "float_encoding": "decimal_string",
                "object_key_order": "lexicographic",
                "revision": _REVISION,
            },
            "evidence": self.evidence,
            "facts": self.facts,
            "intent": self.intent,
            "limitations": list(self.limitations),
            "next_action": self.next_action,
            "status": self.status,
            "subject_id": self.subject_id,
            "tool_plan": list(self.tool_plan),
        }
        canonical = _canonical_value(payload)
        return json.dumps(
            canonical,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @property
    def payload_sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        payload = cast(dict[str, Any], json.loads(self.canonical_bytes()))
        payload["payload_sha256"] = self.payload_sha256
        return payload


def build_assistant_packet(request: AssistantRequest) -> AssistantPacket:
    intent = _normalize_intent(request.intent)
    specification = _INTENTS.get(intent)
    if specification is None:
        return _bounded_packet(
            intent=intent,
            subject_id=None,
            status="refused",
            next_action=(
                "Choose a supported intent: " + ", ".join(sorted(_INTENTS)) + "."
            ),
            limitation="Unsupported free-form scientific claims are not generated.",
        )

    tool_plan, subject_required, next_action = specification
    subject_id = request.subject_id.strip() if request.subject_id else None
    if subject_required and not subject_id:
        return _bounded_packet(
            intent=intent,
            subject_id=None,
            status="needs_input",
            next_action=f"Provide a subject_id for the {intent} intent.",
            limitation="No subject-specific claim was evaluated.",
        )

    evidence = dict(request.evidence)
    evidence.setdefault(
        "assistant_claim",
        {
            "basis": "Deterministic intent routing and caller-supplied typed state only.",
            "classification": "EXACT",
            "source": "app.services.lab_assistant",
        },
    )
    return AssistantPacket(
        intent=intent,
        subject_id=subject_id,
        status="ready",
        tool_plan=tool_plan,
        facts=dict(request.facts),
        calculations=dict(request.calculations),
        evidence=evidence,
        assumptions=tuple(str(value) for value in request.assumptions),
        limitations=tuple(str(value) for value in request.limitations),
        next_action=next_action,
    )


def _bounded_packet(
    *,
    intent: str,
    subject_id: str | None,
    status: str,
    next_action: str,
    limitation: str,
) -> AssistantPacket:
    return AssistantPacket(
        intent=intent,
        subject_id=subject_id,
        status=status,
        tool_plan=(),
        facts={},
        calculations={},
        evidence={
            "assistant_claim": {
                "basis": "No supported deterministic claim was evaluated.",
                "classification": "UNKNOWN",
                "source": "app.services.lab_assistant",
            }
        },
        assumptions=(),
        limitations=(limitation,),
        next_action=next_action,
    )


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical assistant packets reject non-finite numbers")
        decimal = Decimal(str(value)).quantize(_DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN)
        if decimal == 0:
            decimal = abs(decimal)
        return format(decimal, ".6f")
    if isinstance(value, Decimal):
        decimal = value.quantize(_DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN)
        return format(decimal, ".6f")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise TypeError(f"Unsupported canonical packet value: {type(value).__name__}")


def _normalize_intent(value: str) -> str:
    return "_".join(value.strip().casefold().replace("-", " ").split())


__all__ = ["AssistantPacket", "AssistantRequest", "build_assistant_packet"]
