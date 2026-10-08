"""Explicit stock-strength boundaries for legacy advisory analysis.

These helpers validate a declared fraction, not its concentration basis,
carrier, density, physical stock or build authority. No mass/volume conversion
or sensory claim follows from a valid fraction.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

_PERCENT = re.compile(
    r"(?:pre[- ]dilute\s+)?([+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*%"
    r"(?:\s*(?:\((?:w/w|w/v|v/v)\)|w/w|w/v|v/v))?"
    r"(?:\s+in\s+[^%\r\n]+)?",
    re.IGNORECASE,
)


def declared_stock_fraction(raw: str) -> float:
    """Accept explicit neat/percent only; unknown is never silently neat."""
    if isinstance(raw, str):
        text = raw.replace("**", "").strip().casefold()
        if text in {"neat", "pure", "undiluted", "neat solid", "neat crystals", "pure crystals"}:
            return 1.0
        match = _PERCENT.fullmatch(text)
        if match is not None:
            fraction = Decimal(match.group(1).replace(",", ".")) / Decimal(100)
            if fraction.is_finite() and Decimal(0) < fraction <= Decimal(1):
                return float(fraction)
    raise ValueError("Stock strength is missing, ambiguous or invalid; cannot default to neat")


def _fraction(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean stock fraction")
    try:
        fraction = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("stock fraction not declared") from error
    if not math.isfinite(fraction) or not 0 < fraction <= 1:
        raise ValueError("stock fraction outside (0, 1]")
    return fraction


def validated_advisory_dilutions(
    ingredients: Mapping[str, Any],
    dilutions: Mapping[str, Any],
    *,
    context: str,
    stock_specs: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    """Validate every positive-dose declaration before constructing a vector."""
    try:
        result: dict[str, float] = {}
        for name, dose in ingredients.items():
            if isinstance(dose, bool):
                raise ValueError("boolean dose")
            amount = float(dose)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("invalid dose")
            if amount == 0:
                continue
            fraction = _fraction(dilutions.get(name))
            if stock_specs is not None:
                spec = stock_specs.get(name)
                if not isinstance(spec, Mapping) or spec.get("declared") is not True:
                    raise ValueError("stock declaration missing")
                if spec.get("conflict"):
                    raise ValueError("conflicting stock declaration")
                if not math.isclose(
                    fraction, _fraction(spec.get("fraction")), rel_tol=1e-12, abs_tol=0,
                ):
                    raise ValueError("stock fraction disagrees with dilution")
            result[name] = fraction
        return result
    except (TypeError, ValueError, OverflowError, AttributeError) as error:
        raise ValueError(f"{context} abstained: {error}") from error
