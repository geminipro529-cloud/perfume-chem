"""House antioxidant pre-charge: BHT 5% w/v in ethanol.

IFRA Standards 184 (Pinacea derivatives), 186 (Limonene) and 187 (Linalool) say
these materials, and natural products containing substantial amounts of them,
should only be used when (hydro)peroxides are kept low, "for instance by adding
antioxidants at the time of production" (data/regulatory/ifra_cat4_51.json).

The dose is the house dose Kenny mixes: 120 uL of BHT 5% w/v in ethanol per
30 mL of finished perfume (6 mg BHT; the solution is about 100 mg BHT made up to
2.000 mL with ethanol). The row is a technical pre-charge, not an odour row, and
it carries no shelf-life claim.

How a formula file carries it (Rule 1: stock dose, concentration, ODT and OAV stay
separate):

- The parser (``scripts/verify_formula_workflow.py``) keeps an antioxidant row out of
  ``ingredients_ul`` and lists it under ``technical_precharge_rows`` instead, so it never
  enters the odour physics: no ODT, OAV, headspace, role or note.
- Its stock dose is the raw uL of the solution; its active dose is BHT mg, exact for a
  w/v stock (5% w/v = 50 mg per mL, so 120 uL = 6 mg).
- It is outside the liquid stock-charge total (the odour stocks) and inside the
  finished-batch make-up: ethanol q.s. = batch - odour stocks - pre-charge.
- The release gate checks its stock against the same stock contract as every other row
  (RULE 0) and holds, in plain words, while the solution is not recorded.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from engine.name_utils import normalize_name
from engine.units.concentration import ANTIOXIDANT_NAME_TOKENS

HOUSE_BHT_STOCK = "BHT 5% w/v in ethanol"
HOUSE_BHT_FRACTION = 0.05  # 5% w/v: 0.05 g BHT per mL of solution
HOUSE_BHT_FRACTION_BASIS = "mass_per_volume"
HOUSE_BHT_CARRIER = "ethanol"
HOUSE_BHT_MG_PER_UL = 0.05  # 5% w/v = 50 mg per mL
HOUSE_BHT_UL_PER_ML_FINISHED = 4.0  # 120 uL per 30 mL
HOUSE_BHT_MAKE_UP = "about 100 mg BHT made up to 2.000 mL with ethanol"
ANTIOXIDANT_IFRA_STANDARDS = ("IFRA_STD_184", "IFRA_STD_186", "IFRA_STD_187")
ANTIOXIDANT_ROLE = "antioxidant, not an odour row"
TECHNICAL_PRECHARGE_GATE = "technical_precharge"

_ANTIOXIDANT_TOKENS = ANTIOXIDANT_NAME_TOKENS
# Rows the house dose applies to: the house stock under any of its written names.
_HOUSE_STOCK_KEYS = frozenset(
    normalize_name(name)
    for name in (HOUSE_BHT_STOCK, "BHT 5% in ethanol", "BHT 5% w/v EtOH", "BHT 5% w/v ethanol")
)
_MASS_MG_PER_UNIT = {"mg": 1.0, "g": 1000.0, "kg": 1_000_000.0}


def is_antioxidant_row(name: str) -> bool:
    """True for a BHT or tocopherol row, whatever its strength or solvent."""
    normalized = normalize_name(name)
    words = normalized.replace("-", " ").split()
    return any(token in words or normalized.startswith(token) for token in _ANTIOXIDANT_TOKENS)


def is_house_bht_stock(name: str) -> bool:
    """True when ``name`` is the house BHT 5% w/v in ethanol solution."""
    return normalize_name(name) in _HOUSE_STOCK_KEYS


@dataclass(frozen=True)
class AntioxidantPrecharge:
    material: str
    raw_ul: float
    bht_mg: float
    batch_volume_ml: float
    operation: str = "PRECHARGE"
    role: str = ANTIOXIDANT_ROLE

    def as_mapping(self) -> dict[str, object]:
        return {
            "material": self.material,
            "raw_ul": self.raw_ul,
            "bht_mg": self.bht_mg,
            "batch_volume_ml": self.batch_volume_ml,
            "operation": self.operation,
            "role": self.role,
            # The row in the yardstick/formula-row shape, so it can sit beside odour rows.
            "amount": f"{self.raw_ul:g}",
            "unit": "uL",
            "active_fraction": f"{HOUSE_BHT_FRACTION:g}",
            "fraction_basis": HOUSE_BHT_FRACTION_BASIS,
            "carrier": HOUSE_BHT_CARRIER,
            "category": "technical",
            "odour_row": False,
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


# ── Formula-file rows ───────────────────────────────────────────────────────


def _active_mg(
    amount: float, unit: str, fraction: float | None, basis: str
) -> tuple[float | None, str]:
    """Antioxidant mg delivered by one row, and how it was worked out.

    Exact only where no density is needed: a w/v stock poured by volume
    (fraction g/mL = mg/uL) or a neat or w/w stock weighed by mass. Anything
    else is ``None``, never a guess.
    """
    if fraction is None:
        return None, "strength not readable"
    if unit == "uL":
        if basis == "mass_per_volume":
            return round(amount * fraction, 6), "w/v stock by volume: uL x g/mL = mg"
        return None, "a volume of a w/w, v/v or neat stock needs a density to give mg"
    if unit in _MASS_MG_PER_UNIT:
        mass_mg = amount * _MASS_MG_PER_UNIT[unit]
        if fraction >= 1.0 or basis in {"neat", "mass_fraction"}:
            return round(mass_mg * fraction, 6), "weighed stock: mg x w/w fraction"
        return None, "a weighed w/v or v/v stock needs a density to give mg"
    return None, f"unit {unit!r} is not a volume or mass"


def technical_precharge_row(
    material: str,
    amount: float,
    unit: str,
    spec: Mapping[str, Any],
    *,
    strength_problem: str | None = None,
    source_line: int | None = None,
) -> dict[str, Any]:
    """One formula-file antioxidant row, kept apart from the odour rows.

    ``amount`` is the stock dose in ``unit`` (``uL`` for a poured solution, or
    ``mg``/``g`` for a weighed stock); ``spec`` is the parser's stock spec for
    the strength cell. The row carries no odour data: no ODT, OAV, role or note.
    """
    fraction_value = spec.get("fraction")
    fraction = None if fraction_value is None else float(fraction_value)
    basis = str(spec.get("fraction_basis", "unspecified") or "unspecified")
    active_mg, active_basis = _active_mg(float(amount), unit, fraction, basis)
    row: dict[str, Any] = {
        "material": material,
        "amount": float(amount),
        "amount_unit": unit,
        "raw_ul": float(amount) if unit == "uL" else None,
        "fraction": fraction,
        "fraction_basis": basis,
        "carrier": str(spec.get("carrier", "") or ""),
        "declared": bool(spec.get("declared", False)),
        "strength_text": str(spec.get("raw", "") or ""),
        "active_mg": active_mg,
        "active_mg_basis": active_basis,
        "category": "technical",
        "stock_component_role": "technical_active",
        "operation": "PRECHARGE",
        "role": ANTIOXIDANT_ROLE,
        "odour_row": False,
    }
    if strength_problem:
        row["strength_problem"] = strength_problem
    if source_line is not None:
        row["source_line"] = int(source_line)
    return row


def formula_has_antioxidant(formula: Mapping[str, Any]) -> bool:
    """True when a parsed formula carries a BHT or tocopherol row anywhere.

    The parser moves such rows into ``technical_precharge_rows``; a record from
    another source may still list one among ``ingredients_ul``. A check for a
    missing antioxidant must read both.
    """
    if any(
        is_antioxidant_row(str(row.get("material", "")))
        for row in formula.get("technical_precharge_rows", []) or []
    ):
        return True
    return any(is_antioxidant_row(str(name)) for name in formula.get("ingredients_ul", {}) or {})


def precharge_make_up(
    liquid_stock_charge_ul: float,
    technical_rows: Sequence[Mapping[str, Any]],
    batch_volume_ml: float,
) -> dict[str, Any]:
    """Where the pre-charge sits in the finished batch.

    The liquid stock-charge total is the odour stocks only; the pre-charge
    solution is extra liquid inside the batch, so it comes off the ethanol q.s.
    Weighed rows (mg) are not liquid and are left out of both totals here.
    """
    technical_ul = sum(float(row.get("raw_ul") or 0.0) for row in technical_rows)
    batch_ul = float(batch_volume_ml) * 1000.0
    ethanol_qs_ul = batch_ul - float(liquid_stock_charge_ul) - technical_ul
    return {
        "batch_volume_ml": float(batch_volume_ml),
        "liquid_stock_charge_total_ul": round(float(liquid_stock_charge_ul), 6),
        "technical_precharge_ul": round(technical_ul, 6),
        "ethanol_qs_ul": round(ethanol_qs_ul, 6),
        "counted_in_liquid_stock_charge_total": False,
        "counted_in_batch_make_up": True,
        "basis": (
            "batch = liquid stock-charge total (odour stocks) + technical pre-charge "
            "+ ethanol q.s.; weighed solids modelled as uL stay in the stock-charge total"
        ),
    }


def _technical_liquid_ul(formula: Mapping[str, Any]) -> float:
    return sum(
        float(row.get("raw_ul") or 0.0)
        for row in formula.get("technical_precharge_rows", []) or []
    )


def stock_charge_expected_ul(expected_ul: float, formula: Mapping[str, Any]) -> float:
    """The expected liquid stock-charge total to check the odour rows against.

    The house method counts the pre-charge outside the stock-charge total. An
    older file that counted it inside (``Total concentrate: 6000 uL`` with a
    5 uL BHT row) is read the same way: when the odour rows miss the expected
    total by exactly the pre-charge volume, the pre-charge is taken off the
    expected total. Any other gap is left for the subtotal check to report.
    """
    technical_ul = _technical_liquid_ul(formula)
    odour_ul = sum(float(v or 0.0) for v in (formula.get("ingredients_ul", {}) or {}).values())
    if (
        technical_ul > 0
        and abs(odour_ul - expected_ul) > 0.5
        and abs(odour_ul + technical_ul - expected_ul) <= 0.5
    ):
        return float(expected_ul) - technical_ul
    return float(expected_ul)


def _stock_message(row: Mapping[str, Any], issue: Mapping[str, Any]) -> str:
    material = str(row.get("material", ""))
    reason = str(issue.get("reason", "inventory_stock_contract_failed"))
    if reason == "not_in_inventory":
        what = (
            f"the solution ({HOUSE_BHT_MAKE_UP})" if is_house_bht_stock(material) else "it"
        )
        return (
            f"{material} is not recorded as a stock yet: record {what} "
            "on the Stock page before mixing. The gate holds this row until it is recorded."
        )
    if reason in {"inventory_stock_unavailable", "inventory_stock_non_executable"}:
        return f"{material} is recorded but not ready to use ({reason}); check the stock record."
    return f"{material}: stock check says {reason}; check the stock record."


def _default_stock_contract(formula: Mapping[str, Any]) -> Any:
    from engine.pipeline.preflight import resolve_inventory_stock_contract

    return resolve_inventory_stock_contract(formula)


def technical_precharge_gate(
    formula: Mapping[str, Any],
    *,
    batch_volume_ml: float,
    stock_contract: Callable[[Mapping[str, Any]], Any] | None = None,
    expected_concentrate_ul: float | None = None,
) -> dict[str, Any] | None:
    """Gate entry for a formula's technical pre-charge rows; ``None`` when it has none.

    PASS: every row's stock is recorded and ready, its strength is readable, and a
    house BHT row has the house dose. WARN: a house BHT row off the house dose.
    HOLD: a stock that is not recorded or not ready (RULE 0) or a strength that
    gives no mg. The rows never vote in OAV, role, note or headspace gates.
    ``expected_concentrate_ul`` (the run's requested total) lets the entry say
    when that total counted the pre-charge (see ``stock_charge_expected_ul``).
    """
    rows = [dict(row) for row in formula.get("technical_precharge_rows", []) or []]
    if not rows:
        return None
    holds: list[str] = []
    warnings: list[str] = []
    stock_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("material", ""))
        if row.get("strength_problem") or row.get("fraction") is None:
            holds.append(
                f"{name}: strength {row.get('strength_text') or '(blank)'!r} can't be read; "
                "write it as e.g. 5% w/v in ethanol"
            )
        elif row.get("active_mg") is None:
            holds.append(f"{name}: antioxidant mg unknown ({row.get('active_mg_basis')})")
        if is_house_bht_stock(name) and row.get("raw_ul") is not None:
            house = house_bht_precharge(batch_volume_ml)
            if abs(float(row["raw_ul"]) - house.raw_ul) > 1e-6:
                warnings.append(
                    f"{name} {float(row['raw_ul']):g} uL is not the house dose "
                    f"{house.raw_ul:g} uL for {batch_volume_ml:g} mL "
                    f"({HOUSE_BHT_UL_PER_ML_FINISHED:g} uL per mL, {house.bht_mg:g} mg BHT)"
                )
        if row.get("fraction") is not None:
            stock_rows[name] = row

    resolver = stock_contract or _default_stock_contract
    stock_check: dict[str, Any] = {"status": "NOT_RUN", "matched_stocks": [], "issues": []}
    if stock_rows:
        mini = {
            "ingredients_ul": {name: float(row["amount"]) for name, row in stock_rows.items()},
            "dilutions": {name: float(row["fraction"]) for name, row in stock_rows.items()},
            "stock_specs": {
                name: {
                    "fraction": float(row["fraction"]),
                    "fraction_basis": row.get("fraction_basis", "unspecified"),
                    "carrier": row.get("carrier", ""),
                    "approximate": False,
                    "declared": bool(row.get("declared", False)),
                    "raw": row.get("strength_text", ""),
                }
                for name, row in stock_rows.items()
            },
        }
        contract = resolver(mini)
        data = dict(getattr(contract, "data", {}) or {})
        stock_check = {
            "status": str(getattr(contract, "status", "FAIL")),
            "matched_stocks": list(data.get("matched_stocks", []) or []),
            "issues": list(data.get("issues", []) or []),
        }
        for issue in stock_check["issues"]:
            row = stock_rows.get(str(issue.get("material", "")), {})
            holds.append(_stock_message(row or {"material": issue.get("material", "")}, issue))
    matched = {str(m.get("material")): m for m in stock_check["matched_stocks"]}
    for row in rows:
        stock = matched.get(str(row.get("material")))
        row["stock_id"] = str(stock.get("stock_id", "")) if stock else ""
        row["stock_recorded"] = stock is not None
        if row.get("active_mg") is not None and batch_volume_ml > 0:
            row["finished_mg_per_ml"] = round(float(row["active_mg"]) / batch_volume_ml, 6)

    liquid_total = sum(float(v or 0.0) for v in (formula.get("ingredients_ul", {}) or {}).values())
    make_up = precharge_make_up(liquid_total, rows, batch_volume_ml)
    notes: list[str] = []
    if expected_concentrate_ul is not None:
        checked = stock_charge_expected_ul(float(expected_concentrate_ul), formula)
        make_up["expected_concentrate_ul"] = float(expected_concentrate_ul)
        make_up["expected_counts_precharge"] = checked != float(expected_concentrate_ul)
        if make_up["expected_counts_precharge"]:
            notes.append(
                f"The expected concentrate {float(expected_concentrate_ul):g} uL counts this "
                f"pre-charge; the stock-charge subtotal was checked against {checked:g} uL."
            )
    status = "HOLD" if holds else "WARN" if warnings else "PASS"
    summary = "; ".join(
        f"{row['material']} {row['amount']:g} {row['amount_unit']}"
        + (f" = {row['active_mg']:g} mg" if row.get("active_mg") is not None else "")
        for row in rows
    )
    detail = (
        f"Technical pre-charge, first step, not an odour row (no ODT, OAV, role or headspace): "
        f"{summary}. Outside the {make_up['liquid_stock_charge_total_ul']:g} uL liquid "
        f"stock-charge total; inside the {batch_volume_ml:g} mL make-up "
        f"(ethanol q.s. {make_up['ethanol_qs_ul']:g} uL)."
    )
    if holds or warnings or notes:
        detail += " " + " ".join(
            text if text.endswith(".") else f"{text}." for text in (*holds, *warnings, *notes)
        )
    return {
        "gate": TECHNICAL_PRECHARGE_GATE,
        "status": status,
        "detail": detail,
        "data": {
            "rows": rows,
            "make_up": make_up,
            "stock_check": stock_check,
            "holds": holds,
            "warnings": warnings,
            "ifra_basis": list(ANTIOXIDANT_IFRA_STANDARDS),
            "odour_physics": "EXCLUDED_TECHNICAL_ROW",
            "shelf_life_claim": None,
        },
    }


__all__ = [
    "ANTIOXIDANT_IFRA_STANDARDS",
    "ANTIOXIDANT_ROLE",
    "AntioxidantPrecharge",
    "HOUSE_BHT_CARRIER",
    "HOUSE_BHT_FRACTION",
    "HOUSE_BHT_FRACTION_BASIS",
    "HOUSE_BHT_MAKE_UP",
    "HOUSE_BHT_MG_PER_UL",
    "HOUSE_BHT_STOCK",
    "HOUSE_BHT_UL_PER_ML_FINISHED",
    "TECHNICAL_PRECHARGE_GATE",
    "formula_has_antioxidant",
    "house_bht_precharge",
    "is_antioxidant_row",
    "is_house_bht_stock",
    "precharge_make_up",
    "stock_charge_expected_ul",
    "technical_precharge_gate",
    "technical_precharge_row",
]
