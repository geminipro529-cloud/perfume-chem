"""Mixer API endpoints: pre-bonding analysis, mixing sequence, and instructions."""

import math
import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.mixer.instructions import InstructionGenerator
from engine.mixer.prebonding import PreBondingAnalyzer
from engine.mixer.sequencer import MixingSequencer

from app.api.deps import get_db
from app.services.engine_job_compatibility import (
    enqueue_formula_analysis_compatibility,
    enqueue_mixer_sequence_compatibility,
)
from app.services.validation_pipeline import (
    attach_validation,
    validate_formula,
    validate_pair,
)

router = APIRouter()


# ── Request / Response schemas ──

class FormulaInput(BaseModel):
    ingredients: dict[str, float] = Field(..., description="Material name → percentage")
    name: str = Field("Custom Formula", description="Formula name for protocol header")


class PhysicalMixingRowInput(BaseModel):
    row_id: str = Field(..., min_length=1)
    material: str = Field(..., min_length=1)
    raw_ul: float = Field(..., gt=0)
    basket: int | None = Field(None, ge=1, le=17)
    physical_stock_label: str = ""
    prepared_dilution_id: str | None = None
    operation: Literal["PRECHARGE", "DIRECT_ADD", "POSTCHARGE"] = "DIRECT_ADD"

    @field_validator("raw_ul")
    @classmethod
    def finite_raw_ul(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("raw_ul must be finite")
        return value


class MixingFormulaInput(BaseModel):
    ingredients: dict[str, float] | None = Field(
        None,
        description="Legacy material name to percentage mapping",
    )
    rows: list[PhysicalMixingRowInput] = Field(default_factory=list)
    name: str = Field("Custom Formula", description="Formula name for protocol header")

    @model_validator(mode="after")
    def exactly_one_input_mode(self):
        has_ingredients = bool(self.ingredients)
        has_rows = bool(self.rows)
        if has_ingredients == has_rows:
            raise ValueError("Provide exactly one of non-empty ingredients or rows")
        row_ids = [row.row_id for row in self.rows]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("rows require unique row_id values")
        return self


class PairInput(BaseModel):
    material_a: str
    material_b: str


class PairResult(BaseModel):
    classification: str
    reaction: str
    note: str
    validation: dict
    validation_compatibility: dict = Field(alias="_validation")


class PreBondingResult(BaseModel):
    must_prebond: list
    benefits: list
    keep_separate: list
    crystalline: list[str]
    validation: dict
    validation_compatibility: dict = Field(alias="_validation")


class MixingStep(BaseModel):
    order: int
    material: str
    pct: float
    phase: str
    rationale: str
    row_id: str | None = None
    physical_stock_label: str | None = None
    prepared_dilution_id: str | None = None
    raw_ul: float | None = None
    amount_unit: str | None = None
    basket: int | None = None
    operation: str | None = None


class SequenceResult(BaseModel):
    steps: list[MixingStep]
    prebond_steps: list
    dissolution_steps: list
    maceration_estimate_days: int
    compounding_authority: str
    authority_blockers: list[str] = Field(default_factory=list)
    ordering_contract: str
    mixing_timing: dict = Field(default_factory=dict)
    elapsed_time_scope: dict = Field(default_factory=dict)
    basket_checkpoints: list = Field(default_factory=list)
    raw_total_ul: float | None = None
    ordered_raw_total_ul: float | None = None
    validation: dict
    validation_compatibility: dict = Field(alias="_validation")


class InstructionResult(BaseModel):
    title: str
    total_materials: int
    total_pct: float | None
    raw_total_ul: float | None = None
    ordered_raw_total_ul: float | None = None
    phases: list
    maceration: str
    warnings: list[str]
    full_text: str
    mixing_timing: dict = Field(default_factory=dict)
    elapsed_time_scope: dict = Field(default_factory=dict)
    compounding_authority: str
    authority_blockers: list[str] = Field(default_factory=list)
    ordering_contract: str
    basket_checkpoints: list = Field(default_factory=list)
    validation: dict
    validation_compatibility: dict = Field(alias="_validation")


def _mixing_inputs(
    body: MixingFormulaInput,
) -> tuple[dict[str, float] | None, list[dict] | None, dict[str, float]]:
    """Keep physical rows intact while deriving percentages for validation."""

    if body.ingredients:
        return body.ingredients, None, body.ingredients

    rows = [row.model_dump() for row in body.rows]
    totals: dict[str, float] = {}
    for row in rows:
        material = str(row["material"])
        totals[material] = totals.get(material, 0.0) + float(row["raw_ul"])
    total_ul = sum(totals.values())
    validation_ingredients = {
        material: raw_ul / total_ul * 100.0
        for material, raw_ul in totals.items()
    }
    return None, rows, validation_ingredients


# ── Endpoints ──

@router.post("/analyze-pair", response_model=PairResult)
def analyze_pair(body: PairInput):
    """Analyze the chemical interaction between two materials."""
    report = validate_pair(body.material_a, body.material_b)
    analyzer = PreBondingAnalyzer()
    return attach_validation(
        analyzer.analyze_pair(body.material_a, body.material_b), report
    )


@router.post("/analyze-formula", response_model=PreBondingResult)
async def analyze_formula(
    body: FormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Analyze all pairs in a formula for pre-bonding requirements."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="mixer.analyze-formula",
        formula_name=body.name,
    )
    analyzer = PreBondingAnalyzer()
    result = analyzer.analyze_formula(body.ingredients)
    # Convert tuples to dicts for JSON serialization
    for key in ["must_prebond", "benefits", "keep_separate"]:
        result[key] = [
            {"material_a": a, "material_b": b, "details": d}
            for a, b, d in result[key]
        ]
    return attach_validation(result, report)


@router.post("/sequence", response_model=SequenceResult)
async def get_sequence(
    body: MixingFormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Compute optimal mixing order for a formula."""
    ingredients, rows, validation_ingredients = _mixing_inputs(body)
    report = await enqueue_mixer_sequence_compatibility(
        session,
        validate_formula(validation_ingredients),
        scope="mixer.sequence",
        formula_name=body.name,
        ingredients=ingredients,
        rows=rows,
    )
    sequencer = MixingSequencer()
    return attach_validation(
        sequencer.sequence(ingredients=ingredients, rows=rows), report
    )


@router.post("/instructions", response_model=InstructionResult)
async def get_instructions(
    body: MixingFormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Generate complete step-by-step mixing protocol."""
    ingredients, rows, validation_ingredients = _mixing_inputs(body)
    report = await enqueue_mixer_sequence_compatibility(
        session,
        validate_formula(validation_ingredients),
        scope="mixer.instructions",
        formula_name=body.name,
        ingredients=ingredients,
        rows=rows,
    )
    generator = InstructionGenerator()
    return attach_validation(
        generator.generate(
            ingredients=ingredients,
            rows=rows,
            formula_name=body.name,
        ),
        report,
    )
