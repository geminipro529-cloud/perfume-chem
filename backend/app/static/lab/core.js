"use strict";

// Shared by every page: the API client, messages, form helpers, refresh and navigation.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

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
    turns: [],
    designedAt: null,
  },
  improve: {
    jobId: null,
    pollCancelled: false,
    pollAbort: null,
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

const OFFLINE_TEXT = "Can't reach the app on this PC. Is it still running?";
const MESSAGE_LIMIT = 200;
let offlineFailures = 0;

function notify(message, error = false) {
  const node = $("#status");
  node.textContent = message;
  node.classList.toggle("is-error", error);
  // Tagged so the next successful request can clear a "can't reach the app" message.
  if (String(message).includes(OFFLINE_TEXT)) node.dataset.offline = "true";
  else delete node.dataset.offline;
}

// The server is reachable again: drop every message that said it was not.
function clearOfflineMessages() {
  const status = $("#status");
  if (status.dataset.offline) {
    status.textContent = "";
    status.classList.remove("is-error");
    delete status.dataset.offline;
  }
  $$(".form-error[data-offline]").forEach((box) => box.remove());
  const errors = stockView.basketErrors || {};
  const stale = Object.keys(errors).filter((id) => String(errors[id]).includes(OFFLINE_TEXT));
  if (stale.length) {
    stale.forEach((id) => { delete errors[id]; });
    if (state.projectInventory) renderProjectInventory($("#project-inventory-search").value);
  }
}

function capMessage(text) {
  const value = String(text);
  return value.length > MESSAGE_LIMIT ? `${value.slice(0, MESSAGE_LIMIT - 1)}…` : value;
}

// Server text in plain words: one pair of surrounding quotes off, and not longer than a line or two.
function plainServerText(text) {
  let value = String(text ?? "").trim();
  if (value.length >= 2 && (value[0] === "'" || value[0] === '"') && value.endsWith(value[0])) value = value.slice(1, -1).trim();
  return capMessage(value);
}

const PYDANTIC_WORDS = [
  [/^Field required$/, () => "required"],
  [/^String should have at least 1 character$/, () => "required"],
  [/^String should have at most (\d+) characters?$/, (m) => `too long (at most ${m[1]} characters)`],
  [/^Input should be greater than or equal to (\S+)$/, (m) => `must be ${m[1]} or more`],
  [/^Input should be greater than (\S+)$/, (m) => `must be more than ${m[1]}`],
  [/^Input should be less than or equal to (\S+)$/, (m) => `must be ${m[1]} or less`],
  [/^Input should be less than (\S+)$/, (m) => `must be less than ${m[1]}`],
  [/^Input should be a valid number/, () => "must be a number"],
  [/^Input should be a finite number/, () => "must be a number"],
];

function plainValidationText(text) {
  const value = String(text ?? "");
  for (const [pattern, words] of PYDANTIC_WORDS) {
    const match = value.match(pattern);
    if (match) return words(match);
  }
  return capMessage(value);
}

// A routine success message must not erase an error the user has not dismissed yet.
function notifyRoutine(message) {
  if ($("#status").classList.contains("is-error")) return;
  notify(message);
}

function fieldWords(name) {
  const text = String(name || "").replaceAll("_", " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "This field";
}

const REQUEST_TIMEOUT_MS = 120000;

async function request(path, options = {}) {
  // base: another API root on this app (the liking card posts to /api/v1/feedback).
  const { timeoutMs, base = API, ...fetchOptions } = options;
  // timeoutMs: 0 means no limit (slow synchronous server work); undefined gets the default.
  const limitMs = timeoutMs === undefined ? REQUEST_TIMEOUT_MS : timeoutMs;
  const controller = new AbortController();
  const timer = limitMs > 0 ? setTimeout(() => controller.abort(), limitMs) : null;
  let response;
  let payload;
  const failuresAtStart = offlineFailures;
  try {
    response = await fetch(`${base}${path}`, {
      headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
      ...fetchOptions,
      signal: controller.signal,
    });
    payload = await response.json().catch(() => ({}));
  } catch (error) {
    if (controller.signal.aborted) {
      const wait = limitMs % 60000 === 0
        ? `${limitMs / 60000} minute${limitMs === 60000 ? "" : "s"}`
        : `${Math.round(limitMs / 1000)} seconds`;
      const method = String(fetchOptions.method || "GET").toUpperCase();
      throw new Error(`The app didn't answer within ${wait}.${method === "GET" ? "" : " It may still finish, so check before you try again."}`);
    }
    offlineFailures += 1;
    throw new Error(OFFLINE_TEXT);
  } finally {
    if (timer) clearTimeout(timer);
  }
  if (!response.ok) {
    // Network runs need the lab password: a signed-out device goes to the sign-in page.
    if (response.status === 401 && response.headers.get("X-Lab-Login") === "required") {
      window.location.href = "/login";
    }
    const rawText = typeof payload?.detail === "string" ? payload.detail : payload?.error?.message;
    const serverText = rawText ? plainServerText(rawText) : rawText;
    let items = [];
    let message;
    if (Array.isArray(payload?.detail)) {
      items = payload.detail.map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc.filter((part) => typeof part === "string" && part !== "body") : [];
        const field = loc.length ? loc[loc.length - 1] : "";
        return { field, path: loc.join("."), msg: plainValidationText(item.msg || "is not valid") };
      });
      message = capMessage(items.map((item) => `${fieldWords(item.field)}: ${item.msg}`).join("; "));
    } else if (response.status === 409) {
      message = capMessage(serverText ? `That already exists. ${serverText}` : "That already exists.");
    } else {
      message = serverText || `The server returned ${response.status}.`;
    }
    const error = new Error(message);
    error.status = response.status;
    error.code = payload?.error?.code || "";
    error.serverText = serverText || "";
    error.items = items;
    error.fields = items.map((item) => item.field).filter(Boolean);
    throw error;
  }
  // Not while another request failed to connect meanwhile: that failure's message is newer.
  if (offlineFailures === failuresAtStart) clearOfflineMessages();
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

async function refresh() {
  const [dashboard, materials, stocks, formulas, bottles, experiments, formulaLibrary, projectInventory] = await Promise.all([
    request("/dashboard"), request("/materials"), request("/stocks"), request("/formulas"), request("/bottles"), request("/experiments"), request("/v2/workbench/formula-library"), request("/v2/workbench/current-inventory"),
  ]);
  Object.assign(state, { materials, stocks, formulas, bottles, experiments, formulaLibrary: formulaLibrary.sources || [], projectInventory });
  $("#dashboard-counts").innerHTML = overviewTiles(dashboard.counts, projectInventory.counts, (projectInventory.stocks || []).length).map(([label, value]) => `<article class="metric"><strong>${value}</strong><span>${escapeHtml(label)}</span></article>`).join("");
  $("#dashboard-warnings").innerHTML = dashboard.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  recordList("#material-list", materials, "canonical_name", (row) => row.cas_number || "No CAS recorded");
  recordList("#formula-list", formulas, "name", () => "Immutable versions are appended separately");
  recordList("#bottle-list", bottles, "label", (row) => row.status);
  smellLog?.setBottles(bottles);
  recordList("#experiment-list", experiments, "name", (row) => row.status);
  renderProjectInventory($("#project-inventory-search").value);
  if (typeof editorInventoryChanged === "function") editorInventoryChanged();
  if (typeof makeNowInventoryChanged === "function") makeNowInventoryChanged();
  // A design shown before the inventory arrived (a restored draft) picks up its basket order.
  if (state.formulaChat.result) renderFormulaRows(selectedFormulaVariant(state.formulaChat.result).formula?.rows || []);
  updateSelectors();
  syncImproveSourceMode();
  notifyRoutine("Inventory and ledger refreshed.");
}

// False until the start-up navigate() has run: the first Tab must still reach the skip link.
let pageStarted = false;

function navigate(view) {
  $$(".nav-item").forEach((item) => item.classList.toggle("is-active", item.dataset.view === view));
  $$(".nav-item").forEach((item) => {
    if (item.dataset.view === view) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  $$(".view").forEach((panel) => panel.classList.toggle("is-visible", panel.dataset.panel === view));
  history.replaceState(null, "", `#${view}`);
  if (pageStarted) {
    // Switching views makes no request, so a routine "refreshed" line would go stale; an error stays.
    if (!$("#status").classList.contains("is-error")) notify("");
    const heading = $(`[data-panel="${view}"] h1`);
    // Only some headings carry tabindex in the HTML; without one, focus() silently does nothing.
    if (heading && !heading.hasAttribute("tabindex")) heading.tabIndex = -1;
    if (heading) heading.focus?.({ preventScroll: true });
  }
  if (view === "science") {
    loadScienceAuthority().catch((error) => notify(error.message, true));
  }
  if (view === "editor" && typeof editorSideShown === "function") editorSideShown();
  if (view === "nose" && typeof noseShown === "function") noseShown();
  if (view === "make" && typeof makeNowShown === "function") makeNowShown();
  if (view === "batch" && typeof phoneBenchShown === "function") phoneBenchShown();
}

function formData(form) { return Object.fromEntries(new FormData(form).entries()); }

function fieldLabel(form, name) {
  const input = [...form.elements].find((element) => element.name === name);
  const label = input?.closest("label") || (input?.id ? form.querySelector(`label[for="${input.id}"]`) : null);
  if (!label) return fieldWords(name);
  const copy = label.cloneNode(true);
  copy.querySelectorAll("span, small, select, input, textarea, button").forEach((node) => node.remove());
  return copy.textContent.replace(/\s+/g, " ").trim() || fieldWords(name);
}

function clearFormError(form) {
  form.querySelectorAll("[aria-invalid]").forEach((input) => {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-describedby");
  });
  document.getElementById(`${form.id}-error`)?.remove();
}

function showFormError(form, error, title = "Not saved.") {
  // Each listed item is its own sentence; the field that holds it is the nested path, else the last name.
  const names = (error.items || []).map((item) => [item.path, item.field].find((name) => name
    && [...form.elements].some((element) => element.name === name)) || "");
  const lines = error.items?.length
    ? [capMessage(error.items.map((item, index) => {
      const name = names[index] || item.field;
      return `${name ? fieldLabel(form, name) : "This form"}: ${item.msg}`;
    }).join("; "))]
    : capMessage(error.message).split("\n");
  const id = `${form.id}-error`;
  let box = document.getElementById(id);
  if (!box) {
    box = document.createElement("div");
    box.className = "form-error";
    box.setAttribute("role", "alert");
    box.id = id;
    const submit = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
    const anchor = submit?.closest(".button-row, .actions, .row") || submit;
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
    else form.appendChild(box);
  }
  box.replaceChildren();
  if (String(error.message).includes(OFFLINE_TEXT)) box.dataset.offline = "true";
  else delete box.dataset.offline;
  const strong = document.createElement("strong");
  strong.textContent = title;
  box.append(strong, " ");
  lines.forEach((line, index) => {
    if (index) box.appendChild(document.createElement("br"));
    box.appendChild(document.createTextNode(line));
  });
  (error.items?.length ? names : error.fields || []).filter(Boolean).forEach((name) => {
    [...form.elements].filter((element) => element.name === name).forEach((input) => {
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", id);
    });
  });
  return lines;
}

function bindForm(selector, handler) {
  $(selector).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    clearFormError(form);
    const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type])');
    buttons.forEach((button) => { button.disabled = true; });
    try {
      try { await handler(formData(form)); }
      catch (error) { notify(showFormError(form, error).join("; "), true); return; }
      notify("Record committed.");
      // The record is saved; a failed refresh must not show "Not saved." and invite a duplicate.
      await refresh().catch((error) => notify(`Saved, but the lists didn't refresh: ${error.message}`, true));
    } finally { buttons.forEach((button) => { button.disabled = false; }); }
  });
}

// Like bindForm for the forms that keep their own success behaviour: handler(data, form) does the
// save and renders its own result. A failed save shows the inline "Not saved." box and marks a 422
// field; the submit button stays disabled while the save is in flight so a second click can't save twice.
const savingForms = new WeakSet();
// A local server can answer before a double click's second click lands; after a good save the
// button stays disabled this long (from the first click) so that click can't save again.
const SAVE_COOLDOWN_MS = 800;

function bindSavingForm(selector, handler) {
  $(selector).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (savingForms.has(form)) return;
    savingForms.add(form);
    clearFormError(form);
    const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type])');
    buttons.forEach((button) => { button.disabled = true; });
    // The handler calls saved() as soon as its save request has succeeded. A later failure
    // (re-render, refresh) must not show "Not saved." or re-enable a retry that would save twice.
    let didSave = false;
    const startedAt = Date.now();
    try {
      await handler(formData(form), form, () => { didSave = true; });
    } catch (error) {
      if (didSave) notify(`Saved, but the lists didn't refresh: ${error.message}`, true);
      else notify(showFormError(form, error).join("; "), true);
    } finally {
      const wait = didSave ? SAVE_COOLDOWN_MS - (Date.now() - startedAt) : 0;
      if (wait > 0) await new Promise((resolve) => { setTimeout(resolve, wait); });
      buttons.forEach((button) => { button.disabled = false; });
      savingForms.delete(form);
    }
  });
}

// A bottle or stock starts with 0 to 10,000 g; 0 is an empty bottle.
const MAX_INITIAL_MASS_G = 10000;
function checkedInitialMassG(value) {
  const text = String(value ?? "").trim();
  const mass = text === "" ? NaN : Number(text);
  if (!Number.isFinite(mass) || mass < 0 || mass > MAX_INITIAL_MASS_G) {
    const error = new Error("Initial mass, g: must be a number from 0 to 10,000 g.");
    error.items = [{ field: "initial_mass_g", msg: "must be a number from 0 to 10,000 g" }];
    error.fields = ["initial_mass_g"];
    throw error;
  }
  return mass;
}
// The browser stops a submit with an out-of-range number before our handler runs; show the same
// inline box there instead of a hover bubble.
function showMassLimitInline(selector) {
  const form = $(selector);
  form.elements.initial_mass_g.addEventListener("invalid", (event) => {
    event.preventDefault();
    clearFormError(form);
    try { checkedInitialMassG(event.target.value); } catch (error) { showFormError(form, error); }
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
const newRequestId = (prefix) => globalThis.crypto?.randomUUID?.()
  || `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
