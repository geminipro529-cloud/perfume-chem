# allow: SIZE_OK — query layer with many small functions

"""Rules query API over the perfumery knowledge SQLite database.

Connects to ``data/perfumery_kb.db`` and exposes rule tables:
archetypes, pyramid ratios, IFRA limits, EU allergens,
olfactory fatigue, Jellinek classes, character shifts,
Hill parameters, iconic skeletons, accords, and brief defaults.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "perfumery_kb.db"


def _get_conn() -> sqlite3.Connection:
    """Open a read-only connection."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    """Convert a Row to a plain dict."""
    keys = row.keys()
    return {k: _coerce(row[k]) for k in keys}


def _coerce(val: object) -> object:
    """Return a JSON-parsed object if *val* is a JSON string, else *val*."""
    if isinstance(val, str) and val.startswith(("{", "[")):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return val
    return val


# ── Archetype ──────────────────────────────────────────────────────────


def get_archetype(key: str) -> dict[str, object] | None:
    """Return the full archetype with all related data.

    Returns base info from ``family_archetypes`` plus ``anchors``,
    ``drift_limits``, ``oav_targets``, and ``repair_pool``.
    Returns ``None`` if *key* is not found.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM family_archetypes WHERE key = ?", (key,))
        base = cur.fetchone()
        if base is None:
            return None

        result = _row_to_dict(base)
        aid: int = result["id"]  # type: ignore[assignment]

        # Anchors
        cur.execute(
            "SELECT * FROM archetype_anchors WHERE archetype_id = ?",
            (aid,),
        )
        result["anchors"] = [_row_to_dict(r) for r in cur.fetchall()]

        # Drift limits
        cur.execute(
            "SELECT * FROM archetype_drift_limits WHERE archetype_id = ?",
            (aid,),
        )
        result["drift_limits"] = [_row_to_dict(r) for r in cur.fetchall()]

        # OAV targets
        cur.execute(
            "SELECT * FROM archetype_oav_targets WHERE archetype_id = ?",
            (aid,),
        )
        result["oav_targets_list"] = [_row_to_dict(r) for r in cur.fetchall()]

        # Repair pool
        cur.execute(
            "SELECT * FROM archetype_repair_pool WHERE archetype_id = ?",
            (aid,),
        )
        result["repair_pool"] = [_row_to_dict(r) for r in cur.fetchall()]

        return result
    finally:
        conn.close()


# ── Pyramid ratios ─────────────────────────────────────────────────────


def get_pyramid_ratio(family: str, bracket: str) -> dict[str, object] | None:
    """Return ``{top_pct, heart_pct, base_pct}`` for a family and bracket.

    *bracket* is a concentration bracket like ``'EdT'``, ``'EdP'``,
    ``'EdC'``, ``'Extrait'``.
    Returns ``None`` if no matching ratio exists.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM pyramid_ratios WHERE family_key = ? AND bracket = ?",
            (family, bracket),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ── OAV targets ────────────────────────────────────────────────────────


def get_oav_targets(family: str) -> list[dict[str, object]]:
    """Return OAV target entries for a family.

    Each entry contains ``time_window``, ``odor_family``, ``target_oav``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM oav_targets WHERE family_key = ?", (family,))
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_material_role_ratios(style: str) -> list[dict[str, object]]:
    """Return role ratio entries for a style (e.g. ``'fougere'``).

    Each entry contains ``role``, ``min_pct``, ``max_pct``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT role, min_pct, max_pct FROM material_role_ratios WHERE style = ?",
            (style,),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Cross-family compatibility ─────────────────────────────────────────


def check_cross_family(family_a: str, family_b: str) -> str | None:
    """Return the compatibility level between two families.

    Returns ``'high'``, ``'medium'``, ``'low'``, ``'very_low'``, or
    ``None`` if no entry exists.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT compatibility_level FROM cross_family_compatibility "
            "WHERE (family_a = ? AND family_b = ?) "
            "OR (family_a = ? AND family_b = ?)",
            (family_a, family_b, family_b, family_a),
        )
        row = cur.fetchone()
        return str(row[0]) if row else None
    finally:
        conn.close()


# ── IFRA limits ────────────────────────────────────────────────────────


def get_ifra_limit(name: str) -> float | None:
    """Return the IFRA Cat 4 limit percentage for a material.

    Queries the ``ifra_limits`` table. Returns ``None`` if no limit.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT cat4_limit_pct FROM ifra_limits WHERE material_name = ?",
            (name,),
        )
        row = cur.fetchone()
        val = row[0] if row else None
        return float(val) if val is not None else None
    finally:
        conn.close()


# ── EU allergens ───────────────────────────────────────────────────────


def get_eu_allergens() -> list[dict[str, object]]:
    """Return all EU allergen entries from ``eu_allergens``."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM eu_allergens")
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Banned materials ───────────────────────────────────────────────────


def get_banned_materials() -> list[str]:
    """Return a list of banned material names."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT material_name FROM banned_materials")
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Olfactory fatigue ──────────────────────────────────────────────────


def get_fatigue_threshold(name: str) -> dict[str, float | None] | None:
    """Return ``{warn_oav, fail_oav}`` for a material.

    Returns ``None`` if no threshold exists.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT warn_oav, fail_oav FROM olfactory_fatigue WHERE material_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "warn_oav": float(row[0]) if row[0] is not None else None,
            "fail_oav": float(row[1]) if row[1] is not None else None,
        }
    finally:
        conn.close()


# ── Jellinek class ─────────────────────────────────────────────────────


def get_jellinek_class(name: str) -> str | None:
    """Return the Jellinek psychophysical class for a material.

    Returns ``None`` if no entry exists.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT class FROM jellinek_classes WHERE material_name = ?",
            (name,),
        )
        row = cur.fetchone()
        return str(row[0]) if row else None
    finally:
        conn.close()


# ── Character shifts ───────────────────────────────────────────────────


def get_character_shifts(name: str) -> list[dict[str, object]]:
    """Return character shift zones for a material.

    Each entry contains ``max_conc_pct``, ``character``, ``quality``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT max_conc_pct, character, quality FROM character_shifts WHERE material_name = ?",
            (name,),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Hill parameters ────────────────────────────────────────────────────


def get_hill_params(name: str) -> dict[str, float | None] | None:
    """Return ``{ec50, n, rmax}`` for a material.

    Returns ``None`` if no Hill parameters exist.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ec50, n, rmax FROM hill_params WHERE material_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "ec50": float(row[0]) if row[0] is not None else None,
            "n": float(row[1]) if row[1] is not None else None,
            "rmax": float(row[2]) if row[2] is not None else None,
        }
    finally:
        conn.close()


# ── Iconic skeleton ────────────────────────────────────────────────────


def get_iconic_skeleton(family: str) -> dict[str, object] | None:
    """Return the iconic skeleton for a fragrance family.

    Returns ``{marker_materials, source_reference}`` or ``None``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT marker_materials_json, source_reference FROM iconic_skeletons WHERE family = ?",
            (family,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        marker_raw = row[0]
        marker = (
            json.loads(marker_raw)
            if isinstance(marker_raw, str) and marker_raw.startswith(("{", "["))
            else marker_raw
        )
        return {
            "marker_materials": marker,
            "source_reference": str(row[1]) if row[1] else None,
        }
    finally:
        conn.close()


# ── Accord ─────────────────────────────────────────────────────────────


def get_accord(family: str) -> dict[str, object] | None:
    """Return the accord entry for a fragrance family.

    Queries the ``accords`` table by matching *family* against
    the ``type`` or ``key`` column. Returns the parsed ``value_json``
    content, or ``None`` if not found.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT value_json FROM accords WHERE type = ? OR key = ?",
            (family, family),
        )
        rows = cur.fetchall()
        if not rows:
            return None
        # Return the first matching record's parsed JSON
        raw = rows[0][0]
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return {"value": raw}
        return {"value": str(raw)}
    finally:
        conn.close()


# ── Brief defaults ─────────────────────────────────────────────────────


def get_brief_defaults() -> dict[str, str]:
    """Map brief keys to fragrance families.

    Tries to import ``engine.families.registry.BRIEF_DEFAULTS`` first.
    Falls back to deriving the mapping from ``family_archetypes``:
    each brief key is the family part (before the first ``.``)
    of an archetype key, mapped to the archetype's family value.
    """
    try:
        from engine.families.registry import (
            BRIEF_DEFAULTS as _BD,  # type: ignore[import-untyped]  # noqa: PLC0415
        )

        if isinstance(_BD, dict):
            return dict(_BD)
    except (ImportError, AttributeError):
        pass

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT "
            "CASE WHEN instr(key, '.') > 0 "
            "  THEN substr(key, 1, instr(key, '.') - 1) "
            "  ELSE key END AS brief_key, "
            "family "
            "FROM family_archetypes "
            "ORDER BY brief_key"
        )
        defaults: dict[str, str] = {}
        for row in cur.fetchall():
            bk = str(row[0])
            fam = str(row[1])
            if bk not in defaults:
                defaults[bk] = fam
        return defaults
    finally:
        conn.close()
