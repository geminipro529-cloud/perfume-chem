"""Smell strips on the phone (phone-strips.js): page wiring and the pure rules, run in Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.lab_page_scripts import get_lab_script

PHONE_STRIPS_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "phone-strips.js"


@pytest.mark.asyncio
async def test_the_bottles_view_carries_the_strips_panel_and_script(client):
    page = (await client.get("/app")).text
    javascript = (await get_lab_script(client)).text
    script = await client.get("/static/phone-strips.js")
    assert script.status_code == 200

    panel = page[page.index('data-panel="bottles"'):]
    assert panel.index('id="phone-strips-root"') < panel.index("</section>")
    # After smell-log.js, whose chip and request-body rules it uses; before the Lab scripts.
    assert page.index('src="/static/smell-log.js"') < page.index('src="/static/phone-strips.js"') < page.index('src="/static/lab/core.js"')
    assert 'attachPhoneStrips({ doc: document, request, root: $("#phone-strips-root") })' in javascript
    assert "phoneStripsPanel?.setBottles(bottles);" in javascript
    assert ".innerHTML" not in script.text
    assert "/smell-log`" in script.text and 'request("/smell-log/calibration")' in script.text


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the smell strips logic test needs it")
    program = (
        f"const m = require({json.dumps(str(PHONE_STRIPS_JS))});\n"
        "const dipped = Date.parse('2026-10-15T10:00:00Z');\n"
        "const at = (minutes) => dipped + minutes * 60000;\n"
        f"{script}"
    )
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
    )
    return json.loads(completed.stdout)


def test_each_check_opens_at_its_time_and_closes_at_one_and_a_half_times_it():
    result = _node(
        """
const strip = { dippedAt: "2026-10-15T10:00:00Z", logged: { strip_1h: "strip.x.strip_1h" } };
const statuses = (minutes) => m.phoneStripChecks(strip, at(minutes)).map((check) => check.status);
console.log(JSON.stringify({
  m5: statuses(5), m10: statuses(10), m15: statuses(15), m180: statuses(180), m270: statuses(270),
  next: m.phoneStripNext(m.phoneStripChecks(strip, at(5))).window,
  clock: [m.phoneStripClock(245000), m.phoneStripClock(3725000), m.phoneStripClock(-5)],
}));
"""
    )
    assert result["m5"] == ["waiting", "logged", "waiting"]
    assert result["m10"] == ["open", "logged", "waiting"]
    assert result["m15"] == ["missed", "logged", "waiting"]
    assert result["m180"] == ["missed", "logged", "open"]
    assert result["m270"] == ["missed", "logged", "missed"]
    assert result["next"] == "strip_10m"
    assert result["clock"] == ["4:05", "1:02:05", "0:00"]


def test_a_note_started_before_its_check_closed_stays_until_the_next_check_opens():
    result = _node(
        """
const strip = { dippedAt: "2026-10-15T10:00:00Z", logged: {} };
const late = (minutes, drafts) => {
  const checks = m.phoneStripChecks(strip, at(minutes));
  return m.phoneStripLateCheck(checks, (window) => drafts.includes(window), at(minutes))?.window ?? null;
};
console.log(JSON.stringify({
  stillOpen: late(12, ["strip_10m"]),
  closedWithNote: late(16, ["strip_10m"]),
  closedEmpty: late(16, []),
  beforeNext: late(59, ["strip_10m"]),
  nextOpened: late(60, ["strip_10m"]),
  latestWins: late(100, ["strip_10m", "strip_1h"]),
  lastCheck: late(400, ["strip_3h"]),
}));
"""
    )
    assert result == {
        "stillOpen": None,
        "closedWithNote": "strip_10m",
        "closedEmpty": None,
        "beforeNext": "strip_10m",
        "nextOpened": None,
        "latestWins": "strip_1h",
        "lastCheck": "strip_3h",
    }


def test_a_note_the_pc_would_refuse_is_named_before_it_is_kept():
    result = _node(
        """
const names = (count) => Array.from({ length: count }, (_unused, index) => `Name ${index}`);
console.log(JSON.stringify({
  both: m.phoneStripsProblem("en", { leads: ["Orris", "Musk"], weak: [" orris "] }),
  bothThai: m.phoneStripsProblem("th", { leads: ["Orris"], weak: ["ORRIS"] }),
  tooManyLeads: m.phoneStripsProblem("en", { leads: names(13), weak: [] }),
  tooManyWeak: m.phoneStripsProblem("en", { leads: [], weak: names(13) }),
  repeatsCountOnce: m.phoneStripsProblem("en", { leads: [...names(12), "name 0"], weak: [] }),
  fine: m.phoneStripsProblem("en", { leads: ["Orris"], weak: ["Musk"] }),
}));
"""
    )
    assert result["both"] == "Orris: marked both leading and weak. Pick one for each."
    assert result["bothThai"] == "Orris: เลือกไว้ทั้งเด่นและจาง เลือกได้อย่างเดียวต่อชื่อ"
    assert result["tooManyLeads"] == result["tooManyWeak"] == "Mark at most 12 names as leading, and 12 as weak."
    assert result["repeatsCountOnce"] == ""
    assert result["fine"] == ""


def test_a_kept_note_reads_in_one_line_and_goes_oldest_first():
    result = _node(
        """
const note = { clientId: "strip.b.strip_1h", window: "strip_1h", liking: 7, leads: ["Iso E Super"], weak: ["Ambrox"], words: "dry", loggedAt: "2026-10-15T11:01:00.000Z" };
const outbox = {
  b: note,
  a: { clientId: "strip.a.strip_10m", window: "strip_10m", leads: [], weak: [], liking: null, words: "", loggedAt: "2026-10-15T10:11:00.000Z" },
  r: { clientId: "strip.r.strip_3h", window: "strip_3h", refused: true, loggedAt: "2026-10-15T09:00:00.000Z" },
};
console.log(JSON.stringify({
  en: m.phoneStripsNoteText("en", note),
  th: m.phoneStripsNoteText("th", { window: "strip_10m", liking: 4, leads: [], weak: [], words: "" }),
  order: m.phoneStripsToSend(outbox).map((item) => item.clientId),
  body: m.phoneStripNoteBody(note),
}));
"""
    )
    assert result["en"] == "1 h · 7/10 · leads: Iso E Super · weak: Ambrox · “dry”"
    assert result["th"] == "10 นาที · 4/10"
    assert result["order"] == ["strip.a.strip_10m", "strip.b.strip_1h"]
    assert result["body"] == {
        "window": "strip_1h", "leads": ["Iso E Super"], "weak": ["Ambrox"], "liking": 7, "words": "dry",
        "logged_at": "2026-10-15T11:01:00.000Z", "client_id": "strip.b.strip_1h",
    }
