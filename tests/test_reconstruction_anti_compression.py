"""Tests for engine.reconstruction.anti_compression."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.anti_compression import (
    ANTI_COMPRESSION_CRITERIA,
    CompressionCheck,
    audit_formula,
    should_merge,
)


def test_anti_compression_all_12_criteria_match_spec():
    """Verify that all 12 criteria match the PROTOCOL.md §16.1 spec."""
    spec_names = [
        "chemical_scaffold_isomer",
        "supplier_grade",
        "volatility_time_window",
        "odor_quality",
        "diffusion_behavior",
        "texture",
        "substantivity",
        "matrix_partitioning",
        "gc_peak_ri_evidence",
        "gco_odor_event",
        "official_note_support",
        "source_roster_identity",
    ]
    code_names = [c["name"] for c in ANTI_COMPRESSION_CRITERIA]
    assert code_names == spec_names, f"Criteria mismatch! Code: {code_names}"


def test_audit_formula_basic_pair():
    """Audit a small formula pair — all criteria should run."""
    results = audit_formula(["Iso E Super", "Hedione"])
    assert len(results) == 1  # one pair
    checks = list(results.values())[0]
    assert len(checks) == 12  # all 12 criteria


def test_should_merge_all_pass():
    """If all 12 pass, should_merge returns True."""
    checks = []
    for c in ANTI_COMPRESSION_CRITERIA:
        checks.append(CompressionCheck(c["name"], True, "ok", "A", "B"))
    assert should_merge("A", "B", checks) is True


def test_should_merge_one_fails():
    """If any criterion fails, should_merge returns False."""
    checks = []
    for c in ANTI_COMPRESSION_CRITERIA:
        checks.append(CompressionCheck(c["name"], True, "ok", "A", "B"))
    checks[5] = CompressionCheck("texture", False, "different texture", "A", "B")
    assert should_merge("A", "B", checks) is False


def test_audit_formula_identical_materials():
    """Repeated roster rows remain auditable and are not silently collapsed."""
    results = audit_formula(["Iso E Super", "Iso E Super"])
    assert len(results) == 1
    checks = results["Iso E Super<->Iso E Super"]
    assert len(checks) == 12
    assert not should_merge("Iso E Super", "Iso E Super", checks)


def test_audit_formula_three_materials():
    """Three materials produce 3 pairs."""
    results = audit_formula(["Bergamot FCF", "Hedione", "Iso E Super"])
    assert len(results) == 3  # 3 choose 2 = 3 pairs
    for pair_key, checks in results.items():
        assert len(checks) == 12


def test_compression_check_as_dict():
    """CompressionCheck.as_dict() returns expected keys."""
    check = CompressionCheck("texture", True, "both texture=lift", "A", "B")
    d = check.as_dict()
    assert d["criterion_name"] == "texture"
    assert d["passed"] is True
    assert d["detail"] == "both texture=lift"
    assert d["material_a"] == "A"
    assert d["material_b"] == "B"


def test_should_merge_empty_checks():
    """Empty checks list returns False."""
    assert should_merge("A", "B", []) is False
