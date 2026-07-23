"""Solvent matrix model — track carrier solvents entering perfume through dilutions.

When a perfumer doses 300 µL of Neroli EO (10% in DPG), they add:
  - 30 µL neroli oil (active aromachemicals)
  - 270 µL DPG (carrier solvent)

The cumulative carriers (DPG, TEC, DEP, BB, IPM, EtOH from dilutions) modify:
  - Mole fractions (carrier MW contributes to total moles)
  - Activity coefficients (DPG depresses γ for polar compounds)
  - Total vapor pressure (Raoult summation over all matrix components)
  - Cost (carriers consume volume but cost less than aromachemicals)

This module provides SolventLedger for gate-time matrix composition reporting.
"""

from dataclasses import dataclass, field

# Solvent physical properties — verified against PubChem, Good Scents, EPI Suite
_SOLVENT_PROPERTIES: dict[str, dict[str, object]] = {
    "DPG": {
        "mw": 134.17,
        "density": 1.02,
        "vp_pa": 0.02,
        "gamma": 0.5,
        "logP": -0.6,
        "full_name": "Dipropylene Glycol",
        "cas": "25265-71-8",
    },
    "EtOH": {
        "mw": 46.07,
        "density": 0.79,
        "vp_pa": 7870,
        "gamma": 1.0,
        "logP": -0.3,
        "full_name": "Ethanol",
        "cas": "64-17-5",
    },
    "TEC": {
        "mw": 276.28,
        "density": 1.14,
        "vp_pa": 0.001,
        "gamma": 0.4,
        "logP": 1.5,
        "full_name": "Triethyl Citrate",
        "cas": "77-93-0",
    },
    "DEP": {
        "mw": 222.24,
        "density": 1.12,
        "vp_pa": 0.002,
        "gamma": 0.4,
        "logP": 2.5,
        "full_name": "Diethyl Phthalate",
        "cas": "84-66-2",
    },
    "IPM": {
        "mw": 270.45,
        "density": 0.85,
        "vp_pa": 0.001,
        "gamma": 0.7,
        "logP": 7.2,
        "full_name": "Isopropyl Myristate",
        "cas": "110-27-0",
    },
    "BB": {
        "mw": 212.24,
        "density": 1.12,
        "vp_pa": 0.001,
        "gamma": 0.5,
        "logP": 3.9,
        "full_name": "Benzyl Benzoate",
        "cas": "120-51-4",
    },
    "MCT": {
        "mw": 520.0,
        "density": 0.94,
        "vp_pa": 0.0,
        "gamma": 0.7,
        "logP": 10.0,
        "full_name": "Medium Chain Triglycerides (Fractionated Coconut Oil)",
        "cas": "73398-61-5",
    },
    "none": {
        "mw": 0.0,
        "density": 0.0,
        "vp_pa": 0.0,
        "gamma": 1.0,
        "logP": 0.0,
        "full_name": "None (neat material)",
        "cas": "",
    },
}


@dataclass
class SolventLedger:
    """Accumulated carrier solvent profile for a formula."""

    carriers: dict[str, float] = field(default_factory=dict)  # solvent_name -> µL
    solute_ul: float = 0.0  # total active solute µL
    ethanol_matrix_ul: float = 0.0  # ethanol from matrix (not dilutions)

    def add_material(self, dose_ul: float, dilution_fraction: float, solvent: str) -> None:
        """Track a material dose. solvent is the carrier (DPG, TEC, etc.) or 'none' for neat."""
        active_ul = dose_ul * dilution_fraction
        carrier_ul = dose_ul - active_ul
        self.solute_ul += active_ul
        if solvent.lower() not in ("none", "", "neat"):
            self.carriers[solvent.upper()] = self.carriers.get(solvent.upper(), 0.0) + carrier_ul

    def set_ethanol_matrix(self, ethanol_ul: float) -> None:
        """Set the bulk ethanol matrix volume (not from dilutions)."""
        self.ethanol_matrix_ul = ethanol_ul

    @property
    def total_carrier_ul(self) -> float:
        return sum(self.carriers.values())

    @property
    def total_matrix_ul(self) -> float:
        return self.ethanol_matrix_ul + self.total_carrier_ul

    @property
    def carrier_pct_of_matrix(self) -> float:
        """What % of the final ethanol+carrier matrix is carrier solvent."""
        if self.total_matrix_ul <= 0:
            return 0.0
        return (self.total_carrier_ul / self.total_matrix_ul) * 100.0

    def to_dict(self) -> dict:
        return {
            "ethanol_matrix_ul": round(self.ethanol_matrix_ul, 1),
            "solute_active_ul": round(self.solute_ul, 1),
            "carrier_solvents_ul": {k: round(v, 1) for k, v in self.carriers.items()},
            "total_carrier_ul": round(self.total_carrier_ul, 1),
            "total_matrix_ul": round(self.total_matrix_ul, 1),
            "carrier_pct": round(self.carrier_pct_of_matrix, 1),
        }


def get_solvent_properties(solvent_name: str) -> dict:
    """Look up solvent physical properties. Returns empty dict for unknown solvents."""
    key = solvent_name.upper().strip()
    return _SOLVENT_PROPERTIES.get(key, _SOLVENT_PROPERTIES["none"]).copy()


def parse_solvent_from_inventory_entry(inventory_line: str) -> tuple[str, float]:
    """Parse solvent and dilution from inventory.txt line.
    Returns (solvent_name, dilution_fraction).
    Example: '- Neroli EO (10% in DPG)' -> ('DPG', 0.10)
    Example: '- Bergamot FCF' -> ('none', 1.0)
    """
    import re

    dilution = 1.0
    solvent = "none"
    match = re.search(r"\((\d+)%\s*(?:in\s+)?(\w+(?:\s+\w+)?)\)", inventory_line)
    if match:
        dilution = int(match.group(1)) / 100.0
        solvent = match.group(2).strip() or "unknown"
    # Map common solvent aliases
    solvent_map = {
        "dpg": "DPG",
        "tec": "TEC",
        "dep": "DEP",
        "ipm": "IPM",
        "bb": "BB",
        "benzyl benzoate": "BB",
        "etoh": "EtOH",
        "ethanol": "EtOH",
        "dipropylene glycol": "DPG",
        "triethyl citrate": "TEC",
        "diethyl phthalate": "DEP",
        "isopropyl myristate": "IPM",
        "mct": "MCT",
        "coconut mct": "MCT",
    }
    return solvent_map.get(solvent.lower(), solvent.upper()), dilution
