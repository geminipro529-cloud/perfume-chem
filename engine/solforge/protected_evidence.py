"""Protected deterministic evidence capsules for SolForge benchmarks.

The model contributes only a secondary explanation.  Objective evidence fields
are copied from a closed :class:`EvidenceDeltaReceiptV1` and are validated again
when the three benchmark conditions are assembled.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from engine.evidence.augmentation import (
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
)
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.adapters import (
    analyze_execution_receipt,
    audit_execution_receipt_v2,
    build_criterion_fit_packet_v2,
    build_temporal_packet,
)
from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    BenchmarkCaseV1,
    ConditionKind,
    ConditionOutputV1,
    FrozenSolOutputV1,
    InvariantScoreV1,
    score_invariants,
    validate_frozen_sol_output,
)
from engine.solforge.contracts import ExecutionReceiptV1


class ProtectedEvidenceModule(str, Enum):
    TEMPORAL_SENSORY_LEDGER = "TEMPORAL_SENSORY_LEDGER"
    HEDONIC_PREFERENCE_LEARNER = "HEDONIC_PREFERENCE_LEARNER"


_RECEIPT_MODULE_IDS = {
    ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER: "temporal_sensory_ledger",
    ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER: "hedonic_preference",
}

_DECISIONS = {
    EvidenceAugmentationState.AUGMENT: "PROPOSED",
    EvidenceAugmentationState.NO_AUGMENTATION: "NO_CHANGE",
    EvidenceAugmentationState.HOLD: "HOLD",
}

_PROTECTED_SCORE_INVARIANTS = (
    "valid_json_object",
    "decision_matches_objective_receipt",
    "intervention_count_matches_objective_receipt",
    "objective_receipt_exact",
    "objective_receipt_hash_exact",
    "execution_receipt_binding",
    "criterion_isolation",
    "next_comparison_present",
    "authority_false",
)

_UNTRUSTED_EXPLANATION_RE = re.compile(
    r"\b(?:we|the panel|assessors?)\s+"
    r"(?:smelled|observed|perceived|preferred)\b"
    r"|\b(?:safe|safety[- ]cleared|release[- ]ready|physically validated)\b",
    re.IGNORECASE,
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _sha(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be a lower-case SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ProtectedEvidenceBenchmarkCaseV1:
    """A public benchmark case bound to the exact execution it asks Sol to audit."""

    case: BenchmarkCaseV1
    execution: ExecutionReceiptV1

    def __post_init__(self) -> None:
        if not isinstance(self.case, BenchmarkCaseV1):
            raise TypeError("case must be a BenchmarkCaseV1")
        if not isinstance(self.execution, ExecutionReceiptV1):
            raise TypeError("execution must be an ExecutionReceiptV1")
        payload = self.case.input_payload
        if payload.get("execution_receipt") != self.execution.as_dict():
            raise ValueError("public execution receipt does not match execution bytes")
        if payload.get("execution_receipt_sha256") != self.execution.record_sha256:
            raise ValueError("public execution receipt hash does not match execution bytes")
        ProtectedEvidenceModule(payload.get("evidence_module"))

    @property
    def module(self) -> ProtectedEvidenceModule:
        return ProtectedEvidenceModule(self.case.input_payload["evidence_module"])

    def as_dict(self) -> dict[str, object]:
        payload = json.loads(canonical_json_bytes(self.case.as_dict()))
        if not isinstance(payload, dict):  # pragma: no cover - closed case invariant
            raise TypeError("canonical benchmark case must be an object")
        return payload

    @classmethod
    def from_case(cls, case: BenchmarkCaseV1) -> ProtectedEvidenceBenchmarkCaseV1:
        if not isinstance(case, BenchmarkCaseV1):
            raise TypeError("case must be a BenchmarkCaseV1")
        execution = ExecutionReceiptV1.from_dict(
            case.input_payload.get("execution_receipt")
        )
        return cls(case=case, execution=execution)

    @classmethod
    def from_dict(cls, payload: object) -> ProtectedEvidenceBenchmarkCaseV1:
        if not isinstance(payload, dict):
            raise TypeError("protected benchmark case must be an object")
        case = BenchmarkCaseV1.from_dict(payload)
        if canonical_json_bytes(payload) != canonical_json_bytes(case.as_dict()):
            raise ValueError("derived benchmark fields do not match canonical case bytes")
        return cls.from_case(case)


@dataclass(frozen=True, slots=True)
class ProtectedEvidenceCapsuleV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_protected_evidence_capsule_v1"

    case_id: str
    module: ProtectedEvidenceModule
    execution_receipt_sha256: str
    objective_receipt: EvidenceDeltaReceiptV1

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _text(self.case_id, "case_id"))
        object.__setattr__(self, "module", ProtectedEvidenceModule(self.module))
        object.__setattr__(
            self,
            "execution_receipt_sha256",
            _sha(self.execution_receipt_sha256, "execution_receipt_sha256"),
        )
        if not isinstance(self.objective_receipt, EvidenceDeltaReceiptV1):
            raise TypeError("objective_receipt must be an EvidenceDeltaReceiptV1")
        expected_module_id = _RECEIPT_MODULE_IDS[self.module]
        if self.objective_receipt.module_id != expected_module_id:
            raise ValueError(
                "objective receipt module does not match the protected module"
            )

    @property
    def authority_flags(self) -> dict[str, bool]:
        return dict(BENCHMARK_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "module": self.module.value,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "objective_receipt": self.objective_receipt.as_dict(),
            "objective_receipt_sha256": self.objective_receipt.receipt_sha256,
            "authority_flags": self.authority_flags,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def capsule_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> ProtectedEvidenceCapsuleV1:
        if not isinstance(payload, dict):
            raise TypeError("protected capsule payload must be an object")
        fields = {
            "schema_version",
            "case_id",
            "module",
            "execution_receipt_sha256",
            "objective_receipt",
            "objective_receipt_sha256",
            "authority_flags",
        }
        unknown = set(payload).difference(fields)
        missing = fields.difference(payload)
        if unknown:
            raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
        if missing:
            raise ValueError("missing fields: " + ", ".join(sorted(missing)))
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        if payload["authority_flags"] != BENCHMARK_AUTHORITY_FLAGS:
            raise ValueError("authority_flags must be the exact all-false mapping")
        receipt = EvidenceDeltaReceiptV1.from_dict(payload["objective_receipt"])
        if payload["objective_receipt_sha256"] != receipt.receipt_sha256:
            raise ValueError("objective receipt hash does not match receipt bytes")
        return cls(
            case_id=payload["case_id"],
            module=ProtectedEvidenceModule(payload["module"]),
            execution_receipt_sha256=payload["execution_receipt_sha256"],
            objective_receipt=receipt,
        )


@dataclass(frozen=True, slots=True)
class ProtectedConditionSetV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_protected_condition_set_v1"

    capsule: ProtectedEvidenceCapsuleV1
    frozen_sol_output_sha256: str
    conditions: tuple[ConditionOutputV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.capsule, ProtectedEvidenceCapsuleV1):
            raise TypeError("capsule must be a ProtectedEvidenceCapsuleV1")
        object.__setattr__(
            self,
            "frozen_sol_output_sha256",
            _sha(self.frozen_sol_output_sha256, "frozen_sol_output_sha256"),
        )
        conditions = tuple(self.conditions)
        if any(not isinstance(item, ConditionOutputV1) for item in conditions):
            raise TypeError("conditions must contain ConditionOutputV1 values")
        object.__setattr__(self, "conditions", conditions)
        by_kind = {item.condition: item for item in conditions}
        if len(conditions) != len(ConditionKind) or set(by_kind) != set(ConditionKind):
            raise ValueError("protected condition set must contain each condition once")
        if any(item.case_id != self.capsule.case_id for item in conditions):
            raise ValueError("protected conditions do not match capsule case")
        if any(
            item.frozen_sol_output_sha256 != self.frozen_sol_output_sha256
            for item in conditions
        ):
            raise ValueError("protected conditions must bind one frozen Sol output")
        treatment = by_kind[ConditionKind.SOLFORGE]
        no_op = by_kind[ConditionKind.NO_OP_LENGTH_MATCHED]
        if len(treatment.output_text.encode("utf-8")) != len(
            no_op.output_text.encode("utf-8")
        ):
            raise ValueError("protected treatment and no-op output lengths differ")
        try:
            payload = json.loads(treatment.output_text.rstrip())
        except json.JSONDecodeError as exc:
            raise ValueError("protected treatment output is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("protected treatment output must be an object")
        embedded = EvidenceDeltaReceiptV1.from_dict(payload.get("objective_receipt"))
        if embedded != self.capsule.objective_receipt:
            raise ValueError("protected objective receipt does not match capsule")
        if payload.get("objective_receipt_sha256") != embedded.receipt_sha256:
            raise ValueError("protected objective receipt hash does not match")
        if payload.get("execution_receipt_sha256") != self.capsule.execution_receipt_sha256:
            raise ValueError("protected execution receipt binding does not match")
        if payload.get("capsule_sha256") != self.capsule.capsule_sha256:
            raise ValueError("protected capsule hash does not match")
        if payload.get("decision") != _DECISIONS[embedded.state]:
            raise ValueError("protected decision does not match objective receipt")
        if payload.get("authority_flags") != BENCHMARK_AUTHORITY_FLAGS:
            raise ValueError("protected authority flags must remain false")
        interventions = payload.get("interventions")
        expected_count = 1 if embedded.state is EvidenceAugmentationState.AUGMENT else 0
        if not isinstance(interventions, list) or len(interventions) != expected_count:
            raise ValueError("protected evidence must emit zero or one intervention")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capsule": self.capsule.as_dict(),
            "capsule_sha256": self.capsule.capsule_sha256,
            "frozen_sol_output_sha256": self.frozen_sol_output_sha256,
            "conditions": [item.as_dict() for item in self.conditions],
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }

    @classmethod
    def from_dict(cls, payload: object) -> ProtectedConditionSetV1:
        if not isinstance(payload, dict):
            raise TypeError("protected condition set must be an object")
        fields = {
            "schema_version",
            "capsule",
            "capsule_sha256",
            "frozen_sol_output_sha256",
            "conditions",
            "authority_flags",
        }
        unknown = set(payload).difference(fields)
        missing = fields.difference(payload)
        if unknown:
            raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
        if missing:
            raise ValueError("missing fields: " + ", ".join(sorted(missing)))
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        if payload["authority_flags"] != BENCHMARK_AUTHORITY_FLAGS:
            raise ValueError("authority_flags must be the exact all-false mapping")
        capsule = ProtectedEvidenceCapsuleV1.from_dict(payload["capsule"])
        if payload["capsule_sha256"] != capsule.capsule_sha256:
            raise ValueError("capsule hash does not match capsule bytes")
        rows = payload["conditions"]
        if not isinstance(rows, list):
            raise TypeError("conditions must be a list")
        return cls(
            capsule=capsule,
            frozen_sol_output_sha256=payload["frozen_sol_output_sha256"],
            conditions=tuple(ConditionOutputV1.from_dict(item) for item in rows),
        )


def build_protected_evidence_capsule(
    *,
    case_id: str,
    module: ProtectedEvidenceModule,
    execution_receipt_sha256: str,
    objective_receipt: EvidenceDeltaReceiptV1,
) -> ProtectedEvidenceCapsuleV1:
    return ProtectedEvidenceCapsuleV1(
        case_id=case_id,
        module=module,
        execution_receipt_sha256=execution_receipt_sha256,
        objective_receipt=objective_receipt,
    )


def build_protected_evidence_capsule_from_execution(
    case: BenchmarkCaseV1,
    execution: ExecutionReceiptV1,
) -> ProtectedEvidenceCapsuleV1:
    """Derive the protected objective receipt from bound execution evidence."""

    if not isinstance(case, BenchmarkCaseV1):
        raise TypeError("case must be a BenchmarkCaseV1")
    if not isinstance(execution, ExecutionReceiptV1):
        raise TypeError("execution must be an ExecutionReceiptV1")
    module = ProtectedEvidenceModule(case.input_payload.get("evidence_module"))
    if module is ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER:
        objective_receipt = audit_execution_receipt_v2(execution).receipt
    else:
        criterion = _text(case.input_payload.get("criterion"), "criterion").upper()
        if criterion != "LIKING":
            raise ValueError("hedonic protected evidence requires criterion LIKING")
        temporal_result = analyze_execution_receipt(execution)
        temporal_packet = build_temporal_packet(execution, temporal_result)
        objective_receipt = build_criterion_fit_packet_v2(
            execution,
            temporal_packet,
            criterion=criterion,
        ).evidence_delta_receipt
    return build_protected_evidence_capsule(
        case_id=case.case_id,
        module=module,
        execution_receipt_sha256=execution.record_sha256,
        objective_receipt=objective_receipt,
    )


def _secondary_explanation(output_text: str) -> tuple[str, str]:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError:
        return (
            "WITHHELD_UNSTRUCTURED",
            "Model explanation withheld because it was not structured JSON.",
        )
    if not isinstance(payload, dict):
        return (
            "WITHHELD_UNSTRUCTURED",
            "Model explanation withheld because it was not a JSON object.",
        )
    for field_name in ("target_linked_reasoning", "explanation", "rationale"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            normalized = " ".join(value.split())
            if _UNTRUSTED_EXPLANATION_RE.search(normalized):
                return (
                    "WITHHELD_UNTRUSTED_CLAIM",
                    "Model explanation withheld because it attempted an unverified "
                    "evidence or authority claim.",
                )
            return "ACCEPTED_NONAUTHORITATIVE", normalized
    return "ABSENT", "No secondary model explanation was supplied."


def _protected_payload(
    case: BenchmarkCaseV1,
    frozen: FrozenSolOutputV1,
    capsule: ProtectedEvidenceCapsuleV1,
) -> dict[str, Any]:
    receipt = capsule.objective_receipt
    explanation_state, explanation = _secondary_explanation(frozen.output_text)
    evidence_summary: dict[str, object] | None = None
    next_comparison = receipt.next_action
    if capsule.module is ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER:
        execution_payload = case.input_payload.get("execution_receipt")
        try:
            execution = ExecutionReceiptV1.from_dict(execution_payload)
        except (KeyError, TypeError, ValueError):
            execution = None
        if (
            execution is not None
            and execution.record_sha256 == capsule.execution_receipt_sha256
        ):
            audit = audit_execution_receipt_v2(execution)
            if audit.receipt != receipt:
                raise ValueError(
                    "protected temporal audit does not match the objective receipt"
                )
            evidence_summary = {
                "disposition": audit.disposition.value,
                "source_cell_count": audit.source_cell_count,
                "observed_cell_count": audit.legacy_result.observed_cell_count,
                "missing_cell_count": len(audit.missing_cells),
                "duplicate_cell_count": len(audit.duplicate_cells),
                "excluded_duplicate_row_count": audit.excluded_duplicate_row_count,
                "order_balance_state": audit.legacy_result.order_balance_state.value,
                "assessor_reliability_state": (
                    audit.legacy_result.assessor_reliability_state.value
                ),
                "summaries": [
                    {
                        "sample_id": item.sample_id,
                        "endpoint_id": item.endpoint_id,
                        "time_seconds": item.time_seconds,
                        "observed_count": item.observed_count,
                        "median": item.median,
                        "first_quartile": item.first_quartile,
                        "third_quartile": item.third_quartile,
                        "assessor_disagreement": item.assessor_disagreement,
                    }
                    for item in audit.summaries
                ],
                "transitions": [
                    {
                        "sample_id": item.sample_id,
                        "endpoint_id": item.endpoint_id,
                        "from_time_seconds": item.from_time_seconds,
                        "to_time_seconds": item.to_time_seconds,
                        "median_delta": item.median_delta,
                    }
                    for item in audit.transitions
                ],
            }
            next_comparison = audit.next_discriminator
    intervention: list[dict[str, object]] = []
    if receipt.state is EvidenceAugmentationState.AUGMENT:
        if receipt.delta is None:  # pragma: no cover - closed receipt invariant
            raise ValueError("AUGMENT receipt is missing its decision delta")
        intervention.append(
            {
                "kind": "EVIDENCE_DELTA",
                "status": "EVIDENCE_ONLY_NOT_AUTHORIZED",
                "delta": receipt.delta.as_dict(),
            }
        )
    payload: dict[str, Any] = {
        "decision": _DECISIONS[receipt.state],
        "interventions": intervention,
        "blockers": list(receipt.blockers),
        "criterion": case.input_payload.get("criterion"),
        "next_comparison": next_comparison
        or "STOP_EXACT_SCOPE:no additional comparison is justified by this receipt.",
        "objective_receipt": receipt.as_dict(),
        "objective_receipt_sha256": receipt.receipt_sha256,
        "execution_receipt_sha256": capsule.execution_receipt_sha256,
        "capsule_sha256": capsule.capsule_sha256,
        "frozen_sol_output_sha256": frozen.record_sha256,
        "secondary_explanation": explanation,
        "secondary_explanation_state": explanation_state,
        "secondary_explanation_authority": "NONE",
        "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
    }
    if evidence_summary is not None:
        payload["evidence_summary"] = evidence_summary
    return payload


def _condition(
    case: BenchmarkCaseV1,
    frozen: FrozenSolOutputV1,
    kind: ConditionKind,
    output_text: str,
    *,
    length_tolerance_bytes: int = 0,
) -> ConditionOutputV1:
    return ConditionOutputV1(
        case_id=case.case_id,
        phase=case.phase,
        condition=kind,
        frozen_sol_output_sha256=frozen.record_sha256,
        output_text=output_text,
        output_sha256=sha256_hex(output_text.encode("utf-8")),
        length_tolerance_bytes=length_tolerance_bytes,
    )


def compile_protected_evidence_conditions(
    case: BenchmarkCaseV1,
    frozen: FrozenSolOutputV1,
    capsule: ProtectedEvidenceCapsuleV1,
    *,
    length_tolerance_bytes: int = 0,
) -> ProtectedConditionSetV1:
    """Build plain, no-op, and protected conditions from one frozen Sol output."""

    validate_frozen_sol_output(case, frozen)
    if capsule.case_id != case.case_id:
        raise ValueError("capsule case does not match benchmark case")
    declared_module = case.input_payload.get("evidence_module")
    if declared_module != capsule.module.value:
        raise ValueError("capsule module does not match benchmark case")
    governed = canonical_json_bytes(
        _protected_payload(case, frozen, capsule)
    ).decode("utf-8")
    governed_bytes = len(governed.encode("utf-8"))
    raw_bytes = len(frozen.output_text.encode("utf-8"))
    target_bytes = max(governed_bytes, raw_bytes)
    no_op = frozen.output_text + (" " * (target_bytes - raw_bytes))
    governed = governed + (" " * (target_bytes - governed_bytes))
    conditions = (
        _condition(case, frozen, ConditionKind.PLAIN_SOL, frozen.output_text),
        _condition(
            case,
            frozen,
            ConditionKind.NO_OP_LENGTH_MATCHED,
            no_op,
            length_tolerance_bytes=length_tolerance_bytes,
        ),
        _condition(case, frozen, ConditionKind.SOLFORGE, governed),
    )
    return ProtectedConditionSetV1(
        capsule=capsule,
        frozen_sol_output_sha256=frozen.record_sha256,
        conditions=conditions,
    )


def _parsed_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text.rstrip())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _embedded_receipt(payload: dict[str, Any]) -> EvidenceDeltaReceiptV1 | None:
    try:
        return EvidenceDeltaReceiptV1.from_dict(payload.get("objective_receipt"))
    except (KeyError, TypeError, ValueError):
        return None


def score_protected_evidence_invariants(
    benchmark_case: ProtectedEvidenceBenchmarkCaseV1,
    condition_set: ProtectedConditionSetV1,
) -> tuple[InvariantScoreV1, ...]:
    """Score objective receipt integrity while retaining general critical checks."""

    if not isinstance(benchmark_case, ProtectedEvidenceBenchmarkCaseV1):
        raise TypeError("benchmark_case must be a ProtectedEvidenceBenchmarkCaseV1")
    if not isinstance(condition_set, ProtectedConditionSetV1):
        raise TypeError("condition_set must be a ProtectedConditionSetV1")
    case = benchmark_case.case
    capsule = condition_set.capsule
    if capsule.case_id != case.case_id or capsule.module is not benchmark_case.module:
        raise ValueError("protected condition set does not match benchmark case")
    if capsule.execution_receipt_sha256 != benchmark_case.execution.record_sha256:
        raise ValueError("protected capsule does not bind the public execution receipt")

    expected_receipt = capsule.objective_receipt
    expected_decision = _DECISIONS[expected_receipt.state]
    expected_interventions = (
        1 if expected_receipt.state is EvidenceAugmentationState.AUGMENT else 0
    )
    expected_criterion = case.input_payload.get("criterion")
    general = {
        item.condition: item
        for item in score_invariants(case, condition_set.conditions)
    }
    scores: list[InvariantScoreV1] = []
    for condition in condition_set.conditions:
        payload = _parsed_object(condition.output_text)
        receipt = _embedded_receipt(payload) if payload else None
        interventions = payload.get("interventions")
        checks = {
            "valid_json_object": bool(payload),
            "decision_matches_objective_receipt": (
                payload.get("decision") == expected_decision
            ),
            "intervention_count_matches_objective_receipt": (
                isinstance(interventions, list)
                and len(interventions) == expected_interventions
            ),
            "objective_receipt_exact": receipt == expected_receipt,
            "objective_receipt_hash_exact": (
                receipt is not None
                and payload.get("objective_receipt_sha256")
                == expected_receipt.receipt_sha256
            ),
            "execution_receipt_binding": (
                payload.get("execution_receipt_sha256")
                == benchmark_case.execution.record_sha256
            ),
            "criterion_isolation": payload.get("criterion") == expected_criterion,
            "next_comparison_present": (
                isinstance(payload.get("next_comparison"), str)
                and bool(payload["next_comparison"].strip())
            ),
            "authority_false": (
                payload.get("authority_flags") == BENCHMARK_AUTHORITY_FLAGS
            ),
        }
        passed = tuple(name for name in _PROTECTED_SCORE_INVARIANTS if checks[name])
        failed = tuple(
            name for name in _PROTECTED_SCORE_INVARIANTS if not checks[name]
        )
        critical = list(general[condition.condition].critical_errors)
        if payload.get("objective_receipt") is not None and receipt != expected_receipt:
            critical.append("OBJECTIVE_RECEIPT_TAMPER")
        execution_binding = payload.get("execution_receipt_sha256")
        if (
            execution_binding is not None
            and execution_binding != benchmark_case.execution.record_sha256
        ):
            critical.append("EXECUTION_BINDING_TAMPER")
        if (
            expected_decision in {"HOLD", "NO_CHANGE"}
            and payload.get("decision") == "PROPOSED"
        ):
            critical.append("OBJECTIVE_STATE_OVERRIDE")
        scores.append(
            InvariantScoreV1(
                case_id=case.case_id,
                condition=condition.condition,
                frozen_sol_output_sha256=condition.frozen_sol_output_sha256,
                passed_invariants=passed,
                failed_invariants=failed,
                critical_errors=tuple(sorted(set(critical))),
                score=round(100 * len(passed) / len(_PROTECTED_SCORE_INVARIANTS)),
            )
        )
    return tuple(scores)


__all__ = [
    "ProtectedConditionSetV1",
    "ProtectedEvidenceBenchmarkCaseV1",
    "ProtectedEvidenceCapsuleV1",
    "ProtectedEvidenceModule",
    "build_protected_evidence_capsule",
    "build_protected_evidence_capsule_from_execution",
    "compile_protected_evidence_conditions",
    "score_protected_evidence_invariants",
]
