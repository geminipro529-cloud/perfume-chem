"""3-compartment skin model: bulk-liquid film → stratum corneum → vapor.

Adds Potts–Guy permeability and a depot release that re-feeds vapor as the
liquid film evaporates. Couples to thermo.trajectory by providing a
"skin sink" rate per material.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def potts_guy_log_kp(logp: float, mw_g_mol: float) -> float:
    """log10(Kp [cm/s]) for stratum-corneum permeation.

    Potts & Guy 1992: log Kp(cm/s) = 0.71·logP − 0.0061·MW − 6.3
    """
    return 0.71 * logp - 0.0061 * mw_g_mol - 6.3


def kp_cm_per_h(logp: float, mw_g_mol: float) -> float:
    """Permeability in cm/h (Potts-Guy intercept is for cm/s, multiply by 3600)."""
    return (10.0 ** potts_guy_log_kp(logp, mw_g_mol)) * 3600.0


def sebum_retention_factor(logp: float) -> float:
    """High-logP musks bind sebum lipids 2–4× longer (Kasting & Saiyasombati).

    Returns a multiplicative depot-residence factor.
    """
    if logp >= 5.0:
        return 3.0
    if logp >= 4.0:
        return 2.0
    if logp >= 3.0:
        return 1.4
    return 1.0


def fabric_partition_factor(fabric: str) -> float:
    """Cotton vs wool vs synthetic depot multiplier."""
    return {"cotton": 1.0, "wool": 1.6, "polyester": 0.7, "silk": 1.2}.get(
        fabric.lower(), 1.0
    )


@dataclass(slots=True)
class SkinPartition:
    name: str
    kp_cm_per_h: float
    fraction_into_skin: float          # of mass that crosses film boundary per step
    depot_tau_s: float                 # 1/e residence time in skin reservoir
    sebum_factor: float


def skin_partition(
    name: str,
    *,
    logp: float | None = None,
    mw_g_mol: float | None = None,
    contact_seconds: float = 3600.0,
    skin_film_thickness_um: float = 50.0,
) -> SkinPartition:
    if logp is None or mw_g_mol is None:
        # Generic moderate-volatility default
        logp = 3.5 if logp is None else logp
        mw_g_mol = 200.0 if mw_g_mol is None else mw_g_mol
    kp = kp_cm_per_h(logp, mw_g_mol)
    # Convert to fractional uptake over `contact_seconds`
    # Mass flux ≈ kp · C_film; for a fixed-thickness film, fraction ≈ kp·dt/thickness
    kp_cm_s = kp / 3600.0
    thickness_cm = skin_film_thickness_um / 10_000.0
    frac = 1.0 - math.exp(-kp_cm_s * contact_seconds / thickness_cm)
    sebum = sebum_retention_factor(logp)
    # Depot τ scales with sebum binding, baseline 30 min
    tau = 1800.0 * sebum
    return SkinPartition(name, kp, frac, tau, sebum)


def depot_release_rate(
    moles_in_depot: float,
    tau_s: float,
) -> float:
    """First-order release: dn/dt = −n/τ. Returns mol/s leaving depot."""
    return moles_in_depot / max(tau_s, 1.0)


if __name__ == "__main__":
    for n, lp, mw in [
        ("Limonene", 4.5, 136),
        ("Iso E Super", 5.7, 234),
        ("Hedione", 2.6, 226),
        ("Habanolide", 6.0, 252),
    ]:
        sp = skin_partition(n, logp=lp, mw_g_mol=mw)
        print(f"{n:14s} Kp={sp.kp_cm_per_h:.2e} cm/h  frac→skin={sp.fraction_into_skin:.3f}  τ_depot={sp.depot_tau_s/60:.1f} min")
