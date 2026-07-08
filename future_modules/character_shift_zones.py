"""Hedonic character shift zone database for key materials.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the hedonic dose-response zone data from the Formulation Intelligence
Database (Part VII). Each material has multiple shift zones defined by:
  - Concentration range in the concentrate
  - OAV range
  - Character description at that zone
  - Hedonic score at that zone

Materials covered:
  - Indole (CAS 120-72-9)
  - Calone (CAS 28940-11-6)
  - β-Damascenone (CAS 23726-93-4)
  - Geosmin (CAS 19700-21-1)
  - Vanillin (CAS 121-33-5)
  - Isobutyl Quinoline (IBQ)
  - Ethyl Maltol

Hill equation parameters (EC50, n, Rmax) are also provided for materials where
the dose-response is well-characterized, enabling sigmoidal hedonic modeling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ._shared_types import HedgeShiftZone, MaterialShiftProfile


# ---------------------------------------------------------------------------
# Indole (CAS 120-72-9) — the classic sharp-cliff material
# ---------------------------------------------------------------------------

INDOLE_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="trace",
        conc_min_pct=0.001, conc_max_pct=0.05,
        oav_min=0.01, oav_max=0.5,
        character="Green-floral, barely animalic",
        hedonic=1.0,
    ),
    HedgeShiftZone(
        label="moderate",
        conc_min_pct=0.06, conc_max_pct=0.5,
        oav_min=0.6, oav_max=5.0,
        character="Narcotic jasmine, white floral depth",
        hedonic=4.5,
    ),
    HedgeShiftZone(
        label="dominant",
        conc_min_pct=0.6, conc_max_pct=2.0,
        oav_min=5.1, oav_max=20.0,
        character="Heavy animalic, challenging territory",
        hedonic=0.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=2.1, conc_max_pct=100.0,
        oav_min=20.0, oav_max=float("inf"),
        character="Fecal, nauseating",
        hedonic=-5.0,
    ),
)

INDOLE_PROFILE = MaterialShiftProfile(
    material="Indole",
    cas="120-72-9",
    zones=INDOLE_ZONES,
    hill_ec50=0.3,
    hill_n=2.1,
    hill_rmax=1.0,
)


# ---------------------------------------------------------------------------
# Calone (CAS 28940-11-6)
# ---------------------------------------------------------------------------

CALONE_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="trace",
        conc_min_pct=0.001, conc_max_pct=0.010,
        oav_min=0.1, oav_max=1.0,
        character="Subtle marine-green freshness",
        hedonic=2.0,
    ),
    HedgeShiftZone(
        label="working",
        conc_min_pct=0.010, conc_max_pct=0.020,
        oav_min=1.0, oav_max=20.0,
        character="Marine-watermelon, ozonic fresh",
        hedonic=3.0,
    ),
    HedgeShiftZone(
        label="threshold",
        conc_min_pct=0.020, conc_max_pct=0.050,
        oav_min=20.0, oav_max=50.0,
        character="Metallic-ozonic begins",
        hedonic=1.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=0.05, conc_max_pct=0.5,
        oav_min=50.0, oav_max=500.0,
        character="Metallic pool cleaner",
        hedonic=-2.0,
    ),
    HedgeShiftZone(
        label="danger",
        conc_min_pct=0.5, conc_max_pct=100.0,
        oav_min=500.0, oav_max=float("inf"),
        character="Synthetic chemical off-note",
        hedonic=-4.0,
    ),
)

CALONE_PROFILE = MaterialShiftProfile(
    material="Calone",
    cas="28940-11-6",
    zones=CALONE_ZONES,
)


# ---------------------------------------------------------------------------
# β-Damascenone (CAS 23726-93-4)
# ---------------------------------------------------------------------------

DAMASCENONE_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="trace",
        conc_min_pct=0.0001, conc_max_pct=0.005,
        oav_min=1.0, oav_max=50.0,
        character="Subtle rose-plum, fruit-enhancer",
        hedonic=3.0,
    ),
    HedgeShiftZone(
        label="working",
        conc_min_pct=0.005, conc_max_pct=0.05,
        oav_min=50.0, oav_max=500.0,
        character="Clear rose-damascene, plum richness",
        hedonic=4.5,
    ),
    HedgeShiftZone(
        label="dominant",
        conc_min_pct=0.05, conc_max_pct=0.15,
        oav_min=500.0, oav_max=1500.0,
        character="Rose-metallic edge appears",
        hedonic=3.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=0.15, conc_max_pct=100.0,
        oav_min=1500.0, oav_max=float("inf"),
        character="Metallic-harsh",
        hedonic=0.5,
    ),
)

DAMASCENONE_PROFILE = MaterialShiftProfile(
    material="Beta-Damascenone",
    cas="23726-93-4",
    zones=DAMASCENONE_ZONES,
)


# ---------------------------------------------------------------------------
# Geosmin (CAS 19700-21-1)
# ---------------------------------------------------------------------------

GEOSMIN_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="petrichor",
        conc_min_pct=0.000001, conc_max_pct=0.00001,
        oav_min=10.0, oav_max=100.0,
        character="Rain-on-earth petrichor, geological freshness",
        hedonic=2.0,
    ),
    HedgeShiftZone(
        label="working",
        conc_min_pct=0.00001, conc_max_pct=0.0001,
        oav_min=100.0, oav_max=1000.0,
        character="Strong earth-petrichor, geosmin identifiable",
        hedonic=1.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=0.001, conc_max_pct=100.0,
        oav_min=1000.0, oav_max=float("inf"),
        character="Beetroot-dirt, off-note",
        hedonic=-3.0,
    ),
)

GEOSMIN_PROFILE = MaterialShiftProfile(
    material="Geosmin",
    cas="19700-21-1",
    zones=GEOSMIN_ZONES,
)


# ---------------------------------------------------------------------------
# Vanillin (CAS 121-33-5)
# ---------------------------------------------------------------------------

VANILLIN_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="background",
        conc_min_pct=0.01, conc_max_pct=0.5,
        oav_min=2.0, oav_max=100.0,
        character="Subtle sweet background",
        hedonic=2.5,
    ),
    HedgeShiftZone(
        label="working",
        conc_min_pct=0.5, conc_max_pct=2.0,
        oav_min=100.0, oav_max=400.0,
        character="Sweet-creamy vanilla, beautiful",
        hedonic=3.5,
    ),
    HedgeShiftZone(
        label="dominant",
        conc_min_pct=2.0, conc_max_pct=5.0,
        oav_min=400.0, oav_max=1000.0,
        character="Dominant vanilla, beginning cloying",
        hedonic=2.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=5.0, conc_max_pct=100.0,
        oav_min=1000.0, oav_max=float("inf"),
        character="Plasticky-artificial, overwhelming",
        hedonic=-1.0,
    ),
)

VANILLIN_PROFILE = MaterialShiftProfile(
    material="Vanillin",
    cas="121-33-5",
    zones=VANILLIN_ZONES,
)


# ---------------------------------------------------------------------------
# Isobutyl Quinoline / IBQ (CAS 1333-58-0 approx.)
# ---------------------------------------------------------------------------

IBQ_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="leather",
        conc_min_pct=0.001, conc_max_pct=0.05,
        oav_min=0.5, oav_max=3.0,
        character="Harsh tarry leather — the indispensable leather flaw",
        hedonic=-3.0,  # intrinsically unpleasant but contextually essential
    ),
    HedgeShiftZone(
        label="dominant",
        conc_min_pct=0.05, conc_max_pct=0.5,
        oav_min=3.0, oav_max=10.0,
        character="Heavy leather, medicinal character emerging",
        hedonic=-4.0,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=0.5, conc_max_pct=100.0,
        oav_min=10.0, oav_max=float("inf"),
        character="Medicinal-tar, nauseating",
        hedonic=-5.0,
    ),
)

IBQ_PROFILE = MaterialShiftProfile(
    material="Isobutyl Quinoline",
    cas="1333-58-0",  # approximate CAS for IBQ
    zones=IBQ_ZONES,
)


# ---------------------------------------------------------------------------
# Ethyl Maltol (CAS 4940-11-8)
# ---------------------------------------------------------------------------

ETHYL_MALTOL_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="cotton_candy",
        conc_min_pct=0.001, conc_max_pct=0.05,
        oav_min=5.0, oav_max=20.0,
        character="Cotton candy — subtle sweet bridge",
        hedonic=3.0,
    ),
    HedgeShiftZone(
        label="caramel",
        conc_min_pct=0.05, conc_max_pct=0.5,
        oav_min=20.0, oav_max=80.0,
        character="Rich caramel, warm sweetness",
        hedonic=3.5,
    ),
    HedgeShiftZone(
        label="burnt",
        conc_min_pct=0.5, conc_max_pct=2.0,
        oav_min=80.0, oav_max=150.0,
        character="Intense caramel, approaching burnt",
        hedonic=1.5,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=2.0, conc_max_pct=100.0,
        oav_min=150.0, oav_max=float("inf"),
        character="Burnt sugar-artificial, acrid",
        hedonic=-2.0,
    ),
)

ETHYL_MALTOL_PROFILE = MaterialShiftProfile(
    material="Ethyl Maltol",
    cas="4940-11-8",
    zones=ETHYL_MALTOL_ZONES,
)


# ---------------------------------------------------------------------------
# Coumarin (CAS 91-64-5)
# ---------------------------------------------------------------------------

COUMARIN_ZONES: tuple[HedgeShiftZone, ...] = (
    HedgeShiftZone(
        label="hay",
        conc_min_pct=0.01, conc_max_pct=0.5,
        oav_min=2.0, oav_max=30.0,
        character="Sweet hay, dried grass — fresh-clean coumarin character",
        hedonic=3.5,
    ),
    HedgeShiftZone(
        label="tonka",
        conc_min_pct=0.5, conc_max_pct=2.0,
        oav_min=30.0, oav_max=60.0,
        character="Deep tonka bean, almond sweetness",
        hedonic=3.0,
    ),
    HedgeShiftZone(
        label="dominant",
        conc_min_pct=2.0, conc_max_pct=5.0,
        oav_min=60.0, oav_max=120.0,
        character="Dominant coumarin, bitter almond emerging",
        hedonic=1.5,
    ),
    HedgeShiftZone(
        label="overdose",
        conc_min_pct=5.0, conc_max_pct=100.0,
        oav_min=120.0, oav_max=float("inf"),
        character="Bitter-almond aggressive, metallic",
        hedonic=-1.5,
    ),
)

COUMARIN_PROFILE = MaterialShiftProfile(
    material="Coumarin",
    cas="91-64-5",
    zones=COUMARIN_ZONES,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_SHIFT_PROFILES: tuple[MaterialShiftProfile, ...] = (
    INDOLE_PROFILE,
    CALONE_PROFILE,
    DAMASCENONE_PROFILE,
    GEOSMIN_PROFILE,
    VANILLIN_PROFILE,
    IBQ_PROFILE,
    ETHYL_MALTOL_PROFILE,
    COUMARIN_PROFILE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_shift_profile(material_name: str) -> MaterialShiftProfile | None:
    """Return the complete character shift profile for a material."""
    key = material_name.lower()
    for profile in ALL_SHIFT_PROFILES:
        if profile.material.lower() == key or profile.cas == key.replace("cas:", "").strip():
            return profile
    return None


def get_current_zone(
    material_name: str,
    concentration_pct: float,  # % in concentrate
) -> HedgeShiftZone | None:
    """Return the shift zone a material is currently in at a given concentration.

    Returns None if the material has no defined shift profile or if the
    concentration doesn't map to any zone.
    """
    profile = get_shift_profile(material_name)
    if profile is None:
        return None

    for zone in profile.zones:
        if zone.conc_min_pct <= concentration_pct <= zone.conc_max_pct:
            return zone

    return None


def get_zone_by_oav(
    material_name: str,
    oav: float,
) -> HedgeShiftZone | None:
    """Return the shift zone based on OAV instead of concentration."""
    profile = get_shift_profile(material_name)
    if profile is None:
        return None

    for zone in profile.zones:
        if zone.oav_min <= oav <= zone.oav_max:
            return zone

    return None


def check_zone_boundaries(
    material_name: str,
    concentration_pct: float,
    safety_margin: float = 0.2,  # 20% below cliff as safety
) -> tuple[bool, str]:
    """Check if a material is approaching a hedonic cliff.

    Returns:
        (is_safe, warning message)
    """
    profile = get_shift_profile(material_name)
    if profile is None:
        return True, f"No shift profile data for {material_name}"

    current_zone = get_current_zone(material_name, concentration_pct)
    if current_zone is None:
        return True, f"Cannot classify zone for {material_name} at {concentration_pct}%"

    # Find the next zone (if any) — zones are ordered
    zones = profile.zones
    for i, zone in enumerate(zones):
        if zone.label == current_zone.label and i < len(zones) - 1:
            next_zone = zones[i + 1]
            distance = (next_zone.conc_min_pct - concentration_pct) / next_zone.conc_min_pct
            if distance < safety_margin:
                if next_zone.hedonic < current_zone.hedonic:
                    return False, (
                        f"WARNING: {material_name} at {concentration_pct:.3f}% approaching {next_zone.label} zone "
                        f"({next_zone.character}) at {next_zone.conc_min_pct:.3f}% — margin only {distance:.0%}"
                    )
            break

    return True, f"{material_name} safe in {current_zone.label} zone"


def get_hill_parameters(material_name: str) -> tuple[float, float, float] | None:
    """Return Hill equation parameters (EC50, n, Rmax) for hedonic modeling.

    Returns:
        (ec50, hill_coefficient, rmax) or None
    """
    profile = get_shift_profile(material_name)
    if profile is None or profile.hill_ec50 is None:
        return None
    return (profile.hill_ec50, profile.hill_n or 1.0, profile.hill_rmax)


def hill_response(
    concentration_pct: float,
    ec50: float,
    n: float,
    rmax: float = 1.0,
) -> float:
    """Compute Hill equation response for a given concentration.

    Response = Rmax * C^n / (EC50^n + C^n)
    """
    if concentration_pct <= 0:
        return 0.0
    c_n = concentration_pct ** n
    ec50_n = ec50 ** n
    return rmax * c_n / (ec50_n + c_n)


def list_all_shift_profiles() -> tuple[str, ...]:
    """Return material names for all available shift profiles."""
    return tuple(p.material for p in ALL_SHIFT_PROFILES)
