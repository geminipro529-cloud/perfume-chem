from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from hashlib import sha256

import pytest

from engine.research.commercial_references import (
    DEFAULT_REGISTRY_PATH,
    build_commercial_reference_panel,
    load_commercial_reference_registry,
)


def test_old_fy24_launch_is_context_not_a_current_anchor():
    registry = load_commercial_reference_registry()
    old = registry.evidence["coty-fy24-burberry-goddess"]
    assert old.source_period_end == "2024-06-30"
    assert old.published_on == "2024-08-20"
    assert old.market_region == "UNITED_STATES_CANADA_GERMANY"
    assert "not a global sales rank" in old.metric
    assert old.is_current(date(2026, 10, 6)) is False
    panel = build_commercial_reference_panel(("lavender",), as_of_date="2026-10-06")
    goddess = next(row for row in panel["panel"]["active_members"] if row["product_id"] == "burberry-goddess-edp")
    assert goddess["structural_neighbour"] is True
    assert goddess["market_anchor"] is False
    assert panel["historical_market_evidence_ids"] == [old.evidence_id]
    assert sum(row["market_anchor"] for row in panel["panel"]["active_members"]) == 2
    assert next(row for row in panel["evidence"] if row["evidence_id"] == old.evidence_id)["selection_role"] == "HISTORICAL_CONTEXT_ONLY"


def test_rereview_cannot_renew_old_observation():
    old = load_commercial_reference_registry().evidence["coty-fy24-burberry-goddess"]
    rereviewed = replace(old, reviewed_on="2026-10-06", expires_on="2030-10-06")
    assert rereviewed.is_current(date(2026, 10, 6)) is False


def test_market_twelve_calendar_month_boundary_and_missing_dates():
    row = load_commercial_reference_registry().evidence["lvmh-2025-sauvage-franchise"]
    assert row.is_current(date(2026, 12, 31)) is True
    assert row.is_current(date(2027, 1, 1)) is False
    assert replace(row, source_period_start=None, source_period_end=None).is_current(date(2026, 10, 6)) is False
    leap = replace(row, reviewed_on="2024-02-29", source_period_start="2023-03-01", source_period_end="2024-02-29", expires_on=None)
    assert leap.is_current(date(2025, 2, 28)) is True
    assert leap.is_current(date(2025, 3, 1)) is False


@pytest.mark.parametrize("change", [
    {"source_period_start": "2026-01-01"},
    {"source_period_start": None},
    {"published_on": "2024-01-01"},
    {"published_on": "2028-01-01"},
    {"usable_for_panel_selection": 1},
])
def test_malformed_period_and_boolean_flags_fail_closed(change):
    row = load_commercial_reference_registry().evidence["lvmh-2025-sauvage-franchise"]
    with pytest.raises((ValueError, TypeError)):
        replace(row, **change)


def test_future_observation_and_retracted_anchor_fail_closed():
    registry = load_commercial_reference_registry()
    key = "lvmh-2025-sauvage-franchise"
    for change in [
        {"source_period_start": "2026-01-01", "source_period_end": "2026-12-31"},
        {"retraction_state": "EXPRESSION_OF_CONCERN"},
    ]:
        bad = replace(registry, evidence={**registry.evidence, key: replace(registry.evidence[key], **change)})
        with pytest.raises(ValueError, match="CURRENT_MARKET_ANCHOR"):
            build_commercial_reference_panel(("lavender",), as_of_date="2026-10-06", registry=bad)


def test_historical_v1_registry_is_readable_but_unbound_dates_cannot_select():
    path = DEFAULT_REGISTRY_PATH.with_name("commercial_reference_registry_v1.json")
    assert sha256(path.read_bytes()).hexdigest() == "1d83c920487b69f55c7ca0b439f43beeaac048f5edc6b6d6bfcce00c441510f3"
    old = load_commercial_reference_registry(path)
    assert len(old.products) == 5
    with pytest.raises(ValueError, match="CURRENT_MARKET_ANCHOR"):
        build_commercial_reference_panel(("lavender",), as_of_date="2026-10-06", registry=old)


def test_v2_missing_observation_period_and_unsupported_schema_are_rejected(tmp_path):
    raw = json.loads(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    raw["evidence"][0].pop("source_period_end")
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="source_period_end"):
        load_commercial_reference_registry(path)
    raw["schema_version"] = "unknown"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_commercial_reference_registry(path)
