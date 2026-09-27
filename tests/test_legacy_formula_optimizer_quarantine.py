"""Legacy formula-specific optimizers must not write from diagnostic totals."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "scripts.optimize_cobalt_cedar_air",
        "scripts.optimize_orris_damascone_deep_luxury",
    ],
)
def test_legacy_formula_optimizer_entrypoint_is_quarantined(
    module_name: str, tmp_path, monkeypatch
) -> None:
    module = importlib.import_module(module_name)
    output_path = tmp_path / "must-not-be-written.md"
    monkeypatch.setattr(module, "OUTPUT_PATH", output_path)

    with pytest.raises(SystemExit, match="BLOCKED: legacy heuristic totals"):
        module.main()

    assert not output_path.exists()
