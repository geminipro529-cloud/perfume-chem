"""OAV (Odor Activity Value) and perceived intensity with mixture shifts.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- OAV < 1: below threshold (not perceptible).
- OAV 1-5: perceptible but weak.
- OAV 5-50: clearly perceptible.
- OAV > 50: dominant; consider reduction.

OAV(i) = C(i) / ODT(i)
Perceived intensity (Stevens): I(i) = k · OAV(i)^n   (n family-specific)
Weber–Fechner alternative:    I(i) = k · log(1 + OAV(i))
Mixture-shifted ODT (Ferreira 2012-style):
    ODT_eff(i) = ODT(i) · (1 + Σⱼ≠ᵢ wⱼ · OAV(j))^β
"""
from __future__ import annotations

import math
from typing import Mapping

# Default Stevens exponents per OR-family (literature ranges 0.2–0.7).
STEVENS_BY_FAMILY: dict[str, float] = {
    "musk": 0.30,
    "amber": 0.35,
    "wood": 0.38,
    "iris": 0.40,
    "floral": 0.42,
    "citrus": 0.55,
    "green": 0.55,
    "aldehyde": 0.58,
    "spice": 0.50,
    "default": 0.40,
}


def stevens_exponent(family: str | None) -> float:
    if family is None:
        return STEVENS_BY_FAMILY["default"]
    return STEVENS_BY_FAMILY.get(family.lower(), STEVENS_BY_FAMILY["default"])


def oav(conc_ppm: float, odt_air_ppm: float) -> float:
    """OAV = vapor concentration / odor detection threshold (both same units)."""
    if odt_air_ppm <= 0:
        return 0.0
    return conc_ppm / odt_air_ppm


def perceived_intensity_stevens(oav_value: float, family: str | None = None,
                                k: float = 1.0) -> float:
    if oav_value <= 0:
        return 0.0
    return k * (oav_value ** stevens_exponent(family))


def perceived_intensity_weber(oav_value: float, k: float = 1.0) -> float:
    if oav_value <= 0:
        return 0.0
    return k * math.log1p(oav_value)


def mixture_shifted_odt(
    name: str,
    odt_table: Mapping[str, float],   # ppm
    conc_table: Mapping[str, float],  # ppm
    *,
    beta: float = 0.3,
    family_weights: Mapping[str, float] | None = None,
) -> float:
    """Apply mixture-suppression. Weights default to 1.0 each."""
    if name not in odt_table:
        return 0.0
    base = odt_table[name]
    accum = 0.0
    for j, c in conc_table.items():
        if j == name:
            continue
        odj = odt_table.get(j)
        if not odj or odj <= 0:
            continue
        wj = (family_weights or {}).get(j, 1.0)
        accum += wj * (c / odj)
    return base * (1.0 + accum) ** beta


def oav_profile(
    conc_ppm: Mapping[str, float],
    odt_ppm: Mapping[str, float],
    family_of: Mapping[str, str] | None = None,
    *,
    use_mixture_shift: bool = True,
    beta: float = 0.3,
    use_weber: bool = False,
) -> dict[str, dict[str, float]]:
    """Return {name: {oav, intensity, odt_eff}}."""
    out: dict[str, dict[str, float]] = {}
    for n, c in conc_ppm.items():
        if use_mixture_shift:
            odt_eff = mixture_shifted_odt(n, odt_ppm, conc_ppm, beta=beta)
        else:
            odt_eff = odt_ppm.get(n, 0.0)
        v = oav(c, odt_eff)
        if use_weber:
            inten = perceived_intensity_weber(v)
        else:
            fam = (family_of or {}).get(n)
            inten = perceived_intensity_stevens(v, fam)
        out[n] = {"oav": v, "intensity": inten, "odt_eff": odt_eff}
    return out


if __name__ == "__main__":
    conc = {"Limonene": 0.5, "Iso E Super": 0.05, "Hedione": 0.02}
    odt = {"Limonene": 0.21, "Iso E Super": 0.5, "Hedione": 0.02}
    fam = {"Limonene": "citrus", "Iso E Super": "wood", "Hedione": "floral"}
    prof = oav_profile(conc, odt, fam)
    for k, v in prof.items():
        print(f"{k:14s} OAV={v['oav']:.2f} I={v['intensity']:.2f} ODT_eff={v['odt_eff']:.3f}")
