# allow: SIZE_OK — query layer with many small functions

"""Material query API over the perfumery knowledge SQLite database.

All functions connect to ``data/perfumery_kb.db`` and return typed results.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "perfumery_kb.db"


def _get_conn() -> sqlite3.Connection:
    """Open a read-only connection to the knowledge database."""
    conn = sqlite3.connect(
        f"file:{_DB_PATH.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_alias(name: str, cur: sqlite3.Cursor) -> str | None:
    """Return the canonical material name if *name* is an alias."""
    cur.execute(
        "SELECT m.canonical_name FROM material_aliases a "
        "JOIN materials m ON a.material_id = m.id "
        "WHERE LOWER(a.alias_name) = LOWER(?)",
        (name,),
    )
    row = cur.fetchone()
    return str(row[0]) if row else None


def _resolve_canonical(name: str, cur: sqlite3.Cursor) -> str | None:
    """Resolve a name to its canonical form (case-insensitive)."""
    cur.execute(
        "SELECT canonical_name FROM materials WHERE LOWER(canonical_name) = LOWER(?)",
        (name,),
    )
    row = cur.fetchone()
    if row is not None:
        return str(row[0])
    return _resolve_alias(name, cur)


def _material_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    """Convert a materials sqlite3.Row to a plain dict."""
    keys = row.keys()
    return dict(zip(keys, [row[k] for k in keys], strict=False))


def get_material(name: str) -> dict[str, object] | None:
    """Return all fields for a material by canonical name or alias.

    Resolves aliases via the ``material_aliases`` table first, then
    queries the ``materials`` table. Returns ``None`` if not found.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials WHERE canonical_name = ?", (name,))
        row = cur.fetchone()
        if row is not None:
            return _material_row_to_dict(row)

        resolved = _resolve_alias(name, cur)
        if resolved is not None:
            cur.execute("SELECT * FROM materials WHERE canonical_name = ?", (resolved,))
            row = cur.fetchone()
            if row is not None:
                return _material_row_to_dict(row)

        return None
    finally:
        conn.close()


def get_materials_by_note(note: str) -> list[dict[str, object]]:
    """Return all materials whose ``note`` column matches."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials WHERE note = ?", (note,))
        return [_material_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_materials_by_role(role: str) -> list[dict[str, object]]:
    """Return all materials whose ``role`` column matches."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials WHERE role = ?", (role,))
        return [_material_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_materials_by_family(family: str) -> list[dict[str, object]]:
    """Return all materials whose ``odor_family`` column matches."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials WHERE odor_family = ?", (family,))
        return [_material_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_material_vp(name: str) -> float | None:
    """Return ``vp_25c_pa`` for a material, or ``None`` if not found."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT vp_25c_pa FROM materials WHERE canonical_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is not None:
            val = row[0]
            return float(val) if val is not None else None

        resolved = _resolve_alias(name, cur)
        if resolved is not None:
            cur.execute(
                "SELECT vp_25c_pa FROM materials WHERE canonical_name = ?",
                (resolved,),
            )
            row = cur.fetchone()
            if row is not None:
                val = row[0]
                return float(val) if val is not None else None
        return None
    finally:
        conn.close()


def get_material_odt(name: str) -> tuple[float, float] | None:
    """Return ``(odt_air_ppb, odt_eth_ppm)`` or ``None``."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT odt_air_ppb, odt_eth_ppm FROM materials WHERE canonical_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is not None:
            air, eth = row[0], row[1]
            if air is not None or eth is not None:
                return (
                    float(air) if air is not None else 0.0,
                    float(eth) if eth is not None else 0.0,
                )

        resolved = _resolve_alias(name, cur)
        if resolved is not None:
            cur.execute(
                "SELECT odt_air_ppb, odt_eth_ppm FROM materials WHERE canonical_name = ?",
                (resolved,),
            )
            row = cur.fetchone()
            if row is not None:
                air, eth = row[0], row[1]
                if air is not None or eth is not None:
                    return (
                        float(air) if air is not None else 0.0,
                        float(eth) if eth is not None else 0.0,
                    )
        return None
    finally:
        conn.close()


def get_material_ifra_limit(name: str) -> float | None:
    """Return ``ifra_cat4_limit_pct`` (may be ``NULL``)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ifra_cat4_limit_pct FROM materials WHERE canonical_name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is not None:
            val = row[0]
            return float(val) if val is not None else None

        resolved = _resolve_alias(name, cur)
        if resolved is not None:
            cur.execute(
                "SELECT ifra_cat4_limit_pct FROM materials WHERE canonical_name = ?",
                (resolved,),
            )
            row = cur.fetchone()
            val = row[0] if row else None
            return float(val) if val is not None else None
        return None
    finally:
        conn.close()


def get_material_synergies(name: str) -> list[str]:
    """Return list of material names that synergise with *name*.

    Queries ``material_interactions`` where ``material_a`` matches
    (case-insensitive) and ``type`` is ``'synergy'``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        canonical = _resolve_canonical(name, cur)
        if canonical is None:
            return []

        cur.execute(
            "SELECT material_b FROM material_interactions "
            "WHERE LOWER(material_a) = LOWER(?) AND type = 'synergy'",
            (canonical,),
        )
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()


def get_material_clashes(name: str) -> list[str]:
    """Return list of material names that clash with *name*.

    Queries ``material_interactions`` where ``material_a`` matches
    (case-insensitive) and ``type`` is ``'conflict'`` or ``'clash'``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        canonical = _resolve_canonical(name, cur)
        if canonical is None:
            return []

        cur.execute(
            "SELECT material_b FROM material_interactions "
            "WHERE LOWER(material_a) = LOWER(?) AND type IN ('conflict', 'clash')",
            (canonical,),
        )
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()


def get_natural_decomposition(name: str) -> list[dict[str, object]] | None:
    """Return constituent breakdown for a natural material.

    Returns a list of dicts with keys ``constituent_name``,
    ``weight_frac``, ``mw``, ``vp``, ``odt_air_ppb``, ``odt_eth_ppm``.
    Returns ``None`` if the material has no decomposition or is unknown.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM materials WHERE canonical_name = ?", (name,))
        row = cur.fetchone()
        material_id: int | None = row[0] if row else None

        if material_id is None:
            resolved = _resolve_alias(name, cur)
            if resolved is None:
                return None
            cur.execute(
                "SELECT id FROM materials WHERE canonical_name = ?",
                (resolved,),
            )
            row = cur.fetchone()
            material_id = row[0] if row else None

        if material_id is None:
            return None

        cur.execute(
            "SELECT constituent_name, weight_frac, mw, vp, odt_air_ppb, odt_eth_ppm "
            "FROM material_natural_decomposition WHERE material_id = ?",
            (material_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        return [
            {
                "constituent_name": str(r[0]),
                "weight_frac": r[1],
                "mw": r[2],
                "vp": r[3],
                "odt_air_ppb": r[4],
                "odt_eth_ppm": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def search_materials(query: str) -> list[dict[str, object]]:
    """Text search ``canonical_name``, ``role``, ``texture``, ``odor_family``.

    Uses SQL ``LIKE`` with ``%`` wildcards on each side of *query*.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        pattern = f"%{query}%"
        cur.execute(
            "SELECT * FROM materials WHERE "
            "canonical_name LIKE ? OR role LIKE ? OR texture LIKE ? OR odor_family LIKE ?",
            (pattern, pattern, pattern, pattern),
        )
        return [_material_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
