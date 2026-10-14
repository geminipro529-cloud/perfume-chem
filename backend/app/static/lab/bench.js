"use strict";

// Bench sheet page: a printable sheet for any project or pasted formula, with the pour fix.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

// ---- Bench sheet view: a printable sheet for any project or pasted formula ----
// Read-only: it fetches and parses the formula, matches owned stocks and draws
// the same sheet as Create (bench-sheet.js); nothing is saved.
// `ticket` changes whenever the form changes, so a reply that arrives after
// an edit is dropped instead of drawing a sheet for the old values.
const benchSource = { html: "", autoSourceMl: "", ticket: 0, base: null, orderedRows: [], pours: [], costRows: null };

// Cost per row, per bottle and per batch for the whole formula (stock-prices.js).
function showBenchCostBlock() {
  if (typeof showBenchCost !== "function" || !benchSource.costRows) return;
  showBenchCost({ doc: document, container: $("#bench-cost"), rows: benchSource.costRows, bottleMl: benchSource.base?.sizeMl || "" });
}

function benchFieldError(message, field) {
  const error = new Error(message);
  error.fields = [field];
  return error;
}

function syncBenchSourceFields() {
  const pasted = $('#bench-source-form [name="source_kind"]').value === "PASTED";
  $("#bench-project-field").hidden = pasted;
  $("#bench-paste-field").hidden = !pasted;
}

function clearBenchPreview() {
  benchSource.ticket += 1;
  benchSource.html = "";
  benchSource.base = null;
  benchSource.orderedRows = [];
  benchSource.pours = [];
  benchSource.costRows = null;
  $("#bench-cost").hidden = true;
  $("#bench-cost").replaceChildren();
  resetBenchPourForm();
  $("#bench-source-print").disabled = true;
  $("#bench-preview-card").hidden = true;
  $("#bench-preview").replaceChildren();
}

// Fill "Formula is for" from a size in the name, unless Kenny typed his own.
function prefillBenchSourceMl(...texts) {
  const input = $('#bench-source-form [name="source_ml"]');
  const current = input.value.trim();
  if (current && current !== benchSource.autoSourceMl) return;
  const size = benchBottleMl(...texts) || "";
  input.value = size;
  benchSource.autoSourceMl = size;
}

// A size filled in from the old formula's name must not scale a different one.
function dropAutoBenchSourceMl() {
  const input = $('#bench-source-form [name="source_ml"]');
  if (input.value.trim() === benchSource.autoSourceMl) input.value = "";
  benchSource.autoSourceMl = "";
}

function benchSheetSizes(data) {
  const from = String(data.source_ml || "").trim();
  const to = String(data.target_ml || "").trim();
  [[from, "source_ml"], [to, "target_ml"]].forEach(([value, field]) => {
    if (value && (!/^\d+(\.\d+)?$/.test(value) || Number(value) <= 0 || Number(value) > 1000)) {
      throw benchFieldError("Bottle sizes are plain numbers of mL, more than 0 and at most 1000.", field);
    }
  });
  return { from, to };
}

async function loadBenchSource(data) {
  if (data.source_kind === "PASTED") {
    const text = String(data.pasted_text || "");
    if (!text.trim()) throw benchFieldError("Paste a formula table first.", "pasted_text");
    return request("/v2/workbench/formula-text", { method: "POST", body: JSON.stringify({ text }) });
  }
  const path = String(data.project_formula_path || "").trim();
  if (!state.formulaLibrary.some((item) => item.source_path === path)) {
    throw benchFieldError("Choose a project formula from the search list first.", "project_formula_path");
  }
  return request(`/v2/workbench/formula-source?source_path=${encodeURIComponent(path)}`);
}

function drawBenchSheet(sheet) {
  benchSource.html = benchSheetHtml({
    formulaName: sheet.formulaName,
    variantLabel: sheet.variantLabel,
    dateText: new Date().toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }),
    totals: sheet.grams ? benchWeighedTotals(sheet.rows) : benchSeparateTotals(sheet.rows),
    rows: sheet.rows,
    critic: {},
    basketLookup: sheet.lookup,
    notes: sheet.notes,
  });
  $("#bench-preview").innerHTML = benchSource.html;
  // The pour fix works on the rows in the order this sheet prints them.
  benchSource.orderedRows = benchBasketOrder(sheet.rows, sheet.lookup).map((entry) => entry.row);
  const select = $('#bench-pour-form [name="pour_row"]');
  select.replaceChildren(...benchSource.orderedRows.map((row, index) => {
    const planned = benchPlannedPour(row);
    if (!planned || row.pour_target === null) return null;
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${index + 1}. ${row.material} · ${planned.amount} ${planned.unit}${planned.mix ? " of the mix" : ""}`;
    return option;
  }).filter(Boolean));
  $("#bench-pour-form").hidden = !select.options.length;
  $("#bench-pour-undo").hidden = benchSource.pours.length < 2;
}

// Densities at 25 °C for the rows of a source, by material and identity name,
// for a sheet in grams.
async function benchDensities(source) {
  const rows = benchMatchStocks((source.rows || []).map(benchRowFromSource), state.projectInventory).rows;
  const names = [...new Set(rows.flatMap((row) => [row.identity_name, row.material]).map((name) => String(name ?? "").trim()).filter(Boolean))].slice(0, 300);
  if (!names.length) return {};
  const reply = await request("/v2/workbench/material-densities", { method: "POST", body: JSON.stringify({ names }) });
  return reply.densities || {};
}

function renderBenchPreview(source, sizes, densities = null) {
  const rows = (source.rows || []).map(benchRowFromSource);
  if (!rows.length) throw new Error("The formula has no rows the sheet can read.");
  const scaling = sizes.to && compareDecimalText(sizes.to, sizes.from) !== 0;
  const scaled = scaling ? benchScaleRows(rows, sizes.from, sizes.to) : { rows, unscaled: [] };
  const matched = benchMatchStocks(scaled.rows, state.projectInventory);
  const grams = densities ? benchRowsInGrams(matched.rows, densities) : null;
  const start = benchPourStart(grams ? grams.rows : matched.rows);
  benchSource.base = {
    formulaName: source.formula_name,
    variantLabel: scaling ? `${sizes.to} mL` : "",
    sizeMl: (scaling ? sizes.to : sizes.from) || null,
    rows: benchPourSheet(start).rows,
    lookup: benchBasketLookup(state.projectInventory),
    grams: Boolean(grams),
    notes: [
      ...benchSourceNotes({
        scaledFrom: scaling ? sizes.from : null,
        scaledTo: scaling ? sizes.to : null,
        unscaled: scaled.unscaled,
        unmatched: matched.unmatched,
        ambiguous: matched.ambiguous,
        held: matched.held,
        warnings: source.warnings,
      }),
      ...(grams ? benchGramsNotes(grams) : []),
    ],
  };
  // Each pour fix pushes the batch and the sheet it leads to; undo pops one.
  benchSource.pours = [{ state: start, sheet: benchSource.base }];
  drawBenchSheet(benchSource.base);
  benchSource.costRows = matched.rows;
  showBenchCostBlock();
  $("#bench-preview-card").hidden = false;
  $("#bench-source-print").disabled = false;
}

function resetBenchPourForm() {
  const form = $("#bench-pour-form");
  clearFormError(form);
  form.reset();
  $('#bench-pour-form [name="pour_row"]').replaceChildren();
  $("#bench-pour-result").textContent = "";
  $("#bench-pour-undo").hidden = true;
}

$("#bench-pour-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  clearFormError(form);
  $("#bench-pour-result").textContent = "";
  const current = benchSource.pours.at(-1);
  if (!benchSource.base || !current) return;
  try {
    const data = formData(form);
    const index = Number(data.pour_row);
    const fix = benchPourFix(current.state, benchSource.orderedRows, index, data.pour_actual);
    if (fix.kind === "invalid") {
      throw benchFieldError(fix.reason, benchPlannedPour(benchSource.orderedRows[index] || {}) ? "pour_actual" : "pour_row");
    }
    const next = fix.kind === "same" ? null : benchPourSheet(fix.state);
    const text = benchPourFixText(fix, next, benchSource.base.sizeMl);
    if (next) {
      const sheet = {
        ...benchSource.base,
        rows: next.rows,
        variantLabel: `${text.sizeMl ? `${text.sizeMl} mL · ` : ""}still to add`,
        notes: [...text.notes, ...benchSource.base.notes],
      };
      benchSource.pours.push({ state: fix.state, sheet });
      drawBenchSheet(sheet);
      form.reset();
    }
    $("#bench-pour-result").textContent = text.message;
  } catch (error) {
    showFormError(form, error, "No fix yet.");
  }
});
$("#bench-pour-undo").addEventListener("click", () => {
  if (benchSource.pours.length < 2) return;
  benchSource.pours.pop();
  clearFormError($("#bench-pour-form"));
  drawBenchSheet(benchSource.pours.at(-1).sheet);
  $("#bench-pour-result").textContent = benchSource.pours.length === 1 ? "Undone: back to the sheet as first shown." : "Undone: back to the sheet before the last fix.";
});

$('#bench-source-form [name="source_kind"]').addEventListener("change", () => {
  syncBenchSourceFields();
  clearBenchPreview();
});
$('#bench-source-form [name="project_formula_path"]').addEventListener("change", (event) => {
  // Hiding the focused path field (switching to Pasted) blurs it, and the blur
  // fires a late change; that must not refill the size for a pasted formula.
  if ($('#bench-source-form [name="source_kind"]').value === "PASTED") return;
  const selected = state.formulaLibrary.find((item) => item.source_path === event.target.value.trim());
  if (selected) prefillBenchSourceMl(selected.source_path, selected.display_name);
});
$("#bench-source-form").addEventListener("input", (event) => {
  if (["source_kind", "project_formula_path", "pasted_text"].includes(event.target.name)) dropAutoBenchSourceMl();
  clearBenchPreview();
});
$("#bench-source-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.dataset.busy) return;
  const button = form.querySelector('button[type="submit"]');
  clearFormError(form);
  clearBenchPreview();
  const ticket = benchSource.ticket;
  form.dataset.busy = "true";
  button.disabled = true;
  try {
    const data = formData(form);
    const sizes = benchSheetSizes(data);
    const source = await loadBenchSource(data);
    if (ticket !== benchSource.ticket) return;
    if (sizes.to && !sizes.from) {
      sizes.from = benchBottleMl(source.formula_name, source.source_path) || "";
      if (!sizes.from) throw benchFieldError("Say what size the formula is for, so it can be scaled.", "source_ml");
      form.elements.source_ml.value = sizes.from;
      benchSource.autoSourceMl = sizes.from;
    }
    const densities = data.measure_by === "G" ? await benchDensities(source) : null;
    if (ticket !== benchSource.ticket) return;
    renderBenchPreview(source, sizes, densities);
    $("#bench-preview").focus({ preventScroll: false });
  } catch (error) {
    if (ticket === benchSource.ticket) showFormError(form, error, "No sheet yet.");
  } finally {
    delete form.dataset.busy;
    button.disabled = false;
  }
});
$("#bench-source-print").addEventListener("click", () => {
  if (!benchSource.html) return;
  $("#bench-sheet").innerHTML = benchSource.html;
  document.body.classList.add("printing-bench-sheet");
  window.addEventListener("afterprint", () => document.body.classList.remove("printing-bench-sheet"), { once: true });
  window.print();
});
