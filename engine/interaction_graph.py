# allow: SIZE_OK — query layer with many small functions

"""Interaction graph query API over the perfumery knowledge SQLite database.

Provides functions to query, insert, and analyse material interactions
(synergies, clashes, pairing recommendations, replacements) plus chemical
incompatibility rules documented in AGENTS.md F11.

Usage::

    from engine.interaction_graph import (
        get_interaction,
        get_synergies,
        get_clashes,
        add_interaction,
        get_coverage_stats,
        get_incompatible_naturals,
        check_chemical_compatibility,
    )
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "perfumery_kb.db"

# ── F11 Chemical Incompatibility Rules (AGENTS.md F11) ────────────────
# These encode known chemical-family incompatibilities between complex
# natural mixtures.  See AGENTS.md "Agent Failure Registry F11".
F11_INCOMPATIBILITIES: list[dict[str, str | float]] = [
    {
        "material_a": "Blue Chamomile EO",
        "material_b": "Rose EO",
        "type": "clash",
        "effect": (
            "Chemically incompatible: azulene/matricine (Blue Chamomile) vs "
            "citronellol/geraniol (Rose) — chemically unrelated families clash"
        ),
        "magnitude": 0.0,
        "source": "AGENTS.md F11",
        "context": "chemical_family_incompatibility",
    },
    {
        "material_a": "Osmanthus Absolute",
        "material_b": "Clove EO",
        "type": "clash",
        "effect": (
            "Chemically incompatible: lactone/\u03b2-ionone (Osmanthus) vs "
            "eugenol/phenylpropanoid (Clove) — chemically unrelated families clash"
        ),
        "magnitude": 0.0,
        "source": "AGENTS.md F11",
        "context": "chemical_family_incompatibility",
    },
    {
        "material_a": "Geranium EO",
        "material_b": "Violet Leaf",
        "type": "clash",
        "effect": (
            "Chemically incompatible: citronellol/geraniol/menthone (Geranium) vs "
            "nonadienal/undecatriene (Violet Leaf) — chemically unrelated families clash"
        ),
        "magnitude": 0.0,
        "source": "AGENTS.md F11",
        "context": "chemical_family_incompatibility",
    },
]


def _get_conn(*, writable: bool = False) -> sqlite3.Connection:
    """Open an immutable query connection or an explicit writable connection."""

    if writable:
        conn = sqlite3.connect(str(_DB_PATH))
    else:
        conn = sqlite3.connect(
            f"file:{_DB_PATH.as_posix()}?mode=ro&immutable=1",
            uri=True,
        )
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _ensure_f11_seeded() -> None:
    """Insert F11 chemical incompatibility rules into the DB if missing.

    Idempotent — checks for existing entries before inserting.
    """
    conn = _get_conn(writable=True)
    try:
        cur = conn.cursor()
        insert_sql = """
            INSERT INTO material_interactions
                (material_a, material_b, type, effect, magnitude, source, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for rule in F11_INCOMPATIBILITIES:
            cur.execute(
                "SELECT id FROM material_interactions "
                "WHERE LOWER(material_a) = LOWER(?) AND LOWER(material_b) = LOWER(?) "
                "AND source = 'AGENTS.md F11'",
                (rule["material_a"], rule["material_b"]),
            )
            if cur.fetchone() is None:
                cur.execute(
                    insert_sql,
                    (
                        rule["material_a"],
                        rule["material_b"],
                        rule["type"],
                        rule["effect"],
                        rule["magnitude"],
                        rule["source"],
                        rule["context"],
                    ),
                )
        conn.commit()
    finally:
        conn.close()


# ── Query API ──────────────────────────────────────────────────────────


def get_interaction(material_a: str, material_b: str) -> list[dict]:
    """Return all interactions between *material_a* and *material_b*.

    Searches both directions (A\u00d7B and B\u00d7A) and returns results
    ordered by descending magnitude.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions WHERE "
            "(LOWER(material_a) = LOWER(?) AND LOWER(material_b) = LOWER(?)) "
            "OR (LOWER(material_a) = LOWER(?) AND LOWER(material_b) = LOWER(?)) "
            "ORDER BY magnitude DESC",
            (material_a, material_b, material_b, material_a),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_all_interactions(material: str) -> list[dict]:
    """Return all interactions involving *material* (as either A or B).

    Results grouped by type, ordered by descending magnitude within each type.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions "
            "WHERE LOWER(material_a) = LOWER(?) OR LOWER(material_b) = LOWER(?) "
            "ORDER BY type, magnitude DESC",
            (material, material),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_synergies(material: str) -> list[dict]:
    """Return only synergy-type interactions for *material*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions WHERE "
            "(LOWER(material_a) = LOWER(?) OR LOWER(material_b) = LOWER(?)) "
            "AND type = 'synergy' ORDER BY magnitude DESC",
            (material, material),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_clashes(material: str) -> list[dict]:
    """Return only clash/conflict-type interactions for *material*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions WHERE "
            "(LOWER(material_a) = LOWER(?) OR LOWER(material_b) = LOWER(?)) "
            "AND type IN ('conflict', 'clash') ORDER BY magnitude DESC",
            (material, material),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_replacements(material: str) -> list[dict]:
    """Return replacement-type interactions for *material*.

    The existing database uses ``type = 'rejection'`` to encode replacement
    warnings (e.g. "use one or the other, not both").
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions WHERE "
            "(LOWER(material_a) = LOWER(?) OR LOWER(material_b) = LOWER(?)) "
            "AND type = 'rejection' ORDER BY magnitude DESC",
            (material, material),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Mutation API ───────────────────────────────────────────────────────


def add_interaction(
    material_a: str,
    material_b: str,
    type_: str,
    effect: str,
    magnitude: float,
    source: str,
    context: str,
) -> int:
    """Insert a new interaction and return its auto-generated id.

    Parameters
    ----------
    material_a : str
        First material name.
    material_b : str
        Second material name.
    type_ : str
        Interaction type (e.g. ``'synergy'``, ``'clash'``, ``'conflict'``,
        ``'pairing'``, ``'rejection'``).
    effect : str
        Human-readable description of the interaction effect.
    magnitude : float
        Strength / importance score (higher = stronger).
    source : str
        Attribution source (e.g. ``'AGENTS.md F11'``).
    context : str
        Machine-readable context tag (e.g. ``'chemical_family_incompatibility'``).
    """
    conn = _get_conn(writable=True)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO material_interactions "
            "(material_a, material_b, type, effect, magnitude, source, context) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (material_a, material_b, type_, effect, magnitude, source, context),
        )
        conn.commit()
        row_id = cur.lastrowid
        if row_id is None:
            raise RuntimeError("SQLite did not return an interaction row id.")
        return row_id
    finally:
        conn.close()


# ── Analysis API ───────────────────────────────────────────────────────


def get_coverage_stats() -> dict:
    """Return coverage statistics for the interaction graph.

    Returns
    -------
    dict
        Keys: ``total_possible_pairs``, ``covered_pairs``, ``coverage_pct``,
        ``distinct_materials``, ``total_interactions``, ``by_type``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Distinct materials that appear in interactions
        cur.execute(
            "SELECT DISTINCT material_a FROM material_interactions "
            "UNION SELECT DISTINCT material_b FROM material_interactions"
        )
        all_materials = [r[0] for r in cur.fetchall()]
        n = len(all_materials)

        # Total possible undirected pairs given N materials
        total_possible = n * (n - 1) // 2 if n >= 2 else 0

        # Distinct covered undirected pairs (normalise order via CASE)
        cur.execute(
            "SELECT COUNT(*) FROM ( "
            "  SELECT DISTINCT "
            "    CASE WHEN material_a < material_b THEN material_a ELSE material_b END, "
            "    CASE WHEN material_a < material_b THEN material_b ELSE material_a END "
            "  FROM material_interactions "
            ")"
        )
        covered_pairs = int(cur.fetchone()[0])

        coverage_pct = (
            round(covered_pairs / total_possible * 100, 2)
            if total_possible > 0
            else 0.0
        )

        # Breakdown by type
        cur.execute(
            "SELECT type, COUNT(*) FROM material_interactions GROUP BY type "
            "ORDER BY COUNT(*) DESC"
        )
        by_type: dict[str, int] = {str(r[0]): int(r[1]) for r in cur.fetchall()}

        return {
            "total_possible_pairs": total_possible,
            "covered_pairs": covered_pairs,
            "coverage_pct": coverage_pct,
            "distinct_materials": n,
            "total_interactions": sum(by_type.values()),
            "by_type": by_type,
        }
    finally:
        conn.close()


def get_incompatible_naturals() -> list[dict]:
    """Return all F11 chemical incompatibility rules from the database.

    These are ``clash``-type interactions with ``source = 'AGENTS.md F11'``.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM material_interactions "
            "WHERE source = 'AGENTS.md F11' ORDER BY material_a"
        )
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def check_chemical_compatibility(material_a: str, material_b: str) -> dict:
    """Check whether two materials have a known chemical incompatibility.

    First consults the hardcoded F11 incompatibility rules, then falls back
    to querying the database for ``clash`` / ``conflict`` entries between the
    pair.

    Returns
    -------
    dict
        ``{"compatible": bool, "reason": str | None, "source": str | None}``.
    """
    a_lower = material_a.lower()
    b_lower = material_b.lower()

    # 1. Check hardcoded F11 rules (always available)
    for rule in F11_INCOMPATIBILITIES:
        rule_a = str(rule["material_a"]).lower()
        rule_b = str(rule["material_b"]).lower()
        if (a_lower == rule_a and b_lower == rule_b) or (
            a_lower == rule_b and b_lower == rule_a
        ):
            return {
                "compatible": False,
                "reason": str(rule["effect"]),
                "source": str(rule["source"]),
            }

    # 2. Check database for any clash/conflict between this pair
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT effect, source FROM material_interactions WHERE "
            "((LOWER(material_a) = LOWER(?) AND LOWER(material_b) = LOWER(?)) "
            "OR (LOWER(material_a) = LOWER(?) AND LOWER(material_b) = LOWER(?))) "
            "AND type IN ('clash', 'conflict')",
            (material_a, material_b, material_b, material_a),
        )
        row = cur.fetchone()
        if row is not None:
            return {
                "compatible": False,
                "reason": str(row["effect"]),
                "source": str(row["source"]),
            }
    finally:
        conn.close()

    return {"compatible": True, "reason": None, "source": None}
