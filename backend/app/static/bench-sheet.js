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
// The formula-file parser's codes (W_W, V_V, NEAT, UNKNOWN) read the same way.
const BENCH_BASIS_TEXT = {
  mass_fraction: "w/w", volume_fraction: "v/v", mass_per_volume: "w/v",
  W_W: "w/w", V_V: "v/v", NEAT: "neat", UNKNOWN: "basis not stated",
};
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

// Kenny's pipetting rule (2026-10-09): nothing goes in under 10 uL. A liquid
// row under 10 uL goes in through a mix that carries the same amount of stock:
// 1 part stock to (parts - 1) parts carrier, poured at parts x the amount,
// where parts is the smallest whole number that lifts the pour to 10 uL
// (2 is his 1:1). Fresh mixes are made in DPG; BHT stays in ethanol. The stock
// part is 10 uL, or 20 uL when 10 would leave under 10 uL of mix to spare.
// Rows needing more than 100 parts (under 0.1 uL) get no recipe.
const BENCH_MIX_MAX_PARTS = 100;

// Exact product of a plain decimal string and a whole number, without trailing zeros.
function multiplyDecimalText(value, factor) {
  const text = String(value ?? "").trim();
  if (!BENCH_DECIMAL.test(text) || !Number.isInteger(factor) || factor < 0) return null;
  const [whole, fraction = ""] = text.split(".");
  const digits = (BigInt(whole + fraction) * BigInt(factor)).toString().padStart(fraction.length + 1, "0");
  if (!fraction.length) return digits;
  const kept = digits.slice(-fraction.length).replace(/0+$/, "");
  return kept ? `${digits.slice(0, -fraction.length)}.${kept}` : digits.slice(0, -fraction.length);
}

function benchMixRecipe(row) {
  if (benchUnitKey(row?.amount_unit) !== "µL") return null;
  const amount = String(row.amount_decimal ?? "").trim();
  if (!BENCH_DECIMAL.test(amount)) return null;
  const [whole, fraction = ""] = amount.split(".");
  const scaled = BigInt(whole + fraction);
  const floor = BigInt(BENCH_MIN_PIPETTE_UL) * 10n ** BigInt(fraction.length);
  if (scaled <= 0n || scaled >= floor) return null;
  const parts = (floor + scaled - 1n) / scaled;
  if (parts > BigInt(BENCH_MIX_MAX_PARTS)) return null;
  const count = Number(parts);
  const stockUl = (floor - scaled) * parts >= floor ? BENCH_MIN_PIPETTE_UL : 2 * BENCH_MIN_PIPETTE_UL;
  const carrier = /\bBHT\b/i.test(`${row.material ?? ""} ${row.stock_label ?? ""}`) ? "ethanol" : "DPG";
  return {
    parts: count,
    stockUl: String(stockUl),
    carrierUl: String(stockUl * (count - 1)),
    carrier,
    stockAmount: addDecimalText("0", amount),
    pourUl: multiplyDecimalText(amount, count),
    addedCarrierUl: multiplyDecimalText(amount, count - 1),
  };
}

function benchMixText(recipe, unit) {
  return `Under 10 ${unit}: first mix ${recipe.stockUl} ${unit} of this stock with ${recipe.carrierUl} ${unit} ${recipe.carrier}, then add ${recipe.pourUl} ${unit} of the mix (it carries the ${recipe.stockAmount} ${unit}).`;
}

function benchMixShortText(recipe, unit) {
  return `under 10 ${unit}: mix ${recipe.stockUl} ${unit} stock + ${recipe.carrierUl} ${unit} ${recipe.carrier}, add ${recipe.pourUl} ${unit} of the mix`;
}

// "2 rows under 10 µL go in from a mix; the mixes add 24 µL DPG to the bottle."
function benchMixNote(recipes) {
  if (!recipes?.length) return "";
  const added = new Map();
  recipes.forEach((recipe) => {
    const sum = added.has(recipe.carrier) ? addDecimalText(added.get(recipe.carrier), recipe.addedCarrierUl) : recipe.addedCarrierUl;
    added.set(recipe.carrier, sum);
  });
  const parts = [...added].map(([carrier, ul]) => `${ul} µL ${carrier}`).join(" and ");
  const rowsText = recipes.length === 1 ? "1 row under 10 µL goes in from a mix; the mix adds" : `${recipes.length} rows under 10 µL go in from a mix; the mixes add`;
  return `${rowsText} ${parts} to the bottle.`;
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
      strength: percent === null && !String(row.stock_fraction_decimal ?? "").trim()
        ? "strength not stated"
        : `${percent ?? String(row.stock_fraction_decimal ?? "")} ${benchBasisText(row.fraction_basis)}${row.carrier ? ` in ${row.carrier}` : ""}`.trim(),
      amount,
      unit,
      unitKey: key,
      mass: key === "mg",
      pipettable: true,
      mix: null,
      runningTotal: null,
      mark: null,
    };
    if (benchNeedsPreparedDilution(row)) {
      line.mix = benchMixRecipe(row);
      if (line.mix === null) {
        line.pipettable = false;
        leftOut += 1;
        line.mark = benchDilutionMark(amount, unit);
        return line;
      }
      line.mark = benchMixText(line.mix, unit);
    }
    const poured = line.mix ? line.mix.pourUl : amount;
    running[key] = running[key] === undefined ? addDecimalText("0", poured) : addDecimalText(running[key], poured);
    line.runningTotal = running[key] === null ? "check by hand" : `${running[key]} ${key}`;
    return line;
  });
  return { lines, leftOut, mixes: lines.filter((line) => line.mix).map((line) => line.mix) };
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
function benchSheetHtml({ formulaName, variantLabel, dateText, totals, rows, critic, basketLookup = null, notes = [] }) {
  const ordered = benchBasketOrder(rows, basketLookup);
  const { lines, leftOut, mixes } = benchSheetLines(ordered.map((entry) => entry.row));
  const hold = benchSheetHold(rows, critic);
  const totalParts = [];
  if (totals?.liquid_total_ul !== undefined) totalParts.push(`${totals.liquid_total_ul} µL liquid stock`);
  if (Number(totals?.mass_total_mg) > 0) totalParts.push(`${totals.mass_total_mg} mg solids, weighed as separate mg lines`);
  const note = benchLeaveOutNote(leftOut);
  const mixNote = benchMixNote(mixes);
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
      <td><strong>${benchEscape(line.material)}</strong>${entry.basket !== null ? `<small class="bench-basket-tag">Basket ${benchEscape(entry.basket)}</small>` : entry.group === "unassigned" ? '<small class="bench-basket-tag">No basket</small>' : ""}${entry.row.pour_fix === "top-up" ? '<small class="bench-basket-tag">Top-up</small>' : ""}${line.mark ? `<small class="bench-dilution-mark">${benchEscape(line.mark)}</small>` : ""}</td>
      <td>${benchEscape(line.stockLabel)}<small>${benchEscape(line.strength)}</small></td>
      <td class="bench-amount">${line.mix ? `${benchEscape(line.mix.pourUl)} ${benchEscape(line.unit)} of the mix<small>${benchEscape(line.mix.stockAmount)} ${benchEscape(line.unit)} stock</small>` : `${benchEscape(line.amount)} ${benchEscape(line.unit)}`}</td>
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
      ${mixNote ? `<p class="bench-sheet-note">${benchEscape(mixNote)}</p>` : ""}
      ${note ? `<p class="bench-sheet-note">${benchEscape(note)}</p>` : ""}
      ${(notes || []).filter(Boolean).map((text) => `<p class="bench-sheet-note">${benchEscape(text)}</p>`).join("")}
    </header>
    <table class="bench-sheet-table">
      <thead><tr><th>#</th><th>Done</th><th>Material</th><th>Stock and strength</th><th>Amount</th><th>Running total</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

// ---- A bench sheet for any formula (a project file or a pasted table) ----

// The bottle a formula was written for, from "30mL", "30 mL" or "5ml" in its
// name or file path; null when neither says.
function benchBottleMl(...texts) {
  for (const text of texts) {
    for (const match of String(text ?? "").matchAll(/(\d+(?:\.\d+)?)\s*ml(?![a-z])/gi)) {
      if (Number(match[1]) > 0) return match[1].replace(/^0+(?=\d)/, "");
    }
  }
  return null;
}

// Exact value x target / source, rounded half up to `places` decimals, as a
// plain decimal without trailing zeros. null unless all three are plain
// decimals and source is not zero.
function scaleDecimalText(value, target, source, places) {
  const parse = (text) => {
    const trimmed = String(text ?? "").trim();
    if (!BENCH_DECIMAL.test(trimmed)) return null;
    const [whole, fraction = ""] = trimmed.split(".");
    return { digits: BigInt(whole + fraction), scale: fraction.length };
  };
  const amount = parse(value);
  const to = parse(target);
  const from = parse(source);
  if (!amount || !to || !from || from.digits === 0n) return null;
  const numerator = amount.digits * to.digits * 10n ** BigInt(from.scale + places);
  const denominator = 10n ** BigInt(amount.scale + to.scale) * from.digits;
  const digits = ((2n * numerator + denominator) / (2n * denominator)).toString().padStart(places + 1, "0");
  if (!places) return digits;
  const fraction = digits.slice(-places).replace(/0+$/, "");
  return fraction ? `${digits.slice(0, -places)}.${fraction}` : digits.slice(0, -places);
}

// Decimal places kept when scaling: 0.1 µL and 0.1 mg, 1 µL in mL, 1 mg in g.
const BENCH_SCALE_PLACES = { "µL": 1, mg: 1, mL: 3, g: 3 };

// Every row scaled by target / source mL. A row too small to show at the
// usual places keeps two more, so it still reaches the mix rule. Rows whose
// amount is not a plain number stay as written and are listed.
function benchScaleAmount(row, target, source) {
  const places = BENCH_SCALE_PLACES[benchUnitKey(row.amount_unit)];
  let amount = places === undefined ? null : scaleDecimalText(row.amount_decimal, target, source, places);
  if (amount === "0" && Number(row.amount_decimal) > 0) amount = scaleDecimalText(row.amount_decimal, target, source, places + 2);
  return amount;
}

function benchScaleRows(rows, sourceMl, targetMl) {
  const unscaled = [];
  const scaled = (rows || []).map((row) => {
    const amount = benchScaleAmount(row, targetMl, sourceMl);
    if (amount === null) {
      unscaled.push(String(row.material ?? ""));
      return { ...row };
    }
    return { ...row, amount_decimal: amount, unscaled_amount_decimal: row.amount_decimal };
  });
  return { rows: scaled, unscaled };
}

// Liquid µL (mL x 1000) and mg (g x 1000) totals, exact; "check by hand" when
// an amount is not a plain number.
function benchSeparateTotals(rows) {
  let liquid = "0";
  let mass = "0";
  let liquidOk = true;
  let massOk = true;
  (rows || []).forEach((row) => {
    const key = benchUnitKey(row.amount_unit);
    const amount = String(row.amount_decimal ?? "").trim();
    if (key === "µL" || key === "mL") {
      const ul = key === "mL" ? multiplyDecimalText(amount, 1000) : amount;
      const sum = ul === null ? null : addDecimalText(liquid, ul);
      if (sum === null) liquidOk = false; else liquid = sum;
    } else if (key === "mg" || key === "g") {
      const mg = key === "g" ? multiplyDecimalText(amount, 1000) : amount;
      const sum = mg === null ? null : addDecimalText(mass, mg);
      if (sum === null) massOk = false; else mass = sum;
    }
  });
  return { liquid_total_ul: liquidOk ? liquid : "check by hand", mass_total_mg: massOk ? mass : "check by hand" };
}

// A row from GET /workbench/formula-source (or the pasted-text parser) in the
// shape the sheet reads. The file gives strength and basis but no solvent.
function benchRowFromSource(row) {
  return {
    material: String(row.material ?? ""),
    amount_decimal: String(row.amount_decimal ?? ""),
    amount_unit: String(row.amount_unit ?? ""),
    stock_fraction_decimal: row.concentration_fraction_decimal ?? "",
    fraction_basis: row.concentration_basis || "UNKNOWN",
    carrier: null,
    stock_label: null,
    stock_id: row.stock_id ?? null,
    operation: row.operation,
  };
}

const BENCH_BASIS_GROUP = { mass_fraction: "w/w", W_W: "w/w", volume_fraction: "v/v", V_V: "v/v" };

function benchBasisFits(rowBasis, stockBasis, fraction) {
  if (String(fraction).trim() === "1") return true;
  const row = BENCH_BASIS_GROUP[rowBasis];
  return !row || !BENCH_BASIS_GROUP[stockBasis] || row === BENCH_BASIS_GROUP[stockBasis];
}

// Fill each row's stock from the owned inventory: same material name (or
// identity name) and the same strength, with a basis that does not conflict.
// One match (or several that read the same) names the bottle, solvent and
// basket; otherwise the row keeps the file's words and is listed in a note.
function benchMatchStocks(rows, inventory) {
  const owned = (inventory?.stocks || []).filter((stock) => String(stock.status ?? "").toLowerCase() === "owned");
  const unmatched = [];
  const ambiguous = [];
  const held = [];
  const matched = (rows || []).map((row) => {
    const names = new Set([row.material, row.identity_name].map(benchNameKey).filter(Boolean));
    const fraction = String(row.stock_fraction_decimal ?? "").trim();
    const sameName = owned.filter((stock) => names.has(benchNameKey(stock.material)) || names.has(benchNameKey(stock.identity_name)));
    // A hold on any owned stock of this material is listed, even when the
    // row's strength is missing or matches none of them.
    const heldStocks = sameName.filter((stock) => stock.design_ready === false);
    heldStocks.forEach((stock) => {
      held.push(`${stock.stock_label || stock.material} (${String(stock.design_hold_reason || "on hold").replaceAll("_", " ").toLowerCase()})`);
    });
    const executionReady = heldStocks.length ? false : row.execution_ready;
    const candidates = BENCH_DECIMAL.test(fraction) ? sameName.filter((stock) => (
      BENCH_DECIMAL.test(String(stock.fraction_decimal ?? ""))
      && compareDecimalText(String(stock.fraction_decimal), fraction) === 0
      && benchBasisFits(row.fraction_basis, stock.fraction_basis, fraction)
    )) : [];
    const readings = new Set(candidates.map((stock) => [stock.stock_label, stock.fraction_basis, stock.carrier ?? ""].join("|")));
    if (!candidates.length) {
      unmatched.push(row.material);
      return { ...row, execution_ready: executionReady };
    }
    if (readings.size > 1) {
      ambiguous.push(row.material);
      return { ...row, execution_ready: executionReady };
    }
    const stock = candidates[0];
    return {
      ...row,
      stock_id: stock.stock_id,
      identity_name: stock.identity_name,
      stock_label: stock.stock_label || stock.material,
      fraction_basis: stock.fraction_basis || row.fraction_basis,
      carrier: stock.carrier || null,
      execution_ready: executionReady,
    };
  });
  return { rows: matched, unmatched, ambiguous, held };
}

function benchNameList(names) {
  const unique = [...new Set(names.filter(Boolean))];
  return unique.length > 6 ? `${unique.slice(0, 6).join(", ")} and ${unique.length - 6} more` : unique.join(", ");
}

// Plain-language notes for the sheet header.
function benchSourceNotes({ scaledFrom = null, scaledTo = null, unscaled = [], unmatched = [], ambiguous = [], held = [], warnings = [] }) {
  const notes = [];
  if (scaledFrom && scaledTo) notes.push(`Scaled from the ${scaledFrom} mL formula to ${scaledTo} mL; µL and mg rounded to one decimal, mL and g to three, and a row that would round to zero keeps two more places.`);
  if (unscaled.length) notes.push(`Not scaled, the amount is not a plain number: ${benchNameList(unscaled)}.`);
  if (held.length) notes.push(`On hold in Stock: ${benchNameList(held)}.`);
  if (unmatched.length) notes.push(`No owned stock with this name and strength, check the bottle: ${benchNameList(unmatched)}.`);
  if (ambiguous.length) notes.push(`More than one owned stock fits, pick the bottle by hand: ${benchNameList(ambiguous)}.`);
  (warnings || []).slice(0, 5).forEach((warning) => notes.push(`From the file: ${String(warning).slice(0, 200)}`));
  return notes;
}

// ---- Pour fix: one row went in over or under, what to do with the rest ----

// Exact left - right for plain decimals; null unless left >= right.
function subtractDecimalText(left, right) {
  const a = String(left ?? "").trim();
  const b = String(right ?? "").trim();
  if (!BENCH_DECIMAL.test(a) || !BENCH_DECIMAL.test(b) || compareDecimalText(a, b) < 0) return null;
  const [aWhole, aFraction = ""] = a.split(".");
  const [bWhole, bFraction = ""] = b.split(".");
  const scale = Math.max(aFraction.length, bFraction.length);
  const digits = (BigInt(aWhole + aFraction.padEnd(scale, "0")) - BigInt(bWhole + bFraction.padEnd(scale, "0"))).toString().padStart(scale + 1, "0");
  if (!scale) return digits;
  const fraction = digits.slice(-scale).replace(/0+$/, "");
  return fraction ? `${digits.slice(0, -scale)}.${fraction}` : digits.slice(0, -scale);
}

// What the sheet tells Kenny to pour for a row, in the sheet's unit: the mix
// pour for a row under 10 µL, else the amount. null when the sheet does not
// pour the row as written.
function benchPlannedPour(row) {
  const line = benchSheetLines([row]).lines[0];
  if (!line || !line.pipettable) return null;
  const amount = line.mix ? line.mix.pourUl : line.amount;
  if (!BENCH_DECIMAL.test(String(amount ?? "")) || compareDecimalText(amount, "0") <= 0) return null;
  return { amount, unit: line.unitKey, mix: Boolean(line.mix) };
}

// `rows` are in sheet order; the rows above `overIndex` are already in.
// `actualText` is what really went in for that row, in the unit the sheet
// shows for it (µL of the mix for a mix row).
// - under: the amount still missing.
// - over: every ratio is kept by scaling the batch by actual / planned: the
//   rows already in get a top-up of (factor - 1) x their amount, the rows
//   still to come are poured at factor x, the over row itself is done.
function benchPourFix(rows, overIndex, actualText) {
  const row = (rows || [])[overIndex];
  const planned = row ? benchPlannedPour(row) : null;
  if (!planned) return { kind: "invalid", reason: "Pick a row the sheet pours as written." };
  const actual = String(actualText ?? "").trim();
  if (!BENCH_DECIMAL.test(actual) || compareDecimalText(actual, "0") <= 0) {
    return { kind: "invalid", reason: "Type what went in as a plain number, more than 0." };
  }
  const material = String(row.material ?? "");
  const base = { material, planned: planned.amount, actual, unit: planned.unit, mix: planned.mix };
  const order = compareDecimalText(actual, planned.amount);
  if (order === 0) return { ...base, kind: "same" };
  if (order < 0) {
    const missing = subtractDecimalText(planned.amount, actual);
    return { ...base, kind: "under", missing, percent: scaleDecimalText("100", missing, planned.amount, 1) };
  }
  const extra = subtractDecimalText(actual, planned.amount);
  const fixed = [];
  const skipped = [];
  const unscaled = [];
  (rows || []).forEach((item, index) => {
    if (index === overIndex) return;
    const alreadyIn = index < overIndex && benchPlannedPour(item) !== null;
    const amount = alreadyIn ? benchScaleAmount(item, extra, planned.amount) : benchScaleAmount(item, actual, planned.amount);
    if (amount === null) {
      unscaled.push(String(item.material ?? ""));
      fixed.push({ ...item });
    } else if (compareDecimalText(amount, "0") === 0) {
      skipped.push(String(item.material ?? ""));
    } else {
      fixed.push({ ...item, amount_decimal: amount, ...(alreadyIn ? { pour_fix: "top-up" } : {}) });
    }
  });
  return {
    ...base,
    kind: "over",
    factor: scaleDecimalText("1", actual, planned.amount, 3),
    percent: scaleDecimalText("100", extra, planned.amount, 1),
    rows: fixed,
    topUps: fixed.filter((item) => item.pour_fix === "top-up").length,
    skipped,
    unscaled,
  };
}

// Plain-language result. `sizeMl` is the batch the sheet makes, when known.
function benchPourFixText(fix, sizeMl = null) {
  const unit = fix.unit;
  const what = fix.mix ? `${unit} of the mix` : unit;
  if (fix.kind === "invalid") return { message: fix.reason, notes: [] };
  if (fix.kind === "same") return { message: `${fix.material} went in as planned; nothing to fix.`, notes: [] };
  if (fix.kind === "under") {
    const small = unit === "µL" && Number(fix.missing) < BENCH_MIN_PIPETTE_UL;
    const how = !small ? `Add the missing ${fix.missing} ${what}.`
      : fix.mix ? `Add ${fix.missing} ${what} more, or leave it: under 10 µL is hard to pipette.`
        : (() => {
          const recipe = benchMixRecipe({ amount_unit: "µL", amount_decimal: fix.missing, material: fix.material });
          return recipe ? benchMixText(recipe, "µL") : `${fix.missing} µL is too small to add; leave it.`;
        })();
    return { message: `${fix.material} went in ${fix.missing} ${what} short (${fix.percent}% under). ${how}`, notes: [] };
  }
  const bigger = sizeMl ? scaleDecimalText(sizeMl, fix.actual, fix.planned, 2) : null;
  const notes = [
    `Pour fix: ${fix.material} went in at ${fix.actual} ${what} instead of ${fix.planned} (${fix.percent}% over). To keep every ratio, this sheet lists only what still goes in: top-ups for the ${fix.topUps} ${fix.topUps === 1 ? "row" : "rows"} already in, then the rest at ${fix.factor} times.`,
    bigger ? `The batch becomes ${bigger} mL instead of ${sizeMl} mL.` : `The batch grows by ${fix.percent}%.`,
    `Or leave it: ${fix.material} stays ${fix.percent}% over and the rest pours as first printed; check its IFRA limit if it is restricted.`,
  ];
  if (fix.skipped.length) notes.push(`Top-ups too small to matter are left out: ${benchNameList(fix.skipped)}.`);
  if (fix.unscaled.length) notes.push(`Not rescaled, the amount is not a plain number: ${benchNameList(fix.unscaled)}.`);
  return { message: `Fixed: the sheet now shows what still goes in after ${fix.material}.`, notes, sizeMl: bigger };
}

if (typeof module === "object" && module.exports) {
  module.exports = { addDecimalText, benchUnitKey, benchPercentText, benchBasisText, benchNeedsPreparedDilution, benchSheetLines, benchSheetHold, benchLeaveOutNote, benchSheetHtml, benchEscape, compareDecimalText, benchBasketLookup, benchRowBasket, benchBasketOrder, multiplyDecimalText, benchMixRecipe, benchMixText, benchMixShortText, benchMixNote, benchBottleMl, scaleDecimalText, benchScaleRows, benchSeparateTotals, benchRowFromSource, benchMatchStocks, benchSourceNotes, subtractDecimalText, benchPlannedPour, benchPourFix, benchPourFixText };
}
