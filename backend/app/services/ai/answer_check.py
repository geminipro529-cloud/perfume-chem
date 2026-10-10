"""Post-check an AI answer against the materials Kenny owns (inventory.txt)."""

from __future__ import annotations

import re
from typing import Any, Iterable

from engine.inventory_parser import parse_inventory

# Answer fields that name materials the AI is proposing (not the user's own input).
_NAME_FIELDS: tuple[tuple[tuple[str, ...], str | None], ...] = (
    (("modifications", "to_add"), "name"),
    (("chemistry_insights", "suggested_fixatives"), None),
    (("classic_pairings",), "ingredient"),
    (("modern_pairings",), "ingredient"),
    (("synthetic_alternatives",), "name"),
    (("natural_alternatives",), "name"),
)
_TEXT_ROW = re.compile(r"^[\s\-*\d.)]*([A-Za-z][A-Za-z0-9 ,'/\-]*?)\s*[:–-]\s*[\d.]+\s*%")


def _key(name: str) -> str:
    cleaned = re.sub(r"\([^)]*\)|\d+(\.\d+)?\s*%", " ", name)
    return " ".join(cleaned.split()).casefold()


def _dig(answer: Any, path: tuple[str, ...]) -> Any:
    for part in path:
        if not isinstance(answer, dict):
            return None
        answer = answer.get(part)
    return answer


def _names_from(answer: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for path, field in _NAME_FIELDS:
        items = _dig(answer, path)
        for item in items if isinstance(items, list) else []:
            value = item.get(field) if field and isinstance(item, dict) else item
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
    raw = answer.get("raw_analysis")
    if isinstance(raw, str):
        for line in raw.splitlines():
            match = _TEXT_ROW.match(line)
            if match:
                names.append(match.group(1).strip())
    return names


def owned_keys() -> frozenset[str]:
    return frozenset(
        _key(m.name)
        for m in parse_inventory(unique=True, include_solvents=True, include_unavailable=False)
    )


def check_answer(answer: dict[str, Any], owned: Iterable[str] | None = None) -> dict[str, Any]:
    """Return {"checked": True, "not_in_stock": [...]}; unknown names count as not in stock."""
    try:
        stock = frozenset(owned) if owned is not None else owned_keys()
    except Exception:  # an unreadable inventory must not break the AI answer itself
        return {"checked": False, "not_in_stock": []}
    missing: list[str] = []
    seen: set[str] = set()
    for name in _names_from(answer):
        key = _key(name)
        if key and key not in stock and key not in seen:
            seen.add(key)
            missing.append(name)
    return {"checked": True, "not_in_stock": missing}
