"""Sniff dynamics.

Tidal volume ≈ 500 mL/breath; sniff peak-flow ≈ 1 L/s for ~0.5 s.
Olfactory cleft sees only ~5–15% of inspired air (diversion fraction).
Mucus barrier: D_mucus ≈ D_air / 100, traversal ~10–100 ms.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SniffProfile:
    tidal_volume_ml: float = 500.0
    peak_flow_ml_s: float = 1000.0  # 1 L/s during a vigorous sniff
    duration_s: float = 0.5
    cleft_diversion_fraction: float = 0.10


def olfactory_cleft_concentration(
    vapor_conc_ug_m3: float, profile: SniffProfile | None = None
) -> float:
    """Concentration of odorant reaching the olfactory cleft (µg/m³).

    Approximation: cleft sees the same gas-phase concentration as inhaled air
    multiplied by the diversion fraction (rest goes to lungs).
    """
    p = profile or SniffProfile()
    return vapor_conc_ug_m3 * p.cleft_diversion_fraction


def sherwood_mass_transfer(
    d_h_m: float = 0.005,
    v_m_s: float = 1.0,
    kinematic_visc_m2_s: float = 1.5e-5,
    diffusivity_m2_s: float = 1.0e-5,
) -> float:
    """k_g [m/s] for the cleft using Sherwood–Reynolds–Schmidt.

    Sh = 0.023 · Re^0.8 · Sc^0.33  (turbulent pipe analogue, ducted nasal flow).
    """
    Re = v_m_s * d_h_m / kinematic_visc_m2_s  # noqa: N806
    Sc = kinematic_visc_m2_s / diffusivity_m2_s  # noqa: N806
    Sh = 0.023 * (Re**0.8) * (Sc**0.33)  # noqa: N806
    return Sh * diffusivity_m2_s / d_h_m


def mucus_traversal_ms(thickness_um: float = 30.0, d_mucus_m2_s: float = 1.0e-7) -> float:
    """Diffusive crossing time t ≈ L²/D (ms)."""
    L = thickness_um * 1e-6  # noqa: N806
    return 1000.0 * L * L / d_mucus_m2_s


if __name__ == "__main__":
    p = SniffProfile()
    c_cleft = olfactory_cleft_concentration(100.0, p)
    print(f"Cleft conc for 100 µg/m³ inhaled: {c_cleft:.1f} µg/m³")
    print(f"Sherwood kg: {sherwood_mass_transfer():.3e} m/s")
    print(f"Mucus crossing: {mucus_traversal_ms():.1f} ms")
