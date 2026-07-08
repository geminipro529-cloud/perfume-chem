"""Spray atomisation physics.

Log-normal droplet size distribution (typical perfume atomiser:
σ_g ≈ 1.5, Dv50 ≈ 30 µm). d²-law for in-flight evaporation. Stokes settling
to estimate skin-vs-air partition of the cloud.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class DropletStats:
    diameters_um: list[float]
    counts: list[float]            # relative
    dv50_um: float
    dv90_um: float


def droplet_distribution(dv50_um: float = 30.0, sigma_g: float = 1.5,
                         n_bins: int = 30) -> DropletStats:
    """Sample a log-normal distribution by volume."""
    mu = math.log(dv50_um)
    sigma = math.log(sigma_g)
    diams: list[float] = []
    counts: list[float] = []
    d_min = math.exp(mu - 3.0 * sigma)
    d_max = math.exp(mu + 3.0 * sigma)
    log_step = (math.log(d_max) - math.log(d_min)) / (n_bins - 1)
    cum_vol = 0.0
    rows = []
    for i in range(n_bins):
        d = math.exp(math.log(d_min) + i * log_step)
        x = (math.log(d) - mu) / sigma
        # log-normal pdf (volume-weighted by definition since we vary log-d uniformly)
        pdf = (1.0 / (d * sigma * math.sqrt(2 * math.pi))) * math.exp(-0.5 * x * x)
        rows.append((d, pdf))
        diams.append(d)
        counts.append(pdf)
    # Volume fractions
    total = sum(counts)
    counts = [c / total for c in counts]
    # Dv50 / Dv90
    cum = 0.0
    dv50 = dv50_um
    dv90 = dv50_um * 1.5
    for d, c in zip(diams, counts):
        cum += c
        if cum >= 0.5 and dv50 == dv50_um:
            dv50 = d
        if cum >= 0.9 and dv90 == dv50_um * 1.5:
            dv90 = d
    return DropletStats(diams, counts, dv50, dv90)


def stokes_settling_velocity(d_um: float,
                              rho_drop_kg_m3: float = 900.0,
                              rho_air_kg_m3: float = 1.2,
                              mu_air_pa_s: float = 1.8e-5,
                              g: float = 9.81) -> float:
    """Terminal velocity for a small spherical droplet (m/s)."""
    d_m = d_um * 1e-6
    return (d_m * d_m * (rho_drop_kg_m3 - rho_air_kg_m3) * g) / (18.0 * mu_air_pa_s)


def droplet_d2_evaporation(d0_um: float, K_um2_s: float, t_s: float) -> float:
    """d²-law:  d² = d0² − K·t. Returns diameter at time t (µm)."""
    d2 = d0_um * d0_um - K_um2_s * t_s
    if d2 <= 0:
        return 0.0
    return math.sqrt(d2)


if __name__ == "__main__":
    stats = droplet_distribution()
    print(f"Dv50 = {stats.dv50_um:.1f} µm   Dv90 = {stats.dv90_um:.1f} µm")
    for d in [5, 30, 100]:
        v = stokes_settling_velocity(d)
        print(f"d={d}µm  vt={v*1000:.3f} mm/s")
    # Ethanol K ≈ 1000 µm²/s in still air at 20 °C
    print(f"30 µm ethanol drop after 0.5 s: {droplet_d2_evaporation(30, 1000, 0.5):.1f} µm")
