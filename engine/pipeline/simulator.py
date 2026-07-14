"""Time-window simulation over FormulaState.

This module intentionally starts with a conservative evaporation approximation
and explicit source labels.  It gives release gates a stable time-series API
now, while leaving room for a stricter finite-film/UNIFAC backend later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.receptor.binding import ligands_from_family, or_occupancy
from engine.biology.genetics import apply_polymorphism  # OR genotype modulation
from engine.delivery.spray import droplet_distribution  # spray droplet physics


DEFAULT_WINDOWS: tuple[tuple[str, float], ...] = (
    ("opening", 0.0),
    ("top", 300.0),
    ("heart", 1800.0),
    ("late_heart", 7200.0),
    ("drydown", 14400.0),
)


@dataclass(frozen=True, slots=True)
class SimulationFrame:
    label: str
    t_seconds: float
    state: FormulaState
    receptor_activation: dict[str, float] = field(default_factory=dict)
    receptor_source: str = "family_prior_proxy"

    def dominant_oav(self, limit: int = 8) -> list[dict]:
        rows = sorted(
            self.state.materials,
            key=lambda m: (m.oav or 0.0),
            reverse=True,
        )
        return [
            {
                "material": m.name,
                "oav": round(m.oav or 0.0, 3),
                "ppm": round(m.vapor_ppm, 6),
                "intensity": round(m.intensity or 0.0, 3),
                "family": m.family,
            }
            for m in rows[:limit]
        ]

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "t_seconds": self.t_seconds,
            "state": self.state.as_dict(),
            "dominant_oav": self.dominant_oav(),
            "receptor_activation": {
                k: round(v, 4) for k, v in self.receptor_activation.items()
            },
            "receptor_source": self.receptor_source,
        }


def _loss_rate_per_s(
    vp_pa: float | None, gamma_value: float, mw_g_mol: float | None
) -> float:
    """Heuristic finite-film loss rate.

    The rate scales with headspace escaping tendency (gamma * VP) and inverse
    square-root molecular weight.  It is only used for gate time windows; the
    source is reported as a heuristic until a finite-film backend replaces it.
    """
    if not vp_pa or vp_pa <= 0:
        return 0.0
    mw = max(mw_g_mol or 200.0, 1.0)
    return min(2.5e-3, max(0.0, (gamma_value * vp_pa / math.sqrt(mw)) * 2.0e-5))


def _remaining_raw_ul(state: FormulaState, t_seconds: float) -> dict[str, float]:
    remaining: dict[str, float] = {}
    for m in state.materials:
        k = _loss_rate_per_s(m.vp_pure_pa, m.gamma, m.mw_g_mol)
        active_remaining = m.active_ul * math.exp(-k * t_seconds)
        dilution = max(m.dilution, 1e-9)
        remaining[m.name] = active_remaining / dilution
    return remaining


def _receptor_activation(state: FormulaState) -> dict[str, float]:
    conc_proxy = {
        m.name: max(0.0, m.vapor_ppm)
        for m in state.materials
        if m.vapor_ppm > 0 and m.family
    }
    ligands = {
        m.name: ligands_from_family(m.name, m.family)
        for m in state.materials
        if m.family
    }
    return or_occupancy(conc_proxy, ligands)


def simulate_formula(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
    *,
    batch_volume_ml: float = 30.0,
    temperature_K: float = 305.0,
    context: str = "skin",
    windows: Sequence[tuple[str, float]] = DEFAULT_WINDOWS,
    initial_state: FormulaState | None = None,
) -> list[SimulationFrame]:
    """Return time-window FormulaState frames for release gates and reports."""
    initial = initial_state or build_formula_state(
        ingredients_ul,
        dilutions,
        batch_volume_ml=batch_volume_ml,
        temperature_K=temperature_K,
        context=context,
    )
    frames: list[SimulationFrame] = []
    for label, seconds in windows:
        if seconds <= 0:
            frame_state = initial
        else:
            remaining = _remaining_raw_ul(initial, seconds)
            frame_state = FormulaState.from_base(initial, new_raw_ul=remaining)
        frames.append(
            SimulationFrame(
                label=label,
                t_seconds=float(seconds),
                state=frame_state,
                receptor_activation=_receptor_activation(frame_state),
            )
        )
    return frames
