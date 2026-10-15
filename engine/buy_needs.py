"""What Kenny's saved formula cards call for that he doesn't own: the buy list's needs.

Owned status comes only from What's missing (``explain_holds``), which reads the stock
authority (AGENTS.md Rule 0). Each card's rows go to it the way the formula editor sends
them (``editorHoldRows`` in backend/app/static/formula-editor.js). A material neither
stock list has is a need; one only inventory.txt has, or that the two lists match only on
a guess, is a disagreement, named with both lists' words and counted as neither owned nor
not owned. Anything else (owned at another strength, a dilution to make, details or IFRA
data missing) is not a need.

Read-only: no stock, card or gate verdict changes, and no smell or liking claim is made.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

from engine.formulation_intelligence.hold_reasons import (
    STOCK_LISTS_DISAGREE,
    STOCK_NOT_OWNED,
    STOCK_OWNED,
    explain_holds,
)

# formula-editor.js EDITOR_ETHANOL_NAMES: the bottle's top-up, not a stock.
_ETHANOL_NAMES = frozenset({"ethanol", "perfumer's alcohol", "perfumers alcohol", "alcohol"})
_DEFAULT_BOTTLE_ML = 30.0
# bench-sheet.js BENCH_DECIMAL, and editorNumber's thousands separators and spaces.
_DECIMAL = re.compile(r"^\d+(\.\d+)?$")
_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
_SPACES = re.compile("[   ]")


def material_key(name: str, *, registry: Any | None = None) -> str:
    """One key per material: its registry canonical name, else its name with spacing and case evened."""

    if registry is None:
        from engine.data_spine.loader import load_registry

        registry = load_registry()
    material = registry.get(name)
    if material is not None:
        return str(material.canonical_name).casefold()
    return " ".join(name.casefold().split())


def _editor_number(text: Any) -> Fraction | None:
    """editorNumber: "1200", "1,200", "1 200", ".5" or "0.5" as an exact fraction; None otherwise."""

    raw = _SPACES.sub("", str(text if text is not None else "").strip())
    plain = raw.replace(",", "") if _THOUSANDS.match(raw) else raw
    plain = f"0{plain}" if re.fullmatch(r"\.\d+", plain) else plain
    return Fraction(plain) if _DECIMAL.match(plain) else None


def _amount(text: Any) -> Fraction | None:
    """A saved amount ("600" or "1000/3"), exact; None when blank."""

    raw = str(text if text is not None else "").strip()
    return Fraction(raw) if raw else None


def _decimal_text(value: Fraction) -> str:
    """bench-sheet.js benchFractionText(value, 6): half up to six places, no trailing zeros."""

    scaled = (2 * value.numerator * 10**6 + value.denominator) // (2 * value.denominator)
    text = format(Decimal(scaled).scaleb(-6), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _exact(value: Fraction) -> Decimal:
    with localcontext() as context:
        context.prec = 28
        return Decimal(value.numerator) / Decimal(value.denominator)


def _card_rows(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The card's stock rows (editorHoldRows): named, with an amount, not ethanol; strength in (0, 1] or neat."""

    rows = []
    for row in card.get("rows") or []:
        material = str(row.get("material") or "")
        amount = _amount(row.get("amount"))
        if not material or not amount or material.strip().lower() in _ETHANOL_NAMES:
            continue
        fraction = _editor_number(row.get("fraction"))
        strength = fraction if fraction is not None and 0 < fraction <= 1 else Fraction(1)
        rows.append({"material": material, "row": row, "amount": amount, "strength": strength})
    return rows


def _card_states(
    card: Mapping[str, Any], registry: Any, holds: Callable[..., dict]
) -> tuple[list[dict[str, Any]], dict[str, Fraction | None]]:
    """The card's stock items with a material key, and each key's neat fraction of the concentrate."""

    rows = _card_rows(card)
    bottle = str(card.get("bottle_ml") or "").strip()
    bottle_ml = float(bottle) if bottle else _DEFAULT_BOTTLE_ML
    hold_rows = [
        {
            "material": r["material"],
            "stock_id": r["row"].get("stock_id") or "",
            "amount_ul": _decimal_text(r["amount"]),
            "fraction": _decimal_text(r["strength"]),
            "basis": str(r["row"].get("basis") or "").strip(),
            "carrier": r["row"].get("carrier") or "",
        }
        for r in rows
    ]
    answer = holds(hold_rows, bottle_ml=bottle_ml)
    concentrate = sum((r["amount"] for r in rows), Fraction(0))
    active: dict[str, Fraction] = {}
    texts: dict[str, str] = {}
    for r in rows:
        key = material_key(r["material"], registry=registry)
        active[key] = active.get(key, Fraction(0)) + r["amount"] * r["strength"]
        texts.setdefault(key, r["material"])
    fractions = {key: (amount / concentrate if concentrate else None) for key, amount in active.items()}
    items = []
    for item in answer.get("items") or []:
        if item.get("check") != "stock":
            continue
        key = material_key(str(item.get("material") or ""), registry=registry)
        items.append({**item, "material_key": key, "row_text": texts.get(key, str(item.get("material") or ""))})
    return items, fractions


def card_needs(
    cards: Sequence[Mapping[str, Any]],
    *,
    registry: Any | None = None,
    holds: Callable[..., dict] = explain_holds,
) -> dict[str, Any]:
    """One entry per material the cards call for that Kenny doesn't own, with the cards that call for it.

    ``cards`` are ``GET /v2/workbench/make-now``'s formulas. A material either stock list
    disagrees on in any card goes to ``disagreements``; one that is owned in any card is
    not a need; a card whose check can't run goes to ``unreadable``.
    """

    if registry is None:
        from engine.data_spine.loader import load_registry

        registry = load_registry()
    entries: dict[str, dict[str, Any]] = {}
    owned: set[str] = set()
    unreadable: list[dict[str, Any]] = []
    for card in cards:
        try:
            items, fractions = _card_states(card, registry, holds)
        except Exception as error:  # one card's failure must not hide the others' needs
            unreadable.append({"formula_id": card.get("formula_id"), "name": card.get("name"), "error": str(error)})
            continue
        seen: set[str] = set()
        for item in items:
            key = item["material_key"]
            state = item.get("stock_state")
            if state == STOCK_OWNED:
                owned.add(key)
                continue
            if state not in {STOCK_NOT_OWNED, STOCK_LISTS_DISAGREE}:
                continue
            entry = entries.setdefault(key, {"material_key": key, "material": item["row_text"], "cards": []})
            if state == STOCK_LISTS_DISAGREE and "code" not in entry:
                entry["code"] = str(item.get("code") or "")
                entry["reason"] = str(item.get("reason") or "")
            if key not in seen:
                seen.add(key)
                entry["cards"].append({
                    "formula_id": card.get("formula_id"),
                    "version": card.get("version"),
                    "name": card.get("name"),
                    "neat_fraction": _exact(fractions[key]) if fractions.get(key) is not None else None,
                })
    needs, disagreements = [], []
    for key, entry in entries.items():
        entry["cards"].sort(key=lambda c: str(c["name"] or ""))
        if "code" in entry:
            disagreements.append(entry)
        elif key not in owned:
            needs.append(entry)
    return {
        "needs": sorted(needs, key=_by_count_then_name),
        "disagreements": sorted(disagreements, key=_by_count_then_name),
        "unreadable": unreadable,
    }


def _by_count_then_name(entry: Mapping[str, Any]) -> tuple[int, str, str]:
    return -len(entry["cards"]), str(entry["material"]).casefold(), str(entry["material_key"])


__all__ = ["card_needs", "material_key"]
