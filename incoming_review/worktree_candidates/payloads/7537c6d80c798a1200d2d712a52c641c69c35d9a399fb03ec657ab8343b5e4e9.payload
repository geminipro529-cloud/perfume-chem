# Codex Desktop Repair Report — 2026-07-29

## Executive Summary

Codex Desktop (OpenAI's desktop AI assistant app, v26.721.41059) stopped working after
its `config.toml` was changed to route main chat traffic through a non-existent local
LiteLLM proxy. The fix involved restoring the original auth state and correcting 4
configuration errors. The app is now functional with a clean separation between
Codex Desktop (DeepLuna via DeepInfra) and OpenCode (CheapLuna via DeepSeek Direct).

---

## 1. Architecture: Two Environments, Two Bridges

| | DeepLuna (Codex Desktop) | CheapLuna (OpenCode CLI) |
|---|---|---|
| **Primary profile** | `deepinfra-fast` | `deepseek-direct` |
| **API endpoint** | `api.deepinfra.com/v1/openai` | `api.deepseek.com` |
| **Auth credential** | `DEEPINFRA_API_TOKEN` | `DEEPSEEK_API_KEY` |
| **FAST_ONLY** | `1` (FLASH only) | `0` (PRO + FLASH) |
| **Reader lanes** | 5 | 2 (default) |
| **Fallback** | Disabled (GLM/Luna filtered) | Disabled (GLM/Luna filtered) |
| **Project ID** | `perfume-chem` | `perfume-chem-cheapluna` |
| **Bridge script** | `scripts/start_cheapluna_vscode.ps1` | `.opencode/scripts/cheapluna-bridge.ps1` |
| **MCP tool prefix** | `deepseek_*` (Codex Desktop) | `deepseek_*` (OpenCode) |
| **Daemon storage** | `AppData\Local\Codex\deepseek-orchestrator\` | `.cheapluna-home\dynamic-pool-v1\` |

They are fully independent — separate daemons, separate project-ids, separate bridge
processes. One does not affect the other.

---

## 2. Configuration Files

### 2.1 `C:\Users\ASUS\.codex\config.toml` — Codex Desktop config

This file controls the main Codex Desktop app (model selection, provider routing,
MCP servers, project trusts, etc.). It is the primary config for the Electron app
at `C:\Users\ASUS\.codex\.sandbox-bin\codex.exe`.

### 2.2 `scripts/start_cheapluna_vscode.ps1` — Codex Desktop bridge launcher

Used by Codex Desktop/VS Code to start the DeepLuna bridge MCP server. Sets
environment variables, validates them, runs a health probe, then launches
`server.mjs` over stdio.

### 2.3 `.opencode/scripts/cheapluna-bridge.ps1` — OpenCode bridge launcher

Used by OpenCode's MCP framework. Sets environment variables, ensures daemon is
running (or starts one), runs `server.mjs` over stdio. The daemon persists across
bridge restarts.

### 2.4 `.opencode/skills/cheapluna-literature-review/SKILL.md`

Skill defining a two-phase workflow for deep research:
- **Phase 1**: `deepseek_read_submit` with PRO tier (V4 Pro, reasoning=high) for
  deep literature review
- **Phase 2**: `deepseek_batch_submit` with FLASH tier (V4 Flash) for parallel
  follow-up tasks

---

## 3. Root Causes of the Failure

### 3.1 Primary: `model_provider` changed to `litellm_glm`

**File**: `C:\Users\ASUS\.codex\config.toml` (line 1, was)
```toml
model_provider = "litellm_glm"
```

This forced Codex Desktop to route ALL chat traffic through
`http://127.0.0.1:4000/v1` — a local LiteLLM proxy server that did not exist.
The app could not connect, cached the failure in `state_5.sqlite`, and displayed
"LiteLLM GLM 5.2" in the account area.

**Fix**: Removed the `model_provider` line entirely. When absent, Codex Desktop
uses its built-in OpenAI authentication and direct API access.

### 3.2 Cascading: `state_5.sqlite` corruption

The broken provider config corrupted the app's SQLite state database. When we
first attempted to fix this by renaming the state file, Codex Desktop created a
fresh empty state — but an empty state has NO auth tokens. The app could not
authenticate the user without the original auth data, and failed with
"ChatGPT failed to start".

**Fix**: Deleted the broken new state, restored `state_5.sqlite` from
`state_5.sqlite.bak` (the August 4 backup from before the GLM change).

### 3.3 Missing `service_tier`

**File**: `C:\Users\ASUS\.codex\config.toml`

The original working config had `service_tier = "default"`. This was removed
sometime between July 12 and July 27. Without it, Codex Desktop may refuse to
initialize the chat service.

**Fix**: Added back `service_tier = "default"`.

### 3.4 `model_reasoning_effort` changed

**File**: `C:\Users\ASUS\.codex\config.toml` (line 3)

Original value: `"medium"`. Was changed to `"low"`. While low doesn't cause
startup failure, the user's preference is medium.

**Fix**: Restored to `"medium"`.

### 3.5 `deepinfra.wire_api` validation

**File**: `C:\Users\ASUS\.codex\config.toml` (line 23)

Codex Desktop v26.721.41059 validates ALL `[model_providers.*]` sections at
startup, even ones that aren't active. The `deepinfra` block had
`wire_api = "chat"` which the new version rejects.

**Fix**: Changed to `wire_api = "responses"`.

---

## 4. Changes Applied

### 4.1 `config.toml` — 4 edits

| Setting | Before | After |
|----------|--------|--------|
| `model_provider` | `"litellm_glm"` | _(removed)_ |
| `service_tier` | _(missing)_ | `"default"` |
| `model_reasoning_effort` | `"low"` | `"medium"` |
| `[model_providers.deepinfra].wire_api` | `"chat"` | `"responses"` |

### 4.2 `state_5.sqlite` — Restored from backup

- Broke new state files (from failed startup) deleted
- Original `state_5.sqlite` (2.8 MB, with working auth tokens) restored from
  `state_5.sqlite.bak`

### 4.3 `start_cheapluna_vscode.ps1` — Reverted to original

The script was briefly modified to use `deepseek-direct` but reverted. Current
settings match the original pre-troubleshooting state:

- `DEEPLUNA_PRIMARY_PROFILE` = `"deepinfra-fast"`
- `DEEPLUNA_FAST_ONLY` = `"1"`
- `NANODRUG_DEEPINFRA_READER_LANES` = `"5"`
- `DEEPLUNA_CODEX_ORCHESTRATION` = `"disabled"`
- Health probe expects `read_limit !== 5`

### 4.4 `opencode.json` — CheapLuna MCP entry added

```json
"cheapluna": {
  "type": "local",
  "command": ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".opencode/scripts/cheapluna-bridge.ps1"],
  "enabled": true,
  "timeout": 120000,
  "environment": {}
}
```

### 4.5 New files created

| File | Purpose |
|------|---------|
| `.opencode/scripts/cheapluna-bridge.ps1` | OpenCode bridge launcher |
| `.opencode/skills/cheapluna-literature-review/SKILL.md` | Lit review → delegation workflow |

---

## 5. Key Files Referenced

| File | Role |
|------|------|
| `C:\Users\ASUS\.codex\config.toml` | Codex Desktop main config |
| `C:\Users\ASUS\.codex\config.toml.orig` | Working backup (July ~12) |
| `C:\Users\ASUS\.codex\config.toml.bak-deepluna-fix` | GLM config snapshot (~July 27) |
| `C:\Users\ASUS\.codex\state_5.sqlite` | App state database (auth, sessions) |
| `C:\Users\ASUS\.codex\.codex-global-state.json` | Global app state |
| `C:\Users\ASUS\.codex\models_cache.json` | Cached model list |
| `C:\Users\ASUS\.codex\computer-use\config.json` | Computer-use plugin config |
| `C:\Users\ASUS\AppData\Local\Codex\deepseek-orchestrator\state-v4.json` | Codex Desktop DeepLuna orchestrator state |
| `C:\Users\ASUS\AppData\Local\Codex\deepseek-orchestrator\head-state-v1.json` | Codex Desktop head state |
| `C:\Users\ASUS\.codex\tools\opencode-deepseek-mcp\server.mjs` | Bridge server (shared by both bridges) |

---

## 6. Prevention Recommendations

1. **Never set `model_provider` unless a working proxy is running.** The default
   `model_provider` absence routes through Codex Desktop's built-in OpenAI auth.
2. **Keep `state_5.sqlite` backups** before any provider/model changes. This file
   contains auth tokens that can't be recreated without signing in again.
3. **Avoid settings changes to `config.toml` during voice/realtime sessions.**
   The app actively re-reads this file and may fail mid-session.
4. **The bridge MCP (`deepseek_orchestrator`) is independent from chat model config.**
   Adding, removing, or changing the bridge MCP server does NOT affect the main
   chat model — those are separate systems within Codex Desktop.

---

## 7. Bridge Version

- **Bridge server**: `C:\Users\ASUS\.codex\tools\opencode-deepseek-mcp\server.mjs`
- **Version**: 0.9.9 (DeepLuna / NanoDrug orchestrator)
- **GLM fallback**: Baked into the code but disabled via
  `DEEPLUNA_CODEX_ORCHESTRATION = "disabled"` (line 1793 filters GLM from routes)
- **Embedded compat**: `DEEPLUNA_EMBEDDED_COMPAT = ""` disables embedded runtime;
  the bridge uses daemon-backed workers
