"""Fuckup Registry — living failure memory for perfume formulation.

Every time a formula fails to match its intended character, the failure is
captured here with root cause analysis. The detector learns from these patterns
and flags repetition risks before the user mixes the bottle.

Architecture:
  models.py   — data models: FuckupEntry, FailurePattern, DetectionWarning
  patterns.py — known failure patterns (cross-referenced by detector)
  detector.py — checks new formulas against all known patterns
  registry.py — persistent store of fuckup entries (JSON-backed)
"""

from .detector import FuckupDetector, scan_formula
from .models import DetectionWarning, FuckupEntry, RootCauseCategory
from .registry import FuckupRegistry, get_registry

__all__ = [
    "FuckupEntry",
    "DetectionWarning",
    "RootCauseCategory",
    "FuckupDetector",
    "scan_formula",
    "FuckupRegistry",
    "get_registry",
]
