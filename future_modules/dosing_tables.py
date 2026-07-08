"""µL dosing tables — stock preparation, dilution calculations, and material handling.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the practical dosing and handling data from the Formulation Intelligence
Database (Part X). Covers:

  - Solid material stock solution recipes (coumarin, vanillin, ethyl maltol, etc.)
  - Viscous material handling (labdanum, benzoin)
  - Potent material working dilutions (β-damascenone, geosmin, IBQ, skatole, calone)
  - µL-to-ppm-to-OAV conversion for common dosing scenarios
  - Sample dosing table for 10g concentrate at 25% EdP

Integrates with pipeline by providing the dilutions and stock recipes needed
to convert between formulation intent (ppm/OAV) and physical dosing (µL/grams).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import DosingEntry, SolubilityData, SolubilityRisk


# ---------------------------------------------------------------------------
# Solid material stock preparations
# ---------------------------------------------------------------------------

SOLID_STOCK_RECIPES: tuple[SolubilityData, ...] = (
    SolubilityData(
        material="Coumarin",
        solubility_in_etoh_96="Precipitates below 2% in EtOH 96%",
        precipitation_temp_c=5.0,
        recommended_stock="10% in benzyl benzoate",
        co_solvent="Benzyl benzoate 5%, IPM 5%",
        risk=SolubilityRisk.MEDIUM,
    ),
    SolubilityData(
        material="Vanillin",
        solubility_in_etoh_96="Precipitates below 5% in EtOH 96%",
        precipitation_temp_c=5.0,
        recommended_stock="20% in DPG",
        co_solvent="DPG, benzyl benzoate",
        risk=SolubilityRisk.MEDIUM,
    ),
    SolubilityData(
        material="Oranger Crystals",
        solubility_in_etoh_96="Precipitates below 1% without co-solvent",
        precipitation_temp_c=20.0,  # can precipitate at room temp
        recommended_stock="5% in EtOH + 5% benzyl benzoate",
        co_solvent="5% benzyl benzoate",
        risk=SolubilityRisk.HIGH,
    ),
    SolubilityData(
        material="Ethyl Maltol",
        solubility_in_etoh_96="Precipitates below 0.5% over time",
        precipitation_temp_c=20.0,
        recommended_stock="10% in DPG",
        co_solvent="DPG",
        risk=SolubilityRisk.HIGH,
    ),
    SolubilityData(
        material="Musk Ketone",
        solubility_in_etoh_96="Precipitates below 1% in ethanol",
        precipitation_temp_c=5.0,
        recommended_stock="10% in DPG",
        co_solvent="DPG",
        risk=SolubilityRisk.MEDIUM,
    ),
)


# ---------------------------------------------------------------------------
# Viscous material handling
# ---------------------------------------------------------------------------

VISCOUS_MATERIALS: tuple[tuple[str, str, float], ...] = (
    ("Labdanum Absolute", "Pre-warm to 40°C; measure by weight not volume; recommended stock 50% in DPG or benzyl benzoate", 50.0),
    ("Benzoin Resinoid", "Pre-warm to 40°C; measure by weight not volume; recommended stock 50% in DPG or benzyl benzoate", 50.0),
    ("Benzoin Sumatra", "Pre-warm to 40°C; measure by weight not volume; recommended stock 50% in DPG or benzyl benzoate", 50.0),
    ("Tolu Balsam", "Pre-warm to 40°C; recommended stock 50% in benzyl benzoate", 50.0),
    ("Styrax Resinoid", "Pre-warm to 40°C; recommended stock 50% in DPG", 50.0),
)


# ---------------------------------------------------------------------------
# Potent material working dilutions
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PotentMaterialDilution:
    """Working dilution recommendation for a potent material."""
    material: str
    recommended_stock_pct: float   # e.g., 0.1% for β-damascenone
    solvent: str                   # DPG or EtOH
    reason: str


POTENT_MATERIALS: tuple[PotentMaterialDilution, ...] = (
    PotentMaterialDilution(
        "Beta-Damascenone", 0.1, "DPG",
        "0.01 g doses become pipettable; ODT ~0.002-0.009 ppb is one of the lowest known",
    ),
    PotentMaterialDilution(
        "Geosmin", 0.001, "DPG",
        "Extreme potency — 5 ppt ODT in water; neat geosmin is impossible to dose precisely",
    ),
    PotentMaterialDilution(
        "Rose Oxide", 1.0, "EtOH",
        "ODT very low; at 100% too strong to handle precisely",
    ),
    PotentMaterialDilution(
        "Isobutyl Quinoline (IBQ)", 1.0, "EtOH",
        "Risk of overdose above 0.05% in formula — 1% stock enables precise dosing",
    ),
    PotentMaterialDilution(
        "Skatole", 0.1, "DPG",
        "Transitions fecal at very low concentration; 0.1% stock for handling",
    ),
    PotentMaterialDilution(
        "Calone", 10.0, "EtOH",
        "ODT very low; 10% stock is the industry standard for handling",
    ),
    PotentMaterialDilution(
        "Methyl 2-Octynoate", 1.0, "EtOH",
        "IFRA max 0.047% in finished product — must dose precisely; 1% stock recommended",
    ),
    PotentMaterialDilution(
        "Indole", 10.0, "DPG",
        "Fecal cliff at ~1% in concentrate; 10% stock for controlled dosing of 0.01-0.5% in formula",
    ),
    PotentMaterialDilution(
        "Guaiacol", 10.0, "DPG",
        "Smoky-phenolic; 10% stock for 0.5% effective in formula",
    ),
    PotentMaterialDilution(
        "1-p-Menthene-8-thiol", 0.01, "EtOH",
        "Grapefruit mercaptan — ODT 0.000034 ng/L air; the lowest recorded ODT of any food odorant",
    ),
)


# ---------------------------------------------------------------------------
# Sample dosing table (10g concentrate at 25% EdP)
# ---------------------------------------------------------------------------

SAMPLE_DOSING_TABLE: tuple[DosingEntry, ...] = (
    DosingEntry("Hedione", 100.0, 5.0, 500, 50000, 50),
    DosingEntry("Iso E Super", 100.0, 3.0, 300, 30000, 80),
    DosingEntry("Galaxolide 50%", 50.0, 3.0, 600, 30000, 25),
    DosingEntry("Beta-Damascenone", 0.1, 0.01, 1000, 100, 500),
    DosingEntry("Indole", 10.0, 0.02, 20, 200, 5),
    DosingEntry("Calone", 10.0, 0.01, 10, 100, 100),
    DosingEntry("Rose Absolute", 100.0, 0.5, 50, 5000, 8),
    DosingEntry("Linalool", 100.0, 2.0, 200, 20000, 40),
    DosingEntry("Coumarin", 10.0, 0.5, 500, 5000, 15),
    DosingEntry("Ambroxan", 100.0, 0.5, 50, 5000, 50),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_solid_stock(material_name: str) -> SolubilityData | None:
    """Return stock preparation data for a solid material."""
    key = material_name.lower()
    for s in SOLID_STOCK_RECIPES:
        if s.material.lower() == key:
            return s
    return None


def get_viscous_handling(material_name: str) -> tuple[str, float] | None:
    """Return handling guidance and recommended stock % for a viscous material."""
    key = material_name.lower()
    for mat, guidance, stock_pct in VISCOUS_MATERIALS:
        if mat.lower() == key:
            return (guidance, stock_pct)
    return None


def get_potent_dilution(material_name: str) -> PotentMaterialDilution | None:
    """Return recommended working dilution for a potent material."""
    key = material_name.lower()
    for pm in POTENT_MATERIALS:
        if pm.material.lower() == key:
            return pm
    return None


def calculate_dose(
    target_mass_g: float,           # grams of pure material needed in concentrate
    stock_concentration_pct: float,  # stock solution concentration (%)
    concentrate_total_g: float = 10.0,  # total concentrate mass
) -> float:
    """Calculate µL of stock solution needed for a target mass of pure material.

    Args:
        target_mass_g: mass of pure material desired (g)
        stock_concentration_pct: concentration of stock solution (%, e.g., 10.0 for 10%)
        concentrate_total_g: total batch mass (g) — used for validation

    Returns:
        µL of stock solution to pipette

    Note: This assumes density ≈ 1.0 g/mL. For precise work, use weight-based dosing
    for materials with density significantly different from 1.0.
    """
    if stock_concentration_pct <= 0:
        raise ValueError(f"Stock concentration must be > 0, got {stock_concentration_pct}%")

    stock_fraction = stock_concentration_pct / 100.0
    stock_mass_g = target_mass_g / stock_fraction
    # µL ≈ mg assuming density = 1.0
    return stock_mass_g * 1000.0


def calculate_target_percent(
    ul_stock: float,                # µL of stock solution used
    stock_concentration_pct: float,  # stock concentration (%)
    concentrate_total_g: float = 10.0,  # total concentrate mass
) -> float:
    """Calculate the effective % of pure material in the concentrate.

    Returns:
        % (w/w) of pure material in the concentrate
    """
    stock_fraction = stock_concentration_pct / 100.0
    pure_mass_g = (ul_stock / 1000.0) * stock_fraction
    return (pure_mass_g / concentrate_total_g) * 100.0


def calculate_ppm(percent_in_conc: float) -> float:
    """Convert % in concentrate to ppm in concentrate."""
    return percent_in_conc * 10000.0


def estimate_oav(
    ppm_in_conc: float,
    odt_ppm: float,
) -> float:
    """Estimate OAV from ppm in concentrate and ODT (ppm in ethanol).

    OAV = ppm / ODT_ppm

    Note: This is the single-material OAV. In complex mixtures,
    apply mixture suppression factor (divide by 3-5) for effective OAV.
    """
    if odt_ppm <= 0:
        return float("inf")
    return ppm_in_conc / odt_ppm


def get_sample_dosing(material_name: str) -> DosingEntry | None:
    """Return sample dosing entry for a material."""
    key = material_name.lower()
    for entry in SAMPLE_DOSING_TABLE:
        if entry.material.lower() == key:
            return entry
    return None


def get_all_sample_dosing() -> tuple[DosingEntry, ...]:
    """Return all sample dosing entries."""
    return SAMPLE_DOSING_TABLE


def list_solids() -> tuple[str, ...]:
    """Return materials that require stock solution preparation (solids)."""
    return tuple(s.material for s in SOLID_STOCK_RECIPES)


def list_viscous() -> tuple[str, ...]:
    """Return materials that require special viscous handling."""
    return tuple(mat for mat, _, _ in VISCOUS_MATERIALS)


def list_potent() -> tuple[str, ...]:
    """Return materials that require working dilutions (potent)."""
    return tuple(pm.material for pm in POTENT_MATERIALS)


def prepare_stock_solution(
    material_name: str,
    target_concentration_pct: float = 10.0,
    target_volume_ml: float = 10.0,
    solvent: str = "DPG",
) -> dict[str, float] | None:
    """Calculate stock solution preparation quantities.

    Args:
        material_name: name of the material
        target_concentration_pct: desired concentration (%)
        target_volume_ml: desired total volume (mL)
        solvent: solvent to use (DPG or EtOH)

    Returns:
        dict with 'material_g', 'solvent_ml', 'total_ml', or None if unknown material
    """
    # Check if there's a recommended stock
    stock = get_solid_stock(material_name)
    if stock:
        target_concentration_pct = float(stock.recommended_stock.split("%")[0])

    material_g = target_volume_ml * (target_concentration_pct / 100.0)
    solvent_ml = target_volume_ml - material_g  # approximate

    return {
        "material_name": material_name,
        "material_g": round(material_g, 3),
        "solvent_ml": round(solvent_ml, 1),
        "total_ml": target_volume_ml,
        "concentration_pct": target_concentration_pct,
        "solvent": solvent,
    }
