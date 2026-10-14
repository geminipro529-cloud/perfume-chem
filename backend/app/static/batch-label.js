// Batch view: printable Thai retail label and IFRA Category 4 self-declaration.
//
// The server builds both pages (POST /commercial-pack/label and
// /commercial-pack/ifra-statement); this file turns its answers into printable
// DOM. labelView / statementView are plain-data and DOM-free; renderView builds
// elements with createElement + textContent only, never HTML strings, so names
// and anything typed cannot become markup. Node loads the file in the tests
// through module.exports.

const BATCH_TO_FILL = "[ to fill ]";

// Text split so every "[ to fill ]" can be marked on the page.
function fillParts(text) {
  const parts = [];
  String(text ?? "").split(BATCH_TO_FILL).forEach((piece, index) => {
    if (index > 0) parts.push({ text: BATCH_TO_FILL, fill: true });
    if (piece) parts.push({ text: piece, fill: false });
  });
  return parts;
}

function labelView(label) {
  const blocks = [];
  if (label.draft_banner) blocks.push({ tag: "p", className: "batch-banner", text: label.draft_banner });
  blocks.push({
    tag: "div", className: "batch-label-front",
    children: label.front.map((text, index) => ({ tag: "p", className: index === 0 ? "batch-label-name" : "", text })),
  });
  blocks.push({
    tag: "div", className: "batch-label-back", lang: "th",
    children: label.thai.map((line) => ({ tag: "p", label: line.label ? `${line.label}:` : "", text: line.text })),
  });
  if (label.english.length) {
    blocks.push({
      tag: "div", className: "batch-label-back batch-label-english", lang: "en",
      children: label.english.map((text) => ({ tag: "p", text })),
    });
  }
  const notes = [label.type.concentration_text, label.type.note];
  if (label.ingredients.order_note) notes.push(label.ingredients.order_note);
  if (label.missing.length) notes.push(`To fill: ${label.missing.map((item) => item.title).join("; ")}.`);
  return {
    className: "batch-label-box",
    blocks,
    notes,
    footer: label.footer,
  };
}

function statementView(statement) {
  const blocks = [];
  if (statement.draft_banner) blocks.push({ tag: "p", className: "batch-banner", text: statement.draft_banner });
  blocks.push({ tag: "h2", text: statement.title });
  blocks.push({ tag: "p", className: "batch-declaration", text: statement.declaration });
  for (const [label, text] of [
    ["Product", statement.product_name],
    ["Lot", statement.lot],
    ["Date", statement.date],
    ["Manufacturer", statement.manufacturer],
    ["Fragrance", statement.fragrance_concentration_text],
  ]) blocks.push({ tag: "p", label: `${label}:`, text });
  blocks.push({ tag: "p", className: "batch-verdict", label: "Verdict:", text: `${statement.verdict}. ${statement.verdict_text}` });
  blocks.push({
    tag: "table",
    head: ["Material or constituent total", "% in finished product", "Category 4 limit", "% of limit"],
    rows: statement.rows.map((row) => [row.detail ? `${row.name}: ${row.detail}` : row.name, row.actual_text, row.limit_text, row.pct_of_limit_text]),
  });
  blocks.push({ tag: "p", className: "batch-small", text: `${statement.basis_text} ${statement.limits_source}` });
  if (statement.failures.length) {
    blocks.push({ tag: "h3", text: "Over the limit or prohibited" });
    blocks.push({ tag: "ul", items: statement.failures.map((item) => item.text) });
  }
  if (statement.open_items.length) {
    blocks.push({ tag: "h3", text: "Open items" });
    blocks.push({ tag: "ul", items: statement.open_items.map((item) => item.text) });
  }
  if (statement.notes.length) {
    blocks.push({ tag: "h3", text: "Notes" });
    blocks.push({ tag: "ul", className: "batch-small", items: statement.notes });
  }
  blocks.push({
    tag: "div", className: "batch-signature",
    children: statement.signature.lines.map((line) => ({
      tag: "p", label: `${line}:`, text: line === "Name" && statement.signature.name ? statement.signature.name : "",
    })),
  });
  return { className: "batch-statement", blocks, notes: [], footer: statement.footer };
}

function renderView(doc, view) {
  function el(tag, className) {
    const element = doc.createElement(tag);
    if (className) element.className = className;
    return element;
  }
  function textInto(element, text) {
    for (const part of fillParts(text)) {
      if (part.fill) {
        const mark = el("mark", "batch-fill");
        mark.textContent = part.text;
        element.append(mark);
      } else {
        element.append(doc.createTextNode(part.text));
      }
    }
  }
  function block(spec) {
    const element = el(spec.tag, spec.className);
    if (spec.lang) element.lang = spec.lang;
    if (spec.label) {
      const strong = el("strong");
      strong.textContent = spec.label;
      element.append(strong, doc.createTextNode(" "));
    }
    if (spec.text !== undefined) textInto(element, spec.text);
    for (const child of spec.children || []) element.append(block(child));
    for (const item of spec.items || []) {
      const li = el("li");
      textInto(li, item);
      element.append(li);
    }
    if (spec.head) {
      const head = el("thead");
      const headRow = el("tr");
      for (const text of spec.head) {
        const th = el("th");
        th.textContent = text;
        headRow.append(th);
      }
      head.append(headRow);
      const body = el("tbody");
      for (const cells of spec.rows) {
        const tr = el("tr");
        for (const text of cells) {
          const td = el("td");
          textInto(td, text);
          tr.append(td);
        }
        body.append(tr);
      }
      element.append(head, body);
    }
    return element;
  }
  const root = el("section", `batch-print ${view.className}`);
  for (const spec of view.blocks) root.append(block(spec));
  if (view.notes.length) root.append(block({ tag: "ul", className: "batch-label-notes", items: view.notes }));
  root.append(block({ tag: "p", className: "batch-footer", text: view.footer }));
  return root;
}

const BATCH_LABEL_INPUTS = [
  ["name", "Product name"],
  ["thai_name", "Name in Thai"],
  ["manufacturer_name", "Manufacturer"],
  ["manufacturer_address", "Address"],
  ["lot", "Lot"],
  ["mfg", "Made (MM/YYYY)"],
  ["exp", "Expires (MM/YYYY, optional)"],
  ["notification_no", "Thai FDA notification no."],
  ["date", "Statement date"],
  ["signatory_name", "Signed by"],
];
const BATCH_TYPES = [
  ["eau_de_parfum", "Eau de Parfum"],
  ["eau_de_toilette", "Eau de Toilette"],
  ["parfum", "Parfum"],
  ["extrait_de_parfum", "Extrait de Parfum"],
  ["eau_de_cologne", "Eau de Cologne"],
];

// Request bodies from the form's values (plain object of strings and booleans).
function batchLabelBody(values, rows) {
  const fields = { type: values.type || "eau_de_parfum", alcohol_denat: Boolean(values.alcohol_denat), declare_carriers: Boolean(values.declare_carriers), include_english: values.include_english !== false };
  for (const key of ["name", "thai_name", "manufacturer_name", "manufacturer_address", "lot", "mfg", "exp", "notification_no"]) {
    const text = String(values[key] || "").trim();
    if (text) fields[key] = text;
  }
  const net = Number(values.net_ml);
  fields.net_ml = Number.isFinite(net) && net > 0 ? net : 30;
  const names = {};
  for (const [raw, inci] of Object.entries(values.carrier_names || {})) if (String(inci).trim()) names[raw] = String(inci).trim();
  if (Object.keys(names).length) fields.carrier_names = names;
  return { fields, rows: rows || [] };
}

function batchStatementBody(values, source) {
  const meta = {};
  const pairs = [["product_name", "name"], ["lot", "lot"], ["date", "date"], ["signatory_name", "signatory_name"], ["manufacturer_name", "manufacturer_name"], ["manufacturer_address", "manufacturer_address"]];
  for (const [key, from] of pairs) {
    const text = String(values[from] || "").trim();
    if (text) meta[key] = text;
  }
  return { ...source, meta };
}

// container: element to fill. fetchFn(path, options) -> Promise of parsed JSON,
// rejecting with an Error on failure (lab.js `request`, base /api/v1/lab).
// Returns { setRows(rows), setGate(source), setFields(values) }; source is
// { gate_json } or { gate_path: "data/user/batches/<lot>/gate.json" }.
function attachBatchLabel(container, fetchFn) {
  const doc = container.ownerDocument;
  let rows = [];
  let gateSource = null;
  const carrierNames = {};
  const node = (tag, props = {}, text) => {
    const element = doc.createElement(tag);
    Object.assign(element, props);
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const inputs = {};
  const form = node("form", { className: "batch-label-controls" });
  for (const [key, title] of BATCH_LABEL_INPUTS) {
    inputs[key] = node("input", { name: key, type: "text" });
    form.append(node("label", {}, title), inputs[key]);
  }
  inputs.net_ml = node("input", { name: "net_ml", type: "number", value: "30", min: "1" });
  form.append(node("label", {}, "Net mL"), inputs.net_ml);
  inputs.type = node("select", { name: "type" });
  for (const [key, title] of BATCH_TYPES) inputs.type.append(node("option", { value: key }, title));
  form.append(node("label", {}, "Type"), inputs.type);
  for (const [key, title, checked] of [["alcohol_denat", "Alcohol Denat.", false], ["declare_carriers", "List carriers", false], ["include_english", "English back", true]]) {
    inputs[key] = node("input", { name: key, type: "checkbox", checked });
    const label = node("label", { className: "check-line" });
    label.append(inputs[key], node("span", {}, title));
    form.append(label);
  }
  const carrierBox = node("div", { className: "batch-carrier-names" });
  const buttons = node("div", { className: "batch-label-buttons" });
  const makeLabel = node("button", { type: "button", className: "primary-button" }, "Make label");
  const makeStatement = node("button", { type: "button", className: "primary-button" }, "Make IFRA statement");
  const printLabel = node("button", { type: "button", className: "quiet-button", disabled: true }, "Print label");
  const printStatement = node("button", { type: "button", className: "quiet-button", disabled: true }, "Print statement");
  buttons.append(makeLabel, makeStatement, printLabel, printStatement);
  const status = node("p", { className: "batch-label-status" });
  status.setAttribute("aria-live", "polite");
  const labelOut = node("div", { className: "batch-label-output" });
  const statementOut = node("div", { className: "batch-statement-output" });
  form.append(carrierBox, buttons, status);
  container.replaceChildren(form, labelOut, statementOut);

  function values() {
    const out = { carrier_names: { ...carrierNames } };
    for (const [key, input] of Object.entries(inputs)) out[key] = input.type === "checkbox" ? input.checked : input.value;
    return out;
  }

  function showCarriers(unknown) {
    carrierBox.replaceChildren();
    for (const raw of unknown) {
      const input = node("input", { type: "text", value: carrierNames[raw] || "", placeholder: "INCI name" });
      input.addEventListener("input", () => { carrierNames[raw] = input.value; });
      carrierBox.append(node("label", {}, `Carrier “${raw}”`), input);
    }
  }

  function printOne(output) {
    const page = output.firstElementChild;
    if (!page) return;
    page.classList.add("batch-print-active");
    doc.body.classList.add("batch-printing");
    try {
      doc.defaultView.print();
    } finally {
      doc.body.classList.remove("batch-printing");
      page.classList.remove("batch-print-active");
    }
  }

  makeLabel.addEventListener("click", async () => {
    status.textContent = "Making the label…";
    try {
      const label = await fetchFn("/commercial-pack/label", { method: "POST", body: JSON.stringify(batchLabelBody(values(), rows)) });
      labelOut.replaceChildren(renderView(doc, labelView(label)));
      showCarriers(label.ingredients.unknown_carriers || []);
      printLabel.disabled = false;
      status.textContent = label.draft ? "Draft: fill the marked fields before printing." : "Label ready.";
    } catch (error) {
      status.textContent = error.message || "Label not made.";
    }
  });
  makeStatement.addEventListener("click", async () => {
    if (!gateSource) {
      status.textContent = "Run the release gate for this batch first.";
      return;
    }
    status.textContent = "Making the IFRA statement…";
    try {
      const statement = await fetchFn("/commercial-pack/ifra-statement", { method: "POST", body: JSON.stringify(batchStatementBody(values(), gateSource)) });
      statementOut.replaceChildren(renderView(doc, statementView(statement)));
      printStatement.disabled = false;
      status.textContent = `IFRA: ${statement.verdict}.`;
    } catch (error) {
      status.textContent = error.message || "Statement not made.";
    }
  });
  printLabel.addEventListener("click", () => printOne(labelOut));
  printStatement.addEventListener("click", () => printOne(statementOut));

  return {
    setRows(next) { rows = Array.isArray(next) ? next : []; },
    setGate(source) { gateSource = source && (source.gate_json || source.gate_path) ? source : null; },
    setFields(next) {
      for (const [key, value] of Object.entries(next || {})) {
        const input = inputs[key];
        if (!input) continue;
        if (input.type === "checkbox") input.checked = Boolean(value);
        else input.value = value ?? "";
      }
    },
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = { BATCH_TO_FILL, fillParts, labelView, statementView, renderView, batchLabelBody, batchStatementBody, attachBatchLabel };
}
