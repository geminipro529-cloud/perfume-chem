"""Closed, deterministic records for the shadow SolForge evidence loop."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, ClassVar, Mapping

from engine.evidence.augmentation import (
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
)
from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CRITERIA = frozenset({"TARGET_FIDELITY", "DEPTH", "RICHNESS", "LIKING"})
AUTHORITY_FLAGS_FALSE = {
    "compounding": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class SolForgeCaseState(str, Enum):
    READY = "READY"
    HOLD = "HOLD"


class CompilationState(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    COMPILED = "COMPILED"
    HOLD = "HOLD"


class DecisionState(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    TEST_NEXT = "TEST_NEXT"
    RETAIN_CURRENT = "RETAIN_CURRENT"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    HOLD = "HOLD"


class _FrozenObject(tuple):
    pass


class _FrozenArray(tuple):
    pass


def _freeze_json(value: object) -> object:
    if isinstance(value, (_FrozenObject, _FrozenArray)):
        return value
    if isinstance(value, Mapping):
        pairs: list[tuple[str, object]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            pairs.append((key, _freeze_json(item)))
        return _FrozenObject(sorted(pairs))
    if isinstance(value, (list, tuple)):
        return _FrozenArray(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _thaw_json(value: object) -> object:
    if isinstance(value, _FrozenObject):
        return {key: _thaw_json(item) for key, item in value}
    if isinstance(value, _FrozenArray):
        return [_thaw_json(item) for item in value]
    return value


def _text(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _sha(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{name} must be a lower-case SHA-256 digest")
    return value


def _texts(values: object, name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    return tuple(str(_text(value, name)) for value in values)


def _finite(value: object, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{name} is outside its allowed range")
    return result


def _criterion(value: object) -> str:
    result = str(_text(value, "criterion")).upper()
    if result not in _CRITERIA:
        raise ValueError(f"criterion must be one of {sorted(_CRITERIA)}")
    return result


def _load(
    payload: object,
    *,
    schema_version: str,
    fields: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("record payload must be an object")
    expected = fields | {"schema_version", "authority_flags"}
    unknown = set(payload).difference(expected)
    missing = expected.difference(payload)
    if unknown:
        raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
    if missing:
        raise ValueError("missing fields: " + ", ".join(sorted(missing)))
    if payload["schema_version"] != schema_version:
        raise ValueError(f"schema_version must be {schema_version}")
    if payload["authority_flags"] != AUTHORITY_FLAGS_FALSE:
        raise ValueError("authority_flags must be the exact all-false mapping")
    return {field: payload[field] for field in fields}


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    def _envelope(self, fields: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **fields,
            "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
        }


@dataclass(frozen=True, slots=True)
class SolForgeCaseV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "solforge_case_v1"
    state: SolForgeCaseState
    case_id: str
    target_identity: str
    ideal_architecture: object
    current_inventory_build: object
    inventory_path: str
    inventory_sha256: str
    formula_sha256: str
    dose_receipt_sha256: str
    constraints: tuple[str, ...]
    criterion: str
    forbidden_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", SolForgeCaseState(self.state))
        for name in ("case_id", "target_identity", "inventory_path"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("inventory_sha256", "formula_sha256", "dose_receipt_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        object.__setattr__(self, "ideal_architecture", _freeze_json(self.ideal_architecture))
        object.__setattr__(
            self, "current_inventory_build", _freeze_json(self.current_inventory_build)
        )
        object.__setattr__(self, "constraints", _texts(self.constraints, "constraints"))
        object.__setattr__(self, "criterion", _criterion(self.criterion))
        object.__setattr__(
            self, "forbidden_claims", _texts(self.forbidden_claims, "forbidden_claims")
        )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "state": self.state.value,
                "case_id": self.case_id,
                "target_identity": self.target_identity,
                "ideal_architecture": _thaw_json(self.ideal_architecture),
                "current_inventory_build": _thaw_json(self.current_inventory_build),
                "inventory_path": self.inventory_path,
                "inventory_sha256": self.inventory_sha256,
                "formula_sha256": self.formula_sha256,
                "dose_receipt_sha256": self.dose_receipt_sha256,
                "constraints": list(self.constraints),
                "criterion": self.criterion,
                "forbidden_claims": list(self.forbidden_claims),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> SolForgeCaseV1:
        fields = frozenset(
            {
                "state", "case_id", "target_identity", "ideal_architecture",
                "current_inventory_build", "inventory_path", "inventory_sha256",
                "formula_sha256", "dose_receipt_sha256", "constraints", "criterion",
                "forbidden_claims",
            }
        )
        return cls(**_load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields))


@dataclass(frozen=True, slots=True)
class SolHypothesisV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "sol_hypothesis_v1"
    hypothesis_id: str
    rank: int
    claim: str
    target_function: str
    material_names: tuple[str, ...]
    intervention_kind: str
    expected_behavior: str
    rationale: str
    uncertainty: float
    evidence_refs: tuple[str, ...]
    nary_factors: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "hypothesis_id", "claim", "target_function", "expected_behavior", "rationale"
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 1:
            raise ValueError("rank must be a positive integer")
        kind = str(_text(self.intervention_kind, "intervention_kind")).upper()
        if kind not in {"OMISSION", "ADDITION", "RATIO", "NARY_DESIGN", "NO_CHANGE"}:
            raise ValueError("intervention_kind is invalid")
        object.__setattr__(self, "intervention_kind", kind)
        object.__setattr__(self, "material_names", _texts(self.material_names, "material_names"))
        object.__setattr__(self, "nary_factors", _texts(self.nary_factors, "nary_factors"))
        object.__setattr__(self, "uncertainty", _finite(self.uncertainty, "uncertainty", minimum=0))
        if self.uncertainty > 1:
            raise ValueError("uncertainty must be at most 1")
        refs = tuple(str(_sha(value, "evidence_ref")) for value in self.evidence_refs)
        object.__setattr__(self, "evidence_refs", refs)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "hypothesis_id": self.hypothesis_id, "rank": self.rank,
                "claim": self.claim, "target_function": self.target_function,
                "material_names": list(self.material_names),
                "intervention_kind": self.intervention_kind,
                "expected_behavior": self.expected_behavior, "rationale": self.rationale,
                "uncertainty": self.uncertainty, "evidence_refs": list(self.evidence_refs),
                "nary_factors": list(self.nary_factors),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> SolHypothesisV1:
        fields = frozenset(
            {"hypothesis_id", "rank", "claim", "target_function", "material_names",
             "intervention_kind", "expected_behavior", "rationale", "uncertainty",
             "evidence_refs", "nary_factors"}
        )
        return cls(**_load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields))


@dataclass(frozen=True, slots=True)
class SolHypothesisSetV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "sol_hypothesis_set_v1"
    case_sha256: str
    model_identity: str
    reasoning_setting: str
    prompt_sha256: str
    input_sha256: str
    output_sha256: str
    hypotheses: tuple[SolHypothesisV1, ...]
    uncertainty: str

    def __post_init__(self) -> None:
        for name in ("case_sha256", "prompt_sha256", "input_sha256", "output_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        for name in ("model_identity", "reasoning_setting", "uncertainty"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        hypotheses = tuple(self.hypotheses)
        if any(not isinstance(item, SolHypothesisV1) for item in hypotheses):
            raise TypeError("hypotheses must contain SolHypothesisV1 records")
        ids = [item.hypothesis_id for item in hypotheses]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate hypothesis_id")
        if len([item for item in hypotheses if item.rank == 1]) > 1:
            raise ValueError("multiple first-ranked interventions")
        object.__setattr__(self, "hypotheses", hypotheses)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"case_sha256": self.case_sha256, "model_identity": self.model_identity,
             "reasoning_setting": self.reasoning_setting, "prompt_sha256": self.prompt_sha256,
             "input_sha256": self.input_sha256, "output_sha256": self.output_sha256,
             "hypotheses": [item.as_dict() for item in self.hypotheses],
             "uncertainty": self.uncertainty}
        )

    @classmethod
    def from_dict(cls, payload: object) -> SolHypothesisSetV1:
        fields = frozenset(
            {"case_sha256", "model_identity", "reasoning_setting", "prompt_sha256",
             "input_sha256", "output_sha256", "hypotheses", "uncertainty"}
        )
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["hypotheses"] = tuple(SolHypothesisV1.from_dict(item) for item in values["hypotheses"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class CompiledArmV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "compiled_arm_v1"
    arm_id: str
    formula: object
    total_active_mass_g: float
    blind_code: str
    sample_sha256: str

    def __post_init__(self) -> None:
        for name in ("arm_id", "blind_code"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "formula", _freeze_json(self.formula))
        object.__setattr__(self, "total_active_mass_g", _finite(self.total_active_mass_g, "total_active_mass_g", minimum=0))
        object.__setattr__(self, "sample_sha256", _sha(self.sample_sha256, "sample_sha256"))

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"arm_id": self.arm_id, "formula": _thaw_json(self.formula),
             "total_active_mass_g": self.total_active_mass_g,
             "blind_code": self.blind_code, "sample_sha256": self.sample_sha256}
        )

    @classmethod
    def from_dict(cls, payload: object) -> CompiledArmV1:
        fields = frozenset({"arm_id", "formula", "total_active_mass_g", "blind_code", "sample_sha256"})
        return cls(**_load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields))


@dataclass(frozen=True, slots=True)
class CompiledExperimentV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "compiled_experiment_v1"
    case_sha256: str
    hypothesis_set_sha256: str
    inventory_refresh_sha256: str
    inventory_source_row_count: int
    state: CompilationState
    delta_kind: str | None
    selected_hypothesis_id: str | None
    arms: tuple[CompiledArmV1, ...]
    blockers: tuple[str, ...]
    inventory_statuses: tuple[tuple[str, str], ...]
    omission_loss: str | None
    failure_mode: str | None
    next_comparison: str | None

    def __post_init__(self) -> None:
        for name in ("case_sha256", "hypothesis_set_sha256", "inventory_refresh_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        if isinstance(self.inventory_source_row_count, bool) or not isinstance(self.inventory_source_row_count, int) or self.inventory_source_row_count < 0:
            raise ValueError("inventory_source_row_count must be a nonnegative integer")
        object.__setattr__(self, "state", CompilationState(self.state))
        kind = None if self.delta_kind is None else str(_text(self.delta_kind, "delta_kind")).upper()
        if kind not in {None, "OMISSION", "ADDITION", "RATIO", "NARY_DESIGN"}:
            raise ValueError("delta_kind is invalid")
        object.__setattr__(self, "delta_kind", kind)
        object.__setattr__(self, "selected_hypothesis_id", _text(self.selected_hypothesis_id, "selected_hypothesis_id", optional=True))
        arms = tuple(self.arms)
        if any(not isinstance(arm, CompiledArmV1) for arm in arms):
            raise TypeError("arms must contain CompiledArmV1 records")
        ids = [arm.arm_id for arm in arms]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate arm_id")
        blind_codes = [arm.blind_code for arm in arms]
        if len(blind_codes) != len(set(blind_codes)):
            raise ValueError("duplicate blind_code")
        object.__setattr__(self, "arms", arms)
        object.__setattr__(self, "blockers", _texts(self.blockers, "blockers"))
        statuses = tuple((str(_text(name, "inventory material")), str(_text(status, "inventory status")).upper()) for name, status in self.inventory_statuses)
        object.__setattr__(self, "inventory_statuses", statuses)
        for name in ("omission_loss", "failure_mode", "next_comparison"):
            object.__setattr__(self, name, _text(getattr(self, name), name, optional=True))

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"case_sha256": self.case_sha256, "hypothesis_set_sha256": self.hypothesis_set_sha256,
             "inventory_refresh_sha256": self.inventory_refresh_sha256,
             "inventory_source_row_count": self.inventory_source_row_count,
             "state": self.state.value, "delta_kind": self.delta_kind,
             "selected_hypothesis_id": self.selected_hypothesis_id,
             "arms": [arm.as_dict() for arm in self.arms], "blockers": list(self.blockers),
             "inventory_statuses": [list(item) for item in self.inventory_statuses],
             "omission_loss": self.omission_loss, "failure_mode": self.failure_mode,
             "next_comparison": self.next_comparison}
        )

    @classmethod
    def from_dict(cls, payload: object) -> CompiledExperimentV1:
        fields = frozenset(
            {"case_sha256", "hypothesis_set_sha256", "inventory_refresh_sha256",
             "inventory_source_row_count", "state", "delta_kind", "selected_hypothesis_id",
             "arms", "blockers", "inventory_statuses", "omission_loss", "failure_mode",
             "next_comparison"}
        )
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["arms"] = tuple(CompiledArmV1.from_dict(item) for item in values["arms"])
        values["inventory_statuses"] = tuple(tuple(item) for item in values["inventory_statuses"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class ExecutionReceiptV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "execution_receipt_v1"
    compiled_experiment_sha256: str
    executor: str
    execution_context: object
    sample_sha256: tuple[tuple[str, str], ...]
    deviations: tuple[str, ...]
    test_only: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "compiled_experiment_sha256", _sha(self.compiled_experiment_sha256, "compiled_experiment_sha256"))
        object.__setattr__(self, "executor", _text(self.executor, "executor"))
        object.__setattr__(self, "execution_context", _freeze_json(self.execution_context))
        samples = tuple((str(_text(name, "sample id")), str(_sha(digest, "sample_sha256"))) for name, digest in self.sample_sha256)
        if len(samples) != len({name for name, _ in samples}):
            raise ValueError("duplicate sample id")
        object.__setattr__(self, "sample_sha256", samples)
        object.__setattr__(self, "deviations", _texts(self.deviations, "deviations"))
        if not isinstance(self.test_only, bool):
            raise TypeError("test_only must be boolean")
        context = _thaw_json(self.execution_context)
        synthetic = "SYNTHETIC" in self.executor.upper() or (isinstance(context, dict) and context.get("synthetic") is True)
        if synthetic and not self.test_only:
            raise ValueError("synthetic execution requires test_only=True")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"compiled_experiment_sha256": self.compiled_experiment_sha256,
             "executor": self.executor, "execution_context": _thaw_json(self.execution_context),
             "sample_sha256": [list(item) for item in self.sample_sha256],
             "deviations": list(self.deviations), "test_only": self.test_only}
        )

    @classmethod
    def from_dict(cls, payload: object) -> ExecutionReceiptV1:
        fields = frozenset({"compiled_experiment_sha256", "executor", "execution_context", "sample_sha256", "deviations", "test_only"})
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["sample_sha256"] = tuple(tuple(item) for item in values["sample_sha256"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class TemporalEvidencePacketV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "temporal_evidence_packet_v1"
    execution_receipt_sha256: str
    ledger_payload_sha256: str
    state: str
    observed_cell_count: int
    missing_cells: tuple[str, ...]
    duplicate_cells: tuple[str, ...]
    disagreement: object
    safety_stop: bool
    next_discriminator: str | None
    test_only: bool

    def __post_init__(self) -> None:
        for name in ("execution_receipt_sha256", "ledger_payload_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        state = str(_text(self.state, "state")).upper()
        if state not in {"COMPLETE", "DIAGNOSTIC", "INSUFFICIENT", "HOLD"}:
            raise ValueError("temporal evidence state is invalid")
        object.__setattr__(self, "state", state)
        if isinstance(self.observed_cell_count, bool) or not isinstance(self.observed_cell_count, int) or self.observed_cell_count < 0:
            raise ValueError("observed_cell_count must be a nonnegative integer")
        object.__setattr__(self, "missing_cells", _texts(self.missing_cells, "missing_cells"))
        object.__setattr__(self, "duplicate_cells", _texts(self.duplicate_cells, "duplicate_cells"))
        object.__setattr__(self, "disagreement", _freeze_json(self.disagreement))
        for name in ("safety_stop", "test_only"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        object.__setattr__(self, "next_discriminator", _text(self.next_discriminator, "next_discriminator", optional=True))

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"execution_receipt_sha256": self.execution_receipt_sha256,
             "ledger_payload_sha256": self.ledger_payload_sha256, "state": self.state,
             "observed_cell_count": self.observed_cell_count,
             "missing_cells": list(self.missing_cells), "duplicate_cells": list(self.duplicate_cells),
             "disagreement": _thaw_json(self.disagreement), "safety_stop": self.safety_stop,
             "next_discriminator": self.next_discriminator, "test_only": self.test_only}
        )

    @classmethod
    def from_dict(cls, payload: object) -> TemporalEvidencePacketV1:
        fields = frozenset({"execution_receipt_sha256", "ledger_payload_sha256", "state", "observed_cell_count", "missing_cells", "duplicate_cells", "disagreement", "safety_stop", "next_discriminator", "test_only"})
        return cls(**_load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields))


@dataclass(frozen=True, slots=True)
class CriterionFitPacketV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "criterion_fit_packet_v1"
    temporal_evidence_sha256: str
    comparison_payload_sha256: str
    criterion: str
    preference_result_sha256: str
    validation_state: str
    utility_intervals: object
    tie_rate: float
    assessor_heterogeneity: float | None
    order_effect: float | None
    next_pair: tuple[str, str] | None
    test_only: bool

    def __post_init__(self) -> None:
        for name in ("temporal_evidence_sha256", "comparison_payload_sha256", "preference_result_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        object.__setattr__(self, "criterion", _criterion(self.criterion))
        state = str(_text(self.validation_state, "validation_state")).upper()
        if state not in {"VALIDATED_EXACT_SCOPE", "DIAGNOSTIC", "WITHHELD", "FAILED_BASELINE", "NOT_TESTED", "INVALID"}:
            raise ValueError("validation_state is invalid")
        object.__setattr__(self, "validation_state", state)
        object.__setattr__(self, "utility_intervals", _freeze_json(self.utility_intervals))
        object.__setattr__(self, "tie_rate", _finite(self.tie_rate, "tie_rate", minimum=0))
        if self.tie_rate > 1:
            raise ValueError("tie_rate must be at most 1")
        for name in ("assessor_heterogeneity", "order_effect"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _finite(value, name, minimum=0))
        if self.next_pair is not None:
            if len(self.next_pair) != 2:
                raise ValueError("next_pair must contain exactly two item ids")
            object.__setattr__(self, "next_pair", tuple(str(_text(item, "next_pair")) for item in self.next_pair))
        if not isinstance(self.test_only, bool):
            raise TypeError("test_only must be boolean")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"temporal_evidence_sha256": self.temporal_evidence_sha256,
             "comparison_payload_sha256": self.comparison_payload_sha256,
             "criterion": self.criterion, "preference_result_sha256": self.preference_result_sha256,
             "validation_state": self.validation_state,
             "utility_intervals": _thaw_json(self.utility_intervals), "tie_rate": self.tie_rate,
             "assessor_heterogeneity": self.assessor_heterogeneity, "order_effect": self.order_effect,
             "next_pair": None if self.next_pair is None else list(self.next_pair),
             "test_only": self.test_only}
        )

    @classmethod
    def from_dict(cls, payload: object) -> CriterionFitPacketV1:
        fields = frozenset({"temporal_evidence_sha256", "comparison_payload_sha256", "criterion", "preference_result_sha256", "validation_state", "utility_intervals", "tie_rate", "assessor_heterogeneity", "order_effect", "next_pair", "test_only"})
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        if values["next_pair"] is not None:
            values["next_pair"] = tuple(values["next_pair"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class CriterionFitPacketV2(_Record):
    """Versioned proper-scoring preference packet preserving the V1 parent."""

    SCHEMA_VERSION: ClassVar[str] = "criterion_fit_packet_v2"
    parent_v1: CriterionFitPacketV1
    preference_fit_evidence_v2_sha256: str | None
    hedonic_state: str
    cluster_bootstrap_sha256: str | None
    heldout_validation_sha256: str | None
    transitivity_sha256: str | None
    next_pair_sha256: str | None
    evidence_delta_receipt: EvidenceDeltaReceiptV1
    test_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.parent_v1, CriterionFitPacketV1):
            raise TypeError("parent_v1 must be a CriterionFitPacketV1")
        for name in (
            "preference_fit_evidence_v2_sha256",
            "cluster_bootstrap_sha256",
            "heldout_validation_sha256",
            "transitivity_sha256",
            "next_pair_sha256",
        ):
            object.__setattr__(
                self, name, _sha(getattr(self, name), name, optional=True)
            )
        state = str(_text(self.hedonic_state, "hedonic_state")).upper()
        if state not in {
            "VALIDATED_EXACT_SCOPE",
            "DIAGNOSTIC",
            "WITHHELD",
            "FAILED_BASELINE",
            "NOT_TESTED",
            "INVALID",
        }:
            raise ValueError("hedonic_state is invalid")
        object.__setattr__(self, "hedonic_state", state)
        if not isinstance(self.evidence_delta_receipt, EvidenceDeltaReceiptV1):
            raise TypeError(
                "evidence_delta_receipt must be an EvidenceDeltaReceiptV1"
            )
        if not isinstance(self.test_only, bool):
            raise TypeError("test_only must be boolean")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "parent_v1": self.parent_v1.as_dict(),
                "preference_fit_evidence_v2_sha256": (
                    self.preference_fit_evidence_v2_sha256
                ),
                "hedonic_state": self.hedonic_state,
                "cluster_bootstrap_sha256": self.cluster_bootstrap_sha256,
                "heldout_validation_sha256": self.heldout_validation_sha256,
                "transitivity_sha256": self.transitivity_sha256,
                "next_pair_sha256": self.next_pair_sha256,
                "evidence_delta_receipt": self.evidence_delta_receipt.as_dict(),
                "test_only": self.test_only,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> CriterionFitPacketV2:
        fields = frozenset(
            {
                "parent_v1",
                "preference_fit_evidence_v2_sha256",
                "hedonic_state",
                "cluster_bootstrap_sha256",
                "heldout_validation_sha256",
                "transitivity_sha256",
                "next_pair_sha256",
                "evidence_delta_receipt",
                "test_only",
            }
        )
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["parent_v1"] = CriterionFitPacketV1.from_dict(values["parent_v1"])
        values["evidence_delta_receipt"] = EvidenceDeltaReceiptV1.from_dict(
            values["evidence_delta_receipt"]
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class CriterionFitPacketV3(_Record):
    """Item-, sample-, context-, order-, and adequacy-bound liking packet."""

    SCHEMA_VERSION: ClassVar[str] = "criterion_fit_packet_v3"
    parent_v2: CriterionFitPacketV2
    preference_fit_evidence_v3_sha256: str | None
    evaluation_context_sha256: str | None
    item_bindings_sha256: str | None
    order_carryover_sha256: str | None
    adequacy_contract_sha256: str | None
    hedonic_state: str
    evidence_delta_receipt: EvidenceDeltaReceiptV1
    test_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.parent_v2, CriterionFitPacketV2):
            raise TypeError("parent_v2 must be a CriterionFitPacketV2")
        for name in (
            "preference_fit_evidence_v3_sha256",
            "evaluation_context_sha256",
            "item_bindings_sha256",
            "order_carryover_sha256",
            "adequacy_contract_sha256",
        ):
            object.__setattr__(
                self, name, _sha(getattr(self, name), name, optional=True)
            )
        state = str(_text(self.hedonic_state, "hedonic_state")).upper()
        if state not in {
            "VALIDATED_EXACT_SCOPE",
            "DIAGNOSTIC",
            "WITHHELD",
            "FAILED_BASELINE",
            "NOT_TESTED",
            "INVALID",
        }:
            raise ValueError("hedonic_state is invalid")
        object.__setattr__(self, "hedonic_state", state)
        if not isinstance(self.evidence_delta_receipt, EvidenceDeltaReceiptV1):
            raise TypeError(
                "evidence_delta_receipt must be an EvidenceDeltaReceiptV1"
            )
        if not isinstance(self.test_only, bool):
            raise TypeError("test_only must be boolean")
        if self.test_only != self.parent_v2.test_only:
            raise ValueError("test_only must match parent_v2")

        receipt = self.evidence_delta_receipt
        if receipt.module_id != "hedonic_preference_v3":
            raise ValueError(
                "V3 evidence_delta_receipt module_id must be hedonic_preference_v3"
            )
        criterion = self.parent_v2.parent_v1.criterion
        if receipt.exact_scope.rsplit("/", 1)[-1] != criterion:
            raise ValueError(
                "V3 evidence_delta_receipt scope must end with the parent criterion"
            )

        binding_hashes = (
            self.preference_fit_evidence_v3_sha256,
            self.evaluation_context_sha256,
            self.item_bindings_sha256,
            self.order_carryover_sha256,
            self.adequacy_contract_sha256,
        )
        present = tuple(value is not None for value in binding_hashes)
        if any(present) and not all(present):
            raise ValueError("V3 binding hashes must be all present or all absent")
        fully_bound = all(present)

        if fully_bound:
            if receipt.evidence_sha256 != self.preference_fit_evidence_v3_sha256:
                raise ValueError(
                    "V3 evidence receipt must bind the V3 preference evidence hash"
                )
        else:
            valid_parent_evidence = {
                self.parent_v2.parent_v1.preference_result_sha256,
            }
            if self.parent_v2.preference_fit_evidence_v2_sha256 is not None:
                valid_parent_evidence.add(
                    self.parent_v2.preference_fit_evidence_v2_sha256
                )
            if receipt.evidence_sha256 not in valid_parent_evidence:
                raise ValueError(
                    "unbound V3 receipt must bind a declared parent evidence hash"
                )

        if state == "VALIDATED_EXACT_SCOPE":
            if not fully_bound:
                raise ValueError(
                    "VALIDATED_EXACT_SCOPE requires every V3 binding hash"
                )
            if receipt.state is not EvidenceAugmentationState.AUGMENT:
                raise ValueError(
                    "VALIDATED_EXACT_SCOPE requires an AUGMENT evidence receipt"
                )
            required_sources = {value for value in binding_hashes if value is not None}
            if not required_sources.issubset(receipt.source_binding_sha256):
                raise ValueError(
                    "validated V3 receipt must source-bind every V3 evidence hash"
                )
        elif receipt.state is EvidenceAugmentationState.AUGMENT:
            raise ValueError("only VALIDATED_EXACT_SCOPE may AUGMENT")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "parent_v2": self.parent_v2.as_dict(),
                "preference_fit_evidence_v3_sha256": (
                    self.preference_fit_evidence_v3_sha256
                ),
                "evaluation_context_sha256": self.evaluation_context_sha256,
                "item_bindings_sha256": self.item_bindings_sha256,
                "order_carryover_sha256": self.order_carryover_sha256,
                "adequacy_contract_sha256": self.adequacy_contract_sha256,
                "hedonic_state": self.hedonic_state,
                "evidence_delta_receipt": self.evidence_delta_receipt.as_dict(),
                "test_only": self.test_only,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> CriterionFitPacketV3:
        fields = frozenset(
            {
                "parent_v2",
                "preference_fit_evidence_v3_sha256",
                "evaluation_context_sha256",
                "item_bindings_sha256",
                "order_carryover_sha256",
                "adequacy_contract_sha256",
                "hedonic_state",
                "evidence_delta_receipt",
                "test_only",
            }
        )
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["parent_v2"] = CriterionFitPacketV2.from_dict(values["parent_v2"])
        values["evidence_delta_receipt"] = EvidenceDeltaReceiptV1.from_dict(
            values["evidence_delta_receipt"]
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class DecisionReceiptV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "decision_receipt_v1"
    case_sha256: str
    hypothesis_set_sha256: str
    compiled_experiment_sha256: str | None
    execution_receipt_sha256: str | None
    temporal_evidence_sha256: str | None
    criterion_fit_sha256: str | None
    decision: DecisionState
    evidence_limitations: tuple[str, ...]
    next_action: str | None

    def __post_init__(self) -> None:
        for name in ("case_sha256", "hypothesis_set_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        for name in ("compiled_experiment_sha256", "execution_receipt_sha256", "temporal_evidence_sha256", "criterion_fit_sha256"):
            object.__setattr__(self, name, _sha(getattr(self, name), name, optional=True))
        object.__setattr__(self, "decision", DecisionState(self.decision))
        object.__setattr__(self, "evidence_limitations", _texts(self.evidence_limitations, "evidence_limitations"))
        object.__setattr__(self, "next_action", _text(self.next_action, "next_action", optional=True))

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {"case_sha256": self.case_sha256, "hypothesis_set_sha256": self.hypothesis_set_sha256,
             "compiled_experiment_sha256": self.compiled_experiment_sha256,
             "execution_receipt_sha256": self.execution_receipt_sha256,
             "temporal_evidence_sha256": self.temporal_evidence_sha256,
             "criterion_fit_sha256": self.criterion_fit_sha256,
             "decision": self.decision.value,
             "evidence_limitations": list(self.evidence_limitations), "next_action": self.next_action}
        )

    @classmethod
    def from_dict(cls, payload: object) -> DecisionReceiptV1:
        fields = frozenset({"case_sha256", "hypothesis_set_sha256", "compiled_experiment_sha256", "execution_receipt_sha256", "temporal_evidence_sha256", "criterion_fit_sha256", "decision", "evidence_limitations", "next_action"})
        return cls(**_load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields))


@dataclass(frozen=True, slots=True)
class EvidenceDeltaPacketV2(_Record):
    """Versioned transport that leaves every closed V1 packet unchanged."""

    SCHEMA_VERSION: ClassVar[str] = "evidence_delta_packet_v2"
    parent_decision: DecisionReceiptV1
    evidence_delta_receipt: EvidenceDeltaReceiptV1 | None

    def __post_init__(self) -> None:
        if not isinstance(self.parent_decision, DecisionReceiptV1):
            raise TypeError("parent_decision must be a DecisionReceiptV1")
        if self.evidence_delta_receipt is not None and not isinstance(
            self.evidence_delta_receipt, EvidenceDeltaReceiptV1
        ):
            raise TypeError(
                "evidence_delta_receipt must be an EvidenceDeltaReceiptV1 or None"
            )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "parent_decision": self.parent_decision.as_dict(),
                "evidence_delta_receipt": (
                    None
                    if self.evidence_delta_receipt is None
                    else self.evidence_delta_receipt.as_dict()
                ),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceDeltaPacketV2:
        fields = frozenset({"parent_decision", "evidence_delta_receipt"})
        values = _load(payload, schema_version=cls.SCHEMA_VERSION, fields=fields)
        values["parent_decision"] = DecisionReceiptV1.from_dict(
            values["parent_decision"]
        )
        if values["evidence_delta_receipt"] is not None:
            values["evidence_delta_receipt"] = EvidenceDeltaReceiptV1.from_dict(
                values["evidence_delta_receipt"]
            )
        return cls(**values)


__all__ = [
    "AUTHORITY_FLAGS_FALSE", "CompilationState", "CompiledArmV1",
    "CompiledExperimentV1", "CriterionFitPacketV1", "CriterionFitPacketV2", "CriterionFitPacketV3", "DecisionReceiptV1",
    "DecisionState", "EvidenceDeltaPacketV2", "ExecutionReceiptV1", "SolForgeCaseState", "SolForgeCaseV1",
    "SolHypothesisSetV1", "SolHypothesisV1", "TemporalEvidencePacketV1",
]
