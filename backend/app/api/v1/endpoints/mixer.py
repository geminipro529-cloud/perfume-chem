"""Mixer API endpoints: pre-bonding analysis, mixing sequence, and instructions."""

import sys
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel, Field

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.mixer.prebonding import PreBondingAnalyzer
from engine.mixer.sequencer import MixingSequencer
from engine.mixer.instructions import InstructionGenerator
from app.services.validation_pipeline import validate_formula, validate_pair, attach_validation

router = APIRouter()


# ── Request / Response schemas ──

class FormulaInput(BaseModel):
    ingredients: dict[str, float] = Field(..., description="Material name → percentage")
    name: str = Field("Custom Formula", description="Formula name for protocol header")


class PairInput(BaseModel):
    material_a: str
    material_b: str


class PairResult(BaseModel):
    classification: str
    reaction: str
    note: str


class PreBondingResult(BaseModel):
    must_prebond: list
    benefits: list
    keep_separate: list
    crystalline: list[str]


class MixingStep(BaseModel):
    order: int
    material: str
    pct: float
    phase: str
    rationale: str


class SequenceResult(BaseModel):
    steps: list[MixingStep]
    prebond_steps: list
    dissolution_steps: list
    maceration_estimate_days: int


class InstructionResult(BaseModel):
    title: str
    total_materials: int
    total_pct: float
    phases: list
    maceration: str
    warnings: list[str]
    full_text: str


# ── Endpoints ──

@router.post("/analyze-pair", response_model=PairResult)
def analyze_pair(body: PairInput):
    """Analyze the chemical interaction between two materials."""
    validate_pair(body.material_a, body.material_b)
    analyzer = PreBondingAnalyzer()
    return analyzer.analyze_pair(body.material_a, body.material_b)


@router.post("/analyze-formula", response_model=PreBondingResult)
def analyze_formula(body: FormulaInput):
    """Analyze all pairs in a formula for pre-bonding requirements."""
    validate_formula(body.ingredients)
    analyzer = PreBondingAnalyzer()
    result = analyzer.analyze_formula(body.ingredients)
    # Convert tuples to dicts for JSON serialization
    for key in ["must_prebond", "benefits", "keep_separate"]:
        result[key] = [
            {"material_a": a, "material_b": b, "details": d}
            for a, b, d in result[key]
        ]
    return result


@router.post("/sequence", response_model=SequenceResult)
def get_sequence(body: FormulaInput):
    """Compute optimal mixing order for a formula."""
    validate_formula(body.ingredients)
    sequencer = MixingSequencer()
    return sequencer.sequence(body.ingredients)


@router.post("/instructions", response_model=InstructionResult)
def get_instructions(body: FormulaInput):
    """Generate complete step-by-step mixing protocol."""
    validate_formula(body.ingredients)
    generator = InstructionGenerator()
    return generator.generate(body.ingredients, body.name)
