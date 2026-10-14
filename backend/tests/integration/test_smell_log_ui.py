"""The Bottles page smell log: script wiring and the form's pure rules."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.lab_page_scripts import get_lab_script

SMELL_LOG_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "smell-log.js"


@pytest.mark.asyncio
async def test_bottles_page_loads_the_smell_log_and_the_bottles_page_hooks_it(client):
    page = await client.get("/app")
    javascript = await get_lab_script(client)
    smell_log = await client.get("/static/smell-log.js")

    assert smell_log.status_code == 200
    assert page.text.index('src="/static/smell-log.js"') < page.text.index('src="/static/lab/core.js"')
    bottles_panel = page.text[page.text.index('data-panel="bottles"'):]
    assert bottles_panel.index('id="smell-log"') < bottles_panel.index("</section>")
    assert 'typeof attachSmellLog === "function"' in javascript.text
    assert 'attachSmellLog({ doc: document, request, root: $("#smell-log") })' in javascript.text
    assert "smellLog?.setBottles(bottles);" in javascript.text
    assert "/smell-log`" in smell_log.text
    assert "/smell-log/comparison`" in smell_log.text
    assert 'request("/smell-log/calibration")' in smell_log.text
    assert "Model said / you smelled" in smell_log.text
    assert "detection screen" in smell_log.text
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


def test_comparison_block_reads_names_in_order_and_one_agreement_line():
    result = _node(
        """
const inRange = m.smellCompareLines({
  window: "strip_10m", label: "Strip 10 min", n_entries: 2, liking_mean: 7.5,
  you_leads: [{ name: "Linalool", count: 2 }, { name: "Musk", count: 1 }], you_weak: [{ name: "Ambrox", count: 1 }],
  model_in_range: true, model_time_label: "10 min", model_top: ["Linalool", "Ambrox", "Hedione"],
  agreement: {
    leads_the_model_also_had_on_top: ["Linalool"], model_top_you_did_not_mark_leading: ["Ambrox", "Hedione"],
    you_marked_weak_but_model_had_on_top: ["Ambrox"], leads_the_model_did_not_have_on_top: ["Musk"],
  },
});
const beyond = m.smellCompareLines({
  window: "skin_day7", label: "Skin day 7", n_entries: 1, liking_mean: null, you_leads: [], you_weak: [],
  model_in_range: false, model_time_label: null, model_top: [], agreement: null,
  model_note: "Beyond the model's range: its time curve stops at 4 h, so it says nothing about skin day 7.",
});
console.log(JSON.stringify({ inRange, beyond }));
"""
    )

    assert result["inRange"] == {
        "title": "Strip 10 min · 2 entries · liked 7.5/10",
        "model": "Model, 10 min: Linalool, Ambrox, Hedione",
        "you": "You: leads Linalool ×2, Musk · weak Ambrox",
        "corrected": "",
        "agreement": (
            "Model and you agree on Linalool. You smelled Musk leading; the model didn't have it on top. "
            "You marked Ambrox weak; the model had it on top."
        ),
    }
    assert result["beyond"] == {
        "title": "Skin day 7 · 1 entry",
        "model": "Beyond the model's range: its time curve stops at 4 h, so it says nothing about skin day 7.",
        "you": "You: no names marked",
        "corrected": "",
        "agreement": "",
    }


def test_calibration_line_and_corrected_line_follow_the_gates():
    result = _node(
        """
const lines = [
  { calibrated: false, n_bottles: 3, min_bottles: 10, reason: "3 of 10 bottles logged" },
  { calibrated: false, n_bottles: 10, min_bottles: 10,
    reason: "10 bottles logged; the correction does not beat the plain model yet, so it is not used." },
  { calibrated: true, n_bottles: 12, min_bottles: 10, reason: null },
].map(m.smellCalibrationLine);
const block = {
  window: "strip_1h", label: "Strip 1 h", n_entries: 1, liking_mean: null, you_leads: [], you_weak: [],
  model_in_range: true, model_time_label: "1 h", model_top: ["Linalool", "Lavender EO", "Iso E Super"],
  agreement: { leads_the_model_also_had_on_top: [], model_top_you_did_not_mark_leading: [],
    you_marked_weak_but_model_had_on_top: [], leads_the_model_did_not_have_on_top: [] },
};
const corrected = m.smellCompareLines({ ...block, corrected_top: ["Linalool", "Lavender EO", "Hedione"] }).corrected;
const plain = m.smellCompareLines({ ...block, corrected_top: null }).corrected;
console.log(JSON.stringify({ lines, corrected, plain }));
"""
    )

    assert result["lines"] == [
        "Learning from your nose: 3 of 10 bottles logged",
        "10 bottles logged; the correction does not beat the plain model yet, so it is not used.",
        "Model corrected by your nose (12 bottles, beats the plain model on held-out bottles)",
    ]
    assert result["corrected"] == "Corrected: Linalool, Lavender EO, Hedione"
    assert result["plain"] == ""


def test_chart_rows_order_by_the_models_place_and_mark_agreement_and_clashes():
    result = _node(
        """
const ranks = { "Linalool": 1, "Hedione": 2, "Lavender EO": 3, "Ambrox": 7, "Iris": null };
const block = (window, label, leads, weak, corrected_top) => ({
  window, label, model_in_range: true, model_ranks: ranks, corrected_top,
  you_leads: leads.map((name) => ({ name, count: name === "Ambrox" ? 2 : 1 })),
  you_weak: weak.map((name) => ({ name, count: 1 })),
});
const data = {
  calibrated: true,
  windows: [
    block("strip_10m", "Strip 10 min", ["Linalool", "Ambrox"], ["hedione"], ["Linalool", "Ambrox", "Lavender EO"]),
    block("strip_1h", "Strip 1 h", ["Iris"], [], null),
    { window: "skin_day1", label: "Skin day 1", model_in_range: false, you_leads: [], you_weak: [] },
  ],
  corrections: [
    { name: "Ambrox", n_bottles: 10, min_bottles: 3, used: true, label: "×2.0" },
    { name: "Hedione", n_bottles: 2, min_bottles: 3, used: false, label: null },
    { name: "Iris", n_bottles: 0, min_bottles: 3, used: false, label: null },
  ],
};
const chart = m.smellChartModel(data);
const none = m.smellChartModel({ windows: [data.windows[2]] });
const unused = m.smellCorrectionText({ name: "Ambrox", n_bottles: 4, min_bottles: 3, used: false }, false);
console.log(JSON.stringify({ chart, none, unused }));
"""
    )

    chart = result["chart"]
    assert chart["columns"] == [{"key": "strip_10m", "label": "Strip 10 min"}, {"key": "strip_1h", "label": "Strip 1 h"}]
    assert [row["name"] for row in chart["rows"]] == ["Linalool", "Hedione", "Lavender EO", "Ambrox", "Iris"]
    cells = {row["name"]: row["cells"][0] for row in chart["rows"]}
    assert cells["Linalool"] == {"text": "1st · you: leads", "state": "agree"}
    assert cells["Hedione"] == {"text": "2nd · you: weak", "state": "clash"}
    assert cells["Ambrox"] == {"text": "7th · corrected 2nd · you: leads ×2", "state": "missed"}
    assert cells["Lavender EO"] == {"text": "3rd", "state": ""}
    assert chart["rows"][4]["cells"][1] == {"text": "not ranked · you: leads", "state": "missed"}
    corrections = {row["name"]: row["correction"] for row in chart["rows"]}
    assert corrections == {
        "Linalool": "not in the model", "Hedione": "none yet: 2 of 3 bottles", "Lavender EO": "not in the model",
        "Ambrox": "×2.0 from 10 bottles", "Iris": "not in the model",
    }
    assert result["none"] is None
    assert result["unused"] == "not used yet: 4 bottles"
