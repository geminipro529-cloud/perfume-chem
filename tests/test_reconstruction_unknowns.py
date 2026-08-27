"""Tests for engine.reconstruction.unknowns."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.unknowns import (
    create_unknown_node,
    UnknownRegistry,
    chassis_classify_unknown,
    evidence_needed_to_resolve,
    UnknownNode,
)


def test_create_unknown_node():
    node = create_unknown_node(
        description="muguet-like radiant",
        functional_neighbors=["Hedione", "Florol"],
        amount_range=(10, 20, 30),
        time_windows=["heart"],
    )
    assert node.unknown_id.startswith("UNKNOWN_")
    assert "muguet" in node.description.lower()
    assert node.amount_median == 20
    assert node.amount_p05 == 10
    assert node.amount_p95 == 30


def test_registry():
    reg = UnknownRegistry()
    node = create_unknown_node("woody amber", ["Iso E", "Ambrox"], (5, 10, 15))
    reg.register(node)
    assert reg.get(node.unknown_id) is node
    assert len(reg.list_all()) == 1


def test_registry_by_window():
    reg = UnknownRegistry()
    a = create_unknown_node("top citrus", ["Bergamot"], time_windows=["opening"])
    b = create_unknown_node("base musk", ["Galaxolide"], time_windows=["drydown"])
    reg.register(a)
    reg.register(b)
    assert len(reg.list_by_window("opening")) == 1
    assert len(reg.list_by_window("drydown")) == 1
    assert len(reg.list_by_window("heart")) == 0


def test_chassis_classify_protected():
    node = create_unknown_node("test", [])
    assert chassis_classify_unknown(node, True, False, False, False) == "UNKNOWN_PROTECTED"
    assert chassis_classify_unknown(node, False, True, False, False) == "UNKNOWN_PROTECTED"
    assert chassis_classify_unknown(node, False, False, False, False) == "UNKNOWN_MODULE_CANDIDATE"


def test_evidence_checklist():
    node = create_unknown_node("test", [])
    evidence = evidence_needed_to_resolve(node)
    assert len(evidence) >= 5
    assert any("standard" in e.lower() for e in evidence)
