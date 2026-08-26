"""Competitive binding across the OR array.

Hill model with competition:
        Σᵢ ([Lᵢ]/Kᵢᵏ)^h · eᵢᵏ
   Rᵏ = ───────────────────────
        1 + Σᵢ ([Lᵢ]/Kᵢᵏ)^h

  Rᵏ ∈ [0, 1] is the activation of OR k. eᵢᵏ is per-ligand efficacy
  (full agonist = 1, partial = 0–1, antagonist = 0 with K still entering
  the denominator).

Without per-material EC50 data (the Phase-0 audit shows or_targets at 0%),
we use a structural-similarity fallback: every material has a default
spread-out OR profile keyed off its odor-family fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(slots=True)
class ORLigand:
    """One ligand binding one OR."""

    or_gene: str
    ec50_uM: float  # noqa: N815  half-max activating concentration
    hill: float = 1.0
    efficacy: float = 1.0  # 1.0 = full agonist, <1 partial, 0 antagonist


@dataclass(slots=True)
class ORArray:
    """Population of ORs we model. Default = 8 representative families."""

    or_genes: tuple[str, ...] = (
        "OR1A1",  # citrus / generic
        "OR2W1",  # aldehydic
        "OR5A1",  # ionone / floral
        "OR7D4",  # androstenone / musk-related
        "OR10G4",  # vanillin / sweet
        "OR11H7",  # isovaleric / sour
        "OR8B3",  # spicy
        "OR_WD",  # woody catch-all
    )

    def index(self, gene: str) -> int | None:
        try:
            return self.or_genes.index(gene)
        except ValueError:
            return None


# Family-to-OR-affinity fallback (no EC50 data → use these prior profiles).
# Each entry maps OR gene → relative EC50 in µM (lower = stronger binding).
# Calibrated so a single material at 1 µM in vapor produces ~50% activation
# of its primary OR.
_FAMILY_OR_PROFILE: dict[str, dict[str, float]] = {
    "citrus": {"OR1A1": 1.0, "OR2W1": 5.0, "OR_WD": 50.0},
    "aldehyde": {"OR2W1": 0.5, "OR1A1": 5.0},
    "floral": {"OR5A1": 1.0, "OR1A1": 10.0},
    "iris": {"OR5A1": 0.8, "OR_WD": 5.0},
    "musk": {"OR7D4": 1.5, "OR_WD": 3.0},
    "amber": {"OR_WD": 1.0, "OR10G4": 4.0},
    "wood": {"OR_WD": 1.0, "OR5A1": 8.0},
    "spice": {"OR8B3": 1.0, "OR2W1": 8.0},
    "green": {"OR1A1": 3.0, "OR2W1": 3.0},
    "gourmand": {"OR10G4": 0.8, "OR8B3": 5.0},
    "leather": {"OR11H7": 2.0, "OR_WD": 2.0},
    "ozone": {"OR2W1": 2.0, "OR1A1": 4.0},
    "default": {"OR_WD": 5.0, "OR1A1": 10.0, "OR5A1": 10.0},
}


def ligands_from_family(name: str, family: str | None) -> list[ORLigand]:
    profile = _FAMILY_OR_PROFILE.get((family or "default").lower(), _FAMILY_OR_PROFILE["default"])
    return [ORLigand(or_gene=g, ec50_uM=ec, hill=1.0, efficacy=1.0) for g, ec in profile.items()]


def or_occupancy(
    conc_uM: Mapping[str, float],  # noqa: N803  vapor concentration per material in µM
    ligand_table: Mapping[str, Sequence[ORLigand]],
    *,
    array: ORArray | None = None,
    adaptation: Mapping[str, float] | None = None,  # OR → 0..1 attenuation
) -> dict[str, float]:
    """Activation per OR ∈ [0, 1].

    `adaptation[k]` ∈ [0,1] reduces the apparent efficacy of all ligands at
    receptor k (post-Phase-5 Ca²⁺/GRK feedback).
    """
    arr = array or ORArray()
    out: dict[str, float] = {g: 0.0 for g in arr.or_genes}
    for or_gene in arr.or_genes:
        num = 0.0
        den = 1.0
        atten = 1.0 - (adaptation or {}).get(or_gene, 0.0)
        for material, c in conc_uM.items():
            if c <= 0:
                continue
            for lig in ligand_table.get(material, []) or []:
                if lig.or_gene != or_gene:
                    continue
                term = (c / max(lig.ec50_uM, 1e-9)) ** lig.hill
                num += term * lig.efficacy * atten
                den += term
        out[or_gene] = num / den
    return out


if __name__ == "__main__":
    arr = ORArray()
    ligands = {
        "Limonene": ligands_from_family("Limonene", "citrus"),
        "Hedione": ligands_from_family("Hedione", "floral"),
        "Iso E Super": ligands_from_family("Iso E Super", "wood"),
    }
    conc = {"Limonene": 5.0, "Hedione": 0.5, "Iso E Super": 2.0}  # µM
    R = or_occupancy(conc, ligands, array=arr)
    for g, v in R.items():
        print(f"{g}: R={v:.3f}")
