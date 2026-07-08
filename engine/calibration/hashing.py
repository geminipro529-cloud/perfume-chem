"""Stable identity helpers for empirical calibration records."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping


def stable_formula_hash(
    formula_name: str,
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
) -> str:
    """Hash formula identity from name, raw uL rows, and dilution rows.

    Row order is intentionally ignored. Amounts are rounded to 6 decimals so
    parser float noise does not create a different identity.
    """
    dilutions = dilutions or {}
    payload = {
        "name": _norm_text(formula_name),
        "rows": [
            {
                "material": _norm_text(material),
                "raw_ul": round(float(amount or 0.0), 6),
                "dilution": round(float(dilutions.get(material, 1.0) or 1.0), 6),
            }
            for material, amount in sorted(
                ingredients_ul.items(),
                key=lambda item: _norm_text(item[0]),
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def formula_hash_from_record(formula: Mapping) -> str:
    """Hash a parsed formula record from `scripts.verify_formula_workflow`."""
    return stable_formula_hash(
        str(formula.get("name", "")),
        formula.get("ingredients_ul", {}) or {},
        formula.get("dilutions", {}) or {},
    )


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())
