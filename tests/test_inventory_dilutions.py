"""Dilutions prepared on the Stock page count at the release gate (Kenny, 2026-10-09).

The current gate inventory has no neat Rose Oxide (only a 1% stock), so the
worked example is Alpha Damascone 1% w/w in DPG from the neat bottle.  Every
test writes to temporary logs through the environment variables the app and
the gate both read, never to the real data/user logs.
"""

import json

import pytest

from engine import user_records
from engine.inventory_completions import record_inventory_completion
from engine.inventory_dilutions import (
    FALSE_ACTION_AUTHORITY,
    PREPARED_DILUTION_AUTHORITY,
    PREPARED_DILUTION_PARENT_CHANGED,
    PreparedDilutionError,
    dilution_parent_ready,
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
        "parent_stock_id": (
            overrides.pop("parent_stock_id", None) or _neat_parent(baseline).stock_id
        ),
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
        if dilution_parent_ready(s) and 0 < s.dilution < 0.5
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


def _stock(identity: str, fraction: float, materialized=None):
    materialized = materialized or materialize_current_inventory()
    return next(
        s
        for s in materialized.stocks
        if s.identity_name == identity
        and s.dilution == fraction
        and s.authority != PREPARED_DILUTION_AUTHORITY
    )


def _complete(stock, key: str, fraction: str, carrier: str):
    record_inventory_completion(
        stock_id=stock.stock_id,
        expected_effective_inventory_sha256=(
            materialize_current_inventory().effective_inventory_sha256
        ),
        idempotency_key=key,
        fraction_decimal=fraction,
        fraction_basis="mass_fraction",
        carrier=carrier,
        physical_form="liquid",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=True,
        source_kind="PERSONAL_CONFIRMATION",
    )


def _prepared(materialized):
    return [s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY]


def test_completed_but_gate_held_parent_cannot_be_diluted(dilution_log) -> None:
    apritone = _stock("Apritone", 0.1)
    assert "IDENTITY KEPT SEPARATE" in apritone.row_unresolved_tokens
    _complete(apritone, "apritone-10", "0.1", "DPG")
    completed = _stock("Apritone", 0.1)
    assert completed.design_ready is True and completed.execution_ready is False

    with pytest.raises(PreparedDilutionError, match="held at the release gate"):
        _prepare("apritone-1", parent_stock_id=completed.stock_id)
    assert not dilution_log.exists()


def test_execution_held_parent_without_a_completion_cannot_be_diluted(dilution_log) -> None:
    manzanate = _stock("Manzanate", 1.0)
    assert manzanate.execution_ready is False
    with pytest.raises(PreparedDilutionError, match="held at the release gate"):
        _prepare("manzanate-1", parent_stock_id=manzanate.stock_id)
    assert not dilution_log.exists()


def test_dilution_is_held_when_its_parent_bottle_changes(dilution_log) -> None:
    _prepare("first")
    assert _issues(0.01) == []

    _complete(_neat_parent(), "now-half", "0.5", "DPG")
    (held,) = _prepared(materialize_current_inventory())
    assert held.execution_ready is False
    assert held.execution_hold_reason == PREPARED_DILUTION_PARENT_CHANGED
    assert _issues(0.01) != []

    # Recording it again from the bottle as it now stands appends a new event
    # and replaces the held stock.
    receipt, materialized = _prepare("again", parent_stock_id=_stock(MATERIAL, 0.5).stock_id)
    assert len(load_prepared_dilution_events()) == 2
    (ready,) = _prepared(materialized)
    assert ready.execution_ready is True
    assert ready.completion_event_sha256 == receipt["event_sha256"]
    assert _issues(0.01) == []


def test_basis_change_needs_a_neat_parent(dilution_log) -> None:
    anisaldehyde = _stock("Anisaldehyde", 0.1)
    assert anisaldehyde.fraction_basis == "volume_fraction"
    with pytest.raises(PreparedDilutionError, match="needs densities"):
        _prepare("ww-from-vv", parent_stock_id=anisaldehyde.stock_id)
    assert not dilution_log.exists()


def test_prepared_stock_shows_its_own_strength_and_both_carriers(dilution_log) -> None:
    anisaldehyde = _stock("Anisaldehyde", 0.1)
    assert anisaldehyde.name == "Anisaldehyde 10%" and anisaldehyde.carrier == "ethanol"
    _, materialized = _prepare(
        "anis-1", parent_stock_id=anisaldehyde.stock_id, fraction_basis="volume_fraction"
    )
    (stock,) = _prepared(materialized)
    assert stock.name == "Anisaldehyde 1%"
    assert stock.carrier == "dpg + ethanol"
    assert stock.raw_name == "Anisaldehyde 1% v/v in DPG + ETHANOL (prepared)"


def test_prepared_stock_does_not_copy_the_parents_authority_disagreement(dilution_log) -> None:
    _complete(_neat_parent(), "now-half", "0.5", "DEP")
    parent = _stock(MATERIAL, 0.5)
    assert parent.authority_facts_differ != ()
    _, materialized = _prepare("from-half", parent_stock_id=parent.stock_id)
    (stock,) = _prepared(materialized)
    assert stock.authority_facts_differ == ()
    assert stock.carrier == "dpg + dep"


def test_returned_inventory_reads_the_log_it_wrote(dilution_log, tmp_path) -> None:
    other = tmp_path / "other-dilutions.jsonl"
    receipt, materialized = _prepare("elsewhere", path=other)
    assert other.exists() and not dilution_log.exists()
    (stock,) = _prepared(materialized)
    assert stock.completion_event_sha256 == receipt["event_sha256"]


def test_unspecified_parent_basis_is_refused_before_the_basis_change_message(
    dilution_log,
) -> None:
    adoxal = _stock("Adoxal", 0.1)
    assert adoxal.fraction_basis == "unspecified" and adoxal.execution_ready is True
    with pytest.raises(PreparedDilutionError, match="concentration basis isn't recorded"):
        _prepare("adoxal-1", parent_stock_id=adoxal.stock_id)
    assert not dilution_log.exists()


def test_same_dilution_from_two_owned_bottles_is_two_events_with_two_parents(
    dilution_log,
) -> None:
    neat = _stock("Ambrox Super", 1.0)
    quarter = _stock("Ambrox Super", 0.25)
    assert neat.execution_ready and quarter.execution_ready
    for key, parent in (("ambrox-from-neat", neat), ("ambrox-from-quarter", quarter)):
        baseline = materialize_current_inventory()
        record_prepared_dilution(
            parent_stock_id=parent.stock_id,
            expected_effective_inventory_sha256=baseline.effective_inventory_sha256,
            idempotency_key=key,
            fraction_decimal="0.01",
        )
    events = load_prepared_dilution_events()
    assert len(events) == 2
    parents = {str(event["prepared"]["parent_stock_id"]) for event in events}
    assert parents == {neat.stock_id, quarter.stock_id}


def test_parent_carrier_components_are_not_repeated(dilution_log) -> None:
    quarter = _stock("Ambrox Super", 0.25)
    assert quarter.carrier == "dpg + ipm + ethanol"
    _, materialized = _prepare("ambrox-1-dpg", parent_stock_id=quarter.stock_id)
    (stock,) = _prepared(materialized)
    assert stock.carrier == "dpg + ipm + ethanol"
    assert stock.raw_name == "Ambrox Super 1% w/w in DPG + IPM + ETHANOL (prepared)"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Cabreuva EO 50% in DPG", "Cabreuva EO 1% in DPG"),
        ("Apritone 10%", "Apritone 1%"),
        ("Alpha Damascone", "Alpha Damascone"),
        ("Base 10% in 50% DPG", "Base 10% in 50% DPG"),
    ],
)
def test_prepared_name_states_its_own_strength(name, expected) -> None:
    from decimal import Decimal
    from types import SimpleNamespace

    from engine.inventory_dilutions import _prepared_name

    # The parent's current strength (here 25%) need not match the name.
    parent = SimpleNamespace(name=name, dilution=0.25)
    assert _prepared_name(parent, Decimal("0.01")) == expected
