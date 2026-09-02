"""Typed, fail-closed observations for the frozen formulation benchmark.

This module does not execute a model, render a prompt, judge an answer, reveal
an arm mapping, or admit runtime code.  It represents the evidence that an
independent benchmark harness must produce and derives a non-compensatory
PASS/FAIL/HOLD evaluation from that evidence.  Admission code must re-run
``evaluate_frozen_benchmark_result``; a serialized evaluation is never a trust
token.

The public corpus and its scorer-only mappings remain separate.  Every
authority outside the exact computational benchmark is permanently withheld.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from math import gcd
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from .benchmark import (
    _ARM_ID_RE,
    PUBLIC_AUTHORITY_EXCLUSIONS,
    ArmPromptReceipt,
    BenchmarkRunReceipt,
    BlindLabelMapping,
    CorpusPartition,
    JudgeReceipt,
    NonCompensatoryGateContract,
    RecursiveClosureReceiptRef,
    RunStatus,
    SealedPublicCorpus,
    _BenchmarkRecord,
    _canonical_json_bytes,
    _digest,
    _digest_tuple,
    _identifier,
    _identifier_tuple,
    _nonnegative_int,
    _record_payload,
    _text,
    _utc_timestamp,
    validate_arm_prompt_receipt,
    validate_blind_label_mapping,
)


def _positive_int(value: object, field_name: str) -> int:
    normalized = _nonnegative_int(value, field_name)
    if normalized == 0:
        raise ValueError(f"{field_name} must be positive")
    return normalized


def _signed_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    return value


def _optional_digest(value: str | None, field_name: str) -> str | None:
    return None if value is None else _digest(value, field_name)


def _optional_text(value: str | None, field_name: str) -> str | None:
    return None if value is None else _text(value, field_name)


def _same_closure(
    left: RecursiveClosureReceiptRef, right: RecursiveClosureReceiptRef
) -> bool:
    return left == right


class BenchmarkArmRole(str, Enum):
    INTEGRATED_CANDIDATE = "integrated_candidate"
    PLAIN_SOL_XHIGH = "plain_sol_xhigh"
    LENGTH_MATCHED_PLACEBO = "length_matched_placebo"
    ABLATION = "ablation"
    SAFE_COUNTERCASE = "safe_countercase"


class ExecutionOrder(str, Enum):
    AB = "ab"
    BA = "ba"


class EvaluationValidity(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"
    ORDER_CONFOUNDED = "order_confounded"
    BLINDING_BREACH = "blinding_breach"
    HASH_MISMATCH = "hash_mismatch"
    WITHHELD = "withheld"


class ObservationDisposition(str, Enum):
    CURRENT = "current"
    PROVENANCE_TOMBSTONE = "provenance_tombstone"
    SUPERSEDED = "superseded"


class PairOutcome(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    TIE = "tie"
    INVALID = "invalid"
    NOT_EVALUABLE = "not_evaluable"


class DerivedPairState(str, Enum):
    INTEGRATED_WIN = "integrated_win"
    COMPARATOR_WIN = "comparator_win"
    TIE = "tie"
    HETEROGENEOUS = "heterogeneous"
    NOT_EVALUABLE = "not_evaluable"


class PartitionScope(str, Enum):
    ALL = "all"
    HELD_OUT = "held_out"


class BenchmarkEvaluationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    HOLD = "hold"


_ADMISSION_CRITICAL_GATE_ROLES = frozenset(
    {
        BenchmarkArmRole.INTEGRATED_CANDIDATE,
        BenchmarkArmRole.SAFE_COUNTERCASE,
    }
)


@dataclass(frozen=True, slots=True)
class ExactRatio(_BenchmarkRecord):
    """Canonical nonnegative ratio for frozen benchmark thresholds."""

    SCHEMA_VERSION = "benchmark_exact_ratio_v1"

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        numerator = _nonnegative_int(self.numerator, "numerator")
        denominator = _positive_int(self.denominator, "denominator")
        if numerator > denominator:
            raise ValueError("benchmark ratios must be between zero and one")
        divisor = gcd(numerator, denominator)
        object.__setattr__(self, "numerator", numerator // divisor)
        object.__setattr__(self, "denominator", denominator // divisor)

    def is_at_least(self, other: ExactRatio) -> bool:
        if not isinstance(other, ExactRatio):
            raise TypeError("other must be ExactRatio")
        return self.numerator * other.denominator >= other.numerator * self.denominator

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ExactRatio:
        data = _record_payload(cls, payload)
        return cls(numerator=data["numerator"], denominator=data["denominator"])


@dataclass(frozen=True, slots=True)
class BenchmarkVerifierIdentity(_BenchmarkRecord):
    """Pinned identity for the deterministic verifier, never a trust assertion."""

    SCHEMA_VERSION = "benchmark_verifier_identity_v1"

    verifier_id: str
    verifier_version: str
    verifier_implementation_sha256: str
    independence_key: str
    deterministic_local_verifier: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "verifier_id", _identifier(self.verifier_id, "verifier_id"))
        object.__setattr__(
            self, "verifier_version", _identifier(self.verifier_version, "verifier_version")
        )
        object.__setattr__(
            self,
            "verifier_implementation_sha256",
            _digest(
                self.verifier_implementation_sha256,
                "verifier_implementation_sha256",
            ),
        )
        object.__setattr__(
            self, "independence_key", _digest(self.independence_key, "independence_key")
        )
        if self.deterministic_local_verifier is not True:
            raise ValueError("benchmark evaluation requires a deterministic local verifier")
        if self.admission_authorized is not False:
            raise ValueError("the benchmark verifier cannot authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BenchmarkVerifierIdentity:
        data = _record_payload(cls, payload)
        return cls(
            verifier_id=data["verifier_id"],
            verifier_version=data["verifier_version"],
            verifier_implementation_sha256=data["verifier_implementation_sha256"],
            independence_key=data["independence_key"],
            deterministic_local_verifier=data["deterministic_local_verifier"],
            admission_authorized=data["admission_authorized"],
        )


@dataclass(frozen=True, slots=True)
class ArmRoleInstruction(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_arm_role_instruction_v1"

    role: BenchmarkArmRole
    instruction_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", BenchmarkArmRole(self.role))
        object.__setattr__(
            self,
            "instruction_sha256",
            _digest(self.instruction_sha256, "instruction_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArmRoleInstruction:
        data = _record_payload(cls, payload)
        return cls(
            role=BenchmarkArmRole(data["role"]),
            instruction_sha256=data["instruction_sha256"],
        )


@dataclass(frozen=True, slots=True)
class ArmRoleAssignment(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_arm_role_assignment_v1"

    arm_id: str
    role: BenchmarkArmRole

    def __post_init__(self) -> None:
        arm_id = _identifier(self.arm_id, "arm_id")
        if not _ARM_ID_RE.fullmatch(arm_id):
            raise ValueError("arm_id must be anonymized")
        object.__setattr__(self, "arm_id", arm_id)
        object.__setattr__(self, "role", BenchmarkArmRole(self.role))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArmRoleAssignment:
        data = _record_payload(cls, payload)
        return cls(arm_id=data["arm_id"], role=BenchmarkArmRole(data["role"]))


@dataclass(frozen=True, slots=True)
class ArmRoleMapping(_BenchmarkRecord):
    """Confidential arm-to-condition mapping supplied only to the evaluator."""

    SCHEMA_VERSION = "benchmark_arm_role_mapping_v1"

    mapping_id: str
    assignments: tuple[ArmRoleAssignment, ...]
    mapping_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mapping_id", _identifier(self.mapping_id, "mapping_id"))
        assignments = tuple(sorted(self.assignments, key=lambda item: item.arm_id))
        if not assignments or any(
            not isinstance(item, ArmRoleAssignment) for item in assignments
        ):
            raise TypeError("assignments must contain ArmRoleAssignment values")
        if len({item.arm_id for item in assignments}) != len(assignments):
            raise ValueError("arm role assignments must use unique arm_id values")
        roles = [item.role for item in assignments]
        for singleton in (
            BenchmarkArmRole.INTEGRATED_CANDIDATE,
            BenchmarkArmRole.PLAIN_SOL_XHIGH,
            BenchmarkArmRole.LENGTH_MATCHED_PLACEBO,
        ):
            if roles.count(singleton) != 1:
                raise ValueError(f"arm role mapping requires exactly one {singleton.value} arm")
        if set(roles) != set(BenchmarkArmRole):
            raise ValueError("arm role mapping must cover every benchmark arm role")
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "mapping_sha256", _digest(self.mapping_sha256, "mapping_sha256"))
        actual = sha256(
            _canonical_json_bytes([item.as_dict() for item in assignments])
        ).hexdigest()
        if actual != self.mapping_sha256:
            raise ValueError("mapping_sha256 does not match arm role assignments")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArmRoleMapping:
        data = _record_payload(cls, payload)
        return cls(
            mapping_id=data["mapping_id"],
            assignments=tuple(
                ArmRoleAssignment.from_dict(item) for item in data["assignments"]
            ),
            mapping_sha256=data["mapping_sha256"],
        )


def validate_arm_role_mapping(
    corpus: SealedPublicCorpus, *, role_mapping: ArmRoleMapping
) -> None:
    if not isinstance(corpus, SealedPublicCorpus):
        raise TypeError("corpus must be SealedPublicCorpus")
    if not isinstance(role_mapping, ArmRoleMapping):
        raise TypeError("role_mapping must be supplied separately")
    expected = {item.arm_id for item in corpus.anonymized_arms}
    received = {item.arm_id for item in role_mapping.assignments}
    if received != expected:
        raise ValueError(
            "arm role mapping must cover every anonymized arm exactly once; "
            f"missing={sorted(expected - received)!r}, "
            f"extra={sorted(received - expected)!r}"
        )


def execution_cell_id(
    *, case_id: str, arm_id: str, seed: int, order: ExecutionOrder, repeat_index: int
) -> str:
    normalized_case = _identifier(case_id, "case_id")
    normalized_arm = _identifier(arm_id, "arm_id")
    if not _ARM_ID_RE.fullmatch(normalized_arm):
        raise ValueError("arm_id must be anonymized")
    normalized_seed = _nonnegative_int(seed, "seed")
    normalized_repeat = _nonnegative_int(repeat_index, "repeat_index")
    normalized_order = ExecutionOrder(order)
    return (
        f"{normalized_case}:{normalized_arm}:seed-{normalized_seed}:"
        f"{normalized_order.value}:repeat-{normalized_repeat}"
    )


@dataclass(frozen=True, slots=True)
class ExecutionCellSpec(_BenchmarkRecord):
    """One generation replicate bound to one judge-presentation orientation.

    ``seed`` is a preregistered replicate label.  It does not claim that the
    provider exposes or consumed a deterministic RNG seed.  AB and BA cells
    for an otherwise identical replicate must reuse one run receipt.
    """

    SCHEMA_VERSION = "benchmark_execution_cell_spec_v1"

    cell_id: str
    case_id: str
    arm_id: str
    seed: int
    order: ExecutionOrder
    repeat_index: int
    execution_config_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _identifier(self.case_id, "case_id"))
        arm_id = _identifier(self.arm_id, "arm_id")
        if not _ARM_ID_RE.fullmatch(arm_id):
            raise ValueError("arm_id must be anonymized")
        object.__setattr__(self, "arm_id", arm_id)
        object.__setattr__(self, "seed", _nonnegative_int(self.seed, "seed"))
        object.__setattr__(self, "order", ExecutionOrder(self.order))
        object.__setattr__(
            self, "repeat_index", _nonnegative_int(self.repeat_index, "repeat_index")
        )
        expected_id = execution_cell_id(
            case_id=self.case_id,
            arm_id=self.arm_id,
            seed=self.seed,
            order=self.order,
            repeat_index=self.repeat_index,
        )
        if self.cell_id != expected_id:
            raise ValueError(f"cell_id must equal deterministic identity {expected_id!r}")
        object.__setattr__(self, "cell_id", expected_id)
        object.__setattr__(
            self,
            "execution_config_sha256",
            _digest(self.execution_config_sha256, "execution_config_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ExecutionCellSpec:
        data = _record_payload(cls, payload)
        return cls(
            cell_id=data["cell_id"],
            case_id=data["case_id"],
            arm_id=data["arm_id"],
            seed=data["seed"],
            order=ExecutionOrder(data["order"]),
            repeat_index=data["repeat_index"],
            execution_config_sha256=data["execution_config_sha256"],
        )


@dataclass(frozen=True, slots=True)
class BenchmarkExecutionMatrix(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_execution_matrix_v2"

    matrix_id: str
    corpus_sha256: str
    frozen_execution_config_sha256: str
    case_ids: tuple[str, ...]
    arm_ids: tuple[str, ...]
    seeds: tuple[int, ...]
    orders: tuple[ExecutionOrder, ...]
    repeat_count: int
    cells: tuple[ExecutionCellSpec, ...]
    sealed: bool
    benchmark_execution_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "matrix_id", _identifier(self.matrix_id, "matrix_id"))
        object.__setattr__(self, "corpus_sha256", _digest(self.corpus_sha256, "corpus_sha256"))
        object.__setattr__(
            self,
            "frozen_execution_config_sha256",
            _digest(
                self.frozen_execution_config_sha256,
                "frozen_execution_config_sha256",
            ),
        )
        case_ids = _identifier_tuple(self.case_ids, "case_ids", nonempty=True)
        object.__setattr__(self, "case_ids", case_ids)
        arm_ids = tuple(sorted(_identifier(value, "arm_ids") for value in self.arm_ids))
        if not arm_ids or len(arm_ids) != len(set(arm_ids)):
            raise ValueError("arm_ids must be nonempty and unique")
        if any(not _ARM_ID_RE.fullmatch(value) for value in arm_ids):
            raise ValueError("arm_ids must be anonymized")
        object.__setattr__(self, "arm_ids", arm_ids)
        seeds = tuple(sorted(_nonnegative_int(value, "seeds") for value in self.seeds))
        if not seeds or len(seeds) != len(set(seeds)):
            raise ValueError("seeds must be nonempty and unique")
        object.__setattr__(self, "seeds", seeds)
        orders = tuple(sorted((ExecutionOrder(value) for value in self.orders), key=lambda x: x.value))
        if len(orders) != len(set(orders)) or set(orders) != set(ExecutionOrder):
            raise ValueError("orders must contain AB and BA exactly once")
        object.__setattr__(self, "orders", orders)
        repeat_count = _positive_int(self.repeat_count, "repeat_count")
        object.__setattr__(self, "repeat_count", repeat_count)
        if self.sealed is not True:
            raise ValueError("execution matrix must be sealed")
        if self.benchmark_execution_authorized is not False:
            raise ValueError("an execution matrix cannot authorize benchmark execution")
        cells = tuple(sorted(self.cells, key=lambda item: item.cell_id))
        if any(not isinstance(item, ExecutionCellSpec) for item in cells):
            raise TypeError("cells must contain ExecutionCellSpec values")
        received = {item.cell_id for item in cells}
        if len(received) != len(cells):
            raise ValueError("execution matrix cell_id values must be unique")
        expected = {
            execution_cell_id(
                case_id=case_id,
                arm_id=arm_id,
                seed=seed,
                order=order,
                repeat_index=repeat_index,
            )
            for case_id in case_ids
            for arm_id in arm_ids
            for seed in seeds
            for order in orders
            for repeat_index in range(repeat_count)
        }
        if received != expected:
            raise ValueError(
                "execution cells must exactly cover case x arm x seed x order x repeat; "
                f"missing={sorted(expected - received)!r}, "
                f"extra={sorted(received - expected)!r}"
            )
        for cell in cells:
            expected_config_sha256 = execution_cell_config_sha256(
                frozen_execution_config_sha256=(
                    self.frozen_execution_config_sha256
                ),
                case_id=cell.case_id,
                arm_id=cell.arm_id,
                seed=cell.seed,
                repeat_index=cell.repeat_index,
            )
            if cell.execution_config_sha256 != expected_config_sha256:
                raise ValueError(
                    "execution cell configuration does not bind the frozen "
                    "configuration and generation replicate"
                )
        generation_configs = {
            (cell.case_id, cell.arm_id, cell.seed, cell.repeat_index): (
                cell.execution_config_sha256
            )
            for cell in cells
        }
        if len(set(generation_configs.values())) != len(generation_configs):
            raise ValueError(
                "distinct generation replicates require distinct configuration "
                "bindings"
            )
        object.__setattr__(self, "cells", cells)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BenchmarkExecutionMatrix:
        data = _record_payload(cls, payload)
        return cls(
            matrix_id=data["matrix_id"],
            corpus_sha256=data["corpus_sha256"],
            frozen_execution_config_sha256=data[
                "frozen_execution_config_sha256"
            ],
            case_ids=tuple(data["case_ids"]),
            arm_ids=tuple(data["arm_ids"]),
            seeds=tuple(data["seeds"]),
            orders=tuple(ExecutionOrder(item) for item in data["orders"]),
            repeat_count=data["repeat_count"],
            cells=tuple(ExecutionCellSpec.from_dict(item) for item in data["cells"]),
            sealed=data["sealed"],
            benchmark_execution_authorized=data["benchmark_execution_authorized"],
        )


def execution_cell_config_sha256(
    *,
    frozen_execution_config_sha256: str,
    case_id: str,
    arm_id: str,
    seed: int,
    repeat_index: int,
) -> str:
    """Bind a frozen model configuration to one generation replicate.

    AB/BA is deliberately absent: it is a judge-presentation orientation, not
    a reason to regenerate model output.  Both order-specific cells for one
    case/arm/seed/repeat must reuse the exact same run receipt and output.
    """

    base_digest = _digest(
        frozen_execution_config_sha256, "frozen_execution_config_sha256"
    )
    normalized_arm_id = _identifier(arm_id, "arm_id")
    if not _ARM_ID_RE.fullmatch(normalized_arm_id):
        raise ValueError("arm_id must be anonymized")
    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "benchmark_generation_config_binding_v1",
                "frozen_execution_config_sha256": base_digest,
                "case_id": _identifier(case_id, "case_id"),
                "arm_id": normalized_arm_id,
                "seed": _nonnegative_int(seed, "seed"),
                "repeat_index": _nonnegative_int(repeat_index, "repeat_index"),
            }
        )
    ).hexdigest()


def build_minimum_seed_order_execution_matrix(
    *,
    corpus: SealedPublicCorpus,
    matrix_id: str,
    frozen_execution_config_sha256: str,
    seeds: tuple[int, ...] = (0, 1),
) -> BenchmarkExecutionMatrix:
    """Freeze the smallest non-vacuous seed/order execution matrix.

    A seed/order stability claim cannot be tested with one seed.  This builder
    therefore requires at least two distinct replicate labels, both AB and BA
    judge-presentation orders, one repeat, and exact coverage of every public
    case and anonymized arm.  AB/BA cells share a generation-configuration
    digest so the same output can be presented in both directions without
    confounding presentation order with model-output variance.  The builder
    never executes a model or grants any authority.
    """

    if not isinstance(corpus, SealedPublicCorpus):
        raise TypeError("corpus must be SealedPublicCorpus")
    normalized_matrix_id = _identifier(matrix_id, "matrix_id")
    base_digest = _digest(
        frozen_execution_config_sha256, "frozen_execution_config_sha256"
    )
    normalized_seeds = tuple(
        sorted(_nonnegative_int(seed, "seeds") for seed in seeds)
    )
    if len(normalized_seeds) < 2 or len(normalized_seeds) != len(
        set(normalized_seeds)
    ):
        raise ValueError(
            "a minimum seed/order matrix requires at least two distinct seeds"
        )

    cells: list[ExecutionCellSpec] = []
    for case in corpus.cases:
        for arm in corpus.anonymized_arms:
            for seed in normalized_seeds:
                for order in ExecutionOrder:
                    cell_id = execution_cell_id(
                        case_id=case.case_id,
                        arm_id=arm.arm_id,
                        seed=seed,
                        order=order,
                        repeat_index=0,
                    )
                    cells.append(
                        ExecutionCellSpec(
                            cell_id=cell_id,
                            case_id=case.case_id,
                            arm_id=arm.arm_id,
                            seed=seed,
                            order=order,
                            repeat_index=0,
                            execution_config_sha256=execution_cell_config_sha256(
                                frozen_execution_config_sha256=base_digest,
                                case_id=case.case_id,
                                arm_id=arm.arm_id,
                                seed=seed,
                                repeat_index=0,
                            ),
                        )
                    )

    return BenchmarkExecutionMatrix(
        matrix_id=normalized_matrix_id,
        corpus_sha256=corpus.content_sha256,
        frozen_execution_config_sha256=base_digest,
        case_ids=tuple(item.case_id for item in corpus.cases),
        arm_ids=tuple(item.arm_id for item in corpus.anonymized_arms),
        seeds=normalized_seeds,
        orders=(ExecutionOrder.AB, ExecutionOrder.BA),
        repeat_count=1,
        cells=tuple(cells),
        sealed=True,
        benchmark_execution_authorized=False,
    )


@dataclass(frozen=True, slots=True)
class SuperiorityDecisionContract(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_superiority_decision_contract_v1"

    contract_id: str
    benchmark_model_id: str
    frozen_reasoning_level: str
    role_instructions: tuple[ArmRoleInstruction, ...]
    required_comparator_roles: tuple[BenchmarkArmRole, ...]
    required_endpoint_keys: tuple[str, ...]
    minimum_independent_scorers: int
    minimum_evaluable_pairs_per_endpoint: int
    minimum_win_fraction: ExactRatio
    minimum_net_wins: int
    required_pair_orientations: tuple[ExecutionOrder, ...]
    ties_retained: bool
    invalid_or_not_evaluable_blocks: bool
    safe_no_change_required: bool
    held_out_required: bool
    seed_order_stability_required: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_id", _identifier(self.contract_id, "contract_id"))
        model_id = _text(self.benchmark_model_id, "benchmark_model_id")
        if model_id.casefold() != "gpt-5.6-sol":
            raise ValueError("the frozen baseline must use plain GPT-5.6 Sol")
        object.__setattr__(self, "benchmark_model_id", model_id)
        reasoning = _identifier(self.frozen_reasoning_level, "frozen_reasoning_level")
        if reasoning != "xhigh":
            raise ValueError("the frozen benchmark reasoning level must be xhigh")
        object.__setattr__(self, "frozen_reasoning_level", reasoning)
        instructions = tuple(sorted(self.role_instructions, key=lambda item: item.role.value))
        if any(not isinstance(item, ArmRoleInstruction) for item in instructions):
            raise TypeError("role_instructions must contain ArmRoleInstruction values")
        if {item.role for item in instructions} != set(BenchmarkArmRole):
            raise ValueError("role_instructions must bind every benchmark arm role")
        if len(instructions) != len(BenchmarkArmRole):
            raise ValueError("role_instructions must bind each arm role exactly once")
        object.__setattr__(self, "role_instructions", instructions)
        comparators = tuple(sorted((BenchmarkArmRole(item) for item in self.required_comparator_roles), key=lambda x: x.value))
        expected_comparators = {
            BenchmarkArmRole.PLAIN_SOL_XHIGH,
            BenchmarkArmRole.LENGTH_MATCHED_PLACEBO,
        }
        if len(comparators) != len(set(comparators)) or set(comparators) != expected_comparators:
            raise ValueError("plain Sol xhigh and length-matched placebo are both required")
        object.__setattr__(self, "required_comparator_roles", comparators)
        object.__setattr__(
            self,
            "required_endpoint_keys",
            _identifier_tuple(self.required_endpoint_keys, "required_endpoint_keys", nonempty=True),
        )
        scorers = _positive_int(self.minimum_independent_scorers, "minimum_independent_scorers")
        if scorers < 2:
            raise ValueError("at least two independent scorers are required")
        object.__setattr__(self, "minimum_independent_scorers", scorers)
        object.__setattr__(
            self,
            "minimum_evaluable_pairs_per_endpoint",
            _positive_int(
                self.minimum_evaluable_pairs_per_endpoint,
                "minimum_evaluable_pairs_per_endpoint",
            ),
        )
        if not isinstance(self.minimum_win_fraction, ExactRatio):
            raise TypeError("minimum_win_fraction must be ExactRatio")
        if self.minimum_win_fraction.numerator * 2 <= self.minimum_win_fraction.denominator:
            raise ValueError("superiority requires minimum_win_fraction greater than 0.5")
        object.__setattr__(
            self, "minimum_net_wins", _positive_int(self.minimum_net_wins, "minimum_net_wins")
        )
        orientations = tuple(
            sorted(
                (ExecutionOrder(item) for item in self.required_pair_orientations),
                key=lambda item: item.value,
            )
        )
        if len(orientations) != len(set(orientations)) or set(orientations) != set(ExecutionOrder):
            raise ValueError("both AB and BA pair orientations are required")
        object.__setattr__(self, "required_pair_orientations", orientations)
        if self.ties_retained is not True:
            raise ValueError("ties must be retained as benchmark evidence")
        if self.invalid_or_not_evaluable_blocks is not True:
            raise ValueError("invalid and not-evaluable observations must block admission")
        if not (
            self.safe_no_change_required
            and self.held_out_required
            and self.seed_order_stability_required
        ):
            raise ValueError("safe no-change, held-out, and seed/order evidence are required")
        if self.admission_authorized is not False:
            raise ValueError("a superiority contract cannot authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SuperiorityDecisionContract:
        data = _record_payload(cls, payload)
        return cls(
            contract_id=data["contract_id"],
            benchmark_model_id=data["benchmark_model_id"],
            frozen_reasoning_level=data["frozen_reasoning_level"],
            role_instructions=tuple(
                ArmRoleInstruction.from_dict(item) for item in data["role_instructions"]
            ),
            required_comparator_roles=tuple(
                BenchmarkArmRole(item) for item in data["required_comparator_roles"]
            ),
            required_endpoint_keys=tuple(data["required_endpoint_keys"]),
            minimum_independent_scorers=data["minimum_independent_scorers"],
            minimum_evaluable_pairs_per_endpoint=data[
                "minimum_evaluable_pairs_per_endpoint"
            ],
            minimum_win_fraction=ExactRatio.from_dict(data["minimum_win_fraction"]),
            minimum_net_wins=data["minimum_net_wins"],
            required_pair_orientations=tuple(
                ExecutionOrder(item) for item in data["required_pair_orientations"]
            ),
            ties_retained=data["ties_retained"],
            invalid_or_not_evaluable_blocks=data["invalid_or_not_evaluable_blocks"],
            safe_no_change_required=data["safe_no_change_required"],
            held_out_required=data["held_out_required"],
            seed_order_stability_required=data["seed_order_stability_required"],
            admission_authorized=data["admission_authorized"],
        )


@dataclass(frozen=True, slots=True)
class FrozenBenchmarkDefinition(_BenchmarkRecord):
    SCHEMA_VERSION = "formulation_intelligence_frozen_benchmark_definition_v1"

    definition_id: str
    benchmark_id: str
    fixture_bytes_sha256: str
    canonical_corpus_sha256: str
    execution_matrix_sha256: str
    gate_contract_sha256: str
    superiority_contract_sha256: str
    blind_label_mapping_sha256: str
    arm_role_mapping_sha256: str
    pair_schedule_commitment_sha256: str
    rubric_sha256: str
    scorer_protocol_sha256: str
    recursive_closure_required: bool
    benchmark_execution_authorized: bool
    empirical_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _identifier(self.definition_id, "definition_id"))
        object.__setattr__(self, "benchmark_id", _identifier(self.benchmark_id, "benchmark_id"))
        for field_name in (
            "fixture_bytes_sha256",
            "canonical_corpus_sha256",
            "execution_matrix_sha256",
            "gate_contract_sha256",
            "superiority_contract_sha256",
            "blind_label_mapping_sha256",
            "arm_role_mapping_sha256",
            "pair_schedule_commitment_sha256",
            "rubric_sha256",
            "scorer_protocol_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        if self.recursive_closure_required is not True:
            raise ValueError("the frozen benchmark requires complete recursive closure")
        if self.benchmark_execution_authorized is not False:
            raise ValueError("the definition cannot authorize benchmark execution")
        if self.empirical_authority is not False:
            raise ValueError("the definition has no empirical authority")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenBenchmarkDefinition:
        data = _record_payload(cls, payload)
        return cls(**{item: data[item] for item in data if item != "schema_version"})


class CampaignArtifactAudience(str, Enum):
    PUBLIC_MODEL_INPUT = "public_model_input"
    PRODUCER_ONLY = "producer_only"
    SCORER_ONLY = "scorer_only"
    UNBLINDER_ONLY = "unblinder_only"
    VERIFIER_ONLY = "verifier_only"
    ADMISSION_ONLY = "admission_only"


class CampaignArtifactKind(str, Enum):
    PUBLIC_CORPUS = "public_corpus"
    CASE_PACKET_SET = "case_packet_set"
    PRIVATE_ANSWER_KEY_SET = "private_answer_key_set"
    BENCHMARK_DEFINITION = "benchmark_definition"
    EXECUTION_MATRIX = "execution_matrix"
    GENERATION_PLAN = "generation_plan"
    REQUEST_CONFIG = "request_config"
    PROMPT_RENDERER = "prompt_renderer"
    RENDERED_PROMPT_PACK = "rendered_prompt_pack"
    ROLE_INSTRUCTION_SET = "role_instruction_set"
    ABLATION_PLAN = "ablation_plan"
    PLACEBO_TOKEN_PARITY = "placebo_token_parity"
    PAIR_SCHEDULE = "pair_schedule"
    RUBRIC = "rubric"
    SCORER_PROTOCOL = "scorer_protocol"
    SCORER_ROSTER = "scorer_roster"
    BLIND_LABEL_MAP = "blind_label_map"
    ARM_ROLE_MAP = "arm_role_map"
    VERIFIER_IMPLEMENTATION = "verifier_implementation"
    RUNTIME_CLOSURE = "runtime_closure"
    RETRY_POLICY = "retry_policy"


_REQUIRED_CAMPAIGN_ARTIFACT_KINDS = frozenset(CampaignArtifactKind)
_PRIVATE_CAMPAIGN_ARTIFACT_AUDIENCES: dict[
    CampaignArtifactKind, frozenset[CampaignArtifactAudience]
] = {
    CampaignArtifactKind.PRIVATE_ANSWER_KEY_SET: frozenset(
        {CampaignArtifactAudience.SCORER_ONLY}
    ),
    CampaignArtifactKind.BLIND_LABEL_MAP: frozenset(
        {
            CampaignArtifactAudience.UNBLINDER_ONLY,
            CampaignArtifactAudience.VERIFIER_ONLY,
        }
    ),
    CampaignArtifactKind.ARM_ROLE_MAP: frozenset(
        {
            CampaignArtifactAudience.UNBLINDER_ONLY,
            CampaignArtifactAudience.VERIFIER_ONLY,
        }
    ),
    CampaignArtifactKind.SCORER_ROSTER: frozenset(
        {CampaignArtifactAudience.VERIFIER_ONLY}
    ),
}


def _relative_campaign_path(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("relative_path must be text")
    normalized = value.replace("\\", "/")
    if not normalized or normalized != normalized.strip():
        raise ValueError("relative_path must be nonblank with no outer whitespace")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("relative_path must stay within the campaign artifact root")
    if ":" in path.parts[0]:
        raise ValueError("relative_path must not contain a Windows drive prefix")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class CampaignArtifactBinding(_BenchmarkRecord):
    """One exact campaign artifact with an explicit information-flow audience."""

    SCHEMA_VERSION = "benchmark_campaign_artifact_binding_v1"

    artifact_id: str
    artifact_kind: CampaignArtifactKind
    relative_path: str
    byte_length: int
    artifact_sha256: str
    audience: CampaignArtifactAudience
    dependency_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "artifact_id", _identifier(self.artifact_id, "artifact_id")
        )
        object.__setattr__(
            self, "artifact_kind", CampaignArtifactKind(self.artifact_kind)
        )
        object.__setattr__(
            self, "relative_path", _relative_campaign_path(self.relative_path)
        )
        object.__setattr__(
            self, "byte_length", _positive_int(self.byte_length, "byte_length")
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _digest(self.artifact_sha256, "artifact_sha256"),
        )
        object.__setattr__(self, "audience", CampaignArtifactAudience(self.audience))
        dependencies = _identifier_tuple(self.dependency_ids, "dependency_ids")
        if self.artifact_id in dependencies:
            raise ValueError("campaign artifacts cannot depend on themselves")
        object.__setattr__(self, "dependency_ids", dependencies)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CampaignArtifactBinding:
        data = _record_payload(cls, payload)
        return cls(
            artifact_id=data["artifact_id"],
            artifact_kind=CampaignArtifactKind(data["artifact_kind"]),
            relative_path=data["relative_path"],
            byte_length=data["byte_length"],
            artifact_sha256=data["artifact_sha256"],
            audience=CampaignArtifactAudience(data["audience"]),
            dependency_ids=tuple(data["dependency_ids"]),
        )


def _assert_acyclic_campaign_dependencies(
    bindings: tuple[CampaignArtifactBinding, ...],
) -> None:
    dependency_map = {
        binding.artifact_id: binding.dependency_ids for binding in bindings
    }
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(artifact_id: str) -> None:
        if artifact_id in visited:
            return
        if artifact_id in visiting:
            raise ValueError("campaign artifact dependency graph must be acyclic")
        visiting.add(artifact_id)
        for dependency_id in dependency_map[artifact_id]:
            visit(dependency_id)
        visiting.remove(artifact_id)
        visited.add(artifact_id)

    for artifact_id in dependency_map:
        visit(artifact_id)


@dataclass(frozen=True, slots=True)
class FrozenCampaignManifest(_BenchmarkRecord):
    """Byte-resolving, preexecution definition of one production campaign."""

    SCHEMA_VERSION = "formulation_intelligence_frozen_campaign_manifest_v1"

    campaign_id: str
    benchmark_id: str
    benchmark_definition_sha256: str
    source_identity_sha256: str
    workspace_state_sha256: str
    generation_plan_sha256: str
    artifacts: tuple[CampaignArtifactBinding, ...]
    case_ids: tuple[str, ...]
    arm_ids: tuple[str, ...]
    independent_generation_count_per_case_arm: int
    unique_generation_group_count: int
    presentation_cell_count: int
    model_provider_id: str
    model_snapshot_id: str
    reasoning_level: str
    authority_exclusions: tuple[str, ...]
    sealed: bool
    benchmark_execution_authorized: bool
    empirical_authority: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        for field_name in ("campaign_id", "benchmark_id"):
            object.__setattr__(
                self, field_name, _identifier(getattr(self, field_name), field_name)
            )
        for field_name in (
            "benchmark_definition_sha256",
            "source_identity_sha256",
            "workspace_state_sha256",
            "generation_plan_sha256",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        artifacts = tuple(sorted(self.artifacts, key=lambda item: item.artifact_id))
        if not artifacts or any(
            not isinstance(item, CampaignArtifactBinding) for item in artifacts
        ):
            raise TypeError("artifacts must contain CampaignArtifactBinding values")
        artifact_ids = tuple(item.artifact_id for item in artifacts)
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("campaign artifact_id values must be unique")
        artifact_paths = tuple(item.relative_path for item in artifacts)
        if len(artifact_paths) != len(set(artifact_paths)):
            raise ValueError("campaign artifact paths must be unique")
        missing_kinds = _REQUIRED_CAMPAIGN_ARTIFACT_KINDS - {
            item.artifact_kind for item in artifacts
        }
        if missing_kinds:
            raise ValueError(
                "campaign manifest is missing required artifact kinds: "
                f"{sorted(item.value for item in missing_kinds)!r}"
            )
        known_ids = set(artifact_ids)
        missing_dependencies = {
            dependency
            for item in artifacts
            for dependency in item.dependency_ids
            if dependency not in known_ids
        }
        if missing_dependencies:
            raise ValueError(
                "campaign artifact dependencies must resolve exactly: "
                f"{sorted(missing_dependencies)!r}"
            )
        for item in artifacts:
            permitted = _PRIVATE_CAMPAIGN_ARTIFACT_AUDIENCES.get(
                item.artifact_kind
            )
            if permitted is not None and item.audience not in permitted:
                raise ValueError(
                    f"{item.artifact_kind.value} has an unsafe artifact audience"
                )
        _assert_acyclic_campaign_dependencies(artifacts)
        object.__setattr__(self, "artifacts", artifacts)

        case_ids = _identifier_tuple(self.case_ids, "case_ids", nonempty=True)
        if len(case_ids) < 22:
            raise ValueError("production campaigns require at least 22 cases")
        object.__setattr__(self, "case_ids", case_ids)
        arm_ids = tuple(sorted(_identifier(item, "arm_ids") for item in self.arm_ids))
        if len(arm_ids) != 5 or len(set(arm_ids)) != 5:
            raise ValueError("production campaigns require exactly five arms")
        if any(not _ARM_ID_RE.fullmatch(item) for item in arm_ids):
            raise ValueError("production campaign arm_ids must be anonymized")
        object.__setattr__(self, "arm_ids", arm_ids)

        replicate_count = _positive_int(
            self.independent_generation_count_per_case_arm,
            "independent_generation_count_per_case_arm",
        )
        if replicate_count < 2:
            raise ValueError(
                "production campaigns require at least two independent generations "
                "per case and arm"
            )
        object.__setattr__(
            self,
            "independent_generation_count_per_case_arm",
            replicate_count,
        )
        expected_generation_groups = len(case_ids) * len(arm_ids) * replicate_count
        generation_groups = _positive_int(
            self.unique_generation_group_count,
            "unique_generation_group_count",
        )
        if generation_groups != expected_generation_groups or generation_groups < 220:
            raise ValueError(
                "unique_generation_group_count must equal case x arm x independent "
                "generation count and be at least 220"
            )
        object.__setattr__(
            self, "unique_generation_group_count", generation_groups
        )
        presentation_cells = _positive_int(
            self.presentation_cell_count, "presentation_cell_count"
        )
        if presentation_cells != generation_groups * len(ExecutionOrder):
            raise ValueError(
                "presentation_cell_count must contain AB and BA for every generation"
            )
        object.__setattr__(self, "presentation_cell_count", presentation_cells)

        provider = _identifier(self.model_provider_id, "model_provider_id")
        if provider != "openai":
            raise ValueError("production benchmark campaigns are OpenAI-only")
        object.__setattr__(self, "model_provider_id", provider)
        model = _text(self.model_snapshot_id, "model_snapshot_id")
        if model.casefold() != "gpt-5.6-sol":
            raise ValueError("production campaigns require the frozen Sol baseline")
        object.__setattr__(self, "model_snapshot_id", model)
        reasoning = _identifier(self.reasoning_level, "reasoning_level")
        if reasoning != "xhigh":
            raise ValueError("production campaigns require xhigh reasoning")
        object.__setattr__(self, "reasoning_level", reasoning)
        exclusions = _identifier_tuple(
            self.authority_exclusions,
            "authority_exclusions",
            nonempty=True,
        )
        if exclusions != PUBLIC_AUTHORITY_EXCLUSIONS:
            raise ValueError("campaign authority exclusions must match the public ceiling")
        object.__setattr__(self, "authority_exclusions", exclusions)
        if self.sealed is not True:
            raise ValueError("production campaign manifests must be sealed")
        for field_name in (
            "benchmark_execution_authorized",
            "empirical_authority",
            "admission_authorized",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"campaign manifests cannot grant {field_name}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenCampaignManifest:
        data = _record_payload(cls, payload)
        return cls(
            campaign_id=data["campaign_id"],
            benchmark_id=data["benchmark_id"],
            benchmark_definition_sha256=data["benchmark_definition_sha256"],
            source_identity_sha256=data["source_identity_sha256"],
            workspace_state_sha256=data["workspace_state_sha256"],
            generation_plan_sha256=data["generation_plan_sha256"],
            artifacts=tuple(
                CampaignArtifactBinding.from_dict(item) for item in data["artifacts"]
            ),
            case_ids=tuple(data["case_ids"]),
            arm_ids=tuple(data["arm_ids"]),
            independent_generation_count_per_case_arm=data[
                "independent_generation_count_per_case_arm"
            ],
            unique_generation_group_count=data["unique_generation_group_count"],
            presentation_cell_count=data["presentation_cell_count"],
            model_provider_id=data["model_provider_id"],
            model_snapshot_id=data["model_snapshot_id"],
            reasoning_level=data["reasoning_level"],
            authority_exclusions=tuple(data["authority_exclusions"]),
            sealed=data["sealed"],
            benchmark_execution_authorized=data[
                "benchmark_execution_authorized"
            ],
            empirical_authority=data["empirical_authority"],
            admission_authorized=data["admission_authorized"],
        )


@dataclass(frozen=True, slots=True)
class ExecutionCellObservation(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_execution_cell_observation_v1"

    observation_id: str
    cell_id: str
    prompt_receipt_sha256: str
    run_receipt_sha256: str
    validity: EvaluationValidity
    reason_codes: tuple[str, ...]
    used_for_admission: bool
    disposition: ObservationDisposition
    supersedes_observation_sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation_id", _identifier(self.observation_id, "observation_id"))
        object.__setattr__(self, "cell_id", _identifier(self.cell_id, "cell_id"))
        object.__setattr__(
            self,
            "prompt_receipt_sha256",
            _digest(self.prompt_receipt_sha256, "prompt_receipt_sha256"),
        )
        object.__setattr__(
            self, "run_receipt_sha256", _digest(self.run_receipt_sha256, "run_receipt_sha256")
        )
        validity = EvaluationValidity(self.validity)
        disposition = ObservationDisposition(self.disposition)
        object.__setattr__(self, "validity", validity)
        object.__setattr__(self, "disposition", disposition)
        reasons = _identifier_tuple(self.reason_codes, "reason_codes")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(
            self,
            "supersedes_observation_sha256",
            _optional_digest(
                self.supersedes_observation_sha256, "supersedes_observation_sha256"
            ),
        )
        if validity is EvaluationValidity.VALID and reasons:
            raise ValueError("valid execution observations cannot carry reason codes")
        if validity is not EvaluationValidity.VALID and not reasons:
            raise ValueError("non-valid execution observations require reason codes")
        if disposition is ObservationDisposition.CURRENT:
            if self.used_for_admission is not (validity is EvaluationValidity.VALID):
                raise ValueError("only current valid execution observations are admissible")
        elif self.used_for_admission is not False:
            raise ValueError("tombstone and superseded observations cannot be used for admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ExecutionCellObservation:
        data = _record_payload(cls, payload)
        return cls(
            observation_id=data["observation_id"],
            cell_id=data["cell_id"],
            prompt_receipt_sha256=data["prompt_receipt_sha256"],
            run_receipt_sha256=data["run_receipt_sha256"],
            validity=EvaluationValidity(data["validity"]),
            reason_codes=tuple(data["reason_codes"]),
            used_for_admission=data["used_for_admission"],
            disposition=ObservationDisposition(data["disposition"]),
            supersedes_observation_sha256=data["supersedes_observation_sha256"],
        )


def blinded_pair_schedule_sha256(
    *,
    pair_id: str,
    swap_group_id: str,
    case_id: str,
    endpoint_key: str,
    seed: int,
    repeat_index: int,
    planned_orientation: ExecutionOrder,
    left_cell_id: str,
    right_cell_id: str,
    left_blind_label: str,
    right_blind_label: str,
) -> str:
    """Hash only fields that must be fixed before any output is judged.

    Output bytes, realized order, validity, and outcomes are intentionally
    absent.  The frozen definition can therefore commit this schedule before
    model execution without learning or adapting to benchmark results.
    """

    payload = {
        "schema_version": "benchmark_blinded_pair_schedule_payload_v1",
        "pair_id": _identifier(pair_id, "pair_id"),
        "swap_group_id": _identifier(swap_group_id, "swap_group_id"),
        "case_id": _identifier(case_id, "case_id"),
        "endpoint_key": _identifier(endpoint_key, "endpoint_key"),
        "seed": _nonnegative_int(seed, "seed"),
        "repeat_index": _nonnegative_int(repeat_index, "repeat_index"),
        "planned_orientation": ExecutionOrder(planned_orientation).value,
        "left_cell_id": _identifier(left_cell_id, "left_cell_id"),
        "right_cell_id": _identifier(right_cell_id, "right_cell_id"),
        "left_blind_label": _identifier(left_blind_label, "left_blind_label"),
        "right_blind_label": _identifier(right_blind_label, "right_blind_label"),
    }
    if payload["left_cell_id"] == payload["right_cell_id"]:
        raise ValueError("a blinded pair schedule requires distinct cells")
    if payload["left_blind_label"] == payload["right_blind_label"]:
        raise ValueError("a blinded pair schedule requires distinct labels")
    return sha256(_canonical_json_bytes(payload)).hexdigest()


def blinded_pair_assignment_commitment_sha256(
    *, pair_id: str, schedule_sha256: str
) -> str:
    """Bind an assignment identity to its preregistered schedule digest."""

    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "benchmark_blinded_pair_assignment_commitment_v1",
                "pair_id": _identifier(pair_id, "pair_id"),
                "schedule_sha256": _digest(schedule_sha256, "schedule_sha256"),
            }
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class BlindedPairAssignment(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_blinded_pair_assignment_v1"

    pair_id: str
    swap_group_id: str
    case_id: str
    endpoint_key: str
    seed: int
    repeat_index: int
    planned_orientation: ExecutionOrder
    realized_orientation: ExecutionOrder
    left_cell_id: str
    right_cell_id: str
    left_blind_label: str
    right_blind_label: str
    blinded_bundle_sha256: str
    schedule_sha256: str
    assignment_commitment_sha256: str
    validity: EvaluationValidity
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "pair_id",
            "swap_group_id",
            "case_id",
            "endpoint_key",
            "left_cell_id",
            "right_cell_id",
            "left_blind_label",
            "right_blind_label",
        ):
            object.__setattr__(self, field_name, _identifier(getattr(self, field_name), field_name))
        if self.left_cell_id == self.right_cell_id:
            raise ValueError("a blinded pair requires two distinct execution cells")
        if self.left_blind_label == self.right_blind_label:
            raise ValueError("a blinded pair requires two distinct blind labels")
        object.__setattr__(self, "seed", _nonnegative_int(self.seed, "seed"))
        object.__setattr__(
            self, "repeat_index", _nonnegative_int(self.repeat_index, "repeat_index")
        )
        planned = ExecutionOrder(self.planned_orientation)
        realized = ExecutionOrder(self.realized_orientation)
        object.__setattr__(self, "planned_orientation", planned)
        object.__setattr__(self, "realized_orientation", realized)
        for field_name in (
            "blinded_bundle_sha256",
            "schedule_sha256",
            "assignment_commitment_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        validity = EvaluationValidity(self.validity)
        object.__setattr__(self, "validity", validity)
        reasons = _identifier_tuple(self.reason_codes, "reason_codes")
        object.__setattr__(self, "reason_codes", reasons)
        if planned is not realized:
            if validity is not EvaluationValidity.ORDER_CONFOUNDED:
                raise ValueError("planned/realized order mismatch must be ORDER_CONFOUNDED")
        elif validity is EvaluationValidity.ORDER_CONFOUNDED:
            raise ValueError("ORDER_CONFOUNDED requires a planned/realized mismatch")
        if validity is EvaluationValidity.VALID and reasons:
            raise ValueError("valid pair assignments cannot carry reason codes")
        if validity is not EvaluationValidity.VALID and not reasons:
            raise ValueError("non-valid pair assignments require reason codes")
        expected_schedule = blinded_pair_schedule_sha256(
            pair_id=self.pair_id,
            swap_group_id=self.swap_group_id,
            case_id=self.case_id,
            endpoint_key=self.endpoint_key,
            seed=self.seed,
            repeat_index=self.repeat_index,
            planned_orientation=self.planned_orientation,
            left_cell_id=self.left_cell_id,
            right_cell_id=self.right_cell_id,
            left_blind_label=self.left_blind_label,
            right_blind_label=self.right_blind_label,
        )
        if self.schedule_sha256 != expected_schedule:
            raise ValueError("schedule_sha256 does not match preregistered pair fields")
        expected_assignment = blinded_pair_assignment_commitment_sha256(
            pair_id=self.pair_id,
            schedule_sha256=expected_schedule,
        )
        if self.assignment_commitment_sha256 != expected_assignment:
            raise ValueError(
                "assignment_commitment_sha256 does not bind the pair schedule"
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BlindedPairAssignment:
        data = _record_payload(cls, payload)
        return cls(
            pair_id=data["pair_id"],
            swap_group_id=data["swap_group_id"],
            case_id=data["case_id"],
            endpoint_key=data["endpoint_key"],
            seed=data["seed"],
            repeat_index=data["repeat_index"],
            planned_orientation=ExecutionOrder(data["planned_orientation"]),
            realized_orientation=ExecutionOrder(data["realized_orientation"]),
            left_cell_id=data["left_cell_id"],
            right_cell_id=data["right_cell_id"],
            left_blind_label=data["left_blind_label"],
            right_blind_label=data["right_blind_label"],
            blinded_bundle_sha256=data["blinded_bundle_sha256"],
            schedule_sha256=data["schedule_sha256"],
            assignment_commitment_sha256=data["assignment_commitment_sha256"],
            validity=EvaluationValidity(data["validity"]),
            reason_codes=tuple(data["reason_codes"]),
        )


def pair_schedule_commitment_sha256(
    assignments: Iterable[BlindedPairAssignment],
) -> str:
    """Commit the preregistered pair schedule without exposing semantic roles."""

    normalized = tuple(
        sorted(
            assignments,
            key=lambda item: item.pair_id,
        )
    )
    if not normalized or any(
        not isinstance(item, BlindedPairAssignment) for item in normalized
    ):
        raise TypeError("assignments must contain BlindedPairAssignment values")
    return sha256(
        _canonical_json_bytes(
            tuple(
                {
                    "pair_id": item.pair_id,
                    "schedule_sha256": item.schedule_sha256,
                    "assignment_commitment_sha256": (
                        item.assignment_commitment_sha256
                    ),
                }
                for item in normalized
            )
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PairJudgeObservation(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_pair_judge_observation_v1"

    observation_id: str
    pair_id: str
    endpoint_key: str
    judge_receipt_sha256: str
    outcome: PairOutcome
    left_score: int | None
    right_score: int | None
    tie_reason: str | None
    reason_codes: tuple[str, ...]
    critical_error_codes: tuple[str, ...]
    evidence_artifact_sha256: str
    validity: EvaluationValidity
    used_for_admission: bool
    disposition: ObservationDisposition
    supersedes_observation_sha256: str | None

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "pair_id", "endpoint_key"):
            object.__setattr__(self, field_name, _identifier(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "judge_receipt_sha256",
            _digest(self.judge_receipt_sha256, "judge_receipt_sha256"),
        )
        outcome = PairOutcome(self.outcome)
        validity = EvaluationValidity(self.validity)
        disposition = ObservationDisposition(self.disposition)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "validity", validity)
        object.__setattr__(self, "disposition", disposition)
        left = (
            None
            if self.left_score is None
            else _nonnegative_int(self.left_score, "left_score")
        )
        right = (
            None
            if self.right_score is None
            else _nonnegative_int(self.right_score, "right_score")
        )
        if (left is None) != (right is None):
            raise ValueError("left_score and right_score must be supplied together")
        object.__setattr__(self, "left_score", left)
        object.__setattr__(self, "right_score", right)
        object.__setattr__(self, "tie_reason", _optional_text(self.tie_reason, "tie_reason"))
        reasons = _identifier_tuple(self.reason_codes, "reason_codes")
        critical = _identifier_tuple(self.critical_error_codes, "critical_error_codes")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "critical_error_codes", critical)
        object.__setattr__(
            self,
            "evidence_artifact_sha256",
            _digest(self.evidence_artifact_sha256, "evidence_artifact_sha256"),
        )
        object.__setattr__(
            self,
            "supersedes_observation_sha256",
            _optional_digest(
                self.supersedes_observation_sha256, "supersedes_observation_sha256"
            ),
        )
        valid_outcomes = {PairOutcome.LEFT, PairOutcome.RIGHT, PairOutcome.TIE}
        if validity is EvaluationValidity.VALID:
            if outcome not in valid_outcomes or left is None:
                raise ValueError("valid pair observations require a scored LEFT, RIGHT, or TIE")
            assert right is not None
            if reasons:
                raise ValueError("valid pair observations cannot carry reason codes")
            if outcome is PairOutcome.LEFT and not left > right:
                raise ValueError("LEFT outcome requires left_score greater than right_score")
            if outcome is PairOutcome.RIGHT and not right > left:
                raise ValueError("RIGHT outcome requires right_score greater than left_score")
            if outcome is PairOutcome.TIE and self.tie_reason is None:
                raise ValueError("TIE outcomes require a tie_reason")
        else:
            if outcome not in {PairOutcome.INVALID, PairOutcome.NOT_EVALUABLE}:
                raise ValueError("non-valid pair observations must be INVALID or NOT_EVALUABLE")
            if left is not None or self.tie_reason is not None or not reasons:
                raise ValueError("non-valid pair observations require reasons and no scores")
        if disposition is ObservationDisposition.CURRENT:
            if self.used_for_admission is not (validity is EvaluationValidity.VALID):
                raise ValueError("only current valid pair observations are admissible")
        elif self.used_for_admission is not False:
            raise ValueError("tombstone and superseded pair observations are never admissible")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PairJudgeObservation:
        data = _record_payload(cls, payload)
        return cls(
            observation_id=data["observation_id"],
            pair_id=data["pair_id"],
            endpoint_key=data["endpoint_key"],
            judge_receipt_sha256=data["judge_receipt_sha256"],
            outcome=PairOutcome(data["outcome"]),
            left_score=data["left_score"],
            right_score=data["right_score"],
            tie_reason=data["tie_reason"],
            reason_codes=tuple(data["reason_codes"]),
            critical_error_codes=tuple(data["critical_error_codes"]),
            evidence_artifact_sha256=data["evidence_artifact_sha256"],
            validity=EvaluationValidity(data["validity"]),
            used_for_admission=data["used_for_admission"],
            disposition=ObservationDisposition(data["disposition"]),
            supersedes_observation_sha256=data["supersedes_observation_sha256"],
        )


@dataclass(frozen=True, slots=True)
class HardGateObservation(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_hard_gate_observation_v1"

    observation_id: str
    cell_id: str
    gate_key: str
    judge_receipt_sha256: str
    critical_error_count: int
    evidence_artifact_sha256: str
    validity: EvaluationValidity
    reason_codes: tuple[str, ...]
    used_for_admission: bool
    disposition: ObservationDisposition
    supersedes_observation_sha256: str | None

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "cell_id", "gate_key"):
            object.__setattr__(self, field_name, _identifier(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "judge_receipt_sha256",
            _digest(self.judge_receipt_sha256, "judge_receipt_sha256"),
        )
        object.__setattr__(
            self,
            "critical_error_count",
            _nonnegative_int(self.critical_error_count, "critical_error_count"),
        )
        object.__setattr__(
            self,
            "evidence_artifact_sha256",
            _digest(self.evidence_artifact_sha256, "evidence_artifact_sha256"),
        )
        validity = EvaluationValidity(self.validity)
        disposition = ObservationDisposition(self.disposition)
        object.__setattr__(self, "validity", validity)
        object.__setattr__(self, "disposition", disposition)
        reasons = _identifier_tuple(self.reason_codes, "reason_codes")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(
            self,
            "supersedes_observation_sha256",
            _optional_digest(
                self.supersedes_observation_sha256, "supersedes_observation_sha256"
            ),
        )
        if validity is EvaluationValidity.VALID and reasons:
            raise ValueError("valid gate observations cannot carry reason codes")
        if validity is not EvaluationValidity.VALID and not reasons:
            raise ValueError("non-valid gate observations require reason codes")
        if disposition is ObservationDisposition.CURRENT:
            if self.used_for_admission is not (validity is EvaluationValidity.VALID):
                raise ValueError("only current valid gate observations are admissible")
        elif self.used_for_admission is not False:
            raise ValueError("tombstone and superseded gate observations are never admissible")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HardGateObservation:
        data = _record_payload(cls, payload)
        return cls(
            observation_id=data["observation_id"],
            cell_id=data["cell_id"],
            gate_key=data["gate_key"],
            judge_receipt_sha256=data["judge_receipt_sha256"],
            critical_error_count=data["critical_error_count"],
            evidence_artifact_sha256=data["evidence_artifact_sha256"],
            validity=EvaluationValidity(data["validity"]),
            reason_codes=tuple(data["reason_codes"]),
            used_for_admission=data["used_for_admission"],
            disposition=ObservationDisposition(data["disposition"]),
            supersedes_observation_sha256=data["supersedes_observation_sha256"],
        )


@dataclass(frozen=True, slots=True)
class FrozenBenchmarkObservationPacket(_BenchmarkRecord):
    """Observed benchmark evidence with no caller-supplied aggregate status."""

    SCHEMA_VERSION = "formulation_intelligence_frozen_benchmark_observation_packet_v2"

    result_id: str
    benchmark_id: str
    benchmark_definition_sha256: str
    fixture_bytes_sha256: str
    canonical_corpus_sha256: str
    source_identity_sha256: str
    workspace_state_sha256: str
    admission_challenge_nonce: str
    admission_request_scope_sha256: str
    producer_independence_key: str
    module_manifest_sha256s: tuple[str, ...]
    covered_module_ids: tuple[str, ...]
    covered_capability_ids: tuple[str, ...]
    covered_schema_ids: tuple[str, ...]
    artifact_closure_sha256: str
    covered_artifact_ids: tuple[str, ...]
    execution_matrix_sha256: str
    gate_contract_sha256: str
    superiority_contract_sha256: str
    rubric_sha256: str
    scorer_protocol_sha256: str
    blind_mapping_sha256: str
    arm_role_mapping_sha256: str
    prompt_receipt_sha256s: tuple[str, ...]
    run_receipt_sha256s: tuple[str, ...]
    judge_receipt_sha256s: tuple[str, ...]
    execution_observations: tuple[ExecutionCellObservation, ...]
    pair_assignments: tuple[BlindedPairAssignment, ...]
    pair_observations: tuple[PairJudgeObservation, ...]
    hard_gate_observations: tuple[HardGateObservation, ...]
    observed_at_utc: str
    recursive_closure: RecursiveClosureReceiptRef
    authority_exclusions: tuple[str, ...]
    benchmark_execution_authorized: bool
    runtime_admission_authorized: bool
    empirical_authority: bool
    formula_authority: bool
    physical_execution_authority: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_id", _identifier(self.result_id, "result_id"))
        object.__setattr__(self, "benchmark_id", _identifier(self.benchmark_id, "benchmark_id"))
        for field_name in (
            "benchmark_definition_sha256",
            "fixture_bytes_sha256",
            "canonical_corpus_sha256",
            "source_identity_sha256",
            "workspace_state_sha256",
            "admission_challenge_nonce",
            "admission_request_scope_sha256",
            "producer_independence_key",
            "artifact_closure_sha256",
            "execution_matrix_sha256",
            "gate_contract_sha256",
            "superiority_contract_sha256",
            "rubric_sha256",
            "scorer_protocol_sha256",
            "blind_mapping_sha256",
            "arm_role_mapping_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        object.__setattr__(
            self,
            "module_manifest_sha256s",
            _digest_tuple(
                self.module_manifest_sha256s,
                "module_manifest_sha256s",
                nonempty=True,
            ),
        )
        for field_name in (
            "covered_module_ids",
            "covered_capability_ids",
            "covered_schema_ids",
            "covered_artifact_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier_tuple(getattr(self, field_name), field_name, nonempty=True),
            )
        for field_name in (
            "prompt_receipt_sha256s",
            "run_receipt_sha256s",
            "judge_receipt_sha256s",
        ):
            object.__setattr__(
                self,
                field_name,
                _digest_tuple(getattr(self, field_name), field_name, nonempty=True),
            )
        typed_collections: tuple[tuple[str, type[Any], str], ...] = (
            ("execution_observations", ExecutionCellObservation, "observation_id"),
            ("pair_assignments", BlindedPairAssignment, "pair_id"),
            ("pair_observations", PairJudgeObservation, "observation_id"),
            ("hard_gate_observations", HardGateObservation, "observation_id"),
        )
        for field_name, expected_type, identity_field in typed_collections:
            values = tuple(
                sorted(
                    getattr(self, field_name),
                    key=lambda item: getattr(item, identity_field),
                )
            )
            if not values or any(not isinstance(item, expected_type) for item in values):
                raise TypeError(f"{field_name} must contain {expected_type.__name__} values")
            identities = [getattr(item, identity_field) for item in values]
            if len(identities) != len(set(identities)):
                raise ValueError(f"{field_name} identities must be unique")
            object.__setattr__(self, field_name, values)
        object.__setattr__(
            self, "observed_at_utc", _utc_timestamp(self.observed_at_utc, "observed_at_utc")
        )
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")
        exclusions = _identifier_tuple(
            self.authority_exclusions, "authority_exclusions", nonempty=True
        )
        if exclusions != PUBLIC_AUTHORITY_EXCLUSIONS:
            raise ValueError("authority_exclusions must match the benchmark ceiling")
        object.__setattr__(self, "authority_exclusions", exclusions)
        authority_flags = (
            self.benchmark_execution_authorized,
            self.runtime_admission_authorized,
            self.empirical_authority,
            self.formula_authority,
            self.physical_execution_authority,
            self.compounding_authority,
            self.sensory_authority,
            self.liking_authority,
            self.safety_authority,
            self.stability_authority,
            self.purchase_authority,
            self.release_authority,
        )
        if any(value is not False for value in authority_flags):
            raise ValueError("benchmark observations cannot grant authority")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenBenchmarkObservationPacket:
        data = _record_payload(cls, payload)
        return cls(
            result_id=data["result_id"],
            benchmark_id=data["benchmark_id"],
            benchmark_definition_sha256=data["benchmark_definition_sha256"],
            fixture_bytes_sha256=data["fixture_bytes_sha256"],
            canonical_corpus_sha256=data["canonical_corpus_sha256"],
            source_identity_sha256=data["source_identity_sha256"],
            workspace_state_sha256=data["workspace_state_sha256"],
            admission_challenge_nonce=data["admission_challenge_nonce"],
            admission_request_scope_sha256=data["admission_request_scope_sha256"],
            producer_independence_key=data["producer_independence_key"],
            module_manifest_sha256s=tuple(data["module_manifest_sha256s"]),
            covered_module_ids=tuple(data["covered_module_ids"]),
            covered_capability_ids=tuple(data["covered_capability_ids"]),
            covered_schema_ids=tuple(data["covered_schema_ids"]),
            artifact_closure_sha256=data["artifact_closure_sha256"],
            covered_artifact_ids=tuple(data["covered_artifact_ids"]),
            execution_matrix_sha256=data["execution_matrix_sha256"],
            gate_contract_sha256=data["gate_contract_sha256"],
            superiority_contract_sha256=data["superiority_contract_sha256"],
            rubric_sha256=data["rubric_sha256"],
            scorer_protocol_sha256=data["scorer_protocol_sha256"],
            blind_mapping_sha256=data["blind_mapping_sha256"],
            arm_role_mapping_sha256=data["arm_role_mapping_sha256"],
            prompt_receipt_sha256s=tuple(data["prompt_receipt_sha256s"]),
            run_receipt_sha256s=tuple(data["run_receipt_sha256s"]),
            judge_receipt_sha256s=tuple(data["judge_receipt_sha256s"]),
            execution_observations=tuple(
                ExecutionCellObservation.from_dict(item)
                for item in data["execution_observations"]
            ),
            pair_assignments=tuple(
                BlindedPairAssignment.from_dict(item) for item in data["pair_assignments"]
            ),
            pair_observations=tuple(
                PairJudgeObservation.from_dict(item) for item in data["pair_observations"]
            ),
            hard_gate_observations=tuple(
                HardGateObservation.from_dict(item)
                for item in data["hard_gate_observations"]
            ),
            observed_at_utc=data["observed_at_utc"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
            authority_exclusions=tuple(data["authority_exclusions"]),
            benchmark_execution_authorized=data["benchmark_execution_authorized"],
            runtime_admission_authorized=data["runtime_admission_authorized"],
            empirical_authority=data["empirical_authority"],
            formula_authority=data["formula_authority"],
            physical_execution_authority=data["physical_execution_authority"],
            compounding_authority=data["compounding_authority"],
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            purchase_authority=data["purchase_authority"],
            release_authority=data["release_authority"],
        )


@dataclass(frozen=True, slots=True)
class ComparisonSummary(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_comparison_summary_v1"

    endpoint_key: str
    comparator_role: BenchmarkArmRole
    partition_scope: PartitionScope
    case_count: int
    pair_count: int
    evaluable_pair_count: int
    integrated_wins: int
    comparator_wins: int
    ties: int
    heterogeneous: int
    not_evaluable: int
    directional_win_fraction: ExactRatio
    net_wins: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "endpoint_key", _identifier(self.endpoint_key, "endpoint_key"))
        comparator = BenchmarkArmRole(self.comparator_role)
        if comparator not in {
            BenchmarkArmRole.PLAIN_SOL_XHIGH,
            BenchmarkArmRole.LENGTH_MATCHED_PLACEBO,
        }:
            raise ValueError("comparison summaries are limited to plain and placebo controls")
        object.__setattr__(self, "comparator_role", comparator)
        object.__setattr__(self, "partition_scope", PartitionScope(self.partition_scope))
        for field_name in (
            "case_count",
            "pair_count",
            "evaluable_pair_count",
            "integrated_wins",
            "comparator_wins",
            "ties",
            "heterogeneous",
            "not_evaluable",
        ):
            object.__setattr__(self, field_name, _nonnegative_int(getattr(self, field_name), field_name))
        if self.evaluable_pair_count != self.integrated_wins + self.comparator_wins + self.ties:
            raise ValueError("evaluable_pair_count must preserve directional outcomes and ties")
        if self.pair_count != self.evaluable_pair_count + self.heterogeneous + self.not_evaluable:
            raise ValueError("pair_count must preserve heterogeneous and not-evaluable outcomes")
        directional_total = self.integrated_wins + self.comparator_wins
        expected_fraction = ExactRatio(
            numerator=self.integrated_wins,
            denominator=directional_total or 1,
        )
        if not isinstance(self.directional_win_fraction, ExactRatio):
            raise TypeError("directional_win_fraction must be ExactRatio")
        if self.directional_win_fraction != expected_fraction:
            raise ValueError("directional_win_fraction does not match directional outcomes")
        expected_net = self.integrated_wins - self.comparator_wins
        net_wins = _signed_int(self.net_wins, "net_wins")
        if net_wins != expected_net:
            raise ValueError("net_wins does not match directional outcomes")
        object.__setattr__(self, "net_wins", net_wins)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComparisonSummary:
        data = _record_payload(cls, payload)
        return cls(
            endpoint_key=data["endpoint_key"],
            comparator_role=BenchmarkArmRole(data["comparator_role"]),
            partition_scope=PartitionScope(data["partition_scope"]),
            case_count=data["case_count"],
            pair_count=data["pair_count"],
            evaluable_pair_count=data["evaluable_pair_count"],
            integrated_wins=data["integrated_wins"],
            comparator_wins=data["comparator_wins"],
            ties=data["ties"],
            heterogeneous=data["heterogeneous"],
            not_evaluable=data["not_evaluable"],
            directional_win_fraction=ExactRatio.from_dict(
                data["directional_win_fraction"]
            ),
            net_wins=data["net_wins"],
        )


@dataclass(frozen=True, slots=True)
class FrozenBenchmarkEvaluation(_BenchmarkRecord):
    """Derived evaluation; admission must recompute it from the source packet."""

    SCHEMA_VERSION = "formulation_intelligence_frozen_benchmark_evaluation_v2"

    result_id: str
    benchmark_id: str
    observation_packet_sha256: str
    benchmark_definition_sha256: str
    source_identity_sha256: str
    workspace_state_sha256: str
    admission_challenge_nonce: str
    admission_request_scope_sha256: str
    verifier_identity: BenchmarkVerifierIdentity
    producer_independence_key: str
    scorer_independence_keys: tuple[str, ...]
    module_manifest_sha256s: tuple[str, ...]
    covered_module_ids: tuple[str, ...]
    covered_capability_ids: tuple[str, ...]
    covered_schema_ids: tuple[str, ...]
    artifact_closure_sha256: str
    covered_artifact_ids: tuple[str, ...]
    comparison_summaries: tuple[ComparisonSummary, ...]
    hard_gate_violation_keys: tuple[str, ...]
    failure_codes: tuple[str, ...]
    hold_codes: tuple[str, ...]
    evaluated_at_utc: str
    recursive_closure: RecursiveClosureReceiptRef
    benchmark_contract_satisfied: bool
    admission_authorized: bool
    empirical_authority: bool
    formula_authority: bool
    physical_execution_authority: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_id", _identifier(self.result_id, "result_id"))
        object.__setattr__(self, "benchmark_id", _identifier(self.benchmark_id, "benchmark_id"))
        for field_name in (
            "observation_packet_sha256",
            "benchmark_definition_sha256",
            "source_identity_sha256",
            "workspace_state_sha256",
            "admission_challenge_nonce",
            "admission_request_scope_sha256",
            "producer_independence_key",
            "artifact_closure_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        if not isinstance(self.verifier_identity, BenchmarkVerifierIdentity):
            raise TypeError("verifier_identity must be BenchmarkVerifierIdentity")
        object.__setattr__(
            self,
            "scorer_independence_keys",
            _digest_tuple(
                self.scorer_independence_keys,
                "scorer_independence_keys",
                nonempty=True,
            ),
        )
        object.__setattr__(
            self,
            "module_manifest_sha256s",
            _digest_tuple(
                self.module_manifest_sha256s,
                "module_manifest_sha256s",
                nonempty=True,
            ),
        )
        for field_name in (
            "covered_module_ids",
            "covered_capability_ids",
            "covered_schema_ids",
            "covered_artifact_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier_tuple(getattr(self, field_name), field_name, nonempty=True),
            )
        summaries = tuple(
            sorted(
                self.comparison_summaries,
                key=lambda item: (
                    item.partition_scope.value,
                    item.endpoint_key,
                    item.comparator_role.value,
                ),
            )
        )
        if any(not isinstance(item, ComparisonSummary) for item in summaries):
            raise TypeError("comparison_summaries must contain ComparisonSummary values")
        summary_keys = {
            (item.partition_scope, item.endpoint_key, item.comparator_role)
            for item in summaries
        }
        if len(summary_keys) != len(summaries):
            raise ValueError("comparison summary identities must be unique")
        object.__setattr__(self, "comparison_summaries", summaries)
        for field_name in (
            "hard_gate_violation_keys",
            "failure_codes",
            "hold_codes",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self, "evaluated_at_utc", _utc_timestamp(self.evaluated_at_utc, "evaluated_at_utc")
        )
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")
        expected_satisfied = not self.failure_codes and not self.hold_codes
        if self.benchmark_contract_satisfied is not expected_satisfied:
            raise ValueError("benchmark_contract_satisfied must be derived from blockers")
        if any(
            value is not False
            for value in (
                self.admission_authorized,
                self.empirical_authority,
                self.formula_authority,
                self.physical_execution_authority,
                self.compounding_authority,
                self.sensory_authority,
                self.liking_authority,
                self.safety_authority,
                self.stability_authority,
                self.purchase_authority,
                self.release_authority,
            )
        ):
            raise ValueError("benchmark evaluation cannot grant downstream authority")

    @property
    def status(self) -> BenchmarkEvaluationStatus:
        if self.failure_codes:
            return BenchmarkEvaluationStatus.FAIL
        if self.hold_codes:
            return BenchmarkEvaluationStatus.HOLD
        return BenchmarkEvaluationStatus.PASS

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenBenchmarkEvaluation:
        data = _record_payload(cls, payload)
        return cls(
            result_id=data["result_id"],
            benchmark_id=data["benchmark_id"],
            observation_packet_sha256=data["observation_packet_sha256"],
            benchmark_definition_sha256=data["benchmark_definition_sha256"],
            source_identity_sha256=data["source_identity_sha256"],
            workspace_state_sha256=data["workspace_state_sha256"],
            admission_challenge_nonce=data["admission_challenge_nonce"],
            admission_request_scope_sha256=data["admission_request_scope_sha256"],
            verifier_identity=BenchmarkVerifierIdentity.from_dict(data["verifier_identity"]),
            producer_independence_key=data["producer_independence_key"],
            scorer_independence_keys=tuple(data["scorer_independence_keys"]),
            module_manifest_sha256s=tuple(data["module_manifest_sha256s"]),
            covered_module_ids=tuple(data["covered_module_ids"]),
            covered_capability_ids=tuple(data["covered_capability_ids"]),
            covered_schema_ids=tuple(data["covered_schema_ids"]),
            artifact_closure_sha256=data["artifact_closure_sha256"],
            covered_artifact_ids=tuple(data["covered_artifact_ids"]),
            comparison_summaries=tuple(
                ComparisonSummary.from_dict(item) for item in data["comparison_summaries"]
            ),
            hard_gate_violation_keys=tuple(data["hard_gate_violation_keys"]),
            failure_codes=tuple(data["failure_codes"]),
            hold_codes=tuple(data["hold_codes"]),
            evaluated_at_utc=data["evaluated_at_utc"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
            benchmark_contract_satisfied=data["benchmark_contract_satisfied"],
            admission_authorized=data["admission_authorized"],
            empirical_authority=data["empirical_authority"],
            formula_authority=data["formula_authority"],
            physical_execution_authority=data["physical_execution_authority"],
            compounding_authority=data["compounding_authority"],
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            purchase_authority=data["purchase_authority"],
            release_authority=data["release_authority"],
        )


@dataclass(frozen=True, slots=True)
class FrozenBenchmarkVerificationBundle(_BenchmarkRecord):
    """Complete typed inputs that admission must independently re-evaluate."""

    SCHEMA_VERSION = "formulation_intelligence_frozen_benchmark_verification_bundle_v1"

    corpus: SealedPublicCorpus
    definition: FrozenBenchmarkDefinition
    execution_matrix: BenchmarkExecutionMatrix
    gate_contract: NonCompensatoryGateContract
    superiority_contract: SuperiorityDecisionContract
    scorer_mapping: BlindLabelMapping
    arm_role_mapping: ArmRoleMapping
    prompt_receipts: tuple[ArmPromptReceipt, ...]
    run_receipts: tuple[BenchmarkRunReceipt, ...]
    judge_receipts: tuple[JudgeReceipt, ...]
    observation_packet: FrozenBenchmarkObservationPacket
    verifier_identity: BenchmarkVerifierIdentity

    def __post_init__(self) -> None:
        typed_records: tuple[tuple[object, type[object], str], ...] = (
            (self.corpus, SealedPublicCorpus, "corpus"),
            (self.definition, FrozenBenchmarkDefinition, "definition"),
            (self.execution_matrix, BenchmarkExecutionMatrix, "execution_matrix"),
            (self.gate_contract, NonCompensatoryGateContract, "gate_contract"),
            (
                self.superiority_contract,
                SuperiorityDecisionContract,
                "superiority_contract",
            ),
            (self.scorer_mapping, BlindLabelMapping, "scorer_mapping"),
            (self.arm_role_mapping, ArmRoleMapping, "arm_role_mapping"),
            (
                self.observation_packet,
                FrozenBenchmarkObservationPacket,
                "observation_packet",
            ),
            (self.verifier_identity, BenchmarkVerifierIdentity, "verifier_identity"),
        )
        for value, expected_type, field_name in typed_records:
            if not isinstance(value, expected_type):
                raise TypeError(f"{field_name} must be {expected_type.__name__}")

        for field_name, expected_type, identity_field in (
            ("prompt_receipts", ArmPromptReceipt, "receipt_id"),
            ("run_receipts", BenchmarkRunReceipt, "run_id"),
            ("judge_receipts", JudgeReceipt, "judge_receipt_id"),
        ):
            values = tuple(
                sorted(
                    getattr(self, field_name),
                    key=lambda item: getattr(item, identity_field),
                )
            )
            if not values or any(not isinstance(item, expected_type) for item in values):
                raise TypeError(f"{field_name} must contain {expected_type.__name__} values")
            receipt_ids = tuple(getattr(item, identity_field) for item in values)
            if len(receipt_ids) != len(set(receipt_ids)):
                raise ValueError(f"{field_name} receipt_id values must be unique")
            object.__setattr__(self, field_name, values)

    def recompute(self) -> FrozenBenchmarkEvaluation:
        """Derive the result from complete evidence; never trust serialized status."""

        return evaluate_frozen_benchmark_result(
            corpus=self.corpus,
            definition=self.definition,
            execution_matrix=self.execution_matrix,
            gate_contract=self.gate_contract,
            superiority_contract=self.superiority_contract,
            scorer_mapping=self.scorer_mapping,
            arm_role_mapping=self.arm_role_mapping,
            prompt_receipts=self.prompt_receipts,
            run_receipts=self.run_receipts,
            judge_receipts=self.judge_receipts,
            observation_packet=self.observation_packet,
            verifier_identity=self.verifier_identity,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenBenchmarkVerificationBundle:
        data = _record_payload(cls, payload)
        return cls(
            corpus=SealedPublicCorpus.from_dict(data["corpus"]),
            definition=FrozenBenchmarkDefinition.from_dict(data["definition"]),
            execution_matrix=BenchmarkExecutionMatrix.from_dict(data["execution_matrix"]),
            gate_contract=NonCompensatoryGateContract.from_dict(data["gate_contract"]),
            superiority_contract=SuperiorityDecisionContract.from_dict(
                data["superiority_contract"]
            ),
            scorer_mapping=BlindLabelMapping.from_dict(data["scorer_mapping"]),
            arm_role_mapping=ArmRoleMapping.from_dict(data["arm_role_mapping"]),
            prompt_receipts=tuple(
                ArmPromptReceipt.from_dict(item) for item in data["prompt_receipts"]
            ),
            run_receipts=tuple(
                BenchmarkRunReceipt.from_dict(item) for item in data["run_receipts"]
            ),
            judge_receipts=tuple(
                JudgeReceipt.from_dict(item) for item in data["judge_receipts"]
            ),
            observation_packet=FrozenBenchmarkObservationPacket.from_dict(
                data["observation_packet"]
            ),
            verifier_identity=BenchmarkVerifierIdentity.from_dict(data["verifier_identity"]),
        )


def _unique_by_hash(
    values: Iterable[_BenchmarkRecord], *, field_name: str
) -> tuple[dict[str, _BenchmarkRecord], bool]:
    result: dict[str, _BenchmarkRecord] = {}
    duplicate = False
    for value in values:
        digest = value.content_sha256
        if digest in result:
            duplicate = True
        result[digest] = value
    return result, duplicate


def _current_by_identity(
    values: Iterable[Any], *, identity_field: str
) -> tuple[dict[str, list[Any]], set[str], set[str], set[str]]:
    current: dict[str, list[Any]] = {}
    dangling_supersedes: set[str] = set()
    cross_identity_supersedes: set[str] = set()
    valid_superseded: set[str] = set()
    records = tuple(values)
    by_hash = {item.content_sha256: item for item in records}
    for value in records:
        if (
            value.validity is EvaluationValidity.VALID
            and value.disposition is not ObservationDisposition.CURRENT
        ):
            valid_superseded.add(value.observation_id)
        supersedes = getattr(value, "supersedes_observation_sha256", None)
        if supersedes is not None:
            predecessor = by_hash.get(supersedes)
            if predecessor is None:
                dangling_supersedes.add(value.observation_id)
            else:
                if getattr(predecessor, identity_field) != getattr(
                    value, identity_field
                ):
                    cross_identity_supersedes.add(value.observation_id)
                if predecessor.validity is EvaluationValidity.VALID:
                    valid_superseded.add(predecessor.observation_id)
        if value.disposition is ObservationDisposition.CURRENT:
            current.setdefault(getattr(value, identity_field), []).append(value)
    return (
        current,
        dangling_supersedes,
        cross_identity_supersedes,
        valid_superseded,
    )


def _scorer_principal_key(judge_receipt: JudgeReceipt) -> str:
    """Bind scorer independence to one declared principal, not its settings."""

    return sha256(
        _canonical_json_bytes(
            {
                "provider_id": judge_receipt.scorer_provider_id,
                "scorer_identity": judge_receipt.scorer_identity,
            }
        )
    ).hexdigest()


def evaluate_frozen_benchmark_result(
    *,
    corpus: SealedPublicCorpus,
    definition: FrozenBenchmarkDefinition,
    execution_matrix: BenchmarkExecutionMatrix,
    gate_contract: NonCompensatoryGateContract,
    superiority_contract: SuperiorityDecisionContract,
    scorer_mapping: BlindLabelMapping,
    arm_role_mapping: ArmRoleMapping,
    prompt_receipts: tuple[ArmPromptReceipt, ...],
    run_receipts: tuple[BenchmarkRunReceipt, ...],
    judge_receipts: tuple[JudgeReceipt, ...],
    observation_packet: FrozenBenchmarkObservationPacket,
    verifier_identity: BenchmarkVerifierIdentity,
) -> FrozenBenchmarkEvaluation:
    """Recompute a complete, blinded, non-voting benchmark evaluation.

    Cross-object integrity problems become HOLD evidence.  Completed adverse
    observations (critical errors, comparator superiority, no-change regression,
    or seed/order instability) become FAIL evidence.  No majority vote is used:
    conflicting independent scorers are retained as HETEROGENEOUS and block.
    """

    typed_inputs: tuple[tuple[object, type[object], str], ...] = (
        (corpus, SealedPublicCorpus, "corpus"),
        (definition, FrozenBenchmarkDefinition, "definition"),
        (execution_matrix, BenchmarkExecutionMatrix, "execution_matrix"),
        (gate_contract, NonCompensatoryGateContract, "gate_contract"),
        (superiority_contract, SuperiorityDecisionContract, "superiority_contract"),
        (scorer_mapping, BlindLabelMapping, "scorer_mapping"),
        (arm_role_mapping, ArmRoleMapping, "arm_role_mapping"),
        (observation_packet, FrozenBenchmarkObservationPacket, "observation_packet"),
        (verifier_identity, BenchmarkVerifierIdentity, "verifier_identity"),
    )
    for value, expected_type, field_name in typed_inputs:
        if not isinstance(value, expected_type):
            raise TypeError(f"{field_name} must be {expected_type.__name__}")

    failures: set[str] = set()
    holds: set[str] = set()
    hard_gate_violations: set[str] = set()

    def hold(code: str) -> None:
        holds.add(_identifier(code, "hold_code"))

    def fail(code: str) -> None:
        failures.add(_identifier(code, "failure_code"))

    observed_pair_schedule_sha256 = pair_schedule_commitment_sha256(
        observation_packet.pair_assignments
    )
    expected_definition_bindings = {
        "benchmark_id": observation_packet.benchmark_id,
        "fixture_bytes_sha256": observation_packet.fixture_bytes_sha256,
        "canonical_corpus_sha256": observation_packet.canonical_corpus_sha256,
        "execution_matrix_sha256": observation_packet.execution_matrix_sha256,
        "gate_contract_sha256": observation_packet.gate_contract_sha256,
        "superiority_contract_sha256": observation_packet.superiority_contract_sha256,
        "blind_label_mapping_sha256": observation_packet.blind_mapping_sha256,
        "arm_role_mapping_sha256": observation_packet.arm_role_mapping_sha256,
        "pair_schedule_commitment_sha256": observed_pair_schedule_sha256,
        "rubric_sha256": observation_packet.rubric_sha256,
        "scorer_protocol_sha256": observation_packet.scorer_protocol_sha256,
    }
    if observation_packet.benchmark_definition_sha256 != definition.content_sha256:
        hold("benchmark_definition_hash_mismatch")
    for field_name, received in expected_definition_bindings.items():
        if getattr(definition, field_name) != received:
            hold(f"benchmark_definition_{field_name}_mismatch")
    if corpus.content_sha256 != definition.canonical_corpus_sha256:
        hold("canonical_corpus_hash_mismatch")
    if execution_matrix.content_sha256 != definition.execution_matrix_sha256:
        hold("execution_matrix_hash_mismatch")
    if gate_contract.content_sha256 != definition.gate_contract_sha256:
        hold("gate_contract_hash_mismatch")
    if superiority_contract.content_sha256 != definition.superiority_contract_sha256:
        hold("superiority_contract_hash_mismatch")
    if execution_matrix.corpus_sha256 != corpus.content_sha256:
        hold("execution_matrix_corpus_mismatch")
    if set(execution_matrix.case_ids) != {item.case_id for item in corpus.cases}:
        hold("execution_matrix_case_coverage_mismatch")
    if set(execution_matrix.arm_ids) != {item.arm_id for item in corpus.anonymized_arms}:
        hold("execution_matrix_arm_coverage_mismatch")
    if set(superiority_contract.required_endpoint_keys) != set(
        gate_contract.required_superiority_endpoint_keys
    ):
        hold("superiority_endpoint_contract_mismatch")
    if (
        superiority_contract.seed_order_stability_required
        and len(execution_matrix.seeds) < 2
    ):
        hold("seed_stability_design_insufficient")

    try:
        validate_blind_label_mapping(corpus, scorer_mapping=scorer_mapping)
    except (TypeError, ValueError):
        hold("blind_label_mapping_invalid")
    try:
        validate_arm_role_mapping(corpus, role_mapping=arm_role_mapping)
    except (TypeError, ValueError):
        hold("arm_role_mapping_invalid")
    if observation_packet.blind_mapping_sha256 != scorer_mapping.mapping_sha256:
        hold("blind_label_mapping_hash_mismatch")
    if observation_packet.arm_role_mapping_sha256 != arm_role_mapping.mapping_sha256:
        hold("arm_role_mapping_hash_mismatch")
    if definition.blind_label_mapping_sha256 != scorer_mapping.mapping_sha256:
        hold("benchmark_result_blind_mapping_commitment_mismatch")
    if definition.arm_role_mapping_sha256 != arm_role_mapping.mapping_sha256:
        hold("benchmark_result_arm_role_commitment_mismatch")
    if definition.pair_schedule_commitment_sha256 != observed_pair_schedule_sha256:
        hold("benchmark_result_schedule_commitment_mismatch")

    role_by_arm = {item.arm_id: item.role for item in arm_role_mapping.assignments}
    blind_arm_by_label = {
        item.blind_label: item.arm_id for item in scorer_mapping.assignments
    }
    instruction_by_role = {
        item.role: item.instruction_sha256
        for item in superiority_contract.role_instructions
    }
    case_by_id = {item.case_id: item for item in corpus.cases}
    cell_by_id = {item.cell_id: item for item in execution_matrix.cells}

    prompt_map_raw, duplicate_prompt_hash = _unique_by_hash(
        prompt_receipts, field_name="prompt_receipts"
    )
    prompt_by_hash = {
        key: value for key, value in prompt_map_raw.items() if isinstance(value, ArmPromptReceipt)
    }
    if duplicate_prompt_hash:
        hold("duplicate_prompt_receipt_hash")
    if set(prompt_by_hash) != set(observation_packet.prompt_receipt_sha256s):
        hold("prompt_receipt_manifest_mismatch")
    prompt_by_case_arm: dict[tuple[str, str], ArmPromptReceipt] = {}
    for prompt_receipt in prompt_receipts:
        if not isinstance(prompt_receipt, ArmPromptReceipt):
            raise TypeError("prompt_receipts must contain ArmPromptReceipt values")
        try:
            validate_arm_prompt_receipt(corpus, prompt_receipt)
        except (TypeError, ValueError):
            hold("prompt_receipt_binding_invalid")
        if not _same_closure(
            prompt_receipt.recursive_closure, observation_packet.recursive_closure
        ):
            hold("prompt_receipt_closure_mismatch")
        prompt_key = (prompt_receipt.case_id, prompt_receipt.arm_id)
        if prompt_key in prompt_by_case_arm:
            hold("duplicate_case_arm_prompt_receipt")
        prompt_by_case_arm[prompt_key] = prompt_receipt
        role = role_by_arm.get(prompt_receipt.arm_id)
        if (
            role is None
            or prompt_receipt.arm_instruction_sha256 != instruction_by_role.get(role)
        ):
            hold("prompt_role_instruction_hash_mismatch")
    expected_prompt_keys = {
        (case_id, arm_id)
        for case_id in execution_matrix.case_ids
        for arm_id in execution_matrix.arm_ids
    }
    if set(prompt_by_case_arm) != expected_prompt_keys:
        hold("prompt_case_arm_coverage_mismatch")

    run_map_raw, duplicate_run_hash = _unique_by_hash(run_receipts, field_name="run_receipts")
    run_by_hash = {
        key: value for key, value in run_map_raw.items() if isinstance(value, BenchmarkRunReceipt)
    }
    if duplicate_run_hash:
        hold("duplicate_run_receipt_hash")
    if set(run_by_hash) != set(observation_packet.run_receipt_sha256s):
        hold("run_receipt_manifest_mismatch")
    for run_receipt in run_receipts:
        if not isinstance(run_receipt, BenchmarkRunReceipt):
            raise TypeError("run_receipts must contain BenchmarkRunReceipt values")
        if not _same_closure(
            run_receipt.recursive_closure, observation_packet.recursive_closure
        ):
            hold("run_receipt_closure_mismatch")

    judge_map_raw, duplicate_judge_hash = _unique_by_hash(
        judge_receipts, field_name="judge_receipts"
    )
    judge_by_hash = {
        key: value for key, value in judge_map_raw.items() if isinstance(value, JudgeReceipt)
    }
    if duplicate_judge_hash:
        hold("duplicate_judge_receipt_hash")
    if set(judge_by_hash) != set(observation_packet.judge_receipt_sha256s):
        hold("judge_receipt_manifest_mismatch")
    for judge_receipt in judge_receipts:
        if not isinstance(judge_receipt, JudgeReceipt):
            raise TypeError("judge_receipts must contain JudgeReceipt values")
        if judge_receipt.rubric_sha256 != definition.rubric_sha256:
            hold("judge_receipt_rubric_mismatch")
        if not _same_closure(
            judge_receipt.recursive_closure, observation_packet.recursive_closure
        ):
            hold("judge_receipt_closure_mismatch")

    scorer_independence_keys = tuple(
        sorted({_scorer_principal_key(item) for item in judge_receipts})
    )
    if verifier_identity.independence_key == observation_packet.producer_independence_key:
        hold("benchmark_verifier_matches_result_producer")
    if verifier_identity.independence_key in scorer_independence_keys:
        hold("benchmark_verifier_matches_scorer")

    (
        execution_current,
        dangling_execution,
        cross_identity_execution,
        valid_superseded_execution,
    ) = _current_by_identity(
        observation_packet.execution_observations, identity_field="cell_id"
    )
    if dangling_execution:
        hold("execution_observation_dangling_supersedes")
    if cross_identity_execution:
        hold("execution_observation_cross_identity_supersedes")
    if valid_superseded_execution:
        hold("execution_valid_observation_superseded")
    if set(execution_current) != set(cell_by_id):
        hold("execution_observation_cell_coverage_mismatch")
    active_execution: dict[str, ExecutionCellObservation] = {}
    for cell_id, observations in execution_current.items():
        admissible = [item for item in observations if item.used_for_admission]
        if len(admissible) != 1:
            hold("execution_cell_requires_one_current_valid_observation")
            continue
        observation = admissible[0]
        active_execution[cell_id] = observation
        cell = cell_by_id.get(cell_id)
        prompt = prompt_by_hash.get(observation.prompt_receipt_sha256)
        run = run_by_hash.get(observation.run_receipt_sha256)
        if cell is None or prompt is None or run is None:
            hold("execution_observation_receipt_link_missing")
            continue
        expected_prompt = prompt_by_case_arm.get((cell.case_id, cell.arm_id))
        if expected_prompt is None or expected_prompt.content_sha256 != observation.prompt_receipt_sha256:
            hold("execution_observation_prompt_mismatch")
        if run.arm_prompt_receipt_sha256 != observation.prompt_receipt_sha256:
            hold("run_to_prompt_hash_mismatch")
        if run.execution_config_sha256 != cell.execution_config_sha256:
            hold("run_execution_config_hash_mismatch")
        if run.status is not RunStatus.COMPLETED or run.output_sha256 is None:
            hold("execution_cell_not_completed")
        role = role_by_arm.get(cell.arm_id)
        if role is None:
            hold("execution_cell_role_unknown")
        if run.model_id.casefold() != superiority_contract.benchmark_model_id.casefold():
            hold("benchmark_model_identity_mismatch")
        if run.reasoning_level != superiority_contract.frozen_reasoning_level:
            hold("benchmark_reasoning_level_mismatch")

    generation_groups: dict[
        tuple[str, str, int, int], list[ExecutionCellSpec]
    ] = {}
    for cell in execution_matrix.cells:
        generation_groups.setdefault(
            (cell.case_id, cell.arm_id, cell.seed, cell.repeat_index), []
        ).append(cell)
    used_generation_run_hashes: set[str] = set()
    generation_group_by_run_hash: dict[
        str, tuple[str, str, int, int]
    ] = {}
    for generation_key, cells in generation_groups.items():
        if {cell.order for cell in cells} != set(ExecutionOrder):
            hold("generation_presentation_order_coverage_mismatch")
            continue
        observations = [active_execution.get(cell.cell_id) for cell in cells]
        if any(observation is None for observation in observations):
            hold("generation_presentation_observation_missing")
            continue
        run_hashes = {
            observation.run_receipt_sha256
            for observation in observations
            if observation is not None
        }
        if len(run_hashes) != 1:
            hold("generation_output_not_reused_across_ab_ba")
            continue
        run_hash = next(iter(run_hashes))
        prior_generation_key = generation_group_by_run_hash.get(run_hash)
        if prior_generation_key is not None and prior_generation_key != generation_key:
            hold("generation_run_reused_across_replicates")
        generation_group_by_run_hash[run_hash] = generation_key
        used_generation_run_hashes.update(run_hashes)
    if set(run_by_hash) != used_generation_run_hashes:
        hold("generation_run_receipt_reference_coverage_mismatch")

    pair_by_id = {item.pair_id: item for item in observation_packet.pair_assignments}
    pair_group: dict[
        tuple[str, str, int, int, BenchmarkArmRole, ExecutionOrder],
        BlindedPairAssignment,
    ] = {}
    for assignment in observation_packet.pair_assignments:
        left_cell = cell_by_id.get(assignment.left_cell_id)
        right_cell = cell_by_id.get(assignment.right_cell_id)
        if assignment.validity is not EvaluationValidity.VALID:
            if assignment.validity is EvaluationValidity.ORDER_CONFOUNDED:
                fail("realized_order_confounded")
            else:
                hold("pair_assignment_invalid")
            continue
        if left_cell is None or right_cell is None:
            hold("pair_assignment_cell_missing")
            continue
        if left_cell.cell_id not in active_execution or right_cell.cell_id not in active_execution:
            hold("pair_assignment_cell_not_admissible")
        if left_cell.case_id != assignment.case_id or right_cell.case_id != assignment.case_id:
            hold("pair_assignment_case_mismatch")
        if (
            left_cell.seed != assignment.seed
            or right_cell.seed != assignment.seed
            or left_cell.repeat_index != assignment.repeat_index
            or right_cell.repeat_index != assignment.repeat_index
        ):
            hold("pair_assignment_seed_repeat_mismatch")
        if (
            left_cell.order is not assignment.realized_orientation
            or right_cell.order is not assignment.realized_orientation
        ):
            fail("pair_assignment_realized_order_cell_mismatch")
        if blind_arm_by_label.get(assignment.left_blind_label) != left_cell.arm_id:
            hold("pair_assignment_left_blind_label_mismatch")
        if blind_arm_by_label.get(assignment.right_blind_label) != right_cell.arm_id:
            hold("pair_assignment_right_blind_label_mismatch")
        left_role = role_by_arm.get(left_cell.arm_id)
        right_role = role_by_arm.get(right_cell.arm_id)
        role_set = {left_role, right_role}
        comparator_candidates = tuple(
            role
            for role in superiority_contract.required_comparator_roles
            if role in role_set
        )
        if (
            BenchmarkArmRole.INTEGRATED_CANDIDATE not in role_set
            or len(comparator_candidates) != 1
        ):
            hold("pair_assignment_not_integrated_vs_required_comparator")
            continue
        comparator = comparator_candidates[0]
        if assignment.realized_orientation is ExecutionOrder.AB:
            if left_role is not BenchmarkArmRole.INTEGRATED_CANDIDATE:
                fail("pair_assignment_ab_orientation_reversed")
        elif left_role is not comparator:
            fail("pair_assignment_ba_orientation_reversed")
        pair_key = (
            assignment.case_id,
            assignment.endpoint_key,
            assignment.seed,
            assignment.repeat_index,
            comparator,
            assignment.realized_orientation,
        )
        if pair_key in pair_group:
            hold("duplicate_pair_assignment_cell")
        pair_group[pair_key] = assignment

    expected_pair_keys = {
        (case_id, endpoint, seed, repeat_index, comparator, orientation)
        for case_id in execution_matrix.case_ids
        for endpoint in superiority_contract.required_endpoint_keys
        for seed in execution_matrix.seeds
        for repeat_index in range(execution_matrix.repeat_count)
        for comparator in superiority_contract.required_comparator_roles
        for orientation in superiority_contract.required_pair_orientations
    }
    if set(pair_group) != expected_pair_keys:
        hold("pair_assignment_exact_coverage_mismatch")

    (
        pair_observation_current,
        dangling_pair,
        cross_identity_pair,
        valid_superseded_pair,
    ) = _current_by_identity(
        observation_packet.pair_observations, identity_field="pair_id"
    )
    if dangling_pair:
        hold("pair_observation_dangling_supersedes")
    if cross_identity_pair:
        hold("pair_observation_cross_identity_supersedes")
    if valid_superseded_pair:
        hold("pair_valid_observation_superseded")
    if set(pair_observation_current) != set(pair_by_id):
        hold("pair_observation_pair_coverage_mismatch")

    pair_states: dict[str, DerivedPairState] = {}
    for pair_id, assignment in pair_by_id.items():
        observations = pair_observation_current.get(pair_id, [])
        gate_scorer_keys: set[str] = set()
        normalized: list[DerivedPairState] = []
        not_evaluable = assignment.validity is not EvaluationValidity.VALID
        for observation in observations:
            judge = judge_by_hash.get(observation.judge_receipt_sha256)
            if judge is None:
                hold("pair_observation_judge_receipt_missing")
                not_evaluable = True
                continue
            gate_scorer_keys.add(_scorer_principal_key(judge))
            if judge.blinded_bundle_sha256 != assignment.blinded_bundle_sha256:
                hold("pair_observation_blinded_bundle_mismatch")
                not_evaluable = True
            if judge.score_artifact_sha256 != observation.evidence_artifact_sha256:
                hold("pair_observation_score_artifact_mismatch")
                not_evaluable = True
            if observation.endpoint_key != assignment.endpoint_key:
                hold("pair_observation_endpoint_mismatch")
                not_evaluable = True
            if observation.disposition is not ObservationDisposition.CURRENT:
                continue
            if observation.validity is not EvaluationValidity.VALID:
                not_evaluable = True
                continue
            if observation.critical_error_codes:
                hold("pair_observation_critical_error_unattributed")
                not_evaluable = True
                continue
            left_cell = cell_by_id.get(assignment.left_cell_id)
            if left_cell is None:
                not_evaluable = True
                continue
            left_is_integrated = (
                role_by_arm.get(left_cell.arm_id)
                is BenchmarkArmRole.INTEGRATED_CANDIDATE
            )
            if observation.outcome is PairOutcome.TIE:
                normalized.append(DerivedPairState.TIE)
            elif observation.outcome is PairOutcome.LEFT:
                normalized.append(
                    DerivedPairState.INTEGRATED_WIN
                    if left_is_integrated
                    else DerivedPairState.COMPARATOR_WIN
                )
            elif observation.outcome is PairOutcome.RIGHT:
                normalized.append(
                    DerivedPairState.COMPARATOR_WIN
                    if left_is_integrated
                    else DerivedPairState.INTEGRATED_WIN
                )
            else:
                not_evaluable = True
        if len(gate_scorer_keys) < superiority_contract.minimum_independent_scorers:
            hold("pair_independent_scorer_count_insufficient")
            not_evaluable = True
        if not_evaluable or not normalized:
            pair_states[pair_id] = DerivedPairState.NOT_EVALUABLE
        else:
            directional = {
                item
                for item in normalized
                if item
                in {
                    DerivedPairState.INTEGRATED_WIN,
                    DerivedPairState.COMPARATOR_WIN,
                }
            }
            if len(directional) > 1:
                pair_states[pair_id] = DerivedPairState.HETEROGENEOUS
            elif len(directional) == 1:
                pair_states[pair_id] = next(iter(directional))
            else:
                pair_states[pair_id] = DerivedPairState.TIE

    (
        gate_current,
        dangling_gate,
        cross_identity_gate,
        valid_superseded_gate,
    ) = _current_by_identity(
        observation_packet.hard_gate_observations, identity_field="cell_id"
    )
    if dangling_gate:
        hold("hard_gate_observation_dangling_supersedes")
    if cross_identity_gate:
        hold("hard_gate_observation_cross_identity_supersedes")
    if valid_superseded_gate:
        hold("hard_gate_valid_observation_superseded")
    gate_requirements = {item.gate_key: item for item in gate_contract.hard_gates}
    gate_coverage: dict[tuple[str, str], list[HardGateObservation]] = {}
    for observations in gate_current.values():
        for observation in observations:
            gate_coverage.setdefault((observation.cell_id, observation.gate_key), []).append(
                observation
            )
    expected_gate_keys = {
        (cell_id, gate_key) for cell_id in cell_by_id for gate_key in gate_requirements
    }
    if set(gate_coverage) != expected_gate_keys:
        hold("hard_gate_exact_coverage_mismatch")
    for (cell_id, gate_key), observations in gate_coverage.items():
        if cell_id not in active_execution or gate_key not in gate_requirements:
            hold("hard_gate_observation_unknown_identity")
            continue
        scorer_keys: set[str] = set()
        valid_count = 0
        for observation in observations:
            judge = judge_by_hash.get(observation.judge_receipt_sha256)
            if judge is None:
                hold("hard_gate_judge_receipt_missing")
                continue
            scorer_keys.add(_scorer_principal_key(judge))
            if judge.score_artifact_sha256 != observation.evidence_artifact_sha256:
                hold("hard_gate_score_artifact_mismatch")
            if observation.validity is not EvaluationValidity.VALID:
                hold("hard_gate_observation_not_valid")
                continue
            valid_count += 1
            requirement = gate_requirements[gate_key]
            if observation.critical_error_count > requirement.maximum_critical_errors:
                cell = cell_by_id.get(cell_id)
                role = None if cell is None else role_by_arm.get(cell.arm_id)
                if role in _ADMISSION_CRITICAL_GATE_ROLES:
                    hard_gate_violations.add(gate_key)
                    fail(f"critical_gate_{gate_key}_failed")
        if len(scorer_keys) < superiority_contract.minimum_independent_scorers:
            hold("hard_gate_independent_scorer_count_insufficient")
        if valid_count < superiority_contract.minimum_independent_scorers:
            hold("hard_gate_valid_observation_count_insufficient")

    replicate_states: dict[
        tuple[str, str, BenchmarkArmRole, int, int], DerivedPairState
    ] = {}
    stability_groups: dict[
        tuple[str, str, BenchmarkArmRole, int, int],
        dict[ExecutionOrder, DerivedPairState],
    ] = {}
    for stability_key, assignment in pair_group.items():
        case_id, endpoint, seed, repeat_index, comparator, orientation = stability_key
        stability_groups.setdefault(
            (case_id, endpoint, comparator, seed, repeat_index), {}
        )[orientation] = pair_states.get(
            assignment.pair_id, DerivedPairState.NOT_EVALUABLE
        )
    for replicate_key, orientation_states in stability_groups.items():
        if set(orientation_states) != set(ExecutionOrder):
            hold("seed_order_orientation_incomplete")
            replicate_states[replicate_key] = DerivedPairState.NOT_EVALUABLE
            continue
        orientation_state_set = set(orientation_states.values())
        if DerivedPairState.HETEROGENEOUS in orientation_state_set:
            hold("seed_order_evidence_not_evaluable")
            replicate_states[replicate_key] = DerivedPairState.HETEROGENEOUS
            continue
        if DerivedPairState.NOT_EVALUABLE in orientation_state_set:
            hold("seed_order_evidence_not_evaluable")
            replicate_states[replicate_key] = DerivedPairState.NOT_EVALUABLE
            continue
        directional = orientation_state_set & {
            DerivedPairState.INTEGRATED_WIN,
            DerivedPairState.COMPARATOR_WIN,
        }
        if len(directional) > 1:
            fail("ab_ba_directional_instability")
            replicate_states[replicate_key] = DerivedPairState.NOT_EVALUABLE
            continue
        if len(orientation_state_set) > 1:
            hold("ab_ba_outcome_instability")
            replicate_states[replicate_key] = DerivedPairState.NOT_EVALUABLE
            continue
        collapsed_state = next(iter(orientation_state_set))
        replicate_states[replicate_key] = collapsed_state

    case_outcomes: dict[
        tuple[str, str, BenchmarkArmRole], set[DerivedPairState]
    ] = {}
    for (case_id, endpoint, comparator, _seed, _repeat), state in (
        replicate_states.items()
    ):
        case_outcomes.setdefault((case_id, endpoint, comparator), set()).add(
            state
        )

    case_level_states: dict[
        tuple[str, str, BenchmarkArmRole], DerivedPairState
    ] = {}
    for case_key, outcomes in case_outcomes.items():
        directional = outcomes & {
            DerivedPairState.INTEGRATED_WIN,
            DerivedPairState.COMPARATOR_WIN,
        }
        if DerivedPairState.HETEROGENEOUS in outcomes:
            case_level_states[case_key] = DerivedPairState.HETEROGENEOUS
        elif DerivedPairState.NOT_EVALUABLE in outcomes:
            case_level_states[case_key] = DerivedPairState.NOT_EVALUABLE
        elif len(directional) > 1:
            fail("seed_repeat_directional_instability")
            case_level_states[case_key] = DerivedPairState.NOT_EVALUABLE
        elif len(outcomes) > 1:
            hold("seed_repeat_outcome_instability")
            case_level_states[case_key] = DerivedPairState.NOT_EVALUABLE
        elif outcomes:
            case_level_states[case_key] = next(iter(outcomes))

    expected_case_level_keys = {
        (case_id, endpoint, comparator)
        for case_id in execution_matrix.case_ids
        for endpoint in superiority_contract.required_endpoint_keys
        for comparator in superiority_contract.required_comparator_roles
    }
    if set(case_level_states) != expected_case_level_keys:
        hold("case_level_superiority_coverage_incomplete")
        for key in expected_case_level_keys - set(case_level_states):
            case_level_states[key] = DerivedPairState.NOT_EVALUABLE

    summaries: list[ComparisonSummary] = []
    for scope in PartitionScope:
        scoped_case_ids = {
            case_id
            for case_id, case in case_by_id.items()
            if scope is PartitionScope.ALL or case.partition is CorpusPartition.HELD_OUT
        }
        for endpoint in superiority_contract.required_endpoint_keys:
            for comparator in superiority_contract.required_comparator_roles:
                states = [
                    state
                    for key, state in case_level_states.items()
                    if key[0] in scoped_case_ids
                    and key[1] == endpoint
                    and key[2] is comparator
                ]
                integrated_wins = states.count(DerivedPairState.INTEGRATED_WIN)
                comparator_wins = states.count(DerivedPairState.COMPARATOR_WIN)
                ties = states.count(DerivedPairState.TIE)
                heterogeneous = states.count(DerivedPairState.HETEROGENEOUS)
                not_evaluable_count = states.count(DerivedPairState.NOT_EVALUABLE)
                directional_total = integrated_wins + comparator_wins
                fraction = ExactRatio(
                    numerator=integrated_wins,
                    denominator=directional_total or 1,
                )
                summary = ComparisonSummary(
                    endpoint_key=endpoint,
                    comparator_role=comparator,
                    partition_scope=scope,
                    case_count=len(scoped_case_ids),
                    pair_count=len(states),
                    evaluable_pair_count=integrated_wins + comparator_wins + ties,
                    integrated_wins=integrated_wins,
                    comparator_wins=comparator_wins,
                    ties=ties,
                    heterogeneous=heterogeneous,
                    not_evaluable=not_evaluable_count,
                    directional_win_fraction=fraction,
                    net_wins=integrated_wins - comparator_wins,
                )
                summaries.append(summary)
                suffix = f"{scope.value}_{endpoint}_{comparator.value}"
                if heterogeneous:
                    hold(f"heterogeneous_scorer_evidence_{suffix}")
                if not_evaluable_count:
                    hold(f"not_evaluable_pair_evidence_{suffix}")
                if summary.evaluable_pair_count < superiority_contract.minimum_evaluable_pairs_per_endpoint:
                    hold(f"insufficient_evaluable_pairs_{suffix}")
                elif (
                    directional_total == 0
                    or not summary.directional_win_fraction.is_at_least(
                        superiority_contract.minimum_win_fraction
                    )
                    or summary.net_wins < superiority_contract.minimum_net_wins
                ):
                    fail(f"superiority_not_demonstrated_{suffix}")

    safe_case_ids = {
        item.case_id for item in corpus.cases if "safe_no_change" in item.challenge_tags
    }
    if not safe_case_ids:
        hold("safe_no_change_cases_missing")
    for safe_case_key, state in case_level_states.items():
        if safe_case_key[0] not in safe_case_ids:
            continue
        if state is DerivedPairState.COMPARATOR_WIN:
            fail("safe_no_change_regression")
        elif state in {DerivedPairState.HETEROGENEOUS, DerivedPairState.NOT_EVALUABLE}:
            hold("safe_no_change_evidence_incomplete")

    return FrozenBenchmarkEvaluation(
        result_id=observation_packet.result_id,
        benchmark_id=observation_packet.benchmark_id,
        observation_packet_sha256=observation_packet.content_sha256,
        benchmark_definition_sha256=definition.content_sha256,
        source_identity_sha256=observation_packet.source_identity_sha256,
        workspace_state_sha256=observation_packet.workspace_state_sha256,
        admission_challenge_nonce=observation_packet.admission_challenge_nonce,
        admission_request_scope_sha256=(
            observation_packet.admission_request_scope_sha256
        ),
        verifier_identity=verifier_identity,
        producer_independence_key=observation_packet.producer_independence_key,
        scorer_independence_keys=scorer_independence_keys,
        module_manifest_sha256s=observation_packet.module_manifest_sha256s,
        covered_module_ids=observation_packet.covered_module_ids,
        covered_capability_ids=observation_packet.covered_capability_ids,
        covered_schema_ids=observation_packet.covered_schema_ids,
        artifact_closure_sha256=observation_packet.artifact_closure_sha256,
        covered_artifact_ids=observation_packet.covered_artifact_ids,
        comparison_summaries=tuple(summaries),
        hard_gate_violation_keys=tuple(hard_gate_violations),
        failure_codes=tuple(failures),
        hold_codes=tuple(holds),
        evaluated_at_utc=observation_packet.observed_at_utc,
        recursive_closure=observation_packet.recursive_closure,
        benchmark_contract_satisfied=not failures and not holds,
        admission_authorized=False,
        empirical_authority=False,
        formula_authority=False,
        physical_execution_authority=False,
        compounding_authority=False,
        sensory_authority=False,
        liking_authority=False,
        safety_authority=False,
        stability_authority=False,
        purchase_authority=False,
        release_authority=False,
    )


__all__ = [
    "ArmRoleAssignment",
    "ArmRoleInstruction",
    "ArmRoleMapping",
    "BenchmarkArmRole",
    "BenchmarkEvaluationStatus",
    "BenchmarkExecutionMatrix",
    "BenchmarkVerifierIdentity",
    "BlindedPairAssignment",
    "CampaignArtifactAudience",
    "CampaignArtifactBinding",
    "CampaignArtifactKind",
    "ComparisonSummary",
    "DerivedPairState",
    "EvaluationValidity",
    "ExecutionCellObservation",
    "ExecutionCellSpec",
    "ExecutionOrder",
    "ExactRatio",
    "FrozenBenchmarkDefinition",
    "FrozenBenchmarkEvaluation",
    "FrozenBenchmarkObservationPacket",
    "FrozenBenchmarkVerificationBundle",
    "FrozenCampaignManifest",
    "HardGateObservation",
    "ObservationDisposition",
    "PairJudgeObservation",
    "PairOutcome",
    "PartitionScope",
    "SuperiorityDecisionContract",
    "blinded_pair_assignment_commitment_sha256",
    "blinded_pair_schedule_sha256",
    "build_minimum_seed_order_execution_matrix",
    "evaluate_frozen_benchmark_result",
    "execution_cell_config_sha256",
    "execution_cell_id",
    "pair_schedule_commitment_sha256",
    "validate_arm_role_mapping",
]
