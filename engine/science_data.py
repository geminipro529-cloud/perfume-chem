"""Science data layer — olfactory adaptation, chemical stability, and solubility.

Adds physicochemical data that the temporal/synergy engines can consume:

  1. Olfactory adaptation timescales (minutes to significant anosmia)
  2. Chemical stability flags (autoxidation, Schiff base, photodegradation)
  3. Hansen solubility parameters (δD, δP, δH) where available
  4. Skin partition coefficients (stratum corneum / ethanol)

Sources: Ohloff (1994) Scent & Chemistry, Sell (2006) Chemistry of Fragrances,
         Hansen Solubility Parameters Handbook 2nd ed., CIR Safety Assessments,
         RIFM database (estimated where not directly available).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StabilityRisk(Enum):
    """Chemical stability risk classification."""
    STABLE = "stable"                    # >5yr unopened, >2yr opened
    MODERATE = "moderate"                # 2-5yr shelf life
    OXIDATION_PRONE = "oxidation_prone"  # autoxidation risk (terpenes, aldehydes)
    SCHIFF_BASE = "schiff_base"          # aldehyde + amine reactivity
    PHOTOLABILE = "photolabile"          # UV-degradable (furocoumarins, etc.)
    POLYMERIZES = "polymerizes"          # e.g. styrene derivatives at high T


@dataclass
class ScienceProfile:
    """Extended physicochemical data for one material."""
    name: str
    # Olfactory adaptation
    adaptation_tau_min: float | None = None     # minutes to 50% anosmia
    adaptation_pct: float | None = None         # % of population affected
    # Stability
    stability_class: StabilityRisk = StabilityRisk.STABLE
    autoxidation_half_life_weeks: float | None = None
    schiff_base_partners: list[str] | None = None  # materials that react
    photostability: str = "stable"              # stable / moderate / labile
    # Hansen solubility parameters (MPa^0.5)
    hansen_dd: float | None = None   # dispersion
    hansen_dp: float | None = None   # polar
    hansen_dh: float | None = None   # hydrogen bonding
    # Skin interaction
    skin_partition_coeff: float | None = None   # Kp stratum corneum/ethanol


# ── Olfactory adaptation data ──────────────────────────────────
# tau_min = time to 50% perceived intensity reduction
# pct = proportion of general population that becomes anosmic

_ADAPTATION_DATA: dict[str, dict] = {
    # Macrocyclic/polycyclic musks — rapid habituation
    "Iso E Super":      {"tau": 12,  "pct": 80, "note": "most people anosmic within 15 min"},
    "Galaxolide":       {"tau": 25,  "pct": 60, "note": "macrocyclic musk habituation"},
    "Habanolide":       {"tau": 28,  "pct": 50, "note": "macrolide adaptation"},
    "Cashmeran":        {"tau": 22,  "pct": 55, "note": "polycyclic musk; woody-musky"},
    "Musk T":           {"tau": 20,  "pct": 65, "note": "polycyclic musk rapid adaptation"},
    "Ethylene Brassylate": {"tau": 30, "pct": 45, "note": "macrolide, moderate adaptation"},
    # Woody/amber
    "Ambrox Super":     {"tau": 30, "pct": 40, "note": "ambergris-type, moderate adaptation"},
    "Vertofix Coeur":   {"tau": 35, "pct": 35},
    "Kephalis":         {"tau": 40, "pct": 30},
    "Timberol":         {"tau": 45, "pct": 25},
    # Coumarinic
    "Coumarin":         {"tau": 35, "pct": 30, "note": "coumarinic adaptation, moderate"},
    # Salicylates
    "Benzyl Salicylate": {"tau": 40, "pct": 25, "note": "cushion effect — slow adaptation"},
    "Hexyl Salicylate":  {"tau": 45, "pct": 20},
    # Bases and fixatives — very slow adaptation
    "Hedione":          {"tau": 180, "pct": 5, "note": "radiance hero; near-zero adaptation"},
    "Linalool":         {"tau": 120, "pct": 10},
    "Geraniol":         {"tau": 100, "pct": 10},
    "Phenethyl Alcohol": {"tau": 90, "pct": 15},
    # Citrus — rapid evaporation masks adaptation
    "Bergamot FCF":     {"tau": 90, "pct": 10},
    "D-Limonene":       {"tau": 60, "pct": 15},
    "Rose Absolute":    {"tau": 60, "pct": 15},
    "Patchouli EO":     {"tau": 50, "pct": 20},
    "Vetiver EO":       {"tau": 55, "pct": 20},
    # Indolic — complex adaptation (initial spike then plateau)
    "Indole":           {"tau": 15, "pct": 70, "note": "strong initial impact, rapid decay"},
}


# ── Chemical stability data ────────────────────────────────────

_STABILITY_DATA: dict[str, dict] = {
    # Oxidation-prone terpenes
    "D-Limonene":       {"class": "oxidation_prone", "t_half_wk": 3,
                         "note": "autoxidation → carvone + limonene oxide; allergen risk"},
    "Linalool":         {"class": "oxidation_prone", "t_half_wk": 5,
                         "note": "peroxidation → linalool hydroperoxide; skin sensitizer"},
    "Geraniol":         {"class": "oxidation_prone", "t_half_wk": 4},
    "Citral":           {"class": "oxidation_prone", "t_half_wk": 4,
                         "note": "aldehyde oxidation + Schiff base with amines"},
    "Citronellal":      {"class": "oxidation_prone", "t_half_wk": 6},
    # Aldehydes — Schiff base risk with amines
    "Aldehyde C10":     {"class": "schiff_base",
                         "partners": ["Indole", "Methyl Anthranilate"]},
    "Aldehyde C11":     {"class": "schiff_base",
                         "partners": ["Indole", "Methyl Anthranilate"]},
    "Aldehyde C12 MNA": {"class": "schiff_base",
                         "partners": ["Indole", "Methyl Anthranilate"]},
    "Hydroxycitronellal": {"class": "schiff_base",
                           "partners": ["Indole", "Methyl Anthranilate"],
                           "note": "slow reaction at room temperature"},
    "Cyclamen Aldehyde": {"class": "schiff_base",
                          "partners": ["Indole"]},
    # Photolabile
    "Bergamot FCF":     {"class": "moderate", "photo": "moderate",
                         "note": "FCF removes bergaptene but still UV-sensitive"},
    # Very stable synthetics
    "Iso E Super":      {"class": "stable"},
    "Hedione":          {"class": "stable"},
    "Galaxolide":       {"class": "stable"},
    "Benzyl Salicylate": {"class": "stable"},
    "Ambrox Super":     {"class": "stable"},
    "Coumarin":         {"class": "stable"},
    "Vanillin":         {"class": "stable", "note": "can yellow over time but odor stable"},
    "Evernyl":          {"class": "stable"},
}


# ── Hansen solubility parameters (estimated, MPa^0.5) ─────────
# These are estimates based on group contribution methods (Van Krevelen/Hoftyzer).
# True values require experimental determination.

_HANSEN_DATA: dict[str, dict[str, float]] = {
    "Ethanol":              {"dd": 15.8, "dp": 8.8, "dh": 19.4},
    "DPG":                  {"dd": 16.2, "dp": 10.6, "dh": 21.3},
    "IPM":                  {"dd": 15.1, "dp": 3.3, "dh": 4.5},
    "Benzyl Salicylate":    {"dd": 19.2, "dp": 6.8, "dh": 8.2},
    "Iso E Super":          {"dd": 16.8, "dp": 2.1, "dh": 2.4},
    "Hedione":              {"dd": 16.5, "dp": 4.2, "dh": 5.8},
    "Vanillin":             {"dd": 19.5, "dp": 11.4, "dh": 14.7},
    "Coumarin":             {"dd": 20.1, "dp": 9.8, "dh": 8.6},
    "Linalool":             {"dd": 16.0, "dp": 3.5, "dh": 10.2},
    "Galaxolide":           {"dd": 17.2, "dp": 2.8, "dh": 3.1},
    "Ambrox Super":         {"dd": 17.0, "dp": 2.5, "dh": 4.0},
    "Patchouli EO":         {"dd": 17.5, "dp": 3.0, "dh": 6.5},
    "D-Limonene":           {"dd": 17.2, "dp": 1.8, "dh": 4.3},
}


# ── Public API ─────────────────────────────────────────────────

def get_science_profile(name: str) -> ScienceProfile:
    """Build a ScienceProfile for *name*, merging adaptation + stability + Hansen."""
    prof = ScienceProfile(name=name)

    adapt = _ADAPTATION_DATA.get(name)
    if adapt:
        prof.adaptation_tau_min = adapt.get("tau")
        prof.adaptation_pct = adapt.get("pct")

    stab = _STABILITY_DATA.get(name)
    if stab:
        cls = stab.get("class", "stable")
        try:
            prof.stability_class = StabilityRisk(cls)
        except ValueError:
            prof.stability_class = StabilityRisk.MODERATE
        prof.autoxidation_half_life_weeks = stab.get("t_half_wk")
        prof.schiff_base_partners = stab.get("partners")
        prof.photostability = stab.get("photo", "stable")

    hansen = _HANSEN_DATA.get(name)
    if hansen:
        prof.hansen_dd = hansen.get("dd")
        prof.hansen_dp = hansen.get("dp")
        prof.hansen_dh = hansen.get("dh")

    return prof


def adaptation_penalty(name: str, concentration_pct: float) -> float:
    """Return an adaptation penalty factor (0.0=no penalty, 1.0=fully anosmic).

    High-concentration anosmia-prone materials get penalized more.
    Used by temporal engine to model perceived-intensity decay.
    """
    adapt = _ADAPTATION_DATA.get(name)
    if not adapt:
        return 0.0
    tau = adapt.get("tau", 180)
    pct = adapt.get("pct", 10) / 100.0
    # Penalty grows with concentration and population susceptibility
    # At low concentrations (<2%), adaptation is slower
    conc_factor = min(concentration_pct / 10.0, 1.0)
    return pct * conc_factor * (1.0 / (1.0 + tau / 30.0))


def stability_warnings(ingredient_names: list[str]) -> list[str]:
    """Return actionable stability warnings for a formula's ingredients.

    Checks:
      - Autoxidation-prone terpenes
      - Schiff base pairs (aldehyde + amine in same formula)
      - Photolabile materials
    """
    warnings: list[str] = []
    aldehydes: set[str] = set()
    amines: set[str] = set()

    for name in ingredient_names:
        stab = _STABILITY_DATA.get(name)
        if not stab:
            continue

        cls = stab.get("class", "stable")
        if cls == "oxidation_prone":
            t_half = stab.get("t_half_wk", "?")
            warnings.append(
                f"⚠ {name}: autoxidation t½ ≈ {t_half} weeks — "
                f"store cool, sealed, dark; add BHT 0.01% if >5% of formula"
            )

        if cls == "schiff_base":
            aldehydes.add(name)
            partners = stab.get("partners", [])
            for p in partners:
                if p in ingredient_names:
                    amines.add(p)

        photo = stab.get("photo", "stable")
        if photo in ("moderate", "labile"):
            warnings.append(
                f"⚠ {name}: photolabile ({photo}) — "
                f"protect from UV in final packaging"
            )

    # Cross-check Schiff base pairs
    if aldehydes and amines:
        for ald in aldehydes:
            for amine in amines:
                warnings.append(
                    f"⚠ Schiff base risk: {ald} + {amine} — "
                    f"possible yellowing and odor drift over months. "
                    f"Separate pre-blending or reduce contact time."
                )

    return warnings


def hansen_distance(mat_a: str, mat_b: str) -> float | None:
    """Hansen distance (Ra) between two materials. Lower = more compatible.

    Ra² = 4(δD₁-δD₂)² + (δP₁-δP₂)² + (δH₁-δH₂)²
    Returns None if either material lacks HSP data.
    """
    a = _HANSEN_DATA.get(mat_a)
    b = _HANSEN_DATA.get(mat_b)
    if not a or not b:
        return None
    ra2 = (4 * (a["dd"] - b["dd"]) ** 2 +
           (a["dp"] - b["dp"]) ** 2 +
           (a["dh"] - b["dh"]) ** 2)
    return ra2 ** 0.5
