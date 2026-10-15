// Search for the Lab page. Ctrl+K (⌘K on a Mac), "/" or the Search button
// opens one box that finds a card, a formula saved here, a stock or a bottle by
// any part of its name, and opens it where it lives. It reads only what the
// page already has, plus the saved formulas when they were not asked for yet;
// nothing is saved or changed.
//
// The page loads it before the Lab page files in lab/, which wire it up
// (lab/search.js); node runs the pure rules in the tests.

const LAB_SEARCH_GROUP_MAX = 8;
const LAB_SEARCH_GROUPS = [
  { kind: "card", one: "card", many: "cards", label: "Cards" },
  { kind: "saved", one: "saved formula", many: "saved formulas", label: "Saved formulas" },
  { kind: "stock", one: "stock", many: "stocks", label: "Stock" },
  { kind: "bottle", one: "bottle", many: "bottles", label: "Bottles" },
];
// The first action is what Enter or a tap on the name does.
const LAB_SEARCH_ACTIONS = {
  card: [
    { action: "edit", label: "Open in the editor" },
    { action: "bench", label: "Bench sheet" },
    { action: "download", label: "Download", stay: true },
  ],
  saved: [
    { action: "edit", label: "Open in the editor" },
    { action: "download", label: "Download", stay: true },
  ],
  stock: [{ action: "show", label: "Show on the Stock page" }],
  bottle: [{ action: "show", label: "Open its smell log" }],
};

// Lower case, Latin accents dropped (é finds e), anything that is not a
// letter, mark or digit read as a space. Thai keeps its vowels and tone marks.
function labSearchFold(text) {
  return String(text ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^\p{L}\p{M}\p{N}]+/gu, " ").trim();
}

// Everything the box can find, from what the page holds. `describeStock`
// gives a stock's strength in the Stock page's own words.
function labSearchItems({ cards, saved, stocks, bottles } = {}, describeStock = () => "") {
  const items = [];
  (cards || []).forEach((card) => {
    if (!card?.source_path) return;
    items.push({ kind: "card", id: card.source_path, title: card.display_name || card.source_path, detail: "Card file", extra: [card.source_path] });
  });
  (saved || []).forEach((formula) => {
    if (!formula?.formula_id) return;
    const latest = formula.latest ?? formula.versions?.[formula.versions.length - 1]?.version ?? null;
    items.push({
      kind: "saved", id: formula.formula_id, title: formula.name || "Untitled formula", latest,
      detail: latest ? `Saved here, version ${latest}` : "Saved here", extra: [],
    });
  });
  (stocks || []).forEach((stock) => {
    if (!stock?.stock_id) return;
    items.push({
      kind: "stock", id: stock.stock_id, title: stock.identity_name || stock.material || stock.stock_label || stock.stock_id,
      detail: String(describeStock(stock) || ""),
      extra: [stock.stock_label, stock.material, stock.normalized_identity, stock.category, stock.carrier],
    });
  });
  (bottles || []).forEach((bottle) => {
    if (!bottle?.id) return;
    items.push({ kind: "bottle", id: bottle.id, title: bottle.label || bottle.id, detail: bottle.status ? `Bottle, ${bottle.status}` : "Bottle", extra: [] });
  });
  return items;
}

// A card's name after its folders ("studio › Rose" is "Rose"); any other name as it is.
function labSearchLeaf(title) {
  return String(title ?? "").split("›").pop().trim();
}

// How well an item matches the query, best first: 0 the name (or a card's
// name after its folder, "studio › Rose") starts with the whole query, 1 every
// word starts a word of the name, 2 every word is in the name, 3 found only in
// the item's other details; null when a word is missing.
function labSearchScore(item, query) {
  const folded = labSearchFold(query);
  if (!folded) return null;
  const words = folded.split(" ");
  const title = labSearchFold(item.title);
  const leaf = labSearchFold(labSearchLeaf(item.title));
  const all = `${title} ${labSearchFold((item.extra || []).filter(Boolean).join(" "))}`;
  if (!words.every((word) => all.includes(word))) return null;
  if (title.startsWith(folded) || leaf.startsWith(folded)) return 0;
  if (words.every((word) => ` ${title}`.includes(` ${word}`))) return 1;
  if (words.every((word) => title.includes(word))) return 2;
  return 3;
}

// The matches in groups (cards, saved formulas, stock, bottles), each sorted
// best first and cut to `max`; `total` says how many matched before the cut.
function labSearchGroups(items, query, max = LAB_SEARCH_GROUP_MAX) {
  const scored = [];
  (items || []).forEach((item) => {
    const score = labSearchScore(item, query);
    if (score !== null) scored.push({ item, score });
  });
  scored.sort((a, b) => (a.score - b.score)
    || labSearchLeaf(a.item.title).localeCompare(labSearchLeaf(b.item.title), undefined, { sensitivity: "base" })
    || String(a.item.title).localeCompare(String(b.item.title), undefined, { sensitivity: "base" }));
  return LAB_SEARCH_GROUPS.map((group) => {
    const found = scored.filter((entry) => entry.item.kind === group.kind).map((entry) => entry.item);
    return { kind: group.kind, label: group.label, total: found.length, shown: found.slice(0, max) };
  }).filter((group) => group.total);
}

function labSearchCount(count, group) {
  return `${count} ${count === 1 ? group.one : group.many}`;
}

// The status line under the box.
function labSearchSummary(groups, query) {
  if (!labSearchFold(query)) return "Type part of a card, stock or bottle name.";
  if (!groups.length) return "Nothing matches. Try fewer letters, or another part of the name.";
  const parts = groups.map((found) => labSearchCount(found.total, LAB_SEARCH_GROUPS.find((group) => group.kind === found.kind)));
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}` : parts[0];
  return `${list} ${parts.length === 1 && groups[0].total === 1 ? "matches" : "match"}.`;
}

function labSearchIsTyping(target) {
  if (!target || typeof target.closest !== "function") return false;
  return Boolean(target.closest("input, textarea, select, [contenteditable]:not([contenteditable='false'])"));
}

// The box itself. `dialog` is an empty <dialog>; `opener` the Search button;
// `data()` returns { cards, saved, stocks, bottles } (saved is null until the
// saved formulas were asked for); `loadSaved()` asks for them; `act(item,
// action)` opens an item, and for a download returns the line to show.
function attachLabSearch({ doc, dialog, opener, data, loadSaved, describeStock, act }) {
  const make = (tag, attributes = {}, text) => {
    const element = doc.createElement(tag);
    Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const head = make("div", { class: "lab-search-head" });
  const title = make("h2", { id: "lab-search-title" }, "Search");
  const close = make("button", { type: "button", class: "quiet-button lab-search-close" }, "Close");
  head.append(title, close);
  const label = make("label", { for: "lab-search-input", class: "sr-only" }, "Search cards, saved formulas, stock and bottles");
  const input = make("input", {
    id: "lab-search-input", type: "text", enterkeyhint: "search", autocomplete: "off", spellcheck: "false",
    placeholder: "A card, a stock or a bottle", "aria-describedby": "lab-search-status",
  });
  const status = make("p", { id: "lab-search-status", class: "lab-search-status", role: "status", "aria-live": "polite" });
  const results = make("div", { class: "lab-search-results" });
  const keys = make("p", { class: "field-help lab-search-keys" }, "↑ and ↓ move between results, Enter opens one, Esc closes.");
  dialog.replaceChildren(head, label, input, status, results, keys);
  dialog.setAttribute("aria-labelledby", "lab-search-title");

  let savedState = "idle";
  let savedError = "";
  let returnFocus = null;
  let closingForAction = false;
  let note = null;

  const mainButtons = () => [...results.querySelectorAll(".lab-search-main")];

  function render() {
    const query = input.value;
    const groups = labSearchGroups(labSearchItems(data(), describeStock), query);
    const lines = [labSearchSummary(groups, query)];
    if (savedState === "loading") lines.push("Looking for the formulas you saved here.");
    if (savedState === "failed") lines.push(`Your saved formulas could not be read: ${savedError}`);
    if (note) lines.push(note);
    status.textContent = lines.join(" ");
    status.classList.toggle("is-error", Boolean(note && note.startsWith("Not downloaded")));
    const sections = groups.map((group) => {
      const section = make("section", { class: "lab-search-group", "aria-label": group.label });
      const heading = make("h3", {}, group.total > group.shown.length ? `${group.label} · ${group.shown.length} of ${group.total}` : group.label);
      const list = make("ul", { class: "lab-search-list" });
      group.shown.forEach((item) => {
        const [first, ...others] = LAB_SEARCH_ACTIONS[item.kind];
        const row = make("li", { class: "lab-search-row" });
        const main = make("button", { type: "button", class: "lab-search-main" });
        main.append(make("span", { class: "lab-search-name" }, item.title));
        main.append(make("span", { class: "lab-search-detail" }, [item.detail, first.label].filter(Boolean).join(" · ")));
        main.addEventListener("click", () => run(item, first));
        row.append(main);
        if (others.length) {
          const more = make("span", { class: "lab-search-actions" });
          others.forEach((choice) => {
            const button = make("button", { type: "button", class: "quiet-button", "aria-label": `${choice.label}: ${item.title}` }, choice.label);
            button.addEventListener("click", () => run(item, choice));
            more.append(button);
          });
          row.append(more);
        }
        list.append(row);
      });
      section.append(heading, list);
      if (group.total > group.shown.length) {
        section.append(make("p", { class: "field-help" }, `Type more of the name to see the other ${group.total - group.shown.length}.`));
      }
      return section;
    });
    results.replaceChildren(...sections);
  }

  async function run(item, choice) {
    if (choice.stay) {
      note = null;
      try {
        note = await act(item, choice.action) || null;
      } catch (error) {
        note = `Not downloaded: ${error?.message || "something went wrong."}`;
      }
      render();
      return;
    }
    closingForAction = true;
    dialog.close();
    await act(item, choice.action);
  }

  async function askSaved() {
    if (data().saved || savedState === "loading") return;
    savedState = "loading";
    render();
    try {
      await loadSaved();
      savedState = "idle";
    } catch (error) {
      savedState = "failed";
      savedError = error?.message || "the app did not answer.";
    }
    if (dialog.open) render();
  }

  function open() {
    if (!dialog.open) {
      returnFocus = doc.activeElement;
      note = null;
      if (savedState === "failed") savedState = "idle";
      dialog.showModal();
    }
    input.select();
    input.focus();
    render();
    askSaved();
  }

  input.addEventListener("input", () => { note = null; render(); });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      mainButtons()[0]?.focus();
    } else if (event.key === "Enter") {
      event.preventDefault();
      mainButtons()[0]?.click();
    }
  });
  results.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    const buttons = mainButtons();
    const at = buttons.indexOf(doc.activeElement?.closest?.(".lab-search-row")?.querySelector(".lab-search-main"));
    if (at < 0) return;
    event.preventDefault();
    if (event.key === "ArrowDown") buttons[Math.min(at + 1, buttons.length - 1)].focus();
    else if (at === 0) input.focus();
    else buttons[at - 1].focus();
  });
  close.addEventListener("click", () => dialog.close());
  // A tap on the dim area around the box closes it.
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => {
    if (closingForAction) {
      closingForAction = false;
      return;
    }
    if (returnFocus && returnFocus.isConnected && typeof returnFocus.focus === "function") returnFocus.focus();
  });
  opener?.addEventListener("click", open);
  doc.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || event.isComposing) return;
    const otherDialog = [...doc.querySelectorAll("dialog[open]")].some((node) => node !== dialog);
    if (otherDialog) return;
    // event.code too: with a Thai keyboard layout on, the K key types "า".
    const kKey = String(event.key || "").toLowerCase() === "k" || event.code === "KeyK";
    const shortcut = (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && kKey;
    const slash = event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey && !labSearchIsTyping(event.target);
    if (!shortcut && !slash) return;
    event.preventDefault();
    open();
  });

  return { open, render };
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    LAB_SEARCH_GROUP_MAX, LAB_SEARCH_ACTIONS, labSearchFold, labSearchItems, labSearchScore, labSearchGroups,
    labSearchSummary, labSearchIsTyping, attachLabSearch,
  };
}
