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
  $$('[data-stock-select]').forEach((node) => { node.innerHTML = optionRows(state.stocks, "id"); });
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
bindForm("#version-form", (data) => request(`/formulas/${data.formula_id}/versions`, { method: "POST", body: JSON.stringify({ brief: { identity: data.identity }, constraints: { must_preserve: ["identity"] }, concentration_fraction: Number(data.concentration_fraction), concentration_basis: "mass_fraction" }) }));
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

$("#assistant-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const packet = await request("/assistant", { method: "POST", body: JSON.stringify({ intent: data.intent, subject_id: data.subject_id || null, facts: {}, calculations: {}, evidence: {} }) });
    $("#assistant-output").textContent = JSON.stringify(packet, null, 2); notify(`Packet ${packet.payload_sha256.slice(0, 10)} built.`);
  } catch (error) { notify(error.message, true); }
});

navigate(location.hash.slice(1) || "dashboard");
refresh().catch((error) => notify(error.message, true));
