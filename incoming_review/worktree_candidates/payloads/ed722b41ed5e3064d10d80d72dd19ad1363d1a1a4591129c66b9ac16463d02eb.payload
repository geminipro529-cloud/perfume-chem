"use strict";

const API = "/api/v1/solforge/workbench";
const MAX_FILE_BYTES = 262144;
const MAX_REQUEST_BYTES = 524288;
const EXPECTED_SCHEMAS = Object.freeze({
  case: "solforge_case_v1",
  hypotheses: "sol_hypothesis_set_v1",
});

const packets = { case: null, hypotheses: null };
let runtimeReady = false;

function element(id) {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing workbench element: ${id}`);
  return found;
}

function setText(id, value) {
  element(id).textContent = value === null || value === undefined || value === "" ? "—" : String(value);
}

function setUiStatus(message, kind = "neutral") {
  const node = element("ui-status");
  node.textContent = message;
  node.classList.toggle("is-error", kind === "error");
  node.classList.toggle("is-success", kind === "success");
}

function formatBytes(value) {
  if (!Number.isFinite(value)) return "—";
  if (value < 1024) return `${value} B`;
  return `${(value / 1024).toFixed(1)} KiB`;
}

function appendList(node, values, emptyMessage) {
  node.replaceChildren();
  if (!Array.isArray(values) || values.length === 0) {
    const item = document.createElement("li");
    item.className = "is-empty";
    item.textContent = emptyMessage;
    node.append(item);
    return;
  }
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = String(value);
    node.append(item);
  });
}

function appendKeyValue(node, label, value) {
  const row = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
  row.append(term, description);
  node.append(row);
}

function resetPacket(kind) {
  packets[kind] = null;
  setText(`${kind}-file-name`, "Not selected");
  setText(`${kind}-schema`, "—");
  setText(`${kind}-size`, "—");
  updateCompileState();
}

function updateCompileState() {
  const packetsReady = Boolean(packets.case && packets.hypotheses);
  const ready = packetsReady && runtimeReady;
  element("compile-experiment").disabled = !ready;
  if (ready) {
    setUiStatus("Both closed packets are ready for server verification.", "success");
  } else if (packetsReady) {
    setUiStatus("Packets are valid, but the local runtime is not ready.", "error");
  }
}

async function loadPacket(kind, input) {
  const file = input.files && input.files[0];
  resetPacket(kind);
  if (!file) {
    setUiStatus("Select both valid packets to continue.");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".json")) {
    input.value = "";
    setUiStatus(`${kind} packet must be a .json file.`, "error");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    input.value = "";
    setUiStatus(`${kind} packet exceeds the 256 KiB browser limit.`, "error");
    return;
  }

  let parsed;
  try {
    parsed = JSON.parse(await file.text());
  } catch (_error) {
    input.value = "";
    setUiStatus(`${kind} packet is not valid UTF-8 JSON.`, "error");
    return;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    input.value = "";
    setUiStatus(`${kind} packet must be one JSON object.`, "error");
    return;
  }
  if (parsed.schema_version !== EXPECTED_SCHEMAS[kind]) {
    input.value = "";
    setUiStatus(`${kind} packet schema must be ${EXPECTED_SCHEMAS[kind]}.`, "error");
    return;
  }

  packets[kind] = parsed;
  setText(`${kind}-file-name`, file.name);
  setText(`${kind}-schema`, parsed.schema_version);
  setText(`${kind}-size`, formatBytes(file.size));
  updateCompileState();
}

function renderRuntimeBlockers(values) {
  const node = element("runtime-blockers");
  node.replaceChildren();
  (values || []).forEach((value) => {
    const item = document.createElement("li");
    item.textContent = String(value);
    node.append(item);
  });
}

function renderRuntimeStatus(status) {
  const dot = element("runtime-dot");
  dot.classList.remove("is-checking", "is-ready", "is-blocked");
  dot.classList.add(status.ready ? "is-ready" : "is-blocked");
  setText("runtime-state", status.ready ? "Configured and within quota" : "Blocked by local configuration");
  setText("completed-runs", `${status.completed_run_count} / ${status.max_runs}`);
  setText("artifact-use", `${formatBytes(status.artifact_bytes)} / ${formatBytes(status.max_artifact_bytes)}`);
  setText("runtime-concurrency", status.max_concurrent_runs);
  renderRuntimeBlockers(status.blockers);
  const contractViolation = status.artifact_download_available !== false
    || Object.values(status.authority_flags || {}).some(Boolean);
  runtimeReady = Boolean(status.ready) && !contractViolation;
  if (contractViolation) {
    setUiStatus("Runtime status violated the closed authority contract.", "error");
  }
  updateCompileState();
}

async function refreshRuntimeStatus() {
  try {
    const response = await fetch(`${API}/status`, { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail?.message || "Runtime status unavailable");
    renderRuntimeStatus(payload);
  } catch (error) {
    runtimeReady = false;
    const dot = element("runtime-dot");
    dot.classList.remove("is-checking", "is-ready");
    dot.classList.add("is-blocked");
    setText("runtime-state", "Runtime status unavailable");
    renderRuntimeBlockers([error.message]);
    updateCompileState();
  }
}

function renderBlockers(result) {
  appendList(element("result-blockers"), result.blockers, "No reported blocker.");
}

function renderLimitations(result) {
  appendList(
    element("result-limitations"),
    result.evidence_limitations,
    "No additional limitation was recorded; the all-false authority ceiling still applies.",
  );
}

function renderArms(result) {
  const target = element("result-arms");
  target.replaceChildren();
  if (!Array.isArray(result.arms) || result.arms.length === 0) {
    const note = document.createElement("p");
    note.textContent = "No arm was compiled for this decision.";
    target.append(note);
    return;
  }
  result.arms.forEach((arm) => {
    const card = document.createElement("article");
    card.className = "arm";
    const title = document.createElement("h4");
    title.textContent = `${arm.arm_id} · blind ${arm.blind_code}`;
    const mass = document.createElement("p");
    mass.textContent = `Total active mass: ${arm.total_active_mass_g} g`;
    const factors = document.createElement("p");
    const factorText = Object.entries(arm.factor_presence || {})
      .map(([name, present]) => `${name}=${present ? "present" : "absent"}`)
      .join(", ");
    factors.textContent = factorText || "No factor-presence map reported";
    const hash = document.createElement("code");
    hash.textContent = arm.sample_sha256;
    card.append(title, mass, factors, hash);
    target.append(card);
  });
}

function renderInventory(result) {
  const target = element("result-inventory");
  target.replaceChildren();
  if (!Array.isArray(result.inventory_statuses) || result.inventory_statuses.length === 0) {
    appendKeyValue(target, "Status", "No inventory status rows reported");
    return;
  }
  result.inventory_statuses.forEach(([material, status]) => appendKeyValue(target, material, status));
}

function renderLineage(result) {
  const target = element("result-lineage");
  target.replaceChildren();
  appendKeyValue(target, "Registry SHA-256", result.registry_sha256);
  appendKeyValue(target, "Manifest SHA-256", result.manifest_sha256);
  appendKeyValue(target, "Compiled SHA-256", result.compiled_experiment_sha256);
  appendKeyValue(target, "Admitted modules", (result.admitted_module_ids || []).join(", "));
  appendKeyValue(target, "History", (result.history || []).join(" → "));
  appendKeyValue(target, "Hypothesis", result.selected_hypothesis_id);
}

function renderRecords(result) {
  const target = element("result-records");
  target.replaceChildren();
  (result.records || []).forEach((record) => {
    const card = document.createElement("div");
    card.className = "record";
    const filename = document.createElement("strong");
    filename.textContent = record.filename;
    const schema = document.createElement("span");
    schema.textContent = record.schema_version;
    const recordHash = document.createElement("span");
    recordHash.textContent = `record ${record.record_sha256}`;
    const fileHash = document.createElement("span");
    fileHash.textContent = `file ${record.file_sha256}`;
    card.append(filename, schema, recordHash, fileHash);
    target.append(card);
  });
  if (target.childElementCount === 0) {
    const note = document.createElement("p");
    note.textContent = "No verified artifact records reported.";
    target.append(note);
  }
}

function renderAuthority(result) {
  const target = element("result-authority");
  target.replaceChildren();
  Object.entries(result.authority_flags || {}).forEach(([name, granted]) => {
    appendKeyValue(target, name, granted ? "TRUE — CONTRACT VIOLATION" : "false");
  });
  setText(
    "download-posture",
    result.artifact_download_available
      ? "Artifact download unexpectedly enabled — do not proceed."
      : "Artifact download unavailable. Physical execution and release authority remain false.",
  );
}

function renderResult(result) {
  setText("result-run-id", result.run_id);
  setText("result-stage", result.stage);
  setText("result-decision", result.decision);
  setText("result-delta", result.delta_kind);
  setText("result-next-action", result.next_action);
  renderBlockers(result);
  renderLimitations(result);
  renderArms(result);
  renderInventory(result);
  renderLineage(result);
  renderRecords(result);
  renderAuthority(result);
  const resultStage = element("result");
  resultStage.hidden = false;
  resultStage.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function compileExperiment() {
  if (!packets.case || !packets.hypotheses || !runtimeReady) return;
  const button = element("compile-experiment");
  button.disabled = true;
  setUiStatus("Verifying bindings and compiling through the admitted runtime…");
  const requestBody = JSON.stringify({
    schema_version: "solforge_workbench_design_request_v1",
    case: packets.case,
    hypotheses: packets.hypotheses,
  });
  if (new TextEncoder().encode(requestBody).byteLength > MAX_REQUEST_BYTES) {
    setUiStatus("Combined packets exceed the 512 KiB request limit.", "error");
    updateCompileState();
    return;
  }
  try {
    const response = await fetch(`${API}/design`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: requestBody,
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail || {};
      throw new Error([detail.code, detail.message].filter(Boolean).join(": ") || "Workbench rejected the request");
    }
    renderResult(payload);
    setUiStatus(`Verified ${payload.decision} result ${payload.run_id}.`, "success");
  } catch (error) {
    setUiStatus(error.message || "Workbench request failed.", "error");
  } finally {
    updateCompileState();
  }
}

element("case-file").addEventListener("change", (event) => loadPacket("case", event.currentTarget));
element("hypotheses-file").addEventListener("change", (event) => loadPacket("hypotheses", event.currentTarget));
element("compile-experiment").addEventListener("click", compileExperiment);
refreshRuntimeStatus();
