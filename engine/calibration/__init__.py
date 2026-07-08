"""Calibration data models for observed wear tests and panel feedback."""

import importlib.util
from pathlib import Path

from .hashing import formula_hash_from_record, stable_formula_hash
from .models import CalibrationRecord, PanelResult, WearTestObservation
from .store import append_record, count_outcome_records, load_records, summarize_records

_LEGACY_PATH = Path(__file__).resolve().parents[1] / "calibration.py"
_LEGACY_SPEC = importlib.util.spec_from_file_location("engine._legacy_score_calibration", _LEGACY_PATH)
if _LEGACY_SPEC is not None and _LEGACY_SPEC.loader is not None:
    _legacy = importlib.util.module_from_spec(_LEGACY_SPEC)
    _LEGACY_SPEC.loader.exec_module(_legacy)
    CalibrationReport = _legacy.CalibrationReport
    CalibrationResult = _legacy.CalibrationResult
    ScoreCalibrationPipeline = _legacy.ScoreCalibrationPipeline
    load_outcome_records = _legacy.load_outcome_records

__all__ = [
    "CalibrationRecord",
    "CalibrationReport",
    "CalibrationResult",
    "PanelResult",
    "ScoreCalibrationPipeline",
    "WearTestObservation",
    "append_record",
    "count_outcome_records",
    "formula_hash_from_record",
    "load_outcome_records",
    "load_records",
    "stable_formula_hash",
    "summarize_records",
]
