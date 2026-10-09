"""Time-window simulation over :class:`FormulaState`.

The temporal path is an explicitly uncalibrated screening model. It integrates
composition-dependent modeled headspace over bounded time steps, but it does
not predict measured skin life, blotter life, or absolute evaporation.

Loss law (mass-balanced, diagnosis M3): each material leaves at a gas-side
limited flux ``dn_i/dt = -A * gamma_i * x_i * P_i* / sqrt(MW_i)`` with
``x_i = n_i / N(t)`` recomputed from the current pool after every step, so the
amount removed tracks the partial pressure each frame reports. ``A`` is an
unfitted relative scale, ``2e-5 * N_0``, with ``N_0`` the t=0 concentrate
moles without the declared matrix (audit PHYS-01), so a formula with no matrix
starts at the previous per-material constant ``2e-5 * gamma*P*/sqrt(MW)`` and
a declared matrix no longer inflates the scale.

A declared ethanol/water matrix leaves by the same law, cap and step
(diagnosis M1a), so it no longer stays in the pool for the whole run.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.solvent_matrix import canonical_solvent_name

DEFAULT_WINDOWS: tuple[tuple[str, float], ...] = (
    ("opening", 0.0),
    ("top", 300.0),
    ("heart", 1800.0),
    ("late_heart", 7200.0),
    ("drydown", 14400.0),
)

TEMPORAL_MODEL = "dynamic_headspace_mass_balanced_loss_v4"
TEMPORAL_AUTHORITY = "HEURISTIC_UNCALIBRATED"
REMAINING_QUANTITY_BASIS = "heuristic_remaining_stock_volume_equivalent_ul"
MAX_INTEGRATION_STEP_SECONDS = 300.0
# Unfitted relative scale and cap of the loss law; not kinetic parameters.
LOSS_RATE_SCALE = 2.0e-5
MAX_LOSS_RATE_PER_S = 2.5e-3
# Matrix components that evaporate (diagnosis M1a): canonical solvent key ->
# (vapour pressure in Pa at 25 C, molar mass in g/mol). Source: CRC Handbook
# of Chemistry and Physics (vapour pressure of fluids; physical constants of
# organic compounds). The data spine's Ethanol 96% row (5900 Pa) carries no
# vp_source, so it is not used. No temperature correction is applied.
MATRIX_COMPONENT_VP_MW: dict[str, tuple[float, float]] = {
    "ETHANOL": (7870.0, 46.07),
    "WATER": (3170.0, 18.02),
}
# FormulaState assigns no activity coefficient to matrix components, so the
# matrix loss uses gamma = 1.0 (ideal solution) as an explicit assumption.
MATRIX_COMPONENT_GAMMA = 1.0


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
            (
                material
                for material in self.state.materials
                if material.screening_oav is not None
            ),
            key=lambda m: float(m.screening_oav or 0.0),
            reverse=True,
        )
        return [
            {
                "material": m.name,
                "oav": round(float(m.screening_oav), 3),
                "ppm": (
                    None
                    if m.screening_vapor_ppm is None
                    else round(float(m.screening_vapor_ppm), 6)
                ),
                "intensity": (
                    None
                    if m.screening_intensity is None
                    else round(float(m.screening_intensity), 3)
                ),
                "family": m.family,
                "physics_status": m.physics_status,
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
    if material.physics_status == "WITHHELD":
        return 0.0
    if material.partial_pressure_pa > 0.0 and material.mole_fraction > 0.0:
        return material.partial_pressure_pa / material.mole_fraction
    if material.vp_pure_pa is None or material.vp_pure_pa <= 0.0:
        return 0.0
    return max(0.0, material.gamma * material.vp_pure_pa)


def _loss_rate_per_s(
    escaping_tendency_pa: float,
    mw_g_mol: float | None,
    pool_ratio: float = 1.0,
) -> float:
    """Return an uncalibrated relative-loss rate for temporal screening.

    ``pool_ratio`` is ``N_0 / N(t)``: the initial pool moles over the current
    pool moles that the headspace mole fractions use. Multiplying by it turns
    the per-material constant into the mass-balanced flux
    ``A * gamma * x_i * P* / sqrt(MW)`` divided by ``n_i``, with
    ``A = LOSS_RATE_SCALE * N_0`` (diagnosis M3) and ``N_0`` the t=0
    concentrate moles without the matrix (audit PHYS-01). The scale constant and cap
    are not fitted kinetic parameters and therefore cannot support an
    absolute evaporation or longevity claim.
    """
    if escaping_tendency_pa <= 0.0:
        return 0.0
    mw = max(mw_g_mol or 200.0, 1.0)
    return min(
        MAX_LOSS_RATE_PER_S,
        (escaping_tendency_pa / math.sqrt(mw)) * LOSS_RATE_SCALE * pool_ratio,
    )


def _pool_total_moles(state: FormulaState) -> float:
    """Return the mole total that the state's headspace mole fractions use."""
    return sum(m.moles for m in state.materials) + state.matrix_moles


def _loss_scale_moles(state: FormulaState) -> float:
    """Return ``N_0`` for the loss scale: the t=0 concentrate moles only.

    The declared ethanol/water matrix is left out (audit PHYS-01). With it in,
    ``A`` grew with the matrix, so once the matrix had evaporated every
    material lost at a rate inflated by about the matrix-to-concentrate mole
    ratio (about 137x for a 30 mL EDP), and a declared solvent emptied the base.
    """
    return sum(m.moles for m in state.materials)


def _pool_ratio(state: FormulaState, initial_pool_moles: float | None) -> float:
    """Return ``N_0 / N(t)``; 1 when ``N_0`` is omitted or the pool is empty."""
    pool_moles = _pool_total_moles(state)
    if initial_pool_moles is None or pool_moles <= 0.0:
        return 1.0
    return float(initial_pool_moles) / pool_moles


def _remaining_raw_ul(
    state: FormulaState,
    delta_seconds: float,
    *,
    initial_pool_moles: float | None = None,
) -> dict[str, float]:
    """Return raw stock remaining after one step of the loss law.

    The rate of each material is frozen over the step at its start-of-step
    value and applied as ``exp(-k * dt)``. ``initial_pool_moles`` is ``N_0``;
    omitted, the state is treated as the initial pool (ratio 1).
    """
    pool_ratio = _pool_ratio(state, initial_pool_moles)
    remaining: dict[str, float] = {}
    for m in state.materials:
        k = _loss_rate_per_s(
            _effective_escaping_tendency_pa(m),
            m.mw_g_mol,
            pool_ratio,
        )
        active_remaining = m.active_ul * math.exp(-k * delta_seconds)
        dilution = max(m.dilution, 1e-9)
        remaining[m.name] = active_remaining / dilution
    return remaining


def _remaining_matrix_moles(
    state: FormulaState,
    delta_seconds: float,
    *,
    initial_pool_moles: float | None = None,
) -> tuple[tuple[str, float], ...]:
    """Return matrix component moles after one step of the same loss law.

    Each component's escaping tendency is ``MATRIX_COMPONENT_GAMMA * P*`` from
    ``MATRIX_COMPONENT_VP_MW``; the rate, cap, pool ratio and ``exp(-k * dt)``
    step are those applied to materials. A component without constants there
    is kept unchanged rather than given guessed properties.
    """
    pool_ratio = _pool_ratio(state, initial_pool_moles)
    remaining: list[tuple[str, float]] = []
    for name, moles in state.matrix_components_moles:
        constants = MATRIX_COMPONENT_VP_MW.get(canonical_solvent_name(name) or "")
        if constants is None:
            remaining.append((name, moles))
            continue
        vp_pa, mw_g_mol = constants
        k = _loss_rate_per_s(MATRIX_COMPONENT_GAMMA * vp_pa, mw_g_mol, pool_ratio)
        remaining.append((name, moles * math.exp(-k * delta_seconds)))
    return tuple(remaining)


def _advance_state(
    state: FormulaState,
    delta_seconds: float,
    *,
    max_step_seconds: float = MAX_INTEGRATION_STEP_SECONDS,
    initial_pool_moles: float | None = None,
) -> FormulaState:
    """Integrate the heuristic loss model while recomputing headspace.

    ``initial_pool_moles`` is ``N_0``, the t=0 concentrate moles without the
    matrix (:func:`_loss_scale_moles`); omitted, ``state`` is taken to be the
    t=0 state.
    """
    if delta_seconds < 0.0:
        raise ValueError("Temporal windows must be nondecreasing.")
    if max_step_seconds <= 0.0:
        raise ValueError("max_step_seconds must be positive.")

    if initial_pool_moles is None:
        initial_pool_moles = _loss_scale_moles(state)
    current = state
    remaining_seconds = float(delta_seconds)
    while remaining_seconds > 0.0:
        step = min(max_step_seconds, remaining_seconds)
        remaining = _remaining_raw_ul(
            current,
            step,
            initial_pool_moles=initial_pool_moles,
        )
        if current.matrix_components_moles:
            matrix = _remaining_matrix_moles(
                current,
                step,
                initial_pool_moles=initial_pool_moles,
            )
            current = FormulaState.from_base(
                current,
                new_raw_ul=remaining,
                new_matrix_moles=matrix,
            )
        else:
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
    initial_pool_moles = _loss_scale_moles(initial)
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
            initial_pool_moles=initial_pool_moles,
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
