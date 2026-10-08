"""Read-only, fixed-row mass-basis omission experiments, not a formula re-solve.

An equal mass of the declared stock carrier replaces the omitted stock. This
preserves total mass and every retained dose, not total fragrance-active mass.
No density, active-volume, mixed-carrier or sensory equivalence is inferred.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping, Sequence

from engine.research.contracts import FALSE_ACTION_AUTHORITY


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _quantity(value: Any, *, positive: bool = False) -> Decimal:
    if (not isinstance(value, str) or len(value) > 40
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value)):
        raise ValueError("bounded plain decimal strings required")
    result = Decimal(value)
    if not result.is_finite() or result < 0 or (positive and not result):
        raise ValueError("invalid physical quantity")
    return result


def plan_controlled_omission(
    *, control_rows: Sequence[Mapping[str, Any]], omit_stock_ids: Sequence[str],
    protected_stock_ids: Sequence[str], carrier_blanks: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Pure bounded planning. Nothing is saved, reserved, added or committed.

    Blank entries identify an existing blank stock and its exact carrier. This
    entry point does not authenticate inventory; its receipt remains a proposal.
    """
    result: dict[str, Any] = {
        "schema_version": "controlled-omission-plan-v1", "state": "WITHHOLD_UNKNOWN",
        "formula_action": "NO_CHANGE", "authority": dict(FALSE_ACTION_AUTHORITY),
        "control_sha256": None, "candidate_rows": [], "reason_codes": [],
        "comparison_basis": "EQUAL_TOTAL_MASS_FIXED_RETAINED_STOCK_DOSES",
        "active_total_preserved": False, "inventory_binding_verified": False,
        "sensory_validation": "NOT_TESTED",
    }
    try:
        if (not isinstance(control_rows, (list, tuple)) or not 1 <= len(control_rows) <= 60
                or not isinstance(omit_stock_ids, (list, tuple)) or not omit_stock_ids
                or not isinstance(protected_stock_ids, (list, tuple))
                or not isinstance(carrier_blanks, dict)):
            raise ValueError("invalid omission shape")
        if not all(isinstance(x, str) and x for x in (*omit_stock_ids, *protected_stock_ids)):
            raise ValueError("invalid stock identity")
        if len(set(omit_stock_ids)) != len(omit_stock_ids):
            raise ValueError("duplicate omission")
        blank_identities: dict[str, str] = {}
        for carrier, blank in carrier_blanks.items():
            if not isinstance(carrier, str) or not isinstance(blank, dict):
                raise ValueError("invalid carrier blank")
            blank_id = blank.get("stock_id")
            if not isinstance(blank_id, str):
                raise ValueError("invalid blank stock identity")
            if blank_id in blank_identities and blank_identities[blank_id] != carrier:
                raise ValueError("one blank stock cannot have two carrier identities")
            blank_identities[blank_id] = carrier
        fields = {"stock_id", "identity_name", "amount_decimal", "amount_unit",
                  "stock_fraction_decimal", "fraction_basis", "carrier"}
        rows = []
        total = Decimal(0)
        for row in control_rows:
            if not isinstance(row, dict) or set(row) != fields:
                raise ValueError("invalid control row")
            if not all(isinstance(row[k], str) and row[k].strip() for k in ("stock_id", "identity_name")):
                raise ValueError("invalid control identity")
            amount = _quantity(row["amount_decimal"], positive=True)
            fraction = _quantity(row["stock_fraction_decimal"], positive=True)
            if fraction > 1:
                raise ValueError("invalid fraction")
            rows.append(copy.deepcopy(row))
            # At most 60 plain <=40-character quantities. 128 digits preserves
            # the largest integer plus smallest fractional term without rounding.
            with localcontext() as arithmetic:
                arithmetic.prec = 128
                total += amount
        ids = [r["stock_id"] for r in rows]
        if len(ids) != len(set(ids)) or not set(omit_stock_ids) < set(ids):
            raise ValueError("omission requires distinct existing rows and a retained control")
        if not set(protected_stock_ids) <= set(ids):
            raise ValueError("unknown protected stock")
        result["control_sha256"] = _hash(rows)
        if set(omit_stock_ids) & set(protected_stock_ids):
            result["reason_codes"] = ["PROTECTED_STOCK_OMISSION_FORBIDDEN"]
            return result
        if any(r["amount_unit"] != "mg" or r["fraction_basis"] != "w/w" for r in rows):
            result["reason_codes"] = ["HOLD_EXACT_COMMON_MASS_BASIS_REQUIRED"]
            return result
        retained = [r for r in rows if r["stock_id"] not in omit_stock_ids]
        omitted = [r for r in rows if r["stock_id"] in omit_stock_ids]
        additions = []
        for row in omitted:
            carrier = row["carrier"]
            blank = carrier_blanks.get(carrier) if isinstance(carrier, str) else None
            if (not carrier or not isinstance(blank, dict)
                    or set(blank) != {"stock_id", "carrier"}
                    or not isinstance(blank["stock_id"], str) or not blank["stock_id"]
                    or blank["stock_id"] in ids or blank["carrier"] != carrier):
                result["reason_codes"] = ["HOLD_MATCHED_CARRIER_BLANK_REQUIRED"]
                return result
            additions.append({"stock_id": blank["stock_id"], "identity_name": carrier,
                              "carrier": carrier, "amount_decimal": row["amount_decimal"],
                              "amount_unit": "mg", "stock_fraction_decimal": "0",
                              "fraction_basis": "w/w", "operation": "CARRIER_BLANK_REPLACEMENT",
                              "replaces_stock_id": row["stock_id"]})
        result.update(
            state="CONTROLLED_OMISSION_DESIGN_READY", formula_action="PROPOSAL_ONLY",
            candidate_rows=[*retained, *additions], omitted_stock_ids=list(omit_stock_ids),
            retained_rows_sha256=_hash(retained), carrier_replacements=additions,
            total_mass_mg=format(total, "f"), retained_doses_exactly_preserved=True,
            limitation="Equal mass blanking lowers active fragrance mass; it is not equal-active-dose comparison or safety approval.",
        )
        result["plan_sha256"] = _hash(result)
        return result
    except (ValueError, TypeError, InvalidOperation):
        result.update(state="INVALID_INPUT", candidate_rows=[], reason_codes=["INVALID_OMISSION_INPUT"])
        return result


def verify_controlled_omission(receipt: Mapping[str, Any], **inputs: Any) -> bool:
    """Independent exact replay against the supplied control, never self-hashing alone."""
    try:
        return dict(receipt) == plan_controlled_omission(**inputs)
    except (ValueError, TypeError):
        return False
