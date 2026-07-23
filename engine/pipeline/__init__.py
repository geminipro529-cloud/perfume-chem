"""Gate-first orchestration layer for formula simulation and release checks."""

from .formula_state import FormulaState, MaterialState, build_formula_state
from .gates import GateReport, GateResult, ReleaseGateConfig, gate_formula
from .oav_authority import (
    OAVAuthorityRequest,
    OAVAuthorityResult,
    OAVMaterialRow,
    OAVTimeWindowSummary,
    analyze_oav_authority,
)
from .oav_intelligence import OAVIntelligenceResult, analyze_oav_intelligence
from .robustness import RobustnessReport, audit_formula_robustness
from .simulator import SimulationFrame, simulate_formula

__all__ = [
    "FormulaState",
    "GateReport",
    "GateResult",
    "MaterialState",
    "OAVIntelligenceResult",
    "OAVAuthorityRequest",
    "OAVAuthorityResult",
    "OAVMaterialRow",
    "OAVTimeWindowSummary",
    "ReleaseGateConfig",
    "RobustnessReport",
    "SimulationFrame",
    "analyze_oav_intelligence",
    "analyze_oav_authority",
    "audit_formula_robustness",
    "build_formula_state",
    "gate_formula",
    "simulate_formula",
]
