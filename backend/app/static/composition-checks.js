// Pure wording for the composer's advisory gate checks. It touches no DOM, so
// the page loads it before lab.js (its functions become page globals) and node
// runs it in the tests. lab.js writes the returned text with textContent.

const COMPOSITION_CHECK_LABELS = {
  hedione_share: "Hedione share",
  musk_count: "Musk count",
  ifra: "IFRA",
  gate: "Checks",
};

function compositionCheckLines(compositionChecks) {
  if (!compositionChecks || !Array.isArray(compositionChecks.checks)) return null;
  const flagged = compositionChecks.checks.filter((check) => check.status === "WARN" || check.status === "FAIL");
  const skipped = compositionChecks.checks.filter((check) => check.check === "gate");
  const lines = [...flagged, ...skipped].map((check) => ({
    status: String(check.status || ""),
    text: `${COMPOSITION_CHECK_LABELS[check.check] || String(check.check || "Check")}: ${String(check.message || "")}`,
  }));
  if (!lines.length) {
    lines.push({ status: "PASS", text: "Checks passed: Hedione share, musk count, IFRA" });
  }
  const unchecked = (compositionChecks.unchecked_rows || []).filter(Boolean);
  if (unchecked.length) {
    lines.push({ status: "SKIP", text: `Not checked (stock strength unknown): ${unchecked.join(", ")}` });
  }
  return {
    flagged: flagged.length > 0 || skipped.length > 0,
    lines,
    basis: String(compositionChecks.basis || ""),
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = { compositionCheckLines };
}
