"use strict";

// Bottles page: bottles, additions and the smell log; also attaches the Batch page (batch.js)
// and the Your nose page (smell-log.js and blind-test.js).
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

showMassLimitInline("#bottle-form");
bindForm("#bottle-form", (data) => request("/bottles", { method: "POST", body: JSON.stringify({ label: data.label, initial_mass_g: checkedInitialMassG(data.initial_mass_g) }) }));
// Bottles view: the smell log form (smell-log.js); refresh() hands it the bottle list.
const smellLog = typeof attachSmellLog === "function"
  ? attachSmellLog({ doc: document, request, root: $("#smell-log") })
  : null;
if (typeof attachBatch === "function") attachBatch({ doc: document, request, root: $("#batch-root") });
if (typeof attachPhoneBench === "function") attachPhoneBench({ doc: document, request, root: $("#phone-bench-root") });
bindForm("#addition-form", (data) => request(`/bottles/${data.bottle_id}/additions`, { method: "POST", body: JSON.stringify({ stock_solution_id: data.stock_solution_id, mass_g: Number(data.mass_g), expected_sequence: Number(data.expected_sequence), command_id: newRequestId("command") }) }));
// Your nose page: what the model learned from the smell log, and blind tests.
const noseLearning = typeof attachNoseLearning === "function"
  ? attachNoseLearning({ doc: document, request, root: $("#nose-learning") })
  : null;
const blindTest = typeof attachBlindTest === "function"
  ? attachBlindTest({
    doc: document,
    request,
    root: $("#blind-test"),
    rowText: (saved) => {
      const [row] = editorRowsFromSaved([saved]);
      const amount = row.amount ? benchFractionText(row.amount, 1) : "?";
      return [row.material, editorStrengthText(row), row.solid ? `${amount} mg` : `${amount} µL`].filter(Boolean).join(" · ");
    },
    toBench: (title, saved) => sendRowsToBench(title, editorRowsFromSaved(saved)),
  })
  : null;
// Loaded when the page is opened (navigate in core.js), so it shows the latest logs and saves.
function noseShown() {
  noseLearning?.show();
  blindTest?.show();
}
