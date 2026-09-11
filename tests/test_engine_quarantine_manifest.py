"""Enforce the engine quarantine manifest.

Quarantined modules are dead (no runtime use). This test fails if:
  * a quarantined path is deleted or moved without updating the manifest,
  * a quarantined file loses its QUARANTINED banner,
  * runtime code (engine/scripts/backend/future_modules/tools + root) starts
    importing or referencing a quarantined module.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "governance" / "engine_quarantine_manifest_20260911.json"
BANNER_MARKER = "# QUARANTINED 2026-09-11"

SKIP_PARTS = {"__pycache__", ".venv", ".venv_py311_a0", "venv", "node_modules",
              "build", "dist", ".git", ".mypy_cache", ".ruff_cache", ".pytest_cache"}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _skipped(p: Path) -> bool:
    return any(part in SKIP_PARTS for part in p.parts)


def _runtime_py_files():
    roots = ["engine", "scripts", "backend", "future_modules", "tools"]
    files = []
    for r in roots:
        base = ROOT / r
        if base.exists():
            files += [p for p in base.rglob("*.py") if not _skipped(p)]
    files += [p for p in ROOT.glob("*.py")]
    return files


def test_quarantine_manifest_is_well_formed():
    data = _manifest()
    assert data["schema_version"] == "engine_quarantine_manifest_v1"
    assert data["quarantined"], "manifest has no quarantined entries"
    assert all(entry["do_not_develop"] is True for entry in data["quarantined"])
    assert all(entry["do_not_develop"] is True for entry in data["already_retired"])


def test_quarantined_paths_exist_and_are_bannered():
    for entry in _manifest()["quarantined"]:
        path = ROOT / entry["path"]
        assert path.exists(), f"missing quarantined path: {entry['path']}"
        head = path.read_text(encoding="utf-8", errors="replace")[:400]
        assert BANNER_MARKER in head, f"missing quarantine banner: {entry['path']}"


def test_no_runtime_reference_to_quarantined_modules():
    quarantined = _manifest()["quarantined"]
    patterns = []
    for entry in quarantined:
        dotted = entry["module"]           # e.g. engine.calibration.state_diff
        leaf = dotted.split(".")[-1]
        parent = ".".join(dotted.split(".")[:-1])
        patterns.append(re.compile(r"\b" + re.escape(dotted) + r"\b"))
        patterns.append(
            re.compile(r"from\s+" + re.escape(parent) + r"\s+import\s+[^\n]*\b" + re.escape(leaf) + r"\b")
        )
        patterns.append(re.compile(r"\bimport\s+" + re.escape(parent) + r"\." + re.escape(leaf) + r"\b"))

    quarantined_paths = {(ROOT / e["path"]).resolve() for e in quarantined}
    offenders = []
    for f in _runtime_py_files():
        if f.resolve() in quarantined_paths:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if any(pat.search(text) for pat in patterns):
            offenders.append(str(f.relative_to(ROOT)).replace("\\", "/"))
    assert not offenders, f"runtime code references quarantined modules: {offenders}"


def test_already_retired_entries_are_registry_retired():
    registry = json.loads(
        (ROOT / "configs" / "complexity" / "complexity_module_registry_v1.json").read_text(encoding="utf-8")
    )
    states = {m["module_id"]: m["state"] for m in registry["modules"]}
    for entry in _manifest()["already_retired"]:
        module_id = entry["module_id"]
        path = ROOT / entry["path"]
        assert path.exists(), f"missing retired path: {entry['path']}"
        if module_id in states:
            if "integration_v1_state" in entry:
                # Retired in the root registry v2 but still a future candidate here.
                assert states[module_id] == entry["integration_v1_state"], module_id
            else:
                assert states[module_id] == "RETIRED_BENCHMARK_UNDERPERFORMER", module_id
