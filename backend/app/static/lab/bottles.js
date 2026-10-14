"use strict";

// Bottles page: bottles, additions and the smell log; also attaches the Batch page (batch.js).
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, bench, bottles, experiments, perfumery, assistant, science, boot.

showMassLimitInline("#bottle-form");
bindForm("#bottle-form", (data) => request("/bottles", { method: "POST", body: JSON.stringify({ label: data.label, initial_mass_g: checkedInitialMassG(data.initial_mass_g) }) }));
// Bottles view: the smell log form (smell-log.js); refresh() hands it the bottle list.
const smellLog = typeof attachSmellLog === "function"
  ? attachSmellLog({ doc: document, request, root: $("#smell-log") })
  : null;
if (typeof attachBatch === "function") attachBatch({ doc: document, request, root: $("#batch-root") });
bindForm("#addition-form", (data) => request(`/bottles/${data.bottle_id}/additions`, { method: "POST", body: JSON.stringify({ stock_solution_id: data.stock_solution_id, mass_g: Number(data.mass_g), expected_sequence: Number(data.expected_sequence), command_id: newRequestId("command") }) }));
