"""Verification-layer invariants.

Assigned to the ``truth-core`` engine shard in ``engine/project_verification.py``.

Invariant 1 - EOL stability. Every repository path that a frozen hash pin
compares against must be materialised with bytes that do not depend on the
checkout's line-ending policy: ``.gitattributes`` must give it ``eol=lf``, or
``-text`` so git copies the blob verbatim. Without that, a pin captured on one
workstation passes there and fails on a Linux clone - which is exactly the
defect this file exists to catch.

Out of scope, deliberately: this test does not check that a pinned value is
*reproducible* from repository history, and it does not check symbol/line or
call-edge token pins. A green run here means "the pinned bytes are
platform-stable", not "the pinned values are correct".
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# Pin discovery. Each extractor follows the pin's own fields rather than
# regexing the repository for filenames.
# --------------------------------------------------------------------------


def _c0_inventory_pins(root: Path) -> dict[str, list[str]]:
    payload = json.loads(
        (root / "docs/verification/c0/physical_model_inventory.json").read_text(encoding="utf-8")
    )
    pins: dict[str, list[str]] = {}
    for record in payload["implementations"]:
        record_id = record.get("id", "<unknown>")
        for relative in record.get("source_sha256") or {}:
            pins.setdefault(relative, []).append(f"c0_inventory[{record_id}].source_sha256")
    return pins


def _c0_legacy_fixture_pins(root: Path) -> dict[str, list[str]]:
    payload = json.loads(
        (root / "tests/fixtures/c0_legacy_physical_model_cases.json").read_text(encoding="utf-8")
    )
    pins: dict[str, list[str]] = {}
    for case in payload["cases"]:
        case_id = case.get("id", "<unknown>")
        for relative in case.get("source_sha256") or {}:
            pins.setdefault(relative, []).append(f"c0_legacy_fixture[{case_id}].source_sha256")
    for sidecar_pinned in (
        "tests/fixtures/c0_legacy_physical_model_cases.json",
        "tests/fixtures/c0_legacy_physical_model_cases.sha256",
    ):
        pins.setdefault(sidecar_pinned, []).append("c0_legacy_fixture.sha256 sidecar")
    return pins


def _d0_pins(root: Path) -> dict[str, list[str]]:
    source = (root / "scripts/verify_d0_claim_matrix.py").read_text(encoding="utf-8")
    pins: dict[str, list[str]] = {}
    for constant in ("CONTROL_RELATIVE", "INTERVENTION_RELATIVE"):
        match = re.search(rf'{constant}\s*=\s*Path\(\s*"([^"]+)"', source)
        assert match is not None, f"could not locate {constant} in verify_d0_claim_matrix.py"
        pins.setdefault(match.group(1), []).append(f"verify_d0_claim_matrix.{constant}")
    return pins


def _complexity_registry_pins(root: Path) -> dict[str, list[str]]:
    pins: dict[str, list[str]] = {}
    base_rel = "configs/complexity/complexity_module_registry_v1.json"
    base = json.loads((root / base_rel).read_text(encoding="utf-8"))
    for module in base["modules"]:
        pins.setdefault(module["path"], []).append(f"complexity_registry_v1[{module['module_id']}]")
    pins.setdefault(base_rel, []).append("complexity_registry_v1.frozen-registry-bytes")
    overlay_rel = "configs/complexity/complexity_module_registry_integration_20260910.json"
    overlay = json.loads((root / overlay_rel).read_text(encoding="utf-8"))
    pins.setdefault(overlay["base_registry"], []).append("complexity_overlay.base_registry_sha256")
    for addition in overlay.get("module_additions", []):
        pins.setdefault(addition["path"], []).append(
            f"complexity_overlay[{addition['module_id']}]"
        )
    return pins


def _c5_pins(root: Path) -> dict[str, list[str]]:
    source = (root / "engine/physics/calibration_program.py").read_text(encoding="utf-8")
    assert "C5_INVENTORY_SHA256" in source, "C5_INVENTORY_SHA256 vanished from calibration_program.py"
    # tests/test_c5_calibration_program.py hashes ROOT/"inventory.txt" against that constant.
    return {"inventory.txt": ["calibration_program.C5_INVENTORY_SHA256"]}


def _backend_identity_pins(root: Path) -> dict[str, list[str]]:
    relative = "backend/tests/fixtures/b4_identity_resolution_baseline.json"
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    pins: dict[str, list[str]] = {relative: [f"{relative}: frozen fixture bytes"]}
    for corpus in payload.get("source_corpus_sha256", {}):
        pins.setdefault(corpus, []).append(f"{relative}.source_corpus_sha256")
    return pins


def collect_pinned_paths(root: Path = ROOT) -> dict[str, list[str]]:
    """Map every byte-pinned repository path to the stores that pin it."""
    pins: dict[str, list[str]] = {}
    for extractor in (
        _c0_inventory_pins,
        _c0_legacy_fixture_pins,
        _d0_pins,
        _complexity_registry_pins,
        _c5_pins,
        _backend_identity_pins,
    ):
        for path, stores in extractor(root).items():
            pins.setdefault(path, []).extend(stores)
    return pins


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _git_attributes(root: Path, paths: list[str]) -> dict[str, dict[str, str]]:
    """Resolve `text` and `eol` for each path exactly as git would."""
    proc = subprocess.run(
        ["git", "-C", str(root), "check-attr", "text", "eol", "--", *paths],
        capture_output=True,
        text=True,
        check=True,
    )
    resolved: dict[str, dict[str, str]] = {path: {} for path in paths}
    for line in proc.stdout.splitlines():
        # "<path>: <attr>: <value>"; paths in these stores contain no ": ".
        path, attribute, value = line.split(": ", 2)
        resolved.setdefault(path, {})[attribute] = value
    return resolved


def _is_eol_stable(attributes: dict[str, str]) -> bool:
    """`eol=lf` pins the checkout; `-text` copies the blob verbatim."""
    return attributes.get("eol") == "lf" or attributes.get("text") == "unset"


def _engine_test_shards(root: Path) -> dict[str, list[str]]:
    """Read `_ENGINE_TEST_SHARDS` without importing the engine package."""
    source = (root / "engine/project_verification.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_ENGINE_TEST_SHARDS"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    pytest.fail("_ENGINE_TEST_SHARDS not found in engine/project_verification.py")


# --------------------------------------------------------------------------
# Invariant 1
# --------------------------------------------------------------------------


def test_every_pinned_path_is_eol_stable() -> None:
    pins = collect_pinned_paths()
    assert pins, "pin discovery returned nothing - the extractors are broken"

    present = sorted(path for path in pins if (ROOT / path).exists())
    missing = sorted(path for path in pins if not (ROOT / path).exists())
    attributes = _git_attributes(ROOT, present)

    unstable = {
        path: (attributes.get(path, {}), pins[path])
        for path in present
        if not _is_eol_stable(attributes.get(path, {}))
    }

    if unstable:
        detail = "\n".join(
            f"  {path}\n    attrs={attrs}  pinned by={sorted(set(stores))}"
            for path, (attrs, stores) in sorted(unstable.items())
        )
        raise AssertionError(
            f"{len(unstable)} pinned path(s) have no checkout-stable line endings.\n"
            f"Add `<path> text eol=lf` to .gitattributes for each:\n{detail}"
        )

    if missing:
        raise AssertionError(
            "pinned paths absent from the checkout (pin cannot be verified at all):\n  "
            + "\n  ".join(missing)
        )


# --------------------------------------------------------------------------
# Invariant 2
# --------------------------------------------------------------------------

def test_every_test_file_is_assigned_to_exactly_one_engine_shard() -> None:
    shards = _engine_test_shards(ROOT)
    assignment: dict[str, list[str]] = {}
    for shard, files in shards.items():
        for relative in files:
            assignment.setdefault(relative, []).append(shard)

    on_disk = {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").glob("test_*.py")
    }

    unassigned = sorted(on_disk - set(assignment))
    duplicated = {path: names for path, names in assignment.items() if len(names) > 1}
    ghosts = sorted(set(assignment) - on_disk)

    problems = []
    if unassigned:
        problems.append("on disk but in no shard: " + ", ".join(unassigned))
    if duplicated:
        problems.append(
            "in more than one shard: "
            + ", ".join(f"{path} -> {names}" for path, names in sorted(duplicated.items()))
        )
    if ghosts:
        problems.append("in a shard but not on disk: " + ", ".join(ghosts))
    assert not problems, "\n".join(problems)
