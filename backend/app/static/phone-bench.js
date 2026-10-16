"use strict";

// Phone bench mode: weigh a recorded batch one line at a time, in big numbers,
// in grams where the stock's density is known, in English or Thai.
//
// Once a batch is open it works without the network: its steps and every
// amount typed are kept in this browser's localStorage, and the weighed amounts
// go to the PC (POST /v2/batches/{lot}/actuals) whenever it answers. Each send
// carries every line, and says which batch and which saved set of amounts
// (the record's recorded_at and actuals_version) it was built on: the PC
// refuses a send that missed another device's save (409), and the phone then
// merges line by line (phoneBenchMerge) and sends again, asking the person only
// about a line both changed. Sending what is already saved changes nothing. A
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
// Amounts kept for an earlier batch that had the same lot number: set aside, never sent.
const PHONE_BENCH_ASIDE = "perfumechem.bench.aside.v1.";
const PHONE_BENCH_LANG = "perfumechem.bench.lang";
const PHONE_BENCH_RETRY_MS = 15000;
const PHONE_BENCH_NOTES_MS = 1500;
// 409s in a row before the phone stops and asks: the PC's amounts keep changing.
const PHONE_BENCH_MERGES_IN_A_ROW = 3;
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
    notSent: "Not on the PC yet.",
    refused: "The PC refused these amounts: {message}",
    nothingYet: "Nothing weighed yet.",
    progressLabel: "Lines weighed",
    conflict: "The PC also changed {what} since this phone last sent. Choose which to keep.",
    conflictLine: "line {n}",
    conflictNotes: "the notes",
    pcHas: "PC: {amount}",
    pcNothing: "nothing",
    keepPhone: "Keep this phone's",
    usePc: "Use the PC's",
    otherBatch: "Lot {lot} is now a different batch on the PC. The amounts on this phone were for an earlier batch, so they are not sent.",
    setAside: "Amounts kept on this phone for an earlier batch with lot {lot} were set aside and not sent.",
    keepsChanging: "The PC's amounts for this lot keep changing. Check them on the PC, then tap Send now.",
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
    notSent: "ยังไม่ได้ส่งไปที่คอมพิวเตอร์",
    refused: "คอมพิวเตอร์ไม่รับค่านี้: {message}",
    nothingYet: "ยังไม่ได้ชั่งรายการใด",
    progressLabel: "รายการที่ชั่งแล้ว",
    conflict: "คอมพิวเตอร์ก็แก้ {what} ด้วย หลังจากโทรศัพท์ส่งครั้งล่าสุด เลือกค่าที่จะเก็บไว้",
    conflictLine: "รายการที่ {n}",
    conflictNotes: "บันทึกเพิ่มเติม",
    pcHas: "คอมพิวเตอร์: {amount}",
    pcNothing: "ไม่มี",
    keepPhone: "ใช้ค่าในโทรศัพท์นี้",
    usePc: "ใช้ค่าในคอมพิวเตอร์",
    otherBatch: "ล็อต {lot} ในคอมพิวเตอร์ตอนนี้เป็นแบทช์อื่นแล้ว ค่าในโทรศัพท์นี้เป็นของแบทช์ก่อนหน้า จึงไม่ส่ง",
    setAside: "ค่าที่เก็บไว้ในโทรศัพท์สำหรับแบทช์ก่อนหน้าที่ใช้ล็อต {lot} ถูกแยกเก็บไว้และไม่ได้ส่ง",
    keepsChanging: "ค่าของล็อตนี้ในคอมพิวเตอร์เปลี่ยนอยู่เรื่อยๆ ตรวจที่คอมพิวเตอร์ก่อน แล้วกดส่งตอนนี้",
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

// The actuals request: every line, the notes, and the batch and saved set of
// amounts it was built on, which the PC checks.
function phoneBenchBody(progress) {
  const entries = Object.values(progress?.entries || {}).sort((a, b) => a.line - b.line);
  const body = { actuals: entries.map(phoneBenchActual), notes: String(progress?.notes ?? "").trim() };
  if (Number.isInteger(progress?.base?.version)) body.based_on = progress.base.version;
  if (progress?.batch) body.batch_recorded_at = progress.batch;
  return body;
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

// The batch as the PC holds it, in the phone's terms: its weighed amounts as
// entries, its notes, and which saved set this is (the record's actuals_version).
function phoneBenchServer(steps, record) {
  return {
    entries: phoneBenchSeed(steps, record?.actuals),
    notes: String(record?.actual_notes ?? ""),
    version: Number.isInteger(record?.actuals_version) ? record.actuals_version : 0,
  };
}

// Two entries hold the same amount: the same fields, and the same numbers
// ("10.310" and "10.31" are the same). Nothing on both sides is the same too.
function phoneBenchSame(a, b) {
  if (!a || !b) return !a && !b;
  const x = phoneBenchActual(a);
  const y = phoneBenchActual(b);
  for (const key of new Set([...Object.keys(x), ...Object.keys(y)])) {
    if (key === "line") continue;
    const first = x[key] ?? null;
    const second = y[key] ?? null;
    if (first === null || second === null) {
      if (first !== second) return false;
      continue;
    }
    const p = phoneBenchExact.benchFractionOf(first);
    const q = phoneBenchExact.benchFractionOf(second);
    if (p && q ? phoneBenchExact.benchCompare(p, q) !== 0 : String(first) !== String(second)) return false;
  }
  return true;
}

function phoneBenchNotesOf(text) {
  return String(text ?? "").trim();
}

// Two sets of amounts and notes are the same, line for line.
function phoneBenchSameSet(a, b) {
  const first = a?.entries || {};
  const second = b?.entries || {};
  for (const line of new Set([...Object.keys(first), ...Object.keys(second)])) {
    if (!phoneBenchSame(first[line], second[line])) return false;
  }
  return phoneBenchNotesOf(a?.notes) === phoneBenchNotesOf(b?.notes);
}

// The phone holds something the PC hasn't confirmed. Blank notes never count:
// the PC keeps its notes when a send has none.
function phoneBenchChanged(progress) {
  const base = progress?.base?.entries || {};
  const entries = progress?.entries || {};
  for (const line of new Set([...Object.keys(base), ...Object.keys(entries)])) {
    if (!phoneBenchSame(entries[line], base[line])) return true;
  }
  const notes = phoneBenchNotesOf(progress?.notes);
  return Boolean(notes) && notes !== phoneBenchNotesOf(progress?.base?.notes);
}

// A three-way merge, line by line, of what the phone holds (`local`) with what
// the PC holds now (`server`), both changed from `base`, the set the PC last
// confirmed to the phone. A line only one side changed takes that side's
// amount. A line both changed to different amounts is a conflict: it keeps the
// phone's amount until the person chooses. The notes merge the same way, and
// blank notes on the phone take the PC's.
function phoneBenchMerge(base, server, local) {
  const from = base?.entries || {};
  const theirs = server?.entries || {};
  const mine = local?.entries || {};
  const entries = {};
  const lines = [];
  const all = [...new Set([...Object.keys(from), ...Object.keys(theirs), ...Object.keys(mine)])].sort((a, b) => Number(a) - Number(b));
  for (const line of all) {
    const was = from[line] || null;
    const pc = theirs[line] || null;
    const phone = mine[line] || null;
    let kept = phone;
    if (phoneBenchSame(phone, was)) kept = pc;
    else if (!phoneBenchSame(pc, was) && !phoneBenchSame(pc, phone)) lines.push({ line: Number(line), pc });
    if (kept) entries[line] = kept;
  }
  const wasNotes = phoneBenchNotesOf(base?.notes);
  const pcNotes = phoneBenchNotesOf(server?.notes);
  const phoneNotes = phoneBenchNotesOf(local?.notes);
  let notes = phoneNotes;
  let notesConflict = null;
  if (!phoneNotes || phoneNotes === wasNotes) notes = pcNotes;
  else if (pcNotes !== wasNotes && pcNotes !== phoneNotes) notesConflict = pcNotes;
  return { entries, notes, conflict: lines.length || notesConflict !== null ? { lines, notes: notesConflict } : null };
}

// The base to merge against: the set the PC last confirmed to the phone, with
// each line (and the notes) the PC now holds exactly as one of this phone's
// unanswered sends had it taken as confirmed too. The PC may have saved a send
// whose answer never reached the phone, and those lines are then the phone's
// own, not a change made on the PC.
function phoneBenchMergeBase(base, unanswered, server) {
  const sends = Array.isArray(unanswered) ? unanswered : [];
  if (!sends.length) return base;
  const entries = { ...(base?.entries || {}) };
  const theirs = server?.entries || {};
  for (const sent of sends) {
    const mine = sent?.entries || {};
    for (const line of new Set([...Object.keys(theirs), ...Object.keys(mine)])) {
      if (!phoneBenchSame(theirs[line], mine[line])) continue;
      if (theirs[line]) entries[line] = theirs[line];
      else delete entries[line];
    }
  }
  const pcNotes = phoneBenchNotesOf(server?.notes);
  const notes = sends.some((sent) => phoneBenchNotesOf(sent?.notes) === pcNotes) ? String(server?.notes ?? "") : base?.notes;
  return { ...base, entries, notes };
}

// Sending this lot waits on the person: a refusal, a problem (another batch,
// amounts on the PC that keep changing) or a choice between the phone's and the
// PC's amounts.
function phoneBenchStuck(progress) {
  return Boolean(progress?.error || progress?.problem || progress?.conflict);
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
    const whole = progress && progress.lot === lot && typeof progress.batch === "string" && Array.isArray(progress.steps)
      && progress.entries && typeof progress.entries === "object" && progress.base && typeof progress.base === "object";
    return whole ? progress : null;
  } catch {
    return null;
  }
}

// The kept copy as it was stored, whatever its shape: a copy an earlier version
// of this page kept is set aside when its lot opens, not dropped.
function phoneBenchRaw(storage, lot) {
  try {
    const progress = JSON.parse(storage.getItem(PHONE_BENCH_STORE + lot) || "null");
    return progress && typeof progress === "object" && !Array.isArray(progress) ? progress : null;
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

function phoneBenchSetAside(storage, progress) {
  try {
    storage.setItem(`${PHONE_BENCH_ASIDE}${progress.lot}.${progress.batch}`, JSON.stringify(progress));
    return true;
  } catch {
    return false;
  }
}

// Lots with amounts to send: kept and not on the PC yet, with nothing waiting
// on the person.
function phoneBenchPendingLots(storage) {
  const lots = [];
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key || !key.startsWith(PHONE_BENCH_STORE)) continue;
      const progress = phoneBenchLoad(storage, key.slice(PHONE_BENCH_STORE.length));
      if (progress?.pending && !phoneBenchStuck(progress)) lots.push(progress.lot);
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
  const merging = new Set();
  let sendCount = 0;
  const tab = `${Date.now().toString(36)}.${Math.random().toString(36).slice(2, 8)}`;
  const timers = new Map();
  const merges = new Map();
  const inerted = [];
  let records = [];
  let listError = "";
  let listTicket = 0;
  let openTicket = 0;
  let notesTimer = null;
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
  const notice = node("p", { className: "phone-bench-notice", role: "status" });
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
  const doneTitle = node("h2", { className: "phone-bench-material", id: "phone-bench-done-title", tabindex: "-1" });
  const doneList = node("ol", { className: "phone-bench-summary" });
  const keepPhone = node("button", { type: "button", className: "phone-bench-keep-phone" });
  const usePc = node("button", { type: "button", className: "quiet-button phone-bench-use-pc" });
  const choose = node("div", { className: "phone-bench-actions phone-bench-choose", hidden: true });
  choose.append(keepPhone, usePc);
  const notes = node("textarea", { rows: 2, maxlength: "4000", id: "phone-bench-notes" });
  const notesLabel = node("label", { for: "phone-bench-notes" });
  const pcNotes = node("p", { className: "phone-bench-pc-notes", hidden: true });
  const sendNow = node("button", { type: "button", className: "phone-bench-send" });
  done.append(doneTitle, doneList, choose, notesLabel, notes, pcNotes, sendNow);

  const sync = node("p", { className: "phone-bench-sync", role: "status", "aria-live": "polite" });
  sheet.append(top, notice, where, bar, step, done, sync);
  doc.body.append(sheet);

  // Each write says which tab made it and when, so a tab can tell another
  // tab's newer copy of the open lot from its own.
  function write(progress) {
    progress.tab = tab;
    progress.keptAt = Date.now();
    return phoneBenchKeep(store, progress);
  }

  // Writes a lot's copy, unless another tab has opened the lot as another batch
  // since: then this copy is set aside, never written over that one.
  function keepFor(progress) {
    const kept = phoneBenchRaw(store, progress.lot);
    if (kept && typeof kept.batch === "string" && kept.batch !== progress.batch) {
      if (progress.pending || progress.conflict) phoneBenchSetAside(store, progress);
      progress.problem = "otherBatch";
      return false;
    }
    return write(progress);
  }

  function keep() {
    if (current) keepFor(current);
  }

  // Another tab on this phone kept a newer copy of the lot open here: carry on
  // from it, keeping this tab's line and units, so neither tab writes over lines
  // the other weighed.
  function adoptKept() {
    if (!current) return false;
    const kept = phoneBenchLoad(store, current.lot);
    if (!kept || kept.batch !== current.batch || kept.tab === tab) return false;
    if (kept.tab === current.tab && kept.keptAt === current.keptAt) return false;
    if ((kept.keptAt || 0) < (current.keptAt || 0)) return false;
    current = { ...kept, at: current.at, by: current.by };
    if (notes.value !== (current.notes || "")) notes.value = current.notes || "";
    return true;
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

  function conflictWhat(conflict) {
    const parts = (conflict.lines || []).map((item) => say("conflictLine", { n: item.line }));
    if (conflict.notes !== null && conflict.notes !== undefined) parts.push(say("conflictNotes"));
    return parts.join(", ");
  }

  function syncWords(progress) {
    if (!progress) return "";
    if (sending.has(progress.lot) || merging.has(progress.lot)) return say("sending");
    if (progress.conflict) return say("conflict", { what: conflictWhat(progress.conflict) });
    if (progress.problem) return say(progress.problem, { lot: progress.lot });
    if (progress.error) return say("refused", { message: progress.error });
    // "No connection" only once the PC failed to answer; until then, not sent yet.
    if (progress.pending) return progress.offline ? say("waiting", { count: countOf(progress) }) : say("notSent");
    if (progress.savedAt) return say("savedAt", { time: timeText(progress.savedAt) });
    return countOf(progress) ? "" : say("nothingYet");
  }

  // ---- sending, with a retry while the PC doesn't answer ----
  function schedule(lot) {
    if (timers.has(lot)) return;
    timers.set(lot, view.setTimeout(() => { timers.delete(lot); send(lot); }, PHONE_BENCH_RETRY_MS));
  }

  // The newest copy of a lot's progress: the open one (with any newer copy
  // another tab kept, whose storage event may not have arrived yet), else the
  // kept one. A send or merge that lands after the lot was reopened updates what
  // is open now.
  function liveProgress(lot) {
    if (current?.lot !== lot) return phoneBenchLoad(store, lot);
    adoptKept();
    return current;
  }

  function sameSend(first, second) {
    return JSON.stringify(first.actuals) === JSON.stringify(second.actuals) && first.notes === second.notes;
  }

  async function send(lot) {
    // A send on its way checks, when it lands, whether anything changed
    // meanwhile; a merge under way sends what it merged once it is done.
    if (sending.has(lot) || merging.has(lot)) return;
    const progress = liveProgress(lot);
    if (!progress || progress.conflict) return;
    const body = phoneBenchBody(progress);
    progress.pending = true;
    // What the PC holds if this send is saved, kept until the PC answers: if the
    // answer is lost, or the page closes first, a later merge knows the PC may
    // hold it (phoneBenchMergeBase).
    // Every one is kept, the oldest included: all were built on the same saved
    // set, so the PC holds at most one of them, the first that reached it. A
    // retry of the same amounts is kept once.
    const attempt = { id: `${Date.now().toString(36)}.${(sendCount += 1)}`, entries: { ...progress.entries }, notes: body.notes || phoneBenchNotesOf(progress.base?.notes) };
    const known = Array.isArray(progress.unanswered) ? progress.unanswered : [];
    progress.unanswered = known.some((item) => phoneBenchSameSet(item, attempt)) ? known : [...known, attempt];
    if (!keepFor(progress)) {
      render();
      showList();
      return;
    }
    sending.add(lot);
    render();
    let record = null;
    let failure = null;
    try {
      record = await request(`/v2/batches/${encodeURIComponent(lot)}/actuals`, { method: "POST", body: JSON.stringify(body) });
    } catch (error) {
      failure = error || new Error("no answer");
    }
    sending.delete(lot);
    const live = liveProgress(lot) || progress;
    // The lot was recorded again as another batch meanwhile, and its new copy
    // is open: this answer was about the earlier batch. What was weighed for the
    // new batch while this send held the lot goes now.
    if (live.batch !== progress.batch) {
      render();
      showList();
      if (live.pending && !phoneBenchStuck(live)) send(lot);
      return;
    }
    let next = null;
    live.offline = false;
    // A send the PC refused was not saved, and a saved one is the new base; one
    // with no answer, or a server error, may have been saved.
    if (record) live.unanswered = [];
    else if (failure.status && failure.status < 500) live.unanswered = (live.unanswered || []).filter((item) => item?.id !== attempt.id);
    if (record) {
      merges.delete(lot);
      const server = phoneBenchServer(live.steps, record);
      // Nothing changed while it was on its way: the phone now holds what the PC holds.
      if (sameSend(phoneBenchBody(live), body)) {
        live.entries = { ...server.entries };
        live.notes = server.notes;
      }
      live.base = server;
      live.error = "";
      live.problem = "";
      live.pending = phoneBenchChanged(live);
      if (live.pending) next = "send";
      else live.savedAt = record.actuals_recorded_at || new Date().toISOString();
    } else if (failure.status === 409 && failure.code === "BATCH_CHANGED") {
      next = "merge";
    } else if (failure.status === 409 && failure.code === "BATCH_REPLACED") {
      live.problem = "otherBatch";
    } else if (failure.status && failure.status < 500) {
      // A refusal is kept and shown; only a PC that didn't answer is tried again.
      live.error = failure.message || String(failure.status);
    } else {
      live.offline = true;
      schedule(lot);
    }
    keepFor(live);
    render();
    showList();
    if (next === "merge") await merge(lot, live.batch);
    else if (next === "send") send(lot);
  }

  // Another device saved this batch since the phone's last send: merge what the
  // PC holds now with what the phone holds, and send again, unless both changed
  // a line, which waits for the person's choice.
  async function merge(lot, batch) {
    if (merging.has(lot)) return;
    merging.add(lot);
    render();
    const tries = (merges.get(lot) || 0) + 1;
    merges.set(lot, tries);
    let record = null;
    let failure = null;
    try {
      record = await request(`/v2/batches/${encodeURIComponent(lot)}`);
    } catch (error) {
      failure = error || new Error("no answer");
    }
    merging.delete(lot);
    const live = liveProgress(lot);
    // Reopened meanwhile as another batch with this lot: the merge was for the earlier one.
    if (!live || live.batch !== batch) {
      render();
      if (live?.pending && !phoneBenchStuck(live)) send(lot);
      return;
    }
    if (!record) {
      if (failure.status && failure.status < 500) {
        live.offline = false;
        live.error = failure.message || String(failure.status);
      } else {
        live.offline = true;
        schedule(lot);
      }
    } else if (record.recorded_at !== live.batch) {
      live.problem = "otherBatch";
    } else {
      const server = phoneBenchServer(live.steps, record);
      const merged = phoneBenchMerge(phoneBenchMergeBase(live.base, live.unanswered, server), server, live);
      live.entries = merged.entries;
      live.notes = merged.notes;
      if (merged.conflict) {
        // The base stays as it was, so a later merge still sees the same lines as changed on both.
        live.conflict = { ...merged.conflict, server, savedAt: record.actuals_recorded_at || null };
        live.pending = true;
        if (live === current) live.at = live.steps.length;
      } else {
        live.base = server;
        live.unanswered = [];
        live.pending = phoneBenchChanged(live);
        if (!live.pending) live.savedAt = record.actuals_recorded_at || live.savedAt;
        else if (tries > PHONE_BENCH_MERGES_IN_A_ROW) live.problem = "keepsChanging";
      }
    }
    keepFor(live);
    render();
    showList();
    if (live.pending && !phoneBenchStuck(live)) send(lot);
  }

  function resume() {
    for (const lot of phoneBenchPendingLots(store)) send(lot);
  }

  // The page behind the full-screen view can't be reached with the keyboard.
  function setPageInert(on) {
    if (!on) {
      for (const element of inerted.splice(0)) element.inert = false;
      return;
    }
    for (const element of doc.body.children) {
      // Another full-screen view (smell strips) is never made inert by this one.
      if (element === sheet || element.inert || element.getAttribute("aria-modal") === "true") continue;
      element.inert = true;
      inerted.push(element);
    }
  }

  // ---- drawing ----
  function render() {
    sheet.setAttribute("lang", lang);
    langButton.textContent = say("otherLanguage");
    langButton.setAttribute("aria-label", say("otherLanguageName"));
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", say("close"));
    if (!current) return;
    const focusWas = doc.activeElement;
    const steps = current.steps;
    const anyGrams = steps.some((item) => item.grams);
    byButton.hidden = !anyGrams;
    byButton.textContent = current.by === "g" ? say("inUnits") : say("inGrams");
    lotLine.textContent = `${current.lot} · ${current.formula}`;
    const count = countOf(current);
    bar.max = Math.max(steps.length, 1);
    bar.value = count;
    bar.setAttribute("aria-label", say("progressLabel"));
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
      const conflict = current.conflict;
      const onBoth = new Map((conflict?.lines || []).map((item) => [String(item.line), item.pc]));
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
        if (onBoth.has(String(item.line))) {
          const pc = onBoth.get(String(item.line));
          button.classList.add("is-conflict");
          button.append(node("span", { className: "phone-bench-summary-pc" }, say("pcHas", { amount: pc ? `${pc.typed} ${pc.unit}` : say("pcNothing") })));
        }
        button.addEventListener("click", () => { current.at = index; keep(); render(); input.focus(); });
        row.append(button);
        return row;
      }));
      choose.hidden = !conflict;
      keepPhone.textContent = say("keepPhone");
      usePc.textContent = say("usePc");
      notesLabel.textContent = say("notes");
      if (doc.activeElement !== notes) notes.value = current.notes || "";
      const notesOnBoth = conflict && conflict.notes !== null && conflict.notes !== undefined;
      pcNotes.hidden = !notesOnBoth;
      pcNotes.textContent = notesOnBoth ? say("pcHas", { amount: conflict.notes || say("pcNothing") }) : "";
      sendNow.textContent = say("sendNow");
      sendNow.hidden = Boolean(conflict) || !current.pending || sending.has(current.lot) || merging.has(current.lot);
    }
    // The control that had the focus was hidden or replaced: keep the focus in the view.
    if (!sheet.hidden && focusWas && focusWas !== doc.body && (!focusWas.isConnected || focusWas.closest("[hidden]"))) {
      (atStep ? input : doneTitle).focus();
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
      const kept = phoneBenchLoad(store, record.lot);
      const local = kept && kept.batch === record.recorded_at ? kept : null;
      const saved = (record.actuals || []).length;
      const total = (record.planned_rows || []).length;
      const item = node("li", { className: "phone-bench-batch" });
      const words = node("div");
      words.append(
        node("strong", {}, record.lot),
        node("span", {}, ` ${record.formula_name} · ${record.bottles} × ${record.bottle_ml} mL · ${record.made_on}`),
      );
      const progressLine = node("p", { className: "field-help" }, local?.pending
        ? say("keptOnPhone", { count: countOf(local) })
        : say("weighedCount", { done: saved, total }));
      words.append(progressLine);
      const button = node("button", { type: "button", className: "primary-button phone-bench-open" }, saved || countOf(local) ? say("carryOn") : say("weigh"));
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
    const ticket = ++openTicket;
    // The language may have been changed in the smell strips view meanwhile.
    try { lang = store.getItem(PHONE_BENCH_LANG) === "th" ? "th" : "en"; } catch { /* keep the one in use */ }
    listStatus.textContent = say("opening", { lot });
    let record = null;
    let failure = null;
    try {
      record = await request(`/v2/batches/${encodeURIComponent(lot)}`);
    } catch (error) {
      failure = error;
    }
    const steps = record ? await stepsWithGrams(record) : null;
    // A lot tapped later wins; this one was left behind.
    if (ticket !== openTicket) return;
    // Another full-screen view (smell strips) took the page while the PC answered.
    if ([...doc.querySelectorAll("[aria-modal='true']")].some((element) => element !== sheet && !element.hidden)) {
      listStatus.textContent = "";
      return;
    }
    // Read the kept copy only now: a send that landed meanwhile has updated it.
    let local = phoneBenchLoad(store, lot);
    let aside = "";
    const raw = record ? phoneBenchRaw(store, lot) : null;
    if (raw && (!local || local.batch !== record.recorded_at)) {
      // Kept for an earlier batch that had this lot number, or by an earlier
      // version of this page: set aside, never sent here and never dropped. That
      // version sent notes only when the box lost focus, so notes it kept that
      // the PC doesn't hold count as not sent.
      const unsentNotes = !raw.base && phoneBenchNotesOf(raw.notes) && phoneBenchNotesOf(raw.notes) !== phoneBenchNotesOf(record.actual_notes);
      if (raw.pending || raw.conflict || unsentNotes) {
        phoneBenchSetAside(store, { ...raw, lot, batch: typeof raw.batch === "string" ? raw.batch : "earlier" });
        aside = say("setAside", { lot });
      }
      local = null;
    }
    if (!record && !local) {
      listStatus.textContent = say("openFailed", { lot, message: failure?.message || "no answer" });
      return;
    }
    let progress = local;
    if (record) {
      // The PC's amounts, unless this phone holds amounts it hasn't confirmed:
      // those are merged with the PC's line by line.
      const server = phoneBenchServer(steps, record);
      progress = {
        lot: record.lot,
        batch: record.recorded_at,
        formula: record.formula_name,
        steps,
        entries: { ...server.entries },
        notes: server.notes,
        base: server,
        at: 0,
        by: local?.by || "g",
        pending: false,
        savedAt: record.actuals_recorded_at || null,
        error: "",
        conflict: null,
      };
      if (local && (local.pending || local.conflict)) {
        const merged = phoneBenchMerge(phoneBenchMergeBase(local.base, local.unanswered, server), server, local);
        progress.entries = merged.entries;
        progress.notes = merged.notes;
        progress.savedAt = local.savedAt || progress.savedAt;
        progress.error = local.error || "";
        // A send still on its way, or whose answer was lost, may yet be saved.
        progress.unanswered = local.unanswered || [];
        if (merged.conflict) {
          progress.conflict = { ...merged.conflict, server, savedAt: record.actuals_recorded_at || null };
          progress.base = local.base;
        }
        progress.pending = Boolean(merged.conflict) || phoneBenchChanged(progress);
      }
      progress.at = progress.conflict ? steps.length : phoneBenchNextIndex(steps, progress.entries, -1);
    }
    current = progress;
    merges.delete(lot);
    // Any earlier batch's copy was set aside above; this one replaces it.
    write(current);
    listStatus.textContent = "";
    notice.textContent = aside;
    input.dataset.line = "";
    sheet.hidden = false;
    doc.body.classList.add("phone-bench-open");
    setPageInert(true);
    render();
    (current.at < current.steps.length ? input : doneTitle).focus?.();
    if (record && current.pending && !phoneBenchStuck(current)) send(current.lot);
  }

  function close() {
    view.clearTimeout(notesTimer);
    if (current?.pending && !phoneBenchStuck(current)) send(current.lot);
    sheet.hidden = true;
    doc.body.classList.remove("phone-bench-open");
    setPageInert(false);
    notice.textContent = "";
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
    current.problem = "";
    if (phoneBenchChanged(current)) current.pending = true;
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
  // Notes count as a change to send: they go after a short pause in typing, when
  // the box loses focus, or with the next send, even if the page closes first.
  notes.addEventListener("input", () => {
    if (!current) return;
    current.notes = notes.value;
    if (phoneBenchChanged(current)) current.pending = true;
    keep();
    sync.textContent = syncWords(current);
    sendNow.hidden = Boolean(current.conflict) || !current.pending || sending.has(current.lot) || merging.has(current.lot);
    view.clearTimeout(notesTimer);
    const lot = current.lot;
    notesTimer = view.setTimeout(() => send(lot), PHONE_BENCH_NOTES_MS);
  });
  notes.addEventListener("change", () => { if (current?.pending) send(current.lot); });
  sendNow.addEventListener("click", () => {
    if (!current) return;
    current.error = "";
    current.problem = "";
    merges.delete(current.lot);
    send(current.lot);
  });
  // Both choices start from what the PC holds now; the next send is checked against it.
  keepPhone.addEventListener("click", () => {
    if (!current?.conflict) return;
    current.base = current.conflict.server;
    current.unanswered = [];
    current.conflict = null;
    current.pending = phoneBenchChanged(current);
    keep();
    render();
    if (current.pending) send(current.lot);
  });
  usePc.addEventListener("click", () => {
    if (!current?.conflict) return;
    const { server, lines, notes: theirs, savedAt } = current.conflict;
    for (const { line } of lines) {
      if (server.entries[line]) current.entries[line] = server.entries[line];
      else delete current.entries[line];
    }
    if (theirs !== null && theirs !== undefined) current.notes = theirs;
    current.base = server;
    current.unanswered = [];
    current.conflict = null;
    current.pending = phoneBenchChanged(current);
    // Nothing left to send: what is shown is what the PC saved, and when.
    if (!current.pending) current.savedAt = savedAt || new Date().toISOString();
    keep();
    render();
    if (current.pending) send(current.lot);
  });
  view.addEventListener("online", resume);
  view.addEventListener("storage", (event) => {
    if (current && event.key === PHONE_BENCH_STORE + current.lot && adoptKept()) render();
  });
  // A phone that locks or switches app may close the page: send what is kept now.
  doc.addEventListener("visibilitychange", () => { if (doc.visibilityState === "hidden") resume(); });

  showList();
  resume();
  phoneBench = { show, open, close, resume, send };
  return phoneBench;
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    PHONE_BENCH_STORE, PHONE_BENCH_ASIDE, PHONE_BENCH_LANG, PHONE_BENCH_WORDS, phoneBenchSay, phoneBenchFixed, phoneBenchSourceRows,
    phoneBenchSteps, phoneBenchShows, phoneBenchDeviation, phoneBenchEntry, phoneBenchActual, phoneBenchBody, phoneBenchSeed,
    phoneBenchServer, phoneBenchSame, phoneBenchSameSet, phoneBenchChanged, phoneBenchMerge, phoneBenchMergeBase, phoneBenchStuck, phoneBenchNextIndex,
    phoneBenchLoad, phoneBenchRaw, phoneBenchKeep, phoneBenchSetAside, phoneBenchPendingLots, attachPhoneBench,
  };
}
