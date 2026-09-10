"""Strict concentration and units engine.

Enforces explicit concentration basis for every material stock.
A naked "10%" or "30%" MUST fail validation — the basis (w/w, v/v, w/v)
must be declared.

Separates active accounting into:
  odorant_active  — materials that contribute to scent
  technical_active — non-odorant actives (BHT, EDTA, etc.)
  carrier          — solvents/carriers that dilute actives (DPG, DEP, TEC, IPM)
  solvent          — ethanol, water, etc. in finished product (not concentrate)
  finished_product — total final volume including solvent

RULE 1: All perfume calculations must use ppm, ODT, and OAV.
RULE: DPG is NOT odorant-active — formulas reporting neat DPG
as active material are overstating their odorant loading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite
from typing import Any

from engine.domain_errors import ReconstructionInputError

# ---------------------------------------------------------------------------
# Concentration basis
# ---------------------------------------------------------------------------

_WW_PCT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s+(?:w/w|\(w/w\))$", re.IGNORECASE)
_VV_PCT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s+(?:v/v|\(v/v\))$", re.IGNORECASE)
_WV_PCT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s+(?:w/v|\(w/v\))$", re.IGNORECASE)
_PCT_BASIS_IN_CARRIER_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*%\s*\(?\s*(w/w|v/v|w/v)\s*\)?\s+in\s+([A-Za-z\s/-]+)$",
    re.IGNORECASE,
)
_PCT_IN_CARRIER_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s*in\s+([A-Za-z\s/-]+)$")
_PCT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s*$")


class ConcentrationBasis:
    WEIGHT_WEIGHT = "w/w"
    VOLUME_VOLUME = "v/v"
    WEIGHT_VOLUME = "w/v"
    UNSPECIFIED = "unspecified"


class StockComponentRole:
    """Declared physical role of one stock-composition component."""

    ODORANT_ACTIVE = "odorant_active"
    TECHNICAL_ACTIVE = "technical_active"
    CARRIER = "carrier"
    SOLVENT = "solvent"
    SOLVENT_ETHANOL = "solvent_ethanol"
    SOLVENT_WATER = "solvent_water"
    UNALLOCATED = "unallocated"


_STOCK_COMPONENT_ROLES = frozenset(
    {
        StockComponentRole.ODORANT_ACTIVE,
        StockComponentRole.TECHNICAL_ACTIVE,
        StockComponentRole.CARRIER,
        StockComponentRole.SOLVENT,
        StockComponentRole.SOLVENT_ETHANOL,
        StockComponentRole.SOLVENT_WATER,
        StockComponentRole.UNALLOCATED,
    }
)


@dataclass(frozen=True, slots=True)
class StockComponent:
    """One declared component of a physical stock."""

    role: str
    fraction: float
    identity: str = ""

    def __post_init__(self) -> None:
        if self.role not in _STOCK_COMPONENT_ROLES:
            raise ReconstructionInputError(f"unknown stock component role: {self.role!r}")
        if not isfinite(self.fraction) or self.fraction < 0.0:
            raise ReconstructionInputError(
                f"stock component fraction must be finite and nonnegative, got {self.fraction!r}"
            )


@dataclass(frozen=True, slots=True)
class DeclaredStock:
    """Physical stock with explicit unit, basis, and composition authority."""

    name: str
    raw_amount: float
    unit: str
    basis: str
    components: tuple[StockComponent, ...]

    def __post_init__(self) -> None:
        if not isfinite(self.raw_amount) or self.raw_amount < 0.0:
            raise ReconstructionInputError(
                f"stock raw amount must be finite and nonnegative, got {self.raw_amount!r}"
            )
        if self.unit != "uL":
            raise ReconstructionInputError(
                f"active accounting requires unit 'uL', got {self.unit!r}"
            )
        if self.basis not in {
            ConcentrationBasis.WEIGHT_WEIGHT,
            ConcentrationBasis.VOLUME_VOLUME,
            ConcentrationBasis.WEIGHT_VOLUME,
        }:
            raise ReconstructionInputError(
                f"stock concentration basis must be explicit, got {self.basis!r}"
            )
        if not self.components:
            raise ReconstructionInputError("declared stock composition cannot be empty")
        component_total = sum(component.fraction for component in self.components)
        if not isfinite(component_total) or abs(component_total - 1.0) > 1e-9:
            raise ReconstructionInputError(
                "declared stock component fractions must conserve to 1.0; "
                f"got {component_total!r}"
            )


# Regex to strip trailing concentration information from a material name
# so that classify_material_category matches base identities like "BHT"
# against the classifier sets regardless of dilution suffix.
_CONC_STRIP_RE = re.compile(
    r"\s+\d+(?:\.\d+)?\s*%(?:\s+(?:w/w|v/v|w/v|\(w/w\)|\(v/v\)|\(w/v\)))?(?:\s+in\s+\S+(?:\s+\S+)?)?$",
    re.IGNORECASE,
)


SOLVENT_MATERIALS: frozenset[str] = frozenset(
    {
        "ethanol",
        "ethanol 96%",
        "ethyl alcohol",
        "water",
        "aqua",
    }
)

CARRIER_MATERIALS: frozenset[str] = frozenset(
    {
        "dipropylene glycol",
        "dpg",
        "diethyl phthalate",
        "dep",
        "triethyl citrate",
        "tec",
        "isopropyl myristate",
        "ipm",
        "propylene glycol",
        "benzyl benzoate",
    }
)

TECHNICAL_MATERIALS: frozenset[str] = frozenset(
    {
        "butylated hydroxytoluene",
        "bht",
        "edta",
        "disodium edta",
        "tocopherol",
        "vitamin e",
        "uv absorber",
    }
)


@dataclass(frozen=True, slots=True)
class Concentration:
    """A validated concentration value with explicit basis.

    Create via parse_concentration() — never construct directly
    without basis specification.
    """

    value: float
    basis: str
    carrier: str = ""
    approximate: bool = False
    raw_input: str = ""

    @property
    def is_diluted(self) -> bool:
        return self.value < 1.0

    @property
    def is_neat(self) -> bool:
        return abs(self.value - 1.0) < 1e-9

    @property
    def is_valid(self) -> bool:
        return self.basis != ConcentrationBasis.UNSPECIFIED

    def active_fraction(self) -> float:
        """Return the fraction of this stock that is active material."""
        return self.value

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "basis": self.basis,
            "carrier": self.carrier,
            "approximate": self.approximate,
            "raw_input": self.raw_input,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Concentration:
        return cls(
            value=float(data["value"]),
            basis=str(data["basis"]),
            carrier=str(data.get("carrier") or ""),
            approximate=bool(data.get("approximate", False)),
            raw_input=str(data.get("raw_input") or ""),
        )


def parse_concentration(raw: str, *, strict: bool = True) -> Concentration:
    """Parse a concentration string into a validated Concentration.

    Accepts:
      "10%"           -> fails in strict mode (basis unspecified)
      "10% w/w"       -> w/w basis
      "10% in DPG"    -> v/v in DPG (inferred when carrier specified)
      "50% in DEP"    -> v/v in DEP
      "20% (w/w)"     -> w/w basis
      "30% solution"  -> fails in strict mode
      "neat"          -> 1.0 w/w

    A naked percentage with no basis declaration raises ValueError
    in strict mode.
    """
    raw = raw.strip()
    if not raw:
        if strict:
            raise ValueError("empty concentration string")
        return Concentration(1.0, ConcentrationBasis.UNSPECIFIED)

    lower = raw.lower()

    if lower in ("neat", "pure", "undiluted", "100%"):
        return Concentration(1.0, ConcentrationBasis.WEIGHT_WEIGHT, raw_input=raw)

    explicit_carrier_match = _PCT_BASIS_IN_CARRIER_RE.search(lower)
    if explicit_carrier_match:
        basis_by_label = {
            "w/w": ConcentrationBasis.WEIGHT_WEIGHT,
            "v/v": ConcentrationBasis.VOLUME_VOLUME,
            "w/v": ConcentrationBasis.WEIGHT_VOLUME,
        }
        return Concentration(
            float(explicit_carrier_match.group(1)) / 100.0,
            basis_by_label[explicit_carrier_match.group(2).lower()],
            carrier=_normalize_carrier(explicit_carrier_match.group(3)),
            raw_input=raw,
        )

    carrier_match = _PCT_IN_CARRIER_RE.search(lower)
    if carrier_match:
        value = float(carrier_match.group(1)) / 100.0
        carrier = _normalize_carrier(carrier_match.group(2).strip())
        if carrier == "dpg":
            return Concentration(
                value, ConcentrationBasis.VOLUME_VOLUME, carrier=carrier, raw_input=raw
            )
        return Concentration(
            value, ConcentrationBasis.VOLUME_VOLUME, carrier=carrier, raw_input=raw
        )

    ww_match = _WW_PCT_RE.search(lower)
    if ww_match:
        return Concentration(
            float(ww_match.group(1)) / 100.0, ConcentrationBasis.WEIGHT_WEIGHT, raw_input=raw
        )

    vv_match = _VV_PCT_RE.search(lower)
    if vv_match:
        return Concentration(
            float(vv_match.group(1)) / 100.0, ConcentrationBasis.VOLUME_VOLUME, raw_input=raw
        )

    wv_match = _WV_PCT_RE.search(lower)
    if wv_match:
        return Concentration(
            float(wv_match.group(1)) / 100.0, ConcentrationBasis.WEIGHT_VOLUME, raw_input=raw
        )

    bare_pct = _PCT_RE.search(lower)
    if bare_pct:
        if strict:
            raise ValueError(
                f"concentration '{raw}' has no basis (w/w, v/v, w/v required). "
                f"Use e.g. '10% w/w' or '10% in DPG'."
            )
        return Concentration(
            float(bare_pct.group(1)) / 100.0,
            ConcentrationBasis.UNSPECIFIED,
            raw_input=raw,
        )

    raise ValueError(f"unrecognized concentration format: '{raw}'")


def _normalize_carrier(carrier: str) -> str:
    """Normalize carrier name to canonical form."""
    c = carrier.strip().lower()
    c = re.sub(r"\s*[\(\[].*?[\)\]]", "", c)
    mapping = {
        "dpg": "dipropylene glycol",
        "dipropylene glycol": "dipropylene glycol",
        "dep": "diethyl phthalate",
        "diethyl phthalate": "diethyl phthalate",
        "tec": "triethyl citrate",
        "triethyl citrate": "triethyl citrate",
        "ipm": "isopropyl myristate",
        "isopropyl myristate": "isopropyl myristate",
        "ethanol": "ethanol",
        "ethyl alcohol": "ethanol",
    }
    return mapping.get(c, c)


def is_carrier(material_name: str) -> bool:
    """Return True if the material is a carrier/solvent, not an odorant."""
    name = material_name.strip().lower()
    return name in CARRIER_MATERIALS


def is_technical(material_name: str) -> bool:
    """Return True if the material is a technical additive, not an odorant."""
    name = material_name.strip().lower()
    return name in TECHNICAL_MATERIALS


def classify_material_category(
    material_name: str,
) -> str:
    """Classify a material as odorant, technical, or carrier.

    Concentration suffixes are stripped before classification so that
    ``"BHT 10%"`` matches ``TECHNICAL_MATERIALS`` and ``"DPG"``
    matches ``CARRIER_MATERIALS`` regardless of appended dilution text.
    """
    name = material_name.strip().lower()
    name = _CONC_STRIP_RE.sub("", name).strip()
    if name in SOLVENT_MATERIALS:
        return "solvent"
    if name in CARRIER_MATERIALS:
        return "carrier"
    if name in TECHNICAL_MATERIALS:
        return "technical"
    return "odorant"


@dataclass(frozen=True, slots=True)
class ActiveAccounting:
    """Breakdown of a formula's active volume by material category.

    ``unallocated_ul`` captures raw volume whose diluent could not be
    classified (unknown or unrecognised carrier/solvent).  It preserves
    total physical conservation without misclassifying an unknown or
    ethanol fraction as carrier.
    """

    odorant_active_ul: float = 0.0
    technical_active_ul: float = 0.0
    carrier_ul: float = 0.0
    solvent_ul: float = 0.0
    ethanol_ul: float = 0.0
    water_ul: float = 0.0
    unallocated_ul: float = 0.0
    total_raw_ul: float = 0.0

    @property
    def total_active_ul(self) -> float:
        return self.odorant_active_ul + self.technical_active_ul

    @property
    def classified_total(self) -> float:
        """Sum of all four classified categories (excludes unallocated)."""
        return (
            self.odorant_active_ul
            + self.technical_active_ul
            + self.carrier_ul
            + self.solvent_ul
            + self.unallocated_ul
        )

    @property
    def odorant_pct_of_raw(self) -> float:
        if self.total_raw_ul <= 0:
            return 0.0
        return (self.odorant_active_ul / self.total_raw_ul) * 100.0

    @property
    def total_active_pct_of_raw(self) -> float:
        if self.total_raw_ul <= 0:
            return 0.0
        return (self.total_active_ul / self.total_raw_ul) * 100.0

    @property
    def carrier_pct_of_raw(self) -> float:
        if self.total_raw_ul <= 0:
            return 0.0
        return (self.carrier_ul / self.total_raw_ul) * 100.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActiveAccounting:
        return cls(
            odorant_active_ul=float(data.get("odorant_active_ul", 0.0)),
            technical_active_ul=float(data.get("technical_active_ul", 0.0)),
            carrier_ul=float(data.get("carrier_ul", 0.0)),
            solvent_ul=float(data.get("solvent_ul", 0.0)),
            ethanol_ul=float(data.get("ethanol_ul", 0.0)),
            water_ul=float(data.get("water_ul", 0.0)),
            unallocated_ul=float(data.get("unallocated_ul", 0.0)),
            total_raw_ul=float(data.get("total_raw_ul", 0.0)),
        )


# Regex to match "% in X" pattern anywhere in a string (no ^/$ anchors),
# so material names like "Galaxolide 50% in DPG" can be parsed.
_PCT_IN_DILUENT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*in\s+([A-Za-z\s/-]+)",
    re.IGNORECASE,
)


def _infer_diluent_category(material_name: str) -> str:
    """Return ``"carrier"``, ``"solvent"``, or ``"unknown"`` for the
    diluent parsed from *material_name*.

    Used to allocate the inactive fraction of a diluted odorant stock to
    the correct category instead of silently dumping it all into carrier.
    """
    lower = material_name.strip().lower()
    m = _PCT_IN_DILUENT_RE.search(lower)
    if not m:
        return "unknown"
    carrier = _normalize_carrier(m.group(2).strip())
    if carrier in CARRIER_MATERIALS:
        return "carrier"
    # Include common ethanol synonyms
    if carrier in ("ethanol", "ethyl alcohol", "alcohol", "aqua", "water"):
        return "solvent"
    return "unknown"


def compute_active_accounting(
    materials: list[DeclaredStock | tuple[str, float, float]],
) -> ActiveAccounting:
    """Compute active-odorant / technical / carrier / solvent breakdown.

    The inactive fraction of a diluted stock is allocated to *carrier*,
    *solvent*, or *unallocated* according to the named diluent.

    * DPG, DEP, TEC, IPM -> carrier
    * ethanol or aqueous ethanol -> solvent
    * unknown/unrecognised diluent -> unallocated (preserves total
      conservation without misclassification)

    Args:
        materials: list of (name, raw_ul, active_fraction) tuples

    Returns:
        ActiveAccounting with separated totals
    """
    if not materials:
        raise ReconstructionInputError("active accounting materials cannot be empty")

    declared = [material for material in materials if isinstance(material, DeclaredStock)]
    if declared and len(declared) != len(materials):
        raise ReconstructionInputError(
            "declared and legacy accounting inputs cannot be mixed"
        )
    if declared:
        bases = {stock.basis for stock in declared}
        units = {stock.unit for stock in declared}
        if len(bases) != 1 or len(units) != 1:
            raise ReconstructionInputError(
                "active accounting requires unit/basis consistency across declared stocks"
            )

        odorant_active_ul = 0.0
        technical_active_ul = 0.0
        carrier_ul = 0.0
        solvent_ul = 0.0
        ethanol_ul = 0.0
        water_ul = 0.0
        unallocated_ul = 0.0
        total_raw_ul = 0.0
        for stock in declared:
            total_raw_ul += stock.raw_amount
            for component in stock.components:
                amount = stock.raw_amount * component.fraction
                if component.role == StockComponentRole.ODORANT_ACTIVE:
                    odorant_active_ul += amount
                elif component.role == StockComponentRole.TECHNICAL_ACTIVE:
                    technical_active_ul += amount
                elif component.role == StockComponentRole.CARRIER:
                    carrier_ul += amount
                elif component.role == StockComponentRole.SOLVENT_ETHANOL:
                    ethanol_ul += amount
                    solvent_ul += amount
                elif component.role == StockComponentRole.SOLVENT_WATER:
                    water_ul += amount
                    solvent_ul += amount
                elif component.role == StockComponentRole.SOLVENT:
                    solvent_ul += amount
                else:
                    unallocated_ul += amount

        result = ActiveAccounting(
            odorant_active_ul=odorant_active_ul,
            technical_active_ul=technical_active_ul,
            carrier_ul=carrier_ul,
            solvent_ul=solvent_ul,
            ethanol_ul=ethanol_ul,
            water_ul=water_ul,
            unallocated_ul=unallocated_ul,
            total_raw_ul=total_raw_ul,
        )
        if abs(result.classified_total - result.total_raw_ul) > 1e-7:
            raise ReconstructionInputError(
                "declared stock accounting failed physical conservation"
            )
        return result

    legacy_materials = [material for material in materials if isinstance(material, tuple)]
    for _name, raw_ul, active_fraction in legacy_materials:
        if (
            not isfinite(raw_ul)
            or raw_ul < 0.0
            or not isfinite(active_fraction)
            or not 0.0 <= active_fraction <= 1.0
        ):
            raise ReconstructionInputError(
                "legacy accounting amounts and active fractions must be finite and nonnegative"
            )

    result = ActiveAccounting(total_raw_ul=sum(r for _, r, _ in legacy_materials))
    for name, raw_ul, active_fraction in legacy_materials:
        category = classify_material_category(name)
        active_ul = raw_ul * active_fraction
        if category == "carrier":
            result = ActiveAccounting(
                odorant_active_ul=result.odorant_active_ul,
                technical_active_ul=result.technical_active_ul,
                carrier_ul=result.carrier_ul + raw_ul,
                solvent_ul=result.solvent_ul,
                unallocated_ul=result.unallocated_ul,
                total_raw_ul=result.total_raw_ul,
            )
        elif category == "technical":
            inactive = raw_ul - active_ul
            diluent = _infer_diluent_category(name)
            carrier_ul = inactive if diluent == "carrier" else 0.0
            solvent_ul = inactive if diluent == "solvent" else 0.0
            unallocated = inactive if diluent == "unknown" else 0.0
            result = ActiveAccounting(
                odorant_active_ul=result.odorant_active_ul,
                technical_active_ul=result.technical_active_ul + active_ul,
                carrier_ul=result.carrier_ul + carrier_ul,
                solvent_ul=result.solvent_ul + solvent_ul,
                unallocated_ul=result.unallocated_ul + unallocated,
                total_raw_ul=result.total_raw_ul,
            )
        elif category == "solvent":
            result = ActiveAccounting(
                odorant_active_ul=result.odorant_active_ul,
                technical_active_ul=result.technical_active_ul,
                carrier_ul=result.carrier_ul,
                solvent_ul=result.solvent_ul + raw_ul,
                unallocated_ul=result.unallocated_ul,
                total_raw_ul=result.total_raw_ul,
            )
        else:
            inactive = raw_ul - active_ul
            diluent = _infer_diluent_category(name)
            carrier_ul = inactive if diluent == "carrier" else 0.0
            solvent_ul = inactive if diluent == "solvent" else 0.0
            unallocated = inactive if diluent == "unknown" else 0.0
            result = ActiveAccounting(
                odorant_active_ul=result.odorant_active_ul + active_ul,
                technical_active_ul=result.technical_active_ul,
                carrier_ul=result.carrier_ul + carrier_ul,
                solvent_ul=result.solvent_ul + solvent_ul,
                unallocated_ul=result.unallocated_ul + unallocated,
                total_raw_ul=result.total_raw_ul,
            )
    return result


__all__ = [
    "ActiveAccounting",
    "CARRIER_MATERIALS",
    "Concentration",
    "ConcentrationBasis",
    "DeclaredStock",
    "SOLVENT_MATERIALS",
    "StockComponent",
    "StockComponentRole",
    "TECHNICAL_MATERIALS",
    "_infer_diluent_category",
    "classify_material_category",
    "compute_active_accounting",
    "is_carrier",
    "is_technical",
    "parse_concentration",
]
