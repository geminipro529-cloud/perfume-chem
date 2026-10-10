from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.api.v1.endpoints import ai as ai_endpoint
from app.schemas.perfume import AIAnalysisRequest
from app.services.ai import answer_check
from app.services.ai.prompts.perfume_analysis import CHEMISTRY_SYSTEM_CONTEXT

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"
OWNED = frozenset({"hedione", "iso e super"})


def test_unowned_material_is_flagged_and_owned_is_not() -> None:
    answer = {
        "modifications": {
            "to_add": [{"name": "Hedione 10%"}, {"name": "Unobtainium Musk"}]
        }
    }
    result = answer_check.check_answer(answer, OWNED)
    assert result == {"checked": True, "not_in_stock": ["Unobtainium Musk"]}


def test_raw_text_rows_are_checked_and_no_fuzzy_match() -> None:
    result = answer_check.check_answer(
        {"raw_analysis": "- Hedione: 10%\n- Hedionee: 5%\nplain prose"}, OWNED
    )
    assert result["not_in_stock"] == ["Hedionee"]


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
    assert out["inventory_check"] == {"checked": True, "not_in_stock": ["Ghost Amber"]}


def test_hedione_prompt_guidance_matches_project_rule() -> None:
    assert "Hedione: MAX 12%" in CHEMISTRY_SYSTEM_CONTEXT
    assert "chypre" in CHEMISTRY_SYSTEM_CONTEXT
    assert "(Linalool, Hedione): MAX 15%" not in CHEMISTRY_SYSTEM_CONTEXT


def test_assistant_view_uses_plain_wording() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "lab.js").read_text(encoding="utf-8")
    for jargon in ("Build canonical packet", "Claim boundary", "Unknown stays visible"):
        assert jargon not in html
    assert '<option value="bottle_status">' in html
    assert 'id="assistant-summary"' in html and "<details>" in html
    assert "not known yet" in js
    summary = js[js.index("function renderAssistantSummary") :].split("\n}\n")[0]
    assert "innerHTML" not in summary


def test_unreadable_inventory_does_not_break_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> frozenset[str]:
        raise OSError("inventory.txt missing")

    monkeypatch.setattr(answer_check, "owned_keys", boom)
    result = answer_check.check_answer({"modifications": {"to_add": [{"name": "Hedione"}]}})
    assert result == {"checked": False, "not_in_stock": []}
