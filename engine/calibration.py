"""Score calibration pipeline — learn correction factors from user feedback.

After enough FormulationOutcome data, linear regression learns how to
adjust each scoring axis so predictions match reality.

Uses the ScoreCalibration model (slope, intercept, r_squared, n_samples)
stored in the database via OutcomeStore.

Workflow:
  1. Pull all FormulationOutcome rows with both predicted_scores and ratings
  2. For each axis, collect (predicted, actual) pairs
  3. Fit y = slope*x + intercept via least-squares
  4. Persist calibration coefficients
  5. Apply calibration to future predictions
"""

import json
import sqlite3
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from engine.optimizer.models import DB_PATH


# Axis mapping: scoring axis → outcome column name
AXIS_TO_RATING = {
    "longevity": "rating_longevity",
    "sillage": "rating_sillage",
    "balance": "rating_balance",
}

CALIBRATION_MIN_SAMPLES = 3


@dataclass
class CalibrationResult:
    axis: str
    slope: float
    intercept: float
    r_squared: float
    n_samples: int
    mean_error: float  # mean absolute error

    def as_dict(self) -> dict:
        return {
            "axis": self.axis,
            "slope": self.slope,
            "intercept": self.intercept,
            "r_squared": self.r_squared,
            "n_samples": self.n_samples,
            "mean_error": self.mean_error,
        }


@dataclass
class CalibrationReport:
    results: list[CalibrationResult] = field(default_factory=list)
    total_outcomes_used: int = 0
    axes_calibrated: int = 0

    def summary(self) -> list[str]:
        lines = [f"Calibration trained on {self.total_outcomes_used} outcomes"]
        for r in self.results:
            direction = "overestimates" if r.slope < 1.0 else "underestimates"
            lines.append(
                f"  {r.axis}: y = {r.slope:.3f}x + {r.intercept:.2f} "
                f"(R²={r.r_squared:.3f}, n={r.n_samples}, MAE={r.mean_error:.1f}) "
                f"— engine {direction}"
            )
        return lines

    def as_dict(self) -> dict:
        return {
            "total_outcomes_used": self.total_outcomes_used,
            "axes_calibrated": self.axes_calibrated,
            "results": [r.as_dict() for r in self.results],
        }


class ScoreCalibrationPipeline:
    """Learn and apply score corrections from FormulationOutcome data."""

    def __init__(self):
        self._calibrations: dict[str, CalibrationResult] | None = None

    def train(self) -> CalibrationReport:
        """Pull outcome data from DB and fit per-axis corrections."""
        report = CalibrationReport()

        if not DB_PATH.exists():
            return report

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT predicted_scores, rating_longevity, rating_sillage, "
                "rating_balance, rating_overall FROM formulation_outcomes "
                "WHERE predicted_scores IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()

        return self.train_from_rows([dict(row) for row in rows])

    def train_from_records(self, records: Iterable[dict]) -> CalibrationReport:
        """Train calibration coefficients from standalone record dicts."""
        return self._train_from_rows(list(records))

    def train_from_rows(self, rows: Iterable[dict]) -> CalibrationReport:
        """Train calibration coefficients from DB rows or similar records."""
        normalized = [dict(row) if not isinstance(row, dict) else row for row in rows]
        return self._train_from_rows(normalized)

    def calibrate(self, raw_scores: dict[str, float]) -> dict[str, float]:
        """Apply learned corrections to raw scores."""
        if self._calibrations is None:
            self._load_from_db()

        calibrated = dict(raw_scores)
        for axis, cal in (self._calibrations or {}).items():
            if axis in calibrated and cal.r_squared >= 0.3:
                corrected = cal.slope * calibrated[axis] + cal.intercept
                calibrated[axis] = round(max(0, min(100, corrected)), 1)

        # Recalculate total if present
        if "total" in calibrated:
            non_total = {k: v for k, v in calibrated.items() if k != "total"}
            if non_total:
                calibrated["total"] = round(
                    sum(non_total.values()) / len(non_total), 1
                )

        return calibrated

    def calibration_readiness(self, records: Iterable[dict] | None = None) -> dict:
        """Summarize whether the current record set is usable for calibration."""
        if records is None:
            report = self.train()
            return {
                "source": "database",
                "total_outcomes_used": report.total_outcomes_used,
                "axes_calibrated": report.axes_calibrated,
                "usable_axes": [r.axis for r in report.results],
                "minimum_samples_per_axis": CALIBRATION_MIN_SAMPLES,
                "ready": report.axes_calibrated > 0,
            }

        rows = list(records)
        summary = {}
        ready_axes = []
        for axis, rating_col in AXIS_TO_RATING.items():
            predicted, actual = _collect_axis_samples(rows, axis, rating_col)
            sample_count = len(predicted)
            summary[axis] = {
                "samples": sample_count,
                "trainable": sample_count >= CALIBRATION_MIN_SAMPLES,
            }
            if sample_count >= CALIBRATION_MIN_SAMPLES:
                ready_axes.append(axis)
        return {
            "source": "standalone_records",
            "total_outcomes_used": len(rows),
            "axes": summary,
            "minimum_samples_per_axis": CALIBRATION_MIN_SAMPLES,
            "ready_axes": ready_axes,
            "ready": bool(ready_axes),
        }

    def _load_from_db(self):
        """Load previously trained calibrations from DB."""
        self._calibrations = {}
        if not DB_PATH.exists():
            return
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT scoring_axis, slope, intercept, r_squared, n_samples "
                "FROM score_calibrations"
            ).fetchall()
            conn.close()
            for row in rows:
                self._calibrations[row["scoring_axis"]] = CalibrationResult(
                    axis=row["scoring_axis"],
                    slope=row["slope"],
                    intercept=row["intercept"],
                    r_squared=row["r_squared"],
                    n_samples=row["n_samples"],
                    mean_error=0.0,
                )
        except Exception:
            pass

    def _train_from_rows(self, rows: list[dict]) -> CalibrationReport:
        report = CalibrationReport()
        if not rows:
            return report

        self._calibrations = {}
        for axis, rating_col in AXIS_TO_RATING.items():
            predicted, actual = _collect_axis_samples(rows, axis, rating_col)
            if len(predicted) < CALIBRATION_MIN_SAMPLES:
                continue
            result = _linear_regression(axis, predicted, actual)
            self._calibrations[axis] = result
            report.results.append(result)

        report.total_outcomes_used = len(rows)
        report.axes_calibrated = len(report.results)
        return report


def _parse_predicted_scores(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _collect_axis_samples(rows: list[dict], axis: str, rating_col: str) -> tuple[list[float], list[float]]:
    predicted = []
    actual = []
    for row in rows:
        scores = _parse_predicted_scores(_row_value(row, "predicted_scores"))
        if not scores:
            continue
        pred_val = scores.get(axis)
        actual_val = _row_value(row, rating_col)
        if pred_val is None or actual_val is None:
            continue
        predicted.append(float(pred_val))
        actual.append(float(actual_val) * 10)
    return predicted, actual


def _row_value(row, key: str):
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)


def load_outcome_records(source: str | Path) -> list[dict]:
    """Load standalone outcome records from JSON or JSONL files/directories."""
    path = Path(source)
    if not path.exists():
        return []

    if path.is_dir():
        records: list[dict] = []
        seen: set[Path] = set()
        for candidate in sorted(path.rglob("outcome_record.json")):
            if candidate not in seen:
                records.extend(load_outcome_records(candidate))
                seen.add(candidate)
        for candidate in sorted(path.rglob("*.jsonl")):
            if candidate not in seen:
                records.extend(load_outcome_records(candidate))
                seen.add(candidate)
        return records

    if path.suffix.lower() == ".jsonl":
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    if path.suffix.lower() == ".json":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(value, dict) and isinstance(value.get("records"), list):
            return [v for v in value["records"] if isinstance(v, dict)]
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        if isinstance(value, dict) and (
            value.get("formula_name") is not None or value.get("predicted_scores") is not None
        ):
            return [value]
    return []


def _linear_regression(
    axis: str, x: list[float], y: list[float]
) -> CalibrationResult:
    """Simple OLS: y = slope*x + intercept."""
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return CalibrationResult(axis, 1.0, 0.0, 0.0, n, 0.0)

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R²
    y_mean = sum_y / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # MAE
    mean_error = sum(abs(yi - (slope * xi + intercept)) for xi, yi in zip(x, y)) / n

    return CalibrationResult(
        axis=axis,
        slope=round(slope, 6),
        intercept=round(intercept, 4),
        r_squared=round(max(0, r_squared), 4),
        n_samples=n,
        mean_error=round(mean_error, 2),
    )
