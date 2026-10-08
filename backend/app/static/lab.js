"use strict";

const API = "/api/v1/lab";
const state = {
  materials: [],
  stocks: [],
  projectInventory: { stocks: [], counts: {} },
  formulas: [],
  formulaLibrary: [],
  bottles: [],
  experiments: [],
  omissionRows: [],
  formulaChat: {
    messages: [],
    result: null,
    variantIndex: 0,
  },
  improve: {
    jobId: null,
    pollCancelled: false,
    sourceKind: null,
    sourceId: null,
    sourceRows: [],
    sourceMetadata: null,
    analysis: null,
    selectedHypothesis: null,
    selectedVariant: "low_variant",
    preparedLines: [],
    additionEvents: [],
    evaluationCommandId: null,
    evaluationRequestBody: null,
  },
};
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
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
      : payload.detail;
    const error = new Error(payload?.error?.message || detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
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
  const preferredFormula = state.improve.sourceKind === "formula" ? state.improve.sourceId : null;
  const preferredBottle = state.improve.sourceKind === "bottle" ? state.improve.sourceId : null;
  $$('[data-material-select]').forEach((node) => { node.innerHTML = optionRows(state.materials, "canonical_name"); });
  $$('[data-stock-select]').forEach((node) => { node.innerHTML = stockOptionRows(); });
  $$('[data-formula-select]').forEach((node) => { node.innerHTML = optionRows(state.formulas, "name"); });
  $$('[data-bottle-select]').forEach((node) => { node.innerHTML = optionRows(state.bottles, "label"); });
  $$('[data-experiment-select]').forEach((node) => { node.innerHTML = optionRows(state.experiments, "name"); });
  $("#project-formula-options").innerHTML = state.formulaLibrary.map((source) => (
    `<option value="${escapeHtml(source.source_path)}">${escapeHtml(source.display_name)}</option>`
  )).join("");
  if (preferredFormula) $$('[data-formula-select]').forEach((node) => { if ([...node.options].some((option) => option.value === preferredFormula)) node.value = preferredFormula; });
  if (preferredBottle) $$('[data-bottle-select]').forEach((node) => { if ([...node.options].some((option) => option.value === preferredBottle)) node.value = preferredBottle; });
}

function renderProjectInventory(filter = "") {
  const inventory = state.projectInventory || { stocks: [], counts: {} };
  const query = String(filter || "").trim().toLowerCase();
  const incompleteOnly = Boolean($("#project-inventory-incomplete-only")?.checked);
  const rows = (inventory.stocks || []).filter((stock) => {
    if (incompleteOnly && stock.design_ready) return false;
    if (!query) return true;
    return [stock.material, stock.identity_name, stock.normalized_identity, stock.stock_label, stock.category, stock.carrier]
      .some((value) => String(value || "").toLowerCase().includes(query));
  });
  const counts = inventory.counts || {};
  $("#project-inventory-count").textContent = `${counts.stocks || 0} current stock entries`;
  $("#project-inventory-ready").textContent = `${counts.design_ready || counts.execution_ready || 0} ready for design · ${counts.live_inventory_text || 0} recovered from the live list · ${counts.personal_additions || 0} personal additions`;
  $("#project-inventory-source").textContent = `${inventory.display_source || "Current project inventory"}. Effective version ${String(inventory.effective_inventory_sha256 || inventory.snapshot_sha256 || "unknown").slice(0, 12)}…`;
  $("#project-inventory-list").innerHTML = rows.length
    ? rows.map((stock) => {
      const carrier = stock.carrier ? ` in ${stock.carrier}` : "";
      const form = stock.physical_form ? ` · ${stock.physical_form}` : "";
      const stateLabel = stock.design_ready
        ? (stock.execution_ready ? "Ready for design" : "Ready for personal design · physical records separate")
        : "Owned · details incomplete";
      const missing = (stock.missing_fields || []).map((field) => humanize(field)).join(", ");
      const completion = !stock.design_ready && stock.completion_available
        ? `<button class="inventory-complete-button quiet-button" type="button" data-complete-stock="${escapeHtml(stock.stock_id)}">Complete details</button>`
        : "";
      const sourceLabel = stock.source_class === "LIVE_INVENTORY_TEXT"
        ? "Recovered from inventory.txt"
        : (stock.source_class === "PERSONAL_ADDITION" ? "Your direct addition" : "Governed stock record");
      return `<article class="inventory-item">
        <div><strong>${escapeHtml(stock.identity_name)}</strong><span>${escapeHtml(stock.category || "uncategorized")}</span></div>
        <p>${escapeHtml(stock.fraction_percent_decimal)}% ${escapeHtml(stock.fraction_basis)}${escapeHtml(carrier)}${escapeHtml(form)}</p>
        <small class="${stock.design_ready ? "inventory-ready" : "inventory-hold"}">${escapeHtml(stateLabel)}</small>
        <small class="inventory-source">${escapeHtml(sourceLabel)}</small>
        ${missing ? `<small class="inventory-missing">Needed: ${escapeHtml(missing)}</small>` : ""}
        ${completion}
      </article>`;
    }).join("")
    : '<p class="empty">No current inventory entries match that search.</p>';
}

async function refresh() {
  const [dashboard, materials, stocks, formulas, bottles, experiments, formulaLibrary, projectInventory] = await Promise.all([
    request("/dashboard"), request("/materials"), request("/stocks"), request("/formulas"), request("/bottles"), request("/experiments"), request("/v2/workbench/formula-library"), request("/v2/workbench/current-inventory"),
  ]);
  Object.assign(state, { materials, stocks, formulas, bottles, experiments, formulaLibrary: formulaLibrary.sources || [], projectInventory });
  $("#dashboard-counts").innerHTML = Object.entries(dashboard.counts).map(([label, value]) => `<article class="metric"><strong>${value}</strong><span>${escapeHtml(label)}</span></article>`).join("");
  $("#dashboard-warnings").innerHTML = dashboard.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  recordList("#material-list", materials, "canonical_name", (row) => row.cas_number || "No CAS recorded");
  recordList("#formula-list", formulas, "name", () => "Immutable versions are appended separately");
  recordList("#bottle-list", bottles, "label", (row) => row.status);
  recordList("#experiment-list", experiments, "name", (row) => row.status);
  renderProjectInventory($("#project-inventory-search").value);
  updateSelectors();
  syncImproveSourceMode();
  notify("Inventory and ledger refreshed.");
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

// Guided personal improvement workflow ------------------------------------
function splitList(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function humanize(value) {
  return String(value || "").toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function localIsoDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDecimal(value, maximum = 6) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "unknown");
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: maximum }).format(number);
}

function setWorkflowStep(current) {
  $$('[data-workflow-step]').forEach((node) => {
    const step = Number(node.dataset.workflowStep);
    node.classList.toggle("is-current", step === current);
    node.classList.toggle("is-complete", step < current || (current === 6 && step <= 5));
  });
}

function setImproveBusy(busy) {
  $("#improve-submit").disabled = busy;
  $("#improve-running").hidden = !busy;
}

function selectedExecutionStrategy() {
  return $('[name="execution_strategy"]:checked', $("#improve-form"))?.value || "EVOLVING_BOTTLE";
}

function syncImproveSourceMode() {
  const form = $("#improve-form");
  if (!form) return;
  let strategy = selectedExecutionStrategy();
  if (strategy === "EVOLVING_BOTTLE" && !state.bottles.length && (state.formulas.length || state.formulaLibrary.length)) {
    $('[name="execution_strategy"][value="NEW_FORMULA"]', form).checked = true;
    strategy = "NEW_FORMULA";
  }
  const bottleMode = strategy === "EVOLVING_BOTTLE";
  $("#improve-bottle-source").hidden = !bottleMode;
  $("#improve-formula-source").hidden = bottleMode;
  $('[name="bottle_id"]', form).required = bottleMode;
  if (!bottleMode) syncImproveFormulaSource();
  else {
    $('[name="formula_id"]', form).required = false;
    $('[name="project_formula_path"]', form).required = false;
  }
  $("#improve-source-note").textContent = bottleMode
    ? (state.bottles.length
      ? "The current committed bottle state will be replayed before analysis. Suggestions can only add material."
      : "No current bottle is recorded yet. Use Formula design now, or create a bottle in the Bottles view.")
    : "This is a read-only design comparison. No inventory or physical bottle will change.";
}

function syncImproveFormulaSource() {
  const form = $("#improve-form");
  if (!form || selectedExecutionStrategy() === "EVOLVING_BOTTLE") return;
  const selector = $('[name="formula_source_kind"]', form);
  if (selector.value === "LEDGER_FORMULA" && !state.formulas.length) selector.value = "PROJECT_FILE";
  const projectMode = selector.value === "PROJECT_FILE";
  $("#improve-project-formula-field").hidden = !projectMode;
  $("#improve-ledger-formula-field").hidden = projectMode;
  $('[name="project_formula_path"]', form).required = projectMode;
  $('[name="formula_id"]', form).required = !projectMode;
  const sourceState = $("#formula-source-state");
  sourceState.hidden = false;
  sourceState.textContent = projectMode
    ? (state.formulaLibrary.length
      ? `${state.formulaLibrary.length} read-only project formulas are available. Start typing to search; selecting one does not import or alter it.`
      : "No project formula files are available. Create or save a formula before analysis.")
    : (state.formulas.length
      ? "The latest immutable version in the formula ledger will be analyzed."
      : "There are no saved formula-ledger records yet. Use a project formula file instead.");
}

function engineConcentrationBasis(stock) {
  if (Number(stock.active_fraction) === 1) return "NEAT";
  if (stock.fraction_basis === "mass_fraction") return "W_W";
  if (stock.fraction_basis === "volume_fraction") return "V_V";
  return "UNKNOWN";
}

function stockAndMaterial(stockId) {
  const stock = state.stocks.find((item) => item.id === stockId);
  if (!stock) throw new Error(`The formula references a stock that is not in the current ledger: ${stockId}`);
  const material = state.materials.find((item) => item.id === stock.material_id);
  if (!material) throw new Error(`The stock references an unknown material: ${stock.material_id}`);
  return { stock, material };
}

async function analysisSourceFromBottle(bottleId) {
  const bottle = state.bottles.find((item) => item.id === bottleId);
  if (!bottle) throw new Error("Choose a current bottle first.");
  const replay = await request(`/v2/bottles/${encodeURIComponent(bottleId)}/replay`);
  if (replay.is_closed) throw new Error("This bottle is closed. Choose an active bottle or analyze a formula instead.");
  const rows = Object.entries(replay.stock_masses_g || {}).filter(([, amount]) => Number(amount) > 0).map(([stockId, amount]) => {
    const { stock, material } = stockAndMaterial(stockId);
    return {
      row_id: stockId,
      material: material.canonical_name,
      amount_decimal: String(amount),
      amount_unit: "g",
      stock_id: stockId,
      concentration_fraction_decimal: String(stock.active_fraction),
      concentration_basis: engineConcentrationBasis(stock),
      operation: "DIRECT_ADD",
    };
  });
  if (!rows.length) throw new Error("This bottle has no recorded stock additions to analyze yet.");
  state.improve.sourceMetadata = {
    source_kind: "current_bottle",
    formula_name: bottle.label,
    row_count: rows.length,
    stream_sequence: replay.stream_sequence,
  };
  return {
    sourceKind: "bottle",
    sourceId: bottleId,
    formula_id: bottleId,
    formula_name: bottle.label,
    rows,
    mode: "between_mix",
    execution_strategy: "EVOLVING_BOTTLE",
    active_bottle_id: bottleId,
  };
}

async function analysisSourceFromFormula(formulaId) {
  const formula = state.formulas.find((item) => item.id === formulaId);
  if (!formula) throw new Error("Choose a formula first.");
  const versions = await request(`/formulas/${encodeURIComponent(formulaId)}/versions`);
  if (!versions.length) throw new Error("This formula has no recorded composition yet.");
  const version = [...versions].sort((left, right) => Number(left.version_number) - Number(right.version_number)).at(-1);
  if (!version.components?.length) throw new Error("The latest formula version has no stock rows to analyze.");
  const rows = version.components.map((component) => {
    const { stock, material } = stockAndMaterial(component.stock_solution_id);
    const useVolume = component.requested_volume_ul !== null && component.requested_volume_ul !== undefined;
    return {
      row_id: component.id,
      material: material.canonical_name,
      amount_decimal: String(useVolume ? component.requested_volume_ul : component.requested_mass_g),
      amount_unit: useVolume ? "uL" : "g",
      stock_id: stock.id,
      concentration_fraction_decimal: String(stock.active_fraction),
      concentration_basis: engineConcentrationBasis(stock),
      role: component.role || undefined,
      operation: useVolume ? "DIRECT_ADD" : "MASS_ADD",
    };
  });
  state.improve.sourceMetadata = {
    source_kind: "formula_ledger",
    formula_name: formula.name,
    version_number: version.version_number,
    row_count: rows.length,
  };
  return {
    sourceKind: "formula",
    sourceId: formulaId,
    formula_id: version.id,
    formula_name: `${formula.name} · version ${version.version_number}`,
    rows,
    mode: "pre_mix",
    execution_strategy: "NEW_FORMULA",
    active_bottle_id: undefined,
  };
}

async function analysisSourceFromProjectFormula(sourcePath) {
  const selected = state.formulaLibrary.find((item) => item.source_path === sourcePath);
  if (!selected) throw new Error("Choose a project formula from the search list first.");
  const source = await request(`/v2/workbench/formula-source?source_path=${encodeURIComponent(sourcePath)}`);
  if (!source.rows?.length) throw new Error("The selected project formula did not contain analyzable material rows.");
  state.improve.sourceMetadata = {
    schema_version: source.schema_version,
    source_path: source.source_path,
    source_sha256: source.source_sha256,
    formula_name: source.formula_name,
    row_count: source.rows.length,
    separate_totals: source.separate_totals,
    warnings: source.warnings,
    design_only: source.design_only,
  };
  return {
    sourceKind: "project_formula",
    sourceId: source.source_path,
    formula_id: `project-${source.source_sha256}`,
    formula_name: source.formula_name,
    rows: source.rows,
    mode: "pre_mix",
    execution_strategy: "NEW_FORMULA",
    active_bottle_id: undefined,
  };
}

async function buildGoalAnalysisPayload(data) {
  const strategy = data.execution_strategy;
  state.improve.sourceMetadata = null;
  let source;
  if (strategy === "EVOLVING_BOTTLE") source = await analysisSourceFromBottle(data.bottle_id);
  else if (data.formula_source_kind === "PROJECT_FILE") source = await analysisSourceFromProjectFormula(data.project_formula_path);
  else source = await analysisSourceFromFormula(data.formula_id);
  state.improve.sourceKind = source.sourceKind;
  state.improve.sourceId = source.sourceId;
  state.improve.sourceRows = source.rows;
  const payload = {
    formula_id: source.formula_id,
    formula_name: source.formula_name,
    workflow_mode: "PERSONAL_RESEARCH",
    rows: source.rows,
    goals: [data.goal.trim()],
    observations: splitList(data.observations),
    must_preserve: splitList(data.must_preserve),
    must_avoid: splitList(data.must_avoid),
    mode: source.mode,
    max_hypotheses: 3,
    original_request: data.goal.trim(),
    desired_changes: [data.goal.trim()],
    execution_strategy: source.execution_strategy,
    appeal_mode: data.appeal_mode,
    comparison_evidence: data.comparison_evidence,
    evaluation_windows: splitList(data.evaluation_windows),
    application_context: data.application_context.trim() || undefined,
    active_bottle_id: source.active_bottle_id,
    market_evidence_as_of_date: localIsoDate(),
  };
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== undefined));
}

function resetImproveResult() {
  state.improve.analysis = null;
  state.improve.selectedHypothesis = null;
  state.improve.selectedVariant = "low_variant";
  state.improve.preparedLines = [];
  state.improve.additionEvents = [];
  state.improve.evaluationCommandId = null;
  state.improve.evaluationRequestBody = null;
  $("#interpretation-card").hidden = true;
  $("#improve-results").hidden = true;
  $("#delta-card").hidden = true;
  $("#record-delta-card").hidden = true;
  $("#quick-reaction-form").hidden = true;
  $("#physical-addition-confirmed").checked = false;
  setWorkflowStep(1);
}

async function pollEngineJob(jobId) {
  const terminalStates = new Set(["SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED"]);
  for (let attempt = 0; attempt < 180; attempt += 1) {
    if (state.improve.pollCancelled) throw new Error("Analysis cancelled.");
    const snapshot = await request(`/v2/engine-jobs/${encodeURIComponent(jobId)}`);
    $("#improve-running-detail").textContent = `Job state: ${humanize(snapshot.state)}.`;
    if (terminalStates.has(snapshot.state)) return snapshot;
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("The analysis is still running. Its durable job can be checked again without resubmitting the request.");
}

function addSummaryRow(list, label, value) {
  const row = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value || "Not specified";
  row.append(term, detail);
  list.append(row);
}

function formatEvaluationWindows(windows) {
  if (!windows?.length) return "Use the requested smelling window";
  return windows.map((item) => typeof item === "string" ? item : humanize(item.label)).join(", ");
}

function renderInterpretation(analysis) {
  const interpretation = analysis.request_interpretation;
  const card = $("#interpretation-card");
  card.hidden = false;
  $("#interpretation-state").textContent = humanize(interpretation.status);
  const summary = $("#interpretation-summary");
  summary.replaceChildren();
  addSummaryRow(summary, "Goal", interpretation.normalized_goal);
  if (state.improve.sourceMetadata?.formula_name) addSummaryRow(summary, "Source", state.improve.sourceMetadata.formula_name);
  const totals = state.improve.sourceMetadata?.separate_totals;
  if (totals) {
    const parts = [];
    if (Number(totals.liquid_total_ul) > 0) parts.push(`${formatDecimal(totals.liquid_total_ul)} µL liquid rows`);
    if (Number(totals.mass_total_mg) > 0) parts.push(`${formatDecimal(totals.mass_total_mg)} mg mass rows`);
    if (parts.length) addSummaryRow(summary, "Composition", `${parts.join(" + ")} (kept separate)`);
  }
  addSummaryRow(summary, "Preserve", interpretation.must_preserve.join(", ") || "Nothing specified");
  addSummaryRow(summary, "Avoid", interpretation.must_avoid.join(", ") || "Nothing specified");
  addSummaryRow(summary, "Workflow", interpretation.execution_strategy === "EVOLVING_BOTTLE" ? "Add to the current bottle" : "Design a new formula version");
  addSummaryRow(summary, "Approach", interpretation.appeal_mode === "GLOBAL_CROWD_PLEASING" ? "Identity plus global reference architecture" : "Protect this perfume's identity");
  addSummaryRow(summary, "Smell at", formatEvaluationWindows(interpretation.evaluation_windows));
  const ambiguity = $("#interpretation-ambiguity");
  ambiguity.hidden = !interpretation.confirmation_required;
  ambiguity.textContent = interpretation.confirmation_required
    ? `Please correct the brief before continuing: ${interpretation.ambiguities.join("; ")}`
    : "";
  return !interpretation.confirmation_required;
}

function renderHypotheses(analysis) {
  const list = $("#hypothesis-list");
  list.replaceChildren();
  for (const [index, hypothesis] of analysis.modification_hypotheses.entries()) {
    const card = document.createElement("article");
    card.className = "hypothesis-card";
    card.dataset.hypothesisId = hypothesis.hypothesis_id;
    const number = document.createElement("p");
    number.className = "panel-index";
    number.textContent = `Option ${index + 1}`;
    const title = document.createElement("h3");
    title.textContent = hypothesis.material_or_block;
    const rationale = document.createElement("p");
    rationale.textContent = hypothesis.rationale;
    const meta = document.createElement("p");
    meta.className = "hypothesis-meta";
    meta.textContent = `${humanize(hypothesis.action)} · ${humanize(hypothesis.evidence_class)}`;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Choose this direction";
    button.addEventListener("click", () => selectHypothesis(hypothesis));
    card.append(number, title, rationale, meta, button);
    list.append(card);
  }
  if (!analysis.modification_hypotheses.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No safe concrete hypothesis was generated. Refine the brief or leave the scent unchanged.";
    list.append(empty);
  }
}

function renderGoalAnalysis(analysis, envelope) {
  state.improve.analysis = analysis;
  const ready = renderInterpretation(analysis);
  $("#improve-analysis-details").textContent = JSON.stringify({ source: state.improve.sourceMetadata, validation: envelope.validation, applicability: envelope.applicability, analysis }, null, 2);
  if (!ready) {
    $("#improve-results").hidden = true;
    setWorkflowStep(2);
    return;
  }
  $("#improve-results").hidden = false;
  $("#strongest-clue").textContent = analysis.default_user_view.strongest_clue || "The evidence does not support a specific change yet.";
  const sourceWarnings = state.improve.sourceMetadata?.warnings || [];
  $("#clue-boundary").textContent = [
    analysis.default_user_view.uncertainty_or_stop_condition,
    sourceWarnings.length ? `${sourceWarnings.length} source row warning(s) remain visible in the details.` : "",
  ].filter(Boolean).join(" ");
  $("#selection-state").textContent = humanize(analysis.selection.status);
  renderHypotheses(analysis);
  setWorkflowStep(3);
}

function variantTargets(hypothesis, variantName) {
  const variant = hypothesis?.trial?.[variantName];
  return variant && typeof variant === "object" && Array.isArray(variant.row_targets) ? variant.row_targets : [];
}

function renderDeltaVariant() {
  const hypothesis = state.improve.selectedHypothesis;
  if (!hypothesis) return;
  const targets = variantTargets(hypothesis, state.improve.selectedVariant);
  $$('.variant-button').forEach((button) => button.classList.toggle("is-active", button.dataset.variant === state.improve.selectedVariant));
  $("#delta-title").textContent = hypothesis.material_or_block;
  const lineList = $("#delta-lines");
  lineList.replaceChildren();
  if (targets.length) {
    for (const target of targets) {
      const line = document.createElement("div");
      line.className = "delta-line";
      const material = document.createElement("strong");
      material.textContent = target.material;
      const amount = document.createElement("span");
      amount.textContent = `+ ${formatDecimal(target.delta_amount_decimal)} ${target.unit}`;
      line.append(material, amount);
      lineList.append(line);
    }
  } else {
    const unavailable = document.createElement("p");
    unavailable.className = "empty";
    unavailable.textContent = "This clue identifies a material direction, but not an exact physical dose. It remains a design hypothesis.";
    lineList.append(unavailable);
  }
  const summary = $("#delta-purpose");
  summary.replaceChildren();
  addSummaryRow(summary, "Purpose", hypothesis.goal);
  addSummaryRow(summary, "Expected", humanize(hypothesis.expected_direction));
  addSummaryRow(summary, "Preserves", hypothesis.success_criteria.must_preserve.join(", ") || "No extra preserve constraint");
  addSummaryRow(summary, "Smell again", formatEvaluationWindows(hypothesis.success_criteria.evaluation_windows));
  addSummaryRow(summary, "Main risk", hypothesis.uncertainty);
  const executable = state.improve.sourceKind === "bottle" && targets.length > 0 && targets.every((target) => Number(target.delta_amount_decimal) > 0);
  $("#prepare-delta").disabled = !executable;
  $("#prepare-delta").textContent = executable ? "Prepare this change" : "Design comparison only";
}

function selectHypothesis(hypothesis) {
  state.improve.selectedHypothesis = hypothesis;
  state.improve.selectedVariant = "low_variant";
  $$('[data-hypothesis-id]').forEach((card) => card.classList.toggle("is-selected", card.dataset.hypothesisId === hypothesis.hypothesis_id));
  $("#delta-card").hidden = false;
  $("#record-delta-card").hidden = true;
  $("#quick-reaction-form").hidden = true;
  renderDeltaVariant();
  $("#delta-card").scrollIntoView({ behavior: "smooth", block: "start" });
}

function sourceRowForTarget(target) {
  return state.improve.sourceRows.find((row) => row.row_id === target.row_id)
    || state.improve.sourceRows.find((row) => row.material.toLocaleLowerCase() === String(target.material).toLocaleLowerCase());
}

function suggestedPhysicalAmounts(target, stock) {
  const amount = Number(target.delta_amount_decimal);
  if (target.unit === "g") return { massG: amount, volumeUl: null };
  if (target.unit === "mg") return { massG: amount / 1000, volumeUl: null };
  const volumeUl = target.unit === "mL" ? amount * 1000 : amount;
  const density = Number(stock.density_g_ml);
  return { massG: Number.isFinite(density) && density > 0 ? volumeUl * density / 1000 : null, volumeUl };
}

function renderPhysicalLines() {
  const editor = $("#delta-line-editor");
  editor.replaceChildren();
  for (const [index, line] of state.improve.preparedLines.entries()) {
    const row = document.createElement("div");
    row.className = "physical-line";
    const title = document.createElement("div");
    title.className = "physical-line-title";
    const name = document.createElement("strong");
    name.textContent = line.material;
    const proposed = document.createElement("span");
    proposed.textContent = `Proposed: +${formatDecimal(line.proposedAmount)} ${line.unit}`;
    title.append(name, proposed);
    const massLabel = document.createElement("label");
    massLabel.textContent = line.suggestedVolumeUl === null ? "Actual mass, g" : "Mass equivalent, g";
    const massInput = document.createElement("input");
    massInput.type = "number";
    massInput.min = "0.000001";
    massInput.step = "any";
    massInput.dataset.lineIndex = String(index);
    massInput.dataset.quantity = "mass";
    massInput.placeholder = line.suggestedMassG === null ? "Weigh the transfer" : "Actual mass";
    if (line.suggestedMassG !== null) massInput.value = String(Number(line.suggestedMassG.toPrecision(10)));
    massLabel.append(massInput);
    const volumeLabel = document.createElement("label");
    volumeLabel.textContent = "Actual volume, µL";
    const volumeInput = document.createElement("input");
    volumeInput.type = "number";
    volumeInput.min = "0.000001";
    volumeInput.step = "any";
    volumeInput.dataset.lineIndex = String(index);
    volumeInput.dataset.quantity = "volume";
    if (line.suggestedVolumeUl !== null) volumeInput.value = String(Number(line.suggestedVolumeUl.toPrecision(10)));
    else {
      volumeInput.placeholder = "Not needed";
      volumeInput.disabled = true;
    }
    volumeLabel.append(volumeInput);
    row.append(title, massLabel, volumeLabel);
    if (line.stock.fraction_basis !== "mass_fraction") {
      const warning = document.createElement("p");
      warning.className = "inline-warning";
      warning.textContent = "This stock is not mass-basis bound in the ledger, so the personal mass-governed record must remain on hold.";
      row.append(warning);
    }
    editor.append(row);
  }
  validatePhysicalRecord();
}

function validatePhysicalRecord() {
  const confirmed = $("#physical-addition-confirmed").checked;
  const linesValid = state.improve.preparedLines.length > 0 && state.improve.preparedLines.every((line, index) => {
    const input = $(`[data-line-index="${index}"][data-quantity="mass"]`, $("#delta-line-editor"));
    return line.stock.fraction_basis === "mass_fraction" && Number(input?.value) > 0;
  });
  $("#record-delta").disabled = !(confirmed && linesValid);
}

function preparePhysicalDelta() {
  const hypothesis = state.improve.selectedHypothesis;
  const targets = variantTargets(hypothesis, state.improve.selectedVariant);
  if (state.improve.sourceKind !== "bottle" || !targets.length) throw new Error("This hypothesis is not an executable positive-only bottle delta.");
  state.improve.preparedLines = targets.map((target) => {
    const sourceRow = sourceRowForTarget(target);
    if (!sourceRow?.stock_id) throw new Error(`No exact stock is bound to ${target.material}.`);
    const { stock } = stockAndMaterial(sourceRow.stock_id);
    const suggested = suggestedPhysicalAmounts(target, stock);
    return {
      material: target.material,
      stock,
      proposedAmount: Number(target.delta_amount_decimal),
      unit: target.unit,
      suggestedMassG: suggested.massG,
      suggestedVolumeUl: suggested.volumeUl,
      commandId: crypto.randomUUID(),
      expectedSequence: null,
      requestBody: null,
      event: null,
    };
  });
  $("#physical-addition-confirmed").checked = false;
  renderPhysicalLines();
  $("#record-delta-card").hidden = false;
  setWorkflowStep(4);
  $("#record-delta-card").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function recordPreparedDelta() {
  validatePhysicalRecord();
  if ($("#record-delta").disabled) throw new Error("Confirm the physical addition and enter every measured mass first.");
  const button = $("#record-delta");
  button.disabled = true;
  $("#record-delta-status").textContent = "Recording the measured additions…";
  const bottleId = state.improve.sourceId;
  try {
    for (const [index, line] of state.improve.preparedLines.entries()) {
      if (line.event) continue;
      if (!line.requestBody) {
        const replay = await request(`/v2/bottles/${encodeURIComponent(bottleId)}/replay`);
        line.expectedSequence = replay.stream_sequence;
        const massInput = $(`[data-line-index="${index}"][data-quantity="mass"]`, $("#delta-line-editor"));
        const volumeInput = $(`[data-line-index="${index}"][data-quantity="volume"]`, $("#delta-line-editor"));
        const measuredVolume = volumeInput && !volumeInput.disabled && Number(volumeInput.value) > 0 ? volumeInput.value : null;
        line.requestBody = {
          stock_solution_id: line.stock.id,
          mass_g: massInput.value,
          expected_sequence: line.expectedSequence,
          command_id: line.commandId,
          actor: "personal-workbench",
          role: "material",
          goal_analysis_sha256: state.improve.analysis.analysis_sha256,
          hypothesis_id: state.improve.selectedHypothesis.hypothesis_id,
          hypothesis_variant: state.improve.selectedVariant,
          ...(measuredVolume ? { measured_volume_ul: measuredVolume, volume_measurement_method: "user_recorded_transfer" } : {}),
        };
      }
      line.event = await request(`/bottles/${encodeURIComponent(bottleId)}/additions`, { method: "POST", body: JSON.stringify(line.requestBody) });
      $("#record-delta-status").textContent = `Recorded ${index + 1} of ${state.improve.preparedLines.length} additions.`;
    }
    state.improve.additionEvents = state.improve.preparedLines.map((line) => line.event);
    state.improve.evaluationCommandId = crypto.randomUUID();
    state.improve.evaluationRequestBody = null;
    $$("#delta-line-editor input").forEach((input) => { input.disabled = true; });
    $("#physical-addition-confirmed").disabled = true;
    $("#record-delta-status").textContent = "Recorded once in the personal bottle ledger. This remains a non-production, non-release record.";
    $("#quick-reaction-form").hidden = false;
    setWorkflowStep(5);
    await refresh();
    notify("Personal bottle delta recorded exactly once.");
    $("#quick-reaction-form").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    $("#record-delta-status").textContent = `Recording stopped: ${error.message}. Completed lines will not be repeated on retry.`;
    button.disabled = false;
    throw error;
  }
}

async function recordQuickReaction(data) {
  if (!state.improve.additionEvents.length) throw new Error("Record the physical delta before saving a reaction.");
  const bottleId = state.improve.sourceId;
  if (!state.improve.evaluationRequestBody) {
    const replay = await request(`/v2/bottles/${encodeURIComponent(bottleId)}/replay`);
    state.improve.evaluationRequestBody = {
      schema_version: "quick-bottle-evaluation-v1",
      addition_event_ids: state.improve.additionEvents.map((event) => event.id),
      goal_analysis_sha256: state.improve.analysis.analysis_sha256,
      hypothesis_id: state.improve.selectedHypothesis.hypothesis_id,
      hypothesis_variant: state.improve.selectedVariant,
      expected_sequence: replay.stream_sequence,
      command_id: state.improve.evaluationCommandId,
      actor: "personal-workbench",
      evaluated_at: new Date().toISOString(),
      waited_seconds: Number(data.waited_seconds),
      reaction: data.reaction.trim(),
      decision: data.decision,
    };
  }
  const body = state.improve.evaluationRequestBody;
  const saved = await request(`/v2/bottles/${encodeURIComponent(bottleId)}/quick-evaluations`, { method: "POST", body: JSON.stringify(body) });
  $("#reaction-status").textContent = `Saved as ${humanize(saved.evidence_scope)}. No population claim was created.`;
  $('#quick-reaction-form button[type="submit"]').disabled = true;
  setWorkflowStep(6);
  notify("Personal sensory reaction saved.");
}

$$('[name="execution_strategy"]').forEach((input) => input.addEventListener("change", syncImproveSourceMode));
$('[name="formula_source_kind"]').addEventListener("change", syncImproveFormulaSource);

$("#improve-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  resetImproveResult();
  setImproveBusy(true);
  state.improve.pollCancelled = false;
  try {
    const data = formData(event.currentTarget);
    const payload = await buildGoalAnalysisPayload(data);
    setWorkflowStep(2);
    const submitted = await request("/v2/engine-jobs", {
      method: "POST",
      body: JSON.stringify({
        schema_version: "lab-engine-job-request-v2",
        job_type: "FORMULA_ANALYSIS",
        requester: "personal-workbench-ui",
        idempotency_key: crypto.randomUUID(),
        payload,
      }),
    });
    state.improve.jobId = submitted.id;
    const completed = await pollEngineJob(submitted.id);
    if (!completed.result?.result) throw new Error(completed.events?.at(-1)?.reason || `Analysis ended as ${completed.state}.`);
    const envelope = completed.result.result;
    const analysis = envelope.result?.goal_analysis;
    if (!analysis) throw new Error("The completed job did not contain a goal analysis result.");
    renderGoalAnalysis(analysis, envelope);
    notify(analysis.request_interpretation.confirmation_required ? "Please correct the interpretation." : "Goal-directed clues are ready.");
  } catch (error) {
    notify(error.message, true);
    if (!state.improve.pollCancelled) setWorkflowStep(1);
  } finally {
    setImproveBusy(false);
  }
});

$("#cancel-improve-job").addEventListener("click", async () => {
  state.improve.pollCancelled = true;
  if (state.improve.jobId) {
    try {
      await request(`/v2/engine-jobs/${encodeURIComponent(state.improve.jobId)}/cancel`, {
        method: "POST",
        body: JSON.stringify({ requester: "personal-workbench-ui", reason: "Cancelled from the guided workbench." }),
      });
    } catch (error) { notify(error.message, true); }
  }
  setImproveBusy(false);
  setWorkflowStep(1);
});

$("#edit-improve-request").addEventListener("click", () => {
  $('#improve-form [name="goal"]').focus();
  $("#improve-form").scrollIntoView({ behavior: "smooth", block: "start" });
});

$$('.variant-button').forEach((button) => button.addEventListener("click", () => {
  state.improve.selectedVariant = button.dataset.variant;
  $("#record-delta-card").hidden = true;
  $("#quick-reaction-form").hidden = true;
  renderDeltaVariant();
}));

$("#prepare-delta").addEventListener("click", () => {
  try { preparePhysicalDelta(); }
  catch (error) { notify(error.message, true); }
});
$("#physical-addition-confirmed").addEventListener("change", validatePhysicalRecord);
$("#delta-line-editor").addEventListener("input", validatePhysicalRecord);
$("#record-delta").addEventListener("click", () => recordPreparedDelta().catch((error) => notify(error.message, true)));
$("#abandon-delta").addEventListener("click", () => {
  $("#record-delta-card").hidden = true;
  state.improve.preparedLines = [];
  setWorkflowStep(3);
  notify("Bottle left unchanged.");
});
$("#quick-reaction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { await recordQuickReaction(formData(event.currentTarget)); }
  catch (error) {
    if (error.status >= 400 && error.status < 500) state.improve.evaluationRequestBody = null;
    notify(error.message, true);
  }
});

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

$("#project-inventory-search").addEventListener("input", (event) => {
  renderProjectInventory(event.currentTarget.value);
});

$("#project-inventory-incomplete-only").addEventListener("change", () => {
  renderProjectInventory($("#project-inventory-search").value);
});

function closeInventoryCompletion() {
  $("#inventory-completion-panel").hidden = true;
  $("#inventory-completion-form").reset();
}

function openInventoryCompletion(stock) {
  const panel = $("#inventory-completion-panel");
  const form = $("#inventory-completion-form");
  form.reset();
  $("#inventory-completion-name").textContent = stock.identity_name || stock.material;
  const missing = (stock.missing_fields || []).map((field) => humanize(field)).join(", ");
  $("#inventory-completion-help").textContent = missing
    ? `Still needed for personal formulation: ${missing}. Confirm only what you actually know.`
    : "Review and confirm the details that describe your current bottle.";
  $('[name="stock_id"]', form).value = stock.stock_id;
  $('[name="expected_effective_inventory_sha256"]', form).value = state.projectInventory.canonical_effective_inventory_sha256;
  $('[name="fraction_percent_decimal"]', form).value = stock.fraction_percent_decimal || "";
  const supportedBasis = ["neat", "mass_fraction", "volume_fraction", "mass_per_volume"];
  $('[name="fraction_basis"]', form).value = supportedBasis.includes(stock.fraction_basis)
    ? stock.fraction_basis
    : "unspecified";
  $('[name="carrier"]', form).value = stock.carrier || "";
  const supportedForms = ["as_supplied", "solution", "oil", "resin", "paste", "crystals", "powder", "solid"];
  const normalizedForm = stock.physical_form === "as_supplied_product" ? "as_supplied" : stock.physical_form;
  $('[name="physical_form"]', form).value = supportedForms.includes(normalizedForm) ? normalizedForm : "";
  $('[name="homogeneity"]', form).value = stock.homogeneity
    || (Number(stock.fraction_percent_decimal) === 100 ? "NOT_APPLICABLE" : "UNKNOWN");
  $('[name="final_fraction_known"]', form).checked = !String(stock.fraction_basis || "").includes("starting_charge");
  panel.hidden = false;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
  $('[name="fraction_percent_decimal"]', form).focus();
}

$("#project-inventory-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-complete-stock]");
  if (!button) return;
  const stock = (state.projectInventory.stocks || []).find(
    (item) => item.stock_id === button.dataset.completeStock,
  );
  if (stock) openInventoryCompletion(stock);
});

$("#inventory-completion-close").addEventListener("click", closeInventoryCompletion);
$("#inventory-completion-cancel").addEventListener("click", closeInventoryCompletion);

$("#inventory-completion-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formData(form);
  const idempotencyKey = globalThis.crypto?.randomUUID?.()
    || `inventory-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = "Saving…";
  try {
    const result = await request("/v2/workbench/current-inventory/complete", {
      method: "POST",
      body: JSON.stringify({
        schema_version: "personal-inventory-completion-request-v1",
        stock_id: data.stock_id,
        expected_effective_inventory_sha256: data.expected_effective_inventory_sha256,
        idempotency_key: idempotencyKey,
        fraction_percent_decimal: data.fraction_percent_decimal || null,
        fraction_basis: data.fraction_basis || null,
        carrier: data.carrier || "",
        physical_form: data.physical_form || null,
        possession_confirmed: Boolean(form.elements.possession_confirmed.checked),
        homogeneity: data.homogeneity,
        final_fraction_known: Boolean(form.elements.final_fraction_known.checked),
        source_kind: data.source_kind,
        user_note: data.user_note || "",
      }),
    });
    state.projectInventory = result.inventory;
    renderProjectInventory($("#project-inventory-search").value);
    if (result.design_ready) {
      closeInventoryCompletion();
      notify("Inventory details saved. This stock is now available for personal formula design.");
    } else {
      const missing = (result.missing_fields || []).map((field) => humanize(field)).join(", ");
      $("#inventory-completion-help").textContent = `Saved, but this still needs: ${missing}.`;
      $('[name="expected_effective_inventory_sha256"]', form).value = result.inventory.canonical_effective_inventory_sha256;
      notify("Details saved, but the stock is still incomplete.", true);
    }
  } catch (error) {
    notify(error.message, true);
  } finally {
    submit.disabled = false;
    submit.textContent = "Save these details";
  }
});

function closeInventoryAddition() {
  $("#inventory-addition-panel").hidden = true;
  $("#inventory-addition-form").reset();
}

$("#inventory-add-open").addEventListener("click", () => {
  closeInventoryCompletion();
  $("#inventory-addition-panel").hidden = false;
  $("#inventory-addition-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  $('#inventory-addition-form [name="identity_name"]').focus();
});
$("#inventory-add-close").addEventListener("click", closeInventoryAddition);
$("#inventory-add-cancel").addEventListener("click", closeInventoryAddition);

$("#inventory-addition-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formData(form);
  const idempotencyKey = globalThis.crypto?.randomUUID?.()
    || `inventory-add-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = "Adding…";
  try {
    const result = await request("/v2/workbench/current-inventory/add", {
      method: "POST",
      body: JSON.stringify({
        schema_version: "personal-inventory-addition-request-v1",
        expected_design_inventory_sha256: state.projectInventory.effective_inventory_sha256,
        idempotency_key: idempotencyKey,
        identity_name: data.identity_name,
        category: data.category,
        fraction_percent_decimal: data.fraction_percent_decimal,
        fraction_basis: data.fraction_basis,
        carrier: data.carrier || "",
        physical_form: data.physical_form,
        possession_confirmed: Boolean(form.elements.possession_confirmed.checked),
        homogeneity: data.homogeneity,
        source_kind: "PERSONAL_CONFIRMATION",
        supplier_name: data.supplier_name || "",
        supplier_sku: data.supplier_sku || "",
        user_note: data.user_note || "",
      }),
    });
    state.projectInventory = result.inventory;
    $("#project-inventory-search").value = data.identity_name;
    renderProjectInventory(data.identity_name);
    closeInventoryAddition();
    notify(`${data.identity_name} is now available for personal formula design.`);
  } catch (error) {
    notify(error.message, true);
  } finally {
    submit.disabled = false;
    submit.textContent = "Add to my inventory";
  }
});

// Inventory-grounded formulation conversation ----------------------------
function appendFormulaChatBubble(kind, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${kind === "user" ? "user-bubble" : "assistant-bubble"}`;
  const label = document.createElement("strong");
  label.textContent = kind === "user" ? "You" : "Perfumer";
  const message = document.createElement("p");
  message.textContent = text;
  bubble.append(label, message);
  $("#formula-chat-log").append(bubble);
  bubble.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function addFormulaResultSummary(list, label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  wrapper.append(term, detail);
  list.append(wrapper);
}

function selectedFormulaVariant(result, variantIndex = state.formulaChat.variantIndex || 0) {
  const variants = result?.design_variants || [];
  const variant = variants[variantIndex] || variants[0] || null;
  const critic = variant?.critic || result?.critic || null;
  return {
    variant,
    formula: critic?.state === "WITHHELD" ? null : (variant ? variant.formula : result?.optimized_formula) || null,
    critic,
  };
}

function renderFormulaDesign(result, variantIndex = 0) {
  state.formulaChat.result = result;
  state.formulaChat.variantIndex = variantIndex;
  const card = $("#formula-chat-result");
  card.hidden = false;
  $("#formula-result-name").textContent = result.formula_name || "Formula draft";
  const selected = selectedFormulaVariant(result, variantIndex);
  const hasFormula = Boolean(selected.formula);
  $("#formula-result-state").textContent = hasFormula
    ? (selected.critic?.issues?.length ? "Proposal · check hold" : "Proposal only")
    : "Needs clarification";
  $("#formula-result-summary").textContent = result.assistant_message || "No formula was generated.";
  const picker = $("#formula-variant-picker");
  const variants = result.design_variants || [];
  picker.hidden = variants.length <= 1;
  $("#formula-result-variant").textContent = variants.length > 1
    ? `Alternative shown: ${variants[variantIndex]?.label || `Alternative ${variantIndex + 1}`}`
    : "";
  picker.replaceChildren();
  variants.forEach((variant, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = index === variantIndex ? "is-active" : "";
    button.textContent = variant.label || `Alternative ${index + 1}`;
    button.addEventListener("click", () => renderFormulaDesign(result, index));
    picker.append(button);
  });
  const rows = selected.formula?.rows || [];
  $("#formula-result-rows").innerHTML = rows.length
    ? rows.map((row) => {
      const fraction = `${formatDecimal(Number(row.stock_fraction_decimal) * 100, 4)}%`;
      const carrier = row.carrier ? ` in ${row.carrier}` : "";
      const proxy = row.profile_source === "HEURISTIC_CATEGORY_PROXY" ? '<small class="proxy-label">category proxy</small>' : "";
      const stockLabel = row.stock_label || `${fraction} ${row.fraction_basis}${carrier}`;
      return `<tr>
        <td><strong>${escapeHtml(row.material)}</strong>${proxy}<small class="formula-why">${escapeHtml(row.rationale)}</small></td>
        <td class="formula-dose">${escapeHtml(row.amount_decimal)} ${escapeHtml(row.amount_unit)}${benchNeedsPreparedDilution(row) ? '<small class="formula-dose-hold">prepare dilution first</small>' : ""}</td>
        <td>${escapeHtml(stockLabel)}<small>${escapeHtml(fraction)} ${escapeHtml(row.fraction_basis)}${escapeHtml(carrier)}</small></td>
        <td>${escapeHtml(row.slot_label)}<small>${escapeHtml(row.note)} · ${escapeHtml(row.role)}</small></td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="4">Clarify the brief before a formula can be created.</td></tr>';

  const totals = $("#formula-result-totals");
  totals.replaceChildren();
  if (selected.formula) {
    addFormulaResultSummary(totals, "Liquid stock total", `${selected.formula.separate_totals.liquid_total_ul} µL`);
    addFormulaResultSummary(totals, "Solid total", `${selected.formula.separate_totals.mass_total_mg} mg`);
    addFormulaResultSummary(totals, "Structure", String(result.concept_family || "concept").replaceAll("_", " "));
    addFormulaResultSummary(totals, "Planning method", String(result.composition_plan?.method || result.optimization?.status || "not run").replaceAll("_", " ").toLowerCase());
    addFormulaResultSummary(totals, "Rows used", `${rows.length} of at most ${result.requested_material_limit || rows.length}`);
  }

  const detail = $("#formula-result-detail");
  detail.replaceChildren();
  const repairLabels = (result.composition_plan?.request_specific_repairs || [])
    .map((value) => String(value).replaceAll("_", " ").toLowerCase());
  const temporalSequence = (selected.variant?.temporal_hypothesis || result.temporal_hypothesis)?.sequence || [];
  const referenceContext = selected.variant?.commercial_reference_context || result.commercial_reference_context;
  const referenceProducts = (referenceContext?.named_products || [])
    .map((product) => typeof product === "string" ? product : product.display_name)
    .filter(Boolean);
  const referenceCriteria = referenceContext?.design_criteria || [];
  const usesStrengthCompensation = rows.some(
    (row) => row.allocation_basis === "STOCK_STRENGTH_COMPENSATED_HEURISTIC_NOT_ACTIVE_MASS",
  );
  const reasoningPasses = (result.design_reasoning || [])
    .map((entry) => String(entry.pass || "").replaceAll("_", " ").toLowerCase())
    .filter(Boolean);
  const paragraphs = [
    selected.critic?.strongest_clue
      ? `Strongest composition clue: ${selected.critic.strongest_clue}`
      : "No composition clue was generated because the request needs clarification.",
    result.composition_plan
      ? `The planner filled ${selected.variant?.role_plan?.length ?? result.composition_plan.roles_filled?.length ?? 0} nonredundant roles and stopped under the material ceiling. Ingredient count was not an objective.`
      : "No structural plan ran because a hard request constraint was unresolved.",
    selected.critic?.issues?.length
      ? `Practical hold: ${String(selected.critic.issues[0]).replaceAll("_", " ").toLowerCase()}. Expand details only if you need to resolve it before compounding.`
      : selected.critic?.limitations?.length
        ? `Evidence limit: ${String(selected.critic.limitations[0]).replaceAll("_", " ").toLowerCase()}. The formula is still usable as a bench hypothesis.`
        : "Practical hold: none detected in the design inputs. This is still not sensory or safety validation.",
    "Unknown until smelled: pleasantness, personal liking, mixture interactions, and whether this is actually better than an unchanged control.",
    "No inventory, formula file, bottle, or laboratory record was changed.",
  ];
  if (selected.variant?.architecture?.comparison_question) {
    paragraphs.splice(1, 0,
      `Architecture comparison: ${selected.variant.architecture.comparison_question} This is an untested role-plan hypothesis, not a measured improvement.`);
  }
  if (repairLabels.length) {
    paragraphs.splice(2, 0, `Request-specific adaptation: ${repairLabels.join("; ")}.`);
  }
  if (temporalSequence.length) {
    const timing = temporalSequence.map((entry) => {
      const windowLabel = String(entry.window || "requested window").replaceAll("_", " ").toLowerCase();
      const roles = (entry.intended_roles || []).map((role) => role.role).filter(Boolean).join(", ");
      return `${windowLabel}: ${roles || "role hypothesis"}`;
    }).join("; ");
    paragraphs.splice(-2, 0, `Timing map (hypothesis only): ${timing}. Smell or measure the pilot at those windows before accepting it.`);
  }
  if (referenceProducts.length) {
    paragraphs.splice(-2, 0, `Commercial references: ${referenceProducts.join("; ")}. Their marketed facets were used only as documentary contrasts; no proprietary formula, sensory similarity, or liking was inferred.`);
  } else if (referenceCriteria.length) {
    paragraphs.splice(-2, 0, `Prestige comparison criteria: ${referenceCriteria.join(", ")}. No unrelated bestseller was borrowed, and these request-derived criteria are not a liking label.`);
  } else if (result.request_interpretation?.appeal_mode === "GLOBAL_CROWD_PLEASING") {
    paragraphs.splice(-2, 0, "Commercial comparison was requested, but no applicable named reference panel was available; market alignment and population liking remain withheld.");
  }
  if (usesStrengthCompensation) {
    paragraphs.splice(-2, 0, "Dose reconciliation used a bounded stock-strength compensation heuristic so diluted stocks were not treated like neat materials. It is not an active-mass or sensory-equivalence claim; exact active mass remains withheld wherever basis or density is incomplete.");
  }
  if (reasoningPasses.length) {
    paragraphs.splice(-2, 0, `Design audit trail: ${reasoningPasses.join(" → ")}.`);
  }
  paragraphs.forEach((text) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    detail.append(paragraph);
  });
  const knowledge = result.formulation_knowledge;
  if (knowledge) {
    const evidence = document.createElement("details");
    evidence.className = "formulation-knowledge";
    const heading = document.createElement("summary");
    heading.textContent = "Research behind this design · optional details";
    evidence.append(heading);
    const scope = document.createElement("p");
    scope.textContent = knowledge.strongest_clue || "Local literature knowledge is unavailable for this request.";
    evidence.append(scope);
    const limit = document.createElement("p");
    limit.textContent = "Source-supported descriptions and formulation hypotheses are separate. These references do not supply measured doses, liking scores or safety approval.";
    evidence.append(limit);
    const coverage = result.architecture_planning?.implementation_coverage;
    if (coverage) {
      const coverageDetails = document.createElement("details");
      const coverageHeading = document.createElement("summary");
      coverageHeading.textContent = "Coverage and remaining prerequisites";
      coverageDetails.append(coverageHeading);
      (coverage.items || []).forEach((item) => {
        const line = document.createElement("p");
        line.textContent = `${item.subtype_id}: ${String(item.implementation_state).replaceAll("_", " ").toLowerCase()}. ${item.required_next}`;
        coverageDetails.append(line);
      });
      if (coverage.state === "WITHHOLD_UNKNOWN") {
        const unavailable = document.createElement("p");
        unavailable.textContent = "The reviewed coverage record is unavailable; no completeness claim is made.";
        coverageDetails.append(unavailable);
      }
      evidence.append(coverageDetails);
    }
    (knowledge.construction_context?.dossiers || []).forEach((dossier) => {
      const section = document.createElement("section");
      const title = document.createElement("h4");
      title.textContent = `${dossier.title} · untested construction options`;
      section.append(title);
      const recognizer = document.createElement("p");
      recognizer.textContent = (dossier.recognizers || []).join(" ");
      section.append(recognizer);
      (dossier.architectures || []).forEach((architecture, index) => {
        const option = document.createElement("p");
        option.textContent = `${index === 0 ? "Control" : "Alternative"}: ${architecture.intent}`;
        section.append(option);
      });
      const comparison = document.createElement("p");
      comparison.textContent = `Question to resolve: ${dossier.comparison?.question || "No supported comparison question."} Avoid: ${(dossier.negative_space || []).join(" ")}`;
      section.append(comparison);
      evidence.append(section);
    });
    (knowledge.subtype_context?.campaign_identity_holds || []).forEach((hold) => {
      const note = document.createElement("p");
      note.textContent = `Reference identity unresolved: ${hold.reason} ${hold.question}`;
      evidence.append(note);
    });
    (knowledge.subtype_context?.cards || []).forEach((card) => {
      const section = document.createElement("section");
      const title = document.createElement("h4");
      title.textContent = `${card.title} · subtype research hypothesis`;
      section.append(title);
      const fact = document.createElement("p");
      fact.textContent = `Evidence: ${card.evidence_summary}`;
      section.append(fact);
      const hypothesis = document.createElement("p");
      hypothesis.textContent = `Design hypothesis: ${card.construction_hypothesis}`;
      section.append(hypothesis);
      const comparison = document.createElement("p");
      comparison.textContent = `Question to resolve: ${card.comparison?.question} Avoid: ${(card.negative_space || []).join("; ")}`;
      section.append(comparison);
      const boundary = document.createElement("p");
      boundary.textContent = `Limits: ${(card.identity_limits || []).join(" ")}`;
      section.append(boundary);
      (card.review_addenda || []).forEach((addendum) => {
        const update = document.createElement("p");
        update.textContent = `Deeper source review: ${addendum.evidence_summary} Limits: ${(addendum.identity_limits || []).join(" ")}`;
        section.append(update);
      });
      evidence.append(section);
    });
    (knowledge.sources || []).forEach((source) => {
      const paragraph = document.createElement("p");
      const label = `${source.title} · ${String(source.evidence_class).replaceAll("_", " ").toLowerCase()}`;
      let sourceURL = null;
      if (typeof source.url === "string") {
        try {
          const parsed = new URL(source.url);
          if (parsed.protocol === "https:" && !parsed.username && !parsed.password) {
            sourceURL = parsed.href;
          }
        } catch {
          // An unavailable/malformed reference remains plain text.
        }
      }
      if (sourceURL) {
        const link = document.createElement("a");
        link.textContent = label;
        link.href = sourceURL;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        paragraph.append(link);
      } else {
        paragraph.textContent = label;
      }
      evidence.append(paragraph);
    });
    (knowledge.prior_references || []).forEach((reference) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = `${reference.title} · prior local reference only · ${reference.state}`;
      evidence.append(paragraph);
    });
    detail.append(evidence);
  }
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetFormulaChat() {
  state.formulaChat = { messages: [], result: null, variantIndex: 0 };
  const form = $("#formula-chat-form");
  form.reset();
  $('[name="liquid_concentrate_ul_decimal"]', form).value = "6000";
  $('[name="max_materials"]', form).value = "30";
  $('[name="design_mode"]', form).value = "FAST_SKETCH";
  $("#formula-chat-log").innerHTML = '<div class="chat-bubble assistant-bubble"><strong>Perfumer</strong><p>Tell me the name or feeling of the perfume you want to make. I will use your inventory, honor hard constraints first, and stop before filler.</p></div>';
  $("#formula-chat-result").hidden = true;
  $("#formula-chat-submit").textContent = "Create my formula";
  notify("Ready for a new perfume idea.");
}

$("#formula-chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formData(form);
  const message = String(data.message || "").trim();
  const previous = state.formulaChat.result;
  const priorMessages = state.formulaChat.messages.slice(-8);
  const previousRows = selectedFormulaVariant(previous).formula?.rows || [];
  appendFormulaChatBubble("user", message);
  state.formulaChat.messages.push(message);
  const submit = $("#formula-chat-submit");
  submit.disabled = true;
  submit.textContent = previous ? "Refining…" : "Creating…";
  try {
    const designMode = String(data.design_mode || "FAST_SKETCH");
    const payload = {
      message,
      formula_name: data.formula_name || previous?.formula_name || null,
      liquid_concentrate_ul_decimal: String(data.liquid_concentrate_ul_decimal || "6000"),
      max_materials: Number(data.max_materials || 30),
      must_preserve: splitList(data.must_preserve),
      must_avoid: splitList(data.must_avoid),
      previous_stock_ids: previousRows.map((row) => row.stock_id),
      conversation_context: priorMessages,
      design_mode: designMode,
      variant_count: designMode === "DEEP_COMPOSE" ? 3 : 1,
    };
    let result;
    if (designMode === "DEEP_COMPOSE") {
      submit.textContent = "Composing alternatives…";
      const submitted = await request("/v2/engine-jobs", {
        method: "POST",
        body: JSON.stringify({
          schema_version: "lab-engine-job-request-v2",
          job_type: "FORMULA_DESIGN",
          requester: "formula-studio-ui",
          idempotency_key: crypto.randomUUID(),
          payload,
        }),
      });
      const terminalStates = new Set(["SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED"]);
      let completed = submitted;
      for (let attempt = 0; attempt < 500 && !terminalStates.has(completed.state); attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 600));
        completed = await request(`/v2/engine-jobs/${encodeURIComponent(submitted.id)}`);
      }
      if (!terminalStates.has(completed.state)) throw new Error("Deep Compose is still running; its durable job remains available without resubmitting.");
      result = completed.result?.result?.result?.formula_design;
      if (!result) throw new Error(completed.events?.at(-1)?.reason || `Deep Compose ended as ${completed.state}.`);
    } else {
      result = await request("/v2/workbench/formula-chat", {
        method: "POST",
        body: JSON.stringify({
          schema_version: "inventory-grounded-formula-chat-request-v2",
          ...payload,
        }),
      });
    }
    appendFormulaChatBubble("assistant", result.assistant_message || "The brief needs clarification before I can create the formula.");
    renderFormulaDesign(result);
    if (result.formula_name) $('[name="formula_name"]', form).value = result.formula_name;
    $('[name="message"]', form).value = "";
    submit.textContent = result.optimized_formula ? "Refine this formula" : "Try clarified brief";
    notify(result.optimized_formula ? "Inventory-grounded composition plan created." : "Clarification required before formulation.");
  } catch (error) {
    appendFormulaChatBubble("assistant", `I could not create that draft: ${error.message}`);
    submit.textContent = previous ? "Refine this formula" : "Create my formula";
    notify(error.message, true);
  } finally {
    submit.disabled = false;
  }
});

$("#formula-chat-reset").addEventListener("click", resetFormulaChat);

$("#formula-download").addEventListener("click", () => {
  const result = state.formulaChat.result;
  if (!result) return;
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${String(result.formula_name || "formula-draft").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "formula-draft"}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  notify("Read-only formula draft downloaded.");
});

// The sheet's arithmetic and markup live in bench-sheet.js (pure, node-tested).
function buildBenchSheet(result, variantIndex) {
  const selected = selectedFormulaVariant(result, variantIndex);
  const rows = selected.formula?.rows || [];
  const variants = result.design_variants || [];
  $("#bench-sheet").innerHTML = benchSheetHtml({
    formulaName: result.formula_name,
    variantLabel: variants.length > 1 ? (variants[variantIndex]?.label || `Alternative ${variantIndex + 1}`) : "",
    dateText: new Date().toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }),
    totals: selected.formula?.separate_totals || {},
    rows,
    critic: selected.critic,
  });
  return rows.length;
}

$("#formula-print-bench").addEventListener("click", () => {
  const result = state.formulaChat.result;
  if (!result) return;
  if (!buildBenchSheet(result, state.formulaChat.variantIndex || 0)) {
    notify("There is no formula to print yet. Clarify the brief first.", true);
    return;
  }
  document.body.classList.add("printing-bench-sheet");
  window.addEventListener("afterprint", () => document.body.classList.remove("printing-bench-sheet"), { once: true });
  window.print();
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

function loadOmissionRows(rows) {
  if (!Array.isArray(rows) || rows.length < 2 || rows.length > 60) throw new Error("Load two to sixty exact control rows.");
  const fields = ["stock_id", "identity_name", "amount_decimal", "amount_unit", "stock_fraction_decimal", "fraction_basis", "carrier"];
  state.omissionRows = rows.map((row) => Object.fromEntries(fields.map((field) => [field, row[field] ?? null])));
  const choices = $("#omission-stock-choices");
  choices.replaceChildren();
  state.omissionRows.forEach((row) => {
    const block = document.createElement("div");
    const title = document.createElement("p");
    title.textContent = `${row.identity_name}: ${row.amount_decimal} ${row.amount_unit} · ${row.stock_fraction_decimal} ${row.fraction_basis}`;
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
  $("#omission-input-help").textContent = rows.every((r) => r.amount_unit === "mg" && r.fraction_basis === "w/w")
    ? "Choose a mobile ingredient to omit; protect recognizers you want kept. Stock identity is supplied evidence, not independently verified."
    : "These rows lack a common mg / w/w basis. The quantitative plan will hold; you can still record a simple personal observation below. No density is guessed.";
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
$("#omission-plan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $('button[type="submit"]', form);
  button.disabled = true;
  try {
    const data = formData(form);
    const selected = (kind) => $$(`[data-omission-kind="${kind}"]:checked`, form).map((node) => node.value);
    if (!state.omissionRows.length || !selected("omit").length) throw new Error("Load a control and choose the material to omit.");
    const blanks = data.blank_carrier && data.blank_stock_id
      ? { [data.blank_carrier]: { stock_id: data.blank_stock_id, carrier: data.blank_carrier } } : {};
    const submitted = await request("/v2/engine-jobs", { method: "POST", body: JSON.stringify({
      schema_version: "lab-engine-job-request-v2", job_type: "OMISSION_COMPARISON_PLAN",
      requester: "omission-planning-ui", idempotency_key: crypto.randomUUID(),
      payload: { schema_version: "omission-comparison-plan-request-v1", control_rows: state.omissionRows,
        omit_stock_ids: selected("omit"), protected_stock_ids: selected("protect"), carrier_blanks: blanks,
        goal: data.goal, mode: data.mode, seed: 17 },
    }) });
    let completed = submitted;
    const terminal = new Set(["SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED"]);
    for (let i = 0; i < 120 && !terminal.has(completed.state); i += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      completed = await request(`/v2/engine-jobs/${encodeURIComponent(submitted.id)}`);
    }
    const handoff = completed.result?.result?.result;
    if (!handoff?.omission_plan) throw new Error(`Planning job ${submitted.id}: ${completed.state}. It remains available without resubmitting.`);
    const output = $("#omission-plan-output"); output.replaceChildren();
    const summary = document.createElement("p");
    summary.textContent = handoff.omission_plan.state === "CONTROLLED_OMISSION_DESIGN_READY"
      ? `Comparison proposed: ${data.goal}. Retained doses unchanged. Nothing was compounded, reserved, or evaluated. This is not yet an executable blind session.`
      : `Quantitative comparison withheld: ${(handoff.omission_plan.reason_codes || []).join(", ")}. You may still use the ordinary observation form.`;
    const details = document.createElement("details"); const heading = document.createElement("summary");
    heading.textContent = "Exact planning receipt"; const receipt = document.createElement("pre");
    receipt.textContent = JSON.stringify(handoff, null, 2); details.append(heading, receipt); output.append(summary, details);
    notify("Comparison planning finished. No bottle or inventory changes.");
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
});

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

window.addEventListener("hashchange", () => {
  const requested = location.hash.slice(1) || "improve";
  if ($(`[data-panel="${requested}"]`)) navigate(requested);
});

navigate(location.hash.slice(1) || "improve");
refresh().catch((error) => notify(error.message, true));
