"""Confidence scoring for formula predictions.

Implements Perplexity recommendation: "Every prediction should come with a
confidence band." Three confidence dimensions:

  data_confidence      — How complete are the material profiles?
  pairing_confidence   — Are ingredient pairs covered by known rules?
  prediction_confidence — How many similar formulas have observed outcomes?

Inspired by pharma CADD applicability-domain analysis.
"""

import math
import sqlite3

from engine.calibration.store import count_outcome_records
from engine.optimizer.models import (
    DB_PATH,
    _lookup_material,
    analyze_formula_rule_coverage,
)

# Fields that matter most for scoring accuracy
CRITICAL_FIELDS = [
    "mw", "bp", "vp", "clp", "odt",
    "carles_position", "sar_class", "odor_family",
    "roudnitska_function", "jellinek_quadrant",
]


class ConfidenceScorer:
    """Compute confidence bands for a formula's predicted scores."""

    def __init__(self):
        self._outcome_count: int | None = None

    def _count_outcomes(self) -> int:
        if self._outcome_count is not None:
            return self._outcome_count
        sqlite_count = 0
        if not DB_PATH.exists():
            sqlite_count = 0
        else:
            try:
                conn = sqlite3.connect(str(DB_PATH))
                sqlite_count = int(conn.execute(
                    "SELECT COUNT(*) FROM formulation_outcomes"
                ).fetchone()[0])
                conn.close()
            except Exception:
                sqlite_count = 0
        try:
            calibration_count = count_outcome_records()
        except Exception:
            calibration_count = 0
        self._outcome_count = sqlite_count + calibration_count
        return self._outcome_count

    # ── Per-material data confidence ──

    def material_data_confidence(self, name: str) -> float:
        """0-100: how complete is this material's profile?"""
        mat = _lookup_material(name)
        if mat is None:
            return 0.0
        filled = sum(1 for f in CRITICAL_FIELDS if mat.get(f) is not None)
        return round(filled / len(CRITICAL_FIELDS) * 100, 1)

    # ── Formula-level confidences ──

    def data_confidence(self, ingredients: dict[str, float]) -> float:
        """Average data completeness across all ingredients. 0-100."""
        if not ingredients:
            return 0.0
        scores = [self.material_data_confidence(n) for n in ingredients]
        return round(sum(scores) / len(scores), 1)

    def pairing_confidence(self, ingredients: dict[str, float]) -> float:
        """What fraction of ingredient pairs are covered by known rules? 0-100.

        Now weighted by effect magnitude — a pair with magnitude 3.0 synergy
        contributes more than a magnitude 1.0 pairing.
        """
        names = list(ingredients)
        if len(names) < 2:
            return 0.0
        coverage = analyze_formula_rule_coverage(names)
        total_pairs = int(coverage["total_pairs"])
        covered_pairs = len(coverage["covered_pairs"])
        total_mag = float(coverage.get("total_axis_magnitude", 0.0))

        # Base coverage ratio (classic)
        base_score = (covered_pairs / total_pairs * 100) if total_pairs else 0.0

        # Effect bonus: magnitude per pair
        # If every pair had max synergy (3.0), total_mag = total_pairs * 3.0
        # Scale: 0-20 bonus points
        max_mag = max(total_pairs * 3.0, 1.0)
        mag_ratio = total_mag / max_mag
        mag_bonus = min(20.0, mag_ratio * 25.0)

        return round(min(100.0, base_score + mag_bonus), 1)

    def prediction_confidence(self, ingredients: dict[str, float]) -> float:
        """How many observed outcomes exist? More data = higher confidence.
        0-100, logarithmic scale (10 outcomes=50%, 100=80%, 500+=95%)."""
        return self.prediction_confidence_from_count(self._count_outcomes())

    @staticmethod
    def prediction_confidence_from_count(outcome_count: int) -> float:
        if outcome_count <= 0:
            return 5.0  # Minimal baseline (system is untested)
        # Log scale: ~50 at n=10, ~80 at n=100, ~95 at n=500
        return round(min(95, 18.5 * math.log(outcome_count + 1)), 1)

    def score(self, ingredients: dict[str, float]) -> dict:
        """Full confidence report for a formula."""
        dc = self.data_confidence(ingredients)
        pc = self.pairing_confidence(ingredients)
        prc = self.prediction_confidence(ingredients)
        overall = round((dc * 0.4 + pc * 0.3 + prc * 0.3), 1)

        return {
            "data_confidence": dc,
            "pairing_confidence": pc,
            "prediction_confidence": prc,
            "overall_confidence": overall,
            "confidence_grade": _grade(overall),
            "per_material": {
                name: self.material_data_confidence(name)
                for name in ingredients
            },
        }

    def outcome_readiness(self) -> dict:
        """Summarize how ready the system is for empirical calibration."""
        outcome_count = self._count_outcomes()
        prediction_confidence = self.prediction_confidence_from_count(outcome_count)
        return {
            "outcome_count": outcome_count,
            "prediction_confidence": prediction_confidence,
            "confidence_grade": _grade(prediction_confidence),
            "calibration_ready": outcome_count >= 3,
            "calibration_practical": outcome_count >= 10,
            "notes": [
                "At least 3 outcomes are needed for a first regression fit.",
                "10+ outcomes is the point where calibration starts to become useful.",
                "The current prediction confidence still depends only on recorded outcomes.",
            ],
        }


def _grade(score: float) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    if score >= 25:
        return "LOW"
    return "VERY_LOW"
