// "Add a dilution" on the Stock page. Kenny (2026-10-09): a dilution he makes
// and saves here counts at the release gate with no code change, and every
// freshly prepared stock is in DPG, so DPG and w/w are the defaults.
//
// The page loads this before lab.js, which calls attachStockDilutions once.
// Material names and server messages go in through textContent only, never
// HTML strings. Node loads the same file in the tests through module.exports.

const DILUTION_ENDPOINT = "/v2/workbench/current-inventory/dilute";

function dilutionRequestBody(stock, fields, expectedSha, idempotencyKey) {
  const text = (value) => String(value ?? "").trim();
  return {
    schema_version: "prepared-dilution-request-v1",
    parent_stock_id: stock.stock_id,
    expected_effective_inventory_sha256: expectedSha,
    idempotency_key: idempotencyKey,
    fraction_percent_decimal: text(fields.fraction_percent_decimal),
    fraction_basis: fields.fraction_basis === "volume_fraction" ? "volume_fraction" : "mass_fraction",
    carrier: text(fields.carrier),
    amount_made_g: text(fields.amount_made_g) || null,
    prepared_on: text(fields.prepared_on) || null,
    user_note: text(fields.user_note),
  };
}

function dilutionNode(doc, tag, attributes = {}, text = "") {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

function dilutionInput(doc, fields, name, labelText, attributes, value = "") {
  const label = dilutionNode(doc, "label", {}, labelText);
  const input = dilutionNode(doc, "input", { name, ...attributes });
  input.value = value;
  label.appendChild(input);
  fields[name] = input;
  return label;
}

const MIX_BASIS_WORDS = { mass_fraction: "w/w", volume_fraction: "v/v" };

// The plain-words mix for a new strength n (percent) from a parent of strength
// p (percent): 1 part parent + (p/n - 1) parts carrier. "" when not computable.
function dilutionMixText(stock, newPercent, basis, carrier) {
  const p = Number(String(stock.fraction_percent_decimal ?? "").trim());
  const raw = String(newPercent ?? "").trim();
  const n = raw === "" ? NaN : Number(raw);
  if (!Number.isFinite(p) || !Number.isFinite(n) || !(n > 0) || !(p > n)) return "";
  // The server refuses a basis that differs from a non-neat parent's, so no mix is shown.
  if (p !== 100 && basis !== stock.fraction_basis) return "";
  const parts = Math.round((p / n - 1) * 100) / 100;
  const base = stock.identity_name || stock.material || "parent";
  const parentBasis = MIX_BASIS_WORDS[stock.fraction_basis];
  const name = p === 100 ? base : `${base} ${p}%${parentBasis ? ` ${parentBasis}` : ""}`;
  const by = basis === "volume_fraction" ? "by volume" : "by weight";
  const carrierName = String(carrier ?? "").trim() || "carrier";
  return `Mix 1 part ${name} + ${parts} parts ${carrierName} ${by}`;
}

function buildDilutionForm(doc, stock) {
  const fields = {};
  const form = dilutionNode(doc, "form", { class: "form-panel inventory-completion-form stock-dilution-form" });
  const parentText = `From your ${stock.fraction_percent_decimal}% ${stock.fraction_basis || ""} stock`
    + (stock.carrier ? ` in ${stock.carrier}` : "") + ". The bottle you diluted from is not changed.";
  form.appendChild(dilutionNode(doc, "p", { class: "field-help" }, parentText));

  const strength = dilutionNode(doc, "div", { class: "field-pair" });
  strength.appendChild(dilutionInput(doc, fields, "fraction_percent_decimal", "Strength of the material in the new bottle, %", {
    inputmode: "decimal", pattern: "[0-9]+(\\.[0-9]+)?", required: "",
  }));
  const basisLabel = dilutionNode(doc, "label", {}, "How that percentage is defined");
  const basis = dilutionNode(doc, "select", { name: "fraction_basis" });
  basis.appendChild(dilutionNode(doc, "option", { value: "mass_fraction" }, "w/w — mass fraction"));
  basis.appendChild(dilutionNode(doc, "option", { value: "volume_fraction" }, "v/v — volume fraction"));
  basis.value = "mass_fraction";
  basisLabel.appendChild(basis);
  fields.fraction_basis = basis;
  strength.appendChild(basisLabel);
  form.appendChild(strength);
  const mix = dilutionNode(doc, "p", { class: "field-help stock-dilution-mix" });
  mix.hidden = true;
  form.appendChild(mix);

  const made = dilutionNode(doc, "div", { class: "field-pair" });
  made.appendChild(dilutionInput(doc, fields, "carrier", "Carrier", { maxlength: "120", required: "" }, "DPG"));
  made.appendChild(dilutionInput(doc, fields, "amount_made_g", "Amount made, g (optional)", {
    inputmode: "decimal", pattern: "[0-9]+(\\.[0-9]+)?",
  }));
  form.appendChild(made);
  form.appendChild(dilutionInput(doc, fields, "prepared_on", "Date made (optional)", { type: "date" }));
  form.appendChild(dilutionInput(doc, fields, "user_note", "Optional note", { maxlength: "1000" }));

  const error = dilutionNode(doc, "p", { class: "status-line is-error", role: "alert" });
  error.hidden = true;
  form.appendChild(error);
  const actions = dilutionNode(doc, "div", { class: "request-actions" });
  const submit = dilutionNode(doc, "button", { type: "submit" }, "Save this dilution");
  const cancel = dilutionNode(doc, "button", { type: "button", class: "quiet-button" }, "Cancel");
  actions.appendChild(submit);
  actions.appendChild(cancel);
  form.appendChild(actions);
  const updateMix = () => {
    const text = dilutionMixText(stock, fields.fraction_percent_decimal.value, fields.fraction_basis.value, fields.carrier.value);
    mix.textContent = text;
    mix.hidden = !text;
  };
  for (const name of ["fraction_percent_decimal", "fraction_basis", "carrier"]) {
    fields[name].addEventListener("input", updateMix);
    fields[name].addEventListener("change", updateMix);
  }
  form.dilutionParts = { fields, error, submit, cancel, mix, updateMix };
  return form;
}

function showDilutionError(form, message) {
  const { error } = form.dilutionParts;
  error.textContent = message;
  error.hidden = !message;
}

// Posts the form once and reports the outcome. Returns the server result, or
// null after showing the refusal inline.
async function submitDilutionForm(form, { stock, expectedSha, idempotencyKey, request }) {
  const { fields, submit } = form.dilutionParts;
  const values = Object.fromEntries(Object.entries(fields).map(([name, node]) => [name, node.value]));
  showDilutionError(form, "");
  submit.disabled = true;
  try {
    const result = await request(DILUTION_ENDPOINT, {
      method: "POST",
      body: JSON.stringify(dilutionRequestBody(stock, values, expectedSha, idempotencyKey)),
    });
    if (result && result.prepared_stock_id === null) {
      showDilutionError(form, "Saved, but this dilution doesn't count as a stock yet: its parent bottle changed or is held. Check the parent bottle on the Stock page.");
      return null;
    }
    return result;
  } catch (error) {
    showDilutionError(form, error.message || "The dilution was not saved.");
    return null;
  } finally {
    submit.disabled = false;
  }
}

function attachStockDilutions({ doc, list, getInventory, request, onSaved, newKey }) {
  const panel = dilutionNode(doc, "article", { id: "stock-dilution-panel", class: "panel inventory-completion-panel" });
  panel.hidden = true;
  (list.closest("article") || list).after(panel);

  function close() {
    panel.hidden = true;
    panel.replaceChildren();
  }

  function open(stock) {
    const heading = dilutionNode(doc, "div", { class: "card-title-row" });
    const title = dilutionNode(doc, "div");
    title.appendChild(dilutionNode(doc, "p", { class: "panel-index" }, "Add a dilution"));
    title.appendChild(dilutionNode(doc, "h2", {}, stock.identity_name || stock.material));
    heading.appendChild(title);
    const form = buildDilutionForm(doc, stock);
    const idempotencyKey = newKey();
    form.dilutionParts.cancel.addEventListener("click", close);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = await submitDilutionForm(form, {
        stock,
        expectedSha: getInventory().canonical_effective_inventory_sha256,
        idempotencyKey,
        request,
      });
      if (!result) return;
      close();
      onSaved(result);
    });
    panel.replaceChildren(heading, form);
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    form.dilutionParts.fields.fraction_percent_decimal.focus();
  }

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-dilute-stock]");
    if (!button) return;
    const stock = (getInventory().stocks || []).find((item) => item.stock_id === button.dataset.diluteStock);
    if (stock) open(stock);
  });
}

if (typeof module === "object" && module.exports) {
  module.exports = { DILUTION_ENDPOINT, dilutionMixText, dilutionRequestBody, buildDilutionForm, showDilutionError, submitDilutionForm, attachStockDilutions };
}
