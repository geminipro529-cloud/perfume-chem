"""OR genetic polymorphism (population averages).

Per the locked decision (3): default user is a population-average composite
across the major polymorphisms. This module exposes per-OR variant frequencies
and a helper to perturb an OR-occupancy vector to a specific genotype if
requested later.

Variants captured (frequencies are rough global averages):
  OR7D4-WT  ~0.45  → androstenone "urinous"
  OR7D4-RT  ~0.35  → androstenone weak
  OR7D4-WM  ~0.20  → anosmic to androstenone
  OR11H7    SNP    → 4-methylpentanoic acid sensitivity
  OR5A1     SNP    → β-ionone "violet" anosmia (~25%)
"""
from __future__ import annotations

from typing import Mapping


OR_POLYMORPHISMS = {
    "OR7D4": {
        "WT": {"freq": 0.45, "ec50_factor": 1.0,  "label": "urinous"},
        "RT": {"freq": 0.35, "ec50_factor": 5.0,  "label": "weak"},
        "WM": {"freq": 0.20, "ec50_factor": 1e6,  "label": "anosmic"},
    },
    "OR5A1": {
        "WT":      {"freq": 0.75, "ec50_factor": 1.0, "label": "violet"},
        "anosmic": {"freq": 0.25, "ec50_factor": 1e4, "label": "anosmic-bionone"},
    },
    "OR11H7": {
        "WT":      {"freq": 0.65, "ec50_factor": 1.0, "label": "sensitive"},
        "low":     {"freq": 0.35, "ec50_factor": 8.0, "label": "low-sensitivity"},
    },
}


def apply_polymorphism(or_occupancy: Mapping[str, float],
                       genotype: Mapping[str, str] | None = None) -> dict[str, float]:
    """Adjust per-OR occupancy by genotype's relative ec50 factor.

    A factor of 5× ⇒ effective concentration is 1/5, so occupancy roughly
    halves in the linear regime. We approximate by scaling the occupancy
    by 1/(1+factor−1) ≈ 1/factor for factor ≥ 1.
    """
    out = dict(or_occupancy)
    g = genotype or {}
    for or_gene, variant in g.items():
        info = OR_POLYMORPHISMS.get(or_gene, {}).get(variant)
        if info is None:
            continue
        factor = info["ec50_factor"]
        if or_gene in out:
            out[or_gene] = out[or_gene] / max(factor, 1.0)
    return out


def population_average_response(or_occupancy: Mapping[str, float]) -> dict[str, float]:
    """Average across variant frequencies for each polymorphic OR."""
    out = dict(or_occupancy)
    for or_gene, variants in OR_POLYMORPHISMS.items():
        if or_gene not in out:
            continue
        avg = 0.0
        for v in variants.values():
            avg += v["freq"] * out[or_gene] / max(v["ec50_factor"], 1.0)
        out[or_gene] = avg
    return out


if __name__ == "__main__":
    R = {"OR7D4": 0.6, "OR5A1": 0.5, "OR11H7": 0.4, "OR_WD": 0.3}
    print("WT genotype:", apply_polymorphism(R, {"OR7D4": "WT"}))
    print("Anosmic AND:", apply_polymorphism(R, {"OR7D4": "WM"}))
    print("Population average:", population_average_response(R))
