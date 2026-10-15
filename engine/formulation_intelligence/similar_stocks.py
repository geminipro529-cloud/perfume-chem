"""Owned stocks with a similar character, and a map of the shelf by character.

Plan item F6. When a stock runs out, the Lab offers owned stocks whose declared
character is close, always labelled "similar, not the same". The comparison reads
the capability index the composer uses (engine/formulation_intelligence/
material_capability_index.py): each stock's character scores (0 to 10 per
facet such as woody or powdery) and its own odor words. A stock whose profile is
only its category's (HEURISTIC_CATEGORY_PROXY) says so.

This is a comparison of written profiles, not of smell: it makes no strength,
intensity, OAV or liking claim (AGENTS.md Rule 1). Stocks are grouped by material
name (a note in brackets or a trailing "neat" does not make another material), and
the stock's own other bottles are listed apart, first, because they are not a
substitute but the same thing at another strength or grade; each keeps its own
label. Read-only: nothing changes a formula or stock.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "similar-stocks-v1"
MAP_SCHEMA_VERSION = "shelf-map-v1"
LABEL = "similar, not the same"
BASIS = (
    "Compared by the character scores and odor words written for each stock, not by smell. "
    "A swap still needs your nose."
)
PROXY_SOURCE = "HEURISTIC_CATEGORY_PROXY"
# Facets the shelf map counts for gaps (the composer's main character axes).
MAIN_FACETS = (
    "sweetness", "floral", "green", "freshness", "transparency", "warmth", "woody",
    "powdery", "creamy", "animalic", "spicy", "smoky", "radiance",
)
# Facet names some profiles spell differently; each pair is one facet.
_FACET_ALIASES = {"transparent": "transparency", "sweet": "sweetness", "fresh": "freshness", "leathery": "leather"}
# How a facet reads after "more" or "less", or in "both ...".
_FACET_WORDS = {
    "sweetness": "sweet", "freshness": "fresh", "transparency": "transparent", "warmth": "warm",
    "radiance": "radiant", "rose": "rosy", "citrus": "citrusy", "sourness": "sour", "sulfury": "sulfurous",
}
_SHARED_MIN = 4.0
_DIFFER_MIN = 3.0
_LEAD_MIN = 6.0
_NEAR_DUPLICATE = 0.97
_SIMILAR_MIN = 0.5
_CLOSE = 0.8
_NEAR_DUPLICATE_MAX = 30


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _name_key(name: object) -> str:
    """One key for the stocks of one material: a note in brackets and a trailing "neat" do not count."""

    key = _key(re.sub(r"\([^)]*\)", " ", str(name or "")))
    return re.sub(r"(?: neat)+$", "", key).strip() or _key(name)


def _vector(capability: Any) -> dict[str, float]:
    vector: dict[str, float] = {}
    for name, value in capability.character:
        facet = _FACET_ALIASES.get(str(name), str(name))
        if float(value) > 0:
            vector[facet] = max(vector.get(facet, 0.0), float(value))
    return vector


def _word(facet: str) -> str:
    return _FACET_WORDS.get(facet, facet)


def _cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(name, 0.0) for name, value in a.items())
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    left, right = set(a), set(b)
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _similarity(a: Any, b: Any) -> float:
    va, vb = _vector(a), _vector(b)
    words = _jaccard(a.descriptor_vocabulary, b.descriptor_vocabulary)
    if va and vb:
        return 0.7 * _cosine(va, vb) + 0.3 * words
    return words


def _shared_and_differs(a: Any, b: Any) -> tuple[list[str], list[str]]:
    va, vb = _vector(a), _vector(b)
    if not (va and vb):
        return sorted(set(a.descriptor_vocabulary) & set(b.descriptor_vocabulary))[:4], []
    shared = sorted(
        (name for name in va if va[name] >= _SHARED_MIN and vb.get(name, 0.0) >= _SHARED_MIN),
        key=lambda name: (-min(va[name], vb[name]), name),
    )
    differs = []
    for name in sorted(set(va) | set(vb), key=lambda n: (-abs(vb.get(n, 0.0) - va.get(n, 0.0)), n)):
        gap = vb.get(name, 0.0) - va.get(name, 0.0)
        if abs(gap) >= _DIFFER_MIN:
            differs.append(f"more {_word(name)}" if gap > 0 else f"less {_word(name)}")
    return [_word(name) for name in shared[:4]], differs[:3]


def _owned_capabilities() -> tuple[Any, ...]:
    from engine.formulation_intelligence.material_capability_index import (
        build_material_capability_index,
    )
    from engine.personal_inventory import materialize_personal_inventory

    owned = {
        stock.stock_id for stock in materialize_personal_inventory().stocks
        if str(stock.status).casefold() == "owned"
    }
    return tuple(c for c in build_material_capability_index().capabilities if c.stock_id in owned)


def _stock_line(capability: Any) -> dict[str, Any]:
    return {
        "stock_id": capability.stock_id,
        "stock_label": capability.stock_label,
        "design_ready": bool(capability.design_ready),
    }


def _display_name(group: Sequence[Any]) -> str:
    return min((c.identity_name for c in group), key=lambda name: (len(name), name.casefold()))


def _groups(pool: Iterable[Any]) -> dict[str, list[Any]]:
    """Owned stocks by material name, each group's ready stocks first."""

    groups: dict[str, list[Any]] = {}
    for capability in pool:
        groups.setdefault(_name_key(capability.identity_name), []).append(capability)
    for group in groups.values():
        group.sort(key=lambda c: (not c.design_ready, str(c.stock_label).casefold(), c.stock_id))
    return groups


def _profiled(group: Sequence[Any]) -> Any:
    """The stock whose written profile stands for its group: a declared profile over a category's."""

    ranked = sorted(group, key=lambda c: (not _vector(c), c.profile_source == PROXY_SOURCE))
    return ranked[0]


def _find_base(pool: Sequence[Any], stock_id: str | None, material: str | None) -> Any:
    if stock_id:
        base = next((c for c in pool if c.stock_id == stock_id), None)
        if base is not None:
            return base
    if material:
        same = _groups(pool).get(_name_key(material))
        if same:
            return _profiled(same)
    raise LookupError("That stock has no character profile in the Lab yet, so nothing can be compared with it.")


def similar_stocks(
    stock_id: str | None = None,
    *,
    material: str | None = None,
    limit: int = 6,
    capabilities: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Owned materials closest in written character to a stock, with its other bottles first.

    The stock is found by `stock_id`, or else by material name. Each similar
    material lists every owned stock of it, so a swap can pick a strength.
    """

    pool = tuple(capabilities) if capabilities is not None else _owned_capabilities()
    base = _find_base(pool, stock_id, material)
    groups = _groups(pool)
    own_key = _name_key(base.identity_name)
    no_profile = not _vector(base) and not base.descriptor_vocabulary
    scored = []
    for key, group in groups.items():
        if key == own_key or no_profile:
            continue
        stand_in = _profiled(group)
        score = _similarity(base, stand_in)
        if score >= _SIMILAR_MIN:
            scored.append((score, key, group, stand_in))
    scored.sort(key=lambda item: (-item[0], _display_name(item[2]).casefold(), item[1]))
    similar = []
    for score, _key_text, group, stand_in in scored[: max(0, limit)]:
        shares, differs = _shared_and_differs(base, stand_in)
        similar.append({
            "identity_name": _display_name(group),
            "note": stand_in.note,
            "shares": shares,
            "differs": differs,
            "closeness": "close" if score >= _CLOSE else "some",
            "profile_from_category": stand_in.profile_source == PROXY_SOURCE,
            "stocks": [_stock_line(c) for c in group],
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "stock": {
            "stock_id": base.stock_id, "identity_name": base.identity_name, "stock_label": base.stock_label,
            "note": base.note, "profile_from_category": base.profile_source == PROXY_SOURCE,
        },
        "same_material": [_stock_line(c) for c in groups.get(own_key, []) if c.stock_id != base.stock_id],
        "similar": similar,
        "label": LABEL,
        "basis": BASIS,
        "no_profile": no_profile,
        "inventory_modified": False,
        "formula_modified": False,
    }


def _project(vectors: Sequence[Mapping[str, float]]) -> tuple[list[tuple[float, float]], dict[str, dict[str, str]]]:
    """Two principal components of the character scores, scaled to 0..1, and the
    facet each axis runs towards at either end."""

    import numpy as np

    facets = sorted({name for vector in vectors for name in vector})
    if len(vectors) < 3 or len(facets) < 2:
        return [(0.5, 0.5) for _ in vectors], {}
    matrix = np.array([[vector.get(name, 0.0) for name in facets] for vector in vectors], dtype=float)
    centred = matrix - matrix.mean(axis=0)
    _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
    axes: dict[str, dict[str, str]] = {}
    for axis, name in enumerate(("x", "y")):
        loading = vt[axis]
        # A fixed sign (the facet that weighs most runs to the high end), so the map does not flip between runs.
        if loading[int(np.argmax(np.abs(loading)))] < 0:
            vt[axis] = -loading
        axes[name] = {"low": _word(facets[int(np.argmin(vt[axis]))]), "high": _word(facets[int(np.argmax(vt[axis]))])}
    points = centred @ vt[:2].T
    for axis in range(2):
        low, high = points[:, axis].min(), points[:, axis].max()
        points[:, axis] = (points[:, axis] - low) / (high - low) if high > low else 0.5
    return [(round(float(x), 4), round(float(y), 4)) for x, y in points], axes


def shelf_map(*, capabilities: Sequence[Any] | None = None) -> dict[str, Any]:
    """Owned materials placed by character, pairs written almost alike, and thinly stocked facets.

    One dot per material: its stocks at several strengths share one written profile.
    """

    pool = tuple(capabilities) if capabilities is not None else _owned_capabilities()
    groups = _groups(pool)
    placed = []
    unplaced = []
    for key, group in sorted(groups.items()):
        stand_in = _profiled(group)
        (placed if _vector(stand_in) else unplaced).append((key, group, stand_in))
    points, axes = _project([_vector(stand_in) for _key_text, _group, stand_in in placed])
    stocks = []
    for (_key_text, group, stand_in), (x, y) in zip(placed, points, strict=True):
        vector = _vector(stand_in)
        lead = max(vector, key=lambda name: (vector[name], name))
        stocks.append({
            "identity_name": _display_name(group), "note": stand_in.note, "x": x, "y": y,
            "leads_with": lead if vector[lead] >= _LEAD_MIN else "",
            "leads_with_word": _word(lead) if vector[lead] >= _LEAD_MIN else "",
            "profile_from_category": stand_in.profile_source == PROXY_SOURCE,
            "stocks": [_stock_line(c) for c in group],
        })
    declared = [item for item in placed if item[2].profile_source != PROXY_SOURCE]
    pairs = []
    for index, (_ka, group_a, a) in enumerate(declared):
        for _kb, group_b, b in declared[index + 1:]:
            score = _cosine(_vector(a), _vector(b))
            if score >= _NEAR_DUPLICATE:
                pairs.append((score, _display_name(group_a), _display_name(group_b), a, b))
    pairs.sort(key=lambda item: (-item[0], item[1].casefold(), item[2].casefold()))
    leaders = {facet: sorted(s["identity_name"] for s in stocks if s["leads_with"] == facet) for facet in MAIN_FACETS}
    return {
        "schema_version": MAP_SCHEMA_VERSION,
        "stocks": stocks,
        "axes": axes,
        "unplaced": sorted(_display_name(group) for _key_text, group, _stand_in in unplaced),
        "written_alike": [
            {"a": name_a, "b": name_b, "shares": _shared_and_differs(a, b)[0]}
            for _score, name_a, name_b, a, b in pairs[:_NEAR_DUPLICATE_MAX]
        ],
        "facets": [
            {"facet": facet, "word": _word(facet), "leaders": leaders[facet], "count": len(leaders[facet])}
            for facet in MAIN_FACETS
        ],
        "label": LABEL,
        "basis": (
            "Placed by the character scores written for each stock, not by smell. Close dots have similar "
            "written profiles; a facet led by few materials is thin on your shelf. Pairs written almost "
            "alike may smell quite different: the Lab cannot tell them apart, your nose can."
        ),
        "inventory_modified": False,
    }


__all__ = ["BASIS", "LABEL", "MAIN_FACETS", "SCHEMA_VERSION", "shelf_map", "similar_stocks"]
