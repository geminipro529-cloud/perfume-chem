"""FormulationOutcomeStore — service layer for recording and querying
formulation outcomes, pairwise preferences, and score calibrations.

This closes the feedback loop: system predicts → user creates → user rates → system learns.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_graph import (
    FormulationOutcome,
    PairwisePreference,
    ScoreCalibration,
)


class OutcomeStore:
    """CRUD + analytics for formulation outcomes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── FormulationOutcome CRUD ─────────────────────────────────────

    async def record_outcome(self, data: dict) -> FormulationOutcome:
        """Record a new formulation outcome."""
        outcome = FormulationOutcome(**data)
        self.session.add(outcome)
        await self.session.commit()
        await self.session.refresh(outcome)
        return outcome

    async def get_outcome(self, outcome_id: int) -> Optional[FormulationOutcome]:
        result = await self.session.execute(
            select(FormulationOutcome).where(FormulationOutcome.id == outcome_id)
        )
        return result.scalar_one_or_none()

    async def list_outcomes(
        self,
        skip: int = 0,
        limit: int = 50,
        formula_name: Optional[str] = None,
        min_rating: Optional[float] = None,
    ) -> list[FormulationOutcome]:
        query = select(FormulationOutcome)
        if formula_name:
            query = query.where(FormulationOutcome.formula_name == formula_name)
        if min_rating is not None:
            query = query.where(FormulationOutcome.rating_overall >= min_rating)
        query = query.order_by(FormulationOutcome.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_outcome(self, outcome_id: int, data: dict) -> Optional[FormulationOutcome]:
        outcome = await self.get_outcome(outcome_id)
        if not outcome:
            return None
        for key, value in data.items():
            if hasattr(outcome, key):
                setattr(outcome, key, value)
        await self.session.commit()
        await self.session.refresh(outcome)
        return outcome

    async def outcome_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(FormulationOutcome)
        )
        return result.scalar_one()

    # ── PairwisePreference CRUD ─────────────────────────────────────

    async def record_preference(self, data: dict) -> PairwisePreference:
        pref = PairwisePreference(**data)
        self.session.add(pref)
        await self.session.commit()
        await self.session.refresh(pref)
        return pref

    async def list_preferences(
        self,
        material: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PairwisePreference]:
        query = select(PairwisePreference)
        if material:
            query = query.where(
                (PairwisePreference.material_a == material) |
                (PairwisePreference.material_b == material)
            )
        query = query.order_by(PairwisePreference.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Score Calibration ───────────────────────────────────────────

    async def get_calibration(self, axis: str) -> Optional[ScoreCalibration]:
        result = await self.session.execute(
            select(ScoreCalibration).where(ScoreCalibration.scoring_axis == axis)
        )
        return result.scalar_one_or_none()

    async def upsert_calibration(
        self, axis: str, slope: float, intercept: float,
        r_squared: float, n_samples: int,
    ) -> ScoreCalibration:
        cal = await self.get_calibration(axis)
        if cal:
            cal.slope = slope
            cal.intercept = intercept
            cal.r_squared = r_squared
            cal.n_samples = n_samples
            cal.last_trained = datetime.now(timezone.utc)
        else:
            cal = ScoreCalibration(
                scoring_axis=axis,
                slope=slope,
                intercept=intercept,
                r_squared=r_squared,
                n_samples=n_samples,
                last_trained=datetime.now(timezone.utc),
            )
            self.session.add(cal)
        await self.session.commit()
        await self.session.refresh(cal)
        return cal

    async def all_calibrations(self) -> list[ScoreCalibration]:
        result = await self.session.execute(
            select(ScoreCalibration).order_by(ScoreCalibration.scoring_axis)
        )
        return list(result.scalars().all())

    # ── Analytics ───────────────────────────────────────────────────

    async def prediction_accuracy(self) -> dict:
        """Compare predicted scores vs actual ratings across all outcomes."""
        outcomes = await self.list_outcomes(limit=10000)
        axes = ["longevity", "sillage", "balance", "overall", "complexity"]
        stats: dict = {}

        for axis in axes:
            predicted_vals = []
            actual_vals = []
            for o in outcomes:
                predicted = (o.predicted_scores or {}).get(axis)
                actual = getattr(o, f"rating_{axis}", None)
                if predicted is not None and actual is not None:
                    predicted_vals.append(predicted)
                    actual_vals.append(actual)

            if len(predicted_vals) >= 2:
                mean_err = sum(
                    abs(p - a) for p, a in zip(predicted_vals, actual_vals)
                ) / len(predicted_vals)
                stats[axis] = {
                    "n_samples": len(predicted_vals),
                    "mean_absolute_error": round(mean_err, 2),
                }
            else:
                stats[axis] = {"n_samples": len(predicted_vals), "mean_absolute_error": None}

        return stats

    async def top_ingredients(self, min_outcomes: int = 3) -> list[dict]:
        """Find ingredients that appear most often in highly-rated formulations."""
        outcomes = await self.list_outcomes(min_rating=7.0, limit=10000)
        ingredient_scores: dict[str, list[float]] = {}

        for o in outcomes:
            rating = o.rating_overall or 0
            for name in (o.ingredients or {}):
                ingredient_scores.setdefault(name, []).append(rating)

        results = []
        for name, ratings in ingredient_scores.items():
            if len(ratings) >= min_outcomes:
                results.append({
                    "ingredient": name,
                    "appearances": len(ratings),
                    "avg_rating": round(sum(ratings) / len(ratings), 2),
                })

        return sorted(results, key=lambda x: x["avg_rating"], reverse=True)
