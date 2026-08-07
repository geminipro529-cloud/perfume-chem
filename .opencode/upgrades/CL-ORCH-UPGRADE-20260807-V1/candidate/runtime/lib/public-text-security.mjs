export const PUBLIC_TEXT_PATH_PATTERN =
  /(?:[A-Za-z]:[\\/]|\\\\|(?:^|\s)\/[A-Za-z0-9._-]+\/)/u;

export const PUBLIC_TEXT_SECRET_PATTERN =
  /(?:\b(?:api[_ -]?key|bearer|password|secret)\b|\bsk-[A-Za-z0-9]|\bauthorization\s*(?:header\s*)?[:=]\s*\S+)/iu;

export function containsUnsafePublicText(value) {
  return (
    PUBLIC_TEXT_PATH_PATTERN.test(value) ||
    PUBLIC_TEXT_SECRET_PATTERN.test(value)
  );
}
