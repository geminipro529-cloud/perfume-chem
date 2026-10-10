"""Post-check an AI answer against the materials Kenny owns (inventory.txt)."""

from __future__ import annotations

import re
from typing import Any, Iterable

from engine.inventory_parser import parse_inventory
from engine.name_utils import normalize_name

# Answer fields that name materials the AI is proposing (not the user's own input).
_NAME_FIELDS: tuple[tuple[tuple[str, ...], str | None], ...] = (
    (("modifications", "to_add"), "name"),
    (("chemistry_insights", "suggested_fixatives"), None),
    (("classic_pairings",), "ingredient"),
    (("modern_pairings",), "ingredient"),
    (("synthetic_alternatives",), "name"),
    (("natural_alternatives",), "name"),
    (("cost_optimization",), "with"),
)

# Everyday names the engine's alias table does not carry; values are inventory names.
_EXTRA_ALIASES = {
    "bergamot": "Bergamot FCF oil Sicilian",
    "bergamot oil": "Bergamot FCF oil Sicilian",
    "bergamot eo": "Bergamot FCF oil Sicilian",
    "bergamot essential oil": "Bergamot FCF oil Sicilian",
    "dpg": "Dipropylene Glycol",
}


def _key(name: str) -> str:
    cleaned = re.sub(r"[®™]|\([^)]*\)|\d+(\.\d+)?\s*%", " ", name)
    cleaned = re.sub(r"\s+\d+(\.\d+)?$", "", " ".join(cleaned.split()))
    key = normalize_name(cleaned)
    extra = _EXTRA_ALIASES.get(key)
    return str(normalize_name(extra) if extra else key)


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
    return names


def owned_keys() -> frozenset[str]:
    return frozenset(
        _key(m.name)
        for m in parse_inventory(unique=True, include_solvents=True, include_unavailable=False)
    )


def check_answer(answer: dict[str, Any], owned: Iterable[str] | None = None) -> dict[str, Any]:
    """Return {"checked": True, "not_matched": [...]}: names not matched to the inventory.

    A raw-text fallback answer (any raw_* key) was never parsed into fields, so it is
    reported as not checked rather than scanned with a guess.
    """
    if any(isinstance(k, str) and k.startswith("raw_") for k in answer):
        return {"checked": False, "not_matched": []}
    try:
        stock = frozenset(owned) if owned is not None else owned_keys()
    except Exception:  # an unreadable inventory must not break the AI answer itself
        return {"checked": False, "not_matched": []}
    missing: list[str] = []
    seen: set[str] = set()
    for name in _names_from(answer):
        key = _key(name)
        if key and key not in stock and key not in seen:
            seen.add(key)
            missing.append(name)
    return {"checked": True, "not_matched": missing}
