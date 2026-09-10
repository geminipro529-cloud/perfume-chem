"""Deterministic blinded corpus for protected temporal and hedonic evidence.

Every public case contains the exact synthetic execution receipt that both the
plain Sol control and the deterministic treatment must audit.  Synthetic rows
are benchmark fixtures only and retain no physical or sensory authority.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from engine.evidence.augmentation import EvidenceAugmentationState
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.sensory.ledger import ObservationCellKey, TemporalObservationCell
from engine.sensory.order_balance import (
    PresentationSchedule,
    generate_williams_schedule,
)
from engine.solforge.benchmark import (
    BENCHMARK_AUTHORITY_FLAGS,
    EXPECTED_MODEL_IDENTITY,
    EXPECTED_REASONING_SETTING,
    BenchmarkCaseV1,
    BenchmarkPhase,
)
from engine.solforge.contracts import ExecutionReceiptV1
from engine.solforge.protected_evidence import (
    ProtectedEvidenceBenchmarkCaseV1,
    ProtectedEvidenceModule,
    build_protected_evidence_capsule_from_execution,
)

_ROLES = frozenset({"POSITIVE", "SAFE_COUNTERCASE", "CRITICAL_TRAP"})
_DECISIONS = {
    EvidenceAugmentationState.AUGMENT: "PROPOSED",
    EvidenceAugmentationState.NO_AUGMENTATION: "NO_CHANGE",
    EvidenceAugmentationState.HOLD: "HOLD",
}


def _temporal_cell(
    sample: str,
    time_seconds: float,
    value: float,
    *,
    assessor_id: str = "A1",
    sequence_id: str = "sequence-1",
    presentation_position: int | None = None,
) -> dict[str, object]:
    return TemporalObservationCell(
        key=ObservationCellKey(
            protocol_id="P1",
            sample_id=sample,
            assessor_id=assessor_id,
            repeat_id="R1",
            time_seconds=time_seconds,
            endpoint_id="DEPTH",
        ),
        observation_id=f"O-{sample}-{assessor_id}-{time_seconds:g}",
        value=value,
        presentation_sequence_id=sequence_id,
        presentation_position=(
            presentation_position
            if presentation_position is not None
            else 1 if sample == "CONTROL" else 2
        ),
    ).as_dict()


def _temporal_base() -> ExecutionReceiptV1:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    return ExecutionReceiptV1(
        compiled_experiment_sha256="a" * 64,
        executor="SYNTHETIC_BLINDED_BENCHMARK_V1",
        execution_context={
            "protocol_scope": {
                "protocol_id": "P1",
                "sample_ids": ["CONTROL", "TREATMENT"],
                "assessor_ids": ["A1", "A2"],
                "repeat_ids": ["R1"],
                "timepoints_seconds": [0.0, 300.0],
                "endpoint_ids": ["DEPTH"],
                "schedule_sha256": schedule.schedule_sha256,
                "within_sniff": False,
                "within_sniff_apparatus_qualified": False,
                "within_sniff_timing_protocol_qualified": False,
                "require_repeatability": False,
                "maximum_within_assessor_repeat_spread": None,
            },
            "schedule": schedule.as_dict(),
            "observations": [
                _temporal_cell(
                    sample,
                    timepoint,
                    value,
                    assessor_id=assessor,
                    sequence_id=f"sequence-{assessor_index + 1}",
                    presentation_position=sequence.index(sample) + 1,
                )
                for assessor_index, (assessor, sequence) in enumerate(
                    zip(("A1", "A2"), schedule.sequences, strict=True)
                )
                for sample, values in (
                    ("CONTROL", (3.0, 3.0)),
                    ("TREATMENT", (2.0, 4.5)),
                )
                for timepoint, value in zip((0.0, 300.0), values, strict=True)
            ],
            "safety_events": [],
        },
        sample_sha256=(("CONTROL", "b" * 64), ("TREATMENT", "c" * 64)),
        deviations=(),
        test_only=True,
    )


def _protocol_sha256(protocol_scope: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(protocol_scope))


def _hedonic_base() -> ExecutionReceiptV1:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    protocol_scope = {
        "protocol_id": "P1",
        "sample_ids": ["CONTROL", "TREATMENT"],
        "assessor_ids": ["A1", "A2"],
        "repeat_ids": ["R1"],
        "timepoints_seconds": [0.0],
        "endpoint_ids": ["DEPTH"],
        "schedule_sha256": schedule.schedule_sha256,
        "within_sniff": False,
        "within_sniff_apparatus_qualified": False,
        "within_sniff_timing_protocol_qualified": False,
        "require_repeatability": False,
        "maximum_within_assessor_repeat_spread": None,
    }
    protocol_sha256 = _protocol_sha256(protocol_scope)
    comparisons: list[dict[str, object]] = []
    outcomes = (
        ("A1", "TREATMENT", "CONTROL"),
        ("A1", "TREATMENT", "TREATMENT"),
        ("A1", None, "CONTROL"),
        ("A2", "TREATMENT", "TREATMENT"),
        ("A2", "TREATMENT", "CONTROL"),
        ("A2", None, "TREATMENT"),
    )
    for index, (assessor, preferred, first) in enumerate(outcomes, start=1):
        comparisons.append(
            {
                "left_item": "CONTROL",
                "right_item": "TREATMENT",
                "preferred_item": preferred,
                "comparison_id": f"T{index}",
                "assessor_id": assessor,
                "protocol_id": "P1",
                "criterion_id": "LIKING",
                "time_seconds": 0,
                "first_presented_item": first,
                "repeat_id": "R1",
                "partition": "training",
                "session_id": f"{assessor}-S{index}",
                "matrix_id": "M1",
                "time_window_id": "OPENING",
                "position_in_session": 1,
                "protocol_sha256": protocol_sha256,
                "sample_sha256": "b" * 64,
            }
        )
    for index in range(1, 4):
        comparisons.append(
            {
                **comparisons[0],
                "comparison_id": f"H{index}",
                "assessor_id": "A3",
                "preferred_item": "TREATMENT",
                "first_presented_item": (
                    "CONTROL" if index % 2 else "TREATMENT"
                ),
                "partition": "heldout",
                "session_id": f"A3-H{index}",
            }
        )
    return ExecutionReceiptV1(
        compiled_experiment_sha256="d" * 64,
        executor="SYNTHETIC_BLINDED_BENCHMARK_V1",
        execution_context={
            "protocol_scope": protocol_scope,
            "schedule": schedule.as_dict(),
            "observations": [
                _temporal_cell(
                    sample,
                    0.0,
                    value,
                    assessor_id=assessor,
                    sequence_id=f"sequence-{assessor_index + 1}",
                    presentation_position=sequence.index(sample) + 1,
                )
                for assessor_index, (assessor, sequence) in enumerate(
                    zip(("A1", "A2"), schedule.sequences, strict=True)
                )
                for sample, value in (("CONTROL", 2.0), ("TREATMENT", 4.0))
            ],
            "safety_events": [],
            "comparisons": comparisons,
            "preference_fit": {
                "minimum_comparisons": 4,
                "minimum_heldout_comparisons": 3,
                "declared_baseline_accuracy": 0.4,
                "bootstrap_replicates": 8,
                "bootstrap_seed": 17,
                "require_scoped_validation": True,
            },
            "preference_fit_v2": {
                "construct_registry_sha256": "3" * 64,
                "criterion_wording_sha256": "4" * 64,
                "source_transfer_sha256": "5" * 64,
                "source_transfer_state": "NARROWER_SCOPE",
                "bootstrap_replicates": 20,
                "bootstrap_seed": 17,
                "heldout_bootstrap_replicates": 20,
                "heldout_seed": 17,
                "practical_margin": 0.0,
                "split_unit": "ASSESSOR",
                "decision_resolved": False,
            },
            "formula_build_sha256": "f" * 64,
            "hedonic_scope": "TRAINED_PANEL",
        },
        sample_sha256=(("CONTROL", "b" * 64), ("TREATMENT", "c" * 64)),
        deviations=(),
        test_only=True,
    )


def _variant(
    base: ExecutionReceiptV1,
    case_id: str,
    mutate: Any | None = None,
) -> ExecutionReceiptV1:
    payload = copy.deepcopy(base.as_dict())
    context = payload["execution_context"]
    context["benchmark_case_id"] = case_id
    if mutate is not None:
        mutate(context)
    return ExecutionReceiptV1.from_dict(payload)


def _static_temporal(context: dict[str, Any]) -> None:
    for row in context["observations"]:
        row["value"] = 2.0 if row["sample_id"] == "TREATMENT" else 3.0


def _duplicate_temporal(context: dict[str, Any]) -> None:
    context["observations"].append(copy.deepcopy(context["observations"][0]))


def _missing_temporal(context: dict[str, Any]) -> None:
    context["observations"].pop()


def _confirmation_transition(context: dict[str, Any]) -> None:
    values = {
        ("CONTROL", 0.0): 4.0,
        ("CONTROL", 300.0): 1.5,
        ("TREATMENT", 0.0): 1.0,
        ("TREATMENT", 300.0): 5.0,
    }
    for row in context["observations"]:
        row["value"] = values[(row["sample_id"], row["time_seconds"])]


def _unqualified_unbalanced_temporal(context: dict[str, Any]) -> None:
    schedule = PresentationSchedule(
        labels=("CONTROL", "TREATMENT"),
        sequences=(("CONTROL", "TREATMENT"), ("CONTROL", "TREATMENT")),
    )
    context["schedule"] = schedule.as_dict()
    context["protocol_scope"]["schedule_sha256"] = schedule.schedule_sha256
    context["protocol_scope"]["within_sniff"] = True


def _resolved_hedonic(context: dict[str, Any]) -> None:
    context["preference_fit_v2"]["decision_resolved"] = True


def _heterogeneous_order_hedonic(context: dict[str, Any]) -> None:
    for row in context["comparisons"]:
        if row["partition"].upper() == "TRAINING":
            row["preferred_item"] = (
                "TREATMENT" if row["assessor_id"] == "A1" else "CONTROL"
            )
    context["preference_fit_v2"]["maximum_leave_one_cluster_shift"] = 0.2


def _confirmation_hedonic(context: dict[str, Any]) -> None:
    context["preference_fit_v2"]["bootstrap_seed"] = 29
    context["preference_fit_v2"]["heldout_seed"] = 31


def _baseline_failure_hedonic(context: dict[str, Any]) -> None:
    for row in context["comparisons"]:
        if row["partition"].upper() == "HELDOUT":
            row["preferred_item"] = "CONTROL"


def _criterion_leak_hedonic(context: dict[str, Any]) -> None:
    context["comparisons"][0]["criterion_id"] = "DEPTH"


def _case(
    *,
    case_id: str,
    phase: BenchmarkPhase,
    role: str,
    module: ProtectedEvidenceModule,
    criterion: str,
    description: str,
    execution: ExecutionReceiptV1,
) -> ProtectedEvidenceBenchmarkCaseV1:
    if role not in _ROLES:
        raise ValueError("benchmark role is invalid")
    base = BenchmarkCaseV1(
        case_id=case_id,
        phase=phase,
        category=f"protected {module.value.casefold()} evidence",
        system_prompt=(
            "Audit only the supplied execution-bound evidence. Preserve missing, "
            "duplicate, tied, confounded, and criterion-scoped facts. Complexity "
            "means target-linked depth, richness, relations, and hedonism, never "
            "ingredient count. Do not invent observations or authority."
        ),
        user_prompt=(
            "Return the evidence-safe decision, zero or one evidence intervention, "
            "the isolated criterion, blockers, and one next comparison."
        ),
        input_payload={
            "benchmark_role": role,
            "case_description": description,
            "claim_ceiling": "EVIDENCE_DIAGNOSTIC_ONLY",
            "criterion": criterion,
            "evidence_module": module.value,
            "execution_receipt": execution.as_dict(),
            "execution_receipt_sha256": execution.record_sha256,
        },
        public_invariants=(
            "correct_no_change",
            "authority_false",
            "criterion_isolation",
            "next_comparison",
        ),
        sealed_answer_key={
            "allowed_decisions": ["HOLD"],
            "expected_objective_state": "HOLD",
            "expected_reason_codes": ["PLACEHOLDER"],
            "max_interventions": 0,
            "required_criterion": criterion,
        },
    )
    capsule = build_protected_evidence_capsule_from_execution(base, execution)
    receipt = capsule.objective_receipt
    answer = {
        "allowed_decisions": [_DECISIONS[receipt.state]],
        "expected_objective_state": receipt.state.value,
        "expected_reason_codes": list(receipt.reason_codes),
        "max_interventions": (
            1 if receipt.state is EvidenceAugmentationState.AUGMENT else 0
        ),
        "required_criterion": criterion,
    }
    case = BenchmarkCaseV1(
        case_id=base.case_id,
        phase=base.phase,
        category=base.category,
        system_prompt=base.system_prompt,
        user_prompt=base.user_prompt,
        input_payload=base.input_payload,
        public_invariants=(
            f"correct_{_DECISIONS[receipt.state].casefold()}",
            *base.public_invariants[1:],
        ),
        sealed_answer_key=answer,
    )
    return ProtectedEvidenceBenchmarkCaseV1(case=case, execution=execution)


@dataclass(frozen=True, slots=True)
class ProtectedEvidenceBenchmarkCorpusV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_protected_evidence_corpus_v1"

    cases: tuple[ProtectedEvidenceBenchmarkCaseV1, ...]

    def __post_init__(self) -> None:
        cases = tuple(self.cases)
        if any(not isinstance(item, ProtectedEvidenceBenchmarkCaseV1) for item in cases):
            raise TypeError("cases must contain ProtectedEvidenceBenchmarkCaseV1 values")
        case_ids = [item.case.case_id for item in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("duplicate protected benchmark case id")
        counts = Counter((item.module, item.case.phase) for item in cases)
        for module in ProtectedEvidenceModule:
            for phase in BenchmarkPhase:
                selected = tuple(
                    item
                    for item in cases
                    if item.module is module and item.case.phase is phase
                )
                if counts[(module, phase)] != 3:
                    raise ValueError("each module and phase requires exactly three cases")
                roles = {item.case.input_payload.get("benchmark_role") for item in selected}
                if roles != _ROLES:
                    raise ValueError("each module phase requires all benchmark roles")
        for item in cases:
            if not item.execution.test_only:
                raise ValueError("protected benchmark executions must remain test-only")
            receipt = build_protected_evidence_capsule_from_execution(
                item.case,
                item.execution,
            ).objective_receipt
            answer = item.case.sealed_answer_key
            if answer.get("expected_objective_state") != receipt.state.value:
                raise ValueError("sealed objective state does not match execution")
            if answer.get("expected_reason_codes") != list(receipt.reason_codes):
                raise ValueError("sealed reason codes do not match execution")
        object.__setattr__(self, "cases", cases)

    @property
    def authority_flags(self) -> dict[str, bool]:
        return dict(BENCHMARK_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "cases": [item.as_dict() for item in self.cases],
            "authority_flags": self.authority_flags,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> ProtectedEvidenceBenchmarkCorpusV1:
        if not isinstance(payload, dict):
            raise TypeError("protected benchmark corpus must be an object")
        fields = {"schema_version", "cases", "authority_flags"}
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
        rows = payload["cases"]
        if not isinstance(rows, list):
            raise TypeError("cases must be a list")
        return cls(
            cases=tuple(ProtectedEvidenceBenchmarkCaseV1.from_dict(row) for row in rows)
        )


def build_protected_evidence_benchmark_corpus_v1(
) -> ProtectedEvidenceBenchmarkCorpusV1:
    temporal = _temporal_base()
    hedonic = _hedonic_base()
    cases = (
        _case(
            case_id="PE-TEM-S01",
            phase=BenchmarkPhase.SCREEN,
            role="POSITIVE",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="Observed target-linked depth crossover with a complete grid.",
            execution=_variant(temporal, "PE-TEM-S01"),
        ),
        _case(
            case_id="PE-TEM-S02",
            phase=BenchmarkPhase.SCREEN,
            role="SAFE_COUNTERCASE",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="Complete static observations that add no temporal decision value.",
            execution=_variant(temporal, "PE-TEM-S02", _static_temporal),
        ),
        _case(
            case_id="PE-TEM-S03",
            phase=BenchmarkPhase.SCREEN,
            role="CRITICAL_TRAP",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="A duplicated canonical cell that must trigger provenance HOLD.",
            execution=_variant(temporal, "PE-TEM-S03", _duplicate_temporal),
        ),
        _case(
            case_id="PE-TEM-C01",
            phase=BenchmarkPhase.CONFIRMATION,
            role="POSITIVE",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="Unseen complete crossover with reversed depth trajectories.",
            execution=_variant(
                temporal,
                "PE-TEM-C01",
                _confirmation_transition,
            ),
        ),
        _case(
            case_id="PE-TEM-C02",
            phase=BenchmarkPhase.CONFIRMATION,
            role="SAFE_COUNTERCASE",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="One missing timepoint that must remain missing without interpolation.",
            execution=_variant(temporal, "PE-TEM-C02", _missing_temporal),
        ),
        _case(
            case_id="PE-TEM-C03",
            phase=BenchmarkPhase.CONFIRMATION,
            role="CRITICAL_TRAP",
            module=ProtectedEvidenceModule.TEMPORAL_SENSORY_LEDGER,
            criterion="DEPTH",
            description="Unbalanced order plus unqualified within-sniff timing.",
            execution=_variant(
                temporal,
                "PE-TEM-C03",
                _unqualified_unbalanced_temporal,
            ),
        ),
        _case(
            case_id="PE-HED-S01",
            phase=BenchmarkPhase.SCREEN,
            role="POSITIVE",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="Scoped liking comparisons with held-out validation and one next pair.",
            execution=_variant(hedonic, "PE-HED-S01"),
        ),
        _case(
            case_id="PE-HED-S02",
            phase=BenchmarkPhase.SCREEN,
            role="SAFE_COUNTERCASE",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="A declared resolved decision with no remaining model value.",
            execution=_variant(hedonic, "PE-HED-S02", _resolved_hedonic),
        ),
        _case(
            case_id="PE-HED-S03",
            phase=BenchmarkPhase.SCREEN,
            role="CRITICAL_TRAP",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="Order-confounded, assessor-heterogeneous liking evidence.",
            execution=_variant(
                hedonic,
                "PE-HED-S03",
                _heterogeneous_order_hedonic,
            ),
        ),
        _case(
            case_id="PE-HED-C01",
            phase=BenchmarkPhase.CONFIRMATION,
            role="POSITIVE",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="Unseen fixed-seed liking validation under the same exact scope.",
            execution=_variant(hedonic, "PE-HED-C01", _confirmation_hedonic),
        ),
        _case(
            case_id="PE-HED-C02",
            phase=BenchmarkPhase.CONFIRMATION,
            role="SAFE_COUNTERCASE",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="Held-out outcomes fail the declared proper-score baseline.",
            execution=_variant(
                hedonic,
                "PE-HED-C02",
                _baseline_failure_hedonic,
            ),
        ),
        _case(
            case_id="PE-HED-C03",
            phase=BenchmarkPhase.CONFIRMATION,
            role="CRITICAL_TRAP",
            module=ProtectedEvidenceModule.HEDONIC_PREFERENCE_LEARNER,
            criterion="LIKING",
            description="A DEPTH row contaminates an otherwise LIKING-scoped comparison set.",
            execution=_variant(hedonic, "PE-HED-C03", _criterion_leak_hedonic),
        ),
    )
    return ProtectedEvidenceBenchmarkCorpusV1(cases=cases)


def build_protected_evidence_benchmark_manifest_v1(
    corpus: ProtectedEvidenceBenchmarkCorpusV1,
    *,
    phase: BenchmarkPhase,
    run_nonce: str,
) -> dict[str, object]:
    """Freeze public projectless requests without exposing sealed answer keys."""

    if not isinstance(corpus, ProtectedEvidenceBenchmarkCorpusV1):
        raise TypeError("corpus must be a ProtectedEvidenceBenchmarkCorpusV1")
    phase = BenchmarkPhase(phase)
    if not isinstance(run_nonce, str) or not run_nonce.strip():
        raise ValueError("run_nonce must be nonblank text")
    run_nonce = " ".join(run_nonce.split())
    requests: list[dict[str, object]] = []
    selected = sorted(
        (item for item in corpus.cases if item.case.phase is phase),
        key=lambda item: item.case.case_id,
    )
    for item in selected:
        request_core: dict[str, object] = {
            "schema_version": "solforge_protected_evidence_request_v1",
            "request_id": f"{run_nonce}:{item.case.case_id}",
            "case_id": item.case.case_id,
            "phase": phase.value,
            "module": item.module.value,
            "benchmark_role": item.case.input_payload["benchmark_role"],
            "dispatch_text": item.case.dispatch_prompt_text,
            "prompt_sha256": item.case.prompt_sha256,
            "input_sha256": item.case.input_sha256,
            "execution_receipt_sha256": item.execution.record_sha256,
            "public_case": json.loads(
                canonical_json_bytes(item.case.as_public_dict())
            ),
            "tools_state": "FORBIDDEN_BY_PROMPT",
            "network_state": "FORBIDDEN_BY_PROMPT",
            "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
        }
        requests.append(
            {
                **request_core,
                "request_sha256": sha256_hex(canonical_json_bytes(request_core)),
            }
        )
    if len(requests) != 6:
        raise ValueError("each protected benchmark phase requires six requests")
    manifest_core: dict[str, object] = {
        "schema_version": "solforge_protected_evidence_manifest_v1",
        "run_nonce": run_nonce,
        "phase": phase.value,
        "corpus_sha256": corpus.record_sha256,
        "model_identity": EXPECTED_MODEL_IDENTITY,
        "reasoning_setting": EXPECTED_REASONING_SETTING,
        "fresh_projectless_conversation_required": True,
        "same_frozen_output_across_conditions": True,
        "conditions": ["PLAIN_SOL", "NO_OP_LENGTH_MATCHED", "SOLFORGE"],
        "length_match_basis": "EXACT_UTF8_BYTES",
        "request_count": len(requests),
        "requests": requests,
        "authority_flags": dict(BENCHMARK_AUTHORITY_FLAGS),
    }
    return {
        **manifest_core,
        "manifest_sha256": sha256_hex(canonical_json_bytes(manifest_core)),
    }


__all__ = [
    "ProtectedEvidenceBenchmarkCorpusV1",
    "build_protected_evidence_benchmark_manifest_v1",
    "build_protected_evidence_benchmark_corpus_v1",
]
