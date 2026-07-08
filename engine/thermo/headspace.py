"""Modified-Raoult headspace: pᵢ = γᵢ · xᵢ · Pᵢᵛᵃᵖ(T).

Inputs at the user-facing layer are wt% / µL. Internally we convert to
mole fractions, compute γᵢ, evaluate VP via Antoine, return partial pressures
and vapor-phase concentrations (Pa, mol/m³, ppm, µg/m³).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .antoine import vp_pa, R_GAS
from .activity import gamma


@dataclass(slots=True)
class HeadspaceComponent:
    name: str
    mole_fraction: float
    gamma: float
    vp_pure_pa: float
    partial_pressure_pa: float
    vapor_conc_mol_m3: float
    vapor_conc_ug_m3: float
    vapor_ppm: float


def _mw(name: str, mw_table: Mapping[str, float]) -> float:
    """Best-effort MW lookup; default 200 g/mol if unknown (typical fragrance)."""
    return mw_table.get(name) or 200.0


def headspace_from_wt_pct(
    wt_pct: Mapping[str, float],
    T_K: float = 305.0,
    *,
    mw_table: Mapping[str, float] | None = None,
    vp_table: Mapping[str, float] | None = None,
    antoine_table: Mapping[str, tuple[float, float, float]] | None = None,
    dhvap_table: Mapping[str, float] | None = None,
    hsp_table: Mapping[str, tuple[float, float, float]] | None = None,
    P_atm: float = 101_325.0,
) -> dict[str, HeadspaceComponent]:
    """Compute per-material headspace at temperature T from wt% composition.

    `wt_pct` may sum to anything — we normalise to fraction (sum=1) then
    convert to mole fraction with `mw_table`. Default T_K = 305 K (skin).
    """
    mw_table = mw_table or {}
    vp_table = vp_table or {}
    antoine_table = antoine_table or {}
    dhvap_table = dhvap_table or {}
    hsp_table = hsp_table or {}

    # Normalise wt fraction
    total_w = sum(v for v in wt_pct.values() if v > 0)
    if total_w <= 0:
        return {}
    w = {k: v / total_w for k, v in wt_pct.items() if v > 0}

    # Convert to mole fraction
    moles = {k: w[k] / _mw(k, mw_table) for k in w}
    total_n = sum(moles.values())
    x = {k: moles[k] / total_n for k in moles}

    # Per-component VP and γ
    out: dict[str, HeadspaceComponent] = {}
    for k, xk in x.items():
        ant = antoine_table.get(k)
        if ant is not None:
            P_pure = vp_pa(T_K, A=ant[0], B=ant[1], C=ant[2])
        else:
            P_pure = vp_pa(
                T_K,
                vp_25c_pa=vp_table.get(k),
                dhvap_kj_mol=dhvap_table.get(k),
            ) if vp_table.get(k) else 0.0
        gk = gamma(k, x, T_K, hsp_table=hsp_table)
        p_partial = gk * xk * P_pure
        # Ideal gas: c = P / (R T)
        c_mol_m3 = p_partial / (R_GAS * T_K)
        c_ug_m3 = c_mol_m3 * _mw(k, mw_table) * 1e6  # g/mol→µg/mol
        ppm = 1e6 * p_partial / P_atm
        out[k] = HeadspaceComponent(
            name=k,
            mole_fraction=xk,
            gamma=gk,
            vp_pure_pa=P_pure,
            partial_pressure_pa=p_partial,
            vapor_conc_mol_m3=c_mol_m3,
            vapor_conc_ug_m3=c_ug_m3,
            vapor_ppm=ppm,
        )
    return out


def partial_pressures(*args, **kwargs) -> dict[str, float]:
    """Convenience: just the {name: partial_pressure_pa} map."""
    hs = headspace_from_wt_pct(*args, **kwargs)
    return {k: c.partial_pressure_pa for k, c in hs.items()}


if __name__ == "__main__":
    wt = {"Ethanol": 80.0, "Limonene": 5.0, "Iso E Super": 15.0}
    mw = {"Ethanol": 46.07, "Limonene": 136.23, "Iso E Super": 234.4}
    vp = {"Ethanol": 7900.0, "Limonene": 198.0, "Iso E Super": 0.36}
    hsp = {
        "Ethanol": (15.8, 8.8, 19.4),
        "Limonene": (16.5, 1.1, 4.2),
        "Iso E Super": (16.0, 1.5, 3.0),
    }
    hs = headspace_from_wt_pct(wt, mw_table=mw, vp_table=vp, hsp_table=hsp)
    for c in hs.values():
        print(f"{c.name:14s} x={c.mole_fraction:.3f} γ={c.gamma:.2f} "
              f"P={c.partial_pressure_pa:7.1f} Pa  ppm={c.vapor_ppm:.2f}")
