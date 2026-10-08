"""Read-only single-change comparison plans: control versus one addition or dose step.

One plan changes exactly one row of a fixed control. Every other row keeps its
amount; total amount differs by the step. Nothing is saved, reserved, added or
committed, and no sensory equivalence, blinding or safety approval is implied.
"""

from __future__ import annotations

import copy
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from math import comb
from typing import Any, Mapping, Sequence

from engine.research.contracts import FALSE_ACTION_AUTHORITY

SPLIT_VIAL_UL = 3000
MIN_SPLIT_STEP_UL = 100
BLOTTER_TIMES_MIN = (0, 15, 60)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _plain(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _whole(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def stock_label(row: Mapping[str, Any]) -> str:
    """Name the stock being dosed with its dilution, e.g. ``Ambrox (10% w/w in DPG)``."""
    fraction = Decimal(row["stock_fraction_decimal"])
    if fraction == 1 or row["fraction_basis"] == "neat":
        return f"{row['identity_name']} (neat)"
    basis = "" if row["fraction_basis"] == "unknown" else f" {row['fraction_basis']}"
    carrier = f" in {row['carrier']}" if row.get("carrier") else ""
    return f"{row['identity_name']} ({_plain(fraction * 100)}%{basis}{carrier})"


def triangle_min_correct(tries: int, alpha: Fraction = Fraction(1, 20)) -> int | None:
    """Smallest correct count significant at ``alpha`` (exact one-sided binomial, p = 1/3)."""
    p = Fraction(1, 3)
    tail = Fraction(0)
    for k in range(tries, -1, -1):
        tail += comb(tries, k) * p**k * (1 - p) ** (tries - k)
        if tail > alpha:
            return k + 1 if k < tries else None
    return 0


def triangle_test_sheet(tries: int = 6) -> dict[str, Any]:
    needed = triangle_min_correct(tries)
    if needed is None:
        raise ValueError("too few triangle tries to show a difference at the 5% level")
    return {
        "tries": tries, "min_correct": needed, "chance_per_try": "1/3", "significance_level": "0.05",
        "method": "Exact one-sided binomial test, chance of a lucky guess 1 in 3 per try.",
        "steps": [
            "Label three blotters on the back: two dipped in the control and one dipped in the variant.",
            "Shuffle them so you cannot see the labels, smell all three and pick the odd one out.",
            f"Turn it over to check, then repeat with fresh blotters until you have done {tries} tries.",
        ],
        "reading": (f"{needed} or more right out of {tries} means you can really tell them apart. "
                    "Fewer means this test couldn't show a difference, so keep the control."),
        "blinding_note": ("Planning only: you shuffle the blotters yourself. The program does not "
                          "blind this test or record the answers."),
    }


def _blotter_preview(label: str) -> dict[str, Any]:
    return {
        "steps": [
            "Dip two blotters in the perfume.",
            f"Touch one of them with the tip of a third blotter dipped briefly in {label}.",
            "Smell the pair side by side at 0, 15 and 60 minutes.",
        ],
        "times_min": list(BLOTTER_TIMES_MIN),
        "note": "This shows only the direction of the change, not the amount.",
    }


def _split_vial(label: str, step: Decimal, bottle_ul: Decimal) -> dict[str, Any]:
    split = _whole(step * SPLIT_VIAL_UL / bottle_ul)
    main = _whole(step) - split
    return {
        "bottle_volume_ul": _plain(bottle_ul), "vial_ul": SPLIT_VIAL_UL,
        "full_bottle_step_ul": _whole(step), "split_ul": split, "main_bottle_ul": main,
        "remaining_main_bottle_ul": _plain(bottle_ul - SPLIT_VIAL_UL), "stock": label,
        "steps": [
            f"Pull {SPLIT_VIAL_UL:,} µL of the perfume from the main bottle into a small clean vial.",
            f"Add {split} µL of {label} to the vial.",
            "Dip one blotter in the vial and one in the main bottle; smell them side by side at 0, 15 and 60 minutes.",
            f"If you like the vial better, add {main} µL of {label} to the main bottle, then pour the vial back in.",
            "If you don't, keep the vial apart and leave the main bottle as it is.",
        ],
        "times_min": list(BLOTTER_TIMES_MIN),
    }


def _why_no_split(unit: str, step: Decimal, bottle_ul: Decimal | None) -> str | None:
    if unit != "uL":
        return "The split recipe is worked out in µL and this step is in mg, so try the blotter preview instead."
    if bottle_ul is None:
        return "No bottle volume was given, so there is no split recipe; try the blotter preview instead."
    if bottle_ul <= SPLIT_VIAL_UL:
        return "The bottle holds 3,000 µL or less, so there is nothing to split off; try the blotter preview instead."
    if step < MIN_SPLIT_STEP_UL:
        return (f"The step is {_plain(step)} µL, under the 100 µL needed for an accurate one-tenth split, "
                "so try the blotter preview instead.")
    return None


def plan_one_change(*, control_rows: Sequence[Mapping[str, Any]], change: Mapping[str, Any]) -> dict[str, Any]:
    """Apply exactly one ADDITION or DOSE_STEP to a fixed control (pure, deterministic)."""
    rows = [copy.deepcopy(dict(row)) for row in control_rows]
    ids = [row["stock_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("control rows must be distinct")
    kind = change["kind"]
    if kind == "ADDITION":
        added = copy.deepcopy(dict(change["row"]))
        if added["stock_id"] in ids:
            raise ValueError("an addition must be a material not already in the control")
        step = Decimal(added["amount_decimal"])
        changed_row, before, after, direction = added, Decimal(0), step, "UP"
        candidate = [*rows, added]
    elif kind == "DOSE_STEP":
        if change["stock_id"] not in ids:
            raise ValueError("a dose step must name a control row")
        direction = change["direction"]
        step = Decimal(change["step_decimal"])
        index = ids.index(change["stock_id"])
        before = Decimal(rows[index]["amount_decimal"])
        after = before + step if direction == "UP" else before - step
        if step <= 0 or after <= 0:
            raise ValueError("a dose step must be positive and leave some material")
        changed_row = dict(rows[index], amount_decimal=_plain(after))
        candidate = [*rows[:index], changed_row, *rows[index + 1:]]
    else:
        raise ValueError("unsupported change kind")
    unit = changed_row["amount_unit"]
    label = stock_label(changed_row)
    plan: dict[str, Any] = {
        "schema_version": "one-change-plan-v1", "state": "ONE_CHANGE_DESIGN_READY",
        "change_kind": kind, "direction": direction, "formula_action": "PROPOSAL_ONLY",
        "authority": dict(FALSE_ACTION_AUTHORITY),
        "control_sha256": _hash(rows), "candidate_rows": candidate,
        "changed_row": {"stock_id": changed_row["stock_id"], "identity_name": changed_row["identity_name"],
                        "stock": label, "amount_unit": unit, "control_amount_decimal": _plain(before),
                        "variant_amount_decimal": _plain(after), "full_bottle_step_decimal": _plain(step)},
        "comparison_basis": "FIXED_OTHER_ROWS_ONE_ROW_CHANGED",
        "active_total_preserved": False, "inventory_binding_verified": False, "sensory_validation": "NOT_TESTED",
        "limitation": "Every other row keeps its amount, so the total differs by the step; this is not safety approval.",
    }
    bottle = change.get("bottle_volume_ul_decimal")
    bottle_ul = Decimal(bottle) if bottle is not None else None
    how: dict[str, Any] = {"method": None, "split_vial": None, "blotter_preview": None,
                           "fresh_vials": None, "why_no_split": None}
    if direction == "UP":
        reason = _why_no_split(unit, step, bottle_ul)
        if reason is None and bottle_ul is not None:
            how.update(method="SPLIT_VIAL", split_vial=_split_vial(label, step, bottle_ul))
        else:
            how.update(method="BLOTTER_PREVIEW", blotter_preview=_blotter_preview(label), why_no_split=reason)
    else:
        how.update(method="FRESH_VIALS", why_no_split=(
            "Nothing can be taken out of a mixed bottle, so a step down is tried in fresh vials."), fresh_vials={
            "steps": [
                "Mix the control rows in one fresh vial and the variant rows in another, using the same amounts for every other row.",
                f"The only difference is {label}: {_plain(before)} {unit} in the control, {_plain(after)} {unit} in the variant.",
                "Compare the two on blotters at 0, 15 and 60 minutes.",
            ],
            "times_min": list(BLOTTER_TIMES_MIN),
        })
    plan["how_to_try"] = how
    plan["plan_sha256"] = _hash(plan)
    return plan
