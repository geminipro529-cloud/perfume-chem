"""Tests for engine.safety.regulatory — RegulatorySnapshot, compliance checks,
compliant build generation, snapshot comparison, and IFRA limit lookups."""

from __future__ import annotations

import pytest

from engine.ifra_safety import get_ifra_limit
from engine.safety.regulatory import (
    REDUCED_RISK_PRODUCT_TYPES,
    RegulatorySnapshot,
    check_compliance,
    compare_snapshots,
    generate_compliant_build,
    make_snapshot,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_COUMARIN_WITHIN = {
    "name": "Coumarin",
    "active_ul": 30,
    "finished_product_volume_ml": 30000,
}

# Coumarin limit = 1.5% of finished product (IFRA_STD_023, sourced table).
# 3000 µL active in 30 mL finished = 10% → exceeds 1.5%.
_COUMARIN_EXCEED = {
    "name": "Coumarin",
    "active_ul": 3000,
    "finished_product_volume_ml": 30,
}

_UNKNOWN_MATERIAL = {
    "name": "Fictionalium",
    "active_ul": 500,
    "finished_product_volume_ml": 30000,
}

_ZERO_VOLUME = {
    "name": "Coumarin",
    "active_ul": 100,
    "finished_product_volume_ml": 0,
}

# A different material that exceeds its limit (Eugenol limit = 2.5%, IFRA_STD_035).
# 900 µL active in 30 mL finished = 3% → exceeds 2.5%.
_EUGENOL_EXCEED = {
    "name": "Eugenol",
    "active_ul": 900,
    "finished_product_volume_ml": 30,
}


def _snapshot(
    jurisdiction: str = "EU",
    product_category: str = "Cat4",
    rule_set: str = "IFRA_51st_2025",
    effective_date: str = "2025-01-01",
) -> RegulatorySnapshot:
    return make_snapshot(
        jurisdiction=jurisdiction,
        product_category=product_category,
        rule_set=rule_set,
        effective_date=effective_date,
    )


# ── RegulatorySnapshot ─────────────────────────────────────────────────────────


class TestRegulatorySnapshot:
    """RegulatorySnapshot creation and field access."""

    def test_create_with_all_fields(self) -> None:
        snap = RegulatorySnapshot(
            snapshot_id="snap_test_001",
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-01-01",
            source_url="https://ifrafragrance.org/standards",
            hash="abc123",
            notes="Test snapshot",
        )
        assert snap.snapshot_id == "snap_test_001"
        assert snap.jurisdiction == "EU"
        assert snap.product_category == "Cat4"
        assert snap.rule_set == "IFRA_51st_2025"
        assert snap.effective_date == "2025-01-01"
        assert snap.source_url == "https://ifrafragrance.org/standards"
        assert snap.hash == "abc123"
        assert snap.notes == "Test snapshot"

    def test_create_with_defaults(self) -> None:
        snap = RegulatorySnapshot(
            snapshot_id="snap_defaults",
            jurisdiction="US",
            product_category="Cat2",
            rule_set="IFRA_50th_2022",
            effective_date="2022-06-01",
        )
        assert snap.source_url == ""
        assert snap.hash == ""
        assert snap.notes == ""

    def test_as_dict(self) -> None:
        snap = RegulatorySnapshot(
            snapshot_id="snap_dict",
            jurisdiction="UK",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-03-01",
        )
        d = snap.as_dict()
        assert d["snapshot_id"] == "snap_dict"
        assert d["jurisdiction"] == "UK"
        assert d["product_category"] == "Cat4"
        assert d["rule_set"] == "IFRA_51st_2025"
        assert d["effective_date"] == "2025-03-01"
        assert d["source_url"] == ""
        assert d["hash"] == ""
        assert d["notes"] == ""

    def test_is_frozen(self) -> None:
        snap = _snapshot()
        with __import__("pytest").raises(AttributeError):
            snap.jurisdiction = "US"  # type: ignore[misc]

    def test_make_snapshot_auto_generates_id_and_hash(self) -> None:
        snap = make_snapshot(
            jurisdiction="GLOBAL",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-07-01",
        )
        assert snap.snapshot_id.startswith("snap_")
        assert len(snap.snapshot_id) == 17  # "snap_" + 12 hex chars
        assert snap.hash != ""
        assert snap.jurisdiction == "GLOBAL"
        assert snap.product_category == "Cat4"
        assert snap.rule_set == "IFRA_51st_2025"
        assert snap.effective_date == "2025-07-01"


# ── check_compliance ───────────────────────────────────────────────────────────


class TestCheckCompliance:
    """check_compliance: material limit checking."""

    def test_material_within_limit(self) -> None:
        snap = _snapshot()
        results = check_compliance(
            formula_materials=[_COUMARIN_WITHIN],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert len(results) == 1
        r = results[0]
        assert r.material == "Coumarin"
        assert r.exceeds is False
        assert r.max_allowed_pct == 1.5
        assert r.current_dose_pct < r.max_allowed_pct
        assert "within limit" in r.detail

    def test_material_exceeding_limit(self) -> None:
        snap = _snapshot()
        results = check_compliance(
            formula_materials=[_COUMARIN_EXCEED],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert len(results) == 1
        r = results[0]
        assert r.material == "Coumarin"
        assert r.exceeds is True
        assert r.max_allowed_pct == 1.5
        assert r.current_dose_pct > r.max_allowed_pct
        assert "exceeds limit" in r.detail

    def test_unknown_material_no_violation(self) -> None:
        snap = _snapshot()
        results = check_compliance(
            formula_materials=[_UNKNOWN_MATERIAL],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert len(results) == 1
        r = results[0]
        assert r.material == "Fictionalium"
        assert r.exceeds is False
        assert r.max_allowed_pct is None
        assert r.ifra_status == "unknown"
        assert "not in the IFRA 51st Amendment Category 4 table" in r.detail

    def test_zero_volume_returns_no_exceed(self) -> None:
        snap = _snapshot()
        results = check_compliance(
            formula_materials=[_ZERO_VOLUME],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert len(results) == 1
        r = results[0]
        assert r.exceeds is False
        assert r.current_dose_pct == 0.0
        assert "volume is zero or missing" in r.detail

    def test_multiple_materials_mixed(self) -> None:
        snap = _snapshot()
        # Use different material names to avoid name collision in violation lookup
        results = check_compliance(
            formula_materials=[_COUMARIN_WITHIN, _EUGENOL_EXCEED, _UNKNOWN_MATERIAL],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert len(results) == 3
        assert results[0].exceeds is False
        assert results[1].exceeds is True
        assert results[2].exceeds is False

    def test_snapshot_fields_propagated_to_result(self) -> None:
        snap = _snapshot(rule_set="IFRA_50th_2022", effective_date="2022-06-01")
        results = check_compliance(
            formula_materials=[_COUMARIN_WITHIN],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        r = results[0]
        assert r.rule_reference == "IFRA_50th_2022"
        assert r.rule_version == "2022-06-01"

    def test_compliance_result_as_dict(self) -> None:
        snap = _snapshot()
        results = check_compliance(
            formula_materials=[_COUMARIN_WITHIN],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        d = results[0].as_dict()
        assert d["material"] == "Coumarin"
        assert d["exceeds"] is False
        assert "max_allowed_pct" in d
        assert "current_dose_pct" in d
        assert "detail" in d


    def test_coumarin_reports_sourced_limit_and_standard(self) -> None:
        results = check_compliance(
            formula_materials=[_COUMARIN_EXCEED],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=_snapshot(),
        )
        r = results[0]
        assert r.max_allowed_pct == 1.5
        assert r.ifra_status == "restricted"
        assert r.ifra_standard == "IFRA_STD_023"
        assert "IFRA_STD_023" in r.detail
        assert r.as_dict()["ifra_standard"] == "IFRA_STD_023"

    def test_hedione_is_reported_as_having_no_standard(self) -> None:
        # Hedione has no IFRA standard: no number, no fallback, never exceeds.
        results = check_compliance(
            formula_materials=[
                {"name": "Hedione", "active_ul": 15000, "finished_product_volume_ml": 30}
            ],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=_snapshot(),
        )
        r = results[0]
        assert r.ifra_status == "no_standard"
        assert r.ifra_standard is None
        assert r.max_allowed_pct is None
        assert r.exceeds is False
        assert "has no IFRA standard" in r.detail

    def test_prohibited_material_exceeds_when_present(self) -> None:
        results = check_compliance(
            formula_materials=[
                {"name": "Lilial", "active_ul": 1, "finished_product_volume_ml": 30}
            ],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=_snapshot(),
        )
        r = results[0]
        assert r.ifra_status == "prohibited"
        assert r.max_allowed_pct == 0.0
        assert r.exceeds is True
        assert "prohibited" in r.detail


# ── generate_compliant_build ───────────────────────────────────────────────────


class TestGenerateCompliantBuild:
    """generate_compliant_build: cap violating materials."""

    def test_exceeding_material_gets_capped(self) -> None:
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[_COUMARIN_EXCEED],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        adjusted = generate_compliant_build(
            target_materials=[_COUMARIN_EXCEED],
            violations=violations,
        )
        assert len(adjusted) == 1
        capped = adjusted[0]
        # Coumarin limit = 1.5% of 30 mL = 0.45 mL = 450 µL
        # Original was 3000 µL → should be capped to 450 µL
        assert capped["active_ul"] < 3000
        assert capped["active_ul"] == pytest.approx(450.0)
        assert "_capped_from_ul" in capped

    def test_material_within_limit_unchanged(self) -> None:
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[_COUMARIN_WITHIN],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        adjusted = generate_compliant_build(
            target_materials=[_COUMARIN_WITHIN],
            violations=violations,
        )
        assert len(adjusted) == 1
        assert adjusted[0]["active_ul"] == 30
        assert "_capped_from_ul" not in adjusted[0]

    def test_original_target_not_modified(self) -> None:
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[_COUMARIN_EXCEED],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        original = [dict(_COUMARIN_EXCEED)]
        _ = generate_compliant_build(
            target_materials=original,
            violations=violations,
        )
        # Original should be unchanged
        assert original[0]["active_ul"] == 3000
        assert "_capped_from_ul" not in original[0]

    def test_capped_material_has_annotation_keys(self) -> None:
        """A truly exceeding material: Coumarin at 3000 µL in 30 mL finished product.
        3000 µL / 1000 = 3 mL active in 30 mL = 10% → exceeds 1.5% limit."""
        mat_exceed_small_fp = {
            "name": "Coumarin",
            "active_ul": 3000,
            "finished_product_volume_ml": 30,
        }
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[mat_exceed_small_fp],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        assert violations[0].exceeds is True
        adjusted = generate_compliant_build(
            target_materials=[mat_exceed_small_fp],
            violations=violations,
        )
        capped = adjusted[0]
        assert capped["active_ul"] < 3000
        assert "_capped_from_ul" in capped
        assert capped["_capped_from_ul"] == 3000.0
        assert "_compliance_note" in capped
        assert "Capped from" in capped["_compliance_note"]

    def test_unknown_material_passed_through(self) -> None:
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[_UNKNOWN_MATERIAL],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        adjusted = generate_compliant_build(
            target_materials=[_UNKNOWN_MATERIAL],
            violations=violations,
        )
        assert len(adjusted) == 1
        assert adjusted[0]["active_ul"] == 500
        assert "_capped_from_ul" not in adjusted[0]

    def test_mixed_list_preserves_order(self) -> None:
        # Use different material names to avoid name collision in violation lookup
        snap = _snapshot()
        violations = check_compliance(
            formula_materials=[_COUMARIN_WITHIN, _EUGENOL_EXCEED, _UNKNOWN_MATERIAL],
            jurisdiction="EU",
            product_category="Cat4",
            snapshot=snap,
        )
        adjusted = generate_compliant_build(
            target_materials=[_COUMARIN_WITHIN, _EUGENOL_EXCEED, _UNKNOWN_MATERIAL],
            violations=violations,
        )
        assert len(adjusted) == 3
        # First: within limit, unchanged
        assert adjusted[0]["active_ul"] == 30
        assert "_capped_from_ul" not in adjusted[0]
        # Second: exceeded, capped
        assert adjusted[1]["active_ul"] < 900
        assert "_capped_from_ul" in adjusted[1]
        # Third: unknown, passed through
        assert adjusted[2]["active_ul"] == 500
        assert "_capped_from_ul" not in adjusted[2]


# ── compare_snapshots ──────────────────────────────────────────────────────────


class TestCompareSnapshots:
    """compare_snapshots: diff between two RegulatorySnapshots."""

    def test_identical_snapshots(self) -> None:
        s1 = RegulatorySnapshot(
            snapshot_id="snap_same",
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-01-01",
        )
        s2 = RegulatorySnapshot(
            snapshot_id="snap_same",
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-01-01",
        )
        diffs = compare_snapshots(s1, s2)
        assert diffs == ["Snapshots are identical."]

    def test_different_effective_dates(self) -> None:
        s1 = RegulatorySnapshot(
            snapshot_id="snap_a",
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-01-01",
        )
        s2 = RegulatorySnapshot(
            snapshot_id="snap_b",
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_51st_2025",
            effective_date="2025-06-01",
        )
        diffs = compare_snapshots(s1, s2)
        assert len(diffs) >= 2
        assert any("effective_date" in d for d in diffs)

    def test_different_jurisdiction(self) -> None:
        s1 = _snapshot(jurisdiction="EU")
        s2 = _snapshot(jurisdiction="US")
        diffs = compare_snapshots(s1, s2)
        assert any("jurisdiction" in d for d in diffs)

    def test_different_rule_set(self) -> None:
        s1 = _snapshot(rule_set="IFRA_50th_2022")
        s2 = _snapshot(rule_set="IFRA_51st_2025")
        diffs = compare_snapshots(s1, s2)
        assert any("rule_set" in d for d in diffs)

    def test_multiple_differences(self) -> None:
        s1 = _snapshot(
            jurisdiction="EU",
            product_category="Cat4",
            rule_set="IFRA_50th_2022",
            effective_date="2022-06-01",
        )
        s2 = _snapshot(
            jurisdiction="US",
            product_category="Cat2",
            rule_set="IFRA_51st_2025",
            effective_date="2025-01-01",
        )
        diffs = compare_snapshots(s1, s2)
        assert len(diffs) >= 4  # header + 4 field diffs
        assert diffs[0].startswith("Diff:")


# ── get_ifra_limit ─────────────────────────────────────────────────────────────


class TestGetIfraLimit:
    """get_ifra_limit: IFRA Cat4 limit lookups."""

    def test_known_material_returns_value(self) -> None:
        # IFRA_STD_023 (Coumarin), 51st Amendment, Category 4: 1.5 %.
        limit = get_ifra_limit("Coumarin")
        assert limit is not None
        assert limit == 1.5

    def test_unknown_material_returns_none(self) -> None:
        limit = get_ifra_limit("Fictionalium")
        assert limit is None

    def test_case_insensitive(self) -> None:
        limit = get_ifra_limit("coumarin")
        assert limit == 1.5

    def test_known_material_different_rule_set(self) -> None:
        limit = get_ifra_limit("Coumarin", rule_set="IFRA_50th_2022")
        assert limit == 1.6

    def test_rule_set_without_material_falls_back(self) -> None:
        # Oakmoss is not in IFRA_50th_2022, so the current sourced table answers (0.1 %).
        assert get_ifra_limit("Oakmoss Absolute", rule_set="IFRA_50th_2022") == 0.1

    def test_material_without_a_standard_has_no_limit(self) -> None:
        # Hedione has no IFRA Standard; the old hand-typed 40 % fallback is gone.
        assert get_ifra_limit("Hedione") is None
        assert get_ifra_limit("Hedione", rule_set="IFRA_50th_2022") is None


# ── REDUCED_RISK_PRODUCT_TYPES ─────────────────────────────────────────────────


class TestReducedRiskProductTypes:
    """REDUCED_RISK_PRODUCT_TYPES constant."""

    def test_constant_exists_and_is_frozenset(self) -> None:
        assert isinstance(REDUCED_RISK_PRODUCT_TYPES, frozenset)

    def test_contains_expected_types(self) -> None:
        assert "deodorant" in REDUCED_RISK_PRODUCT_TYPES
        assert "cream" in REDUCED_RISK_PRODUCT_TYPES
        assert "rinse_off" in REDUCED_RISK_PRODUCT_TYPES

    def test_does_not_contain_fine_fragrance(self) -> None:
        assert "fine_fragrance" not in REDUCED_RISK_PRODUCT_TYPES
        assert "edp" not in REDUCED_RISK_PRODUCT_TYPES
