// Formula editor logic for the "Edit a formula" page. It touches no DOM, so the
// page loads it after bench-sheet.js and before the Lab page files in lab/, and
// node runs it in the tests.
//
// A row's amount is an exact fraction: a liquid in µL of its stock, a solid in
// mg. The unit on screen (µL, grams, or the share of the liquid in % or parts
// per 1000) is only a view of those amounts, so switching it changes no row.

const editorBench = (typeof module === "object" && module.exports)
  ? require("./bench-sheet.js")
  : {
    benchFraction, benchFractionOf, benchTimes, benchOver, benchPlus, benchMinus, benchCompare,
    benchFractionText, benchNameKey, benchStockDensity, benchUnitKey, benchPercentText,
  };

const EDITOR_UNIT_LABELS = { uL: "µL", g: "g", pct: "%", parts: "‰" };
const EDITOR_NOTES = ["top", "heart", "base"];
const EDITOR_HISTORY_MAX = 200;
const EDITOR_ZERO = { n: 0n, d: 1n };
const EDITOR_SHARE_PER = { pct: 100n, parts: 1000n };
let editorKeySeq = 0;

const editorWhole = (value) => ({ n: BigInt(value), d: 1n });
const editorNameKey = (value) => editorBench.benchNameKey(value);

function editorKey() {
  editorKeySeq += 1;
  return `row-${editorKeySeq}`;
}

function editorRow(fields = {}) {
  return {
    key: fields.key || editorKey(),
    material: String(fields.material ?? "").trim(),
    stockId: fields.stockId ?? null,
    fraction: String(fields.fraction ?? "").trim(),
    basis: String(fields.basis ?? "").trim(),
    carrier: fields.carrier ? String(fields.carrier) : null,
    solid: Boolean(fields.solid),
    // µL of the stock for a liquid, mg for a solid; null while the row is empty.
    amount: fields.amount ?? null,
    // Grams read from a card or a paste, waiting for the stock's density.
    grams: fields.grams ?? null,
    note: EDITOR_NOTES.includes(fields.note) ? fields.note : "",
  };
}

// "1200", "1,200", "1 200", ".5" or "0.5" as an exact fraction; null otherwise.
function editorNumber(text) {
  const raw = String(text ?? "").trim().replace(/[   ]/g, "");
  const plain = /^\d{1,3}(,\d{3})+(\.\d+)?$/.test(raw) ? raw.replaceAll(",", "") : raw;
  return editorBench.benchFractionOf(/^\.\d+$/.test(plain) ? `0${plain}` : plain);
}

// The fewest decimals (from `places`, up to three more) that do not round a
// non-zero value to 0.
function editorFigure(value, places) {
  if (!value || value.n <= 0n) return "0";
  for (let extra = 0; extra <= 3; extra += 1) {
    const text = editorBench.benchFractionText(value, places + extra);
    if (text !== "0") return text;
  }
  return editorBench.benchFractionText(value, places + 3);
}

function editorNoteOf(...texts) {
  for (const text of texts) {
    const words = String(text ?? "").toLowerCase();
    if (/\btop\b/.test(words)) return "top";
    if (/\b(heart|middle|mid)\b/.test(words)) return "heart";
    if (/\bbase\b/.test(words)) return "base";
  }
  return "";
}

// An amount from a card, the composer or a paste: µL and mL are liquid µL, mg
// is a solid, and g is a weighed amount that waits for the stock's density.
function editorSourceAmount(amountText, unit) {
  const value = editorNumber(amountText);
  if (!value || value.n <= 0n) return null;
  const key = editorBench.benchUnitKey(unit);
  if (key === "µL") return { amount: value, solid: false };
  if (key === "mL") return { amount: editorBench.benchTimes(value, editorWhole(1000)), solid: false };
  if (key === "mg") return { amount: value, solid: true };
  if (key === "g") return { grams: value, solid: false };
  return null;
}

// Rows from a parsed card, the composer's draft or the bench sheet.
function editorRowsFromSource(rows) {
  const out = [];
  const skipped = [];
  (rows || []).forEach((row) => {
    const material = String(row.material || row.identity_name || "").trim();
    const amount = editorSourceAmount(row.amount_decimal, row.amount_unit);
    if (!material || !amount) {
      skipped.push(material || "a row with no name");
      return;
    }
    out.push(editorRow({
      material,
      stockId: row.stock_id || null,
      fraction: row.stock_fraction_decimal ?? row.concentration_fraction_decimal ?? "",
      basis: row.fraction_basis ?? row.concentration_basis ?? "",
      carrier: row.carrier || null,
      note: editorNoteOf(row.note, row.role, row.slot),
      ...amount,
    }));
  });
  return { rows: out, skipped };
}

const EDITOR_UNIT_WORD = /^(?:[uµμ]l|ml|mg|g)$/i;
const EDITOR_AMOUNT_CELL = /^(\.?\d[\d,.   ]*)\s*([uµμ]l|ml|mg|g)?$/i;
const EDITOR_STRENGTH_CELL = /^(\d+(?:\.\d+)?)\s*%|^neat$/i;

function editorUnitOf(word) {
  const text = String(word ?? "").toLowerCase();
  if (!text) return null;
  if (/^[uµμ]l$/.test(text)) return "uL";
  return { ml: "mL", mg: "mg", g: "g" }[text] || null;
}

function editorStrengthOf(cell) {
  const match = String(cell ?? "").trim().match(EDITOR_STRENGTH_CELL);
  if (!match) return null;
  if (!match[1]) return "1";
  const fraction = editorBench.benchOver(editorNumber(match[1]), editorWhole(100));
  return editorBench.benchFractionText(fraction, 8);
}

// Cells of one copied spreadsheet row: the name is the first cell with a
// letter, the amount the last cell that is a number (with its unit, or a unit
// in the next cell), and a "10%" or "neat" cell is the stock's strength.
function editorCellsRow(cells) {
  let amountIndex = -1;
  for (let index = cells.length - 1; index >= 0; index -= 1) {
    if (EDITOR_AMOUNT_CELL.test(cells[index]) && editorNumber(cells[index].match(EDITOR_AMOUNT_CELL)[1])) {
      amountIndex = index;
      break;
    }
  }
  const material = cells.find((cell, index) => index !== amountIndex && /\p{L}/u.test(cell)
    && !EDITOR_UNIT_WORD.test(cell) && !EDITOR_STRENGTH_CELL.test(cell));
  if (amountIndex < 0 || !material) return null;
  const [, number, inline] = cells[amountIndex].match(EDITOR_AMOUNT_CELL);
  const next = cells[amountIndex + 1];
  const strength = cells.map(editorStrengthOf).find(Boolean) || "";
  return {
    material,
    amountText: number.trim(),
    unit: editorUnitOf(inline) || (EDITOR_UNIT_WORD.test(next ?? "") ? editorUnitOf(next) : null),
    fraction: strength,
  };
}

// Rows copied from Excel (a tab between cells, or ";"), or plain lines such as
// "Hedione 1200 µL". Returns { rows: [{ material, amountText, unit, fraction }],
// skipped } with unit null for a bare number, or null for a Markdown table,
// which the server's card parser reads.
function editorParsePlain(text) {
  const lines = String(text ?? "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length || lines.some((line) => line.includes("|"))) return null;
  const rows = [];
  const skipped = [];
  lines.forEach((line, index) => {
    const cells = line.includes("\t") ? line.split("\t") : (line.includes(";") ? line.split(";") : null);
    let row = null;
    if (cells) {
      row = editorCellsRow(cells.map((cell) => cell.trim()).filter(Boolean));
    } else {
      const match = line.match(/^(.*\p{L}.*?)\s+(\.?\d[\d,.]*)\s*([uµμ]l|ml|mg|g)?$/iu);
      if (match && editorNumber(match[2])) row = { material: match[1].trim(), amountText: match[2], unit: editorUnitOf(match[3]), fraction: "" };
    }
    if (row) rows.push(row);
    // A first line without a number is a header row: dropped without a word.
    else if (index > 0 || /\d/.test(line)) skipped.push(line);
  });
  return { rows, skipped };
}

// Pasted rows as editor rows. A row that names its unit keeps it; a bare number
// is read in the unit on screen. In the % or parts view a bare number is a share
// of a 1,000 µL formula, which works only when the editor has no liquid yet.
function editorRowsFromPlain(parsed, viewUnit, existingRows = []) {
  const shareView = Boolean(EDITOR_SHARE_PER[viewUnit]);
  const hasLiquid = editorTotals(existingRows).liquidUl.n > 0n;
  const bare = (parsed.rows || []).some((row) => !row.unit);
  if (shareView && bare && hasLiquid) {
    throw new Error("Numbers without a unit are read in the unit on screen. Switch to µL or g to paste them into a formula that already has liquid, or say µL, mg or g after each number.");
  }
  const rows = [];
  const skipped = [...(parsed.skipped || [])];
  (parsed.rows || []).forEach((row) => {
    let unit = row.unit;
    let amountText = row.amountText;
    if (!unit) {
      if (shareView) {
        // Shares of 1,000 µL: 1% is 10 µL, one part per 1000 is 1 µL.
        const value = editorNumber(amountText);
        amountText = value ? editorBench.benchFractionText(editorBench.benchTimes(value, editorWhole(viewUnit === "pct" ? 10 : 1)), 6) : "";
        unit = "uL";
      } else {
        unit = viewUnit === "g" ? "g" : "uL";
      }
    }
    const amount = editorSourceAmount(amountText, unit);
    if (!amount) {
      skipped.push(row.material);
      return;
    }
    rows.push(editorRow({ material: row.material, fraction: row.fraction || "", ...amount }));
  });
  return { rows, skipped };
}

// "Rose Oxide 1% DPG", "Vanillin 10% in DPG", "Iso E Super (neat)": the name
// without its strength, and the strength as a fraction ("0.01", "1" for neat).
function editorNameStrength(text) {
  const name = String(text ?? "").trim();
  const neat = name.match(/^(.*?)[\s(]+(?:neat|undiluted)\s*\)?$/i);
  if (neat && neat[1].trim()) return { name: neat[1].trim(), fraction: "1" };
  const match = name.match(/^(.*?)[\s(]+(\d+(?:\.\d+)?)\s*%(?:\s*(?:w\/w|v\/v|w\/v))?(?:\s+(?:in\s+)?[\p{L}][\p{L}' -]*)?\s*\)?$/iu);
  if (match && match[1].trim()) return { name: match[1].trim(), fraction: editorStrengthOf(`${match[2]}%`) };
  return { name, fraction: "" };
}

function editorStockIsSolid(stock) {
  const form = String(stock?.physical_form ?? "").toLowerCase();
  return form === "crystals" || form.startsWith("solid");
}

function editorOwned(stocks) {
  return (stocks || []).filter((stock) => String(stock.status ?? "").toLowerCase() === "owned");
}

// The owned stocks a row could pour: the same name (as typed, or without a
// trailing strength), at the row's strength when it states one.
function editorStockCandidates(row, stocks) {
  const parsed = editorNameStrength(row.material);
  const keys = new Set([row.material, parsed.name].map(editorNameKey).filter(Boolean));
  const fraction = editorNumber(row.fraction || parsed.fraction);
  const sameName = editorOwned(stocks).filter((stock) => keys.has(editorNameKey(stock.material)) || keys.has(editorNameKey(stock.identity_name)));
  if (!fraction) return sameName;
  return sameName.filter((stock) => {
    const owned = editorNumber(stock.fraction_decimal);
    return owned && editorBench.benchCompare(owned, fraction) === 0;
  });
}

function editorBindRow(row, stock) {
  // An empty row takes the stock's form; a row that already has an amount keeps it.
  const solid = row.amount || row.grams ? row.solid : editorStockIsSolid(stock);
  return {
    ...row,
    stockId: stock.stock_id,
    material: String(stock.identity_name || stock.material || row.material),
    fraction: String(stock.fraction_decimal ?? ""),
    basis: String(stock.fraction_basis ?? ""),
    carrier: stock.carrier || null,
    solid,
  };
}

function editorStockOf(row, stocks) {
  return row.stockId ? editorOwned(stocks).find((stock) => stock.stock_id === row.stockId) || null : null;
}

// Binds every row that is not bound to an owned stock and has exactly one
// candidate. Returns the rows with the names left unmatched (no owned stock at
// that name and strength) and ambiguous (several stocks to choose from).
function editorBindRows(rows, stocks) {
  const unmatched = [];
  const ambiguous = [];
  const out = (rows || []).map((row) => {
    if (!row.material || editorStockOf(row, stocks)) return row;
    const candidates = editorStockCandidates(row, stocks);
    if (candidates.length === 1) return editorBindRow(row, candidates[0]);
    (candidates.length ? ambiguous : unmatched).push(row.material);
    return row.stockId ? { ...row, stockId: null } : row;
  });
  return { rows: out, unmatched, ambiguous };
}

function editorTotals(rows) {
  let liquidUl = EDITOR_ZERO;
  let solidMg = EDITOR_ZERO;
  (rows || []).forEach((row) => {
    if (!row.amount) return;
    if (row.solid) solidMg = editorBench.benchPlus(solidMg, row.amount);
    else liquidUl = editorBench.benchPlus(liquidUl, row.amount);
  });
  return { liquidUl, solidMg };
}

// The row's stock density in g/mL as an exact fraction, or null. `densities`
// maps a material name (any case) to its density at 25 °C as decimal text.
function editorDensity(row, densities) {
  const lookup = {};
  Object.entries(densities || {}).forEach(([name, value]) => { if (value) lookup[editorNameKey(name)] = String(value); });
  const result = editorBench.benchStockDensity({
    material: row.material,
    stock_fraction_decimal: row.fraction,
    fraction_basis: row.basis,
    carrier: row.carrier,
  }, lookup[editorNameKey(row.material)] ?? null);
  return result ? result.density : null;
}

// What a row's amount cell shows in `unit`, and the unit beside it. Solids
// stay in mg (g in the grams view) and are not part of a share of the liquid.
// `why` says when a liquid row can't be shown in grams.
function editorShown(row, totals, unit, densities) {
  if (row.solid) {
    if (unit === "g") return { text: row.amount ? editorFigure(editorBench.benchOver(row.amount, editorWhole(1000)), 3) : "", unit: "g" };
    return { text: row.amount ? editorFigure(row.amount, 1) : "", unit: "mg" };
  }
  if (unit === "g") {
    const density = editorDensity(row, densities);
    if (!density) return { text: "", unit: "g", why: "density not known" };
    if (!row.amount) return { text: "", unit: "g" };
    return { text: editorFigure(editorBench.benchOver(editorBench.benchTimes(row.amount, density), editorWhole(1000)), 3), unit: "g" };
  }
  const per = EDITOR_SHARE_PER[unit];
  if (!per) return { text: row.amount ? editorFigure(row.amount, 1) : "", unit: "µL" };
  if (!row.amount) return { text: "", unit: EDITOR_UNIT_LABELS[unit] };
  const share = editorBench.benchTimes(editorBench.benchOver(row.amount, totals.liquidUl), editorWhole(per));
  return { text: editorFigure(share, unit === "pct" ? 2 : 1), unit: EDITOR_UNIT_LABELS[unit] };
}

function editorReplace(rows, index, row) {
  return rows.map((item, at) => (at === index ? row : item));
}

function editorInsert(rows, index, row = editorRow()) {
  return [...rows.slice(0, index), row, ...rows.slice(index)];
}

function editorRemove(rows, index) {
  return rows.filter((_, at) => at !== index);
}

// The rows with row `index` set from what was typed in `unit`. Throws an Error
// whose message says what to type instead.
function editorSetAmount(rows, index, text, unit, densities) {
  const row = rows[index];
  const raw = String(text ?? "").trim();
  if (!raw) return editorReplace(rows, index, { ...row, amount: null, grams: null });
  const value = editorNumber(raw);
  if (!value) throw new Error(`"${raw}" is not an amount. Type a number such as 120 or 0.5.`);
  if (value.n <= 0n) throw new Error("Type an amount above 0, or remove the row.");
  let amount;
  if (row.solid) {
    amount = unit === "g" ? editorBench.benchTimes(value, editorWhole(1000)) : value;
  } else if (unit === "g") {
    const density = editorDensity(row, densities);
    if (!density) throw new Error(`${row.material || "This row"} has no known density, so it can't be typed in grams. Switch to µL for this row.`);
    amount = editorBench.benchOver(editorBench.benchTimes(value, editorWhole(1000)), density);
  } else if (EDITOR_SHARE_PER[unit]) {
    const per = editorWhole(EDITOR_SHARE_PER[unit]);
    if (editorBench.benchCompare(value, per) >= 0) {
      throw new Error(unit === "pct" ? "A row's share must be under 100%." : "A row's share must be under 1000 parts.");
    }
    // The other rows keep their amounts; this row takes the share typed.
    const others = editorBench.benchMinus(editorTotals(rows).liquidUl, row.amount || EDITOR_ZERO);
    if (others.n <= 0n) throw new Error("This is the only liquid, so it is all of it. Type its amount in µL or g instead.");
    amount = editorBench.benchOver(editorBench.benchTimes(value, others), editorBench.benchMinus(per, value));
  } else {
    amount = value;
  }
  return editorReplace(rows, index, { ...row, amount, grams: null });
}

// Rows read in grams take their µL once the stock's density is known. Returns
// the rows and the names still waiting for a density.
function editorResolveGrams(rows, densities, stocks = []) {
  const waiting = [];
  const out = rows.map((row) => {
    if (!row.grams) return row;
    const stock = editorStockOf(row, stocks);
    if (row.solid || editorStockIsSolid(stock)) {
      return { ...row, solid: true, amount: editorBench.benchTimes(row.grams, editorWhole(1000)), grams: null };
    }
    const density = editorDensity(row, densities);
    if (!density) {
      waiting.push(row.material);
      return row;
    }
    return { ...row, amount: editorBench.benchOver(editorBench.benchTimes(row.grams, editorWhole(1000)), density), grams: null };
  });
  return { rows: out, waiting };
}

// Every row scaled so the liquid comes to `text` µL; solids scale with it.
function editorScaleTo(rows, text) {
  const target = editorNumber(text);
  if (!target || target.n <= 0n) throw new Error("Type the liquid total in µL, such as 6000.");
  const total = editorTotals(rows).liquidUl;
  if (total.n <= 0n) throw new Error("There is no liquid to scale yet.");
  const factor = editorBench.benchOver(target, total);
  return rows.map((row) => (row.amount ? { ...row, amount: editorBench.benchTimes(row.amount, factor) } : row));
}

// By note: top, heart, base, then rows with no note; largest first within each.
// By amount: liquids by µL, then solids by mg, largest first; empty rows last.
function editorSorted(rows, by) {
  const noteRank = (row) => {
    const rank = EDITOR_NOTES.indexOf(row.note);
    return rank < 0 ? EDITOR_NOTES.length : rank;
  };
  const kindRank = (row) => (!row.amount ? 2 : (row.solid ? 1 : 0));
  const larger = (a, b) => (a.amount && b.amount ? editorBench.benchCompare(b.amount, a.amount) : 0);
  return rows.map((row, index) => ({ row, index })).sort((a, b) => (
    (by === "note" ? noteRank(a.row) - noteRank(b.row) : 0)
    || kindRank(a.row) - kindRank(b.row)
    || larger(a.row, b.row)
    || a.index - b.index
  )).map(({ row }) => row);
}

function editorHistory(rows) {
  return { past: [], present: rows, future: [] };
}

function editorCommit(history, rows) {
  if (rows === history.present) return history;
  return { past: [...history.past, history.present].slice(-EDITOR_HISTORY_MAX), present: rows, future: [] };
}

function editorUndo(history) {
  if (!history.past.length) return history;
  return { past: history.past.slice(0, -1), present: history.past[history.past.length - 1], future: [history.present, ...history.future] };
}

function editorRedo(history) {
  if (!history.future.length) return history;
  return { past: [...history.past, history.present], present: history.future[0], future: history.future.slice(1) };
}

const EDITOR_BASIS_WORDS = { mass_fraction: "w/w", W_W: "w/w", volume_fraction: "v/v", V_V: "v/v", mass_per_volume: "w/v" };

// A stock's strength as a card's Dilution cell: "neat", "10% w/w in DPG", "1%".
function editorStrengthText(row) {
  const fraction = String(row.fraction ?? "").trim();
  if (!fraction) return "";
  if (fraction === "1" || /^neat$/i.test(row.basis)) return "neat";
  const percent = editorBench.benchPercentText(fraction);
  if (!percent) return "";
  const basis = EDITOR_BASIS_WORDS[row.basis];
  const carrier = row.carrier ? ` in ${/^(dpg|dep|ipm|tec)$/i.test(row.carrier) ? row.carrier.toUpperCase() : row.carrier}` : "";
  return `${percent}${basis ? ` ${basis}` : ""}${carrier}`;
}

const editorCell = (text) => String(text ?? "").replace(/\|/g, "/").replace(/\s+/g, " ").trim();

// The formula as a card table the bench sheet's paste box reads. Rows without
// a name or an amount are left out and named.
function editorBenchTable(name, rows) {
  const lines = ["| Material | Dilution | Amount (µL) |", "|---|---|---:|"];
  const leftOut = [];
  (rows || []).forEach((row) => {
    if (!row.material || !row.amount) {
      if (row.material) leftOut.push(row.material);
      return;
    }
    const amount = editorBench.benchFractionText(row.amount, 3);
    lines.push(`| ${editorCell(row.material)} | ${editorCell(editorStrengthText(row))} | ${row.solid ? `${amount} mg` : amount} |`);
  });
  const title = editorCell(name) || "Edited formula";
  return { text: `# ${title}\n\n${lines.join("\n")}\n`, leftOut };
}

// The formula as tab-separated text for a spreadsheet, amounts as shown.
function editorTsv(rows, unit, densities) {
  const totals = editorTotals(rows);
  const lines = [["Material", "Strength", "Amount", "Unit", "Note"].join("\t")];
  (rows || []).forEach((row) => {
    if (!row.material) return;
    const shown = editorShown(row, totals, unit, densities);
    lines.push([editorCell(row.material), editorStrengthText(row), shown.text, shown.text ? shown.unit : "", row.note].join("\t"));
  });
  return `${lines.join("\n")}\n`;
}

// ---- The side panel's inputs ----

const EDITOR_ETHANOL_NAMES = new Set(["ethanol", "perfumer's alcohol", "perfumers alcohol", "alcohol"]);
const EDITOR_CHECK_BASIS = { mass_fraction: "w/w", w_w: "w/w", volume_fraction: "v/v", v_v: "v/v", neat: "neat", mass_per_volume: "w/v", w_v: "w/v" };
const editorDecimal = (value) => editorBench.benchFractionText(value, 6);

function editorIsEthanol(row) {
  return EDITOR_ETHANOL_NAMES.has(String(row.material ?? "").trim().toLowerCase());
}

// Rows for POST /v2/workbench/formula-checks: each named row with an amount, a
// liquid in µL of its stock or a solid in mg, with the stock's strength.
function editorCheckRows(rows) {
  return (rows || []).filter((row) => row.material && row.amount).map((row) => {
    const fraction = editorNumber(row.fraction);
    const strength = fraction && fraction.n > 0n && editorBench.benchCompare(fraction, editorWhole(1)) <= 0 ? editorDecimal(fraction) : "1";
    const basis = EDITOR_CHECK_BASIS[String(row.basis ?? "").trim().toLowerCase()] || null;
    return {
      material: row.material,
      ...(row.solid ? { amount_mg: editorDecimal(row.amount) } : { amount_ul: editorDecimal(row.amount) }),
      stock_fraction: strength,
      fraction_basis: basis,
      carrier: row.carrier || null,
    };
  });
}

// Rows for POST /v2/workbench/formula-holds ("What's missing", hold-list.js): the
// stock each row is bound to, its strength as written and its amount (mg for a
// solid). Ethanol is the bottle's top-up, not a stock, so it is left out.
function editorHoldRows(rows) {
  return (rows || []).filter((row) => row.material && row.amount && !editorIsEthanol(row)).map((row) => {
    const fraction = editorNumber(row.fraction);
    const strength = fraction && fraction.n > 0n && editorBench.benchCompare(fraction, editorWhole(1)) <= 0 ? editorDecimal(fraction) : "1";
    return {
      material: row.material,
      stock_id: row.stockId || null,
      amount: editorDecimal(row.amount),
      unit: row.solid ? "mg" : "uL",
      fraction: strength,
      basis: String(row.basis ?? "").trim(),
      carrier: row.carrier || "",
    };
  });
}

// Rows for benchCost (stock-prices.js). A liquid whose stock is priced per g
// goes in grams when its density is known, so it is costed rather than skipped.
function editorCostRows(rows, densities, prices) {
  return (rows || []).filter((row) => row.material && row.amount).map((row) => {
    const base = { material: row.material, identity_name: row.material, stock_id: row.stockId || null };
    if (row.solid) return { ...base, amount_decimal: editorDecimal(row.amount), amount_unit: "mg" };
    const entry = row.stockId ? (prices || {})[row.stockId] : null;
    const density = entry && entry.per_unit === "g" ? editorDensity(row, densities) : null;
    if (density) {
      const grams = editorBench.benchOver(editorBench.benchTimes(row.amount, density), editorWhole(1000));
      return { ...base, amount_decimal: editorDecimal(grams), amount_unit: "g" };
    }
    return { ...base, amount_decimal: editorDecimal(row.amount), amount_unit: "µL" };
  });
}

// Rows for the smell-over-time chart (scent-chart.js): liquids only, ethanol left out.
function editorChartRows(rows) {
  return (rows || []).filter((row) => row.material && row.amount && !row.solid && !editorIsEthanol(row)).map((row) => ({
    identity_name: row.material,
    amount_decimal: editorDecimal(row.amount),
    amount_unit: "uL",
    stock_fraction_decimal: row.fraction || "1",
  }));
}

// What each row's bottles in the Lab hold now and after `bottles` bottles of
// this formula. A Lab stock matches a row by material name and strength;
// several bottles of one stock are added together. `remaining` maps a Lab
// stock id to its grams left (null while not known).
function editorStockLeft(rows, labStocks, materials, remaining, densities, bottles) {
  const nameOf = new Map((materials || []).map((material) => [material.id, material.canonical_name]));
  const count = editorWhole(Math.max(1, Number.parseInt(bottles, 10) || 1));
  const lines = [];
  const unweighed = [];
  const noDensity = [];
  (rows || []).forEach((row) => {
    if (!row.material || !row.amount || editorIsEthanol(row)) return;
    const strength = editorNumber(row.fraction || "1");
    const matches = (labStocks || []).filter((stock) => editorNameKey(nameOf.get(stock.material_id)) === editorNameKey(row.material)
      && strength && editorBench.benchCompare(editorNumber(String(stock.active_fraction)) || EDITOR_ZERO, strength) === 0);
    if (!matches.length) {
      unweighed.push(row.material);
      return;
    }
    let perBottle = null;
    if (row.solid) perBottle = editorBench.benchOver(row.amount, editorWhole(1000));
    else {
      const labDensity = matches.map((stock) => editorNumber(String(stock.density_g_ml ?? ""))).find((value) => value && value.n > 0n);
      const density = labDensity || editorDensity(row, densities);
      if (density) perBottle = editorBench.benchOver(editorBench.benchTimes(row.amount, density), editorWhole(1000));
    }
    if (!perBottle) {
      noDensity.push(row.material);
      return;
    }
    const known = matches.map((stock) => (remaining || {})[stock.id]).filter((value) => value !== null && value !== undefined);
    const nowG = known.length === matches.length ? known.reduce((sum, value) => sum + Number(value), 0) : null;
    const useG = Number(editorBench.benchFractionText(editorBench.benchTimes(perBottle, count), 6));
    lines.push({
      material: row.material,
      stockIds: matches.map((stock) => stock.id),
      nowG,
      useG,
      afterG: nowG === null ? null : nowG - useG,
      short: nowG !== null && nowG < useG,
    });
  });
  return { lines, unweighed, noDensity };
}

// ---- Saved versions ----

// An exact amount as the versions log keeps it: "600" or "1000/3".
function editorAmountText(value) {
  const exact = editorBench.benchFraction(value.n, value.d);
  return exact.d === 1n ? exact.n.toString() : `${exact.n}/${exact.d}`;
}

function editorAmountOf(text) {
  const match = /^([1-9]\d{0,29})(?:\/([1-9]\d{0,29}))?$/.exec(String(text ?? ""));
  return match ? editorBench.benchFraction(BigInt(match[1]), BigInt(match[2] || "1")) : null;
}

// The rows a version keeps: every named row with an amount, exactly as typed.
// Named rows still waiting for an amount are left out and named.
function editorSavedRows(rows) {
  const saved = [];
  const leftOut = [];
  (rows || []).forEach((row) => {
    if (!row.material) return;
    if (!row.amount || row.amount.n <= 0n) {
      leftOut.push(row.material);
      return;
    }
    saved.push({
      material: row.material,
      stock_id: row.stockId || null,
      fraction: row.fraction || "",
      basis: row.basis || "",
      carrier: row.carrier || null,
      solid: Boolean(row.solid),
      amount: editorAmountText(row.amount),
      note: row.note || "",
    });
  });
  return { rows: saved, leftOut };
}

function editorRowsFromSaved(saved) {
  return (saved || []).map((row) => editorRow({
    material: row.material,
    stockId: row.stock_id || null,
    fraction: row.fraction,
    basis: row.basis,
    carrier: row.carrier,
    solid: row.solid,
    amount: editorAmountOf(row.amount),
    note: row.note,
  }));
}

// Equal keys mean nothing a version keeps has changed: the name, the rows and the bottle size.
function editorContentKey(name, rows, bottleMl) {
  return JSON.stringify([String(name ?? "").trim(), editorSavedRows(rows).rows, String(bottleMl ?? "").trim()]);
}

// A share of the finished bottle, % w/w: two significant figures under 1%.
function editorPctText(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return "0%";
  if (number < 0.0001) return "under 0.0001%";
  return `${number >= 1 ? number.toFixed(2) : String(Number(number.toPrecision(2)))}%`;
}

// The mL a card makes, as the Batch page asks for it: the rows themselves when
// they list their ethanol, otherwise one bottle of the size saved with it.
function editorCardMakesMl(rows, bottleMl) {
  if (!(rows || []).some((row) => row.amount && editorIsEthanol(row))) return String(bottleMl ?? "").trim();
  return editorBench.benchFractionText(editorBench.benchOver(editorTotals(rows).liquidUl, editorWhole(1000)), 3);
}

// What changed between two versions' rows. Rows are matched by material,
// strength and unit (one material at two strengths is two rows); a material
// listed twice is summed. Amounts are exact; % is the share of each version's
// liquid. Unchanged amounts are counted, not listed.
function editorCompare(rowsA, rowsB) {
  const collect = (rows) => {
    const byKey = new Map();
    (rows || []).forEach((row) => {
      if (!row.material || !row.amount || row.amount.n <= 0n) return;
      const key = `${editorNameKey(row.material)}|${editorNumber(row.fraction) ? editorAmountText(editorNumber(row.fraction)) : ""}|${row.solid ? "mg" : "uL"}`;
      const seen = byKey.get(key);
      byKey.set(key, seen ? { row: seen.row, amount: editorBench.benchPlus(seen.amount, row.amount) } : { row, amount: row.amount });
    });
    return byKey;
  };
  const before = collect(rowsA);
  const after = collect(rowsB);
  const totalsA = editorTotals(rowsA);
  const totalsB = editorTotals(rowsB);
  const share = (entry, totals) => {
    if (!entry || entry.row.solid || totals.liquidUl.n <= 0n) return "";
    return `${editorFigure(editorBench.benchTimes(editorBench.benchOver(entry.amount, totals.liquidUl), editorWhole(100)), 2)}%`;
  };
  const lines = [];
  let same = 0;
  [...before.keys(), ...[...after.keys()].filter((key) => !before.has(key))].forEach((key) => {
    const a = before.get(key);
    const b = after.get(key);
    if (a && b && editorBench.benchCompare(a.amount, b.amount) === 0) {
      same += 1;
      return;
    }
    const row = (a || b).row;
    let change = "";
    if (a && b) {
      const up = editorBench.benchCompare(b.amount, a.amount) > 0;
      const size = up ? editorBench.benchMinus(b.amount, a.amount) : editorBench.benchMinus(a.amount, b.amount);
      change = `${up ? "+" : "−"}${editorFigure(size, 1)}`;
    }
    lines.push({
      material: row.material,
      strength: editorStrengthText(row),
      unit: row.solid ? "mg" : "µL",
      kind: a && b ? "changed" : (a ? "removed" : "added"),
      a: a ? editorFigure(a.amount, 1) : "",
      b: b ? editorFigure(b.amount, 1) : "",
      change,
      aPct: share(a, totalsA),
      bPct: share(b, totalsB),
    });
  });
  return {
    lines,
    same,
    liquid: [totalsA.liquidUl, totalsB.liquidUl].map((value) => editorFigure(value, 1)),
  };
}

const EDITOR_VERDICT_WORDS = { PASS: "within the limits", WARN: "within the limits, with notes", HOLD: "not fully checked", FAIL: "over an IFRA limit" };

// How an IFRA row reads in a comparison.
function editorIfraRowText(row) {
  if (!row) return "not in this version";
  if (row.verdict === "fail") {
    return row.ifra_status === "prohibited" ? "prohibited" : `${editorPctText(row.actual_pct)} of the bottle, over its ${editorPctText(row.limit_pct)} limit`;
  }
  if (row.usage_pct !== null && row.usage_pct !== undefined) return `${row.usage_pct}% of its limit`;
  return row.verdict === "warn" ? "counted by its constituents" : "within its limit";
}

// Which checks changed between two formula-checks answers: the IFRA verdict,
// rows whose verdict changed, allergens to declare, and the oil share.
function editorCheckChanges(before, after) {
  const changes = [];
  if (before.ifra.verdict !== after.ifra.verdict) {
    const word = (verdict) => EDITOR_VERDICT_WORDS[verdict] || verdict;
    changes.push({ text: `IFRA: ${word(before.ifra.verdict)} → ${word(after.ifra.verdict)}`, problem: after.ifra.verdict === "FAIL" });
  }
  const byName = (answer) => new Map(answer.ifra.rows.map((row) => [editorNameKey(row.material), row]));
  const rowsA = byName(before);
  const rowsB = byName(after);
  [...rowsA.keys(), ...[...rowsB.keys()].filter((key) => !rowsA.has(key))].forEach((key) => {
    const a = rowsA.get(key);
    const b = rowsB.get(key);
    if (a?.verdict === b?.verdict) return;
    // A row added or removed while within its limit is in the rows table already.
    if ((!a && b?.verdict === "pass") || (!b && a?.verdict === "pass")) return;
    changes.push({ text: `${(a || b).material}: ${editorIfraRowText(a)} → ${editorIfraRowText(b)}`, problem: b?.verdict === "fail" });
  });
  const declared = (answer) => new Set(answer.allergens.declare.map((row) => row.allergen));
  const declaredA = declared(before);
  const declaredB = declared(after);
  const added = [...declaredB].filter((name) => !declaredA.has(name));
  const dropped = [...declaredA].filter((name) => !declaredB.has(name));
  if (added.length) changes.push({ text: `Now declared on the label: ${added.join(", ")}` });
  if (dropped.length) changes.push({ text: `No longer declared: ${dropped.join(", ")}` });
  const oilA = Number(before.oil_pct).toFixed(1);
  const oilB = Number(after.oil_pct).toFixed(1);
  if (oilA !== oilB) changes.push({ text: `Oil: ${oilA}% → ${oilB}%` });
  return changes;
}

// ---- Why each row: the notes of the name a row's stock carries ----
// From POST /v2/workbench/formula-roles (engine/formulation_intelligence/brief_notes.py):
// a stock carries a note by its own name or only by its odor words. Not strength.

function editorJoinWords(items) {
  const list = (items || []).filter(Boolean);
  if (list.length < 2) return list.join("");
  return `${list.slice(0, -1).join(", ")} and ${list.at(-1)}`;
}

// The key a row is asked about under: its stock, then its name as typed.
function editorWhyKey(row) {
  return `${row.stockId || ""}|${row.material || ""}`;
}

// The line above the rows: the notes the name asks for.
function editorWhyNotesLine(answer) {
  const notes = (answer && answer.notes) || [];
  if (!notes.length) return `The name “${answer.formula_name}” names no note the composer knows, so each row shows its own profile.`;
  const labels = notes.map((note) => (note.star ? `${note.label} (the star)` : note.label));
  return `The name asks for ${editorJoinWords(labels)}. Each row says which of these its stock carries: by its own name, or only by its odor words.`;
}

// One row's line.
function editorWhyText(info, nameHasNotes = true) {
  if (!info) return "";
  if (!info.found) return "Not in your stock list, so what it carries is not known.";
  const label = (item) => (item.star ? `${item.label} (the star)` : item.label);
  const named = info.carries.filter((item) => item.kind === "material");
  const byName = info.carries.filter((item) => item.kind === "note" && item.by === "name").map(label);
  const byOdor = info.carries.filter((item) => item.kind === "note" && item.by !== "name").map(label);
  const parts = [];
  if (named.length) parts.push("The name names it");
  if (byName.length) parts.push(`${parts.length ? "carries" : "Carries"} the ${editorJoinWords(byName)}`);
  if (byOdor.length) parts.push(`${parts.length ? "" : "Carries "}the ${editorJoinWords(byOdor)} only by its odor words`);
  if (parts.length) return `${parts.join("; ")}.`;
  const profile = info.profile && info.profile.length ? `its own profile: ${info.profile.join(", ")}` : "";
  if (!nameHasNotes) return profile ? `${profile[0].toUpperCase()}${profile.slice(1)}.` : "";
  return profile ? `None of the name's notes; ${profile}.` : "None of the name's notes.";
}

// What the drop preview says the row does for the name.
function editorWhyDropLine(info) {
  if (!info || !info.found) return "";
  const notes = info.carries.filter((item) => item.kind === "note").map((item) => item.label);
  if (info.carries.some((item) => item.kind === "material")) return "The name names this material.";
  if (notes.length) return `It carries the ${editorJoinWords(notes)} the name asks for.`;
  return "It carries none of the notes the name asks for.";
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    editorCheckRows, editorHoldRows, editorCostRows, editorChartRows, editorStockLeft,
    EDITOR_NOTES, editorRow, editorNumber, editorFigure, editorRowsFromSource, editorParsePlain, editorRowsFromPlain,
    editorNameStrength, editorStockCandidates, editorBindRow, editorBindRows, editorStockOf, editorStockIsSolid,
    editorTotals, editorDensity, editorShown, editorInsert, editorRemove, editorReplace, editorSetAmount,
    editorResolveGrams, editorScaleTo, editorSorted, editorHistory, editorCommit, editorUndo, editorRedo,
    editorStrengthText, editorBenchTable, editorTsv,
    editorAmountText, editorAmountOf, editorSavedRows, editorRowsFromSaved, editorContentKey, editorPctText,
    editorCompare, editorIfraRowText, editorCheckChanges, editorCardMakesMl,
    editorJoinWords, editorWhyKey, editorWhyNotesLine, editorWhyText, editorWhyDropLine,
  };
}
