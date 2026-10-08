# Perfume-Chem Fail-Closed MCP Bridge Design

**Date:** 2026-09-03  
**Status:** implementation specification  
**Target repository:** `geminipro529-cloud/perfume-chem`  
**Local target root:** `D:\chatbots\perfume-chem`  
**Work hub:** `chatgpt-conversation://6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf`  
**Linked Codex task:** `019fe3a3-3cca-7462-b8e9-e315015e95df`

## Goal

Build a tool-only MCP bridge that lets ChatGPT inspect the local Perfume-Chem repository, verify its exact state, search and fetch allowlisted text files, verify the current inventory authority, and stage one nonce-scoped incoming-review packet only after every publication guard passes.

## Non-goals

The connected MCP app exposes four read-only tools by default. The fifth packet-stage tool is registered only when `PERFUME_CHEM_EXPOSE_WRITE_TOOL=1`; this is separate from the deeper write arm.

The bridge does not:

- claim access to the local Windows repository before a local canary passes;
- promote packet claims into canonical scientific or formula authority;
- write formula, inventory, bottle, database, migration, or release state;
- execute arbitrary shell commands;
- expose secrets, environment values, private keys, database files, or binary inventory contents;
- infer measured headspace, strict empirical OAV, liking, similarity, stability, safety, or release readiness;
- revive DeepLuna Fast.

## Authority locks

1. Inventory authority for this bridge is `Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx`, 199,635 bytes, SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`.
2. A harmless filename suffix such as `(1)` may be accepted only when the file size and SHA-256 match exactly.
3. Repository `inventory.txt` remains repository ancestry and must not override Inventory V5 for bridge inventory decisions.
4. `PROTOCOL.md` in the project sources is the Universal Non-Compressed Perfume Reconstruction Protocol, not Chat Bridge Protocol v2.1.
5. Packet staging remains blocked until the exact local `chat_bridge/complex_perfumery/PROTOCOL.md` exists and its SHA-256 matches `PERFUME_CHEM_PROTOCOL_SHA256`.
6. Unknown or conflicting authority resolves to `HOLD`, never a synthesized compromise.

## Architecture

The bridge is an isolated `engine.bridge` namespace. Core canary, hashing, repository reading, and packet staging use the Python standard library. The MCP adapter is the only module that imports the optional `mcp` package.

```text
ChatGPT / MCP client
        |
        v
engine.bridge.server
        |
        +--> canary.py        fixed, allowlisted subprocess probes
        +--> repository.py    confined text search/fetch
        +--> packet_intake.py atomic, no-overwrite packet staging
        +--> receipts.py      canonical JSON hash and optional HMAC seal
        +--> config.py        environment-derived immutable settings
```

## MCP tools

### `perfume_chem_bridge_status`

Read-only. Runs a metadata, quick, or full canary and returns a sealed provenance receipt. Metadata mode never claims a verified bridge.

### `perfume_chem_inventory_authority`

Read-only. Returns inventory path, byte length, SHA-256, and exact-match state. It never returns workbook bytes or sheet contents.

### `perfume_chem_search`

Read-only. Searches UTF-8 text only beneath explicitly allowlisted repository prefixes, with bounded result and file-size limits.

### `perfume_chem_fetch`

Read-only. Fetches one allowlisted UTF-8 text file with path confinement and a character ceiling.

### `perfume_chem_stage_review_packet`

Optional MCP write tool, disabled by default and intended only for a workspace plan that supports MCP write actions. The same operation remains available through the local `stage` CLI. Mutating but non-destructive. Creates exactly one new `PACKET.json` at:

```text
chat_bridge/complex_perfumery/inbox/<conversation-id>/<nonce>/PACKET.json
```

It refuses to run unless:

- a full canary has passed;
- the exact protocol file and configured protocol SHA-256 match;
- Inventory V5 matches its byte and hash lock;
- the repository is clean and its origin is the expected repository;
- `PERFUME_CHEM_PACKET_WRITES=1`;
- `PERFUME_CHEM_BRIDGE_SIGNING_KEY` is present;
- the conversation ID is the authorized work-hub ID;
- the nonce is a valid UUID;
- the packet declares `INCOMING_REVIEW_ONLY`;
- `canonical_mutation_authorized` and `formula_mutation_authorized` are both false;
- the caller provides the exact confirmation string;
- the target directory does not already exist.

## Canary states

- `BRIDGE_BLOCKED`: a required identity, authority, protocol, import, or verification check failed or was not run.
- `READY_FOR_VERIFICATION`: metadata checks passed, but repository-native verification was not run.
- `PASS`: quick or full repository-native verification passed and every required guard passed.

Only `PASS` from full mode can arm packet staging.

## Receipt contract

Every receipt includes:

- schema and bridge version;
- UTC generation timestamp;
- canary mode and aggregate state;
- repository root, normalized origin, branch, full HEAD, dirty state, and worktree records;
- Python executable and version;
- migration-head probe result;
- `PerfumeWorkbench` import result;
- native verifier command, return code, and output SHA-256 values;
- inventory identity, size, and hash result;
- bridge-protocol identity and hash result;
- write-arm state and secret-exposure assertion;
- canonical receipt SHA-256;
- optional HMAC-SHA256 signature, without disclosing the signing key.

## Security constraints

- Bind locally to `127.0.0.1` by default through the documented Uvicorn command.
- Use OpenAI Secure MCP Tunnel for a private local endpoint, or a stable authenticated HTTPS host where appropriate.
- Put authentication at the tunnel or reverse-proxy boundary.
- Never log environment values.
- Never return stdout containing detected secret patterns.
- Use fixed subprocess argument vectors only.
- Reject symlink and path traversal escape.
- Reject `.env`, `.git`, key, certificate, database, spreadsheet, archive, image, and binary paths.
- Packet staging is atomic and refuses overwrite.

## Scientific boundary

The bridge transports evidence and invokes repository-native computation. It does not transform modeled outputs into empirical facts. Evidence-faithful target formulas remain separate from current-inventory builds and bottle ledgers. Missing-material ranking remains advisory and cannot automatically mutate formulas.

## Verification strategy

1. Unit tests use disposable Git repositories and synthetic inventory/protocol bytes.
2. Tests cover exact origin normalization, forbidden-root rejection, inventory hash lock, protocol lock, metadata versus full state, confined reads, no-overwrite packet staging, mutation flags, and receipt stability.
3. A disposable local end-to-end canary verifies the protocol machinery without claiming access to `D:\chatbots\perfume-chem`.
4. The actual bridge remains `BRIDGE_BLOCKED` until the user runs the full canary inside the real repository.
