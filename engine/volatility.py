"""Volatility curve simulation — temporal fragrance evolution.

Implements Perplexity recommendation: "In-silico performance simulators to
estimate volatility curves, skin adhesion, and matrix effects."

Simulates how a formula's headspace composition changes over time using
vapor pressure data from the knowledge graph. Physics: simplified
Clausius-Clapeyron / Raoult's law evaporation model.

Output: time-series of relative headspace concentration per ingredient
at t = 0, 15min, 1hr, 4hr, 8hr, 24hr — showing top→heart→base evolution.
"""

import math
from dataclasses import dataclass, field

from engine.optimizer.models import _lookup_material, classify_note

# Standard time points (hours)
TIME_POINTS = [0, 0.25, 1, 4, 8, 24]
TIME_LABELS = ["0min", "15min", "1hr", "4hr", "8hr", "24hr"]

# Default VP estimates (Pa at 25°C) when KG data is missing
DEFAULT_VP = {
    "top": 2.0,
    "heart": 0.3,
    "base": 0.01,
}

# Temperature (skin surface, ~32°C)
SKIN_TEMP_K = 305.15
REF_TEMP_K = 298.15


@dataclass
class VolatilityProfile:
    """Time-series volatility data for a formula."""

    time_points: list[float] = field(default_factory=lambda: list(TIME_POINTS))
    time_labels: list[str] = field(default_factory=lambda: list(TIME_LABELS))
    # ingredient_name → [concentration at each time point]
    curves: dict[str, list[float]] = field(default_factory=dict)
    # Dominant note at each time point
    dominant_notes: list[str] = field(default_factory=list)
    # Top/heart/base balance at each time point
    note_evolution: list[dict[str, float]] = field(default_factory=list)


class VolatilityCurveSimulator:
    """Simulate fragrance temporal evolution using vapor pressure data."""

    def simulate(self, ingredients: dict[str, float]) -> VolatilityProfile:
        """Run volatility simulation for a formula.

        Args:
            ingredients: {name: percentage} mapping

        Returns:
            VolatilityProfile with per-ingredient curves and note evolution.
        """
        profile = VolatilityProfile()

        # Gather VP and MW for each ingredient
        mat_data = {}
        for name, pct in ingredients.items():
            mat = _lookup_material(name)
            note = classify_note(name)

            # Get vapor pressure (Pa)
            vp = None
            mw = None
            bp = None
            if mat:
                vp = mat.get("vp")
                mw = mat.get("mw")
                bp = mat.get("bp")

            # Estimate VP from boiling point if missing
            if vp is None and bp is not None and mw is not None:
                vp = self._estimate_vp_from_bp(bp, mw)

            # Fallback to note-based default
            if vp is None:
                vp = DEFAULT_VP.get(note, 0.3)

            # Adjust VP to skin temperature using Clausius-Clapeyron
            vp_skin = self._adjust_vp_to_skin(vp, mw)

            mat_data[name] = {
                "pct": pct,
                "vp_skin": vp_skin,
                "mw": mw or 200,
                "note": note,
            }

        # Simulate evaporation at each time point
        for t in TIME_POINTS:
            headspace = {}
            note_totals = {"top": 0.0, "heart": 0.0, "base": 0.0}

            for name, data in mat_data.items():
                # Exponential decay: C(t) = C0 * exp(-k * t)
                # k proportional to VP / MW (lighter, more volatile = faster)
                k = data["vp_skin"] / data["mw"] * 10
                remaining = data["pct"] * math.exp(-k * t)
                # Headspace concentration ∝ remaining × VP
                hs = remaining * data["vp_skin"]
                headspace[name] = hs
                note_totals[data["note"]] += hs

            # Normalize headspace to percentages
            total_hs = sum(headspace.values()) or 1.0
            for name in headspace:
                headspace[name] = round(headspace[name] / total_hs * 100, 2)

            # Store curves
            for name in ingredients:
                if name not in profile.curves:
                    profile.curves[name] = []
                profile.curves[name].append(headspace.get(name, 0))

            # Note balance at this time point
            total_notes = sum(note_totals.values()) or 1.0
            note_pct = {k: round(v / total_notes * 100, 1) for k, v in note_totals.items()}
            profile.note_evolution.append(note_pct)

            # Dominant note
            dominant = max(note_pct, key=note_pct.get)
            profile.dominant_notes.append(dominant)

        return profile

    def _estimate_vp_from_bp(self, bp_c: float, mw: float) -> float:
        """Rough VP estimate from boiling point using Clausius-Clapeyron.
        Assumes ΔH_vap ≈ 87 * Tb (Trouton's rule in J/mol)."""
        bp_k = bp_c + 273.15
        delta_h = 87 * bp_k  # J/mol (Trouton's rule)
        R = 8.314  # noqa: N806
        # VP at 25°C relative to BP (where VP ≈ 101325 Pa)
        ln_ratio = (delta_h / R) * (1 / bp_k - 1 / REF_TEMP_K)
        return 101325 * math.exp(ln_ratio)

    def _adjust_vp_to_skin(self, vp_25c: float, mw: float | None) -> float:
        """Adjust VP from 25°C to skin temp (32°C) using Clausius-Clapeyron."""
        if mw is None:
            mw = 200
        # Estimate ΔH_vap from MW (rough: heavier = higher ΔH)
        delta_h = 40000 + mw * 100  # J/mol, very approximate
        R = 8.314  # noqa: N806
        ln_ratio = (delta_h / R) * (1 / REF_TEMP_K - 1 / SKIN_TEMP_K)
        return vp_25c * math.exp(ln_ratio)

    def summary(self, profile: VolatilityProfile) -> dict:
        """Generate a human-readable summary of the volatility profile."""
        transitions = []
        for i in range(1, len(profile.dominant_notes)):
            if profile.dominant_notes[i] != profile.dominant_notes[i - 1]:
                transitions.append(
                    {
                        "from": profile.dominant_notes[i - 1],
                        "to": profile.dominant_notes[i],
                        "at": profile.time_labels[i],
                    }
                )

        # Find when each ingredient drops below 5% headspace
        fadeout = {}
        for name, curve in profile.curves.items():
            for i, val in enumerate(curve):
                if val < 5.0 and i > 0 and curve[0] >= 5.0:
                    fadeout[name] = profile.time_labels[i]
                    break
            else:
                if curve[-1] >= 5.0:
                    fadeout[name] = ">24hr"

        return {
            "transitions": transitions,
            "fadeout_times": fadeout,
            "opening_note": profile.dominant_notes[0],
            "drydown_note": profile.dominant_notes[-1],
            "note_evolution": {
                label: profile.note_evolution[i] for i, label in enumerate(profile.time_labels)
            },
        }
