"""Closed, data-only registry for durable Checkpoint-2 engine jobs.

The registry is deliberately incapable of accepting import paths, callables,
shell commands, training requests, or caller-selected execution code.  It
normalizes the small public payload for each admitted job type and binds the
exact implementation files that must participate in its fingerprint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

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
    max_hypotheses: int = Field(default=5, ge=1, le=12)

    @field_validator("goals", "observations", "must_preserve", "must_avoid")
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

    @field_validator("family", "profile")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("optional text must be omitted rather than blank")
        return text


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


ENGINE_JOB_REGISTRY: dict[str, EngineJobSpec] = {
    "FORMULA_ANALYSIS": EngineJobSpec(
        FormulaAnalysisPayload,
        "READ_ONLY_DIAGNOSTIC",
        90,
        (
            "engine/workbench.py",
            "engine/pipeline/formula_state.py",
            "backend/app/services/validation_pipeline.py",
            "engine/research/goal_analysis.py",
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
