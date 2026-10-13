// Smell log on the Bottles page: Kenny smells a strip or his skin at a set time
// after applying a bottle and notes what leads, what is weak, how much he likes
// it and a few words. Each save is one application plus one observation.
//
// lab.js calls attachSmellLog once and passes it the bottle list after each
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
  const pastTitle = node("h3", {}, "Earlier entries");
  const past = node("ul", { class: "smell-log-past" });
  pastTitle.hidden = true;
  root.append(bottleLabel, bottleSelect, form, pastTitle, past);

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
  module.exports = { nextSmellChipState, splitSmellNames, smellLogBody, smellLogLine, attachSmellLog };
}
