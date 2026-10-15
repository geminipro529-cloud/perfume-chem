// Batch view: scale one formula card to N bottles, rerun the release gate on
// the scaled card, keep a lot record, add what was really weighed, and print
// the batch sheet. The label and IFRA statement come from batch-label.js.
//
// lab/bottles.js calls attachBatch once. The pure functions below build request bodies
// and plain-data views; the DOM is built with createElement + textContent only,
// never HTML strings, so formula and material names cannot become markup.
// Node loads the same file in the tests through module.exports.

const BATCH_POLL_MS = 2500;
const BATCH_NO_PARENT = "No parent formula is compared: scaling keeps every stock and strength, so only the amounts change.";

function batchText(value) {
  return String(value ?? "").trim();
}

// Plan / gate / record body from the form's values. An empty loss or card
// volume is left out so the server's default (or the "30mL" in the name) applies.
function batchPlanBody(values) {
  const body = { bottles: batchText(values.bottles) || "1", bottle_ml: batchText(values.bottle_ml) || "30" };
  if (values.source_kind === "PASTED") {
    body.text = String(values.pasted_text || "");
    if (batchText(values.name)) body.name = batchText(values.name);
  } else {
    body.source_path = batchText(values.source_path);
  }
  if (batchText(values.loss_percent)) body.loss_percent = batchText(values.loss_percent);
  if (batchText(values.card_total_ml)) body.card_total_ml = batchText(values.card_total_ml);
  return body;
}

function batchUnitLabel(unit) {
  return unit === "uL" ? "µL" : unit;
}

// Rows for the label's ingredient line: µL rows only (the label reads volumes).
function batchLabelRows(plan) {
  return (plan?.rows || []).filter((row) => row.unit === "uL").map((row) => {
    const out = { material: row.material, volume_ul: Number(row.planned_amount) };
    const fraction = Number(row.concentration_fraction_decimal);
    if (row.concentration_fraction_decimal != null && row.concentration_fraction_decimal !== "" && fraction > 0 && fraction <= 1) {
      out.stock_fraction_decimal = fraction;
    }
    return out;
  });
}

function batchGatePath(lot) {
  return `data/user/batches/${batchText(lot)}/gate.json`;
}

// "2026-10-13" -> "10/2026" for the label's Made field.
function batchMonthYear(isoDate) {
  const match = /^(\d{4})-(\d{2})-\d{2}$/.exec(batchText(isoDate));
  return match ? `${match[2]}/${match[1]}` : "";
}

function batchPlanSummary(plan) {
  const lines = [];
  const totals = [];
  if (Number(plan.totals.planned_ul) > 0) totals.push(`${plan.totals.planned_ul} µL`);
  if (Number(plan.totals.planned_mg) > 0) totals.push(`${plan.totals.planned_mg} mg`);
  lines.push(`${plan.formula_name}: ${plan.bottles} × ${plan.bottle_ml} mL with ${plan.loss_percent}% loss allowance makes ${plan.finished_volume_ml} mL.`);
  const source = plan.card_total_ml_source === "formula name" ? " (from the formula name)" : "";
  lines.push(`The card makes ${plan.card_total_ml} mL${source}; every row is multiplied by ${plan.factor}.`);
  if (totals.length) lines.push(`Stocks in total: ${totals.join(" and ")}. Alcohol makes up the rest of the volume.`);
  lines.push(plan.rounding);
  const change = plan.proportionality?.largest_rounding_change_percent;
  lines.push(`Every stock and strength stays as on the card; rounding moves any one row by at most ${change}%.`);
  return lines;
}

// Plain words for one gate-run poll answer.
function batchGateWords(run) {
  if (!run) return { done: false, failed: false, lines: [] };
  if (run.state === "QUEUED" || run.state === "RUNNING") {
    return { done: false, failed: false, lines: [run.state === "QUEUED" ? "Waiting for another gate run to finish…" : "The gate is running on the scaled card. This can take a few minutes.", BATCH_NO_PARENT] };
  }
  if (run.state === "FAILED") {
    return { done: true, failed: true, lines: [`The gate could not finish: ${run.error || "no reason given"}.`] };
  }
  const lines = [`Gate result: ${run.status || "UNKNOWN"}.`];
  const notPass = run.not_pass || [];
  if (!notPass.length) lines.push("Every gate passed.");
  for (const gate of notPass) {
    lines.push(`${gate.gate}: ${gate.status}${gate.detail ? ` — ${gate.detail}` : ""}`);
  }
  lines.push(BATCH_NO_PARENT);
  return { done: true, failed: false, lines };
}

// Actual weighed amounts typed per line; blanks are left out.
function batchActualsBody(typed, notes) {
  const actuals = [];
  for (const [line, value] of typed) {
    const text = batchText(value);
    if (text) actuals.push({ line: Number(line), actual_amount: text });
  }
  return { actuals, notes: batchText(notes) };
}

// Two typed amounts are the same number ("2061" and "2061.0"), or the same text.
function batchSameAmount(a, b) {
  const tidy = (value) => {
    const text = batchText(value);
    if (!/^\d+(\.\d+)?$/.test(text)) return text;
    const [whole, part = ""] = text.split(".");
    const fraction = part.replace(/0+$/, "");
    const integer = whole.replace(/^0+(?=\d)/, "");
    return fraction ? `${integer}.${fraction}` : integer;
  };
  return tidy(a) === tidy(b);
}

// The table's boxes once another device (the phone) has saved amounts since the
// table was filled in: a box left as it was takes the other device's amount, a
// box changed here keeps what was typed. `conflicts` lists the lines both
// changed to different amounts, with the other device's amount.
function batchMergeTyped(baseActuals, serverActuals, typed) {
  const amountOf = (actuals, line) => String((actuals || []).find((item) => item.line === line)?.actual_amount ?? "");
  const values = [];
  const conflicts = [];
  for (const [line, value] of typed) {
    const mine = batchText(value);
    const base = amountOf(baseActuals, Number(line));
    const theirs = amountOf(serverActuals, Number(line));
    if (batchSameAmount(mine, base)) {
      values.push([Number(line), theirs]);
      continue;
    }
    values.push([Number(line), mine]);
    if (!batchSameAmount(theirs, base) && !batchSameAmount(theirs, mine)) conflicts.push({ line: Number(line), theirs });
  }
  return { values, conflicts };
}

// The notes box the same way. A blank box takes the other device's notes too,
// since saving blank notes keeps the saved ones. `conflict` is the other
// device's notes when both changed them.
function batchMergeNotes(baseNotes, serverNotes, typed) {
  const was = batchText(baseNotes);
  const theirs = batchText(serverNotes);
  const mine = batchText(typed);
  if (!mine || mine === was) return { value: theirs, conflict: null };
  return { value: mine, conflict: theirs !== was && theirs !== mine ? theirs : null };
}

function batchMergeWords(lot, conflicts, notesConflict = null) {
  let words = `Another device (the phone, perhaps) saved amounts for lot ${lot} after this table was filled in, so nothing was saved. The table now shows its amounts, with the boxes you changed kept. Check it, then save again.`;
  const both = conflicts.map((item) => `line ${item.line} (the other device saved ${item.theirs || "nothing"})`);
  if (notesConflict !== null) both.push(`the notes (the other device saved ${notesConflict ? `"${notesConflict}"` : "none"})`);
  if (both.length) words += ` Changed on both, with yours kept in the box: ${both.join(", ")}.`;
  return words;
}

// The printable batch sheet as plain data.
function batchSheetView(plan, meta) {
  return {
    title: plan.formula_name,
    facts: [
      ["Lot", batchText(meta.lot) || "________"],
      ["Date", batchText(meta.made_on) || "________"],
      ["Made by", batchText(meta.made_by) || "________"],
      ["Batch", `${plan.bottles} × ${plan.bottle_ml} mL, ${plan.loss_percent}% loss allowance, ${plan.finished_volume_ml} mL in all`],
      ["Scale", `card ${plan.card_total_ml} mL × ${plan.factor}`],
    ],
    head: ["#", "Material", "Strength", "Planned", "Weighed"],
    rows: plan.rows.map((row) => [String(row.line), row.material, row.strength || "", `${row.planned_amount} ${batchUnitLabel(row.unit)}`, ""]),
    note: plan.rounding,
    signature: ["Weighed by", "Checked by"],
  };
}

function attachBatch({ doc, request, root }) {
  if (!root) return null;
  const node = (tag, props = {}, text) => {
    const element = doc.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === "className" || key === "type" || key === "value" || key === "hidden" || key === "disabled" || key === "rows") element[key] = value;
      else element.setAttribute(key, value);
    }
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const field = (title, input, help) => {
    const label = node("label", {}, title);
    if (help) label.append(" ", node("span", {}, help));
    label.append(input);
    return label;
  };
  const state = { plan: null, body: null, runId: null, gateDone: false, record: null, timer: null, ticket: 0 };

  // 1. Source and size
  const planForm = node("form", { className: "panel batch-plan-form", novalidate: "" });
  const kind = node("select", { name: "source_kind" });
  kind.append(node("option", { value: "PROJECT_FILE" }, "Project formula file"), node("option", { value: "PASTED" }, "Paste a formula table"));
  const sourcePath = node("input", { name: "source_path", list: "project-formula-options", placeholder: "Start typing a formula name", autocomplete: "off" });
  const pasted = node("textarea", { name: "pasted_text", rows: 8, maxlength: "200000" });
  const pastedName = node("input", { name: "name", autocomplete: "off", placeholder: "Pasted formula" });
  const bottles = node("input", { name: "bottles", inputmode: "numeric", value: "1", autocomplete: "off" });
  const bottleMl = node("input", { name: "bottle_ml", inputmode: "decimal", value: "30", autocomplete: "off" });
  const loss = node("input", { name: "loss_percent", inputmode: "decimal", placeholder: "3", autocomplete: "off" });
  const cardMl = node("input", { name: "card_total_ml", inputmode: "decimal", placeholder: "from the name", autocomplete: "off" });
  const projectField = field("Project formula", sourcePath);
  const pasteField = field("Formula table", pasted, "a Markdown table with material, strength and amount columns");
  const nameField = field("Name", pastedName);
  pasteField.hidden = true;
  nameField.hidden = true;
  const planButton = node("button", { type: "submit" }, "Plan the batch");
  const planStatus = node("p", { className: "batch-status", role: "status", "aria-live": "polite" });
  planForm.append(
    node("h2", {}, "1. Formula and size"),
    node("div", { className: "field-pair" }, undefined),
  );
  planForm.lastChild.append(field("Formula source", kind), projectField);
  planForm.append(pasteField, nameField);
  const sizes = node("div", { className: "field-pair batch-sizes" });
  sizes.append(field("Bottles", bottles), field("Bottle size", bottleMl, "mL"), field("Loss allowance", loss, "%, empty for the default"), field("Card makes", cardMl, "mL, optional"));
  planForm.append(sizes, node("div", { className: "request-actions" }), planStatus);
  planForm.querySelector(".request-actions").append(planButton);

  // 2. Scaled rows
  const planCard = node("section", { className: "panel batch-plan", hidden: true, "aria-label": "Scaled rows" });
  const summary = node("div", { className: "batch-summary" });
  const tableWrap = node("div", { className: "formula-table-wrap" });
  const warnings = node("ul", { className: "batch-warnings" });
  const printSheet = node("button", { type: "button", className: "quiet-button" }, "Print batch sheet");
  planCard.append(node("h2", {}, "2. Scaled rows"), summary, warnings, tableWrap, printSheet);

  // 3. Lot, gate and record
  const recordForm = node("form", { className: "panel batch-record-form", hidden: true, novalidate: "" });
  const initials = node("input", { name: "initials", autocomplete: "off", maxlength: "4", placeholder: "KS" });
  const suggest = node("button", { type: "button", className: "quiet-button" }, "Suggest a lot number");
  const lot = node("input", { name: "lot", autocomplete: "off", maxlength: "64" });
  const madeBy = node("input", { name: "made_by", autocomplete: "off", maxlength: "120" });
  const madeOn = node("input", { name: "made_on", type: "date" });
  madeOn.value = new Date().toISOString().slice(0, 10);
  const notes = node("textarea", { name: "notes", rows: 3, maxlength: "4000" });
  const gateButton = node("button", { type: "button", className: "quiet-button" }, "Rerun the gate");
  const gateOut = node("div", { className: "batch-gate", role: "status", "aria-live": "polite" });
  const saveButton = node("button", { type: "submit" }, "Save batch record");
  const recordStatus = node("p", { className: "batch-status", role: "status", "aria-live": "polite" });
  const lotRow = node("div", { className: "field-pair" });
  lotRow.append(field("Your initials", initials), field("Lot number", lot));
  const whoRow = node("div", { className: "field-pair" });
  whoRow.append(field("Made by", madeBy), field("Date made", madeOn));
  const gateActions = node("div", { className: "request-actions" });
  gateActions.append(suggest, gateButton);
  const saveActions = node("div", { className: "request-actions" });
  saveActions.append(saveButton);
  recordForm.append(node("h2", {}, "3. Lot, gate and record"), lotRow, whoRow, field("Notes", notes), gateActions, gateOut, saveActions, recordStatus);

  // 4. Actual amounts
  const actualsForm = node("form", { className: "panel batch-actuals-form", hidden: true, novalidate: "" });
  const actualsTable = node("div", { className: "formula-table-wrap" });
  const actualsNotes = node("textarea", { name: "actual_notes", rows: 2, maxlength: "4000" });
  const actualsStatus = node("p", { className: "batch-status", role: "status", "aria-live": "polite" });
  const actualsButton = node("button", { type: "submit" }, "Save weighed amounts");
  actualsForm.append(node("h2", {}, "4. What you really weighed"), node("p", { className: "field-help" }, "Optional. Fill in any rows; blanks are left out."), actualsTable, field("Notes", actualsNotes), actualsButton, actualsStatus);

  root.replaceChildren(planForm, planCard, recordForm, actualsForm);

  const labelArea = doc.getElementById("batch-label-area");
  const label = labelArea && typeof attachBatchLabel === "function" ? attachBatchLabel(labelArea, request) : null;
  const sheet = doc.getElementById("batch-sheet");

  function values() {
    return { source_kind: kind.value, source_path: sourcePath.value, pasted_text: pasted.value, name: pastedName.value, bottles: bottles.value, bottle_ml: bottleMl.value, loss_percent: loss.value, card_total_ml: cardMl.value };
  }

  function syncLabelFields() {
    if (!label || !state.plan) return;
    label.setFields({ name: state.plan.formula_name, lot: lot.value.trim(), mfg: batchMonthYear(madeOn.value), date: madeOn.value, net_ml: state.plan.bottle_ml });
  }

  function stopPolling() {
    if (state.timer) clearTimeout(state.timer);
    state.timer = null;
  }

  function clearPlan() {
    state.ticket += 1;
    stopPolling();
    state.plan = null;
    state.body = null;
    state.runId = null;
    state.gateDone = false;
    planCard.hidden = true;
    recordForm.hidden = true;
    actualsForm.hidden = true;
    gateOut.replaceChildren();
    label?.setRows([]);
    label?.setGate(null);
  }

  function table(head, rows) {
    const element = node("table", { className: "formula-design-table batch-table" });
    const thead = node("thead");
    const headRow = node("tr");
    for (const text of head) headRow.append(node("th", { scope: "col" }, text));
    thead.append(headRow);
    const tbody = node("tbody");
    for (const cells of rows) {
      const tr = node("tr");
      for (const cell of cells) {
        const td = node("td");
        if (cell instanceof doc.defaultView.Node) td.append(cell);
        else td.textContent = cell;
        tr.append(td);
      }
      tbody.append(tr);
    }
    element.append(thead, tbody);
    return element;
  }

  function showPlan(plan) {
    summary.replaceChildren(...batchPlanSummary(plan).map((line) => node("p", {}, line)));
    warnings.replaceChildren(...[...(plan.parse_warnings || []), ...(plan.warnings || [])].map((text) => node("li", {}, text)));
    tableWrap.replaceChildren(table(["#", "Material", "Strength", "On the card", "For this batch"], plan.rows.map((row) => [String(row.line), row.material, row.strength || "", `${row.card_amount} ${batchUnitLabel(row.unit)}`, `${row.planned_amount} ${batchUnitLabel(row.unit)}`])));
    planCard.hidden = false;
    recordForm.hidden = false;
    label?.setRows(batchLabelRows(plan));
    syncLabelFields();
  }

  kind.addEventListener("change", () => {
    const isPasted = kind.value === "PASTED";
    projectField.hidden = isPasted;
    pasteField.hidden = !isPasted;
    nameField.hidden = !isPasted;
  });
  for (const input of [kind, sourcePath, pasted, pastedName, bottles, bottleMl, loss, cardMl]) {
    input.addEventListener("input", () => { if (state.plan) { clearPlan(); planStatus.textContent = "Changed: plan the batch again."; } });
  }
  for (const input of [lot, madeOn]) input.addEventListener("input", syncLabelFields);
  lot.addEventListener("input", () => {
    if (state.runId) {
      stopPolling();
      state.runId = null;
      state.gateDone = false;
      label?.setGate(null);
      gateOut.replaceChildren(node("p", {}, "The lot changed: rerun the gate for this lot."));
    }
  });

  planForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearPlan();
    const ticket = state.ticket;
    const body = batchPlanBody(values());
    planStatus.textContent = "Scaling…";
    planButton.disabled = true;
    try {
      const plan = await request("/v2/batches/plan", { method: "POST", body: JSON.stringify(body) });
      if (ticket !== state.ticket) return;
      state.plan = plan;
      state.body = body;
      showPlan(plan);
      planStatus.textContent = "Planned. Nothing is saved until you save the batch record.";
    } catch (error) {
      planStatus.textContent = error.message || "The batch was not planned.";
    } finally {
      planButton.disabled = false;
    }
  });

  suggest.addEventListener("click", async () => {
    const query = new URLSearchParams({ initials: initials.value.trim(), day: madeOn.value || "" });
    try {
      const answer = await request(`/v2/batches/suggest-lot?${query}`);
      lot.value = answer.lot;
      lot.dispatchEvent(new Event("input"));
    } catch (error) {
      recordStatus.textContent = error.message || "No lot number suggested.";
    }
  });

  function showGate(run) {
    const words = batchGateWords(run);
    gateOut.replaceChildren(...words.lines.map((line, index) => node("p", { className: index === 0 && words.done ? "batch-gate-head" : "" }, line)));
    return words;
  }

  async function poll(runId, ticket) {
    try {
      const run = await request(`/v2/batches/gate-runs/${encodeURIComponent(runId)}`);
      if (ticket !== state.ticket || runId !== state.runId) return;
      const words = showGate(run);
      if (!words.done) {
        state.timer = setTimeout(() => poll(runId, ticket), BATCH_POLL_MS);
        return;
      }
      gateButton.disabled = false;
      state.gateDone = !words.failed;
      if (state.gateDone) label?.setGate({ gate_path: batchGatePath(run.lot) });
    } catch (error) {
      if (ticket !== state.ticket) return;
      gateButton.disabled = false;
      gateOut.replaceChildren(node("p", {}, error.message || "Lost track of the gate run."));
    }
  }

  gateButton.addEventListener("click", async () => {
    if (!state.plan) return;
    if (!lot.value.trim()) {
      gateOut.replaceChildren(node("p", {}, "Type or suggest a lot number first; the gate result is kept under it."));
      return;
    }
    stopPolling();
    const ticket = state.ticket;
    gateButton.disabled = true;
    gateOut.replaceChildren(node("p", {}, "Starting the gate…"));
    try {
      const run = await request("/v2/batches/gate-runs", { method: "POST", body: JSON.stringify({ ...state.body, lot: lot.value.trim() }) });
      if (ticket !== state.ticket) return;
      state.runId = run.run_id;
      showGate(run);
      state.timer = setTimeout(() => poll(run.run_id, ticket), BATCH_POLL_MS);
    } catch (error) {
      gateButton.disabled = false;
      gateOut.replaceChildren(node("p", {}, error.message || "The gate did not start."));
    }
  });

  recordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.plan) return;
    saveButton.disabled = true;
    recordStatus.textContent = "Saving…";
    try {
      const body = { ...state.body, lot: lot.value.trim(), made_on: madeOn.value, made_by: madeBy.value.trim(), notes: notes.value };
      if (state.runId) body.gate_run_id = state.runId;
      const record = await request("/v2/batches", { method: "POST", body: JSON.stringify(body) });
      state.record = record;
      recordStatus.textContent = `Saved lot ${record.lot}.${record.gate ? "" : " No gate result is attached."}`;
      showActuals(record);
    } catch (error) {
      recordStatus.textContent = error.message || "The batch record was not saved.";
    } finally {
      saveButton.disabled = false;
    }
  });

  const actualInputs = new Map();
  function showActuals(record) {
    actualInputs.clear();
    const rows = record.planned_rows.map((row) => {
      const input = node("input", { inputmode: "decimal", autocomplete: "off", "aria-label": `Weighed, line ${row.line}` });
      const done = (record.actuals || []).find((item) => item.line === row.line);
      if (done) input.value = done.actual_amount;
      actualInputs.set(row.line, input);
      return [String(row.line), row.material, `${row.planned_amount} ${batchUnitLabel(row.unit)}`, input];
    });
    actualsTable.replaceChildren(table(["#", "Material", "Planned", "Weighed"], rows));
    actualsNotes.value = record.actual_notes || "";
    actualsForm.hidden = false;
    if (typeof openPhoneBench === "function") {
      const stepByStep = node("button", { type: "button", className: "quiet-button" }, "Weigh it step by step");
      stepByStep.addEventListener("click", () => openPhoneBench(record.lot));
      actualsTable.append(stepByStep);
    }
  }

  // Another device saved since this table was filled in: show its amounts with
  // the boxes changed here kept, and let the person check and save again.
  async function mergeNewerAmounts() {
    const lot = state.record.lot;
    let fresh;
    try {
      fresh = await request(`/v2/batches/${encodeURIComponent(lot)}`);
    } catch (error) {
      actualsStatus.textContent = `Another device saved amounts for lot ${lot} after this table was filled in, so nothing was saved, and its amounts didn't load: ${error.message || "no answer"}`;
      return;
    }
    // The boxes as they are now, with anything typed while the save was on its way.
    const typed = [...actualInputs].map(([line, input]) => [line, input.value]);
    const merged = batchMergeTyped(state.record.actuals, fresh.actuals, typed);
    const notes = batchMergeNotes(state.record.actual_notes, fresh.actual_notes, actualsNotes.value);
    state.record = fresh;
    showActuals(fresh);
    for (const [line, value] of merged.values) {
      const input = actualInputs.get(line);
      if (input) input.value = value;
    }
    actualsNotes.value = notes.value;
    actualsStatus.textContent = batchMergeWords(lot, merged.conflicts, notes.conflict);
  }

  actualsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.record) return;
    const typed = [...actualInputs].map(([line, input]) => [line, input.value]);
    const body = {
      ...batchActualsBody(typed, actualsNotes.value),
      based_on: state.record.actuals_version ?? 0,
      batch_recorded_at: state.record.recorded_at,
    };
    actualsButton.disabled = true;
    try {
      const record = await request(`/v2/batches/${encodeURIComponent(state.record.lot)}/actuals`, { method: "POST", body: JSON.stringify(body) });
      state.record = record;
      actualsStatus.textContent = `Saved ${record.actuals.length} weighed ${record.actuals.length === 1 ? "amount" : "amounts"} for lot ${record.lot}.`;
    } catch (error) {
      if (error.status === 409 && error.code === "BATCH_CHANGED") await mergeNewerAmounts();
      else actualsStatus.textContent = (error.status === 409 && error.serverText) || error.message || "The weighed amounts were not saved.";
    } finally {
      actualsButton.disabled = false;
    }
  });

  printSheet.addEventListener("click", () => {
    if (!state.plan || !sheet) return;
    const view = batchSheetView(state.plan, { lot: lot.value, made_on: madeOn.value, made_by: madeBy.value });
    const facts = node("dl");
    for (const [term, text] of view.facts) {
      const pair = node("div");
      pair.append(node("dt", {}, term), node("dd", {}, text));
      facts.append(pair);
    }
    const signature = node("div", { className: "batch-sheet-signature" });
    for (const line of view.signature) signature.append(node("p", {}, `${line}:`));
    sheet.replaceChildren(node("p", { className: "batch-sheet-kicker" }, "Batch sheet"), node("h1", {}, view.title), facts, table(view.head, view.rows), node("p", { className: "batch-sheet-note" }, view.note), signature);
    doc.body.classList.add("printing-batch-sheet");
    doc.defaultView.addEventListener("afterprint", () => doc.body.classList.remove("printing-batch-sheet"), { once: true });
    doc.defaultView.print();
  });

  return { state };
}

if (typeof module === "object" && module.exports) {
  module.exports = { BATCH_NO_PARENT, batchPlanBody, batchLabelRows, batchGatePath, batchMonthYear, batchPlanSummary, batchGateWords, batchActualsBody, batchSameAmount, batchMergeTyped, batchMergeNotes, batchMergeWords, batchSheetView, attachBatch };
}
