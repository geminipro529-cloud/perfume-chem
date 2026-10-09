// Pure bench-sheet logic. It touches no DOM, so the page loads it before
// lab.js (its functions become page globals) and node runs it in the tests.

const BENCH_MIN_PIPETTE_UL = 10;
const BENCH_DECIMAL = /^\d+(\.\d+)?$/;

function benchEscape(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

// Exact sum of two non-negative decimal strings, so a running total never
// drifts from the pipetted values the design gives (no float rounding).
// Returns the sum without trailing zeros, or null when either side is not a
// plain decimal.
function addDecimalText(left, right) {
  if (!BENCH_DECIMAL.test(String(left)) || !BENCH_DECIMAL.test(String(right))) return null;
  const [leftWhole, leftFraction = ""] = String(left).split(".");
  const [rightWhole, rightFraction = ""] = String(right).split(".");
  const scale = Math.max(leftFraction.length, rightFraction.length);
  const sum = BigInt(leftWhole + leftFraction.padEnd(scale, "0")) + BigInt(rightWhole + rightFraction.padEnd(scale, "0"));
  const digits = sum.toString().padStart(scale + 1, "0");
  if (!scale) return digits;
  const fraction = digits.slice(-scale).replace(/0+$/, "");
  return fraction ? `${digits.slice(0, -scale)}.${fraction}` : digits.slice(0, -scale);
}

// "uL", "µL" (micro sign) and "μL" (Greek mu) are one unit; every other unit stays apart.
function benchUnitKey(unit) {
  const text = String(unit ?? "").trim();
  return /^[uµμ]L$/.test(text) ? "µL" : text;
}

// Stock strength as a percentage without locale formatting: the decimal
// point of the exact fraction is moved two places.
function benchPercentText(fraction) {
  const text = String(fraction ?? "").trim();
  if (!BENCH_DECIMAL.test(text)) return null;
  const [whole, part = ""] = text.split(".");
  const digits = whole + part.padEnd(2, "0");
  const integer = digits.slice(0, whole.length + 2).replace(/^0+(?=\d)/, "");
  const decimals = digits.slice(whole.length + 2).replace(/0+$/, "");
  return decimals ? `${integer}.${decimals}%` : `${integer}%`;
}

// The planner's basis codes in the words a bench card uses: "w/w", not "mass_fraction".
const BENCH_BASIS_TEXT = { mass_fraction: "w/w", volume_fraction: "v/v", mass_per_volume: "w/v" };
function benchBasisText(basis) {
  const text = String(basis ?? "").trim();
  return BENCH_BASIS_TEXT[text] || text.replaceAll("_", " ");
}

// A liquid row the planner marks PREPARED_DILUTION_REQUIRED (raw volume of the
// existing stock under the 10 uL transfer floor) is not pipetted as written.
function benchNeedsPreparedDilution(row) {
  if (row.operation === "PREPARED_DILUTION_REQUIRED") return true;
  const amount = String(row.amount_decimal ?? "").trim();
  return benchUnitKey(row.amount_unit) === "µL" && BENCH_DECIMAL.test(amount) && Number(amount) > 0 && Number(amount) < BENCH_MIN_PIPETTE_UL;
}

function benchDilutionMark(amount, unit) {
  if (benchUnitKey(unit) === "µL" && BENCH_DECIMAL.test(amount) && Number(amount) < BENCH_MIN_PIPETTE_UL) {
    return `Prepare a dilution first: ${amount} ${unit} of this stock is under 10 ${unit}, too small to pipette as written.`;
  }
  return "Prepare a dilution first: the design marks this amount as too small to pipette as written.";
}

// Kenny's pipetting floor (2026-10-08): pour 20 uL or more. A liquid row from
// 10 uL up to under 20 uL is diluted 1:1 by volume in ethanol and pipetted at
// twice the amount. Under 10 uL stays the prepared-dilution hold above.
const BENCH_SMALL_POUR_UL = 20;
const BENCH_SMALL_POUR_TEXT = "Under 20 µL: dilute 1:1 in ethanol, pipette double";

function benchSmallPour(row) {
  if (benchNeedsPreparedDilution(row)) return false;
  const amount = String(row.amount_decimal ?? "").trim();
  return benchUnitKey(row.amount_unit) === "µL" && BENCH_DECIMAL.test(amount)
    && Number(amount) >= BENCH_MIN_PIPETTE_UL && Number(amount) < BENCH_SMALL_POUR_UL;
}

// Exact comparison of two plain decimal strings (-1, 0, 1); no float rounding.
function compareDecimalText(left, right) {
  const [leftWhole, leftFraction = ""] = String(left).split(".");
  const [rightWhole, rightFraction = ""] = String(right).split(".");
  const scale = Math.max(leftFraction.length, rightFraction.length);
  const a = BigInt(leftWhole + leftFraction.padEnd(scale, "0"));
  const b = BigInt(rightWhole + rightFraction.padEnd(scale, "0"));
  if (a === b) return 0;
  return a < b ? -1 : 1;
}

function benchNameKey(value) {
  return String(value ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

// Basket data from GET /v2/workbench/current-inventory: each stock may carry
// "basket" (1-17 or null) and "basket_status"; the top level lists "baskets".
// Returns null for an older payload without baskets, so callers keep the
// design order. A name shared by stocks in different baskets is not used.
function benchBasketLookup(inventory) {
  if (!inventory || !Array.isArray(inventory.baskets) || !inventory.baskets.length) return null;
  const names = new Map();
  inventory.baskets.forEach((basket) => {
    if (Number.isInteger(basket?.number)) names.set(basket.number, String(basket.name ?? ""));
  });
  const byStockId = new Map();
  const byName = new Map();
  (inventory.stocks || []).forEach((stock) => {
    const basket = Number.isInteger(stock.basket) && stock.basket >= 1 && stock.basket <= 17 ? stock.basket : null;
    const entry = { basket, status: String(stock.basket_status || "none") };
    if (stock.stock_id) byStockId.set(String(stock.stock_id), entry);
    new Set([stock.material, stock.identity_name, stock.normalized_identity].map(benchNameKey).filter(Boolean)).forEach((key) => {
      const seen = byName.get(key);
      if (seen === undefined) byName.set(key, entry);
      else if (seen && (seen.basket !== entry.basket || seen.status !== entry.status)) byName.set(key, null);
    });
  });
  return { names, byStockId, byName };
}

// Carriers and solvents stay in their own pre-charge block before the baskets.
// Benzyl benzoate is not listed: Kenny keeps it in basket 1.
const BENCH_CARRIER_NAMES = new Set(["ethanol", "perfumer's alcohol", "dpg", "dipropylene glycol", "ipm", "isopropyl myristate", "dep", "diethyl phthalate", "tec", "triethyl citrate"]);
function benchIsCarrierRow(row) {
  return row.operation === "PRECHARGE" || BENCH_CARRIER_NAMES.has(benchNameKey(row.material));
}

// The stock id decides when the inventory knows it; otherwise the material or
// identity name. A conflicting assignment is not a basket to walk to.
function benchRowBasket(row, lookup) {
  const byStock = row.stock_id ? lookup.byStockId.get(String(row.stock_id)) : undefined;
  const found = byStock !== undefined
    ? byStock
    : [row.material, row.identity_name].map(benchNameKey).filter(Boolean).map((key) => lookup.byName.get(key)).find(Boolean) || null;
  if (!found || found.basket === null || found.status === "conflicting") return { basket: null, status: found ? found.status : "none" };
  return found;
}

// Liquids before mg solids, larger raw amount first, then material name.
// Amounts that are not plain decimals go after the ones that are.
function benchPourCompare(left, right) {
  const leftMass = benchUnitKey(left.row.amount_unit) === "mg" ? 1 : 0;
  const rightMass = benchUnitKey(right.row.amount_unit) === "mg" ? 1 : 0;
  if (leftMass !== rightMass) return leftMass - rightMass;
  const a = String(left.row.amount_decimal ?? "").trim();
  const b = String(right.row.amount_decimal ?? "").trim();
  const aOk = BENCH_DECIMAL.test(a);
  const bOk = BENCH_DECIMAL.test(b);
  if (aOk !== bOk) return aOk ? -1 : 1;
  const byAmount = aOk ? compareDecimalText(b, a) : 0;
  if (byAmount) return byAmount;
  const byName = benchNameKey(left.row.material).localeCompare(benchNameKey(right.row.material));
  return byName || left.index - right.index;
}

// Kenny's basket order (docs/basket_order_preference.md): the carrier pre-charge
// block first, then baskets 1 to 17, then rows with no basket yet, then any
// final make-up (POSTCHARGE, in design order). Inside a block the largest raw
// pour comes first. The row objects are returned as given, amounts untouched.
// Each entry carries its group key and heading; with no basket data the rows
// keep the design order and carry no group.
function benchBasketOrder(rows, lookup) {
  if (!lookup) return (rows || []).map((row) => ({ row, group: null, basket: null, heading: "", check: false }));
  const entries = (rows || []).map((row, index) => ({ row, index, basket: null, check: false }));
  entries.forEach((entry) => {
    if (entry.row.operation === "POSTCHARGE") Object.assign(entry, { rank: 1000, group: "postcharge" });
    else if (benchIsCarrierRow(entry.row)) Object.assign(entry, { rank: 0, group: "carrier" });
    else {
      const found = benchRowBasket(entry.row, lookup);
      entry.basket = found.basket;
      entry.check = found.basket !== null && found.status === "from_past_cards";
      entry.rank = found.basket === null ? 999 : found.basket;
      entry.group = found.basket === null ? "unassigned" : `basket-${found.basket}`;
    }
  });
  entries.sort((left, right) => (left.rank - right.rank)
    || (left.group === "postcharge" ? left.index - right.index : benchPourCompare(left, right)));
  const checked = new Set(entries.filter((entry) => entry.check).map((entry) => entry.group));
  return entries.map((entry) => {
    let heading = "Carriers and solvents · pre-charge";
    if (entry.group === "postcharge") heading = "Final make-up";
    else if (entry.group === "unassigned") heading = "No basket yet";
    else if (entry.basket !== null) {
      const name = lookup.names.get(entry.basket);
      heading = `Basket ${entry.basket}${name ? ` · ${name}` : ""}`;
    }
    return { row: entry.row, group: entry.group, basket: entry.basket, heading, check: checked.has(entry.group) };
  });
}

// One line per row, in the order given. Running totals are exact and per
// unit, and cover only rows that can be pipetted or weighed as written.
function benchSheetLines(rows) {
  const running = {};
  let leftOut = 0;
  const lines = (rows || []).map((row, index) => {
    const unit = String(row.amount_unit ?? "");
    const amount = String(row.amount_decimal ?? "").trim();
    const key = benchUnitKey(unit);
    const percent = benchPercentText(row.stock_fraction_decimal);
    const line = {
      number: index + 1,
      material: String(row.material ?? ""),
      stockLabel: String(row.stock_label || row.material || ""),
      strength: `${percent ?? String(row.stock_fraction_decimal ?? "")} ${benchBasisText(row.fraction_basis)}${row.carrier ? ` in ${row.carrier}` : ""}`.trim(),
      amount,
      unit,
      unitKey: key,
      mass: key === "mg",
      pipettable: !benchNeedsPreparedDilution(row),
      smallPour: benchSmallPour(row),
      runningTotal: null,
      mark: null,
    };
    if (!line.pipettable) {
      leftOut += 1;
      line.mark = benchDilutionMark(amount, unit);
      return line;
    }
    running[key] = running[key] === undefined ? addDecimalText("0", amount) : addDecimalText(running[key], amount);
    line.runningTotal = running[key] === null ? "check by hand" : `${running[key]} ${key}`;
    return line;
  });
  return { lines, leftOut };
}

// The page's own hold wording: "Proposal · check hold" when the critic has
// issues or any row is not execution ready.
function benchSheetHold(rows, critic) {
  const issues = (critic?.issues || []).map((issue) => String(issue).replaceAll("_", " ").toLowerCase());
  const onHold = issues.length > 0 || (rows || []).some((row) => row.execution_ready === false);
  return { onHold, stateText: onHold ? "Proposal · check hold" : "Proposal only", issues };
}

function benchLeaveOutNote(leftOut) {
  if (!leftOut) return "";
  return leftOut === 1
    ? "Running totals leave out 1 row that needs a prepared dilution first."
    : `Running totals leave out ${leftOut} rows that need a prepared dilution first.`;
}

const BENCH_DESIGN_ORDER_TEXT = "Order as designed. Use your own basket order at the balance.";
const BENCH_BASKET_ORDER_TEXT = "Basket order 1 to 17, largest pour first in each basket. Baskets marked 'check' come from past cards.";

// basketLookup (from benchBasketLookup) is optional: without it the sheet keeps
// the design order, exactly as before baskets existed.
function benchSheetHtml({ formulaName, variantLabel, dateText, totals, rows, critic, basketLookup = null }) {
  const ordered = benchBasketOrder(rows, basketLookup);
  const { lines, leftOut } = benchSheetLines(ordered.map((entry) => entry.row));
  const hold = benchSheetHold(rows, critic);
  const totalParts = [];
  if (totals?.liquid_total_ul !== undefined) totalParts.push(`${totals.liquid_total_ul} µL liquid stock`);
  if (Number(totals?.mass_total_mg) > 0) totalParts.push(`${totals.mass_total_mg} mg solids, weighed as separate mg lines`);
  const note = benchLeaveOutNote(leftOut);
  let group = null;
  const body = lines.map((line, index) => {
    const entry = ordered[index];
    let heading = "";
    if (entry.group && entry.group !== group) {
      group = entry.group;
      heading = `<tr class="bench-basket-row"><th colspan="6" scope="colgroup">${benchEscape(entry.heading)}${entry.check ? " · check" : ""}</th></tr>`;
    }
    const classes = [line.mass ? "bench-mass-line" : "", line.pipettable ? "" : "bench-dilution-line"].filter(Boolean).join(" ");
    return `${heading}<tr${classes ? ` class="${classes}"` : ""}>
      <td class="bench-number">${line.number}</td>
      <td>${line.pipettable ? '<span class="bench-tick" role="img" aria-label="not yet added"></span>' : ""}</td>
      <td><strong>${benchEscape(line.material)}</strong>${entry.basket !== null ? `<small class="bench-basket-tag">Basket ${benchEscape(entry.basket)}</small>` : entry.group === "unassigned" ? '<small class="bench-basket-tag">No basket</small>' : ""}${line.mark ? `<small class="bench-dilution-mark">${benchEscape(line.mark)}</small>` : ""}${line.smallPour ? `<small class="bench-small-pour">${benchEscape(BENCH_SMALL_POUR_TEXT)}</small>` : ""}</td>
      <td>${benchEscape(line.stockLabel)}<small>${benchEscape(line.strength)}</small></td>
      <td class="bench-amount">${benchEscape(line.amount)} ${benchEscape(line.unit)}</td>
      <td class="bench-amount">${line.pipettable ? benchEscape(line.runningTotal) : "not in total"}</td>
    </tr>`;
  }).join("");
  return `
    <header class="bench-sheet-header">
      <p class="bench-sheet-kicker">Bench sheet · design proposal, not a compounding authorization</p>
      <h1>${benchEscape(formulaName || "Formula draft")}${variantLabel ? ` · ${benchEscape(variantLabel)}` : ""}</h1>
      <dl>
        <div><dt>State</dt><dd>${benchEscape(hold.stateText)}</dd></div>
        ${hold.issues.length ? `<div><dt>Holds</dt><dd>${benchEscape(hold.issues.join("; "))}</dd></div>` : ""}
        <div><dt>Date</dt><dd>${benchEscape(dateText)}</dd></div>
        <div><dt>Total</dt><dd>${benchEscape(totalParts.join(" · ") || "not stated")}</dd></div>
        <div><dt>Order</dt><dd>${benchEscape(basketLookup ? BENCH_BASKET_ORDER_TEXT : BENCH_DESIGN_ORDER_TEXT)}</dd></div>
      </dl>
      ${note ? `<p class="bench-sheet-note">${benchEscape(note)}</p>` : ""}
    </header>
    <table class="bench-sheet-table">
      <thead><tr><th>#</th><th>Done</th><th>Material</th><th>Stock and strength</th><th>Amount</th><th>Running total</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

if (typeof module === "object" && module.exports) {
  module.exports = { addDecimalText, benchUnitKey, benchPercentText, benchBasisText, benchNeedsPreparedDilution, benchSheetLines, benchSheetHold, benchLeaveOutNote, benchSheetHtml, benchEscape, benchSmallPour, compareDecimalText, benchBasketLookup, benchRowBasket, benchBasketOrder, BENCH_SMALL_POUR_TEXT };
}
