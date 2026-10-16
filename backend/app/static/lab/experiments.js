"use strict";

// Experiments page: experiments, blind samples, applications, outcomes and the one-change comparison.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, search, boot.

bindForm("#experiment-form", (data) => request("/experiments", { method: "POST", body: JSON.stringify({ name: data.name, protocol: { observation_times_seconds: data.times.split(",").map((item) => Number(item.trim())) } }) }));

const OMISSION_BASIS = { mass_fraction: "w/w", volume_fraction: "v/v", mass_per_volume: "w/v", "w/w": "w/w", "v/v": "v/v", "w/v": "w/v", neat: "neat" };
function omissionBasis(value) { return OMISSION_BASIS[value] || "unknown"; }
function omissionStrength(row) {
  if (row.fraction_basis === "neat") return "neat";
  const fraction = Number(row.stock_fraction_decimal);
  if (row.stock_fraction_decimal == null || row.stock_fraction_decimal === "" || !Number.isFinite(fraction)) return `strength unknown (${row.fraction_basis})`;
  return `${Number((fraction * 100).toPrecision(6))}% ${row.fraction_basis}`;
}

function loadOmissionRows(rows) {
  if (!Array.isArray(rows) || rows.length < 2 || rows.length > 60) throw new Error("Load two to sixty exact control rows.");
  const fields = ["stock_id", "identity_name", "amount_decimal", "amount_unit", "stock_fraction_decimal", "fraction_basis", "carrier"];
  state.omissionRows = rows.map((row) => {
    const loaded = Object.fromEntries(fields.map((field) => [field, row[field] ?? null]));
    loaded.fraction_basis = omissionBasis(loaded.fraction_basis);
    return loaded;
  });
  const choices = $("#omission-stock-choices");
  choices.replaceChildren();
  state.omissionRows.forEach((row) => {
    const block = document.createElement("div");
    const title = document.createElement("p");
    title.textContent = `${row.identity_name}: ${row.amount_decimal} ${row.amount_unit} · ${omissionStrength(row)}`;
    block.append(title);
    [["omit", "Omit in the comparison"], ["protect", "Keep this stock fixed"]].forEach(([kind, label]) => {
      const line = document.createElement("label");
      line.className = "check-line";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox"; checkbox.dataset.omissionKind = kind; checkbox.value = row.stock_id;
      line.append(checkbox, document.createTextNode(label)); block.append(line);
    });
    choices.append(block);
  });
  const doseSelect = $('[name="dose_stock_id"]', $("#omission-plan-form"));
  doseSelect.replaceChildren(...state.omissionRows.map((row) => {
    const option = document.createElement("option");
    option.value = row.stock_id;
    option.textContent = `${row.identity_name}: ${row.amount_decimal} ${unitLabel(row.amount_unit)}`;
    return option;
  }));
  applyChangeKind();
}

const unitLabel = (unit) => (unit === "uL" ? "µL" : unit);

function selectedChangeKind() {
  return $('[name="change_kind"]:checked', $("#omission-plan-form"))?.value || "OMISSION";
}

function applyChangeKind() {
  const kind = selectedChangeKind();
  const toggle = (selector, on) => { const node = $(selector); node.hidden = !on; node.disabled = !on; };
  toggle("#change-addition-fields", kind === "ADDITION");
  toggle("#change-dose-fields", kind === "DOSE_STEP");
  toggle("#change-shared-fields", kind !== "OMISSION");
  $$("[data-omission-kind]", $("#omission-stock-choices")).forEach((box) => { box.closest("label").hidden = kind !== "OMISSION"; });
  const rows = state.omissionRows;
  const help = $("#omission-input-help");
  if (!rows.length) {
    help.textContent = "Exact mg and w/w inputs are required only for this quantitative comparison. Volumes are never silently converted to masses.";
  } else if (kind !== "OMISSION") {
    help.textContent = "One row changes; every other row keeps its amount. Each amount stays in its own unit (µL or mg); nothing is converted.";
  } else {
    help.textContent = rows.every((r) => r.amount_unit === "mg" && r.fraction_basis === "w/w")
      ? "Choose a mobile ingredient to omit; protect recognizers you want kept. Stock identity is supplied evidence, not independently verified."
      : "These rows lack a common mg / w/w basis. The quantitative plan will hold; you can still record a simple personal observation below. No density is guessed.";
  }
}

function changeRequest(kind, data) {
  const shared = data.bottle_volume_ul_decimal ? { bottle_volume_ul_decimal: data.bottle_volume_ul_decimal.trim() } : {};
  if (kind === "ADDITION") {
    return { kind, row: {
      stock_id: data.add_stock_id.trim(), identity_name: data.add_identity_name.trim(),
      amount_decimal: data.add_amount_decimal.trim(), amount_unit: data.add_amount_unit,
      stock_fraction_decimal: data.add_stock_fraction_decimal.trim(), fraction_basis: data.add_fraction_basis,
      carrier: data.add_carrier.trim() || null,
    }, ...shared };
  }
  if (!data.dose_stock_id) throw new Error("Load a control and choose the row to step.");
  return { kind, stock_id: data.dose_stock_id, direction: data.dose_direction,
    step_decimal: data.dose_step_decimal.trim(), ...shared };
}

function textNode(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function stepList(steps) {
  const list = document.createElement("ol");
  (steps || []).forEach((step) => list.append(textNode("li", step)));
  return list;
}

function triangleSheet(sheet) {
  const block = document.createElement("div");
  block.append(textNode("h3", "Triangle test sheet"),
    textNode("p", `${sheet.tries} tries · at least ${sheet.min_correct} right to count as a real difference.`),
    stepList(sheet.steps), textNode("p", sheet.reading), textNode("p", sheet.blinding_note, "field-help"));
  return block;
}

function oneChangeView(handoff) {
  const plan = handoff.one_change_plan;
  const row = plan.changed_row;
  const how = handoff.how_to_try;
  const block = document.createElement("div");
  const unit = unitLabel(row.amount_unit);
  block.append(textNode("h3", "What changes"),
    textNode("p", `${row.stock}: ${row.control_amount_decimal} ${unit} in the control → ${row.variant_amount_decimal} ${unit} in the variant.`));
  if (plan.carrier_blank) {
    const blank = plan.carrier_blank;
    block.append(textNode("p", `Carrier blank for the variant: ${blank.amount_decimal} ${unitLabel(blank.amount_unit)} of ${blank.carrier} (stock ${blank.stock_id}), so both vials hold the same total.`));
  }
  block.append(textNode("p", plan.limitation, "field-help"), textNode("h3", "How to try it"));
  if (how.method === "SPLIT_VIAL") {
    const split = how.split_vial;
    block.append(textNode("p", `Split vial: ${split.split_ul} µL into a ${split.vial_ul.toLocaleString("en-US")} µL vial now; ${split.main_bottle_ul} µL into the main bottle only if you prefer the vial.`),
      textNode("p", split.note, "field-help"), stepList(split.steps));
  } else if (how.method === "BLOTTER_PREVIEW") {
    block.append(textNode("p", "Blotter preview:"), stepList(how.blotter_preview.steps),
      textNode("p", how.blotter_preview.note, "field-help"));
  } else if (how.method === "FRESH_VIALS") {
    block.append(textNode("p", "Fresh vials:"), stepList(how.fresh_vials.steps));
  }
  if (how.why_no_split) block.append(textNode("p", how.why_no_split, "field-help"));
  return block;
}

$("#omission-load-design").addEventListener("click", () => {
  try {
    const result = state.formulaChat.result;
    const rows = result?.design_variants?.[state.formulaChat.variantIndex]?.formula?.rows || result?.optimized_formula?.rows;
    if (!rows) throw new Error("Create or select a Formula Studio design first.");
    loadOmissionRows(rows);
  } catch (error) { notify(error.message, true); }
});
$("#omission-load-rows").addEventListener("click", () => {
  try { loadOmissionRows(JSON.parse($('[name="control_rows_json"]', $("#omission-plan-form")).value)); }
  catch (error) { notify(error.message, true); }
});
$$('[name="change_kind"]', $("#omission-plan-form")).forEach((radio) => radio.addEventListener("change", applyChangeKind));
$("#omission-plan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('button[type="submit"]', form);
  button.disabled = true;
  try {
    const data = formData(form);
    const kind = selectedChangeKind();
    const selected = (box) => $$(`[data-omission-kind="${box}"]:checked`, form).map((node) => node.value);
    const blanks = data.blank_carrier && data.blank_stock_id
      ? { [data.blank_carrier]: { stock_id: data.blank_stock_id, carrier: data.blank_carrier } } : {};
    let payload;
    if (kind === "OMISSION") {
      if (!state.omissionRows.length || !selected("omit").length) throw new Error("Load a control and choose the material to omit.");
      payload = { schema_version: "omission-comparison-plan-request-v1", control_rows: state.omissionRows,
        omit_stock_ids: selected("omit"), protected_stock_ids: selected("protect"), carrier_blanks: blanks,
        goal: data.goal, mode: data.mode, seed: 17 };
    } else {
      if (!state.omissionRows.length) throw new Error("Load a control before planning a change.");
      payload = { schema_version: "omission-comparison-plan-request-v1", control_rows: state.omissionRows,
        change: changeRequest(kind, data), carrier_blanks: kind === "DOSE_STEP" && data.dose_direction === "DOWN" ? blanks : {},
        triangle_tries: Number(data.triangle_tries) || 6, goal: data.goal, mode: data.mode, seed: 17 };
    }
    $("#omission-plan-output").replaceChildren();
    let submitted;
    try {
      submitted = await request("/v2/engine-jobs", { method: "POST", body: JSON.stringify({
        schema_version: "lab-engine-job-request-v2", job_type: "OMISSION_COMPARISON_PLAN",
        requester: "omission-planning-ui", idempotency_key: newRequestId("comparison"), payload,
      }) });
    } catch (error) {
      if (error.status === 400) {
        const message = textNode("p", `The plan request was not accepted: ${error.message}`, "field-help");
        message.style.whiteSpace = "pre-line";
        $("#omission-plan-output").append(message);
      }
      throw error;
    }
    const completed = await waitForEngineJob(submitted.id, {
      area: $("#omission-plan-output"),
      intervalMs: 500,
      stillRunningMessage: `Planning job ${submitted.id} is still running. It remains available without resubmitting.`,
    });
    const handoff = completed.result?.result?.result;
    if (!handoff?.omission_plan && !handoff?.one_change_plan) throw new Error(`Planning job ${submitted.id}: ${completed.state}. It remains available without resubmitting.`);
    const output = $("#omission-plan-output"); output.replaceChildren();
    const summary = document.createElement("p");
    const goalText = data.goal.trim();
    const goalSentence = /[.?!]$/.test(goalText) ? goalText : `${goalText}.`;
    if (handoff.one_change_plan) {
      summary.textContent = `Comparison proposed: ${goalSentence} Only one row changes. Nothing was compounded, reserved, or evaluated. This is not yet an executable blind session.`;
    } else {
      summary.textContent = handoff.omission_plan.state === "CONTROLLED_OMISSION_DESIGN_READY"
        ? `Comparison proposed: ${goalSentence} Retained doses unchanged. Nothing was compounded, reserved, or evaluated. This is not yet an executable blind session.`
        : `Quantitative comparison withheld: ${(handoff.omission_plan.reason_codes || []).join(", ")}. You may still use the ordinary observation form.`;
    }
    output.append(summary);
    if (handoff.one_change_plan) output.append(oneChangeView(handoff));
    if (handoff.triangle_test) output.append(triangleSheet(handoff.triangle_test));
    const details = document.createElement("details"); const heading = document.createElement("summary");
    heading.textContent = "Exact planning receipt"; const receipt = document.createElement("pre");
    receipt.textContent = JSON.stringify(handoff, null, 2); details.append(heading, receipt); output.append(details);
    notify("Comparison planning finished. No bottle or inventory changes.");
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
});

bindSavingForm("#sample-form", async (data, form, saved) => {
  const row = await request(`/experiments/${data.experiment_id}/samples`, { method: "POST", body: JSON.stringify({ bottle_id: data.bottle_id, blind_code: data.blind_code }) });
  saved();
  $("#latest-sample").value = row.id; notify("Blind sample recorded.");
});

bindSavingForm("#application-form", async (data, form, saved) => {
  const row = await request("/applications", { method: "POST", body: JSON.stringify({ sample_id: data.sample_id, applied_at: new Date().toISOString(), dose: { mass_mg: Number(data.mass_mg) }, context: { substrate: "blotter" } }) });
  saved();
  $("#latest-application").value = row.id; notify("Application recorded.");
});

bindForm("#observation-form", (data) => request(`/applications/${encodeURIComponent(String(data.application_id).trim())}/observations`, { method: "POST", body: JSON.stringify({ elapsed_seconds: Number(data.elapsed_seconds), observations: { note: data.observation } }) }));
bindForm("#outcome-form", (data) => request("/outcomes", { method: "POST", body: JSON.stringify({ experiment_id: data.experiment_id, prediction_id: null, outcome: { note: data.outcome } }) }));
