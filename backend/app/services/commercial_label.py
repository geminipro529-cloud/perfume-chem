"""Thai retail label and IFRA Category 4 self-declaration for one bottled batch.

Two pure functions feed the Batch view's printable pages:

* ``build_label(fields, rows)``: the front and back label of a 30 mL perfume sold
  in Thailand (Thai lines required, English lines optional). Fragrance allergens
  are not listed: under the ASEAN cosmetic rules "Parfum (Fragrance)" suffices.
* ``build_ifra_statement(gate_json, meta)``: the manufacturer's own declaration of
  conformity with the IFRA 51st Amendment, Category 4 (fine fragrance), read from
  the release gate's ``safety_ifra_allergen`` result. It says "Conforms" only when
  that gate passed with no violation; anything else is a draft that names each
  open item.

Missing inputs print as ``[ to fill ]`` and keep the page marked as a draft.
Neither function decides anything about the formula, and neither is legal advice.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

TO_FILL = "[ to fill ]"
LABEL_DRAFT_BANNER = "DRAFT — not for print"
STATEMENT_DRAFT_BANNER = "DRAFT — not a conformity statement until these are resolved"
LABEL_FOOTER = (
    "Draft prepared from the formula for the manufacturer to check; not legal advice. "
    "Check current Thai FDA labelling rules before printing."
)
STATEMENT_FOOTER = (
    "Prepared from the release gate's calculation for the manufacturer to check and sign; "
    "not legal advice and not issued or endorsed by IFRA."
)

# The repository's sourced table (data/regulatory/ifra_cat4_51.json, read by
# engine/ifra_standards.py) is the 51st Amendment, Category 4, % w/w of the finished product.
IFRA_AMENDMENT = 51
IFRA_CATEGORY = "4"
IFRA_TABLE_SOURCE = (
    "Category 4 limits are the IFRA 51st Amendment table kept in this project "
    "(data/regulatory/ifra_cat4_51.json, read by engine/ifra_standards.py), each row "
    "quoted from the IFRA standard it names."
)

TYPE_OPTIONS: dict[str, str] = {
    "eau_de_parfum": "Eau de Parfum",
    "eau_de_toilette": "Eau de Toilette",
    "parfum": "Parfum",
    "extrait_de_parfum": "Extrait de Parfum",
    "eau_de_cologne": "Eau de Cologne",
}
TYPE_NOTE = (
    "No law sets a percentage for these names; trade usage is roughly "
    "Eau de Parfum 10–20 % and Eau de Toilette 5–15 %."
)

# Carrier text as written on stock rows -> INCI name for the ingredient line.
CARRIER_INCI: dict[str, str] = {
    "dpg": "Dipropylene Glycol",
    "dipropylene glycol": "Dipropylene Glycol",
    "dep": "Diethyl Phthalate",
    "diethyl phthalate": "Diethyl Phthalate",
    "ipm": "Isopropyl Myristate",
    "isopropyl myristate": "Isopropyl Myristate",
    "tec": "Triethyl Citrate",
    "triethyl citrate": "Triethyl Citrate",
    "bb": "Benzyl Benzoate",
    "benzyl benzoate": "Benzyl Benzoate",
}
# Ethanol in a stock is already declared as Alcohol.
ALCOHOL_NAMES = frozenset({
    "alcohol", "alcohol denat", "alcohol denat.", "denatured alcohol", "ethanol",
    "etoh", "perfumer's alcohol", "perfumers alcohol", "perfumers' alcohol", "sda 40b",
    "sda40b",
})

_LABEL_REQUIRED_FOR_PRINT = (
    "notification_no", "manufacturer_name", "manufacturer_address", "lot", "mfg",
)
_FIELD_TITLES = {
    "name": "Product name",
    "thai_name": "Thai spelling of the name",
    "manufacturer_name": "Manufacturer name",
    "manufacturer_address": "Manufacturer address",
    "lot": "Lot (batch) number",
    "mfg": "Manufacture date (MM/YYYY)",
    "exp": "Expiry date (MM/YYYY), needed when shelf life is under 30 months",
    "notification_no": "Thai FDA notification number",
    "date": "Statement date",
    "product_name": "Product name",
}
_LABEL_TEXT_LIMITS = {
    "name": 80,
    "thai_name": 120,
    "manufacturer_name": 120,
    "manufacturer_address": 300,
    "lot": 40,
    "notification_no": 40,
    "mfg": 7,
    "exp": 7,
}
_LABEL_BOOL_FIELDS = ("alcohol_denat", "declare_carriers", "include_english")
_LABEL_KEYS = frozenset({
    *_LABEL_TEXT_LIMITS, *_LABEL_BOOL_FIELDS, "type", "net_ml", "shelf_life_months",
    "carrier_names",
})
_META_TEXT_LIMITS = {
    "product_name": 120,
    "lot": 40,
    "date": 32,
    "signatory_name": 120,
    "manufacturer_name": 120,
    "manufacturer_address": 300,
}
_META_KEYS = frozenset({*_META_TEXT_LIMITS, "fragrance_concentration_pct"})
_MONTH_YEAR = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_UNIT_UL = {"ul": 1.0, "µl": 1.0, "μl": 1.0, "ml": 1000.0}
_MAX_ROWS = 500


class CommercialPackError(ValueError):
    """An input the label or statement cannot be built from."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------- inputs


def _text(value: Any, key: str, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CommercialPackError("invalid_field", f"{key} must be text.")
    text = " ".join(value.split())
    if _CONTROL.search(value.replace("\n", " ").replace("\t", " ")):
        raise CommercialPackError("invalid_field", f"{key} contains control characters.")
    if len(text) > limit:
        raise CommercialPackError("invalid_field", f"{key} is longer than {limit} characters.")
    return text or None


def _number(value: Any, key: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CommercialPackError("invalid_field", f"{key} must be a number.")
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise CommercialPackError("invalid_field", f"{key} must be between {low:g} and {high:g}.")
    return number


def _month_year(value: str | None, key: str) -> tuple[int, int] | None:
    if value is None:
        return None
    match = _MONTH_YEAR.match(value)
    if match is None:
        raise CommercialPackError("invalid_field", f"{key} must be written MM/YYYY.")
    return int(match.group(2)), int(match.group(1))


def _label_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, Mapping):
        raise CommercialPackError("invalid_fields", "fields must be an object.")
    unknown = sorted(str(key) for key in fields if key not in _LABEL_KEYS)
    if unknown:
        raise CommercialPackError("invalid_fields", f"Unknown label field(s): {', '.join(unknown)}.")
    clean: dict[str, Any] = {
        key: _text(fields.get(key), key, limit) for key, limit in _LABEL_TEXT_LIMITS.items()
    }
    for key in _LABEL_BOOL_FIELDS:
        value = fields.get(key, key == "include_english")
        if not isinstance(value, bool):
            raise CommercialPackError("invalid_field", f"{key} must be true or false.")
        clean[key] = value
    type_key = fields.get("type", "eau_de_parfum")
    if type_key not in TYPE_OPTIONS:
        raise CommercialPackError(
            "invalid_field", f"type must be one of: {', '.join(TYPE_OPTIONS)}."
        )
    clean["type"] = type_key
    clean["net_ml"] = _number(fields.get("net_ml", 30), "net_ml", 1, 1000)
    shelf = fields.get("shelf_life_months")
    clean["shelf_life_months"] = None if shelf is None else _number(
        shelf, "shelf_life_months", 1, 120
    )
    mfg = _month_year(clean["mfg"], "mfg")
    exp = _month_year(clean["exp"], "exp")
    if mfg is not None and exp is not None and exp <= mfg:
        raise CommercialPackError("invalid_field", "exp must be later than mfg.")
    names = fields.get("carrier_names") or {}
    if not isinstance(names, Mapping):
        raise CommercialPackError("invalid_field", "carrier_names must be an object.")
    clean["carrier_names"] = {}
    for raw, inci in names.items():
        raw_key = _carrier_key(str(raw))
        inci_text = _text(inci, f"carrier_names[{raw}]", 80)
        if raw_key and inci_text:
            clean["carrier_names"][raw_key] = inci_text
    return clean


def _carrier_key(text: str) -> str:
    return " ".join(text.lower().split())


def _carrier_parts(text: str) -> list[str]:
    """Carrier components of one stock's carrier text, e.g. 'dpg + ipm + ethanol'."""
    cleaned = re.sub(r"\b[wv]\s*/\s*[wv]\b", " ", text.lower())
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*%", " ", cleaned)
    parts = re.split(r"\+|,|;|&|/|\band\b", cleaned)
    return [key for key in (_carrier_key(part) for part in parts) if key]


def _row_ul(row: Mapping[str, Any], index: int) -> float:
    if "volume_ul" in row:
        return _number(row["volume_ul"], f"rows[{index}].volume_ul", 0, 1e7)
    amount = row.get("amount_decimal")
    unit = _UNIT_UL.get(str(row.get("amount_unit") or "").strip().lower())
    if amount is None or unit is None:
        raise CommercialPackError(
            "invalid_rows",
            f"rows[{index}] needs volume_ul, or amount_decimal with amount_unit uL or mL.",
        )
    try:
        value = float(amount)
    except (TypeError, ValueError) as error:
        raise CommercialPackError(
            "invalid_rows", f"rows[{index}].amount_decimal must be a number."
        ) from error
    return _number(value, f"rows[{index}].amount_decimal", 0, 1e7) * unit


def _row_fraction(row: Mapping[str, Any], index: int) -> float | None:
    value = row.get("stock_fraction_decimal", row.get("dilution"))
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise CommercialPackError(
            "invalid_rows", f"rows[{index}] stock fraction must be a number."
        ) from error
    if not math.isfinite(number) or not 0 < number <= 1:
        raise CommercialPackError(
            "invalid_rows", f"rows[{index}] stock fraction must be above 0 and at most 1."
        )
    return number


def _rows(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if not isinstance(rows, Sequence) or isinstance(rows, str | bytes):
        raise CommercialPackError("invalid_rows", "rows must be a list.")
    if len(rows) > _MAX_ROWS:
        raise CommercialPackError("invalid_rows", f"At most {_MAX_ROWS} rows.")
    parsed = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CommercialPackError("invalid_rows", f"rows[{index}] must be an object.")
        name = _text(
            row.get("material") or row.get("identity_name") or row.get("name"),
            f"rows[{index}].material",
            200,
        )
        carrier = _text(row.get("carrier"), f"rows[{index}].carrier", 200)
        parsed.append({
            "material": name or "",
            "ul": _row_ul(row, index),
            "fraction": _row_fraction(row, index),
            "carrier": carrier or "",
        })
    return parsed


# --------------------------------------------------------------------------- label


def _ingredients(
    rows: list[dict[str, Any]], fields: dict[str, Any]
) -> dict[str, Any]:
    """Ingredient line: Alcohol, then Parfum and any declared carriers by volume."""
    alcohol = "Alcohol Denat." if fields["alcohol_denat"] else "Alcohol"
    volumes: dict[str, float] = {"Parfum (Fragrance)": 0.0}
    order_known = True
    unknown: list[str] = []

    def carrier_inci(key: str) -> str | None:
        return fields["carrier_names"].get(key) or CARRIER_INCI.get(key)

    for row in rows:
        material_key = _carrier_key(row["material"])
        if material_key in ALCOHOL_NAMES:
            continue
        if material_key in CARRIER_INCI or material_key in fields["carrier_names"]:
            # A row that is itself a carrier (e.g. a DPG top-up).
            inci = carrier_inci(material_key) or row["material"]
            volumes[inci] = volumes.get(inci, 0.0) + row["ul"]
            continue
        parts = [part for part in _carrier_parts(row["carrier"]) if part not in ALCOHOL_NAMES]
        fraction = row["fraction"]
        if fraction is None:
            fraction = 1.0 if not row["carrier"] else None
        if fraction is None:
            order_known = False
            fraction = 1.0
        volumes["Parfum (Fragrance)"] += row["ul"] * fraction
        if len(parts) > 1:
            order_known = False  # the split between carriers in one stock is not written
        for part in parts:
            inci = carrier_inci(part)
            if inci is None:
                if part not in unknown:
                    unknown.append(part)
                continue
            share = row["ul"] * (1 - fraction) / len(parts)
            volumes[inci] = volumes.get(inci, 0.0) + share
    carriers = [name for name in volumes if name != "Parfum (Fragrance)"]
    if not fields["declare_carriers"]:
        items = [alcohol, "Parfum (Fragrance)"]
        return {"line": ", ".join(items), "items": items, "carriers": carriers,
                "unknown_carriers": unknown, "order_note": None}
    if rows and order_known:
        rest = sorted(volumes, key=lambda name: (-volumes[name], name))
        note = None
    else:
        rest = ["Parfum (Fragrance)", *sorted(carriers)]
        note = (
            "Parfum and carrier volumes could not all be worked out from the rows, so "
            "they are not in order of amount; check the order before printing."
            if carriers or unknown
            else None
        )
    items = [alcohol, *rest]
    items.extend(f"{TO_FILL} (carrier written as “{part}”)" for part in unknown)
    return {"line": ", ".join(items), "items": items, "carriers": carriers,
            "unknown_carriers": unknown, "order_note": note}


def _concentration(rows: list[dict[str, Any]], net_ml: float) -> float | None:
    if not rows:
        return None
    stock_ul = sum(
        row["ul"] for row in rows if _carrier_key(row["material"]) not in ALCOHOL_NAMES
    )
    return round(float(stock_ul) / (net_ml * 1000) * 100, 1)


def _ml(value: float) -> str:
    return f"{value:g}"


def build_label(fields: Any, rows: Any = ()) -> dict[str, Any]:
    """Printable Thai label content from the user's fields and the formula rows."""
    clean = _label_fields(fields)
    parsed = _rows(rows)
    missing: list[dict[str, str]] = []

    def value(key: str, *, required: bool = True) -> str:
        text = clean.get(key)
        if text:
            return str(text)
        if required:
            missing.append({"field": key, "title": _FIELD_TITLES[key]})
        return TO_FILL

    name = value("name")
    type_name = TYPE_OPTIONS[clean["type"]]
    thai_name = value("thai_name")
    maker = value("manufacturer_name")
    address = value("manufacturer_address")
    lot = value("lot")
    mfg = value("mfg")
    notification = value("notification_no")
    exp_needed = clean["shelf_life_months"] is not None and clean["shelf_life_months"] < 30
    exp = clean["exp"] or (value("exp") if exp_needed else None)
    net = _ml(clean["net_ml"])
    ingredients = _ingredients(parsed, clean)
    for part in ingredients["unknown_carriers"] if clean["declare_carriers"] else []:
        missing.append({"field": "carrier_names", "title": f"INCI name for carrier “{part}”"})

    thai_address = address
    if address != TO_FILL and not address.endswith("ประเทศไทย"):
        thai_address = f"{address} ประเทศไทย"
    thai = [
        {"label": "ชื่อเครื่องสำอาง", "text": f"{name} {type_name} ({thai_name})"},
        {"label": "ประเภทเครื่องสำอาง", "text": "น้ำหอม"},
        {"label": "ส่วนประกอบ", "text": ingredients["line"]},
        {"label": "วิธีใช้", "text": "ฉีดพ่นบนผิวบริเวณลำคอและข้อมือ ห่างจากผิวประมาณ 15–20 ซม."},
        {"label": "คำเตือน",
         "text": "ใช้ภายนอกเท่านั้น ระวังอย่าให้เข้าตา หากมีอาการระคายเคืองให้หยุดใช้"},
        {"label": "", "text": "ไวไฟ เก็บให้ห่างจากความร้อนและเปลวไฟ เก็บให้พ้นมือเด็ก"},
        {"label": "ผลิตโดย", "text": f"{maker} {thai_address}"},
        {"label": "ปริมาณสุทธิ", "text": f"{net} มล."},
        {"label": "เลขที่ผลิต", "text": lot},
        {"label": "วันที่ผลิต", "text": mfg},
    ]
    if exp is not None:
        thai.append({"label": "วันหมดอายุ", "text": exp})
    thai.append({"label": "เลขที่ใบรับจดแจ้ง", "text": notification})

    english: list[str] = []
    if clean["include_english"]:
        batch = f"Batch no.: {lot}  MFG: {mfg}" + (f"  EXP: {exp}" if exp is not None else "")
        english_address = address
        if address != TO_FILL and not address.rstrip(". ").endswith("Thailand"):
            english_address = f"{address}, Thailand"
        english = [
            f"{name} {type_name}",
            "Type: Perfume",
            f"Ingredients: {ingredients['line']}",
            "Directions: Spray onto the neck and wrists from about 15–20 cm.",
            "Caution: For external use only. Avoid contact with eyes. "
            "Stop use if irritation occurs.",
            "Flammable: keep away from heat and flame. Keep out of reach of children.",
            f"Manufactured by: {maker}, {english_address}",
            f"Net content: {net} mL",
            batch,
            f"Thai FDA notification no.: {notification}",
        ]

    concentration = _concentration(parsed, clean["net_ml"])
    if concentration is None:
        concentration_text = "Fragrance concentration: not computable without the formula rows."
    else:
        concentration_text = (
            f"Fragrance stocks are {concentration:g} % v/v of the {net} mL bottle."
        )
        if concentration > 100:
            concentration_text += " That is more than the bottle holds; check the rows."
    blocking = {item["field"] for item in missing} & {*_LABEL_REQUIRED_FOR_PRINT, "exp",
                                                      "carrier_names"}
    draft = bool(blocking)
    return {
        "draft": draft,
        "draft_banner": LABEL_DRAFT_BANNER if draft else None,
        "missing": missing,
        "front": [name, type_name, "น้ำหอม", f"{net} มล. / {net} mL"],
        "thai": thai,
        "english": english,
        "ingredients": ingredients,
        "type": {
            "key": clean["type"],
            "name": type_name,
            "concentration_pct": concentration,
            "concentration_text": concentration_text,
            "note": TYPE_NOTE,
        },
        "type_options": [{"key": key, "name": label} for key, label in TYPE_OPTIONS.items()],
        "footer": LABEL_FOOTER,
    }


# --------------------------------------------------------------------------- IFRA


def _pct(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return "—"
    return f"{value:.4g} %"


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _list_of_dicts(data: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _statement_meta(meta: Any) -> dict[str, Any]:
    if meta is None:
        meta = {}
    if not isinstance(meta, Mapping):
        raise CommercialPackError("invalid_meta", "meta must be an object.")
    unknown = sorted(str(key) for key in meta if key not in _META_KEYS)
    if unknown:
        raise CommercialPackError("invalid_meta", f"Unknown meta field(s): {', '.join(unknown)}.")
    clean: dict[str, Any] = {
        key: _text(meta.get(key), key, limit) for key, limit in _META_TEXT_LIMITS.items()
    }
    pct = meta.get("fragrance_concentration_pct")
    clean["fragrance_concentration_pct"] = None if pct is None else _number(
        pct, "fragrance_concentration_pct", 0, 100
    )
    return clean


def _ifra_gate(gate_json: Any) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(gate_json, Mapping):
        raise CommercialPackError("invalid_gate", "The gate result must be a JSON object.")
    formulas = gate_json.get("formulas")
    if not isinstance(formulas, list) or not formulas or not isinstance(formulas[0], Mapping):
        raise CommercialPackError("invalid_gate", "The gate result has no formulas[0].")
    formula = formulas[0]
    gates = formula.get("gates")
    if isinstance(gates, list):
        for gate in gates:
            if isinstance(gate, Mapping) and gate.get("gate") == "safety_ifra_allergen":
                return formula, gate
    raise CommercialPackError(
        "invalid_gate", "The gate result has no safety_ifra_allergen gate to read."
    )


def _table_rows(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every material with its own Category 4 limit, then each counted group total."""
    rows: list[dict[str, Any]] = []
    for row in _list_of_dicts(data, "rows"):
        limit = _num(row.get("limit_pct"))
        actual = _num(row.get("actual_pct"))
        if limit is None or limit <= 0:
            continue
        rows.append(_table_row(
            kind="material",
            name=str(row.get("material") or ""),
            standard=row.get("standard"),
            actual=actual,
            limit=limit,
            verdict=row.get("verdict"),
            detail="",
        ))
    substances = {
        str(total.get("standard")): str(total.get("substance"))
        for total in _list_of_dicts(data, "constituent_totals")
        if total.get("standard") and total.get("substance")
    }
    for group in _list_of_dicts(data, "groups"):
        limit = _num(group.get("limit_pct"))
        if limit is None or limit <= 0:
            continue
        key = str(group.get("group") or group.get("material") or "")
        standard = str(group.get("standard") or "")
        if key.endswith("_constituents") and standard in substances:
            name = f"{substances[standard]} (constituents of naturals)"
        else:
            name = key.replace("_", " ").strip().capitalize()
        members = group.get("members")
        detail = ""
        if isinstance(members, Mapping):
            detail = ", ".join(
                f"{member} {_pct(_num(pct))}" for member, pct in members.items()
            )
        rows.append(_table_row(
            kind="group",
            name=name,
            standard=standard or None,
            actual=_num(group.get("actual_pct")),
            limit=limit,
            verdict=group.get("verdict"),
            detail=detail,
        ))
    return rows


def _table_row(
    *, kind: str, name: str, standard: Any, actual: float | None, limit: float,
    verdict: Any, detail: str,
) -> dict[str, Any]:
    share = None if actual is None else round(actual / limit * 100, 1)
    return {
        "kind": kind,
        "name": name,
        "standard": str(standard) if standard else None,
        "actual_pct": actual,
        "limit_pct": limit,
        "pct_of_limit": share,
        "actual_text": _pct(actual),
        "limit_text": _pct(limit),
        "pct_of_limit_text": "—" if share is None else f"{share:g} %",
        "verdict": str(verdict or ""),
        "detail": detail,
    }


def _failures(data: Mapping[str, Any]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    # headroom_violations holds every over-limit row; violations is the subset over the
    # limit itself, read too in case a gate result carries only that list.
    for row in _list_of_dicts(data, "headroom_violations") + _list_of_dicts(data, "violations"):
        name = str(row.get("material") or row.get("group") or "")
        message = str(row.get("message") or "") or (
            f"{name} at {_pct(_num(row.get('actual_pct')))} is over its Category 4 limit of "
            f"{_pct(_num(row.get('limit_pct')))}."
        )
        if (name, message) not in seen:
            seen.add((name, message))
            failures.append({"material": name, "text": message})
    named = {name for name, _ in seen}
    banned = data.get("banned")
    for name in banned if isinstance(banned, list) else []:
        if str(name) not in named:
            failures.append({
                "material": str(name),
                "text": f"{name} is prohibited by IFRA and cannot be in the product.",
            })
    return failures


def _open_items(data: Mapping[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    def add(kind: str, material: str, text: str) -> None:
        items.append({"kind": kind, "material": material, "text": text})

    for row in _list_of_dicts(data, "holds"):
        name = str(row.get("material") or "")
        add("not_in_table", name, (
            f"{name} ({_pct(_num(row.get('actual_pct')))} of the product) is not in the IFRA "
            "Category 4 table, so nothing was checked for it. Needs the supplier's IFRA "
            "certificate, or a match to the IFRA standard it falls under."
        ))
    for row in _list_of_dicts(data, "undisclosed_bases"):
        name = str(row.get("material") or "")
        add("base_composition_unknown", name, (
            f"{name} ({_pct(_num(row.get('actual_pct')))} of the product) is a supplier base "
            "whose composition is not published, so restricted substances inside it are not "
            "counted. Needs the supplier's IFRA certificate for Category 4."
        ))
    for row in _list_of_dicts(data, "warnings"):
        name = str(row.get("material") or row.get("group") or "")
        if row.get("ifra_status") == "natural_no_own_standard":
            add("natural_constituents", name, (
                f"{name} ({_pct(_num(row.get('actual_pct')))} of the product) is a natural "
                "with no IFRA standard of its own; only some of its restricted constituents "
                "are counted. Needs the supplier's IFRA certificate to confirm the rest."
            ))
        elif row.get("ifra_status") == "restricted" or "group" in row:
            share = _num(row.get("usage_pct"))
            add("near_limit", name, (
                f"{name} is within its Category 4 limit but close to it "
                f"({_pct(_num(row.get('actual_pct')))} of {_pct(_num(row.get('limit_pct')))}"
                + (f", {share:g} % of the limit" if share is not None else "")
                + "). The gate flags this; confirm the weighing at this dose."
            ))
    for name in data.get("stock_conflicts") or []:
        add("stock_conflict", str(name), (
            f"{name} is written at more than one strength, so its amount in the product "
            "is not known."
        ))
    for text in data.get("unwritten_strengths") or []:
        add("unwritten_strength", "", str(text))
    if data.get("overfilled"):
        add("overfilled", "", (
            "The stocks add up to more than the bottle holds, so the % in the finished "
            "product is not defined."
        ))
    if data.get("batch_volume_source") == "default":
        volume = _num(data.get("batch_volume_ml"))
        add("bottle_size_assumed", "", (
            "The bottle size was not found in the formula; the gate assumed "
            f"{volume:g} mL. Re-run the gate with the bottle size." if volume is not None
            else "The bottle size was not found in the formula. Re-run the gate with it."
        ))
    allergens = data.get("allergen_declarations")
    if isinstance(allergens, list) and allergens:
        names = sorted({str(name) for name in allergens})
        add("allergen_declarations", "", (
            f"The gate lists EU allergens for declaration ({', '.join(names)}). These are "
            "not IFRA Category 4 limits; the gate still reports them as a warning, so the "
            "IFRA check did not pass cleanly."
        ))
    return items


def _fragrance_concentration(
    formula: Mapping[str, Any], data: Mapping[str, Any], override: float | None
) -> tuple[float | None, str]:
    if override is not None:
        return override, f"{override:g} % fragrance in the finished product (as entered)."
    state = formula.get("formula_state")
    state = state if isinstance(state, Mapping) else {}
    total_ul = _num(state.get("total_raw_ul"))
    volume_ml = _num(data.get("batch_volume_ml")) or _num(state.get("batch_volume_ml"))
    if total_ul is None or not volume_ml:
        return None, f"Fragrance concentration: {TO_FILL}"
    pct = round(total_ul / (volume_ml * 1000) * 100, 1)
    return pct, (
        f"Fragrance stocks are {pct:g} % v/v of the finished product "
        f"({total_ul / 1000:.4g} mL of stocks in a {volume_ml:g} mL bottle)."
    )


def build_ifra_statement(gate_json: Any, meta: Any = None) -> dict[str, Any]:
    """The manufacturer's IFRA Category 4 self-declaration from a release-gate result."""
    clean = _statement_meta(meta)
    formula, gate = _ifra_gate(gate_json)
    raw_data = gate.get("data")
    data: Mapping[str, Any] = raw_data if isinstance(raw_data, Mapping) else {}
    status = str(gate.get("status") or "").upper()
    table = data.get("ifra_table")
    table = table if isinstance(table, Mapping) else {}
    amendment = table.get("amendment_in_force")
    category = str(table.get("category") or "")

    failures = _failures(data)
    open_items = _open_items(data)
    if amendment != IFRA_AMENDMENT or category != IFRA_CATEGORY:
        open_items.insert(0, {"kind": "table_mismatch", "material": "", "text": (
            f"The gate used IFRA amendment {amendment or 'not stated'}, category "
            f"{category or 'not stated'}; this statement is for the {_ordinal(IFRA_AMENDMENT)} "
            f"Amendment, Category {IFRA_CATEGORY}. Re-run the gate on that table."
        )})

    if status == "FAIL" or failures:
        verdict = "Does not conform"
        verdict_text = (
            "The product does not conform to IFRA Category 4: the items below are over "
            "their limit or prohibited."
        )
    elif status == "PASS" and not open_items:
        verdict = "Conforms"
        verdict_text = (
            "On the calculation below, every material with an IFRA Category 4 limit and "
            "every counted constituent total is within its limit."
        )
    else:
        verdict = "Not yet determined"
        verdict_text = (
            f"The IFRA check is {status or 'missing'}: the open items below must be "
            "resolved before this can be a conformity statement."
        )
        if not open_items:
            detail = str(gate.get("detail") or "").strip()
            open_items.append({"kind": "gate_status", "material": "", "text": (
                detail or f"The IFRA check did not complete (status {status or 'missing'})."
            )})

    missing: list[dict[str, str]] = []

    def value(key: str) -> str:
        text = clean.get(key)
        if text:
            return str(text)
        missing.append({"field": key, "title": _FIELD_TITLES.get(key, key)})
        return TO_FILL

    product = clean["product_name"] or str(formula.get("name") or "") or value("product_name")
    lot = value("lot")
    date = value("date")
    maker = value("manufacturer_name")
    if clean["manufacturer_address"]:
        maker = f"{maker}, {clean['manufacturer_address']}"
    concentration, concentration_text = _fragrance_concentration(
        formula, data, clean["fragrance_concentration_pct"]
    )
    basis = str(data.get("concentration_basis") or "")
    assumptions = data.get("assumptions")
    basis_text = (
        "Percentages are % w/w of the finished product"
        + (", estimated by the release gate" if basis.endswith("estimate") else "")
        + (f" ({len(assumptions)} density or carrier assumptions)"
           if isinstance(assumptions, list) and assumptions else "")
        + "."
    )
    notes = [
        str(row.get("message"))
        for row in _list_of_dicts(data, "specification_notes")
        if row.get("message")
    ]
    if data.get("constituent_coverage"):
        notes.append(str(data["constituent_coverage"]))
    draft = verdict != "Conforms" or bool(missing)
    title_amendment = amendment if isinstance(amendment, int) else IFRA_AMENDMENT
    return {
        "title": (
            f"IFRA Conformity Certificate — {_ordinal(title_amendment)} Amendment, "
            f"Category {category or IFRA_CATEGORY} (fine fragrance)"
        ),
        "declaration": (
            "Manufacturer's self-declaration. The manufacturer named below declares the "
            "result of its own calculation; this is not a certificate issued by IFRA."
        ),
        "amendment": amendment,
        "category": category or None,
        "product_name": product,
        "lot": lot,
        "date": date,
        "manufacturer": maker,
        "fragrance_concentration_pct": concentration,
        "fragrance_concentration_text": concentration_text,
        "basis_text": basis_text,
        "limits_source": IFRA_TABLE_SOURCE + (
            f" Table verified on {table['verified_on']}." if table.get("verified_on") else ""
        ),
        "gate_status": status or None,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "rows": _table_rows(data),
        "failures": failures,
        "open_items": open_items,
        "notes": notes,
        "missing": missing,
        "draft": draft,
        "draft_banner": STATEMENT_DRAFT_BANNER if draft else None,
        "signature": {
            "name": clean["signatory_name"] or "",
            "lines": ["Signature", "Name", "Position", "Date"],
        },
        "footer": STATEMENT_FOOTER,
    }
