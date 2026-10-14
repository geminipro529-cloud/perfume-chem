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
}

$('#editor-source-form [name="source_kind"]').addEventListener("change", syncEditorSourceFields);

async function loadEditorSource(data) {
  if (data.source_kind === "EMPTY") return { name: "", rows: [editorRow()], skipped: [] };
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
    const count = prepared.rows.filter((row) => row.material).length;
    editorPage.notes = count ? [`Loaded ${count} ${count === 1 ? "row" : "rows"}. Undo goes back to what was here before.`, ...prepared.notes] : [];
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

// refresh() calls this when the stock list arrives or changes.
function editorInventoryChanged() {
  renderEditor();
}

syncEditorSourceFields();
renderEditor();
