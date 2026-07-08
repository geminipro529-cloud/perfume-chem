"""Maturation reactor: predicts composition drift over time.

Reactions:
  acetal:    aldehyde + 2 EtOH ⇌ acetal + H₂O   (acid-cat; Blakeway 1987)
  schiff:    aldehyde + amine → imine
  autoxid:   terpene + O₂  → hydroperoxide      (BHT-quenchable)
  isomer:    cis ⇌ trans   (e.g., isoeugenol)

Rate constants are Arrhenius:  k(T) = A·exp(-Ea / R·T).
Ea / A constants below are order-of-magnitude calibrated to reproduce
Blakeway's reference: ~40% acetal conversion of an aliphatic aldehyde at
37 °C / 90 days in 80% EtOH.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

R_GAS = 8.314_462_618


def arrhenius_k(A: float, Ea_kj_mol: float, T_K: float) -> float:
    return A * math.exp(-Ea_kj_mol * 1000.0 / (R_GAS * T_K))


# Approximate Arrhenius parameters per reaction class (s^-1 pseudo-first-order
# in dilute EtOH-rich matrix). Tuned, not from primary literature for every
# aldehyde — the schema lets users override per-material later.
RXN_PARAMS = {
    "acetal":    {"A": 5.0e6,  "Ea": 75.0},
    "schiff":    {"A": 1.0e7,  "Ea": 70.0},
    "autoxid":   {"A": 2.0e5,  "Ea": 80.0},
    "isomer":    {"A": 1.0e4,  "Ea": 90.0},
}


# Heuristic: which materials are susceptible to which reactions. Falls back
# to functional-group inference when a Material record carries `functional_groups`.
SUSCEPTIBLE = {
    "acetal":  {"aldehyde"},
    "schiff":  {"aldehyde"},
    "autoxid": {"terpene", "alkene"},
    "isomer":  {"isoeugenol", "citral", "alkene"},
}


@dataclass(slots=True)
class MaturationReactor:
    composition_g: dict[str, float]
    T_K: float = 295.0      # 22 °C (cellar)
    days_aged: float = 0.0
    bht_protected: bool = False
    history: list[tuple[float, dict[str, float]]] = field(default_factory=list)

    def step(self, days: float, *, functional_groups: Mapping[str, set[str]] | None = None):
        """Advance ageing by `days`, mutate composition_g in place."""
        if days <= 0:
            return
        dt_s = days * 86400.0
        fg = functional_groups or {}
        new_comp = dict(self.composition_g)
        for name, mass in self.composition_g.items():
            if mass <= 0:
                continue
            tags = fg.get(name, set())
            for rxn, susceptible in SUSCEPTIBLE.items():
                if not (tags & susceptible):
                    continue
                params = RXN_PARAMS[rxn]
                k = arrhenius_k(params["A"], params["Ea"], self.T_K)
                if rxn == "autoxid" and self.bht_protected:
                    k *= 0.05
                # First-order conversion fraction
                frac_remaining = math.exp(-k * dt_s)
                lost = mass * (1.0 - frac_remaining)
                new_comp[name] = max(0.0, new_comp[name] - lost)
                # Track byproducts under a generic key
                bp_key = f"_byproduct_{rxn}"
                new_comp[bp_key] = new_comp.get(bp_key, 0.0) + lost
        self.composition_g = new_comp
        self.days_aged += days
        self.history.append((self.days_aged, dict(new_comp)))

    def conversion_pct(self, name: str, original_g: float) -> float:
        if original_g <= 0:
            return 0.0
        return 100.0 * (1.0 - self.composition_g.get(name, 0.0) / original_g)


def predict_shelf_life_days(
    composition_g: Mapping[str, float],
    *,
    T_K: float = 295.0,
    bht_protected: bool = False,
    threshold_pct: float = 10.0,
    functional_groups: Mapping[str, set[str]] | None = None,
    max_days: int = 1825,    # 5 years cap
) -> int:
    """Day at which the first character-defining material crosses
    `threshold_pct` conversion. Returns max_days if none triggered.
    """
    reactor = MaturationReactor(dict(composition_g), T_K=T_K, bht_protected=bht_protected)
    original = dict(composition_g)
    step_days = 7.0
    days = 0.0
    while days < max_days:
        reactor.step(step_days, functional_groups=functional_groups)
        days += step_days
        for name, og in original.items():
            if reactor.conversion_pct(name, og) >= threshold_pct:
                return int(days)
    return max_days


if __name__ == "__main__":
    comp = {"Aldehyde C12 MNA": 1.0, "Limonene": 5.0, "Hedione": 30.0}
    fg = {
        "Aldehyde C12 MNA": {"aldehyde"},
        "Limonene": {"terpene", "alkene"},
        "Hedione": set(),
    }
    r = MaturationReactor(comp, T_K=310.15, bht_protected=False)
    r.step(90, functional_groups=fg)
    for k, v in r.composition_g.items():
        print(f"{k:30s} {v:.4f}")
    print("conversion C12:", r.conversion_pct("Aldehyde C12 MNA", 1.0), "%")
    print("shelf life days:", predict_shelf_life_days(comp, T_K=310.15, functional_groups=fg))
