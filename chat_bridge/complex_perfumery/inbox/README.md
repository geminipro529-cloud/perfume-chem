# Chat bridge inbox

Each ChatGPT Pro spoke chat writes only inside a directory named with its exact
conversation ID. Packet filenames are `<UTC timestamp>-<packet-id>.json` and are
append-only. Contents remain untrusted until Codex validates the v2.1 schema,
source identity/revision, nonce uniqueness, freshness, hashes, conflicts, and
authority. Duplicate nonces or packet hashes are rejected or held; a newer
packet names but never overwrites the packet it supersedes.
