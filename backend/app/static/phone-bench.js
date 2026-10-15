"use strict";

// Phone bench mode: weigh a recorded batch one line at a time, in big numbers,
// in grams where the stock's density is known, in English or Thai.
//
// Once a batch is open it works without the network: its steps and every
// amount typed are kept in this browser's localStorage, and the weighed amounts
// go to the PC (POST /v2/batches/{lot}/actuals) whenever it answers. Each send
// carries every line weighed so far, so sending again changes nothing. A
// service worker could let the page itself reload offline, but browsers allow
// one only over HTTPS or on the PC itself, and the phone opens the app over
// plain http on the home network; so the page says to keep it open.
//
// Grams come from the bench sheet's rules (bench-sheet.js): a liquid line of at
// least 0.1 g whose stock density is known, or a solid of at least 100 mg. The
// PC works the line's µL out of the grams and the density sent with them.
//
// lab/bottles.js calls attachPhoneBench once; lab/core.js calls
// phoneBenchShown() when the Batch view opens. The DOM is built with
// createElement + textContent only, never HTML strings. Node loads the pure
// functions in the tests through module.exports.

const PHONE_BENCH_STORE = "perfumechem.bench.v1.";
const PHONE_BENCH_LANG = "perfumechem.bench.lang";
const PHONE_BENCH_RETRY_MS = 15000;
const PHONE_BENCH_GRAMS_FROM_MG = 100;
const PHONE_BENCH_NUMBER = /^\d+(\.\d+)?$/;

const phoneBenchExact = typeof benchFractionOf === "function"
  ? { benchFractionOf, benchFractionText, benchTimes, benchOver, benchMinus, benchCompare }
  : require("./bench-sheet.js");

const PHONE_BENCH_WORDS = {
  en: {
    panelTitle: "Weigh at the bench",
    panelHelp: "Open a recorded batch on your phone and weigh it one line at a time. If the Wi-Fi drops, carry on: what you weigh stays on this phone and goes to the PC when it answers again. Keep this page open; reloading it needs the PC.",
    loading: "Loading the recorded batches…",
    noBatches: "No batch is recorded yet. Record one in step 3 below, then weigh it here.",
    listFailed: "The recorded batches didn't load: {message}",
    weigh: "Weigh step by step",
    carryOn: "Carry on weighing",
    weighedCount: "{done} of {total} weighed",
    keptOnPhone: "{count} kept on this phone, not on the PC yet",
    opening: "Opening lot {lot}…",
    openFailed: "Lot {lot} didn't open: {message}",
    lineOf: "Line {n} of {total}",
    putIn: "Put in",
    onBalance: "on the balance; tare it first",
    withPipette: "with the pipette or a cylinder",
    stock: "Stock: {strength}",
    weighed: "Weighed",
    measured: "Measured",
    asPlanned: "As planned",
    saveNext: "Save, next",
    back: "Back",
    skip: "Skip for now",
    close: "Close",
    otherLanguage: "ไทย",
    otherLanguageName: "Thai",
    inGrams: "Grams",
    inUnits: "µL / mg",
    over: "{percent}% over the plan",
    under: "{percent}% under the plan",
    same: "Right on the plan",
    typeNumber: "Type a plain number, like 1.25",
    density: "Grams use the stock's density, {density} g/mL.",
    allDone: "Every line is weighed",
    someDone: "{done} of {total} weighed. Tap a line to weigh it.",
    notYet: "not yet",
    notes: "Notes",
    sendNow: "Send now",
    sending: "Sending to the PC…",
    savedAt: "On the PC, saved at {time}",
    waiting: "No connection to the PC. {count} kept on this phone; they go when it answers.",
    refused: "The PC refused these amounts: {message}",
    nothingYet: "Nothing weighed yet.",
  },
  th: {
    panelTitle: "ชั่งที่โต๊ะผสม",
    panelHelp: "เปิดแบทช์ที่บันทึกไว้บนโทรศัพท์ แล้วชั่งทีละรายการ ถ้า Wi-Fi หลุดก็ทำต่อได้เลย ค่าที่ชั่งจะเก็บไว้ในโทรศัพท์และส่งไปที่คอมพิวเตอร์เมื่อเชื่อมต่อได้อีกครั้ง อย่าปิดหน้านี้ การโหลดหน้าใหม่ต้องเชื่อมต่อคอมพิวเตอร์",
    loading: "กำลังโหลดแบทช์ที่บันทึกไว้…",
    noBatches: "ยังไม่มีแบทช์ที่บันทึกไว้ บันทึกแบทช์ในขั้นที่ 3 ด้านล่างก่อน แล้วมาชั่งที่นี่",
    listFailed: "โหลดแบทช์ที่บันทึกไว้ไม่ได้: {message}",
    weigh: "ชั่งทีละขั้น",
    carryOn: "ชั่งต่อ",
    weighedCount: "ชั่งแล้ว {done} จาก {total}",
    keptOnPhone: "เก็บไว้ในโทรศัพท์ {count} รายการ ยังไม่ถึงคอมพิวเตอร์",
    opening: "กำลังเปิดล็อต {lot}…",
    openFailed: "เปิดล็อต {lot} ไม่ได้: {message}",
    lineOf: "รายการที่ {n} จาก {total}",
    putIn: "ใส่",
    onBalance: "บนตาชั่ง กดตั้งศูนย์ (tare) ก่อน",
    withPipette: "ด้วยปิเปตหรือกระบอกตวง",
    stock: "สต็อก: {strength}",
    weighed: "ชั่งได้",
    measured: "ตวงได้",
    asPlanned: "ตามสูตร",
    saveNext: "บันทึก ไปต่อ",
    back: "ย้อนกลับ",
    skip: "ข้ามไปก่อน",
    close: "ปิด",
    otherLanguage: "English",
    otherLanguageName: "อังกฤษ",
    inGrams: "กรัม",
    inUnits: "µL / mg",
    over: "เกินสูตร {percent}%",
    under: "ขาดจากสูตร {percent}%",
    same: "ตรงตามสูตร",
    typeNumber: "พิมพ์ตัวเลข เช่น 1.25",
    density: "กรัมคำนวณจากความหนาแน่นของสต็อก {density} g/mL",
    allDone: "ชั่งครบทุกรายการแล้ว",
    someDone: "ชั่งแล้ว {done} จาก {total} แตะที่รายการเพื่อชั่ง",
    notYet: "ยังไม่ได้ชั่ง",
    notes: "บันทึกเพิ่มเติม",
    sendNow: "ส่งตอนนี้",
    sending: "กำลังส่งไปที่คอมพิวเตอร์…",
    savedAt: "บันทึกลงคอมพิวเตอร์แล้ว เวลา {time}",
    waiting: "เชื่อมต่อคอมพิวเตอร์ไม่ได้ เก็บไว้ในโทรศัพท์ {count} รายการ จะส่งเมื่อเชื่อมต่อได้",
    refused: "คอมพิวเตอร์ไม่รับค่านี้: {message}",
    nothingYet: "ยังไม่ได้ชั่งรายการใด",
  },
};

function phoneBenchSay(lang, key, values = {}) {
  const words = PHONE_BENCH_WORDS[lang] || PHONE_BENCH_WORDS.en;
  const template = words[key] ?? PHONE_BENCH_WORDS.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}

// Decimal text with exactly `places` decimals, rounded half up.
function phoneBenchFixed(text, places) {
  const value = phoneBenchExact.benchFractionOf(text);
  if (!value) return String(text ?? "");
  const rounded = phoneBenchExact.benchFractionText(value, places);
  if (!places) return rounded;
  const [whole, part = ""] = rounded.split(".");
  return `${whole}.${part.padEnd(places, "0")}`;
}

// A batch's planned rows as formula-source rows, for the bench sheet's stock
// match and grams rules (benchRowFromSource, benchMatchStocks, benchRowsInGrams).
function phoneBenchSourceRows(record) {
  return (record?.planned_rows || []).map((row) => ({
    material: String(row.material ?? ""),
    amount_decimal: String(row.planned_amount ?? ""),
    amount_unit: row.unit === "uL" ? "µL" : String(row.unit ?? ""),
    concentration_fraction_decimal: row.concentration_fraction_decimal ?? "",
    concentration_basis: row.concentration_basis || "UNKNOWN",
  }));
}

// One step per planned row. `gramRows` is benchRowsInGrams(...).rows for
// phoneBenchSourceRows(record), in the same order; a row it turned into grams
// gives the step its grams and the stock density they came from.
function phoneBenchSteps(record, gramRows = []) {
  return (record?.planned_rows || []).map((row, index) => {
    const unit = row.unit === "mg" ? "mg" : "µL";
    const planned = String(row.planned_amount ?? "");
    const step = { line: row.line, material: String(row.material ?? ""), strength: String(row.strength ?? ""), unit, planned, grams: null, density: null };
    const amount = phoneBenchExact.benchFractionOf(planned);
    if (unit === "mg") {
      if (amount && phoneBenchExact.benchCompare(amount, { n: BigInt(PHONE_BENCH_GRAMS_FROM_MG), d: 1n }) >= 0) {
        step.grams = phoneBenchFixed(phoneBenchExact.benchFractionText(phoneBenchExact.benchOver(amount, { n: 1000n, d: 1n }), 3), 3);
      }
      return step;
    }
    const converted = gramRows[index];
    if (converted && converted.amount_unit === "g" && converted.stock_density_g_ml && amount) {
      step.grams = phoneBenchFixed(converted.amount_decimal, 3);
      step.density = String(converted.stock_density_g_ml);
    }
    return step;
  });
}

// What to put in for a step: grams when weighing by grams and known.
function phoneBenchShows(step, by) {
  if (by === "g" && step.grams) return { amount: step.grams, unit: "g" };
  return { amount: step.planned, unit: step.unit };
}

// How far a typed amount is from the plan, in percent of the plan.
function phoneBenchDeviation(typed, planned) {
  const actual = phoneBenchExact.benchFractionOf(typed);
  const plan = phoneBenchExact.benchFractionOf(planned);
  if (!actual || !plan || plan.n === 0n) return null;
  const order = phoneBenchExact.benchCompare(actual, plan);
  if (order === 0) return { kind: "same", percent: "0" };
  const gap = order > 0 ? phoneBenchExact.benchMinus(actual, plan) : phoneBenchExact.benchMinus(plan, actual);
  const share = phoneBenchExact.benchTimes(phoneBenchExact.benchOver(gap, plan), { n: 100n, d: 1n });
  let percent = phoneBenchExact.benchFractionText(share, 1);
  if (percent === "0") percent = phoneBenchExact.benchFractionText(share, 2);
  if (percent === "0") percent = "0.01";
  return { kind: order > 0 ? "over" : "under", percent };
}

// The entry kept for a step from what was typed, or the reason it can't be kept.
function phoneBenchEntry(step, by, typedText) {
  const typed = String(typedText ?? "").trim().replace(",", ".");
  if (!PHONE_BENCH_NUMBER.test(typed)) return { error: "typeNumber" };
  const shows = phoneBenchShows(step, by);
  return {
    entry: {
      line: step.line,
      typed,
      unit: shows.unit,
      planned: shows.amount,
      density: shows.unit === "g" && step.unit === "µL" ? step.density : null,
    },
  };
}

// One line of the actuals request: grams (with the density for a µL line) or
// the amount in the line's own unit.
function phoneBenchActual(entry) {
  if (entry.unit === "g") {
    return entry.density ? { line: entry.line, weighed_g: entry.typed, density_g_ml: entry.density } : { line: entry.line, weighed_g: entry.typed };
  }
  return { line: entry.line, actual_amount: entry.typed };
}

function phoneBenchBody(progress) {
  const entries = Object.values(progress?.entries || {}).sort((a, b) => a.line - b.line);
  return { actuals: entries.map(phoneBenchActual), notes: String(progress?.notes ?? "").trim() };
}

// Entries for the amounts the PC already holds for this batch.
function phoneBenchSeed(steps, actuals) {
  const entries = {};
  for (const actual of actuals || []) {
    const step = steps.find((item) => item.line === actual.line);
    if (!step) continue;
    entries[step.line] = actual.weighed_g
      ? { line: step.line, typed: String(actual.weighed_g), unit: "g", planned: step.grams, density: actual.density_g_ml ? String(actual.density_g_ml) : null }
      : { line: step.line, typed: String(actual.actual_amount), unit: step.unit, planned: step.planned, density: null };
  }
  return entries;
}

// The next step with nothing weighed after `from`, else the first such step,
// else steps.length (the summary).
function phoneBenchNextIndex(steps, entries, from) {
  for (let index = from + 1; index < steps.length; index += 1) {
    if (!entries[steps[index].line]) return index;
  }
  for (let index = 0; index < steps.length; index += 1) {
    if (!entries[steps[index].line]) return index;
  }
  return steps.length;
}

function phoneBenchLoad(storage, lot) {
  try {
    const progress = JSON.parse(storage.getItem(PHONE_BENCH_STORE + lot) || "null");
    return progress && progress.lot === lot && Array.isArray(progress.steps) ? progress : null;
  } catch {
    return null;
  }
}

function phoneBenchKeep(storage, progress) {
  try {
    storage.setItem(PHONE_BENCH_STORE + progress.lot, JSON.stringify(progress));
    return true;
  } catch {
    return false;
  }
}

function phoneBenchPendingLots(storage) {
  const lots = [];
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key || !key.startsWith(PHONE_BENCH_STORE)) continue;
      const progress = phoneBenchLoad(storage, key.slice(PHONE_BENCH_STORE.length));
      if (progress?.pending) lots.push(progress.lot);
    }
  } catch {
    return lots;
  }
  return lots.sort();
}

let phoneBench = null;

function phoneBenchShown() {
  phoneBench?.show();
}

function openPhoneBench(lot) {
  phoneBench?.open(lot);
}

function attachPhoneBench({ doc, request, root, storage = null }) {
  if (!root) return null;
  const view = doc.defaultView;
  let store = storage;
  if (!store) {
    try { store = view.localStorage; } catch { store = null; }
  }
  const memory = new Map();
  store = store || { getItem: (key) => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, String(value)), get length() { return memory.size; }, key: (index) => [...memory.keys()][index] ?? null };

  const node = (tag, props = {}, text) => {
    const element = doc.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "className" || key === "type" || key === "value" || key === "hidden" || key === "disabled" || key === "rows" || key === "max") element[key] = value;
      else element.setAttribute(key, value);
    }
    if (text !== undefined) element.textContent = text;
    return element;
  };

  let lang = "en";
  try { lang = store.getItem(PHONE_BENCH_LANG) === "th" ? "th" : "en"; } catch { lang = "en"; }
  const say = (key, values) => phoneBenchSay(lang, key, values);
  const sending = new Set();
  const again = new Set();
  const timers = new Map();
  let records = [];
  let listError = "";
  let listTicket = 0;
  let current = null;
  let opener = null;

  // ---- the panel in the Batch view ----
  const title = node("h2", { id: "phone-bench-panel-title" });
  const help = node("p", { className: "field-help" });
  const list = node("ul", { className: "phone-bench-list" });
  const listStatus = node("p", { className: "batch-status", role: "status", "aria-live": "polite" });
  root.replaceChildren(node("p", { className: "panel-index" }, "Phone"), title, help, list, listStatus);

  // ---- the full-screen step view ----
  const sheet = node("div", { className: "phone-bench", hidden: true, role: "dialog", "aria-modal": "true", "aria-labelledby": "phone-bench-material" });
  const lotLine = node("p", { className: "phone-bench-lot" });
  const langButton = node("button", { type: "button", className: "quiet-button phone-bench-lang" });
  const byButton = node("button", { type: "button", className: "quiet-button phone-bench-by" });
  const closeButton = node("button", { type: "button", className: "quiet-button phone-bench-close" });
  const top = node("div", { className: "phone-bench-top" });
  const topActions = node("div", { className: "phone-bench-top-actions" });
  topActions.append(langButton, byButton, closeButton);
  top.append(lotLine, topActions);
  const where = node("p", { className: "phone-bench-where" });
  const bar = node("progress", { className: "phone-bench-bar", max: 1, value: "0" });

  const step = node("form", { className: "phone-bench-step", novalidate: "" });
  const material = node("h2", { id: "phone-bench-material", className: "phone-bench-material" });
  const strength = node("p", { className: "phone-bench-strength" });
  const putIn = node("p", { className: "phone-bench-put" });
  const amount = node("p", { className: "phone-bench-amount" });
  const amountNumber = node("span", { className: "phone-bench-number" });
  const amountUnit = node("span", { className: "phone-bench-unit" });
  amount.append(amountNumber, amountUnit);
  const how = node("p", { className: "phone-bench-how" });
  const input = node("input", { className: "phone-bench-input", inputmode: "decimal", autocomplete: "off", enterkeyhint: "next", id: "phone-bench-input" });
  const inputLabel = node("label", { className: "phone-bench-label", for: "phone-bench-input" });
  const inputUnit = node("span", { className: "phone-bench-input-unit" });
  const inputRow = node("div", { className: "phone-bench-input-row" });
  inputRow.append(input, inputUnit);
  const check = node("p", { className: "phone-bench-check", role: "status", "aria-live": "polite" });
  const density = node("p", { className: "phone-bench-density" });
  const asPlanned = node("button", { type: "button", className: "quiet-button phone-bench-as-planned" });
  const saveNext = node("button", { type: "submit", className: "phone-bench-save" });
  const back = node("button", { type: "button", className: "quiet-button" });
  const skip = node("button", { type: "button", className: "quiet-button" });
  const mainActions = node("div", { className: "phone-bench-actions" });
  mainActions.append(asPlanned, saveNext);
  const moveActions = node("div", { className: "phone-bench-actions phone-bench-move" });
  moveActions.append(back, skip);
  step.append(material, strength, putIn, amount, how, inputLabel, inputRow, check, density, mainActions, moveActions);

  const done = node("div", { className: "phone-bench-done", hidden: true });
  const doneTitle = node("h2", { className: "phone-bench-material", id: "phone-bench-done-title" });
  const doneList = node("ol", { className: "phone-bench-summary" });
  const notes = node("textarea", { rows: 2, maxlength: "4000", id: "phone-bench-notes" });
  const notesLabel = node("label", { for: "phone-bench-notes" });
  const sendNow = node("button", { type: "button", className: "phone-bench-send" });
  done.append(doneTitle, doneList, notesLabel, notes, sendNow);

  const sync = node("p", { className: "phone-bench-sync", role: "status", "aria-live": "polite" });
  sheet.append(top, where, bar, step, done, sync);
  doc.body.append(sheet);

  function keep() {
    if (current) phoneBenchKeep(store, current);
  }

  function countOf(progress) {
    return Object.keys(progress?.entries || {}).length;
  }

  function timeText(iso) {
    try {
      return new Date(iso).toLocaleTimeString(lang === "th" ? "th-TH" : undefined, { hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  }

  function syncWords(progress) {
    if (!progress) return "";
    if (sending.has(progress.lot)) return say("sending");
    if (progress.error) return say("refused", { message: progress.error });
    if (progress.pending) return say("waiting", { count: countOf(progress) });
    if (progress.savedAt) return say("savedAt", { time: timeText(progress.savedAt) });
    return countOf(progress) ? "" : say("nothingYet");
  }

  // ---- sending, with a retry while the PC doesn't answer ----
  function schedule(lot) {
    if (timers.has(lot)) return;
    timers.set(lot, view.setTimeout(() => { timers.delete(lot); send(lot); }, PHONE_BENCH_RETRY_MS));
  }

  async function send(lot) {
    if (sending.has(lot)) {
      again.add(lot);
      return;
    }
    const progress = current?.lot === lot ? current : phoneBenchLoad(store, lot);
    if (!progress) return;
    progress.pending = true;
    phoneBenchKeep(store, progress);
    sending.add(lot);
    render();
    try {
      await request(`/v2/batches/${encodeURIComponent(lot)}/actuals`, { method: "POST", body: JSON.stringify(phoneBenchBody(progress)) });
      progress.error = "";
      if (!again.has(lot)) {
        progress.pending = false;
        progress.savedAt = new Date().toISOString();
      }
    } catch (error) {
      // A refusal is kept and shown; only a PC that didn't answer is tried again.
      if (error && error.status && error.status < 500) progress.error = error.message || String(error.status);
      else schedule(lot);
    } finally {
      sending.delete(lot);
      phoneBenchKeep(store, progress);
      if (again.delete(lot)) send(lot);
      render();
      showList();
    }
  }

  function resume() {
    for (const lot of phoneBenchPendingLots(store)) send(lot);
  }

  // ---- drawing ----
  function render() {
    sheet.setAttribute("lang", lang);
    langButton.textContent = say("otherLanguage");
    langButton.setAttribute("aria-label", say("otherLanguageName"));
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", say("close"));
    if (!current) return;
    const steps = current.steps;
    const anyGrams = steps.some((item) => item.grams);
    byButton.hidden = !anyGrams;
    byButton.textContent = current.by === "g" ? say("inUnits") : say("inGrams");
    lotLine.textContent = `${current.lot} · ${current.formula}`;
    const count = countOf(current);
    bar.max = Math.max(steps.length, 1);
    bar.value = count;
    sync.textContent = syncWords(current);
    const atStep = current.at < steps.length;
    step.hidden = !atStep;
    done.hidden = atStep;
    where.textContent = atStep ? say("lineOf", { n: current.at + 1, total: steps.length }) : say("weighedCount", { done: count, total: steps.length });
    if (atStep) {
      const item = steps[current.at];
      const shows = phoneBenchShows(item, current.by);
      const entry = current.entries[item.line];
      material.textContent = item.material;
      strength.textContent = item.strength ? say("stock", { strength: item.strength }) : "";
      putIn.textContent = say("putIn");
      amountNumber.textContent = shows.amount;
      amountUnit.textContent = ` ${shows.unit}`;
      how.textContent = shows.unit === "µL" ? say("withPipette") : say("onBalance");
      inputLabel.textContent = shows.unit === "µL" ? say("measured") : say("weighed");
      inputUnit.textContent = shows.unit;
      density.textContent = shows.unit === "g" && item.density ? say("density", { density: item.density }) : "";
      asPlanned.textContent = say("asPlanned");
      saveNext.textContent = say("saveNext");
      back.textContent = say("back");
      skip.textContent = say("skip");
      back.disabled = current.at === 0;
      if (input.dataset.line !== String(item.line) || input.dataset.unit !== shows.unit) {
        input.dataset.line = String(item.line);
        input.dataset.unit = shows.unit;
        input.value = entry && entry.unit === shows.unit ? entry.typed : "";
        showCheck();
      }
    } else {
      doneTitle.textContent = count === steps.length ? say("allDone") : say("someDone", { done: count, total: steps.length });
      doneList.replaceChildren(...steps.map((item, index) => {
        const entry = current.entries[item.line];
        const shows = phoneBenchShows(item, current.by);
        const row = node("li");
        const button = node("button", { type: "button", className: "phone-bench-summary-line" });
        const planned = entry ? `${entry.planned ?? shows.amount} ${entry.planned ? entry.unit : shows.unit}` : `${shows.amount} ${shows.unit}`;
        let weighedText = say("notYet");
        if (entry) {
          const gap = entry.planned ? phoneBenchDeviation(entry.typed, entry.planned) : null;
          weighedText = `${entry.typed} ${entry.unit}${gap && gap.kind !== "same" ? ` (${gap.kind === "over" ? "+" : "−"}${gap.percent}%)` : ""}`;
        }
        button.append(node("span", { className: "phone-bench-summary-name" }, `${item.line}. ${item.material}`), node("span", {}, `${planned} → ${weighedText}`));
        button.addEventListener("click", () => { current.at = index; keep(); render(); input.focus(); });
        row.append(button);
        return row;
      }));
      notesLabel.textContent = say("notes");
      if (doc.activeElement !== notes) notes.value = current.notes || "";
      sendNow.textContent = say("sendNow");
      sendNow.hidden = !current.pending || sending.has(current.lot);
    }
  }

  function showCheck(errorKey = null) {
    check.classList.toggle("is-error", Boolean(errorKey));
    if (errorKey) {
      check.textContent = say(errorKey);
      return;
    }
    if (!current || current.at >= current.steps.length) return;
    const shows = phoneBenchShows(current.steps[current.at], current.by);
    const typed = input.value.trim().replace(",", ".");
    const gap = PHONE_BENCH_NUMBER.test(typed) ? phoneBenchDeviation(typed, shows.amount) : null;
    check.textContent = gap ? (gap.kind === "same" ? say("same") : say(gap.kind, { percent: gap.percent })) : "";
  }

  function showList() {
    title.textContent = say("panelTitle");
    help.textContent = say("panelHelp");
    if (listError) {
      list.replaceChildren();
      listStatus.textContent = say("listFailed", { message: listError });
      return;
    }
    listStatus.textContent = records ? (records.length ? "" : say("noBatches")) : say("loading");
    list.replaceChildren(...(records || []).map((record) => {
      const local = phoneBenchLoad(store, record.lot);
      const total = (record.planned_rows || []).length;
      const item = node("li", { className: "phone-bench-batch" });
      const words = node("div");
      words.append(
        node("strong", {}, record.lot),
        node("span", {}, ` ${record.formula_name} · ${record.bottles} × ${record.bottle_ml} mL · ${record.made_on}`),
      );
      const progressLine = node("p", { className: "field-help" }, local?.pending
        ? say("keptOnPhone", { count: countOf(local) })
        : say("weighedCount", { done: local ? countOf(local) : (record.actuals || []).length, total }));
      words.append(progressLine);
      const button = node("button", { type: "button", className: "primary-button phone-bench-open" }, local && countOf(local) ? say("carryOn") : say("weigh"));
      button.addEventListener("click", () => { opener = button; open(record.lot); });
      item.append(words, button);
      return item;
    }));
  }

  async function show() {
    const ticket = ++listTicket;
    if (!records.length) records = null;
    listError = "";
    showList();
    try {
      const answer = await request("/v2/batches");
      if (ticket !== listTicket) return;
      records = answer.records || [];
    } catch (error) {
      if (ticket !== listTicket) return;
      records = records || [];
      listError = error.message || "no answer";
    }
    showList();
    resume();
  }

  async function stepsWithGrams(record) {
    const rows = phoneBenchSourceRows(record).map(benchRowFromSource);
    const matched = benchMatchStocks(rows, typeof state === "object" ? state.projectInventory : null).rows;
    const names = [...new Set(matched.flatMap((row) => [row.identity_name, row.material]).map((name) => String(name ?? "").trim()).filter(Boolean))].slice(0, 300);
    if (!names.length) return phoneBenchSteps(record);
    try {
      const reply = await request("/v2/workbench/material-densities", { method: "POST", body: JSON.stringify({ names }) });
      return phoneBenchSteps(record, benchRowsInGrams(matched, reply.densities || {}).rows);
    } catch {
      return phoneBenchSteps(record);
    }
  }

  async function open(lot) {
    listStatus.textContent = say("opening", { lot });
    const local = phoneBenchLoad(store, lot);
    let record = null;
    try {
      record = await request(`/v2/batches/${encodeURIComponent(lot)}`);
    } catch (error) {
      if (!local) {
        listStatus.textContent = say("openFailed", { lot, message: error.message || "no answer" });
        return;
      }
    }
    let progress = local;
    if (record) {
      const steps = await stepsWithGrams(record);
      const entries = local ? local.entries : phoneBenchSeed(steps, record.actuals);
      progress = {
        lot: record.lot,
        formula: record.formula_name,
        steps,
        entries,
        at: 0,
        by: local?.by || "g",
        notes: local ? local.notes : (record.actual_notes || ""),
        pending: Boolean(local?.pending),
        savedAt: local?.savedAt || record.actuals_recorded_at || null,
        error: local?.error || "",
      };
      progress.at = phoneBenchNextIndex(steps, entries, -1);
    }
    current = progress;
    keep();
    listStatus.textContent = "";
    input.dataset.line = "";
    sheet.hidden = false;
    doc.body.classList.add("phone-bench-open");
    render();
    (current.at < current.steps.length ? input : doneTitle).focus?.();
  }

  function close() {
    sheet.hidden = true;
    doc.body.classList.remove("phone-bench-open");
    current = null;
    showList();
    opener?.focus?.();
  }

  function weighed(typed) {
    const item = current.steps[current.at];
    const result = phoneBenchEntry(item, current.by, typed);
    if (result.error) {
      showCheck(result.error);
      input.focus();
      return;
    }
    current.entries[item.line] = result.entry;
    current.at = phoneBenchNextIndex(current.steps, current.entries, current.at);
    current.error = "";
    keep();
    render();
    send(current.lot);
    if (current.at < current.steps.length) input.focus();
  }

  step.addEventListener("submit", (event) => {
    event.preventDefault();
    if (current) weighed(input.value);
  });
  input.addEventListener("input", () => showCheck());
  asPlanned.addEventListener("click", () => {
    if (!current) return;
    const shows = phoneBenchShows(current.steps[current.at], current.by);
    input.value = shows.amount;
    weighed(shows.amount);
  });
  back.addEventListener("click", () => {
    if (!current || current.at === 0) return;
    current.at -= 1;
    keep();
    render();
  });
  skip.addEventListener("click", () => {
    if (!current) return;
    current.at = Math.min(current.at + 1, current.steps.length);
    keep();
    render();
  });
  byButton.addEventListener("click", () => {
    if (!current) return;
    current.by = current.by === "g" ? "unit" : "g";
    keep();
    render();
  });
  langButton.addEventListener("click", () => {
    lang = lang === "th" ? "en" : "th";
    try { store.setItem(PHONE_BENCH_LANG, lang); } catch { /* storage unavailable */ }
    input.dataset.line = "";
    render();
    showList();
  });
  closeButton.addEventListener("click", close);
  sheet.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  notes.addEventListener("input", () => {
    if (!current) return;
    current.notes = notes.value;
    keep();
  });
  notes.addEventListener("change", () => { if (current) send(current.lot); });
  sendNow.addEventListener("click", () => { if (current) send(current.lot); });
  view.addEventListener("online", resume);

  showList();
  resume();
  phoneBench = { show, open, close, resume, send };
  return phoneBench;
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    PHONE_BENCH_STORE, PHONE_BENCH_LANG, PHONE_BENCH_WORDS, phoneBenchSay, phoneBenchFixed, phoneBenchSourceRows, phoneBenchSteps,
    phoneBenchShows, phoneBenchDeviation, phoneBenchEntry, phoneBenchActual, phoneBenchBody, phoneBenchSeed, phoneBenchNextIndex,
    phoneBenchLoad, phoneBenchKeep, phoneBenchPendingLots, attachPhoneBench,
  };
}
