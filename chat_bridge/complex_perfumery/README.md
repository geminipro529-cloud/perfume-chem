# DeepLuna Chat <-> Complex Perfumery <-> Codex Bridge

This directory is the durable hub-and-spoke bridge between ChatGPT Pro chats in
the `Complex Perfumery` project and the local `D:\chatbots\perfume-chem`
workspace.

It is not a shared hidden transcript. ChatGPT project chats share project files,
instructions, and connected sources, while each chat keeps its own conversation
history. The bridge transfers explicit, provenance-bearing packets instead.

## Current hub

- ChatGPT project: `Complex Perfumery`
  (`g-p-6a74ab83668081919f5cbd0dfe80eb09`)
- Active orchestration program: `DeepLuna Chat` (non-Fast), with Sol as the
  engineer and final authority
- Work hub: `Data Integration for Perfume-Chem`
  (`6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf`)
- Linked Codex task: `Review Perfume-Chem data integration`
  (`019fe3a3-3cca-7462-b8e9-e315015e95df`)
- DeepLuna Fast: `TEMPORARILY_RETIRED_BY_USER` until explicitly re-enabled

## Selected architecture

The accepted route is hybrid:

- the Secure MCP Tunnel provides live workspace reads, explicit user-authorized
  file edits, and the intake-mailbox transport;
- Codex/Sol performs local schema, identity, freshness, replay, conflict,
  provenance, security, and scientific-authority validation;
- Git records accepted code, manifests, and reviewable derived artifacts;
- GitHub is optional collaboration/publication for non-sensitive accepted
  artifacts, not hidden chat memory and not the local filesystem.

Raw chat captures, browser session material, credentials, and protected
scientific stores do not enter Git or GitHub by default. A content hash proves
byte identity; it does not prove scientific truth.

## Data flow

1. A project chat publishes one nonce-bearing immutable packet to
   `chat_bridge/complex_perfumery/inbox/<conversation-id>/<timestamp>-<packet-id>.json`.
2. The work hub reads the packet and synthesizes only the requested workstream.
3. Codex validates provenance, conflicts, hashes, and repository impact.
4. Accepted state is promoted by Codex to `shared_state.json`, an outbox packet,
   or the appropriate existing repository ingestion path.
5. Browser files are staged under `incoming_review/chatgpt/` with a manifest and
   SHA-256 before any scientific or code authority is granted.

## Security boundary

The Secure MCP Tunnel permits ChatGPT to create and edit ordinary files anywhere
under `D:\chatbots\perfume-chem` when the user explicitly requests it. Absolute
paths, workspace escapes, symlink traversal, credentials, `.env*`, Git internals,
and local agent/tool-state paths remain server-fenced. The MCP surface has no
shell, delete, or rename tool. Existing-file rewrites can carry an expected
SHA-256 to prevent stale overwrites. This technical write capability does not
grant scientific, formula, inventory, bottle, code-review, or release authority;
Codex/Sol still validates and accepts consequential changes.

The installed connector passed a remote create/edit/read-back canary from Codex
on 2026-08-10 at `output/chatgpt_tunnel_remote_write_canary.txt` (SHA-256
`6a517a272bcb7d226a2c278b12306ec88f3dd60aa60884ff14609f481774aea8`), and a
credential-like `.env` write was denied. A browser ChatGPT project chat should
refresh the app and run one final canary before the bridge's browser-chat
release HOLD is removed.

## Registry completeness

`chat_registry.json` records the 38 chats exposed by the signed-in Complex
Perfumery project sidebar after full expansion on 2026-08-09. That is complete
for the current project UI snapshot, not a claim about deleted, inaccessible,
separately archived, or future chats. Twenty-nine spoke notices are delivered;
eight remain explicitly pending because the task service rate-limited their
latest delivery attempt. All 38 chats are nevertheless linked through the
shared project-instruction block, which was saved and verified after reopening
the project settings. That project-level link is shared context, not hidden
transcript sharing or connector proof.

## Chat commands

- `Publish to DeepLuna Chat` - create an immutable inbox packet for the work hub.
- `Load work-hub packet` - read the named validated packet or `shared_state.json`.
- `Stage browser files` - place files plus a manifest in `incoming_review/chatgpt/`.
- `Sync accepted state` - ask Codex to validate and promote a packet.
- `Modify workspace file` - on an explicit request, read, edit with a hash
  precondition when available, and verify the resulting SHA-256.

See `PROTOCOL.md` and `handoff.schema.json` for the exact contract.
