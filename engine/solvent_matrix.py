"""Source-aware solvent and diluted-stock carrier accounting.

This module is a reconciliation ledger. It does not silently add stock
carriers to the canonical headspace mole fractions: a declaration such as
``10% in DPG`` does not state whether the percentage is a mass fraction,
volume fraction, or mass concentration. The residual-volume calculation is
therefore a diagnostic proxy unless a volume-fraction basis is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Values support diagnostic volume/mole reconciliation only. They are not a
# substitute for a batch COA. DPG is a commercial isomer mixture.
_SOLVENT_PROPERTIES: dict[str, dict[str, object]] = {
    "DPG": {
        "mw": 134.2,
        "density": 1.027,
        "vp_pa": 0.02,
        "full_name": "Dipropylene Glycol",
        "cas": "25265-71-8",
        "source": "Shell DPG technical data sheet U1521, revised July 2023",
    },
    "ETHANOL": {
        "mw": 46.0684,
        "density": 0.785,
        "vp_pa": 7870.0,
        "full_name": "Ethanol",
        "cas": "64-17-5",
        "source": "formula-declared or local reference property",
    },
    "WATER": {
        "mw": 18.01528,
        "density": 0.997,
        "vp_pa": 3169.0,
        "full_name": "Water",
        "cas": "7732-18-5",
        "source": "formula-declared or local reference property",
    },
    "TEC": {
        "mw": 276.28,
        "density": 1.1369,
        "vp_pa": 0.001,
        "full_name": "Triethyl Citrate",
        "cas": "77-93-0",
        "source": "PubChem CID 6506 (CRC density record)",
    },
    "DEP": {
        "mw": 222.24,
        "density": 1.12,
        "vp_pa": 0.002,
        "full_name": "Diethyl Phthalate",
        "cas": "84-66-2",
        "source": "local reference property",
    },
    "IPM": {
        "mw": 270.5,
        "density": 0.8532,
        "vp_pa": 0.001,
        "full_name": "Isopropyl Myristate",
        "cas": "110-27-0",
        "source": "PubChem CID 8042 (Merck density record)",
    },
    "BB": {
        "mw": 212.24,
        "density": 1.12,
        "vp_pa": 0.001,
        "full_name": "Benzyl Benzoate",
        "cas": "120-51-4",
        "source": "local reference property",
    },
    "MCT": {
        "mw": 520.0,
        "density": 0.94,
        "vp_pa": 0.0,
        "full_name": "Medium Chain Triglycerides",
        "cas": "73398-61-5",
        "source": "bulk mixture proxy",
    },
}

_SOLVENT_ALIASES = {
    "dpg": "DPG",
    "dipropylene glycol": "DPG",
    "etoh": "ETHANOL",
    "ethanol": "ETHANOL",
    "ethanol 96%": "ETHANOL",
    "ethyl alcohol": "ETHANOL",
    "water": "WATER",
    "h2o": "WATER",
    "tec": "TEC",
    "triethyl citrate": "TEC",
    "dep": "DEP",
    "diethyl phthalate": "DEP",
    "ipm": "IPM",
    "isopropyl myristate": "IPM",
    "bb": "BB",
    "benzyl benzoate": "BB",
    "mct": "MCT",
    "coconut mct": "MCT",
    "medium chain triglycerides": "MCT",
}


def canonical_solvent_name(value: str) -> str | None:
    """Return a supported canonical solvent key without guessing unknown names."""
    normalized = " ".join(str(value or "").strip().casefold().split())
    if normalized in {"", "none", "neat"}:
        return None
    return _SOLVENT_ALIASES.get(normalized)


def get_solvent_properties(solvent_name: str) -> dict[str, object]:
    """Return a copy of supported physical properties, or an empty mapping."""
    canonical = canonical_solvent_name(solvent_name)
    if canonical is None:
        return {}
    return dict(_SOLVENT_PROPERTIES[canonical])


@dataclass
class SolventLedger:
    """Accumulate bulk-matrix and diluted-stock carrier evidence."""

    carriers: dict[str, float] = field(default_factory=dict)
    bulk_matrix: dict[str, float] = field(default_factory=dict)
    solute_ul: float = 0.0
    stock_rows: list[dict[str, object]] = field(default_factory=list)
    unresolved_bulk_components: list[str] = field(default_factory=list)

    def add_material(
        self,
        dose_ul: float,
        dilution_fraction: float,
        solvent: str,
        *,
        material: str = "",
        fraction_basis: str = "unspecified",
    ) -> None:
        """Track a stock dose while preserving concentration-basis authority."""
        dose = max(0.0, float(dose_ul))
        fraction = min(1.0, max(0.0, float(dilution_fraction)))
        active_ul = dose * fraction
        carrier_proxy_ul = max(0.0, dose - active_ul)
        self.solute_ul += active_ul
        if carrier_proxy_ul <= 0.0:
            return

        canonical = canonical_solvent_name(solvent)
        basis = str(fraction_basis or "unspecified").strip().casefold()
        authority = (
            "DECLARED_VOLUME_FRACTION"
            if basis == "volume_fraction" and canonical is not None
            else "RESIDUAL_VOLUME_PROXY"
            if canonical is not None
            else "UNRESOLVED_CARRIER_IDENTITY"
        )
        if canonical is not None:
            self.carriers[canonical] = (
                self.carriers.get(canonical, 0.0) + carrier_proxy_ul
            )
        self.stock_rows.append(
            {
                "material": material,
                "fraction": fraction,
                "fraction_basis": basis,
                "declared_carrier": str(solvent or ""),
                "canonical_carrier": canonical,
                "carrier_volume_ul": round(carrier_proxy_ul, 6),
                "authority": authority,
                "included_in_headspace_matrix": False,
            }
        )

    def add_bulk_component(self, name: str, volume_ul: float) -> None:
        """Add a formula-declared bulk matrix component."""
        canonical = canonical_solvent_name(name)
        if canonical is None:
            self.unresolved_bulk_components.append(str(name))
            return
        self.bulk_matrix[canonical] = (
            self.bulk_matrix.get(canonical, 0.0) + max(0.0, float(volume_ul))
        )

    def set_ethanol_matrix(self, ethanol_ul: float) -> None:
        """Backward-compatible ethanol-only bulk-matrix setter."""
        self.add_bulk_component("ethanol", ethanol_ul)

    @property
    def total_carrier_ul(self) -> float:
        return sum(self.carriers.values())

    @property
    def unresolved_carrier_proxy_ul(self) -> float:
        return sum(
            float(row["carrier_volume_ul"])
            for row in self.stock_rows
            if row["canonical_carrier"] is None
        )

    @property
    def total_bulk_matrix_ul(self) -> float:
        return sum(self.bulk_matrix.values())

    @property
    def total_matrix_ul(self) -> float:
        return self.total_bulk_matrix_ul + self.total_carrier_ul

    @property
    def carrier_pct_of_matrix(self) -> float | None:
        if self.total_matrix_ul <= 0.0:
            return None
        return 100.0 * self.total_carrier_ul / self.total_matrix_ul

    @property
    def authority(self) -> str:
        if self.unresolved_carrier_proxy_ul > 0.0:
            return "PARTIAL_UNRESOLVED"
        if any(
            row["authority"] == "RESIDUAL_VOLUME_PROXY"
            for row in self.stock_rows
        ):
            return "NAMED_CARRIER_VOLUME_PROXY"
        if self.stock_rows:
            return "DECLARED_VOLUME_FRACTION"
        return "NOT_APPLICABLE"

    def to_dict(self) -> dict[str, object]:
        carrier_pct = self.carrier_pct_of_matrix
        return {
            "authority": self.authority,
            "release_authority": False,
            "bulk_matrix_components_ul": {
                key: round(value, 3) for key, value in self.bulk_matrix.items()
            },
            "known_stock_carriers_ul": {
                key: round(value, 3) for key, value in self.carriers.items()
            },
            "unresolved_carrier_proxy_ul": round(
                self.unresolved_carrier_proxy_ul,
                3,
            ),
            "solute_active_ul": round(self.solute_ul, 3),
            "total_known_carrier_ul": round(self.total_carrier_ul, 3),
            "known_carrier_pct_of_reconciled_matrix": (
                None if carrier_pct is None else round(carrier_pct, 3)
            ),
            "stock_rows": list(self.stock_rows),
            "unresolved_bulk_components": list(self.unresolved_bulk_components),
            "headspace_stock_carrier_inclusion": "NOT_INCLUDED_PENDING_RECONCILIATION",
        }


def parse_solvent_from_inventory_entry(inventory_line: str) -> tuple[str, float]:
    """Legacy convenience parser retained for non-canonical callers."""
    import re

    match = re.search(
        r"\((\d+(?:\.\d+)?)%\s*(?:in\s+)?([^),]+)\)",
        str(inventory_line),
        flags=re.IGNORECASE,
    )
    if match is None:
        return "none", 1.0
    dilution = float(match.group(1)) / 100.0
    canonical = canonical_solvent_name(match.group(2))
    return (canonical or "unknown"), dilution
