// Browser-saved drafts: the parts that need no page. Every function takes the
// storage object as a parameter, so blocked, full, old or corrupt storage can be
// exercised without a browser. lab.js draws and restores the page around these.
// One versioned key per view. Only what the page shows is kept, plus the stock ids
// a refine needs; server hashes and source paths are never stored.
(function exposeLabDrafts() {
  const DRAFT_VERSION = 1;
  const DRAFT_KEYS = { create: "perfume-lab.draft.create.v1", improve: "perfume-lab.draft.improve.v1" };
  const DRAFT_MAX_CHARS = 1000000;
  const DRAFT_ROW_FIELDS = ["material", "stock_label", "stock_id", "stock_fraction_decimal", "fraction_basis", "carrier", "profile_source", "slot_label", "note", "role", "amount_decimal", "amount_unit", "rationale", "allocation_basis", "operation", "execution_ready"];

  function isTimestamp(value) {
    return typeof value === "string" && !Number.isNaN(Date.parse(value));
  }

  // A stored value is usable only when it is current-version JSON within the size
  // limit with valid timestamps; anything else counts as no draft.
  function parseDraft(raw) {
    if (typeof raw !== "string" || !raw || raw.length > DRAFT_MAX_CHARS) return null;
    let draft;
    try {
      draft = JSON.parse(raw);
    } catch {
      return null;
    }
    if (!draft || typeof draft !== "object" || draft.version !== DRAFT_VERSION) return null;
    if (!isTimestamp(draft.saved_at)) return null;
    if (draft.designed_at != null && !isTimestamp(draft.designed_at)) return null;
    return draft;
  }

  // Identifies one write: which tab wrote it and when.
  function draftStamp(draft) {
    return draft ? `${draft.writer || ""}@${draft.saved_at}` : null;
  }

  function removeDraft(storage, view) {
    try {
      storage.removeItem(DRAFT_KEYS[view]);
    } catch {
      // Blocked storage has nothing to remove.
    }
  }

  // Returns { draft, outcome }: outcome is "none", "restored", "removed" (an
  // unusable value was deleted) or "unavailable" (storage could not be read).
  function readDraft(storage, view) {
    let raw = null;
    try {
      raw = storage.getItem(DRAFT_KEYS[view]);
    } catch {
      return { draft: null, outcome: "unavailable" };
    }
    if (raw == null || raw === "") return { draft: null, outcome: "none" };
    const draft = parseDraft(raw);
    if (draft) return { draft, outcome: "restored" };
    removeDraft(storage, view);
    return { draft: null, outcome: "removed" };
  }

  // Saves body for view unless another tab wrote or discarded since this tab last
  // saw the stored draft (lastSeen is the stamp this tab restored or wrote, or null
  // when it saw none). A stale write is refused so it can neither undo a Discard
  // nor overwrite a newer draft. A body that cannot be kept removes the older draft.
  // Returns { outcome, stamp }: outcome is "saved", "cleared", "stale", "too_large"
  // or "failed"; stamp is what this tab should treat as last seen afterwards.
  function writeDraft(storage, view, body, { writer, lastSeen = null, now = new Date() } = {}) {
    let current;
    try {
      current = draftStamp(parseDraft(storage.getItem(DRAFT_KEYS[view])));
    } catch {
      removeDraft(storage, view);
      return { outcome: "failed", stamp: null };
    }
    if (current !== lastSeen) return { outcome: "stale", stamp: lastSeen };
    if (!body) {
      removeDraft(storage, view);
      return { outcome: "cleared", stamp: null };
    }
    const draft = { version: DRAFT_VERSION, saved_at: now.toISOString(), writer: String(writer || ""), ...body };
    const text = JSON.stringify(draft);
    if (text.length > DRAFT_MAX_CHARS) {
      removeDraft(storage, view);
      return { outcome: "too_large", stamp: null };
    }
    try {
      storage.setItem(DRAFT_KEYS[view], text);
    } catch {
      removeDraft(storage, view);
      return { outcome: "failed", stamp: null };
    }
    return { outcome: "saved", stamp: draftStamp(draft) };
  }

  function pickDraftFields(source, keys) {
    const copy = {};
    if (!source || typeof source !== "object") return copy;
    keys.forEach((key) => { if (source[key] !== undefined) copy[key] = source[key]; });
    return copy;
  }

  function draftFormulaCopy(formula) {
    if (!formula) return null;
    return {
      rows: (formula.rows || []).map((row) => pickDraftFields(row, DRAFT_ROW_FIELDS)),
      separate_totals: pickDraftFields(formula.separate_totals, ["liquid_total_ul", "mass_total_mg"]),
    };
  }

  function draftCriticCopy(critic) {
    return critic ? pickDraftFields(critic, ["state", "issues", "limitations", "strongest_clue"]) : null;
  }

  function draftTemporalCopy(hypothesis) {
    if (!hypothesis) return null;
    return {
      sequence: (hypothesis.sequence || []).map((entry) => ({
        window: entry.window,
        intended_roles: (entry.intended_roles || []).map((role) => ({ role: role.role })),
      })),
    };
  }

  function draftReferenceCopy(context) {
    if (!context) return null;
    return {
      named_products: (context.named_products || []).map((product) => (
        typeof product === "string" ? product : { display_name: product?.display_name }
      )),
      design_criteria: context.design_criteria || [],
    };
  }

  // The fields renderFormulaDesign draws, plus stock ids so a refine can seed from them.
  function draftDisplayCopy(result) {
    const knowledge = result.formulation_knowledge;
    const coverage = result.architecture_planning?.implementation_coverage;
    return {
      ...pickDraftFields(result, ["formula_name", "assistant_message", "concept_family", "requested_material_limit"]),
      draft_copy_note: "Display copy saved in this browser; the full design response was not kept.",
      request_interpretation: { appeal_mode: result.request_interpretation?.appeal_mode },
      composition_plan: result.composition_plan
        ? pickDraftFields(result.composition_plan, ["method", "request_specific_repairs", "roles_filled"])
        : null,
      optimization: result.optimization ? { status: result.optimization.status } : null,
      design_reasoning: (result.design_reasoning || []).map((entry) => ({ pass: entry.pass })),
      critic: draftCriticCopy(result.critic),
      temporal_hypothesis: draftTemporalCopy(result.temporal_hypothesis),
      commercial_reference_context: draftReferenceCopy(result.commercial_reference_context),
      optimized_formula: draftFormulaCopy(result.optimized_formula),
      design_variants: (result.design_variants || []).map((variant) => ({
        label: variant.label,
        formula: draftFormulaCopy(variant.formula),
        critic: draftCriticCopy(variant.critic),
        role_plan: (variant.role_plan || []).map((role) => ({ role_id: role.role_id })),
        architecture: { comparison_question: variant.architecture?.comparison_question },
        temporal_hypothesis: draftTemporalCopy(variant.temporal_hypothesis),
        commercial_reference_context: draftReferenceCopy(variant.commercial_reference_context),
      })),
      architecture_planning: coverage ? {
        implementation_coverage: {
          state: coverage.state,
          items: (coverage.items || []).map((item) => pickDraftFields(item, ["subtype_id", "implementation_state", "required_next"])),
        },
      } : null,
      formulation_knowledge: knowledge ? {
        strongest_clue: knowledge.strongest_clue,
        construction_context: {
          dossiers: (knowledge.construction_context?.dossiers || []).map((dossier) => ({
            title: dossier.title,
            recognizers: dossier.recognizers,
            architectures: (dossier.architectures || []).map((architecture) => ({ intent: architecture.intent })),
            comparison: { question: dossier.comparison?.question },
            negative_space: dossier.negative_space,
          })),
        },
        subtype_context: {
          campaign_identity_holds: (knowledge.subtype_context?.campaign_identity_holds || []).map((hold) => pickDraftFields(hold, ["reason", "question"])),
          cards: (knowledge.subtype_context?.cards || []).map((card) => ({
            ...pickDraftFields(card, ["title", "evidence_summary", "construction_hypothesis", "negative_space", "identity_limits"]),
            comparison: { question: card.comparison?.question },
            review_addenda: (card.review_addenda || []).map((addendum) => pickDraftFields(addendum, ["evidence_summary", "identity_limits"])),
          })),
        },
        sources: (knowledge.sources || []).map((source) => pickDraftFields(source, ["title", "evidence_class", "url"])),
        prior_references: (knowledge.prior_references || []).map((reference) => pickDraftFields(reference, ["title", "state"])),
      } : null,
    };
  }

  // File name and status message for Download draft. A restored draft is the
  // trimmed browser copy, so it must not be named or announced like a server result.
  function draftDownload(result, restored) {
    const slug = String(result?.formula_name || "formula-draft").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "formula-draft";
    if (restored) {
      return {
        filename: `${slug}-restored-browser-copy.json`,
        message: "Downloaded the trimmed browser copy of a restored draft, not the full server result.",
      };
    }
    return { filename: `${slug}.json`, message: "Read-only formula draft downloaded." };
  }

  const api = {
    DRAFT_VERSION, DRAFT_KEYS, DRAFT_MAX_CHARS, DRAFT_ROW_FIELDS,
    parseDraft, draftStamp, readDraft, removeDraft, writeDraft, draftDisplayCopy, draftDownload,
  };
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof window === "object") window.LabDrafts = api;
}());
