"""Fresh xhigh admission contracts for evidence-producing complexity modules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
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
_BLINDED_MANIFEST_SCHEMA = "complexity_replacement_benchmark_manifest_v3_blinded"
_BLINDED_RECEIPT_SCHEMA = "complexity_replacement_benchmark_receipt_v3_blinded"


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
    plain_wins = sum(item.delta > 0 for item in plain_control_scores)
    placebo_wins = sum(item.delta > 0 for item in placebo_scores)
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


def load_replacement_benchmark_cases(
    path: Path,
) -> tuple[ReplacementBenchmarkCase, ...]:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in {
        "complexity_replacement_retest_cases_v1",
        "complexity_replacement_retest_cases_v2",
    }:
        raise ValueError("unsupported replacement benchmark corpus schema")
    packets = _load_module_packets(payload.get("module_packets"))
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise TypeError("cases must be a list")
    cases: list[ReplacementBenchmarkCase] = []
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
    requests = []
    for case in cases:
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
                    "nonce": request.nonce,
                    "packet_sha256": request.packet_sha256,
                    "packet_byte_count": request.packet_byte_count,
                    "context_requirement": request.context_requirement,
                }
            )
    manifest: dict[str, Any] = {
        "schema_version": _BLINDED_MANIFEST_SCHEMA,
        "run_nonce": normalized_run_nonce,
        "corpus_sha256": _validated_sha256(corpus_sha256, "corpus_sha256"),
        "rubric_sha256": _validated_sha256(rubric_sha256, "rubric_sha256"),
        "model_identity": normalized_model,
        "request_count": len(requests),
        "requests": requests,
        "old_frozen_requests_resumed": False,
        "admission_policy": {
            "screen": "at least 2/3 wins against each control and zero critical regressions",
            "final": "at least 4/6 wins and median paired gain >= 5 against each control, zero critical errors",
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
                "arm": request["arm"],
                "prompt_sha256": request["prompt_sha256"],
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
        "result_count": len(results),
        "results": results,
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
    prompt_hash = hashlib.sha256(_canonical_bytes(prompt)).hexdigest()
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
        nonce=nonce,
        packet_sha256=packet_hash,
        packet_byte_count=packet_bytes,
    )


__all__ = [
    "REPLACEMENT_MODULE_IDS",
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
]
