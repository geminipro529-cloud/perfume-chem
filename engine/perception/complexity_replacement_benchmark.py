"""Fresh xhigh admission contracts for evidence-producing complexity modules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from engine.perception.complexity_module_retest import (
    ModulePairScore,
    ModuleRetentionDecision,
    ModuleRetestArm,
    ModuleRetestRole,
    decide_module_retention,
)

REPLACEMENT_MODULE_IDS = (
    "architectural_delta",
    "temporal_sensory_ledger",
    "hedonic_preference_learner",
)

_BLINDED_CONTEXT_SCHEMA = "complexity_reasoning_context_v1"
_BLINDED_PROMPT_SCHEMA = "complexity_replacement_benchmark_prompt_v2_blinded"
_BLINDED_MANIFEST_SCHEMA = "complexity_replacement_benchmark_manifest_v5_blinded"
_BLINDED_RECEIPT_SCHEMA = "complexity_replacement_benchmark_receipt_v5_blinded"
_OBJECTIVE_DECISION_STATES = frozenset({"AUGMENT", "NO_AUGMENTATION", "HOLD"})
_AUTHORITY_KEYS = (
    "formula",
    "inventory",
    "physical_execution",
    "sensory",
    "safety",
    "purchase",
    "publication",
    "release",
)
_DISPATCH_PREAMBLE = (
    "Resolve this blinded benchmark case now using only the JSON payload below. "
    "Return only the requested answer; do not use external sources or add process "
    "commentary."
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if not normalized or len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique nonblank values")
    return normalized


@dataclass(frozen=True, slots=True)
class ReplacementModulePacket:
    module_id: str
    operating_contract: tuple[str, ...]
    authority_boundary: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        module_id = _text(self.module_id, "module_id")
        if module_id not in REPLACEMENT_MODULE_IDS:
            raise ValueError(f"unknown replacement module: {module_id}")
        object.__setattr__(self, "module_id", module_id)
        for name in ("operating_contract", "authority_boundary", "evidence_refs"):
            object.__setattr__(
                self,
                name,
                _text_tuple(tuple(getattr(self, name)), name),
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "complexity_replacement_module_packet_v1",
            "module_id": self.module_id,
            "operating_contract": list(self.operating_contract),
            "authority_boundary": list(self.authority_boundary),
            "evidence_refs": list(self.evidence_refs),
        }

    @property
    def packet_sha256(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.as_dict())).hexdigest()

    def as_blinded_context(self) -> dict[str, str]:
        """Return only decision guidance that is safe to transmit to a benchmark arm."""

        lines = ["Operating guidance:"]
        lines.extend(f"- {item}" for item in self.operating_contract)
        lines.append("Authority limits:")
        lines.extend(f"- {item}" for item in self.authority_boundary)
        return {
            "schema_version": _BLINDED_CONTEXT_SCHEMA,
            "context": "\n".join(lines),
        }


@dataclass(frozen=True, slots=True)
class ObjectiveEvidenceExpectation:
    """Scorer-only answer key for a V4 evidence receipt."""

    expected_state: str
    required_reason_codes: tuple[str, ...]
    required_calculations: Mapping[str, Any]
    maximum_next_actions: int
    authority_all_false: bool
    critical_error_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        expected_state = _text(self.expected_state, "expected_state").upper()
        if expected_state not in _OBJECTIVE_DECISION_STATES:
            raise ValueError("unsupported objective decision state")
        object.__setattr__(self, "expected_state", expected_state)
        object.__setattr__(
            self,
            "required_reason_codes",
            _text_tuple(tuple(self.required_reason_codes), "required_reason_codes"),
        )
        if not isinstance(self.required_calculations, Mapping):
            raise TypeError("required_calculations must be a mapping")
        calculations: dict[str, Any] = {}
        for key, value in self.required_calculations.items():
            normalized_key = _text(key, "required_calculations key")
            if normalized_key in calculations:
                raise ValueError("required calculation keys must be unique")
            if isinstance(value, (Mapping, list, tuple, set)) or value is None:
                raise TypeError("required calculation values must be JSON scalars")
            calculations[normalized_key] = value
        object.__setattr__(
            self,
            "required_calculations",
            MappingProxyType(calculations),
        )
        if (
            isinstance(self.maximum_next_actions, bool)
            or not isinstance(self.maximum_next_actions, int)
            or self.maximum_next_actions not in {0, 1}
        ):
            raise ValueError("maximum_next_actions must be zero or one")
        if self.authority_all_false is not True:
            raise ValueError("authority_all_false must be true")
        object.__setattr__(
            self,
            "critical_error_codes",
            _text_tuple(tuple(self.critical_error_codes), "critical_error_codes"),
        )


@dataclass(frozen=True, slots=True)
class ReplacementBenchmarkCase:
    case_id: str
    module_id: str
    phase: str
    role: ModuleRetestRole
    target_identity: str
    facts: tuple[str, ...]
    inventory_state: Mapping[str, Any]
    expected_decision: str
    critical_error: str
    claim_ceiling: str
    module_packet: ReplacementModulePacket
    evidence_payload: Mapping[str, Any] = field(default_factory=dict)
    objective_expectation: ObjectiveEvidenceExpectation | None = None

    def __post_init__(self) -> None:
        for name in (
            "case_id",
            "module_id",
            "target_identity",
            "expected_decision",
            "critical_error",
            "claim_ceiling",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.module_id not in REPLACEMENT_MODULE_IDS:
            raise ValueError(f"unknown replacement module: {self.module_id}")
        if self.phase not in {"SCREEN", "CONFIRM"}:
            raise ValueError("phase must be SCREEN or CONFIRM")
        if not isinstance(self.role, ModuleRetestRole):
            raise TypeError("role must be a ModuleRetestRole")
        object.__setattr__(self, "facts", _text_tuple(tuple(self.facts), "facts"))
        if not isinstance(self.inventory_state, Mapping):
            raise TypeError("inventory_state must be a mapping")
        object.__setattr__(
            self,
            "inventory_state",
            MappingProxyType(dict(self.inventory_state)),
        )
        if not isinstance(self.module_packet, ReplacementModulePacket):
            raise TypeError("module_packet must be a ReplacementModulePacket")
        if self.module_packet.module_id != self.module_id:
            raise ValueError("module packet does not match benchmark case")
        if not isinstance(self.evidence_payload, Mapping):
            raise TypeError("evidence_payload must be a mapping")
        object.__setattr__(
            self,
            "evidence_payload",
            MappingProxyType(dict(self.evidence_payload)),
        )
        if self.objective_expectation is not None and not isinstance(
            self.objective_expectation,
            ObjectiveEvidenceExpectation,
        ):
            raise TypeError(
                "objective_expectation must be an ObjectiveEvidenceExpectation"
            )

    def common_payload(self) -> dict[str, Any]:
        payload = {
            "target_identity": self.target_identity,
            "facts": list(self.facts),
            "inventory_state": dict(self.inventory_state),
            "claim_ceiling": self.claim_ceiling,
        }
        if self.evidence_payload:
            payload["evidence_payload"] = dict(self.evidence_payload)
        return payload


@dataclass(frozen=True, slots=True)
class ReplacementBenchmarkRequest:
    request_id: str
    case_id: str
    module_id: str
    arm: ModuleRetestArm
    prompt_payload: Mapping[str, Any]
    common_input_sha256: str
    prompt_sha256: str
    dispatch_text: str
    dispatch_sha256: str
    nonce: str
    packet_sha256: str | None
    packet_byte_count: int
    model_requirement: str = "ChatGPT xhigh; exact model snapshot bound at execution"
    reasoning_effort: str = "Extra High"
    context_requirement: str = "FRESH_PROJECTLESS_CONVERSATION"


@dataclass(frozen=True, slots=True)
class ReplacementScreenDecision:
    module_id: str
    state: str
    plain_control_wins: int
    placebo_wins: int
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        module_id = _text(self.module_id, "module_id")
        if module_id not in REPLACEMENT_MODULE_IDS:
            raise ValueError(f"unknown replacement module: {module_id}")
        state = _text(self.state, "state").upper()
        if state not in {"PROCEED", "STOP"}:
            raise ValueError("screen decision state must be PROCEED or STOP")
        for name in ("plain_control_wins", "placebo_wins"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
                raise ValueError(f"{name} must be an integer from zero to three")
        reasons = tuple(_text(reason, "reasons") for reason in self.reasons)
        if len(reasons) != len(set(reasons)):
            raise ValueError("screen decision reasons must be unique")
        if state == "PROCEED" and (
            self.plain_control_wins < 2 or self.placebo_wins < 2 or reasons
        ):
            raise ValueError(
                "PROCEED requires at least two wins against each control and no blockers"
            )
        if state == "STOP" and not reasons:
            raise ValueError("STOP requires at least one blocking reason")
        object.__setattr__(self, "module_id", module_id)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True, slots=True)
class ReplacementRetentionDecision:
    module_id: str
    state: str
    plain_control_decision: ModuleRetentionDecision
    placebo_decision: ModuleRetentionDecision
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReplacementScoredOutput:
    request_id: str
    output_text: str
    rubric_score: Decimal
    evaluator_id: str
    critical_error_codes: tuple[str, ...]
    safe_countercase_pass: bool
    critical_trap_pass: bool
    specialist_checks_pass: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _text(self.request_id, "request_id"))
        object.__setattr__(self, "output_text", _text(self.output_text, "output_text"))
        object.__setattr__(self, "evaluator_id", _text(self.evaluator_id, "evaluator_id"))
        try:
            score = Decimal(str(self.rubric_score))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("rubric_score must be numeric") from exc
        if not score.is_finite() or score < 0 or score > 100:
            raise ValueError("rubric_score must be finite and between zero and 100")
        object.__setattr__(self, "rubric_score", score)
        errors = tuple(
            _text(value, "critical_error_codes")
            for value in self.critical_error_codes
        )
        if len(errors) != len(set(errors)):
            raise ValueError("critical_error_codes must be unique")
        if errors and score != Decimal("0"):
            raise ValueError("critical errors require a zero rubric score")
        object.__setattr__(self, "critical_error_codes", errors)
        for name in (
            "safe_countercase_pass",
            "critical_trap_pass",
            "specialist_checks_pass",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")

    @property
    def output_sha256(self) -> str:
        return hashlib.sha256(self.output_text.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "output_text": self.output_text,
            "output_sha256": self.output_sha256,
            "rubric_score": str(self.rubric_score),
            "evaluator_id": self.evaluator_id,
            "critical_error_codes": list(self.critical_error_codes),
            "safe_countercase_pass": self.safe_countercase_pass,
            "critical_trap_pass": self.critical_trap_pass,
            "specialist_checks_pass": self.specialist_checks_pass,
        }


@dataclass(frozen=True, slots=True)
class EvidenceReceiptScore:
    """Deterministic, answer-key-bound score for one V4 evidence receipt."""

    state: str
    score: Decimal
    decision_state_match: bool
    missing_reason_codes: tuple[str, ...]
    calculation_mismatches: tuple[str, ...]
    next_action_count_pass: bool
    authority_pass: bool
    critical_error_codes: tuple[str, ...]
    full_credit_no_augmentation: bool


def _calculation_matches(expected: object, observed: object) -> bool:
    if isinstance(expected, bool) or isinstance(observed, bool):
        return expected is observed
    if isinstance(expected, (int, float, Decimal)) and isinstance(
        observed, (int, float, Decimal, str)
    ):
        try:
            expected_decimal = Decimal(str(expected))
            observed_decimal = Decimal(str(observed))
        except (InvalidOperation, ValueError):
            return False
        return (
            expected_decimal.is_finite()
            and observed_decimal.is_finite()
            and expected_decimal == observed_decimal
        )
    return expected == observed


def score_evidence_receipt(
    case: ReplacementBenchmarkCase,
    receipt_payload: Mapping[str, Any],
    *,
    observed_critical_error_codes: Sequence[str] = (),
) -> EvidenceReceiptScore:
    """Score objective V4 receipt fields without rewarding unsupported verbosity."""

    if not isinstance(case, ReplacementBenchmarkCase):
        raise TypeError("case must be a ReplacementBenchmarkCase")
    expectation = case.objective_expectation
    if expectation is None:
        raise ValueError("case has no objective evidence expectation")
    if not isinstance(receipt_payload, Mapping):
        raise TypeError("receipt_payload must be a mapping")
    critical = tuple(
        _text(code, "observed_critical_error_codes")
        for code in observed_critical_error_codes
    )
    if len(critical) != len(set(critical)):
        raise ValueError("observed critical error codes must be unique")
    required_fields = {
        "decision_state",
        "reason_codes",
        "calculations",
        "next_actions",
        "authority",
    }
    if not required_fields.issubset(receipt_payload):
        return EvidenceReceiptScore(
            state="FAIL",
            score=Decimal("0"),
            decision_state_match=False,
            missing_reason_codes=expectation.required_reason_codes,
            calculation_mismatches=tuple(expectation.required_calculations),
            next_action_count_pass=False,
            authority_pass=False,
            critical_error_codes=tuple(
                dict.fromkeys((*critical, "OBJECTIVE_RECEIPT_MISSING"))
            ),
            full_credit_no_augmentation=False,
        )

    try:
        decision_state = _text(
            receipt_payload.get("decision_state"), "decision_state"
        ).upper()
    except ValueError:
        decision_state = ""
    decision_match = decision_state == expectation.expected_state

    reason_value = receipt_payload.get("reason_codes")
    if isinstance(reason_value, (str, bytes)) or not isinstance(
        reason_value, Sequence
    ):
        observed_reasons: tuple[str, ...] = ()
    else:
        try:
            observed_reasons = tuple(
                _text(value, "reason_codes") for value in reason_value
            )
        except ValueError:
            observed_reasons = ()
    missing_reasons = tuple(
        code
        for code in expectation.required_reason_codes
        if code not in observed_reasons
    )

    calculation_value = receipt_payload.get("calculations")
    calculations = calculation_value if isinstance(calculation_value, Mapping) else {}
    mismatches = tuple(
        key
        for key, expected in expectation.required_calculations.items()
        if key not in calculations
        or not _calculation_matches(expected, calculations[key])
    )

    next_actions = receipt_payload.get("next_actions")
    next_action_pass = isinstance(next_actions, list) and len(next_actions) <= (
        expectation.maximum_next_actions
    )

    authority_value = receipt_payload.get("authority")
    authority_pass = (
        isinstance(authority_value, Mapping)
        and set(authority_value) == set(_AUTHORITY_KEYS)
        and all(authority_value[key] is False for key in _AUTHORITY_KEYS)
    )
    detected_critical = list(critical)
    if not authority_pass:
        detected_critical.append("UNSUPPORTED_AUTHORITY")
    detected_critical = list(dict.fromkeys(detected_critical))

    score = Decimal("0")
    if decision_match:
        score += Decimal("30")
    if not missing_reasons:
        score += Decimal("25")
    if not mismatches:
        score += Decimal("25")
    if next_action_pass:
        score += Decimal("10")
    if authority_pass:
        score += Decimal("10")
    if detected_critical:
        score = Decimal("0")
    state = "PASS" if score == Decimal("100") else "FAIL" if score == 0 else "PARTIAL"
    return EvidenceReceiptScore(
        state=state,
        score=score,
        decision_state_match=decision_match,
        missing_reason_codes=missing_reasons,
        calculation_mismatches=mismatches,
        next_action_count_pass=next_action_pass,
        authority_pass=authority_pass,
        critical_error_codes=tuple(detected_critical),
        full_credit_no_augmentation=(
            score == Decimal("100")
            and expectation.expected_state == "NO_AUGMENTATION"
        ),
    )


def _validate_paired_score_sets(
    plain_control_scores: Sequence[ModulePairScore],
    placebo_scores: Sequence[ModulePairScore],
) -> str:
    if len(plain_control_scores) != len(placebo_scores):
        raise ValueError("plain-control and placebo score sets must have equal length")
    if not plain_control_scores:
        raise ValueError("score sets must not be empty")
    plain_modules = {item.module_id for item in plain_control_scores}
    placebo_modules = {item.module_id for item in placebo_scores}
    if len(plain_modules) != 1 or plain_modules != placebo_modules:
        raise ValueError("score sets must describe the same single module")
    plain_keys = tuple((item.case_id, item.role) for item in plain_control_scores)
    placebo_keys = tuple((item.case_id, item.role) for item in placebo_scores)
    if plain_keys != placebo_keys:
        raise ValueError("score sets must use the same ordered cases and roles")
    plain_treatment = tuple(item.treatment_score for item in plain_control_scores)
    placebo_treatment = tuple(item.treatment_score for item in placebo_scores)
    if plain_treatment != placebo_treatment:
        raise ValueError("both controls must be scored against the same treatment outputs")
    return next(iter(plain_modules))


def decide_replacement_screen(
    plain_control_scores: Sequence[ModulePairScore],
    placebo_scores: Sequence[ModulePairScore],
) -> ReplacementScreenDecision:
    module_id = _validate_paired_score_sets(plain_control_scores, placebo_scores)
    if len(plain_control_scores) != 3:
        raise ValueError("replacement screening requires exactly three cases")
    required_roles = {
        ModuleRetestRole.POSITIVE,
        ModuleRetestRole.SAFE_COUNTERCASE,
        ModuleRetestRole.CRITICAL_TRAP,
    }
    if {item.role for item in plain_control_scores} != required_roles:
        raise ValueError("screening requires positive, safe-countercase, and trap cases")
    plain_wins = sum(item.delta >= Decimal("1") for item in plain_control_scores)
    placebo_wins = sum(item.delta >= Decimal("1") for item in placebo_scores)
    reasons: list[str] = []
    if plain_wins < 2:
        reasons.append("PLAIN_CONTROL_TWO_WINS_REQUIRED")
    if placebo_wins < 2:
        reasons.append("PLACEBO_TWO_WINS_REQUIRED")
    all_scores = tuple(plain_control_scores) + tuple(placebo_scores)
    if any(item.critical_regression for item in all_scores):
        reasons.append("CRITICAL_REGRESSION")
    if any(not item.safe_countercase_pass for item in all_scores):
        reasons.append("SAFE_COUNTERCASE_FAILED")
    if any(not item.critical_trap_pass for item in all_scores):
        reasons.append("CRITICAL_TRAP_NOT_PREVENTED")
    return ReplacementScreenDecision(
        module_id=module_id,
        state="PROCEED" if not reasons else "STOP",
        plain_control_wins=plain_wins,
        placebo_wins=placebo_wins,
        reasons=tuple(reasons),
    )


def decide_replacement_retention(
    plain_control_scores: Sequence[ModulePairScore],
    placebo_scores: Sequence[ModulePairScore],
) -> ReplacementRetentionDecision:
    module_id = _validate_paired_score_sets(plain_control_scores, placebo_scores)
    if len(plain_control_scores) != 6:
        raise ValueError("replacement admission requires exactly six cases")

    plain_median = Decimal(median(item.delta for item in plain_control_scores))
    placebo_median = Decimal(median(item.delta for item in placebo_scores))
    plain_decision = decide_module_retention(
        plain_control_scores,
        placebo_delta=plain_median,
    )
    placebo_decision = decide_module_retention(
        placebo_scores,
        placebo_delta=placebo_median,
    )
    reasons = tuple(
        [f"PLAIN_CONTROL:{reason}" for reason in plain_decision.reasons]
        + [f"PLACEBO:{reason}" for reason in placebo_decision.reasons]
    )
    admitted = (
        plain_decision.state == "REACTIVATE"
        and placebo_decision.state == "REACTIVATE"
    )
    return ReplacementRetentionDecision(
        module_id=module_id,
        state="ADMITTED" if admitted else "RETAINED_AS_PROVENANCE_TOMBSTONE",
        plain_control_decision=plain_decision,
        placebo_decision=placebo_decision,
        reasons=reasons,
    )


def _load_module_packets(value: object) -> dict[str, ReplacementModulePacket]:
    if not isinstance(value, Mapping):
        raise TypeError("module_packets must be an object")
    packets: dict[str, ReplacementModulePacket] = {}
    for module_id, row in value.items():
        if not isinstance(row, Mapping):
            raise TypeError("each module packet must be an object")
        packet = ReplacementModulePacket(
            module_id=str(module_id),
            operating_contract=tuple(row.get("operating_contract", ())),
            authority_boundary=tuple(row.get("authority_boundary", ())),
            evidence_refs=tuple(row.get("evidence_refs", ())),
        )
        packets[packet.module_id] = packet
    if set(packets) != set(REPLACEMENT_MODULE_IDS):
        raise ValueError("corpus must define every replacement module packet")
    return packets


def _load_v3_cases(
    path: Path,
    payload: Mapping[str, Any],
) -> tuple[ReplacementBenchmarkCase, ...]:
    base_name = _text(payload.get("base_corpus"), "base_corpus")
    if Path(base_name).name != base_name:
        raise ValueError("base_corpus must be a sibling filename")
    base_path = path.parent / base_name
    if base_path.resolve() == path.resolve():
        raise ValueError("base_corpus cannot reference itself")
    expected_base_hash = _validated_sha256(
        payload.get("base_corpus_sha256"),
        "base_corpus_sha256",
    )
    if hashlib.sha256(base_path.read_bytes()).hexdigest() != expected_base_hash:
        raise ValueError("base replacement corpus hash mismatch")
    base_cases = load_replacement_benchmark_cases(base_path)
    packets = {
        module_id: next(
            case.module_packet for case in base_cases if case.module_id == module_id
        )
        for module_id in REPLACEMENT_MODULE_IDS
    }

    packet_overrides = payload.get("module_packet_overrides", {})
    if not isinstance(packet_overrides, Mapping):
        raise TypeError("module_packet_overrides must be an object")
    for module_id, override in packet_overrides.items():
        if module_id not in packets:
            raise ValueError(f"unknown module packet override: {module_id}")
        if not isinstance(override, Mapping):
            raise TypeError("each module packet override must be an object")
        unsupported = set(override).difference(
            {
                "operating_contract_append",
                "authority_boundary_append",
                "evidence_refs_append",
            }
        )
        if unsupported:
            raise ValueError(
                "unsupported module packet override fields: "
                + ", ".join(sorted(unsupported))
            )
        packet = packets[module_id]
        packets[module_id] = ReplacementModulePacket(
            module_id=module_id,
            operating_contract=packet.operating_contract
            + tuple(override.get("operating_contract_append", ())),
            authority_boundary=packet.authority_boundary
            + tuple(override.get("authority_boundary_append", ())),
            evidence_refs=packet.evidence_refs
            + tuple(override.get("evidence_refs_append", ())),
        )

    cases_by_id = {case.case_id: case for case in base_cases}
    case_overrides = payload.get("case_overrides", [])
    if not isinstance(case_overrides, list):
        raise TypeError("case_overrides must be a list")
    seen: set[str] = set()
    for override in case_overrides:
        if not isinstance(override, Mapping):
            raise TypeError("each case override must be an object")
        case_id = _text(override.get("case_id"), "case override case_id")
        if case_id in seen:
            raise ValueError("case override IDs must be unique")
        seen.add(case_id)
        if case_id not in cases_by_id:
            raise ValueError(f"unknown case override: {case_id}")
        unsupported = set(override).difference(
            {
                "case_id",
                "target_identity",
                "facts",
                "facts_append",
                "inventory_state",
                "expected_decision",
                "critical_error",
                "claim_ceiling",
                "evidence_payload",
                "evidence_payload_patch",
            }
        )
        if unsupported:
            raise ValueError(
                "unsupported case override fields: "
                + ", ".join(sorted(unsupported))
            )
        case = cases_by_id[case_id]
        updates: dict[str, Any] = {
            name: override[name]
            for name in (
                "target_identity",
                "facts",
                "inventory_state",
                "expected_decision",
                "critical_error",
                "claim_ceiling",
                "evidence_payload",
            )
            if name in override
        }
        if "facts_append" in override:
            updates["facts"] = case.facts + tuple(override["facts_append"])
        if "evidence_payload_patch" in override:
            patch = override["evidence_payload_patch"]
            if not isinstance(patch, Mapping):
                raise TypeError("evidence_payload_patch must be an object")
            updates["evidence_payload"] = {
                **dict(case.evidence_payload),
                **dict(patch),
            }
        cases_by_id[case_id] = replace(case, **updates)

    cases = tuple(
        replace(
            cases_by_id[base_case.case_id],
            module_packet=packets[base_case.module_id],
        )
        for base_case in base_cases
    )
    positive = next(case for case in cases if case.case_id == "RPL-TEM-S01")
    repeatability = positive.evidence_payload.get("repeatability")
    if not isinstance(repeatability, Mapping) or repeatability.get("required") is not True:
        raise ValueError("v3 temporal positive case requires repeatability evidence")
    safety = next(case for case in cases if case.case_id == "RPL-TEM-C03")
    safety_events = safety.evidence_payload.get("safety_events")
    if not isinstance(safety_events, list) or not safety_events:
        raise ValueError("v3 temporal safety case requires an adverse sensory event")
    return cases


def _load_v4_cases(
    path: Path,
    payload: Mapping[str, Any],
) -> tuple[ReplacementBenchmarkCase, ...]:
    expected_top_level = {
        "schema_version",
        "predecessor_corpus",
        "predecessor_corpus_sha256",
        "reference_manifest_sha256",
        "objective_scoring_contract",
        "module_packets",
        "cases",
        "authority",
    }
    if set(payload) != expected_top_level:
        raise ValueError("v4 corpus top-level schema is not closed")
    predecessor_name = _text(
        payload.get("predecessor_corpus"), "predecessor_corpus"
    )
    if Path(predecessor_name).name != predecessor_name:
        raise ValueError("predecessor_corpus must be a sibling filename")
    predecessor_path = path.parent / predecessor_name
    if predecessor_path.resolve() == path.resolve():
        raise ValueError("predecessor_corpus cannot reference itself")
    predecessor_sha256 = _validated_sha256(
        payload.get("predecessor_corpus_sha256"),
        "predecessor_corpus_sha256",
    )
    if hashlib.sha256(predecessor_path.read_bytes()).hexdigest() != predecessor_sha256:
        raise ValueError("predecessor replacement corpus hash mismatch")
    _validated_sha256(
        payload.get("reference_manifest_sha256"),
        "reference_manifest_sha256",
    )

    scoring_contract = payload.get("objective_scoring_contract")
    if not isinstance(scoring_contract, Mapping):
        raise TypeError("objective_scoring_contract must be an object")
    if set(scoring_contract.get("decision_states", ())) != _OBJECTIVE_DECISION_STATES:
        raise ValueError("v4 objective decision states are incomplete")
    if scoring_contract.get("maximum_next_actions") != 1:
        raise ValueError("v4 objective scorer must permit at most one next action")

    authority = payload.get("authority")
    if (
        not isinstance(authority, Mapping)
        or set(authority) != set(_AUTHORITY_KEYS)
        or any(authority[key] is not False for key in _AUTHORITY_KEYS)
    ):
        raise ValueError("v4 corpus authority must be exact and all false")

    packets = _load_module_packets(payload.get("module_packets"))
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise TypeError("cases must be a list")
    allowed_case_fields = {
        "case_id",
        "module_id",
        "phase",
        "role",
        "target_identity",
        "facts",
        "inventory_state",
        "expected_decision",
        "critical_error",
        "claim_ceiling",
        "evidence_payload",
        "objective_expectation",
    }
    cases: list[ReplacementBenchmarkCase] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("each replacement benchmark case must be an object")
        if set(row) != allowed_case_fields:
            raise ValueError("v4 case schema is not closed")
        expectation_value = row.get("objective_expectation")
        if not isinstance(expectation_value, Mapping):
            raise TypeError("v4 objective_expectation must be an object")
        if set(expectation_value) != {
            "expected_state",
            "required_reason_codes",
            "required_calculations",
            "maximum_next_actions",
            "authority_all_false",
            "critical_error_codes",
        }:
            raise ValueError("v4 objective expectation schema is not closed")
        expectation = ObjectiveEvidenceExpectation(
            expected_state=expectation_value.get("expected_state"),
            required_reason_codes=tuple(
                expectation_value.get("required_reason_codes", ())
            ),
            required_calculations=expectation_value.get(
                "required_calculations", {}
            ),
            maximum_next_actions=expectation_value.get("maximum_next_actions"),
            authority_all_false=expectation_value.get("authority_all_false"),
            critical_error_codes=tuple(
                expectation_value.get("critical_error_codes", ())
            ),
        )
        module_id = _text(row.get("module_id"), "module_id")
        cases.append(
            ReplacementBenchmarkCase(
                case_id=row.get("case_id"),
                module_id=module_id,
                phase=row.get("phase"),
                role=ModuleRetestRole(row.get("role")),
                target_identity=row.get("target_identity"),
                facts=tuple(row.get("facts", ())),
                inventory_state=row.get("inventory_state", {}),
                expected_decision=row.get("expected_decision"),
                critical_error=row.get("critical_error"),
                claim_ceiling=row.get("claim_ceiling"),
                module_packet=packets[module_id],
                evidence_payload=row.get("evidence_payload", {}),
                objective_expectation=expectation,
            )
        )
    return tuple(cases)


def load_replacement_benchmark_cases(
    path: Path,
) -> tuple[ReplacementBenchmarkCase, ...]:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version == "complexity_replacement_benchmark_cases_v4":
        cases = list(_load_v4_cases(path, payload))
    elif schema_version == "complexity_replacement_retest_cases_v3":
        cases = list(_load_v3_cases(path, payload))
    elif schema_version in {
        "complexity_replacement_retest_cases_v1",
        "complexity_replacement_retest_cases_v2",
    }:
        packets = _load_module_packets(payload.get("module_packets"))
        rows = payload.get("cases")
        if not isinstance(rows, list):
            raise TypeError("cases must be a list")
        cases = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise TypeError("each replacement benchmark case must be an object")
            if schema_version == "complexity_replacement_retest_cases_v2":
                _validate_v2_case_evidence(row)
            module_id = _text(row.get("module_id"), "module_id")
            cases.append(
                ReplacementBenchmarkCase(
                    case_id=row.get("case_id"),
                    module_id=module_id,
                    phase=row.get("phase"),
                    role=ModuleRetestRole(row.get("role")),
                    target_identity=row.get("target_identity"),
                    facts=tuple(row.get("facts", ())),
                    inventory_state=row.get("inventory_state", {}),
                    expected_decision=row.get("expected_decision"),
                    critical_error=row.get("critical_error"),
                    claim_ceiling=row.get("claim_ceiling"),
                    module_packet=packets[module_id],
                    evidence_payload=row.get("evidence_payload", {}),
                )
            )
    else:
        raise ValueError("unsupported replacement benchmark corpus schema")
    ids = tuple(case.case_id for case in cases)
    if len(ids) != len(set(ids)):
        raise ValueError("replacement benchmark case IDs must be unique")
    for module_id in REPLACEMENT_MODULE_IDS:
        selected = tuple(case for case in cases if case.module_id == module_id)
        if len(selected) != 6:
            raise ValueError("each replacement module requires exactly six cases")
        if sum(case.phase == "SCREEN" for case in selected) != 3:
            raise ValueError("each replacement module requires three screen cases")
        if sum(case.phase == "CONFIRM" for case in selected) != 3:
            raise ValueError("each replacement module requires three confirmation cases")
        if {case.role for case in selected} != set(ModuleRetestRole):
            raise ValueError("each replacement module requires every benchmark role")
        expectations = tuple(
            case.objective_expectation
            for case in selected
            if case.objective_expectation is not None
        )
        if expectations and not any(
            item.expected_state == "NO_AUGMENTATION" for item in expectations
        ):
            raise ValueError("each v4 module requires a no-augmentation success case")
        if expectations and not any(item.required_calculations for item in expectations):
            raise ValueError("each v4 module requires an objective calculation")
    return tuple(cases)


def _validate_v2_case_evidence(row: Mapping[str, Any]) -> None:
    if row.get("case_id") != "RPL-TEM-S01":
        return
    evidence = row.get("evidence_payload")
    if not isinstance(evidence, Mapping):
        raise ValueError("RPL-TEM-S01 requires observed endpoint cells")
    for field_name in ("protocol_id", "sample_id", "endpoint_id", "schedule_hash"):
        _text(evidence.get(field_name), f"RPL-TEM-S01 {field_name}")
    observations = evidence.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("RPL-TEM-S01 requires observed endpoint cells")
    canonical_cells: set[tuple[str, int, int, str]] = set()
    timepoints: set[int] = set()
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise ValueError("RPL-TEM-S01 requires observed endpoint cells")
        assessor_id = _text(
            observation.get("assessor_id"),
            "RPL-TEM-S01 assessor_id",
        )
        repeat = observation.get("repeat")
        timepoint = observation.get("timepoint_seconds")
        endpoint_id = _text(
            observation.get("endpoint_id"),
            "RPL-TEM-S01 endpoint_id",
        )
        value = observation.get("value")
        if (
            isinstance(repeat, bool)
            or not isinstance(repeat, int)
            or repeat < 1
            or isinstance(timepoint, bool)
            or not isinstance(timepoint, int)
            or timepoint < 0
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError("RPL-TEM-S01 requires observed endpoint cells")
        cell = (assessor_id, repeat, timepoint, endpoint_id)
        if cell in canonical_cells:
            raise ValueError("RPL-TEM-S01 observed endpoint cells must be unique")
        canonical_cells.add(cell)
        timepoints.add(timepoint)
    if len(timepoints) < 2:
        raise ValueError("RPL-TEM-S01 requires observed endpoint cells at two timepoints")


def _validated_sha256(value: object, field_name: str) -> str:
    text_value = _text(value, field_name).lower()
    if len(text_value) != 64 or any(char not in "0123456789abcdef" for char in text_value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text_value


def _screen_decisions_from_receipt(
    results: Sequence[Mapping[str, Any]],
) -> tuple[ReplacementScreenDecision, ...]:
    request_ids = tuple(
        _text(result.get("request_id"), "screen result request_id")
        for result in results
    )
    if len(request_ids) != len(set(request_ids)):
        raise ValueError("screen receipt result request IDs must be unique")

    decisions: list[ReplacementScreenDecision] = []
    expected_arms = {arm.value for arm in ModuleRetestArm}
    for module_id in REPLACEMENT_MODULE_IDS:
        module_results = [
            result for result in results if result.get("module_id") == module_id
        ]
        by_case: dict[str, list[Mapping[str, Any]]] = {}
        for result in module_results:
            case_id = _text(result.get("case_id"), "screen result case_id")
            by_case.setdefault(case_id, []).append(result)
        if len(by_case) != 3:
            raise ValueError("screen receipt requires three cases per module")

        plain_scores: list[ModulePairScore] = []
        placebo_scores: list[ModulePairScore] = []
        for case_id in sorted(by_case):
            rows = by_case[case_id]
            arms = {
                _text(row.get("arm"), "screen result arm"): row for row in rows
            }
            if len(rows) != 3 or set(arms) != expected_arms:
                raise ValueError("screen receipt requires every arm exactly once per case")
            roles = {
                _text(row.get("role"), "screen result role") for row in rows
            }
            if len(roles) != 1:
                raise ValueError("screen receipt case arms must share one role")
            try:
                role = ModuleRetestRole(next(iter(roles)))
            except ValueError as exc:
                raise ValueError("screen receipt contains an unknown case role") from exc

            scored: dict[str, Decimal] = {}
            for arm, row in arms.items():
                _validated_sha256(
                    row.get("dispatch_sha256"),
                    "screen result dispatch_sha256",
                )
                try:
                    score = Decimal(str(row.get("rubric_score")))
                except (InvalidOperation, ValueError) as exc:
                    raise ValueError("screen receipt rubric score must be numeric") from exc
                if not score.is_finite() or not Decimal("0") <= score <= Decimal("100"):
                    raise ValueError(
                        "screen receipt rubric score must be between zero and 100"
                    )
                output_text = _text(row.get("output_text"), "screen result output_text")
                output_hash = _validated_sha256(
                    row.get("output_sha256"),
                    "screen result output_sha256",
                )
                if hashlib.sha256(output_text.encode("utf-8")).hexdigest() != output_hash:
                    raise ValueError("screen receipt output hash mismatch")
                scored[arm] = score

            treatment = arms[ModuleRetestArm.TREATMENT.value]
            critical_errors = treatment.get("critical_error_codes")
            if not isinstance(critical_errors, list):
                raise ValueError("screen receipt critical error codes must be a list")
            normalized_errors = tuple(
                _text(code, "screen result critical error code")
                for code in critical_errors
            )
            if len(normalized_errors) != len(set(normalized_errors)):
                raise ValueError("screen receipt critical error codes must be unique")
            flag_names = (
                "safe_countercase_pass",
                "critical_trap_pass",
                "specialist_checks_pass",
            )
            if any(not isinstance(treatment.get(name), bool) for name in flag_names):
                raise ValueError("screen receipt treatment checks must be boolean")
            common = {
                "module_id": module_id,
                "case_id": case_id,
                "role": role,
                "treatment_score": scored[ModuleRetestArm.TREATMENT.value],
                "critical_regression": bool(normalized_errors),
                "safe_countercase_pass": treatment["safe_countercase_pass"],
                "critical_trap_pass": treatment["critical_trap_pass"],
                "specialist_checks_pass": treatment["specialist_checks_pass"],
            }
            plain_scores.append(
                ModulePairScore(
                    **common,
                    control_score=scored[ModuleRetestArm.CONTROL.value],
                )
            )
            placebo_scores.append(
                ModulePairScore(
                    **common,
                    control_score=scored[ModuleRetestArm.PLACEBO.value],
                )
            )
        decisions.append(decide_replacement_screen(plain_scores, placebo_scores))
    return tuple(decisions)


def _validated_screen_receipt(
    receipt: Mapping[str, Any],
    *,
    corpus_sha256: str,
    rubric_sha256: str,
    model_identity: Mapping[str, str],
) -> tuple[str, tuple[ReplacementScreenDecision, ...]]:
    """Validate the actual SCREEN receipt before opening confirmation work."""

    if not isinstance(receipt, Mapping):
        raise ValueError("screen receipt must be a mapping")
    if receipt.get("schema_version") != _BLINDED_RECEIPT_SCHEMA:
        raise ValueError("screen receipt schema mismatch")
    receipt_hash = _validated_sha256(
        receipt.get("receipt_sha256"),
        "screen receipt SHA-256",
    )
    unhashed_receipt = dict(receipt)
    unhashed_receipt.pop("receipt_sha256", None)
    observed_hash = hashlib.sha256(_canonical_bytes(unhashed_receipt)).hexdigest()
    if observed_hash != receipt_hash:
        raise ValueError("screen receipt hash mismatch")
    if receipt.get("phase") != "SCREEN":
        raise ValueError("screen receipt must record the SCREEN phase")
    if receipt.get("screen_receipt_sha256") is not None:
        raise ValueError("screen receipt cannot depend on an earlier screen receipt")
    if receipt.get("corpus_sha256") != corpus_sha256:
        raise ValueError("screen receipt corpus hash mismatch")
    if receipt.get("rubric_sha256") != rubric_sha256:
        raise ValueError("screen receipt rubric hash mismatch")
    if receipt.get("model_identity") != dict(model_identity):
        raise ValueError("screen receipt model identity mismatch")

    results = receipt.get("results")
    if not isinstance(results, list) or len(results) != 27:
        raise ValueError("screen receipt must contain exactly 27 results")
    if receipt.get("result_count") != len(results):
        raise ValueError("screen receipt result count mismatch")
    if any(
        not isinstance(result, Mapping) or result.get("phase") != "SCREEN"
        for result in results
    ):
        raise ValueError("screen receipt contains a non-SCREEN result")
    module_counts = {
        module_id: sum(result.get("module_id") == module_id for result in results)
        for module_id in REPLACEMENT_MODULE_IDS
    }
    if module_counts != {module_id: 9 for module_id in REPLACEMENT_MODULE_IDS}:
        raise ValueError("screen receipt does not cover every module exactly")

    authority = receipt.get("authority")
    if not isinstance(authority, Mapping) or not authority:
        raise ValueError("screen receipt authority map is missing")
    if any(value is not False for value in authority.values()):
        raise ValueError("screen receipt cannot grant authority")
    return receipt_hash, _screen_decisions_from_receipt(results)


def _blinded_placebo_context(target_bytes: int) -> dict[str, str]:
    """Build an inert context packet with the same public shape and byte length."""

    if target_bytes <= 0:
        raise ValueError("target placebo byte count must be positive")
    payload = {
        "schema_version": _BLINDED_CONTEXT_SCHEMA,
        "context": (
            "Review the supplied evidence carefully, keep the answer concise, "
            "preserve uncertainty, and state a controlled comparison. "
        ),
    }
    current = len(_canonical_bytes(payload))
    if current > target_bytes:
        raise ValueError("target placebo byte count is too small for the blind envelope")
    payload["context"] += "x" * (target_bytes - current)
    if len(_canonical_bytes(payload)) != target_bytes:
        raise AssertionError("blinded placebo context must be exactly length matched")
    return payload


def build_replacement_benchmark_manifest(
    *,
    cases: Sequence[ReplacementBenchmarkCase],
    corpus_sha256: str,
    rubric_sha256: str,
    run_nonce: str,
    model_identity: Mapping[str, str],
    phase: str,
    screen_decisions: Sequence[ReplacementScreenDecision] = (),
    screen_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(cases) != 18:
        raise ValueError("replacement benchmark manifest requires 18 frozen cases")
    required_model_fields = (
        "provider",
        "product",
        "model",
        "reasoning_effort",
        "surface",
        "context",
    )
    if not isinstance(model_identity, Mapping):
        raise TypeError("model_identity must be a mapping")
    normalized_model = {
        field: _text(model_identity.get(field), f"model_identity {field}")
        for field in required_model_fields
    }
    normalized_run_nonce = _text(run_nonce, "run_nonce")
    normalized_phase = _text(phase, "phase").upper()
    if normalized_phase not in {"SCREEN", "CONFIRM", "ALL"}:
        raise ValueError("phase must be SCREEN, CONFIRM, or ALL")
    normalized_corpus_sha256 = _validated_sha256(corpus_sha256, "corpus_sha256")
    normalized_rubric_sha256 = _validated_sha256(rubric_sha256, "rubric_sha256")
    decisions = tuple(screen_decisions)
    normalized_screen_receipt: str | None = None
    if normalized_phase == "CONFIRM":
        if screen_receipt is None:
            raise ValueError("confirmation requires the actual validated screen receipt")
        normalized_screen_receipt, receipt_decisions = _validated_screen_receipt(
            screen_receipt,
            corpus_sha256=normalized_corpus_sha256,
            rubric_sha256=normalized_rubric_sha256,
            model_identity=normalized_model,
        )
        if any(not isinstance(decision, ReplacementScreenDecision) for decision in decisions):
            raise TypeError("screen decisions must be ReplacementScreenDecision values")
        if len(decisions) != len(REPLACEMENT_MODULE_IDS):
            raise ValueError("confirmation requires one screen decision per module")
        decision_modules = tuple(decision.module_id for decision in decisions)
        if set(decision_modules) != set(REPLACEMENT_MODULE_IDS) or len(
            decision_modules
        ) != len(set(decision_modules)):
            raise ValueError("screen decisions must cover every module exactly once")
        if any(decision.state not in {"PROCEED", "STOP"} for decision in decisions):
            raise ValueError("screen decisions must be PROCEED or STOP")
        decisions_by_module = {decision.module_id: decision for decision in decisions}
        receipt_decisions_by_module = {
            decision.module_id: decision for decision in receipt_decisions
        }
        if decisions_by_module != receipt_decisions_by_module:
            raise ValueError("screen decisions do not match the validated screen receipt")
        eligible_modules = {
            decision.module_id
            for decision in receipt_decisions
            if decision.state == "PROCEED"
        }
        if not eligible_modules:
            raise ValueError("confirmation cannot run because no module passed screening")
        selected_cases = tuple(
            case
            for case in cases
            if case.phase == "CONFIRM" and case.module_id in eligible_modules
        )
    else:
        if decisions or screen_receipt is not None:
            raise ValueError(
                "screen decisions and screen receipt are valid only for confirmation"
            )
        selected_cases = tuple(
            case
            for case in cases
            if normalized_phase == "ALL" or case.phase == normalized_phase
        )
    requests = []
    for case in selected_cases:
        for arm in ModuleRetestArm:
            request = prepare_replacement_benchmark_request(
                case,
                arm,
                run_nonce=normalized_run_nonce,
            )
            requests.append(
                {
                    "request_id": request.request_id,
                    "case_id": request.case_id,
                    "module_id": request.module_id,
                    "phase": case.phase,
                    "role": case.role.value,
                    "arm": request.arm.value,
                    "prompt_payload": dict(request.prompt_payload),
                    "common_input_sha256": request.common_input_sha256,
                    "prompt_sha256": request.prompt_sha256,
                    "dispatch_text": request.dispatch_text,
                    "dispatch_sha256": request.dispatch_sha256,
                    "nonce": request.nonce,
                    "packet_sha256": request.packet_sha256,
                    "packet_byte_count": request.packet_byte_count,
                    "context_requirement": request.context_requirement,
                }
            )
    manifest: dict[str, Any] = {
        "schema_version": _BLINDED_MANIFEST_SCHEMA,
        "phase": normalized_phase,
        "run_nonce": normalized_run_nonce,
        "corpus_sha256": normalized_corpus_sha256,
        "rubric_sha256": normalized_rubric_sha256,
        "model_identity": normalized_model,
        "request_count": len(requests),
        "requests": requests,
        "screen_receipt_sha256": normalized_screen_receipt,
        "screen_decisions": [
            {
                "module_id": decision.module_id,
                "state": decision.state,
                "plain_control_wins": decision.plain_control_wins,
                "placebo_wins": decision.placebo_wins,
                "reasons": list(decision.reasons),
            }
            for decision in decisions
        ],
        "old_frozen_requests_resumed": False,
        "admission_policy": {
            "screen": "at least 2/3 wins against each control and zero critical regressions",
            "final": "at least 4/6 wins and median paired gain >= 5 against each control, zero critical errors",
        },
        "execution_gate": {
            "screen_first": True,
            "confirmation_requires_screen_state": "PROCEED",
            "confirmation_requires_screen_receipt": True,
        },
        "rollback_policy": {
            "runtime_reachable_during_benchmark": False,
            "post_admission_triggers": [
                "critical regression",
                "registry hash drift",
                "reproducibility failure",
                "authority-boundary violation",
            ],
            "action": (
                "Make the candidate runtime-unreachable and restore the last "
                "validated registry state while preserving source and evidence bytes."
            ),
            "source_deletion_authorized": False,
            "formula_mutation_authorized": False,
            "release_authority": False,
            "post_restore_verification_required": True,
            "post_restore_verification": [
                "registry hash equals the last validated registry hash",
                "candidate import paths remain runtime-unreachable",
                "authority flags remain false",
                "focused freeze and ensemble tests pass",
            ],
            "rollback_failure_state": "HOLD_RUNTIME_UNREACHABLE",
            "runtime_reenable_requires_fresh_admission": True,
        },
        "authority": {
            "formula": False,
            "inventory": False,
            "physical_execution": False,
            "sensory": False,
            "safety": False,
            "purchase": False,
            "publication": False,
            "release": False,
        },
    }
    manifest["manifest_sha256"] = hashlib.sha256(_canonical_bytes(manifest)).hexdigest()
    return manifest


def build_replacement_benchmark_receipt(
    *,
    run_id: str,
    manifest: Mapping[str, Any],
    scored_outputs: Sequence[ReplacementScoredOutput],
) -> dict[str, Any]:
    if manifest.get("schema_version") != _BLINDED_MANIFEST_SCHEMA:
        raise ValueError("unsupported replacement benchmark manifest schema")
    manifest_hash = _validated_sha256(
        manifest.get("manifest_sha256"), "manifest_sha256"
    )
    unhashed_manifest = dict(manifest)
    unhashed_manifest.pop("manifest_sha256", None)
    if hashlib.sha256(_canonical_bytes(unhashed_manifest)).hexdigest() != manifest_hash:
        raise ValueError("replacement benchmark manifest hash mismatch")
    requests = manifest.get("requests")
    if not isinstance(requests, list):
        raise TypeError("manifest requests must be a list")
    request_ids = tuple(
        _text(request.get("request_id"), "manifest request_id")
        for request in requests
        if isinstance(request, Mapping)
    )
    if len(request_ids) != len(requests):
        raise TypeError("every manifest request must be an object")
    outputs = tuple(scored_outputs)
    if any(not isinstance(item, ReplacementScoredOutput) for item in outputs):
        raise TypeError("scored_outputs must contain ReplacementScoredOutput values")
    output_ids = tuple(item.request_id for item in outputs)
    if len(output_ids) != len(set(output_ids)):
        raise ValueError("scored output request IDs must be unique")
    if set(output_ids) != set(request_ids):
        raise ValueError("scored outputs must cover every manifest request exactly once")
    by_id = {item.request_id: item for item in outputs}
    results = []
    for request in requests:
        output = by_id[request["request_id"]]
        result = output.as_dict()
        result.update(
            {
                "case_id": request["case_id"],
                "module_id": request["module_id"],
                "phase": request["phase"],
                "role": request["role"],
                "arm": request["arm"],
                "prompt_sha256": request["prompt_sha256"],
                "dispatch_sha256": request["dispatch_sha256"],
                "common_input_sha256": request["common_input_sha256"],
            }
        )
        results.append(result)
    receipt: dict[str, Any] = {
        "schema_version": _BLINDED_RECEIPT_SCHEMA,
        "run_id": _text(run_id, "run_id"),
        "manifest_sha256": manifest_hash,
        "corpus_sha256": manifest["corpus_sha256"],
        "rubric_sha256": manifest["rubric_sha256"],
        "model_identity": dict(manifest["model_identity"]),
        "phase": manifest["phase"],
        "screen_receipt_sha256": manifest["screen_receipt_sha256"],
        "result_count": len(results),
        "results": results,
        "rollback_policy": dict(manifest["rollback_policy"]),
        "authority": dict(manifest["authority"]),
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
    return receipt


def prepare_replacement_benchmark_request(
    case: ReplacementBenchmarkCase,
    arm: ModuleRetestArm,
    *,
    run_nonce: str | None = None,
) -> ReplacementBenchmarkRequest:
    if not isinstance(case, ReplacementBenchmarkCase):
        raise TypeError("case must be a ReplacementBenchmarkCase")
    if not isinstance(arm, ModuleRetestArm):
        raise TypeError("arm must be a ModuleRetestArm")
    normalized_run_nonce = (
        _text(run_nonce, "run_nonce") if run_nonce is not None else None
    )
    common = {
        "schema_version": _BLINDED_PROMPT_SCHEMA,
        "task": (
            "Resolve the supplied case using only its evidence. Complexity means "
            "target-linked depth, richness, and relationships, never ingredient count."
        ),
        "case": case.common_payload(),
        "output_contract": {
            "required_fields": [
                "decision",
                "target_linked_reasoning",
                "controlled_comparison",
                "claim_ceiling",
            ],
            "maximum_characters": 1800,
            "physical_liking_state": "NOT TESTED",
        },
    }
    if case.objective_expectation is not None:
        common["output_contract"]["format"] = "ONE_JSON_OBJECT"
        common["output_contract"]["objective_receipt"] = {
            "decision_state": "AUGMENT | NO_AUGMENTATION | HOLD",
            "reason_codes": "array of concise evidence-bound codes",
            "calculations": "object of named deterministic calculations",
            "next_actions": "array containing zero or one discriminating action",
            "authority": {key: False for key in _AUTHORITY_KEYS},
        }
    common_hash = hashlib.sha256(_canonical_bytes(common)).hexdigest()
    prompt = dict(common)
    packet_hash: str | None = None
    packet_bytes = 0
    if arm is ModuleRetestArm.TREATMENT:
        packet = case.module_packet.as_blinded_context()
        prompt["context_packet"] = packet
        packet_hash = hashlib.sha256(_canonical_bytes(packet)).hexdigest()
        packet_bytes = len(_canonical_bytes(packet))
    elif arm is ModuleRetestArm.PLACEBO:
        target_bytes = len(_canonical_bytes(case.module_packet.as_blinded_context()))
        packet = _blinded_placebo_context(target_bytes)
        prompt["context_packet"] = packet
        encoded = _canonical_bytes(packet)
        packet_hash = hashlib.sha256(encoded).hexdigest()
        packet_bytes = len(encoded)
    prompt_bytes = _canonical_bytes(prompt)
    prompt_hash = hashlib.sha256(prompt_bytes).hexdigest()
    dispatch_text = f"{_DISPATCH_PREAMBLE}\n\n{prompt_bytes.decode('utf-8')}"
    dispatch_hash = hashlib.sha256(dispatch_text.encode("utf-8")).hexdigest()
    nonce_material = f"{case.case_id}|{arm.value}|{prompt_hash}"
    if normalized_run_nonce is not None:
        nonce_material = f"{normalized_run_nonce}|{nonce_material}"
    nonce_hash = hashlib.sha256(nonce_material.encode("utf-8")).hexdigest()
    nonce = f"{case.case_id}-{arm.value.casefold()}-{nonce_hash[:16]}"
    request_id = f"rplreq-{hashlib.sha256(nonce.encode('utf-8')).hexdigest()[:20]}"
    return ReplacementBenchmarkRequest(
        request_id=request_id,
        case_id=case.case_id,
        module_id=case.module_id,
        arm=arm,
        prompt_payload=MappingProxyType(prompt),
        common_input_sha256=common_hash,
        prompt_sha256=prompt_hash,
        dispatch_text=dispatch_text,
        dispatch_sha256=dispatch_hash,
        nonce=nonce,
        packet_sha256=packet_hash,
        packet_byte_count=packet_bytes,
    )


__all__ = [
    "REPLACEMENT_MODULE_IDS",
    "EvidenceReceiptScore",
    "ObjectiveEvidenceExpectation",
    "ReplacementBenchmarkCase",
    "ReplacementBenchmarkRequest",
    "ReplacementModulePacket",
    "ReplacementRetentionDecision",
    "ReplacementScoredOutput",
    "ReplacementScreenDecision",
    "build_replacement_benchmark_manifest",
    "build_replacement_benchmark_receipt",
    "decide_replacement_retention",
    "decide_replacement_screen",
    "load_replacement_benchmark_cases",
    "prepare_replacement_benchmark_request",
    "score_evidence_receipt",
]
