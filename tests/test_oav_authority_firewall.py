from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.pipeline.oav_authority import (
    OAVAuthorityError,
    OAVAuthorityRequest,
    analyze_oav_authority,
)


def _request(receipt_sha: str | None = None) -> OAVAuthorityRequest:
    return OAVAuthorityRequest(
        formula_name="x",
        ingredients_ul={"Hedione": 1.0},
        dose_receipt_sha256=receipt_sha,
    )


def test_unbound_oav_is_blocked_by_default_before_legacy_analysis(monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(
        "engine.pipeline.oav_authority._legacy_analyze",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    with pytest.raises(OAVAuthorityError):
        analyze_oav_authority(_request())
    assert calls == []


def test_explicit_exploratory_mode_is_only_unbound_escape_hatch(monkeypatch):
    calls: list[object] = []

    def fake(request, *, gate_report=None):
        calls.append((request, gate_report))
        return "ok"

    monkeypatch.setattr("engine.pipeline.oav_authority._legacy_analyze", fake)
    assert (
        analyze_oav_authority(
            _request(),
            allow_unbound_exploratory=True,
        )
        == "ok"
    )
    assert len(calls) == 1
    assert calls[0][1] is None


def test_abstained_gate_receipt_blocks_before_legacy_analysis(monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(
        "engine.pipeline.oav_authority._legacy_analyze",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    gate_report = SimpleNamespace(
        dose_receipt=SimpleNamespace(
            status="ABSTAINED",
            receipt_sha256="a" * 64,
        )
    )
    with pytest.raises(OAVAuthorityError):
        analyze_oav_authority(_request(), gate_report=gate_report)
    assert calls == []


def test_bound_gate_receipt_is_injected_into_request(monkeypatch):
    seen: dict[str, object] = {}

    def fake(request, *, gate_report=None):
        seen["request"] = request
        seen["gate_report"] = gate_report
        return "ok"

    monkeypatch.setattr("engine.pipeline.oav_authority._legacy_analyze", fake)
    gate_report = SimpleNamespace(
        dose_receipt=SimpleNamespace(
            status="BOUND",
            receipt_sha256="a" * 64,
        )
    )
    assert analyze_oav_authority(_request(), gate_report=gate_report) == "ok"
    assert seen["request"].dose_receipt_sha256 == "a" * 64
    assert seen["gate_report"] is gate_report


def test_mismatched_explicit_receipt_is_rejected_before_legacy(monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(
        "engine.pipeline.oav_authority._legacy_analyze",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    gate_report = SimpleNamespace(
        dose_receipt=SimpleNamespace(
            status="BOUND",
            receipt_sha256="a" * 64,
        )
    )
    with pytest.raises(OAVAuthorityError):
        analyze_oav_authority(_request("b" * 64), gate_report=gate_report)
    assert calls == []
