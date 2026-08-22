"""Frozen per-module ChatGPT xhigh retest contracts and retention gates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from statistics import median
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from engine.perception.complexity_decision_cards import DecisionCard

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_MODULE_IDS = (
    "construction_profile",
    "complexity_expansion",
    "musk_design_restraint",
    "model_admission",
    "model_lifecycle",
    "within_sniff",
    "temporal_observations",
    "order_balance",
    "panel_contract",
    "citrus_selection",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value.strip()


def _sha256(value: object, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    normalized = tuple(_text(item, f"{field_name} item") for item in value)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


class ModuleRetestArm(str, Enum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"
    PLACEBO = "PLACEBO"


class ModuleRetestRole(str, Enum):
    POSITIVE = "POSITIVE"
    SAFE_COUNTERCASE = "SAFE_COUNTERCASE"
    CRITICAL_TRAP = "CRITICAL_TRAP"
    INVENTORY_MISMATCH = "INVENTORY_MISMATCH"
    CONTROL = "CONTROL"
    UNSEEN_VARIANT = "UNSEEN_VARIANT"


@dataclass(frozen=True, slots=True)
class ModuleRetestCase:
    case_id: str
    module_id: str
    phase: str
    role: ModuleRetestRole
    target_name: str
    target_identity: str
    brief: str
    facts: tuple[str, ...]
    inventory_state: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    expected_decision: str
    critical_error: str
    claim_ceiling: str
    native_result: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field_name in (
            "case_id",
            "module_id",
            "target_name",
            "target_identity",
            "brief",
            "expected_decision",
            "critical_error",
            "claim_ceiling",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if self.module_id not in EXPECTED_MODULE_IDS:
            raise ValueError(f"unknown module_id: {self.module_id}")
        if self.phase not in {"SCREEN", "CONFIRM"}:
            raise ValueError("phase must be SCREEN or CONFIRM")
        if not isinstance(self.role, ModuleRetestRole):
            raise TypeError("role must be a ModuleRetestRole")
        object.__setattr__(self, "facts", _string_tuple(self.facts, "facts"))
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        if not isinstance(self.inventory_state, Mapping):
            raise TypeError("inventory_state must be a mapping")
        if not isinstance(self.native_result, Mapping):
            raise TypeError("native_result must be a mapping")
        _sha256(self.native_result.get("result_sha256"), "native result_sha256")
        object.__setattr__(self, "inventory_state", MappingProxyType(dict(self.inventory_state)))
        object.__setattr__(self, "native_result", MappingProxyType(dict(self.native_result)))

    def common_payload(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "module_id": self.module_id,
            "phase": self.phase,
            "role": self.role.value,
            "target_name": self.target_name,
            "target_identity": self.target_identity,
            "brief": self.brief,
            "facts": list(self.facts),
            "inventory_state": dict(self.inventory_state),
            "evidence_refs": list(self.evidence_refs),
            "claim_ceiling": self.claim_ceiling,
        }


def load_module_retest_cases(path: Path) -> tuple[ModuleRetestCase, ...]:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "complexity_module_retest_cases_v1":
        raise ValueError("unsupported module retest corpus schema")
    shared = payload.get("shared_native_results", {})
    if not isinstance(shared, dict):
        raise ValueError("shared_native_results must be an object")
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise ValueError("corpus cases must be a list")
    cases: list[ModuleRetestCase] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("each corpus case must be an object")
        if "native_result" in row:
            native_result = row["native_result"]
        else:
            reference = _text(row.get("native_result_ref"), "native_result_ref")
            if reference not in shared:
                raise ValueError(f"unknown native_result_ref: {reference}")
            source = shared[reference]
            if not isinstance(source, dict):
                raise TypeError(f"shared native result {reference} must be an object")
            native_result = dict(source)
            native_result["result_sha256"] = hashlib.sha256(
                _canonical_bytes(source)
            ).hexdigest()
        cases.append(
            ModuleRetestCase(
                case_id=row["case_id"],
                module_id=row["module_id"],
                phase=row["phase"],
                role=ModuleRetestRole(row["role"]),
                target_name=row["target_name"],
                target_identity=row["target_identity"],
                brief=row["brief"],
                facts=tuple(row["facts"]),
                inventory_state=row["inventory_state"],
                evidence_refs=tuple(row["evidence_refs"]),
                expected_decision=row["expected_decision"],
                critical_error=row["critical_error"],
                claim_ceiling=row["claim_ceiling"],
                native_result=native_result,
            )
        )
    ids = tuple(item.case_id for item in cases)
    if len(ids) != len(set(ids)):
        raise ValueError("case IDs must be unique")
    return tuple(cases)


def group_cases(
    cases: Sequence[ModuleRetestCase],
) -> dict[str, tuple[ModuleRetestCase, ...]]:
    grouped: dict[str, list[ModuleRetestCase]] = {}
    for case in cases:
        grouped.setdefault(case.module_id, []).append(case)
    return {key: tuple(value) for key, value in grouped.items()}


@dataclass(frozen=True, slots=True)
class ModuleRetestRequest:
    request_id: str
    case_id: str
    module_id: str
    arm: ModuleRetestArm
    prompt_payload: Mapping[str, Any]
    common_input_sha256: str
    prompt_sha256: str
    nonce: str
    card_sha256: str | None
    card_byte_count: int
    model_requirement: str = "ChatGPT 5.6 Sol Extra High"
    reasoning_effort: str = "Extra High"
    context_requirement: str = "FRESH_PROJECTLESS_CONVERSATION"


def _placebo_card(target_bytes: int) -> dict[str, str]:
    if target_bytes <= 0:
        raise ValueError("target placebo byte count must be positive")
    payload = {
        "schema_version": "length_matched_placebo_v1",
        "text": "",
    }
    base = len(_canonical_bytes(payload))
    payload["text"] = (
        "Review the supplied facts carefully, keep the answer concise, preserve "
        "uncertainty, and state a controlled comparison. "
    )
    current = len(_canonical_bytes(payload))
    if current < target_bytes:
        payload["text"] += "x" * (target_bytes - current)
    while len(_canonical_bytes(payload)) > target_bytes and payload["text"]:
        payload["text"] = payload["text"][:-1]
    if len(_canonical_bytes(payload)) < base:
        raise ValueError("unable to build length-matched placebo")
    return payload


def prepare_module_retest_request(
    case: ModuleRetestCase,
    arm: ModuleRetestArm,
    *,
    card: DecisionCard | None,
) -> ModuleRetestRequest:
    if not isinstance(case, ModuleRetestCase):
        raise TypeError("case must be a ModuleRetestCase")
    if not isinstance(arm, ModuleRetestArm):
        raise TypeError("arm must be a ModuleRetestArm")
    if arm is ModuleRetestArm.CONTROL and card is not None:
        raise ValueError("control must not receive a decision card")
    if arm is not ModuleRetestArm.CONTROL and card is None:
        raise ValueError(f"{arm.value} requires a decision card")
    if card is not None and card.module_id != case.module_id:
        raise ValueError("decision card module does not match the case")

    common = {
        "schema_version": "complexity_module_retest_prompt_v1",
        "task": (
            "Resolve the case using only supplied evidence. Useful complexity means "
            "identity-linked depth and richness, not complication. Return the exact "
            "decision, reasoning, controlled comparison, and claim ceiling."
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
    common_hash = hashlib.sha256(_canonical_bytes(common)).hexdigest()
    prompt = dict(common)
    card_sha256: str | None = None
    card_byte_count = 0
    if arm is ModuleRetestArm.TREATMENT:
        assert card is not None
        prompt["decision_card"] = card.as_dict()
        card_sha256 = card.card_sha256
        card_byte_count = len(card.to_json_bytes())
    elif arm is ModuleRetestArm.PLACEBO:
        assert card is not None
        placebo = _placebo_card(len(card.to_json_bytes()))
        prompt["decision_card"] = placebo
        placebo_bytes = _canonical_bytes(placebo)
        card_sha256 = hashlib.sha256(placebo_bytes).hexdigest()
        card_byte_count = len(placebo_bytes)
    prompt_hash = hashlib.sha256(_canonical_bytes(prompt)).hexdigest()
    nonce_digest = hashlib.sha256(
        f"{case.case_id}|{arm.value}|{prompt_hash}".encode("utf-8")
    ).hexdigest()[:16]
    nonce = f"{case.case_id}-{arm.value.casefold()}-{nonce_digest}"
    request_id = f"cmreq-{hashlib.sha256(nonce.encode('utf-8')).hexdigest()[:20]}"
    return ModuleRetestRequest(
        request_id=request_id,
        case_id=case.case_id,
        module_id=case.module_id,
        arm=arm,
        prompt_payload=prompt,
        common_input_sha256=common_hash,
        prompt_sha256=prompt_hash,
        nonce=nonce,
        card_sha256=card_sha256,
        card_byte_count=card_byte_count,
    )


@dataclass(frozen=True, slots=True)
class ModulePairScore:
    module_id: str
    case_id: str
    role: ModuleRetestRole
    treatment_score: Decimal
    control_score: Decimal
    critical_regression: bool
    safe_countercase_pass: bool
    critical_trap_pass: bool
    specialist_checks_pass: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))
        object.__setattr__(self, "case_id", _text(self.case_id, "case_id"))
        if not isinstance(self.role, ModuleRetestRole):
            raise TypeError("role must be a ModuleRetestRole")
        object.__setattr__(
            self,
            "treatment_score",
            _decimal(self.treatment_score, "treatment_score"),
        )
        object.__setattr__(
            self, "control_score", _decimal(self.control_score, "control_score")
        )
        for field_name in (
            "critical_regression",
            "safe_countercase_pass",
            "critical_trap_pass",
            "specialist_checks_pass",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")

    @property
    def delta(self) -> Decimal:
        return self.treatment_score - self.control_score

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "case_id": self.case_id,
            "role": self.role.value,
            "treatment_score": str(self.treatment_score),
            "control_score": str(self.control_score),
            "delta": str(self.delta),
            "critical_regression": self.critical_regression,
            "safe_countercase_pass": self.safe_countercase_pass,
            "critical_trap_pass": self.critical_trap_pass,
            "specialist_checks_pass": self.specialist_checks_pass,
        }


@dataclass(frozen=True, slots=True)
class ModuleRetentionDecision:
    module_id: str
    state: str
    treatment_wins: int
    median_paired_delta: Decimal
    placebo_delta: Decimal
    reasons: tuple[str, ...]
    pair_scores: tuple[ModulePairScore, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "state": self.state,
            "treatment_wins": self.treatment_wins,
            "median_paired_delta": str(self.median_paired_delta),
            "placebo_delta": str(self.placebo_delta),
            "reasons": list(self.reasons),
            "pair_scores": [item.as_dict() for item in self.pair_scores],
        }


def decide_module_retention(
    pair_scores: Sequence[ModulePairScore],
    *,
    placebo_delta: Decimal,
) -> ModuleRetentionDecision:
    if len(pair_scores) != 6:
        raise ValueError("module retention requires exactly six pair scores")
    modules = {item.module_id for item in pair_scores}
    if len(modules) != 1:
        raise ValueError("pair scores must describe one module")
    roles = {item.role for item in pair_scores}
    if roles != set(ModuleRetestRole):
        raise ValueError("pair scores must contain every module retest role exactly once")
    ids = tuple(item.case_id for item in pair_scores)
    if len(ids) != len(set(ids)):
        raise ValueError("pair score case IDs must be unique")
    placebo = _decimal(placebo_delta, "placebo_delta")
    deltas = tuple(item.delta for item in pair_scores)
    wins = sum(delta > 0 for delta in deltas)
    median_delta = Decimal(median(deltas))
    reasons: list[str] = []
    if wins < 4:
        reasons.append("FOUR_WINS_REQUIRED")
    if median_delta < Decimal("5"):
        reasons.append("MEDIAN_GAIN_BELOW_FIVE")
    if any(item.critical_regression for item in pair_scores):
        reasons.append("CRITICAL_REGRESSION")
    safe = next(
        item for item in pair_scores if item.role is ModuleRetestRole.SAFE_COUNTERCASE
    )
    if not safe.safe_countercase_pass:
        reasons.append("SAFE_COUNTERCASE_FAILED")
    trap = next(
        item for item in pair_scores if item.role is ModuleRetestRole.CRITICAL_TRAP
    )
    if not trap.critical_trap_pass:
        reasons.append("CRITICAL_TRAP_NOT_PREVENTED")
    if any(not item.specialist_checks_pass for item in pair_scores):
        reasons.append("SPECIALIST_CHECK_FAILED")
    if placebo <= 0:
        reasons.append("PLACEBO_NOT_BEATEN")
    state = "REACTIVATE" if not reasons else "RETIRED_BENCHMARK_UNDERPERFORMER"
    return ModuleRetentionDecision(
        module_id=next(iter(modules)),
        state=state,
        treatment_wins=wins,
        median_paired_delta=median_delta,
        placebo_delta=placebo,
        reasons=tuple(reasons),
        pair_scores=tuple(pair_scores),
    )


def build_module_retest_receipt(
    *,
    run_id: str,
    corpus_sha256: str,
    registry_sha256: str,
    decisions: Sequence[ModuleRetentionDecision],
    execution_artifacts: Sequence[Mapping[str, str]],
    telemetry_state: str,
) -> dict[str, Any]:
    artifacts: list[dict[str, str]] = []
    for item in execution_artifacts:
        artifacts.append(
            {
                "path": _text(item.get("path"), "execution artifact path"),
                "sha256": _sha256(
                    item.get("sha256"), "execution artifact sha256"
                ),
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "complexity_module_retest_receipt_v1",
        "run_id": _text(run_id, "run_id"),
        "corpus_sha256": _sha256(corpus_sha256, "corpus_sha256"),
        "registry_sha256": _sha256(registry_sha256, "registry_sha256"),
        "decisions": [item.as_dict() for item in decisions],
        "execution_artifacts": artifacts,
        "telemetry_state": _text(telemetry_state, "telemetry_state"),
        "authority": {
            "formula": False,
            "inventory": False,
            "physical_execution": False,
            "sensory": False,
            "safety": False,
            "publication": False,
            "release": False,
        },
    }
    payload["semantic_receipt_sha256"] = hashlib.sha256(
        _canonical_bytes(payload)
    ).hexdigest()
    return payload


__all__ = [
    "EXPECTED_MODULE_IDS",
    "ModulePairScore",
    "ModuleRetentionDecision",
    "ModuleRetestArm",
    "ModuleRetestCase",
    "ModuleRetestRequest",
    "ModuleRetestRole",
    "build_module_retest_receipt",
    "decide_module_retention",
    "group_cases",
    "load_module_retest_cases",
    "prepare_module_retest_request",
]
