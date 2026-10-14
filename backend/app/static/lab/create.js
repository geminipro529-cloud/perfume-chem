"use strict";

// Create page (Formulas): the formula chat, create several, saved drafts, formula records and versions.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, bench, bottles, experiments, perfumery, assistant, science, boot.

// Inventory-grounded formulation conversation ----------------------------
function appendFormulaChatBubble(kind, text) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${kind === "user" ? "user-bubble" : "assistant-bubble"}`;
  const label = document.createElement("strong");
  label.textContent = kind === "user" ? "You" : "Perfumer";
  const message = document.createElement("p");
  message.textContent = text;
  bubble.append(label, message);
  $("#formula-chat-log").append(bubble);
  state.formulaChat.turns.push({ kind: kind === "user" ? "user" : "assistant", text });
  bubble.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function addFormulaResultSummary(list, label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  wrapper.append(term, detail);
  list.append(wrapper);
}

function selectedFormulaVariant(result, variantIndex = state.formulaChat.variantIndex || 0) {
  const variants = result?.design_variants || [];
  const variant = variants[variantIndex] || variants[0] || null;
  const critic = variant?.critic || result?.critic || null;
  return {
    variant,
    formula: critic?.state === "WITHHELD" ? null : (variant ? variant.formula : result?.optimized_formula) || null,
    critic,
  };
}

function renderCompositionChecks(compositionChecks) {
  const box = $("#formula-result-checks");
  const summary = typeof compositionCheckLines === "function" ? compositionCheckLines(compositionChecks) : null;
  box.replaceChildren();
  box.hidden = !summary;
  if (!summary) return;
  box.className = summary.flagged ? "formula-result-checks inline-warning" : "formula-result-checks";
  const list = document.createElement("ul");
  summary.lines.forEach((line) => {
    const item = document.createElement("li");
    item.dataset.status = line.status;
    item.textContent = line.text;
    list.append(item);
  });
  box.append(list);
  if (summary.basis) {
    const basis = document.createElement("small");
    basis.textContent = summary.basis;
    box.append(basis);
  }
}

function renderDetectionCheck(detectionCheck) {
  const box = $("#formula-result-detection");
  const summary = typeof detectionCheckLines === "function" ? detectionCheckLines(detectionCheck) : null;
  box.replaceChildren();
  box.hidden = !summary;
  if (!summary) return;
  box.className = summary.flagged ? "formula-result-checks inline-warning" : "formula-result-checks";
  const list = document.createElement("ul");
  summary.lines.forEach((line) => {
    const item = document.createElement("li");
    item.dataset.status = line.status;
    item.textContent = line.text;
    list.append(item);
  });
  box.append(list);
  if (summary.note) {
    const note = document.createElement("small");
    note.textContent = summary.note;
    box.append(note);
  }
}

function renderFormulaVoices(complexitySummary) {
  const box = $("#formula-result-voices");
  const summary = typeof formulaVoiceLines === "function" ? formulaVoiceLines(complexitySummary) : null;
  box.replaceChildren();
  box.hidden = !summary || (!summary.lines.length && !summary.note);
  if (box.hidden) return;
  const list = document.createElement("ul");
  summary.lines.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    list.append(item);
  });
  box.append(list);
  if (summary.note) {
    const note = document.createElement("small");
    note.textContent = summary.note;
    box.append(note);
  }
}

// With basket data in the inventory payload the rows follow Kenny's basket
// order (benchBasketOrder in bench-sheet.js) under one heading per basket;
// without it they keep the design order. Doses are never changed.
function renderFormulaRows(rows) {
  let group = null;
  // scent-chart.js is optional: without it the rationale shows unchanged.
  const hasScent = typeof scentWhyText === "function" && typeof scentChartRows === "function" && typeof scentCurveCache !== "undefined";
  const curve = hasScent ? scentCurveCache.get(JSON.stringify(scentChartRows(rows))) : null;
  $("#formula-result-rows").innerHTML = rows.length
    ? benchBasketOrder(rows, benchBasketLookup(state.projectInventory)).map((entry) => {
      const row = entry.row;
      let heading = "";
      if (entry.group && entry.group !== group) {
        group = entry.group;
        heading = `<tr class="formula-basket-row"><th colspan="4" scope="colgroup">${escapeHtml(entry.heading)}${entry.check ? ' <small class="formula-basket-check">check it: from past cards</small>' : ""}</th></tr>`;
      }
      const fraction = `${formatDecimal(Number(row.stock_fraction_decimal) * 100, 4)}%`;
      const carrier = row.carrier ? ` in ${row.carrier}` : "";
      const proxy = row.profile_source === "HEURISTIC_CATEGORY_PROXY" ? '<small class="proxy-label">category proxy</small>' : "";
      const basketTag = entry.basket !== null ? `<small class="formula-basket-tag">Basket ${escapeHtml(entry.basket)}</small>`
        : entry.group === "unassigned" ? '<small class="formula-basket-tag">No basket</small>' : "";
      const basis = benchBasisText(row.fraction_basis);
      const stockLabel = row.stock_label || `${fraction} ${basis}${carrier}`;
      const why = hasScent ? scentWhyText(row.rationale, row, curve) : String(row.rationale || "");
      const mix = benchNeedsPreparedDilution(row) ? benchMixRecipe(row) : null;
      const doseNote = mix ? `<small class="formula-dose-mix">${escapeHtml(benchMixShortText(mix, row.amount_unit))}</small>`
        : benchNeedsPreparedDilution(row) ? '<small class="formula-dose-hold">prepare dilution first</small>' : "";
      return `${heading}<tr>
        <td><strong>${escapeHtml(row.material)}</strong>${basketTag}${proxy}${why ? `<small class="formula-why">${escapeHtml(why)}</small>` : ""}</td>
        <td class="formula-dose">${escapeHtml(row.amount_decimal)} ${escapeHtml(row.amount_unit)}${doseNote}</td>
        <td>${escapeHtml(stockLabel)}<small>${escapeHtml(fraction)} ${escapeHtml(basis)}${escapeHtml(carrier)}</small></td>
        <td>${escapeHtml(row.slot_label)}<small>${escapeHtml(row.note)} · ${escapeHtml(row.role)}</small></td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="4">Clarify the brief before a formula can be created.</td></tr>';
}

function renderFormulaDesign(result, variantIndex = 0) {
  state.formulaChat.result = result;
  state.formulaChat.variantIndex = variantIndex;
  const card = $("#formula-chat-result");
  card.hidden = false;
  $("#formula-result-name").textContent = result.formula_name || "Formula draft";
  const selected = selectedFormulaVariant(result, variantIndex);
  const hasFormula = Boolean(selected.formula);
  $("#formula-result-state").textContent = hasFormula
    ? benchSheetHold(selected.formula?.rows || [], selected.critic).stateText
    : "Needs clarification";
  $("#formula-result-summary").textContent = result.assistant_message || "No formula was generated.";
  const picker = $("#formula-variant-picker");
  const variants = result.design_variants || [];
  picker.hidden = variants.length <= 1;
  $("#formula-result-variant").textContent = variants.length > 1
    ? `Alternative shown: ${variants[variantIndex]?.label || `Alternative ${variantIndex + 1}`}`
    : "";
  picker.replaceChildren();
  variants.forEach((variant, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = index === variantIndex ? "is-active" : "";
    button.textContent = variant.label || `Alternative ${index + 1}`;
    button.addEventListener("click", () => {
      renderFormulaDesign(result, index);
      scheduleDraftSave("create");
    });
    picker.append(button);
  });
  renderCompositionChecks(selected.variant ? selected.variant.composition_checks : result.composition_checks);
  renderDetectionCheck((selected.variant ? selected.formula : (selected.formula || result.initial_formula))?.detection_check);
  renderFormulaVoices(selected.variant ? selected.variant.complexity_summary : result.complexity_summary);
  if (typeof renderFormulaLiking === "function") renderFormulaLiking(result, variantIndex, selected);
  const rows = selected.formula?.rows || [];
  // Once the curve is cached the rows pick up their modelled shares.
  (typeof renderScentChart === "function" ? renderScentChart($("#formula-result-scent"), rows) : Promise.resolve()).then(() => {
    if (state.formulaChat.result === result && state.formulaChat.variantIndex === variantIndex) renderFormulaRows(rows);
  });
  renderFormulaRows(rows);

  const totals = $("#formula-result-totals");
  totals.replaceChildren();
  if (selected.formula) {
    addFormulaResultSummary(totals, "Liquid stock total", `${selected.formula.separate_totals.liquid_total_ul} µL`);
    addFormulaResultSummary(totals, "Solid total", `${selected.formula.separate_totals.mass_total_mg} mg`);
    addFormulaResultSummary(totals, "Structure", String(result.concept_family || "concept").replaceAll("_", " "));
    addFormulaResultSummary(totals, "Planning method", String(result.composition_plan?.method || result.optimization?.status || "not run").replaceAll("_", " ").toLowerCase());
    addFormulaResultSummary(totals, "Rows used", `${rows.length} of at most ${result.requested_material_limit || rows.length}`);
  }

  const detail = $("#formula-result-detail");
  detail.replaceChildren();
  const repairLabels = (result.composition_plan?.request_specific_repairs || [])
    .map((value) => String(value).replaceAll("_", " ").toLowerCase());
  const temporalSequence = (selected.variant?.temporal_hypothesis || result.temporal_hypothesis)?.sequence || [];
  const referenceContext = selected.variant?.commercial_reference_context || result.commercial_reference_context;
  const referenceProducts = (referenceContext?.named_products || [])
    .map((product) => typeof product === "string" ? product : product.display_name)
    .filter(Boolean);
  const referenceCriteria = referenceContext?.design_criteria || [];
  const usesStrengthCompensation = rows.some(
    (row) => row.allocation_basis === "STOCK_STRENGTH_COMPENSATED_HEURISTIC_NOT_ACTIVE_MASS",
  );
  const reasoningPasses = (result.design_reasoning || [])
    .map((entry) => String(entry.pass || "").replaceAll("_", " ").toLowerCase())
    .filter(Boolean);
  const paragraphs = [
    selected.critic?.strongest_clue
      ? `Strongest composition clue: ${selected.critic.strongest_clue}`
      : "No composition clue was generated because the request needs clarification.",
    result.composition_plan
      ? `The planner filled ${selected.variant?.role_plan?.length ?? result.composition_plan.roles_filled?.length ?? 0} nonredundant roles and stopped under the material ceiling. Ingredient count was not an objective.`
      : "No structural plan ran because a hard request constraint was unresolved.",
    selected.critic?.issues?.length
      ? `Practical hold: ${String(selected.critic.issues[0]).replaceAll("_", " ").toLowerCase()}. Expand details only if you need to resolve it before compounding.`
      : selected.critic?.limitations?.length
        ? `Evidence limit: ${String(selected.critic.limitations[0]).replaceAll("_", " ").toLowerCase()}. The formula is still usable as a bench hypothesis.`
        : "Practical hold: none detected in the design inputs. This is still not sensory or safety validation.",
    "Unknown until smelled: pleasantness, personal liking, mixture interactions, and whether this is actually better than an unchanged control.",
    "No inventory, formula file, bottle, or laboratory record was changed.",
  ];
  if (selected.variant?.architecture?.comparison_question) {
    paragraphs.splice(1, 0,
      `Architecture comparison: ${selected.variant.architecture.comparison_question} This is an untested role-plan hypothesis, not a measured improvement.`);
  }
  if (repairLabels.length) {
    paragraphs.splice(2, 0, `Request-specific adaptation: ${repairLabels.join("; ")}.`);
  }
  if (temporalSequence.length) {
    const timing = temporalSequence.map((entry) => {
      const windowLabel = String(entry.window || "requested window").replaceAll("_", " ").toLowerCase();
      const roles = (entry.intended_roles || []).map((role) => role.role).filter(Boolean).join(", ");
      return `${windowLabel}: ${roles || "role hypothesis"}`;
    }).join("; ");
    paragraphs.splice(-2, 0, `Timing map (hypothesis only): ${timing}. Smell or measure the pilot at those windows before accepting it.`);
  }
  if (referenceProducts.length) {
    paragraphs.splice(-2, 0, `Commercial references: ${referenceProducts.join("; ")}. Their marketed facets were used only as documentary contrasts; no proprietary formula, sensory similarity, or liking was inferred.`);
  } else if (referenceCriteria.length) {
    paragraphs.splice(-2, 0, `Prestige comparison criteria: ${referenceCriteria.join(", ")}. No unrelated bestseller was borrowed, and these request-derived criteria are not a liking label.`);
  } else if (result.request_interpretation?.appeal_mode === "GLOBAL_CROWD_PLEASING") {
    paragraphs.splice(-2, 0, "Commercial comparison was requested, but no applicable named reference panel was available; market alignment and population liking remain withheld.");
  }
  if (usesStrengthCompensation) {
    paragraphs.splice(-2, 0, "Dose reconciliation used a bounded stock-strength compensation heuristic so diluted stocks were not treated like neat materials. It is not an active-mass or sensory-equivalence claim; exact active mass remains withheld wherever basis or density is incomplete.");
  }
  if (reasoningPasses.length) {
    paragraphs.splice(-2, 0, `Design audit trail: ${reasoningPasses.join(" → ")}.`);
  }
  paragraphs.forEach((text) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    detail.append(paragraph);
  });
  const knowledge = result.formulation_knowledge;
  if (knowledge) {
    const evidence = document.createElement("details");
    evidence.className = "formulation-knowledge";
    const heading = document.createElement("summary");
    heading.textContent = "Research behind this design · optional details";
    evidence.append(heading);
    const scope = document.createElement("p");
    scope.textContent = knowledge.strongest_clue || "Local literature knowledge is unavailable for this request.";
    evidence.append(scope);
    const limit = document.createElement("p");
    limit.textContent = "Source-supported descriptions and formulation hypotheses are separate. These references do not supply measured doses, liking scores or safety approval.";
    evidence.append(limit);
    const coverage = result.architecture_planning?.implementation_coverage;
    if (coverage) {
      const coverageDetails = document.createElement("details");
      const coverageHeading = document.createElement("summary");
      coverageHeading.textContent = "Coverage and remaining prerequisites";
      coverageDetails.append(coverageHeading);
      (coverage.items || []).forEach((item) => {
        const line = document.createElement("p");
        line.textContent = `${item.subtype_id}: ${String(item.implementation_state).replaceAll("_", " ").toLowerCase()}. ${item.required_next}`;
        coverageDetails.append(line);
      });
      if (coverage.state === "WITHHOLD_UNKNOWN") {
        const unavailable = document.createElement("p");
        unavailable.textContent = "The reviewed coverage record is unavailable; no completeness claim is made.";
        coverageDetails.append(unavailable);
      }
      evidence.append(coverageDetails);
    }
    (knowledge.construction_context?.dossiers || []).forEach((dossier) => {
      const section = document.createElement("section");
      const title = document.createElement("h4");
      title.textContent = `${dossier.title} · untested construction options`;
      section.append(title);
      const recognizer = document.createElement("p");
      recognizer.textContent = (dossier.recognizers || []).join(" ");
      section.append(recognizer);
      (dossier.architectures || []).forEach((architecture, index) => {
        const option = document.createElement("p");
        option.textContent = `${index === 0 ? "Control" : "Alternative"}: ${architecture.intent}`;
        section.append(option);
      });
      const comparison = document.createElement("p");
      comparison.textContent = `Question to resolve: ${dossier.comparison?.question || "No supported comparison question."} Avoid: ${(dossier.negative_space || []).join(" ")}`;
      section.append(comparison);
      evidence.append(section);
    });
    (knowledge.subtype_context?.campaign_identity_holds || []).forEach((hold) => {
      const note = document.createElement("p");
      note.textContent = `Reference identity unresolved: ${hold.reason} ${hold.question}`;
      evidence.append(note);
    });
    (knowledge.subtype_context?.cards || []).forEach((card) => {
      const section = document.createElement("section");
      const title = document.createElement("h4");
      title.textContent = `${card.title} · subtype research hypothesis`;
      section.append(title);
      const fact = document.createElement("p");
      fact.textContent = `Evidence: ${card.evidence_summary}`;
      section.append(fact);
      const hypothesis = document.createElement("p");
      hypothesis.textContent = `Design hypothesis: ${card.construction_hypothesis}`;
      section.append(hypothesis);
      const comparison = document.createElement("p");
      comparison.textContent = `Question to resolve: ${card.comparison?.question} Avoid: ${(card.negative_space || []).join("; ")}`;
      section.append(comparison);
      const boundary = document.createElement("p");
      boundary.textContent = `Limits: ${(card.identity_limits || []).join(" ")}`;
      section.append(boundary);
      (card.review_addenda || []).forEach((addendum) => {
        const update = document.createElement("p");
        update.textContent = `Deeper source review: ${addendum.evidence_summary} Limits: ${(addendum.identity_limits || []).join(" ")}`;
        section.append(update);
      });
      evidence.append(section);
    });
    (knowledge.sources || []).forEach((source) => {
      const paragraph = document.createElement("p");
      const label = `${source.title} · ${String(source.evidence_class).replaceAll("_", " ").toLowerCase()}`;
      let sourceURL = null;
      if (typeof source.url === "string") {
        try {
          const parsed = new URL(source.url);
          if (parsed.protocol === "https:" && !parsed.username && !parsed.password) {
            sourceURL = parsed.href;
          }
        } catch {
          // An unavailable/malformed reference remains plain text.
        }
      }
      if (sourceURL) {
        const link = document.createElement("a");
        link.textContent = label;
        link.href = sourceURL;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        paragraph.append(link);
      } else {
        paragraph.textContent = label;
      }
      evidence.append(paragraph);
    });
    (knowledge.prior_references || []).forEach((reference) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = `${reference.title} · prior local reference only · ${reference.state}`;
      evidence.append(paragraph);
    });
    detail.append(evidence);
  }
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetFormulaChat(announce = true) {
  state.formulaChat = { messages: [], result: null, variantIndex: 0, turns: [], designedAt: null, restored: false };
  discardStoredDraft("create");
  const form = $("#formula-chat-form");
  form.reset();
  $('[name="liquid_concentrate_ul_decimal"]', form).value = "6000";
  $('[name="max_materials"]', form).value = "60";
  $('[name="design_mode"]', form).value = "FAST_SKETCH";
  $("#formula-chat-log").innerHTML = '<div class="chat-bubble assistant-bubble"><strong>Perfumer</strong><p>Tell me the name or feeling of the perfume you want to make. I will use your inventory, honor hard constraints first, and stop before filler.</p></div>';
  $("#formula-chat-result").hidden = true;
  $("#formula-chat-submit").textContent = "Create my formula";
  if (announce) notify("Ready for a new perfume idea.");
}

$("#formula-chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formData(form);
  const message = String(data.message || "").trim();
  const previous = state.formulaChat.result;
  const priorMessages = state.formulaChat.messages.slice(-8);
  const previousRows = selectedFormulaVariant(previous).formula?.rows || [];
  appendFormulaChatBubble("user", message);
  const pushedAt = state.formulaChat.messages.push(message) - 1;
  const submit = $("#formula-chat-submit");
  submit.disabled = true;
  submit.textContent = previous ? "Refining…" : "Creating…";
  try {
    const designMode = String(data.design_mode || "FAST_SKETCH");
    const payload = {
      message,
      formula_name: data.formula_name || previous?.formula_name || null,
      liquid_concentrate_ul_decimal: String(data.liquid_concentrate_ul_decimal || "6000"),
      max_materials: Number(data.max_materials || 60),
      must_preserve: splitList(data.must_preserve),
      must_avoid: splitList(data.must_avoid),
      previous_stock_ids: previousRows.map((row) => row.stock_id),
      conversation_context: priorMessages,
      design_mode: designMode,
      variant_count: designMode === "DEEP_COMPOSE" ? 3 : 1,
    };
    let result;
    if (designMode === "DEEP_COMPOSE") {
      submit.textContent = "Composing alternatives…";
      const submitted = await request("/v2/engine-jobs", {
        method: "POST",
        body: JSON.stringify({
          schema_version: "lab-engine-job-request-v2",
          job_type: "FORMULA_DESIGN",
          requester: "formula-studio-ui",
          idempotency_key: newRequestId("job"),
          payload,
        }),
      });
      const jobArea = $("#formula-chat-job-status");
      jobArea.hidden = false;
      let completed;
      try {
        completed = await waitForEngineJob(submitted.id, {
          area: jobArea,
          intervalMs: 600,
          stillRunningMessage: "Deep Compose is still running; its durable job remains available without resubmitting.",
        });
      } finally {
        if (!jobArea.childElementCount) jobArea.hidden = true;
      }
      result = completed.result?.result?.result?.formula_design;
      if (!result) throw new Error(completed.events?.at(-1)?.reason || `Deep Compose ended as ${completed.state}.`);
    } else {
      result = await request("/v2/workbench/formula-chat", {
        method: "POST",
        body: JSON.stringify({
          schema_version: "inventory-grounded-formula-chat-request-v2",
          ...payload,
        }),
        timeoutMs: 0,
      });
    }
    appendFormulaChatBubble("assistant", result.assistant_message || "The brief needs clarification before I can create the formula.");
    renderFormulaDesign(result);
    state.formulaChat.restored = false;
    hideDraftRestoredLine("create");
    if (result.formula_name) $('[name="formula_name"]', form).value = result.formula_name;
    $('[name="message"]', form).value = "";
    submit.textContent = result.optimized_formula ? "Refine this formula" : "Try clarified brief";
    notify(result.optimized_formula ? "Inventory-grounded composition plan created." : "Clarification required before formulation.");
  } catch (error) {
    // A failed brief must not ride along as conversation_context on every later request.
    // A Deep compose job that is only still running may yet finish, so its brief stays.
    if (!error.jobStillRunning && state.formulaChat.messages[pushedAt] === message) state.formulaChat.messages.splice(pushedAt, 1);
    appendFormulaChatBubble("assistant", `I could not create that draft: ${error.message}`);
    submit.textContent = previous ? "Refine this formula" : "Create my formula";
    notify(error.message, true);
  } finally {
    submit.disabled = false;
    if (state.formulaChat.result !== previous) state.formulaChat.designedAt = new Date().toISOString();
    saveDraftNow("create");
  }
});

$("#formula-chat-reset").addEventListener("click", () => resetFormulaChat());

// Create several: one engine job per idea (create-several.js holds the pure rules).
const several = { cards: [], skipped: "" };

function updateSeveralStatus(elapsed = "") {
  $("#several-status").textContent = severalStatusText(
    several.cards.map((card) => card.state),
    { elapsed, skipped: several.skipped },
  );
}

function severalTickedCards() {
  return several.cards.filter((card) => card.result && card.checkbox.checked);
}

function updateSeveralCompareButton() {
  const ticked = severalTickedCards().length;
  $("#several-compare-button").disabled = ticked !== 2;
  $("#several-own-compare").disabled = ticked !== 1 || !$("#several-own-text").value.trim();
}

// A table with a header row and one row per material, all as text.
function severalTable(headers, rows) {
  const table = document.createElement("table");
  table.className = "several-compare-table";
  const head = document.createElement("tr");
  for (const label of headers) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    head.append(cell);
  }
  const thead = document.createElement("thead");
  thead.append(head);
  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const line = document.createElement("tr");
    line.className = row.shared ? "is-shared" : "is-single";
    for (const value of row.cells) {
      const cell = document.createElement("td");
      cell.textContent = value;
      line.append(cell);
    }
    tbody.append(line);
  }
  table.append(thead, tbody);
  return table;
}

function showSeveralCompare(...children) {
  const area = $("#several-compare");
  area.hidden = false;
  area.replaceChildren(...children);
  area.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function severalCardShell(brief, jobRequest) {
  const element = document.createElement("article");
  element.className = "several-card";
  const head = document.createElement("div");
  head.className = "several-card-head";
  const title = document.createElement("h3");
  title.textContent = brief;
  const pick = document.createElement("label");
  pick.className = "several-pick";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.disabled = true;
  checkbox.addEventListener("change", updateSeveralCompareButton);
  pick.append(checkbox, document.createTextNode(" Compare"));
  head.append(title, pick);
  const progress = document.createElement("div");
  progress.className = "engine-job-status";
  const body = document.createElement("div");
  body.className = "several-card-body";
  element.append(head, progress, body);
  $("#several-cards").append(element);
  // jobRequest keeps its idempotency key, so sending it again finds the same job.
  const card = { brief, jobRequest, jobId: null, state: "COMPOSING", element, checkbox, progress, body, result: null };
  several.cards.push(card);
  return card;
}

// Submits the card's job unless the server already gave it an id, then polls it.
async function composeSeveralCard(card) {
  card.state = "COMPOSING";
  try {
    if (!card.jobId) {
      const submitted = await request("/v2/engine-jobs", { method: "POST", body: JSON.stringify(card.jobRequest) });
      card.jobId = submitted.id;
    }
    const completed = await waitForEngineJob(card.jobId, {
      area: card.progress,
      intervalMs: severalPollIntervalMs(several.cards.length),
      stillRunningMessage: "still composing after the job's time limit",
    });
    const result = completed.result?.result?.result?.formula_design;
    if (!result) {
      const ended = new Error(completed.events?.at(-1)?.reason || `the job ended as ${completed.state}`);
      ended.jobEnded = true;
      throw ended;
    }
    fillSeveralCard(card, result);
    card.state = "DONE";
  } catch (error) {
    card.state = severalCanCheckAgain(error) ? "WAITING" : "FAILED";
    failSeveralCard(card, error.message);
  }
}

// target: a part of the studio's result to scroll to, such as its rating card;
// the result itself when that part is missing or hidden.
function scrollToStudioPart(target) {
  const part = $(target);
  (part && part.getClientRects().length ? part : $("#formula-chat-result")).scrollIntoView({ behavior: "smooth", block: "start" });
}

function openSeveralInStudio(card, target = "#formula-chat-result") {
  const result = card.result;
  if (state.formulaChat.result === result) {
    // Already open: keep the conversation and any rating not yet saved, and show
    // the card's own formula (the first alternative) if another one is selected.
    if ((state.formulaChat.variantIndex || 0) !== 0) renderFormulaDesign(result, 0);
    scrollToStudioPart(target);
    return;
  }
  resetFormulaChat(false);
  state.formulaChat.messages.push(card.brief);
  appendFormulaChatBubble("user", card.brief);
  appendFormulaChatBubble("assistant", result.assistant_message || "Here is the formula from Create several.");
  renderFormulaDesign(result);
  state.formulaChat.designedAt = new Date().toISOString();
  const form = $("#formula-chat-form");
  if (result.formula_name) $('[name="formula_name"]', form).value = result.formula_name;
  $("#formula-chat-submit").textContent = "Refine this formula";
  scheduleDraftSave("create");
  scrollToStudioPart(target);
  notify(`${result.formula_name || "The formula"} is open in the studio.`);
}

// The studio keeps one formula; replacing a different one takes a second click.
function severalStudioButton(card, label, target) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "quiet-button";
  button.textContent = label;
  button.addEventListener("click", () => {
    const current = state.formulaChat.result;
    if (current && current !== card.result && button.dataset.confirm !== "1") {
      button.dataset.confirm = "1";
      button.textContent = "Replace the studio's formula?";
      return;
    }
    delete button.dataset.confirm;
    button.textContent = label;
    openSeveralInStudio(card, target);
  });
  return button;
}

function fillSeveralCard(card, result) {
  card.result = result;
  const summary = severalCardSummary(result);
  card.progress.replaceChildren();
  const name = document.createElement("p");
  name.className = "several-name";
  name.textContent = summary.name;
  const facts = document.createElement("p");
  facts.className = "field-help";
  const more = summary.alternatives
    ? ` · ${summary.alternatives} more alternative${summary.alternatives === 1 ? "" : "s"} in the studio`
    : "";
  facts.textContent = summary.hasFormula
    ? `${summary.materials} materials · ${summary.totalUl.toLocaleString()} µL${more}`
    : "No formula yet";
  const chips = document.createElement("ul");
  chips.className = "several-floors";
  chips.setAttribute("aria-label", "Floors");
  for (const chip of severalFloorChips(result)) {
    const item = document.createElement("li");
    item.className = `several-floor status-${chip.status.toLowerCase()}`;
    item.textContent = `${chip.label} ${chip.status === "PASS" ? "✓" : chip.status.toLowerCase()}`;
    chips.append(item);
  }
  const lines = document.createElement("ul");
  lines.className = "several-lines";
  for (const line of summary.lines) {
    const item = document.createElement("li");
    item.className = `several-line status-${String(line.status || "info").toLowerCase()}`;
    item.textContent = line.text;
    lines.append(item);
  }
  const actions = document.createElement("div");
  actions.className = "request-actions";
  if (summary.hasFormula) {
    const bench = document.createElement("button");
    bench.type = "button";
    bench.className = "quiet-button";
    bench.textContent = "Bench sheet";
    bench.addEventListener("click", () => printBenchSheet(result, 0));
    actions.append(
      severalStudioButton(card, "Open in the studio"),
      bench,
      // The studio's rating card links each rating to this formula's materials.
      severalStudioButton(card, "Mixed it? Rate it", "#formula-result-liking .liking-rate"),
    );
    card.checkbox.disabled = false;
  }
  card.body.replaceChildren(name, facts, ...(chips.childElementCount ? [chips] : []), lines, actions);
}

function failSeveralCard(card, message) {
  card.progress.replaceChildren();
  const text = document.createElement("p");
  if (card.state !== "WAITING") {
    text.className = "several-line status-fail";
    text.textContent = `Not composed: ${message}`;
    card.body.replaceChildren(text);
    return;
  }
  text.className = "several-line status-hold";
  text.textContent = `Not collected yet: ${message}`;
  const actions = document.createElement("div");
  actions.className = "request-actions";
  const again = document.createElement("button");
  again.type = "button";
  again.className = "quiet-button";
  again.textContent = "Check again";
  again.addEventListener("click", async () => {
    again.disabled = true;
    card.body.replaceChildren();
    await composeSeveralCard(card);
    // A new batch replaces the cards; this one then no longer counts.
    if (several.cards.includes(card)) updateSeveralStatus();
  });
  actions.append(again);
  card.body.replaceChildren(text, actions);
}

$("#several-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = formData(form);
  const status = $("#several-status");
  const { briefs, repeated, over } = parseSeveralBriefs(data.briefs);
  if (!briefs.length) {
    status.textContent = "Write at least one idea, one per line.";
    return;
  }
  const submit = $("#several-submit");
  submit.disabled = true;
  several.cards = [];
  $("#several-cards").replaceChildren();
  const compare = $("#several-compare");
  compare.hidden = true;
  compare.replaceChildren();
  updateSeveralCompareButton();
  several.skipped = [
    repeated ? `${repeated} repeated` : "",
    over ? `${over} over the limit of ${SEVERAL_MAX_BRIEFS}` : "",
  ].filter(Boolean).join(" and ");
  const startedAt = Date.now();
  const plural = briefs.length === 1 ? "" : "s";
  status.textContent = `Composing ${briefs.length} perfume${plural}.${several.skipped ? ` Skipped ${several.skipped}.` : ""}`;
  const cards = briefs.map((brief) => severalCardShell(brief, severalJobRequest(brief, data.several_mode, newRequestId("job"), {
    liquid_concentrate_ul_decimal: data.liquid_concentrate_ul_decimal,
  })));
  await Promise.all(cards.map(async (card) => {
    await composeSeveralCard(card);
    if (several.cards.includes(card)) updateSeveralStatus();
  }));
  if (cards.every((card) => several.cards.includes(card))) updateSeveralStatus(formatElapsed(Date.now() - startedAt));
  submit.disabled = false;
  notify(`Create several finished: ${briefs.length} idea${plural}.`);
});

$("#several-compare-button").addEventListener("click", () => {
  const [first, second] = severalTickedCards();
  if (!first || !second) return;
  const nameOf = (card) => card.result.formula_name || card.brief;
  const rows = severalCompareRows(first.result, second.result);
  const amount = (value, unit) => (value ? `${value.toLocaleString()} ${unit}` : "—");
  const table = severalTable(
    ["Material", nameOf(first), nameOf(second)],
    rows.map((row) => ({ shared: row.shared, cells: [row.material, amount(row.a, row.unit), amount(row.b, row.unit)] })),
  );
  const shared = rows.filter((row) => row.shared).length;
  const heading = document.createElement("p");
  heading.className = "field-help";
  heading.textContent = `${shared} material${shared === 1 ? "" : "s"} in both, ${rows.length - shared} in only one.`;
  showSeveralCompare(heading, table);
});

// One of Kenny's own bench cards beside the ticked card, in active amounts. The pasted
// text goes only to this app's read-only parser and is kept nowhere.
$("#several-own-text").addEventListener("input", updateSeveralCompareButton);
$("#several-own-compare").addEventListener("click", async () => {
  const [card] = severalTickedCards();
  const text = $("#several-own-text").value;
  const status = $("#several-own-status");
  if (!card || !text.trim()) return;
  const button = $("#several-own-compare");
  button.disabled = true;
  status.textContent = "Reading your card…";
  try {
    const own = await request("/v2/workbench/formula-text", { method: "POST", body: JSON.stringify({ text }) });
    const compared = severalOwnCompare(card.result, own);
    const amount = (value, unit) => (value ? `${value.toLocaleString()} ${unit}` : "—");
    const table = severalTable(
      ["Material", card.result.formula_name || card.brief, own.formula_name || "Your card"],
      compared.rows.map((row) => ({ shared: row.shared, cells: [row.material, amount(row.a, row.unit), amount(row.b, row.unit)] })),
    );
    const heading = document.createElement("p");
    heading.className = "field-help";
    heading.textContent = `${compared.inBoth} in both, ${compared.onlyHere} only in this card, ${compared.onlyYours} only in yours. `
      + "Amounts are active material: each pour times its strength, without densities, so they are approximate.";
    const children = [heading, table];
    if (compared.unread.length) {
      const unread = document.createElement("p");
      unread.className = "several-line status-hold";
      unread.textContent = `Strength not read, so left out: ${compared.unread.join(", ")}.`;
      children.push(unread);
    }
    showSeveralCompare(...children);
    status.textContent = "";
  } catch (error) {
    status.textContent = `Could not read your card: ${error.message}`;
  } finally {
    updateSeveralCompareButton();
  }
});

$("#formula-download").addEventListener("click", () => {
  const result = state.formulaChat.result;
  if (!result) return;
  const { filename, message } = Drafts.draftDownload(result, state.formulaChat.restored);
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
  notify(message);
});

// Browser-saved drafts ---------------------------------------------------
// Storage rules live in lab-drafts.js (window.LabDrafts); this part draws the page.
// A tab saves only over the draft it last saw (its writer id and saved_at), so a
// stale tab can neither undo a Discard made elsewhere nor overwrite a newer draft.
const Drafts = window.LabDrafts;
const CREATE_DRAFT_FIELDS = ["formula_name", "liquid_concentrate_ul_decimal", "message", "must_preserve", "must_avoid", "max_materials", "design_mode"];
const CREATE_DRAFT_TYPED_FIELDS = ["formula_name", "message", "must_preserve", "must_avoid"];
const DRAFT_WRITER = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
const DRAFT_UNSAVED_TEXT = {
  failed: "This draft couldn't be kept in this browser (storage is blocked or full), so it won't come back after a reload.",
  too_large: "This draft is too large to keep in this browser, so it won't come back after a reload.",
  stale: "Changes in this tab aren't being kept: the saved draft was changed or discarded in another tab. Reload to continue from the saved draft.",
};
const draftSaveTimers = {};
const draftLastSeen = { create: null, improve: null };

function draftStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function createDraftBody() {
  const form = $("#formula-chat-form");
  const fields = {};
  CREATE_DRAFT_FIELDS.forEach((name) => { fields[name] = String($(`[name="${name}"]`, form)?.value ?? ""); });
  const chat = state.formulaChat;
  const typed = CREATE_DRAFT_TYPED_FIELDS.some((name) => fields[name].trim());
  if (!chat.result && !chat.turns.length && !typed) return null;
  return {
    fields,
    turns: chat.turns,
    messages: chat.messages,
    variant_index: chat.variantIndex,
    designed_at: chat.result ? chat.designedAt : null,
    result: chat.result ? Drafts.draftDisplayCopy(chat.result) : null,
  };
}

function improveDraftBody() {
  const goal = $('#improve-form [name="goal"]').value;
  return goal.trim() ? { fields: { goal } } : null;
}

function showDraftSaveOutcome(view, outcome) {
  const note = $(view === "create" ? "#formula-draft-unsaved" : "#improve-draft-unsaved");
  note.textContent = DRAFT_UNSAVED_TEXT[outcome] || "";
  note.hidden = !DRAFT_UNSAVED_TEXT[outcome];
}

function saveDraftNow(view) {
  window.clearTimeout(draftSaveTimers[view]);
  delete draftSaveTimers[view];
  const options = { writer: DRAFT_WRITER, lastSeen: draftLastSeen[view] };
  let saved;
  try {
    saved = Drafts.writeDraft(draftStorage(), view, view === "create" ? createDraftBody() : improveDraftBody(), options);
  } catch {
    // The page state could not be copied; drop the older draft so it cannot come back.
    saved = Drafts.writeDraft(draftStorage(), view, null, options);
    if (saved.outcome === "cleared") saved.outcome = "failed";
  }
  draftLastSeen[view] = saved.stamp;
  showDraftSaveOutcome(view, saved.outcome);
}

function scheduleDraftSave(view) {
  window.clearTimeout(draftSaveTimers[view]);
  draftSaveTimers[view] = window.setTimeout(() => saveDraftNow(view), 400);
}

function discardStoredDraft(view) {
  window.clearTimeout(draftSaveTimers[view]);
  delete draftSaveTimers[view];
  Drafts.removeDraft(draftStorage(), view);
  draftLastSeen[view] = null;
  hideDraftRestoredLine(view);
  showDraftSaveOutcome(view, null);
}

function draftRestoredLine(view) {
  return $(view === "create" ? "#formula-draft-restored" : "#improve-draft-restored");
}

function hideDraftRestoredLine(view) {
  const line = draftRestoredLine(view);
  if (line) line.hidden = true;
}

function formatDraftTime(iso) {
  const saved = new Date(iso);
  const time = saved.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (saved.toDateString() === new Date().toDateString()) return time;
  return `${saved.toLocaleDateString([], { day: "numeric", month: "short" })}, ${time}`;
}

function showDraftRestoredLine(view, iso, text) {
  const line = draftRestoredLine(view);
  $("[data-draft-restored-text]", line).textContent = `Restored your draft from ${formatDraftTime(iso)}. ${text}`;
  line.hidden = false;
}

function restoreCreateDraft() {
  const { draft } = Drafts.readDraft(draftStorage(), "create");
  if (!draft) return;
  draftLastSeen.create = Drafts.draftStamp(draft);
  try {
    const form = $("#formula-chat-form");
    const fields = draft.fields && typeof draft.fields === "object" ? draft.fields : {};
    CREATE_DRAFT_FIELDS.forEach((name) => {
      const node = $(`[name="${name}"]`, form);
      const value = fields[name];
      if (!node || typeof value !== "string") return;
      if (node.tagName === "SELECT" && ![...node.options].some((option) => option.value === value)) return;
      node.value = value;
    });
    state.formulaChat.messages = Array.isArray(draft.messages) ? draft.messages.filter((message) => typeof message === "string") : [];
    (Array.isArray(draft.turns) ? draft.turns : []).forEach((turn) => {
      if (turn && typeof turn.text === "string") appendFormulaChatBubble(turn.kind === "user" ? "user" : "assistant", turn.text);
    });
    const result = draft.result && typeof draft.result === "object" ? draft.result : null;
    const line = draftRestoredLine("create");
    if (result) {
      const variantCount = Array.isArray(result.design_variants) ? result.design_variants.length : 0;
      const variantIndex = Number.isInteger(draft.variant_index) && draft.variant_index >= 0 && draft.variant_index < Math.max(variantCount, 1)
        ? draft.variant_index
        : 0;
      state.formulaChat.designedAt = draft.designed_at || null;
      renderFormulaDesign(result, variantIndex);
      state.formulaChat.restored = true;
      $("#formula-chat-submit").textContent = result.optimized_formula ? "Refine this formula" : "Try clarified brief";
      $("#formula-result-summary").before(line);
      showDraftRestoredLine("create", state.formulaChat.designedAt || draft.saved_at,
        "This is a copy saved in this browser, made from your inventory at that time; refining plans again from current stock.");
    } else {
      form.before(line);
      showDraftRestoredLine("create", draft.saved_at, "Your typed brief was saved in this browser.");
    }
  } catch (error) {
    console.info(`A saved create draft could not be shown and was removed: ${error.message}`);
    resetFormulaChat(false);
  }
}

function restoreImproveDraft() {
  const { draft } = Drafts.readDraft(draftStorage(), "improve");
  const goal = draft?.fields?.goal;
  if (typeof goal !== "string" || !goal.trim()) {
    if (draft) Drafts.removeDraft(draftStorage(), "improve");
    return;
  }
  draftLastSeen.improve = Drafts.draftStamp(draft);
  $('#improve-form [name="goal"]').value = goal;
  showDraftRestoredLine("improve", draft.saved_at, "Your typed change was saved in this browser. Choose the formula or bottle again before you run it.");
}

function restoreStoredDrafts() {
  restoreCreateDraft();
  restoreImproveDraft();
}

$("#formula-chat-form").addEventListener("input", () => scheduleDraftSave("create"));
$("#formula-chat-form").addEventListener("change", () => scheduleDraftSave("create"));
$('#improve-form [name="goal"]').addEventListener("input", () => scheduleDraftSave("improve"));
$$("[data-discard-draft]").forEach((button) => {
  button.addEventListener("click", () => {
    const view = button.dataset.discardDraft;
    if (view === "create") resetFormulaChat();
    else $('#improve-form [name="goal"]').value = "";
    discardStoredDraft(view);
    notify("Saved draft discarded.");
  });
});
window.addEventListener("pagehide", () => {
  Object.keys(draftSaveTimers).forEach((view) => saveDraftNow(view));
});

// The sheet's arithmetic and markup live in bench-sheet.js (pure, node-tested).
function buildBenchSheet(result, variantIndex) {
  const selected = selectedFormulaVariant(result, variantIndex);
  const rows = selected.formula?.rows || [];
  const variants = result.design_variants || [];
  $("#bench-sheet").innerHTML = benchSheetHtml({
    formulaName: result.formula_name,
    variantLabel: variants.length > 1 ? (variants[variantIndex]?.label || `Alternative ${variantIndex + 1}`) : "",
    dateText: new Date().toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }),
    totals: selected.formula?.separate_totals || {},
    rows,
    critic: selected.critic,
    basketLookup: benchBasketLookup(state.projectInventory),
  });
  return rows.length;
}

function printBenchSheet(result, variantIndex) {
  if (!buildBenchSheet(result, variantIndex)) {
    notify("There is no formula to print yet. Clarify the brief first.", true);
    return;
  }
  document.body.classList.add("printing-bench-sheet");
  window.addEventListener("afterprint", () => document.body.classList.remove("printing-bench-sheet"), { once: true });
  window.print();
}

$("#formula-print-bench").addEventListener("click", () => {
  const result = state.formulaChat.result;
  if (!result) return;
  printBenchSheet(result, state.formulaChat.variantIndex || 0);
});
bindForm("#formula-form", (data) => request("/formulas", { method: "POST", body: JSON.stringify(data) }));

function componentRows() {
  const rows = $$('[data-component-row]', $("#component-editor"));
  if (!rows.length) throw new Error("Add at least one stock component.");
  return rows.map((row) => {
    const stock = $('[name="component_stock"]', row).value;
    const mass = Number($('[name="component_mass_g"]', row).value);
    const volumeValue = $('[name="component_volume_ul"]', row).value;
    const volume = volumeValue ? Number(volumeValue) : null;
    if (!stock || !Number.isFinite(mass) || mass <= 0) {
      throw new Error("Every component needs a stock and a positive mass.");
    }
    if (volume !== null && (!Number.isFinite(volume) || volume <= 0)) {
      throw new Error("Component volume must be blank or a positive number.");
    }
    return {
      stock_solution_id: stock,
      requested_mass_g: mass,
      requested_volume_ul: volume,
      role: $('[name="component_role"]', row).value || null,
      unit: "g",
    };
  });
}

$("#add-component-row").addEventListener("click", () => {
  const source = $('[data-component-row]', $("#component-editor"));
  const row = source.cloneNode(true);
  $('[name="component_mass_g"]', row).value = "0.1";
  $('[name="component_volume_ul"]', row).value = "";
  $('[name="component_role"]', row).value = "";
  $("#component-editor").append(row);
  const stockSelect = $('[name="component_stock"]', row);
  stockSelect.innerHTML = stockOptionRows();
  stockSelect.selectedIndex = 0;
});

$("#component-editor").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-component]");
  if (!button) return;
  const rows = $$('[data-component-row]', $("#component-editor"));
  if (rows.length === 1) {
    notify("A formula version needs at least one component.", true);
    return;
  }
  button.closest("[data-component-row]").remove();
});

$("#version-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = formData(event.currentTarget);
  try {
    await request(`/formulas/${data.formula_id}/versions`, {
      method: "POST",
      body: JSON.stringify({
        brief: { identity: data.identity },
        constraints: { must_preserve: ["identity"] },
        concentration_fraction: Number(data.concentration_fraction),
        concentration_basis: "mass_fraction",
        components: componentRows(),
      }),
    });
    notify("Immutable formula version committed.");
    await refresh();
  } catch (error) { notify(error.message, true); }
});

bindSavingForm("#analysis-form", async (data, form, saved) => {
  const result = await request("/analysis", { method: "POST", body: JSON.stringify({ name: data.name, total_volume_ml: 10, concentration_percent: 20, ingredients: [{ name: data.material, percentage: 100, stock_active_fraction: 1, stock_fraction_basis: "volume_fraction" }] }), timeoutMs: 0 });
  saved();
  $("#analysis-output").textContent = JSON.stringify(result, null, 2); notify("Evidence analysis complete.");
});
