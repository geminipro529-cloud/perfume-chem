"""Thermodynamics layer: Antoine VP, UNIFAC γ, modified-Raoult headspace, trajectory.

All physical units in SI: Pa, K, mol, m³. Wt%/µL stays at the user-facing layer.
"""
from .antoine import vp_pa, antoine_from_dhvap
from .activity import gamma
from .headspace import headspace_from_wt_pct, partial_pressures
from .trajectory import evaporate

__all__ = [
    "vp_pa",
    "antoine_from_dhvap",
    "gamma",
    "headspace_from_wt_pct",
    "partial_pressures",
    "evaporate",
]
