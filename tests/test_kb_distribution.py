"""#4 KB distribution: the gitignored SQLite KB must be provisionable/reproducible.

``data/perfumery_kb.db`` is a generated artifact (gitignored ``*.db``), so a fresh
clone has none. ``tests/conftest.py`` provisions it on demand and
``scripts/build_perfumery_kb_db.py`` builds it explicitly. These tests assert the
live DB is present with the expected tables and that it can be rebuilt from the
source stores.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "perfumery_kb.db"

REQUIRED_TABLES = {
    "materials",
    "material_aliases",
    "family_archetypes",
    "pyramid_ratios",
    "oav_targets",
    "ifra_limits",
    "theory_rules",
    "ingredient_catalog",
}


def _tables(path: Path | str) -> set[str]:
    con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
    try:
        return {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    finally:
        con.close()


def test_live_kb_is_present_with_required_tables():
    assert KB_PATH.exists(), "data/perfumery_kb.db missing; conftest should provision it"
    assert REQUIRED_TABLES <= _tables(KB_PATH)


def test_live_kb_has_material_rows():
    con = sqlite3.connect(f"file:{KB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        count = con.execute("select count(*) from materials").fetchone()[0]
    finally:
        con.close()
    assert count > 100


def test_kb_is_reproducible_from_source():
    from engine.kb_migrate import migrate

    tmp = tempfile.mktemp(suffix=".db", prefix="perfumery_kb_repro_")
    try:
        built = migrate(tmp)
        assert REQUIRED_TABLES <= _tables(built)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
