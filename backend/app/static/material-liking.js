// "Rate" on the Stock page: Kenny smells one material on a blotter and rates it
// 1 to 10. Each rating is a direct observation in his personal liking fit.
//
// lab.js calls attachMaterialLiking once. Material names and anything typed go
// in through textContent / .value only, never HTML strings. Node loads the same
// file in the tests through module.exports.

const MATERIAL_LIKING_API = "/api/v1/feedback";
const MATERIAL_STRENGTHS = ["weak", "medium", "strong"];

function materialLikingNode(doc, tag, attributes = {}, text = "") {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

function materialLikingBody(stock, stockLabel, fields) {
  const note = String(fields.note ?? "").trim();
  return {
    material: String(stock.identity_name || stock.material || "").trim(),
    stock_label: String(stockLabel || "").trim() || null,
    strength: MATERIAL_STRENGTHS.includes(fields.strength) ? fields.strength : null,
    liking: Number(fields.liking),
    note: note || null,
    source: "stock_card",
  };
}

function materialRatingsPath(material) {
  return `/liking/materials?material=${encodeURIComponent(material)}`;
}

function attachMaterialLiking({ doc, list, getInventory, request }) {
  let openRow = null;

  function close() {
    if (openRow) openRow.remove();
    openRow = null;
  }

  function summaryText(ratings) {
    if (!ratings.length) return "No ratings of this material yet.";
    return `${ratings.length} saved rating${ratings.length === 1 ? "" : "s"}; last ${ratings[0].liking} of 10.`;
  }

  function open(row, stock, stockLabel) {
    close();
    const material = String(stock.identity_name || stock.material || "").trim();
    const form = materialLikingNode(doc, "form", { class: "form-panel stock-liking-form" });
    form.appendChild(materialLikingNode(doc, "p", { class: "field-help" },
      `Smell ${material} on a blotter and rate how much you like it, 1 (dislike) to 10 (love).`));
    const choice = materialLikingNode(doc, "select", { name: "liking", "aria-label": "Liking, 1 to 10" });
    choice.appendChild(materialLikingNode(doc, "option", { value: "" }, "Liking…"));
    for (let n = 1; n <= 10; n += 1) choice.appendChild(materialLikingNode(doc, "option", { value: String(n) }, String(n)));
    const strength = materialLikingNode(doc, "select", { name: "strength", "aria-label": "Strength on the blotter" });
    strength.appendChild(materialLikingNode(doc, "option", { value: "" }, "Strength (optional)"));
    for (const word of MATERIAL_STRENGTHS) strength.appendChild(materialLikingNode(doc, "option", { value: word }, word));
    const note = materialLikingNode(doc, "input", { name: "note", type: "text", maxlength: "500", "aria-label": "Note (optional)", placeholder: "Note (optional)" });
    const save = materialLikingNode(doc, "button", { type: "submit" }, "Save");
    const cancel = materialLikingNode(doc, "button", { type: "button", class: "quiet-button" }, "Cancel");
    const undo = materialLikingNode(doc, "button", { type: "button", class: "quiet-button" }, "Undo");
    undo.hidden = true;
    const status = materialLikingNode(doc, "p", { class: "status-line", role: "status" });
    form.append(choice, strength, note, save, cancel, undo, status);

    let ratings = [];
    const showSummary = () => {
      status.textContent = summaryText(ratings);
      undo.hidden = !ratings.length;
    };
    request(materialRatingsPath(material), { base: MATERIAL_LIKING_API })
      .then((rows) => { ratings = Array.isArray(rows) ? rows : []; showSummary(); })
      .catch(() => { status.textContent = "Couldn't load your earlier ratings of this material."; });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!choice.value) { status.textContent = "Pick a liking from 1 to 10."; return; }
      save.disabled = true;
      try {
        const body = materialLikingBody(stock, stockLabel, { liking: choice.value, strength: strength.value, note: note.value });
        const saved = await request("/liking/materials", { method: "POST", base: MATERIAL_LIKING_API, body: JSON.stringify(body) });
        ratings = [saved, ...ratings];
        showSummary();
        status.textContent = `Saved. ${summaryText(ratings)}`;
      } catch (error) {
        status.textContent = error.message || "The rating was not saved.";
      } finally {
        save.disabled = false;
      }
    });
    undo.addEventListener("click", async () => {
      if (!ratings.length) return;
      undo.disabled = true;
      try {
        await request(`/liking/materials/${encodeURIComponent(ratings[0].id)}`, { method: "DELETE", base: MATERIAL_LIKING_API });
        ratings = ratings.slice(1);
        showSummary();
      } catch (error) {
        status.textContent = error.message || "The rating was not removed.";
      } finally {
        undo.disabled = false;
      }
    });
    cancel.addEventListener("click", close);

    const cell = materialLikingNode(doc, "td", { colspan: String(row.children.length || 1) });
    cell.appendChild(form);
    openRow = materialLikingNode(doc, "tr", { class: "stock-liking-row" });
    openRow.appendChild(cell);
    row.after(openRow);
    choice.focus();
  }

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-rate-stock]");
    if (!button) return;
    const stock = (getInventory().stocks || []).find((item) => item.stock_id === button.dataset.rateStock);
    const row = button.closest("tr");
    if (stock && row) open(row, stock, button.dataset.stockLabel || "");
  });
}

if (typeof module === "object" && module.exports) {
  module.exports = { materialLikingBody, materialRatingsPath, attachMaterialLiking };
}
