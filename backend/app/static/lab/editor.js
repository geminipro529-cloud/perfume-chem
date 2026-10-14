"use strict";

// Edit a formula page: a card, a paste or the Create draft in one editor you can
// drive from the keyboard. The maths lives in formula-editor.js.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

const EDITOR_UNIT_NAMES = { uL: "µL", g: "grams", pct: "% of the liquid", parts: "parts per 1000 of the liquid" };
const EDITOR_NOTE_WORDS = { "": "—", top: "Top", heart: "Heart", base: "Base" };

const editorPage = {
  // Each history entry is { name, rows }; a load, an edit or a sort is one step.
  history: editorHistory({ name: "", rows: [editorRow()] }),
  unit: "uL",
  // Material name -> density at 25 °C as text, or null; each name is asked once.
  densities: {},
  notes: [],
  labels: new Map(),
  stocksSeen: null,
  focus: null,
  ticket: 0,
  // The saved version the rows came from or were last saved as:
  // { formulaId, version, name, savedAt, lockedBy, key }, or null.
  saved: null,
  // Saved formulas from the versions log, asked for when needed; versions by "id:n".
  formulas: null,
  versions: new Map(),
  saving: false,
  compareSeq: 0,
};

const editorNow = () => editorPage.history.present;

function editorStocks() {
  return state.projectInventory?.stocks || [];
}

function editorStockLabel(stock) {
  return `${stock.identity_name || stock.material} · ${stockStrengthLabel(stock)}`;
}

// One datalist option per owned stock; a label two stocks share gets the
// stock's own line from the inventory so every option picks one stock.
function syncEditorStockOptions(stocks) {
  if (editorPage.stocksSeen === stocks) return;
  editorPage.stocksSeen = stocks;
  const owned = stocks.filter((stock) => String(stock.status ?? "").toLowerCase() === "owned");
  const counts = new Map();
  owned.forEach((stock) => counts.set(editorStockLabel(stock), (counts.get(editorStockLabel(stock)) || 0) + 1));
  editorPage.labels = new Map();
  const options = owned.map((stock) => {
    const plain = editorStockLabel(stock);
    const label = counts.get(plain) > 1 ? `${plain} · ${String(stock.stock_label || stock.stock_id).split("#")[0].trim()}` : plain;
    editorPage.labels.set(label, stock);
    const option = document.createElement("option");
    option.value = label;
    return option;
  });
  $("#editor-stock-options").replaceChildren(...options);
}

function editorLabelOf(stock) {
  for (const [label, item] of editorPage.labels) if (item === stock) return label;
  return editorStockLabel(stock);
}

function editorCommitRows(rows, name = editorNow().name) {
  editorPage.history = editorCommit(editorPage.history, { name, rows });
}

function showEditorError(message, input = null) {
  const box = $("#editor-error");
  box.textContent = message;
  box.hidden = false;
  if (input) {
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", "editor-error");
  }
}

function clearEditorError() {
  $("#editor-error").hidden = true;
  $("#editor-error").textContent = "";
  $$("#editor-rows [aria-invalid]").forEach((input) => {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-describedby");
  });
}

function editorCellNode(className = "") {
  const cell = document.createElement("td");
  // Roles keep the table readable as rows and cells when a phone lays it out as a grid.
  cell.setAttribute("role", "cell");
  if (className) cell.className = className;
  return cell;
}

// Sets a cell's value unless Kenny is typing in it right now.
function editorSetValue(input, value) {
  if (document.activeElement === input && input.value !== input.dataset.saved) return;
  input.value = value;
  input.dataset.saved = value;
}

function editorInput(field) {
  const input = document.createElement("input");
  input.dataset.field = field;
  input.setAttribute("autocomplete", "off");
  return input;
}

// A row's cells, made once per row and filled in place on every render, so a
// cell keeps the keyboard while the rows around it change.
function editorRowNode(row) {
  const tr = document.createElement("tr");
  tr.setAttribute("role", "row");
  tr.dataset.key = row.key;
  const material = editorInput("material");
  material.setAttribute("list", "editor-stock-options");
  const amount = editorInput("amount");
  amount.setAttribute("inputmode", "decimal");
  const amountWrap = document.createElement("div");
  amountWrap.className = "editor-amount";
  const unit = document.createElement("span");
  unit.className = "editor-unit";
  amountWrap.append(amount, unit);
  const note = document.createElement("select");
  note.dataset.field = "note";
  Object.entries(EDITOR_NOTE_WORDS).forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    note.append(option);
  });
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "quiet-button editor-remove";
  remove.dataset.action = "remove";
  // A phone shows the × only (formula-editor.css); the aria-label names the row.
  const word = document.createElement("span");
  word.className = "editor-remove-word";
  word.textContent = "Remove";
  const mark = document.createElement("span");
  mark.className = "editor-remove-mark";
  mark.setAttribute("aria-hidden", "true");
  mark.textContent = "×";
  remove.append(word, mark);
  const cells = [editorCellNode("editor-number"), editorCellNode(), editorCellNode(), editorCellNode(), editorCellNode("editor-stock"), editorCellNode()];
  cells[1].append(material);
  cells[2].append(amountWrap);
  cells[3].append(note);
  cells[5].append(remove);
  tr.append(...cells);
  return tr;
}

function editorFillRow(tr, row, index, totals, stocks) {
  const number = index + 1;
  const [numberCell, , , , stockCell] = tr.children;
  numberCell.textContent = String(number);
  const material = tr.querySelector('[data-field="material"]');
  const amount = tr.querySelector('[data-field="amount"]');
  const note = tr.querySelector('[data-field="note"]');
  const stock = editorStockOf(row, stocks);
  material.setAttribute("aria-label", `Material, row ${number}`);
  editorSetValue(material, stock ? editorLabelOf(stock) : row.material);
  const shown = editorShown(row, totals, editorPage.unit, editorPage.densities);
  amount.setAttribute("aria-label", `Amount in ${row.solid ? shown.unit : EDITOR_UNIT_NAMES[editorPage.unit]}, row ${number}`);
  amount.placeholder = shown.why || "";
  editorSetValue(amount, shown.text);
  tr.querySelector(".editor-unit").textContent = shown.unit;
  note.setAttribute("aria-label", `Note, row ${number}`);
  note.value = row.note;
  tr.querySelector('[data-action="remove"]').setAttribute("aria-label", `Remove row ${number}`);
  let text = "";
  let problem = false;
  if (stock) {
    text = stockStrengthLabel(stock);
  } else if (row.material) {
    text = editorStockCandidates(row, stocks).length > 1 ? "Several stocks: pick one from the list" : "Not in your stock";
    problem = true;
  }
  if (row.grams && !row.amount) {
    text = `${text ? `${text}. ` : ""}${editorFigure(row.grams, 3)} g read; density not known, type its µL`;
    problem = true;
  }
  stockCell.textContent = text;
  stockCell.classList.toggle("is-problem", problem);
}

function editorTotalsText(rows) {
  const totals = editorTotals(rows);
  const named = rows.filter((row) => row.material).length;
  const parts = [`${named} ${named === 1 ? "row" : "rows"}`, `${editorFigure(totals.liquidUl, 1)} µL liquid`];
  if (totals.solidMg.n > 0n) parts.push(`${editorFigure(totals.solidMg, 1)} mg solids`);
  if (editorPage.unit === "g") {
    const unknown = rows.filter((row) => row.amount && !row.solid && !editorDensity(row, editorPage.densities)).length;
    if (unknown) parts.push(`${unknown} without a known density`);
  }
  return parts.join(" · ");
}

function renderEditor() {
  const { name, rows } = editorNow();
  const stocks = editorStocks();
  syncEditorStockOptions(stocks);
  const totals = editorTotals(rows);
  $("#editor-name").value = name;
  $("#editor-unit").value = editorPage.unit;
  const body = $("#editor-rows");
  if (rows.length) {
    const existing = new Map([...body.querySelectorAll("tr[data-key]")].map((tr) => [tr.dataset.key, tr]));
    const wanted = rows.map((row) => existing.get(row.key) || editorRowNode(row));
    rows.forEach((row, index) => editorFillRow(wanted[index], row, index, totals, stocks));
    // Nodes move only when the order changed: moving a node takes its focus away.
    const current = [...body.children];
    if (current.length !== wanted.length || current.some((node, index) => node !== wanted[index])) body.replaceChildren(...wanted);
  } else {
    const empty = document.createElement("tr");
    empty.setAttribute("role", "row");
    const cell = editorCellNode("editor-empty");
    cell.colSpan = 6;
    cell.textContent = "No rows yet. Load a formula above, or add a row and start typing a material.";
    empty.append(cell);
    body.replaceChildren(empty);
  }
  $("#editor-totals").textContent = editorTotalsText(rows);
  $("#editor-notes").replaceChildren(...editorPage.notes.map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  }));
  $("#editor-undo").disabled = !editorPage.history.past.length;
  $("#editor-redo").disabled = !editorPage.history.future.length;
  const focus = editorPage.focus;
  editorPage.focus = null;
  if (focus) {
    const input = $(`#editor-rows tr[data-key="${CSS.escape(focus.key)}"] [data-field="${focus.field}"]`);
    if (input) {
      input.focus();
      if (input.select) input.select();
    }
  }
  renderEditorSide();
  renderEditorVersionState();
}

// Densities for every named row not asked about yet (the grams view needs them).
async function editorEnsureDensities(rows) {
  const names = [...new Set(rows.map((row) => row.material).filter((name) => name && !Object.hasOwn(editorPage.densities, name)))].slice(0, 300);
  if (!names.length) return false;
  const answer = await request("/v2/workbench/material-densities", { method: "POST", body: JSON.stringify({ names }) });
  names.forEach((name) => { editorPage.densities[name] = answer.densities?.[name] ?? null; });
  return true;
}

// New rows bound to owned stocks where the name and strength say which, with
// rows read in grams converted by density. Returns the rows and notes on them.
async function editorPrepareRows(rows, skipped = []) {
  const bound = editorBindRows(rows, editorStocks());
  const needGrams = bound.rows.some((row) => row.grams);
  if (needGrams || editorPage.unit === "g") await editorEnsureDensities(bound.rows);
  const resolved = editorResolveGrams(bound.rows, editorPage.densities, editorStocks());
  const notes = [];
  if (bound.unmatched.length) notes.push(`Not in your stock at that strength: ${benchNameList(bound.unmatched)}.`);
  if (bound.ambiguous.length) notes.push(`Several stocks fit, pick one in the row: ${benchNameList(bound.ambiguous)}.`);
  if (resolved.waiting.length) notes.push(`Read in grams but the density is not known, so type their µL: ${benchNameList(resolved.waiting)}.`);
  if (skipped.length) notes.push(`Skipped, no amount with a unit: ${benchNameList(skipped)}.`);
  return { rows: resolved.rows, notes };
}

async function editorRowsFromText(text) {
  const plain = editorParsePlain(text);
  if (plain) return editorRowsFromPlain(plain, editorPage.unit, editorNow().rows);
  const source = await request("/v2/workbench/formula-text", { method: "POST", body: JSON.stringify({ text }) });
  const result = editorRowsFromSource(source.rows);
  return { ...result, name: source.formula_name };
}

function editorRowIndex(element) {
  const key = element.closest("tr[data-key]")?.dataset.key;
  return editorNow().rows.findIndex((row) => row.key === key);
}

function editorCommitMaterial(index, text) {
  const { rows } = editorNow();
  const row = rows[index];
  const typed = String(text ?? "").trim();
  const picked = editorPage.labels.get(typed);
  let next;
  if (picked) {
    next = editorBindRow(row, picked);
  } else {
    next = { ...row, material: typed, stockId: null, fraction: "", basis: "", carrier: null };
    const candidates = typed ? editorStockCandidates(next, editorStocks()) : [];
    if (candidates.length === 1) next = editorBindRow(next, candidates[0]);
  }
  editorCommitRows(editorReplace(rows, index, next));
}

function editorCommitAmount(index, input) {
  const { rows } = editorNow();
  editorCommitRows(editorSetAmount(rows, index, input.value, editorPage.unit, editorPage.densities));
}

// Saves the cell being edited. Returns false (and says why) when it can't be saved.
function editorSaveCell(input) {
  if (!input?.dataset.field || input.value === input.dataset.saved) return true;
  const index = editorRowIndex(input);
  if (index < 0) return true;
  try {
    if (input.dataset.field === "material") editorCommitMaterial(index, input.value);
    else if (input.dataset.field === "amount") editorCommitAmount(index, input);
    input.dataset.saved = input.value;
    clearEditorError();
    return true;
  } catch (error) {
    showEditorError(error.message, input);
    return false;
  }
}

async function editorAfterChange() {
  if (editorPage.unit === "g" && await editorEnsureDensities(editorNow().rows)) renderEditor();
}

function editorFocusRow(index, field) {
  const row = editorNow().rows[index];
  if (row) editorPage.focus = { key: row.key, field };
}

function editorUndoOrRedo(redo) {
  const before = editorPage.history;
  editorPage.history = redo ? editorRedo(before) : editorUndo(before);
  if (editorPage.history === before) return;
  clearEditorError();
  editorPage.notes = [];
  const active = document.activeElement;
  if (active?.dataset?.field) {
    const key = active.closest("tr[data-key]")?.dataset.key;
    if (key && editorNow().rows.some((row) => row.key === key)) editorPage.focus = { key, field: active.dataset.field };
  }
  renderEditor();
  notify(redo ? "Redone." : "Undone.");
}

async function editorPaste(index, text) {
  const pasted = await editorRowsFromText(text);
  if (!pasted.rows.length) throw new Error("No rows with a name and an amount were found in what you pasted.");
  const prepared = await editorPrepareRows(pasted.rows, pasted.skipped);
  const { rows } = editorNow();
  // Pasting into an empty row fills it; otherwise the rows go below it.
  const target = rows[index];
  const empty = target && !target.material && !target.amount;
  const base = empty ? editorRemove(rows, index) : rows;
  const at = empty ? index : index + 1;
  let next = base;
  prepared.rows.forEach((row, offset) => { next = editorInsert(next, at + offset, row); });
  editorCommitRows(next);
  editorPage.notes = [`Pasted ${prepared.rows.length} ${prepared.rows.length === 1 ? "row" : "rows"}.`, ...prepared.notes];
  editorFocusRow(at, "amount");
  renderEditor();
}

$("#editor-rows").addEventListener("change", (event) => {
  const input = event.target;
  const index = editorRowIndex(input);
  if (index < 0) return;
  if (input.dataset.field === "note") {
    const { rows } = editorNow();
    editorCommitRows(editorReplace(rows, index, { ...rows[index], note: input.value }));
    renderEditor();
    return;
  }
  if (input.value === input.dataset.saved) return;
  if (editorSaveCell(input)) {
    renderEditor();
    editorAfterChange().catch((error) => notify(error.message, true));
  }
});

$("#editor-rows").addEventListener("click", (event) => {
  const button = event.target.closest('[data-action="remove"]');
  if (!button) return;
  const index = editorRowIndex(button);
  const { rows } = editorNow();
  editorCommitRows(editorRemove(rows, index));
  editorFocusRow(Math.min(index, rows.length - 2), "material");
  renderEditor();
});

$("#editor-rows").addEventListener("keydown", (event) => {
  const input = event.target;
  const field = input.dataset?.field;
  if (!field) return;
  const key = event.key;
  const mod = event.ctrlKey || event.metaKey;
  const index = editorRowIndex(input);
  if (mod && !event.altKey && (key === "z" || key === "Z" || key === "y" || key === "Y")) {
    // Undo inside a cell being typed in stays the browser's own.
    if (field !== "note" && input.value !== input.dataset.saved) return;
    event.preventDefault();
    editorUndoOrRedo(key === "y" || key === "Y" || event.shiftKey);
    return;
  }
  if (mod && key === "Enter") {
    event.preventDefault();
    if (!editorSaveCell(input)) return;
    const row = editorRow();
    editorCommitRows(editorInsert(editorNow().rows, index + 1, row));
    editorPage.focus = { key: row.key, field: "material" };
    renderEditor();
    return;
  }
  if (mod && key === "Delete") {
    event.preventDefault();
    const { rows } = editorNow();
    editorCommitRows(editorRemove(rows, index));
    editorFocusRow(Math.min(index, rows.length - 2), field);
    renderEditor();
    return;
  }
  const down = key === "Enter" || (key === "ArrowDown" && field === "amount");
  const up = key === "ArrowUp" && field === "amount";
  if (!down && !up) return;
  const move = () => {
    if (!editorSaveCell(input)) return;
    const rows = editorNow().rows;
    const target = up ? index - 1 : index + 1;
    if (target >= rows.length && key === "Enter") {
      editorCommitRows(editorInsert(rows, rows.length, editorRow()));
    }
    if (target >= 0 && target < editorNow().rows.length) editorFocusRow(target, field);
    renderEditor();
    editorAfterChange().catch((error) => notify(error.message, true));
  };
  // Enter on a highlighted suggestion fills the material cell after this key
  // event, so the material cell is read once the browser has done that.
  if (field === "material") {
    setTimeout(move, 0);
    return;
  }
  event.preventDefault();
  move();
});

$("#editor-rows").addEventListener("paste", (event) => {
  const input = event.target;
  if (!input.dataset?.field || input.tagName !== "INPUT") return;
  const text = event.clipboardData?.getData("text/plain") || "";
  if (!/[\t\n]/.test(text.trim())) return;
  event.preventDefault();
  const index = editorRowIndex(input);
  editorPaste(index, text).catch((error) => showEditorError(error.message));
});

$("#editor-name").addEventListener("change", (event) => {
  editorPage.history = editorCommit(editorPage.history, { ...editorNow(), name: event.target.value.trim() });
  renderEditor();
});

$("#editor-unit").addEventListener("change", async (event) => {
  editorPage.unit = event.target.value;
  clearEditorError();
  try {
    if (editorPage.unit === "g") await editorEnsureDensities(editorNow().rows);
  } catch (error) {
    notify(error.message, true);
  }
  renderEditor();
});

$("#editor-undo").addEventListener("click", () => editorUndoOrRedo(false));
$("#editor-redo").addEventListener("click", () => editorUndoOrRedo(true));

$("#editor-add-row").addEventListener("click", () => {
  const row = editorRow();
  editorCommitRows([...editorNow().rows, row]);
  editorPage.focus = { key: row.key, field: "material" };
  renderEditor();
});

$("#editor-sort-note").addEventListener("click", () => {
  editorCommitRows(editorSorted(editorNow().rows, "note"));
  renderEditor();
  notify("Sorted by note: top, heart, base, then rows with no note; largest first in each.");
});

$("#editor-sort-amount").addEventListener("click", () => {
  editorCommitRows(editorSorted(editorNow().rows, "amount"));
  renderEditor();
  notify("Sorted by amount: liquids largest first, then solids.");
});

$("#editor-scale").addEventListener("click", () => {
  try {
    editorCommitRows(editorScaleTo(editorNow().rows, $("#editor-scale-to").value));
    clearEditorError();
    renderEditor();
    notify(`Scaled to ${$("#editor-scale-to").value.trim()} µL of liquid; every row keeps its share.`);
  } catch (error) {
    showEditorError(error.message, $("#editor-scale-to"));
  }
});

$("#editor-to-bench").addEventListener("click", () => {
  const { name, rows } = editorNow();
  const table = editorBenchTable(name, rows);
  if (!rows.some((row) => row.material && row.amount)) {
    showEditorError("Add at least one row with a material and an amount first.");
    return;
  }
  const form = $("#bench-source-form");
  form.elements.source_kind.value = "PASTED";
  form.elements.source_kind.dispatchEvent(new Event("change"));
  form.elements.pasted_text.value = table.text;
  navigate("benchsheet");
  form.requestSubmit();
  if (table.leftOut.length) notify(`Left off the bench sheet, no amount yet: ${benchNameList(table.leftOut)}.`);
});

$("#editor-copy").addEventListener("click", async () => {
  const { rows } = editorNow();
  try {
    await navigator.clipboard.writeText(editorTsv(rows, editorPage.unit, editorPage.densities));
    notify("Copied as a table. Paste it into a spreadsheet.");
  } catch {
    notify("This browser did not allow copying. Select the rows by hand instead.", true);
  }
});

function syncEditorSourceFields() {
  const kind = $('#editor-source-form [name="source_kind"]').value;
  $("#editor-project-field").hidden = kind !== "PROJECT_FILE";
  $("#editor-paste-field").hidden = kind !== "PASTED";
  $("#editor-saved-field").hidden = kind !== "SAVED";
  if (kind === "SAVED" && pageStarted) editorLoadFormulas().catch((error) => notify(error.message, true));
}

$('#editor-source-form [name="source_kind"]').addEventListener("change", syncEditorSourceFields);

async function loadEditorSource(data) {
  if (data.source_kind === "EMPTY") return { name: "", rows: [editorRow()], skipped: [] };
  if (data.source_kind === "SAVED") {
    if (!editorPage.formulas) await editorLoadFormulas();
    const formula = editorPage.formulas.find((item) => item.formula_id === data.saved_formula);
    if (!formula) throw benchFieldError("Choose a saved formula first. Save one with Save a version, under the rows.", "saved_formula");
    const version = await editorFetchVersion(formula.formula_id, formula.latest);
    return { name: version.name, rows: editorRowsFromSaved(version.rows), skipped: [], version };
  }
  if (data.source_kind === "CREATE") {
    const result = state.formulaChat.result;
    const rows = result ? selectedFormulaVariant(result).formula?.rows || [] : [];
    if (!rows.length) throw benchFieldError("There is no draft on Create a formula yet. Make one there first.", "source_kind");
    return { name: result.formula_name || "", ...editorRowsFromSource(rows) };
  }
  if (data.source_kind === "PASTED") {
    const text = String(data.pasted_text || "");
    if (!text.trim()) throw benchFieldError("Paste a card table or rows from a spreadsheet first.", "pasted_text");
    const result = await editorRowsFromText(text);
    return { name: result.name || "", ...result };
  }
  const path = String(data.project_formula_path || "").trim();
  if (!state.formulaLibrary.some((item) => item.source_path === path)) {
    throw benchFieldError("Choose a project formula from the search list first.", "project_formula_path");
  }
  const source = await request(`/v2/workbench/formula-source?source_path=${encodeURIComponent(path)}`);
  return { name: source.formula_name || "", ...editorRowsFromSource(source.rows) };
}

$("#editor-source-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.dataset.busy) return;
  const button = form.querySelector('button[type="submit"]');
  clearFormError(form);
  editorPage.ticket += 1;
  const ticket = editorPage.ticket;
  form.dataset.busy = "true";
  button.disabled = true;
  try {
    const loaded = await loadEditorSource(formData(form));
    if (!loaded.rows.length) throw new Error("No rows with a name and an amount were found.");
    const prepared = await editorPrepareRows(loaded.rows, loaded.skipped);
    if (ticket !== editorPage.ticket) return;
    editorPage.history = editorCommit(editorPage.history, { name: loaded.name, rows: prepared.rows });
    if (loaded.version) editorOpenedVersion(loaded.version);
    else editorPage.saved = null;
    const count = prepared.rows.filter((row) => row.material).length;
    const what = loaded.version ? `Opened version ${loaded.version.version}` : `Loaded ${count} ${count === 1 ? "row" : "rows"}`;
    editorPage.notes = count ? [`${what}. Undo goes back to what was here before.`, ...prepared.notes] : [];
    clearEditorError();
    editorFocusRow(0, "material");
    renderEditor();
  } catch (error) {
    if (ticket === editorPage.ticket) showFormError(form, error, "Not loaded.");
  } finally {
    delete form.dataset.busy;
    button.disabled = false;
  }
});

// ---- Side panel: IFRA, allergens, cost, stock left, smell over time ----
// Cost and stock left are worked out here on every render. The IFRA and
// allergen check (the gate's own functions, on the server) is asked once
// typing pauses, and the smell chart a little later; both only while the
// editor is on screen.

const EDITOR_CHECK_DELAY_MS = 250;
const EDITOR_CHART_DELAY_MS = 800;
const EDITOR_LIST_MAX = 8;
const editorSide = {
  checkTimer: 0,
  chartTimer: 0,
  checkSeq: 0,
  checkKey: "",
  answers: new Map(),
  // Lab stock id -> grams left; a stock asked about and not answered yet is null.
  remaining: {},
};

function editorSideVisible() {
  return pageStarted && $('[data-panel="editor"]').classList.contains("is-visible");
}

function editorBottleMl() {
  const value = editorNumber($("#editor-bottle-ml").value);
  return value && value.n > 0n ? value : null;
}

function editorBottleCount() {
  const text = $("#editor-bottles").value.trim();
  return /^[1-9]\d{0,4}$/.test(text) ? text : "";
}

function editorSideList(selector, items) {
  const shown = items.slice(0, EDITOR_LIST_MAX);
  if (items.length > shown.length) shown.push({ text: `and ${items.length - shown.length} more` });
  $(selector).replaceChildren(...shown.map((item) => {
    const line = document.createElement("li");
    line.textContent = item.text;
    if (item.problem) line.className = "is-problem";
    return line;
  }));
}

const editorGramsText = (value) => `${Number(value).toFixed(2)} g`;

function setEditorVerdict(text, kind) {
  const verdict = $("#editor-ifra-verdict");
  verdict.textContent = text;
  verdict.className = `editor-verdict${kind ? ` is-${kind}` : ""}`;
}

function renderEditorCost(rows) {
  const prices = stockPricesCurrent();
  const bottle = editorBottleMl();
  const volumeRows = editorCostRows(rows, editorPage.densities, {});
  const ethanolMl = bottle ? benchCostEthanolEstimate(volumeRows, benchFractionText(bottle, 3)) : "";
  const bottles = editorBottleCount();
  const costRows = editorCostRows(rows, editorPage.densities, prices);
  if (!costRows.length) {
    $("#editor-cost-summary").textContent = "Add rows with amounts to cost them.";
    editorSideList("#editor-cost-list", []);
    return;
  }
  const cost = benchCost({ rows: costRows, prices, ethanolMl, bottles: bottles || "1" });
  if (cost.problem) $("#editor-cost-summary").textContent = cost.problem;
  else if (![...cost.lines, ...cost.extras].some((item) => item.cost)) {
    $("#editor-cost-summary").textContent = "No prices yet. Type them on the Stock page to see the cost per bottle.";
    editorSideList("#editor-cost-list", []);
    return;
  } else {
    const perBottle = `${stockPriceMoneyText(cost.bottle, cost.currency)} per bottle`;
    const batch = bottles && bottles !== "1" ? `, ${stockPriceMoneyText(cost.batch, cost.currency)} for ${bottles}` : "";
    $("#editor-cost-summary").textContent = `${perBottle}${batch}${cost.partial ? ", not counting what is listed below" : ""}.`;
  }
  editorSideList("#editor-cost-list", [
    ...cost.lines.filter((line) => !line.cost).map((line) => ({ text: `${line.material}: ${line.reason}` })),
    ...cost.extras.filter((item) => !item.cost).map((item) => ({ text: `${item.label}: ${item.reason}` })),
  ]);
}

function renderEditorStock(rows) {
  const bottles = editorBottleCount() || "1";
  if (!state.stocks.length) {
    $("#editor-stock-summary").textContent = "No bottles are weighed into the Lab yet, so there is nothing to count down.";
    editorSideList("#editor-stock-list", []);
    return [];
  }
  const left = editorStockLeft(rows, state.stocks, state.materials, editorSide.remaining, editorPage.densities, bottles);
  const after = `after ${bottles} ${bottles === "1" ? "bottle" : "bottles"}`;
  const short = left.lines.filter((line) => line.short);
  $("#editor-stock-summary").textContent = short.length
    ? `Not enough for ${bottles === "1" ? "one bottle" : `${bottles} bottles`}: ${benchNameList(short.map((line) => line.material))}.`
    : (left.lines.length ? `Grams in your weighed Lab bottles, now and ${after}.` : "None of these rows has a bottle weighed into the Lab.");
  editorSideList("#editor-stock-list", [
    ...left.lines.map((line) => {
      if (line.nowG === null) return { text: `${line.material}: uses ${editorGramsText(line.useG)}, checking what is left…` };
      if (line.short) return { text: `${line.material}: needs ${editorGramsText(line.useG)}, ${editorGramsText(line.nowG)} left`, problem: true };
      return { text: `${line.material}: ${editorGramsText(line.nowG)} now, ${editorGramsText(line.afterG)} ${after}` };
    }),
    ...(left.noDensity.length ? [{ text: `Density not known, so the grams used can't be worked out: ${benchNameList(left.noDensity)}` }] : []),
    ...(left.unweighed.length ? [{ text: `No weighed bottle in the Lab: ${benchNameList(left.unweighed)}` }] : []),
  ]);
  return left.lines.flatMap((line) => line.stockIds).filter((id) => !Object.hasOwn(editorSide.remaining, id));
}

function renderEditorChecks(answer) {
  if (!answer) return;
  if (answer.error) {
    setEditorVerdict("", "");
    $("#editor-side-oil").textContent = "";
    $("#editor-allergen-summary").textContent = "";
    editorSideList("#editor-allergen-list", []);
    editorSideList("#editor-ifra-list", [{ text: `The IFRA and allergen check is not available right now: ${answer.error}`, problem: true }]);
    return;
  }
  const ifra = answer.ifra;
  const bottle = Number(answer.bottle_ml);
  $("#editor-side-oil").textContent = answer.bottle_source === "rows"
    ? `${Number(answer.oil_pct).toFixed(1)}% oil; the bottle is the rows with their ethanol, ${bottle.toFixed(1)} mL.`
    : `${Number(answer.oil_pct).toFixed(1)}% oil in a ${bottle} mL bottle, topped up with ${Number(answer.ethanol_ml).toFixed(1)} mL ethanol.`;
  const words = {
    PASS: ["Within the limits", "pass"],
    WARN: ["Within the limits, with notes", "warn"],
    HOLD: ["Not fully checked", "hold"],
    FAIL: ["Over an IFRA limit", "fail"],
  }[ifra.verdict] || [ifra.verdict, ""];
  setEditorVerdict(`${words[0]} · IFRA ${ifra.amendment}, Category ${ifra.category} (fine fragrance)`, words[1]);
  const items = [];
  if (answer.overfilled) items.push({ text: "The stocks fill more than the bottle, so no share of the bottle is defined.", problem: true });
  ifra.rows.filter((row) => row.verdict === "fail").forEach((row) => items.push({
    text: row.ifra_status === "prohibited"
      ? `${row.material}: prohibited`
      : `${row.material}: ${editorPctText(row.actual_pct)} of the bottle, limit ${editorPctText(row.limit_pct)}`,
    problem: true,
  }));
  ifra.groups.filter((group) => group.verdict === "fail").forEach((group) => items.push({ text: group.message, problem: true }));
  if (ifra.unrecognised.length) items.push({ text: `Not in the IFRA table, so not checked: ${benchNameList(ifra.unrecognised)}`, problem: true });
  ifra.rows.filter((row) => row.verdict === "warn" && row.usage_pct !== null).forEach((row) => items.push({ text: `${row.material}: ${row.usage_pct}% of its limit` }));
  ifra.groups.filter((group) => group.verdict === "warn").forEach((group) => items.push({ text: group.message }));
  const naturals = ifra.rows.filter((row) => row.verdict === "warn" && row.usage_pct === null).map((row) => row.material);
  if (naturals.length) items.push({ text: `Naturals with no IFRA standard of their own, counted by the constituents IFRA lists: ${benchNameList(naturals)}` });
  if (ifra.undisclosed_bases.length) items.push({ text: `Supplier bases with no published composition, not counted inside: ${benchNameList(ifra.undisclosed_bases)}` });
  items.push({ text: "Other product categories are not in the app's IFRA data yet." });
  editorSideList("#editor-ifra-list", items);
  const declare = answer.allergens.declare;
  $("#editor-allergen-summary").textContent = declare.length
    ? `Over the label line (0.001% for leave-on), declare: ${declare.length}. Named allergen materials only; those inside naturals and bases are not counted.`
    : "None over the label line (0.001% for leave-on). Named allergen materials only; those inside naturals and bases are not counted.";
  editorSideList("#editor-allergen-list", declare.map((row) => ({ text: `${row.allergen}: ${editorPctText(row.pct)}` })));
}

async function runEditorChecks() {
  const rows = editorCheckRows(editorNow().rows);
  const bottle = editorBottleMl();
  if (!rows.length || !bottle) {
    editorSide.checkKey = "";
    setEditorVerdict("", "");
    $("#editor-side-oil").textContent = bottle ? "Add rows with amounts to check them." : "Type the bottle size in mL, such as 30.";
    $("#editor-allergen-summary").textContent = "";
    editorSideList("#editor-ifra-list", []);
    editorSideList("#editor-allergen-list", []);
    return;
  }
  const body = JSON.stringify({ rows, bottle_ml: benchFractionText(bottle, 3) });
  if (body === editorSide.checkKey) return;
  editorSide.checkKey = body;
  const seq = ++editorSide.checkSeq;
  let answer = editorSide.answers.get(body);
  if (!answer) {
    try {
      answer = await request("/v2/workbench/formula-checks", { method: "POST", body });
      editorSide.answers.set(body, answer);
      if (editorSide.answers.size > 20) editorSide.answers.delete(editorSide.answers.keys().next().value);
    } catch (error) {
      answer = { error: error.message };
      editorSide.checkKey = "";
    }
  }
  if (seq === editorSide.checkSeq) renderEditorChecks(answer);
}

async function askEditorRemaining(ids) {
  ids.forEach((id) => { editorSide.remaining[id] = null; });
  const answers = await Promise.all(ids.map((id) => request(`/stocks/${encodeURIComponent(id)}`).catch(() => null)));
  answers.forEach((stock, index) => {
    const grams = Number(stock?.remaining_mass_g);
    if (Number.isFinite(grams)) editorSide.remaining[ids[index]] = grams;
    else delete editorSide.remaining[ids[index]];
  });
  renderEditorStock(editorNow().rows);
}

function renderEditorSide() {
  const rows = editorNow().rows;
  renderEditorCost(rows);
  const unknown = renderEditorStock(rows);
  if (!editorSideVisible()) return;
  if (unknown.length) askEditorRemaining(unknown).catch(() => {});
  // Grams (cost per g, stock used) need densities; ask for any new names once.
  editorEnsureDensities(rows).then((asked) => { if (asked) renderEditorSide(); }).catch(() => {});
  clearTimeout(editorSide.checkTimer);
  editorSide.checkTimer = setTimeout(() => runEditorChecks().catch(() => {}), EDITOR_CHECK_DELAY_MS);
  clearTimeout(editorSide.chartTimer);
  editorSide.chartTimer = setTimeout(() => renderScentChart($("#editor-scent"), editorChartRows(editorNow().rows)), EDITOR_CHART_DELAY_MS);
}

["#editor-bottle-ml", "#editor-bottles"].forEach((selector) => $(selector).addEventListener("input", () => {
  renderEditorSide();
  renderEditorVersionState();
}));

// navigate() calls this when the editor comes on screen.
function editorSideShown() {
  renderEditorSide();
  // A batch recorded or a bottle poured since may have changed the open formula's versions.
  if (editorPage.saved) editorLoadFormulas().catch(() => {});
}

// refresh() calls this when the stock list arrives or changes.
function editorInventoryChanged() {
  // Lab bottles may have been weighed or poured since: ask again.
  editorSide.remaining = {};
  renderEditor();
}

// ---- Versions: save, open and compare ----
// Every save is a version in the versions log in data/user
// (app/services/formula_versions.py). The list is asked for only when it is
// needed: choosing a saved formula, saving, or opening a version.

const EDITOR_VERSIONS_URL = "/v2/workbench/formula-versions";

function editorNode(tag, text = "", className = "") {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function editorVersionDate(text) {
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return String(text || "");
  return date.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function editorBottleText() {
  const bottle = editorBottleMl();
  return bottle ? benchFractionText(bottle, 3) : "";
}

function editorCurrentKey() {
  const { name, rows } = editorNow();
  return editorContentKey(name, rows, editorBottleText());
}

function editorSavedFormula() {
  const saved = editorPage.saved;
  if (!saved || !editorPage.formulas) return null;
  return editorPage.formulas.find((formula) => formula.formula_id === saved.formulaId) || null;
}

async function editorFetchVersion(formulaId, number) {
  const key = `${formulaId}:${number}`;
  if (!editorPage.versions.has(key)) {
    // A version never changes, so its rows are asked for once.
    editorPage.versions.set(key, await request(`${EDITOR_VERSIONS_URL}/${encodeURIComponent(formulaId)}/${number}`));
  }
  return editorPage.versions.get(key);
}

function syncEditorSavedOptions() {
  const select = $('#editor-source-form [name="saved_formula"]');
  const keep = select.value;
  const formulas = editorPage.formulas || [];
  if (!formulas.length) {
    const none = new Option("Nothing saved yet", "");
    none.disabled = true;
    select.replaceChildren(none);
    return;
  }
  select.replaceChildren(...formulas.map((formula) => new Option(
    `${formula.name} · ${formula.latest === 1 ? "1 version" : `${formula.latest} versions`}, last saved ${editorVersionDate(formula.updated_at)}`,
    formula.formula_id,
  )));
  if (formulas.some((formula) => formula.formula_id === keep)) select.value = keep;
}

async function editorLoadFormulas() {
  const answer = await request(EDITOR_VERSIONS_URL);
  editorPage.formulas = answer.formulas || [];
  syncEditorSavedOptions();
  renderEditorVersionState();
}

// The rows on screen came from (or were just saved as) this version.
function editorOpenedVersion(version) {
  $("#editor-bottle-ml").value = version.bottle_ml || "";
  editorPage.saved = {
    formulaId: version.formula_id,
    version: version.version,
    name: version.name,
    savedAt: version.saved_at,
    lockedBy: version.locked_by || [],
    // From the rows as saved, so a stock bound since then shows as a change.
    key: editorContentKey(version.name, editorRowsFromSaved(version.rows), version.bottle_ml || ""),
  };
}

function renderEditorVersionState() {
  const saved = editorPage.saved;
  const line = $("#editor-version-state");
  if (!saved) {
    line.textContent = "Not saved yet. Save a version to keep this formula as it is now and compare later changes with it.";
  } else {
    const formula = editorSavedFormula();
    const entry = formula?.versions.find((version) => version.version === saved.version);
    const lots = entry ? entry.locked_by : saved.lockedBy;
    const lock = lots.length ? ` Locked: batch ${lots.join(", ")} was made from it.` : "";
    line.textContent = saved.key === editorCurrentKey()
      ? `Version ${saved.version} of ${saved.name}, saved ${editorVersionDate(saved.savedAt)}. No changes since.${lock}`
      : `Changed since version ${saved.version} of ${saved.name}. Saving makes version ${(formula ? formula.latest : saved.version) + 1}.${lock}`;
  }
  renderEditorVersions();
}

function syncEditorCompareOptions(formula) {
  const numbers = formula.versions.map((version) => version.version);
  const current = editorPage.saved.version;
  // The version before the open one and the open one; the first version is compared with the next.
  const at = numbers.indexOf(current);
  const defaults = at > 0 ? [numbers[at - 1], current] : [current, numbers[1] ?? current];
  ["#editor-compare-a", "#editor-compare-b"].forEach((selector, index) => {
    const select = $(selector);
    const keep = Number(select.value);
    const same = select.dataset.formula === formula.formula_id && select.options.length === numbers.length;
    if (!same) select.replaceChildren(...numbers.map((number) => new Option(String(number), String(number))));
    select.value = String(same && numbers.includes(keep) ? keep : defaults[index]);
    select.dataset.formula = formula.formula_id;
  });
}

function renderEditorVersions() {
  const panel = $("#editor-versions");
  const formula = editorSavedFormula();
  panel.hidden = !formula;
  if (!formula) return;
  $("#editor-versions-title").textContent = `Versions of ${formula.name}`;
  const current = editorPage.saved.version;
  $("#editor-version-list").replaceChildren(...[...formula.versions].reverse().map((version) => {
    const item = editorNode("li", "", version.version === current ? "is-current" : "");
    const parts = [`Version ${version.version}`, `saved ${editorVersionDate(version.saved_at)}`, `${version.row_count} ${version.row_count === 1 ? "row" : "rows"}`];
    if (version.note) parts.push(`“${version.note}”`);
    if (version.locked) parts.push(`locked: batch ${version.locked_by.join(", ")}`);
    if (version.bottles.length) parts.push(`${version.bottles.length} ${version.bottles.length === 1 ? "bottle" : "bottles"} made from it`);
    item.append(editorNode("span", parts.join(" · ")));
    if (version.version === current) {
      item.append(editorNode("span", "open in the editor", "editor-version-open-now"));
    } else {
      const open = editorNode("button", `Open version ${version.version}`, "quiet-button");
      open.type = "button";
      open.dataset.version = String(version.version);
      item.append(open);
    }
    return item;
  }));
  renderEditorVersionBottles(formula);
  syncEditorCompareOptions(formula);
}

// The Lab bottles tied to the version open in the editor, and the bottles that can be tied.
function renderEditorVersionBottles(formula) {
  const number = editorPage.saved.version;
  const tied = formula.versions.find((version) => version.version === number)?.bottles || [];
  $("#editor-version-bottles-title").textContent = `Bottles made from version ${number}`;
  $("#editor-version-bottle-list").replaceChildren(...(tied.length ? tied.map((bottle) => {
    const item = editorNode("li");
    const untie = editorNode("button", "Untie", "quiet-button");
    untie.type = "button";
    untie.dataset.untie = bottle.bottle_id;
    untie.setAttribute("aria-label", `Untie ${bottle.label || "this bottle"} from version ${number}`);
    item.append(editorNode("span", bottle.label || bottle.bottle_id), untie);
    return item;
  }) : [editorNode("li", "None yet. Tie each Lab bottle you pour from this version, so its smell logs show with it.", "editor-side-line")]));
  const here = new Set(tied.map((bottle) => bottle.bottle_id));
  const free = state.bottles.filter((bottle) => !here.has(bottle.id));
  const select = $("#editor-tie-bottle");
  const signature = JSON.stringify(free.map((bottle) => [bottle.id, bottle.label]));
  if (select.dataset.signature !== signature) {
    const keep = select.value;
    if (free.length) {
      select.replaceChildren(...free.map((bottle) => new Option(bottle.label || bottle.id, bottle.id)));
      if (free.some((bottle) => bottle.id === keep)) select.value = keep;
    } else {
      const none = new Option(state.bottles.length ? "Every Lab bottle is tied here" : "No bottles in the Lab yet", "");
      none.disabled = true;
      select.replaceChildren(none);
    }
    select.dataset.signature = signature;
  }
  select.disabled = !free.length;
  $("#editor-tie").disabled = !free.length;
  $("#editor-tie").textContent = `Tie to version ${number}`;
  $("#editor-make-batch").textContent = `Make a batch from version ${number}`;
}

async function editorSaveVersion() {
  if (editorPage.saving) return;
  const active = document.activeElement;
  if (active?.closest?.("#editor-rows") && !editorSaveCell(active)) return;
  const nameInput = $("#editor-name");
  if (nameInput.value.trim() !== editorNow().name) {
    editorPage.history = editorCommit(editorPage.history, { ...editorNow(), name: nameInput.value.trim() });
    renderEditor();
  }
  const { name, rows } = editorNow();
  if (!name) {
    showEditorError("Give the formula a name before saving it.", nameInput);
    return;
  }
  const saved = editorSavedRows(rows);
  if (!saved.rows.length) {
    showEditorError("Add at least one row with a material and an amount first.");
    return;
  }
  const key = editorCurrentKey();
  if (editorPage.saved && editorPage.saved.key === key) {
    notify(`No changes since version ${editorPage.saved.version}, so nothing new was saved.`);
    return;
  }
  const body = {
    name,
    note: $("#editor-version-note").value.trim(),
    bottle_ml: editorBottleText(),
    rows: saved.rows,
    card_text: editorBenchTable(name, rows).text,
  };
  if (editorPage.saved) Object.assign(body, { formula_id: editorPage.saved.formulaId, parent_version: editorPage.saved.version });
  const button = $("#editor-save-version");
  editorPage.saving = true;
  button.disabled = true;
  try {
    const record = await request(EDITOR_VERSIONS_URL, { method: "POST", body: JSON.stringify(body) });
    const { created, ...version } = record;
    editorPage.versions.set(`${version.formula_id}:${version.version}`, version);
    editorPage.saved = {
      formulaId: version.formula_id,
      version: version.version,
      name: version.name,
      savedAt: version.saved_at,
      lockedBy: version.locked_by,
      key,
    };
    clearEditorError();
    if (created) $("#editor-version-note").value = "";
    const left = saved.leftOut.length ? ` Left out, no amount yet: ${benchNameList(saved.leftOut)}.` : "";
    notify(created ? `Saved as version ${version.version}.${left}` : `Nothing new: this is the same as version ${version.version}.`);
    renderEditorVersionState();
    await editorLoadFormulas();
  } catch (error) {
    showEditorError(`Not saved: ${error.message}`);
  } finally {
    editorPage.saving = false;
    button.disabled = false;
  }
}

async function editorOpenVersion(number) {
  const saved = editorPage.saved;
  if (!saved) return;
  editorPage.ticket += 1;
  const ticket = editorPage.ticket;
  const version = await editorFetchVersion(saved.formulaId, number);
  const prepared = await editorPrepareRows(editorRowsFromSaved(version.rows));
  if (ticket !== editorPage.ticket) return;
  editorPage.history = editorCommit(editorPage.history, { name: version.name, rows: prepared.rows });
  editorOpenedVersion(version);
  editorPage.notes = [`Opened version ${version.version}. Undo goes back to what was here before.`, ...prepared.notes];
  clearEditorError();
  renderEditor();
}

$("#editor-save-version").addEventListener("click", () => editorSaveVersion());

$('[data-panel="editor"]').addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || String(event.key || "").toLowerCase() !== "s") return;
  event.preventDefault();
  editorSaveVersion();
});

$("#editor-version-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-version]");
  if (!button) return;
  editorOpenVersion(Number(button.dataset.version)).catch((error) => showEditorError(`Not opened: ${error.message}`));
});

async function editorTieBottle(bottleId, tied) {
  const saved = editorPage.saved;
  if (!saved || !bottleId) return;
  const label = state.bottles.find((bottle) => bottle.id === bottleId)?.label || "The bottle";
  await request(`${EDITOR_VERSIONS_URL}/${encodeURIComponent(saved.formulaId)}/${saved.version}/bottles`, {
    method: "POST",
    body: JSON.stringify({ bottle_id: bottleId, tied }),
  });
  notify(tied ? `${label} is tied to version ${saved.version}.` : `${label} is untied from version ${saved.version}.`);
  await editorLoadFormulas();
}

$("#editor-tie").addEventListener("click", () => {
  editorTieBottle($("#editor-tie-bottle").value, true).catch((error) => notify(`Not tied: ${error.message}`, true));
});

$("#editor-version-bottle-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-untie]");
  if (!button) return;
  editorTieBottle(button.dataset.untie, false).catch((error) => notify(`Not untied: ${error.message}`, true));
});

// The Batch page reads the version's own card text, so the batch record's card
// hash is the version's and recording the batch locks the version.
$("#editor-make-batch").addEventListener("click", async () => {
  const saved = editorPage.saved;
  const form = $(".batch-plan-form");
  if (!saved || !form) return;
  try {
    const version = await editorFetchVersion(saved.formulaId, saved.version);
    const field = (name) => form.elements.namedItem(name);
    field("source_kind").value = "PASTED";
    field("source_kind").dispatchEvent(new Event("change"));
    field("pasted_text").value = version.card_text;
    field("name").value = `${version.name} version ${version.version}`;
    if (version.bottle_ml) field("bottle_ml").value = version.bottle_ml;
    field("card_total_ml").value = editorCardMakesMl(editorRowsFromSaved(version.rows), version.bottle_ml);
    // The Batch page drops a plan when its source changes.
    field("pasted_text").dispatchEvent(new Event("input"));
    navigate("batch");
    field("bottles").focus();
    field("bottles").select();
    notify(`Version ${version.version} is on the Batch page. Type the number of bottles and plan the batch; recording it locks version ${version.version}.`);
  } catch (error) {
    notify(`Not opened on the Batch page: ${error.message}`, true);
  }
});

// Each version's tied bottles with how many smell log entries each has.
async function editorBottleLogs(entry) {
  const bottles = entry?.bottles || [];
  return Promise.all(bottles.map(async (bottle) => {
    try {
      const log = await request(`/bottles/${encodeURIComponent(bottle.bottle_id)}/smell-log`);
      return { label: bottle.label || bottle.bottle_id, count: (log.entries || []).length };
    } catch {
      return { label: bottle.label || bottle.bottle_id, count: null };
    }
  }));
}

function editorBottleLogText(number, logs) {
  if (!logs.length) return `Version ${number}: no bottle tied to it yet.`;
  const one = ({ label, count }) => {
    if (count === null) return `${label} (smell log not available)`;
    return `${label} (${count ? `${count} smell ${count === 1 ? "log" : "logs"}` : "no smell logs yet"})`;
  };
  return `Version ${number}: ${logs.map(one).join(", ")}.`;
}

// The IFRA and allergen answer for a version's rows, from the same cache as the side panel.
async function editorVersionChecks(version, rows) {
  const body = JSON.stringify({ rows: editorCheckRows(rows), bottle_ml: version.bottle_ml || "30" });
  if (!editorSide.answers.has(body)) {
    editorSide.answers.set(body, await request("/v2/workbench/formula-checks", { method: "POST", body }));
    if (editorSide.answers.size > 20) editorSide.answers.delete(editorSide.answers.keys().next().value);
  }
  return editorSide.answers.get(body);
}

// Cost of one bottle from the prices on the Stock page, or "" when nothing is priced.
function editorBottleCostText(rows, bottleMl) {
  const prices = stockPricesCurrent();
  const costRows = editorCostRows(rows, editorPage.densities, prices);
  if (!costRows.length) return "";
  const ethanolMl = bottleMl ? benchCostEthanolEstimate(editorCostRows(rows, editorPage.densities, {}), bottleMl) : "";
  const cost = benchCost({ rows: costRows, prices, ethanolMl, bottles: "1" });
  if (cost.problem || ![...cost.lines, ...cost.extras].some((item) => item.cost)) return "";
  return `${stockPriceMoneyText(cost.bottle, cost.currency)}${cost.partial ? " (not every row priced)" : ""}`;
}

// On a phone each row wraps (formula-editor.css), so the table keeps its roles
// in the markup and each figure carries its column name for the wrapped view.
function editorCompareTable(diff, a, b) {
  const table = editorNode("table", "", "editor-compare-table");
  table.setAttribute("role", "table");
  const columns = ["Material", "Strength", `Version ${a}`, `Version ${b}`, "Change", "Share of the liquid"];
  const head = editorNode("tr");
  head.setAttribute("role", "row");
  columns.forEach((text) => {
    const cell = editorNode("th", text);
    cell.scope = "col";
    cell.setAttribute("role", "columnheader");
    head.append(cell);
  });
  table.append(editorNode("thead"), editorNode("tbody"));
  [table.tHead, table.tBodies[0]].forEach((group) => group.setAttribute("role", "rowgroup"));
  table.tHead.append(head);
  diff.lines.forEach((line) => {
    const tr = editorNode("tr", "", `is-${line.kind}`);
    tr.setAttribute("role", "row");
    const amount = (text) => (text ? `${text} ${line.unit}` : "—");
    const change = line.change ? `${line.change} ${line.unit}` : (line.kind === "added" ? "added" : "removed");
    const share = line.aPct || line.bPct ? `${line.aPct || "—"} → ${line.bPct || "—"}` : "";
    [line.material, line.strength, amount(line.a), amount(line.b), change, share].forEach((text, index) => {
      const cell = editorNode("td", text);
      cell.setAttribute("role", "cell");
      cell.dataset.label = columns[index];
      tr.append(cell);
    });
    table.tBodies[0].append(tr);
  });
  return table;
}

async function editorCompareVersions(a, b) {
  const saved = editorPage.saved;
  const out = $("#editor-compare");
  if (!saved) return;
  if (a === b) {
    out.replaceChildren(editorNode("p", "Pick two different versions to compare.", "editor-side-line"));
    return;
  }
  const seq = ++editorPage.compareSeq;
  out.replaceChildren(editorNode("p", "Comparing…", "editor-side-line"));
  const [versionA, versionB] = await Promise.all([editorFetchVersion(saved.formulaId, a), editorFetchVersion(saved.formulaId, b)]);
  const rowsA = editorRowsFromSaved(versionA.rows);
  const rowsB = editorRowsFromSaved(versionB.rows);
  const diff = editorCompare(rowsA, rowsB);
  const checks = await Promise.all([[versionA, rowsA], [versionB, rowsB]].map(([version, rows]) => (
    editorVersionChecks(version, rows).catch((error) => ({ error: error.message }))
  )));
  await editorEnsureDensities([...rowsA, ...rowsB]).catch(() => false);
  const formula = editorSavedFormula();
  const entries = [a, b].map((number) => formula?.versions.find((version) => version.version === number));
  const logs = await Promise.all(entries.map((entry) => editorBottleLogs(entry)));
  if (seq !== editorPage.compareSeq) return;
  const nodes = [editorNode("h3", `Version ${a} → version ${b}`)];
  if (diff.lines.length) nodes.push(editorCompareTable(diff, a, b));
  const unchanged = diff.same ? `${diff.same} ${diff.same === 1 ? "row" : "rows"} unchanged. ` : "";
  nodes.push(editorNode("p", `${diff.lines.length ? "" : "The rows are the same. "}${unchanged}Liquid: ${diff.liquid[0]} µL → ${diff.liquid[1]} µL.`, "editor-side-line"));
  nodes.push(editorNode("h4", "Checks"));
  const list = editorNode("ul", "", "editor-check-list");
  const failed = checks.find((answer) => answer.error);
  if (failed) {
    list.append(editorNode("li", `The IFRA and allergen check is not available right now: ${failed.error}`, "is-problem"));
  } else {
    const changes = editorCheckChanges(checks[0], checks[1]);
    if (!changes.length) changes.push({ text: `No check changed: IFRA is ${EDITOR_VERDICT_WORDS[checks[1].ifra.verdict] || checks[1].ifra.verdict} in both.` });
    changes.forEach((change) => list.append(editorNode("li", change.text, change.problem ? "is-problem" : "")));
  }
  nodes.push(list);
  const costs = [editorBottleCostText(rowsA, versionA.bottle_ml), editorBottleCostText(rowsB, versionB.bottle_ml)];
  if (costs.some(Boolean)) {
    nodes.push(editorNode("h4", "Cost per bottle"));
    nodes.push(editorNode("p", `${costs[0] || "not priced"} → ${costs[1] || "not priced"}`, "editor-side-line"));
  }
  nodes.push(editorNode("h4", "Bottles and smell logs"));
  const bottleList = editorNode("ul", "", "editor-check-list");
  [a, b].forEach((number, index) => bottleList.append(editorNode("li", editorBottleLogText(number, logs[index]))));
  nodes.push(bottleList);
  out.replaceChildren(...nodes);
}

$("#editor-compare-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const a = Number($("#editor-compare-a").value);
  const b = Number($("#editor-compare-b").value);
  editorCompareVersions(a, b).catch((error) => {
    $("#editor-compare").replaceChildren(editorNode("p", `Not compared: ${error.message}`, "form-error"));
  });
});

syncEditorSourceFields();
renderEditor();
