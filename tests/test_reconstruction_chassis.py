"""Tests for engine.reconstruction.chassis."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.chassis import (
    ChassisRow,
    ChassisPartition,
    ModuleEnvelope,
    validate_partition,
    validate_anchor_floors,
    validate_module,
    canonical_hash,
)


def test_validate_partition_perfect():
    rows = [
        ChassisRow("Iso E Super", 450, 450, 445, 5, "PROTECTED_ANCHOR"),
        ChassisRow("Galaxolide", 140, 140, 140, 0, "IMMUTABLE_CORE"),
        ChassisRow("Hedione", 300, 300, 255, 45, "PROTECTED_ANCHOR"),
    ]
    chassis = ChassisPartition("Test", 840, 50, 890, tuple(rows))
    errors = validate_partition(chassis, 890, 840, 50)
    assert len(errors) == 0


def test_validate_partition_mismatch():
    rows = [ChassisRow("A", 100, 100, 50, 50, "MIXED")]
    chassis = ChassisPartition("Bad", 50, 50, 100, tuple(rows))
    errors = validate_partition(chassis, 100, 60, 40)
    assert len(errors) > 0


def test_validate_anchor_floors_pass():
    rows = [
        ChassisRow("Ginger", 50, 50, 25, 25, "PROTECTED_ANCHOR"),
        ChassisRow("Musk", 200, 200, 200, 0, "IMMUTABLE_CORE"),
    ]
    chassis = ChassisPartition("Test", 225, 25, 250, tuple(rows))
    envelope = ModuleEnvelope(
        socket_raw_ul=25,
        active_range=(20, 40),
        carrier_range=(0, 5),
        anchor_minimums={"Ginger": 20.0},
        required_roles=(),
        family_caps={},
        temporal_ranges={},
        forbidden_materials=(),
    )
    errors = validate_anchor_floors(chassis, envelope)
    assert len(errors) == 0


def test_validate_anchor_floors_fail():
    rows = [ChassisRow("Ginger", 50, 50, 15, 35, "PROTECTED_ANCHOR")]
    chassis = ChassisPartition("Test", 15, 35, 50, tuple(rows))
    envelope = ModuleEnvelope(
        socket_raw_ul=35,
        active_range=(20, 40),
        carrier_range=(0, 5),
        anchor_minimums={"Ginger": 25.0},
        required_roles=(),
        family_caps={},
        temporal_ranges={},
        forbidden_materials=(),
    )
    errors = validate_anchor_floors(chassis, envelope)
    assert len(errors) == 1


def test_validate_module():
    rows = [ChassisRow("A", 100, 100, 0, 100, "MODULE_MOBILE")]
    errors = validate_module(rows, 100)
    assert len(errors) == 0
    errors = validate_module(rows, 99)
    assert len(errors) == 1


def test_canonical_hash():
    rows = [{"ingredient": "Iso E Super", "raw_uL": "450"}]
    h1 = canonical_hash(rows, ["ingredient", "raw_uL"])
    h2 = canonical_hash(rows, ["ingredient", "raw_uL"])
    assert h1 == h2
    assert len(h1) == 64
