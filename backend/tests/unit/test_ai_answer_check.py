from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.api.v1.endpoints import ai as ai_endpoint
from app.schemas.perfume import AIAnalysisRequest
from app.services.ai import answer_check
from app.services.context_builder import ContextBuilder

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"
OWNED = frozenset({"hedione", "iso e super"})


def test_unowned_material_is_flagged_and_owned_is_not() -> None:
    answer = {
        "modifications": {
            "to_add": [{"name": "Hedione 10%"}, {"name": "Unobtainium Musk"}]
        }
    }
    result = answer_check.check_answer(answer, OWNED)
    assert result == {"checked": True, "not_matched": ["Unobtainium Musk"]}


def test_raw_text_fallback_is_not_checked() -> None:
    for key in ("raw_analysis", "raw_suggestions", "raw_pairings"):
        result = answer_check.check_answer({key: "```json\n{\"x\": 1}\n``` - Ghost: 5%"}, OWNED)
        assert result == {"checked": False, "not_matched": []}


def test_long_raw_line_is_fast() -> None:
    start = time.perf_counter()
    result = answer_check.check_answer({"raw_analysis": "- a" + " 1" * 8000 + "\n"}, OWNED)
    assert result["checked"] is False
    assert time.perf_counter() - start < 0.5


def test_owned_stock_is_matched_through_aliases_and_noise() -> None:
    stock = answer_check.owned_keys()
    answer = {
        "classic_pairings": [
            {"ingredient": n}
            for n in ("Bergamot", "Bergamot oil", "DPG", "Galaxolide 50", "ISO E SUPER®", "Hedione 10%")
        ]
        + [{"ingredient": "Unobtainium Musk"}]
    }
    result = answer_check.check_answer(answer, stock)
    assert result == {"checked": True, "not_matched": ["Unobtainium Musk"]}


def test_cost_optimization_with_is_scanned() -> None:
    answer = {"cost_optimization": [{"replace": "Hedione", "with": "Ghost Amber"}]}
    result = answer_check.check_answer(answer, OWNED)
    assert result["not_matched"] == ["Ghost Amber"]


def test_non_dict_model_answer_does_not_500(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAI:
        async def suggest_pairings(self, **_k: Any) -> Any:
            return ["Hedione", "Iso E Super"]

    from app.schemas.perfume import AIPairingRequest

    out = asyncio.run(
        ai_endpoint.suggest_pairings(AIPairingRequest(ingredient="Hedione"), ai_service=FakeAI())  # type: ignore[arg-type]
    )
    assert out == ["Hedione", "Iso E Super"]


def test_endpoint_adds_inventory_check(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_enqueue(*_a: Any, **_k: Any) -> Any:
        return SimpleNamespace(to_dict=lambda: {})

    monkeypatch.setattr(ai_endpoint, "enqueue_formula_analysis_compatibility", fake_enqueue)
    monkeypatch.setattr(ai_endpoint, "validate_formula", lambda _f: None)
    monkeypatch.setattr(answer_check, "owned_keys", lambda: OWNED)

    class FakeAI:
        async def analyze_perfume(self, **_k: Any) -> dict[str, Any]:
            return {"chemistry_insights": {"suggested_fixatives": ["Iso E Super", "Ghost Amber"]}}

    request = AIAnalysisRequest(
        name="t", concentration=15.0, ingredients=[{"name": "Hedione", "percentage": 10.0}]
    )
    out = asyncio.run(ai_endpoint.analyze_perfume(request, ai_service=FakeAI(), session=None))  # type: ignore[arg-type]
    assert out["inventory_check"] == {"checked": True, "not_matched": ["Ghost Amber"]}


def test_hedione_guidance_in_rendered_prompt_context() -> None:
    builder = ContextBuilder()
    dosage = [ln for ln in builder._get_dosage_guidelines().splitlines() if "**Hedione**" in ln]
    assert dosage, "Hedione missing from rendered dosage guidelines"
    for line in dosage:
        assert "12%" in line and "chypre" in line and "15%" in line
        assert "30" not in line and "liberally" not in line
    inventory = [ln for ln in builder._get_inventory_context().splitlines() if "**Hedione**" in ln]
    assert any("(5.0-15.0%)" in ln for ln in inventory)
    assert not any("30.0%" in ln for ln in inventory)


def test_assistant_view_uses_plain_wording() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "lab.js").read_text(encoding="utf-8")
    for jargon in ("Build canonical packet", "Claim boundary", "Unknown stays visible"):
        assert jargon not in html
    assert '<option value="bottle_status">' in html
    assert "Bottle or formula ID" in html and "Bottle or formula name" not in html
    assert 'id="assistant-summary"' in html and "<details>" in html
    assert "not known yet" in js
    summary = js[js.index("function renderAssistantSummary") :].split("\n}\n")[0]
    assert "innerHTML" not in summary


def test_unreadable_inventory_does_not_break_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> frozenset[str]:
        raise OSError("inventory.txt missing")

    monkeypatch.setattr(answer_check, "owned_keys", boom)
    result = answer_check.check_answer({"modifications": {"to_add": [{"name": "Hedione"}]}})
    assert result == {"checked": False, "not_matched": []}
