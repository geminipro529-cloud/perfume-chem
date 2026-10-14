"use strict";

// Assistant page.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

bindSavingForm("#assistant-form", async (data, form, saved) => {
  const packet = await request("/assistant", { method: "POST", body: JSON.stringify({ intent: data.intent, subject_id: data.subject_id || null, facts: {}, calculations: {}, evidence: {} }) });
  saved();
  $("#assistant-output").textContent = JSON.stringify(packet, null, 2);
  renderAssistantSummary(packet);
  notify("Answer ready.");
});

function renderAssistantSummary(packet) {
  const list = $("#assistant-summary");
  list.replaceChildren();
  const add = (label, value) => {
    const item = document.createElement("li");
    const text = Array.isArray(value) ? value.join("; ") : value;
    item.textContent = `${label}: ${text === null || text === undefined || text === "" ? "not known yet" : text}`;
    list.append(item);
  };
  const count = (obj) => (obj && typeof obj === "object" ? Object.keys(obj).length : 0);
  add("Question", String(packet.intent || "").replaceAll("_", " "));
  add("Subject", packet.subject_id);
  add("Result", packet.status === "needs_input" ? "needs more information" : packet.status);
  add("Next step", packet.next_action);
  add("Facts found", count(packet.facts) ? `${count(packet.facts)} item(s)` : null);
  add("Calculations", count(packet.calculations) ? `${count(packet.calculations)} item(s)` : null);
  add("Limits", packet.limitations && packet.limitations.length ? packet.limitations : null);
}
