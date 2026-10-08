"""The release gate reads each formula's bottle size instead of assuming 30 mL."""

from __future__ import annotations

import json

import pytest

import scripts.formula_release_gate as release_cli
from scripts.formula_release_gate import resolve_batch_volume

FORMULA = """# Soliflore Test

| Material | Dilution | uL |
|---|---|---:|
| Hedione | neat | 100 |
"""


def test_title_volume_is_read():
    vol, source, matched = resolve_batch_volume(
        None, "F2 — Fougère Herbier · 30 mL Finished EDP", "formulas/x.md"
    )
    assert (vol, source) == (30.0, "formula_title")
    assert matched and "30" in matched


def test_filename_volume_used_when_title_silent():
    vol, source, matched = resolve_batch_volume(
        None, "Osmanthus Soliflore", "formulas/Osmanthus_Soliflore_10mL_EdT.md"
    )
    assert (vol, source) == (10.0, "formula_filename")
    assert matched and "10" in matched


@pytest.mark.parametrize(("title", "expected"), [("2.5 mL test", 2.5), ("5 mL pilot", 5.0)])
def test_small_and_decimal_volumes(title, expected):
    vol, source, _ = resolve_batch_volume(None, title, "formulas/x.md")
    assert (vol, source) == (expected, "formula_title")


def test_cli_value_wins_over_title():
    assert resolve_batch_volume(15.0, "Thing 30 mL EDP", "formulas/x.md") == (15.0, "cli", None)


def test_default_when_nothing_found():
    assert resolve_batch_volume(None, "Plain title", "formulas/plain.md") == (
        30.0,
        "default",
        None,
    )


def test_microlitres_are_not_millilitres():
    assert resolve_batch_volume(None, "6000 uL concentrate", "formulas/x.md") == (
        30.0,
        "default",
        None,
    )


def test_cli_gate_run_reads_volume_from_filename(tmp_path, capsys):
    path = tmp_path / "Soliflore_10mL_EdT.md"
    path.write_text(FORMULA, encoding="utf-8")
    release_cli.main(
        [
            "--formula-file",
            str(path),
            "--expected-concentrate-ul",
            "100",
            "--brief",
            "generic",
            "--no-audit",
            "--no-append-analysis",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    summary = payload["formulas"][0]["config_summary"]
    assert summary["batch_volume_ml"] == 10
    assert summary["batch_volume_source"] == "formula_filename"
