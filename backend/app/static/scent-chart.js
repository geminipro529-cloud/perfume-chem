// Smell-over-time chart for the Create result. Draws the endpoint's modelled
// share of what the model can detect at five stages as an inline SVG stacked-band
// chart. A screening model, not a measurement. Text reaches the page only
// through textContent / setAttribute. The page loads this before lab.js; node
// loads the pure model for tests.

const SCENT_CHART_ENDPOINT = "/api/v1/lab/v2/workbench/scent-curve";
const SCENT_WINDOW_NAMES = {
  opening: "Opening", top: "5 minutes", heart: "30 minutes", late_heart: "2 hours", drydown: "4 hours",
};
const SCENT_TIERS = ["top", "heart", "base"];
const SCENT_SVG_NS = "http://www.w3.org/2000/svg";
const SCENT_CAPTION = "Share of what the model can detect at each stage (odour-threshold ratio). It says nothing about strength or pleasantness. A model, not a measurement.";
const scentCurveCache = new Map();

function scentPercent(share) {
  const value = Math.round(share * 100);
  return value === 0 && share > 0 ? "<1%" : `${value}%`;
}

function scentChartRows(rows) {
  return (rows || [])
    .filter((row) => row && row.amount_unit === "uL" && row.identity_name)
    .map((row) => ({
      identity_name: String(row.identity_name),
      amount_ul: Number(row.amount_decimal),
      stock_fraction: Number(row.stock_fraction_decimal) > 0 ? Number(row.stock_fraction_decimal) : 1,
    }))
    .filter((row) => Number.isFinite(row.amount_ul) && row.amount_ul > 0);
}

// Pure: endpoint payload -> what the chart draws.
function scentChartModel(curve) {
  const windows = (curve && curve.windows) || [];
  const byName = new Map();
  windows.forEach((win, index) => {
    (win.materials || []).forEach((m) => {
      if (!byName.has(m.name)) byName.set(m.name, { name: m.name, note: m.note, known: m.known, shares: windows.map(() => 0) });
      const entry = byName.get(m.name);
      if (m.known) entry.shares[index] = m.share || 0;
      else entry.known = false;
    });
  });
  const all = [...byName.values()];
  const tierRank = (note) => Math.max(0, SCENT_TIERS.indexOf(note));
  const series = all
    .filter((s) => s.known && s.shares.some((v) => v > 0))
    .sort((a, b) => tierRank(a.note) - tierRank(b.note) || a.name.localeCompare(b.name));
  const tierCount = {};
  series.forEach((s) => { s.rank = tierCount[s.note] = (tierCount[s.note] || 0) + 1; });
  const columns = windows.map((win, index) => {
    const tiers = { top: 0, heart: 0, base: 0 };
    series.forEach((s) => { if (tiers[s.note] !== undefined) tiers[s.note] += s.shares[index]; });
    return {
      key: win.label,
      name: SCENT_WINDOW_NAMES[win.label] || String(win.label),
      top: (win.top || []).slice(0, 3),
      voices: win.effective_voices || 0,
      tiers,
    };
  });
  return { series, columns, unknown: all.filter((s) => !s.known).map((s) => s.name) };
}

function scentSvg(tag, attrs, text) {
  const node = document.createElementNS(SCENT_SVG_NS, tag);
  Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, String(v)));
  if (text !== undefined) node.textContent = text;
  return node;
}

function scentEl(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function scentSummary(model) {
  const parts = model.columns.map((c) => `${c.name}: ${c.top[0] || "nothing detectable"}`);
  return `Smell over time, share of what the model can detect (not strength or pleasantness). Dominant material by stage. ${parts.join("; ")}.`;
}

function drawScentChart(container, model) {
  container.replaceChildren();
  const n = model.columns.length;
  if (!n || !model.series.length) {
    container.append(scentEl("p", "scent-chart-note", "The model finds nothing detectable to draw for these rows."));
    return;
  }
  const W = 600, H = 240, L = 40, R = 12, T = 10, B = 28;
  const x = (i) => L + (n === 1 ? 0 : (i * (W - L - R)) / (n - 1));
  const y = (v) => T + (1 - v) * (H - T - B);
  const svg = scentSvg("svg", { viewBox: `0 0 ${W} ${H}`, class: "scent-chart-svg", role: "img", "aria-label": scentSummary(model) });
  [0, 0.5, 1].forEach((v) => {
    svg.append(scentSvg("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "scent-grid" }));
    svg.append(scentSvg("text", { x: L - 6, y: y(v) + 4, class: "scent-axis", "text-anchor": "end" }, `${v * 100}%`));
  });
  const tip = scentEl("div", "scent-tip");
  tip.hidden = true;
  tip.setAttribute("role", "status");
  const showTip = (lines) => { tip.replaceChildren(...lines.map((t, i) => scentEl(i ? "span" : "strong", "", t))); tip.hidden = false; };
  const hideTip = () => { tip.hidden = true; };
  const cumulative = new Array(n).fill(0);
  model.series.forEach((s) => {
    const lower = cumulative.slice();
    s.shares.forEach((v, i) => { cumulative[i] += v; });
    const upper = cumulative.slice();
    const d = upper.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ")
      + lower.map((v, i) => ` L${x(n - 1 - i)},${y(lower[n - 1 - i])}`).join("") + " Z";
    const band = scentSvg("path", {
      d, class: `scent-band tier-${s.note}`, "data-material": s.name, "data-tier": s.note, tabindex: 0,
      "fill-opacity": [0.95, 0.7, 0.5, 0.82][(s.rank - 1) % 4],
      "aria-label": `${s.name}, ${s.note} note`,
    });
    const lines = [`${s.name} (${s.note} note)`, ...s.shares.map((v, i) => `${model.columns[i].name}: ${scentPercent(v)}`)];
    ["mouseenter", "focus"].forEach((ev) => band.addEventListener(ev, () => showTip(lines)));
    ["mouseleave", "blur"].forEach((ev) => band.addEventListener(ev, hideTip));
    svg.append(band);
  });
  model.columns.forEach((c, i) => {
    svg.append(scentSvg("text", { x: x(i), y: H - 8, class: "scent-axis", "text-anchor": i === 0 ? "start" : i === n - 1 ? "end" : "middle" }, c.name));
    const bar = scentSvg("rect", {
      x: x(i) - 12, y: T, width: 24, height: H - T - B, class: "scent-column", "data-window": c.key, tabindex: 0,
      "aria-label": `${c.name}: ${c.top.join(", ") || "nothing detectable"}`,
    });
    const lines = [c.name, ...(c.top.length ? c.top.map((name) => `${name}: ${scentPercent(model.series.find((s) => s.name === name).shares[i])}`) : ["nothing detectable in the model"])];
    ["mouseenter", "focus"].forEach((ev) => bar.addEventListener(ev, () => showTip(lines)));
    ["mouseleave", "blur"].forEach((ev) => bar.addEventListener(ev, hideTip));
    svg.append(bar);
  });
  const frame = scentEl("div", "scent-frame");
  frame.append(svg, tip);
  container.append(frame, scentEl("p", "scent-caption", SCENT_CAPTION));

  const legend = scentEl("ul", "scent-legend");
  model.series.forEach((s) => {
    const item = scentEl("li");
    const swatch = scentEl("span", `scent-swatch tier-${s.note}`);
    swatch.style.opacity = String([0.95, 0.7, 0.5, 0.82][(s.rank - 1) % 4]);
    item.append(swatch, document.createTextNode(`${s.name} (${s.note})`));
    legend.append(item);
  });
  container.append(legend);

  const strip = scentEl("ol", "scent-dominance");
  model.columns.forEach((c) => {
    const item = scentEl("li");
    item.append(scentEl("strong", "", c.name), scentEl("span", "", c.top.join(", ") || "nothing detectable"));
    strip.append(item);
  });
  container.append(strip);

  const tierBars = scentEl("div", "scent-tiers");
  [model.columns[0], model.columns[n - 2] || model.columns[n - 1]].filter(Boolean).forEach((c) => {
    const row = scentEl("div", "scent-tier-row");
    row.append(scentEl("span", "scent-tier-name", c.name));
    const bar = scentEl("span", "scent-tier-bar");
    SCENT_TIERS.forEach((tier) => {
      const seg = scentEl("span", `tier-${tier}`);
      seg.style.flexGrow = String(c.tiers[tier]);
      bar.append(seg);
    });
    row.append(bar, scentEl("span", "scent-tier-text",
      SCENT_TIERS.map((tier) => `${tier} ${scentPercent(c.tiers[tier])}`).join(" · ")));
    tierBars.append(row);
  });
  container.append(tierBars);

  if (model.unknown.length) {
    container.append(scentEl("p", "scent-unknown", `No data yet for: ${model.unknown.join(", ")}. These are not drawn.`));
  }

  const table = scentEl("table", "sr-only");
  table.append(scentEl("caption", "", "Share of what the model can detect, by material and stage"));
  const head = scentEl("tr");
  head.append(scentEl("th", "", "Material"), ...model.columns.map((c) => scentEl("th", "", c.name)));
  table.append(head);
  model.series.forEach((s) => {
    const row = scentEl("tr");
    row.append(scentEl("th", "", s.name), ...s.shares.map((v) => scentEl("td", "", scentPercent(v))));
    table.append(row);
  });
  container.append(table);
}

// Fetch and draw. A newer call on the same container wins (variant switch).
async function renderScentChart(container, designRows) {
  if (!container) return;
  const seq = (container.scentSeq = (container.scentSeq || 0) + 1);
  const rows = scentChartRows(designRows);
  if (!rows.length) { container.replaceChildren(); container.hidden = true; return; }
  container.hidden = false;
  container.replaceChildren(scentEl("p", "scent-chart-note", "Working out the smell over time…"));
  const key = JSON.stringify(rows);
  try {
    let curve = scentCurveCache.get(key);
    if (!curve) {
      const response = await fetch(SCENT_CHART_ENDPOINT, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      curve = await response.json();
      scentCurveCache.set(key, curve);
    }
    if (seq !== container.scentSeq) return;
    drawScentChart(container, scentChartModel(curve));
  } catch (error) {
    if (seq !== container.scentSeq) return;
    container.replaceChildren(scentEl("p", "scent-chart-note", "The smell-over-time picture is not available right now."));
  }
}

if (typeof module === "object" && module.exports) {
  module.exports = { scentChartModel, scentChartRows };
}
