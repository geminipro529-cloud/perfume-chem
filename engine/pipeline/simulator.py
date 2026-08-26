"""Time-window simulation over :class:`FormulaState`.

The temporal path is an explicitly uncalibrated screening model. It integrates
composition-dependent modeled headspace over bounded time steps, but it does
not predict measured skin life, blotter life, or absolute evaporation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from engine.pipeline.formula_state import FormulaState, build_formula_state

DEFAULT_WINDOWS: tuple[tuple[str, float], ...] = (
    ("opening", 0.0),
    ("top", 300.0),
    ("heart", 1800.0),
    ("late_heart", 7200.0),
    ("drydown", 14400.0),
)

TEMPORAL_MODEL = "dynamic_headspace_exponential_loss_v2"
TEMPORAL_AUTHORITY = "HEURISTIC_UNCALIBRATED"
REMAINING_QUANTITY_BASIS = "heuristic_remaining_stock_volume_equivalent_ul"
MAX_INTEGRATION_STEP_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class SimulationFrame:
    label: str
    t_seconds: float
    state: FormulaState
    receptor_activation: dict[str, float] | None = None
    receptor_source: str = "unavailable:material_specific_assay_required"
    temporal_model: str = TEMPORAL_MODEL
    temporal_authority: str = TEMPORAL_AUTHORITY
    remaining_quantity_basis: str = REMAINING_QUANTITY_BASIS

    def dominant_oav(self, limit: int = 8) -> list[dict]:
        rows = sorted(
            self.state.materials,
            key=lambda m: m.oav or 0.0,
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
            "receptor_activation": (
                {k: round(v, 4) for k, v in self.receptor_activation.items()}
                if self.receptor_activation is not None
                else None
            ),
            "receptor_source": self.receptor_source,
            "temporal_model": self.temporal_model,
            "temporal_authority": self.temporal_authority,
            "remaining_quantity_basis": self.remaining_quantity_basis,
        }


def _effective_escaping_tendency_pa(material) -> float:
    """Return the modeled ``gamma * VP`` term represented by a state row.

    Deriving the term from partial pressure and mole fraction lets supported
    natural mixtures use their constituent-resolved composite headspace rather
    than falling back to a missing or fictitious parent vapor pressure.
    """
    if material.partial_pressure_pa > 0.0 and material.mole_fraction > 0.0:
        return material.partial_pressure_pa / material.mole_fraction
    if material.vp_pure_pa is None or material.vp_pure_pa <= 0.0:
        return 0.0
    return max(0.0, material.gamma * material.vp_pure_pa)


def _loss_rate_per_s(
    escaping_tendency_pa: float,
    mw_g_mol: float | None,
) -> float:
    """Return an uncalibrated relative-loss rate for temporal screening.

    The scale constant and cap preserve the prior model's conservative
    numerical behavior. They are not fitted kinetic parameters and therefore
    cannot support an absolute evaporation or longevity claim.
    """
    if escaping_tendency_pa <= 0.0:
        return 0.0
    mw = max(mw_g_mol or 200.0, 1.0)
    return min(2.5e-3, (escaping_tendency_pa / math.sqrt(mw)) * 2.0e-5)


def _remaining_raw_ul(state: FormulaState, delta_seconds: float) -> dict[str, float]:
    remaining: dict[str, float] = {}
    for m in state.materials:
        k = _loss_rate_per_s(
            _effective_escaping_tendency_pa(m),
            m.mw_g_mol,
        )
        active_remaining = m.active_ul * math.exp(-k * delta_seconds)
        dilution = max(m.dilution, 1e-9)
        remaining[m.name] = active_remaining / dilution
    return remaining


def _advance_state(
    state: FormulaState,
    delta_seconds: float,
    *,
    max_step_seconds: float = MAX_INTEGRATION_STEP_SECONDS,
) -> FormulaState:
    """Integrate the heuristic loss model while recomputing headspace."""
    if delta_seconds < 0.0:
        raise ValueError("Temporal windows must be nondecreasing.")
    if max_step_seconds <= 0.0:
        raise ValueError("max_step_seconds must be positive.")

    current = state
    remaining_seconds = float(delta_seconds)
    while remaining_seconds > 0.0:
        step = min(max_step_seconds, remaining_seconds)
        remaining = _remaining_raw_ul(current, step)
        current = FormulaState.from_base(current, new_raw_ul=remaining)
        remaining_seconds -= step
    return current


def simulate_formula(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
    *,
    batch_volume_ml: float = 30.0,
    temperature_K: float = 305.0,  # noqa: N803
    context: str = "skin",
    windows: Sequence[tuple[str, float]] = DEFAULT_WINDOWS,
    initial_state: FormulaState | None = None,
) -> list[SimulationFrame]:
    """Return uncalibrated temporal-screening frames.

    Windows must be nonnegative and nondecreasing so each frame evolves from
    the preceding composition. FormulaState recomputes activity coefficients
    and natural-composite headspace after every bounded integration step.
    """
    initial = initial_state or build_formula_state(
        ingredients_ul,
        dilutions,
        batch_volume_ml=batch_volume_ml,
        temperature_K=temperature_K,
        context=context,
    )
    frames: list[SimulationFrame] = []
    current_state = initial
    current_seconds = 0.0
    for label, seconds in windows:
        target_seconds = float(seconds)
        if target_seconds < 0.0:
            raise ValueError("Temporal windows must be nonnegative.")
        if target_seconds < current_seconds:
            raise ValueError("Temporal windows must be nondecreasing.")
        current_state = _advance_state(
            current_state,
            target_seconds - current_seconds,
        )
        current_seconds = target_seconds
        frames.append(
            SimulationFrame(
                label=label,
                t_seconds=target_seconds,
                state=current_state,
            )
        )
    return frames
