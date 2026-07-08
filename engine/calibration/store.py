"""JSONL storage helpers for calibration observations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from .models import CalibrationRecord


DEFAULT_CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "data" / "calibration" / "wear_tests.jsonl"


def default_calibration_path() -> Path:
    override = os.environ.get("PERFUME_CALIBRATION_PATH")
    return Path(override) if override else DEFAULT_CALIBRATION_PATH


def load_records(path: str | Path | None = None) -> list[CalibrationRecord]:
    target = Path(path) if path is not None else default_calibration_path()
    if not target.exists():
        return []
    records: list[CalibrationRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(CalibrationRecord.from_dict(json.loads(line)))
    return records


def append_record(record: CalibrationRecord, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else default_calibration_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
    return target


def summarize_records(
    records: Iterable[CalibrationRecord],
    *,
    formula_hash: str | None = None,
) -> dict[str, float | int | bool | None]:
    rows = [
        record for record in records
        if formula_hash is None or record.formula_hash == formula_hash
    ]
    panel_count = sum(len(r.panel_results) for r in rows)
    obs_count = sum(len(r.observations) for r in rows)
    intensities = [
        obs.perceived_intensity_0_10
        for record in rows
        for obs in record.observations
        if obs.perceived_intensity_0_10 is not None
    ]
    projections = [
        obs.projection_cm
        for record in rows
        for obs in record.observations
        if obs.projection_cm is not None
    ]
    intensity_biases = [
        obs.perceived_intensity_0_10 - float(record.predicted["intensity_0_10"])
        for record in rows
        for obs in record.observations
        if obs.perceived_intensity_0_10 is not None
        and record.predicted.get("intensity_0_10") is not None
    ]
    projection_biases = [
        obs.projection_cm - float(record.predicted["projection_cm"])
        for record in rows
        for obs in record.observations
        if obs.projection_cm is not None
        and record.predicted.get("projection_cm") is not None
    ]
    return {
        "formula_records": len(rows),
        "wear_observations": obs_count,
        "panel_results": panel_count,
        "calibration_ready": obs_count >= 3 or panel_count >= 10,
        "calibration_practical": obs_count >= 10 or panel_count >= 30,
        "mean_intensity_0_10": _mean(intensities),
        "mean_projection_cm": _mean(projections),
        "mean_intensity_bias_0_10": _mean(intensity_biases),
        "mean_projection_bias_cm": _mean(projection_biases),
    }


def count_outcome_records(path: str | Path | None = None) -> int:
    return len(load_records(path))


def _mean(values: list[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 3)
