"""Compact, hash-bound projections of native complexity decisions.

The card contract is intentionally narrower than the native scientific outputs.
It carries one decision into a model prompt without copying a full diagnostic
dump or granting sensory, formula, inventory, safety, or release authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_CARD_BYTES = 1600


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value.strip()


class DecisionCardState(str, Enum):
    DECIDE = "DECIDE"
    HOLD = "HOLD"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class DecisionCard:
    module_id: str
    decision_kind: str
    state: DecisionCardState
    decision_question: str
    decisive_evidence: tuple[str, ...]
    preserve: str
    reject: str
    controlled_comparison: str
    claim_ceiling: str
    source_result_sha256: str

    def __post_init__(self) -> None:
        for field_name in (
            "module_id",
            "decision_kind",
            "decision_question",
            "preserve",
            "reject",
            "controlled_comparison",
            "claim_ceiling",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.state, DecisionCardState):
            raise TypeError("state must be a DecisionCardState")
        if not isinstance(self.decisive_evidence, tuple):
            raise TypeError("decisive_evidence must be a tuple")
        if not 1 <= len(self.decisive_evidence) <= 3:
            raise ValueError(
                "decisive_evidence must contain one to three facts; "
                "at most three are allowed"
            )
        normalized_evidence = tuple(
            _text(item, "decisive_evidence item") for item in self.decisive_evidence
        )
        object.__setattr__(self, "decisive_evidence", normalized_evidence)
        if not isinstance(self.source_result_sha256, str) or _SHA256_RE.fullmatch(
            self.source_result_sha256
        ) is None:
            raise ValueError("source_result_sha256 must be a lowercase SHA-256 digest")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "complexity_decision_card_v1",
            "module_id": self.module_id,
            "decision_kind": self.decision_kind,
            "state": self.state.value,
            "decision_question": self.decision_question,
            "decisive_evidence": list(self.decisive_evidence),
            "preserve": self.preserve,
            "reject": self.reject,
            "controlled_comparison": self.controlled_comparison,
            "claim_ceiling": self.claim_ceiling,
            "source_result_sha256": self.source_result_sha256,
        }

    def to_json_bytes(self) -> bytes:
        encoded = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > _MAX_CARD_BYTES:
            raise ValueError("decision card exceeds 1600 UTF-8 bytes")
        return encoded

    @property
    def card_sha256(self) -> str:
        return hashlib.sha256(self.to_json_bytes()).hexdigest()


Projector = Callable[[Mapping[str, Any], str], DecisionCard]


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _items(value: object) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return (value,)
    return tuple(value)


def _brief(value: object, *, limit: int = 240) -> str:
    text = " ".join(str(value).split())
    if not text:
        return "not supplied"
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _source_hash(native_result: Mapping[str, Any]) -> str:
    digest = native_result.get("result_sha256")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ValueError("native result_sha256 must be a lowercase SHA-256 digest")
    return digest


def _claim_ceiling(native_result: Mapping[str, Any]) -> str:
    value = native_result.get("claim_ceiling", "COMPUTATIONAL_DESIGN_ONLY")
    return _text(value, "claim_ceiling")


def _card(
    native_result: Mapping[str, Any],
    *,
    module_id: str,
    decision_kind: str,
    state: DecisionCardState,
    decision_question: str,
    decisive_evidence: tuple[str, ...],
    preserve: str,
    reject: str,
    controlled_comparison: str,
) -> DecisionCard:
    return DecisionCard(
        module_id=module_id,
        decision_kind=decision_kind,
        state=state,
        decision_question=decision_question,
        decisive_evidence=decisive_evidence,
        preserve=preserve,
        reject=reject,
        controlled_comparison=controlled_comparison,
        claim_ceiling=_claim_ceiling(native_result),
        source_result_sha256=_source_hash(native_result),
    )


def _construction_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    axes = _mapping(native_result.get("axes", {}), "construction axes")
    useful: list[tuple[str, Mapping[str, Any]]] = []
    for axis_id, raw in axes.items():
        axis = _mapping(raw, f"construction axis {axis_id}")
        if axis_id == "formula_structure" or axis.get("status") != "AVAILABLE":
            continue
        useful.append((str(axis_id), axis))
    if useful:
        axis_id, axis = useful[0]
        evidence = (f"{axis_id}: {_brief(axis.get('interpretation'))}",)
        state = DecisionCardState.DECIDE
    else:
        evidence = (
            "No target-linked construction relation is available; row accounting is not perceptual depth.",
        )
        state = DecisionCardState.HOLD
    return _card(
        native_result,
        module_id="construction_profile",
        decision_kind="TARGET_DEFINING_RELATION",
        state=state,
        decision_question="Which single supported relation creates the target's depth, and what is lost if it disappears?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="Do not infer richness from ingredient count, row count, or unavailable axes.",
        controlled_comparison="full design versus one target-defining relation omitted at matched dose",
    )


def _expansion_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    candidate: Mapping[str, Any] | None = None
    for raw in _items(native_result.get("pareto_frontier")):
        row = _mapping(raw, "expansion frontier item")
        if (
            str(row.get("origin", "")).startswith("NEW")
            and row.get("mechanism_contract")
            and row.get("first_discriminator")
        ):
            candidate = row
            break
    if candidate is None:
        evidence = (
            "No frontier item establishes a distinct mechanism and first discriminator beyond the current design.",
        )
        state = DecisionCardState.NONE
    else:
        evidence = (
            f"move: {_brief(candidate.get('title'))}",
            f"mechanism: {_brief(candidate.get('mechanism_contract'))}",
            f"first discriminator: {_brief(candidate.get('first_discriminator'))}",
        )
        state = DecisionCardState.DECIDE
    return _card(
        native_result,
        module_id="complexity_expansion",
        decision_kind="MINIMUM_NONREDUNDANT_MOVE",
        state=state,
        decision_question="What is the minimum nonredundant move that adds target-linked depth, or is NONE better?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="Do not reward novelty, frontier size, or decorative complication.",
        controlled_comparison="strongest current design versus one isolated frontier move",
    )


def _musk_card(native_result: Mapping[str, Any], target_identity: str) -> DecisionCard:
    issues = tuple(_brief(item) for item in _items(native_result.get("issue_codes")))
    selected = tuple(
        _mapping(item, "selected musk") for item in _items(native_result.get("selected"))
    )
    if str(native_result.get("state", "")).upper() == "HOLD" or issues:
        evidence = tuple(f"hold: {item}" for item in issues[:3]) or (
            "No complete target-linked musk decision is available.",
        )
        state = DecisionCardState.HOLD
    elif selected:
        first = selected[0]
        evidence = (
            "strongest single: "
            f"{_brief(first.get('material'))} | {_brief(first.get('role'))} | "
            f"{_brief(first.get('target_function'))}",
        )
        if len(selected) > 1:
            second = selected[1]
            evidence += (
                f"proposed distinct layer: {_brief(second.get('material'))} | {_brief(second.get('role'))}",
            )
        state = DecisionCardState.DECIDE
    else:
        evidence = ("Zero musk is the current strongest sparse architecture.",)
        state = DecisionCardState.NONE
    return _card(
        native_result,
        module_id="musk_design_restraint",
        decision_kind="STRONGEST_SINGLE_MUSK",
        state=state,
        decision_question="Does one exact musk own the required role, or does a second layer add a truly distinct function?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject=(
            "Keep Tonalide, Macrolide, and Musk Ketone out unless a complete exception "
            "beats admitted alternatives; never reward musk count."
        ),
        controlled_comparison="zero-musk, strongest-single-musk, omission, and strongest nonredundant alternative",
    )


def _admission_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    failures = tuple(
        _brief(item)
        for key in ("gate_failures", "packet_failures", "oav_blockers")
        for item in _items(native_result.get(key))
    )
    state_text = _brief(native_result.get("state", "HOLD"))
    scope = _brief(native_result.get("claim_scope", "unspecified scope"))
    if failures or "HOLD" in state_text or "REJECT" in state_text:
        evidence = tuple(f"failed gate: {item}" for item in failures[:3]) or (
            f"admission state: {state_text}",
        )
        state = DecisionCardState.HOLD
    else:
        evidence = (f"exact scope: {scope}; admission state: {state_text}",)
        state = DecisionCardState.DECIDE
    return _card(
        native_result,
        module_id="model_admission",
        decision_kind="EXACT_SCOPE_ADMISSION",
        state=state,
        decision_question="For this exact claim scope, is the model ADMIT, HOLD, or REJECT?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="A design-scope pass cannot imply formula, sensory, safety, or release authority.",
        controlled_comparison="required exact-scope gates versus the first failed or missing gate",
    )


def _lifecycle_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    lifecycle_state = _brief(native_result.get("state", "INSUFFICIENT_DATA"))
    release = _brief(native_result.get("release_sha256", native_result.get("card_sha256")))
    scope = _brief(native_result.get("calibration_scope", "unspecified scope"))
    blockers = tuple(_brief(item) for item in _items(native_result.get("blockers")))
    evidence = (
        f"release: {release[:12]}; calibration scope: {scope}",
        f"lifecycle evidence: {lifecycle_state}",
    )
    if blockers:
        evidence += (f"decisive blocker: {blockers[0]}",)
    state = (
        DecisionCardState.DECIDE
        if lifecycle_state == "WITHIN_DECLARED_TOLERANCE"
        and native_result.get("computation_allowed") is True
        else DecisionCardState.HOLD
    )
    return _card(
        native_result,
        module_id="model_lifecycle",
        decision_kind="RELEASE_LIFECYCLE_ACTION",
        state=state,
        decision_question="Should this exact release and scope be RETAINED, QUARANTINED, SUPERSEDED, or ROLLED BACK?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="Do not transfer authority across release, data, preprocessing, endpoint, or scope changes.",
        controlled_comparison="current release versus exact predecessor on the same held-out scope",
    )


def _within_sniff_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    failures = tuple(_brief(item) for item in _items(native_result.get("failures")))
    evidence = (
        f"design state: {_brief(native_result.get('state'))}",
        f"pulse count: {_brief(native_result.get('pulse_count'))}; onset span ms: {_brief(native_result.get('onset_span_ms'))}",
    )
    if failures:
        evidence += (f"failure: {failures[0]}",)
    state = DecisionCardState.HOLD if failures else DecisionCardState.DECIDE
    return _card(
        native_result,
        module_id="within_sniff",
        decision_kind="APPARATUS_INTERPRETABILITY",
        state=state,
        decision_question="Is the pulse-order design interpretable at design scope, and what prevents an observed-effect claim?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="A passing design is not an observed perfume effect.",
        controlled_comparison="counterbalanced pulse order with qualified apparatus and matched delivered-mass receipts",
    )


def _temporal_card(
    native_result: Mapping[str, Any], target_identity: str
) -> DecisionCard:
    cells = tuple(
        _mapping(item, "temporal observed cell")
        for item in _items(native_result.get("observed_cells"))
    )
    blockers = tuple(_brief(item) for item in _items(native_result.get("blockers")))
    facts: list[str] = []
    for cell in cells[:2]:
        fact = f"{_brief(cell.get('timepoint'))}={_brief(cell.get('value'))}"
        dominant = cell.get("dominant_system")
        if dominant is not None:
            fact += f" ({_brief(dominant)})"
        facts.append(fact)
    missing = tuple(_brief(item) for item in _items(native_result.get("missing_cells")))
    if missing and len(facts) < 3:
        facts.append("missing: " + ", ".join(missing))
    disagreement = native_result.get("disagreement")
    if disagreement and len(facts) < 3:
        facts.append("disagreement: " + _brief(disagreement))
    if blockers and len(facts) < 3:
        facts.append("blocker: " + blockers[0])
    if not facts:
        facts.append("No source-bound observed time cells were supplied.")
    state = DecisionCardState.DECIDE if cells and not blockers else DecisionCardState.HOLD
    return _card(
        native_result,
        module_id="temporal_observations",
        decision_kind="OBSERVED_TIME_CELLS",
        state=state,
        decision_question="Which additional observed time cell would distinguish the competing temporal accounts?",
        decisive_evidence=tuple(facts),
        preserve=target_identity,
        reject="Do not interpolate a smooth narrative, dominance handoff, or longevity claim between observed cells.",
        controlled_comparison="same sample, fixed substrate and dose, preregistered missing time cell, participant-level repeats",
    )


def _order_card(native_result: Mapping[str, Any], target_identity: str) -> DecisionCard:
    failures = tuple(_brief(item) for item in _items(native_result.get("failures")))
    state_text = _brief(native_result.get("state", "REBUILD"))
    evidence = tuple(failures[:3]) or (f"order-balance state: {state_text}",)
    state = (
        DecisionCardState.DECIDE
        if state_text == "PASS_FOR_DESIGN" and not failures
        else DecisionCardState.HOLD
    )
    return _card(
        native_result,
        module_id="order_balance",
        decision_kind="POSITION_CARRYOVER_BALANCE",
        state=state,
        decision_question="Are first position and immediate predecessor carryover balanced, or must the schedule be rebuilt?",
        decisive_evidence=evidence,
        preserve=target_identity,
        reject="Balance does not authorize allocation, washout adequacy, execution, or inference.",
        controlled_comparison="first-position counts and every directed immediate-predecessor pair count",
    )


def _panel_card(native_result: Mapping[str, Any], target_identity: str) -> DecisionCard:
    decision = _brief(native_result.get("decision", "hold")).casefold()
    estimand = _brief(native_result.get("estimand", target_identity))
    blockers = tuple(_brief(item) for item in _items(native_result.get("blockers")))
    evidence = [f"estimand: {estimand}; pleasantness remains a separate endpoint"]
    failed = tuple(_brief(item) for item in _items(native_result.get("failed_gates")))
    inconclusive = tuple(
        _brief(item) for item in _items(native_result.get("inconclusive_gates"))
    )
    if failed:
        evidence.append("failed gates: " + ", ".join(failed))
    elif inconclusive:
        evidence.append("inconclusive gates: " + ", ".join(inconclusive))
    if blockers and len(evidence) < 3:
        evidence.append("blocker: " + blockers[0])
    state = DecisionCardState.DECIDE if decision == "go" and not blockers else DecisionCardState.HOLD
    return _card(
        native_result,
        module_id="panel_contract",
        decision_kind="ESTIMAND_AND_CLAIM_CEILING",
        state=state,
        decision_question="What is the exact estimand, and which independent panel gate limits the claim?",
        decisive_evidence=tuple(evidence),
        preserve=target_identity,
        reject="Pleasantness cannot compensate for failed discrimination, agreement, repeatability, or target recognition.",
        controlled_comparison="preregistered estimand with separate construction, target-fidelity, and liking endpoints",
    )


_PROJECTORS: dict[str, Projector] = {
    "construction_profile": _construction_card,
    "complexity_expansion": _expansion_card,
    "musk_design_restraint": _musk_card,
    "model_admission": _admission_card,
    "model_lifecycle": _lifecycle_card,
    "within_sniff": _within_sniff_card,
    "temporal_observations": _temporal_card,
    "order_balance": _order_card,
    "panel_contract": _panel_card,
}


def build_decision_card(
    module_id: str,
    native_result: Mapping[str, Any],
    target_identity: str,
) -> DecisionCard:
    """Project one native result into one bounded decision-changing card."""

    normalized_module = _text(module_id, "module_id")
    projector = _PROJECTORS.get(normalized_module)
    if projector is None:
        raise ValueError(f"unsupported decision-card module: {normalized_module}")
    result = _mapping(native_result, "native_result")
    _source_hash(result)
    return projector(result, _text(target_identity, "target_identity"))


__all__ = ["DecisionCard", "DecisionCardState", "build_decision_card"]
