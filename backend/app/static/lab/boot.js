"use strict";

// Start-up, loaded last: hash navigation, skip link, theme, the first view and the first refresh.
// Loaded in index.html after the shared helper scripts, in this order: core, stock, improve, overview, create, editor, bench, bottles, experiments, perfumery, assistant, science, search, boot.

window.addEventListener("hashchange", () => {
  const requested = location.hash.slice(1) || "improve";
  if ($(`[data-panel="${requested}"]`)) navigate(requested);
});

// Move focus to the main area without putting "#main-content" in the URL.
$(".skip-link").addEventListener("click", (event) => {
  event.preventDefault();
  $("#main-content").focus();
});

const THEME_KEY = "perfumechem.theme";
const THEME_COLORS = { light: "#FFFDF8", dark: "#12171B" };
function applyTheme(choice) {
  const root = document.documentElement;
  if (choice === "light" || choice === "dark") root.dataset.theme = choice;
  else delete root.dataset.theme;
  const resolved = choice === "light" || choice === "dark"
    ? choice
    : (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  $('meta[name="theme-color"]')?.setAttribute("content", THEME_COLORS[resolved]);
}
(() => {
  let choice = "system";
  try { choice = localStorage.getItem(THEME_KEY) || "system"; } catch { choice = "system"; }
  if (!["system", "light", "dark"].includes(choice)) choice = "system";
  const picker = $("#theme-select");
  if (picker) {
    picker.value = choice;
    picker.addEventListener("change", () => {
      try { localStorage.setItem(THEME_KEY, picker.value); } catch { /* storage unavailable */ }
      applyTheme(picker.value);
    });
  }
  applyTheme(choice);
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (!document.documentElement.dataset.theme) applyTheme("system");
  });
})();

// Stock prices (stock.js) load now that every page file is in.
stockPrices?.load();

const startView = location.hash.slice(1);
// An unknown hash (an old "#main-content" bookmark, say) would hide every view.
navigate($$(".view").some((panel) => panel.dataset.panel === startView) ? startView : "improve");
pageStarted = true;
restoreStoredDrafts();
refresh().catch((error) => notify(error.message, true));
