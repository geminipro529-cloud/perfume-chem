"""UV photodegradation: citrals, citrus terpenes.

Norrish + [2+2] dimerisation for furocoumarins; here we model first-order
loss with sunlight-flux-dependent rate constants.
"""
from __future__ import annotations

import math

# Photolysis rate constants under direct outdoor sun (~ 1000 W/m² UV-A+B).
# Indoor scattered light reduces by ~50–100×.
PHOTOLYSIS_K_PER_HOUR_OUTDOOR = {
    "citral":    1.5e-2,
    "limonene":  3.0e-3,
    "linalool":  2.5e-3,
    "bergaptene":1.0e-1,   # furocoumarins photodegrade fast
    "default":   1.0e-3,
}


def photolysis_remaining_fraction(species: str, hours_exposed: float,
                                  indoor: bool = True) -> float:
    k = PHOTOLYSIS_K_PER_HOUR_OUTDOOR.get(species.lower(),
                                          PHOTOLYSIS_K_PER_HOUR_OUTDOOR["default"])
    if indoor:
        k /= 100.0
    return math.exp(-k * hours_exposed)


if __name__ == "__main__":
    for s in ["citral", "limonene", "bergaptene"]:
        for h in (24, 24 * 30):
            print(f"{s:10s} {h}h indoor → remaining {photolysis_remaining_fraction(s, h, True):.3f}")
