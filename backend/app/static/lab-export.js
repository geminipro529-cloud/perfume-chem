// Downloads for the Lab page: a card or the stock list as a CSV file that
// Excel, Numbers and Google Sheets open (Thai names included). Nothing here
// changes a card or your stock.
//
// The page loads it after formula-editor.js, whose row rules it uses, and
// before the Lab page files in lab/; node runs it in the tests.

const exportEditor = (typeof module === "object" && module.exports)
  ? require("./formula-editor.js")
  : { editorRowsFromSource, editorRowsFromSaved, editorTotals, editorShown, editorStrengthText };
const exportBench = (typeof module === "object" && module.exports)
  ? require("./bench-sheet.js")
  : { benchFractionText };

const EXPORT_CARD_HEADER = ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"];
const EXPORT_UNIT_WORDS = { ul: "µL", "µl": "µL", "μl": "µL", ml: "mL", mg: "mg", g: "g" };

// One spreadsheet cell. Text a spreadsheet would run as a formula (it starts
// with =, +, -, @, a tab or a return) is kept as text with a leading '.
function exportCell(value) {
  let text = String(value ?? "");
  if (/^[=+\-@\t\r]/.test(text) && !/^[+-]?\d+(\.\d+)?$/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function exportCsv(lines) {
  return `${(lines || []).map((line) => line.map(exportCell).join(",")).join("\r\n")}\r\n`;
}

// An amount to six decimals, as the editor's own boxes take it: 1/4 µL is
// 0.25, not the screen's rounded 0.3.
const exportAmount = (value) => exportBench.benchFractionText(value, 6);

// Rows from the editor (or a saved version) as a sheet: µL for a liquid and mg
// for a solid, as the formula keeps them, and each liquid's share of the
// liquid. A row typed in grams that still waits for its density keeps its grams.
function exportEditorSheet(rows) {
  const totals = exportEditor.editorTotals(rows);
  const lines = [EXPORT_CARD_HEADER];
  (rows || []).forEach((row) => {
    if (!row.material) return;
    let amount = { text: "", unit: "" };
    if (row.amount) amount = { text: exportAmount(row.amount), unit: row.solid ? "mg" : "µL" };
    else if (row.grams) amount = { text: exportAmount(row.grams), unit: "g" };
    const share = !row.solid && row.amount && totals.liquidUl.n > 0n
      ? exportEditor.editorShown(row, totals, "pct", {}).text
      : "";
    lines.push([row.material, exportEditor.editorStrengthText(row), amount.text, amount.text ? amount.unit : "", share, row.note]);
  });
  return lines;
}

// A project card's rows as written on it: each amount keeps the card's own
// figure and unit; the share of the liquid counts the µL and mL rows.
function exportSourceSheet(sourceRows) {
  const entries = (sourceRows || []).map((row) => ({ row, edited: exportEditor.editorRowsFromSource([row]).rows[0] || null }));
  const totals = exportEditor.editorTotals(entries.map((entry) => entry.edited).filter(Boolean));
  const lines = [EXPORT_CARD_HEADER];
  entries.forEach(({ row, edited }) => {
    const material = String(row.material || row.identity_name || "").trim();
    if (!material) return;
    const strength = exportEditor.editorStrengthText({
      fraction: row.stock_fraction_decimal ?? row.concentration_fraction_decimal ?? "",
      basis: row.fraction_basis ?? row.concentration_basis ?? "",
      carrier: row.carrier || null,
    });
    const unit = String(row.amount_unit ?? "").trim();
    const share = edited && !edited.solid && edited.amount && totals.liquidUl.n > 0n
      ? exportEditor.editorShown(edited, totals, "pct", {}).text
      : "";
    lines.push([material, strength, String(row.amount_decimal ?? "").trim(), EXPORT_UNIT_WORDS[unit.toLowerCase()] || unit, share, edited ? edited.note : ""]);
  });
  return lines;
}

// A saved version's rows (GET formula-versions/{id}/{version}) as a sheet.
function exportSavedSheet(savedRows) {
  return exportEditorSheet(exportEditor.editorRowsFromSaved(savedRows));
}

// Today's date as 2026-10-15, on this device's calendar.
function exportToday(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// A file name every system accepts: letters (Thai too), digits, spaces and
// . _ ( ) -; anything else becomes a dash. `fallback` names a file whose name
// has nothing left.
function exportFileName(name, fallback, suffix = "") {
  const base = String(name ?? "").normalize("NFC")
    .replace(/[^\p{L}\p{M}\p{N} ._()-]+/gu, "-")
    .replace(/\s+/g, " ")
    .replace(/-{2,}/g, "-")
    .replace(/^[\s.-]+|[\s.-]+$/g, "")
    .slice(0, 80)
    .trim();
  return `${base || fallback}${suffix ? ` ${suffix}` : ""}.csv`;
}

// Saves the sheet as a CSV file through the browser's own download. The byte
// order mark makes Excel read the file as UTF-8, so Thai stays Thai.
function exportDownload(doc, fileName, lines) {
  const view = doc.defaultView;
  const blob = new view.Blob(["﻿", exportCsv(lines)], { type: "text/csv;charset=utf-8" });
  const url = view.URL.createObjectURL(blob);
  const link = doc.createElement("a");
  link.href = url;
  link.download = fileName;
  link.hidden = true;
  doc.body.append(link);
  link.click();
  link.remove();
  view.setTimeout(() => view.URL.revokeObjectURL(url), 60000);
}

if (typeof module === "object" && module.exports) {
  module.exports = {
    EXPORT_CARD_HEADER, exportCell, exportCsv, exportEditorSheet, exportSourceSheet, exportSavedSheet,
    exportToday, exportFileName, exportDownload,
  };
}
