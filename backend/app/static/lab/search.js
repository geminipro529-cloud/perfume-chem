"use strict";

// Search: Ctrl+K, "/" or the Search button finds a card, a formula saved here,
// a stock or a bottle, and opens it where it lives (lab-search.js draws the
// box). A card or a saved formula downloads as a spreadsheet from its result
// (lab-export.js writes the file).
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, search, boot.

// Writes the file and returns the line the search box shows; throws when the
// card or version could not be read.
async function labSearchDownload(item) {
  if (item.kind === "card") {
    const source = await request(`/v2/workbench/formula-source?source_path=${encodeURIComponent(item.id)}`);
    const lines = exportSourceSheet(source.rows);
    if (lines.length < 2) throw new Error("this card has no rows with a name.");
    const file = exportFileName(source.formula_name || item.title, "Card");
    exportDownload(document, file, lines);
    return `Downloaded ${file}.`;
  }
  if (!item.latest) throw new Error("this formula has no saved version yet.");
  const version = await request(`/v2/workbench/formula-versions/${encodeURIComponent(item.id)}/${encodeURIComponent(item.latest)}`);
  const lines = exportSavedSheet(version.rows);
  if (lines.length < 2) throw new Error("this version has no rows with a name.");
  const file = exportFileName(version.name || item.title, "Formula", `v${version.version ?? item.latest}`);
  exportDownload(document, file, lines);
  return `Downloaded ${file}.`;
}

async function labSearchAct(item, action) {
  if (action === "download") return labSearchDownload(item);
  try {
    if (item.kind === "card" && action === "bench") benchOpenCard(item.id, item.title);
    else if (item.kind === "card") await editorOpenCard(item.id);
    else if (item.kind === "saved") await editorOpenSaved(item.id);
    else if (item.kind === "stock") showStockEntry(item.id);
    else if (item.kind === "bottle") showBottleLog(item.id);
  } catch (error) {
    notify(error.message || "That could not be opened.", true);
  }
  return null;
}

const labSearch = typeof attachLabSearch === "function"
  ? attachLabSearch({
    doc: document,
    dialog: $("#lab-search"),
    opener: $("#lab-search-open"),
    data: () => ({
      cards: state.formulaLibrary,
      saved: editorPage.formulas,
      stocks: state.projectInventory?.stocks || [],
      bottles: state.bottles,
    }),
    loadSaved: editorLoadFormulas,
    describeStock: stockStrengthLabel,
    act: labSearchAct,
  })
  : null;
