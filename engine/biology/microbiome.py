"""Skin microbiome effects on volatile profile.

Corynebacterium spp. on apocrine sweat liberate androstenone, 3-methyl-
2-hexenoic acid, etc. Modeled as additive vapor-phase background that
modulates OAV of structurally similar materials and shifts musk/leather
perception.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AxillaProfile:
    androstenone_ppm: float = 0.001    # background airborne
    isovaleric_ppm: float = 0.0005
    short_chain_acid_ppm: float = 0.0008
    intensity: float = 1.0             # multiplier (sweat level)


def skin_microbiome_modifier(profile: AxillaProfile | None = None) -> dict[str, float]:
    """Return additive vapor concentrations (ppm) to merge into the perception
    layer. These compete for OR7D4 (androstenone) and OR11H7 (isovalerate).
    """
    p = profile or AxillaProfile()
    return {
        "_endogenous_androstenone": p.androstenone_ppm * p.intensity,
        "_endogenous_isovalerate":  p.isovaleric_ppm * p.intensity,
        "_endogenous_short_chain":  p.short_chain_acid_ppm * p.intensity,
    }


if __name__ == "__main__":
    print(skin_microbiome_modifier())
