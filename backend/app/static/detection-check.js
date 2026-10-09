// Pure wording for the composer's smell check (the detection_check block).
// It touches no DOM, so the page loads it before lab.js (its functions become
// page globals) and node runs it in the tests. lab.js writes the returned text
// with textContent.

function detectionWindowText(windows) {
  const names = (Array.isArray(windows) ? windows : []).map((name) => String(name).replaceAll("_", " "));
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function detectionCheckLines(detectionCheck) {
  if (!detectionCheck || !Array.isArray(detectionCheck.roles)) return null;
  const roles = detectionCheck.roles;
  const isDetectable = (role) => role.status === "detectable" || role.status === "raised";
  const lines = [{
    status: "SUMMARY",
    text: `Smell check: ${roles.filter(isDetectable).length} of ${roles.length} notes detectable at their stage`,
  }];
  roles.forEach((role) => {
    const material = String(role.material || "A material");
    if (role.status === "raised") {
      lines.push({
        status: "raised",
        text: `${material}: raised from ${role.dose_before_ul} to ${role.dose_after_ul} µL so it can be smelled in the ${detectionWindowText(role.intended_windows)}`,
      });
    } else if (role.status === "silent_at_cap") {
      const tried = role.highest_dose_tried_ul != null && role.highest_dose_tried_ul !== ""
        ? `, tried up to ${role.highest_dose_tried_ul} µL` : "";
      lines.push({ status: "silent_at_cap", text: `${material}: below detection at its limit (${role.binding_limit || "unknown limit"})${tried}` });
    } else if (role.status === "no_threshold_data") {
      lines.push({ status: "no_threshold_data", text: `${material}: no smell-threshold data` });
    } else if (role.status === "not_checked") {
      lines.push({ status: "not_checked", text: `${material}: weighed solid, not checked` });
    }
  });
  (Array.isArray(detectionCheck.flags) ? detectionCheck.flags : []).forEach((flag) => {
    lines.push({
      status: "flag",
      text: `${String(flag.material || "A material")} may dominate: smell-check (${detectionWindowText(flag.windows)})`,
    });
  });
  return {
    flagged: lines.some((line) => line.status !== "SUMMARY" && line.status !== "raised"),
    lines,
    note: String(detectionCheck.note || ""),
  };
}

if (typeof module === "object" && module.exports) {
  module.exports = { detectionCheckLines };
}
