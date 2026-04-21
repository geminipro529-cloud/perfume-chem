"""Temporal perfume evolution graph — high-resolution volatilization,
perception, projection, and character evolution visualization.

Physics stack:
  1. Raoult's law mixture evaporation with compositional shift
  2. Clausius-Clapeyron skin-temperature adjustment
  3. Odor Activity Value (OAV) perception modeling
  4. Stevens' power-law perceived intensity
  5. Diffusion-based projection/sillage envelope
  6. Character-dimension evolution (mass-weighted perceptual vectors)

Output: 4-panel matplotlib figure per formula showing:
  Panel 1 — Headspace composition (stacked area, % by material)
  Panel 2 — OAV perception intensity (log-scale lines, threshold at 1)
  Panel 3 — Projection envelope (sillage distance vs time)
  Panel 4 — Character evolution (12-dimension stacked area)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from engine.ingredient_intelligence import (
    get_profile, DIMENSIONS, MaterialProfile,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

SKIN_TEMP_K = 305.15       # 32°C skin surface
REF_TEMP_K = 298.15        # 25°C reference
R_GAS = 8.314              # J/(mol·K)
AVOGADRO = 6.022e23

# Projection model
MAX_PROJECTION_CM = 150    # fresh-spray sillage ~1.5 m
INTIMATE_CM = 10           # skin-scent zone
SPRAY_AREA_CM2 = 200       # approximate skin patch area for spray

# Near-skin concentration factor: the boundary layer directly above
# the skin film (0–5 cm) has ~5× higher vapor concentration than
# the far-field due to limited diffusion volume and convective
# body-heat currents.  Without this, base-note materials with
# VP < 0.01 Pa produce sub-ppb headspace values that never
# reach perception threshold despite being clearly smelled.
NEAR_SKIN_FACTOR = 5.0

# Stevens' power law exponent for olfaction (literature: 0.3–0.5)
STEVENS_EXPONENT = 0.4

# Time grid — adaptive resolution: fine at start, coarser later
# 0–30 min: every 1 min (30 pts), 30–120 min: every 5 min (18 pts),
# 2–8 hr: every 15 min (24 pts), 8–24 hr: every 30 min (32 pts)
# Total: 104 time points
def _build_time_grid() -> np.ndarray:
    """Build non-uniform time grid in hours with adaptive resolution."""
    t = []
    # Phase 1: 0–30 min, Δt = 1 min
    t.extend(np.arange(0, 0.5, 1 / 60))
    # Phase 2: 30–120 min, Δt = 5 min
    t.extend(np.arange(0.5, 2.0, 5 / 60))
    # Phase 3: 2–8 hr, Δt = 15 min
    t.extend(np.arange(2.0, 8.0, 0.25))
    # Phase 4: 8–24 hr, Δt = 30 min
    t.extend(np.arange(8.0, 24.5, 0.5))
    return np.array(sorted(set(round(x, 6) for x in t)))

TIME_GRID = _build_time_grid()


# ═══════════════════════════════════════════════════════════════════════════════
# Odor Detection Thresholds (ODT) — ppb in air
# Literature values where available; estimated where not.
# Sources: Arctander, Leffingwell, van Gemert, PerfumersWorld
# ═══════════════════════════════════════════════════════════════════════════════

_ODT_LITERATURE: dict[str, float] = {
    # ──────────────────────────────────────────────────────────────
    # Citrus / Top — high VP, moderate-to-high ODTs (ppb in air)
    # These reach the nose easily; their ODTs are relatively generous
    # ──────────────────────────────────────────────────────────────
    "Citral": 30.0,
    "Citronellal": 40.0,
    "D-Limonene": 10.0,
    "Linalool": 6.0,
    "Linalyl Acetate": 50.0,
    "Terpinyl Acetate": 80.0,
    "Hexyl Acetate": 2.0,
    "Aldehyde C10": 0.4,
    "Aldehyde C11": 0.5,
    "Aldehyde C11 undecylenic": 0.8,
    "Aldehyde C12 MNA": 0.1,
    "Methyl Pamplemousse": 3.0,
    "Bergamot EO": 15.0,
    "Bergamot FCF": 15.0,
    "Bergamot FCF oil Sicilian": 15.0,
    "Bergamot FCF Sicilian": 15.0,
    "Grapefruit FCF": 5.0,
    "Cedrat FCF oil Sicilian": 12.0,
    "Cedrat FCF Sicilian": 12.0,
    "Blood Orange oil Sicilian": 8.0,
    "Blood Orange Sicilian": 8.0,
    "Red Mandarin EO": 10.0,
    "Ethyl 2-Methylbutyrate": 0.06,
    # ──────────────────────────────────────────────────────────────
    # Green / Fresh — moderate VP, moderate ODTs
    # ──────────────────────────────────────────────────────────────
    "Dihydromyrcenol": 1.0,
    "cis-3-Hexenol": 70.0,
    "Verdox": 20.0,
    "Galbanum Resinoid": 5.0,
    "Cyclamen Aldehyde": 3.5,
    "Scentenal": 0.5,
    "Calone": 0.01,
    "Floralozone": 0.5,
    "Undecavertol": 10.0,
    "Dynascone": 0.3,
    "Parmavert": 15.0,
    "Leafovert": 8.0,
    "Allyl Amyl Glycolate": 2.0,
    "Melonal": 1.5,
    # ──────────────────────────────────────────────────────────────
    # Floral — heart materials need lower ODTs because VP is low.
    # Hedione, DBCA, muguet materials etc. are perceived despite
    # modest headspace because the olfactory system is hyper-
    # sensitive to their structural motifs.
    # ──────────────────────────────────────────────────────────────
    "Hedione": 1.0,               # radiance amplifier — ultra-low threshold
    "Hydroxycitronellal": 15.0,
    "Phenethyl Alcohol": 30.0,    # rosy but mild
    "Florol": 10.0,
    "Nympheal": 2.0,
    "Peonile": 5.0,
    "Aurantiol": 8.0,
    "Geraniol": 40.0,
    "Citronellol": 40.0,
    "Rose Oxide": 0.5,
    "Benzyl Salicylate": 5.0,     # diffusion cushion — mild but perceptible
    "Hexyl Salicylate": 3.0,      # lighter salicylate, transparent
    "Benzyl Benzoate": 200.0,     # genuinely mild fixative
    "Benzyl Acetate": 80.0,
    "Indole": 0.05,               # animalic trace — extremely potent
    "Bourgeonal": 4.0,
    "Freesia HDI": 3.0,
    "Lilyreal ND": 2.0,
    "Helional": 0.5,
    "Heliotropin Fleuressence": 3.0,
    "Petitgrain EO": 12.0,
    "Neroli EO": 10.0,
    "DBCA": 0.5,                  # powerful gardenia-rose character
    "Methyl Benzoate": 30.0,
    "Cis Jasmone": 5.0,
    "Methyl Salicylate": 40.0,
    "Methyl Anthranilate": 2.0,
    "Rose Absolute": 6.0,
    "Jasmine Absolute": 4.0,
    "Jasmine FO": 5.0,
    # ──────────────────────────────────────────────────────────────
    # Iris / Violet — irones and ionones have some of the lowest
    # ODTs of ALL odorants.  Alpha-irone detected at ~0.007-0.05 ppb
    # in air; beta-ionone even lower.  These materials overcome
    # tiny vapor pressures via extraordinary receptor affinity.
    # ──────────────────────────────────────────────────────────────
    "Alpha Irone": 0.05,          # one of the most potent odorants known
    "Alpha Ionone": 1.0,
    "Beta Ionone": 0.007,
    "Allyl Ionone": 3.0,
    "Irotyl": 1.0,
    "Dihydro Beta Ionone": 5.0,
    "Alpha-Isomethyl Ionone": 2.0,
    "Orivone": 0.5,               # warm orris, potent
    "Ultralia": 0.8,
    "I-IRIS F-TEC": 1.0,
    "Orris F-TEC": 1.0,
    "Violet Fleuressence": 3.0,
    "Carrot Seed EO": 12.0,
    "Methyl Ionone": 1.5,
    "Orris Butter Absolute": 0.01, # ultra-potent orris
    # ──────────────────────────────────────────────────────────────
    # Woods / Amber — these materials define modern perfumery
    # BECAUSE of their ultra-low detection thresholds.  Iso E Super
    # creates a "molecular cocoon" at sub-ppb airborne concentrations.
    # Ambrox detected at ~0.003 ppb.  Without lowered ODTs these
    # materials look subliminal despite being the backbone of
    # every modern formula.
    # ──────────────────────────────────────────────────────────────
    "Iso E Super": 0.5,           # molecular-cocoon cedar — famously low threshold
    "Cashmeran": 0.3,             # diffusive woody-musk — extremely potent
    "Cedramber": 0.5,
    "Cedamber": 0.5,
    "Ambermax": 1.0,
    "Amber Xtreme": 0.5,
    "Amber Core": 1.0,
    "Amber Core Accord": 1.0,
    "Ambrox Super": 0.01,         # crystalline amber — among the most potent bases
    "Ambrofix": 0.02,
    "Kephalis": 0.2,              # powerful woody-amber
    "Bacdanol": 1.0,              # creamy sandalwood
    "Ebanol": 0.5,
    "Sandalore": 0.8,
    "Vetival": 0.3,               # suede-vetiver
    "Vertofix Coeur": 0.5,        # woody-musky bridge
    "Vertofix": 0.5,
    "Suederal": 0.2,              # suede leather
    "Javanol": 0.3,               # premium sandalwood
    "Amberwood F": 0.5,
    "Timberol": 0.3,              # dry cedarwood
    "Koavone": 0.5,
    "Cedarwood EO": 1.0,
    "Cedarwood oil Virginia": 1.5,
    "Vetiver EO": 0.5,
    "Clearwood": 0.5,
    "Norlimbanol Dextro": 0.3,
    "Georgywood": 1.0,
    # ──────────────────────────────────────────────────────────────
    # Musks — macrocyclic and polycyclic musks have very low ODTs
    # (0.01–1 ppb in air).  They must, because their VP is near zero.
    # ──────────────────────────────────────────────────────────────
    "Galaxolide": 0.3,            # polycyclic musk — clean laundry
    "Tonalide": 0.5,
    "Ambrettolide": 0.5,          # macrocyclic musk
    "Habanolide": 0.2,
    "Zenolide": 0.5,
    "Exaltolide": 1.0,
    "Macrolide": 1.5,
    "Musk Ketone": 0.005,         # nitro musk — detectable at ppt levels
    "Romandolide": 0.5,
    "Ethylene Brassylate": 2.0,
    # ──────────────────────────────────────────────────────────────
    # Sweet / Gourmand — moderate-to-low ODTs.  Coumarin and vanillin
    # are universally recognized at low levels.
    # ──────────────────────────────────────────────────────────────
    "Ethyl Maltol": 3.0,
    "Coumarin": 0.5,              # hay-tonka, very recognizable
    "Vanillin": 2.0,              # universal sweetness anchor
    "Ethyl Vanillin": 0.5,
    "Maple Lactone": 3.0,
    "Raspberry Ketone": 5.0,
    "Benzoin Resinoid": 5.0,
    "Benzoin Sumatra Resinoid": 5.0,
    "Labdanum Absolute": 3.0,
    "Labdanum": 4.0,
    "Anisaldehyde": 30.0,
    "Gamma Decalactone": 5.0,
    "Gamma Undecalactone": 3.0,
    "Delta Decalactone": 4.0,
    "Siam Benzoin": 5.0,
    # ──────────────────────────────────────────────────────────────
    # Leather / Smoky
    # ──────────────────────────────────────────────────────────────
    "Isobutyl Quinoline": 0.1,    # dirty leather — potent
    "Birch Tar Rectified": 0.5,
    "Styrax FTEC": 3.0,
    "Guaiacol": 1.0,
    "Evernyl": 0.3,               # oakmoss replacement — tenacious
    # ──────────────────────────────────────────────────────────────
    # Spice / Aromatic
    # ──────────────────────────────────────────────────────────────
    "Black Pepper FTEC": 3.0,
    "Black Pepper materials": 3.0,
    "Cardamom FTEC": 5.0,
    "Pink Pepper Base": 5.0,
    "Ethyl Safranate": 0.5,
    "Eugenol": 6.0,
    "Isoeugenol": 3.0,
    "Cinnamaldehyde": 1.0,
    "Lavender EO": 5.0,
    "Patchouli EO": 1.0,          # patchouli — dark, tenacious
    "Myrrh EO": 5.0,
    "Olibanum Resinoid": 5.0,
    # ──────────────────────────────────────────────────────────────
    # Other / Specialty
    # ──────────────────────────────────────────────────────────────
    "Paradisamide": 1.0,
    "Blackcurrant FTEC": 3.0,
    "Dewberry FTEC": 5.0,
    "Leather FO": 5.0,
    "Tonka Bean FO": 5.0,
    "Sandalwood FO": 5.0,
    "Methyl Nonyl Ketone": 40.0,
    "Apritone": 3.0,
    "Lemonile": 2.0,
    "Orange Peel EO": 10.0,
    "Ylang Comoros Complete EO F3255": 5.0,
    "Ylang Comoros III EO F3295": 5.0,
    "Champaca Flower EO": 5.0,
    "Clary Sage EO": 10.0,
    "Cypriol EO": 2.0,
    "Oud Oil": 1.0,
    "Rum Absolute": 10.0,
    "Sandalwood EO": 3.0,
    "Castoreum Base": 0.5,
    "Civet Reconstitution Base": 0.3,
    "Skatole": 0.01,
}


def _estimate_odt(mw: float, vp: float, clogp: float,
                  character: dict[str, float]) -> float:
    """Estimate ODT when no literature value is available.

    Heuristic combining:
      - Higher VP → lower ODT (easier to reach nose)
      - Higher character intensity → lower ODT (more potent)
      - Higher MW → generally higher ODT (slower evaporation)
      - CLogP moderator (lipophilic = slower air-phase partitioning)
    """
    char_max = max(character.values()) if character else 3.0
    potency_factor = max(1.0, char_max)  # 1–10

    # Base estimation: inversely proportional to VP, proportional to MW
    if vp > 0:
        raw = 50.0 * (mw / 200.0) / (vp / 0.01) / (potency_factor / 5.0)
    else:
        raw = 200.0 * (mw / 200.0) / (potency_factor / 5.0)

    # CLogP adjustment: hydrophobic materials need to partition into air
    raw *= max(0.3, clogp / 3.0) if clogp else 1.0

    return max(0.01, min(5000.0, raw))


def get_odt(name: str, profile: MaterialProfile | None = None) -> float:
    """Get odor detection threshold for a material in ppb.

    Priority: literature value > estimation from physical properties.
    """
    # Check literature database
    odt = _ODT_LITERATURE.get(name)
    if odt is not None:
        return odt

    # Try profile odt field
    if profile and profile.odt is not None:
        return profile.odt

    # Estimate from physical properties
    if profile and profile.mw and profile.vp is not None:
        return _estimate_odt(
            profile.mw,
            profile.vp,
            profile.clogp or 3.0,
            profile.character,
        )

    # Ultimate fallback
    return 20.0


# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MaterialTemporal:
    """Per-material temporal data across all time points."""
    name: str
    note: str                          # top / heart / base
    headspace_pct: np.ndarray          # % of headspace at each time point
    headspace_ppb: np.ndarray          # ppb concentration in air
    oav: np.ndarray                    # Odor Activity Value at each time
    perceived_intensity: np.ndarray    # Stevens' law intensity
    odt: float                         # detection threshold (ppb)
    mw: float
    vp_skin: float                     # VP adjusted to skin temp
    character: dict[str, float]        # 12-dim character vector
    color: str                         # assigned color for plotting


@dataclass
class TemporalProfile:
    """Complete temporal evolution profile for a formula."""
    formula_name: str
    time_hours: np.ndarray                           # time grid
    materials: dict[str, MaterialTemporal]            # per-material data
    # Aggregate metrics
    total_headspace_ppb: np.ndarray                   # total concentration
    projection_cm: np.ndarray                         # sillage distance
    character_evolution: dict[str, np.ndarray]        # dim → intensity curve
    note_evolution: dict[str, np.ndarray]             # top/heart/base %
    # Summary
    opening_character: dict[str, float]
    drydown_character: dict[str, float]
    transitions: list[dict[str, Any]]
    perceptual_half_life_hr: float                    # when 50% of opening OAV lost
    longevity_hr: float                               # when total OAV drops < 2


# ═══════════════════════════════════════════════════════════════════════════════
# Temporal Engine — High-Resolution Mixture Evaporation
# ═══════════════════════════════════════════════════════════════════════════════

class TemporalEngine:
    """Simulates the temporal evolution of a perfume formula using
    mixture thermodynamics, OAV perception modeling, and physical
    diffusion for projection estimation.

    Physics:
        - Raoult's law partial pressures with composition shift
        - Clausius-Clapeyron skin-temp VP adjustment
        - Exponential evaporation with rate k ∝ VP_skin / MW
        - Headspace → ppb conversion assuming 1L air volume above skin
        - OAV = headspace_ppb / ODT
        - Perceived intensity = OAV^0.4 (Stevens)
        - Projection = f(total_vapor_flux)
    """

    def __init__(self, time_grid: np.ndarray | None = None):
        self.time_grid = time_grid if time_grid is not None else TIME_GRID

    def simulate(self, formula_name: str,
                 ingredients: dict[str, float]) -> TemporalProfile:
        """Run full temporal simulation.

        Args:
            formula_name: Name of the formula
            ingredients: {material_name: percentage_in_concentrate}

        Returns:
            TemporalProfile with all temporal data
        """
        n_times = len(self.time_grid)
        mat_data: dict[str, dict] = {}

        # ── Gather material properties ──
        for name, pct in ingredients.items():
            profile = get_profile(name)
            if profile is None:
                # Create minimal profile for unknown materials
                profile = MaterialProfile(
                    name=name,
                    character={"warmth": 3, "sweetness": 2},
                    mw=200.0,
                    vp=0.01,
                    clogp=3.0,
                    note="heart",
                )

            vp_25 = profile.vp if profile.vp is not None else 0.01
            mw = profile.mw if profile.mw is not None else 200.0

            # Adjust VP to skin temperature
            vp_skin = self._vp_to_skin(vp_25, mw)

            # Account for dilution — active dose
            active_pct = pct * profile.dilution

            odt = get_odt(name, profile)

            mat_data[name] = {
                "pct": active_pct,
                "pct_original": pct,
                "vp_skin": vp_skin,
                "vp_25": vp_25,
                "mw": mw,
                "note": profile.note,
                "character": profile.character,
                "odt": odt,
                "clogp": profile.clogp or 3.0,
            }

        # ── Simulate evaporation over time ──
        # Exponential decay per material: C(t) = C0 × exp(-k × t)
        # k = (VP_skin / MW) × scaling_factor
        # Headspace ∝ remaining_mass × VP_skin (Raoult's law simplified)
        headspace_raw = {}   # name → array of raw headspace values
        remaining = {}       # name → array of remaining mass fraction

        total_active = sum(d["pct"] for d in mat_data.values())
        if total_active == 0:
            total_active = 1.0

        for name, data in mat_data.items():
            k = (data["vp_skin"] / data["mw"]) * 10.0

            # Remaining mass at each time point
            rem = data["pct"] * np.exp(-k * self.time_grid)
            remaining[name] = rem

            # Headspace contribution ∝ remaining × VP (Raoult's)
            hs = rem * data["vp_skin"]
            headspace_raw[name] = hs

        # ── Compute headspace percentages ──
        total_hs = np.zeros(n_times)
        for hs in headspace_raw.values():
            total_hs += hs
        total_hs = np.maximum(total_hs, 1e-15)

        # ── Convert to ppb (approximate: 1 Pa → ~10,000 ppb at 1 atm) ──
        # P_partial / P_atm × 1e9 = ppb
        # But we need actual partial pressure in Pa
        # P_i(t) = x_i(t) × P_i°(T_skin) where x_i = mole fraction
        # Simplified: use the raw headspace value as proportional to ppb
        # Scale factor: normalize so that the total flux corresponds
        # to a realistic headspace concentration above skin
        # Typical total headspace for a fresh perfume: ~1000-10000 ppb

        # Initial total partial pressure sum (Pa)
        initial_total_pa = sum(
            d["pct"] * d["vp_skin"]
            for d in mat_data.values()
        )
        # ppb scaling: P_partial / 101325 × 1e9
        ppb_scale = 1e9 / 101325.0

        headspace_ppb = {}
        for name, data in mat_data.items():
            # Actual partial pressure (Pa) approximation
            partial_pa = remaining[name] / 100.0 * data["vp_skin"]
            headspace_ppb[name] = partial_pa * ppb_scale * NEAR_SKIN_FACTOR

        total_ppb = np.zeros(n_times)
        for ppb_arr in headspace_ppb.values():
            total_ppb += ppb_arr

        # ── OAV and perception ──
        oav_data = {}
        perceived_data = {}
        for name, data in mat_data.items():
            oav = headspace_ppb[name] / data["odt"]
            oav_data[name] = oav
            # Stevens' power law: intensity = OAV^exponent (only when OAV >= 1)
            perceived = np.where(oav >= 1.0, np.power(oav, STEVENS_EXPONENT), 0.0)
            perceived_data[name] = perceived

        # ── Projection / Sillage ──
        # Total vapor flux at t=0 defines max projection
        # Projection decays proportionally to sqrt of total flux ratio
        initial_flux = total_ppb[0] if total_ppb[0] > 0 else 1.0
        flux_ratio = total_ppb / initial_flux
        projection = INTIMATE_CM + (MAX_PROJECTION_CM - INTIMATE_CM) * np.sqrt(
            np.clip(flux_ratio, 0, 1)
        )

        # ── Note evolution (top/heart/base %) ──
        note_sums = {n: np.zeros(n_times) for n in ("top", "heart", "base")}
        for name, data in mat_data.items():
            note_sums[data["note"]] += headspace_raw[name]
        note_total = sum(note_sums.values())
        note_total = np.maximum(note_total, 1e-15)
        note_evolution = {
            n: arr / note_total * 100.0 for n, arr in note_sums.items()
        }

        # ── Character evolution (perceptual-weighted) ──
        char_evolution = {d: np.zeros(n_times) for d in DIMENSIONS}
        for name, data in mat_data.items():
            intensity = perceived_data[name]
            for dim in DIMENSIONS:
                score = data["character"].get(dim, 0.0)
                char_evolution[dim] += intensity * score

        # Normalize character evolution to percentages
        char_total = np.zeros(n_times)
        for arr in char_evolution.values():
            char_total += arr
        char_total = np.maximum(char_total, 1e-15)
        for dim in DIMENSIONS:
            char_evolution[dim] = char_evolution[dim] / char_total * 100.0

        # ── Assign colors ──
        colors = self._assign_colors(mat_data)

        # ── Build MaterialTemporal objects ──
        materials = {}
        for name, data in mat_data.items():
            materials[name] = MaterialTemporal(
                name=name,
                note=data["note"],
                headspace_pct=headspace_raw[name] / total_hs * 100.0,
                headspace_ppb=headspace_ppb[name],
                oav=oav_data[name],
                perceived_intensity=perceived_data[name],
                odt=data["odt"],
                mw=data["mw"],
                vp_skin=data["vp_skin"],
                character=data["character"],
                color=colors[name],
            )

        # ── Summary metrics ──
        # Opening character snapshot (t=0)
        opening = self._character_snapshot(char_evolution, 0)
        # Drydown snapshot (t ≈ 8hr)
        t8_idx = np.searchsorted(self.time_grid, 8.0)
        if t8_idx >= n_times:
            t8_idx = n_times - 1
        drydown = self._character_snapshot(char_evolution, t8_idx)

        # Transitions: when dominant note changes
        transitions = self._find_transitions(note_evolution)

        # Perceptual half-life
        total_perceived = np.zeros(n_times)
        for arr in perceived_data.values():
            total_perceived += arr
        initial_perceived = total_perceived[0] if total_perceived[0] > 0 else 1.0
        half_idx = np.searchsorted(-total_perceived, -initial_perceived / 2)
        half_life = self.time_grid[min(half_idx, n_times - 1)]

        # Longevity: when total OAV drops below threshold
        total_oav = np.zeros(n_times)
        for arr in oav_data.values():
            total_oav += arr
        longevity_mask = total_oav >= 2.0
        if np.any(longevity_mask):
            longevity_idx = np.where(longevity_mask)[0][-1]
            longevity = self.time_grid[longevity_idx]
        else:
            longevity = 0.0

        return TemporalProfile(
            formula_name=formula_name,
            time_hours=self.time_grid,
            materials=materials,
            total_headspace_ppb=total_ppb,
            projection_cm=projection,
            character_evolution=char_evolution,
            note_evolution=note_evolution,
            opening_character=opening,
            drydown_character=drydown,
            transitions=transitions,
            perceptual_half_life_hr=float(half_life),
            longevity_hr=float(longevity),
        )

    def _vp_to_skin(self, vp_25: float, mw: float) -> float:
        """Adjust VP from 25°C to skin temp (32°C) via Clausius-Clapeyron."""
        delta_h = 40000 + mw * 100  # J/mol (rough Trouton's)
        ln_ratio = (delta_h / R_GAS) * (1 / REF_TEMP_K - 1 / SKIN_TEMP_K)
        return vp_25 * math.exp(ln_ratio)

    def _assign_colors(self, mat_data: dict) -> dict[str, str]:
        """Assign distinct colors to each material based on note category."""
        # Color palettes per note
        top_colors = [
            "#FF6B35", "#FF9F1C", "#FFD166", "#F7B267",
            "#E8871E", "#FFAA5C", "#FF8C42", "#FFB347",
            "#F9A825", "#FF7043", "#FFA726", "#FFB74D",
        ]
        heart_colors = [
            "#7B2D8E", "#C77DFF", "#E040FB", "#AB47BC",
            "#9C27B0", "#BA68C8", "#CE93D8", "#8E24AA",
            "#7B1FA2", "#6A1B9A", "#4A148C", "#AA00FF",
            "#D500F9", "#E91E63", "#F06292", "#EC407A",
        ]
        base_colors = [
            "#1B4332", "#2D6A4F", "#40916C", "#52796F",
            "#354F52", "#3A5A40", "#4E6E58", "#588157",
            "#6B705C", "#7F8B52", "#5F7161", "#344E41",
        ]

        counters = {"top": 0, "heart": 0, "base": 0}
        palettes = {"top": top_colors, "heart": heart_colors, "base": base_colors}
        colors = {}

        for name, data in mat_data.items():
            note = data["note"]
            palette = palettes.get(note, heart_colors)
            idx = counters.get(note, 0)
            colors[name] = palette[idx % len(palette)]
            counters[note] = idx + 1

        return colors

    def _character_snapshot(self, char_evo: dict[str, np.ndarray],
                            idx: int) -> dict[str, float]:
        """Get character dimension values at a specific time index."""
        return {dim: round(float(arr[idx]), 1) for dim, arr in char_evo.items()}

    def _find_transitions(self, note_evo: dict[str, np.ndarray]) -> list[dict]:
        """Find note-category transitions over time."""
        transitions = []
        prev_dominant = None
        for i in range(len(self.time_grid)):
            vals = {n: note_evo[n][i] for n in ("top", "heart", "base")}
            dominant = max(vals, key=vals.get)
            if prev_dominant is not None and dominant != prev_dominant:
                transitions.append({
                    "from": prev_dominant,
                    "to": dominant,
                    "at_hours": round(float(self.time_grid[i]), 2),
                    "at_label": self._format_time(self.time_grid[i]),
                })
            prev_dominant = dominant
        return transitions

    @staticmethod
    def _format_time(hours: float) -> str:
        """Format hours into human-readable label."""
        if hours < 1 / 60:
            return "0min"
        if hours < 1:
            return f"{int(hours * 60)}min"
        if hours == int(hours):
            return f"{int(hours)}hr"
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}hr{m:02d}min"


# ═══════════════════════════════════════════════════════════════════════════════
# Visualization — 6-Panel Temporal Graph with Synergy Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TemporalVisualizer:
    """Generate 6-panel temporal evolution graphs with synergy integration.

    Layout (3×2 grid):
      Row 1: Material Lifecycle Timeline  |  OAV Perception Heatmap
      Row 2: Perceived Composition        |  Olfactive Character Evolution
      Row 3: Projection Envelope          |  Synergy Map

    Educational features:
      - Phase markers across all time-axis panels
      - Material lifecycle shows exactly when each ingredient is perceptible
      - OAV heatmap reveals ALL materials simultaneously
      - Synergy matrix identifies reinforcing/clashing material pairs
      - Inline annotations explain key olfactive phenomena
    """

    # ── Style ──
    BG_COLOR = "#0F1419"
    PANEL_BG = "#171D26"
    GRID_COLOR = "#252D3A"
    TEXT_COLOR = "#D0D7E3"
    MUTED_TEXT = "#7E8A9E"
    ACCENT_COLOR = "#5B9BD5"
    THRESHOLD_COLOR = "#FF6B6B"

    NOTE_COLORS = {
        "top": "#FF9F1C",
        "heart": "#C77DFF",
        "base": "#40916C",
    }
    NOTE_LABELS = {
        "top": "TOP",
        "heart": "HEART",
        "base": "BASE",
    }

    # Phase definitions (hours)
    PHASES = [
        (0.0, 0.083, "SPRAY", "#FF9F1C"),
        (0.083, 0.5, "TOP BURST", "#FFD166"),
        (0.5, 2.0, "DEVELOPMENT", "#C77DFF"),
        (2.0, 6.0, "HEART", "#AB47BC"),
        (6.0, 12.0, "DRYDOWN", "#40916C"),
        (12.0, 24.0, "SKIN SCENT", "#6B705C"),
    ]

    def plot(
        self,
        profile: TemporalProfile,
        save_path: str | Path | None = None,
        show: bool = False,
        dpi: int = 150,
        synergy_data: dict | None = None,
    ) -> Any:
        """Generate the full 6-panel temporal graph.

        Args:
            profile: TemporalProfile from TemporalEngine.simulate()
            save_path: Optional file path to save the figure
            show: Whether to call plt.show()
            dpi: Resolution
            synergy_data: Optional dict of {(name_a,name_b): weight}
                          from SynergyGraph.edges — pass
                          {k: e.weight for k, e in sg.edges.items()}

        Returns:
            matplotlib Figure object
        """
        import matplotlib
        if not show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec

        fig = plt.figure(figsize=(26, 24))
        fig.patch.set_facecolor(self.BG_COLOR)

        gs = gridspec.GridSpec(
            3, 2, figure=fig,
            height_ratios=[1.15, 1.0, 1.0],
            hspace=0.30, wspace=0.22,
        )

        t = profile.time_hours

        # ── Title block ──
        fig.suptitle(
            f"TEMPORAL EVOLUTION — {profile.formula_name}",
            color=self.TEXT_COLOR, fontsize=20, fontweight="bold",
            y=0.98, fontfamily="monospace",
        )

        perceptible = sum(
            1 for m in profile.materials.values() if np.max(m.oav) >= 1.0
        )
        subliminal = len(profile.materials) - perceptible

        fig.text(
            0.5, 0.960,
            f"Half-Life: {profile.perceptual_half_life_hr:.1f}hr  ·  "
            f"Longevity: {profile.longevity_hr:.1f}hr  ·  "
            f"Materials: {len(profile.materials)} "
            f"({perceptible} perceptible, {subliminal} subliminal)",
            ha="center", color=self.MUTED_TEXT, fontsize=11,
            fontfamily="monospace",
        )

        # ── 6 panels ──
        ax_life = fig.add_subplot(gs[0, 0])
        ax_hmap = fig.add_subplot(gs[0, 1])
        ax_comp = fig.add_subplot(gs[1, 0])
        ax_char = fig.add_subplot(gs[1, 1])
        ax_proj = fig.add_subplot(gs[2, 0])
        ax_syn  = fig.add_subplot(gs[2, 1])

        self._plot_lifecycle(ax_life, profile, t)
        self._plot_oav_heatmap(ax_hmap, profile, t)
        self._plot_headspace(ax_comp, profile, t)
        self._plot_character(ax_char, profile, t)
        self._plot_projection(ax_proj, profile, t)
        self._plot_synergy(ax_syn, profile, synergy_data)

        if save_path:
            fig.savefig(save_path, dpi=dpi, bbox_inches="tight",
                        facecolor=fig.get_facecolor(), edgecolor="none")
        if show:
            plt.show()

        return fig

    # ── Shared helpers ─────────────────────────────────────────────────────

    def _style_axis(self, ax, title: str, *, fontsize: int = 13):
        """Apply dark theme styling to an axis."""
        ax.set_facecolor(self.PANEL_BG)
        ax.set_title(title, color=self.TEXT_COLOR, fontsize=fontsize,
                      fontweight="bold", pad=12, fontfamily="monospace")
        ax.tick_params(colors=self.TEXT_COLOR, labelsize=9)
        ax.grid(True, color=self.GRID_COLOR, alpha=0.4, linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(self.GRID_COLOR)
        ax.xaxis.label.set_color(self.TEXT_COLOR)
        ax.yaxis.label.set_color(self.TEXT_COLOR)

    def _time_formatter(self):
        from matplotlib.ticker import FuncFormatter

        def fmt(x, _):
            if x < 1:
                return f"{int(x * 60)}m"
            if x == int(x):
                return f"{int(x)}h"
            return f"{x:.1f}h"
        return FuncFormatter(fmt)

    def _add_phase_bands(self, ax, y_top: float | None = None):
        """Draw subtle phase shading bands on a time-axis panel."""
        for start, end, label, color in self.PHASES:
            ax.axvspan(start, end, color=color, alpha=0.04, zorder=0)
            if y_top is not None:
                ax.text(
                    (start + end) / 2, y_top, label,
                    color=color, fontsize=5.5, ha="center", va="bottom",
                    fontfamily="monospace", alpha=0.6,
                )

    # ── Panel 1: Material Lifecycle Timeline ───────────────────────────────

    def _plot_lifecycle(self, ax, profile: TemporalProfile, t: np.ndarray):
        """Horizontal bars showing when each material is above perception
        threshold (OAV ≥ 1).  Ordered by note → first-appearance time.
        Bar brightness encodes peak OAV intensity.

        Educational: immediately shows the relay of materials — which
        ingredients the nose detects and when they hand off.
        """
        self._style_axis(ax, "MATERIAL LIFECYCLE  (OAV ≥ 1 = perceptible)")
        ax.grid(False)

        # Separate perceptible from subliminal
        all_mats = list(profile.materials.values())
        note_order = {"top": 0, "heart": 1, "base": 2}

        def first_above(m):
            idxs = np.where(m.oav >= 1.0)[0]
            return float(t[idxs[0]]) if len(idxs) > 0 else 99.0

        sorted_mats = sorted(
            all_mats,
            key=lambda m: (note_order.get(m.note, 1), first_above(m)),
        )

        perceptible = [m for m in sorted_mats if np.max(m.oav) >= 1.0]
        subliminal  = [m for m in sorted_mats if np.max(m.oav) < 1.0]

        # Color palette per note (softer, higher contrast)
        bar_bases = {"top": "#FF9F1C", "heart": "#B37ADB", "base": "#52B788"}

        y = 0
        yticks, yticklabels = [], []
        current_note = None

        for m in perceptible:
            # Note-group separator
            if m.note != current_note:
                if current_note is not None:
                    ax.axhline(y - 0.5, color=self.GRID_COLOR,
                               linewidth=0.5, alpha=0.5)
                    ax.text(-0.2, y, self.NOTE_LABELS.get(m.note, ""),
                            color=self.NOTE_COLORS.get(m.note, "#888"),
                            fontsize=7, fontweight="bold",
                            fontfamily="monospace", ha="right", va="bottom",
                            clip_on=False)
                current_note = m.note

            # Find contiguous OAV ≥ 1 ranges
            active = m.oav >= 1.0
            starts, ends = [], []
            in_range = False
            for i in range(len(t)):
                if active[i] and not in_range:
                    starts.append(t[i])
                    in_range = True
                elif not active[i] and in_range:
                    ends.append(t[i])
                    in_range = False
            if in_range:
                ends.append(t[-1])

            # Determine alpha from peak OAV (more impactful = brighter)
            peak_oav = float(np.max(m.oav))
            log_peak = min(math.log10(max(peak_oav, 1.0)) / 3.0, 1.0)
            alpha = 0.45 + 0.50 * log_peak
            base_color = bar_bases.get(m.note, "#888888")

            for s, e in zip(starts, ends):
                ax.barh(y, e - s, left=s, height=0.65,
                        color=base_color, alpha=alpha,
                        edgecolor="#00000033", linewidth=0.3)

            # Peak OAV annotation
            peak_idx = int(np.argmax(m.oav))
            peak_t = float(t[peak_idx])
            ax.text(min(peak_t + 0.3, 23.5), y, f"×{peak_oav:.0f}",
                    color=self.TEXT_COLOR, fontsize=5.5,
                    fontfamily="monospace", va="center", alpha=0.8)

            yticks.append(y)
            yticklabels.append(m.name)
            y += 1

        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, fontsize=6, fontfamily="monospace",
                           color=self.TEXT_COLOR)
        ax.set_xlim(0, 24)
        ax.set_ylim(-0.5, y - 0.5)
        ax.invert_yaxis()
        ax.set_xlabel("Time", fontsize=10)
        ax.xaxis.set_major_formatter(self._time_formatter())
        self._add_phase_bands(ax)

        # Subliminal note
        if subliminal:
            names = ", ".join(m.name for m in subliminal)
            ax.text(
                0.5, -0.06,
                f"Subliminal ({len(subliminal)}): {names}",
                transform=ax.transAxes, fontsize=6, ha="center",
                color=self.THRESHOLD_COLOR, fontfamily="monospace",
                alpha=0.7,
            )

    # ── Panel 2: OAV Perception Heatmap ────────────────────────────────────

    def _plot_oav_heatmap(self, ax, profile: TemporalProfile,
                          t: np.ndarray):
        """Heatmap showing OAV for ALL materials over time.  Replaces the
        old 15-line spaghetti plot with a complete view — every material
        visible, perception threshold clearly marked by the color break.

        Color: below OAV=1 → cool/dark, above → warm/bright.
        Educational: reveals which materials dominate perception at each
        phase and which are always subliminal.
        """
        import matplotlib.colors as mcolors

        self._style_axis(ax, "OAV PERCEPTION MAP  (all materials)")

        note_order = {"top": 0, "heart": 1, "base": 2}
        sorted_mats = sorted(
            profile.materials.values(),
            key=lambda m: (note_order.get(m.note, 1), -np.max(m.oav)),
        )

        n_mats = len(sorted_mats)
        names = [m.name for m in sorted_mats]
        notes = [m.note for m in sorted_mats]

        # Build OAV matrix (materials × time), log-scaled
        oav_matrix = np.array([
            np.log10(np.maximum(m.oav, 1e-3)) for m in sorted_mats
        ])

        # Custom diverging colormap: below threshold = cool, above = warm
        # OAV=1 → log10=0 — the pivot
        cmap_colors = [
            (0.0, "#0D1117"),      # OAV ≈ 0.001 — invisible
            (0.2, "#1A2744"),      # OAV ≈ 0.01 — barely there
            (0.35, "#2A4A6B"),     # OAV ≈ 0.1 — hint
            (0.42, "#3A6B8C"),     # approaching threshold
            (0.50, "#FFE0B2"),     # OAV = 1.0 — threshold break
            (0.60, "#FFB74D"),     # OAV ≈ 10
            (0.72, "#FF8A65"),     # OAV ≈ 100
            (0.85, "#EF5350"),     # OAV ≈ 1000
            (1.0, "#D32F2F"),      # OAV > 10000
        ]
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "oav_perception",
            [(pos, col) for pos, col in cmap_colors],
        )

        # OAV range: log10 spans roughly -3 to +4
        vmin, vmax = -3.0, 4.0

        mesh = ax.pcolormesh(
            t, np.arange(n_mats), oav_matrix,
            cmap=cmap, vmin=vmin, vmax=vmax, shading="nearest",
        )

        # Y-axis labels colored by note
        ax.set_yticks(range(n_mats))
        label_colors = [self.NOTE_COLORS.get(n, self.TEXT_COLOR) for n in notes]
        ax.set_yticklabels(names, fontsize=5.5, fontfamily="monospace")
        for lbl, col in zip(ax.get_yticklabels(), label_colors):
            lbl.set_color(col)

        ax.set_xlim(0, 24)
        ax.set_ylim(-0.5, n_mats - 0.5)
        ax.invert_yaxis()
        ax.set_xlabel("Time", fontsize=10)
        ax.xaxis.set_major_formatter(self._time_formatter())
        self._add_phase_bands(ax)

        # Colorbar
        import matplotlib.pyplot as plt
        cbar = plt.colorbar(mesh, ax=ax, pad=0.02, aspect=30)
        cbar.set_label("log₁₀(OAV)", color=self.MUTED_TEXT, fontsize=9)
        cbar.ax.tick_params(colors=self.MUTED_TEXT, labelsize=7)
        # Mark threshold on colorbar
        cbar.ax.axhline(0.0, color="#FFFFFF", linewidth=1.5, alpha=0.8)
        cbar.ax.text(1.8, 0.0, "OAV=1", color="#FFFFFF", fontsize=6,
                     va="center", fontfamily="monospace")

        # Note-group separators
        prev_note = None
        for i, note in enumerate(notes):
            if prev_note is not None and note != prev_note:
                ax.axhline(i - 0.5, color="#FFFFFF", linewidth=0.5, alpha=0.3)
            prev_note = note

    # ── Panel 3: Perceived Composition ─────────────────────────────────────

    def _plot_headspace(self, ax, profile: TemporalProfile, t: np.ndarray):
        """Stacked area chart of PERCEIVED composition using Stevens'
        power-law compression (OAV^0.4).  Shows each material's perceptual
        contribution — what the nose actually registers, not raw vapor.

        Educational: base notes with ultra-low ODT appear here even though
        their headspace concentration is tiny — perception ≠ concentration.
        """
        self._style_axis(ax, "PERCEIVED COMPOSITION (%)")

        all_mats = list(profile.materials.values())
        perceived_w = {}
        for m in all_mats:
            pw = np.power(np.maximum(m.oav, 0.01), STEVENS_EXPONENT)
            perceived_w[m.name] = pw

        total_pw = np.zeros_like(t)
        for pw in perceived_w.values():
            total_pw += pw
        total_pw = np.maximum(total_pw, 1e-15)

        perceived_pct = {n: pw / total_pw * 100.0
                         for n, pw in perceived_w.items()}

        sorted_mats = sorted(
            all_mats,
            key=lambda m: (
                {"top": 0, "heart": 1, "base": 2}.get(m.note, 1),
                -perceived_pct[m.name][0],
            ),
        )

        # Show materials with >2% perceived contribution at any time
        visible = [m for m in sorted_mats
                   if np.max(perceived_pct[m.name]) > 2.0]
        other_pct = np.zeros_like(t)
        for m in sorted_mats:
            if m not in visible:
                other_pct += perceived_pct[m.name]

        ys = np.array([perceived_pct[m.name] for m in visible])
        if len(other_pct[other_pct > 0.5]) > 0:
            ys = np.vstack([ys, other_pct])

        colors = [m.color for m in visible]
        labels = [f"{m.name} [{m.note[0].upper()}]" for m in visible]
        if len(other_pct[other_pct > 0.5]) > 0:
            colors.append("#444444")
            labels.append("Other (<2%)")

        ax.stackplot(t, ys, colors=colors, alpha=0.85, linewidth=0.3,
                      edgecolor="#00000033")

        ax.legend(labels, loc="upper right", fontsize=5.5,
                  facecolor=self.PANEL_BG, edgecolor=self.GRID_COLOR,
                  labelcolor=self.TEXT_COLOR, ncol=2, framealpha=0.9)

        ax.set_xlim(0, 24)
        ax.set_ylim(0, 100)
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("Perceived %", fontsize=10)
        ax.xaxis.set_major_formatter(self._time_formatter())
        self._add_phase_bands(ax, y_top=101)

        # Transition markers
        for tr in profile.transitions:
            ax.axvline(tr["at_hours"], color=self.ACCENT_COLOR,
                       linestyle="--", alpha=0.5, linewidth=0.8)
            ax.text(tr["at_hours"], 103,
                    f"{tr['from']}→{tr['to']}",
                    color=self.ACCENT_COLOR, fontsize=7, ha="center",
                    fontfamily="monospace")

        # Educational annotation: explain Stevens' law
        ax.text(
            0.02, 0.02,
            "Perception ≠ concentration — Stevens' law: intensity ~ OAV⁰·⁴",
            transform=ax.transAxes, fontsize=6, color=self.MUTED_TEXT,
            fontfamily="monospace", alpha=0.7,
        )

    # ── Panel 4: Character Evolution ───────────────────────────────────────

    def _plot_character(self, ax, profile: TemporalProfile, t: np.ndarray):
        """12-dimension character evolution with driver annotations.

        Educational: shows HOW the scent's character shifts over time,
        with the dominant dimension labeled at key moments.
        """
        self._style_axis(ax, "OLFACTIVE CHARACTER EVOLUTION")

        dim_colors = {
            "warmth": "#FF6B35",  "sweetness": "#FFD166",
            "freshness": "#06D6A0", "powdery": "#E0AFA0",
            "green": "#52B788",   "animalic": "#6B4226",
            "radiance": "#FFE66D", "woody": "#8B5E3C",
            "spicy": "#D62828",   "floral": "#E040FB",
            "smoky": "#6C757D",   "creamy": "#FEFAE0",
        }

        dim_totals = {
            d: float(np.sum(profile.character_evolution[d]))
            for d in DIMENSIONS
        }
        sorted_dims = sorted(DIMENSIONS, key=lambda d: dim_totals[d],
                             reverse=True)

        visible_dims = [d for d in sorted_dims
                        if np.max(profile.character_evolution[d]) > 2.0]

        ys = np.array([profile.character_evolution[d] for d in visible_dims])
        colors = [dim_colors.get(d, "#888888") for d in visible_dims]

        ax.stackplot(t, ys, colors=colors, alpha=0.8, linewidth=0.3,
                      edgecolor="#00000022",
                      labels=[d.capitalize() for d in visible_dims])

        ax.set_xlim(0, 24)
        ax.set_ylim(0, 100)
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("Character %", fontsize=10)
        ax.xaxis.set_major_formatter(self._time_formatter())
        self._add_phase_bands(ax, y_top=101)

        ax.legend(loc="upper right", fontsize=5.5,
                  facecolor=self.PANEL_BG, edgecolor=self.GRID_COLOR,
                  labelcolor=self.TEXT_COLOR, ncol=3, framealpha=0.9)

        # Key-moment driver annotations
        opening = profile.opening_character
        top_open = max(opening, key=opening.get)
        drydown = profile.drydown_character
        top_dry = max(drydown, key=drydown.get)

        ax.text(
            0.5, -0.10,
            f"Opening: {top_open} ({opening[top_open]:.0f}%)  →  "
            f"Drydown: {top_dry} ({drydown[top_dry]:.0f}%)",
            transform=ax.transAxes, color=self.MUTED_TEXT,
            fontsize=9, ha="center", fontfamily="monospace",
        )

    # ── Panel 5: Projection Envelope ───────────────────────────────────────

    def _plot_projection(self, ax, profile: TemporalProfile,
                         t: np.ndarray):
        """Projection/sillage envelope — simplified, with human-scale
        annotations ('arm's length', 'across the room') and clear zone
        bands.  No confusing twin-axis overlay.
        """
        self._style_axis(ax, "PROJECTION ENVELOPE (sillage)")

        projection = profile.projection_cm

        # Fill gradient
        ax.fill_between(t, 0, projection,
                        color=self.ACCENT_COLOR, alpha=0.12)
        ax.plot(t, projection,
                color=self.ACCENT_COLOR, linewidth=2.5, alpha=0.9)

        # Zone bands with human-scale labels
        zones = [
            (100, 150, "SILLAGE CLOUD · across the room", "#FF9F1C"),
            (30, 100, "SOCIAL · arm's length", "#C77DFF"),
            (10, 30, "INTIMATE · close contact", "#40916C"),
            (0, 10, "SKIN SCENT · touching", "#6B705C"),
        ]
        for low, high, label, color in zones:
            ax.axhspan(low, high, color=color, alpha=0.05)
            ax.text(23.5, (low + high) / 2, label,
                    color=color, fontsize=6.5, ha="right",
                    fontfamily="monospace", alpha=0.6, va="center")

        # Key time markers
        for hrs, label in [(0.25, "15min"), (1, "1hr"), (4, "4hr"),
                           (8, "8hr"), (12, "12hr")]:
            idx = int(np.searchsorted(t, hrs))
            if idx < len(projection):
                val = float(projection[idx])
                ax.annotate(
                    f"{val:.0f}cm",
                    (hrs, val), textcoords="offset points",
                    xytext=(0, 12), ha="center",
                    color=self.TEXT_COLOR, fontsize=7,
                    fontfamily="monospace",
                    arrowprops=dict(arrowstyle="-", color="#555"),
                )

        ax.set_xlim(0, 24)
        ax.set_ylim(0, MAX_PROJECTION_CM * 1.1)
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("Projection (cm)", fontsize=10)
        ax.xaxis.set_major_formatter(self._time_formatter())
        self._add_phase_bands(ax)

        # Educational note
        ax.text(
            0.02, 0.02,
            "Projection ∝ √(total vapor flux) — high-VP top notes drive initial sillage",
            transform=ax.transAxes, fontsize=6, color=self.MUTED_TEXT,
            fontfamily="monospace", alpha=0.7,
        )

    # ── Panel 6: Synergy Map ───────────────────────────────────────────────

    def _plot_synergy(self, ax, profile: TemporalProfile,
                      synergy_data: dict | None):
        """Pairwise synergy matrix heatmap showing which materials
        reinforce or clash with each other.

        Green = synergy (materials enhance each other)
        Red = clash (materials fight)
        Grey = neutral / no interaction

        Educational: reveals the hidden accord architecture — which
        materials are working together vs competing.
        """
        import matplotlib.colors as mcolors

        self._style_axis(ax, "SYNERGY MAP  (pairwise interactions)")
        ax.grid(False)

        if synergy_data is None:
            # No synergy data provided — show instructions
            ax.text(
                0.5, 0.5,
                "Synergy data not provided.\n\n"
                "Pass synergy_data to plot():\n"
                "  sg = SynergyGraph()\n"
                "  sg.build(ingredient_names)\n"
                "  synergy_data = {\n"
                "      k: e.weight\n"
                "      for k, e in sg.edges.items()\n"
                "  }",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=9, color=self.MUTED_TEXT,
                fontfamily="monospace", alpha=0.7,
            )
            return

        # Build ordered material list (by note)
        note_order = {"top": 0, "heart": 1, "base": 2}
        sorted_mats = sorted(
            profile.materials.values(),
            key=lambda m: (note_order.get(m.note, 1), m.name),
        )
        names = [m.name for m in sorted_mats]
        notes = [m.note for m in sorted_mats]
        n = len(names)

        # Build matrix
        matrix = np.zeros((n, n))
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                if i != j:
                    key = tuple(sorted((a, b)))
                    matrix[i, j] = synergy_data.get(key, 0.0)

        # Diverging colormap: red → dark → green
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "synergy",
            [
                (0.0, "#D32F2F"),   # strong clash
                (0.3, "#5D3A3A"),   # mild clash
                (0.5, "#1A1F2E"),   # neutral (panel bg)
                (0.7, "#2E5A3A"),   # mild synergy
                (1.0, "#4CAF50"),   # strong synergy
            ],
        )

        im = ax.imshow(
            matrix, cmap=cmap, vmin=-1.0, vmax=1.0,
            aspect="auto", interpolation="nearest",
        )

        # Labels
        ax.set_xticks(range(n))
        ax.set_xticklabels(
            [nm[:14] for nm in names], rotation=55, ha="right",
            fontsize=4.5, fontfamily="monospace", color=self.TEXT_COLOR,
        )
        ax.set_yticks(range(n))
        ax.set_yticklabels(
            [nm[:14] for nm in names],
            fontsize=4.5, fontfamily="monospace",
        )
        # Color labels by note
        label_cols = [self.NOTE_COLORS.get(nt, self.TEXT_COLOR) for nt in notes]
        for lbl, col in zip(ax.get_yticklabels(), label_cols):
            lbl.set_color(col)
        for lbl, col in zip(ax.get_xticklabels(), label_cols):
            lbl.set_color(col)

        # Note-group separators
        prev_note = None
        for i, note in enumerate(notes):
            if prev_note is not None and note != prev_note:
                ax.axhline(i - 0.5, color="#FFFFFF", linewidth=0.5,
                           alpha=0.3)
                ax.axvline(i - 0.5, color="#FFFFFF", linewidth=0.5,
                           alpha=0.3)
            prev_note = note

        # Colorbar
        import matplotlib.pyplot as plt
        cbar = plt.colorbar(im, ax=ax, pad=0.02, aspect=30,
                            shrink=0.85)
        cbar.set_label("Synergy ← 0 → Clash", color=self.MUTED_TEXT,
                       fontsize=8)
        cbar.ax.tick_params(colors=self.MUTED_TEXT, labelsize=7)

        # Top synergy pairs callout
        top_pairs = sorted(
            synergy_data.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )[:3]
        if top_pairs:
            callout = "  |  ".join(
                f"{a[:10]}↔{b[:10]} ({w:+.2f})"
                for (a, b), w in top_pairs if w > 0
            )
            if callout:
                ax.text(
                    0.5, -0.10,
                    f"Top synergies: {callout}",
                    transform=ax.transAxes, fontsize=6, ha="center",
                    color="#4CAF50", fontfamily="monospace", alpha=0.8,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Summary Report Generator
# ═══════════════════════════════════════════════════════════════════════════════

def temporal_report(profile: TemporalProfile) -> str:
    """Generate a text summary of the temporal profile."""
    lines = [
        f"═══ TEMPORAL REPORT: {profile.formula_name} ═══",
        "",
        f"Perceptual half-life: {profile.perceptual_half_life_hr:.1f} hr",
        f"Longevity (OAV > 2):  {profile.longevity_hr:.1f} hr",
        f"Materials:            {len(profile.materials)}",
        "",
    ]

    # Transitions
    if profile.transitions:
        lines.append("─── Note Transitions ───")
        for tr in profile.transitions:
            lines.append(f"  {tr['at_label']}: {tr['from']} → {tr['to']}")
        lines.append("")

    # Top perceived materials at key timepoints
    for hrs, label in [(0, "Opening"), (1, "1hr"), (4, "4hr"), (8, "Drydown")]:
        idx = int(np.searchsorted(profile.time_hours, hrs))
        if idx >= len(profile.time_hours):
            idx = len(profile.time_hours) - 1

        lines.append(f"─── {label} (t={label if hrs > 0 else '0min'}) ───")

        # Top 5 by OAV at this timepoint
        mats_at_t = sorted(
            profile.materials.values(),
            key=lambda m: m.oav[idx],
            reverse=True,
        )
        for m in mats_at_t[:5]:
            oav_val = m.oav[idx]
            pct_val = m.headspace_pct[idx]
            status = "●" if oav_val >= 1 else "○"
            lines.append(
                f"  {status} {m.name:<28s}  "
                f"OAV={oav_val:>8.1f}  "
                f"HS={pct_val:>5.1f}%  "
                f"[{m.note}]"
            )

        # Character snapshot
        char = {d: float(profile.character_evolution[d][idx]) for d in DIMENSIONS}
        top3 = sorted(char, key=char.get, reverse=True)[:3]
        char_str = ", ".join(f"{d}({char[d]:.0f}%)" for d in top3)
        lines.append(f"  Character: {char_str}")
        lines.append("")

    # Materials below perception threshold early
    silent = [
        m.name for m in profile.materials.values()
        if np.max(m.oav) < 1.0
    ]
    if silent:
        lines.append("─── Subliminal Materials (OAV never reaches 1) ───")
        for name in silent:
            m = profile.materials[name]
            lines.append(f"  ○ {name} — peak OAV={np.max(m.oav):.2f}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════════════════════════

def generate_temporal_graph(
    formula_name: str,
    ingredients: dict[str, float],
    save_path: str | Path | None = None,
    show: bool = False,
    synergy_data: dict | None = None,
) -> tuple[TemporalProfile, Any]:
    """One-call convenience: simulate + visualize + report.

    Args:
        formula_name: Name for the formula
        ingredients: {material_name: percentage_in_concentrate}
        save_path: Optional path to save the figure (PNG/PDF/SVG)
        show: Whether to display interactively
        synergy_data: Optional {(name_a,name_b): weight} from SynergyGraph.
                      Build with:
                        sg = SynergyGraph()
                        sg.build(list(ingredients.keys()))
                        synergy_data = {k: e.weight for k, e in sg.edges.items()}

    Returns:
        (TemporalProfile, matplotlib.Figure)
    """
    engine = TemporalEngine()
    profile = engine.simulate(formula_name, ingredients)

    viz = TemporalVisualizer()
    fig = viz.plot(profile, save_path=save_path, show=show,
                   synergy_data=synergy_data)

    return profile, fig
