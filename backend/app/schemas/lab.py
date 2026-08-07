"""Strict request schemas for the local laboratory API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LabRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MaterialCreate(LabRequest):
    canonical_name: str = Field(min_length=1, max_length=255)


class StockCreate(LabRequest):
    material_id: str
    active_fraction: float = Field(gt=0, le=1)
    fraction_basis: Literal["mass_fraction", "volume_fraction", "amount_fraction"]
    initial_mass_g: float = Field(ge=0)
    density_g_ml: float | None = Field(default=None, gt=0)
    supplier: str | None = None
    lot_number: str | None = None
    solvent_name: str | None = None


class AliasCreate(LabRequest):
    alias: str = Field(min_length=1, max_length=255)


class StockUpdateRemaining(LabRequest):
    remaining_mass_g: float = Field(ge=0)


class FormulaResponse(BaseModel):
    id: str
    name: str
    created_at: str | None = None
    latest_version: int | None = None


class FormulaVersionResponse(BaseModel):
    id: str
    formula_id: str
    version_number: int
    brief_json: dict
    constraints_json: dict
    concentration_fraction: float | None = None
    concentration_basis: str | None = None
    composition_status: Literal["recorded", "missing"] = "missing"
    components: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None


class BottleCreate(LabRequest):
    label: str = Field(min_length=1, max_length=255)
    initial_mass_g: float = Field(default=0, ge=0)


class BottleAdditionCreate(LabRequest):
    stock_solution_id: str
    mass_g: float = Field(gt=0)
    expected_sequence: int = Field(ge=0)
    command_id: str = Field(min_length=1)
    measured_volume_ul: float | None = Field(default=None, gt=0)


class BottleTransferCreate(LabRequest):
    source_bottle_id: str
    destination_bottle_id: str
    mass_g: float = Field(gt=0)
    source_expected_sequence: int = Field(ge=0)
    destination_expected_sequence: int = Field(ge=0)
    command_id: str = Field(min_length=1)


class BottleCompensationCreate(LabRequest):
    bottle_id: str
    event_id: str
    expected_sequence: int = Field(ge=0)
    command_id: str = Field(min_length=1)


class LabFormulaCreate(LabRequest):
    name: str = Field(min_length=1, max_length=255)


class FormulaComponentCreate(LabRequest):
    stock_solution_id: str = Field(min_length=1)
    requested_mass_g: float = Field(gt=0)
    requested_volume_ul: float | None = Field(default=None, gt=0)
    role: str | None = Field(default=None, max_length=80)
    unit: Literal["g"] = "g"


class FormulaVersionCreate(LabRequest):
    brief: dict[str, Any]
    constraints: dict[str, Any]
    concentration_fraction: float | None = Field(default=None, ge=0, le=1)
    concentration_basis: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    components: tuple[FormulaComponentCreate, ...] = ()


class ExperimentCreate(LabRequest):
    name: str = Field(min_length=1, max_length=255)
    protocol: dict[str, Any]
    status: str = Field(default="planned", min_length=1)


class SampleCreate(LabRequest):
    bottle_id: str
    blind_code: str = Field(min_length=1, max_length=100)


class ApplicationCreate(LabRequest):
    sample_id: str
    applied_at: datetime
    dose: dict[str, Any]
    context: dict[str, Any]


class ObservationCreate(LabRequest):
    elapsed_seconds: float = Field(ge=0)
    observations: dict[str, Any]


class PairwiseComparisonCreate(LabRequest):
    experiment_id: str
    left_sample_id: str
    right_sample_id: str
    preferred_sample_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PredictionCreate(LabRequest):
    experiment_id: str
    sample_id: str | None = None
    model_key: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    status: str = Field(min_length=1)
    prediction: dict[str, Any]
    evidence_id: str | None = None


class OutcomeCreate(LabRequest):
    experiment_id: str
    prediction_id: str | None = None
    outcome: dict[str, Any]


class AssistantPacketCreate(LabRequest):
    intent: str = Field(min_length=1)
    subject_id: str | None = None
    facts: dict[str, Any] = Field(default_factory=dict)
    calculations: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class BackupCreate(LabRequest):
    label: str = Field(default="manual", min_length=1, max_length=80)


class RestoreSnapshotCreate(LabRequest):
    snapshot_path: str = Field(min_length=1)


class InterventionBriefCreate(LabRequest):
    name: str = Field(min_length=1)
    required_character_tags: frozenset[str] = frozenset()
    forbidden_materials: frozenset[str] = frozenset()
    maximum_active_addition_ppm_w_w: float = Field(default=1_000_000, ge=0)


class InterventionStockCreate(LabRequest):
    material: str
    available_stock_mass_mg: float = Field(ge=0)
    active_mass_fraction: float = Field(gt=0, le=1)
    minimum_measurable_stock_mass_mg: float = Field(gt=0)
    dispensing_increment_mg: float = Field(gt=0)


class InterventionCandidateCreate(LabRequest):
    material: str
    requested_active_ppm_w_w: float = Field(gt=0)
    predicted_oav_delta: float = Field(ge=0)
    desired_effects: dict[str, float]
    preserved_character_tags: frozenset[str]
    safety_status: Literal["pass", "fail", "unverified"] = Field(
        description=(
            "Caller observation only. A client-declared pass is not authoritative "
            "and cannot authorize ranking or skin use."
        )
    )


class InterventionCreate(LabRequest):
    batch_mass_g: float = Field(gt=0)
    brief: InterventionBriefCreate
    inventory: tuple[InterventionStockCreate, ...]
    candidates: tuple[InterventionCandidateCreate, ...]


class InterventionHypothesisCreate(LabRequest):
    brief_name: str = Field(min_length=1, max_length=255)
    observations: tuple[str, ...] = Field(min_length=1)
    family: str | None = None
    profile: str | None = None
    mode: Literal["pre_mix", "between_mix", "post_mix"] = "post_mix"
    forbidden_materials: frozenset[str] = frozenset()
    limit: int = Field(default=5, ge=1, le=20)


class PipetteProfileCreate(LabRequest):
    minimum_ul: float = Field(gt=0)
    increment_ul: float = Field(gt=0)
    maximum_single_step_ul: float | None = Field(default=None, gt=0)
    standard_uncertainty_ul: float = Field(default=0, ge=0)
    systematic_standard_uncertainty_ul: float = Field(default=0, ge=0)


class InterventionTrialPlanCreate(LabRequest):
    brief_name: str = Field(min_length=1, max_length=255)
    material: str = Field(min_length=1, max_length=255)
    bottle_total_mass_g: float = Field(gt=0)
    current_material_active_mass_g: float = Field(default=0, ge=0)
    stock_active_mass_fraction: float = Field(gt=0, le=1)
    stock_density_g_ml: float | None = Field(default=None, gt=0)
    target_active_ppm_w_w: float = Field(gt=0, le=1_000_000)
    threshold_matrix: Literal["ethanol", "unknown"] = "unknown"
    pipette: PipetteProfileCreate | None = None
    evaluation_attribute: str = Field(min_length=1, max_length=255)
    evaluation_times_seconds: tuple[int, ...] = Field(
        default=(0, 300, 1800, 7200, 14400), min_length=1
    )


__all__ = [name for name in globals() if name.endswith("Create")]
