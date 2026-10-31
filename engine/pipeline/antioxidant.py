"""House antioxidant pre-charge: BHT 5% w/v in ethanol.

IFRA Standards 184 (Pinacea derivatives), 186 (Limonene) and 187 (Linalool) say
these materials, and natural products containing substantial amounts of them,
should only be used when (hydro)peroxides are kept low, "for instance by adding
antioxidants at the time of production" (data/regulatory/ifra_cat4_51.json).

The dose is the house dose Kenny mixes: 120 uL of BHT 5% w/v in ethanol per
30 mL of finished perfume (6 mg BHT; the solution is about 100 mg BHT made up to
2.000 mL with ethanol). The row is a technical pre-charge, not an odour row, and
it carries no shelf-life claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.name_utils import normalize_name

HOUSE_BHT_STOCK = "BHT 5% w/v in ethanol"
HOUSE_BHT_MG_PER_UL = 0.05  # 5% w/v = 50 mg per mL
HOUSE_BHT_UL_PER_ML_FINISHED = 4.0  # 120 uL per 30 mL
HOUSE_BHT_MAKE_UP = "about 100 mg BHT made up to 2.000 mL with ethanol"
ANTIOXIDANT_IFRA_STANDARDS = ("IFRA_STD_184", "IFRA_STD_186", "IFRA_STD_187")

_ANTIOXIDANT_TOKENS = ("bht", "tocopherol")


def is_antioxidant_row(name: str) -> bool:
    """True for a BHT or tocopherol row, whatever its strength or solvent."""
    normalized = normalize_name(name)
    words = normalized.replace("-", " ").split()
    return any(token in words or normalized.startswith(token) for token in _ANTIOXIDANT_TOKENS)


@dataclass(frozen=True)
class AntioxidantPrecharge:
    material: str
    raw_ul: float
    bht_mg: float
    batch_volume_ml: float
    operation: str = "PRECHARGE"
    role: str = "antioxidant, not an odour row"

    def as_mapping(self) -> dict[str, object]:
        return {
            "material": self.material,
            "raw_ul": self.raw_ul,
            "bht_mg": self.bht_mg,
            "batch_volume_ml": self.batch_volume_ml,
            "operation": self.operation,
            "role": self.role,
            "dose_basis": (
                f"house dose {HOUSE_BHT_UL_PER_ML_FINISHED:g} uL per mL of finished perfume "
                f"(120 uL per 30 mL = 6 mg BHT)"
            ),
            "make_up": HOUSE_BHT_MAKE_UP,
        }


def house_bht_precharge(batch_volume_ml: float) -> AntioxidantPrecharge:
    """The house BHT row for a finished batch of ``batch_volume_ml``."""
    if batch_volume_ml <= 0:
        raise ValueError("batch_volume_ml must be positive")
    raw_ul = float(round(HOUSE_BHT_UL_PER_ML_FINISHED * batch_volume_ml))
    return AntioxidantPrecharge(
        material=HOUSE_BHT_STOCK,
        raw_ul=raw_ul,
        bht_mg=round(raw_ul * HOUSE_BHT_MG_PER_UL, 3),
        batch_volume_ml=float(batch_volume_ml),
    )
