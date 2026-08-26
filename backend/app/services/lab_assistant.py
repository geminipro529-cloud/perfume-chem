"""Deterministic, claim-bounded assistant packets for the local lab."""

from __future__ import annotations

import json
import re
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
    "reference_formulation": (
        ("InventoryService.live_stock", "ReferenceContract.resolve", "PerfumeWorkbench.analyze"),
        False,
        "Resolve the named reference as an architecture-only contract, then formulate from live inventory.",
    ),
    "purchase_gap_analysis": (
        ("InventoryService.live_stock", "FormulaCorpus.coverage"),
        False,
        "Rank purchases by buildable-family coverage, substitution value, and evidence quality.",
    ),
    "family_gap_analysis": (
        ("InventoryService.live_stock", "FormulaCorpus.coverage"),
        False,
        "Compare inventory-buildable families with the formula corpus before proposing new briefs.",
    ),
    "finished_batch_rescue": (
        ("LabService.reconstruct_bottle", "PerfumeWorkbench.plan_intervention_trial"),
        True,
        "Provide the immutable bottle ledger and exact stock record; test a separate aliquot first.",
    ),
    "performance_diagnosis": (
        ("PerfumeWorkbench.analyze",),
        True,
        "Diagnose the measured formula and evaluation conditions before proposing an addition-only trial.",
    ),
    "perfume_knowledge_question": (
        (),
        False,
        "Answer with source-bounded perfume evidence and clearly separate measurements from hypotheses.",
    ),
}


@dataclass(frozen=True, slots=True)
class IntentClassification:
    intent: str
    matched_rule: str


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
    raw_intent = request.intent.strip()
    intent = _normalize_intent(raw_intent)
    specification = _INTENTS.get(intent)
    routed: IntentClassification | None = None
    if specification is None:
        routed = classify_chat_intent(raw_intent)
        if routed is not None:
            intent = routed.intent
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
    facts = dict(request.facts)
    if routed is not None:
        facts.setdefault("chat_request", raw_intent)
        evidence.setdefault(
            "intent_routing",
            {
                "basis": f"Deterministic lexical rule: {routed.matched_rule}.",
                "classification": "EXACT",
                "source": "app.services.lab_assistant.classify_chat_intent",
            },
        )
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
        facts=facts,
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


def classify_chat_intent(text: str) -> IntentClassification | None:
    """Classify common perfume chat requests without invoking a model.

    Ordering is deliberate: an addition-only rescue request wins over a
    reference-formulation phrase, and unsupported guarantees are refused
    before any scientific route is selected.
    """
    query = re.sub(r"\s+", " ", str(text or "").strip().casefold())
    if not query:
        return None

    guarantee = (
        r"\b(?:prove|guarantee|certify)\b.*\b(?:safe|last|performance|"
        r"dopamine|serotonin|oxytocin|neurotransmitter)\b"
    )
    if re.search(guarantee, query) or re.search(
        r"\bwill\s+last\s+\d+\s*(?:h|hr|hrs|hours)\b", query
    ):
        return None

    rescue_terms = (
        r"\b(?:save|salvage|rescue|fix|improve|finish|finished|already mixed|"
        r"existing batch|source bottle|how much (?:should i )?add|additions? only)\b"
    )
    if re.search(rescue_terms, query):
        return IntentClassification("finished_batch_rescue", "addition_only_rescue")

    if re.search(
        r"\b(?:what|which).{0,35}\b(?:buy|purchase|ingredient|material)s?\b",
        query,
    ) or re.search(r"\bnext best (?:ingredient|material)s?\b", query):
        return IntentClassification("purchase_gap_analysis", "purchase_gap")

    if re.search(
        r"\b(?:famil(?:y|ies)|types? of perfume).{0,50}\b(?:not|haven't|missing|gap|made)\b",
        query,
    ) or re.search(r"\bwhat (?:family|families|types).{0,30}(?:make|try) next\b", query):
        return IntentClassification("family_gap_analysis", "family_gap")

    if re.search(
        r"\b(?:weak|poor projection|no projection|doesn't.{0,40}last|"
        r"does not.{0,40}last|"
        r"performance|sillage|longevity|fades? too fast)\b",
        query,
    ):
        return IntentClassification("performance_diagnosis", "performance_problem")

    if re.search(
        r"\b(?:make|create|design|formulate|reconstruct|version of|similar to|"
        r"inspired by|luxury version)\b",
        query,
    ):
        return IntentClassification("reference_formulation", "formulation_or_reference")

    if re.search(r"\b(?:safe|ifra|allergen|skin use)\b", query):
        return IntentClassification("safety_assessment", "safety_question")

    if re.search(r"\b(?:analy[sz]e|diagnose|what is wrong|why did).{0,80}\b", query):
        return IntentClassification("formula_analysis", "formula_analysis")

    if "perfume" in query or "fragrance" in query or "oav" in query or "odt" in query:
        return IntentClassification("perfume_knowledge_question", "general_perfume_question")
    return None


__all__ = [
    "AssistantPacket",
    "AssistantRequest",
    "IntentClassification",
    "build_assistant_packet",
    "classify_chat_intent",
]
