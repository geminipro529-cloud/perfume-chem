"use strict";

const API = "/api/v1/lab";
const state = { materials: [], stocks: [], formulas: [], bottles: [], experiments: [] };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function notify(message, error = false) {
  const node = $("#status");
  node.textContent = message;
  node.classList.toggle("is-error", error);
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function optionRows(rows, labelKey) {
  if (!rows.length) return '<option value="">Create a record first</option>';
  return rows.map((row) => `<option value="${escapeHtml(row.id)}">${escapeHtml(row[labelKey] || row.id)}</option>`).join("");
}

function stockOptionRows() {
  if (!state.stocks.length) return '<option value="">Create a stock first</option>';
  return state.stocks.map((stock) => {
    const material = state.materials.find((item) => item.id === stock.material_id);
    const name = material?.canonical_name || stock.material_id;
    const dilution = `${(Number(stock.active_fraction) * 100).toFixed(3).replace(/\.?0+$/, "")}%`;
    return `<option value="${escapeHtml(stock.id)}">${escapeHtml(name)} | ${escapeHtml(dilution)}</option>`;
  }).join("");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function recordList(target, rows, titleKey, detail) {
  $(target).innerHTML = rows.length
    ? rows.map((row) => `<div class="record-row"><strong>${escapeHtml(row[titleKey] || "Record")}</strong><span>${escapeHtml(detail(row))}</span><code>${escapeHtml(row.id)}</code></div>`).join("")
    : '<p class="empty">No records yet.</p>';
}

function updateSelectors() {
  $$('[data-material-select]').forEach((node) => { node.innerHTML = optionRows(state.materials, "canonical_name"); });
  $$('[data-stock-select]').forEach((node) => { node.innerHTML = stockOptionRows(); });
  $$('[data-formula-select]').forEach((node) => { node.innerHTML = optionRows(state.formulas, "name"); });
  $$('[data-bottle-select]').forEach((node) => { node.innerHTML = optionRows(state.bottles, "label"); });
  $$('[data-experiment-select]').forEach((node) => { node.innerHTML = optionRows(state.experiments, "name"); });
}

async function refresh() {
  const [dashboard, materials, stocks, formulas, bottles, experiments] = await Promise.all([
    request("/dashboard"), request("/materials"), request("/stocks"), request("/formulas"), request("/bottles"), request("/experiments"),
  ]);
  Object.assign(state, { materials, stocks, formulas, bottles, experiments });
  $("#dashboard-counts").innerHTML = Object.entries(dashboard.counts).map(([label, value]) => `<article class="metric"><strong>${value}</strong><span>${escapeHtml(label)}</span></article>`).join("");
  $("#dashboard-warnings").innerHTML = dashboard.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  recordList("#material-list", materials, "canonical_name", (row) => row.cas_number || "No CAS recorded");
  recordList("#formula-list", formulas, "name", () => "Immutable versions are appended separately");
  recordList("#bottle-list", bottles, "label", (row) => row.status);
  recordList("#experiment-list", experiments, "name", (row) => row.status);
  updateSelectors();
  notify("Ledger refreshed.");
}

function navigate(view) {
  $$(".nav-item").forEach((item) => item.classList.toggle("is-active", item.dataset.view === view));
  $$(".view").forEach((panel) => panel.classList.toggle("is-visible", panel.dataset.panel === view));
  history.replaceState(null, "", `#${view}`);
  const heading = $(`[data-panel="${view}"] h1`);
  if (heading) heading.focus?.({ preventScroll: true });
  if (view === "science") {
    loadScienceAuthority().catch((error) => notify(error.message, true));
  }
}

function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
function bindForm(selector, handler) {
  $(selector).addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await handler(formData(event.currentTarget)); notify("Record committed."); await refresh(); }
    catch (error) { notify(error.message, true); }
  });
}

$$('.nav-item').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));
$("#refresh-all").addEventListener("click", () => refresh().catch((error) => notify(error.message, true)));

$("#backup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const result = await request("/backups", { method: "POST", body: JSON.stringify(data) });
    $("#backup-output").textContent = JSON.stringify(result, null, 2);
    $("#stage-restore-form [name=snapshot_path]").value = result.snapshot_path;
    notify("Verified backup created.");
  } catch (error) { notify(error.message, true); }
});

$("#stage-restore-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const result = await request("/restores/stage", { method: "POST", body: JSON.stringify(data) });
    $("#backup-output").textContent = JSON.stringify(result, null, 2);
    notify("Restore validated and staged. Replacement still requires stopped-server maintenance.");
  } catch (error) { notify(error.message, true); }
});

$("#export-workspace").addEventListener("click", async () => {
  try {
    const result = await request("/export");
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "perfume-chem-lab-export.json";
    link.click();
    URL.revokeObjectURL(link.href);
    $("#backup-output").textContent = `Exported ${Object.keys(result.tables).length} ordered tables.`;
    notify("Workspace export prepared.");
  } catch (error) { notify(error.message, true); }
});

bindForm("#material-form", (data) => request("/materials", { method: "POST", body: JSON.stringify(data) }));
bindForm("#stock-form", (data) => request("/stocks", { method: "POST", body: JSON.stringify({ ...data, active_fraction: Number(data.active_fraction), initial_mass_g: Number(data.initial_mass_g), density_g_ml: data.density_g_ml ? Number(data.density_g_ml) : null }) }));
bindForm("#formula-form", (data) => request("/formulas", { method: "POST", body: JSON.stringify(data) }));

function componentRows() {
  const rows = $$('[data-component-row]', $("#component-editor"));
  if (!rows.length) throw new Error("Add at least one stock component.");
  return rows.map((row) => {
    const stock = $('[name="component_stock"]', row).value;
    const mass = Number($('[name="component_mass_g"]', row).value);
    const volumeValue = $('[name="component_volume_ul"]', row).value;
    const volume = volumeValue ? Number(volumeValue) : null;
    if (!stock || !Number.isFinite(mass) || mass <= 0) {
      throw new Error("Every component needs a stock and a positive mass.");
    }
    if (volume !== null && (!Number.isFinite(volume) || volume <= 0)) {
      throw new Error("Component volume must be blank or a positive number.");
    }
    return {
      stock_solution_id: stock,
      requested_mass_g: mass,
      requested_volume_ul: volume,
      role: $('[name="component_role"]', row).value || null,
      unit: "g",
    };
  });
}

$("#add-component-row").addEventListener("click", () => {
  const source = $('[data-component-row]', $("#component-editor"));
  const row = source.cloneNode(true);
  $('[name="component_mass_g"]', row).value = "0.1";
  $('[name="component_volume_ul"]', row).value = "";
  $('[name="component_role"]', row).value = "";
  $("#component-editor").append(row);
  const stockSelect = $('[name="component_stock"]', row);
  stockSelect.innerHTML = stockOptionRows();
  stockSelect.selectedIndex = 0;
});

$("#component-editor").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-component]");
  if (!button) return;
  const rows = $$('[data-component-row]', $("#component-editor"));
  if (rows.length === 1) {
    notify("A formula version needs at least one component.", true);
    return;
  }
  button.closest("[data-component-row]").remove();
});

$("#version-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    await request(`/formulas/${data.formula_id}/versions`, {
      method: "POST",
      body: JSON.stringify({
        brief: { identity: data.identity },
        constraints: { must_preserve: ["identity"] },
        concentration_fraction: Number(data.concentration_fraction),
        concentration_basis: "mass_fraction",
        components: componentRows(),
      }),
    });
    notify("Immutable formula version committed.");
    await refresh();
  } catch (error) { notify(error.message, true); }
});
bindForm("#bottle-form", (data) => request("/bottles", { method: "POST", body: JSON.stringify({ label: data.label, initial_mass_g: Number(data.initial_mass_g) }) }));
bindForm("#addition-form", (data) => request(`/bottles/${data.bottle_id}/additions`, { method: "POST", body: JSON.stringify({ stock_solution_id: data.stock_solution_id, mass_g: Number(data.mass_g), expected_sequence: Number(data.expected_sequence), command_id: crypto.randomUUID() }) }));
bindForm("#experiment-form", (data) => request("/experiments", { method: "POST", body: JSON.stringify({ name: data.name, protocol: { observation_times_seconds: data.times.split(",").map((item) => Number(item.trim())) } }) }));

$("#sample-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const row = await request(`/experiments/${data.experiment_id}/samples`, { method: "POST", body: JSON.stringify({ bottle_id: data.bottle_id, blind_code: data.blind_code }) });
    $("#latest-sample").value = row.id; notify("Blind sample recorded.");
  } catch (error) { notify(error.message, true); }
});

$("#application-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const row = await request("/applications", { method: "POST", body: JSON.stringify({ sample_id: data.sample_id, applied_at: new Date().toISOString(), dose: { mass_mg: Number(data.mass_mg) }, context: { substrate: "blotter" } }) });
    $("#latest-application").value = row.id; notify("Application recorded.");
  } catch (error) { notify(error.message, true); }
});

bindForm("#observation-form", (data) => request(`/applications/${data.application_id}/observations`, { method: "POST", body: JSON.stringify({ elapsed_seconds: Number(data.elapsed_seconds), observations: { note: data.observation } }) }));
bindForm("#outcome-form", (data) => request("/outcomes", { method: "POST", body: JSON.stringify({ experiment_id: data.experiment_id, prediction_id: null, outcome: { note: data.outcome } }) }));

$("#analysis-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const result = await request("/analysis", { method: "POST", body: JSON.stringify({ name: data.name, total_volume_ml: 10, concentration_percent: 20, ingredients: [{ name: data.material, percentage: 100, stock_active_fraction: 1, stock_fraction_basis: "volume_fraction" }] }) });
    $("#analysis-output").textContent = JSON.stringify(result, null, 2); notify("Evidence analysis complete.");
  } catch (error) { notify(error.message, true); }
});

$("#hypothesis-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  const splitValues = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
  try {
    const result = await request("/intervention-hypotheses", {
      method: "POST",
      body: JSON.stringify({
        brief_name: data.brief_name,
        observations: splitValues(data.observations),
        family: data.family || null,
        profile: null,
        mode: data.mode,
        forbidden_materials: splitValues(data.forbidden_materials),
        limit: Number(data.limit),
      }),
    });
    $("#hypothesis-output").textContent = JSON.stringify(result, null, 2);
    notify(`${result.hypotheses.length} inventory-valid hypotheses generated.`);
  } catch (error) { notify(error.message, true); }
});

$("#trial-plan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const result = await request("/intervention-trials/plan", {
      method: "POST",
      body: JSON.stringify({
        brief_name: data.brief_name,
        material: data.material,
        bottle_total_mass_g: Number(data.bottle_total_mass_g),
        current_material_active_mass_g: Number(data.current_material_active_mass_g),
        stock_active_mass_fraction: Number(data.stock_active_mass_fraction),
        stock_density_g_ml: data.stock_density_g_ml ? Number(data.stock_density_g_ml) : null,
        target_active_ppm_w_w: Number(data.target_active_ppm_w_w),
        threshold_matrix: data.threshold_matrix,
        pipette: {
          minimum_ul: Number(data.pipette_minimum_ul),
          increment_ul: Number(data.pipette_increment_ul),
          maximum_single_step_ul: Number(data.pipette_maximum_ul),
          standard_uncertainty_ul: 0,
          systematic_standard_uncertainty_ul: 0,
        },
        evaluation_attribute: data.evaluation_attribute,
        evaluation_times_seconds: data.evaluation_times_seconds.split(",").map((item) => Number(item.trim())),
      }),
    });
    $("#trial-plan-output").textContent = JSON.stringify(result, null, 2);
    notify(`Trial planned at ${result.achieved_active_ppm_w_w.toFixed(3)} ppm w/w.`);
  } catch (error) { notify(error.message, true); }
});

$("#assistant-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const packet = await request("/assistant", { method: "POST", body: JSON.stringify({ intent: data.intent, subject_id: data.subject_id || null, facts: {}, calculations: {}, evidence: {} }) });
    $("#assistant-output").textContent = JSON.stringify(packet, null, 2); notify(`Packet ${packet.payload_sha256.slice(0, 10)} built.`);
  } catch (error) { notify(error.message, true); }
});

function scienceEvidenceClass(label) {
  return `evidence-${String(label || "UNKNOWN").toLowerCase().replaceAll("_", "-")}`;
}

function scienceRecordCard(record, disposition) {
  const card = document.createElement("article");
  card.className = `science-record science-record-${disposition}`;

  const heading = document.createElement("div");
  heading.className = "science-record-heading";
  const identifier = document.createElement("code");
  identifier.textContent = record.id;
  const badge = document.createElement("span");
  badge.className = `evidence ${scienceEvidenceClass(record.evidence_class)}`;
  badge.dataset.evidenceClass = record.evidence_class;
  badge.textContent = record.evidence_class;
  heading.append(identifier, badge);
  card.append(heading);

  const eligibility = document.createElement("p");
  eligibility.className = "science-eligibility";
  eligibility.textContent = record.strict_eligible
    ? "Strict eligible"
    : "Not strict eligible";
  card.append(eligibility);

  if (record.strict_reason_codes.length) {
    const reasons = document.createElement("ul");
    reasons.className = "science-reasons";
    for (const reason of record.strict_reason_codes) {
      const item = document.createElement("li");
      item.textContent = reason;
      reasons.append(item);
    }
    card.append(reasons);
  }

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Authority, provenance, and facts";
  const payload = document.createElement("pre");
  payload.textContent = JSON.stringify({
    created_at: record.created_at,
    authority: record.authority,
    provenance: record.provenance,
    facts: record.facts,
  }, null, 2);
  details.append(summary, payload);
  card.append(details);
  return card;
}

function scienceRecordGroup(label, records, disposition) {
  const group = document.createElement("section");
  group.className = `science-record-group science-record-group-${disposition}`;
  const heading = document.createElement("h3");
  heading.textContent = `${label} (${records.length})`;
  group.append(heading);
  if (!records.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No records in this partition.";
    group.append(empty);
    return group;
  }
  for (const record of records) {
    group.append(scienceRecordCard(record, disposition));
  }
  return group;
}

function renderScienceAuthority(report) {
  const totals = [
    ["Sections", report.totals.section_count],
    ["Records", report.totals.total_records],
    ["Included", report.totals.included_records],
    ["Withheld", report.totals.withheld_records],
  ];
  const summaryFragment = document.createDocumentFragment();
  for (const [label, value] of totals) {
    const metric = document.createElement("article");
    metric.className = "metric";
    const count = document.createElement("strong");
    count.textContent = value;
    const name = document.createElement("span");
    name.textContent = label;
    metric.append(count, name);
    summaryFragment.append(metric);
  }
  $("#science-summary").replaceChildren(summaryFragment);

  const fragment = document.createDocumentFragment();
  for (const section of report.sections) {
    const panel = document.createElement("article");
    panel.className = "panel science-section";
    const heading = document.createElement("div");
    heading.className = "science-section-heading";
    const title = document.createElement("h2");
    title.textContent = section.label;
    const counts = document.createElement("span");
    counts.textContent = `${section.total_count} total`;
    heading.append(title, counts);
    panel.append(heading);
    panel.append(scienceRecordGroup("Included", section.included, "included"));
    panel.append(scienceRecordGroup("Strict withheld", section.withheld, "withheld"));
    fragment.append(panel);
  }
  const scienceSections = $("#science-sections");
  scienceSections.replaceChildren(fragment);
}

async function loadScienceAuthority() {
  const view = $("#science-view-mode").value;
  const report = await request(`/science/authority?view=${view}`);
  $("#science-json-download").href = `/api/v1/lab/science/authority?view=${view}`;
  $("#science-markdown-download").href = `/api/v1/lab/science/report.md?view=${view}`;
  renderScienceAuthority(report);
  notify(`${report.totals.total_records} science authority records loaded in ${view} view.`);
}

$("#science-view-mode").addEventListener("change", () => {
  loadScienceAuthority().catch((error) => notify(error.message, true));
});
$("#science-refresh").addEventListener("click", () => {
  loadScienceAuthority().catch((error) => notify(error.message, true));
});

navigate(location.hash.slice(1) || "dashboard");
refresh().catch((error) => notify(error.message, true));
