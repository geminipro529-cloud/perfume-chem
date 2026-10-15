"""How much is left of a stock: an append-only, hash-chained log; the last entry wins."""

from __future__ import annotations

import json

import pytest

from engine.stock_on_hand import (
    StockOnHandError,
    StockOnHandLogCorruptError,
    latest_on_hand,
    load_on_hand_events,
    record_on_hand,
)


def test_the_last_entry_per_stock_wins_and_a_cleared_one_is_gone(tmp_path):
    log = tmp_path / "on_hand.jsonl"
    record_on_hand(path=log, stock_id="s-hed", amount_decimal="12.50", unit="mL", supplier=" Bontoux ")
    record_on_hand(path=log, stock_id="s-amb", amount_decimal="3", unit="g")
    record_on_hand(path=log, stock_id="s-hed", amount_decimal="0", unit="mL", note="empty")
    record_on_hand(path=log, stock_id="s-amb", clear=True)

    latest = latest_on_hand(log)
    assert list(latest) == ["s-hed"]
    assert {key: latest["s-hed"][key] for key in ("amount_decimal", "unit", "supplier", "note")} == {
        "amount_decimal": "0", "unit": "mL", "supplier": "", "note": "empty",
    }
    assert len(load_on_hand_events(log)) == 4


@pytest.mark.parametrize("fields", [
    {"stock_id": "", "amount_decimal": "1", "unit": "mL"},
    {"stock_id": "s", "amount_decimal": "-1", "unit": "mL"},
    {"stock_id": "s", "amount_decimal": "lots", "unit": "mL"},
    {"stock_id": "s", "amount_decimal": "NaN", "unit": "mL"},
    {"stock_id": "s", "amount_decimal": "5", "unit": "kg"},
    {"stock_id": "s", "amount_decimal": "5", "unit": "g", "clear": True},
    {"stock_id": "s", "amount_decimal": "5", "unit": "g", "supplier": "x" * 121},
])
def test_a_bad_entry_is_refused_and_nothing_is_written(tmp_path, fields):
    log = tmp_path / "on_hand.jsonl"
    with pytest.raises(StockOnHandError):
        record_on_hand(path=log, **fields)
    assert not log.exists()


def test_a_hand_edit_breaks_the_chain_and_is_named(tmp_path):
    log = tmp_path / "on_hand.jsonl"
    record_on_hand(path=log, stock_id="s-hed", amount_decimal="12", unit="mL")
    record_on_hand(path=log, stock_id="s-iso", amount_decimal="40", unit="mL")
    lines = log.read_text(encoding="utf-8").splitlines()
    edited = json.loads(lines[0])
    edited["amount_decimal"] = "120"
    log.write_text("\n".join([json.dumps(edited), lines[1]]) + "\n", encoding="utf-8")

    with pytest.raises(StockOnHandLogCorruptError, match="line 1"):
        latest_on_hand(log)
    with pytest.raises(StockOnHandLogCorruptError):
        record_on_hand(path=log, stock_id="s-hed", amount_decimal="1", unit="mL")
