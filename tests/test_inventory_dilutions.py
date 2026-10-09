"""Dilutions prepared on the Stock page count at the release gate (Kenny, 2026-10-09).

The current gate inventory has no neat Rose Oxide (only a 1% stock), so the
worked example is Alpha Damascone 1% w/w in DPG from the neat bottle.  Every
test writes to temporary logs through the environment variables the app and
the gate both read, never to the real data/user logs.
"""

import json

import pytest

from engine import user_records
from engine.inventory_dilutions import (
    FALSE_ACTION_AUTHORITY,
    PREPARED_DILUTION_AUTHORITY,
    PreparedDilutionError,
    load_prepared_dilution_events,
    record_prepared_dilution,
)
from engine.inventory_parser import materialize_current_inventory
from engine.personal_inventory import materialize_personal_inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

MATERIAL = "Alpha Damascone"


@pytest.fixture
def dilution_log(tmp_path, monkeypatch):
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "completions.jsonl"))
    monkeypatch.setenv(
        "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(tmp_path / "additions.jsonl")
    )
    path = tmp_path / "dilutions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_DILUTION_PATH", str(path))
    return path


def _neat_parent(materialized=None):
    materialized = materialized or materialize_current_inventory()
    return next(
        stock
        for stock in materialized.stocks
        if stock.identity_name == MATERIAL and stock.dilution == 1.0
    )


def _prepare(key: str, **overrides):
    baseline = materialize_current_inventory()
    command = {
        "parent_stock_id": _neat_parent(baseline).stock_id,
        "expected_effective_inventory_sha256": baseline.effective_inventory_sha256,
        "idempotency_key": key,
        "fraction_decimal": "0.01",
        **overrides,
    }
    return record_prepared_dilution(**command)


def _issues(fraction: float) -> list[str]:
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {MATERIAL: 100.0}, "dilutions": {MATERIAL: fraction}}
    )
    return [issue["reason"] for issue in check.data["issues"]]


def test_prepared_dilution_resolves_in_preflight_and_the_composer(dilution_log) -> None:
    assert _issues(0.01) != []
    parent_before = _neat_parent()

    receipt, materialized = _prepare("alpha-damascone-1")

    assert all(receipt[field] is False for field in FALSE_ACTION_AUTHORITY)
    assert receipt["prepared"]["fraction_basis"] == "mass_fraction"
    assert receipt["prepared"]["carrier"] == "dpg"
    (stock,) = [s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY]
    assert (stock.identity_name, stock.name) == (parent_before.identity_name, parent_before.name)
    assert stock.dilution == 0.01
    assert stock.execution_ready is True and stock.design_ready is True
    assert receipt["event_id"] in stock.source_ref
    assert _neat_parent(materialized) == parent_before

    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {MATERIAL: 100.0}, "dilutions": {MATERIAL: 0.01}}
    )
    assert check.data["issues"] == []
    (matched,) = check.data["matched_stocks"]
    assert matched["stock_facts_source"]["kind"] == "LAB_STOCK_PAGE_PREPARED_DILUTION"
    assert matched["stock_facts_source"]["event_sha256"] == receipt["event_sha256"]

    composer = materialize_personal_inventory()
    assert stock.stock_id in {s.stock_id for s in composer.stocks}


def test_same_dilution_twice_is_one_stock(dilution_log) -> None:
    first, _ = _prepare("first", amount_made_g="10", prepared_on="2026-10-09")
    second, materialized = _prepare("second", carrier="DPG", user_note="again")

    assert second["event_sha256"] == first["event_sha256"]
    assert len(load_prepared_dilution_events()) == 1
    prepared = [s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY]
    assert len(prepared) == 1


def test_volume_basis_is_a_separate_stock(dilution_log) -> None:
    _prepare("ww")
    _, materialized = _prepare("vv", fraction_basis="volume_fraction")
    prepared = [s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY]
    assert sorted(s.fraction_basis for s in prepared) == ["mass_fraction", "volume_fraction"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"parent_stock_id": "inventory:v5:does-not-exist"}, "not in the current inventory"),
        ({"fraction_decimal": "0"}, "above 0%"),
        ({"fraction_decimal": "-0.1"}, "above 0%"),
        ({"fraction_decimal": "1"}, "below 100%"),
        ({"fraction_basis": "unspecified"}, "basis"),
        ({"fraction_basis": ""}, "basis"),
        ({"carrier": ""}, "carrier"),
        ({"prepared_on": "9 Oct"}, "YYYY-MM-DD"),
    ],
)
def test_invalid_dilutions_are_refused(dilution_log, overrides, message) -> None:
    with pytest.raises(PreparedDilutionError, match=message):
        _prepare("bad", **overrides)
    assert not dilution_log.exists()


def test_strength_at_or_above_a_diluted_parent_is_refused(dilution_log) -> None:
    _, materialized = _prepare("one-percent")
    (prepared,) = [s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY]
    with pytest.raises(PreparedDilutionError, match="not in the current inventory"):
        _prepare("from-prepared", parent_stock_id=prepared.stock_id, fraction_decimal="0.001")
    with pytest.raises(PreparedDilutionError, match="weaker than the parent"):
        _prepare(
            "stronger",
            parent_stock_id=_held_diluted_parent_id(materialized),
            fraction_decimal="0.5",
        )


def _held_diluted_parent_id(materialized) -> str:
    return next(
        s.stock_id
        for s in materialized.stocks
        if s.status == "owned" and (s.execution_ready if s.design_ready is None else s.design_ready)
        and 0 < s.dilution < 0.5
        and s.authority != PREPARED_DILUTION_AUTHORITY
    )


def test_tampered_log_is_refused(dilution_log) -> None:
    _prepare("ok")
    event = json.loads(dilution_log.read_text(encoding="utf-8"))
    event["release_authority"] = True
    dilution_log.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(PreparedDilutionError):
        load_prepared_dilution_events()


def test_dilution_log_is_a_user_record(dilution_log) -> None:
    files = user_records.record_files()
    assert files[user_records.DILUTION_LOG_NAME] == dilution_log.resolve()
