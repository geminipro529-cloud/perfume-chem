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

Each item says whose move it is (``owner``): "you" when only Kenny can answer it, "claude"
when the data or code work is Claude's and nothing is needed from him to mix at the bench
(IFRA certificates matter only before a printed IFRA statement; Rule 6).

Read-only: nothing here changes the inventory, a formula or a gate verdict, and no
strength, smell or liking claim is made.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
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
OWNER_YOU = "you"
OWNER_CLAUDE = "claude"
# A stock only inventory.txt lists joins the gate's stock list through a reviewed
# overlay, which the "Stock data into the engine" thread writes from Kenny's word.
# inventory.txt already states its strength, so nothing is asked of him unless it is wrong.
TEXT_ONLY_ACTION = (
    "Nothing for you to do if your inventory list is right: Claude adds it to the checks' stock "
    'list through the "Stock data into the engine" thread. Tell that thread if the list is wrong.'
)
# The same bottle is on the checks' stock list under another name (an overlay alias, or
# a name with a note in brackets): only the link between the two names is missing.
LINK_ACTION = "Nothing for you to do: Claude links the two names."
# Kenny, 14 Oct: IFRA certificates matter only before a printed IFRA statement on a sold
# label; labelled grades count for bench mixing (AGENTS.md Rule 6).
IFRA_LABEL_ACTION = (
    "Nothing is needed to mix it at the bench. Before a printed IFRA statement, "
    "ask the supplier for its IFRA certificate."
)
IFRA_NAME_ACTION = (
    "Nothing to send: Claude adds it to the IFRA table. Until then this formula's IFRA "
    "result leaves it out."
)
_GOVERNANCE = Path(__file__).resolve().parents[2] / "data" / "governance"
_OVERLAY_GLOB = "inventory_user_authority_overlay_*.json"
_STARTING_CHARGE = "mass_fraction_starting_charge"
_UNMEASURED = "FINAL_DISSOLVED_FRACTION_UNMEASURED"
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


@lru_cache(maxsize=1)
def _overlay_aliases() -> dict[str, str]:
    """Each alias in Kenny's dated overlays, normalised, to its record's canonical name."""

    from engine.name_utils import normalize_name

    aliases: dict[str, str] = {}
    for path in sorted(_GOVERNANCE.glob(_OVERLAY_GLOB)):
        try:
            records = json.loads(path.read_text(encoding="utf-8")).get("records") or []
        except (OSError, ValueError, AttributeError):
            continue
        for record in records if isinstance(records, list) else []:
            canonical = str(record.get("canonical_name") or "") if isinstance(record, dict) else ""
            for alias in (record.get("aliases") or []) if canonical else []:
                key = normalize_name(str(alias))
                if key and key != normalize_name(canonical):
                    aliases[key] = canonical
    return aliases


def _qualified(name: str) -> bool:
    """A name carrying a note in brackets other than its strength ("Vetiver EO (Haiti)")."""

    notes = re.findall(r"\(([^)]*)\)", name)
    return any(not re.fullmatch(r"\s*(neat|[\d.]+\s*%.*)\s*", note, re.IGNORECASE) for note in notes)


def _base_key(name: str) -> str:
    """A name without notes in brackets or a strength: "Rosemary EO (French oil) (neat)" -> "rosemary eo"."""

    from engine.name_utils import normalize_name

    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", name)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*%(?:\s*(?:w/w|v/v|w/v))?(?:\s+in\s+[\w+ ]+)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bneat\b", " ", text, flags=re.IGNORECASE)
    return normalize_name(text)


def _governed_twins(stock: Any, governed: Sequence[Any]) -> list[Any]:
    """The checks' own owned stocks of the same material as a stock only inventory.txt lists.

    The same material is one identity reached by Kenny's overlay alias, by the same
    normalised identity, or by the same name once notes in brackets and strengths are set
    aside when at most one of the two names carries such a note (so "Lavender EO
    (BONTAUX SAS)" never meets "Lavender EO (Bulgaria)"). Two or more identities make the
    match ambiguous, so none is claimed.
    """

    from engine.name_utils import normalize_name

    own = str(stock.identity_name or stock.name)
    own_keys = {normalize_name(own), normalize_name(str(stock.name))}
    alias_target = _overlay_aliases().get(normalize_name(own))
    owned = [g for g in governed if str(g.status).casefold() == "owned"]
    by_alias = [
        g for g in owned
        if alias_target and normalize_name(alias_target) in {
            normalize_name(str(g.identity_name or g.name)), normalize_name(str(g.name)),
        }
    ]
    if by_alias:
        return by_alias
    same = [g for g in owned if normalize_name(str(g.identity_name or g.name)) in own_keys]
    if not same:
        base = _base_key(own)
        same = [
            g for g in owned
            if base and _base_key(str(g.identity_name or g.name)) == base
            and not (_qualified(own) and _qualified(str(g.identity_name or g.name)))
        ]
    identities = {normalize_name(str(g.identity_name or g.name)) for g in same}
    return same if len(identities) == 1 else []


def _carrier_text(carrier: str) -> str:
    """A solvent as written on a label: "ethanol + dep" -> "ethanol + DEP"."""

    return " ".join(
        word.upper() if word.isalpha() and len(word) <= 3 and word.casefold() not in {"in", "and", "or"} else word
        for word in str(carrier or "").split()
    )


def _strength_text(stock: Any) -> str:
    fraction = float(stock.dilution or 0)
    if fraction <= 0:
        return "with no strength written down"
    if abs(fraction - 1.0) < 1e-9:
        return "neat"
    carrier = _carrier_text(str(stock.carrier or "").strip())
    return f"{_percent_text(fraction)}{f' in {carrier}' if carrier else ''}"


def _text_only_item(item: dict[str, Any], target: Any, governed: Sequence[Any]) -> dict[str, Any]:
    """A stock only inventory.txt lists: the same bottle elsewhere, a disagreement, or not yet added."""

    twins = _governed_twins(target, governed)
    if not twins:
        item["reason"] = "It is on your inventory list, but the checks can't find a bottle of it on their stock list."
        item["action"] = TEXT_ONLY_ACTION
        item["owner"] = OWNER_CLAUDE
        return item
    fraction = float(target.dilution or 0)
    same = [t for t in twins if abs(float(t.dilution or 0) - fraction) < 1e-9]
    if same:
        from engine.name_utils import normalize_name

        twin = next((t for t in same if t.execution_ready), same[0])
        item["owner"] = OWNER_CLAUDE
        if normalize_name(str(twin.name)) != normalize_name(str(target.identity_name or target.name)):
            item["reason"] = (
                f'The checks\' stock list has this bottle as "{twin.name}", but the Lab hasn\'t linked '
                "that name to the one on your inventory list."
            )
            item["action"] = LINK_ACTION
            return item
        item["reason"] = (
            f"The checks' stock list has this bottle {_strength_text(twin)}, but your inventory list says "
            f"{_strength_text(target)}, so the Lab keeps the two apart."
        )
        item["action"] = "Nothing for you to do: Claude settles which record is current from your own word and links them."
        return item
    theirs = _sentence_list(sorted({_strength_text(t) for t in twins}))
    item["reason"] = f"Your inventory list says {_strength_text(target)}; the checks' stock list has only {theirs}."
    item["action"] = 'Tell Claude which you have, or both; the "Stock data into the engine" thread records it.'
    item["owner"] = OWNER_YOU
    return item


def _stock_item(
    issue: Mapping[str, Any],
    record: Mapping[str, Any],
    row_stock_ids: Mapping[str, str],
    projection: Any,
    holdable: bool,
    governed: Sequence[Any] = (),
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
    item: dict[str, Any] = {
        "material": material, "check": "stock", "code": reason, "open": None, "owner": OWNER_YOU,
    }

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
            item["owner"] = OWNER_CLAUDE
            return item
        item["reason"] = "It is not in your stock."
        item["action"] = "Buy it, or swap the row for a similar stock you own."
        item["code"] = reason or "not_owned"
        return item

    target = next((s for s in owned if not s.execution_ready), owned[0])
    canonical = target.stock_id in projection.canonical_stock_ids
    if not canonical or str(target.authority) == _TEXT_ONLY_AUTHORITY:
        return _text_only_item(item, target, governed)

    hold = str(target.execution_hold_reason or "")
    holds = [h for h in hold.split("|") if h]
    missing = [f for f in inventory_completion_requirements(target) if f != USER_HOLD]
    if hold == USER_HOLD or USER_HOLD in inventory_completion_requirements(target):
        item["reason"] = "You put this stock on hold, so new formulas leave it out."
        item["action"] = "Clear the hold on the Stock page to use it, or swap the row."
        item["open"] = _open(target)
        return item
    if str(target.fraction_basis or "") == _STARTING_CHARGE or _UNMEASURED in holds:
        # A tincture made from a starting charge of resin: the Stock page takes its
        # strength only from a measurement or a label (inventory_completions.py), so the
        # form cannot settle it; whether the built strength may be used is Kenny's word.
        made = _percent_text(float(target.dilution)) if target.dilution else ""
        item["reason"] = (
            "How much of it actually dissolved was never measured, and the Stock page takes "
            "a tincture's strength only from a measurement or a label."
        )
        item["action"] = (
            f"Tell Claude whether it may be used at the strength it was made at{f' ({made})' if made else ''}; "
            'the "Stock data into the engine" thread records it.'
        )
        return item
    receipt_only = bool(holds) and all(
        "RULE 6" in COMPLETION_HOLD_DISPOSITIONS.get(h, (False, ""))[1] for h in holds
    )
    if receipt_only and completion_clears_execution_hold(target) and set(missing) <= {"possession_confirmation"}:
        item["reason"] = (
            "Your bottle and its strength are on record; the Lab only lacks a lot or receipt, "
            "which mixing doesn't need (Rule 6)."
        )
        item["action"] = "Confirm it once on the Stock page to clear the hold."
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
            action = IFRA_NAME_ACTION
            code = "ifra_name_not_recognised"
        else:
            reason = str(hold.get("message") or "IFRA could not check it.")
            action = IFRA_LABEL_ACTION
            code = "ifra_hold"
        items.append({
            "material": material, "check": "ifra", "code": code, "reason": reason, "action": action,
            "open": None, "owner": OWNER_CLAUDE,
        })
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
            "action": IFRA_LABEL_ACTION,
            "open": None, "owner": OWNER_CLAUDE,
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
            "action": IFRA_LABEL_ACTION,
            "open": None, "owner": OWNER_CLAUDE,
        })
    return items


def explain_holds(rows: Sequence[Mapping[str, Any]], *, bottle_ml: float = 30.0) -> dict[str, Any]:
    """Per material: what holds the formula's stock and IFRA checks, and what to do."""

    from engine.formulation_intelligence import yardstick as ys
    from engine.inventory_parser import materialize_current_inventory
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
    governed = materialize_current_inventory()
    projection = materialize_personal_inventory(canonical=governed)

    check = stock_contract.as_dict()
    items: list[dict[str, Any]] = []
    for issue in stock_contract.data.get("issues", []) or []:
        holdable = ys._issue_holdable(check, issue, record)
        items.append(_stock_item(issue, record, row_stock_ids, projection, holdable, governed.stocks))

    status, _detail, data = ys._gate_call(lambda: g._gate_safety(
        state, config, g._stock_conflict_materials(record), g._unwritten_strength_reasons(record)
    ))
    if status == "HOLD" and not data:
        items.append({
            "material": "", "check": "ifra", "code": "ifra_check_could_not_run",
            "reason": "The IFRA check could not run on this formula.",
            "action": "Send the formula to Claude to find out why.", "open": None, "owner": OWNER_YOU,
        })
    items.extend(_ifra_items(data or {}))
    for number, item in enumerate(items, 1):
        item["id"] = f"hold-{number}"
        item["reason"] = _capitalised(item["reason"])

    yours = sum(1 for item in items if item["owner"] == OWNER_YOU)
    claudes = len(items) - yours
    # The items that need Kenny first; the order is otherwise the checks' own.
    items.sort(key=lambda item: item["owner"] != OWNER_YOU)
    if not items:
        summary = "Nothing is missing: every row can be checked against your stock and IFRA."
    elif not yours:
        summary = (
            f"Nothing here needs you: {claudes} {'item is' if claudes == 1 else 'items are'} Claude's part. "
            "Each says what happens next."
        )
    else:
        summary = f"{yours} {'item needs' if yours == 1 else 'items need'} you"
        if claudes:
            summary += (
                f"; {claudes} {'is' if claudes == 1 else 'are'} Claude's part, with nothing for you to do"
            )
        summary += ". Each says what to do."
    return {
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "summary": summary,
        "basis": BASIS,
        "inventory_modified": False,
        "formula_modified": False,
    }


__all__ = ["BASIS", "SCHEMA_VERSION", "explain_holds"]
