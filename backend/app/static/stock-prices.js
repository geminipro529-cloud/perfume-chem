// Prices on the Stock page and costs on the bench sheet. Kenny (2026-10-13)
// sells in Thailand and types every price himself: per g or per mL of the
// stock as it sits in the bottle, or "paid X for Y". Ethanol (per mL) and
// packaging (bottle, cap, box and label, per bottle) are two fixed items.
//
// Money is exact: amounts and prices are BigInt fractions, rounded to 2
// places only for display. A row is costed only when its unit and the price's
// unit measure the same thing (µL/mL with mL, mg/g with g); stocks carry no
// density, so a per-g price never costs a µL row. Such rows are listed and the
// totals say they are partial.
//
// The page loads this before lab.js. Material names and anything typed go in
// through textContent / .value only. Node loads the same file in the tests.

const STOCK_PRICE_ENDPOINT = "/v2/workbench/stock-prices";
const STOCK_PRICE_ETHANOL = "ethanol";
const STOCK_PRICE_PACKAGING = "packaging_per_bottle";
const STOCK_PRICE_DECIMAL = /^\d+(\.\d+)?$/;
const STOCK_PRICE_ETHANOL_NAMES = new Set(["ethanol", "perfumer's alcohol", "perfumers alcohol", "alcohol"]);
// Row unit -> [price unit it can be costed in, divisor to that unit].
const STOCK_PRICE_ROW_UNITS = { "µL": ["mL", 1000n], mL: ["mL", 1n], mg: ["g", 1000n], g: ["g", 1n] };

let stockPricesCache = {};

function stockPricesCurrent() {
  return stockPricesCache;
}

function stockPriceGcd(a, b) {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y) [x, y] = [y, x % y];
  return x || 1n;
}
function stockPriceFrac(n, d) {
  const g = stockPriceGcd(n, d);
  return { n: n / g, d: d / g };
}
// A plain non-negative decimal as an exact fraction; null otherwise.
function stockPriceFraction(text) {
  const trimmed = String(text ?? "").trim();
  if (!STOCK_PRICE_DECIMAL.test(trimmed)) return null;
  const [whole, fraction = ""] = trimmed.split(".");
  return stockPriceFrac(BigInt(whole + fraction), 10n ** BigInt(fraction.length));
}
const stockPriceTimes = (a, b) => stockPriceFrac(a.n * b.n, a.d * b.d);
const stockPricePlus = (a, b) => stockPriceFrac(a.n * b.d + b.n * a.d, a.d * b.d);
const STOCK_PRICE_ZERO = { n: 0n, d: 1n };

// Rounded half up to 2 places, always with 2 decimals: "12.35 THB".
function stockPriceMoneyText(value, currency) {
  const cents = (2n * value.n * 100n + value.d) / (2n * value.d);
  const digits = cents.toString().padStart(3, "0");
  return `${digits.slice(0, -2)}.${digits.slice(-2)}${currency ? ` ${currency}` : ""}`;
}

// The exact price per unit: from the pack when Kenny gave one, else as typed.
function stockPriceUnitPrice(entry) {
  if (!entry) return null;
  const paid = stockPriceFraction(entry.pack_price);
  const size = stockPriceFraction(entry.pack_size);
  if (paid && size && size.n > 0n) return stockPriceFrac(paid.n * size.d, paid.d * size.n);
  return stockPriceFraction(entry.price_decimal);
}

function stockPriceLabel(entry) {
  if (!entry) return "";
  const currency = entry.currency || "THB";
  if (entry.pack_price && entry.pack_size) return `${entry.pack_price} ${currency} for ${entry.pack_size} ${entry.per_unit}`;
  return `${entry.price_decimal} ${currency} per ${entry.per_unit}`;
}

function stockPriceButtonText(stockId) {
  const entry = stockPricesCache[stockId];
  return entry ? `Price: ${stockPriceLabel(entry)}` : "Add price";
}

// The POST body for one entry. fields.mode is "pack" ("paid X for Y") or
// anything else for a price per unit.
function stockPriceRequestBody(stockId, fields) {
  const text = (value) => String(value ?? "").trim();
  const pack = fields.mode === "pack";
  return {
    stock_id: stockId,
    per_unit: text(fields.per_unit),
    price_decimal: pack ? null : text(fields.price_decimal) || null,
    pack_price: pack ? text(fields.pack_price) || null : null,
    pack_size: pack ? text(fields.pack_size) || null : null,
    currency: (text(fields.currency) || "THB").toUpperCase(),
    note: text(fields.note),
  };
}

function stockPriceUnitKey(unit) {
  const text = String(unit ?? "").trim();
  return /^[uµμ]L$/.test(text) ? "µL" : text;
}

function stockPriceNameKey(value) {
  return String(value ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

function stockPriceIsEthanolRow(row) {
  return [row.material, row.identity_name].some((name) => STOCK_PRICE_ETHANOL_NAMES.has(stockPriceNameKey(name)));
}

// Cost of one row, or the reason it is not costed.
function benchCostRow(row, prices) {
  const material = String(row.material ?? "");
  const unit = stockPriceUnitKey(row.amount_unit);
  const amountText = String(row.amount_decimal ?? "").trim();
  const base = { material, amount: amountText, unit, cost: null, currency: null, reason: "" };
  let entry = row.stock_id ? prices[String(row.stock_id)] : undefined;
  if (!entry && stockPriceIsEthanolRow(row)) entry = prices[STOCK_PRICE_ETHANOL];
  if (!entry) return { ...base, reason: row.stock_id ? "no price yet" : "no price: not matched to a stock" };
  const amount = stockPriceFraction(amountText);
  if (!amount) return { ...base, reason: "amount is not a plain number" };
  const conversion = STOCK_PRICE_ROW_UNITS[unit];
  if (!conversion) return { ...base, reason: `not costed: the row is in ${unit || "no unit"}` };
  const [priceUnit, divisor] = conversion;
  if (priceUnit !== entry.per_unit) {
    return { ...base, reason: `not costed: price is per ${entry.per_unit}, row is in ${unit}, no density` };
  }
  const price = stockPriceUnitPrice(entry);
  if (!price) return { ...base, reason: "price is not a plain number" };
  const cost = stockPriceTimes(stockPriceFrac(amount.n, amount.d * divisor), price);
  return { ...base, cost, currency: entry.currency || "THB" };
}

// Ethanol after the concentrate, mL per bottle: the bottle less the liquid
// stock rows (solids are taken to add no volume). "0" when the formula lists
// ethanol as a row itself; "" when the bottle size is not known.
function benchCostEthanolEstimate(rows, bottleMl) {
  if ((rows || []).some(stockPriceIsEthanolRow)) return "0";
  const bottle = stockPriceFraction(bottleMl);
  if (!bottle) return "";
  let liquidUl = STOCK_PRICE_ZERO;
  for (const row of rows || []) {
    const unit = stockPriceUnitKey(row.amount_unit);
    const amount = stockPriceFraction(row.amount_decimal);
    if (!amount) continue;
    if (unit === "µL") liquidUl = stockPricePlus(liquidUl, amount);
    if (unit === "mL") liquidUl = stockPricePlus(liquidUl, stockPriceTimes(amount, { n: 1000n, d: 1n }));
  }
  const left = stockPriceFrac(bottle.n * 1000n * liquidUl.d - liquidUl.n * bottle.d, bottle.d * 1000n * liquidUl.d);
  if (left.n <= 0n) return "0";
  const thousandths = (2n * left.n * 1000n + left.d) / (2n * left.d);
  const digits = thousandths.toString().padStart(4, "0");
  const fraction = digits.slice(-3).replace(/0+$/, "");
  return fraction ? `${digits.slice(0, -3)}.${fraction}` : digits.slice(0, -3);
}

// The whole cost block: per row, one bottle (rows + ethanol + packaging) and
// `bottles` bottles. Totals are exact sums; `partial` says something was left out.
function benchCost({ rows, prices, ethanolMl, bottles }) {
  const lines = (rows || []).map((row) => benchCostRow(row, prices || {}));
  const currencies = new Set(lines.filter((line) => line.cost).map((line) => line.currency));
  const missing = lines.filter((line) => !line.cost).map((line) => line.material);
  const extras = [];
  const ethanolPrice = stockPriceUnitPrice((prices || {})[STOCK_PRICE_ETHANOL]);
  const ethanolAmount = stockPriceFraction(ethanolMl);
  const ethanol = { label: "Ethanol", amount: String(ethanolMl ?? "").trim(), cost: null, reason: "" };
  if (!ethanolAmount) ethanol.reason = "say how much ethanol goes in";
  else if (!ethanolPrice) ethanol.reason = "no ethanol price yet";
  else {
    ethanol.cost = stockPriceTimes(ethanolAmount, ethanolPrice);
    currencies.add(prices[STOCK_PRICE_ETHANOL].currency || "THB");
  }
  extras.push(ethanol);
  const packagingPrice = stockPriceUnitPrice((prices || {})[STOCK_PRICE_PACKAGING]);
  const packaging = { label: "Packaging", amount: "1", cost: null, reason: "" };
  if (!packagingPrice) packaging.reason = "no packaging price yet";
  else {
    packaging.cost = packagingPrice;
    currencies.add(prices[STOCK_PRICE_PACKAGING].currency || "THB");
  }
  extras.push(packaging);
  const left = [...missing, ...extras.filter((item) => !item.cost).map((item) => item.label)];
  const result = { lines, extras, missing: left, partial: left.length > 0, currency: null, bottle: null, batch: null, bottles: null, problem: "" };
  if (currencies.size > 1) {
    result.problem = `Prices are in more than one currency (${[...currencies].sort().join(", ")}); totals are not added.`;
    return result;
  }
  result.currency = [...currencies][0] || "THB";
  let bottle = STOCK_PRICE_ZERO;
  for (const item of [...lines, ...extras]) if (item.cost) bottle = stockPricePlus(bottle, item.cost);
  result.bottle = bottle;
  const count = String(bottles ?? "").trim();
  if (!/^[1-9]\d{0,4}$/.test(count)) {
    result.problem = "Number of bottles must be a whole number from 1 to 99999.";
    return result;
  }
  result.bottles = count;
  result.batch = stockPriceTimes(bottle, { n: BigInt(count), d: 1n });
  return result;
}

// ---- DOM ----

function stockPriceNode(doc, tag, attributes = {}, text = "") {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

function stockPriceInput(doc, fields, name, labelText, attributes = {}, value = "") {
  const label = stockPriceNode(doc, "label", {}, labelText);
  const input = stockPriceNode(doc, "input", { name, ...attributes });
  input.value = value;
  label.appendChild(input);
  fields[name] = input;
  return label;
}

function stockPriceSelect(doc, fields, name, labelText, options, value) {
  const label = stockPriceNode(doc, "label", {}, labelText);
  const select = stockPriceNode(doc, "select", { name });
  for (const [optionValue, text] of options) select.appendChild(stockPriceNode(doc, "option", { value: optionValue }, text));
  select.value = value;
  label.appendChild(select);
  fields[name] = select;
  return label;
}

const STOCK_PRICE_NUMBER = { inputmode: "decimal", pattern: "[0-9]+(\\.[0-9]+)?", autocomplete: "off" };

// One price form. units: the units it may be priced in, e.g. ["g", "mL"].
function buildStockPriceForm(doc, { entry, units, help }) {
  const fields = {};
  const form = stockPriceNode(doc, "form", { class: "form-panel inventory-completion-form stock-price-form" });
  if (help) form.appendChild(stockPriceNode(doc, "p", { class: "field-help" }, help));
  const packMode = Boolean(entry?.pack_price);
  const unit = units.includes(entry?.per_unit) ? entry.per_unit : units[0];
  const head = stockPriceNode(doc, "div", { class: "field-pair" });
  head.appendChild(stockPriceSelect(doc, fields, "mode", "Price given as",
    [["unit", "price per unit"], ["pack", "paid X for Y"]], packMode ? "pack" : "unit"));
  if (units.length > 1) head.appendChild(stockPriceSelect(doc, fields, "per_unit", "Unit", units.map((u) => [u, `per ${u}`]), unit));
  form.appendChild(head);
  const perUnit = stockPriceNode(doc, "div", { class: "field-pair" });
  perUnit.appendChild(stockPriceInput(doc, fields, "price_decimal", `Price per ${unit}`, STOCK_PRICE_NUMBER, packMode ? "" : entry?.price_decimal || ""));
  const pack = stockPriceNode(doc, "div", { class: "field-pair" });
  pack.appendChild(stockPriceInput(doc, fields, "pack_price", "Paid", STOCK_PRICE_NUMBER, entry?.pack_price || ""));
  pack.appendChild(stockPriceInput(doc, fields, "pack_size", `For how many ${unit}`, STOCK_PRICE_NUMBER, entry?.pack_size || ""));
  form.append(perUnit, pack);
  const more = stockPriceNode(doc, "div", { class: "field-pair" });
  more.appendChild(stockPriceInput(doc, fields, "currency", "Currency", { maxlength: "3", autocomplete: "off" }, entry?.currency || "THB"));
  more.appendChild(stockPriceInput(doc, fields, "note", "Note (optional)", { maxlength: "500" }, entry?.note || ""));
  form.appendChild(more);
  const error = stockPriceNode(doc, "p", { class: "status-line is-error", role: "alert" });
  error.hidden = true;
  form.appendChild(error);
  const actions = stockPriceNode(doc, "div", { class: "request-actions" });
  const submit = stockPriceNode(doc, "button", { type: "submit" }, "Save price");
  const clear = stockPriceNode(doc, "button", { type: "button", class: "quiet-button" }, "Remove price");
  clear.hidden = !entry;
  actions.append(submit, clear);
  form.appendChild(actions);
  const sync = () => {
    const chosen = fields.per_unit ? fields.per_unit.value : unit;
    const isPack = fields.mode.value === "pack";
    perUnit.hidden = isPack;
    pack.hidden = !isPack;
    fields.price_decimal.parentNode.firstChild.textContent = `Price per ${chosen}`;
    fields.pack_size.parentNode.firstChild.textContent = `For how many ${chosen}`;
  };
  fields.mode.addEventListener("change", sync);
  if (fields.per_unit) fields.per_unit.addEventListener("change", sync);
  sync();
  form.priceParts = { fields, error, submit, clear, unit };
  return form;
}

function stockPriceFormValues(form) {
  const { fields, unit } = form.priceParts;
  const values = Object.fromEntries(Object.entries(fields).map(([name, node]) => [name, node.value]));
  if (!values.per_unit) values.per_unit = unit;
  return values;
}

async function saveStockPrice(form, stockId, request, { clear = false } = {}) {
  const { error, submit } = form.priceParts;
  error.hidden = true;
  submit.disabled = true;
  try {
    const values = stockPriceFormValues(form);
    const body = clear
      ? { stock_id: stockId, per_unit: values.per_unit, clear: true }
      : stockPriceRequestBody(stockId, values);
    const result = await request(STOCK_PRICE_ENDPOINT, { method: "POST", body: JSON.stringify(body) });
    stockPricesCache = result.prices || {};
    return result;
  } catch (failure) {
    error.textContent = failure.message || "The price was not saved.";
    error.hidden = false;
    return null;
  } finally {
    submit.disabled = false;
  }
}

// Stock page: a "Price" button per stock opens a form; one panel holds
// ethanol and packaging. onChange runs after prices load or change.
function attachStockPrices({ doc, list, request, getInventory, onChange }) {
  const article = list.closest("article") || list;
  const costs = stockPriceNode(doc, "article", { id: "stock-cost-items", class: "panel inventory-completion-panel" });
  const panel = stockPriceNode(doc, "article", { id: "stock-price-panel", class: "panel inventory-completion-panel" });
  panel.hidden = true;
  article.after(panel);
  article.after(costs);

  function drawCosts() {
    const title = stockPriceNode(doc, "div", { class: "card-title-row" });
    const heading = stockPriceNode(doc, "div");
    heading.appendChild(stockPriceNode(doc, "p", { class: "panel-index" }, "Costs per bottle"));
    heading.appendChild(stockPriceNode(doc, "h2", {}, "Ethanol and packaging"));
    title.appendChild(heading);
    const forms = [
      [STOCK_PRICE_ETHANOL, ["mL"], "Ethanol, per mL."],
      [STOCK_PRICE_PACKAGING, ["bottle"], "Packaging per bottle: bottle, cap, box and label together."],
    ].map(([id, units, help]) => {
      const form = buildStockPriceForm(doc, { entry: stockPricesCache[id], units, help });
      form.dataset.costItem = id;
      wire(form, id, () => drawCosts());
      return form;
    });
    costs.replaceChildren(title, ...forms);
  }

  function wire(form, stockId, after) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (await saveStockPrice(form, stockId, request)) { after(); onChange(); }
    });
    form.priceParts.clear.addEventListener("click", async () => {
      if (await saveStockPrice(form, stockId, request, { clear: true })) { after(); onChange(); }
    });
  }

  function close() {
    panel.hidden = true;
    panel.replaceChildren();
  }

  function open(stock) {
    const title = stockPriceNode(doc, "div", { class: "card-title-row" });
    const heading = stockPriceNode(doc, "div");
    heading.appendChild(stockPriceNode(doc, "p", { class: "panel-index" }, "Price"));
    heading.appendChild(stockPriceNode(doc, "h2", {}, stock.identity_name || stock.material || ""));
    title.appendChild(heading);
    const cancel = stockPriceNode(doc, "button", { type: "button", class: "quiet-button" }, "Close");
    cancel.addEventListener("click", close);
    title.appendChild(cancel);
    const strength = `${stock.fraction_percent_decimal ?? ""}%${stock.carrier ? ` in ${stock.carrier}` : ""}`;
    const form = buildStockPriceForm(doc, {
      entry: stockPricesCache[stock.stock_id],
      units: ["g", "mL"],
      help: `What this ${strength} stock cost you, as it is in the bottle. A per-g price costs mg rows and a per-mL price costs µL rows.`,
    });
    wire(form, stock.stock_id, close);
    panel.replaceChildren(title, form);
    panel.hidden = false;
    panel.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-price-stock]");
    if (!button) return;
    const stock = (getInventory().stocks || []).find((item) => item.stock_id === button.dataset.priceStock);
    if (stock) open(stock);
  });

  const load = () => request(STOCK_PRICE_ENDPOINT).then((result) => {
    stockPricesCache = result.prices || {};
    drawCosts();
    onChange();
  }).catch((failure) => {
    costs.replaceChildren(stockPriceNode(doc, "p", { class: "status-line is-error", role: "status" }, failure.message || "Couldn't load your prices."));
  });
  drawCosts();
  return { load };
}

// Bench sheet: the cost block under the preview. Redraws on its own inputs.
function showBenchCost({ doc, container, rows, bottleMl, prices = stockPricesCache }) {
  const fields = {};
  const heading = stockPriceNode(doc, "h2", {}, "Cost");
  const inputs = stockPriceNode(doc, "div", { class: "field-pair" });
  inputs.appendChild(stockPriceInput(doc, fields, "cost_bottles", "Bottles in this batch", { inputmode: "numeric", autocomplete: "off" }, "1"));
  inputs.appendChild(stockPriceInput(doc, fields, "cost_ethanol_ml", "Ethanol per bottle, mL (estimate: bottle less liquid stock; change to what you add)", STOCK_PRICE_NUMBER, benchCostEthanolEstimate(rows, bottleMl)));
  const out = stockPriceNode(doc, "div", { class: "bench-cost-result", "aria-live": "polite" });
  const draw = () => {
    const cost = benchCost({ rows, prices, ethanolMl: fields.cost_ethanol_ml.value, bottles: fields.cost_bottles.value });
    const table = stockPriceNode(doc, "table", { class: "bench-sheet-table bench-cost-table" });
    const head = stockPriceNode(doc, "tr");
    for (const title of ["Material", "Amount", "Cost"]) head.appendChild(stockPriceNode(doc, "th", { scope: "col" }, title));
    table.appendChild(stockPriceNode(doc, "thead")).appendChild(head);
    const body = stockPriceNode(doc, "tbody");
    const money = (value) => stockPriceMoneyText(value, cost.currency);
    for (const line of [...cost.lines, ...cost.extras]) {
      const tr = stockPriceNode(doc, "tr");
      tr.appendChild(stockPriceNode(doc, "td", {}, line.material || line.label));
      const amount = line.label === "Packaging" ? "1 bottle" : line.label === "Ethanol" ? `${line.amount || "?"} mL` : `${line.amount} ${line.unit}`;
      tr.appendChild(stockPriceNode(doc, "td", {}, amount));
      tr.appendChild(stockPriceNode(doc, "td", line.cost ? {} : { class: "bench-cost-missing" }, line.cost ? money(line.cost) : line.reason));
      body.appendChild(tr);
    }
    table.appendChild(body);
    const summary = [];
    const partial = cost.partial ? " (partial: leaves out rows without a cost)" : "";
    if (cost.problem) summary.push(stockPriceNode(doc, "p", { class: "status-line is-error", role: "status" }, cost.problem));
    if (cost.bottle) summary.push(stockPriceNode(doc, "p", { class: "bench-cost-total" }, `One bottle: ${money(cost.bottle)}${partial}`));
    if (cost.batch) summary.push(stockPriceNode(doc, "p", { class: "bench-cost-total" }, `${cost.bottles} bottle${cost.bottles === "1" ? "" : "s"}: ${money(cost.batch)}${partial}`));
    if (cost.missing.length) summary.push(stockPriceNode(doc, "p", { class: "bench-sheet-note" }, `Not costed: ${cost.missing.join(", ")}.`));
    out.replaceChildren(...summary, table);
  };
  fields.cost_bottles.addEventListener("input", draw);
  fields.cost_ethanol_ml.addEventListener("input", draw);
  draw();
  container.replaceChildren(heading, inputs, out);
  container.hidden = false;
  return { draw, fields };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    STOCK_PRICE_ENDPOINT, stockPriceFraction, stockPriceUnitPrice, stockPriceMoneyText, stockPriceLabel,
    stockPriceRequestBody, benchCostRow, benchCostEthanolEstimate, benchCost, buildStockPriceForm,
    attachStockPrices, showBenchCost, stockPricesCurrent, stockPriceButtonText,
  };
}
