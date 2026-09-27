"""Malformed authority files must fail closed with a stable domain error."""

import json

import pytest

from app.services import stock_strength_quarantine as quarantine


@pytest.mark.parametrize(
    "payload",
    [None, [], "invalid", {"source_triage": []}, {"inventory_authority": None}],
)
def test_malformed_quarantine_authority_is_rejected(tmp_path, monkeypatch, payload):
    authority_path = tmp_path / "quarantine.json"
    authority_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(quarantine, "_QUARANTINE_PATH", authority_path)
    with pytest.raises(quarantine.StockStrengthQuarantineError) as caught:
        quarantine._load_quarantine()
    assert caught.value.code == "STOCK_STRENGTH_QUARANTINE_AUTHORITY_INVALID"
