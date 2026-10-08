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

// One line per design row, in design order. Running totals are exact and per
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

function benchSheetHtml({ formulaName, variantLabel, dateText, totals, rows, critic }) {
  const { lines, leftOut } = benchSheetLines(rows);
  const hold = benchSheetHold(rows, critic);
  const totalParts = [];
  if (totals?.liquid_total_ul !== undefined) totalParts.push(`${totals.liquid_total_ul} µL liquid stock`);
  if (Number(totals?.mass_total_mg) > 0) totalParts.push(`${totals.mass_total_mg} mg solids, weighed as separate mg lines`);
  const note = benchLeaveOutNote(leftOut);
  const body = lines.map((line) => {
    const classes = [line.mass ? "bench-mass-line" : "", line.pipettable ? "" : "bench-dilution-line"].filter(Boolean).join(" ");
    return `<tr${classes ? ` class="${classes}"` : ""}>
      <td class="bench-number">${line.number}</td>
      <td>${line.pipettable ? '<span class="bench-tick" role="img" aria-label="not yet added"></span>' : ""}</td>
      <td><strong>${benchEscape(line.material)}</strong>${line.mark ? `<small class="bench-dilution-mark">${benchEscape(line.mark)}</small>` : ""}</td>
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
        <div><dt>Order</dt><dd>Order as designed. Use your own basket order at the balance.</dd></div>
      </dl>
      ${note ? `<p class="bench-sheet-note">${benchEscape(note)}</p>` : ""}
    </header>
    <table class="bench-sheet-table">
      <thead><tr><th>#</th><th>Done</th><th>Material</th><th>Stock and strength</th><th>Amount</th><th>Running total</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

if (typeof module === "object" && module.exports) {
  module.exports = { addDecimalText, benchUnitKey, benchPercentText, benchBasisText, benchNeedsPreparedDilution, benchSheetLines, benchSheetHold, benchLeaveOutNote, benchSheetHtml, benchEscape };
}
