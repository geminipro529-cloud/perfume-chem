// Pure wording for the composer's advisory gate checks. It touches no DOM, so
// the page loads it before lab.js (its functions become page globals) and node
// runs it in the tests. lab.js writes the returned text with textContent.

const COMPOSITION_CHECK_LABELS = {
  hedione_share: "Hedione share",
  musk_count: "Musk count",
  ifra: "IFRA",
  gate: "Checks",
};

const COMPOSITION_CHECK_FLAGS = new Set(["WARN", "FAIL", "ERROR"]);

function compositionCheckLines(compositionChecks) {
  if (!compositionChecks || !Array.isArray(compositionChecks.checks)) return null;
  const flagged = compositionChecks.checks.filter((check) => COMPOSITION_CHECK_FLAGS.has(check.status));
  const lines = flagged.map((check) => ({
    status: String(check.status || ""),
    text: `${COMPOSITION_CHECK_LABELS[check.check] || String(check.check || "Check")}: ${String(check.message || "")}`,
  }));
  const unchecked = (compositionChecks.unchecked_rows || [])
    .filter(Boolean)
    .map((row) => (typeof row === "string" ? { material: row, reason: "" } : row));
  if (!lines.length) {
    lines.push(unchecked.length
      ? { status: "PASS", text: "Hedione share, musk count and IFRA found no problem in the rows they could read" }
      : { status: "PASS", text: "Checks passed: Hedione share, musk count, IFRA" });
  }
  if (unchecked.length) {
    const names = unchecked.map((row) => (row.reason ? `${row.material} (${row.reason})` : String(row.material)));
    lines.push({ status: "SKIP", text: `Not checked: ${names.join(", ")}` });
  }
  return {
    flagged: flagged.length > 0 || unchecked.length > 0,
    lines,
    basis: String(compositionChecks.basis || ""),
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = { compositionCheckLines };
}
