"""material_properties.json must carry the physics the release gate reads.

Preflight, the release-gate script and the material validator read this cache,
while formula state reads the data spine through the shared resolver. The cache
is regenerated offline by ``python _generate_material_properties.py``; these
tests fail when a YAML, profile or ODT edit lands without that regeneration.
Only the physical fields are compared, so stock or inventory edits elsewhere do
not trip them.
"""

import json
import math
import socket
from pathlib import Path

import pytest

from engine.data_spine.reconciliation import CACHE_PATH, reconcile
from engine.material_resolver import (
    resolve_material,
    resolved_logp,
    resolved_mw_g_mol,
    resolved_vp_25c_pa,
)
from engine.pipeline.formula_state import lookup_odt_air_ppb

FIELDS = ("vp", "mw", "clp", "odt")
REGENERATE = "stale cache; run `python _generate_material_properties.py`"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise OSError("network access is blocked in this test")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)


def _committed_rows():
    return json.loads(Path(CACHE_PATH).read_text(encoding="utf-8"))


def _gate_values(name):
    resolved = resolve_material(name)
    if not resolved.is_known:
        return None
    return {
        "vp": resolved_vp_25c_pa(resolved)[0],
        "mw": resolved_mw_g_mol(resolved)[0],
        "clp": resolved_logp(resolved)[0],
        "odt": lookup_odt_air_ppb(name, resolved.profile, resolved.registry_material)[0],
    }


def _same(cached, expected):
    if expected is None:
        return True
    return cached is not None and math.isclose(cached, expected, rel_tol=1e-9, abs_tol=0.0)


def test_cache_physics_equal_what_the_gate_reads():
    mismatches = []
    checked = 0
    for row in _committed_rows():
        gate = _gate_values(row["name"])
        if gate is None:
            continue
        checked += 1
        for field in FIELDS:
            if not _same(row.get(field), gate[field]):
                mismatches.append((row["name"], field, row.get(field), gate[field]))
    assert checked > 0
    assert mismatches == [], f"{REGENERATE}: {mismatches[:20]}"


def test_reconcile_leaves_committed_physics_unchanged():
    rows = _committed_rows()
    rebuilt, _report = reconcile(rows)
    changed = []
    for before, after in zip(rows, rebuilt):
        assert before["name"] == after["name"]
        for field in FIELDS:
            old, new = before.get(field), after.get(field)
            if old is None and new is None:
                continue
            if old is None or new is None or not math.isclose(old, new, rel_tol=1e-9):
                changed.append((before["name"], field, old, new))
    assert changed == [], f"{REGENERATE}: {changed[:20]}"
