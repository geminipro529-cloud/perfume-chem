"""Hansen Solubility Parameter sphere model.

Used to flag micro-phase risk during evaporation (when EtOH leaves and
the matrix moves away from the fragrance HSP centre) and bloom-on-dilution
events when an EtOH-rich solution is sprayed onto skin.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence


def ra2(a: Sequence[float], b: Sequence[float]) -> float:
    """Hansen distance squared: Ra² = 4(δD)² + (δP)² + (δH)²."""
    return 4.0 * (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def relative_energy_difference(solute: Sequence[float], solvent: Sequence[float],
                               solute_radius: float = 8.0) -> float:
    """RED = Ra / R_solute. RED < 1 ⇒ soluble."""
    return math.sqrt(ra2(solute, solvent)) / max(solute_radius, 1e-6)


def micro_phase_risk(
    composition_wt: Mapping[str, float],
    hsp_table: Mapping[str, tuple[float, float, float]],
    *,
    radii: Mapping[str, float] | None = None,
) -> list[tuple[str, float]]:
    """Returns sorted list of (material, RED) where RED > 1 → likely to phase out.

    Uses mole-weighted matrix HSP (excluding the solute under inspection).
    """
    radii = radii or {}
    total = sum(v for v in composition_wt.values() if v > 0)
    if total <= 0:
        return []
    out: list[tuple[str, float]] = []
    for solute, w in composition_wt.items():
        if w <= 0 or solute not in hsp_table:
            continue
        # Mean solvent HSP
        rest = {k: v for k, v in composition_wt.items() if k != solute and v > 0 and k in hsp_table}
        s_total = sum(rest.values())
        if s_total <= 0:
            continue
        mean = [0.0, 0.0, 0.0]
        for k, wk in rest.items():
            for i in range(3):
                mean[i] += (wk / s_total) * hsp_table[k][i]
        red = relative_energy_difference(hsp_table[solute], mean,
                                         solute_radius=radii.get(solute, 8.0))
        out.append((solute, red))
    out.sort(key=lambda kv: -kv[1])
    return out


def bloom_on_dilution_risk(
    hsp_solute: Sequence[float],
    initial_solvent: Sequence[float],   # e.g. 80% EtOH
    final_solvent: Sequence[float],     # e.g. skin sebum
    *,
    radius: float = 8.0,
) -> dict[str, float]:
    """Return RED before vs after dilution. ↑RED ⇒ bloom risk."""
    return {
        "RED_initial": relative_energy_difference(hsp_solute, initial_solvent, radius),
        "RED_final":   relative_energy_difference(hsp_solute, final_solvent, radius),
    }


if __name__ == "__main__":
    hsp = {
        "Iso E Super": (16.0, 1.5, 3.0),
        "Hedione": (17.0, 6.0, 8.0),
        "Ethanol": (15.8, 8.8, 19.4),
        "Limonene": (16.5, 1.1, 4.2),
    }
    comp = {"Iso E Super": 15.0, "Hedione": 5.0, "Ethanol": 75.0, "Limonene": 5.0}
    risks = micro_phase_risk(comp, hsp)
    for k, v in risks:
        flag = "⚠ phase risk" if v > 1 else "ok"
        print(f"{k:14s} RED={v:.2f}  {flag}")
