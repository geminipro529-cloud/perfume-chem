"use strict";

// Smell strips on the phone: dip a strip from a Lab bottle, and the phone shows
// each strip check of the smell log (10 min, 1 h, 3 h) as it comes due, with the
// smell log's own questions (what leads, what is weak, how much you like it, a
// few words) in big buttons, in English or Thai.
//
// Each check opens at its time and stays open for half that time again (the
// 10 min check until 15 min, the 1 h check until 1 h 30, the 3 h check until
// 4 h 30), so a note is filed under the time it was really smelled at; a check
// left longer is missed, and the Bottles page's smell log can still take it.
//
// The strips and the notes are kept in this browser's localStorage. A note goes
// to the bottle's smell log (POST /bottles/{id}/smell-log) whenever the PC
// answers, carrying a client_id, so sending it again after a lost answer saves
// no copy. Browsers allow notifications and keeping the screen awake only over
// HTTPS or on the PC itself, and the phone opens the app over plain http on the
// home network, so a locked phone can't ring: the page shows what is due when it
// is looked at again, and buzzes (where the phone allows it) while it is open.
//
// lab/bottles.js calls attachPhoneStrips once; lab/core.js hands it the bottle
// list after each refresh. The DOM is built with createElement + textContent
// only, never HTML strings. Node loads the pure functions in the tests through
// module.exports.

const PHONE_STRIPS_ACTIVE = "perfumechem.strips.v1.active";
const PHONE_STRIPS_OUTBOX = "perfumechem.strips.v1.outbox";
// The same language choice as phone bench mode (phone-bench.js).
const PHONE_STRIPS_LANG = "perfumechem.bench.lang";
const PHONE_STRIPS_RETRY_MS = 15000;
const PHONE_STRIPS_TICK_MS = 1000;
// A finished strip leaves the list this long after it was dipped.
const PHONE_STRIPS_KEEP_MS = 12 * 3600 * 1000;
// The smell log's strip windows (SMELL_LOG_WINDOWS in lab_service.py), in seconds.
const PHONE_STRIP_CHECKS = [
  { window: "strip_10m", at: 600, name: "check10" },
  { window: "strip_1h", at: 3600, name: "check1h" },
  { window: "strip_3h", at: 10800, name: "check3h" },
];

const phoneStripsSmell = typeof smellLogBody === "function"
  ? { smellLogBody, nextSmellChipState }
  : require("./smell-log.js");

const PHONE_STRIPS_WORDS = {
  en: {
    panelTitle: "Smell strips on the phone",
    panelHelp: "Dip a strip from a bottle and the phone tells you when to smell it: at 10 min, 1 h and 3 h. Your notes go to the bottle's smell log, and stay on this phone until the PC answers. Keep this page open; a locked phone can't ring.",
    open: "Smell strips step by step",
    title: "Smell strips",
    stripsTitle: "Strips you dipped",
    noStrips: "No strip dipped yet.",
    dip: "Dip a strip",
    pickTitle: "Which bottle?",
    noBottles: "No bottle yet. Add one on the Bottles page first.",
    dipHelp: "Dip a strip in it, write the bottle's name on the strip, then tap Dipped.",
    dipped: "Dipped now",
    hasStrip: "a strip is on its way",
    back: "Back",
    allStrips: "All strips",
    endStrip: "End this strip",
    endConfirm: "Tap again to end it",
    dippedAt: "Dipped at {time}",
    check10: "10 min",
    check1h: "1 h",
    check3h: "3 h",
    checkWaiting: "{name}: at {time}",
    checkOpen: "{name}: smell it now",
    checkLogged: "{name}: noted",
    checkMissed: "{name}: missed",
    nextIn: "Next: the {name} check in {clock}",
    smellNow: "Smell now: the {name} check",
    smellNowOther: "Smell now: {label}, the {name} check",
    goThere: "Go to that strip",
    openUntil: "Open until {time}",
    closedTitle: "The {name} check closed at {time}",
    lateHelp: "Your note is kept. Save files it as smelled at {time}, when you started it.",
    closedKept: "The {name} check closed while you were writing. Your note is kept below.",
    dropNote: "Drop this note",
    finished: "Done: every check is noted or missed.",
    whatSmell: "What do you smell?",
    leadsWord: "leads",
    weakWord: "weak",
    chipHelp: "Tap a name once if it leads, twice if it is weak, a third time to clear.",
    leadsTyped: "Leads (names, comma-separated)",
    weakTyped: "Weak (names, comma-separated)",
    liking: "How much do you like it, 1 to 10",
    words: "In a few words",
    save: "Save",
    noted: "Noted.",
    needSomething: "Mark at least one name, a liking or a few words.",
    bothMarked: "{names}: marked both leading and weak. Pick one for each.",
    tooMany: "Mark at most {max} names as leading, and {max} as weak.",
    notKept: "This phone could not keep the note (its storage is full or blocked), so it is not saved. Note it on the PC's smell log instead.",
    noRecipe: "This bottle has no recipe in the Lab, so its strips won't teach the model. Your notes are still kept.",
    rowsLoading: "The recipe names come when the PC answers. You can type names meanwhile.",
    nose: "Your nose: {n} of {min} bottles logged. The Lab starts learning from your nose at {min}.",
    noseOn: "The Lab uses what your nose taught it ({n} bottles).",
    noseNotYet: "{n} bottles logged. What they teach doesn't beat the plain model yet, so the Lab doesn't use it.",
    kept: "{count} kept on this phone, not on the PC yet.",
    allOnPc: "Every note is on the PC.",
    sendingNotes: "Sending to the PC…",
    offline: "No connection to the PC. {count} kept on this phone; they go when it answers.",
    refused: "The PC refused a note for {label}: {message}",
    refusedWhat: "The note: {text}",
    tryAgain: "Try again",
    remove: "Remove it",
    close: "Close",
    otherLanguage: "ไทย",
    otherLanguageName: "Thai",
  },
  th: {
    panelTitle: "แถบดมกลิ่นบนโทรศัพท์",
    panelHelp: "จุ่มแถบดมกลิ่นจากขวด แล้วโทรศัพท์จะบอกเวลาให้ดม: ที่ 10 นาที 1 ชั่วโมง และ 3 ชั่วโมง บันทึกของคุณจะเข้าไปในบันทึกกลิ่นของขวดนั้น และเก็บไว้ในโทรศัพท์จนกว่าคอมพิวเตอร์จะตอบรับ อย่าปิดหน้านี้ โทรศัพท์ที่ล็อกหน้าจออยู่จะส่งเสียงเตือนไม่ได้",
    open: "ดมแถบทีละขั้น",
    title: "แถบดมกลิ่น",
    stripsTitle: "แถบที่จุ่มไว้",
    noStrips: "ยังไม่ได้จุ่มแถบ",
    dip: "จุ่มแถบ",
    pickTitle: "ขวดไหน?",
    noBottles: "ยังไม่มีขวด เพิ่มขวดในหน้าขวดก่อน",
    dipHelp: "จุ่มแถบลงในขวด เขียนชื่อขวดบนแถบ แล้วแตะ จุ่มแล้ว",
    dipped: "จุ่มแล้ว",
    hasStrip: "มีแถบที่กำลังรอดมอยู่",
    back: "ย้อนกลับ",
    allStrips: "แถบทั้งหมด",
    endStrip: "จบแถบนี้",
    endConfirm: "แตะอีกครั้งเพื่อจบ",
    dippedAt: "จุ่มเมื่อ {time}",
    check10: "10 นาที",
    check1h: "1 ชั่วโมง",
    check3h: "3 ชั่วโมง",
    checkWaiting: "{name}: เวลา {time}",
    checkOpen: "{name}: ดมได้เลย",
    checkLogged: "{name}: บันทึกแล้ว",
    checkMissed: "{name}: พลาดไปแล้ว",
    nextIn: "ครั้งต่อไป: รอบ {name} อีก {clock}",
    smellNow: "ดมตอนนี้: รอบ {name}",
    smellNowOther: "ดมตอนนี้: {label} รอบ {name}",
    goThere: "ไปที่แถบนั้น",
    openUntil: "ดมได้ถึง {time}",
    closedTitle: "รอบ {name} ปิดไปเมื่อ {time}",
    lateHelp: "บันทึกของคุณยังอยู่ กดบันทึกเพื่อเก็บเป็นการดมเมื่อ {time} ตอนที่คุณเริ่มเขียน",
    closedKept: "รอบ {name} ปิดไปขณะที่คุณกำลังเขียน บันทึกของคุณยังอยู่ด้านล่าง",
    dropNote: "ทิ้งบันทึกนี้",
    finished: "เสร็จแล้ว: ทุกรอบบันทึกแล้วหรือพลาดไปแล้ว",
    whatSmell: "ได้กลิ่นอะไร?",
    leadsWord: "เด่น",
    weakWord: "จาง",
    chipHelp: "แตะชื่อหนึ่งครั้งถ้ากลิ่นนั้นเด่น สองครั้งถ้าจาง ครั้งที่สามเพื่อล้าง",
    leadsTyped: "กลิ่นเด่น (ชื่อ คั่นด้วยจุลภาค)",
    weakTyped: "กลิ่นจาง (ชื่อ คั่นด้วยจุลภาค)",
    liking: "ชอบแค่ไหน 1 ถึง 10",
    words: "อธิบายสั้นๆ",
    save: "บันทึก",
    noted: "บันทึกแล้ว",
    needSomething: "เลือกชื่ออย่างน้อยหนึ่งชื่อ ให้คะแนนความชอบ หรือเขียนสั้นๆ",
    bothMarked: "{names}: เลือกไว้ทั้งเด่นและจาง เลือกได้อย่างเดียวต่อชื่อ",
    tooMany: "เลือกกลิ่นเด่นได้ไม่เกิน {max} ชื่อ และกลิ่นจางไม่เกิน {max} ชื่อ",
    notKept: "โทรศัพท์เก็บบันทึกนี้ไม่ได้ (พื้นที่เต็มหรือถูกปิดกั้น) จึงยังไม่ได้บันทึก กรุณาบันทึกในบันทึกกลิ่นบนคอมพิวเตอร์แทน",
    noRecipe: "ขวดนี้ไม่มีสูตรในแล็บ แถบของขวดนี้จึงไม่ช่วยสอนโมเดล แต่บันทึกของคุณยังเก็บไว้",
    rowsLoading: "ชื่อในสูตรจะขึ้นเมื่อคอมพิวเตอร์ตอบรับ ระหว่างนี้พิมพ์ชื่อเองได้",
    nose: "จมูกของคุณ: บันทึกแล้ว {n} จาก {min} ขวด แล็บจะเริ่มเรียนรู้จากจมูกของคุณเมื่อครบ {min} ขวด",
    noseOn: "แล็บใช้สิ่งที่จมูกของคุณสอนแล้ว ({n} ขวด)",
    noseNotYet: "บันทึกแล้ว {n} ขวด สิ่งที่เรียนรู้ยังไม่ดีกว่าโมเดลเดิม แล็บจึงยังไม่ใช้",
    kept: "เก็บไว้ในโทรศัพท์ {count} รายการ ยังไม่ถึงคอมพิวเตอร์",
    allOnPc: "บันทึกทั้งหมดอยู่ในคอมพิวเตอร์แล้ว",
    sendingNotes: "กำลังส่งไปที่คอมพิวเตอร์…",
    offline: "เชื่อมต่อคอมพิวเตอร์ไม่ได้ เก็บไว้ในโทรศัพท์ {count} รายการ จะส่งเมื่อเชื่อมต่อได้",
    refused: "คอมพิวเตอร์ไม่รับบันทึกของ {label}: {message}",
    refusedWhat: "บันทึก: {text}",
    tryAgain: "ลองอีกครั้ง",
    remove: "ลบออก",
    close: "ปิด",
    otherLanguage: "English",
    otherLanguageName: "อังกฤษ",
  },
};

function phoneStripsSay(lang, key, values = {}) {
  const words = PHONE_STRIPS_WORDS[lang] || PHONE_STRIPS_WORDS.en;
  const template = words[key] ?? PHONE_STRIPS_WORDS.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}

// Each check of a strip at `now` (ms): waiting, open, noted or missed, with the
// times it opens and closes. A check stays open for half its own time again.
function phoneStripChecks(strip, now) {
  const dipped = Date.parse(strip?.dippedAt || "");
  const logged = strip?.logged || {};
  return PHONE_STRIP_CHECKS.map((check) => {
    const dueAt = dipped + check.at * 1000;
    const closesAt = dipped + check.at * 1500;
    let status = "waiting";
    if (logged[check.window]) status = "logged";
    else if (!Number.isFinite(dipped)) status = "missed";
    else if (now >= closesAt) status = "missed";
    else if (now >= dueAt) status = "open";
    return { window: check.window, name: check.name, dueAt, closesAt, status };
  });
}

// The check to show next: the open one, else the next one still to come.
function phoneStripNext(checks) {
  return checks.find((check) => check.status === "open")
    || checks.find((check) => check.status === "waiting")
    || null;
}

function phoneStripFinished(checks) {
  return checks.every((check) => check.status === "logged" || check.status === "missed");
}

// A finished strip is dropped from the list half a day after it was dipped.
function phoneStripExpired(strip, now) {
  const dipped = Date.parse(strip?.dippedAt || "");
  if (!Number.isFinite(dipped)) return true;
  return phoneStripFinished(phoneStripChecks(strip, now)) && now - dipped > PHONE_STRIPS_KEEP_MS;
}

// Countdown text: "4:05" under an hour, "1:02:05" from an hour.
function phoneStripClock(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}` : `${minutes}:${seconds}`;
}

// The check whose note was being written when it closed: it stays on screen to
// be saved or dropped until the next check opens. `hasDraft(window)` says
// whether a note for that check has anything in it.
function phoneStripLateCheck(checks, hasDraft, now) {
  for (let index = checks.length - 1; index >= 0; index -= 1) {
    const check = checks[index];
    if (check.status !== "missed" || !hasDraft(check.window)) continue;
    const later = checks[index + 1];
    return later && now >= later.dueAt ? null : check;
  }
  return null;
}

// What the PC would refuse in a note (lab_service.add_smell_log's rules): a
// name both leading and weak, or more than 12 names in a list. Names count once
// whatever their case, as on the PC.
const PHONE_STRIPS_MAX_NAMES = 12;
function phoneStripsProblem(lang, body) {
  const fold = (name) => String(name).trim().toLowerCase();
  const once = (names) => [...new Map((names || []).filter((name) => String(name).trim()).map((name) => [fold(name), String(name).trim()])).values()];
  const leads = once(body.leads);
  const weak = once(body.weak);
  const weakKeys = new Set(weak.map(fold));
  const both = leads.filter((name) => weakKeys.has(fold(name)));
  if (both.length) return phoneStripsSay(lang, "bothMarked", { names: both.join(", ") });
  if (leads.length > PHONE_STRIPS_MAX_NAMES || weak.length > PHONE_STRIPS_MAX_NAMES) {
    return phoneStripsSay(lang, "tooMany", { max: PHONE_STRIPS_MAX_NAMES });
  }
  return "";
}

// A kept note in one line, so a refused one can be noted again by hand.
function phoneStripsNoteText(lang, note) {
  const check = PHONE_STRIP_CHECKS.find((item) => item.window === note?.window);
  const parts = [check ? phoneStripsSay(lang, check.name) : note?.window];
  if (note?.liking) parts.push(`${note.liking}/10`);
  if (note?.leads?.length) parts.push(`${phoneStripsSay(lang, "leadsWord")}: ${note.leads.join(", ")}`);
  if (note?.weak?.length) parts.push(`${phoneStripsSay(lang, "weakWord")}: ${note.weak.join(", ")}`);
  if (note?.words) parts.push(`“${note.words}”`);
  return parts.filter(Boolean).join(" · ");
}

// The smell log request body of a kept note.
function phoneStripNoteBody(note) {
  return {
    window: note.window,
    leads: [...(note.leads || [])],
    weak: [...(note.weak || [])],
    liking: note.liking ?? null,
    words: note.words || "",
    logged_at: note.loggedAt,
    client_id: note.clientId,
  };
}

// Notes still to send, oldest first; a refused one waits for the person.
function phoneStripsToSend(outbox) {
  return Object.values(outbox || {})
    .filter((note) => note && note.clientId && !note.refused)
    .sort((a, b) => String(a.loggedAt).localeCompare(String(b.loggedAt)));
}

function phoneStripsRead(storage, key) {
  try {
    const value = JSON.parse(storage.getItem(key) || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch {
    return {};
  }
}

// What the Lab has learned from the smell log, in the person's language.
function phoneStripsNoseText(lang, calibration) {
  if (!calibration || !Number.isFinite(calibration.n_bottles)) return "";
  const values = { n: calibration.n_bottles, min: calibration.min_bottles };
  if (calibration.calibrated) return phoneStripsSay(lang, "noseOn", values);
  if (calibration.n_bottles < calibration.min_bottles) return phoneStripsSay(lang, "nose", values);
  return phoneStripsSay(lang, "noseNotYet", values);
}

let phoneStrips = null;

function attachPhoneStrips({ doc, request, root, storage = null }) {
  if (!root) return null;
  const view = doc.defaultView;
  let store = storage;
  if (!store) {
    try { store = view.localStorage; } catch { store = null; }
  }
  const memory = new Map();
  store = store || { getItem: (key) => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, String(value)) };

  const node = (tag, props = {}, text) => {
    const element = doc.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "className" || key === "type" || key === "value" || key === "hidden" || key === "disabled") element[key] = value;
      else element.setAttribute(key, value);
    }
    if (text !== undefined) element.textContent = text;
    return element;
  };

  let lang = "en";
  try { lang = store.getItem(PHONE_STRIPS_LANG) === "th" ? "th" : "en"; } catch { lang = "en"; }
  const say = (key, values) => phoneStripsSay(lang, key, values);
  const sending = new Set();
  let bottles = [];
  let calibration = null;
  let offline = false;
  let noseStale = false;
  let retryTimer = null;
  let ticker = null;
  let screen = "home";
  let currentBottle = "";
  let pickedBottle = "";
  let ending = false;
  let opener = null;
  const inerted = [];
  // Each strip's check statuses at the last tick, to see a check open or close.
  const tickStatuses = new Map();
  // The statuses the screen was drawn with: a change redraws it.
  let drawnStatuses = "";
  // Recipe names asked for and not answered yet.
  const rowsLoading = new Set();
  // A note being written, per strip and check: chips, liking, what was typed and
  // when it was started. Kept while Kenny looks at another strip or closes the
  // view, and dropped once saved, dropped by him, or past its check.
  const drafts = new Map();
  const draftKey = (bottleId, window) => `${bottleId}\u0000${window}`;
  // The note the form shows, and its key.
  let draft = null;
  let shownKey = null;

  const clock = () => Date.now();
  const timeText = (ms) => new Date(ms).toLocaleTimeString(lang === "th" ? "th-TH" : [], { hour: "2-digit", minute: "2-digit" });
  const newId = (window) => `strip.${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}.${window}`;

  // ---- kept on the phone: every write re-reads, so two tabs' changes add up ----
  function activeStrips() { return phoneStripsRead(store, PHONE_STRIPS_ACTIVE); }
  function outbox() { return phoneStripsRead(store, PHONE_STRIPS_OUTBOX); }
  // false when the phone could not keep it (storage full or blocked).
  function writeKey(key, value) {
    try { store.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
  }
  function changeStrips(change) {
    const strips = activeStrips();
    change(strips);
    return writeKey(PHONE_STRIPS_ACTIVE, strips);
  }
  function changeOutbox(change) {
    const notes = outbox();
    change(notes);
    return writeKey(PHONE_STRIPS_OUTBOX, notes);
  }
  // Set a live region's text only when it changes, so it is not read out again.
  function setText(element, text) {
    if (element.textContent !== text) element.textContent = text;
  }
  function liveStrips() {
    const now = clock();
    const strips = activeStrips();
    const expired = Object.keys(strips).filter((id) => phoneStripExpired(strips[id], now));
    if (expired.length) changeStrips((live) => { for (const id of expired) delete live[id]; });
    return Object.values(activeStrips()).sort((a, b) => String(b.dippedAt).localeCompare(String(a.dippedAt)));
  }

  // ---- the panel in the Bottles view ----
  const title = node("h2", { id: "phone-strips-panel-title" });
  const help = node("p", { className: "field-help" });
  const panelNose = node("p", { className: "field-help phone-strips-nose" });
  const panelList = node("ul", { className: "phone-bench-list phone-strips-panel-list" });
  const openButton = node("button", { type: "button", className: "phone-bench-open phone-strips-open" });
  const panelSync = node("p", { className: "batch-status phone-strips-panel-sync", role: "status", "aria-live": "polite" });
  root.replaceChildren(node("p", { className: "panel-index" }, "Phone"), title, help, panelNose, panelList, openButton, panelSync);

  // ---- the full-screen view ----
  const sheet = node("div", { className: "phone-bench phone-strips", hidden: true, role: "dialog", "aria-modal": "true", "aria-labelledby": "phone-strips-heading" });
  const topLine = node("p", { className: "phone-bench-lot" });
  const langButton = node("button", { type: "button", className: "quiet-button phone-strips-lang" });
  const closeButton = node("button", { type: "button", className: "quiet-button phone-bench-close" });
  const top = node("div", { className: "phone-bench-top" });
  const topActions = node("div", { className: "phone-bench-top-actions" });
  topActions.append(langButton, closeButton);
  top.append(topLine, topActions);
  const notice = node("p", { className: "phone-bench-notice", role: "status", "aria-live": "polite" });
  // Another strip's check opened: one tap goes to it.
  const noticeGo = node("button", { type: "button", className: "quiet-button phone-strips-go", hidden: true });
  const heading = node("h2", { className: "phone-bench-material phone-strips-heading", id: "phone-strips-heading", tabindex: "-1" });

  const home = node("div", { className: "phone-strips-home" });
  const nose = node("p", { className: "phone-bench-how phone-strips-nose" });
  const stripList = node("ul", { className: "phone-bench-summary phone-strips-list" });
  const dipButton = node("button", { type: "button", className: "phone-bench-send phone-strips-dip" });
  home.append(nose, stripList, dipButton);

  const pick = node("div", { className: "phone-strips-pick", hidden: true });
  const pickHelp = node("p", { className: "phone-bench-how" });
  const bottleList = node("ul", { className: "phone-bench-summary phone-strips-bottles" });
  const dippedButton = node("button", { type: "button", className: "phone-bench-send phone-strips-dipped", hidden: true });
  const pickBack = node("button", { type: "button", className: "quiet-button phone-strips-back" });
  pick.append(pickHelp, bottleList, dippedButton, pickBack);

  const strip = node("div", { className: "phone-strips-strip", hidden: true });
  const dippedLine = node("p", { className: "phone-bench-how phone-strips-dipped-at" });
  const checkList = node("ol", { className: "phone-strips-checks" });
  const next = node("p", { className: "phone-bench-where phone-strips-next" });
  const recipeNote = node("p", { className: "phone-bench-notice phone-strips-no-recipe" });
  const form = node("form", { className: "phone-strips-form", hidden: true, novalidate: "" });
  const formTitle = node("p", { className: "phone-bench-put phone-strips-form-title" });
  const openUntil = node("p", { className: "phone-bench-how phone-strips-open-until" });
  const rowSet = node("fieldset", { className: "smell-log-group" });
  const rowLegend = node("legend");
  const chipHelp = node("p", { className: "field-help" });
  const chipList = node("div", { className: "smell-log-choices phone-strips-chips" });
  const leadsInput = node("input", { name: "leads_text", type: "text", autocomplete: "off", id: "phone-strips-leads" });
  const weakInput = node("input", { name: "weak_text", type: "text", autocomplete: "off", id: "phone-strips-weak" });
  const leadsLabel = node("label", { for: "phone-strips-leads" });
  const weakLabel = node("label", { for: "phone-strips-weak" });
  rowSet.append(rowLegend, chipHelp, chipList, leadsLabel, leadsInput, weakLabel, weakInput);
  const likingSet = node("fieldset", { className: "smell-log-group" });
  const likingLegend = node("legend");
  const likingButtons = node("div", { className: "smell-log-choices smell-log-liking phone-strips-liking" });
  likingSet.append(likingLegend, likingButtons);
  const wordsInput = node("input", { name: "words", type: "text", maxlength: "280", autocomplete: "off", id: "phone-strips-words" });
  const wordsLabel = node("label", { for: "phone-strips-words" });
  const save = node("button", { type: "submit", className: "phone-bench-save phone-strips-save" });
  const dropDraft = node("button", { type: "button", className: "quiet-button phone-strips-drop", hidden: true });
  const formStatus = node("p", { className: "phone-bench-check", role: "status", "aria-live": "polite" });
  form.append(formTitle, openUntil, rowSet, likingSet, wordsLabel, wordsInput, save, dropDraft, formStatus);
  const stripActions = node("div", { className: "phone-bench-actions phone-bench-move" });
  const allStrips = node("button", { type: "button", className: "quiet-button phone-strips-all" });
  const endStrip = node("button", { type: "button", className: "quiet-button phone-strips-end" });
  stripActions.append(allStrips, endStrip);
  strip.append(dippedLine, checkList, next, recipeNote, form, stripActions);

  const sync = node("div", { className: "phone-bench-sync phone-strips-sync" });
  const syncLine = node("p", { role: "status", "aria-live": "polite" });
  const refusedLine = node("p", { className: "phone-bench-check is-error", hidden: true });
  const refusedWhat = node("p", { className: "phone-bench-how phone-strips-refused-note", hidden: true });
  const syncActions = node("div", { className: "phone-bench-actions phone-bench-move", hidden: true });
  const tryAgain = node("button", { type: "button", className: "quiet-button phone-strips-try" });
  const removeNote = node("button", { type: "button", className: "quiet-button phone-strips-remove" });
  syncActions.append(tryAgain, removeNote);
  sync.append(syncLine, refusedLine, refusedWhat, syncActions);
  sheet.append(top, notice, noticeGo, heading, home, pick, strip, sync);
  doc.body.append(sheet);

  // ---- sending ----
  function refusedNote() {
    return Object.values(outbox()).find((note) => note?.refused) || null;
  }

  function syncText() {
    const waiting = phoneStripsToSend(outbox()).length;
    if (sending.size) return say("sendingNotes");
    if (waiting && offline) return say("offline", { count: waiting });
    if (waiting) return say("kept", { count: waiting });
    if (refusedNote()) return "";
    return say("allOnPc");
  }

  function schedule() {
    if (retryTimer) return;
    retryTimer = view.setTimeout(() => {
      retryTimer = null;
      resume();
    }, PHONE_STRIPS_RETRY_MS);
  }

  async function send(clientId) {
    if (sending.has(clientId)) return;
    const note = outbox()[clientId];
    if (!note || note.refused) return;
    sending.add(clientId);
    drawSync();
    let failure = null;
    try {
      await request(`/bottles/${encodeURIComponent(note.bottleId)}/smell-log`, { method: "POST", body: JSON.stringify(phoneStripNoteBody(note)) });
    } catch (error) {
      failure = error || new Error("no answer");
    }
    sending.delete(clientId);
    if (!failure) {
      offline = false;
      changeOutbox((notes) => { delete notes[clientId]; });
      noseStale = true;
      loadMissingRows();
    } else if (failure.status && failure.status < 500) {
      // A refusal is kept and shown; only a PC that didn't answer is tried again.
      offline = false;
      changeOutbox((notes) => {
        if (notes[clientId]) Object.assign(notes[clientId], { refused: true, error: failure.message || String(failure.status) });
      });
    } else {
      offline = true;
      schedule();
    }
    drawSync();
    drawPanel();
    // The count of logged bottles is read again once the notes have gone.
    if (noseStale && !sending.size && !sheet.hidden) loadNose();
  }

  function resume() {
    for (const note of phoneStripsToSend(outbox())) send(note.clientId);
  }

  // Back online: send what is kept, and fetch recipe names a strip still lacks.
  function online() {
    resume();
    loadMissingRows();
  }

  // Asked only while the view is open: the PC works it out over every logged bottle.
  async function loadNose() {
    noseStale = false;
    try {
      calibration = await request("/smell-log/calibration");
    } catch {
      return;
    }
    drawPanel();
    if (!sheet.hidden && screen === "home") nose.textContent = phoneStripsNoseText(lang, calibration);
  }

  // The bottle's recipe names, for the chips; kept with the strip for offline use.
  // A strip dipped while the PC didn't answer asks again (loadMissingRows).
  async function loadRows(bottleId) {
    if (rowsLoading.has(bottleId)) return;
    rowsLoading.add(bottleId);
    let data = null;
    try {
      data = await request(`/bottles/${encodeURIComponent(bottleId)}/smell-log`);
    } catch {
      return;
    } finally {
      rowsLoading.delete(bottleId);
    }
    const rows = Array.isArray(data?.rows) ? data.rows.filter((name) => typeof name === "string" && name) : [];
    changeStrips((strips) => {
      if (strips[bottleId]) Object.assign(strips[bottleId], { rows, hasRecipe: rows.length > 0 });
    });
    // A note started before the names came keeps what was typed; an untouched one gets the chips.
    for (const note of drafts.values()) {
      if (note.bottleId === bottleId && !note.chips.size && !draftHasContent(note)) for (const name of rows) note.chips.set(name, "");
    }
    if (!sheet.hidden && screen === "strip" && currentBottle === bottleId) render();
  }

  function loadMissingRows() {
    for (const item of liveStrips()) {
      if (item.hasRecipe === null || item.hasRecipe === undefined) loadRows(item.bottleId);
    }
  }

  function draftHasContent(note) {
    return Boolean(note && ([...note.chips.values()].some(Boolean) || note.liking
      || note.leads.trim() || note.weak.trim() || note.words.trim()));
  }

  function draftFor(item, window) {
    const key = draftKey(item.bottleId, window);
    if (!drafts.has(key)) {
      drafts.set(key, { key, bottleId: item.bottleId, window, chips: new Map((item.rows || []).map((name) => [name, ""])), liking: "", leads: "", weak: "", words: "", startedAt: 0 });
    }
    return drafts.get(key);
  }

  // Something was marked or typed: the note counts as started now, once.
  function touched() {
    if (draft && !draft.startedAt && draftHasContent(draft)) draft.startedAt = clock();
  }

  // ---- drawing ----
  function labelOf(bottleId, fallback = "") {
    return bottles.find((bottle) => bottle.id === bottleId)?.label || fallback || bottleId;
  }

  function nextText(item) {
    const checks = phoneStripChecks(item, clock());
    const coming = phoneStripNext(checks);
    if (!coming) return say("finished");
    if (coming.status === "open") return say("smellNow", { name: say(coming.name) });
    return say("nextIn", { name: say(coming.name), clock: phoneStripClock(coming.dueAt - clock()) });
  }

  function drawPanel() {
    root.setAttribute("lang", lang);
    title.textContent = say("panelTitle");
    help.textContent = say("panelHelp");
    openButton.textContent = say("open");
    panelNose.textContent = phoneStripsNoseText(lang, calibration);
    panelNose.hidden = !panelNose.textContent;
    panelList.replaceChildren(...liveStrips().map((item) => {
      const row = node("li", { className: "phone-bench-batch" });
      const text = node("div");
      text.append(node("strong", {}, labelOf(item.bottleId, item.label)), node("p", { className: "field-help" }, nextText(item)));
      row.append(text);
      return row;
    }));
    setText(panelSync, refusedNote() ? say("refused", { label: refusedNote().label || "", message: refusedNote().error || "" }) : syncText());
  }

  function drawSync() {
    setText(syncLine, syncText());
    const refused = refusedNote();
    refusedLine.hidden = !refused;
    refusedWhat.hidden = !refused;
    syncActions.hidden = !refused;
    refusedLine.textContent = refused ? say("refused", { label: refused.label || "", message: refused.error || "" }) : "";
    refusedWhat.textContent = refused ? say("refusedWhat", { text: phoneStripsNoteText(lang, refused) }) : "";
    tryAgain.textContent = say("tryAgain");
    removeNote.textContent = say("remove");
    if (!sheet.hidden) drawPanel();
  }

  function setPageInert(on) {
    if (!on) {
      for (const element of inerted.splice(0)) element.inert = false;
      return;
    }
    for (const element of doc.body.children) {
      // Another full-screen view (phone bench) is never made inert by this one.
      if (element === sheet || element.inert || element.getAttribute("aria-modal") === "true") continue;
      element.inert = true;
      inerted.push(element);
    }
  }

  function pressed(button, on) { button.setAttribute("aria-pressed", String(on)); }

  // `late`: the check closed while its note was being written (phoneStripLateCheck).
  function drawForm(item, check, late = false) {
    form.hidden = !check;
    if (!check) { draft = null; shownKey = null; return; }
    draft = draftFor(item, check.window);
    if (shownKey !== draft.key) {
      // Another note on screen: its own boxes, as it was left.
      shownKey = draft.key;
      leadsInput.value = draft.leads;
      weakInput.value = draft.weak;
      wordsInput.value = draft.words;
      formStatus.textContent = "";
    }
    if (late) {
      formTitle.textContent = say("closedTitle", { name: say(check.name), time: timeText(check.closesAt) });
      openUntil.textContent = say("lateHelp", { time: timeText(Math.min(draft.startedAt || check.closesAt, check.closesAt)) });
    } else {
      formTitle.textContent = say("smellNow", { name: say(check.name) });
      openUntil.textContent = say("openUntil", { time: timeText(check.closesAt) });
    }
    dropDraft.hidden = !late;
    dropDraft.textContent = say("dropNote");
    rowLegend.textContent = say("whatSmell");
    chipHelp.textContent = say("chipHelp");
    const typed = draft.chips.size === 0;
    chipHelp.hidden = typed;
    leadsLabel.hidden = !typed;
    leadsInput.hidden = !typed;
    weakLabel.hidden = !typed;
    weakInput.hidden = !typed;
    leadsLabel.textContent = say("leadsTyped");
    weakLabel.textContent = say("weakTyped");
    chipList.replaceChildren(...[...draft.chips.keys()].map((name) => {
      const mark = draft.chips.get(name);
      const button = node("button", { type: "button", className: "smell-log-choice smell-log-chip", "data-row": name }, mark ? `${name}: ${mark === "leads" ? say("leadsWord") : say("weakWord")}` : name);
      if (mark) button.dataset.mark = mark;
      pressed(button, Boolean(mark));
      return button;
    }));
    likingLegend.textContent = say("liking");
    likingButtons.replaceChildren(...Array.from({ length: 10 }, (_unused, index) => {
      const value = String(index + 1);
      const button = node("button", { type: "button", className: "smell-log-choice", "data-liking": value }, value);
      pressed(button, value === draft.liking);
      return button;
    }));
    wordsLabel.textContent = say("words");
    save.textContent = say("save");
  }

  function drawStrip() {
    const item = activeStrips()[currentBottle];
    if (!item) { screen = "home"; return drawHome(); }
    const now = clock();
    const checks = phoneStripChecks(item, now);
    heading.textContent = labelOf(item.bottleId, item.label);
    dippedLine.textContent = say("dippedAt", { time: timeText(Date.parse(item.dippedAt)) });
    checkList.replaceChildren(...checks.map((check) => {
      const key = { waiting: "checkWaiting", open: "checkOpen", logged: "checkLogged", missed: "checkMissed" }[check.status];
      const row = node("li", { className: `phone-strips-check is-${check.status}`, "data-window": check.window }, say(key, { name: say(check.name), time: timeText(check.dueAt) }));
      return row;
    }));
    const coming = phoneStripNext(checks);
    next.textContent = coming && coming.status === "waiting"
      ? say("nextIn", { name: say(coming.name), clock: phoneStripClock(coming.dueAt - clock()) })
      : (coming ? "" : say("finished"));
    next.hidden = !next.textContent;
    const noRows = item.hasRecipe === null || item.hasRecipe === undefined;
    recipeNote.textContent = item.hasRecipe === false ? say("noRecipe") : (noRows ? say("rowsLoading") : "");
    recipeNote.hidden = !recipeNote.textContent;
    const late = coming && coming.status === "open"
      ? null
      : phoneStripLateCheck(checks, (window) => draftHasContent(drafts.get(draftKey(item.bottleId, window))), clock());
    drawForm(item, coming && coming.status === "open" ? coming : late, Boolean(late));
    allStrips.textContent = say("allStrips");
    endStrip.textContent = ending ? say("endConfirm") : say("endStrip");
    drawnStatuses = statusesOf(item, now);
  }

  // Every live strip's check statuses, to see when the home list needs a redraw.
  function homeStatuses(items) {
    const now = clock();
    return items.map((item) => statusesOf(item, now)).join(";");
  }

  function drawHome() {
    heading.textContent = say("stripsTitle");
    nose.textContent = phoneStripsNoseText(lang, calibration);
    nose.hidden = !nose.textContent;
    const items = liveStrips();
    drawnStatuses = homeStatuses(items);
    stripList.replaceChildren(...(items.length ? items.map((item) => {
      const button = node("button", { type: "button", className: "phone-bench-summary-line phone-strips-line", "data-bottle": item.bottleId });
      button.append(node("span", { className: "phone-bench-summary-name" }, labelOf(item.bottleId, item.label)), node("span", {}, nextText(item)));
      const row = node("li");
      row.append(button);
      return row;
    }) : [node("li", { className: "phone-bench-how" }, say("noStrips"))]));
    dipButton.textContent = say("dip");
  }

  function drawPick() {
    const strips = activeStrips();
    heading.textContent = pickedBottle ? labelOf(pickedBottle) : say("pickTitle");
    if (pickedBottle) {
      pickHelp.textContent = say("dipHelp");
      bottleList.replaceChildren();
      bottleList.hidden = true;
    } else {
      pickHelp.textContent = bottles.length ? "" : say("noBottles");
      bottleList.hidden = false;
      bottleList.replaceChildren(...[...bottles].reverse().map((bottle) => {
        const button = node("button", { type: "button", className: "phone-bench-summary-line phone-strips-bottle", "data-bottle": bottle.id });
        button.append(node("span", { className: "phone-bench-summary-name" }, bottle.label || bottle.id));
        const live = strips[bottle.id];
        if (live && !phoneStripFinished(phoneStripChecks(live, clock()))) button.append(node("span", {}, say("hasStrip")));
        const row = node("li");
        row.append(button);
        return row;
      }));
    }
    pickHelp.hidden = !pickHelp.textContent;
    dippedButton.hidden = !pickedBottle;
    dippedButton.textContent = say("dipped");
    pickBack.textContent = say("back");
  }

  function render() {
    sheet.setAttribute("lang", lang);
    topLine.textContent = say("title");
    langButton.textContent = say("otherLanguage");
    langButton.setAttribute("aria-label", say("otherLanguageName"));
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", say("close"));
    // Keep the keyboard where it was: the same control after the redraw, else the heading.
    const focusWas = doc.activeElement;
    const focusKey = focusWas && sheet.contains(focusWas)
      ? ["row", "liking", "bottle", "window"].map((name) => [name, focusWas.dataset?.[name]]).find(([, value]) => value !== undefined)
      : null;
    home.hidden = screen !== "home";
    pick.hidden = screen !== "pick";
    strip.hidden = screen !== "strip";
    if (screen === "home") drawHome();
    else if (screen === "pick") drawPick();
    else drawStrip();
    drawSync();
    if (focusKey) {
      const [name, value] = focusKey;
      const again = [...sheet.querySelectorAll(`[data-${name}]`)].find((element) => element.dataset[name] === value);
      if (again && !again.closest("[hidden]")) { again.focus(); return; }
    }
    // Only a control that vanished in the redraw hands the focus to the heading. A
    // tap that left the focus on the page (Safari on iPhone) keeps it there, so
    // the view does not jump back to the top.
    const lost = focusWas && sheet.contains(focusWas) && (!focusWas.isConnected || Boolean(focusWas.closest("[hidden]")));
    if (!sheet.hidden && lost) heading.focus?.({ preventScroll: true });
  }

  // The statuses of one strip's checks, as drawStrip and the ticker compare them.
  function statusesOf(item, now = clock()) {
    return `${item.bottleId}:${phoneStripChecks(item, now).map((check) => check.status).join(",")}`;
  }

  // A notice at the top of the view; `goTo` adds the button to that strip, and
  // `forKey` is the check it is about, so it goes once that check closes.
  let noticeTarget = "";
  let noticeFor = null;
  function setNotice(text, goTo = "", forKey = null) {
    setText(notice, text);
    noticeTarget = goTo;
    noticeFor = forKey;
    noticeGo.hidden = !goTo;
    noticeGo.textContent = say("goThere");
  }

  // The second ticker runs while a strip still has a check to come, whether the
  // view is open or not, so the Bottles panel counts down too.
  function ensureTicker() {
    if (ticker) return;
    const now = clock();
    if (!liveStrips().some((item) => !phoneStripFinished(phoneStripChecks(item, now)))) return;
    ticker = view.setInterval(tick, PHONE_STRIPS_TICK_MS);
  }

  function stopTicker() {
    if (ticker) { view.clearInterval(ticker); ticker = null; }
  }

  // Every second: the countdowns, and a check opening or closing on any strip.
  function tick() {
    const now = clock();
    const items = liveStrips();
    let opened = null;
    let closed = null;
    const seen = new Set();
    for (const item of items) {
      const checks = phoneStripChecks(item, now);
      const before = tickStatuses.get(item.bottleId);
      tickStatuses.set(item.bottleId, checks.map((check) => check.status));
      seen.add(item.bottleId);
      if (!before) continue;
      checks.forEach((check, index) => {
        if (before[index] === "waiting" && check.status === "open") opened = opened || { item, check };
        if (before[index] === "open" && check.status !== "open") {
          const kept = check.status === "missed" && draftHasContent(drafts.get(draftKey(item.bottleId, check.window)));
          closed = closed || { item, check, kept };
        }
      });
    }
    // A strip that was ended or has expired takes its statuses and notes with it.
    for (const bottleId of [...tickStatuses.keys()]) if (!seen.has(bottleId)) tickStatuses.delete(bottleId);
    for (const [key, note] of [...drafts]) if (!seen.has(note.bottleId)) drafts.delete(key);
    if (!items.some((item) => !phoneStripFinished(phoneStripChecks(item, now)))) stopTicker();
    if (opened) {
      try { view.navigator?.vibrate?.([300, 150, 300]); } catch { /* not allowed here */ }
    }
    if (sheet.hidden) {
      drawPanel();
      return;
    }
    const here = screen === "strip" ? items.find((item) => item.bottleId === currentBottle) : null;
    let want = drawnStatuses;
    if (screen === "strip") want = here ? statusesOf(here, now) : "";
    else if (screen === "home") want = homeStatuses(items);
    if (want !== drawnStatuses) {
      render();
    } else if (here) {
      const coming = phoneStripNext(phoneStripChecks(here, now));
      if (coming && coming.status === "waiting") setText(next, say("nextIn", { name: say(coming.name), clock: phoneStripClock(coming.dueAt - now) }));
    } else if (screen === "home") {
      for (const button of stripList.querySelectorAll("[data-bottle]")) {
        const item = items.find((entry) => entry.bottleId === button.dataset.bottle);
        const line = button.lastElementChild;
        if (item && line) setText(line, nextText(item));
      }
    }
    if (opened) {
      const key = draftKey(opened.item.bottleId, opened.check.window);
      const onIt = screen === "strip" && currentBottle === opened.item.bottleId;
      const name = say(opened.check.name);
      if (onIt) setNotice(say("smellNow", { name }), "", key);
      else setNotice(say("smellNowOther", { label: labelOf(opened.item.bottleId, opened.item.label), name }), opened.item.bottleId, key);
    } else if (closed) {
      const onIt = screen === "strip" && currentBottle === closed.item.bottleId;
      if (closed.kept && onIt) setNotice(say("closedKept", { name: say(closed.check.name) }));
      else if (noticeFor === draftKey(closed.item.bottleId, closed.check.window)) setNotice("");
    }
  }

  function show(where = "home", bottleId = "") {
    screen = where;
    currentBottle = where === "strip" ? bottleId : currentBottle;
    pickedBottle = "";
    ending = false;
    setNotice("");
    render();
    // A strip dipped while the PC didn't answer asks for its recipe names again.
    const item = where === "strip" ? activeStrips()[bottleId] : null;
    if (item && (item.hasRecipe === null || item.hasRecipe === undefined)) loadRows(bottleId);
  }

  // Another full-screen view (phone bench's weigh sheet) has the page.
  function pageTaken() {
    return [...doc.querySelectorAll("[aria-modal='true']")].some((element) => element !== sheet && !element.hidden);
  }

  function open() {
    if (pageTaken()) return;
    // The language may have been changed in phone bench mode meanwhile.
    try { lang = store.getItem(PHONE_STRIPS_LANG) === "th" ? "th" : "en"; } catch { /* keep the one in use */ }
    opener = doc.activeElement;
    sheet.hidden = false;
    doc.body.classList.add("phone-bench-open");
    setPageInert(true);
    show("home");
    heading.focus?.();
    ensureTicker();
    loadNose();
    resume();
    loadMissingRows();
  }

  // The notes being written stay, and so does the ticker while a check is to come.
  function close() {
    sheet.hidden = true;
    doc.body.classList.remove("phone-bench-open");
    setPageInert(false);
    setNotice("");
    drawPanel();
    opener?.focus?.();
  }

  function dropDraftsOf(bottleId) {
    for (const [key, note] of [...drafts]) if (note.bottleId === bottleId) drafts.delete(key);
  }

  function saveNote() {
    const item = activeStrips()[currentBottle];
    const now = clock();
    const checks = item ? phoneStripChecks(item, now) : [];
    const coming = phoneStripNext(checks);
    const openCheck = coming && coming.status === "open" ? coming : null;
    const late = item && !openCheck
      ? phoneStripLateCheck(checks, (window) => draftHasContent(drafts.get(draftKey(item.bottleId, window))), now)
      : null;
    const check = openCheck || late;
    if (!item || !check || !draft || draft.window !== check.window) {
      render();
      return;
    }
    const body = phoneStripsSmell.smellLogBody({ window: check.window, chips: draft.chips, leadsText: leadsInput.value, weakText: weakInput.value, liking: draft.liking, words: wordsInput.value });
    if (!body.leads.length && !body.weak.length && body.liking === null && !body.words) {
      formStatus.textContent = say("needSomething");
      return;
    }
    // What the PC would refuse is caught here, while the note is still on screen.
    const problem = phoneStripsProblem(lang, body);
    if (problem) {
      formStatus.textContent = problem;
      return;
    }
    // A note saved after its check closed is filed at the time it was started,
    // and never later than the check's last second.
    const smelledAt = late ? Math.min(draft.startedAt || check.closesAt, check.closesAt - 1000) : now;
    const clientId = newId(check.window);
    const note = { clientId, bottleId: item.bottleId, label: labelOf(item.bottleId, item.label), window: check.window, leads: body.leads, weak: body.weak, liking: body.liking, words: body.words, loggedAt: new Date(smelledAt).toISOString() };
    // The note is kept before the check is marked, so a closed page loses neither.
    if (!changeOutbox((notes) => { notes[clientId] = note; })) {
      formStatus.textContent = say("notKept");
      return;
    }
    changeStrips((strips) => {
      if (strips[item.bottleId]) strips[item.bottleId].logged = { ...(strips[item.bottleId].logged || {}), [check.window]: clientId };
    });
    drafts.delete(draft.key);
    draft = null;
    shownKey = null;
    setNotice(say("noted"));
    render();
    send(clientId);
  }

  // ---- events ----
  openButton.addEventListener("click", open);
  closeButton.addEventListener("click", close);
  // Escape closes the view wherever the focus is, as long as the view is open.
  doc.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !sheet.hidden) close();
  });
  langButton.addEventListener("click", () => {
    lang = lang === "th" ? "en" : "th";
    try { store.setItem(PHONE_STRIPS_LANG, lang); } catch { /* storage unavailable */ }
    noticeGo.textContent = say("goThere");
    render();
    drawPanel();
  });
  noticeGo.addEventListener("click", () => {
    if (!noticeTarget) return;
    show("strip", noticeTarget);
    heading.focus?.();
  });
  dipButton.addEventListener("click", () => { show("pick"); heading.focus?.(); });
  stripList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-bottle]");
    if (!button) return;
    show("strip", button.dataset.bottle);
    heading.focus?.();
  });
  bottleList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-bottle]");
    if (!button) return;
    const live = activeStrips()[button.dataset.bottle];
    // A strip still on its way opens instead of being replaced.
    if (live && !phoneStripFinished(phoneStripChecks(live, clock()))) {
      show("strip", button.dataset.bottle);
      heading.focus?.();
      return;
    }
    pickedBottle = button.dataset.bottle;
    render();
    dippedButton.focus?.();
  });
  dippedButton.addEventListener("click", () => {
    const bottleId = pickedBottle;
    if (!bottleId) return;
    // A new strip of the same bottle starts with no notes.
    dropDraftsOf(bottleId);
    tickStatuses.delete(bottleId);
    changeStrips((strips) => {
      strips[bottleId] = { bottleId, label: labelOf(bottleId), dippedAt: new Date(clock()).toISOString(), logged: {}, rows: [], hasRecipe: null };
    });
    show("strip", bottleId);
    heading.focus?.();
    ensureTicker();
  });
  pickBack.addEventListener("click", () => {
    if (pickedBottle) { pickedBottle = ""; render(); return; }
    show("home");
    heading.focus?.();
  });
  allStrips.addEventListener("click", () => { show("home"); heading.focus?.(); });
  endStrip.addEventListener("click", () => {
    const item = activeStrips()[currentBottle];
    // A strip with a check still to come needs a second tap.
    if (item && !phoneStripFinished(phoneStripChecks(item, clock())) && !ending) {
      ending = true;
      render();
      endStrip.focus();
      return;
    }
    dropDraftsOf(currentBottle);
    changeStrips((strips) => { delete strips[currentBottle]; });
    show("home");
    heading.focus?.();
  });
  form.addEventListener("click", (event) => {
    const button = event.target.closest("button[type=button]");
    if (!button || !draft) return;
    if (button.dataset.row !== undefined) draft.chips.set(button.dataset.row, phoneStripsSmell.nextSmellChipState(draft.chips.get(button.dataset.row)));
    else if (button.dataset.liking !== undefined) draft.liking = button.dataset.liking === draft.liking ? "" : button.dataset.liking;
    else if (button === dropDraft) {
      drafts.delete(draft.key);
      draft = null;
      shownKey = null;
      setNotice("");
      render();
      return;
    } else return;
    touched();
    formStatus.textContent = "";
    render();
  });
  // What is typed is kept with the note, so it survives a look at another strip.
  for (const [input, field] of [[leadsInput, "leads"], [weakInput, "weak"], [wordsInput, "words"]]) {
    input.addEventListener("input", () => {
      if (!draft) return;
      draft[field] = input.value;
      touched();
    });
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    saveNote();
  });
  tryAgain.addEventListener("click", () => {
    const refused = refusedNote();
    if (!refused) return;
    changeOutbox((notes) => {
      if (notes[refused.clientId]) Object.assign(notes[refused.clientId], { refused: false, error: "" });
    });
    drawSync();
    send(refused.clientId);
  });
  removeNote.addEventListener("click", () => {
    const refused = refusedNote();
    if (!refused) return;
    changeOutbox((notes) => { delete notes[refused.clientId]; });
    // The check it was saved for is no longer noted: it can be noted again while open.
    changeStrips((strips) => {
      const live = strips[refused.bottleId];
      if (live?.logged?.[refused.window] === refused.clientId) delete live.logged[refused.window];
    });
    ensureTicker();
    if (!sheet.hidden) render();
    drawPanel();
    if (!syncActions.hidden) return;
    heading.focus?.();
  });
  view.addEventListener("online", online);
  // Another tab kept a strip or a note: show it here too.
  view.addEventListener("storage", (event) => {
    if (event.key !== PHONE_STRIPS_ACTIVE && event.key !== PHONE_STRIPS_OUTBOX) return;
    ensureTicker();
    if (!sheet.hidden) render();
    drawPanel();
  });
  // A phone that locks may close the page: send what is kept now. Back on
  // screen, the countdowns catch up at once.
  doc.addEventListener("visibilitychange", () => {
    if (doc.visibilityState === "hidden") resume();
    else tick();
  });

  function setBottles(list) {
    bottles = Array.isArray(list) ? list : [];
    drawPanel();
    if (!sheet.hidden) render();
  }

  drawPanel();
  resume();
  ensureTicker();
  phoneStrips = { open, close, setBottles, resume, send };
  return phoneStrips;
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    PHONE_STRIPS_ACTIVE, PHONE_STRIPS_OUTBOX, PHONE_STRIPS_LANG, PHONE_STRIPS_WORDS, PHONE_STRIP_CHECKS, PHONE_STRIPS_KEEP_MS,
    phoneStripsSay, phoneStripChecks, phoneStripNext, phoneStripFinished, phoneStripExpired, phoneStripClock,
    phoneStripNoteBody, phoneStripsToSend, phoneStripsRead, phoneStripsNoseText, attachPhoneStrips,
    phoneStripLateCheck, phoneStripsProblem, phoneStripsNoteText, PHONE_STRIPS_MAX_NAMES,
  };
}
