"""Phone bench mode (phone-bench.js): page wiring and the pure rules, run in Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.lab_page_scripts import get_lab_script

PHONE_BENCH_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "phone-bench.js"
BENCH_SHEET_JS = PHONE_BENCH_JS.with_name("bench-sheet.js")


@pytest.mark.asyncio
async def test_the_batch_view_carries_the_bench_panel_script_and_styles(client):
    page = (await client.get("/app")).text
    javascript = (await get_lab_script(client)).text
    script = await client.get("/static/phone-bench.js")
    assert script.status_code == 200
    assert (await client.get("/static/phone-bench.css")).status_code == 200

    panel = page[page.index('data-panel="batch"'):]
    assert panel.index('id="phone-bench-root"') < panel.index('id="batch-root"') < panel.index('id="batch-label-area"')
    # After bench-sheet.js, whose exact-number and grams rules it uses; before the Lab scripts.
    assert page.index('src="/static/bench-sheet.js"') < page.index('src="/static/phone-bench.js"') < page.index('src="/static/lab/core.js"')
    assert page.index('href="/static/phone-bench.css"') < page.index("</head>")
    assert 'attachPhoneBench({ doc: document, request, root: $("#phone-bench-root") })' in javascript
    assert 'if (view === "batch" && typeof phoneBenchShown === "function") phoneBenchShown();' in javascript
    assert ".innerHTML" not in script.text
    # A batch just recorded on the Batch view opens in bench mode from its weighed-amounts step.
    assert "openPhoneBench(record.lot)" in (await client.get("/static/batch.js")).text
    for path in ("/v2/batches`", "/actuals`", "/v2/workbench/material-densities"):
        assert path.replace("`", "") in script.text


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the phone bench logic test needs it")
    program = (
        f"const m = require({json.dumps(str(PHONE_BENCH_JS))});\n"
        f"const b = require({json.dumps(str(BENCH_SHEET_JS))});\n{script}"
    )
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
    )
    return json.loads(completed.stdout)


RECORD = {
    "lot": "KS-1",
    "planned_rows": [
        {"line": 1, "material": "Hedione", "strength": "neat", "unit": "uL", "planned_amount": "10290",
         "concentration_fraction_decimal": None, "concentration_basis": "NEAT"},
        {"line": 2, "material": "Resin", "strength": "50%", "unit": "mg", "planned_amount": "100",
         "concentration_fraction_decimal": "0.5", "concentration_basis": "W_W"},
        {"line": 3, "material": "Musk", "strength": "neat", "unit": "mg", "planned_amount": "99"},
        {"line": 4, "material": "Damascone", "strength": "1%", "unit": "uL", "planned_amount": "8",
         "concentration_fraction_decimal": "0.01", "concentration_basis": "UNKNOWN"},
        {"line": 5, "material": "Rare", "strength": "neat", "unit": "uL", "planned_amount": "500",
         "concentration_fraction_decimal": None, "concentration_basis": "NEAT"},
    ],
}


def _steps_js():
    return f"""
const record = {json.dumps(RECORD)};
const rows = m.phoneBenchSourceRows(record).map(b.benchRowFromSource);
const steps = m.phoneBenchSteps(record, b.benchRowsInGrams(b.benchMatchStocks(rows, null).rows, {{ Hedione: "0.998" }}).rows);
"""


def test_steps_read_in_grams_where_the_bench_sheet_would_weigh_them():
    steps = _node(_steps_js() + "console.log(JSON.stringify(steps));")

    assert [(step["line"], step["unit"], step["planned"], step["grams"], step["density"]) for step in steps] == [
        (1, "µL", "10290", "10.269", "0.998"),  # 10290 µL × 0.998 g/mL
        (2, "mg", "100", "0.100", None),  # a solid of 100 mg or more is weighed in grams
        (3, "mg", "99", None, None),
        (4, "µL", "8", None, None),  # under 0.1 g: pipetted
        (5, "µL", "500", None, None),  # no density known
    ]


def test_an_entry_becomes_grams_with_the_density_or_the_line_s_own_unit():
    result = _node(_steps_js() + """
const entries = {};
for (const [index, by, typed] of [[0, "g", "10,31"], [1, "g", "0.1"], [2, "g", "99"], [3, "unit", "8"], [0, "unit", "10290"]]) {
  const made = m.phoneBenchEntry(steps[index], by, typed);
  if (index !== 0 || by === "g") entries[steps[index].line] = made.entry;
}
const unitEntry = m.phoneBenchEntry(steps[0], "unit", "10290").entry;
console.log(JSON.stringify({
  body: m.phoneBenchBody({ entries: { 4: entries[4], 1: entries[1], 2: entries[2], 3: entries[3] }, notes: "  ok " }),
  unit: m.phoneBenchActual(unitEntry),
  bad: ["", "1.2.3", "-1", "abc"].map((typed) => m.phoneBenchEntry(steps[0], "g", typed)),
}));
""")

    assert result["body"] == {"actuals": [
        {"line": 1, "weighed_g": "10.31", "density_g_ml": "0.998"},
        {"line": 2, "weighed_g": "0.1"},
        {"line": 3, "actual_amount": "99"},
        {"line": 4, "actual_amount": "8"},
    ], "notes": "ok"}
    assert result["unit"] == {"line": 1, "actual_amount": "10290"}
    assert result["bad"] == [{"error": "typeNumber"}] * 4


def test_deviation_seed_and_the_next_line_to_weigh():
    result = _node(_steps_js() + """
console.log(JSON.stringify({
  gaps: [["10.3", "10.269"], ["1", "1"], ["0.2", "0.21"], ["1.0001", "1"], ["5", "0"]].map(([a, p]) => m.phoneBenchDeviation(a, p)),
  seed: m.phoneBenchSeed(steps, [
    { line: 1, unit: "uL", actual_amount: "10330.7", weighed_g: "10.31", density_g_ml: "0.998" },
    { line: 4, unit: "uL", actual_amount: "9" },
    { line: 99, unit: "uL", actual_amount: "1" },
  ]),
  next: [m.phoneBenchNextIndex(steps, { 1: {} }, 0), m.phoneBenchNextIndex(steps, { 2: {}, 3: {}, 4: {}, 5: {} }, 3),
         m.phoneBenchNextIndex(steps, { 1: {}, 2: {}, 3: {}, 4: {}, 5: {} }, 0)],
}));
""")

    assert result["gaps"] == [
        {"kind": "over", "percent": "0.3"}, {"kind": "same", "percent": "0"},
        {"kind": "under", "percent": "4.8"}, {"kind": "over", "percent": "0.01"}, None,
    ]
    assert result["seed"] == {
        "1": {"line": 1, "typed": "10.31", "unit": "g", "planned": "10.269", "density": "0.998"},
        "4": {"line": 4, "typed": "9", "unit": "µL", "planned": "8", "density": None},
    }
    assert result["next"] == [1, 0, 5]


def test_progress_is_kept_per_lot_with_its_batch_and_lots_to_send_are_found():
    result = _node("""
const memory = new Map();
const storage = { getItem: (k) => memory.has(k) ? memory.get(k) : null, setItem: (k, v) => memory.set(k, String(v)),
  get length() { return memory.size; }, key: (i) => [...memory.keys()][i] ?? null };
const kept = (lot, more) => ({ lot, batch: "2026-10-15T09:00:00+00:00", steps: [], entries: {}, base: { entries: {}, notes: "", version: 0 }, ...more });
m.phoneBenchKeep(storage, kept("B-2", { pending: true }));
m.phoneBenchKeep(storage, kept("A-1", { pending: true }));
m.phoneBenchKeep(storage, kept("C-3", { pending: false }));
m.phoneBenchKeep(storage, kept("F-6", { pending: true, error: "refused" }));
m.phoneBenchKeep(storage, kept("G-7", { pending: true, conflict: { lines: [], notes: "x" } }));
m.phoneBenchSetAside(storage, kept("A-1", { pending: true, batch: "2026-10-01T09:00:00+00:00" }));
storage.setItem(m.PHONE_BENCH_STORE + "D-4", "{not json");
storage.setItem(m.PHONE_BENCH_STORE + "E-5", JSON.stringify({ lot: "other", steps: [], pending: true }));
storage.setItem(m.PHONE_BENCH_STORE + "H-8", JSON.stringify({ lot: "H-8", steps: [], entries: {}, pending: true }));
const full = { getItem: () => null, setItem: () => { throw new Error("quota"); } };
console.log(JSON.stringify({
  pending: m.phoneBenchPendingLots(storage),
  loaded: m.phoneBenchLoad(storage, "A-1").batch,
  aside: JSON.parse(storage.getItem(m.PHONE_BENCH_ASIDE + "A-1.2026-10-01T09:00:00+00:00")).lot,
  broken: m.phoneBenchLoad(storage, "D-4"),
  noBatch: m.phoneBenchLoad(storage, "H-8"),
  full: m.phoneBenchKeep(full, { lot: "X" }),
}));
""")

    # Lots with a refusal or a choice waiting on the person are not sent on their own;
    # a copy that doesn't name its batch is not used.
    assert result == {
        "pending": ["A-1", "B-2"], "loaded": "2026-10-15T09:00:00+00:00", "aside": "A-1",
        "broken": None, "noBatch": None, "full": False,
    }


def test_a_send_says_which_batch_and_saved_set_it_was_built_on():
    result = _node(_steps_js() + """
const saved = { recorded_at: "2026-10-15T09:00:00+00:00", actuals_version: 2, actual_notes: "from the PC",
  actuals: [{ line: 4, unit: "uL", actual_amount: "9" }] };
const server = m.phoneBenchServer(steps, saved);
console.log(JSON.stringify({
  server,
  body: m.phoneBenchBody({ batch: saved.recorded_at, base: server, entries: server.entries, notes: "" }),
}));
""")

    assert result["server"] == {
        "entries": {"4": {"line": 4, "typed": "9", "unit": "µL", "planned": "8", "density": None}},
        "notes": "from the PC",
        "version": 2,
    }
    assert result["body"] == {
        "actuals": [{"line": 4, "actual_amount": "9"}], "notes": "",
        "based_on": 2, "batch_recorded_at": "2026-10-15T09:00:00+00:00",
    }


def test_the_phone_and_the_pc_merge_line_by_line_and_only_a_line_both_changed_waits():
    result = _node("""
const g = (line, typed, density = "0.998") => ({ line, typed, unit: "g", planned: "10.269", density });
const ul = (line, typed) => ({ line, typed, unit: "µL", planned: "8", density: null });
const base = { entries: { 1: g(1, "10.3") }, notes: "", version: 1 };
console.log(JSON.stringify({
  // The PC weighed line 4, the phone line 2: both kept, nothing to choose.
  apart: m.phoneBenchMerge(base, { entries: { 1: g(1, "10.3"), 4: ul(4, "9") }, notes: "" }, { entries: { 1: g(1, "10.3"), 2: g(2, "0.1", null) }, notes: "" }),
  // Only the PC changed line 1; only the phone changed it.
  pcOnly: m.phoneBenchMerge(base, { entries: { 1: g(1, "10.25") }, notes: "" }, { entries: { 1: g(1, "10.3") }, notes: "" }).entries,
  phoneOnly: m.phoneBenchMerge(base, { entries: { 1: g(1, "10.3") }, notes: "" }, { entries: { 1: g(1, "10.31") }, notes: "" }).entries,
  // Both changed line 1 to the same amount, written differently.
  sameAmount: m.phoneBenchMerge(base, { entries: { 1: g(1, "10.31") }, notes: "" }, { entries: { 1: g(1, "10.310") }, notes: "" }).conflict,
  // Both changed line 1 to different amounts: the phone's stays until the person chooses.
  both: m.phoneBenchMerge(base, { entries: { 1: ul(1, "10290") }, notes: "" }, { entries: { 1: g(1, "10.31") }, notes: "" }),
  // Blank notes on the phone take the PC's; notes changed on both wait too.
  notes: [
    m.phoneBenchMerge(base, { entries: base.entries, notes: "pc" }, { entries: base.entries, notes: "" }),
    m.phoneBenchMerge({ ...base, notes: "was" }, { entries: base.entries, notes: "was" }, { entries: base.entries, notes: "phone" }).notes,
    m.phoneBenchMerge({ ...base, notes: "was" }, { entries: base.entries, notes: "pc" }, { entries: base.entries, notes: "phone" }).conflict,
  ],
  changed: [
    m.phoneBenchChanged({ base, entries: { 1: g(1, "10.300") }, notes: "" }),
    m.phoneBenchChanged({ base: { ...base, notes: "pc" }, entries: base.entries, notes: "  " }),
    m.phoneBenchChanged({ base, entries: { 1: g(1, "10.3"), 2: ul(2, "1") }, notes: "" }),
    m.phoneBenchChanged({ base, entries: base.entries, notes: "smells right" }),
  ],
}));
""")

    assert result["apart"]["conflict"] is None
    assert sorted(result["apart"]["entries"]) == ["1", "2", "4"]
    assert result["pcOnly"]["1"]["typed"] == "10.25"
    assert result["phoneOnly"]["1"]["typed"] == "10.31"
    assert result["sameAmount"] is None
    assert result["both"]["conflict"] == {
        "lines": [{"line": 1, "pc": {"line": 1, "typed": "10290", "unit": "µL", "planned": "8", "density": None}}], "notes": None,
    }
    assert result["both"]["entries"]["1"]["typed"] == "10.31"
    assert result["notes"][0]["notes"] == "pc" and result["notes"][0]["conflict"] is None
    assert result["notes"][1] == "phone"
    assert result["notes"][2] == {"lines": [], "notes": "pc"}
    assert result["changed"] == [False, False, True, True]


def test_thai_has_every_english_phrase_and_fills_the_same_blanks():
    result = _node("""
const blanks = (text) => [...text.matchAll(/\\{(\\w+)\\}/g)].map((match) => match[1]).sort();
const en = m.PHONE_BENCH_WORDS.en, th = m.PHONE_BENCH_WORDS.th;
console.log(JSON.stringify({
  missing: Object.keys(en).filter((key) => !(key in th)),
  extra: Object.keys(th).filter((key) => !(key in en)),
  blanks: Object.keys(en).filter((key) => key in th && JSON.stringify(blanks(en[key])) !== JSON.stringify(blanks(th[key]))),
  said: m.phoneBenchSay("th", "lineOf", { n: 3, total: 18 }),
  fallback: m.phoneBenchSay("xx", "over", { percent: "2" }),
}));
""")

    assert result == {"missing": [], "extra": [], "blanks": [], "said": "รายการที่ 3 จาก 18", "fallback": "2% over the plan"}
