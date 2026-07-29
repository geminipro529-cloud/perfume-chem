"""Coded sensory evaluation ledger.

Stores time-resolved blind evaluations with separate identity ratings per
phase (opening, heart, drydown). Each sample is assigned a random 3-letter
code for blinding, and observations are recorded against that code.

Usage::

    from engine.sensory.ledger import SensoryTrial, SensorySample, SensoryObservation

    trial = SensoryTrial("Iris v2 vs v3", "sample_ref_001", ["Alice", "Bob"])
    sample = SensorySample(
        sample_id="550e8400-e29b-41d4-a716-446655440000",
        formula_id="iris_v2",
        batch_id="batch_001",
        code="XQP",
    )
    trial.add_sample(sample)
    trial.record_observation(SensoryObservation(
        observation_id="660e8400-e29b-41d4-a716-446655440001",
        sample_id=sample.sample_id,
        assessor="Alice",
        time_seconds=300.0,
        opening_identity=4.0,
        heart_identity=3.5,
        drydown_identity=3.0,
        transition_quality=4.0,
        texture=3.5,
        diffusion=4.0,
        longevity=3.0,
        overall_similarity=3.5,
        preference=4.0,
    ))
    summary = trial.summarize(sample.sample_id)
    mismatches = trial.detect_mismatch("candidate_id", "reference_id")
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from typing import Any

from engine.domain_errors import LegacyWriteProhibitedError

# ── Constants ────────────────────────────────────────────────────────────────────

TIME_POINTS: list[float] = [0, 300, 1800, 7200, 14400, 28800, 86400]
"""Standard evaluation time points in seconds:

* 0 s      — opening / first blast
* 300 s    — 5 min  (top-note burn-off)
* 1800 s   — 30 min (early heart)
* 7200 s   — 2 hr   (heart)
* 14400 s  — 4 hr   (late heart / early drydown)
* 28800 s  — 8 hr   (drydown)
* 86400 s  — 24 hr  (extended drydown)
"""

_OFFENSIVE_CODES: frozenset[str] = frozenset(
    {
        "FUK",
        "DIK",
        "ASS",
        "CUM",
        "SEX",
        "SUK",
        "FAG",
        "KKK",
        "WTF",
        "STD",
        "POO",
        "PEE",
        "CRP",
        "BUM",
        "GAY",
        "NGR",
        "CNT",
        "CLT",
        "KNT",
        "DUM",
        "TWT",
        "FUC",
        "SHI",
        "BIT",
    }
)
"""Three-letter codes that are excluded from generation."""


# ── Dataclasses ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SensorySample:
    """A single blinded sample prepared for sensory evaluation.

    Parameters
    ----------
    sample_id:
        UUID string identifying this sample.
    formula_id:
        Identifier for the formula being evaluated.
    batch_id:
        Identifier for the physical batch.
    code:
        Random 3-letter uppercase blinding code.
    application_mass_g:
        Mass of fragrance applied to the substrate, in grams.
    substrate:
        Substrate type. One of ``"blotter"``, ``"skin_forearm"``,
        ``"skin_wrist"``, ``"mouillette"``.
    room_temperature_c:
        Room temperature at time of preparation, in °C.
    room_humidity_pct:
        Room relative humidity at time of preparation, in percent.
    prepared_at:
        ISO 8601 datetime string when the sample was prepared.
    """

    sample_id: str
    formula_id: str
    batch_id: str
    code: str
    application_mass_g: float = 0.01
    substrate: str = "blotter"
    room_temperature_c: float = 22.0
    room_humidity_pct: float = 50.0
    prepared_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "formula_id": self.formula_id,
            "batch_id": self.batch_id,
            "code": self.code,
            "application_mass_g": self.application_mass_g,
            "substrate": self.substrate,
            "room_temperature_c": self.room_temperature_c,
            "room_humidity_pct": self.room_humidity_pct,
            "prepared_at": self.prepared_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorySample:
        return cls(
            sample_id=str(data["sample_id"]),
            formula_id=str(data["formula_id"]),
            batch_id=str(data["batch_id"]),
            code=str(data["code"]),
            application_mass_g=float(data.get("application_mass_g") or 0.01),
            substrate=str(data.get("substrate") or "blotter"),
            room_temperature_c=float(data.get("room_temperature_c") or 22.0),
            room_humidity_pct=float(data.get("room_humidity_pct") or 50.0),
            prepared_at=str(data["prepared_at"]) if data.get("prepared_at") else None,
        )


@dataclass(frozen=True, slots=True)
class SensoryObservation:
    """A single time-resolved observation from one assessor.

    Parameters
    ----------
    observation_id:
        UUID string identifying this observation.
    sample_id:
        UUID string referencing the :class:`SensorySample`.
    assessor:
        Name or identifier of the assessor.
    time_seconds:
        Time elapsed since application, in seconds.
    opening_identity:
        How well the opening matches the reference (1–5).
    heart_identity:
        How well the heart matches the reference (1–5).
    drydown_identity:
        How well the drydown matches the reference (1–5).
    transition_quality:
        How smooth the phase transitions are (1–5).
    texture:
        How pleasing the tactile sensation is (1–5).
    diffusion:
        How well the fragrance projects (1–5).
    longevity:
        How long the fragrance lasts (1–5).
    off_notes:
        Description of any unpleasant notes. Empty string if none.
    overall_similarity:
        Overall similarity to the reference (1–5).
    preference:
        Personal liking (1–5).
    notes:
        Free-text notes from the assessor.
    """

    observation_id: str
    sample_id: str
    assessor: str
    time_seconds: float
    opening_identity: float
    heart_identity: float
    drydown_identity: float
    transition_quality: float
    texture: float
    diffusion: float
    longevity: float
    off_notes: str = ""
    overall_similarity: float = 3.0
    preference: float = 3.0
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "sample_id": self.sample_id,
            "assessor": self.assessor,
            "time_seconds": self.time_seconds,
            "opening_identity": self.opening_identity,
            "heart_identity": self.heart_identity,
            "drydown_identity": self.drydown_identity,
            "transition_quality": self.transition_quality,
            "texture": self.texture,
            "diffusion": self.diffusion,
            "longevity": self.longevity,
            "off_notes": self.off_notes,
            "overall_similarity": self.overall_similarity,
            "preference": self.preference,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensoryObservation:
        return cls(
            observation_id=str(data["observation_id"]),
            sample_id=str(data["sample_id"]),
            assessor=str(data["assessor"]),
            time_seconds=float(data["time_seconds"]),
            opening_identity=float(data["opening_identity"]),
            heart_identity=float(data["heart_identity"]),
            drydown_identity=float(data["drydown_identity"]),
            transition_quality=float(data["transition_quality"]),
            texture=float(data["texture"]),
            diffusion=float(data["diffusion"]),
            longevity=float(data["longevity"]),
            off_notes=str(data.get("off_notes") or ""),
            overall_similarity=float(data.get("overall_similarity") or 3.0),
            preference=float(data.get("preference") or 3.0),
            notes=str(data.get("notes") or ""),
        )


# ── Code generation ──────────────────────────────────────────────────────────────


def generate_trial_codes(count: int) -> list[str]:
    """Generate ``count`` random 3-letter uppercase blinding codes.

    No duplicates are produced, and offensive combinations (e.g. ``"FUK"``,
    ``"DIK"``) are excluded.

    Parameters
    ----------
    count:
        Number of codes to generate.

    Returns
    -------
    list[str]:
        A list of unique 3-letter uppercase codes.

    Raises
    ------
    ValueError:
        If ``count`` exceeds the number of possible non-offensive codes.
    """
    letters = string.ascii_uppercase
    all_possible = 26**3
    max_safe = all_possible - len(_OFFENSIVE_CODES)
    if count > max_safe:
        raise ValueError(
            f"Cannot generate {count} unique codes; "
            f"only {max_safe} non-offensive combinations available."
        )

    codes: set[str] = set()
    while len(codes) < count:
        code = "".join(random.choices(letters, k=3))
        if code not in _OFFENSIVE_CODES:
            codes.add(code)
    return list(codes)


# ── Trial ────────────────────────────────────────────────────────────────────────


class SensoryTrial:
    """A structured sensory trial comparing one or more samples.

    Manages blinded samples, time-resolved observations, summary statistics,
    and mismatch detection against a reference.

    Parameters
    ----------
    trial_name:
        Human-readable name for this trial (e.g. ``"Iris v2 vs v3"``).
    reference_sample_id:
        The ``sample_id`` of the reference sample that other samples are
        compared against.
    assessors:
        List of assessor names or identifiers participating in this trial.
    """

    def __init__(
        self,
        trial_name: str,
        reference_sample_id: str,
        assessors: list[str],
    ) -> None:
        self.trial_name: str = trial_name
        self.reference_sample_id: str = reference_sample_id
        self.assessors: list[str] = list(assessors)
        self._samples: dict[str, SensorySample] = {}
        self._observations: list[SensoryObservation] = []

    # ── mutation ────────────────────────────────────────────────────────────

    def add_sample(self, sample: SensorySample) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del sample
        raise LegacyWriteProhibitedError(
            "SensoryTrial is read-only; persist samples through LabService"
        )

    def record_observation(self, obs: SensoryObservation) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del obs
        raise LegacyWriteProhibitedError(
            "SensoryTrial is read-only; persist observations through LabService"
        )

    # ── queries ─────────────────────────────────────────────────────────────

    def get_observations_for_sample(self, sample_id: str) -> list[SensoryObservation]:
        """Return all observations for a given sample."""
        return [o for o in self._observations if o.sample_id == sample_id]

    def get_observations_at_time(self, time_seconds: float) -> list[SensoryObservation]:
        """Return all observations recorded at a specific time point."""
        return [o for o in self._observations if o.time_seconds == time_seconds]

    def summarize(self, sample_id: str) -> dict[str, float]:
        """Compute average identity and similarity scores for a sample.

        Returns a dict with keys ``avg_opening``, ``avg_heart``,
        ``avg_drydown``, ``avg_overall``. Returns 0.0 for any axis that
        has no observations.
        """
        obs = self.get_observations_for_sample(sample_id)
        if not obs:
            return {
                "avg_opening": 0.0,
                "avg_heart": 0.0,
                "avg_drydown": 0.0,
                "avg_overall": 0.0,
            }

        n = len(obs)
        return {
            "avg_opening": sum(o.opening_identity for o in obs) / n,
            "avg_heart": sum(o.heart_identity for o in obs) / n,
            "avg_drydown": sum(o.drydown_identity for o in obs) / n,
            "avg_overall": sum(o.overall_similarity for o in obs) / n,
        }

    def detect_mismatch(
        self,
        candidate_id: str,
        reference_id: str,
        threshold: float = 1.0,
    ) -> list[str]:
        """Detect time points where a candidate differs significantly from the
        reference.

        For each time point that has observations for *both* the candidate and
        the reference, the mean ``overall_similarity`` is compared. If the
        absolute difference exceeds ``threshold``, that time point is flagged.

        Parameters
        ----------
        candidate_id:
            ``sample_id`` of the candidate sample.
        reference_id:
            ``sample_id`` of the reference sample.
        threshold:
            Maximum allowed mean difference before a mismatch is reported.

        Returns
        -------
        list[str]:
            Human-readable descriptions of mismatched time points.
        """
        mismatches: list[str] = []

        for tp in TIME_POINTS:
            cand_obs = [
                o
                for o in self._observations
                if o.sample_id == candidate_id and o.time_seconds == tp
            ]
            ref_obs = [
                o
                for o in self._observations
                if o.sample_id == reference_id and o.time_seconds == tp
            ]
            if not cand_obs or not ref_obs:
                continue

            cand_mean = sum(o.overall_similarity for o in cand_obs) / len(cand_obs)
            ref_mean = sum(o.overall_similarity for o in ref_obs) / len(ref_obs)

            if abs(cand_mean - ref_mean) > threshold:
                mismatches.append(
                    f"t={tp:.0f}s: candidate={cand_mean:.2f} vs "
                    f"reference={ref_mean:.2f} (diff={abs(cand_mean - ref_mean):.2f})"
                )

        return mismatches

    # ── serialisation ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire trial to a JSON-compatible dict."""
        return {
            "trial_name": self.trial_name,
            "reference_sample_id": self.reference_sample_id,
            "assessors": self.assessors,
            "samples": [s.as_dict() for s in self._samples.values()],
            "observations": [o.as_dict() for o in self._observations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensoryTrial:
        """Reconstruct a trial from a dict produced by :meth:`to_dict`."""
        return cls.from_records(
            trial_name=str(data["trial_name"]),
            reference_sample_id=str(data["reference_sample_id"]),
            assessors=list(str(a) for a in data.get("assessors", [])),
            samples=[
                SensorySample.from_dict(sample)
                for sample in data.get("samples", [])
            ],
            observations=[
                SensoryObservation.from_dict(observation)
                for observation in data.get("observations", [])
            ],
        )

    @classmethod
    def from_records(
        cls,
        *,
        trial_name: str,
        reference_sample_id: str,
        assessors: list[str],
        samples: list[SensorySample],
        observations: list[SensoryObservation],
    ) -> SensoryTrial:
        """Hydrate a read-only projection without invoking public mutators."""
        trial = cls(trial_name, reference_sample_id, assessors)
        trial._samples = {sample.sample_id: sample for sample in samples}
        trial._observations = list(observations)
        return trial


__all__ = [
    "TIME_POINTS",
    "SensorySample",
    "SensoryObservation",
    "SensoryTrial",
    "generate_trial_codes",
]
