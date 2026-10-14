"use strict";

// Science page: evidence records and their authority.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, boot.

function scienceEvidenceClass(label) {
  return `evidence-${String(label || "UNKNOWN").toLowerCase().replaceAll("_", "-")}`;
}

function scienceRecordCard(record, disposition) {
  const card = document.createElement("article");
  card.className = `science-record science-record-${disposition}`;

  const heading = document.createElement("div");
  heading.className = "science-record-heading";
  const identifier = document.createElement("code");
  identifier.textContent = record.id;
  const badge = document.createElement("span");
  badge.className = `evidence ${scienceEvidenceClass(record.evidence_class)}`;
  badge.dataset.evidenceClass = record.evidence_class;
  badge.textContent = record.evidence_class;
  heading.append(identifier, badge);
  card.append(heading);

  const eligibility = document.createElement("p");
  eligibility.className = "science-eligibility";
  eligibility.textContent = record.strict_eligible
    ? "Strict eligible"
    : "Not strict eligible";
  card.append(eligibility);

  if (record.strict_reason_codes.length) {
    const reasons = document.createElement("ul");
    reasons.className = "science-reasons";
    for (const reason of record.strict_reason_codes) {
      const item = document.createElement("li");
      item.textContent = reason;
      reasons.append(item);
    }
    card.append(reasons);
  }

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Authority, provenance, and facts";
  const payload = document.createElement("pre");
  payload.textContent = JSON.stringify({
    created_at: record.created_at,
    authority: record.authority,
    provenance: record.provenance,
    facts: record.facts,
  }, null, 2);
  details.append(summary, payload);
  card.append(details);
  return card;
}

function scienceRecordGroup(label, records, disposition) {
  const group = document.createElement("section");
  group.className = `science-record-group science-record-group-${disposition}`;
  const heading = document.createElement("h3");
  heading.textContent = `${label} (${records.length})`;
  group.append(heading);
  if (!records.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No records in this partition.";
    group.append(empty);
    return group;
  }
  for (const record of records) {
    group.append(scienceRecordCard(record, disposition));
  }
  return group;
}

function renderScienceAuthority(report) {
  const totals = [
    ["Sections", report.totals.section_count],
    ["Records", report.totals.total_records],
    ["Included", report.totals.included_records],
    ["Withheld", report.totals.withheld_records],
  ];
  const summaryFragment = document.createDocumentFragment();
  for (const [label, value] of totals) {
    const metric = document.createElement("article");
    metric.className = "metric";
    const count = document.createElement("strong");
    count.textContent = value;
    const name = document.createElement("span");
    name.textContent = label;
    metric.append(count, name);
    summaryFragment.append(metric);
  }
  $("#science-summary").replaceChildren(summaryFragment);

  const fragment = document.createDocumentFragment();
  for (const section of report.sections) {
    const panel = document.createElement("article");
    panel.className = "panel science-section";
    const heading = document.createElement("div");
    heading.className = "science-section-heading";
    const title = document.createElement("h2");
    title.textContent = section.label;
    const counts = document.createElement("span");
    counts.textContent = `${section.total_count} total`;
    heading.append(title, counts);
    panel.append(heading);
    panel.append(scienceRecordGroup("Included", section.included, "included"));
    panel.append(scienceRecordGroup("Strict withheld", section.withheld, "withheld"));
    fragment.append(panel);
  }
  const scienceSections = $("#science-sections");
  scienceSections.replaceChildren(fragment);
}

async function loadScienceAuthority() {
  const view = $("#science-view-mode").value;
  const report = await request(`/science/authority?view=${view}`, { timeoutMs: 0 });
  $("#science-json-download").href = `/api/v1/lab/science/authority?view=${view}`;
  $("#science-markdown-download").href = `/api/v1/lab/science/report.md?view=${view}`;
  renderScienceAuthority(report);
  notify(`${report.totals.total_records} science authority records loaded in ${view} view.`);
}

$("#science-view-mode").addEventListener("change", () => {
  loadScienceAuthority().catch((error) => notify(error.message, true));
});
$("#science-refresh").addEventListener("click", () => {
  loadScienceAuthority().catch((error) => notify(error.message, true));
});
