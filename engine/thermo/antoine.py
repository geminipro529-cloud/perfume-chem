"""Antoine vapor-pressure model.

Form: log10(P_mmHg) = A - B / (C + T_C)
Returns Pa. Falls back to Clausius–Clapeyron from VP_25 + ΔHvap when Antoine
constants are missing on the Material record.
"""

from __future__ import annotations

import math
from typing import Optional

R_GAS = 8.314_462_618  # J/mol/K
MMHG_TO_PA = 133.322_387_415


def vp_pa(
    T_K: float,  # noqa: N803
    *,
    A: Optional[float] = None,  # noqa: N803
    B: Optional[float] = None,  # noqa: N803
    C: Optional[float] = None,  # noqa: N803
    vp_25c_pa: Optional[float] = None,
    dhvap_kj_mol: Optional[float] = None,
) -> float:
    """Vapor pressure in Pa at temperature T_K.

    Priority:
      1. Antoine A/B/C (NIST form, log10 mmHg, T in °C)
      2. Clausius–Clapeyron from a known VP_25 + ΔHvap
      3. Last-resort: assume vp_25c_pa is constant (very poor)
    """
    T_C = T_K - 273.15  # noqa: N806
    if A is not None and B is not None and C is not None:
        log10_p_mmhg = A - B / (C + T_C)
        return (10.0**log10_p_mmhg) * MMHG_TO_PA
    if vp_25c_pa is not None and dhvap_kj_mol is not None:
        # Clausius–Clapeyron, reference T = 298.15 K
        T_ref = 298.15  # noqa: N806
        dh = dhvap_kj_mol * 1000.0
        return vp_25c_pa * math.exp(-dh / R_GAS * (1.0 / T_K - 1.0 / T_ref))
    if vp_25c_pa is not None:
        return vp_25c_pa
    raise ValueError("Need Antoine A/B/C or vp_25c_pa (+ optionally dhvap)")


def antoine_from_dhvap(vp_25c_pa: float, dhvap_kj_mol: float) -> tuple[float, float, float]:
    """Build a 2-point Antoine fit from VP_25 + ΔHvap by anchoring at 25 °C
    and computing VP at boiling-ish 100 °C. Returns (A, B, C) for log10 mmHg / °C.

    This is a coarse fallback for materials missing real Antoine constants.
    Sets C = 230 (the cookbook value for many organics) and solves A, B from
    the two computed VPs.
    """
    p25 = vp_25c_pa / MMHG_TO_PA
    p100 = vp_pa(373.15, vp_25c_pa=vp_25c_pa, dhvap_kj_mol=dhvap_kj_mol) / MMHG_TO_PA
    C = 230.0  # noqa: N806
    # log10(p) = A - B/(C+T_C); two equations, two unknowns
    log_p25 = math.log10(p25)
    log_p100 = math.log10(p100)
    # log_p25 = A - B/(C+25); log_p100 = A - B/(C+100)
    # subtract: log_p100 - log_p25 = -B/(C+100) + B/(C+25)
    delta = log_p100 - log_p25
    factor = 1.0 / (C + 25.0) - 1.0 / (C + 100.0)
    B = delta / factor  # noqa: N806
    A = log_p25 + B / (C + 25.0)  # noqa: N806
    return (A, B, C)


if __name__ == "__main__":
    # Self-test: water at 25 C ≈ 3170 Pa
    A, B, C = 8.07131, 1730.63, 233.426
    p = vp_pa(298.15, A=A, B=B, C=C)
    assert 3000 < p < 3300, f"water VP test: {p}"
    print(f"OK water VP@25C = {p:.0f} Pa (expect ~3170)")
    # CC fallback
    p_cc = vp_pa(298.15, vp_25c_pa=3170.0, dhvap_kj_mol=43.99)
    print(f"OK CC fallback = {p_cc:.0f} Pa")
