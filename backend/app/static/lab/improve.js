"use strict";

// Improve page: goal analysis of a bottle or formula, engine jobs and the physical change record.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, bench, bottles, experiments, perfumery, assistant, science, boot.

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

const ENGINE_JOB_TERMINAL_STATES = new Set(["SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED"]);
const ENGINE_JOB_DEFAULT_WAIT_MS = 15 * 60 * 1000;
// The server lets a claimed job run its timeout_seconds plus a 60 s lease grace; wait a little longer.
const ENGINE_JOB_RUN_GRACE_MS = 90 * 1000;
const ENGINE_WORKER_CHECK_MS = 15 * 1000;
const ENGINE_POLL_REQUEST_TIMEOUT_MS = 20 * 1000;
const ENGINE_JOB_FAILURE_WORDS = {
  FAILED_CLOSED_WORKER_STOPPED: "The analysis stopped because the server restarted or shut down, so it has no result. Asking again with the same formula and goals shows this result again; change either one to start a new analysis.",
  FAILED_CLOSED_WORKER_LOST: "The analysis worker stopped while it was running this job, so the job was closed without a result.",
  ENGINE_JOB_TIMEOUT: "The job ran past its time limit and was stopped without a result.",
  ENGINE_JOB_EXECUTION_FAILED: "The analysis hit an internal error and stopped without a result.",
};

function formatElapsed(milliseconds) {
  const total = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours) return `${hours} h ${minutes} min`;
  if (minutes) return `${minutes} min ${seconds} s`;
  return `${seconds} s`;
}

function engineJobFailureText(snapshot) {
  const code = snapshot.result?.result?.code || snapshot.result?.validation_state || snapshot.events?.at(-1)?.reason;
  return ENGINE_JOB_FAILURE_WORDS[code]
    || `The job ended as ${humanize(snapshot.state)}${code ? ` (${humanize(code)})` : ""}, without a result.`;
}

function abortableDelay(milliseconds, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(signal.reason); return; }
    const timer = window.setTimeout(() => { signal?.removeEventListener("abort", onAbort); resolve(); }, milliseconds);
    function onAbort() { window.clearTimeout(timer); reject(signal.reason); }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

async function liveEngineWorkerCount() {
  const status = await request("/v2/engine-workers/status", { timeoutMs: ENGINE_POLL_REQUEST_TIMEOUT_MS });
  return Number(status.live) || 0;
}

// Like liveEngineWorkerCount, but a failed, timed-out or 404 status request (an older server)
// is "worker status unknown" (null) rather than an error, so the job keeps being polled.
async function liveEngineWorkerCountOrUnknown() {
  try {
    return await liveEngineWorkerCount();
  } catch (error) {
    return null;
  }
}

// Shows the no-worker message in `area` and resolves once a re-check finds a live worker.
function waitForEngineWorker(area, jobState, signal) {
  return new Promise((resolve, reject) => {
    const box = document.createElement("div");
    box.className = "inline-warning engine-worker-missing";
    const message = document.createElement("p");
    message.textContent = `No analysis worker is running, so this job can't ${jobState === "QUEUED" ? "start" : "finish"}. Start the app with \`python run_api_server.py\`, or run \`python -m app.services.engine_job_worker\` from backend/. Then press Check again.`;
    const checkStatus = document.createElement("p");
    checkStatus.className = "field-help";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quiet-button";
    button.textContent = "Check again";
    box.append(message, button, checkStatus);
    area.replaceChildren(box);
    function onAbort() { reject(signal.reason); }
    signal?.addEventListener("abort", onAbort, { once: true });
    button.addEventListener("click", async () => {
      button.disabled = true;
      checkStatus.textContent = "Checking…";
      try {
        if (await liveEngineWorkerCount() > 0) {
          signal?.removeEventListener("abort", onAbort);
          resolve();
          return;
        }
        checkStatus.textContent = `Still no worker at ${new Date().toLocaleTimeString()}.`;
      } catch (error) {
        checkStatus.textContent = `Could not check: ${error.message}`;
      }
      button.disabled = false;
    });
  });
}

// Polls one engine job until it reaches a terminal state. Pauses with a plain message while no
// worker is alive, and throws a plain-words error for FAILED jobs. Other terminal
// snapshots are returned unchanged so each caller keeps its own result handling.
async function waitForEngineJob(jobId, { area, intervalMs = 1000, signal, stillRunningMessage } = {}) {
  const path = `/v2/engine-jobs/${encodeURIComponent(jobId)}`;
  const waitStartedAt = Date.now();
  let runningSince = null;
  let nextWorkerCheck = 0;
  const progress = document.createElement("p");
  area.replaceChildren(progress);
  for (;;) {
    if (signal?.aborted) throw signal.reason;
    const snapshot = await request(path, { timeoutMs: ENGINE_POLL_REQUEST_TIMEOUT_MS });
    if (ENGINE_JOB_TERMINAL_STATES.has(snapshot.state)) {
      if (snapshot.state === "FAILED") {
        const reason = engineJobFailureText(snapshot);
        progress.textContent = reason;
        area.replaceChildren(progress);
        const failed = new Error(reason);
        failed.jobEnded = true;
        throw failed;
      }
      area.replaceChildren();
      return snapshot;
    }
    if (Date.now() >= nextWorkerCheck) {
      nextWorkerCheck = Date.now() + ENGINE_WORKER_CHECK_MS;
      if (await liveEngineWorkerCountOrUnknown() === 0) {
        await waitForEngineWorker(area, snapshot.state, signal);
        area.replaceChildren(progress);
        runningSince = null;
        nextWorkerCheck = Date.now() + ENGINE_WORKER_CHECK_MS;
        continue;
      }
    }
    // Queued jobs wait as long as a worker may pick them up. The limit starts at the first
    // running snapshot: the job's timeout plus the server's lease grace.
    if (snapshot.state === "QUEUED") {
      runningSince = null;
    } else if (runningSince === null) {
      runningSince = Date.now();
    }
    if (runningSince !== null) {
      const timeoutMs = snapshot.timeout_seconds ? snapshot.timeout_seconds * 1000 : ENGINE_JOB_DEFAULT_WAIT_MS;
      if (Date.now() - runningSince > timeoutMs + ENGINE_JOB_RUN_GRACE_MS) {
        area.replaceChildren();
        const stillRunning = new Error(stillRunningMessage || "The job is still running. Its durable job can be checked again without resubmitting the request.");
        stillRunning.jobStillRunning = true;
        throw stillRunning;
      }
    }
    const elapsed = Date.now() - (runningSince ?? waitStartedAt);
    progress.textContent = `${runningSince === null ? "Waiting in the queue" : "Running"} for ${formatElapsed(elapsed)}.`;
    await abortableDelay(intervalMs, signal);
  }
}

async function pollEngineJob(jobId) {
  return waitForEngineJob(jobId, {
    area: $("#improve-running-detail"),
    signal: state.improve.pollAbort.signal,
    stillRunningMessage: "The analysis is still running. Its durable job can be checked again without resubmitting the request.",
  });
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
      commandId: newRequestId("command"),
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
    state.improve.evaluationCommandId = newRequestId("command");
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
  state.improve.pollAbort = new AbortController();
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
        idempotency_key: newRequestId("job"),
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
  state.improve.pollAbort?.abort(new Error("Analysis cancelled."));
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
