const CHILD_ENVIRONMENT_ALLOWLIST = Object.freeze(new Set([
  "APPDATA",
  "CODEX_HOME",
  "COMSPEC",
  "HOME",
  "LOCALAPPDATA",
  "NODE_PATH",
  "PATH",
  "PATHEXT",
  "SYSTEMROOT",
  "TEMP",
  "TMP",
  "USERPROFILE",
  "WINDIR",
]));

const SENSITIVE_NAME = /(?:^|[_-])(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTHORIZATION|COOKIE|CREDENTIALS?)(?:$|[_-])|(?:apiKey|accessToken|authToken|refreshToken|password|authorization|cookie|credential)$/i;
const INLINE_ASSIGNMENT = /\b([A-Za-z][A-Za-z0-9_-]{1,100})\s*[=:]\s*[^\s,;]+/g;

export function buildChildEnvironment(parent = process.env) {
  const result = {};
  for (const [name, value] of Object.entries(parent ?? {})) {
    if (value === undefined) continue;
    if (!CHILD_ENVIRONMENT_ALLOWLIST.has(name.toUpperCase())) continue;
    if (SENSITIVE_NAME.test(name)) continue;
    result[name] = String(value);
  }
  return result;
}

export function redactDiagnostic(value, knownSecrets = []) {
  const secrets = knownSecrets
    .map((item) => String(item ?? ""))
    .filter((item) => item.length >= 4)
    .sort((left, right) => right.length - left.length);

  const redactString = (input) => {
    let output = String(input).replace(
      INLINE_ASSIGNMENT,
      (match, name) => SENSITIVE_NAME.test(name) ? "[REDACTED]" : match,
    );
    for (const secret of secrets) output = output.split(secret).join("[REDACTED]");
    output = output.replace(/Bearer\s+[^\s,;]+/gi, "Bearer [REDACTED]");
    return output;
  };

  const visit = (input) => {
    if (Array.isArray(input)) return input.map(visit);
    if (input && typeof input === "object") {
      return Object.fromEntries(Object.entries(input).map(([key, item]) => [
        key,
        SENSITIVE_NAME.test(key) ? "[REDACTED]" : visit(item),
      ]));
    }
    return typeof input === "string" ? redactString(input) : input;
  };

  return visit(value);
}
