"""The release CLI rolls HOLD up as its own verdict and exits 1 on it."""

from __future__ import annotations

import dataclasses
import json

import pytest

import scripts.formula_release_gate as release_cli

FORMULA = """# CLI Formula

| Material | Dilution | uL |
|---|---|---:|
| Hedione | neat | 100 |
"""


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [("PASS", 0), ("WARN", 0), ("HOLD", 1), ("FAIL", 1)],
)
def test_release_cli_verdict_and_exit_code_follow_the_worst_gate(
    tmp_path, capsys, monkeypatch, status, exit_code
):
    real_gate_formula = release_cli.gate_formula

    def gate_with_one_status(formula, config, **kwargs):
        report = real_gate_formula(formula, config, **kwargs)
        gates = tuple(
            dataclasses.replace(g, status=status if g.gate == "phase_compatibility" else "PASS")
            for g in report.gates
        )
        return dataclasses.replace(report, status=status, gates=gates)

    monkeypatch.setattr(release_cli, "gate_formula", gate_with_one_status)
    path = tmp_path / "cli.md"
    path.write_text(FORMULA, encoding="utf-8")

    rc = release_cli.main(
        [
            "--formula-file",
            str(path),
            "--expected-concentrate-ul",
            "100",
            "--brief",
            "generic",
            "--no-audit",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["overall"] == status
    assert rc == exit_code
