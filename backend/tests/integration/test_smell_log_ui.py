"""The Bottles page smell log: script wiring and the form's pure rules."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SMELL_LOG_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "smell-log.js"


@pytest.mark.asyncio
async def test_bottles_page_loads_the_smell_log_and_lab_js_hooks_it(client):
    page = await client.get("/app")
    javascript = await client.get("/static/lab.js")
    smell_log = await client.get("/static/smell-log.js")

    assert smell_log.status_code == 200
    assert page.text.index('src="/static/smell-log.js"') < page.text.index('src="/static/lab.js"')
    bottles_panel = page.text[page.text.index('data-panel="bottles"'):]
    assert bottles_panel.index('id="smell-log"') < bottles_panel.index("</section>")
    assert 'typeof attachSmellLog === "function"' in javascript.text
    assert 'attachSmellLog({ doc: document, request, root: $("#smell-log") })' in javascript.text
    assert "smellLog?.setBottles(bottles);" in javascript.text
    assert "/smell-log`" in smell_log.text
    assert ".innerHTML" not in smell_log.text


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the smell log logic test needs it")
    program = f"const m = require({json.dumps(str(SMELL_LOG_JS))});\n{script}"
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
    )
    return json.loads(completed.stdout)


def test_chip_taps_cycle_leads_weak_clear_and_build_the_request_body():
    result = _node(
        """
const cycle = [undefined];
for (let i = 0; i < 3; i += 1) cycle.push(m.nextSmellChipState(cycle[cycle.length - 1]));
const chips = new Map([["Iris", "leads"], ["Ambrox", "weak"], ["Hedione", ""]]);
const body = m.smellLogBody({ window: "strip_1h", chips, leadsText: " Musk , ,", weakText: "", liking: "7", words: "  soft " });
const typedOnly = m.smellLogBody({ window: "skin_day7", chips: new Map(), leadsText: "", weakText: "Vanilla", liking: "", words: "" });
const line = m.smellLogLine(
  { window: "strip_1h", logged_at: "2026-10-12T10:00:00+00:00", leads: ["Iris"], weak: ["Ambrox"], liking: 7, words: "soft" },
  [{ key: "strip_1h", label: "Strip 1 h" }],
);
console.log(JSON.stringify({ cycle: cycle.slice(1), body, typedOnly, line }));
"""
    )

    assert result["cycle"] == ["leads", "weak", ""]
    assert result["body"] == {
        "window": "strip_1h", "leads": ["Iris", "Musk"], "weak": ["Ambrox"], "liking": 7, "words": "soft",
    }
    assert result["typedOnly"] == {
        "window": "skin_day7", "leads": [], "weak": ["Vanilla"], "liking": None, "words": "",
    }
    assert result["line"].startswith("Strip 1 h · ")
    assert result["line"].endswith("liked 7/10 · leads: Iris · weak: Ambrox · “soft”")
