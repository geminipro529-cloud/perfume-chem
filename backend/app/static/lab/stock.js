"use strict";

// Stock page (Materials): the owned stock list, its filters, details, additions, and the material and stock forms.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

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
  const madeDilutions = counts.prepared_dilutions ? ` · ${counts.prepared_dilutions} dilutions you made` : "";
  const readyCount = counts.design_ready || counts.execution_ready || 0;
  const totalCount = counts.stocks || stocks.length;
  const needCount = counts.details_incomplete ?? Math.max(totalCount - readyCount, 0);
  const needDetails = needCount ? ` · ${needCount} need details` : "";
  $("#project-inventory-ready").textContent = `${readyCount} of ${totalCount} ready to design${needDetails}${madeDilutions}`;
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
    if (stock.source_class === "PREPARED_DILUTION") name.appendChild(stockEl("span", "stock-row-note", "Your dilution"));
    const strength = stockEl("td", "stock-strength", label);
    const statusCell = stockEl("td", "stock-status");
    statusCell.appendChild(stockEl("span", `stock-chip stock-chip-${status}`, STOCK_STATUS_LABEL[status]));
    const note = stockNote(stock, status);
    if (status === "hold") statusCell.appendChild(stockEl("span", "stock-row-note", STOCK_HOLD_NOTE));
    if (note) statusCell.appendChild(stockEl("span", "stock-row-note", note));
    // Why the release gate still holds this bottle, and where a Stock page entry overrides the workbook.
    if (stock.gate_hold_text) statusCell.appendChild(stockEl("span", "stock-row-note inventory-gate-hold", stock.gate_hold_text));
    const disagreement = stock.authority_disagreement?.text;
    if (disagreement) statusCell.appendChild(stockEl("span", "stock-row-note inventory-authority-differs", disagreement));
    const action = stockEl("td", "stock-action");
    if (status !== "ready" && stock.completion_available) {
      const button = stockEl("button", "inventory-complete-button quiet-button", "Complete details");
      button.type = "button";
      button.dataset.completeStock = stock.stock_id;
      action.appendChild(button);
    }
    if (stock.dilution_available) {
      const button = stockEl("button", "inventory-complete-button quiet-button", "Add a dilution");
      button.type = "button";
      button.dataset.diluteStock = stock.stock_id;
      action.appendChild(button);
    }
    if (typeof stockPriceButtonText === "function") {
      const price = stockEl("button", "inventory-complete-button quiet-button", stockPriceButtonText(stock.stock_id));
      price.type = "button";
      price.dataset.priceStock = stock.stock_id;
      action.appendChild(price);
    }
    const rate = stockEl("button", "inventory-complete-button quiet-button", "Rate");
    rate.type = "button";
    rate.dataset.rateStock = stock.stock_id;
    rate.dataset.stockLabel = label;
    action.appendChild(rate);
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

// A suggestion fills only fields that are still empty or "I do not know yet"; it is never saved
// until Kenny ticks the boxes and presses Save, exactly like typing the values himself.
function showInventoryCompletionSuggestion(form, suggestion) {
  const note = $("#inventory-completion-suggestion");
  const filled = [];
  if (suggestion) {
    const percent = $('[name="fraction_percent_decimal"]', form);
    if (!percent.value && suggestion.fraction_percent_decimal) {
      percent.value = suggestion.fraction_percent_decimal;
      filled.push(`${suggestion.fraction_percent_decimal}%`);
    }
    const basis = $('[name="fraction_basis"]', form);
    if (basis.value === "unspecified" && suggestion.fraction_basis) {
      basis.value = suggestion.fraction_basis;
      filled.push(STOCK_BASIS_WORDS[suggestion.fraction_basis] || humanize(suggestion.fraction_basis));
    }
    const carrier = $('[name="carrier"]', form);
    if (!carrier.value.trim() && suggestion.carrier) {
      carrier.value = suggestion.carrier;
      filled.push(`in ${suggestion.carrier}`);
    }
  }
  note.textContent = filled.length
    ? `Suggested: ${filled.join(", ")}. Source: ${suggestion.source_text}. Check it against the bottle; nothing is saved until you confirm and save.`
    : "";
  note.hidden = !filled.length;
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
  showInventoryCompletionSuggestion(form, stock.suggested_completion);
  panel.hidden = false;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
  $('[name="fraction_percent_decimal"]', form).focus();
}

// "What's missing" (hold-list.js) opens one stock here: the list shows that bottle
// with every filter cleared, and its details form opens when the Stock page can
// complete it. Nothing is saved until Kenny confirms and saves, as always.
function openStockEntry(stockId) {
  const stock = (state.projectInventory?.stocks || []).find((item) => item.stock_id === stockId);
  navigate("materials");
  if (!stock) {
    notify("That stock is not on the Stock page's list. Reload the page and try again.", true);
    return;
  }
  Object.assign(stockView, { filter: "all", solvent: "", basket: "" });
  const search = $("#project-inventory-search");
  search.value = stock.identity_name || stock.material || "";
  renderProjectInventory(search.value);
  if (stock.completion_available) {
    openInventoryCompletion(stock);
    return;
  }
  const row = [...$("#project-inventory-list").querySelectorAll("tr[data-stock-id]")].find((node) => node.dataset.stockId === stockId);
  row?.scrollIntoView({ behavior: "smooth", block: "center" });
}

$("#project-inventory-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-complete-stock]");
  if (!button) return;
  const stock = (state.projectInventory.stocks || []).find(
    (item) => item.stock_id === button.dataset.completeStock,
  );
  if (stock) openInventoryCompletion(stock);
});

attachStockDilutions({
  doc: document,
  list: $("#project-inventory-list"),
  getInventory: () => state.projectInventory || { stocks: [] },
  request,
  newKey: () => globalThis.crypto?.randomUUID?.() || `dilution-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  onSaved: (result) => {
    state.projectInventory = result.inventory;
    renderProjectInventory($("#project-inventory-search").value);
    notify("Dilution saved. It is now a stock you can design with and gate.");
  },
});

// What can I make (make-now.js): its own page, reading the inventory and prices loaded here.
const makeNow = typeof attachMakeNow === "function"
  ? attachMakeNow({
    doc: document,
    root: $('[data-panel="make"]'),
    request,
    getInventory: () => state.projectInventory || { stocks: [] },
    getPrices: () => (typeof stockPricesCurrent === "function" ? stockPricesCurrent() : {}),
    notify,
    // Edit a formula (lab/editor.js, loaded later) previews the swap.
    openSwap: (formulaId, stockId, material) => {
      editorOpenSavedSwap(formulaId, stockId, material).catch((error) => notify(error.message, true));
    },
  })
  : null;

function makeNowShown() {
  makeNow?.shown();
}

function makeNowInventoryChanged() {
  makeNow?.changed();
}

// ---- Shelf map: owned materials by written character (similar-stocks.js) ----
// Asked for on a tap only (GET /v2/workbench/shelf-map), and again on each opening,
// since stocks change on this page.

const shelfMapView = { seq: 0 };

async function showShelfMap() {
  const panel = $("#shelf-map");
  const seq = ++shelfMapView.seq;
  panel.replaceChildren(Object.assign(document.createElement("p"), { className: "field-help", textContent: "Placing your stocks…" }));
  try {
    const answer = await request("/v2/workbench/shelf-map");
    if (seq !== shelfMapView.seq) return;
    renderShelfMap(panel, answer);
  } catch (error) {
    if (seq !== shelfMapView.seq) return;
    panel.replaceChildren(Object.assign(document.createElement("p"), { className: "field-help", textContent: `Could not place your stocks: ${error.message}` }));
  }
}

$("#shelf-map-toggle").addEventListener("click", () => {
  const toggle = $("#shelf-map-toggle");
  const open = toggle.getAttribute("aria-expanded") !== "true";
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Hide the shelf map" : "Show the shelf map";
  $("#shelf-map").hidden = !open;
  if (open) showShelfMap();
  else shelfMapView.seq += 1;
});

// Prices Kenny types per stock, plus ethanol and packaging (stock-prices.js).
// boot.js loads them: a price change redraws the bench sheet cost (bench.js), loaded after this file.
const stockPrices = typeof attachStockPrices === "function"
  ? attachStockPrices({
    doc: document,
    list: $("#project-inventory-list"),
    request,
    getInventory: () => state.projectInventory || { stocks: [] },
    onChange: () => {
      if (state.projectInventory) renderProjectInventory($("#project-inventory-search").value);
      if (benchSource.costRows) showBenchCostBlock();
      makeNowInventoryChanged();
    },
  })
  : null;

if (typeof attachMaterialLiking === "function") {
  attachMaterialLiking({
    doc: document,
    list: $("#project-inventory-list"),
    getInventory: () => state.projectInventory || { stocks: [] },
    request,
  });
}

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

bindForm("#material-form", (data) => request("/materials", { method: "POST", body: JSON.stringify(data) }));
bindForm("#stock-form", (data) => request("/stocks", { method: "POST", body: JSON.stringify({ ...data, active_fraction: Number(data.active_fraction), initial_mass_g: checkedInitialMassG(data.initial_mass_g), density_g_ml: data.density_g_ml ? Number(data.density_g_ml) : null }) }));
showMassLimitInline("#stock-form");
