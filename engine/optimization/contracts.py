"""Immutable contracts for constrained perfume experiment selection."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from math import isfinite
from typing import Any

from engine.evidence.unsupported_science import BuildDValidationReceipt


class C10ContractError(ValueError):
    """Raised when a C10 boundary receives invalid or ambiguous input."""


class DesignStage(str, Enum):
    SCREENING = "SCREENING"
    LOCAL_RESPONSE = "LOCAL_RESPONSE"
    ACTIVE_LEARNING = "ACTIVE_LEARNING"


class CandidateRole(str, Enum):
    CONTROL = "CONTROL"
    REPLICATE = "REPLICATE"
    SCREENING = "SCREENING"
    OPTIMIZATION = "OPTIMIZATION"


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ObjectiveDirection(str, Enum):
    MAXIMIZE = "MAXIMIZE"
    MINIMIZE = "MINIMIZE"


class ObjectiveAuthority(str, Enum):
    MEASURED = "MEASURED"
    CALIBRATED_HELD_OUT = "CALIBRATED_HELD_OUT"
    COMPUTED_RESOURCE = "COMPUTED_RESOURCE"


class SelectionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    STOPPED = "STOPPED"
    BLOCKED = "BLOCKED"


class StopReason(str, Enum):
    NO_FEASIBLE_CANDIDATE = "NO_FEASIBLE_CANDIDATE"
    NO_FEASIBLE_IMPROVEMENT = "NO_FEASIBLE_IMPROVEMENT"
    INFORMATION_GAIN_BELOW_THRESHOLD = "INFORMATION_GAIN_BELOW_THRESHOLD"
    UNAVAILABLE_DATA_DOMINATES = "UNAVAILABLE_DATA_DOMINATES"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    PROTECTED_ATTRIBUTE_RISK = "PROTECTED_ATTRIBUTE_RISK"
    SENSORY_PLATEAU = "SENSORY_PLATEAU"
    OUTSIDE_VALIDATED_DOMAIN = "OUTSIDE_VALIDATED_DOMAIN"


def _text(value: object, field_name: str) -> str:
    result = str(value).strip()
    if not result:
        raise C10ContractError(f"{field_name} must not be empty")
    return result


def _finite(value: float | int, field_name: str) -> float:
    result = float(value)
    if not isfinite(result):
        raise C10ContractError(f"{field_name} must be finite")
    return result


def _nonnegative(value: float | int, field_name: str) -> float:
    result = _finite(value, field_name)
    if result < 0:
        raise C10ContractError(f"{field_name} must be nonnegative")
    return result


def _positive(value: float | int, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0:
        raise C10ContractError(f"{field_name} must be greater than zero")
    return result


def is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _sha256(value: object, field_name: str, *, allow_empty: bool = False) -> str:
    result = str(value).strip().casefold()
    if allow_empty and not result:
        return ""
    if not is_sha256(result):
        raise C10ContractError(f"{field_name} must be a lowercase SHA-256 digest")
    return result


def _unique_named(items: tuple[Any, ...], field_name: str, attribute: str) -> None:
    names = [getattr(item, attribute) for item in items]
    if len(names) != len(set(names)):
        raise C10ContractError(f"{field_name} must not contain duplicate {attribute} values")


def to_primitive(value: Any) -> Any:
    """Convert immutable C10 records into canonical JSON-compatible values."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {
            str(key): to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    content_hash = getattr(value, "content_sha256", None)
    if isinstance(content_hash, str):
        return {"content_sha256": content_hash}
    raise C10ContractError(f"value of type {type(value).__name__} is not serializable")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class NumericRange:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        minimum = _nonnegative(self.minimum, "minimum")
        maximum = _nonnegative(self.maximum, "maximum")
        if minimum > maximum:
            raise C10ContractError("minimum must not exceed maximum")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    def contains(self, value: float, *, tolerance: float = 1.0e-9) -> bool:
        return self.minimum - tolerance <= value <= self.maximum + tolerance


@dataclass(frozen=True, slots=True)
class StockDefinition:
    stock_id: str
    material_id: str
    family: str
    active_mass_fraction: float
    carrier_mass_fractions: tuple[tuple[str, float], ...]
    available_raw_mass_mg: float
    minimum_measurable_raw_mass_mg: float
    dispensing_increment_mg: float
    cost_per_raw_mass_mg: float

    def __post_init__(self) -> None:
        stock_id = _text(self.stock_id, "stock_id")
        material_id = _text(self.material_id, "material_id")
        family = _text(self.family, "family")
        active = _positive(self.active_mass_fraction, "active_mass_fraction")
        if active > 1:
            raise C10ContractError("active_mass_fraction must be at most one")
        carriers = tuple(
            sorted(
                (
                    _text(name, "carrier name"),
                    _positive(fraction, "carrier fraction"),
                )
                for name, fraction in self.carrier_mass_fractions
            )
        )
        if len({name for name, _ in carriers}) != len(carriers):
            raise C10ContractError("carrier names must be unique")
        if abs(active + sum(fraction for _, fraction in carriers) - 1.0) > 1.0e-9:
            raise C10ContractError("active and named carrier fractions must sum to one")
        available = _nonnegative(self.available_raw_mass_mg, "available_raw_mass_mg")
        minimum = _positive(
            self.minimum_measurable_raw_mass_mg,
            "minimum_measurable_raw_mass_mg",
        )
        increment = _positive(self.dispensing_increment_mg, "dispensing_increment_mg")
        cost = _nonnegative(self.cost_per_raw_mass_mg, "cost_per_raw_mass_mg")
        object.__setattr__(self, "stock_id", stock_id)
        object.__setattr__(self, "material_id", material_id)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "active_mass_fraction", active)
        object.__setattr__(self, "carrier_mass_fractions", carriers)
        object.__setattr__(self, "available_raw_mass_mg", available)
        object.__setattr__(self, "minimum_measurable_raw_mass_mg", minimum)
        object.__setattr__(self, "dispensing_increment_mg", increment)
        object.__setattr__(self, "cost_per_raw_mass_mg", cost)


@dataclass(frozen=True, slots=True)
class CandidateDose:
    stock_id: str
    raw_mass_mg: float
    module_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "stock_id", _text(self.stock_id, "stock_id"))
        object.__setattr__(
            self,
            "raw_mass_mg",
            _nonnegative(self.raw_mass_mg, "raw_mass_mg"),
        )
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))


@dataclass(frozen=True, slots=True)
class GateReceipt:
    gate_id: str
    status: GateStatus
    subject_sha256: str
    evidence_sha256: str
    authority: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "gate_id", _text(self.gate_id, "gate_id"))
        object.__setattr__(self, "status", GateStatus(self.status))
        object.__setattr__(self, "subject_sha256", _sha256(self.subject_sha256, "subject_sha256"))
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha256(self.evidence_sha256, "evidence_sha256"),
        )
        object.__setattr__(self, "authority", _text(self.authority, "authority"))


@dataclass(frozen=True, slots=True)
class MixtureCandidate:
    candidate_id: str
    stage: DesignStage
    role: CandidateRole
    doses: tuple[CandidateDose, ...]
    gate_receipts: tuple[GateReceipt, ...] = ()
    replicate_of: str | None = None

    def __post_init__(self) -> None:
        candidate_id = _text(self.candidate_id, "candidate_id")
        stage = DesignStage(self.stage)
        role = CandidateRole(self.role)
        doses = tuple(
            sorted(
                (item for item in self.doses if item.raw_mass_mg > 1.0e-12),
                key=lambda item: (item.stock_id, item.module_id),
            )
        )
        if not doses:
            raise C10ContractError("candidate doses must not be empty")
        if any(not isinstance(item, CandidateDose) for item in doses):
            raise C10ContractError("candidate doses must contain CandidateDose values")
        receipts = tuple(sorted(self.gate_receipts, key=lambda item: item.gate_id))
        if any(not isinstance(item, GateReceipt) for item in receipts):
            raise C10ContractError("gate receipts must contain GateReceipt values")
        _unique_named(receipts, "gate_receipts", "gate_id")
        replicate_of = (
            None if self.replicate_of is None else _text(self.replicate_of, "replicate_of")
        )
        if role is CandidateRole.REPLICATE and replicate_of is None:
            raise C10ContractError("replicate candidates require replicate_of")
        if role is not CandidateRole.REPLICATE and replicate_of is not None:
            raise C10ContractError("only replicate candidates may declare replicate_of")
        if replicate_of == candidate_id:
            raise C10ContractError("candidate cannot replicate itself")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "doses", doses)
        object.__setattr__(self, "gate_receipts", receipts)
        object.__setattr__(self, "replicate_of", replicate_of)


@dataclass(frozen=True, slots=True)
class ModuleActiveRange:
    module_id: str
    minimum_active_mass_mg: float
    maximum_active_mass_mg: float

    def __post_init__(self) -> None:
        bounds = NumericRange(self.minimum_active_mass_mg, self.maximum_active_mass_mg)
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))
        object.__setattr__(self, "minimum_active_mass_mg", bounds.minimum)
        object.__setattr__(self, "maximum_active_mass_mg", bounds.maximum)


@dataclass(frozen=True, slots=True)
class RecognizerFloor:
    material_id: str
    minimum_active_mass_mg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", _text(self.material_id, "material_id"))
        object.__setattr__(
            self,
            "minimum_active_mass_mg",
            _nonnegative(self.minimum_active_mass_mg, "minimum_active_mass_mg"),
        )


@dataclass(frozen=True, slots=True)
class FamilyFractionRange:
    family: str
    minimum_fraction: float
    maximum_fraction: float

    def __post_init__(self) -> None:
        bounds = NumericRange(self.minimum_fraction, self.maximum_fraction)
        if bounds.maximum > 1:
            raise C10ContractError("family fractions must be at most one")
        object.__setattr__(self, "family", _text(self.family, "family"))
        object.__setattr__(self, "minimum_fraction", bounds.minimum)
        object.__setattr__(self, "maximum_fraction", bounds.maximum)


@dataclass(frozen=True, slots=True)
class NegativeSpaceCap:
    material_id: str
    maximum_active_mass_mg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", _text(self.material_id, "material_id"))
        object.__setattr__(
            self,
            "maximum_active_mass_mg",
            _nonnegative(self.maximum_active_mass_mg, "maximum_active_mass_mg"),
        )


@dataclass(frozen=True, slots=True)
class MixtureDomain:
    domain_id: str
    total_active_mass_mg: NumericRange
    stocks: tuple[StockDefinition, ...]
    module_active_mass_ranges: tuple[ModuleActiveRange, ...] = ()
    recognizer_floors: tuple[RecognizerFloor, ...] = ()
    family_fraction_ranges: tuple[FamilyFractionRange, ...] = ()
    negative_space_caps: tuple[NegativeSpaceCap, ...] = ()
    required_gate_ids: tuple[str, ...] = ()
    maximum_candidates: int = 10_000

    def __post_init__(self) -> None:
        domain_id = _text(self.domain_id, "domain_id")
        if not isinstance(self.total_active_mass_mg, NumericRange):
            raise C10ContractError("total_active_mass_mg must be NumericRange")
        stocks = tuple(sorted(self.stocks, key=lambda item: item.stock_id))
        if not stocks:
            raise C10ContractError("mixture domain requires at least one stock")
        _unique_named(stocks, "stocks", "stock_id")
        modules = tuple(sorted(self.module_active_mass_ranges, key=lambda item: item.module_id))
        recognizers = tuple(sorted(self.recognizer_floors, key=lambda item: item.material_id))
        families = tuple(sorted(self.family_fraction_ranges, key=lambda item: item.family))
        caps = tuple(sorted(self.negative_space_caps, key=lambda item: item.material_id))
        _unique_named(modules, "module_active_mass_ranges", "module_id")
        _unique_named(recognizers, "recognizer_floors", "material_id")
        _unique_named(families, "family_fraction_ranges", "family")
        _unique_named(caps, "negative_space_caps", "material_id")
        required_gates = tuple(
            sorted(_text(item, "required_gate_id") for item in self.required_gate_ids)
        )
        if len(required_gates) != len(set(required_gates)):
            raise C10ContractError("required_gate_ids must be unique")
        maximum = int(self.maximum_candidates)
        if maximum <= 0:
            raise C10ContractError("maximum_candidates must be greater than zero")
        object.__setattr__(self, "domain_id", domain_id)
        object.__setattr__(self, "stocks", stocks)
        object.__setattr__(self, "module_active_mass_ranges", modules)
        object.__setattr__(self, "recognizer_floors", recognizers)
        object.__setattr__(self, "family_fraction_ranges", families)
        object.__setattr__(self, "negative_space_caps", caps)
        object.__setattr__(self, "required_gate_ids", required_gates)
        object.__setattr__(self, "maximum_candidates", maximum)

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class MixtureDesignAxis:
    stock_id: str
    module_id: str
    minimum_raw_mass_mg: float
    maximum_raw_mass_mg: float

    def __post_init__(self) -> None:
        bounds = NumericRange(self.minimum_raw_mass_mg, self.maximum_raw_mass_mg)
        object.__setattr__(self, "stock_id", _text(self.stock_id, "stock_id"))
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))
        object.__setattr__(self, "minimum_raw_mass_mg", bounds.minimum)
        object.__setattr__(self, "maximum_raw_mass_mg", bounds.maximum)


@dataclass(frozen=True, slots=True)
class ObjectiveEstimate:
    name: str
    value: float
    standard_uncertainty: float
    unit: str
    direction: ObjectiveDirection
    authority: ObjectiveAuthority
    applicability_scope: str
    source_ids: tuple[str, ...]
    model_release_id: str = ""
    held_out_receipt_sha256: str = ""
    build_d_receipt: BuildDValidationReceipt | None = None

    def __post_init__(self) -> None:
        name = _text(self.name, "objective name")
        value = _finite(self.value, "objective value")
        uncertainty = _nonnegative(self.standard_uncertainty, "standard_uncertainty")
        unit = _text(self.unit, "objective unit")
        scope = _text(self.applicability_scope, "applicability_scope")
        source_ids = tuple(sorted(_text(item, "source_id") for item in self.source_ids))
        if not source_ids or len(source_ids) != len(set(source_ids)):
            raise C10ContractError("source_ids must be nonempty and unique")
        model_release = str(self.model_release_id).strip()
        held_out = _sha256(
            self.held_out_receipt_sha256,
            "held_out_receipt_sha256",
            allow_empty=True,
        )
        if self.build_d_receipt is not None and not isinstance(
            self.build_d_receipt, BuildDValidationReceipt
        ):
            raise C10ContractError("build_d_receipt must be BuildDValidationReceipt or None")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "standard_uncertainty", uncertainty)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "direction", ObjectiveDirection(self.direction))
        object.__setattr__(self, "authority", ObjectiveAuthority(self.authority))
        object.__setattr__(self, "applicability_scope", scope)
        object.__setattr__(self, "source_ids", source_ids)
        object.__setattr__(self, "model_release_id", model_release)
        object.__setattr__(self, "held_out_receipt_sha256", held_out)


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate_id: str
    objectives: tuple[ObjectiveEstimate, ...]
    acquisition_estimates: tuple[ObjectiveEstimate, ...]

    def __post_init__(self) -> None:
        candidate_id = _text(self.candidate_id, "candidate_id")
        objectives = tuple(sorted(self.objectives, key=lambda item: item.name))
        acquisitions = tuple(sorted(self.acquisition_estimates, key=lambda item: item.name))
        if not objectives:
            raise C10ContractError("candidate evaluation requires objectives")
        if not acquisitions:
            raise C10ContractError("candidate evaluation requires acquisition estimates")
        _unique_named(objectives, "objectives", "name")
        _unique_named(acquisitions, "acquisition_estimates", "name")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "objectives", objectives)
        object.__setattr__(self, "acquisition_estimates", acquisitions)


@dataclass(frozen=True, slots=True)
class AcquisitionTerm:
    name: str
    direction: ObjectiveDirection
    minimum: float
    maximum: float
    weight: float

    def __post_init__(self) -> None:
        minimum = _finite(self.minimum, "acquisition minimum")
        maximum = _finite(self.maximum, "acquisition maximum")
        if minimum >= maximum:
            raise C10ContractError("acquisition minimum must be less than maximum")
        object.__setattr__(self, "name", _text(self.name, "acquisition term name"))
        object.__setattr__(self, "direction", ObjectiveDirection(self.direction))
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)
        object.__setattr__(self, "weight", _positive(self.weight, "acquisition weight"))


@dataclass(frozen=True, slots=True)
class AcquisitionPolicy:
    policy_id: str
    version: str
    terms: tuple[AcquisitionTerm, ...]
    maximum_new_candidates: int

    def __post_init__(self) -> None:
        terms = tuple(sorted(self.terms, key=lambda item: item.name))
        if not terms:
            raise C10ContractError("acquisition policy requires at least one term")
        _unique_named(terms, "acquisition terms", "name")
        maximum = int(self.maximum_new_candidates)
        if maximum <= 0:
            raise C10ContractError("maximum_new_candidates must be greater than zero")
        object.__setattr__(self, "policy_id", _text(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _text(self.version, "version"))
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "maximum_new_candidates", maximum)

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class StopPolicy:
    policy_id: str
    minimum_expected_information_gain: float
    minimum_expected_improvement: float
    budget_limit: float
    maximum_protected_attribute_risk: float

    def __post_init__(self) -> None:
        maximum_risk = _nonnegative(
            self.maximum_protected_attribute_risk,
            "maximum_protected_attribute_risk",
        )
        if maximum_risk > 1:
            raise C10ContractError("maximum_protected_attribute_risk must be at most one")
        object.__setattr__(self, "policy_id", _text(self.policy_id, "policy_id"))
        object.__setattr__(
            self,
            "minimum_expected_information_gain",
            _nonnegative(
                self.minimum_expected_information_gain,
                "minimum_expected_information_gain",
            ),
        )
        object.__setattr__(
            self,
            "minimum_expected_improvement",
            _nonnegative(
                self.minimum_expected_improvement,
                "minimum_expected_improvement",
            ),
        )
        object.__setattr__(self, "budget_limit", _positive(self.budget_limit, "budget_limit"))
        object.__setattr__(self, "maximum_protected_attribute_risk", maximum_risk)


@dataclass(frozen=True, slots=True)
class CampaignState:
    spent_budget: float
    protected_attribute_risk: float
    unavailable_data_dominates: bool
    unavailable_data_evidence_sha256: str
    sensory_plateau: bool
    sensory_plateau_evidence_sha256: str

    def __post_init__(self) -> None:
        risk = _nonnegative(self.protected_attribute_risk, "protected_attribute_risk")
        if risk > 1:
            raise C10ContractError("protected_attribute_risk must be at most one")
        unavailable_hash = _sha256(
            self.unavailable_data_evidence_sha256,
            "unavailable_data_evidence_sha256",
            allow_empty=True,
        )
        plateau_hash = _sha256(
            self.sensory_plateau_evidence_sha256,
            "sensory_plateau_evidence_sha256",
            allow_empty=True,
        )
        if self.unavailable_data_dominates and not unavailable_hash:
            raise C10ContractError("unavailable-data stop requires evidence SHA-256")
        if self.sensory_plateau and not plateau_hash:
            raise C10ContractError("sensory plateau stop requires evidence SHA-256")
        object.__setattr__(self, "spent_budget", _nonnegative(self.spent_budget, "spent_budget"))
        object.__setattr__(self, "protected_attribute_risk", risk)
        object.__setattr__(
            self, "unavailable_data_dominates", bool(self.unavailable_data_dominates)
        )
        object.__setattr__(self, "unavailable_data_evidence_sha256", unavailable_hash)
        object.__setattr__(self, "sensory_plateau", bool(self.sensory_plateau))
        object.__setattr__(self, "sensory_plateau_evidence_sha256", plateau_hash)


@dataclass(frozen=True, slots=True)
class ConstraintViolation:
    code: str
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "violation code"))
        object.__setattr__(self, "detail", _text(self.detail, "violation detail"))


@dataclass(frozen=True, slots=True)
class CandidateAccounting:
    raw_mass_mg: float
    active_mass_mg: float
    carrier_mass_mg: float
    unallocated_mass_mg: float
    carrier_masses_mg: tuple[tuple[str, float], ...]
    module_active_masses_mg: tuple[tuple[str, float], ...]
    material_active_masses_mg: tuple[tuple[str, float], ...]
    family_active_masses_mg: tuple[tuple[str, float], ...]
    cost: float


@dataclass(frozen=True, slots=True)
class FeasibilityAssessment:
    candidate_id: str
    formula_state_sha256: str
    feasible: bool
    violations: tuple[ConstraintViolation, ...]
    accounting: CandidateAccounting


@dataclass(frozen=True, slots=True)
class MixtureDesignResult:
    domain_sha256: str
    candidates: tuple[MixtureCandidate, ...]
    considered_count: int
    rejected_count: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class ObjectiveAuthorityAssessment:
    accepted: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    candidate_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UtilityContribution:
    name: str
    conservative_value: float
    normalized_value: float
    weight: float
    weighted_contribution: float


@dataclass(frozen=True, slots=True)
class CandidateUtility:
    candidate_id: str
    score: float
    contributions: tuple[UtilityContribution, ...]


@dataclass(frozen=True, slots=True)
class ExperimentProposal:
    status: SelectionStatus
    selected_candidate_ids: tuple[str, ...]
    pareto_candidate_ids: tuple[str, ...]
    rejections: tuple[CandidateRejection, ...]
    stop_reasons: tuple[StopReason, ...]
    blocker_codes: tuple[str, ...]
    utilities: tuple[CandidateUtility, ...]
    domain_sha256: str
    acquisition_policy_sha256: str
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.execution_authorized:
            raise C10ContractError("experiment proposals are never execution-authorized")
        object.__setattr__(self, "status", SelectionStatus(self.status))

    def as_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self.as_dict())


@dataclass(frozen=True, slots=True)
class HumanReviewReceipt:
    status: GateStatus
    subject_sha256: str
    evidence_sha256: str
    reviewer_role: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", GateStatus(self.status))
        object.__setattr__(self, "subject_sha256", _sha256(self.subject_sha256, "subject_sha256"))
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha256(self.evidence_sha256, "evidence_sha256"),
        )
        object.__setattr__(self, "reviewer_role", _text(self.reviewer_role, "reviewer_role"))


@dataclass(frozen=True, slots=True)
class AuthorizedExperimentSet:
    proposal_sha256: str
    selected_candidate_ids: tuple[str, ...]
    human_review_evidence_sha256: str
    execution_authorized: bool = True

    def __post_init__(self) -> None:
        if not self.execution_authorized:
            raise C10ContractError("authorized experiment set must be execution-authorized")
        object.__setattr__(
            self, "proposal_sha256", _sha256(self.proposal_sha256, "proposal_sha256")
        )
        object.__setattr__(
            self,
            "human_review_evidence_sha256",
            _sha256(self.human_review_evidence_sha256, "human_review_evidence_sha256"),
        )


__all__ = [
    "AcquisitionPolicy",
    "AcquisitionTerm",
    "AuthorizedExperimentSet",
    "C10ContractError",
    "CampaignState",
    "CandidateAccounting",
    "CandidateDose",
    "CandidateEvaluation",
    "CandidateRejection",
    "CandidateRole",
    "CandidateUtility",
    "ConstraintViolation",
    "DesignStage",
    "ExperimentProposal",
    "FamilyFractionRange",
    "FeasibilityAssessment",
    "GateReceipt",
    "GateStatus",
    "HumanReviewReceipt",
    "MixtureCandidate",
    "MixtureDesignAxis",
    "MixtureDesignResult",
    "MixtureDomain",
    "ModuleActiveRange",
    "NegativeSpaceCap",
    "NumericRange",
    "ObjectiveAuthority",
    "ObjectiveAuthorityAssessment",
    "ObjectiveDirection",
    "ObjectiveEstimate",
    "RecognizerFloor",
    "SelectionStatus",
    "StockDefinition",
    "StopPolicy",
    "StopReason",
    "UtilityContribution",
    "canonical_json_bytes",
    "canonical_sha256",
    "is_sha256",
    "to_primitive",
]
