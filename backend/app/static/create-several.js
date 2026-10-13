// Pure rules for "Create several" in the Formula studio: one brief per line,
// each composed as its own engine job, so the engine worker runs up to four
// at once in separate processes. It touches no DOM, so the page loads it
// before lab.js (its functions become page globals) and node runs it in the
// tests. lab.js writes the returned text with textContent.

const SEVERAL_MAX_BRIEFS = 8;
const SEVERAL_MODES = {
  QUICK: { design_mode: "FAST_SKETCH", variant_count: 1 },
  BEST_OF_3: { design_mode: "DEEP_COMPOSE", variant_count: 3 },
};

// Each card polls its own job. A phone or another PC on the network may make 120
// requests a minute (main.py), so the cards share about one poll a second.
function severalPollIntervalMs(count) {
  return Math.max(1000, 1000 * Math.max(1, Number(count) || 1));
}

function parseSeveralBriefs(text, max = SEVERAL_MAX_BRIEFS) {
  const seen = new Set();
  const briefs = [];
  let repeated = 0;
  let over = 0;
  for (const line of String(text || "").split(/\r?\n/)) {
    const brief = line.replace(/\s+/g, " ").trim();
    if (!brief) continue;
    const key = brief.toLowerCase();
    if (seen.has(key)) {
      repeated += 1;
      continue;
    }
    seen.add(key);
    if (briefs.length >= max) {
      over += 1;
      continue;
    }
    briefs.push(brief);
  }
  return { briefs, repeated, over };
}

function severalJobRequest(brief, mode, requestId, options = {}) {
  const chosen = SEVERAL_MODES[mode] || SEVERAL_MODES.QUICK;
  return {
    schema_version: "lab-engine-job-request-v2",
    job_type: "FORMULA_DESIGN",
    requester: "formula-studio-several",
    idempotency_key: requestId,
    payload: {
      message: brief,
      formula_name: null,
      liquid_concentrate_ul_decimal: String(options.liquid_concentrate_ul_decimal || "6000"),
      max_materials: Number(options.max_materials || 60),
      must_preserve: [],
      must_avoid: [],
      previous_stock_ids: [],
      conversation_context: [],
      design_mode: chosen.design_mode,
      variant_count: chosen.variant_count,
    },
  };
}

function _primaryFormula(result) {
  const variant = (result?.design_variants || [])[0];
  return variant?.formula || result?.optimized_formula || null;
}

function _amount(row) {
  const raw = String(row?.amount_unit || "uL").toLowerCase();
  const unit = raw === "ul" || raw === "µl" ? "µL" : raw;
  const value = Number(row?.amount_decimal);
  return { unit, value: Number.isFinite(value) ? value : 0 };
}

function _amountUl(row) {
  const amount = _amount(row);
  return amount.unit === "µL" ? amount.value : 0;
}

function _firstSentence(text) {
  const value = String(text || "");
  const end = value.search(/\.\s/);
  return end === -1 ? value : value.slice(0, end + 1);
}

function _percent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : null;
}

function severalCardSummary(result) {
  const formula = _primaryFormula(result);
  const rows = Array.isArray(formula?.rows) ? formula.rows : [];
  if (!formula || !rows.length) {
    return {
      hasFormula: false,
      name: String(result?.formula_name || "No formula"),
      lines: [{ status: "HOLD", text: String(result?.assistant_message || "The brief needs clarification before a formula can be made.") }],
      materials: 0,
      totalUl: 0,
      alternatives: 0,
    };
  }
  const lines = [];
  // The composer's own check: brief words against stock names and descriptors only.
  const selfCheck = result?.composition_plan?.brief_self_check?.check;
  const covered = selfCheck ? _percent(selfCheck.word_coverage) : null;
  if (covered) {
    const missed = (selfCheck.uncovered_words || []).filter(Boolean).map(String);
    lines.push({
      status: missed.length ? "HOLD" : "PASS",
      text: missed.length
        ? `Brief words a stock names: ${covered}. Not named by any stock: ${missed.join(", ")}`
        : `Brief words a stock names: ${covered}`,
    });
  }
  const variant = (result?.design_variants || [])[0];
  const checks = typeof compositionCheckLines === "function"
    ? compositionCheckLines(variant ? variant.composition_checks : result?.composition_checks)
    : null;
  if (checks) {
    // The card keeps each check's first sentence; the studio shows the whole advice.
    for (const line of checks.lines) lines.push({ status: line.status, text: _firstSentence(line.text) });
  }
  const variants = (result?.design_variants || []).filter((row) => row && !row.duplicate_of_variant_id);
  return {
    hasFormula: true,
    name: String(result?.formula_name || formula.name || "Formula draft"),
    lines,
    materials: rows.length,
    totalUl: Math.round(rows.reduce((sum, row) => sum + _amountUl(row), 0)),
    alternatives: Math.max(0, variants.length - 1),
  };
}

function severalCompareRows(resultA, resultB) {
  const byName = new Map();
  const add = (result, side) => {
    for (const row of _primaryFormula(result)?.rows || []) {
      const name = String(row.identity_name || row.material || "");
      if (!name) continue;
      // A weighed solid (mg) stays its own line: mg and µL are never added together.
      const amount = _amount(row);
      const key = `${name}\u0000${amount.unit}`;
      const entry = byName.get(key) || { material: name, unit: amount.unit, a: 0, b: 0 };
      entry[side] += amount.value;
      byName.set(key, entry);
    }
  };
  add(resultA, "a");
  add(resultB, "b");
  return [...byName.values()]
    .map((entry) => ({ ...entry, a: Math.round(entry.a), b: Math.round(entry.b), shared: entry.a > 0 && entry.b > 0 }))
    .sort((x, y) => Math.max(y.a, y.b) - Math.max(x.a, x.b) || x.material.localeCompare(y.material));
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    SEVERAL_MAX_BRIEFS,
    SEVERAL_MODES,
    parseSeveralBriefs,
    severalPollIntervalMs,
    severalJobRequest,
    severalCardSummary,
    severalCompareRows,
  };
}
