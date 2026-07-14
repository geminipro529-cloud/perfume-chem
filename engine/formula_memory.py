# allow: SIZE_OK — query layer

"""
Formula memory API for storing and retrieving perfume formulas.

Provides CRUD operations on the ``formulas``, ``formula_materials``,
``pipeline_results``, ``evaluations``, and ``failures`` tables in the
perfumery knowledge base.

Usage:
    from engine.formula_memory import save_formula, get_formula
    fid = save_formula("formulas/My_Formula.md")
    formula = get_formula(fid)
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Database path resolution
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DB_PATH = str(_PROJECT_ROOT / "data" / "perfumery_kb.db")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    """Open a read-write connection to the formula memory database."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a sqlite3.Row to a plain dict, or return None."""
    if row is None:
        return None
    return dict(row)


def _fetchone_dict(
    cur: sqlite3.Cursor, sql: str, params: tuple = ()
) -> dict[str, Any] | None:
    """Execute a query and return the first result as a dict, or None."""
    cur.execute(sql, params)
    row = cur.fetchone()
    return _row_to_dict(row)


def _fetchall_dicts(
    cur: sqlite3.Cursor, sql: str, params: tuple = ()
) -> list[dict[str, Any]]:
    """Execute a query and return all results as a list of dicts."""
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Formula management
# ---------------------------------------------------------------------------


def save_formula(formula_path: str) -> int:
    """Parse a formula ``.md`` file, extract metadata + materials, save to DB.

    Returns the newly inserted formula ID.

    The file format follows the convention in
    ``formulas/L_Homme_Luxe_30mL_EdP.md``:

    - ``# Title`` on the first line  → *name*
    - ``**Date**`` line             → *date*
    - ``**Family archetype**`` line → *family_archetype*
    - ``**Batch size**`` line       → *batch_size_ml*
    - ``**Concentration**`` line    → *concentrate_ul*
    - ``**Status**`` line           → *status*
    - ``## Design Lock`` section    → *rationale* (first paragraph)
    - Table rows matching ``| # | Ingredient | Dil | uL | mL | Role |``
    """
    with open(formula_path, "r", encoding="utf-8-sig") as fh:
        text = fh.read()
    lines = text.split("\n")

    # ── Extract metadata ────────────────────────────────────────────
    name = ""
    date = ""
    family_archetype = ""
    batch_size_ml: float | None = None
    concentrate_ul: int | None = None
    status = ""

    for line in lines:
        stripped = line.strip()

        # Name: first line starting with "# " (but not "## ")
        if stripped.startswith("# ") and not stripped.startswith("## "):
            name = stripped[2:].strip()

        # Date
        if "**Date**" in stripped:
            m = re.search(r"\*\*Date\*\*\s*:?\s*(.*)", stripped)
            if m:
                date = m.group(1).strip().rstrip(" \t")

        # Family archetype
        if "Family archetype" in stripped:
            m = re.search(r"\*\*Family archetype:\*\*\s*(.*)", stripped)
            if m:
                family_archetype = m.group(1).strip().strip("`").strip()

        # Batch size (mL)
        if "**Batch size**" in stripped:
            m = re.search(r"([\d.]+)\s*mL", stripped)
            if m:
                batch_size_ml = float(m.group(1))

        # Concentration (µL)
        if "**Concentration**" in stripped:
            m = re.search(r"([\d,]+)\s*uL\s*concentrate", stripped)
            if m:
                concentrate_ul = int(m.group(1).replace(",", ""))

        # Status
        if "**Status**" in stripped:
            m = re.search(r"\*\*Status\*\*\s*:?\s*(.*)", stripped)
            if m:
                status = m.group(1).strip().rstrip(" \t")

    # ── Rationale from Design Lock section ──────────────────────────
    rationale = ""
    in_design_lock = False
    paragraphs: list[list[str]] = []
    current_para: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "## Design Lock":
            in_design_lock = True
            continue
        if not in_design_lock:
            continue
        # Stop at next section header or separator
        if stripped.startswith("## ") or stripped == "---":
            break

        if stripped == "":
            if current_para:
                paragraphs.append(current_para)
                current_para = []
        else:
            current_para.append(stripped)

    if current_para:
        paragraphs.append(current_para)

    if paragraphs:
        rationale = " ".join(paragraphs[0])

    # ── Parse material table rows (only inside ## Formula section) ──
    materials: list[dict[str, Any]] = []
    in_formula_section = False

    for line in lines:
        stripped = line.strip()

        # Enter / exit the formula table section
        if stripped == "## Formula":
            in_formula_section = True
            continue
        if not in_formula_section:
            continue
        # Exit on next section header or horizontal rule
        if stripped.startswith("## ") or stripped == "---":
            break

        parts = [p.strip() for p in line.split("|")]
        # Expected: '' | '#'/'N' | 'Ingredient' | 'Dil' | 'uL' | 'mL' | 'Role' | ''
        if len(parts) < 7:
            continue
        try:
            int(parts[1])  # validate it's a number
        except ValueError:
            continue  # skip header (contains '#') and total row

        materials.append(
            {
                "material_name": parts[2],
                "dilution": parts[3],
                "amount_ul": float(parts[4].replace(",", "")),
                "role": parts[6],
            }
        )

    # ── Persist ─────────────────────────────────────────────────────
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO formulas
               (name, date, family_archetype, batch_size_ml,
                concentrate_ul, status, file_path, rationale)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                date,
                family_archetype,
                batch_size_ml,
                concentrate_ul,
                status,
                formula_path,
                rationale,
            ),
        )
        formula_id: int = cur.lastrowid  # type: ignore[assignment]

        for mat in materials:
            cur.execute(
                """INSERT INTO formula_materials
                   (formula_id, material_name, dilution, amount_ul, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    formula_id,
                    mat["material_name"],
                    mat["dilution"],
                    mat["amount_ul"],
                    mat["role"],
                ),
            )

        conn.commit()
        return formula_id
    finally:
        conn.close()


def get_formula(formula_id: int) -> dict[str, Any] | None:
    """Return a formula dict (including a ``materials`` list) or ``None``."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        formula = _fetchone_dict(
            cur, "SELECT * FROM formulas WHERE id = ?", (formula_id,)
        )
        if formula is None:
            return None

        materials = _fetchall_dicts(
            cur,
            "SELECT material_name, dilution, amount_ul, role "
            "FROM formula_materials WHERE formula_id = ? ORDER BY id",
            (formula_id,),
        )
        formula["materials"] = materials
        return formula
    finally:
        conn.close()


def list_formulas(family: str | None = None) -> list[dict[str, Any]]:
    """List all formulas, optionally filtered by *family*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if family:
            return _fetchall_dicts(
                cur,
                "SELECT * FROM formulas WHERE family_archetype = ? ORDER BY id",
                (family,),
            )
        return _fetchall_dicts(cur, "SELECT * FROM formulas ORDER BY id")
    finally:
        conn.close()


def search_formulas(
    material: str | None = None,
    family: str | None = None,
    rating_min: int | None = None,
) -> list[dict[str, Any]]:
    """Search formulas by contained *material*, *family*, or minimum rating.

    All supplied criteria are AND-ed.  Returns distinct formula rows.
    """
    base = "SELECT DISTINCT f.* FROM formulas f"
    joins: list[str] = []
    conditions: list[str] = []
    params: list[Any] = []

    if material is not None:
        joins.append("JOIN formula_materials fm ON f.id = fm.formula_id")
        conditions.append("fm.material_name LIKE ?")
        params.append(f"%{material}%")

    if family is not None:
        conditions.append("f.family_archetype = ?")
        params.append(family)

    if rating_min is not None:
        joins.append("JOIN evaluations e ON f.id = e.formula_id")
        conditions.append("e.rating >= ?")
        params.append(rating_min)

    sql = base
    if joins:
        sql += " " + " ".join(joins)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY f.id"

    conn = _get_conn()
    try:
        cur = conn.cursor()
        return _fetchall_dicts(cur, sql, tuple(params))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pipeline results
# ---------------------------------------------------------------------------


def save_pipeline_result(formula_id: int, json_path: str) -> int:
    """Read a pipeline JSON output and save each gate result.

    Expected JSON structure::

        {"formulas": [{"gates": [{"gate": "...", "status": "...", "detail": "..."}]}]}

    Returns the number of gate rows saved.
    """
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    gates: list[dict[str, Any]] = []
    for fe in data.get("formulas", []):
        gates.extend(fe.get("gates", []))

    conn = _get_conn()
    try:
        cur = conn.cursor()
        for g in gates:
            detail = g.get("detail", "")
            if not isinstance(detail, str):
                detail = json.dumps(detail, ensure_ascii=False)
            cur.execute(
                "INSERT INTO pipeline_results (formula_id, gate_name, status, detail) "
                "VALUES (?, ?, ?, ?)",
                (formula_id, g.get("gate", ""), g.get("status", ""), detail),
            )
        conn.commit()
        return len(gates)
    finally:
        conn.close()


def get_pipeline_result(formula_id: int) -> list[dict[str, Any]]:
    """Return all gate results for *formula_id*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        return _fetchall_dicts(
            cur,
            "SELECT gate_name, status, detail FROM pipeline_results "
            "WHERE formula_id = ? ORDER BY id",
            (formula_id,),
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------


def save_evaluation(
    formula_id: int,
    rating: int,
    feedback_text: str,
    feedback_tags: list[str],
) -> int:
    """Save an evaluation record.  Returns the evaluation ID."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO evaluations (formula_id, rating, feedback_text, feedback_tags_json) "
            "VALUES (?, ?, ?, ?)",
            (
                formula_id,
                rating,
                feedback_text,
                json.dumps(feedback_tags, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_evaluations(formula_id: int) -> list[dict[str, Any]]:
    """Return all evaluations for *formula_id*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        rows = _fetchall_dicts(
            cur,
            "SELECT id, rating, feedback_text, feedback_tags_json "
            "FROM evaluations WHERE formula_id = ? ORDER BY id",
            (formula_id,),
        )
        for r in rows:
            if isinstance(r.get("feedback_tags_json"), str):
                try:
                    r["feedback_tags"] = json.loads(r["feedback_tags_json"])
                except (json.JSONDecodeError, TypeError):
                    r["feedback_tags"] = []
            else:
                r["feedback_tags"] = []
        return rows
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Failures
# ---------------------------------------------------------------------------


def add_failure(
    formula_id: int,
    symptom: str,
    root_cause: str,
    fix: str,
    learning: str,
    applicable_materials: list[str],
) -> int:
    """Record a failure analysis entry.  Returns the failure ID."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO failures (formula_id, symptom, root_cause, fix, learning, "
            "applicable_materials_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                formula_id,
                symptom,
                root_cause,
                fix,
                learning,
                json.dumps(applicable_materials, ensure_ascii=False),
            ),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_failures(formula_id: int | None = None) -> list[dict[str, Any]]:
    """Return failure records, optionally filtered by *formula_id*."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        if formula_id is not None:
            rows = _fetchall_dicts(
                cur,
                "SELECT * FROM failures WHERE formula_id = ? ORDER BY id",
                (formula_id,),
            )
        else:
            rows = _fetchall_dicts(cur, "SELECT * FROM failures ORDER BY id")

        for r in rows:
            raw = r.get("applicable_materials_json")
            if isinstance(raw, str):
                try:
                    r["applicable_materials"] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    r["applicable_materials"] = []
            else:
                r["applicable_materials"] = []
        return rows
    finally:
        conn.close()
