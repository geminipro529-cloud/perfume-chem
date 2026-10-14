"""What stops a formula from being fully checked or mixed, and what Kenny can do about it.

Plan item A4 ("no HOLD without a reason you can act on"). The Lab's HOLD lines come
from two floors the yardstick shares with the release gate: owned stock (Rule 0) and
IFRA. Each says *that* something holds and names the materials; this module says, per
material, *what* is missing and *where* to supply it:

- a stock on inventory.txt that the gate's stock list lacks: the Stock page cannot
  confirm it, so its strength, basis and solvent go to the stock data thread;
- a stock whose details are incomplete or whose hold a Stock page entry clears: open it
  there (AGENTS.md Rule 6: lots and receipts are never needed, a confirmed strength,
  basis and carrier are);
- a stock the user put on hold, or one at another strength, or one not owned at all;
- an IFRA name the Category 4 table does not know, or a natural or supplier base whose
  make-up the Lab lacks, so restricted substances inside it are not counted.

Read-only: nothing here changes the inventory, a formula or a gate verdict, and no
strength, smell or liking claim is made.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = "formula-holds-v1"

BASIS = (
    "From the release gate's stock and IFRA checks on this formula as written. It says what "
    "data is missing, not how the formula smells."
)

# The Stock page's own sentences for a missing detail (static/lab/stock.js).
_FIELD_SENTENCES = {
    "possession_confirmation": "confirm you own it",
    "homogeneity_confirmation": "confirm the solution is fully mixed",
    "fraction_basis": "say whether the strength is w/w or v/v",
    "physical_form": "say what form it is in",
    "carrier": "say which solvent it is in",
    "final_usable_fraction_confirmation": "confirm the strength you actually use",
    "fraction": "type its strength",
}

USER_HOLD = "USER_COMPOUNDING_HOLD"
# A stock only inventory.txt lists joins the gate's stock list through a reviewed
# overlay, which the "Stock data into the engine" thread writes from Kenny's word.
TEXT_ONLY_ACTION = (
    'Tell Claude its strength, basis and solvent in the "Stock data into the engine" thread, '
    "and it goes on the checks' stock list."
)
# Holds a Stock page entry cannot clear, in words (no internal codes on screen).
_HOLD_SENTENCES = {
    "FINAL_DISSOLVED_FRACTION_UNMEASURED": "how much of it actually dissolved was never measured",
    "FILTERED_TINCTURE_FINAL_DISSOLVED_FRACTION_UNKNOWN": "how much the filtered tincture holds is unknown",
    "TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED": "what the tincture's percentage means is not recorded",
    "VISIBLE_CRYSTALS_LIQUID_PHASE_STRENGTH_UNKNOWN": "it has crystals, so the liquid's strength is unknown",
    "LEGACY_TEXT_CURRENT_STOCK_HOLD": "its records disagree",
}
_TEXT_ONLY_AUTHORITY = "LEGACY_INVENTORY_TEXT_DESIGN_ONLY"


def _decimal_text(value: Any, default: str = "") -> str:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return default
    if not number.is_finite() or number < 0:
        return default
    return format(number.normalize(), "f")


def _percent_text(fraction: float | None) -> str:
    if fraction is None:
        return ""
    return f"{fraction * 100:.6g}%"


def _formula(rows: Sequence[Mapping[str, Any]], bottle_ml: float) -> dict[str, Any]:
    """The yardstick's formula dict from Lab rows (amounts in uL for one bottle)."""

    out = []
    for row in rows:
        material = str(row.get("material") or "").strip()
        amount = _decimal_text(row.get("amount_ul"))
        if not material or not amount or Decimal(amount) <= 0:
            continue
        out.append({
            "material": material,
            "amount": amount,
            "unit": "uL",
            "active_fraction": _decimal_text(row.get("fraction"), "1") or "1",
            "fraction_basis": str(row.get("basis") or ""),
            "carrier": str(row.get("carrier") or ""),
            "stock_id": str(row.get("stock_id") or ""),
        })
    return {"name": "Lab formula", "batch_volume_ml": bottle_ml, "rows": out, "parent": None}


def _sentence_list(parts: Sequence[str]) -> str:
    parts = [p for p in parts if p]
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _capitalised(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _stock_lookup(projection: Any) -> tuple[dict[str, Any], dict[str, list[Any]]]:
    by_id = {stock.stock_id: stock for stock in projection.stocks}
    by_name: dict[str, list[Any]] = {}
    for stock in projection.stocks:
        for name in {stock.identity_name or stock.name, stock.name}:
            by_name.setdefault(str(name).casefold(), []).append(stock)
    return by_id, by_name


def _open(stock: Any) -> dict[str, Any]:
    """Where the Stock page form that answers this item opens."""

    return {"kind": "stock_page", "stock_id": stock.stock_id}


def _stock_item(
    issue: Mapping[str, Any],
    record: Mapping[str, Any],
    row_stock_ids: Mapping[str, str],
    projection: Any,
    holdable: bool,
) -> dict[str, Any]:
    from engine.inventory_completions import (
        COMPLETION_HOLD_DISPOSITIONS,
        completion_clears_execution_hold,
        inventory_completion_requirements,
    )

    material = str(issue.get("material") or "")
    reason = str(issue.get("reason") or "")
    fraction = (record.get("dilutions") or {}).get(material)
    by_id, by_name = _stock_lookup(projection)
    stock = by_id.get(str(issue.get("stock_id") or row_stock_ids.get(material) or ""))
    candidates = [stock] if stock else list(by_name.get(material.casefold(), []))
    owned = [s for s in candidates if str(s.status).casefold() == "owned"]
    item: dict[str, Any] = {"material": material, "check": "stock", "code": reason, "open": None}

    at = f" at {_percent_text(fraction)}" if fraction is not None else ""
    if reason == "preparation_required":
        item["reason"] = f"The formula uses it{at}, a dilution you make from a stronger stock you own."
        item["action"] = "Make that dilution first; the bench sheet shows the amounts."
        return item
    if reason == "stock_fraction_mismatch" or issue.get("fraction_matches_formula") is False:
        strengths = [s for s in issue.get("held_stock_strengths") or [] if s is not None]
        yours = _sentence_list([_percent_text(float(s)) for s in strengths]) if strengths else "another strength"
        item["reason"] = f"The formula uses it{at}; your bottle is {yours}."
        item["action"] = "Change the row to your bottle's strength (the editor keeps the dose), or make the dilution."
        return item
    if not owned:
        if holdable:
            item["reason"] = "It is on your inventory list, but the checks could not match it to a bottle."
            item["action"] = TEXT_ONLY_ACTION
            return item
        item["reason"] = "It is not in your stock."
        item["action"] = "Buy it, or swap the row for a similar stock you own."
        item["code"] = reason or "not_owned"
        return item

    target = next((s for s in owned if not s.execution_ready), owned[0])
    canonical = target.stock_id in projection.canonical_stock_ids
    if not canonical or str(target.authority) == _TEXT_ONLY_AUTHORITY:
        item["reason"] = (
            "It is on your inventory list, but not in the stock workbook the checks use, "
            "and the Stock page can't confirm a bottle that isn't there."
        )
        item["action"] = TEXT_ONLY_ACTION
        return item

    hold = str(target.execution_hold_reason or "")
    missing = [f for f in inventory_completion_requirements(target) if f != USER_HOLD]
    if hold == USER_HOLD or USER_HOLD in inventory_completion_requirements(target):
        item["reason"] = "You put this stock on hold, so new formulas leave it out."
        item["action"] = "Clear the hold on the Stock page to use it, or swap the row."
        item["open"] = _open(target)
        return item
    if missing:
        needs = _sentence_list([_FIELD_SENTENCES.get(f, f.replace("_", " ")) for f in missing])
        item["reason"] = f"Its details are not complete: {needs}."
        item["action"] = "Open it on the Stock page and fill those in."
        item["open"] = _open(target)
        return item
    if completion_clears_execution_hold(target):
        why = COMPLETION_HOLD_DISPOSITIONS.get(hold, (True, ""))[1]
        receipt = "RULE 6" in why
        item["reason"] = (
            "Its strength, basis and solvent are not confirmed for mixing yet. No lot or receipt is needed (Rule 6)."
            if receipt else "Its strength, basis and solvent are not confirmed for mixing yet."
        )
        item["action"] = "Open it on the Stock page and confirm them."
        item["open"] = _open(target)
        return item
    why = _HOLD_SENTENCES.get(hold, "its records disagree")
    item["reason"] = f"The Stock page form cannot settle this one: {why}."
    item["action"] = 'Tell Claude what is right in the "Stock data into the engine" thread, or swap the row.'
    return item


def _ifra_items(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hold in data.get("holds", []) or []:
        material = str(hold.get("material") or "")
        if not material or material in seen:
            continue
        seen.add(material)
        if str(hold.get("verdict")) == "unchecked" and not hold.get("matched_name"):
            reason = "IFRA's Category 4 table does not know it by this name, so no limit was checked."
            action = "Send Claude its CAS number from the label or safety sheet, so it can be matched."
            code = "ifra_name_not_recognised"
        else:
            reason = str(hold.get("message") or "IFRA could not check it.")
            action = "Ask the supplier for its IFRA certificate and send it to Claude."
            code = "ifra_hold"
        items.append({"material": material, "check": "ifra", "code": code, "reason": reason, "action": action, "open": None})
    counted = {
        c.get("material")
        for t in data.get("constituent_totals", []) or []
        for c in t.get("contributors", []) or []
        if c.get("kind") == "natural"
    }
    for base in data.get("undisclosed_bases", []) or []:
        material = str(base.get("material") or "")
        if not material or material in seen:
            continue
        seen.add(material)
        items.append({
            "material": material, "check": "ifra", "code": "ifra_base_composition_unpublished",
            "reason": "It is a supplier base whose make-up is not published, so restricted substances inside it are not counted.",
            "action": "Ask the supplier for its IFRA certificate and send it to Claude.",
            "open": None,
        })
    for warning in data.get("warnings", []) or []:
        material = str(warning.get("material") or "")
        if (
            warning.get("ifra_status") != "natural_no_own_standard"
            or not material
            or material in seen
            or material in counted
            or warning.get("ifra_name") in counted
        ):
            continue
        seen.add(material)
        items.append({
            "material": material, "check": "ifra", "code": "ifra_natural_composition_unknown",
            "reason": "The Lab has no make-up for this natural, so IFRA-restricted substances inside it are not counted.",
            "action": "Ask the supplier for its IFRA certificate and send it to Claude.",
            "open": None,
        })
    return items


def explain_holds(rows: Sequence[Mapping[str, Any]], *, bottle_ml: float = 30.0) -> dict[str, Any]:
    """Per material: what holds the formula's stock and IFRA checks, and what to do."""

    from engine.formulation_intelligence import yardstick as ys
    from engine.personal_inventory import materialize_personal_inventory
    from engine.pipeline import gates as g

    formula = _formula(rows, bottle_ml)
    if not formula["rows"]:
        return {
            "schema_version": SCHEMA_VERSION,
            "items": [],
            "summary": "Add rows with amounts to check them.",
            "basis": BASIS,
            "inventory_modified": False,
            "formula_modified": False,
        }
    row_stock_ids = {row["material"]: row["stock_id"] for row in formula["rows"] if row["stock_id"]}
    record = ys._gate_record(formula)
    config = g._resolve_gate_config(record, g.ReleaseGateConfig(batch_volume_ml=bottle_ml))
    state, stock_contract, _ = g._gate_formula_state(record, config)
    projection = materialize_personal_inventory()

    check = stock_contract.as_dict()
    items: list[dict[str, Any]] = []
    for issue in stock_contract.data.get("issues", []) or []:
        holdable = ys._issue_holdable(check, issue, record)
        items.append(_stock_item(issue, record, row_stock_ids, projection, holdable))

    status, _detail, data = ys._gate_call(lambda: g._gate_safety(
        state, config, g._stock_conflict_materials(record), g._unwritten_strength_reasons(record)
    ))
    if status == "HOLD" and not data:
        items.append({
            "material": "", "check": "ifra", "code": "ifra_check_could_not_run",
            "reason": "The IFRA check could not run on this formula.",
            "action": "Send the formula to Claude to find out why.", "open": None,
        })
    items.extend(_ifra_items(data or {}))
    for number, item in enumerate(items, 1):
        item["id"] = f"hold-{number}"
        item["reason"] = _capitalised(item["reason"])

    stock_count = sum(1 for item in items if item["check"] == "stock")
    ifra_count = len(items) - stock_count
    if not items:
        summary = "Nothing is missing: every row can be checked against your stock and IFRA."
    else:
        parts = []
        if stock_count:
            parts.append(f"{stock_count} stock{'s' if stock_count != 1 else ''} to sort out on the Stock page or the bench")
        if ifra_count:
            parts.append(f"{ifra_count} material{'s' if ifra_count != 1 else ''} IFRA cannot fully check yet")
        summary = _capitalised(_sentence_list(parts)) + ". Each says what to do."
    return {
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "summary": summary,
        "basis": BASIS,
        "inventory_modified": False,
        "formula_modified": False,
    }


__all__ = ["BASIS", "SCHEMA_VERSION", "explain_holds"]
