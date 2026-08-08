"""Fuckup Registry — living failure memory for perfume formulation."""

from .detector import FuckupDetector, scan_formula
from .models import DetectionWarning, FuckupEntry, RootCauseCategory
from .pre_mix_guard import (
    PreMixFinding,
    PreMixGuardError,
    PreMixGuardReport,
    evaluate_pre_mix_guard,
)
from .registry import FuckupRegistry, get_registry

__all__ = [
    "FuckupEntry",
    "DetectionWarning",
    "RootCauseCategory",
    "FuckupDetector",
    "scan_formula",
    "FuckupRegistry",
    "get_registry",
    "PreMixFinding",
    "PreMixGuardError",
    "PreMixGuardReport",
    "evaluate_pre_mix_guard",
]
