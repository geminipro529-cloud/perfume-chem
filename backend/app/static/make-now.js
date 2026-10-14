// What can I make now: each saved formula (its latest version from Edit a formula)
// scaled to one bottle, against how much of each stock is left, and a shopping list
// grouped by supplier and priced with Kenny's own prices.
//
// How much is left is asked only for a stock a formula needs (GET/POST
// /v2/workbench/stock-on-hand); nothing else asks for it. Amounts are exact
// fractions (bench-sheet.js) and are rounded only for display; a row is priced
// exactly as the bench sheet prices it (benchCostRow, stock-prices.js), with a
// liquid priced per g weighed by its stock's density when that is known.
//
// lab/stock.js attaches it. Names and anything typed go in through textContent /
// .value only, never HTML strings. Node loads the same file in the tests.

const makeBench = (typeof module === "object" && module.exports)
  ? require("./bench-sheet.js")
  : { benchFraction, benchFractionOf, benchTimes, benchOver, benchPlus, benchMinus, benchCompare, benchFractionText, benchStockDensity };
const makePrices = (typeof module === "object" && module.exports)
  ? require("./stock-prices.js")
  : { benchCostRow, stockPriceMoneyText };

const MAKE_ETHANOL_NAMES = new Set(["ethanol", "perfumer's alcohol", "perfumers alcohol", "alcohol"]);
const MAKE_DEFAULT_BOTTLE_ML = "30";
const MAKE_NOT_OWNED_GROUP = "Not in your stock yet";
const MAKE_YOURSELF_GROUP = "Make yourself";
const MAKE_NO_SUPPLIER = "Supplier not set";
const MAKE_ZERO = { n: 0n, d: 1n };

function makeNameKey(value) {
  return String(value ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

// "600", "0.5" or "1000/3" as an exact fraction; null for anything else or 0.
function makeAmount(text) {
  const value = String(text ?? "").trim();
  const ratio = /^(\d{1,30})\/([1-9]\d{0,29})$/.exec(value);
  const fraction = ratio ? makeBench.benchFraction(BigInt(ratio[1]), BigInt(ratio[2])) : makeBench.benchFractionOf(value);
  return fraction && fraction.n > 0n ? fraction : null;
}

function makeIsEthanol(row) {
  return MAKE_ETHANOL_NAMES.has(makeNameKey(row?.material));
}

function makeStockFraction(stock) {
  const percent = makeAmount(stock?.fraction_percent_decimal);
  return percent ? makeBench.benchOver(percent, { n: 100n, d: 1n }) : null;
}

// The stock a saved row pours: its own stock when the list has it; else the stock of
// that name (the one at the row's strength when there are several); else null.
function makeStockFor(row, stocks) {
  const list = stocks || [];
  if (row?.stock_id) {
    const own = list.find((stock) => stock.stock_id === row.stock_id);
    if (own) return own;
  }
  const name = makeNameKey(row?.material);
  const named = list.filter((stock) => [stock.identity_name, stock.material].some((value) => makeNameKey(value) === name));
  if (named.length <= 1) return named[0] || null;
  const strength = makeAmount(row?.fraction);
  return named.find((stock) => {
    const fraction = makeStockFraction(stock);
    return strength && fraction && makeBench.benchCompare(strength, fraction) === 0;
  }) || null;
}

// One formula's needs for a bottle of `bottleMl`: per stock (or per material when no
// stock is owned), mL for a liquid or g for a solid, summed over its rows. Ethanol is
// the top-up, not a stock, so it is left out. A version saved without a bottle size
// is taken as written.
function makeNeeds(formula, stocks, bottleMl = MAKE_DEFAULT_BOTTLE_ML) {
  const saved = makeAmount(formula?.bottle_ml);
  const target = makeAmount(bottleMl);
  const scale = saved && target ? makeBench.benchOver(target, saved) : { n: 1n, d: 1n };
  const byKey = new Map();
  for (const row of formula?.rows || []) {
    const amount = makeAmount(row.amount);
    if (!row.material || !amount || makeIsEthanol(row)) continue;
    const stock = makeStockFor(row, stocks);
    const unit = row.solid ? "g" : "mL";
    // µL -> mL and mg -> g.
    const need = makeBench.benchOver(makeBench.benchTimes(amount, scale), { n: 1000n, d: 1n });
    const key = `${stock ? stock.stock_id : `name:${makeNameKey(row.material)}`}\u0000${unit}`;
    const entry = byKey.get(key) || {
      key, unit, need: MAKE_ZERO,
      material: stock ? (stock.identity_name || stock.material) : row.material,
      stockId: stock ? stock.stock_id : null,
      fraction: stock ? stock.fraction_percent_decimal : null,
      madeByYou: stock?.source_class === "PREPARED_DILUTION",
      row: { material: row.material, fraction: row.fraction, basis: row.basis, carrier: row.carrier },
    };
    entry.need = makeBench.benchPlus(entry.need, need);
    byKey.set(key, entry);
  }
  return { scaled: Boolean(saved && target), needs: [...byKey.values()] };
}

// Each need against how much is left: enough, short, unknown (nothing typed yet, or
// typed in the other unit) or missing (no stock owned).
function makeCheck(needs, onHand) {
  return (needs || []).map((need) => {
    if (!need.stockId) return { ...need, status: "missing", left: null, short: need.need, otherUnit: null };
    const entry = (onHand || {})[need.stockId];
    const left = entry ? makeBench.benchFractionOf(String(entry.amount_decimal ?? "")) : null;
    if (!entry || !left) return { ...need, status: "unknown", left: null, short: null, otherUnit: null };
    if (entry.unit !== need.unit) return { ...need, status: "unknown", left: null, short: null, otherUnit: entry.unit };
    if (makeBench.benchCompare(left, need.need) >= 0) return { ...need, status: "enough", left, short: null, otherUnit: null };
    return { ...need, status: "short", left, short: makeBench.benchMinus(need.need, left), otherUnit: null };
  });
}

function makeCount(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function makeVerdict(items, bottleMl = MAKE_DEFAULT_BOTTLE_ML) {
  const lacking = items.filter((item) => item.status === "short" || item.status === "missing").length;
  const unknown = items.filter((item) => item.status === "unknown").length;
  if (!items.length) return { status: "unknown", text: "No rows with amounts." };
  if (lacking) {
    const more = unknown ? `, and ${makeCount(unknown, "stock")} still need how much is left` : "";
    return { status: "short", text: `Short of ${makeCount(lacking, "stock")} for ${bottleMl} mL${more}.` };
  }
  if (unknown) return { status: "unknown", text: `Type how much is left of ${makeCount(unknown, "stock")} to know.` };
  return { status: "ok", text: `You can mix it at ${bottleMl} mL.` };
}

// An amount for the page: two decimals, or three when two would show 0.
function makeAmountText(value, unit) {
  const two = makeBench.benchFractionText(value, 2);
  const text = two === "0" ? makeBench.benchFractionText(value, 3) : two;
  return `${text === "0" ? "under 0.001" : text} ${unit}`;
}

function makeLineText(item) {
  const need = makeAmountText(item.need, item.unit);
  if (item.status === "missing") return `${item.material}: needs ${need}; not in your stock.`;
  if (item.status === "unknown") {
    return item.otherUnit
      ? `${item.material}: needs ${need}; you typed how much is left in ${item.otherUnit}.`
      : `${item.material}: needs ${need}; how much is left?`;
  }
  const left = makeAmountText(item.left, item.unit);
  if (item.status === "short") return `${item.material}: needs ${need}; ${left} left, short by ${makeAmountText(item.short, item.unit)}.`;
  return `${item.material}: needs ${need}; ${left} left.`;
}

// A liquid priced per g is weighed by its stock's density when that is known.
function makeCostRow(item, amount, prices, densities) {
  const decimal = makeBench.benchFractionText(amount, 6);
  const row = { material: item.material, stock_id: item.stockId, amount_decimal: decimal, amount_unit: item.unit };
  const entry = item.stockId ? (prices || {})[item.stockId] : null;
  if (entry && entry.per_unit === "g" && item.unit === "mL") {
    const density = makeBench.benchStockDensity({
      material: item.material,
      stock_fraction_decimal: makeStockFraction({ fraction_percent_decimal: item.fraction })
        ? makeBench.benchFractionText(makeStockFraction({ fraction_percent_decimal: item.fraction }), 6)
        : "1",
      fraction_basis: item.row?.basis,
      carrier: item.row?.carrier,
    }, (densities || {})[makeNameKey(item.material)] ?? null);
    if (density) return { ...row, amount_decimal: makeBench.benchFractionText(makeBench.benchTimes(amount, density.density), 6), amount_unit: "g" };
  }
  return row;
}

// The shopping list for the checked items of every formula on it: per stock, the
// summed need less what is left; grouped by supplier (typed with how much is left),
// with the stocks whose amount is still unknown listed first to ask for.
function makeShopping(formulaItems, { onHand = {}, prices = {}, densities = {} } = {}) {
  const totals = new Map();
  for (const items of formulaItems || []) {
    for (const item of items) {
      const entry = totals.get(item.key) || { ...item, need: MAKE_ZERO };
      entry.need = makeBench.benchPlus(entry.need, item.need);
      totals.set(item.key, entry);
    }
  }
  const checked = makeCheck([...totals.values()], onHand);
  const ask = checked.filter((item) => item.status === "unknown");
  const groups = new Map();
  let total = MAKE_ZERO;
  let currency = "";
  let unpriced = 0;
  for (const item of checked) {
    if (item.status !== "short" && item.status !== "missing") continue;
    const supplier = item.madeByYou
      ? MAKE_YOURSELF_GROUP
      : !item.stockId ? MAKE_NOT_OWNED_GROUP : (String(onHand[item.stockId]?.supplier || "").trim() || MAKE_NO_SUPPLIER);
    const cost = item.madeByYou ? null : makePrices.benchCostRow(makeCostRow(item, item.short, prices, densities), prices);
    const line = {
      material: item.material,
      stockId: item.stockId,
      buyText: makeAmountText(item.short, item.unit),
      costText: cost && cost.cost ? makePrices.stockPriceMoneyText(cost.cost, cost.currency) : "",
      reason: item.madeByYou ? "your own dilution: make more" : (cost?.cost ? "" : cost?.reason || ""),
    };
    if (cost?.cost && (!currency || cost.currency === currency)) {
      currency = cost.currency;
      total = makeBench.benchPlus(total, cost.cost);
    } else if (!item.madeByYou) {
      unpriced += 1;
    }
    const group = groups.get(supplier) || { supplier, items: [], subtotal: MAKE_ZERO, currency: "" };
    group.items.push(line);
    if (cost?.cost && cost.currency === currency) {
      group.subtotal = makeBench.benchPlus(group.subtotal, cost.cost);
      group.currency = currency;
    }
    groups.set(supplier, group);
  }
  const order = (name) => (name === MAKE_YOURSELF_GROUP ? 2 : name === MAKE_NOT_OWNED_GROUP || name === MAKE_NO_SUPPLIER ? 1 : 0);
  const listed = [...groups.values()]
    .sort((a, b) => order(a.supplier) - order(b.supplier) || a.supplier.localeCompare(b.supplier))
    .map((group) => ({
      supplier: group.supplier,
      items: group.items.sort((a, b) => a.material.localeCompare(b.material)),
      subtotalText: group.currency ? makePrices.stockPriceMoneyText(group.subtotal, group.currency) : "",
    }));
  return {
    ask: ask.map((item) => ({ stockId: item.stockId, material: item.material, unit: item.unit, needText: makeAmountText(item.need, item.unit), otherUnit: item.otherUnit })),
    groups: listed,
    totalText: currency ? makePrices.stockPriceMoneyText(total, currency) : "",
    unpriced,
  };
}

// The names whose density would let a per-g price cost a liquid line.
function makeDensityNames(formulaItems, prices) {
  const names = new Set();
  for (const items of formulaItems || []) {
    for (const item of items) {
      if (item.stockId && item.unit === "mL" && (prices || {})[item.stockId]?.per_unit === "g") names.add(item.material);
    }
  }
  return [...names].sort();
}

// ---- The page ----

function makeEl(doc, tag, className, text) {
  const node = doc.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// The small "how much is left" form: amount in the unit the formula needs, and
// where it is bought, for the shopping list.
function makeLeftForm(doc, { stockId, material, unit, supplier }, onSave) {
  const form = makeEl(doc, "form", "make-left-form");
  form.setAttribute("aria-label", `How much ${material} is left`);
  const amountLabel = makeEl(doc, "label", "", `${unit} left `);
  const amount = makeEl(doc, "input");
  Object.assign(amount, { name: "amount_decimal", inputMode: "decimal", autocomplete: "off", required: true });
  amount.setAttribute("pattern", "[0-9]+([.][0-9]+)?");
  amountLabel.append(amount);
  const supplierLabel = makeEl(doc, "label", "", "Bought from ");
  const where = makeEl(doc, "input");
  Object.assign(where, { name: "supplier", autocomplete: "off", maxLength: 120, value: supplier || "" });
  supplierLabel.append(where);
  const save = makeEl(doc, "button", "quiet-button", "Save");
  save.type = "submit";
  const message = makeEl(doc, "p", "make-left-message");
  message.setAttribute("role", "status");
  form.append(amountLabel, supplierLabel, save, message);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = amount.value.trim();
    if (!/^\d+(\.\d+)?$/.test(text)) {
      message.textContent = `Type how many ${unit} are left, such as 12.5 (0 if it is empty).`;
      amount.focus();
      return;
    }
    save.disabled = true;
    message.textContent = "Saving…";
    try {
      await onSave({ stock_id: stockId, amount_decimal: text, unit, supplier: where.value.trim() });
    } catch (error) {
      message.textContent = `Not saved: ${error?.message || error}`;
      save.disabled = false;
    }
  });
  return form;
}

// `openSwap(formulaId, stockId, material)` opens the formula in Edit a formula with
// the stocks similar to one that is short; without it, short stocks list none.
function attachMakeNow({ doc, root, request, getInventory, getPrices, notify = () => {}, openSwap = null }) {
  const view = {
    data: null, densities: {}, picked: new Set(), loading: null, open: new Set(),
    // Stocks like a short one, by stock id: the answer, or { error }; and which lists are open.
    similar: new Map(), similarOpen: new Set(),
  };
  const status = root.querySelector("#make-status");
  const list = root.querySelector("#make-formulas");
  const shopping = root.querySelector("#make-shopping");
  const bottleInput = root.querySelector("#make-bottle-ml");

  const bottleMl = () => {
    const text = bottleInput.value.trim();
    return /^\d+(\.\d+)?$/.test(text) && Number(text) > 0 ? text : MAKE_DEFAULT_BOTTLE_ML;
  };
  const stocks = () => getInventory()?.stocks || [];
  const checks = () => (view.data?.formulas || []).map((formula) => ({
    formula,
    items: makeCheck(makeNeeds(formula, stocks(), bottleMl()).needs, view.data.on_hand),
  }));

  async function saveLeft(body) {
    const answer = await request("/v2/workbench/stock-on-hand", { method: "POST", body: JSON.stringify(body) });
    view.data = { ...view.data, on_hand: answer.on_hand };
    notify(`Saved: ${body.amount_decimal} ${body.unit} left.`);
    render();
  }

  function leftForm(item) {
    return makeLeftForm(doc, { ...item, supplier: view.data.on_hand?.[item.stockId]?.supplier }, saveLeft);
  }

  async function loadSimilar(item, id) {
    try {
      const body = JSON.stringify({ stock_id: item.stockId, material: item.material, limit: 4 });
      view.similar.set(item.stockId, await request("/v2/workbench/similar-stocks", { method: "POST", body }));
    } catch (error) {
      view.similar.set(item.stockId, { error: error?.message || String(error) });
    }
    const lost = !root.contains(doc.activeElement);
    render();
    if (lost) root.querySelector(`[aria-controls="${id}"]`)?.focus();
  }

  // A short stock's "Similar you own": owned stocks written alike, opened on a tap.
  function similarBox(formula, item, id) {
    const key = `${formula.formula_id}|${item.stockId}`;
    const open = view.similarOpen.has(key);
    const box = makeEl(doc, "div", "make-similar");
    const toggle = makeEl(doc, "button", "quiet-button", "Similar you own");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-controls", id);
    toggle.setAttribute("aria-label", `Similar you own to ${item.material}`);
    toggle.addEventListener("click", () => {
      if (view.similarOpen.has(key)) view.similarOpen.delete(key);
      else {
        view.similarOpen.add(key);
        if (!view.similar.has(item.stockId)) loadSimilar(item, id);
      }
      render();
      root.querySelector(`[aria-controls="${id}"]`)?.focus();
    });
    const panel = makeEl(doc, "div", "make-similar-list");
    panel.id = id;
    panel.hidden = !open;
    const answer = view.similar.get(item.stockId);
    if (open && !answer) panel.append(makeEl(doc, "p", "field-help", "Looking through your stocks…"));
    else if (open && answer.error) panel.append(makeEl(doc, "p", "field-help", `Not compared right now: ${answer.error}`));
    else if (open) {
      const list = makeEl(doc, "div", "similar-list");
      renderSimilarList(list, answer);
      const swap = makeEl(doc, "button", "quiet-button", "See a swap in Edit a formula");
      swap.type = "button";
      swap.addEventListener("click", () => openSwap(formula.formula_id, item.stockId, item.material));
      panel.append(list, swap);
    }
    box.append(toggle, panel);
    return box;
  }

  function renderFormulas(all) {
    list.replaceChildren();
    if (!all.length) {
      list.append(makeEl(doc, "p", "field-help", "No saved formulas yet. Save one on Edit a formula and it shows here."));
      return;
    }
    all.forEach(({ formula, items }, index) => {
      const verdict = makeVerdict(items, bottleMl());
      const card = makeEl(doc, "article", "make-card");
      card.dataset.status = verdict.status;
      const head = makeEl(doc, "div", "make-card-head");
      const title = makeEl(doc, "h3", "", formula.name);
      const chip = makeEl(doc, "span", `make-chip make-chip-${verdict.status}`, verdict.status === "ok" ? "Can mix" : verdict.status === "short" ? "Short" : "Check amounts");
      head.append(title, chip);
      const facts = makeEl(doc, "p", "field-help",
        `Version ${formula.version}${formula.bottle_ml ? `, saved for ${formula.bottle_ml} mL` : ", saved without a bottle size, so shown as written"}`);
      const line = makeEl(doc, "p", "make-verdict", verdict.text);
      const actions = makeEl(doc, "div", "request-actions");
      const pick = makeEl(doc, "button", "quiet-button", "");
      pick.type = "button";
      const picked = view.picked.has(formula.formula_id);
      pick.textContent = picked ? "On the shopping list" : "Add to shopping list";
      pick.setAttribute("aria-pressed", String(picked));
      pick.addEventListener("click", () => {
        if (view.picked.has(formula.formula_id)) view.picked.delete(formula.formula_id);
        else view.picked.add(formula.formula_id);
        render();
      });
      const rowsId = `make-rows-${index + 1}`;
      const toggle = makeEl(doc, "button", "quiet-button", "Each stock");
      toggle.type = "button";
      toggle.setAttribute("aria-controls", rowsId);
      const open = view.open.has(formula.formula_id);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.addEventListener("click", () => {
        if (view.open.has(formula.formula_id)) view.open.delete(formula.formula_id);
        else view.open.add(formula.formula_id);
        render();
      });
      actions.append(pick, toggle);
      const rows = makeEl(doc, "ul", "make-rows");
      rows.id = rowsId;
      rows.hidden = !open;
      items.forEach((item, at) => {
        const entry = makeEl(doc, "li", "make-row");
        entry.dataset.status = item.status;
        entry.append(makeEl(doc, "span", "", makeLineText(item)));
        if (item.status === "unknown" && item.stockId) entry.append(leftForm(item));
        if (item.status === "short" && item.stockId && openSwap && typeof renderSimilarList === "function") {
          entry.append(similarBox(formula, item, `${rowsId}-similar-${at + 1}`));
        }
        rows.append(entry);
      });
      card.append(head, facts, line, actions, rows);
      list.append(card);
    });
  }

  function renderShopping(all) {
    shopping.replaceChildren();
    const picked = all.filter(({ formula }) => view.picked.has(formula.formula_id));
    if (!picked.length) {
      shopping.append(makeEl(doc, "p", "field-help", "Add formulas to the shopping list to see what to buy for them."));
      return;
    }
    const prices = getPrices() || {};
    const items = picked.map(({ items: entries }) => entries);
    const result = makeShopping(items, { onHand: view.data.on_hand, prices, densities: view.densities });
    shopping.append(makeEl(doc, "p", "make-shopping-for",
      `For ${makeCount(picked.length, "formula")}, one ${bottleMl()} mL bottle each: ${picked.map(({ formula }) => formula.name).join(", ")}.`));
    if (result.ask.length) {
      const ask = makeEl(doc, "section", "make-ask");
      ask.append(makeEl(doc, "h3", "", "How much is left?"),
        makeEl(doc, "p", "field-help", "These stocks are on the list, but how much is left is not known yet. Read it off the bottle."));
      const asks = makeEl(doc, "ul", "make-rows");
      for (const item of result.ask) {
        const entry = makeEl(doc, "li", "make-row");
        entry.dataset.status = "unknown";
        entry.append(makeEl(doc, "span", "", item.otherUnit
          ? `${item.material}: needs ${item.needText}; you typed how much is left in ${item.otherUnit}.`
          : `${item.material}: needs ${item.needText}.`), leftForm(item));
        asks.append(entry);
      }
      ask.append(asks);
      shopping.append(ask);
    }
    if (!result.groups.length) {
      shopping.append(makeEl(doc, "p", "make-verdict", result.ask.length
        ? "Nothing to buy among the stocks whose amount is known."
        : "Nothing to buy: what is left covers these formulas."));
      return;
    }
    for (const group of result.groups) {
      const section = makeEl(doc, "section", "make-group");
      const head = makeEl(doc, "div", "make-card-head");
      head.append(makeEl(doc, "h3", "", group.supplier), makeEl(doc, "span", "make-subtotal", group.subtotalText));
      const lines = makeEl(doc, "ul", "make-rows");
      for (const line of group.items) {
        const entry = makeEl(doc, "li", "make-row");
        entry.dataset.status = "short";
        const text = `${line.material}: ${line.buyText}${line.costText ? `, ${line.costText}` : ""}${line.reason ? ` (${line.reason})` : ""}`;
        entry.append(makeEl(doc, "span", "", text));
        lines.append(entry);
      }
      section.append(head, lines);
      shopping.append(section);
    }
    const total = result.totalText ? `Total with your prices: ${result.totalText}.` : "No line has a price yet.";
    const partial = result.unpriced ? ` ${makeCount(result.unpriced, "line")} without a price ${result.unpriced === 1 ? "is" : "are"} not counted; add prices on the Stock page.` : "";
    shopping.append(makeEl(doc, "p", "make-total", `${total}${partial}`));
  }

  async function loadDensities(all) {
    const names = makeDensityNames(all.filter(({ formula }) => view.picked.has(formula.formula_id)).map(({ items }) => items), getPrices())
      .filter((name) => !(makeNameKey(name) in view.densities));
    if (!names.length) return;
    try {
      const answer = await request("/v2/workbench/material-densities", { method: "POST", body: JSON.stringify({ names }) });
      for (const name of names) view.densities[makeNameKey(name)] = answer?.densities?.[name] ?? null;
      render();
    } catch {
      for (const name of names) view.densities[makeNameKey(name)] = null;
    }
  }

  function render() {
    if (!view.data) return;
    const all = checks();
    const counts = { ok: 0, short: 0, unknown: 0 };
    all.forEach(({ items }) => { counts[makeVerdict(items, bottleMl()).status] += 1; });
    status.textContent = all.length
      ? `${makeCount(all.length, "saved formula")} at ${bottleMl()} mL: ${counts.ok} you can mix now, ${counts.short} short, ${counts.unknown} waiting on how much is left.`
      : "";
    renderFormulas(all);
    renderShopping(all);
    loadDensities(all);
  }

  async function load() {
    status.textContent = "Reading your saved formulas…";
    try {
      view.data = await request("/v2/workbench/make-now");
      render();
    } catch (error) {
      status.textContent = `Could not read your saved formulas: ${error?.message || error}`;
    }
  }

  bottleInput.addEventListener("change", render);
  root.querySelector("#make-refresh").addEventListener("click", load);

  return {
    // The page is shown: read the formulas once; Refresh reads them again.
    shown() {
      if (!view.data && !view.loading) view.loading = load().finally(() => { view.loading = null; });
    },
    // Inventory or prices changed elsewhere: redraw with them.
    changed: render,
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    makeAmount, makeStockFor, makeNeeds, makeCheck, makeVerdict, makeLineText, makeShopping, makeDensityNames, makeAmountText,
    MAKE_NOT_OWNED_GROUP, MAKE_YOURSELF_GROUP, MAKE_NO_SUPPLIER,
  };
}
