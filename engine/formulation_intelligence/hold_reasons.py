"""What stops a formula from being fully checked or mixed, and what Kenny can do about it.

Plan item A4 ("no HOLD without a reason you can act on"). The Lab's HOLD lines come
from two floors the yardstick shares with the release gate: owned stock (Rule 0) and
IFRA. Each says *that* something holds and names the materials; this module says, per
material, *what* is missing and *where* to supply it:

- a stock only inventory.txt lists: the same bottle under another name on the gate's
  stock list (Claude links them, or says what holds that record), a disagreement about
  its strength or solvent (asked, unless Kenny's own word is on record), a name match
  that would be a guess (asked), or a bottle not yet on the gate's list (Claude adds it);
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

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from engine import stock_matching

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
    "fraction_percent": "write down its strength",
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
    "Nothing is needed to mix it at the bench; its IFRA certificate matters only before a "
    "printed IFRA statement on a label you sell."
)
IFRA_NAME_ACTION = (
    "Nothing to send: Claude adds it to the IFRA table. Until then this formula's IFRA "
    "result leaves it out."
)
# A restricted material whose Category 4 limit the Lab's IFRA table lacks: table data.
IFRA_LIMIT_ACTION = "Nothing for you to do: Claude records its Category 4 limit from the IFRA standard."
IFRA_OTHER_ACTION = "Nothing for you to do: Claude finds out why the IFRA check holds it."
# The same name and strength, but the two lists give another solvent or basis. A record
# from one of Kenny's dated overlays quotes his own word (e.g. 14 Oct: his EO, absolute and
# damascone-type dilutions are in DPG), so Claude corrects inventory.txt to it; any other
# record (the stock workbook) is his to settle (Rule 0: report, don't guess).
_USER_WORD_AUTHORITY = stock_matching.USER_WORD_AUTHORITY
FORM_ACTION = "Nothing for you to do unless you have both: Claude corrects your inventory list to match what you said."
FORM_ASK_ACTION = (
    'Tell Claude which is right, or whether you have both; the "Stock data into the engine" thread records it.'
)
# A record the Stock page doesn't list (inventory.txt's line for the same bottle shows there
# instead): Claude completes it from that line in the stock data thread.
OFF_PAGE_ACTION = (
    "Nothing for you to do unless Claude asks: Claude completes that record from your inventory "
    'list in the "Stock data into the engine" thread.'
)
SAME_BOTTLE_ACTION = 'Tell Claude whether it is the same bottle; the "Stock data into the engine" thread records it.'
SAME_MATERIAL_ACTION = (
    'Tell Claude whether it is the same material, and which strengths you have; the "Stock data '
    'into the engine" thread records it.'
)
STRENGTH_ACTION = 'Tell Claude which you have, or both; the "Stock data into the engine" thread records it.'
_GOVERNANCE = stock_matching.GOVERNANCE_DIR
_STARTING_CHARGE = "mass_fraction_starting_charge"
_UNMEASURED = "FINAL_DISSOLVED_FRACTION_UNMEASURED"
# Holds a Stock page entry cannot clear, in words (no internal codes on screen).
_UNRESOLVED_SENTENCES = {
    "IDENTITY KEPT SEPARATE": "its record is kept apart from a similar material until it is known which one it is",
    "SPECIES UNRESOLVED": "its species is not known",
}
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


def _overlay_aliases() -> dict[str, str]:
    """Each alias in Kenny's dated overlays, normalised, to its record's canonical name."""

    return stock_matching.overlay_aliases(_GOVERNANCE)


_qualified = stock_matching.qualified
_base_key = stock_matching.base_key


def _governed_twins(stock: Any, governed: Sequence[Any]) -> list[Any]:
    """The checks' own owned stocks of the same material as a stock only inventory.txt lists."""

    return _twin_match(stock, governed)[0]


def _twin_match(stock: Any, governed: Sequence[Any]) -> tuple[list[Any], str]:
    """The checks' owned stocks of the same material, and how sure the match is (see stock_matching)."""

    return stock_matching.twin_match(stock, governed, _overlay_aliases())


_carrier_text = stock_matching.carrier_text
_carrier_key = stock_matching.carrier_key
_BASIS_KEYS = stock_matching.BASIS_KEYS
_BASIS_WORDS = {"mass": "by weight", "volume": "by volume", "mass_per_volume": "weight per volume"}


_same_form = stock_matching.same_form


def _form_texts(one: Any, other: Any) -> tuple[str, str]:
    """Each record's strength, with its basis when only the basis tells them apart."""

    texts = [_strength_text(one), _strength_text(other)]
    bases = [_BASIS_KEYS.get(str(s.fraction_basis or "")) for s in (one, other)]
    if texts[0] == texts[1] and None not in bases and bases[0] != bases[1]:
        texts = [f"{text} {_BASIS_WORDS[basis]}" for text, basis in zip(texts, bases)]
    return texts[0], texts[1]


def _named(stock: Any) -> str:
    """A stock by its name on the checks' list, with its strength unless the name says it."""

    strength = _strength_text(stock)
    first = strength.split(" in ")[0]
    if first.casefold() in str(stock.name).casefold():
        return f'"{stock.name}"'
    return f'"{stock.name}" ({strength})'


def _strength_text(stock: Any) -> str:
    fraction = float(stock.dilution or 0)
    if fraction <= 0:
        return "no strength"
    if abs(fraction - 1.0) < 1e-9:
        return "neat"
    carrier = _carrier_text(str(stock.carrier or "").strip())
    return f"{_percent_text(fraction)}{f' in {carrier}' if carrier else ''}"


def _inventory_text_strengths() -> dict[str, set[float]]:
    """The strengths inventory.txt lists per material, every line kept."""

    from engine.inventory_parser import parse_inventory

    strengths: dict[str, set[float]] = {}
    try:
        lines = parse_inventory(unique=False)
    except (OSError, ValueError):
        return strengths
    for line in lines:
        if str(line.status).casefold() == "owned" and line.dilution:
            for key in _material_keys(line):
                strengths.setdefault(key, set()).add(float(line.dilution))
    return strengths


def _material_keys(stock: Any) -> set[str]:
    """The keys one material is found by: its identity and name, and its plain name when no origin is noted."""

    from engine.name_utils import normalize_name

    identity = str(stock.identity_name or stock.name)
    keys = {normalize_name(identity), normalize_name(str(stock.name))}
    if not _qualified(identity):
        keys.add(_base_key(identity))
    keys.discard("")
    return keys


def _siblings(twins: Sequence[Any], governed: Sequence[Any]) -> list[Any]:
    """The checks' other owned records of a matched material under a plainer name.

    One material can carry two identities on the gate's list ("Aldehyde C11 neat" and
    "Aldehyde C11 1%"); a record whose name, without strength notes, is the same as a
    matched record's is the same material too, unless either name carries an origin.
    """

    keys = {_base_key(str(t.name)) for t in twins} | {_base_key(str(t.identity_name or t.name)) for t in twins}
    keys.discard("")
    ids = {t.stock_id for t in twins}
    return [
        g for g in governed
        if str(g.status).casefold() == "owned" and g.stock_id not in ids
        and not _qualified(str(g.identity_name or g.name)) and not _qualified(str(g.name))
        and (_base_key(str(g.name)) in keys or _base_key(str(g.identity_name or g.name)) in keys)
    ]


def _text_only_item(
    item: dict[str, Any],
    target: Any,
    governed: Sequence[Any],
    listed_ids: set[str] | None = None,
    text_strengths: Mapping[str, set[float]] | None = None,
) -> dict[str, Any]:
    """A stock only inventory.txt lists: the same bottle elsewhere, a disagreement, or not yet added.

    ``listed_ids`` are the stocks the Stock page shows (None: all); ``text_strengths`` the
    strengths inventory.txt lists per material (None: not checked).
    """


    twins, kind = _twin_match(target, governed)
    if not twins:
        item["reason"] = "It is on your inventory list, but the checks can't find a bottle of it on their stock list."
        item["action"] = TEXT_ONLY_ACTION
        item["owner"] = OWNER_CLAUDE
        return item
    fraction = float(target.dilution or 0)

    def strength(stock: Any) -> bool:
        return fraction > 0 and abs(float(stock.dilution or 0) - fraction) < 1e-9

    if kind == "probable":
        # One name carries an origin, grade or species the other lacks: only Kenny knows (Rule 0).
        one_strength = any(strength(t) for t in twins)
        item["reason"] = (
            f"The checks' stock list has {_sentence_list(sorted(_named(t) for t in twins))}, which may be "
            f"{'this bottle' if one_strength else 'the same material as this one'} ({_strength_text(target)}); "
            "the Lab doesn't link them on a guess."
        )
        item["action"] = SAME_BOTTLE_ACTION if one_strength else SAME_MATERIAL_ACTION
        item["owner"] = OWNER_YOU
        return item
    if not any(strength(t) for t in twins):
        siblings = _siblings(twins, governed)
        close = [t for t in siblings if strength(t)]
        if close:
            # Found only under a plainer name ("Aldehyde C11 1%" for "Aldehyde C11
            # undecylenic"): a plainer name may be another material, so ask.
            item["reason"] = (
                f"The checks' stock list has {_sentence_list(sorted(_named(t) for t in close))}, which may be "
                f"this bottle ({_strength_text(target)}); the Lab doesn't link them on a guess."
            )
            item["action"] = SAME_BOTTLE_ACTION
            item["owner"] = OWNER_YOU
            return item
        twins = [*twins, *siblings]
    same = [t for t in twins if strength(t)]
    one_bottle = [t for t in same if _same_form(t, target)]
    if one_bottle:
        twin = next((t for t in one_bottle if t.execution_ready), one_bottle[0])
        named = f'The checks\' stock list has this bottle as "{twin.name}"'
        if not twin.execution_ready:
            # The link alone would not let it be mixed: say what holds that record.
            _canonical_hold(item, twin, on_stock_page=listed_ids is None or twin.stock_id in listed_ids)
            item["reason"] = f"{named}. {_capitalised(item['reason'])}"
            return item
        item["owner"] = OWNER_CLAUDE
        item["reason"] = f"{named}, but the Lab hasn't linked that name to the one on your inventory list."
        item["action"] = LINK_ACTION
        return item
    if same:
        # One name and strength, another solvent or basis: one bottle whose records disagree.
        twin = next((t for t in same if t.execution_ready), same[0])
        theirs, yours = _form_texts(twin, target)
        if str(getattr(twin, "authority", "") or "").startswith(_USER_WORD_AUTHORITY):
            item["owner"] = OWNER_CLAUDE
            item["reason"] = (
                f'The checks\' stock list has "{twin.name}" at {theirs}, from what you told Claude; '
                f"your inventory list says {yours}."
            )
            item["action"] = FORM_ACTION
            return item
        item["owner"] = OWNER_YOU
        item["reason"] = (
            f'The checks\' stock list has "{twin.name}" at {theirs}, but your inventory list says '
            f"{yours}, so the Lab keeps the two apart."
        )
        item["action"] = FORM_ASK_ACTION
        return item
    listed = {s for key in _material_keys(target) for s in (text_strengths or {}).get(key, set())}
    if fraction > 0 and any(abs(float(t.dilution or 0) - s) < 1e-9 for t in twins for s in listed):
        # inventory.txt lists the checks' strength as well: this is another bottle of it,
        # not a disagreement, and it just isn't on the checks' list yet.
        item["reason"] = (
            f"Your inventory list has it at {_strength_text(target)} as well as "
            f"{_sentence_list(sorted(_named(t) for t in twins))}; the checks' stock list has only the other, "
            "so this bottle isn't on it yet."
        )
        item["action"] = TEXT_ONLY_ACTION
        item["owner"] = OWNER_CLAUDE
        return item
    # Another strength may be another bottle (a dilution made from it): only Kenny knows.
    theirs = _sentence_list(sorted(_named(t) for t in twins))
    yours = f"says {_strength_text(target)}" if fraction > 0 else "gives no strength"
    item["reason"] = f"Your inventory list {yours}; the checks' stock list has {theirs}."
    item["action"] = STRENGTH_ACTION
    item["owner"] = OWNER_YOU
    return item


def _stock_item(
    issue: Mapping[str, Any],
    record: Mapping[str, Any],
    row_stock_ids: Mapping[str, str],
    projection: Any,
    holdable: bool,
    governed: Sequence[Any] = (),
    text_strengths: Mapping[str, set[float]] | None = None,
) -> dict[str, Any]:
    material = str(issue.get("material") or "")
    reason = str(issue.get("reason") or "")
    fraction = (record.get("dilutions") or {}).get(material)
    by_id, by_name = _stock_lookup(projection)
    wanted = str(issue.get("stock_id") or row_stock_ids.get(material) or "")
    # A row saved against an inventory.txt line now shown as the checks' own record.
    wanted = dict(getattr(projection, "merged_text_stock_ids", ()) or ()).get(wanted, wanted)
    stock = by_id.get(wanted)
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
        listed_ids = {s.stock_id for s in projection.stocks}
        return _text_only_item(item, target, governed, listed_ids, text_strengths)

    return _canonical_hold(item, target)


def _canonical_hold(item: dict[str, Any], target: Any, *, on_stock_page: bool = True) -> dict[str, Any]:
    """What holds a stock on the checks' own list, and who answers it.

    ``on_stock_page`` is False for a record the Stock page doesn't list (inventory.txt's
    line for the same bottle shows there instead), so nothing sends Kenny to its form.
    """

    from engine.inventory_completions import (
        COMPLETION_HOLD_DISPOSITIONS,
        completion_clears_execution_hold,
        inventory_completion_requirements,
    )

    item["owner"] = OWNER_YOU
    item["open"] = _open(target) if on_stock_page else None
    hold = str(target.execution_hold_reason or "")
    holds = [h for h in hold.split("|") if h]
    missing = [f for f in inventory_completion_requirements(target) if f != USER_HOLD]
    if hold == USER_HOLD or USER_HOLD in inventory_completion_requirements(target):
        item["reason"] = "You put this stock on hold, so new formulas leave it out."
        item["action"] = (
            "Clear the hold on the Stock page to use it, or swap the row." if on_stock_page
            else 'Tell Claude to clear the hold in the "Stock data into the engine" thread, or swap the row.'
        )
        return item
    if str(target.fraction_basis or "") == _STARTING_CHARGE or _UNMEASURED in holds:
        # A tincture made from a starting charge of resin. The Stock page won't take the
        # recipe as its final strength (inventory_completions.py), but it takes Kenny's own
        # confirmation that the strength it was made at is the one to use.
        made = _percent_text(float(target.dilution)) if target.dilution else ""
        at = f" ({made})" if made else ""
        item["reason"] = (
            "How much of the resin actually dissolved was never measured, so its real strength may be "
            f"below the strength it was made at{at}."
        )
        item["action"] = (
            f"If you're happy to use it at the strength it was made at{at}, confirm that on the Stock page "
            "as your own confirmation and tick that it is the final usable concentration; or swap the row."
            if on_stock_page else
            f"Tell Claude whether it may be used at the strength it was made at{at}; "
            'the "Stock data into the engine" thread records it.'
        )
        return item
    unresolved = str(getattr(target, "row_unresolved_tokens", "") or "")
    if unresolved and not completion_clears_execution_hold(target):
        # The stock workbook row itself is unresolved: no Stock page entry clears it.
        why = _sentence_list([
            _UNRESOLVED_SENTENCES.get(token.strip(), token.strip().casefold())
            for token in unresolved.split("|") if token.strip()
        ])
        item["open"] = None
        item["reason"] = f"The Stock page form cannot settle this one: {why}."
        item["action"] = 'Tell Claude what is right in the "Stock data into the engine" thread, or swap the row.'
        return item
    if not on_stock_page:
        needs = _sentence_list([_FIELD_SENTENCES.get(f, f.replace("_", " ")) for f in missing]) if missing else ""
        item["owner"] = OWNER_CLAUDE
        item["reason"] = (
            f"That record's details are not complete: {needs}." if needs
            else "That record's strength, basis and solvent are not confirmed for mixing yet."
        )
        item["action"] = OFF_PAGE_ACTION
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
        return item
    if missing:
        needs = _sentence_list([_FIELD_SENTENCES.get(f, f.replace("_", " ")) for f in missing])
        item["reason"] = f"Its details are not complete: {needs}."
        item["action"] = "Open it on the Stock page and fill those in."
        return item
    if completion_clears_execution_hold(target):
        why = COMPLETION_HOLD_DISPOSITIONS.get(hold, (True, ""))[1]
        receipt = "RULE 6" in why
        item["reason"] = (
            "Its strength, basis and solvent are not confirmed for mixing yet. No lot or receipt is needed (Rule 6)."
            if receipt else "Its strength, basis and solvent are not confirmed for mixing yet."
        )
        item["action"] = "Open it on the Stock page and confirm them."
        return item
    why = _HOLD_SENTENCES.get(hold, "its records disagree")
    item["open"] = None
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
        elif hold.get("ifra_status") == "restricted_unverified":
            standard = str(hold.get("standard") or "")
            reason = (
                f"IFRA restricts it{f' ({standard})' if standard else ''}, but the Lab's IFRA table has no "
                "Category 4 limit for it yet, so its dose was not checked."
            )
            action = IFRA_LIMIT_ACTION
            code = "ifra_limit_not_recorded"
        else:
            reason = str(hold.get("message") or "IFRA could not check it.")
            action = IFRA_OTHER_ACTION
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


def _summary(items: Sequence[Mapping[str, Any]]) -> str:
    """How many items need Kenny and how many are Claude's part."""

    yours = sum(1 for item in items if item.get("owner") == OWNER_YOU)
    claudes = len(items) - yours
    if not items:
        return "Nothing is missing: every row can be checked against your stock and IFRA."
    if not yours:
        return (
            f"Nothing here needs you: {claudes} {'item is' if claudes == 1 else 'items are'} Claude's part. "
            "Each says what happens next."
        )
    summary = f"{yours} {'item needs' if yours == 1 else 'items need'} you"
    if claudes:
        summary += f"; {claudes} {'is' if claudes == 1 else 'are'} Claude's part, with nothing for you to do"
    return summary + ". Each says what to do."


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
    text_strengths = _inventory_text_strengths()
    items: list[dict[str, Any]] = []
    for issue in stock_contract.data.get("issues", []) or []:
        holdable = ys._issue_holdable(check, issue, record)
        items.append(_stock_item(issue, record, row_stock_ids, projection, holdable, governed.stocks, text_strengths))

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
    # The items that need Kenny first; the order is otherwise the checks' own.
    items.sort(key=lambda item: item["owner"] != OWNER_YOU)
    for number, item in enumerate(items, 1):
        item["id"] = f"hold-{number}"
        item["reason"] = _capitalised(item["reason"])
    return {
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "summary": _summary(items),
        "basis": BASIS,
        "inventory_modified": False,
        "formula_modified": False,
    }


__all__ = ["BASIS", "SCHEMA_VERSION", "explain_holds"]
