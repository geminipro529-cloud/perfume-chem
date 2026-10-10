// Pure wording for the composer's voice-count screening summary. It touches no
// DOM, so the page loads it before lab.js (its function becomes a page global)
// and node runs it in the tests. lab.js writes the returned text with textContent.

function formulaVoiceLines(summary) {
  if (!summary || typeof summary !== "object") return null;
  const windows = Array.isArray(summary.windows) ? summary.windows : [];
  const byLabel = (label) => windows.find((window) => window && window.label === label);
  const lines = [];
  const heart = byLabel("heart");
  if (heart && Number.isFinite(Number(heart.effective_voices))) {
    lines.push(`About ${Math.round(Number(heart.effective_voices))} voices in the heart (model)`);
  }
  const counts = ["opening", "heart", "drydown"].map((label) => [label, byLabel(label)])
    .filter(([, window]) => window && Number.isFinite(Number(window.detectable_components)));
  if (counts.length) {
    lines.push(`Detectable notes: ${counts.map(([label, window]) => `${label} ${Math.round(Number(window.detectable_components))}`).join(", ")}`);
  }
  (Array.isArray(summary.flags) ? summary.flags : []).forEach((flag) => {
    if (flag && flag.message) lines.push(String(flag.message));
  });
  return {
    lines,
    note: String(summary.note || ""),
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = { formulaVoiceLines };
}
