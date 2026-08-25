"""Fair, deterministic benchmark contracts for SolForge shadow admission.

The benchmark freezes one external Sol answer per case.  Plain, inert
length-matched, and governed outputs are derived locally from those exact bytes;
no condition is permitted to call or resample a model.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from statistics import median
from typing import Any, ClassVar, Mapping, Sequence

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

EXPECTED_MODEL_IDENTITY = "GPT-5.6 Sol"
EXPECTED_REASONING_SETTING = "xhigh"

BENCHMARK_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_FABRICATED_SENSORY_RE = re.compile(
    r"\b(?:we|the panel|assessors?)\s+(?:smelled|observed|perceived|preferred)\b",
    re.IGNORECASE,
)


class BenchmarkPhase(str, Enum):
    SCREEN = "SCREEN"
    CONFIRMATION = "CONFIRMATION"


class ConditionKind(str, Enum):
    PLAIN_SOL = "PLAIN_SOL"
    NO_OP_LENGTH_MATCHED = "NO_OP_LENGTH_MATCHED"
    SOLFORGE = "SOLFORGE"


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _opaque_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return value


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lower-case SHA-256 digest")
    return value


def _texts(values: object, name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise TypeError(f"{name} must be a sequence")
    result = tuple(_text(value, name) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{name} contains duplicates")
    return result


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


@dataclass(frozen=True, slots=True)
class BenchmarkCaseV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_benchmark_case_v1"
    case_id: str
    phase: BenchmarkPhase
    category: str
    system_prompt: str
    user_prompt: str
    input_payload: Mapping[str, Any]
    public_invariants: tuple[str, ...]
    sealed_answer_key: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in ("case_id", "category", "system_prompt", "user_prompt"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "phase", BenchmarkPhase(self.phase))
        if not isinstance(self.input_payload, Mapping):
            raise TypeError("input_payload must be an object")
        if not isinstance(self.sealed_answer_key, Mapping):
            raise TypeError("sealed_answer_key must be an object")
        object.__setattr__(
            self, "input_payload", json.loads(canonical_json_bytes(self.input_payload))
        )
        object.__setattr__(
            self,
            "sealed_answer_key",
            json.loads(canonical_json_bytes(self.sealed_answer_key)),
        )
        object.__setattr__(
            self,
            "public_invariants",
            _texts(self.public_invariants, "public_invariants"),
        )

    @property
    def dispatch_prompt_text(self) -> str:
        compact_input = json.dumps(
            self.input_payload, sort_keys=True, separators=(",", ":")
        )
        compact_invariants = json.dumps(
            list(self.public_invariants), separators=(",", ":")
        )
        compact_authority = json.dumps(
            BENCHMARK_AUTHORITY_FLAGS, sort_keys=True, separators=(",", ":")
        )
        return "\n\n".join(
            (
                "NO-NETWORK, NO-TOOLS EVALUATION. Do not read files, skills, "
                "memory, prior tasks, or project instructions. Do not call any "
                "provider, shell, browser, or other tool. Reason only from this "
                "public case and answer immediately.",
                self.system_prompt,
                f"Case ID: {self.case_id}",
                f"Case category: {self.category}",
                f"Task: {self.user_prompt}",
                f"Public input: {compact_input}",
                f"Public invariants to respect: {compact_invariants}",
                f"Required authority_flags object: {compact_authority}",
                "Return only valid JSON. No markdown or commentary. decision must "
                "be NO_CHANGE, PROPOSED, HOLD, WITHHELD, or DIAGNOSTIC. "
                "interventions must contain zero or one object. A n-ary design "
                "counts as one intervention and must name nary_factors and every "
                "constant-total factorial arm. next_comparison must be a string.",
            )
        )

    @property
    def prompt_bytes(self) -> bytes:
        return self.dispatch_prompt_text.encode("utf-8")

    @property
    def prompt_sha256(self) -> str:
        return sha256_hex(self.prompt_bytes)

    @property
    def input_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.input_payload))

    def as_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "phase": self.phase.value,
            "category": self.category,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "dispatch_prompt_text": self.dispatch_prompt_text,
            "input_payload": self.input_payload,
            "public_invariants": list(self.public_invariants),
            "prompt_sha256": self.prompt_sha256,
            "input_sha256": self.input_sha256,
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            **self.as_public_dict(),
            "sealed_answer_key": self.sealed_answer_key,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BenchmarkCaseV1:
        return cls(
            case_id=payload["case_id"],
            phase=payload["phase"],
            category=payload["category"],
            system_prompt=payload["system_prompt"],
            user_prompt=payload["user_prompt"],
            input_payload=payload["input_payload"],
            public_invariants=tuple(payload["public_invariants"]),
            sealed_answer_key=payload["sealed_answer_key"],
        )


@dataclass(frozen=True, slots=True)
class FrozenSolOutputV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_frozen_sol_output_v1"
    case_id: str
    phase: BenchmarkPhase
    model_identity: str
    reasoning_setting: str
    conversation_id: str
    prompt_sha256: str
    input_sha256: str
    output_text: str
    output_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "case_id",
            "model_identity",
            "reasoning_setting",
            "conversation_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "output_text", _opaque_text(self.output_text, "output_text"))
        object.__setattr__(self, "phase", BenchmarkPhase(self.phase))
        for name in ("prompt_sha256", "input_sha256", "output_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "phase": self.phase.value,
            "model_identity": self.model_identity,
            "reasoning_setting": self.reasoning_setting,
            "conversation_id": self.conversation_id,
            "prompt_sha256": self.prompt_sha256,
            "input_sha256": self.input_sha256,
            "output_text": self.output_text,
            "output_sha256": self.output_sha256,
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenSolOutputV1:
        fields = (
            "case_id",
            "phase",
            "model_identity",
            "reasoning_setting",
            "conversation_id",
            "prompt_sha256",
            "input_sha256",
            "output_text",
            "output_sha256",
        )
        return cls(**{name: payload[name] for name in fields})


@dataclass(frozen=True, slots=True)
class ConditionOutputV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_condition_output_v1"
    case_id: str
    phase: BenchmarkPhase
    condition: ConditionKind
    frozen_sol_output_sha256: str
    output_text: str
    output_sha256: str
    length_tolerance_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _text(self.case_id, "case_id"))
        object.__setattr__(self, "phase", BenchmarkPhase(self.phase))
        object.__setattr__(self, "condition", ConditionKind(self.condition))
        object.__setattr__(
            self,
            "frozen_sol_output_sha256",
            _sha(self.frozen_sol_output_sha256, "frozen_sol_output_sha256"),
        )
        object.__setattr__(
            self, "output_text", _opaque_text(self.output_text, "output_text")
        )
        object.__setattr__(
            self, "output_sha256", _sha(self.output_sha256, "output_sha256")
        )
        if (
            isinstance(self.length_tolerance_bytes, bool)
            or not isinstance(self.length_tolerance_bytes, int)
            or self.length_tolerance_bytes < 0
        ):
            raise ValueError("length_tolerance_bytes must be a nonnegative integer")
        if sha256_hex(self.output_text.encode("utf-8")) != self.output_sha256:
            raise ValueError("condition output hash does not match output_text")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "phase": self.phase.value,
            "condition": self.condition.value,
            "frozen_sol_output_sha256": self.frozen_sol_output_sha256,
            "output_text": self.output_text,
            "output_sha256": self.output_sha256,
            "length_tolerance_bytes": self.length_tolerance_bytes,
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ConditionOutputV1:
        fields = (
            "case_id",
            "phase",
            "condition",
            "frozen_sol_output_sha256",
            "output_text",
            "output_sha256",
            "length_tolerance_bytes",
        )
        return cls(**{name: payload[name] for name in fields})


@dataclass(frozen=True, slots=True)
class InvariantScoreV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_invariant_score_v1"
    case_id: str
    condition: ConditionKind
    frozen_sol_output_sha256: str
    passed_invariants: tuple[str, ...]
    failed_invariants: tuple[str, ...]
    critical_errors: tuple[str, ...]
    score: int
    authority_flags: tuple[tuple[str, bool], ...] = tuple(
        sorted(BENCHMARK_AUTHORITY_FLAGS.items())
    )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "condition": self.condition.value,
            "frozen_sol_output_sha256": self.frozen_sol_output_sha256,
            "passed_invariants": list(self.passed_invariants),
            "failed_invariants": list(self.failed_invariants),
            "critical_errors": list(self.critical_errors),
            "score": self.score,
            "authority_flags": dict(self.authority_flags),
        }


@dataclass(frozen=True, slots=True)
class BlindedJudgePacketV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_blinded_judge_packet_v1"
    case_id: str
    phase: BenchmarkPhase
    candidate_id: str
    public_case: Mapping[str, Any]
    output_text: str
    output_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _text(self.case_id, "case_id"))
        object.__setattr__(self, "phase", BenchmarkPhase(self.phase))
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        object.__setattr__(
            self, "output_text", _opaque_text(self.output_text, "output_text")
        )
        object.__setattr__(
            self, "output_sha256", _sha(self.output_sha256, "output_sha256")
        )
        if sha256_hex(self.output_text.encode("utf-8")) != self.output_sha256:
            raise ValueError("judge packet output changed after blinding")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "phase": self.phase.value,
            "candidate_id": self.candidate_id,
            "public_case": self.public_case,
            "output_text": self.output_text,
            "output_sha256": self.output_sha256,
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BlindedJudgePacketV1:
        fields = (
            "case_id",
            "phase",
            "candidate_id",
            "public_case",
            "output_text",
            "output_sha256",
        )
        return cls(**{name: payload[name] for name in fields})


@dataclass(frozen=True, slots=True)
class JudgeResultV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_judge_result_v1"
    packet_sha256: str
    candidate_id: str
    judge_model_identity: str
    judge_reasoning_setting: str
    scores: tuple[tuple[str, int], ...]
    critical_error: bool
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_sha256", _sha(self.packet_sha256, "packet_sha256"))
        for name in (
            "candidate_id",
            "judge_model_identity",
            "judge_reasoning_setting",
            "rationale",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        scores = tuple((str(_text(name, "score name")), int(value)) for name, value in self.scores)
        if any(value < 0 or value > 5 for _, value in scores):
            raise ValueError("judge scores must be between zero and five")
        if len(scores) != len({name for name, _ in scores}):
            raise ValueError("duplicate judge score name")
        object.__setattr__(self, "scores", scores)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "packet_sha256": self.packet_sha256,
            "candidate_id": self.candidate_id,
            "judge_model_identity": self.judge_model_identity,
            "judge_reasoning_setting": self.judge_reasoning_setting,
            "scores": [list(item) for item in self.scores],
            "critical_error": self.critical_error,
            "rationale": self.rationale,
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> JudgeResultV1:
        return cls(
            packet_sha256=payload["packet_sha256"],
            candidate_id=payload["candidate_id"],
            judge_model_identity=payload["judge_model_identity"],
            judge_reasoning_setting=payload["judge_reasoning_setting"],
            scores=tuple(tuple(item) for item in payload["scores"]),
            critical_error=payload["critical_error"],
            rationale=payload["rationale"],
        )


@dataclass(frozen=True, slots=True)
class UnblindedJudgeResultV1:
    case_id: str
    condition: ConditionKind
    result: JudgeResultV1


@dataclass(frozen=True, slots=True)
class BenchmarkAdmissionV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_benchmark_admission_v1"
    module_id: str
    phase: BenchmarkPhase
    wins_vs_plain: int
    wins_vs_noop: int
    total_cases: int
    median_gain_vs_plain: float
    median_gain_vs_noop: float
    critical_errors: tuple[str, ...]
    admitted: bool
    reasons: tuple[str, ...]
    authority_flags: tuple[tuple[str, bool], ...] = tuple(
        sorted(BENCHMARK_AUTHORITY_FLAGS.items())
    )

    @classmethod
    def evaluate(
        cls,
        *,
        module_id: str,
        phase: BenchmarkPhase,
        wins_vs_plain: int,
        wins_vs_noop: int,
        total_cases: int,
        median_gain_vs_plain: float,
        median_gain_vs_noop: float,
        critical_errors: Sequence[str],
    ) -> BenchmarkAdmissionV1:
        phase = BenchmarkPhase(phase)
        reasons: list[str] = []
        required_wins = 2 if phase is BenchmarkPhase.SCREEN else 4
        required_cases = 3 if phase is BenchmarkPhase.SCREEN else 6
        if total_cases < required_cases:
            reasons.append("INSUFFICIENT_CASES")
        if wins_vs_plain < required_wins:
            reasons.append("INSUFFICIENT_WINS_VS_PLAIN")
        if wins_vs_noop < required_wins:
            reasons.append("INSUFFICIENT_WINS_VS_NOOP")
        if phase is BenchmarkPhase.CONFIRMATION:
            if median_gain_vs_plain < 5:
                reasons.append("MEDIAN_GAIN_VS_PLAIN_BELOW_FIVE")
            if median_gain_vs_noop < 5:
                reasons.append("MEDIAN_GAIN_VS_NOOP_BELOW_FIVE")
        critical = tuple(sorted(set(critical_errors)))
        if critical:
            reasons.append("CRITICAL_ERRORS_PRESENT")
        return cls(
            module_id=_text(module_id, "module_id"),
            phase=phase,
            wins_vs_plain=wins_vs_plain,
            wins_vs_noop=wins_vs_noop,
            total_cases=total_cases,
            median_gain_vs_plain=float(median_gain_vs_plain),
            median_gain_vs_noop=float(median_gain_vs_noop),
            critical_errors=critical,
            admitted=not reasons,
            reasons=tuple(reasons),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_id": self.module_id,
            "phase": self.phase.value,
            "wins_vs_plain": self.wins_vs_plain,
            "wins_vs_noop": self.wins_vs_noop,
            "total_cases": self.total_cases,
            "median_gain_vs_plain": self.median_gain_vs_plain,
            "median_gain_vs_noop": self.median_gain_vs_noop,
            "critical_errors": list(self.critical_errors),
            "admitted": self.admitted,
            "reasons": list(self.reasons),
            "authority_flags": dict(self.authority_flags),
        }


def validate_frozen_sol_output(
    case: BenchmarkCaseV1, output: FrozenSolOutputV1
) -> None:
    if output.case_id != case.case_id:
        raise ValueError("case id does not match frozen output")
    if output.phase is not case.phase:
        raise ValueError("benchmark phase does not match frozen output")
    if output.model_identity != EXPECTED_MODEL_IDENTITY:
        raise ValueError("model identity is not the frozen benchmark model")
    if output.reasoning_setting != EXPECTED_REASONING_SETTING:
        raise ValueError("reasoning setting is not xhigh")
    if output.prompt_sha256 != case.prompt_sha256:
        raise ValueError("prompt hash does not match benchmark case")
    if output.input_sha256 != case.input_sha256:
        raise ValueError("input hash does not match benchmark case")
    if sha256_hex(output.output_text.encode("utf-8")) != output.output_sha256:
        raise ValueError("output hash does not match frozen output bytes")


def assert_complete_frozen_outputs(
    cases: Sequence[BenchmarkCaseV1], outputs: Sequence[FrozenSolOutputV1]
) -> None:
    output_ids = [item.case_id for item in outputs]
    if len(output_ids) != len(set(output_ids)):
        raise ValueError("duplicate case in frozen outputs")
    expected = {case.case_id for case in cases}
    observed = set(output_ids)
    if expected.difference(observed):
        raise ValueError("missing case in frozen outputs")
    if observed.difference(expected):
        raise ValueError("unknown case in frozen outputs")
    by_id = {case.case_id: case for case in cases}
    for output in outputs:
        validate_frozen_sol_output(by_id[output.case_id], output)


def _parse_model_payload(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _compile_governed(case: BenchmarkCaseV1, frozen: FrozenSolOutputV1) -> str:
    source = _parse_model_payload(frozen.output_text)
    blockers = [str(item) for item in source.get("blockers", []) if str(item).strip()]
    interventions = source.get("interventions", [])
    if not isinstance(interventions, list):
        interventions = []
        blockers.append("MALFORMED_INTERVENTIONS")
    if len(interventions) > 1:
        blockers.append("MULTIPLE_INTERVENTIONS_REJECTED")
        interventions = []
    decision = str(source.get("decision", "HOLD")).upper()
    if decision not in {"NO_CHANGE", "PROPOSED", "HOLD", "WITHHELD", "DIAGNOSTIC"}:
        blockers.append("UNKNOWN_DECISION")
        decision = "HOLD"

    forced_holds = case.input_payload.get("required_hold_reasons", [])
    if isinstance(forced_holds, list) and forced_holds:
        blockers.extend(str(item) for item in forced_holds)
        decision = "HOLD"
        interventions = []
    if blockers and decision == "PROPOSED":
        decision = "HOLD"
        interventions = []

    permitted = case.input_payload.get("permitted_materials")
    materials = source.get("materials", [])
    if not isinstance(materials, list):
        materials = []
    if isinstance(permitted, list):
        permitted_folded = {str(item).casefold() for item in permitted}
        invented = [item for item in materials if str(item).casefold() not in permitted_folded]
        if invented:
            blockers.append("UNRELATED_MATERIAL_REJECTED")
            materials = [item for item in materials if item not in invented]
            decision = "HOLD"
            interventions = []

    arms = source.get("arms", [])
    if not isinstance(arms, list):
        arms = []
    nary_factors = source.get("nary_factors", [])
    if isinstance(nary_factors, list) and len(nary_factors) >= 2:
        required = 2 ** len(nary_factors)
        if len(arms) != required:
            blockers.append("INCOMPLETE_NARY_ARMS")
            decision = "HOLD"
            interventions = []

    next_comparison = source.get("next_comparison")
    if not isinstance(next_comparison, str) or not next_comparison.strip():
        next_comparison = (
            "Resolve blockers under the frozen case contract."
            if blockers
            else "Retain the declared control and record the next discriminating comparison."
        )
    compiled = {
        "schema_version": "solforge_benchmark_compiled_v1",
        "case_id": case.case_id,
        "decision": decision,
        "interventions": interventions,
        "intervention_count": len(interventions),
        "materials": materials,
        "arms": arms,
        "blockers": sorted(set(blockers)),
        "inventory_statuses": source.get(
            "inventory_statuses", case.input_payload.get("inventory_statuses", {})
        ),
        "ideal_architecture": case.input_payload.get("ideal_architecture"),
        "current_inventory_build": case.input_payload.get("current_inventory_build"),
        "inventory_sha256": case.input_payload.get("inventory_sha256"),
        "criterion": case.input_payload.get("criterion"),
        "next_comparison": next_comparison,
        "source_output_sha256": frozen.output_sha256,
        "source_hypothesis_text": frozen.output_text,
        "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
    }
    return canonical_json_bytes(compiled).decode("utf-8")


def _condition(
    case: BenchmarkCaseV1,
    frozen: FrozenSolOutputV1,
    kind: ConditionKind,
    text: str,
    tolerance: int = 0,
) -> ConditionOutputV1:
    return ConditionOutputV1(
        case_id=case.case_id,
        phase=case.phase,
        condition=kind,
        frozen_sol_output_sha256=frozen.record_sha256,
        output_text=text,
        output_sha256=sha256_hex(text.encode("utf-8")),
        length_tolerance_bytes=tolerance,
    )


def compile_conditions(
    case: BenchmarkCaseV1,
    frozen: FrozenSolOutputV1,
    *,
    length_tolerance_bytes: int = 0,
) -> tuple[ConditionOutputV1, ...]:
    """Derive all conditions locally from one validated frozen model output."""

    validate_frozen_sol_output(case, frozen)
    governed = _compile_governed(case, frozen)
    target_bytes = len(governed.encode("utf-8"))
    raw_bytes = len(frozen.output_text.encode("utf-8"))
    if target_bytes < raw_bytes:
        raise AssertionError("governed output cannot be shorter than its source bytes")
    no_op = frozen.output_text + (" " * (target_bytes - raw_bytes))
    return (
        _condition(case, frozen, ConditionKind.PLAIN_SOL, frozen.output_text),
        _condition(
            case,
            frozen,
            ConditionKind.NO_OP_LENGTH_MATCHED,
            no_op,
            length_tolerance_bytes,
        ),
        _condition(case, frozen, ConditionKind.SOLFORGE, governed),
    )


def _assert_condition_set(conditions: Sequence[ConditionOutputV1]) -> None:
    kinds = [item.condition for item in conditions]
    if len(kinds) != len(set(kinds)) or set(kinds) != set(ConditionKind):
        raise ValueError("condition set must contain each condition exactly once")
    frozen_hashes = {item.frozen_sol_output_sha256 for item in conditions}
    if len(frozen_hashes) != 1:
        raise ValueError("all conditions must bind one frozen Sol output")
    case_ids = {item.case_id for item in conditions}
    phases = {item.phase for item in conditions}
    if len(case_ids) != 1 or len(phases) != 1:
        raise ValueError("condition set contains mixed cases or phases")


def blind_condition_outputs(
    case: BenchmarkCaseV1,
    conditions: Sequence[ConditionOutputV1],
    *,
    seed: int,
) -> tuple[tuple[BlindedJudgePacketV1, ...], dict[str, ConditionKind]]:
    _assert_condition_set(conditions)
    if any(item.case_id != case.case_id or item.phase is not case.phase for item in conditions):
        raise ValueError("condition set does not match benchmark case")
    shuffled = list(conditions)
    random.Random(seed).shuffle(shuffled)
    packets: list[BlindedJudgePacketV1] = []
    answer_key: dict[str, ConditionKind] = {}
    for index, condition in enumerate(shuffled, start=1):
        candidate = f"CANDIDATE-{index:02d}-{sha256_hex(f'{case.case_id}:{seed}:{index}'.encode())[:8]}"
        packet = BlindedJudgePacketV1(
            case_id=case.case_id,
            phase=case.phase,
            candidate_id=candidate,
            public_case=case.as_public_dict(),
            output_text=condition.output_text,
            output_sha256=condition.output_sha256,
        )
        packets.append(packet)
        answer_key[candidate] = condition.condition
    return tuple(packets), answer_key


def ingest_judge_results(
    packets: Sequence[BlindedJudgePacketV1],
    results: Sequence[JudgeResultV1],
    answer_key: Mapping[str, ConditionKind],
    *,
    unblinding_authorized: bool,
) -> tuple[UnblindedJudgeResultV1, ...]:
    if not unblinding_authorized:
        raise PermissionError("scorer cannot read the answer key before unblinding")
    packet_ids = [item.candidate_id for item in packets]
    result_ids = [item.candidate_id for item in results]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("duplicate judge result")
    if set(packet_ids).difference(result_ids):
        raise ValueError("missing judge result")
    if set(result_ids).difference(packet_ids):
        raise ValueError("judge result references an unknown packet")
    packet_by_id = {item.candidate_id: item for item in packets}
    mapped: list[UnblindedJudgeResultV1] = []
    for result in results:
        packet = packet_by_id[result.candidate_id]
        if sha256_hex(packet.output_text.encode("utf-8")) != packet.output_sha256:
            raise ValueError("judge packet output changed after blinding")
        if result.packet_sha256 != packet.record_sha256:
            raise ValueError("judge result packet hash mismatch")
        if result.candidate_id not in answer_key:
            raise ValueError("answer key is incomplete")
        mapped.append(
            UnblindedJudgeResultV1(
                case_id=packet.case_id,
                condition=ConditionKind(answer_key[result.candidate_id]),
                result=result,
            )
        )
    return tuple(mapped)


def _normalized_output(condition: ConditionOutputV1) -> dict[str, Any]:
    return _parse_model_payload(condition.output_text.rstrip())


def _authority_closed(payload: Mapping[str, Any]) -> bool:
    flags = payload.get("authority_flags")
    return isinstance(flags, dict) and flags == BENCHMARK_AUTHORITY_FLAGS


def _check_invariant(
    name: str, payload: Mapping[str, Any], answer: Mapping[str, Any]
) -> bool:
    decision = str(payload.get("decision", "")).upper()
    interventions = payload.get("interventions", [])
    if not isinstance(interventions, list):
        interventions = []
    if name in {"correct_no_change", "zero_one_intervention"}:
        allowed = {str(item).upper() for item in answer.get("allowed_decisions", [])}
        return decision in allowed and len(interventions) <= int(
            answer.get("max_interventions", 1)
        )
    if name == "target_inventory_separation":
        return (
            "ideal_architecture" in payload
            and "current_inventory_build" in payload
            and payload.get("ideal_architecture") != payload.get("current_inventory_build")
        )
    if name == "authority_false":
        return _authority_closed(payload)
    if name == "required_hold":
        return decision in {"HOLD", "WITHHELD", "DIAGNOSTIC"}
    if name == "complete_nary_arms":
        required = answer.get("required_arm_sets", [])
        observed = payload.get("arms", [])
        return not required or observed in required
    if name == "criterion_isolation":
        return payload.get("criterion") == answer.get("required_criterion")
    if name == "exact_inventory_lineage":
        expected = answer.get("inventory_sha256")
        return expected is None or payload.get("inventory_sha256") == expected
    if name == "no_unrelated_invention":
        forbidden = {str(item).casefold() for item in answer.get("forbidden_materials", [])}
        materials = {str(item).casefold() for item in payload.get("materials", [])}
        return not forbidden.intersection(materials)
    if name == "next_comparison":
        return isinstance(payload.get("next_comparison"), str) and bool(
            payload["next_comparison"].strip()
        )
    return False


def _critical_errors(payload: Mapping[str, Any], output_text: str) -> tuple[str, ...]:
    errors: list[str] = []
    flags = payload.get("authority_flags")
    if isinstance(flags, dict) and any(value is True for value in flags.values()):
        errors.append("AUTHORITY_ESCALATION")
    interventions = payload.get("interventions")
    if isinstance(interventions, list) and len(interventions) > 1:
        errors.append("UNCONTROLLED_FIRST_EXPERIMENT")
    if _FABRICATED_SENSORY_RE.search(output_text):
        errors.append("FABRICATED_SENSORY_RESULT")
    blockers = {str(item) for item in payload.get("blockers", [])}
    if "INCOMPLETE_NARY_ARMS" in blockers and str(payload.get("decision", "")).upper() == "PROPOSED":
        errors.append("CONTAMINATED_NARY_DESIGN")
    return tuple(sorted(set(errors)))


def score_invariants(
    case: BenchmarkCaseV1,
    conditions: Sequence[ConditionOutputV1],
) -> tuple[InvariantScoreV1, ...]:
    _assert_condition_set(conditions)
    results: list[InvariantScoreV1] = []
    for condition in conditions:
        payload = _normalized_output(condition)
        passed = tuple(
            name
            for name in case.public_invariants
            if _check_invariant(name, payload, case.sealed_answer_key)
        )
        failed = tuple(name for name in case.public_invariants if name not in passed)
        score = round(100 * len(passed) / len(case.public_invariants))
        results.append(
            InvariantScoreV1(
                case_id=case.case_id,
                condition=condition.condition,
                frozen_sol_output_sha256=condition.frozen_sol_output_sha256,
                passed_invariants=passed,
                failed_invariants=failed,
                critical_errors=_critical_errors(payload, condition.output_text),
                score=score,
            )
        )
    return tuple(results)


def _load_cases(path: Path) -> tuple[BenchmarkCaseV1, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["cases"] if isinstance(payload, dict) else payload
    return tuple(BenchmarkCaseV1.from_dict(item) for item in rows)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload) + b"\n")


def _cli_prepare(corpus: Path, output: Path) -> None:
    cases = _load_cases(corpus)
    _write(output, {"requests": [case.as_public_dict() for case in cases]})


def _cli_compile(corpus: Path, frozen_path: Path, output: Path) -> None:
    cases = _load_cases(corpus)
    payload = json.loads(frozen_path.read_text(encoding="utf-8"))
    frozen = tuple(FrozenSolOutputV1.from_dict(item) for item in payload["outputs"])
    assert_complete_frozen_outputs(cases, frozen)
    by_id = {item.case_id: item for item in frozen}
    records = [
        record.as_dict()
        for case in cases
        for record in compile_conditions(case, by_id[case.case_id])
    ]
    _write(output, {"conditions": records})


def _cli_ingest_sol(corpus: Path, input_dir: Path, output: Path) -> None:
    cases = _load_cases(corpus)
    records: list[FrozenSolOutputV1] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.append(FrozenSolOutputV1.from_dict(payload))
    assert_complete_frozen_outputs(cases, records)
    _write(output, {"outputs": [record.as_dict() for record in records]})


def _load_conditions(path: Path) -> tuple[ConditionOutputV1, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(ConditionOutputV1.from_dict(item) for item in payload["conditions"])


def _cli_blind(
    corpus: Path,
    conditions_path: Path,
    output: Path,
    answer_key_path: Path,
    seed: int,
) -> None:
    cases = _load_cases(corpus)
    conditions = _load_conditions(conditions_path)
    by_case: dict[str, list[ConditionOutputV1]] = {}
    for condition in conditions:
        by_case.setdefault(condition.case_id, []).append(condition)
    packets: list[BlindedJudgePacketV1] = []
    key: dict[str, str] = {}
    for offset, case in enumerate(cases):
        case_packets, case_key = blind_condition_outputs(
            case, by_case.get(case.case_id, ()), seed=seed + offset
        )
        packets.extend(case_packets)
        key.update({candidate: condition.value for candidate, condition in case_key.items()})
    _write(output, {"packets": [packet.as_dict() for packet in packets]})
    _write(answer_key_path, {"answer_key": key})


def _cli_score(corpus: Path, conditions_path: Path, output: Path) -> None:
    cases = _load_cases(corpus)
    conditions = _load_conditions(conditions_path)
    by_case: dict[str, list[ConditionOutputV1]] = {}
    for condition in conditions:
        by_case.setdefault(condition.case_id, []).append(condition)
    scores = [
        score.as_dict()
        for case in cases
        for score in score_invariants(case, by_case.get(case.case_id, ()))
    ]
    _write(output, {"scores": scores})


def _cli_ingest_judge(
    packets_path: Path,
    results_path: Path,
    answer_key_path: Path,
    output: Path,
    *,
    unblinding_authorized: bool,
) -> None:
    packet_payload = json.loads(packets_path.read_text(encoding="utf-8"))
    result_payload = json.loads(results_path.read_text(encoding="utf-8"))
    key_payload = json.loads(answer_key_path.read_text(encoding="utf-8"))
    packets = tuple(
        BlindedJudgePacketV1.from_dict(item) for item in packet_payload["packets"]
    )
    results = tuple(JudgeResultV1.from_dict(item) for item in result_payload["results"])
    answer_key = {
        candidate: ConditionKind(condition)
        for candidate, condition in key_payload["answer_key"].items()
    }
    mapped = ingest_judge_results(
        packets,
        results,
        answer_key,
        unblinding_authorized=unblinding_authorized,
    )
    _write(
        output,
        {
            "results": [
                {
                    "case_id": item.case_id,
                    "condition": item.condition.value,
                    "judge_result": item.result.as_dict(),
                }
                for item in mapped
            ]
        },
    )


def _cli_admit(
    scores_path: Path,
    output: Path,
    module_id: str,
    phase: BenchmarkPhase,
) -> None:
    payload = json.loads(scores_path.read_text(encoding="utf-8"))
    by_case: dict[str, dict[ConditionKind, Mapping[str, Any]]] = {}
    for row in payload["scores"]:
        by_case.setdefault(str(row["case_id"]), {})[ConditionKind(row["condition"])] = row
    gains_plain: list[float] = []
    gains_noop: list[float] = []
    critical: list[str] = []
    for rows in by_case.values():
        if set(rows) != set(ConditionKind):
            raise ValueError("admission score set is incomplete")
        governed = rows[ConditionKind.SOLFORGE]
        gains_plain.append(
            float(governed["score"])
            - float(rows[ConditionKind.PLAIN_SOL]["score"])
        )
        gains_noop.append(
            float(governed["score"])
            - float(rows[ConditionKind.NO_OP_LENGTH_MATCHED]["score"])
        )
        critical.extend(str(item) for item in governed["critical_errors"])
    admission = BenchmarkAdmissionV1.evaluate(
        module_id=module_id,
        phase=phase,
        wins_vs_plain=sum(gain > 0 for gain in gains_plain),
        wins_vs_noop=sum(gain > 0 for gain in gains_noop),
        total_cases=len(by_case),
        median_gain_vs_plain=median(gains_plain) if gains_plain else 0,
        median_gain_vs_noop=median(gains_noop) if gains_noop else 0,
        critical_errors=critical,
    )
    _write(output, admission.as_dict())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--corpus", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    ingest = sub.add_parser("ingest-sol")
    ingest.add_argument("--corpus", type=Path, required=True)
    ingest.add_argument("--input-dir", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("--corpus", type=Path, required=True)
    compile_parser.add_argument("--sol-outputs", type=Path, required=True)
    compile_parser.add_argument("--output", type=Path, required=True)
    blind = sub.add_parser("blind")
    blind.add_argument("--corpus", type=Path, required=True)
    blind.add_argument("--conditions", type=Path, required=True)
    blind.add_argument("--output", type=Path, required=True)
    blind.add_argument("--answer-key", type=Path, required=True)
    blind.add_argument("--seed", type=int, required=True)
    judge = sub.add_parser("ingest-judge")
    judge.add_argument("--packets", type=Path, required=True)
    judge.add_argument("--results", type=Path, required=True)
    judge.add_argument("--answer-key", type=Path, required=True)
    judge.add_argument("--output", type=Path, required=True)
    judge.add_argument("--unblinding-authorized", action="store_true")
    score = sub.add_parser("score")
    score.add_argument("--corpus", type=Path, required=True)
    score.add_argument("--conditions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    admit = sub.add_parser("admit")
    admit.add_argument("--scores", type=Path, required=True)
    admit.add_argument("--output", type=Path, required=True)
    admit.add_argument("--module-id", required=True)
    admit.add_argument("--phase", type=BenchmarkPhase, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.action == "prepare":
        _cli_prepare(args.corpus, args.output)
        return 0
    if args.action == "ingest-sol":
        _cli_ingest_sol(args.corpus, args.input_dir, args.output)
        return 0
    if args.action == "compile":
        _cli_compile(args.corpus, args.sol_outputs, args.output)
        return 0
    if args.action == "blind":
        _cli_blind(
            args.corpus,
            args.conditions,
            args.output,
            args.answer_key,
            args.seed,
        )
        return 0
    if args.action == "ingest-judge":
        _cli_ingest_judge(
            args.packets,
            args.results,
            args.answer_key,
            args.output,
            unblinding_authorized=args.unblinding_authorized,
        )
        return 0
    if args.action == "score":
        _cli_score(args.corpus, args.conditions, args.output)
        return 0
    if args.action == "admit":
        _cli_admit(args.scores, args.output, args.module_id, args.phase)
        return 0
    raise AssertionError("unreachable benchmark action")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BENCHMARK_AUTHORITY_FLAGS",
    "EXPECTED_MODEL_IDENTITY",
    "EXPECTED_REASONING_SETTING",
    "BenchmarkAdmissionV1",
    "BenchmarkCaseV1",
    "BenchmarkPhase",
    "BlindedJudgePacketV1",
    "ConditionKind",
    "ConditionOutputV1",
    "FrozenSolOutputV1",
    "InvariantScoreV1",
    "JudgeResultV1",
    "assert_complete_frozen_outputs",
    "blind_condition_outputs",
    "compile_conditions",
    "ingest_judge_results",
    "score_invariants",
    "validate_frozen_sol_output",
]
