// Brief chips on Create a formula: the materials and notes the composer reads
// in the name and brief (POST /v2/workbench/brief-notes), shown before
// composing. A chip can be made the star (a sentence is added to the brief) or
// left out (its word goes in Must avoid), and a note can be added (a sentence is
// added to the brief), so what is sent is always the text on the page.
//
// lab/create.js attaches it. Names and anything typed go in through
// textContent / .value only, never HTML strings. Node loads the same file in
// the tests through module.exports.

const BRIEF_NOTES_DELAY_MS = 700;
const BRIEF_LAYERS = { top: "top note", heart: "heart note", base: "base note" };

// The brief with one more sentence after it.
function briefSentenceAfter(message, sentence) {
  const text = String(message || "").trimEnd();
  if (!text) return sentence;
  return `${text}${/[.!?]$/.test(text) ? "" : "."} ${sentence}`;
}

function briefStarText(message, phrase) {
  return briefSentenceAfter(message, `The star is ${phrase}.`);
}

function briefWithText(message, word) {
  return briefSentenceAfter(message, `With ${String(word || "").trim()}.`);
}

// Must avoid as typed, with one more word unless it is there already.
function briefAvoidText(current, word) {
  const list = String(current || "").split(",").map((item) => item.trim()).filter(Boolean);
  if (list.some((item) => item.toLowerCase() === String(word).toLowerCase())) return list.join(", ");
  return [...list, word].join(", ");
}

function briefFamilyText(family) {
  const text = String(family || "").toLowerCase();
  return text ? `${text[0].toUpperCase()}${text.slice(1)}` : "";
}

// The small line under a chip's name.
function briefChipMeta(chip) {
  const layer = BRIEF_LAYERS[chip.layer] || chip.layer || "";
  const parts = [chip.kind === "material" ? `material you named, ${layer}` : layer];
  const words = (chip.words || []).filter((word) => word !== chip.label);
  if (chip.kind === "note" && words.length) parts.push(`from “${words.join("”, “")}”`);
  if (chip.from_name) parts.push("from the name");
  if (chip.tied_to) parts.push(`comes with ${chip.tied_to}`);
  return parts.filter(Boolean).join(" · ");
}

// The line above the chips.
function briefStatusLine(result) {
  if (result.needs_confirmation) return result.problems.join(" ");
  if (!result.notes.length) return "No note or material it knows is in this brief yet. Add one below.";
  const star = result.notes.find((chip) => chip.star);
  const lead = star ? `${star.label} is the star.` : "No star yet: make one the star if it must lead.";
  return `${lead} Leave out a note to put its word in Must avoid.`;
}

// Lines below the chips: words read as notes it has no stock note for, what it
// avoids, and the structure the composer adds on its own.
function briefExtraLines(result) {
  const lines = [];
  if (result.unmapped.length) lines.push(`Read as notes, but no stock note for them yet: ${result.unmapped.join(", ")}.`);
  if (result.avoided.length) lines.push(`Avoiding: ${result.avoided.join(", ")}.`);
  const structure = result.structure || {};
  const family = briefFamilyText(structure.family);
  if (family) lines.push(`Family: ${family}.`);
  const roles = (structure.roles || []).map((role) => role.label.toLowerCase());
  if (roles.length) {
    const support = structure.supporting_materials
      ? `, and ${structure.supporting_materials} supporting ${structure.supporting_materials === 1 ? "material" : "materials"} for the notes`
      : "";
    lines.push(`For the structure it also adds: ${roles.join(", ")}${support}.`);
  }
  return lines;
}

function attachBriefNotes({ doc, request, form, toggle, panel, context }) {
  const el = (tag, className, text) => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const field = (name) => form.querySelector(`[name="${name}"]`);
  const status = el("p", "brief-notes-status");
  status.setAttribute("role", "status");
  const list = el("ul", "brief-notes-list");
  list.setAttribute("aria-label", "What the composer understood");
  const extra = el("ul", "brief-notes-extra");
  const addRow = el("div", "brief-notes-add");
  const addLabel = el("label", "", "Add a note ");
  addLabel.append(el("span", "", "a note or a material, added to the brief as “With …”"));
  const addInput = el("input");
  addInput.maxLength = 80;
  addInput.autocomplete = "off";
  addLabel.append(addInput);
  const addButton = el("button", "quiet-button", "Add");
  addButton.type = "button";
  addRow.append(addLabel, addButton);
  panel.replaceChildren(status, list, extra, addRow);

  const live = { open: false, timer: 0, seq: 0, asked: "", result: null };

  const body = () => JSON.stringify({
    formula_name: field("formula_name").value.trim(),
    message: field("message").value.trim(),
    must_avoid: field("must_avoid").value.split(",").map((item) => item.trim()).filter(Boolean),
    conversation_context: context(),
  });

  function draw(result) {
    live.result = result;
    status.textContent = briefStatusLine(result);
    status.classList.toggle("is-problem", Boolean(result.needs_confirmation));
    list.replaceChildren(...result.notes.map((chip) => {
      const item = el("li", "brief-chip");
      item.dataset.chip = chip.id;
      item.dataset.kind = chip.kind;
      const words = el("span", "brief-chip-words");
      words.append(el("span", "brief-chip-label", chip.label), el("span", "brief-chip-meta", briefChipMeta(chip)));
      item.append(words);
      if (chip.star_phrase || chip.star) {
        const star = el("button", "quiet-button brief-chip-star", chip.star ? "★ The star" : "☆ Make the star");
        star.type = "button";
        star.dataset.act = "star";
        star.setAttribute("aria-pressed", String(Boolean(chip.star)));
        star.setAttribute("aria-label", chip.star ? `${chip.label} is the star` : `Make ${chip.label} the star`);
        item.append(star);
      }
      if (chip.remove_word) {
        const remove = el("button", "quiet-button brief-chip-remove", "Leave out");
        remove.type = "button";
        remove.dataset.act = "remove";
        remove.setAttribute("aria-label", `Leave out ${chip.label}`);
        item.append(remove);
      }
      return item;
    }));
    extra.replaceChildren(...briefExtraLines(result).map((line) => el("li", "", line)));
  }

  async function ask() {
    const text = body();
    const parsed = JSON.parse(text);
    if (!parsed.formula_name && !parsed.message && !parsed.conversation_context.length) {
      live.asked = "";
      status.textContent = "Type a name or an idea first.";
      list.replaceChildren();
      extra.replaceChildren();
      return;
    }
    if (text === live.asked) return;
    live.asked = text;
    const seq = ++live.seq;
    status.textContent = "Reading the brief…";
    try {
      const result = await request("/v2/workbench/brief-notes", { method: "POST", body: text });
      if (seq === live.seq && live.open) draw(result);
    } catch (error) {
      if (seq !== live.seq) return;
      live.asked = "";
      status.textContent = `Not read right now: ${error.message}`;
    }
  }

  function changed(delay = BRIEF_NOTES_DELAY_MS) {
    if (!live.open) return;
    clearTimeout(live.timer);
    live.timer = setTimeout(() => { ask().catch(() => {}); }, delay);
  }

  function setValue(name, value) {
    const input = field(name);
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  toggle.addEventListener("click", () => {
    live.open = !live.open;
    toggle.setAttribute("aria-expanded", String(live.open));
    panel.hidden = !live.open;
    if (live.open) changed(0);
  });
  form.addEventListener("input", (event) => {
    if (event.target !== addInput) changed();
  });
  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-act]");
    const result = live.result;
    if (!button || !result) return;
    const chip = result.notes.find((item) => item.id === button.closest("[data-chip]").dataset.chip);
    if (!chip) return;
    if (button.dataset.act === "remove") {
      form.querySelector(".optional-details").open = true;
      setValue("must_avoid", briefAvoidText(field("must_avoid").value, chip.remove_word));
      changed(0);
      return;
    }
    if (chip.star) return;
    if (result.star_marker) {
      status.textContent = "The brief already says what the star is. Change that sentence to move it.";
      return;
    }
    setValue("message", briefStarText(field("message").value, chip.star_phrase));
    changed(0);
  });
  const add = () => {
    const word = addInput.value.trim();
    if (!word) {
      addInput.focus();
      return;
    }
    setValue("message", briefWithText(field("message").value, word));
    addInput.value = "";
    changed(0);
  };
  addButton.addEventListener("click", add);
  addInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    add();
  });
  return { changed: () => changed(0) };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    briefSentenceAfter, briefStarText, briefWithText, briefAvoidText, briefFamilyText,
    briefChipMeta, briefStatusLine, briefExtraLines,
  };
}
