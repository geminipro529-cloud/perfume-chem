// Smell log on the Bottles page: Kenny smells a strip or his skin at a set time
// after applying a bottle and notes what leads, what is weak, how much he likes
// it and a few words. Each save is one application plus one observation.
//
// lab/bottles.js calls attachSmellLog once and passes it the bottle list after each
// refresh. Names and anything typed go in through textContent / .value only,
// never HTML strings. Node loads the same file in the tests through module.exports.

const SMELL_LOG_STATES = ["", "leads", "weak"];

// One tap: leads. Two: weak. Three: cleared.
function nextSmellChipState(current) {
  return SMELL_LOG_STATES[(SMELL_LOG_STATES.indexOf(current || "") + 1) % SMELL_LOG_STATES.length];
}

function splitSmellNames(text) {
  return String(text || "").split(",").map((name) => name.trim()).filter(Boolean);
}

function smellLogBody({ window, chips, leadsText, weakText, liking, words }) {
  const leads = [];
  const weak = [];
  for (const [name, mark] of chips || []) {
    if (mark === "leads") leads.push(name);
    if (mark === "weak") weak.push(name);
  }
  leads.push(...splitSmellNames(leadsText));
  weak.push(...splitSmellNames(weakText));
  return { window, leads, weak, liking: liking ? Number(liking) : null, words: String(words || "").trim() };
}

function smellLogLine(entry, windows) {
  const label = (windows.find((item) => item.key === entry.window) || {}).label || entry.window;
  const when = new Date(entry.logged_at);
  const parts = [label, Number.isNaN(when.getTime()) ? "" : when.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })];
  if (entry.liking) parts.push(`liked ${entry.liking}/10`);
  if (entry.leads.length) parts.push(`leads: ${entry.leads.join(", ")}`);
  if (entry.weak.length) parts.push(`weak: ${entry.weak.join(", ")}`);
  if (entry.words) parts.push(`“${entry.words}”`);
  return parts.filter(Boolean).join(" · ");
}

// One comparison block's lines. Names and their order only: the model's share
// is a detection screen, never how strong anything smells.
function smellCompareLines(block) {
  const title = [block.label, `${block.n_entries} ${block.n_entries === 1 ? "entry" : "entries"}`];
  if (block.liking_mean !== null && block.liking_mean !== undefined) title.push(`liked ${block.liking_mean}/10`);
  const named = (items) => items.map((item) => (item.count > 1 ? `${item.name} ×${item.count}` : item.name)).join(", ");
  const you = [];
  if (block.you_leads.length) you.push(`leads ${named(block.you_leads)}`);
  if (block.you_weak.length) you.push(`weak ${named(block.you_weak)}`);
  const lines = { title: title.join(" · "), model: "", you: `You: ${you.join(" · ") || "no names marked"}`, corrected: "", agreement: "" };
  if (!block.model_in_range) {
    lines.model = block.model_note || "Beyond the model's range.";
    return lines;
  }
  lines.model = `Model, ${block.model_time_label}: ${block.model_top.join(", ") || "nothing it can detect"}`;
  // Present only once the nose calibration passed its held-out check.
  if (block.corrected_top?.length) lines.corrected = `Corrected: ${block.corrected_top.join(", ")}`;
  const agreement = block.agreement;
  const said = [];
  if (agreement.leads_the_model_also_had_on_top.length) said.push(`Model and you agree on ${agreement.leads_the_model_also_had_on_top.join(", ")}.`);
  for (const name of agreement.leads_the_model_did_not_have_on_top) said.push(`You smelled ${name} leading; the model didn't have it on top.`);
  for (const name of agreement.you_marked_weak_but_model_had_on_top) said.push(`You marked ${name} weak; the model had it on top.`);
  if (!said.length) said.push("No leads marked here, so nothing to compare yet.");
  lines.agreement = said.join(" ");
  return lines;
}

function smellOrdinal(n) {
  const suffix = ["th", "st", "nd", "rd"];
  const tail = n % 100;
  return `${n}${suffix[(tail - 20) % 10] || suffix[tail] || suffix[0]}`;
}

// One chart cell: the model's place for a name at one strip time beside what
// was marked there. A place is the model's detection order, never how strong a
// material smells (AGENTS.md Rule 1).
function smellChartCell(block, name, marked) {
  const rank = block.model_ranks?.[name] ?? null;
  const key = name.toLowerCase();
  const corrected = (block.corrected_top || []).findIndex((item) => item.toLowerCase() === key);
  const parts = [rank === null ? "not ranked" : smellOrdinal(rank)];
  if (corrected >= 0 && corrected + 1 !== rank) parts.push(`corrected ${smellOrdinal(corrected + 1)}`);
  if (marked) parts.push(`you: ${marked.mark}${marked.count > 1 ? ` ×${marked.count}` : ""}`);
  const top = rank !== null && rank <= 3;
  let state = "";
  if (marked?.mark === "leads") state = top ? "agree" : "missed";
  else if (marked?.mark === "weak" && top) state = "clash";
  return { text: parts.join(" · "), state };
}

// What the smell log has taught the model about one name, and from how many bottles.
function smellCorrectionText(item, calibrated) {
  if (!item || !item.n_bottles) return "not in the model";
  const bottles = `${item.n_bottles} ${item.n_bottles === 1 ? "bottle" : "bottles"}`;
  if (item.used) return `${item.label} from ${bottles}`;
  if (item.n_bottles < item.min_bottles) return `none yet: ${item.n_bottles} of ${item.min_bottles} bottles`;
  return calibrated ? `none: ${bottles}` : `not used yet: ${bottles}`;
}

// The "model said, you smelled" chart: a row per name, a column per strip time
// the model covers, and the correction with the bottles behind it. Null when no
// logged time is inside the model's range.
function smellChartModel(data) {
  const windows = (data?.windows || []).filter((block) => block.model_in_range && block.model_ranks);
  if (!windows.length) return null;
  const names = Object.keys(windows[0].model_ranks);
  const best = (name) => Math.min(...windows.map((block) => block.model_ranks[name] ?? Infinity));
  const ordered = names
    .map((name, index) => ({ name, index, best: best(name) }))
    .sort((a, b) => a.best - b.best || a.index - b.index)
    .map((item) => item.name);
  const marksOf = (block) => {
    const marks = new Map();
    for (const item of block.you_leads || []) marks.set(item.name.toLowerCase(), { mark: "leads", count: item.count });
    for (const item of block.you_weak || []) marks.set(item.name.toLowerCase(), { mark: "weak", count: item.count });
    return marks;
  };
  const marks = windows.map(marksOf);
  const corrections = new Map((data.corrections || []).map((item) => [item.name.toLowerCase(), item]));
  return {
    columns: windows.map((block) => ({ key: block.window, label: block.label })),
    rows: ordered.map((name) => ({
      name,
      cells: windows.map((block, column) => smellChartCell(block, name, marks[column].get(name.toLowerCase()))),
      correction: smellCorrectionText(corrections.get(name.toLowerCase()), Boolean(data.calibrated)),
    })),
  };
}

function smellChartTable(doc, chart) {
  const node = (tag, attributes, text) => smellLogNode(doc, tag, attributes, text);
  const table = node("table", { class: "smell-chart" });
  table.appendChild(node("caption", {}, "The model's place at each strip time, beside what you marked"));
  const head = node("tr");
  head.append(node("th", { scope: "col" }, "Material"), ...chart.columns.map((column) => node("th", { scope: "col" }, column.label)), node("th", { scope: "col" }, "Correction"));
  const thead = node("thead");
  thead.appendChild(head);
  const body = node("tbody");
  for (const row of chart.rows) {
    const line = node("tr");
    line.appendChild(node("th", { scope: "row" }, row.name));
    row.cells.forEach((cell, index) => {
      const td = node("td", { "data-window": chart.columns[index].key }, cell.text);
      if (cell.state) td.dataset.state = cell.state;
      line.appendChild(td);
    });
    line.appendChild(node("td", { class: "smell-chart-correction" }, row.correction));
    body.appendChild(line);
  }
  table.append(thead, body);
  return table;
}

// The one line saying whether the model has learned from the smell log yet.
function smellCalibrationLine(calibration) {
  if (!calibration) return "";
  if (calibration.calibrated) {
    return `Model corrected by your nose (${calibration.n_bottles} bottles, beats the plain model on held-out bottles)`;
  }
  if (calibration.n_bottles < calibration.min_bottles) {
    return `Learning from your nose: ${calibration.n_bottles} of ${calibration.min_bottles} bottles logged`;
  }
  return calibration.reason || "";
}

function smellLogNode(doc, tag, attributes = {}, text = "") {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

function attachSmellLog({ doc, request, root }) {
  const node = (tag, attributes, text) => smellLogNode(doc, tag, attributes, text);
  const bottleSelect = node("select", { name: "smell_log_bottle", id: "smell-log-bottle" });
  const bottleLabel = node("label", { for: "smell-log-bottle" }, "Bottle");
  const form = node("form", { class: "form-panel smell-log-form" });
  form.hidden = true;
  const windowSet = node("fieldset", { class: "smell-log-group" });
  windowSet.appendChild(node("legend", {}, "When"));
  const windowButtons = node("div", { class: "smell-log-choices smell-log-windows" });
  windowSet.appendChild(windowButtons);
  const rowSet = node("fieldset", { class: "smell-log-group" });
  rowSet.appendChild(node("legend", {}, "What do you smell"));
  const rowHelp = node("p", { class: "field-help" }, "Tap a name once if it leads, twice if it is weak, a third time to clear.");
  const chipList = node("div", { class: "smell-log-choices" });
  const leadsInput = node("input", { name: "leads_text", type: "text", autocomplete: "off", placeholder: "Iris, Hedione" });
  const weakInput = node("input", { name: "weak_text", type: "text", autocomplete: "off", placeholder: "Ambrox" });
  const leadsLabel = node("label", {}, "Leads (names, comma-separated)");
  leadsLabel.appendChild(leadsInput);
  const weakLabel = node("label", {}, "Weak (names, comma-separated)");
  weakLabel.appendChild(weakInput);
  rowSet.append(rowHelp, chipList, leadsLabel, weakLabel);
  const likingSet = node("fieldset", { class: "smell-log-group" });
  likingSet.appendChild(node("legend", {}, "How much do you like it, 1 to 10"));
  const likingButtons = node("div", { class: "smell-log-choices smell-log-liking" });
  likingSet.appendChild(likingButtons);
  const wordsInput = node("input", { name: "words", type: "text", maxlength: "280", autocomplete: "off", placeholder: "Powdery, a bit sharp" });
  const wordsLabel = node("label", {}, "In a few words");
  wordsLabel.appendChild(wordsInput);
  const save = node("button", { type: "submit" }, "Save");
  const status = node("p", { class: "status-line", role: "status", "aria-live": "polite" });
  form.append(windowSet, rowSet, likingSet, wordsLabel, save, status);
  const calibrationLine = node("p", { class: "field-help smell-log-calibration", role: "status" });
  calibrationLine.hidden = true;
  form.prepend(calibrationLine);
  const pastTitle = node("h3", {}, "Earlier entries");
  const past = node("ul", { class: "smell-log-past" });
  pastTitle.hidden = true;
  const compare = node("section", { class: "smell-log-compare", "aria-labelledby": "smell-log-compare-title" });
  compare.hidden = true;
  const compareTitle = node("h3", { id: "smell-log-compare-title" }, "Model said / you smelled");
  const compareBasis = node("p", { class: "field-help" }, "Model's leaders (detection screen): what the model can most easily detect at that time, in order. Not how strong it smells.");
  const compareBody = node("div", { class: "smell-log-compare-blocks" });
  compare.append(compareTitle, compareBasis, compareBody);
  root.append(bottleLabel, bottleSelect, form, pastTitle, past, compare);

  let windows = [];
  let entries = [];
  let chosenWindow = "";
  let liking = "";
  const chips = new Map();
  let loadToken = 0;

  function pressed(button, on) { button.setAttribute("aria-pressed", String(on)); }

  function chipText(name) {
    const mark = chips.get(name);
    return mark ? `${name}: ${mark}` : name;
  }

  function drawChoices() {
    windowButtons.replaceChildren(...windows.map((item) => {
      const button = node("button", { type: "button", class: "smell-log-choice", "data-window": item.key }, item.label);
      pressed(button, item.key === chosenWindow);
      return button;
    }));
    chipList.replaceChildren(...[...chips.keys()].map((name) => {
      const button = node("button", { type: "button", class: "smell-log-choice smell-log-chip", "data-row": name }, chipText(name));
      if (chips.get(name)) button.dataset.mark = chips.get(name);
      pressed(button, Boolean(chips.get(name)));
      return button;
    }));
    const typed = chips.size === 0;
    rowHelp.hidden = typed;
    leadsLabel.hidden = !typed;
    weakLabel.hidden = !typed;
    likingButtons.replaceChildren(...Array.from({ length: 10 }, (_unused, index) => {
      const value = String(index + 1);
      const button = node("button", { type: "button", class: "smell-log-choice", "data-liking": value }, value);
      pressed(button, value === liking);
      return button;
    }));
  }

  function drawPast() {
    pastTitle.hidden = !entries.length;
    past.replaceChildren(...entries.map((entry) => node("li", {}, smellLogLine(entry, windows))));
  }

  function drawComparison(data) {
    compare.hidden = !data || !entries.length;
    if (compare.hidden) { compareBody.replaceChildren(); return; }
    const blocks = [];
    if (!data.available) blocks.push(node("p", { class: "smell-log-compare-note" }, data.reason || "No comparison for this bottle."));
    const chart = smellChartModel(data);
    if (chart) {
      blocks.push(smellChartTable(doc, chart));
      blocks.push(node("p", { class: "field-help smell-chart-key" }, "1st is what the model can most easily detect at that time, not what smells strongest. Green: you and the model agree on a lead. Amber: you smelled it leading, the model didn't have it in its top 3. Red: you marked it weak, the model had it in its top 3. Correction: what your smell log has taught the model, and from how many bottles."));
    }
    for (const block of data.windows || []) {
      const lines = smellCompareLines(block);
      const item = node("div", { class: "smell-log-compare-block", "data-compare-window": block.window });
      item.append(node("h4", {}, lines.title), node("p", {}, lines.model), node("p", {}, lines.you));
      if (lines.corrected) item.appendChild(node("p", { class: "smell-log-compare-corrected" }, lines.corrected));
      if (lines.agreement) item.appendChild(node("p", { class: "smell-log-compare-agreement" }, lines.agreement));
      blocks.push(item);
    }
    if ((data.not_modelled || []).length) {
      blocks.push(node("p", { class: "smell-log-compare-note" }, `Not in the model: ${data.not_modelled.map((row) => `${row.name} (${row.reason})`).join("; ")}.`));
    }
    compareBody.replaceChildren(...blocks);
  }

  async function loadComparison(bottleId, token) {
    try {
      const data = await request(`/bottles/${encodeURIComponent(bottleId)}/smell-log/comparison`);
      if (token === loadToken) drawComparison(data);
    } catch (error) {
      if (token === loadToken) drawComparison({ available: false, reason: error.message || "Couldn't load the model comparison.", windows: [] });
    }
  }

  async function loadCalibration(token) {
    try {
      const data = await request("/smell-log/calibration");
      if (token !== loadToken) return;
      calibrationLine.textContent = smellCalibrationLine(data);
    } catch (_error) {
      if (token !== loadToken) return;
      calibrationLine.textContent = "";
    }
    calibrationLine.hidden = !calibrationLine.textContent;
  }

  function clearForm() {
    chosenWindow = "";
    liking = "";
    for (const name of chips.keys()) chips.set(name, "");
    leadsInput.value = "";
    weakInput.value = "";
    wordsInput.value = "";
    drawChoices();
  }

  async function load(bottleId) {
    const token = ++loadToken;
    form.hidden = true;
    entries = [];
    drawPast();
    drawComparison(null);
    if (!bottleId) { status.textContent = ""; return; }
    try {
      const data = await request(`/bottles/${encodeURIComponent(bottleId)}/smell-log`);
      if (token !== loadToken) return;
      windows = data.windows || [];
      entries = data.entries || [];
      chips.clear();
      for (const name of data.rows || []) chips.set(name, "");
      clearForm();
      status.textContent = "";
      form.hidden = false;
      drawPast();
      await loadCalibration(token);
      if (entries.length) await loadComparison(bottleId, token);
    } catch (error) {
      if (token !== loadToken) return;
      root.querySelector(".smell-log-load-error")?.remove();
      bottleSelect.after(node("p", { class: "field-help smell-log-load-error", role: "alert" }, error.message || "Couldn't load this bottle's smell log."));
    }
  }

  bottleSelect.addEventListener("change", () => {
    root.querySelector(".smell-log-load-error")?.remove();
    load(bottleSelect.value);
  });

  form.addEventListener("click", (event) => {
    const button = event.target.closest("button[type=button]");
    if (!button) return;
    const key = ["window", "row", "liking"].find((name) => button.dataset[name] !== undefined);
    const value = button.dataset[key];
    if (key === "window") chosenWindow = value === chosenWindow ? "" : value;
    else if (key === "row") chips.set(value, nextSmellChipState(chips.get(value)));
    else if (key === "liking") liking = value === liking ? "" : value;
    else return;
    drawChoices();
    // The buttons were redrawn; keep the keyboard on the one just tapped.
    [...form.querySelectorAll("button[type=button]")].find((item) => item.dataset[key] === value)?.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!chosenWindow) { status.textContent = "Pick when you smelled it: a strip time or a skin day."; return; }
    const body = smellLogBody({ window: chosenWindow, chips, leadsText: leadsInput.value, weakText: weakInput.value, liking, words: wordsInput.value });
    if (!body.leads.length && !body.weak.length && body.liking === null && !body.words) {
      status.textContent = "Mark at least one name, a liking or a few words.";
      return;
    }
    save.disabled = true;
    try {
      const saved = await request(`/bottles/${encodeURIComponent(bottleSelect.value)}/smell-log`, { method: "POST", body: JSON.stringify(body) });
      entries = [saved, ...entries];
      clearForm();
      drawPast();
      status.textContent = "Saved.";
      await loadCalibration(loadToken);
      await loadComparison(bottleSelect.value, loadToken);
    } catch (error) {
      status.textContent = error.message || "Not saved.";
    } finally {
      save.disabled = false;
    }
  });

  function setBottles(bottles) {
    const current = bottleSelect.value;
    const options = [node("option", { value: "" }, bottles.length ? "Choose a bottle" : "No bottles yet")];
    for (const bottle of bottles) options.push(node("option", { value: bottle.id }, bottle.label || bottle.id));
    bottleSelect.replaceChildren(...options);
    if (bottles.some((bottle) => bottle.id === current)) bottleSelect.value = current;
    else if (current) load("");
  }

  return { setBottles };
}

if (typeof module === "object" && module.exports) {
  module.exports = { nextSmellChipState, splitSmellNames, smellLogBody, smellLogLine, smellCompareLines, smellCalibrationLine, smellOrdinal, smellChartCell, smellCorrectionText, smellChartModel, attachSmellLog };
}
