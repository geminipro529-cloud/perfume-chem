# Perfume-Chem Local MCP Bridge

This bridge gives ChatGPT a bounded route into the local Perfume-Chem repository. It is **read-only by default**. On ChatGPT Pro, keep the connected app in this default read-only form; packet staging is available through the local CLI. The bridge remains `BRIDGE_BLOCKED` until an exact local canary proves repository identity, Inventory V5, Chat Bridge Protocol v2.1, `PerfumeWorkbench` importability, migration state, and repository-native verification.

## Authority and scope

The bridge locks current stock authority to:

```text
Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx
bytes: 199635
sha256: e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331
```

A filename suffix such as `(1)` is acceptable only when both byte length and SHA-256 match. Repository `inventory.txt` does not override Inventory V5 within this bridge scope.

The project `PROTOCOL.md` is a reconstruction protocol, not Chat Bridge Protocol v2.1. Packet staging therefore stays blocked until the exact local bridge protocol exists at `chat_bridge/complex_perfumery/PROTOCOL.md` and its hash is configured.

## Install

From PowerShell at `D:\chatbots\perfume-chem` using the repository's supported Python 3.11 environment:

```powershell
python -m pip install -r requirements-bridge.txt
```

## Required read-only environment

```powershell
$env:PERFUME_CHEM_REPO_ROOT = 'D:\chatbots\perfume-chem'
$env:PERFUME_CHEM_INVENTORY_PATH = 'D:\path\to\Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx'
$env:PERFUME_CHEM_PROTOCOL_SHA256 = '<sha256-of-exact-chat-bridge-protocol-v2.1>'
```

Optional limits:

```powershell
$env:PERFUME_CHEM_VERIFY_TIMEOUT_SECONDS = '1200'
$env:PERFUME_CHEM_MAX_READ_BYTES = '262144'
```

## Run the canary before the server

Metadata probe:

```powershell
python -m engine.bridge canary --mode metadata
```

Quick repository verification:

```powershell
python -m engine.bridge canary --mode quick
```

Full repository verification:

```powershell
python -m engine.bridge canary --mode full
```

Only the full receipt may authorize packet staging. Metadata mode can return `READY_FOR_VERIFICATION`, never `PASS`.

## Run locally

Bind to loopback:

```powershell
python -m engine.bridge serve --host 127.0.0.1 --port 8765
```

The equivalent ASGI command is:

```powershell
python -m uvicorn engine.bridge.server:app --host 127.0.0.1 --port 8765
```

The MCP endpoint is:

```text
http://127.0.0.1:8765/mcp
```

Test it with MCP Inspector before connecting ChatGPT. For ChatGPT developer-mode testing, use OpenAI Secure MCP Tunnel for the private local endpoint. If a separately managed HTTPS boundary is used, keep authentication at that tunnel or reverse-proxy boundary and never publish an unauthenticated local repository endpoint.

## MCP tools

| Tool | Mutation | Purpose |
|---|---:|---|
| `perfume_chem_bridge_status` | No | Metadata, quick, or full provenance canary |
| `perfume_chem_inventory_authority` | No | Exact V5 size/hash verification |
| `perfume_chem_search` | No | Bounded allowlisted repository-text search |
| `perfume_chem_fetch` | No | Bounded allowlisted repository-text fetch |
| `perfume_chem_stage_review_packet` | New packet only | Optional; registered only when write-tool exposure is explicitly armed |

## Arming packet staging

Do not set these for ordinary read-only use. For an explicit publish or sync operation, configure:

```powershell
$env:PERFUME_CHEM_PACKET_WRITES = '1'
$env:PERFUME_CHEM_BRIDGE_SIGNING_KEY = '<random-secret-from-a-secret-manager>'
```

Stage locally, without exposing an MCP write action:

```powershell
python -m engine.bridge stage --packet .\packet.json --confirmation 'STAGE INCOMING REVIEW ONLY'
```

Only in a Business or Enterprise/Edu workspace where full MCP write actions are enabled and administratively approved, optionally expose the same guarded action to ChatGPT:

```powershell
$env:PERFUME_CHEM_EXPOSE_WRITE_TOOL = '1'
```

`PERFUME_CHEM_EXPOSE_WRITE_TOOL` only registers the tool. It does not bypass `PERFUME_CHEM_PACKET_WRITES`, the signing key, the full canary, or any packet guard.

The mutating tool still requires:

- a fresh full canary;
- exact protocol and Inventory V5 hashes;
- the authorized conversation ID;
- a canonical UUID nonce;
- `authority: INCOMING_REVIEW_ONLY`;
- both mutation flags explicitly false;
- exact confirmation text `STAGE INCOMING REVIEW ONLY`;
- a destination directory that does not already exist.

The tool creates only:

```text
chat_bridge/complex_perfumery/inbox/<conversation-id>/<nonce>/PACKET.json
```

It does not commit, merge, acknowledge, install, or promote anything.

## Scientific and formula boundary

The bridge does not convert repository computation into observed perfume performance. Target architecture remains separate from the current-inventory build and physical bottle ledger. Modeled headspace, OAV, longevity, diffusion, liking, similarity, stability, safety, and release remain bounded by their actual evidence states.

## Current deployment state

This source implementation can be reviewed and tested independently. The production local state remains:

```text
BRIDGE_BLOCKED
```

until the full canary is executed successfully inside the real `D:\chatbots\perfume-chem` repository.
