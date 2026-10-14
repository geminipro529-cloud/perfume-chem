// Blind test on the Your nose page: two versions saved on Edit a formula become
// vials A and B. The server decides which is which and keeps it until Kenny
// reveals it; the page shows each vial's rows for mixing, never its name.
//
// lab/bottles.js attaches it and passes rowText (one saved row as words) and
// toBench (put a vial's rows on the bench sheet). Names and anything typed go in
// through textContent / .value only, never HTML strings. Node loads the same
// file in the tests through module.exports.

const BLIND_CHOICES = [["A", "A"], ["B", "B"], ["same", "No preference"]];
const BLIND_NAME_SCORES = ["", "1", "2", "3", "4", "5"];

function blindVersionOptions(formulas) {
  const options = [];
  for (const formula of formulas || []) {
    for (const version of [...(formula.versions || [])].reverse()) {
      options.push({
        value: `${formula.formula_id}:${version.version}`,
        text: `${formula.name} v${version.version} (${version.row_count} ${version.row_count === 1 ? "row" : "rows"})`,
      });
    }
  }
  return options;
}

function blindSide(value, label) {
  const [formulaId, version] = String(value || "").split(":");
  return { formula_id: formulaId || "", version: Number(version) || 0, label: String(label || "").trim() };
}

function blindPickLine(pick) {
  const parts = [`${pick.time}: ${pick.choice === "same" ? "no preference" : `you picked ${pick.choice}`}`];
  const named = [];
  if (pick.name_a) named.push(`A ${pick.name_a}/5`);
  if (pick.name_b) named.push(`B ${pick.name_b}/5`);
  if (named.length) parts.push(`smells like its name: ${named.join(", ")}`);
  if (pick.note) parts.push(`“${pick.note}”`);
  return parts.join(" · ");
}

// After the reveal: which vial was which, and who won each strip time.
function blindOutcomeLines(test) {
  if (!test.revealed || !test.key) return [];
  const side = (letter) => `${letter} was ${test.key[letter].label} (${test.key[letter].name} v${test.key[letter].version})`;
  const lines = [`${side("A")}; ${side("B")}.`];
  for (const item of test.outcome || []) {
    lines.push(`${item.time}: ${item.preferred ? `you preferred ${item.preferred}` : "no preference"}.`);
  }
  return lines;
}

function blindTallyLine(row) {
  const picks = `${row.picks} ${row.picks === 1 ? "pick" : "picks"}`;
  const name = row.name_mean === null || row.name_mean === undefined ? "" : ` · smells like its name ${row.name_mean}/5 on average`;
  return `${row.label}: preferred in ${row.preferred} of ${picks}${name}`;
}

function blindPickBody({ time, choice, nameA, nameB, note }) {
  return {
    time,
    choice,
    name_a: nameA ? Number(nameA) : null,
    name_b: nameB ? Number(nameB) : null,
    note: String(note || "").trim(),
  };
}

function blindNode(doc, tag, attributes = {}, text = "") {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

function attachBlindTest({ doc, request, root, rowText, toBench }) {
  const node = (tag, attributes, text) => blindNode(doc, tag, attributes, text);
  const tallyTitle = node("h3", {}, "So far");
  const tally = node("ul", { class: "blind-tally" });
  const form = node("form", { class: "form-panel blind-new", novalidate: "" });
  form.appendChild(node("h3", {}, "New blind test"));
  const titleInput = node("input", { name: "title", type: "text", maxlength: "200", autocomplete: "off", placeholder: "Baie Rose" });
  const titleLabel = node("label", {}, "Name of the test");
  titleLabel.appendChild(titleInput);
  const briefInput = node("input", { name: "brief", type: "text", maxlength: "1000", autocomplete: "off", placeholder: "A pink pepper perfume for a man" });
  const briefLabel = node("label", {}, "Brief (optional)");
  briefLabel.appendChild(briefInput);
  const sides = [1, 2].map((number) => {
    const set = node("fieldset", { class: "smell-log-group blind-side" });
    set.appendChild(node("legend", {}, `Formula ${number}`));
    const select = node("select", { name: `version_${number}` });
    const selectLabel = node("label", {}, "Saved version");
    selectLabel.appendChild(select);
    const label = node("input", { name: `label_${number}`, type: "text", maxlength: "80", autocomplete: "off", placeholder: number === 1 ? "Composer" : "Opus card" });
    const labelLabel = node("label", {}, "What it is (hidden until you reveal)");
    labelLabel.appendChild(label);
    set.append(selectLabel, labelLabel);
    return { set, select, label };
  });
  const noVersions = node("p", { class: "field-help" }, "Save two versions on Edit a formula first; a blind test is made from saved versions.");
  noVersions.hidden = true;
  const make = node("button", { type: "submit" }, "Make vials A and B");
  const status = node("p", { class: "status-line", role: "status", "aria-live": "polite" });
  form.append(titleLabel, briefLabel, ...sides.map((side) => side.set), noVersions, make, status);
  const list = node("div", { class: "blind-tests" });
  root.append(tallyTitle, tally, form, list);

  let tests = [];
  const drafts = new Map();

  function draftOf(testId) {
    if (!drafts.has(testId)) drafts.set(testId, { time: "", choice: "", nameA: "", nameB: "", note: "" });
    return drafts.get(testId);
  }

  function drawTally(rows) {
    tally.replaceChildren(...(rows || []).map((row) => node("li", {}, blindTallyLine(row))));
    tallyTitle.hidden = !rows?.length;
    tally.hidden = !rows?.length;
  }

  function drawVersions(formulas) {
    const options = blindVersionOptions(formulas);
    for (const side of sides) {
      const current = side.select.value;
      side.select.replaceChildren(node("option", { value: "" }, options.length ? "Choose a version" : "No saved versions"), ...options.map((option) => node("option", { value: option.value }, option.text)));
      if (options.some((option) => option.value === current)) side.select.value = current;
    }
    noVersions.hidden = options.length >= 2;
  }

  function pressed(button, on) { button.setAttribute("aria-pressed", String(on)); }

  function choiceButtons(test, draft, key, values) {
    const group = node("div", { class: "smell-log-choices blind-choices" });
    for (const [value, text] of values) {
      const button = node("button", { type: "button", class: "smell-log-choice", [`data-${key}`]: value }, text);
      pressed(button, draft[key] === value);
      group.appendChild(button);
    }
    return group;
  }

  function scoreSelect(name, value, letter) {
    const select = node("select", { name });
    select.replaceChildren(...BLIND_NAME_SCORES.map((score) => node("option", { value: score }, score || "–")));
    select.value = value;
    const label = node("label", {}, `How much ${letter} smells like its name, 1 to 5`);
    label.appendChild(select);
    return label;
  }

  function vialBlock(test, vial) {
    const block = node("div", { class: "blind-vial" });
    block.appendChild(node("h4", {}, `Vial ${vial.letter}`));
    const details = node("details", { class: "blind-vial-rows" });
    details.appendChild(node("summary", {}, `${vial.rows.length} ${vial.rows.length === 1 ? "row" : "rows"}`));
    const rows = node("ul");
    for (const row of vial.rows) rows.appendChild(node("li", {}, rowText(row)));
    details.appendChild(rows);
    const bench = node("button", { type: "button", class: "quiet-button", "data-bench": vial.letter }, `Vial ${vial.letter} on the bench sheet`);
    block.append(details, bench);
    return block;
  }

  function testCard(test) {
    const card = node("article", { class: "blind-test", "data-test": test.test_id });
    card.appendChild(node("h3", {}, test.title));
    if (test.brief) card.appendChild(node("p", { class: "field-help" }, test.brief));
    const vials = node("div", { class: "blind-vials" });
    vials.append(...test.vials.map((vial) => vialBlock(test, vial)));
    card.appendChild(vials);
    const past = node("ul", { class: "blind-picks" });
    past.append(...test.picks.map((pick) => node("li", {}, blindPickLine(pick))));
    if (test.picks.length) card.append(node("h4", {}, "Your picks"), past);
    if (test.revealed) {
      const outcome = node("div", { class: "blind-outcome", role: "status" });
      outcome.tabIndex = -1;
      outcome.append(...blindOutcomeLines(test).map((line) => node("p", {}, line)));
      card.appendChild(outcome);
      return card;
    }
    const draft = draftOf(test.test_id);
    const pick = node("form", { class: "form-panel blind-pick", novalidate: "" });
    const timeSet = node("fieldset", { class: "smell-log-group" });
    timeSet.append(node("legend", {}, "Strip time"), choiceButtons(test, draft, "time", test.times.map((time) => [time, time])));
    const choiceSet = node("fieldset", { class: "smell-log-group" });
    choiceSet.append(node("legend", {}, "Which would you rather wear?"), choiceButtons(test, draft, "choice", BLIND_CHOICES));
    const note = node("input", { name: "note", type: "text", maxlength: "280", autocomplete: "off", placeholder: "B is sharper" });
    note.value = draft.note;
    const noteLabel = node("label", {}, "In a few words (optional)");
    noteLabel.appendChild(note);
    const scores = node("div", { class: "field-pair" });
    scores.append(scoreSelect("name_a", draft.nameA, "A"), scoreSelect("name_b", draft.nameB, "B"));
    const save = node("button", { type: "submit" }, "Save pick");
    const pickStatus = node("p", { class: "status-line", role: "status", "aria-live": "polite" });
    pick.append(timeSet, choiceSet, scores, noteLabel, save, pickStatus);
    const reveal = node("button", { type: "button", class: "quiet-button blind-reveal", "data-reveal": test.test_id }, "Show which vial is which");
    reveal.disabled = !test.picks.length;
    const revealHelp = node("p", { class: "field-help" }, test.picks.length ? "Your picks are fixed once you look." : "Pick at least one strip time first.");
    card.append(pick, reveal, revealHelp);
    return card;
  }

  function drawTests() {
    list.replaceChildren(...tests.map(testCard));
  }

  function replaceTest(test) {
    tests = tests.map((item) => (item.test_id === test.test_id ? test : item));
    drawTests();
  }

  async function refreshTally() {
    try {
      drawTally((await request("/v2/workbench/blind-tests")).tally);
    } catch (_error) {
      // The test itself is saved; the summary catches up on the next load.
    }
  }

  async function load() {
    try {
      const [data, saved] = await Promise.all([request("/v2/workbench/blind-tests"), request("/v2/workbench/formula-versions")]);
      tests = data.tests || [];
      drawTally(data.tally);
      drawVersions(saved.formulas || []);
      drawTests();
    } catch (error) {
      status.textContent = error.message || "Couldn't load the blind tests.";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const [first, second] = sides.map((side) => blindSide(side.select.value, side.label.value));
    if (!titleInput.value.trim()) { status.textContent = "Give the test a name."; titleInput.focus(); return; }
    if (!first.formula_id || !second.formula_id) { status.textContent = "Choose a saved version for both formulas."; return; }
    make.disabled = true;
    try {
      const test = await request("/v2/workbench/blind-tests", { method: "POST", body: JSON.stringify({ title: titleInput.value, brief: briefInput.value, first, second }) });
      tests = [test, ...tests];
      drawTests();
      titleInput.value = "";
      briefInput.value = "";
      for (const side of sides) { side.select.value = ""; side.label.value = ""; }
      status.textContent = "Made. Mix vial A and vial B from their sheets below.";
    } catch (error) {
      status.textContent = error.message || "Not made.";
    } finally {
      make.disabled = false;
    }
  });

  list.addEventListener("click", async (event) => {
    const button = event.target.closest("button[type=button]");
    const card = button?.closest("[data-test]");
    if (!button || !card) return;
    const test = tests.find((item) => item.test_id === card.dataset.test);
    if (!test) return;
    if (button.dataset.bench) {
      const vial = test.vials.find((item) => item.letter === button.dataset.bench);
      if (vial && typeof toBench === "function") toBench(`Vial ${vial.letter}`, vial.rows);
      return;
    }
    if (button.dataset.reveal) {
      button.disabled = true;
      try {
        replaceTest(await request(`/v2/workbench/blind-tests/${encodeURIComponent(test.test_id)}/reveal`, { method: "POST", body: "{}" }));
        list.querySelector(`[data-test="${test.test_id}"] .blind-outcome`)?.focus();
        refreshTally();
      } catch (error) {
        button.disabled = false;
        card.querySelector(".blind-pick .status-line").textContent = error.message || "Not revealed.";
      }
      return;
    }
    const key = ["time", "choice"].find((name) => button.dataset[name] !== undefined);
    if (!key) return;
    const draft = draftOf(test.test_id);
    const value = button.dataset[key];
    draft[key] = draft[key] === value ? "" : value;
    for (const item of card.querySelectorAll(`[data-${key}]`)) pressed(item, item.dataset[key] === draft[key]);
  });

  list.addEventListener("input", (event) => {
    const card = event.target.closest("[data-test]");
    if (!card) return;
    const draft = draftOf(card.dataset.test);
    if (event.target.name === "note") draft.note = event.target.value;
    if (event.target.name === "name_a") draft.nameA = event.target.value;
    if (event.target.name === "name_b") draft.nameB = event.target.value;
  });

  list.addEventListener("submit", async (event) => {
    event.preventDefault();
    const card = event.target.closest("[data-test]");
    if (!card) return;
    const draft = draftOf(card.dataset.test);
    const line = card.querySelector(".blind-pick .status-line");
    if (!draft.time) { line.textContent = "Pick the strip time you are smelling."; return; }
    if (!draft.choice) { line.textContent = "Pick A, B or no preference."; return; }
    const save = event.target.querySelector("button[type=submit]");
    save.disabled = true;
    try {
      const test = await request(`/v2/workbench/blind-tests/${encodeURIComponent(card.dataset.test)}/picks`, { method: "POST", body: JSON.stringify(blindPickBody(draft)) });
      drafts.delete(card.dataset.test);
      replaceTest(test);
      list.querySelector(`[data-test="${test.test_id}"] .blind-pick .status-line`).textContent = `Saved: ${blindPickLine(test.picks.find((pick) => pick.time === draft.time))}.`;
    } catch (error) {
      save.disabled = false;
      line.textContent = error.message || "Not saved.";
    }
  });

  // Called when the Your nose page is opened, so it shows the latest logs and saves.
  return { show: load };
}

if (typeof module === "object" && module.exports) {
  module.exports = { blindVersionOptions, blindSide, blindPickLine, blindOutcomeLines, blindTallyLine, blindPickBody, attachBlindTest };
}
