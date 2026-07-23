"""Receptor (GPCR) layer for perfume-chem.

Modules:
  binding   — competitive Hill-equation occupancy across an OR array
  adaptation — three-timescale Ca²⁺/CaMKII/GRK desensitisation
  bulb       — glomerular activation vector + lateral inhibition + novelty
"""
from .adaptation import AdaptationState, step_adaptation
from .binding import ORArray, ORLigand, or_occupancy
from .bulb import configural_blur, glomerular_vector, novelty_score

__all__ = [
    "or_occupancy", "ORLigand", "ORArray",
    "AdaptationState", "step_adaptation",
    "glomerular_vector", "novelty_score", "configural_blur",
]
