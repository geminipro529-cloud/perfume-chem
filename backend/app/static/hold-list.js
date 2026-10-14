// "What's missing": when a stock or IFRA check says HOLD, this lists per material
// what the check lacks and what to do (POST /v2/workbench/formula-holds), with a
// button that opens that stock's entry on the Stock page. It opens on a tap only,
// so nothing calls the engine while a formula is being read or typed.
//
// Create a formula (the studio and each Create several card) and Edit a formula
// attach it. Names and text go in through textContent only, never HTML strings.
// Node loads the same file in the tests through module.exports.

const HOLD_CHECK_WORDS = { stock: "Stock", ifra: "IFRA" };
const HOLD_OPEN_STOCK_TEXT = "Open on the Stock page";

function holdAmountText(value) {
  const text = String(value ?? "").trim();
  const number = Number(text);
  return text && Number.isFinite(number) && number > 0 ? text : "";
}

function holdFractionText(value) {
  const text = String(value ?? "").trim();
  const number = Number(text);
  return text && Number.isFinite(number) && number > 0 && number <= 1 ? text : "1";
}

function holdCarrierText(value) {
  const text = String(value ?? "").trim();
  return text === "None" || text === "null" ? "" : text;
}

// The composer's rows (amount_decimal + amount_unit, stock_fraction_decimal,
// fraction_basis, carrier) as the request's rows. Rows in other units are left out.
function holdRowsFromDesign(rows) {
  const out = [];
  for (const row of rows || []) {
    const material = String(row?.material || row?.identity_name || "").trim();
    const unit = String(row?.amount_unit || "uL").trim().toLowerCase();
    const amount = holdAmountText(row?.amount_decimal);
    if (!material || !amount || !["ul", "µl", "mg"].includes(unit)) continue;
    out.push({
      material,
      stock_id: row?.stock_id || null,
      amount,
      unit: unit === "mg" ? "mg" : "uL",
      fraction: holdFractionText(row?.stock_fraction_decimal),
      basis: String(row?.fraction_basis || ""),
      carrier: holdCarrierText(row?.carrier),
    });
  }
  return out;
}

// What the page shows for an answer: plain data, so the tests can read it.
function holdListView(answer) {
  const items = Array.isArray(answer?.items) ? answer.items : [];
  return {
    summary: String(answer?.summary || ""),
    basis: String(answer?.basis || ""),
    items: items.map((item) => ({
      id: String(item.id || ""),
      check: HOLD_CHECK_WORDS[item.check] || "Check",
      material: String(item.material || "The formula"),
      reason: String(item.reason || ""),
      action: String(item.action || ""),
      stockId: item.open && item.open.kind === "stock_page" && item.open.stock_id ? String(item.open.stock_id) : "",
    })),
  };
}

function holdEl(doc, tag, className, text) {
  const node = doc.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderHoldList(panel, answer, openStock) {
  const doc = panel.ownerDocument;
  const view = holdListView(answer);
  const summary = holdEl(doc, "p", "hold-list-summary", view.summary);
  const list = holdEl(doc, "ul", "hold-list-items");
  for (const item of view.items) {
    const entry = holdEl(doc, "li", "hold-item");
    entry.dataset.check = item.check.toLowerCase();
    const head = holdEl(doc, "p", "hold-item-head");
    head.append(holdEl(doc, "strong", "", item.material), holdEl(doc, "span", "hold-item-check", item.check));
    entry.append(head, holdEl(doc, "p", "hold-item-reason", item.reason), holdEl(doc, "p", "hold-item-action", item.action));
    if (item.stockId && typeof openStock === "function") {
      const button = holdEl(doc, "button", "quiet-button hold-item-open", HOLD_OPEN_STOCK_TEXT);
      button.type = "button";
      button.addEventListener("click", () => openStock(item.stockId));
      entry.append(button);
    }
    list.append(entry);
  }
  panel.replaceChildren(summary, ...(view.items.length ? [list] : []), holdEl(doc, "small", "hold-list-basis", view.basis));
}

// toggle: the "What's missing" button; panel: where the list goes.
// rows() and bottleMl() are read on each tap; an unchanged formula is not asked twice.
function attachHoldList({ toggle, panel, request, rows, bottleMl = () => 30, openStock }) {
  const answers = new Map();
  let seq = 0;
  toggle.setAttribute("aria-expanded", "false");
  if (panel.id) toggle.setAttribute("aria-controls", panel.id);
  panel.hidden = true;

  const collapse = () => {
    seq += 1;
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
  };

  toggle.addEventListener("click", async () => {
    if (toggle.getAttribute("aria-expanded") === "true") {
      collapse();
      return;
    }
    toggle.setAttribute("aria-expanded", "true");
    panel.hidden = false;
    const body = JSON.stringify({ rows: rows(), bottle_ml: Number(bottleMl()) || 30 });
    const mine = ++seq;
    let answer = answers.get(body);
    if (!answer) {
      panel.replaceChildren(holdEl(panel.ownerDocument, "p", "hold-list-summary", "Checking what is missing…"));
      try {
        answer = await request("/v2/workbench/formula-holds", { method: "POST", body });
        answers.set(body, answer);
      } catch (error) {
        if (mine !== seq) return;
        panel.replaceChildren(holdEl(panel.ownerDocument, "p", "hold-list-summary is-problem",
          `Could not check what is missing: ${error?.message || error}`));
        return;
      }
    }
    if (mine !== seq) return;
    renderHoldList(panel, answer, openStock);
  });

  // A new formula on the page: the open list belonged to the old one.
  return { reset: collapse };
}

if (typeof module === "object" && module.exports) {
  module.exports = { holdRowsFromDesign, holdListView, holdAmountText, HOLD_OPEN_STOCK_TEXT };
}
