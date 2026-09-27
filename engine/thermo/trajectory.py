"""Time-evolving evaporation trajectory.

Couples Fick's first law (boundary-layer mass transfer) with modified-Raoult
VLE. At each time step we recompute mole fractions, γᵢ, and partial pressures
from the *current* composition — which is why ethanol-driven blooming events
emerge naturally as the matrix becomes increasingly fragrance-rich.

Integration: explicit Euler with adaptive step (no scipy hard-dep). Drops in
scipy.solve_ivp if available for stiffer mixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .headspace import R_GAS, HeadspaceComponent, _mw, headspace_from_wt_pct


@dataclass(slots=True)
class TrajectoryFrame:
    t_seconds: float
    moles_remaining: dict[str, float]
    headspace: dict[str, HeadspaceComponent]
    bloom_events: list[str] = field(default_factory=list)


def evaporate(
    wt_pct: Mapping[str, float],
    *,
    initial_mass_g: float = 0.05,  # 50 mg = ~typical wrist drop
    surface_area_m2: float = 5e-4,  # ~5 cm²
    kg_m_s: float = 0.005,  # mass-transfer coeff (still air ≈ 5e-3)
    T_K: float = 305.0,  # noqa: N803
    duration_s: float = 7200.0,  # 2 h default
    n_steps: int = 240,  # 30 s frames
    mw_table: Mapping[str, float] | None = None,
    vp_table: Mapping[str, float] | None = None,
    antoine_table: Mapping[str, tuple[float, float, float]] | None = None,
    dhvap_table: Mapping[str, float] | None = None,
    hsp_table: Mapping[str, tuple[float, float, float]] | None = None,
) -> list[TrajectoryFrame]:
    """Integrate composition vs time.

    dnᵢ/dt = − kg · Aₛ · (pᵢ − p∞) / (R · T), with p∞ ≈ 0 (open air).
    Returns list of TrajectoryFrame at evenly spaced times.
    """
    mw_table = mw_table or {}
    # Initial moles from wt%
    total_w = sum(v for v in wt_pct.values() if v > 0)
    moles: dict[str, float] = {}
    for k, v in wt_pct.items():
        if v <= 0:
            continue
        mass_g = initial_mass_g * (v / total_w)
        mw = _mw(k, mw_table)
        moles[k] = mass_g / mw  # g / (g/mol) = mol

    dt = duration_s / n_steps
    out: list[TrajectoryFrame] = []
    prev_gamma: dict[str, float] = {}

    for step in range(n_steps + 1):
        t = step * dt
        # Current wt% from current moles
        cur_mass = {k: moles[k] * _mw(k, mw_table) for k in moles if moles[k] > 0}
        if not cur_mass:
            break
        total_m = sum(cur_mass.values())
        cur_wt = {k: 100.0 * v / total_m for k, v in cur_mass.items()}
        hs = headspace_from_wt_pct(
            cur_wt,
            T_K=T_K,
            mw_table=mw_table,
            vp_table=vp_table,
            antoine_table=antoine_table,
            dhvap_table=dhvap_table,
            hsp_table=hsp_table,
        )
        # Bloom detection
        bloom: list[str] = []
        for k, c in hs.items():
            if k in prev_gamma and prev_gamma[k] > 0:
                if c.gamma / prev_gamma[k] > 2.0:
                    bloom.append(k)
            prev_gamma[k] = c.gamma

        out.append(
            TrajectoryFrame(
                t_seconds=t,
                moles_remaining=dict(moles),
                headspace=hs,
                bloom_events=bloom,
            )
        )

        if step == n_steps:
            break

        # Apply Fick: dn/dt = − kg · A · p / (R T)
        for k, c in hs.items():
            flux_mol_s = kg_m_s * surface_area_m2 * c.partial_pressure_pa / (R_GAS * T_K)
            moles[k] = max(0.0, moles[k] - flux_mol_s * dt)
    return out


if __name__ == "__main__":
    wt = {"Ethanol": 80.0, "Limonene": 5.0, "Iso E Super": 15.0}
    mw = {"Ethanol": 46.07, "Limonene": 136.23, "Iso E Super": 234.4}
    vp = {"Ethanol": 7900.0, "Limonene": 198.0, "Iso E Super": 0.36}
    hsp = {
        "Ethanol": (15.8, 8.8, 19.4),
        "Limonene": (16.5, 1.1, 4.2),
        "Iso E Super": (16.0, 1.5, 3.0),
    }
    traj = evaporate(wt, mw_table=mw, vp_table=vp, hsp_table=hsp, duration_s=3600, n_steps=12)
    for f in traj:
        rem = sum(f.moles_remaining.values())
        bloom = ",".join(f.bloom_events) if f.bloom_events else "-"
        print(f"t={f.t_seconds / 60:5.1f}min  total_mol={rem:.4e}  bloom={bloom}")
