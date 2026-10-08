"""ifra_constraints, the KB seed and ifra_checker read one sourced IFRA table."""

from __future__ import annotations

import sqlite3

import pytest

from engine.ifra_standards import load_ifra_table


@pytest.fixture(scope="module")
def table():
    return load_ifra_table()


def test_table_is_the_reference(table) -> None:
    assert table.lookup("Coumarin").cat4_limit_pct == 1.5
    assert table.lookup("Hydroxycitronellal").cat4_limit_pct == 2.1
    assert table.lookup("Lilial").status == "prohibited"


def test_ifra_constraints_agrees_with_table() -> None:
    from engine.ifra_constraints import IFRA_CAT4_LIMITS, compute_ifra_windows

    assert IFRA_CAT4_LIMITS["coumarin"] == (1.5, 6.0)
    assert IFRA_CAT4_LIMITS["hydroxycitronellal"] == pytest.approx((2.1, 8.4))
    assert IFRA_CAT4_LIMITS["butylphenyl methylpropional"] == (0.0, 0.0)

    result = compute_ifra_windows(["coumarin", "butylphenyl methylpropional"])
    windows = {w.allergen_name: w for w in result.windows}
    assert windows["coumarin"].max_pct == 6.0
    assert windows["butylphenyl methylpropional"].max_pct == 0.0
    assert windows["butylphenyl methylpropional"].ifra_restricted is True
    assert result.unchecked_allergens == []


def test_ifra_constraints_reports_unknown_allergen_unchecked() -> None:
    from engine.ifra_constraints import compute_ifra_windows

    result = compute_ifra_windows(["coumarin", "newly regulated constituent"])
    assert result.unchecked_allergens == ["newly regulated constituent"]


def test_kb_seed_agrees_with_table(tmp_path, table) -> None:
    from engine.kb_migrate import _populate_safety
    from engine.kb_schema import create_database

    db = create_database(str(tmp_path / "kb.db"))
    conn = sqlite3.connect(db)
    try:
        _populate_safety(conn)
        limits = dict(conn.execute("SELECT material_name, cat4_limit_pct FROM ifra_limits"))
        banned = dict(conn.execute("SELECT material_name, reason FROM banned_materials"))
    finally:
        conn.close()

    assert limits["Coumarin"] == 1.5
    assert limits["Hydroxycitronellal"] == 2.1
    assert "Lilial" not in limits
    assert "Linalool" not in limits
    assert limits == table.cat4_limits()
    assert "IFRA 51st Amendment prohibition" in banned["Lilial"]


def test_ifra_checker_agrees_with_table() -> None:
    from engine.ifra_checker import check_formula_ifra

    # 100 uL neat in a 1000 uL concentrate at 10% -> 1.0% of finished product.
    report = check_formula_ifra(
        [("Coumarin", 100, 1.0), ("Hydroxycitronellal", 100, 1.0), ("Lilial", 100, 1.0)],
        total_volume_ul=1000,
        concentration_pct=10.0,
    )
    ok = {row["material"]: row["limit_pct"] for row in report["ok_materials"]}
    violations = {row["material"]: row["limit_pct"] for row in report["violations"]}
    assert ok == {"Coumarin": 1.5, "Hydroxycitronellal": 2.1}
    assert violations == {"Lilial": 0.0}

    # Specification-only (no numeric limit) is reported as having no limit.
    spec = check_formula_ifra([("Linalool", 100, 1.0)], 1000, 10.0)
    assert spec["warnings"] == ["Linalool"]
