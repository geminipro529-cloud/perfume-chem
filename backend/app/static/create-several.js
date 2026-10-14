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
      scorecard: true,
    },
  };
}

// A card whose job may still finish offers "Check again", which asks the server for the
// same job instead of composing anew: the poll lost the network or the app was busy
// (no answer, 429, 5xx), or the job ran past its time limit. A job that ended (failed,
// withheld or cancelled) or a request the server refused (4xx) gets nothing from a
// second look: the server hands the same request the same job.
function severalCanCheckAgain(error) {
  if (!error || error.jobEnded) return false;
  if (error.jobStillRunning) return true;
  const status = Number(error.status) || 0;
  return status === 0 || status === 429 || status >= 500;
}

// states: one per card, COMPOSING, DONE, WAITING (it offers Check again) or FAILED.
// elapsed: the batch's time in words, once every card has settled the first time.
function severalStatusText(states, { elapsed = "", skipped = "" } = {}) {
  const count = (state) => states.filter((value) => value === state).length;
  const total = states.length;
  const done = count("DONE");
  const waiting = count("WAITING");
  const failed = count("FAILED");
  const parts = [];
  if (count("COMPOSING")) {
    parts.push(`Composed ${done} of ${total}.`);
  } else {
    const took = elapsed ? ` in ${elapsed}` : "";
    parts.push(done === total
      ? `Composed ${total} perfume${total === 1 ? "" : "s"}${took}.`
      : `Composed ${done} of ${total} perfumes${took}.`);
  }
  if (waiting) {
    parts.push(waiting === 1
      ? "1 may still finish: press Check again on its card."
      : `${waiting} may still finish: press Check again on their cards.`);
  }
  if (failed) parts.push(`${failed} ${failed === 1 ? "was" : "were"} not composed.`);
  if (skipped) parts.push(`Skipped ${skipped}.`);
  return parts.join(" ");
}

// The yardstick's floors (engine_job_executor._design_scorecards), in card order.
const SEVERAL_FLOOR_LABELS = [
  ["F1_owned_stock", "Stock"],
  ["F2_ifra", "IFRA"],
  ["F3_pre_mix_guard", "Pre-mix guard"],
  ["F4_bottle", "30 mL bottle"],
  ["F5_pours", "Pours"],
  ["F6_musks", "Musks"],
];

function _primaryFloors(result) {
  const variant = (result?.design_variants || [])[0];
  const cards = Array.isArray(result?.scorecards) ? result.scorecards : [];
  const card = cards.find((entry) => variant && entry.variant_id === String(variant.variant_id)) || cards[0];
  return card && card.floors ? card.floors : null;
}

function severalFloorChips(result) {
  const floors = _primaryFloors(result);
  if (!floors) return [];
  return SEVERAL_FLOOR_LABELS
    .filter(([id]) => floors[id] && floors[id].status !== "NOT_APPLICABLE")
    .map(([id, label]) => ({ label, status: String(floors[id].status) }));
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
  const floors = _primaryFloors(result);
  if (floors) {
    for (const [id, label] of SEVERAL_FLOOR_LABELS) {
      const floor = floors[id];
      if (!floor || floor.status === "PASS" || floor.status === "NOT_APPLICABLE") continue;
      const detail = _firstSentence(floor.detail);
      const named = detail.toLowerCase().startsWith(label.toLowerCase());
      lines.push({ status: String(floor.status), text: named ? detail : `${label}: ${detail}` });
    }
  }
  const variant = (result?.design_variants || [])[0];
  const checks = typeof compositionCheckLines === "function"
    ? compositionCheckLines(variant ? variant.composition_checks : result?.composition_checks)
    : null;
  if (checks) {
    // The card keeps each check's first sentence; the studio shows the whole advice.
    // With the floors present, their chips and IFRA line already say what the
    // checks' IFRA and passed lines would, so only the checks' own flags stay.
    for (const line of checks.lines) {
      if (floors && floors.F2_ifra && (line.text.startsWith("IFRA:") || line.status === "PASS")) continue;
      lines.push({ status: line.status, text: _firstSentence(line.text) });
    }
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

// ---- One of Kenny's own bench cards beside a composed card ----
// The card is pasted, parsed by /v2/workbench/formula-text and compared here; nothing
// is saved. Bench cards write the strength into the material, as it is in the bottle:
// "Cashmeran 20% w/w in DPG", "Hedione (neat)", "Ambrofix Crystals (neat), weigh".

// The strength a bench-card material names: a fraction (1 for neat) or null when unread.
function severalStrength(text) {
  const value = String(text || "");
  const percent = value.match(/(\d+(?:[.,]\d+)?)\s*%/);
  if (percent) {
    const fraction = Number(percent[1].replace(",", ".")) / 100;
    return fraction > 0 && fraction <= 1 ? fraction : null;
  }
  return /\bneat\b/i.test(value) ? 1 : null;
}

// The material itself: no strength, solvent, parentheses or bench words.
function severalMaterialName(text) {
  return String(text || "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/\d+(?:[.,]\d+)?\s*%(?:\s*(?:w\/w|v\/v|wt))?(?:\s+in\s+[A-Za-z][\w-]*)?/gi, " ")
    .replace(/,?\s*\*{0,2}weigh\*{0,2}\b/gi, " ")
    .replace(/\bneat\b/gi, " ")
    .replace(/[*_]/g, "")
    .replace(/\s+/g, " ")
    .replace(/^[\s,;:-]+|[\s,;:-]+$/g, "");
}

function severalNameKey(text) {
  return severalMaterialName(text).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

// Active amount of one row: the pour times its strength, in µL or mg as poured.
// Strengths are w/w or v/v as labelled; densities are not applied, so it is approximate.
function _activeAmount(amount, fraction) {
  return fraction === null ? null : amount.value * fraction;
}

function severalOwnCompare(result, ownSource) {
  const byKey = new Map();
  const unread = [];
  const add = (side, name, row, fraction) => {
    const key = severalNameKey(name);
    if (!key) return;
    const amount = _amount(row);
    const active = _activeAmount(amount, fraction);
    if (active === null) {
      unread.push(severalMaterialName(name));
      return;
    }
    const mapKey = `${key}\u0000${amount.unit}`;
    const entry = byKey.get(mapKey) || { material: severalMaterialName(name), unit: amount.unit, a: 0, b: 0 };
    entry[side] += active;
    byKey.set(mapKey, entry);
  };
  for (const row of _primaryFormula(result)?.rows || []) {
    const raw = row.stock_fraction_decimal;
    const fraction = raw === undefined || raw === null || raw === "" ? 1 : Number(raw);
    add("a", row.identity_name || row.material, row, Number.isFinite(fraction) && fraction > 0 ? fraction : null);
  }
  for (const row of ownSource?.rows || []) {
    const given = Number(row.concentration_fraction_decimal);
    const fraction = row.concentration_fraction_decimal && Number.isFinite(given) && given > 0 ? given : severalStrength(row.material);
    add("b", row.material, row, fraction);
  }
  // A trace (1 µL of a 1% dilution is 0.01 µL active) keeps one figure, never 0.
  const shown = (value) => (value <= 0 ? 0 : value < 10 ? Math.max(0.1, Math.round(value * 10) / 10) : Math.round(value));
  const rows = [...byKey.values()]
    .map((entry) => ({ ...entry, a: shown(entry.a), b: shown(entry.b), shared: entry.a > 0 && entry.b > 0 }))
    .sort((x, y) => Math.max(y.a, y.b) - Math.max(x.a, x.b) || x.material.localeCompare(y.material));
  const count = (test) => rows.filter(test).length;
  return {
    rows,
    inBoth: count((row) => row.shared),
    onlyHere: count((row) => row.a > 0 && !row.b),
    onlyYours: count((row) => row.b > 0 && !row.a),
    unread: [...new Set(unread)],
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    SEVERAL_MAX_BRIEFS,
    SEVERAL_MODES,
    parseSeveralBriefs,
    severalPollIntervalMs,
    severalJobRequest,
    severalCanCheckAgain,
    severalStatusText,
    severalCardSummary,
    severalFloorChips,
    severalCompareRows,
    severalStrength,
    severalMaterialName,
    severalOwnCompare,
  };
}
