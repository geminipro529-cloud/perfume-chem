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

if (typeof module === "object" && module.exports) {
  module.exports = {
    EDITOR_NOTES, editorRow, editorNumber, editorFigure, editorRowsFromSource, editorParsePlain, editorRowsFromPlain,
    editorNameStrength, editorStockCandidates, editorBindRow, editorBindRows, editorStockOf, editorStockIsSolid,
    editorTotals, editorDensity, editorShown, editorInsert, editorRemove, editorReplace, editorSetAmount,
    editorResolveGrams, editorScaleTo, editorSorted, editorHistory, editorCommit, editorUndo, editorRedo,
    editorStrengthText, editorBenchTable, editorTsv,
  };
}
