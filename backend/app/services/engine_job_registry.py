"""Closed, data-only registry for durable Checkpoint-2 engine jobs.

The registry is deliberately incapable of accepting import paths, callables,
shell commands, training requests, or caller-selected execution code.  It
normalizes the small public payload for each admitted job type and binds the
exact implementation files that must participate in its fingerprint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENGINE_JOB_CONTRACT_VERSION = "perfume-chem-engine-job-contract-v1"
ENGINE_JOB_CONTRACT_VERSION_V2 = "perfume-chem-engine-job-contract-v2"
_COMMON_IMPLEMENTATION_PATHS = (
    "backend/app/services/engine_job_registry.py",
    "backend/app/services/engine_job_executor.py",
)


def _decimal_text(value: str, *, positive: bool = False) -> str:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("quantity must be a finite decimal string") from error
    if not decimal_value.is_finite() or decimal_value < 0:
        raise ValueError("quantity must be a finite non-negative decimal")
    if positive and decimal_value <= 0:
        raise ValueError("quantity must be greater than zero")
    if decimal_value == 0:
        return "0"
    rendered = format(decimal_value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


class _StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _StrictV2Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EngineFormulaRow(_StrictPayload):
    row_id: str = Field(min_length=1, max_length=255)
    material: str = Field(min_length=1, max_length=255)
    amount_decimal: str
    amount_unit: Literal["uL", "mL", "mg", "g"]
    stock_id: str | None = Field(default=None, max_length=255)
    concentration_fraction_decimal: str | None = None
    concentration_basis: Literal["W_W", "V_V", "NEAT", "UNKNOWN"] = "UNKNOWN"
    carrier: str | None = Field(default=None, max_length=255)
    basket: str | None = Field(default=None, max_length=40)
    role: str | None = Field(default=None, max_length=500)
    operation: Literal["PRECHARGE", "DIRECT_ADD", "POSTCHARGE", "MASS_ADD"] = (
        "DIRECT_ADD"
    )

    @field_validator("amount_decimal")
    @classmethod
    def normalize_amount(cls, value: str) -> str:
        return _decimal_text(value, positive=True)

    @field_validator("concentration_fraction_decimal")
    @classmethod
    def normalize_fraction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _decimal_text(value)
        if Decimal(normalized) > 1:
            raise ValueError("concentration fraction cannot exceed one")
        return normalized

    @field_validator("row_id", "material")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be blank")
        return text

    @field_validator("basket", "role", mode="before")
    @classmethod
    def normalize_optional_row_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class FormulaAnalysisPayload(_StrictPayload):
    formula_id: str = Field(min_length=1, max_length=255)
    formula_name: str = Field(min_length=1, max_length=255)
    rows: list[EngineFormulaRow] = Field(min_length=1, max_length=500)
    final_volume_ml_decimal: str | None = None

    @field_validator("final_volume_ml_decimal")
    @classmethod
    def normalize_volume(cls, value: str | None) -> str | None:
        return None if value is None else _decimal_text(value, positive=True)

    @model_validator(mode="after")
    def unique_rows(self):
        row_ids = [row.row_id for row in self.rows]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("row_id values must be unique")
        return self


class FormulaGoalAnalysisPayloadV2(FormulaAnalysisPayload):
    """Goal-first scientific analysis without caller-selected execution code."""

    model_config = ConfigDict(extra="forbid", strict=True)

    workflow_mode: Literal["PERSONAL_RESEARCH"] = "PERSONAL_RESEARCH"
    goals: list[str] = Field(min_length=1, max_length=12)
    observations: list[str] = Field(default_factory=list, max_length=24)
    must_preserve: list[str] = Field(default_factory=list, max_length=24)
    must_avoid: list[str] = Field(default_factory=list, max_length=24)
    family: str | None = Field(default=None, max_length=255)
    profile: str | None = Field(default=None, max_length=255)
    mode: Literal["pre_mix", "between_mix", "post_mix"] = "pre_mix"
    max_hypotheses: int = Field(default=3, ge=1, le=3)
    original_request: str | None = Field(default=None, max_length=4000)
    desired_changes: list[str] = Field(default_factory=list, max_length=12)
    execution_strategy: Literal["NEW_FORMULA", "EVOLVING_BOTTLE"] | None = None
    appeal_mode: Literal["IDENTITY_FIRST", "GLOBAL_CROWD_PLEASING"] | None = None
    comparison_evidence: Literal[
        "DOCUMENT_ONLY",
        "QUICK_BLIND",
        "CONTROLLED_PERSONAL",
        "TARGET_POPULATION",
    ] = "DOCUMENT_ONLY"
    reference_panel_id: str | None = Field(default=None, max_length=255)
    target_population: str | None = Field(default=None, max_length=500)
    evaluation_windows: list[str] = Field(default_factory=list, max_length=12)
    application_context: str | None = Field(default=None, max_length=500)
    active_bottle_id: str | None = Field(default=None, max_length=255)
    market_evidence_as_of_date: str = Field(
        default_factory=lambda: date.today().isoformat(),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )

    @field_validator(
        "goals",
        "observations",
        "must_preserve",
        "must_avoid",
        "desired_changes",
        "evaluation_windows",
    )
    @classmethod
    def normalize_text_list(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = value.strip()
            if not text:
                raise ValueError("text-list values must not be blank")
            key = " ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

    @field_validator(
        "family",
        "profile",
        "original_request",
        "reference_panel_id",
        "target_population",
        "application_context",
        "active_bottle_id",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("optional text must be omitted rather than blank")
        return text


class FormulaDesignPayloadV2(_StrictV2Payload):
    """Closed data-only contract for durable Formula Studio composition."""

    message: str = Field(min_length=1, max_length=4000)
    formula_name: str | None = Field(default=None, max_length=255)
    liquid_concentrate_ul_decimal: str = "6000"
    max_materials: int = Field(default=60, ge=6, le=60)
    must_preserve: list[str] = Field(default_factory=list, max_length=24)
    must_avoid: list[str] = Field(default_factory=list, max_length=24)
    previous_stock_ids: list[str] = Field(default_factory=list, max_length=60)
    conversation_context: list[str] = Field(default_factory=list, max_length=8)
    execution_strategy: Literal["NEW_FORMULA", "EVOLVING_BOTTLE"] | None = None
    appeal_mode: Literal["IDENTITY_FIRST", "GLOBAL_CROWD_PLEASING"] | None = None
    comparison_evidence: Literal[
        "DOCUMENT_ONLY",
        "QUICK_BLIND",
        "CONTROLLED_PERSONAL",
        "TARGET_POPULATION",
    ] = "DOCUMENT_ONLY"
    active_bottle_id: str | None = Field(default=None, max_length=255)
    design_mode: Literal["FAST_SKETCH", "DEEP_COMPOSE"] = "DEEP_COMPOSE"
    variant_count: int = Field(default=3, ge=1, le=3)

    @field_validator("liquid_concentrate_ul_decimal")
    @classmethod
    def normalize_liquid_total(cls, value: str) -> str:
        return _decimal_text(value, positive=True)

    @field_validator(
        "message",
        "formula_name",
        "active_bottle_id",
        mode="before",
    )
    @classmethod
    def normalize_formula_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("text must be omitted rather than blank")
        return text

    @field_validator(
        "must_preserve",
        "must_avoid",
        "previous_stock_ids",
        "conversation_context",
    )
    @classmethod
    def normalize_formula_lists(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = value.strip()
            if not text:
                raise ValueError("list values must not be blank")
            key = " ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result


class ReferencePanelEvaluationPayloadV2(_StrictV2Payload):
    target_snapshot_id: str = Field(min_length=1, max_length=255)
    target_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_interpretation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_panel_id: str = Field(min_length=1, max_length=255)
    reference_panel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    comparison_evidence: Literal[
        "DOCUMENT_ONLY",
        "QUICK_BLIND",
        "CONTROLLED_PERSONAL",
        "TARGET_POPULATION",
    ]
    observation_record_ids: list[str] = Field(default_factory=list, max_length=10000)
    seed: int
    as_of_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator(
        "target_snapshot_id",
        "reference_panel_id",
    )
    @classmethod
    def strip_reference_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be blank")
        return text

    @field_validator("observation_record_ids")
    @classmethod
    def unique_observation_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("observation record IDs must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("observation record IDs must be unique")
        return normalized


class ReleaseGatePayload(FormulaAnalysisPayload):
    expected_concentrate_ul_decimal: str
    brief: Literal[
        "auto",
        "generic",
        "aromatic_fougere",
        "layton_dna",
        "vetiver_woody",
    ] = "auto"

    @field_validator("expected_concentrate_ul_decimal")
    @classmethod
    def normalize_expected_total(cls, value: str) -> str:
        return _decimal_text(value, positive=True)


class MixerSequencePayload(FormulaAnalysisPayload):
    order_policy: Literal["BASKET_THEN_DESCENDING_LIQUIDS_MASS_SEPARATE"] = (
        "BASKET_THEN_DESCENDING_LIQUIDS_MASS_SEPARATE"
    )


class OptimizerVariable(_StrictPayload):
    variable_id: str = Field(min_length=1, max_length=255)
    minimum_decimal: str
    maximum_decimal: str
    unit: Literal["active_mass_g", "stock_mass_g", "stock_volume_uL"]

    @field_validator("minimum_decimal", "maximum_decimal")
    @classmethod
    def normalize_bound(cls, value: str) -> str:
        return _decimal_text(value)

    @model_validator(mode="after")
    def ordered_bounds(self):
        if Decimal(self.maximum_decimal) < Decimal(self.minimum_decimal):
            raise ValueError("maximum_decimal must be at least minimum_decimal")
        return self


class OptimizerSearchPayload(_StrictPayload):
    search_id: str = Field(min_length=1, max_length=255)
    endpoint_id: str = Field(min_length=1, max_length=255)
    variables: list[OptimizerVariable] = Field(min_length=1, max_length=20)
    budget_per_arm: int = Field(ge=1, le=10000)
    seeds: list[int] = Field(min_length=1, max_length=100)
    constant_total_basis: Literal["active_mass_g", "stock_mass_g", "stock_volume_uL"]
    constant_total_decimal: str

    @field_validator("constant_total_decimal")
    @classmethod
    def normalize_total(cls, value: str) -> str:
        return _decimal_text(value, positive=True)


class ShortlistCandidate(_StrictPayload):
    candidate_id: str = Field(min_length=1, max_length=255)
    lavender_share_decimal: str
    ambrox_share_decimal: str

    @field_validator("lavender_share_decimal", "ambrox_share_decimal")
    @classmethod
    def normalize_share(cls, value: str) -> str:
        normalized = _decimal_text(value)
        if Decimal(normalized) > 1:
            raise ValueError("share cannot exceed one")
        return normalized


class ShortlistEvaluationPayload(_StrictPayload):
    comparator_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    endpoint_id: str = Field(min_length=1, max_length=255)
    candidates: list[ShortlistCandidate] = Field(min_length=1, max_length=100)
    constant_total_basis: Literal[
        "UNRESOLVED",
        "active_mass_g",
        "stock_mass_g",
        "stock_volume_uL",
    ]
    constant_total_decimal: str | None = None

    @field_validator("constant_total_decimal")
    @classmethod
    def normalize_total(cls, value: str | None) -> str | None:
        return None if value is None else _decimal_text(value, positive=True)

    @model_validator(mode="after")
    def total_matches_basis(self):
        if (self.constant_total_basis == "UNRESOLVED") != (
            self.constant_total_decimal is None
        ):
            raise ValueError("unresolved basis must not declare a constant total")
        return self


class BatchGatePayload(_StrictPayload):
    corpus_id: str = Field(min_length=1, max_length=255)
    formula_ids: list[str] = Field(min_length=1, max_length=10000)
    worker_count: int = Field(ge=1, le=8)
    frozen_corpus_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("formula_ids")
    @classmethod
    def unique_formula_ids(cls, value: list[str]) -> list[str]:
        normalized = [str(item).strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("formula IDs must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("formula IDs must be unique")
        return normalized


class ReleaseComponentPayloadV2(_StrictV2Payload):
    material_id: str = Field(min_length=1, max_length=255)
    initial_mass_g_decimal: str = Field(min_length=1, max_length=128)
    identity_state: Literal["EXACT", "UNKNOWN_NATURAL_REMAINDER"] = "EXACT"
    molecular_weight_g_mol: float | None = Field(default=None, gt=0)
    vapor_pressure_pa: float | None = Field(default=None, gt=0)
    activity_coefficient: float | None = Field(default=None, gt=0)
    measured_interfacial_pressure_pa: float | None = Field(default=None, gt=0)
    substrate_retained_fraction_decimal: str = "0"
    precipitated_fraction_decimal: str = "0"
    reacted_fraction_decimal: str = "0"
    desorption_rate_s_decimal: str = "0"
    permeation_rate_s_decimal: str = "0"
    reaction_rate_s_decimal: str = "0"

    @field_validator(
        "initial_mass_g_decimal",
        "substrate_retained_fraction_decimal",
        "precipitated_fraction_decimal",
        "reacted_fraction_decimal",
        "desorption_rate_s_decimal",
        "permeation_rate_s_decimal",
        "reaction_rate_s_decimal",
    )
    @classmethod
    def normalize_release_decimal(cls, value: str) -> str:
        return _decimal_text(value)

    @model_validator(mode="after")
    def validate_release_fractions(self):
        fractions = (
            self.substrate_retained_fraction_decimal,
            self.precipitated_fraction_decimal,
            self.reacted_fraction_decimal,
        )
        if any(Decimal(value) > 1 for value in fractions) or sum(
            Decimal(value) for value in fractions
        ) > 1:
            raise ValueError("release compartment fractions cannot exceed one")
        return self


class ReleaseScenarioPayloadV2(_StrictV2Payload):
    scenario_id: str = Field(min_length=1, max_length=255)
    matrix_id: str = Field(min_length=1, max_length=255)
    substrate: Literal["GLASS", "BLOTTER", "SKIN_SURROGATE", "SKIN"]
    deposit_mass_g_decimal: str
    surface_area_m2_decimal: str
    temperature_k: float = Field(gt=0)
    relative_humidity_decimal: str
    airflow_m_s_decimal: str
    delivery_volume_m3_decimal: str
    sampling_geometry: str = Field(min_length=1, max_length=255)
    timepoints_seconds: list[float] = Field(min_length=1, max_length=1000)

    @field_validator(
        "deposit_mass_g_decimal",
        "surface_area_m2_decimal",
        "delivery_volume_m3_decimal",
    )
    @classmethod
    def normalize_positive_scenario_decimal(cls, value: str) -> str:
        return _decimal_text(value, positive=True)

    @field_validator("relative_humidity_decimal", "airflow_m_s_decimal")
    @classmethod
    def normalize_scenario_decimal(cls, value: str) -> str:
        return _decimal_text(value)

    @model_validator(mode="after")
    def validate_scenario_shape(self):
        if Decimal(self.relative_humidity_decimal) > 1:
            raise ValueError("relative humidity cannot exceed one")
        if self.timepoints_seconds[0] != 0 or self.timepoints_seconds != sorted(
            set(self.timepoints_seconds)
        ):
            raise ValueError("timepoints must begin at zero and be unique and increasing")
        return self


class ReleaseParametersPayloadV2(_StrictV2Payload):
    capability_id: str = Field(min_length=1, max_length=255)
    equilibrium_model: Literal[
        "MEASURED_HEADSPACE",
        "EMPIRICAL_ACTIVITY",
        "NONIDEAL_PARAMETERIZED",
        "IDEAL_SENSITIVITY",
        "HANSEN_SENSITIVITY",
    ]
    matrix_ids: list[str] = Field(min_length=1, max_length=100)
    supported_substrates: list[
        Literal["GLASS", "BLOTTER", "SKIN_SURROGATE", "SKIN"]
    ] = Field(min_length=1, max_length=4)
    mass_transfer_coefficient_m_s_decimal: str
    air_exchange_rate_s_decimal: str
    delivered_capture_fraction_decimal: str
    maximum_step_seconds_decimal: str
    calibration_state: Literal[
        "HELD_OUT_VALIDATED", "CALIBRATED_NO_HELD_OUT", "UNCALIBRATED"
    ]

    @field_validator(
        "mass_transfer_coefficient_m_s_decimal",
        "maximum_step_seconds_decimal",
    )
    @classmethod
    def normalize_positive_release_parameter(cls, value: str) -> str:
        return _decimal_text(value, positive=True)

    @field_validator(
        "air_exchange_rate_s_decimal",
        "delivered_capture_fraction_decimal",
    )
    @classmethod
    def normalize_release_parameter(cls, value: str) -> str:
        return _decimal_text(value)

    @model_validator(mode="after")
    def validate_capture_fraction(self):
        if Decimal(self.delivered_capture_fraction_decimal) > 1:
            raise ValueError("delivered capture fraction cannot exceed one")
        return self


class ReleaseSimulationPayloadV2(_StrictV2Payload):
    formula_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    components: list[ReleaseComponentPayloadV2] = Field(min_length=1, max_length=500)
    scenario: ReleaseScenarioPayloadV2
    parameters: ReleaseParametersPayloadV2

    @model_validator(mode="after")
    def unique_release_materials(self):
        identities = [row.material_id for row in self.components]
        if len(identities) != len(set(identities)):
            raise ValueError("release material identities must be unique")
        return self


class OfflineCandidatePayloadV2(_StrictV2Payload):
    candidate_id: str = Field(min_length=1, max_length=255)
    formula_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    variables: dict[str, float]
    endpoint_value: float
    prediction_interval: list[float] = Field(min_length=2, max_length=2)
    coverage_decimal: str
    applicability_state: Literal[
        "APPLICABLE", "PARTIAL", "OUT_OF_DOMAIN", "UNAVAILABLE"
    ]
    feature_lineage: list[str] = Field(min_length=1, max_length=100)
    model_signs: dict[str, Literal[-1, 0, 1]] = Field(default_factory=dict)

    @field_validator("coverage_decimal")
    @classmethod
    def normalize_candidate_coverage(cls, value: str) -> str:
        normalized = _decimal_text(value)
        if Decimal(normalized) > 1:
            raise ValueError("candidate coverage cannot exceed one")
        return normalized

    @model_validator(mode="after")
    def validate_candidate_numeric_shape(self):
        if not self.variables:
            raise ValueError("candidate variables must not be empty")
        if self.prediction_interval[0] > self.prediction_interval[1]:
            raise ValueError("candidate prediction interval is reversed")
        return self


class OptimizerSearchPayloadV2(_StrictV2Payload):
    search_id: str = Field(min_length=1, max_length=255)
    endpoint_id: str = Field(min_length=1, max_length=255)
    baseline_id: str = Field(min_length=1, max_length=255)
    candidates: list[OfflineCandidatePayloadV2] = Field(min_length=2, max_length=10000)
    budget_per_arm: int = Field(default=64, ge=1, le=10000)
    seeds: list[int] = Field(default_factory=lambda: [17, 29, 43, 71, 101], min_length=1, max_length=100)
    minimize: bool = True

    @model_validator(mode="after")
    def validate_optimizer_pool(self):
        identities = [row.candidate_id for row in self.candidates]
        if len(identities) != len(set(identities)):
            raise ValueError("optimizer candidate IDs must be unique")
        if self.baseline_id not in identities:
            raise ValueError("optimizer baseline_id is absent from candidates")
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("optimizer seeds must be unique")
        return self


class CandidateEvaluationPayloadV2(_StrictV2Payload):
    endpoint_id: str = Field(min_length=1, max_length=255)
    candidate: OfflineCandidatePayloadV2


class ShortlistEvaluationPayloadV2(_StrictV2Payload):
    endpoint_id: str = Field(min_length=1, max_length=255)
    candidates: list[OfflineCandidatePayloadV2] = Field(min_length=1, max_length=1000)
    lower_is_better: bool = True


class ModelBenchmarkPayloadV2(OptimizerSearchPayloadV2):
    benchmark_id: str = Field(min_length=1, max_length=255)


class PairwisePreferencePayloadV2(_StrictV2Payload):
    left_item: str = Field(min_length=1, max_length=255)
    right_item: str = Field(min_length=1, max_length=255)
    preferred_item: str | None = Field(default=None, max_length=255)
    comparison_id: str = Field(min_length=1, max_length=255)
    assessor_id: str = Field(min_length=1, max_length=255)
    protocol_id: str = Field(min_length=1, max_length=255)
    criterion_id: str = Field(min_length=1, max_length=255)
    time_seconds: float = Field(ge=0)
    first_presented_item: str = Field(min_length=1, max_length=255)


class PreferenceAnalysisPayloadV2(_StrictV2Payload):
    analysis_id: str = Field(min_length=1, max_length=255)
    criterion_id: str = Field(min_length=1, max_length=255)
    comparisons: list[PairwisePreferencePayloadV2] = Field(min_length=1, max_length=10000)
    minimum_comparisons: int = Field(default=10, ge=1)
    minimum_sessions: int = Field(default=3, ge=1)
    regularization: float = Field(default=0.1, ge=0)
    bootstrap_replicates: int = Field(default=0, ge=0, le=10000)
    bootstrap_seed: int = 17


class BatchFormulaPayloadV2(ReleaseGatePayload):
    pass


class BatchGatePayloadV2(_StrictV2Payload):
    corpus_id: str = Field(min_length=1, max_length=255)
    frozen_corpus_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    formulas: list[BatchFormulaPayloadV2] = Field(min_length=1, max_length=10000)
    worker_count: int = Field(default=4, ge=1, le=8)

    @model_validator(mode="after")
    def unique_batch_formula_ids(self):
        formula_ids = [row.formula_id for row in self.formulas]
        if len(formula_ids) != len(set(formula_ids)):
            raise ValueError("batch formula IDs must be unique")
        return self


@dataclass(frozen=True, slots=True)
class EngineJobSpec:
    payload_model: type[BaseModel]
    execution_class: str
    timeout_seconds: int
    implementation_paths: tuple[str, ...]
    payload_model_v2: type[BaseModel] | None = None


class OmissionControlRowV1(_StrictV2Payload):
    stock_id: str = Field(min_length=1, max_length=255)
    identity_name: str = Field(min_length=1, max_length=255)
    amount_decimal: str = Field(min_length=1, max_length=40)
    amount_unit: Literal["mg", "uL"]
    stock_fraction_decimal: str = Field(min_length=1, max_length=40)
    fraction_basis: Literal["w/w", "w/v", "v/v", "unknown", "neat"]
    carrier: str | None = Field(default=None, max_length=255)

    @field_validator("amount_decimal", "stock_fraction_decimal")
    @classmethod
    def positive_decimal(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            raise ValueError("use a plain positive decimal string, not exponent notation")
        return _decimal_text(value, positive=True)

    @model_validator(mode="after")
    def fraction_ceiling(self):
        if Decimal(self.stock_fraction_decimal) > 1:
            raise ValueError("stock fraction cannot exceed one")
        return self


class OmissionCarrierBlankV1(_StrictV2Payload):
    stock_id: str = Field(min_length=1, max_length=255)
    carrier: str = Field(min_length=1, max_length=255)


def _positive_plain_decimal(value: str) -> str:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("use a plain positive decimal string, not exponent notation")
    return _decimal_text(value, positive=True)


class AdditionChangeV1(_StrictV2Payload):
    """Add one material that is not in the control, at a stated amount and stock dilution."""

    kind: Literal["ADDITION"]
    row: OmissionControlRowV1
    bottle_volume_ul_decimal: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("bottle_volume_ul_decimal")
    @classmethod
    def positive_volume(cls, value: str | None) -> str | None:
        return None if value is None else _positive_plain_decimal(value)


class DoseStepChangeV1(_StrictV2Payload):
    """Change one existing control row by a stated amount, in that row's unit."""

    kind: Literal["DOSE_STEP"]
    stock_id: str = Field(min_length=1, max_length=255)
    direction: Literal["UP", "DOWN"]
    step_decimal: str = Field(min_length=1, max_length=40)
    bottle_volume_ul_decimal: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("step_decimal", "bottle_volume_ul_decimal")
    @classmethod
    def positive_decimals(cls, value: str | None) -> str | None:
        return None if value is None else _positive_plain_decimal(value)


class OmissionComparisonPlanPayloadV2(_StrictV2Payload):
    schema_version: Literal["omission-comparison-plan-request-v1"]
    control_rows: list[OmissionControlRowV1] = Field(min_length=2, max_length=60)
    omit_stock_ids: list[str] = Field(default_factory=list, max_length=59)
    protected_stock_ids: list[str] = Field(default_factory=list, max_length=60)
    carrier_blanks: dict[str, OmissionCarrierBlankV1] = Field(default_factory=dict, max_length=10)
    goal: str = Field(min_length=1, max_length=500)
    mode: Literal["QUICK_REFERENCE", "CONTROLLED_REFERENCE"] = "QUICK_REFERENCE"
    seed: int = Field(default=17, ge=0, le=2147483647)
    # Absent fields keep an omission request's canonical payload byte-identical.
    change: Annotated[AdditionChangeV1 | DoseStepChangeV1, Field(discriminator="kind")] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    triangle_tries: int | None = Field(default=None, ge=3, le=30, exclude_if=lambda value: value is None)

    @field_validator("change", mode="before")
    @classmethod
    def one_change_object(cls, value: Any) -> Any:
        if isinstance(value, list):
            raise ValueError(
                f"Choose exactly one change per plan; this request lists {len(value)}. "
                "Send each change as its own plan."
            )
        return value

    @model_validator(mode="after")
    def exact_ids(self):
        ids = [row.stock_id for row in self.control_rows]
        if self.change is None:
            if not self.omit_stock_ids:
                raise ValueError(
                    "Choose exactly one change: name the row to omit, or give one ADDITION or DOSE_STEP change."
                )
            if (len(set(ids)) != len(ids) or len(set(self.omit_stock_ids)) != len(self.omit_stock_ids)
                    or not set(self.omit_stock_ids) < set(ids)
                    or not set(self.protected_stock_ids) <= set(ids)):
                raise ValueError("omission IDs must name distinct control rows and retain a control")
        else:
            if self.omit_stock_ids:
                raise ValueError(
                    "Choose exactly one change per plan: this request has both an omission and an "
                    f"{self.change.kind}. Send them as separate plans."
                )
            if len(set(ids)) != len(ids) or not set(self.protected_stock_ids) <= set(ids):
                raise ValueError("control rows must be distinct and protected IDs must name control rows")
            change = self.change
            if isinstance(change, AdditionChangeV1) and change.row.stock_id in ids:
                raise ValueError(
                    "An addition must be a material that is not already in the control; "
                    "use DOSE_STEP to change an existing row."
                )
            if isinstance(change, DoseStepChangeV1):
                if change.stock_id not in ids:
                    raise ValueError("A dose step must name one of the control rows.")
                current = Decimal(self.control_rows[ids.index(change.stock_id)].amount_decimal)
                if change.direction == "DOWN" and Decimal(change.step_decimal) >= current:
                    raise ValueError(
                        "A step down must leave some of the material; to remove it completely, use an omission plan."
                    )
                stepped = self.control_rows[ids.index(change.stock_id)]
                if change.direction == "DOWN" and not stepped.carrier:
                    raise ValueError(
                        f"{stepped.identity_name} is neat, so there is no carrier to balance a step down with; "
                        "this plan can't keep both versions at the same total for a neat material yet."
                    )
                blank = self.carrier_blanks.get(stepped.carrier) if stepped.carrier else None
                if change.direction == "DOWN" and (blank is None or blank.carrier != stepped.carrier
                                                   or blank.stock_id in ids):
                    raise ValueError(
                        "A step down is tried in fresh vials with a carrier blank so both hold the same total: "
                        f"{stepped.identity_name} needs a blank stock for its carrier ({stepped.carrier}) "
                        "that is not one of the control rows."
                    )
        blank_ids = [blank.stock_id for blank in self.carrier_blanks.values()]
        if len(set(blank_ids)) != len(blank_ids):
            raise ValueError("one blank stock cannot represent multiple carriers")
        return self


ENGINE_JOB_REGISTRY: dict[str, EngineJobSpec] = {
    "OMISSION_COMPARISON_PLAN": EngineJobSpec(
        OmissionComparisonPlanPayloadV2, "READ_ONLY_DIAGNOSTIC", 30,
        ("engine/research/controlled_omission.py", "engine/research/one_change.py",
         "engine/research/protocols.py", "engine/research/contracts.py"),
        OmissionComparisonPlanPayloadV2,
    ),
    "FORMULA_DESIGN": EngineJobSpec(
        FormulaDesignPayloadV2,
        "READ_ONLY_BATCH",
        300,
        (
            "engine/research/formula_design.py",
            "engine/research/composition_planner.py",
            "engine/research/request_interpretation.py",
            "engine/formulation_intelligence/semantic_brief_adapter.py",
            "engine/formulation_intelligence/material_capability_index.py",
            "engine/formulation_intelligence/formula_solver.py",
            "engine/formulation_intelligence/formula_critic.py",
            "engine/formulation_intelligence/formula_design_runtime.py",
            "engine/formulation_intelligence/architecture_bridge.py",
            "engine/formulation_intelligence/architecture_rules_v5.py",
            "engine/formulation_intelligence/subtype_coverage.py",
            "engine/formulation_intelligence/literature_knowledge.py",
            "engine/formulation_intelligence/construction_library.py",
            "engine/formulation_intelligence/subtype_research.py",
            "engine/inventory_parser.py",
            "engine/ingredient_intelligence.py",
        ),
        FormulaDesignPayloadV2,
    ),
    "FORMULA_ANALYSIS": EngineJobSpec(
        FormulaAnalysisPayload,
        "READ_ONLY_DIAGNOSTIC",
        90,
        (
            "engine/workbench.py",
            "engine/pipeline/formula_state.py",
            "backend/app/services/validation_pipeline.py",
            "engine/research/goal_analysis.py",
            "engine/formulation_intelligence/literature_knowledge.py",
            "engine/formulation_intelligence/construction_library.py",
            "engine/formulation_intelligence/subtype_research.py",
            "engine/intervention_profiles.py",
            "engine/inventory_parser.py",
        ),
        FormulaGoalAnalysisPayloadV2,
    ),
    "RELEASE_SIMULATION": EngineJobSpec(
        ReleaseSimulationPayloadV2,
        "READ_ONLY_DIAGNOSTIC",
        120,
        (
            "engine/research/contracts.py",
            "engine/research/release.py",
        ),
        ReleaseSimulationPayloadV2,
    ),
    "RELEASE_GATE": EngineJobSpec(
        ReleaseGatePayload,
        "READ_ONLY_DIAGNOSTIC",
        120,
        (
            "scripts/formula_release_gate.py",
            "engine/pipeline/gates.py",
            "engine/pipeline/formula_state.py",
        ),
    ),
    "MIXER_SEQUENCE": EngineJobSpec(
        MixerSequencePayload,
        "READ_ONLY_DIAGNOSTIC",
        60,
        ("engine/mixer/sequencer.py", "engine/mixer/instructions.py"),
    ),
    "OPTIMIZER_SEARCH": EngineJobSpec(
        OptimizerSearchPayload,
        "READ_ONLY_BATCH",
        300,
        (
            "engine/optimizer/gate_aware.py",
            "engine/research/selection.py",
        ),
        OptimizerSearchPayloadV2,
    ),
    "CANDIDATE_EVALUATION": EngineJobSpec(
        CandidateEvaluationPayloadV2,
        "READ_ONLY_DIAGNOSTIC",
        90,
        (
            "engine/research/contracts.py",
            "engine/research/perception.py",
            "engine/research/selection.py",
        ),
        CandidateEvaluationPayloadV2,
    ),
    "SHORTLIST_EVALUATION": EngineJobSpec(
        ShortlistEvaluationPayload,
        "READ_ONLY_BATCH",
        300,
        (
            "engine/dose_response.py",
            "engine/optimizer/gate_aware.py",
            "engine/research/perception.py",
            "engine/research/selection.py",
        ),
        ShortlistEvaluationPayloadV2,
    ),
    "MODEL_BENCHMARK": EngineJobSpec(
        ModelBenchmarkPayloadV2,
        "READ_ONLY_BATCH",
        300,
        (
            "engine/research/selection.py",
            "engine/research/capabilities.py",
            "engine/research/perception.py",
            "engine/dose_response.py",
        ),
        ModelBenchmarkPayloadV2,
    ),
    "PREFERENCE_ANALYSIS": EngineJobSpec(
        PreferenceAnalysisPayloadV2,
        "READ_ONLY_BATCH",
        300,
        (
            "engine/research/preference.py",
            "engine/research/protocols.py",
            "engine/preference.py",
        ),
        PreferenceAnalysisPayloadV2,
    ),
    "REFERENCE_PANEL_EVALUATION": EngineJobSpec(
        ReferencePanelEvaluationPayloadV2,
        "READ_ONLY_DIAGNOSTIC",
        90,
        (
            "engine/research/commercial_references.py",
            "engine/research/request_interpretation.py",
            "engine/research/protocols.py",
            "data/governance/commercial_reference_registry_v1.json",
            "data/governance/commercial_reference_registry_v2.json",
            "data/governance/commercial_reference_registry_v3.json",
        ),
        ReferencePanelEvaluationPayloadV2,
    ),
    "BATCH_GATE": EngineJobSpec(
        BatchGatePayload,
        "READ_ONLY_BATCH",
        1800,
        (
            "scripts/batch_gate_all_formulas.py",
            "scripts/formula_release_gate.py",
            "engine/research/comparison.py",
        ),
        BatchGatePayloadV2,
    ),
}


def validate_engine_payload(
    job_type: str,
    payload: dict[str, Any],
    *,
    request_schema_version: str = "lab-engine-job-request-v1",
) -> dict[str, Any]:
    """Return the exact canonical data-only payload for an admitted job."""

    spec = ENGINE_JOB_REGISTRY.get(job_type)
    if spec is None:
        raise ValueError("UNSUPPORTED_ENGINE_JOB_TYPE")
    model: type[BaseModel] = spec.payload_model
    if request_schema_version == "lab-engine-job-request-v2":
        model = spec.payload_model_v2 or spec.payload_model
    elif request_schema_version != "lab-engine-job-request-v1":
        raise ValueError("UNSUPPORTED_ENGINE_JOB_REQUEST_SCHEMA")
    elif job_type in {
        "RELEASE_SIMULATION",
        "CANDIDATE_EVALUATION",
        "MODEL_BENCHMARK",
        "PREFERENCE_ANALYSIS",
        "REFERENCE_PANEL_EVALUATION",
        "FORMULA_DESIGN",
        "OMISSION_COMPARISON_PLAN",
    }:
        raise ValueError("ENGINE_JOB_TYPE_REQUIRES_V2_SCHEMA")
    validated = model.model_validate(payload)
    normalized = validated.model_dump(
        mode="json",
        exclude_none=request_schema_version == "lab-engine-job-request-v1",
    )
    if (
        request_schema_version == "lab-engine-job-request-v2"
        and job_type == "BATCH_GATE"
    ):
        server_hash = sha256(
            json.dumps(
                {
                    "schema_version": "engine-batch-corpus-v2",
                    "formulas": normalized["formulas"],
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        supplied = normalized.get("frozen_corpus_sha256")
        if supplied is not None and supplied != server_hash:
            raise ValueError("FROZEN_CORPUS_HASH_MISMATCH")
        normalized["frozen_corpus_sha256"] = server_hash
    return normalized


def implementation_paths(job_type: str) -> tuple[Path, ...]:
    spec = ENGINE_JOB_REGISTRY[job_type]
    relative_paths = tuple(dict.fromkeys((*_COMMON_IMPLEMENTATION_PATHS, *spec.implementation_paths)))
    return tuple(REPOSITORY_ROOT / item for item in relative_paths)


__all__ = [
    "ENGINE_JOB_CONTRACT_VERSION",
    "ENGINE_JOB_CONTRACT_VERSION_V2",
    "ENGINE_JOB_REGISTRY",
    "REPOSITORY_ROOT",
    "implementation_paths",
    "validate_engine_payload",
]
