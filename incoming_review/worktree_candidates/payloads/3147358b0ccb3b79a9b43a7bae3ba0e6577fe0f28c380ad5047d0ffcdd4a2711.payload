"""Evidence-gated routing among deterministic code and Sol reasoning tiers.

The router makes model retirement a falsifiable governance decision.  Cost or
speed never lowers the tier for architecture, hedonic interpretation,
scientific transfer, source conflict, gate mutation, or module admission.
Frozen bounded work can move from Ultra to xhigh only after exact-scope
noninferiority evidence, and from xhigh to normal/Fast only after exact
agreement on a larger machine-checkable corpus.

No model tier can grant safety or release authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import ClassVar, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "solforge"
    / "model_tier_policy_v1.json"
)

MODEL_TIER_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class ModelTier(str, Enum):
    """Execution tiers ordered from deterministic code to open judgment."""

    NO_MODEL_DETERMINISTIC = "NO_MODEL_DETERMINISTIC"
    SOL_NORMAL_FAST = "SOL_NORMAL_FAST"
    SOL_XHIGH = "SOL_XHIGH"
    SOL_ULTRA = "SOL_ULTRA"


class ModelTaskClass(str, Enum):
    """Exhaustive task classes admitted by the version-one router."""

    DETERMINISTIC_PARSE = "DETERMINISTIC_PARSE"
    DETERMINISTIC_HASH = "DETERMINISTIC_HASH"
    DETERMINISTIC_SCHEMA_VALIDATION = "DETERMINISTIC_SCHEMA_VALIDATION"
    DETERMINISTIC_TEST_EXECUTION = "DETERMINISTIC_TEST_EXECUTION"
    DETERMINISTIC_INVENTORY_JOIN = "DETERMINISTIC_INVENTORY_JOIN"
    FROZEN_RENDERING = "FROZEN_RENDERING"
    FROZEN_RULE_APPLICATION = "FROZEN_RULE_APPLICATION"
    ARCHITECTURE_DESIGN = "ARCHITECTURE_DESIGN"
    HEDONIC_INTERPRETATION = "HEDONIC_INTERPRETATION"
    SCIENTIFIC_TRANSFER = "SCIENTIFIC_TRANSFER"
    SOURCE_CONFLICT_RESOLUTION = "SOURCE_CONFLICT_RESOLUTION"
    CROSS_MODULE_SYNTHESIS = "CROSS_MODULE_SYNTHESIS"
    GATE_CHANGE = "GATE_CHANGE"
    MODULE_ADMISSION_RETIREMENT = "MODULE_ADMISSION_RETIREMENT"
    SAFETY_RELEASE_AUTHORITY = "SAFETY_RELEASE_AUTHORITY"


class ModelTierRouteState(str, Enum):
    """Governance disposition of one routing request."""

    APPROVED = "APPROVED"
    ESCALATE = "ESCALATE"
    HOLD_HUMAN_AUTHORITY = "HOLD_HUMAN_AUTHORITY"


class _RouteMode(str, Enum):
    DETERMINISTIC = "DETERMINISTIC_IF_FROZEN_AND_MACHINE_CHECKABLE"
    BENCHMARK_GATED = "BENCHMARK_GATED"
    ULTRA_ONLY = "ULTRA_ONLY"
    HUMAN_AUTHORITY_HOLD = "HUMAN_AUTHORITY_HOLD"


_EXPECTED_ROUTE_MODES = {
    ModelTaskClass.DETERMINISTIC_PARSE: _RouteMode.DETERMINISTIC,
    ModelTaskClass.DETERMINISTIC_HASH: _RouteMode.DETERMINISTIC,
    ModelTaskClass.DETERMINISTIC_SCHEMA_VALIDATION: _RouteMode.DETERMINISTIC,
    ModelTaskClass.DETERMINISTIC_TEST_EXECUTION: _RouteMode.DETERMINISTIC,
    ModelTaskClass.DETERMINISTIC_INVENTORY_JOIN: _RouteMode.DETERMINISTIC,
    ModelTaskClass.FROZEN_RENDERING: _RouteMode.BENCHMARK_GATED,
    ModelTaskClass.FROZEN_RULE_APPLICATION: _RouteMode.BENCHMARK_GATED,
    ModelTaskClass.ARCHITECTURE_DESIGN: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.HEDONIC_INTERPRETATION: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.SCIENTIFIC_TRANSFER: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.SOURCE_CONFLICT_RESOLUTION: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.CROSS_MODULE_SYNTHESIS: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.GATE_CHANGE: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.MODULE_ADMISSION_RETIREMENT: _RouteMode.ULTRA_ONLY,
    ModelTaskClass.SAFETY_RELEASE_AUTHORITY: _RouteMode.HUMAN_AUTHORITY_HOLD,
}


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lower-case SHA-256 digest")
    return value


def _bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be boolean")
    return value


def _nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _exact_fields(
    payload: object,
    expected: frozenset[str],
    label: str,
) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{label} must be an object")
    unknown = set(payload).difference(expected)
    missing = expected.difference(payload)
    if unknown:
        raise ValueError(f"unknown {label} fields: " + ", ".join(sorted(unknown)))
    if missing:
        raise ValueError(f"missing {label} fields: " + ", ".join(sorted(missing)))
    return payload


@dataclass(frozen=True, slots=True)
class XhighNoninferiorityPolicy:
    min_screen_cases: int
    min_screen_wins: int
    min_confirmation_cases: int
    min_confirmation_wins: int
    min_confirmation_nonlosses: int
    min_median_paired_delta: float
    require_unseen_variants: bool
    require_mutation_cases: bool
    require_adversarial_cases: bool
    require_deterministic_replay: bool
    max_critical_errors: int
    max_hold_regressions: int
    max_authority_regressions: int

    FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "min_screen_cases",
            "min_screen_wins",
            "min_confirmation_cases",
            "min_confirmation_wins",
            "min_confirmation_nonlosses",
            "min_median_paired_delta",
            "require_unseen_variants",
            "require_mutation_cases",
            "require_adversarial_cases",
            "require_deterministic_replay",
            "max_critical_errors",
            "max_hold_regressions",
            "max_authority_regressions",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "min_screen_cases",
            "min_screen_wins",
            "min_confirmation_cases",
            "min_confirmation_wins",
            "min_confirmation_nonlosses",
            "max_critical_errors",
            "max_hold_regressions",
            "max_authority_regressions",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        object.__setattr__(
            self,
            "min_median_paired_delta",
            _finite_number(self.min_median_paired_delta, "min_median_paired_delta"),
        )
        for name in (
            "require_unseen_variants",
            "require_mutation_cases",
            "require_adversarial_cases",
            "require_deterministic_replay",
        ):
            object.__setattr__(self, name, _bool(getattr(self, name), name))
        if self.min_screen_wins > self.min_screen_cases:
            raise ValueError("min_screen_wins cannot exceed min_screen_cases")
        if self.min_confirmation_wins > self.min_confirmation_cases:
            raise ValueError("min_confirmation_wins cannot exceed min_confirmation_cases")
        if self.min_confirmation_nonlosses > self.min_confirmation_cases:
            raise ValueError(
                "min_confirmation_nonlosses cannot exceed min_confirmation_cases"
            )
        if (
            self.min_screen_cases < 3
            or self.min_screen_wins * 3 < self.min_screen_cases * 2
            or self.min_confirmation_cases < 6
            or self.min_confirmation_wins * 3 < self.min_confirmation_cases * 2
            or self.min_confirmation_nonlosses * 6
            < self.min_confirmation_cases * 5
            or self.min_median_paired_delta < 0
            or not self.require_unseen_variants
            or not self.require_mutation_cases
            or not self.require_adversarial_cases
            or not self.require_deterministic_replay
            or self.max_critical_errors != 0
            or self.max_hold_regressions != 0
            or self.max_authority_regressions != 0
        ):
            raise ValueError("xhigh_noninferiority policy cannot weaken the V1 floor")

    @classmethod
    def from_dict(cls, payload: object) -> XhighNoninferiorityPolicy:
        values = _exact_fields(payload, cls.FIELDS, "xhigh_noninferiority")
        return cls(**values)

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in sorted(self.FIELDS)}


@dataclass(frozen=True, slots=True)
class NormalExactAgreementPolicy:
    min_screen_cases: int
    require_all_screen_wins: bool
    min_confirmation_cases: int
    require_all_confirmation_wins: bool
    require_all_confirmation_nonlosses: bool
    require_exact_confirmation_agreement: bool
    require_unseen_variants: bool
    require_mutation_cases: bool
    require_adversarial_cases: bool
    require_deterministic_replay: bool
    max_critical_errors: int
    max_hold_regressions: int
    max_authority_regressions: int

    FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "min_screen_cases",
            "require_all_screen_wins",
            "min_confirmation_cases",
            "require_all_confirmation_wins",
            "require_all_confirmation_nonlosses",
            "require_exact_confirmation_agreement",
            "require_unseen_variants",
            "require_mutation_cases",
            "require_adversarial_cases",
            "require_deterministic_replay",
            "max_critical_errors",
            "max_hold_regressions",
            "max_authority_regressions",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "min_screen_cases",
            "min_confirmation_cases",
            "max_critical_errors",
            "max_hold_regressions",
            "max_authority_regressions",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        for name in self.FIELDS.difference(
            {
                "min_screen_cases",
                "min_confirmation_cases",
                "max_critical_errors",
                "max_hold_regressions",
                "max_authority_regressions",
            }
        ):
            object.__setattr__(self, name, _bool(getattr(self, name), name))
        if (
            self.min_screen_cases < 6
            or self.min_confirmation_cases < 12
            or not self.require_all_screen_wins
            or not self.require_all_confirmation_wins
            or not self.require_all_confirmation_nonlosses
            or not self.require_exact_confirmation_agreement
            or not self.require_unseen_variants
            or not self.require_mutation_cases
            or not self.require_adversarial_cases
            or not self.require_deterministic_replay
            or self.max_critical_errors != 0
            or self.max_hold_regressions != 0
            or self.max_authority_regressions != 0
        ):
            raise ValueError("normal_exact_agreement policy cannot weaken the V1 floor")

    @classmethod
    def from_dict(cls, payload: object) -> NormalExactAgreementPolicy:
        values = _exact_fields(payload, cls.FIELDS, "normal_exact_agreement")
        return cls(**values)

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in sorted(self.FIELDS)}


@dataclass(frozen=True, slots=True)
class ModelTierPolicy:
    """Strict parsed view of the repository-owned routing policy."""

    schema_version: str
    tier_order: tuple[ModelTier, ...]
    task_routes: tuple[tuple[ModelTaskClass, _RouteMode], ...]
    xhigh_noninferiority: XhighNoninferiorityPolicy
    normal_exact_agreement: NormalExactAgreementPolicy
    source_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "model_tier_policy_v1":
            raise ValueError("schema_version must be model_tier_policy_v1")
        tiers = tuple(ModelTier(item) for item in self.tier_order)
        expected_tiers = tuple(ModelTier)
        if tiers != expected_tiers:
            raise ValueError("tier_order must contain the exact governed order")
        object.__setattr__(self, "tier_order", tiers)
        routes = tuple(
            sorted(
                (
                    (ModelTaskClass(task_class), _RouteMode(route_mode))
                    for task_class, route_mode in self.task_routes
                ),
                key=lambda item: item[0].value,
            )
        )
        if {item[0] for item in routes} != set(ModelTaskClass):
            raise ValueError("task_routes must contain every task class exactly once")
        if len(routes) != len(ModelTaskClass):
            raise ValueError("task_routes contains duplicate task classes")
        if dict(routes) != _EXPECTED_ROUTE_MODES:
            raise ValueError("a V1 task route cannot be reassigned")
        object.__setattr__(self, "task_routes", routes)
        if not isinstance(self.xhigh_noninferiority, XhighNoninferiorityPolicy):
            raise TypeError("xhigh_noninferiority has the wrong type")
        if not isinstance(self.normal_exact_agreement, NormalExactAgreementPolicy):
            raise TypeError("normal_exact_agreement has the wrong type")
        object.__setattr__(
            self,
            "source_sha256",
            _sha256(self.source_sha256, "source_sha256"),
        )

    @property
    def route_map(self) -> dict[ModelTaskClass, _RouteMode]:
        return dict(self.task_routes)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "tier_order": [item.value for item in self.tier_order],
            "task_routes": {
                task_class.value: route.value
                for task_class, route in self.task_routes
            },
            "xhigh_noninferiority": self.xhigh_noninferiority.as_dict(),
            "normal_exact_agreement": self.normal_exact_agreement.as_dict(),
            "authority_flags": dict(MODEL_TIER_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


_POLICY_FIELDS = frozenset(
    {
        "schema_version",
        "tier_order",
        "task_routes",
        "xhigh_noninferiority",
        "normal_exact_agreement",
        "authority_flags",
    }
)


def load_model_tier_policy(path: str | Path | None = None) -> ModelTierPolicy:
    """Load the exact repository policy with duplicate and unknown fields rejected."""

    policy_path = _DEFAULT_POLICY_PATH if path is None else Path(path)
    raw = policy_path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("model tier policy must be valid UTF-8 JSON") from exc
    values = _exact_fields(payload, _POLICY_FIELDS, "policy")
    if values["authority_flags"] != MODEL_TIER_AUTHORITY_FLAGS:
        raise ValueError("policy authority_flags must be the exact all-false mapping")
    tier_order = values["tier_order"]
    if not isinstance(tier_order, list):
        raise TypeError("tier_order must be an array")
    route_payload = values["task_routes"]
    if not isinstance(route_payload, Mapping):
        raise TypeError("task_routes must be an object")
    unknown_routes = set(route_payload).difference(item.value for item in ModelTaskClass)
    missing_routes = {item.value for item in ModelTaskClass}.difference(route_payload)
    if unknown_routes:
        raise ValueError("unknown task_routes fields: " + ", ".join(sorted(unknown_routes)))
    if missing_routes:
        raise ValueError("missing task_routes fields: " + ", ".join(sorted(missing_routes)))
    return ModelTierPolicy(
        schema_version=str(values["schema_version"]),
        tier_order=tuple(ModelTier(item) for item in tier_order),
        task_routes=tuple(
            (ModelTaskClass(key), _RouteMode(value))
            for key, value in route_payload.items()
        ),
        xhigh_noninferiority=XhighNoninferiorityPolicy.from_dict(
            values["xhigh_noninferiority"]
        ),
        normal_exact_agreement=NormalExactAgreementPolicy.from_dict(
            values["normal_exact_agreement"]
        ),
        source_sha256=sha256_hex(raw),
    )


@dataclass(frozen=True, slots=True)
class TierBenchmarkReceipt:
    """Frozen comparison between one candidate tier and its immediate reference."""

    SCHEMA_VERSION: ClassVar[str] = "tier_benchmark_receipt_v1"

    receipt_id: str
    task_class: ModelTaskClass
    candidate_tier: ModelTier
    reference_tier: ModelTier
    frozen_contract_sha256: str
    benchmark_corpus_sha256: str
    prompt_bundle_sha256: str
    input_bundle_sha256: str
    candidate_model_identity: str
    reference_model_identity: str
    screen_case_count: int
    screen_win_count: int
    confirmation_case_count: int
    confirmation_win_count: int
    confirmation_nonloss_count: int
    exact_confirmation_agreement_count: int
    median_paired_delta: float
    unseen_variants_present: bool
    mutation_cases_present: bool
    adversarial_cases_present: bool
    deterministic_replay: bool
    critical_error_count: int
    hold_regression_count: int
    authority_regression_count: int
    candidate_output_bundle_sha256: str
    reference_output_bundle_sha256: str
    score_bundle_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _text(self.receipt_id, "receipt_id"))
        object.__setattr__(self, "task_class", ModelTaskClass(self.task_class))
        object.__setattr__(self, "candidate_tier", ModelTier(self.candidate_tier))
        object.__setattr__(self, "reference_tier", ModelTier(self.reference_tier))
        if self.candidate_tier is self.reference_tier:
            raise ValueError("candidate_tier and reference_tier must differ")
        for name in (
            "frozen_contract_sha256",
            "benchmark_corpus_sha256",
            "prompt_bundle_sha256",
            "input_bundle_sha256",
            "candidate_output_bundle_sha256",
            "reference_output_bundle_sha256",
            "score_bundle_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in ("candidate_model_identity", "reference_model_identity"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "screen_case_count",
            "screen_win_count",
            "confirmation_case_count",
            "confirmation_win_count",
            "confirmation_nonloss_count",
            "exact_confirmation_agreement_count",
            "critical_error_count",
            "hold_regression_count",
            "authority_regression_count",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        if self.screen_win_count > self.screen_case_count:
            raise ValueError("screen_win_count cannot exceed screen_case_count")
        for name in (
            "confirmation_win_count",
            "confirmation_nonloss_count",
            "exact_confirmation_agreement_count",
        ):
            if getattr(self, name) > self.confirmation_case_count:
                raise ValueError(f"{name} cannot exceed confirmation_case_count")
        object.__setattr__(
            self,
            "median_paired_delta",
            _finite_number(self.median_paired_delta, "median_paired_delta"),
        )
        for name in (
            "unseen_variants_present",
            "mutation_cases_present",
            "adversarial_cases_present",
            "deterministic_replay",
        ):
            object.__setattr__(self, name, _bool(getattr(self, name), name))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "task_class": self.task_class.value,
            "candidate_tier": self.candidate_tier.value,
            "reference_tier": self.reference_tier.value,
            "frozen_contract_sha256": self.frozen_contract_sha256,
            "benchmark_corpus_sha256": self.benchmark_corpus_sha256,
            "prompt_bundle_sha256": self.prompt_bundle_sha256,
            "input_bundle_sha256": self.input_bundle_sha256,
            "candidate_model_identity": self.candidate_model_identity,
            "reference_model_identity": self.reference_model_identity,
            "screen_case_count": self.screen_case_count,
            "screen_win_count": self.screen_win_count,
            "confirmation_case_count": self.confirmation_case_count,
            "confirmation_win_count": self.confirmation_win_count,
            "confirmation_nonloss_count": self.confirmation_nonloss_count,
            "exact_confirmation_agreement_count": (
                self.exact_confirmation_agreement_count
            ),
            "median_paired_delta": self.median_paired_delta,
            "unseen_variants_present": self.unseen_variants_present,
            "mutation_cases_present": self.mutation_cases_present,
            "adversarial_cases_present": self.adversarial_cases_present,
            "deterministic_replay": self.deterministic_replay,
            "critical_error_count": self.critical_error_count,
            "hold_regression_count": self.hold_regression_count,
            "authority_regression_count": self.authority_regression_count,
            "candidate_output_bundle_sha256": self.candidate_output_bundle_sha256,
            "reference_output_bundle_sha256": self.reference_output_bundle_sha256,
            "score_bundle_sha256": self.score_bundle_sha256,
            "authority_flags": dict(MODEL_TIER_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> TierBenchmarkReceipt:
        fields = frozenset(
            {
                "schema_version",
                "receipt_id",
                "task_class",
                "candidate_tier",
                "reference_tier",
                "frozen_contract_sha256",
                "benchmark_corpus_sha256",
                "prompt_bundle_sha256",
                "input_bundle_sha256",
                "candidate_model_identity",
                "reference_model_identity",
                "screen_case_count",
                "screen_win_count",
                "confirmation_case_count",
                "confirmation_win_count",
                "confirmation_nonloss_count",
                "exact_confirmation_agreement_count",
                "median_paired_delta",
                "unseen_variants_present",
                "mutation_cases_present",
                "adversarial_cases_present",
                "deterministic_replay",
                "critical_error_count",
                "hold_regression_count",
                "authority_regression_count",
                "candidate_output_bundle_sha256",
                "reference_output_bundle_sha256",
                "score_bundle_sha256",
                "authority_flags",
            }
        )
        values = _exact_fields(payload, fields, "receipt")
        if values["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        if values["authority_flags"] != MODEL_TIER_AUTHORITY_FLAGS:
            raise ValueError("receipt authority_flags must be the exact all-false mapping")
        constructor_values = {
            key: value
            for key, value in values.items()
            if key not in {"schema_version", "authority_flags"}
        }
        return cls(**constructor_values)


@dataclass(frozen=True, slots=True)
class ModelTierRequest:
    """One task classification and its exact frozen inputs."""

    request_id: str
    task_class: ModelTaskClass
    frozen_contract_sha256: str
    input_sha256: str
    requested_tier: ModelTier | None
    contract_frozen: bool
    machine_checkable: bool
    open_source_conflict: bool
    open_critical_regression: bool
    changes_authority: bool
    benchmark_receipts: tuple[TierBenchmarkReceipt, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _text(self.request_id, "request_id"))
        object.__setattr__(self, "task_class", ModelTaskClass(self.task_class))
        for name in ("frozen_contract_sha256", "input_sha256"):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        if self.requested_tier is not None:
            object.__setattr__(self, "requested_tier", ModelTier(self.requested_tier))
        for name in (
            "contract_frozen",
            "machine_checkable",
            "open_source_conflict",
            "open_critical_regression",
            "changes_authority",
        ):
            object.__setattr__(self, name, _bool(getattr(self, name), name))
        receipts = tuple(self.benchmark_receipts)
        if any(not isinstance(item, TierBenchmarkReceipt) for item in receipts):
            raise TypeError("benchmark_receipts must contain TierBenchmarkReceipt records")
        receipt_ids = tuple(item.receipt_id for item in receipts)
        if len(receipt_ids) != len(set(receipt_ids)):
            raise ValueError("benchmark receipt_id values must be unique")
        object.__setattr__(self, "benchmark_receipts", receipts)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "model_tier_request_v1",
            "request_id": self.request_id,
            "task_class": self.task_class.value,
            "frozen_contract_sha256": self.frozen_contract_sha256,
            "input_sha256": self.input_sha256,
            "requested_tier": (
                None if self.requested_tier is None else self.requested_tier.value
            ),
            "contract_frozen": self.contract_frozen,
            "machine_checkable": self.machine_checkable,
            "open_source_conflict": self.open_source_conflict,
            "open_critical_regression": self.open_critical_regression,
            "changes_authority": self.changes_authority,
            "benchmark_receipts": [
                item.as_dict()
                for item in sorted(
                    self.benchmark_receipts,
                    key=lambda receipt: (receipt.receipt_id, receipt.record_sha256),
                )
            ],
            "authority_flags": dict(MODEL_TIER_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


@dataclass(frozen=True, slots=True)
class ModelTierRouteResult:
    """Deterministic routing receipt; never scientific or release authority."""

    SCHEMA_VERSION: ClassVar[str] = "model_tier_route_result_v1"

    state: ModelTierRouteState
    request_sha256: str
    request_id: str
    task_class: ModelTaskClass
    requested_tier: ModelTier | None
    selected_tier: ModelTier | None
    reasons: tuple[str, ...]
    policy_source_sha256: str
    xhigh_benchmark_receipt_sha256: str | None
    normal_benchmark_receipt_sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", ModelTierRouteState(self.state))
        object.__setattr__(
            self,
            "request_sha256",
            _sha256(self.request_sha256, "request_sha256"),
        )
        object.__setattr__(self, "request_id", _text(self.request_id, "request_id"))
        object.__setattr__(self, "task_class", ModelTaskClass(self.task_class))
        if self.requested_tier is not None:
            object.__setattr__(self, "requested_tier", ModelTier(self.requested_tier))
        if self.selected_tier is not None:
            object.__setattr__(self, "selected_tier", ModelTier(self.selected_tier))
        normalized_reasons = tuple(_text(item, "reasons") for item in self.reasons)
        if not normalized_reasons:
            raise ValueError("reasons must be nonempty")
        if len(normalized_reasons) != len(set(normalized_reasons)):
            raise ValueError("reasons must not contain duplicates")
        object.__setattr__(self, "reasons", normalized_reasons)
        object.__setattr__(
            self,
            "policy_source_sha256",
            _sha256(self.policy_source_sha256, "policy_source_sha256"),
        )
        for name in (
            "xhigh_benchmark_receipt_sha256",
            "normal_benchmark_receipt_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _sha256(value, name))
        if self.state is ModelTierRouteState.HOLD_HUMAN_AUTHORITY:
            if self.selected_tier is not None:
                raise ValueError("HOLD_HUMAN_AUTHORITY cannot select a model")
        elif self.selected_tier is None:
            raise ValueError("APPROVED and ESCALATE require selected_tier")

    @property
    def authority_flags(self) -> dict[str, bool]:
        return dict(MODEL_TIER_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
            "request_sha256": self.request_sha256,
            "request_id": self.request_id,
            "task_class": self.task_class.value,
            "requested_tier": (
                None if self.requested_tier is None else self.requested_tier.value
            ),
            "selected_tier": (
                None if self.selected_tier is None else self.selected_tier.value
            ),
            "reasons": list(self.reasons),
            "policy_source_sha256": self.policy_source_sha256,
            "xhigh_benchmark_receipt_sha256": (
                self.xhigh_benchmark_receipt_sha256
            ),
            "normal_benchmark_receipt_sha256": (
                self.normal_benchmark_receipt_sha256
            ),
            "authority_flags": self.authority_flags,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def _passes_common_receipt_checks(
    request: ModelTierRequest,
    receipt: TierBenchmarkReceipt,
) -> bool:
    return (
        receipt.task_class is request.task_class
        and receipt.frozen_contract_sha256 == request.frozen_contract_sha256
        and receipt.critical_error_count == 0
        and receipt.hold_regression_count == 0
        and receipt.authority_regression_count == 0
    )


def _passes_xhigh(
    request: ModelTierRequest,
    receipt: TierBenchmarkReceipt,
    policy: XhighNoninferiorityPolicy,
) -> bool:
    return (
        _passes_common_receipt_checks(request, receipt)
        and receipt.candidate_tier is ModelTier.SOL_XHIGH
        and receipt.reference_tier is ModelTier.SOL_ULTRA
        and receipt.screen_case_count >= policy.min_screen_cases
        and receipt.screen_win_count >= policy.min_screen_wins
        and receipt.screen_win_count * policy.min_screen_cases
        >= policy.min_screen_wins * receipt.screen_case_count
        and receipt.confirmation_case_count >= policy.min_confirmation_cases
        and receipt.confirmation_win_count >= policy.min_confirmation_wins
        and receipt.confirmation_win_count * policy.min_confirmation_cases
        >= policy.min_confirmation_wins * receipt.confirmation_case_count
        and receipt.confirmation_nonloss_count >= policy.min_confirmation_nonlosses
        and receipt.confirmation_nonloss_count * policy.min_confirmation_cases
        >= policy.min_confirmation_nonlosses * receipt.confirmation_case_count
        and receipt.median_paired_delta >= policy.min_median_paired_delta
        and (not policy.require_unseen_variants or receipt.unseen_variants_present)
        and (not policy.require_mutation_cases or receipt.mutation_cases_present)
        and (not policy.require_adversarial_cases or receipt.adversarial_cases_present)
        and (not policy.require_deterministic_replay or receipt.deterministic_replay)
        and receipt.critical_error_count <= policy.max_critical_errors
        and receipt.hold_regression_count <= policy.max_hold_regressions
        and receipt.authority_regression_count <= policy.max_authority_regressions
    )


def _passes_normal(
    request: ModelTierRequest,
    receipt: TierBenchmarkReceipt,
    policy: NormalExactAgreementPolicy,
) -> bool:
    return (
        _passes_common_receipt_checks(request, receipt)
        and receipt.candidate_tier is ModelTier.SOL_NORMAL_FAST
        and receipt.reference_tier is ModelTier.SOL_XHIGH
        and receipt.screen_case_count >= policy.min_screen_cases
        and (
            not policy.require_all_screen_wins
            or receipt.screen_win_count == receipt.screen_case_count
        )
        and receipt.confirmation_case_count >= policy.min_confirmation_cases
        and (
            not policy.require_all_confirmation_wins
            or receipt.confirmation_win_count == receipt.confirmation_case_count
        )
        and (
            not policy.require_all_confirmation_nonlosses
            or receipt.confirmation_nonloss_count == receipt.confirmation_case_count
        )
        and (
            not policy.require_exact_confirmation_agreement
            or receipt.exact_confirmation_agreement_count
            == receipt.confirmation_case_count
        )
        and (not policy.require_unseen_variants or receipt.unseen_variants_present)
        and (not policy.require_mutation_cases or receipt.mutation_cases_present)
        and (not policy.require_adversarial_cases or receipt.adversarial_cases_present)
        and (not policy.require_deterministic_replay or receipt.deterministic_replay)
        and receipt.critical_error_count <= policy.max_critical_errors
        and receipt.hold_regression_count <= policy.max_hold_regressions
        and receipt.authority_regression_count <= policy.max_authority_regressions
    )


_TIER_RANK = {tier: rank for rank, tier in enumerate(ModelTier)}


def route_model_tier(
    request: ModelTierRequest,
    *,
    policy: ModelTierPolicy | None = None,
) -> ModelTierRouteResult:
    """Choose the fastest tier whose exact-scope evidence satisfies policy."""

    if not isinstance(request, ModelTierRequest):
        raise TypeError("request must be a ModelTierRequest")
    resolved_policy = load_model_tier_policy() if policy is None else policy
    if not isinstance(resolved_policy, ModelTierPolicy):
        raise TypeError("policy must be a ModelTierPolicy")
    route_mode = resolved_policy.route_map[request.task_class]

    if route_mode is _RouteMode.HUMAN_AUTHORITY_HOLD:
        return ModelTierRouteResult(
            state=ModelTierRouteState.HOLD_HUMAN_AUTHORITY,
            request_sha256=request.record_sha256,
            request_id=request.request_id,
            task_class=request.task_class,
            requested_tier=request.requested_tier,
            selected_tier=None,
            reasons=("SAFETY_RELEASE_REQUIRES_HUMAN_AUTHORITY",),
            policy_source_sha256=resolved_policy.source_sha256,
            xhigh_benchmark_receipt_sha256=None,
            normal_benchmark_receipt_sha256=None,
        )

    reasons: list[str] = []
    selected_tier: ModelTier
    xhigh_receipt: TierBenchmarkReceipt | None = None
    normal_receipt: TierBenchmarkReceipt | None = None

    risk_reasons: list[str] = []
    if request.open_source_conflict:
        risk_reasons.append("OPEN_SOURCE_CONFLICT")
    if request.open_critical_regression:
        risk_reasons.append("OPEN_CRITICAL_REGRESSION")
    if request.changes_authority:
        risk_reasons.append("AUTHORITY_CHANGE_REQUIRES_ULTRA")

    if risk_reasons:
        selected_tier = ModelTier.SOL_ULTRA
        reasons.extend(risk_reasons)
    elif route_mode is _RouteMode.ULTRA_ONLY:
        selected_tier = ModelTier.SOL_ULTRA
        reasons.append("OPEN_JUDGMENT_REQUIRES_ULTRA")
    elif route_mode is _RouteMode.DETERMINISTIC:
        if request.contract_frozen and request.machine_checkable:
            selected_tier = ModelTier.NO_MODEL_DETERMINISTIC
            reasons.append("FROZEN_MACHINE_CHECKABLE_NO_MODEL")
        else:
            selected_tier = ModelTier.SOL_ULTRA
            reasons.append("DETERMINISTIC_PRECONDITIONS_NOT_MET")
    elif route_mode is _RouteMode.BENCHMARK_GATED:
        if not request.contract_frozen:
            selected_tier = ModelTier.SOL_ULTRA
            reasons.append("CONTRACT_NOT_FROZEN")
        else:
            sorted_receipts = sorted(
                request.benchmark_receipts,
                key=lambda item: (item.receipt_id, item.record_sha256),
            )
            xhigh_receipt = next(
                (
                    item
                    for item in sorted_receipts
                    if _passes_xhigh(
                        request,
                        item,
                        resolved_policy.xhigh_noninferiority,
                    )
                ),
                None,
            )
            if xhigh_receipt is None:
                selected_tier = ModelTier.SOL_ULTRA
                reasons.append("XHIGH_NONINFERIORITY_NOT_PROVEN")
            else:
                selected_tier = ModelTier.SOL_XHIGH
                reasons.append("XHIGH_NONINFERIORITY_PROVEN")
                if request.machine_checkable:
                    normal_receipt = next(
                        (
                            item
                            for item in sorted_receipts
                            if _passes_normal(
                                request,
                                item,
                                resolved_policy.normal_exact_agreement,
                            )
                        ),
                        None,
                    )
                    if normal_receipt is not None:
                        selected_tier = ModelTier.SOL_NORMAL_FAST
                        reasons.append("NORMAL_EXACT_AGREEMENT_PROVEN")
                    else:
                        reasons.append("NORMAL_EXACT_AGREEMENT_NOT_PROVEN")
                else:
                    reasons.append("NORMAL_REQUIRES_MACHINE_CHECKABLE_OUTPUT")
    else:  # pragma: no cover - exhaustive enum guard
        raise AssertionError(f"unhandled route mode: {route_mode}")

    state = ModelTierRouteState.APPROVED
    if (
        request.requested_tier is not None
        and _TIER_RANK[request.requested_tier] < _TIER_RANK[selected_tier]
    ):
        state = ModelTierRouteState.ESCALATE
        reasons.append("REQUESTED_TIER_BELOW_MINIMUM")

    return ModelTierRouteResult(
        state=state,
        request_sha256=request.record_sha256,
        request_id=request.request_id,
        task_class=request.task_class,
        requested_tier=request.requested_tier,
        selected_tier=selected_tier,
        reasons=tuple(reasons),
        policy_source_sha256=resolved_policy.source_sha256,
        xhigh_benchmark_receipt_sha256=(
            None if xhigh_receipt is None else xhigh_receipt.record_sha256
        ),
        normal_benchmark_receipt_sha256=(
            None if normal_receipt is None else normal_receipt.record_sha256
        ),
    )


__all__ = [
    "MODEL_TIER_AUTHORITY_FLAGS",
    "ModelTaskClass",
    "ModelTier",
    "ModelTierPolicy",
    "ModelTierRequest",
    "ModelTierRouteResult",
    "ModelTierRouteState",
    "NormalExactAgreementPolicy",
    "TierBenchmarkReceipt",
    "XhighNoninferiorityPolicy",
    "load_model_tier_policy",
    "route_model_tier",
]
