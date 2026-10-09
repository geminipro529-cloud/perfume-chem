// The Lab formula card's pleasantness and rating block: the crowd guess per
// window, Kenny's "Rate this bottle" rows, the A/B pick and "Your nose so far".
// The wording helpers touch no DOM, so node runs them in the tests. The page
// loads this file before lab.js; renderFormulaLiking runs later, from
// renderFormulaDesign, and uses lab.js's request(). Every name, label and typed
// text goes in with textContent, never as HTML.

const LIKING_API = "/api/v1/feedback";
const LIKING_WINDOWS = [["opening", "Opening"], ["1h", "1 hour"], ["4h", "4 hours"]];
const LIKING_SOURCE = "lab_card";

function likingTimeLabel(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "Opening";
  if (value < 3600) return `${Math.round(value / 60)} min`;
  const hours = value / 3600;
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)} h`;
}

function likingScore(pleasantness) {
  if (pleasantness === null || pleasantness === undefined || pleasantness === "") return null;
  const value = Number(pleasantness);
  return Number.isFinite(value) ? Math.round((value + 1) * 50) : null;
}

function likingPercent(coverage) {
  const value = Number(coverage);
  return Number.isFinite(value) ? Math.round(value * 100) : 0;
}

function likingWindowText(window) {
  const when = likingTimeLabel(window.t_seconds);
  const percent = likingPercent(window.coverage);
  const score = window.score_0_100 === null || window.score_0_100 === undefined || !Number.isFinite(Number(window.score_0_100))
    ? null : `${Math.round(Number(window.score_0_100))}/100`;
  let text;
  if (window.status === "CROWD_GUESS" && score) {
    text = `${when}: ${score} (${percent}% of what you'd smell has a crowd value)`;
  } else if (window.status === "NO_DETECTABLE_MATERIALS") {
    text = `${when}: nothing is expected to be smellable yet`;
  } else if (window.status === "NO_RATED_MATERIALS" || !score) {
    text = `${when}: none of what you'd smell has a crowd value, so there is no guess`;
  } else {
    text = `${when}: only ${percent}% of what you'd smell has a crowd value, so ${score} is a weak guess`;
  }
  const names = (Array.isArray(window.contributors) ? window.contributors : [])
    .map((contributor) => String(contributor?.material || "")).filter(Boolean);
  if (names.length) text += ` · led by ${names.join(", ")}`;
  return text;
}

// Lines for one formula's scientific_overlays.pleasantness.
function pleasantnessLines(overlay) {
  if (!overlay || typeof overlay !== "object") return null;
  const label = String(overlay.label || "");
  if (overlay.state === "ERROR") {
    return { lines: [`No crowd guess: ${String(overlay.reason || "the estimate could not run")}`], label };
  }
  const windows = (Array.isArray(overlay.windows) ? overlay.windows : []).filter((window) => window && typeof window === "object");
  if (!windows.length) return { lines: ["No crowd guess for this formula."], label };
  return { lines: windows.map(likingWindowText), label };
}

// The main formula and each Deep Compose variant that has rows.
function likingFormulaChoices(result) {
  const choices = [];
  const baseName = String(result?.formula_name || "Formula draft");
  const main = result?.optimized_formula || result?.initial_formula;
  if (Array.isArray(main?.rows) && main.rows.length) {
    choices.push({ variantIndex: null, label: "Main formula", formulaName: baseName, rows: main.rows, overlay: result?.scientific_overlays?.pleasantness || null });
  }
  (Array.isArray(result?.design_variants) ? result.design_variants : []).forEach((variant, index) => {
    const rows = variant?.formula?.rows;
    if (!Array.isArray(rows) || !rows.length) return;
    const label = String(variant.label || `Alternative ${index + 1}`);
    choices.push({ variantIndex: index, label, formulaName: `${baseName} · ${label}`, rows, overlay: variant?.scientific_overlays?.pleasantness || null });
  });
  return choices;
}

function variantPleasantnessLines(choices) {
  return choices.filter((choice) => choice.variantIndex !== null).map((choice) => {
    const score = likingScore(choice.overlay?.overall);
    return score === null
      ? `${choice.label}: no overall crowd guess (too little of it has a crowd value)`
      : `${choice.label}: about ${score}/100 overall`;
  });
}

// One canonical text per formula: material, amount, unit and stock fraction of
// every row, sorted, so the same bottle always gets the same key.
function likingCanonicalRows(rows) {
  const texts = (Array.isArray(rows) ? rows : []).map((row) => JSON.stringify({
    amount: String(row?.amount_decimal ?? ""),
    material: String(row?.material ?? ""),
    stock_fraction: String(row?.stock_fraction_decimal ?? ""),
    unit: String(row?.amount_unit ?? ""),
  })).sort();
  return `[${texts.join(",")}]`;
}

async function likingFormulaKey(rows) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error("This browser can't make the bottle's key on this page. Open the app at http://localhost to save ratings.");
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(likingCanonicalRows(rows)));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

// Whether a rating at this window can be tied to the formula's materials.
function likingRatingLink(overlay, windowKey) {
  const cannot = "so this card can't link a rating to its materials.";
  if (!overlay || typeof overlay !== "object") return { ok: false, reason: `This formula has no crowd-guess report, ${cannot}` };
  if (overlay.state === "ERROR") return { ok: false, reason: `The crowd-guess estimate didn't run, ${cannot}` };
  if (!overlay.rating_windows || typeof overlay.rating_windows !== "object") {
    return { ok: false, reason: `This report has no material shares per rating time, ${cannot} Compose the formula again to get them.` };
  }
  const entry = overlay.rating_windows[windowKey];
  const shares = entry && typeof entry.material_shares === "object" && entry.material_shares ? entry.material_shares : {};
  if (!Object.values(shares).some((share) => Number(share) > 0)) {
    return { ok: false, reason: "Nothing is expected to be smellable at this time, so there is nothing to link a rating to." };
  }
  const crowd = entry.crowd_guess === null || entry.crowd_guess === undefined || !Number.isFinite(Number(entry.crowd_guess))
    ? null : Number(entry.crowd_guess);
  return { ok: true, shares: { ...shares }, crowd };
}

function likingOptionalText(value) {
  const text = String(value ?? "").trim();
  return text || null;
}

function likingRatingBody({ formulaName, formulaKey, windowKey, liking, complexity, tooLoud, note, link }) {
  return {
    formula_name: String(formulaName).slice(0, 255),
    formula_key: formulaKey,
    window: windowKey,
    liking: Number(liking),
    complexity: complexity ? Number(complexity) : null,
    too_loud: likingOptionalText(tooLoud),
    note: likingOptionalText(note),
    material_shares: link.shares,
    crowd_guess: link.crowd,
    source: LIKING_SOURCE,
  };
}

function likingPickBody({ windowKey, a, b, preferred, note }) {
  return {
    window: windowKey,
    formula_a_name: String(a.formulaName).slice(0, 255),
    formula_a_key: a.key,
    shares_a: a.link.shares,
    crowd_a: a.link.crowd,
    formula_b_name: String(b.formulaName).slice(0, 255),
    formula_b_key: b.key,
    shares_b: b.link.shares,
    crowd_b: b.link.crowd,
    preferred,
    note: likingOptionalText(note),
  };
}

// -- DOM -------------------------------------------------------------------

function likingEl(tag, className = "", text = null) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== null) node.textContent = text;
  return node;
}

function likingField(labelText, control) {
  const label = likingEl("label", "liking-field");
  label.append(likingEl("span", "", labelText), control);
  return label;
}

function likingSaveControls() {
  const save = likingEl("button", "liking-save", "Save");
  save.type = "button";
  const status = likingEl("span", "liking-status");
  status.setAttribute("role", "status");
  const undo = likingEl("button", "liking-undo", "Undo");
  undo.type = "button";
  undo.hidden = true;
  return { save, status, undo };
}

function likingCrowdBlock(choices, current) {
  const block = likingEl("div", "liking-crowd");
  block.append(likingEl("h3", "", "Pleasantness, crowd guess"));
  const summary = pleasantnessLines(current.overlay) || { lines: ["No crowd guess for this formula."], label: "" };
  const list = likingEl("ul", "liking-windows");
  summary.lines.forEach((text) => list.append(likingEl("li", "", text)));
  block.append(list);
  const variants = variantPleasantnessLines(choices);
  if (variants.length) {
    block.append(likingEl("p", "liking-subhead", "Alternatives"));
    const variantList = likingEl("ul", "liking-variants");
    variants.forEach((text) => variantList.append(likingEl("li", "", text)));
    block.append(variantList);
  }
  if (summary.label) block.append(likingEl("small", "", summary.label));
  return block;
}

function likingRatingRow(choice, windowKey, windowLabel) {
  const row = likingEl("div", "liking-row");
  row.dataset.window = windowKey;
  row.append(likingEl("h4", "", windowLabel));
  const link = likingRatingLink(choice.overlay, windowKey);
  let liking = null;
  let savedId = null;
  let saving = false;
  const { save, status, undo } = likingSaveControls();
  const scale = likingEl("div", "liking-scale");
  scale.setAttribute("role", "group");
  scale.setAttribute("aria-label", `How much you like it at ${windowLabel.toLowerCase()}, 1 to 10`);
  const updateSave = () => { save.disabled = !link.ok || liking === null || saving; };
  for (let value = 1; value <= 10; value += 1) {
    const button = likingEl("button", "", String(value));
    button.type = "button";
    button.dataset.liking = String(value);
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      liking = value;
      [...scale.children].forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
      updateSave();
    });
    scale.append(button);
  }
  const complexity = likingEl("select");
  complexity.name = "complexity";
  complexity.append(likingEl("option", "", "Not rated"));
  complexity.options[0].value = "";
  for (let value = 1; value <= 10; value += 1) {
    const option = likingEl("option", "", String(value));
    option.value = String(value);
    complexity.append(option);
  }
  const tooLoud = likingEl("input");
  tooLoud.type = "text";
  tooLoud.name = "too_loud";
  tooLoud.placeholder = "What was too loud, if anything";
  const note = likingEl("input");
  note.type = "text";
  note.name = "note";
  note.placeholder = "Anything else";
  const fields = likingEl("div", "liking-fields");
  fields.append(
    likingField("Complexity (optional)", complexity),
    likingField("Too loud", tooLoud),
    likingField("Note", note),
  );
  row.append(likingEl("p", "liking-hint", "How much do you like it? 1 = not at all, 10 = love it"), scale, fields);
  if (!link.ok) row.append(likingEl("p", "inline-warning", link.reason));
  save.addEventListener("click", async () => {
    saving = true;
    updateSave();
    status.textContent = "Saving…";
    try {
      const formulaKey = await likingFormulaKey(choice.rows);
      const body = likingRatingBody({
        formulaName: choice.formulaName, formulaKey, windowKey, liking,
        complexity: complexity.value, tooLoud: tooLoud.value, note: note.value, link,
      });
      const saved = await request("/liking/ratings", { method: "POST", base: LIKING_API, body: JSON.stringify(body) });
      savedId = saved?.id ?? null;
      status.textContent = "Saved";
      undo.hidden = savedId === null;
    } catch (error) {
      status.textContent = `Not saved: ${error.message}`;
    } finally {
      saving = false;
      updateSave();
    }
  });
  undo.addEventListener("click", async () => {
    if (savedId === null) return;
    undo.disabled = true;
    try {
      await request(`/liking/ratings/${encodeURIComponent(savedId)}`, { method: "DELETE", base: LIKING_API });
      savedId = null;
      undo.hidden = true;
      status.textContent = "Removed";
    } catch (error) {
      status.textContent = `Not removed: ${error.message}`;
    } finally {
      undo.disabled = false;
    }
  });
  const actions = likingEl("div", "liking-actions");
  actions.append(save, status, undo);
  row.append(actions);
  updateSave();
  return row;
}

function likingSelect(name, options, selectedIndex) {
  const select = likingEl("select");
  select.name = name;
  options.forEach(([value, text], index) => {
    const option = likingEl("option", "", text);
    option.value = value;
    option.selected = index === selectedIndex;
    select.append(option);
  });
  return select;
}

function likingPickBlock(choices) {
  const block = likingEl("div", "liking-pick");
  block.append(likingEl("h3", "", "Which did you prefer?"));
  block.append(likingEl("p", "liking-hint", "If you mixed two of these, smell them side by side and pick one."));
  const formulaOptions = choices.map((choice, index) => [String(index), choice.label]);
  const pickA = likingSelect("formula_a", formulaOptions, 0);
  const pickB = likingSelect("formula_b", formulaOptions, 1);
  const windowPick = likingSelect("window", LIKING_WINDOWS, 0);
  const note = likingEl("input");
  note.type = "text";
  note.name = "note";
  note.placeholder = "Why (optional)";
  const fields = likingEl("div", "liking-fields");
  fields.append(likingField("A", pickA), likingField("B", pickB), likingField("When", windowPick), likingField("Note", note));
  block.append(fields);
  const status = likingEl("span", "liking-status");
  status.setAttribute("role", "status");
  const undo = likingEl("button", "liking-undo", "Undo");
  undo.type = "button";
  undo.hidden = true;
  let savedId = null;
  const actions = likingEl("div", "liking-actions");
  const buttons = [["a", "A"], ["b", "B"], ["same", "Same"]].map(([preferred, text]) => {
    const button = likingEl("button", "liking-pick-button", text);
    button.type = "button";
    button.dataset.preferred = preferred;
    button.addEventListener("click", async () => {
      const a = choices[Number(pickA.value)];
      const b = choices[Number(pickB.value)];
      if (!a || !b || a === b) {
        status.textContent = "Pick two different formulas.";
        return;
      }
      const windowKey = windowPick.value;
      const linkA = likingRatingLink(a.overlay, windowKey);
      const linkB = likingRatingLink(b.overlay, windowKey);
      const broken = [[a, linkA], [b, linkB]].find(([, link]) => !link.ok);
      if (broken) {
        status.textContent = `${broken[0].label}: ${broken[1].reason}`;
        return;
      }
      buttons.forEach((other) => { other.disabled = true; });
      status.textContent = "Saving…";
      try {
        const [keyA, keyB] = await Promise.all([likingFormulaKey(a.rows), likingFormulaKey(b.rows)]);
        const body = likingPickBody({
          windowKey, preferred, note: note.value,
          a: { formulaName: a.formulaName, key: keyA, link: linkA },
          b: { formulaName: b.formulaName, key: keyB, link: linkB },
        });
        const saved = await request("/liking/picks", { method: "POST", base: LIKING_API, body: JSON.stringify(body) });
        savedId = saved?.id ?? null;
        status.textContent = "Saved";
        undo.hidden = savedId === null;
      } catch (error) {
        status.textContent = `Not saved: ${error.message}`;
      } finally {
        buttons.forEach((other) => { other.disabled = false; });
      }
    });
    return button;
  });
  undo.addEventListener("click", async () => {
    if (savedId === null) return;
    undo.disabled = true;
    try {
      await request(`/liking/picks/${encodeURIComponent(savedId)}`, { method: "DELETE", base: LIKING_API });
      savedId = null;
      undo.hidden = true;
      status.textContent = "Removed";
    } catch (error) {
      status.textContent = `Not removed: ${error.message}`;
    } finally {
      undo.disabled = false;
    }
  });
  actions.append(...buttons, status, undo);
  block.append(actions);
  return block;
}

function likingNameList(heading, names) {
  const paragraph = likingEl("p");
  const list = (Array.isArray(names) ? names : []).map((name) => String(name)).filter(Boolean);
  paragraph.textContent = `${heading} ${list.length ? list.join(", ") : "nothing stands out yet"}`;
  return paragraph;
}

function likingPersonalBlock() {
  const details = likingEl("details", "liking-personal");
  details.append(likingEl("summary", "", "Your nose so far"));
  const body = likingEl("div", "liking-personal-body");
  details.append(body);
  details.addEventListener("toggle", async () => {
    if (!details.open) return;
    body.replaceChildren(likingEl("p", "", "Loading…"));
    try {
      const fit = await request("/liking/personal", { base: LIKING_API });
      body.replaceChildren(
        likingEl("p", "", `${Number(fit?.ratings_used) || 0} ratings and ${Number(fit?.picks_used) || 0} A/B picks used so far.`),
        likingNameList("You like these more than the crowd does:", fit?.liked),
        likingNameList("You like these less than the crowd does:", fit?.disliked),
        likingEl("small", "", "Your own ratings start to matter after roughly 10 to 20 rated bottles; until then the crowd guess carries most of the weight."),
      );
    } catch (error) {
      body.replaceChildren(likingEl("p", "inline-warning", `Couldn't load your ratings: ${error.message}`));
    }
  });
  return details;
}

function renderFormulaLiking(result, variantIndex = 0, selected = null) {
  const box = document.getElementById("formula-result-liking");
  if (!box) return;
  box.replaceChildren();
  const choices = likingFormulaChoices(result);
  const wanted = selected?.variant ? variantIndex : null;
  const current = selected?.formula ? choices.find((choice) => choice.variantIndex === wanted) : null;
  box.hidden = !current;
  if (!current) return;
  box.append(likingCrowdBlock(choices, current));
  const rate = likingEl("div", "liking-rate");
  rate.append(likingEl("h3", "", "Rate this bottle"));
  rate.append(likingEl("p", "liking-hint", `Mixed ${current.label === "Main formula" ? "this formula" : current.label}? Rate it at each time. Your ratings teach the app your taste.`));
  LIKING_WINDOWS.forEach(([windowKey, windowLabel]) => rate.append(likingRatingRow(current, windowKey, windowLabel)));
  box.append(rate);
  const seen = new Set();
  const distinct = choices.filter((choice) => {
    const canonical = likingCanonicalRows(choice.rows);
    if (seen.has(canonical)) return false;
    seen.add(canonical);
    return true;
  });
  if (distinct.length >= 2) box.append(likingPickBlock(distinct));
  box.append(likingPersonalBlock());
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    likingTimeLabel,
    pleasantnessLines,
    likingFormulaChoices,
    variantPleasantnessLines,
    likingCanonicalRows,
    likingFormulaKey,
    likingRatingLink,
    likingRatingBody,
    likingPickBody,
  };
}
