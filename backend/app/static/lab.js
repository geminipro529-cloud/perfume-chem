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
  const { timeoutMs, ...fetchOptions } = options;
  // timeoutMs: 0 means no limit (slow synchronous server work); undefined gets the default.
  const limitMs = timeoutMs === undefined ? REQUEST_TIMEOUT_MS : timeoutMs;
  const controller = new AbortController();
  const timer = limitMs > 0 ? setTimeout(() => controller.abort(), limitMs) : null;
  let response;
  let payload;
  const failuresAtStart = offlineFailures;
  try {
    response = await fetch(`${API}${path}`, {
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

const STOCK_SOLVENT_UPPER = new Set(["dpg", "dep", "ipm", "tec", "bb", "pea"]);
const STOCK_BASIS_WORDS = { mass_fraction: "w/w", volume_fraction: "v/v", mass_per_volume: "w/v" };
const STOCK_NEED_SENTENCES = {
  possession_confirmation: "Confirm you own it",
  homogeneity_confirmation: "Confirm the solution is fully mixed",
  fraction_basis: "Say whether the strength is w/w or v/v",
  physical_form: "Say what form it is in",
  carrier: "Say which solvent it is in",
  final_usable_fraction_confirmation: "Confirm the strength you actually use",
  bottle_lot_and_label_receipt_missing: "Add the bottle lot and label",
  execution_stock_binding_required: "Link it to a physical bottle",
};
const STOCK_HOLD_NOTE = "Kept out of new formulas until you clear it";
const STOCK_STATUS_LABEL = { ready: "Ready", needs: "Needs details", hold: "On hold" };
const stockView = { filter: "all", solvent: "", basket: "", sort: "name", basketErrors: {}, basketBusy: new Set() };
const BASKET_CHECK_STATUSES = new Set(["from_past_cards", "conflicting"]);

function stockSolvents(stock) {
  return String(stock.carrier || "").toLowerCase().replace(/\bw\/w\b|\bv\/v\b/g, "")
    .split(/[+,]|\band\b/).map((part) => part.trim()).filter(Boolean);
}

function stockSolventName(solvent) {
  return STOCK_SOLVENT_UPPER.has(solvent) ? solvent.toUpperCase() : solvent;
}

function stockPercent(stock) {
  const value = Number(stock.fraction_percent_decimal);
  return Number.isFinite(value) ? String(Math.round(value * 1000) / 1000) : String(stock.fraction_percent_decimal || "");
}

function stockStatus(stock) {
  const fields = stock.missing_fields || [];
  if (stock.design_hold_reason === "USER_COMPOUNDING_HOLD" || fields.includes("USER_COMPOUNDING_HOLD")) return "hold";
  return stock.design_ready ? "ready" : "needs";
}

function stockIsNeat(stock) {
  return stock.fraction_basis === "neat" || (!stockSolvents(stock).length && Number(stock.fraction_percent_decimal) === 100);
}

function stockStrengthLabel(stock) {
  const basis = stock.fraction_basis;
  const solvents = stockSolvents(stock).map(stockSolventName);
  if (stockIsNeat(stock)) {
    if (stock.physical_form === "crystals") return "Neat crystals, weighed in mg";
    return /^solid/.test(stock.physical_form || "") ? "Neat solid" : "Neat";
  }
  const where = solvents.length > 1
    ? ` in ${solvents.slice(0, -1).join(", ")} and ${solvents[solvents.length - 1]}`
    : (solvents.length ? ` in ${solvents[0]}` : "");
  const percent = `${stockPercent(stock)}%`;
  if (STOCK_BASIS_WORDS[basis]) return `${percent} ${STOCK_BASIS_WORDS[basis]}${where}`;
  if (basis === "mass_fraction_starting_charge") return `${percent} w/w${where}, by starting charge`;
  return `${percent}${where}, w/w or v/v not stated`;
}

function stockNote(stock, status) {
  if (status === "ready") return "";
  // The hold marker is a hold, not a missing detail, so it is never listed here.
  const sentences = (stock.missing_fields || []).filter((field) => field !== "USER_COMPOUNDING_HOLD").map((field) => (
    STOCK_NEED_SENTENCES[String(field).toLowerCase()] || humanize(field)
  ));
  if (!sentences.length) return status === "hold" ? "" : "Some details are missing";
  return sentences.length > 2 ? `${sentences.slice(0, 2).join(". ")}. And ${sentences.length - 2} more` : sentences.join(". ");
}

function stockEl(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Baskets: older inventory payloads have no "baskets" list, and then the page shows nothing about them.
function stockBaskets() {
  const baskets = state.projectInventory?.baskets;
  return Array.isArray(baskets) ? baskets.filter((basket) => Number.isInteger(basket?.number)) : [];
}

function stockBasketNumber(stock) {
  return Number.isInteger(stock.basket) ? stock.basket : null;
}

// Solution and crystals forms of one material share a basket key; older payloads fall back to the identity.
function stockBasketKey(stock) {
  return stock.basket_key || stock.normalized_identity;
}

function stockBasketStatus(stock) {
  return ["confirmed", "from_past_cards", "conflicting"].includes(stock.basket_status) ? stock.basket_status : "none";
}

function basketName(number) {
  const basket = stockBaskets().find((item) => item.number === number);
  return basket && basket.name ? `${number} · ${basket.name}` : `Basket ${number}`;
}

function basketOptionText(number) {
  const basket = stockBaskets().find((item) => item.number === number);
  return basket && basket.name ? `${number} ${basket.name}` : `Basket ${number}`;
}

function basketWordList(numbers) {
  return numbers.length > 1 ? `${numbers.slice(0, -1).join(", ")} or ${numbers[numbers.length - 1]}` : String(numbers[0]);
}

function stockBasketCell(stock) {
  const cell = stockEl("td", "stock-basket");
  const number = stockBasketNumber(stock);
  const status = stockBasketStatus(stock);
  const label = stockEl("span", "stock-basket-label");
  if (status === "conflicting") {
    const suggestions = (stock.basket_suggestions || []).filter(Number.isInteger);
    label.textContent = suggestions.length ? `${basketWordList(suggestions)}?` : (number === null ? "Not sure?" : `${basketName(number)}?`);
  } else {
    label.textContent = number === null ? "—" : basketName(number);
  }
  cell.appendChild(label);
  if (BASKET_CHECK_STATUSES.has(status)) cell.appendChild(stockEl("span", "stock-chip stock-chip-needs stock-basket-check", "check it"));
  const controls = stockEl("div", "stock-basket-controls");
  const busy = stockView.basketBusy.has(stockBasketKey(stock));
  const select = stockEl("select", "stock-basket-select");
  select.setAttribute("aria-label", `Basket for ${stock.identity_name}, ${stockStrengthLabel(stock)}`);
  select.dataset.basketFor = stock.stock_id;
  select.append(new Option("No basket", ""), ...stockBaskets().map((basket) => new Option(basketOptionText(basket.number), String(basket.number))));
  select.value = number === null ? "" : String(number);
  select.disabled = busy;
  controls.appendChild(select);
  if (status === "from_past_cards" && number !== null) {
    const confirm = stockEl("button", "quiet-button stock-basket-confirm", `Confirm ${number}`);
    confirm.type = "button";
    confirm.dataset.confirmBasket = stock.stock_id;
    confirm.setAttribute("aria-label", `Confirm ${number} ${basketName(number).replace(/^\d+ · /, "")} for ${stock.identity_name}`);
    confirm.disabled = busy;
    controls.appendChild(confirm);
  }
  cell.appendChild(controls);
  const error = stockView.basketErrors[stock.stock_id];
  if (error) cell.appendChild(stockEl("span", "stock-row-note stock-basket-error", error));
  return cell;
}

function stockMatchesBasketFilter(stock) {
  if (!stockView.basket) return true;
  const number = stockBasketNumber(stock);
  const status = stockBasketStatus(stock);
  if (stockView.basket === "none") return number === null && status !== "conflicting";
  if (stockView.basket === "check") return BASKET_CHECK_STATUSES.has(status);
  return number !== null && String(number) === stockView.basket;
}

async function setStockBasket(stockId, basket) {
  const stocks = state.projectInventory.stocks || [];
  const stock = stocks.find((item) => item.stock_id === stockId);
  if (!stock || stockView.basketBusy.has(stockBasketKey(stock))) return;
  const identity = stock.normalized_identity;
  const key = stockBasketKey(stock);
  const name = stock.identity_name;
  delete stockView.basketErrors[stockId];
  stockView.basketBusy.add(key);
  renderProjectInventory($("#project-inventory-search").value);
  try {
    const result = await request("/v2/workbench/current-inventory/basket", {
      method: "POST",
      body: JSON.stringify({ normalized_identity: identity, basket }),
    });
    const saved = Number.isInteger(result?.basket) ? result.basket : null;
    // Every strength and form of one material sits in the same basket, so every row of it changes.
    stocks.filter((item) => stockBasketKey(item) === key).forEach((item) => {
      Object.assign(item, { basket: saved, basket_status: result?.basket_status || "confirmed", basket_suggestions: [] });
      delete stockView.basketErrors[item.stock_id];
    });
    // A design already on screen regroups under the new basket without a refresh.
    if (state.formulaChat.result) renderFormulaRows(selectedFormulaVariant(state.formulaChat.result).formula?.rows || []);
    notify(saved === null ? `Basket cleared: ${name}` : `Basket set: ${name} → ${basketOptionText(saved)}`);
  } catch (error) {
    const reason = error.code === "BASKET_LOG_CORRUPT" && error.serverText ? error.serverText : error.message;
    stockView.basketErrors[stockId] = `Basket not saved: ${reason}`;
    notify(`Basket not saved for ${name}: ${reason}`, true);
  } finally {
    stockView.basketBusy.delete(key);
    renderProjectInventory($("#project-inventory-search").value, stockId);
  }
}

function syncStockToolbar(stocks) {
  const select = $("#project-inventory-solvent");
  const found = [...new Set(stocks.flatMap(stockSolvents))].sort();
  const signature = `${found.join("|")}#${stocks.some((stock) => !stockIsNeat(stock) && !stockSolvents(stock).length)}`;
  if (select.dataset.signature !== signature) {
    select.dataset.signature = signature;
    const unrecorded = stocks.some((stock) => !stockIsNeat(stock) && !stockSolvents(stock).length);
    select.replaceChildren(new Option("Any solvent", ""), ...found.map((name) => new Option(stockSolventName(name), name)), new Option("Neat", "neat"), ...(unrecorded ? [new Option("Solvent not recorded", "unrecorded")] : []));
    if (![...select.options].some((option) => option.value === stockView.solvent)) stockView.solvent = "";
  }
  select.value = stockView.solvent;
  const baskets = stockBaskets();
  const basketSelect = $("#project-inventory-basket");
  const basketSignature = baskets.map((basket) => `${basket.number}:${basket.name}`).join("|");
  if (basketSelect.dataset.signature !== basketSignature) {
    basketSelect.dataset.signature = basketSignature;
    basketSelect.replaceChildren(new Option("All baskets", ""), new Option("No basket yet", "none"), new Option("Check it", "check"),
      ...baskets.map((basket) => new Option(basketOptionText(basket.number), String(basket.number))));
  }
  $("#project-inventory-basket-filter").hidden = !baskets.length;
  $('#project-inventory-sort option[value="basket"]').hidden = !baskets.length;
  if (!baskets.length) {
    stockView.basket = "";
    if (stockView.sort === "basket") stockView.sort = "name";
  }
  if (![...basketSelect.options].some((option) => option.value === stockView.basket)) stockView.basket = "";
  basketSelect.value = stockView.basket;
  $("#project-inventory-sort").value = stockView.sort;
  $$("[data-stock-filter]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.stockFilter === stockView.filter));
  });
  $("#project-inventory-incomplete-only").checked = stockView.filter === "unfinished";
}

function renderProjectInventory(filter = "", focusStockId = "") {
  const inventory = state.projectInventory || { stocks: [], counts: {} };
  const query = String(filter || "").trim().toLowerCase();
  const stocks = inventory.stocks || [];
  syncStockToolbar(stocks);
  const entries = stocks.map((stock) => ({ stock, status: stockStatus(stock), label: stockStrengthLabel(stock) }));
  const rows = entries.filter(({ stock, status, label }) => {
    if (stockView.filter === "unfinished" ? status === "ready" : (stockView.filter !== "all" && status !== stockView.filter)) return false;
    if (stockView.solvent) {
      const solvents = stockSolvents(stock);
      if (stockView.solvent === "neat") {
        if (!stockIsNeat(stock)) return false;
      } else if (stockView.solvent === "unrecorded") {
        if (stockIsNeat(stock) || solvents.length) return false;
      } else if (!solvents.includes(stockView.solvent)) return false;
    }
    if (!stockMatchesBasketFilter(stock)) return false;
    if (!query) return true;
    return [stock.material, stock.identity_name, stock.normalized_identity, stock.stock_label, stock.category, stock.carrier, label]
      .some((value) => String(value || "").toLowerCase().includes(query));
  });
  const order = { needs: 0, hold: 1, ready: 2 };
  const byName = (a, b) => String(a.stock.identity_name).localeCompare(String(b.stock.identity_name), undefined, { sensitivity: "base" });
  rows.sort((a, b) => {
    if (stockView.sort === "needs") return (order[a.status] - order[b.status]) || byName(a, b);
    if (stockView.sort === "strength") return (Number(b.stock.fraction_percent_decimal) - Number(a.stock.fraction_percent_decimal)) || byName(a, b);
    if (stockView.sort === "basket") return ((stockBasketNumber(a.stock) ?? 99) - (stockBasketNumber(b.stock) ?? 99)) || byName(a, b);
    return byName(a, b);
  });
  const counts = inventory.counts || {};
  $("#project-inventory-count").textContent = `${counts.stocks || stocks.length} stock bottles`;
  $("#project-inventory-ready").textContent = `${counts.design_ready || counts.execution_ready || 0} ready to use`;
  $("#project-inventory-source").textContent = `${inventory.display_source || "Current project inventory"}. Effective version ${String(inventory.effective_inventory_sha256 || inventory.snapshot_sha256 || "unknown").slice(0, 12)}…`;
  $("#project-inventory-live").textContent = `Showing ${rows.length} of ${stocks.length}`;
  const list = $("#project-inventory-list");
  // A damaged basket log is said once, above the table, and never blocks the stock list.
  const logWarning = [];
  if (typeof inventory.basket_log_error === "string" && inventory.basket_log_error) {
    const warning = stockEl("p", "stock-basket-warning", inventory.basket_log_error);
    warning.setAttribute("role", "status");
    logWarning.push(warning);
  }
  if (!rows.length) {
    list.replaceChildren(...logWarning, stockEl("p", "empty", "No stock matches that search and filter."));
    return;
  }
  const table = stockEl("table", "stock-table");
  table.appendChild(stockEl("caption", "sr-only", "Stock list"));
  const showBaskets = stockBaskets().length > 0;
  const headRow = document.createElement("tr");
  ["Material", "Stock", ...(showBaskets ? ["Basket"] : []), "Status", ""].forEach((title) => {
    const th = stockEl("th", "", title);
    th.scope = "col";
    if (!title) th.appendChild(stockEl("span", "sr-only", "Action"));
    headRow.appendChild(th);
  });
  table.appendChild(stockEl("thead")).appendChild(headRow);
  const body = stockEl("tbody");
  rows.forEach(({ stock, status, label }) => {
    const tr = document.createElement("tr");
    tr.dataset.stockStatus = status;
    tr.dataset.stockId = stock.stock_id;
    const name = stockEl("td", "stock-name");
    name.appendChild(stockEl("strong", "", stock.identity_name));
    if (stock.source_class === "PERSONAL_ADDITION") name.appendChild(stockEl("span", "stock-row-note", "Added by you"));
    const strength = stockEl("td", "stock-strength", label);
    const statusCell = stockEl("td", "stock-status");
    statusCell.appendChild(stockEl("span", `stock-chip stock-chip-${status}`, STOCK_STATUS_LABEL[status]));
    const note = stockNote(stock, status);
    if (status === "hold") statusCell.appendChild(stockEl("span", "stock-row-note", STOCK_HOLD_NOTE));
    if (note) statusCell.appendChild(stockEl("span", "stock-row-note", note));
    const action = stockEl("td", "stock-action");
    if (status !== "ready" && stock.completion_available) {
      const button = stockEl("button", "inventory-complete-button quiet-button", "Complete details");
      button.type = "button";
      button.dataset.completeStock = stock.stock_id;
      action.appendChild(button);
    }
    tr.append(name, strength, ...(showBaskets ? [stockBasketCell(stock)] : []), statusCell, action);
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = stockEl("div", "stock-table-wrap");
  wrap.tabIndex = 0;
  wrap.setAttribute("aria-label", "Stock list");
  wrap.appendChild(table);
  list.replaceChildren(...logWarning, wrap);
  // A basket change redraws the table; keep the keyboard where it was.
  if (focusStockId) [...list.querySelectorAll("[data-basket-for]")].find((node) => node.dataset.basketFor === focusStockId)?.focus();
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
        throw new Error(reason);
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
        throw new Error(stillRunningMessage || "The job is still running. Its durable job can be checked again without resubmitting the request.");
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

bindSavingForm("#backup-form", async (data, form, saved) => {
  const result = await request("/backups", { method: "POST", body: JSON.stringify(data), timeoutMs: 0 });
  saved();
  $("#backup-output").textContent = JSON.stringify(result, null, 2);
  $("#stage-restore-form [name=snapshot_path]").value = result.snapshot_path;
  notify("Verified backup created.");
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
    const result = await request("/export", { timeoutMs: 0 });
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

$("#project-inventory-incomplete-only").addEventListener("change", (event) => {
  stockView.filter = event.currentTarget.checked ? "unfinished" : "all";
  renderProjectInventory($("#project-inventory-search").value);
});

$(".stock-filters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-stock-filter]");
  if (!button) return;
  stockView.filter = button.dataset.stockFilter;
  renderProjectInventory($("#project-inventory-search").value);
});

$("#project-inventory-solvent").addEventListener("change", (event) => {
  stockView.solvent = event.currentTarget.value;
  renderProjectInventory($("#project-inventory-search").value);
});

$("#project-inventory-sort").addEventListener("change", (event) => {
  stockView.sort = event.currentTarget.value;
  renderProjectInventory($("#project-inventory-search").value);
});

$("#project-inventory-basket").addEventListener("change", (event) => {
  stockView.basket = event.currentTarget.value;
  renderProjectInventory($("#project-inventory-search").value);
});

// Basket picker: keys only move the shown value; Enter or leaving the picker saves it, Escape puts the
// saved one back. A change that no key caused (a mouse or touch choice) saves at once.
function savedBasketValue(select) {
  const stock = (state.projectInventory.stocks || []).find((item) => item.stock_id === select.dataset.basketFor);
  return stock && Number.isInteger(stock.basket) ? String(stock.basket) : "";
}

function saveShownBasket(select) {
  delete select.dataset.keyMoved;
  if (select.value === savedBasketValue(select)) return;
  setStockBasket(select.dataset.basketFor, select.value === "" ? null : Number(select.value));
}

$("#project-inventory-list").addEventListener("keydown", (event) => {
  const select = event.target.closest("[data-basket-for]");
  if (!select || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.key === "Enter") {
    event.preventDefault();
    saveShownBasket(select);
  } else if (event.key === "Escape") {
    select.value = savedBasketValue(select);
    delete select.dataset.keyMoved;
  } else if (event.key !== "Tab" && event.key !== "Shift") {
    select.dataset.keyMoved = "1";
  }
});

$("#project-inventory-list").addEventListener("pointerdown", (event) => {
  const select = event.target.closest("[data-basket-for]");
  if (select) delete select.dataset.keyMoved;
});

$("#project-inventory-list").addEventListener("focusout", (event) => {
  const select = event.target.closest?.("[data-basket-for]");
  if (select && select.dataset.keyMoved) saveShownBasket(select);
});

$("#project-inventory-list").addEventListener("change", (event) => {
  const select = event.target.closest("[data-basket-for]");
  if (!select || select.dataset.keyMoved) return;
  setStockBasket(select.dataset.basketFor, select.value === "" ? null : Number(select.value));
});

$("#project-inventory-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-confirm-basket]");
  if (!button) return;
  const stock = (state.projectInventory.stocks || []).find((item) => item.stock_id === button.dataset.confirmBasket);
  if (stock && Number.isInteger(stock.basket)) setStockBasket(stock.stock_id, stock.basket);
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
  const missing = (stock.missing_fields || []).filter((field) => field !== "USER_COMPOUNDING_HOLD").map((field) => humanize(field)).join(", ");
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
  const idempotencyKey = newRequestId("inventory");
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
      const missing = (result.missing_fields || []).filter((field) => field !== "USER_COMPOUNDING_HOLD").map((field) => humanize(field)).join(", ");
      $("#inventory-completion-help").textContent = missing ? `Saved, but this still needs: ${missing}.` : "Saved. This stock stays on hold until you clear the hold.";
      $('[name="expected_effective_inventory_sha256"]', form).value = result.inventory.canonical_effective_inventory_sha256;
      if (missing) notify("Details saved, but the stock is still incomplete.", true);
      else notify("Details saved. This stock stays on hold until you clear the hold.");
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

bindSavingForm("#inventory-addition-form", async (data, form, saved) => {
  const idempotencyKey = newRequestId("inventory-add");
  const submit = form.querySelector('button[type="submit"]');
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
    saved();
    state.projectInventory = result.inventory;
    $("#project-inventory-search").value = data.identity_name;
    Object.assign(stockView, { filter: "all", solvent: "", basket: "" });
    renderProjectInventory(data.identity_name);
    closeInventoryAddition();
    notify(`${data.identity_name} is now available for personal formula design.`);
  } finally {
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
  state.formulaChat.turns.push({ kind: kind === "user" ? "user" : "assistant", text });
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

function renderCompositionChecks(compositionChecks) {
  const box = $("#formula-result-checks");
  const summary = typeof compositionCheckLines === "function" ? compositionCheckLines(compositionChecks) : null;
  box.replaceChildren();
  box.hidden = !summary;
  if (!summary) return;
  box.className = summary.flagged ? "formula-result-checks inline-warning" : "formula-result-checks";
  const list = document.createElement("ul");
  summary.lines.forEach((line) => {
    const item = document.createElement("li");
    item.dataset.status = line.status;
    item.textContent = line.text;
    list.append(item);
  });
  box.append(list);
  if (summary.basis) {
    const basis = document.createElement("small");
    basis.textContent = summary.basis;
    box.append(basis);
  }
}

// With basket data in the inventory payload the rows follow Kenny's basket
// order (benchBasketOrder in bench-sheet.js) under one heading per basket;
// without it they keep the design order. Doses are never changed.
function renderFormulaRows(rows) {
  let group = null;
  $("#formula-result-rows").innerHTML = rows.length
    ? benchBasketOrder(rows, benchBasketLookup(state.projectInventory)).map((entry) => {
      const row = entry.row;
      let heading = "";
      if (entry.group && entry.group !== group) {
        group = entry.group;
        heading = `<tr class="formula-basket-row"><th colspan="4" scope="colgroup">${escapeHtml(entry.heading)}${entry.check ? ' <small class="formula-basket-check">check it: from past cards</small>' : ""}</th></tr>`;
      }
      const fraction = `${formatDecimal(Number(row.stock_fraction_decimal) * 100, 4)}%`;
      const carrier = row.carrier ? ` in ${row.carrier}` : "";
      const proxy = row.profile_source === "HEURISTIC_CATEGORY_PROXY" ? '<small class="proxy-label">category proxy</small>' : "";
      const basketTag = entry.basket !== null ? `<small class="formula-basket-tag">Basket ${escapeHtml(entry.basket)}</small>`
        : entry.group === "unassigned" ? '<small class="formula-basket-tag">No basket</small>' : "";
      const basis = benchBasisText(row.fraction_basis);
      const stockLabel = row.stock_label || `${fraction} ${basis}${carrier}`;
      const mix = benchNeedsPreparedDilution(row) ? benchMixRecipe(row) : null;
      const doseNote = mix ? `<small class="formula-dose-mix">${escapeHtml(benchMixShortText(mix, row.amount_unit))}</small>`
        : benchNeedsPreparedDilution(row) ? '<small class="formula-dose-hold">prepare dilution first</small>' : "";
      return `${heading}<tr>
        <td><strong>${escapeHtml(row.material)}</strong>${basketTag}${proxy}<small class="formula-why">${escapeHtml(row.rationale)}</small></td>
        <td class="formula-dose">${escapeHtml(row.amount_decimal)} ${escapeHtml(row.amount_unit)}${doseNote}</td>
        <td>${escapeHtml(stockLabel)}<small>${escapeHtml(fraction)} ${escapeHtml(basis)}${escapeHtml(carrier)}</small></td>
        <td>${escapeHtml(row.slot_label)}<small>${escapeHtml(row.note)} · ${escapeHtml(row.role)}</small></td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="4">Clarify the brief before a formula can be created.</td></tr>';
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
    button.addEventListener("click", () => {
      renderFormulaDesign(result, index);
      scheduleDraftSave("create");
    });
    picker.append(button);
  });
  renderCompositionChecks(selected.variant ? selected.variant.composition_checks : result.composition_checks);
  const rows = selected.formula?.rows || [];
  renderFormulaRows(rows);

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

function resetFormulaChat(announce = true) {
  state.formulaChat = { messages: [], result: null, variantIndex: 0, turns: [], designedAt: null, restored: false };
  discardStoredDraft("create");
  const form = $("#formula-chat-form");
  form.reset();
  $('[name="liquid_concentrate_ul_decimal"]', form).value = "6000";
  $('[name="max_materials"]', form).value = "15";
  $('[name="design_mode"]', form).value = "FAST_SKETCH";
  $("#formula-chat-log").innerHTML = '<div class="chat-bubble assistant-bubble"><strong>Perfumer</strong><p>Tell me the name or feeling of the perfume you want to make. I will use your inventory, honor hard constraints first, and stop before filler.</p></div>';
  $("#formula-chat-result").hidden = true;
  $("#formula-chat-submit").textContent = "Create my formula";
  if (announce) notify("Ready for a new perfume idea.");
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
      max_materials: Number(data.max_materials || 15),
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
          idempotency_key: newRequestId("job"),
          payload,
        }),
      });
      const jobArea = $("#formula-chat-job-status");
      jobArea.hidden = false;
      let completed;
      try {
        completed = await waitForEngineJob(submitted.id, {
          area: jobArea,
          intervalMs: 600,
          stillRunningMessage: "Deep Compose is still running; its durable job remains available without resubmitting.",
        });
      } finally {
        if (!jobArea.childElementCount) jobArea.hidden = true;
      }
      result = completed.result?.result?.result?.formula_design;
      if (!result) throw new Error(completed.events?.at(-1)?.reason || `Deep Compose ended as ${completed.state}.`);
    } else {
      result = await request("/v2/workbench/formula-chat", {
        method: "POST",
        body: JSON.stringify({
          schema_version: "inventory-grounded-formula-chat-request-v2",
          ...payload,
        }),
        timeoutMs: 0,
      });
    }
    appendFormulaChatBubble("assistant", result.assistant_message || "The brief needs clarification before I can create the formula.");
    renderFormulaDesign(result);
    state.formulaChat.restored = false;
    hideDraftRestoredLine("create");
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
    if (state.formulaChat.result !== previous) state.formulaChat.designedAt = new Date().toISOString();
    saveDraftNow("create");
  }
});

$("#formula-chat-reset").addEventListener("click", () => resetFormulaChat());

$("#formula-download").addEventListener("click", () => {
  const result = state.formulaChat.result;
  if (!result) return;
  const { filename, message } = Drafts.draftDownload(result, state.formulaChat.restored);
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
  notify(message);
});

// Browser-saved drafts ---------------------------------------------------
// Storage rules live in lab-drafts.js (window.LabDrafts); this part draws the page.
// A tab saves only over the draft it last saw (its writer id and saved_at), so a
// stale tab can neither undo a Discard made elsewhere nor overwrite a newer draft.
const Drafts = window.LabDrafts;
const CREATE_DRAFT_FIELDS = ["formula_name", "liquid_concentrate_ul_decimal", "message", "must_preserve", "must_avoid", "max_materials", "design_mode"];
const CREATE_DRAFT_TYPED_FIELDS = ["formula_name", "message", "must_preserve", "must_avoid"];
const DRAFT_WRITER = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
const DRAFT_UNSAVED_TEXT = {
  failed: "This draft couldn't be kept in this browser (storage is blocked or full), so it won't come back after a reload.",
  too_large: "This draft is too large to keep in this browser, so it won't come back after a reload.",
  stale: "Changes in this tab aren't being kept: the saved draft was changed or discarded in another tab. Reload to continue from the saved draft.",
};
const draftSaveTimers = {};
const draftLastSeen = { create: null, improve: null };

function draftStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function createDraftBody() {
  const form = $("#formula-chat-form");
  const fields = {};
  CREATE_DRAFT_FIELDS.forEach((name) => { fields[name] = String($(`[name="${name}"]`, form)?.value ?? ""); });
  const chat = state.formulaChat;
  const typed = CREATE_DRAFT_TYPED_FIELDS.some((name) => fields[name].trim());
  if (!chat.result && !chat.turns.length && !typed) return null;
  return {
    fields,
    turns: chat.turns,
    messages: chat.messages,
    variant_index: chat.variantIndex,
    designed_at: chat.result ? chat.designedAt : null,
    result: chat.result ? Drafts.draftDisplayCopy(chat.result) : null,
  };
}

function improveDraftBody() {
  const goal = $('#improve-form [name="goal"]').value;
  return goal.trim() ? { fields: { goal } } : null;
}

function showDraftSaveOutcome(view, outcome) {
  const note = $(view === "create" ? "#formula-draft-unsaved" : "#improve-draft-unsaved");
  note.textContent = DRAFT_UNSAVED_TEXT[outcome] || "";
  note.hidden = !DRAFT_UNSAVED_TEXT[outcome];
}

function saveDraftNow(view) {
  window.clearTimeout(draftSaveTimers[view]);
  delete draftSaveTimers[view];
  const options = { writer: DRAFT_WRITER, lastSeen: draftLastSeen[view] };
  let saved;
  try {
    saved = Drafts.writeDraft(draftStorage(), view, view === "create" ? createDraftBody() : improveDraftBody(), options);
  } catch {
    // The page state could not be copied; drop the older draft so it cannot come back.
    saved = Drafts.writeDraft(draftStorage(), view, null, options);
    if (saved.outcome === "cleared") saved.outcome = "failed";
  }
  draftLastSeen[view] = saved.stamp;
  showDraftSaveOutcome(view, saved.outcome);
}

function scheduleDraftSave(view) {
  window.clearTimeout(draftSaveTimers[view]);
  draftSaveTimers[view] = window.setTimeout(() => saveDraftNow(view), 400);
}

function discardStoredDraft(view) {
  window.clearTimeout(draftSaveTimers[view]);
  delete draftSaveTimers[view];
  Drafts.removeDraft(draftStorage(), view);
  draftLastSeen[view] = null;
  hideDraftRestoredLine(view);
  showDraftSaveOutcome(view, null);
}

function draftRestoredLine(view) {
  return $(view === "create" ? "#formula-draft-restored" : "#improve-draft-restored");
}

function hideDraftRestoredLine(view) {
  const line = draftRestoredLine(view);
  if (line) line.hidden = true;
}

function formatDraftTime(iso) {
  const saved = new Date(iso);
  const time = saved.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (saved.toDateString() === new Date().toDateString()) return time;
  return `${saved.toLocaleDateString([], { day: "numeric", month: "short" })}, ${time}`;
}

function showDraftRestoredLine(view, iso, text) {
  const line = draftRestoredLine(view);
  $("[data-draft-restored-text]", line).textContent = `Restored your draft from ${formatDraftTime(iso)}. ${text}`;
  line.hidden = false;
}

function restoreCreateDraft() {
  const { draft } = Drafts.readDraft(draftStorage(), "create");
  if (!draft) return;
  draftLastSeen.create = Drafts.draftStamp(draft);
  try {
    const form = $("#formula-chat-form");
    const fields = draft.fields && typeof draft.fields === "object" ? draft.fields : {};
    CREATE_DRAFT_FIELDS.forEach((name) => {
      const node = $(`[name="${name}"]`, form);
      const value = fields[name];
      if (!node || typeof value !== "string") return;
      if (node.tagName === "SELECT" && ![...node.options].some((option) => option.value === value)) return;
      node.value = value;
    });
    state.formulaChat.messages = Array.isArray(draft.messages) ? draft.messages.filter((message) => typeof message === "string") : [];
    (Array.isArray(draft.turns) ? draft.turns : []).forEach((turn) => {
      if (turn && typeof turn.text === "string") appendFormulaChatBubble(turn.kind === "user" ? "user" : "assistant", turn.text);
    });
    const result = draft.result && typeof draft.result === "object" ? draft.result : null;
    const line = draftRestoredLine("create");
    if (result) {
      const variantCount = Array.isArray(result.design_variants) ? result.design_variants.length : 0;
      const variantIndex = Number.isInteger(draft.variant_index) && draft.variant_index >= 0 && draft.variant_index < Math.max(variantCount, 1)
        ? draft.variant_index
        : 0;
      state.formulaChat.designedAt = draft.designed_at || null;
      renderFormulaDesign(result, variantIndex);
      state.formulaChat.restored = true;
      $("#formula-chat-submit").textContent = result.optimized_formula ? "Refine this formula" : "Try clarified brief";
      $("#formula-result-summary").before(line);
      showDraftRestoredLine("create", state.formulaChat.designedAt || draft.saved_at,
        "This is a copy saved in this browser, made from your inventory at that time; refining plans again from current stock.");
    } else {
      form.before(line);
      showDraftRestoredLine("create", draft.saved_at, "Your typed brief was saved in this browser.");
    }
  } catch (error) {
    console.info(`A saved create draft could not be shown and was removed: ${error.message}`);
    resetFormulaChat(false);
  }
}

function restoreImproveDraft() {
  const { draft } = Drafts.readDraft(draftStorage(), "improve");
  const goal = draft?.fields?.goal;
  if (typeof goal !== "string" || !goal.trim()) {
    if (draft) Drafts.removeDraft(draftStorage(), "improve");
    return;
  }
  draftLastSeen.improve = Drafts.draftStamp(draft);
  $('#improve-form [name="goal"]').value = goal;
  showDraftRestoredLine("improve", draft.saved_at, "Your typed change was saved in this browser. Choose the formula or bottle again before you run it.");
}

function restoreStoredDrafts() {
  restoreCreateDraft();
  restoreImproveDraft();
}

$("#formula-chat-form").addEventListener("input", () => scheduleDraftSave("create"));
$("#formula-chat-form").addEventListener("change", () => scheduleDraftSave("create"));
$('#improve-form [name="goal"]').addEventListener("input", () => scheduleDraftSave("improve"));
$$("[data-discard-draft]").forEach((button) => {
  button.addEventListener("click", () => {
    const view = button.dataset.discardDraft;
    if (view === "create") resetFormulaChat();
    else $('#improve-form [name="goal"]').value = "";
    discardStoredDraft(view);
    notify("Saved draft discarded.");
  });
});
window.addEventListener("pagehide", () => {
  Object.keys(draftSaveTimers).forEach((view) => saveDraftNow(view));
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
    basketLookup: benchBasketLookup(state.projectInventory),
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

// ---- Bench sheet view: a printable sheet for any project or pasted formula ----
// Read-only: it fetches and parses the formula, matches owned stocks and draws
// the same sheet as Create (bench-sheet.js); nothing is saved.
// `ticket` changes whenever the form changes, so a reply that arrives after
// an edit is dropped instead of drawing a sheet for the old values.
const benchSource = { html: "", autoSourceMl: "", ticket: 0 };

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

function renderBenchPreview(source, sizes) {
  const rows = (source.rows || []).map(benchRowFromSource);
  if (!rows.length) throw new Error("The formula has no rows the sheet can read.");
  const scaling = sizes.to && compareDecimalText(sizes.to, sizes.from) !== 0;
  const scaled = scaling ? benchScaleRows(rows, sizes.from, sizes.to) : { rows, unscaled: [] };
  const matched = benchMatchStocks(scaled.rows, state.projectInventory);
  benchSource.html = benchSheetHtml({
    formulaName: source.formula_name,
    variantLabel: scaling ? `${sizes.to} mL` : "",
    dateText: new Date().toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }),
    totals: benchSeparateTotals(matched.rows),
    rows: matched.rows,
    critic: {},
    basketLookup: benchBasketLookup(state.projectInventory),
    notes: benchSourceNotes({
      scaledFrom: scaling ? sizes.from : null,
      scaledTo: scaling ? sizes.to : null,
      unscaled: scaled.unscaled,
      unmatched: matched.unmatched,
      ambiguous: matched.ambiguous,
      held: matched.held,
      warnings: source.warnings,
    }),
  });
  $("#bench-preview").innerHTML = benchSource.html;
  $("#bench-preview-card").hidden = false;
  $("#bench-source-print").disabled = false;
}

$('#bench-source-form [name="source_kind"]').addEventListener("change", () => {
  syncBenchSourceFields();
  clearBenchPreview();
});
$('#bench-source-form [name="project_formula_path"]').addEventListener("change", (event) => {
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
    renderBenchPreview(source, sizes);
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

bindForm("#material-form", (data) => request("/materials", { method: "POST", body: JSON.stringify(data) }));
bindForm("#stock-form", (data) => request("/stocks", { method: "POST", body: JSON.stringify({ ...data, active_fraction: Number(data.active_fraction), initial_mass_g: checkedInitialMassG(data.initial_mass_g), density_g_ml: data.density_g_ml ? Number(data.density_g_ml) : null }) }));
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
showMassLimitInline("#stock-form");
showMassLimitInline("#bottle-form");
bindForm("#bottle-form", (data) => request("/bottles", { method: "POST", body: JSON.stringify({ label: data.label, initial_mass_g: checkedInitialMassG(data.initial_mass_g) }) }));
bindForm("#addition-form", (data) => request(`/bottles/${data.bottle_id}/additions`, { method: "POST", body: JSON.stringify({ stock_solution_id: data.stock_solution_id, mass_g: Number(data.mass_g), expected_sequence: Number(data.expected_sequence), command_id: newRequestId("command") }) }));
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
const newRequestId = (prefix) => globalThis.crypto?.randomUUID?.()
  || `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;

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

bindForm("#observation-form", (data) => request(`/applications/${data.application_id}/observations`, { method: "POST", body: JSON.stringify({ elapsed_seconds: Number(data.elapsed_seconds), observations: { note: data.observation } }) }));
bindForm("#outcome-form", (data) => request("/outcomes", { method: "POST", body: JSON.stringify({ experiment_id: data.experiment_id, prediction_id: null, outcome: { note: data.outcome } }) }));

$("#analysis-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    const result = await request("/analysis", { method: "POST", body: JSON.stringify({ name: data.name, total_volume_ml: 10, concentration_percent: 20, ingredients: [{ name: data.material, percentage: 100, stock_active_fraction: 1, stock_fraction_basis: "volume_fraction" }] }), timeoutMs: 0 });
    $("#analysis-output").textContent = JSON.stringify(result, null, 2); notify("Evidence analysis complete.");
  } catch (error) { notify(error.message, true); }
});

bindSavingForm("#hypothesis-form", async (data, form, saved) => {
  const splitValues = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
  {
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
    saved();
    $("#hypothesis-output").textContent = JSON.stringify(result, null, 2);
    notify(`${result.hypotheses.length} inventory-valid hypotheses generated.`);
  }
});

bindSavingForm("#trial-plan-form", async (data, form, saved) => {
  {
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
    saved();
    $("#trial-plan-output").textContent = JSON.stringify(result, null, 2);
    notify(`Trial planned at ${result.achieved_active_ppm_w_w.toFixed(3)} ppm w/w.`);
  }
});

bindSavingForm("#assistant-form", async (data, form, saved) => {
  const packet = await request("/assistant", { method: "POST", body: JSON.stringify({ intent: data.intent, subject_id: data.subject_id || null, facts: {}, calculations: {}, evidence: {} }) });
  saved();
  $("#assistant-output").textContent = JSON.stringify(packet, null, 2); notify(`Packet ${packet.payload_sha256.slice(0, 10)} built.`);
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
  const report = await request(`/science/authority?view=${view}`, { timeoutMs: 0 });
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

// Move focus to the main area without putting "#main-content" in the URL.
$(".skip-link").addEventListener("click", (event) => {
  event.preventDefault();
  $("#main-content").focus();
});

const THEME_KEY = "perfumechem.theme";
const THEME_COLORS = { light: "#FFFDF8", dark: "#12171B" };
function applyTheme(choice) {
  const root = document.documentElement;
  if (choice === "light" || choice === "dark") root.dataset.theme = choice;
  else delete root.dataset.theme;
  const resolved = choice === "light" || choice === "dark"
    ? choice
    : (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  $('meta[name="theme-color"]')?.setAttribute("content", THEME_COLORS[resolved]);
}
(() => {
  let choice = "system";
  try { choice = localStorage.getItem(THEME_KEY) || "system"; } catch { choice = "system"; }
  if (!["system", "light", "dark"].includes(choice)) choice = "system";
  const picker = $("#theme-select");
  if (picker) {
    picker.value = choice;
    picker.addEventListener("change", () => {
      try { localStorage.setItem(THEME_KEY, picker.value); } catch { /* storage unavailable */ }
      applyTheme(picker.value);
    });
  }
  applyTheme(choice);
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (!document.documentElement.dataset.theme) applyTheme("system");
  });
})();

const startView = location.hash.slice(1);
// An unknown hash (an old "#main-content" bookmark, say) would hide every view.
navigate($$(".view").some((panel) => panel.dataset.panel === startView) ? startView : "improve");
pageStarted = true;
restoreStoredDrafts();
refresh().catch((error) => notify(error.message, true));
