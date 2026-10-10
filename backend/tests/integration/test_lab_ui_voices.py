import json
import shutil
import subprocess
from pathlib import Path

import pytest

FORMULA_VOICES_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "formula-voices.js"
NOTE = "Screening model only: not a measured smell."


def _window(label, voices, detectable):
    return {"label": label, "detectable_components": detectable, "of_materials": 12, "effective_voices": voices}


def _run_voices(summary):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the formula-voices wording test needs it")
    program = (
        f"const voices = require({json.dumps(str(FORMULA_VOICES_JS))});\n"
        f"process.stdout.write(JSON.stringify(voices.formulaVoiceLines({json.dumps(summary)})));"
    )
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def test_voices_show_heart_count_detectable_notes_and_every_flag():
    summary = {
        "status": "OK",
        "note": NOTE,
        "windows": [_window("opening", 7.4, 9), _window("heart", 3.6, 6), _window("drydown", 2.2, 4)],
        "flags": [
            {"flag": "one_note", "message": "one-note risk: smell-check. Through heart and drydown Hedione leads."},
            {"flag": "similar_to_variant_2", "message": "close to variant 2: the modeled profiles are nearly the same.", "variant": 2},
        ],
        "overall_score": None,
    }
    result = _run_voices(summary)

    assert result["lines"] == [
        "About 4 voices in the heart (model)",
        "Detectable notes: opening 9, heart 6, drydown 4",
        "one-note risk: smell-check. Through heart and drydown Hedione leads.",
        "close to variant 2: the modeled profiles are nearly the same.",
    ]
    assert result["note"] == NOTE
    assert "score" not in json.dumps(result).lower()


def test_voices_without_flags_show_only_counts_and_the_note():
    summary = {"note": NOTE, "windows": [_window("heart", 5.0, 8)], "flags": []}
    result = _run_voices(summary)

    assert result["lines"] == ["About 5 voices in the heart (model)", "Detectable notes: heart 8"]
    assert result["note"] == NOTE
    assert _run_voices(None) is None


@pytest.mark.asyncio
async def test_formula_card_shows_the_voice_summary(client):
    page = await client.get("/app")
    javascript = await client.get("/static/lab.js")
    helper = await client.get("/static/formula-voices.js")

    assert helper.status_code == 200
    assert page.text.index('src="/static/formula-voices.js"') < page.text.index('src="/static/lab.js"')
    assert page.text.index('id="formula-result-checks"') < page.text.index('id="formula-result-voices"') < page.text.index('id="formula-result-rows"')
    assert "formulaVoiceLines(complexitySummary)" in javascript.text
    assert "selected.variant ? selected.variant.complexity_summary : result.complexity_summary" in javascript.text
