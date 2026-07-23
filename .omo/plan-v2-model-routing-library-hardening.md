# Plan v2 — Multi-Tier Model Routing + Local Perfume Library + Pipeline Hardening

**Author**: Prometheus (high variant)
**Date**: 2026-07-20
**Hands to**: Tier-0 orchestrator (recommended: `deepinfra/deepseek-v4-flash` FP4) → escalates to **GLM-5.2 (max) on flex tier** for final gates only
**Supersedes**: `plan-v1-glm-priority-routing.md` (v1) — v2 incorporates all v1 sections + perfume chemistry domain research + model capability analysis

---

## Part A — DeepInfra & DeepSeek Model Capability Matrix (RESEARCH RESULTS)

### A.1 Artificial Analysis Intelligence Index (verified live)

Source: `artificialanalysis.ai/models/*`, fetched 2026-07-20.

| Model | Provider(s) | Intelligence | Speed t/s | TTFT s | $/M In | $/M Cached | $/M Out | Ctx | Reason? |
|---|---|---|---|---|---|---|---|---|---|
| **GLM-5.2 (max)** | DeepInfra (FP4), 15 others | **51** ⭐ #1 open-weights | 199 | 1.37 | $0.93 | $0.26 | $3.00 | **1.05M** | Yes |
| **DeepSeek V4 Pro (reasoning, max)** | DeepInfra, DeepSeek-direct | 44 | 67 | 1.68 | $1.30 | $0.10 | $2.60 | **1M** | Yes |
| **DeepSeek V4 Flash (reasoning, max)** | DeepInfra (FP4), DeepSeek-direct | 40 | 121 (DS-direct) / 31 (DeepInfra) | 1.27 / 1.11 | $0.09 | $0.018 | $0.18 | **1M** | Yes |
| **DeepSeek V3.1 (non-reasoning)** | DeepInfra, DeepSeek-direct | 21 | — | — | $0.25 | — | $0.95 | 160K | No |
| **gpt-oss-120b (high)** | DeepInfra, DeepInfra Turbo, 20 others | 24 | 312 / 347 (Turbo) | 0.85 | $0.04 | $0.04 | $0.17 | 131K | Yes |
| **DeepSeek R1-0528** | DeepInfra | N/A | — | — | $0.50 | $0.35 | $2.15 | 160K | Yes (heavy) |
| **Qwen3-Max** | DeepInfra | 24 | 53 | 2.38 | $1.20 | $0.24 | $6.00 | 250K | No |
| **Llama-4-Maverick-17B-128E** | DeepInfra | — | — | — | $0.20 | — | $0.80 | **1M** | No |

### A.2 Critical findings

1. **GLM-5.2 is the smartest open-weights model** on the market — the only model with IQ > 50 that runs on DeepInfra. No DeepInfra model beats it for reasoning.
2. **DeepSeek V4 Flash is the price/performance king** — 40 IQ (78% of GLM-5.2's intelligence) at 1/12 the price. With 1M context. Reasoning model.
3. **gpt-oss-120b has 131K context** — too small for this project. Pipeline JSON outputs run 5–10K lines._good for chat-routing only, not for chewing pipeline JSON. It IS the cheapest option though, and DeepInfra Turbo makes it fast (347 t/s). Use it ONLY for short agent dispatching and tool-call routing.
4. **DeepInfra is the CHEAPEST GLM-5.2 provider** — $0.61 blended vs. Scaleway's $2.52. Confirmed.
5. **DeepSeek-direct is FASTER than DeepInfra** for V4 Flash (121 t/s vs 31 t/s) — but DeepInfra is cheaper ($0.05 blended vs $0.06 vs DeepSeek). Trade-off: 4× speedup costs 20% more.
6. **DeepSeek V4 Pro has $0.10 cached tier** — 13× discount on cached prompts. Use it for repeated system-prompt caching of agent instructions.
7. **No DeepInfra model has multimodal input** — all the strong reasoning models are text-only. Images/SDFs would require separate embedding pipeline.

### A.3 Perfume chemistry capability assessment (per domain)

| Domain knowledge area | GLM-5.2 max | DeepSeek V4 Pro | DeepSeek V4 Flash | gpt-oss-120b |
|---|---|---|---|---|
| General organic chemistry | Strong | Strong | Strong | Moderate |
| Terpenes/terpenoids (limonene, ionones, irones) | Moderate | Strong | Moderate | Weak |
| Macrocyclic musks lactones | Moderate | Strong | Weak | Weak |
| Salicylate fixatives | Moderate | Moderate | Weak | Weak |
| OAV/ODT physics (Raoult, γ, Clausius-Clapeyron) | Strong | Strong | Moderate | Weak |
| Perfume GC-MS-O literature | Weak (training cutoff) | Weak | Weak | Weak (May 2024 cutoff) |
| Thai mass-market perfumes | Weak | Weak | Weak | Weak |
| Perfumer's World SKU catalog | None (not in training) | None | None | None |

**Verdict**: None of the available models has deep perfume-domain knowledge. **We must build a local perfume library** from Perfumer's World catalog + Good Scents + TGSC + published GC-MS-O data. Models do retrieval over it.

---

## Part B — Multi-Tier Routing Architecture (REVISED)

### B.1 Tier structure

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 0 — ORCHESTRATOR (every tool call, every message)      │
│  MODEL: deepinfra/deepseek-v4-flash (FP4, reasoning)         │
│  Blended: $0.05/Mtok · 1M ctx · 40 IQ · 121 t/s              │
│  ROLE: Route, dispatch agents, parse commands, run gates      │
└────────────────────────────┬──────────────────────────────────┘
                             │ escalate if blocked 2+ attempts,
                             │ or user explicitly requests "brain"
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 1 — PRE-GATE CHEAP CANARY (flex tier, every gate run)   │
│  MODEL: deepseek-v4-flash on DeepSeek-direct Flex (0.8x)     │
│  Blended: $0.048/Mtok · 121 t/s (faster than DeepInfra's 31)  │
│  ROLE: Catch obvious pipeline/format errors before GLM gate   │
└────────────────────────────┬──────────────────────────────────┘
                             │ escalate (max once or twice)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 2 — FINAL BRAIN GATE (flex tier, 1-2x per session max)  │
│  MODEL: deepinfra/zai-org/GLM-5.2 (FP4, max, reasoning)       │
│  Blended: $0.49/Mtok Flex (0.8x of $0.61) · 1.05M ctx         │
│  ROLE: Approve formula release; author final perfumer report  │
│         Diagnose 2x-failed bug chains; large refactor design   │
└────────────────────────────┬──────────────────────────────────┘
                             │ escalate (rare; user-explicit only)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Tier 3 — ORACLE (only when GLM aborts twice)                 │
│  MODEL: deepseek/deepseek-v4-pro (DeepSeek-direct, reasoning)  │
│  Blended: $0.18/Mtok (with caching) · 1M ctx · 44 IQ          │
│  ROLE: Deep bug-chain diagnosis; large plan critique; never   │
│         default — invoked only by Tier 2 handoff              │
└─────────────────────────────────────────────────────────────┘
```

### B.2 Task → Tier mapping

| Task | Tier | Model | Cost/task (est) | Why |
|---|---|---|---|---|
| Single file edit, format fix | 0 | DeepSeek-V4-Flash | $0.001 | Routine |
| Gate pipeline run | 1 | DeepSeek-V4-Flash (flex) | $0.005 | Cheap, fast |
| Parse 6K-line pipeline JSON | 0 | DeepSeek-V4-Flash (1M ctx) | $0.01 | 1M ctx critical |
| Plan synthesis (5+ dependent steps) | 2 | GLM-5.2 max (flex) | $0.20 | Reasoning matters |
| Formula release final approval | 2 | GLM-5.2 max (flex) | $0.30 | IQ 51 catches silent bugs |
| Bug after 2 failed fix attempts | 2 | GLM-5.2 max (flex) | $0.30 | Escalation rule |
| Vestigial Oracle consult (GLM aborts) | 3 | DeepSeek-V4-Pro (cached) | $0.50 | Last resort |
| 200K-token file dump | 0 | DeepSeek-V4-Flash (1M ctx) | $0.02 | 1M ctx needed |

### B.3 Service tier rules

- **Default**: Standard (1.0x)
- **Tier 0 chat**: Standard — user is talking, latency matters, 121 t/s is fast enough
- **Tier 1 pre-gate (async)**: **Flex (0.8x)** — latency tolerance is high, save 20%
- **Tier 2 GLM-5.2 final gate (async)**: **Flex (0.8x)** — user explicitly said flex
- **Tier 2 GLM-5.2 if user typing in chat**: Standard — get answer in 6-8s instead of 15-30s
- **Tier 3 oracle**: Standard (or Priority (1.5x) only on explicit user frustration)

### B.4 Token use audit (from session history)

20 sessions reviewed 2026-07-10 to 2026-07-20:
- 12 sessions <35 messages → Tier 0 sufficient. Est cost: <$0.10/session
- 5 sessions 50-120 messages → Tier 0 + 1-2 Tier-1 flex calls. Est cost: $0.30-0.50/session
- 3 sessions 150-180 messages (heavy multi-day) → Tier 0 + 2 Tier-2 + 1 Tier-3. Est cost: $1.50-2.00/day
- **Heaviest wasted tokens**: parsing large pipeline JSON in Tier 0 (DeepSeek-V4-Flash at 1M ctx handles this for $0.01 each)

Expected monthly cost at this routing: **$20-40 USD** vs. current DeepLuna-Sol path which often hits $50-100/month.

---

## Part C — Parallel Reader/Brain Framework (CONCURRENT OPencode ISOLATION)

### C.1 Why a local framework

Three OpenCode windows run at once in this env. DeepLuna's shared SQLite state keeps colliding. A local session-scoped framework isolates jobs completely.

### C.2 Directory layout

```
.opencode/parallel/
├── README.md              # 50 lines — contract
├── runner.py              # CLI: submit/status/collect/list
├── jobs/                  # session-scoped (gitignored, in .gitignore append)
│   └── <session_id>/
│       └── <job_id>/
│           ├── job.lock    # cross-process file lock (msvcrt on Win)
│           ├── input.json  # args + reader/brain name
│           ├── output.json ← atomic write (.tmp → os.replace)
│           └── status.json ← atomic write
└── __init__.py            # marker
```

### C.3 Subagents — Reader vs Brain

**READER** (Tier 1 — flash on flex):
- Bounded local file read with atomic sha256 capture
- Optional line range for large files
- Output: `{path, lines, sha256, captured_at, line_count}`
- No model call — pure local IO (free + deterministic)

**BRAIN** (Tier 2 — GLM-5.2 max flex, 1-2x max):
- Input: prompt + file refs + reader outputs already collected
- Calls DeepInfra `zai-org/GLM-5.2` via `urllib.request` stdlib
- Sets `service_tier: "flex"` in body
- Output: structured `{reasoning, decision, refs}`
- Logs token spend to `.opencode/parallel/brain_ledger.jsonl` for audit

### C.4 Concurrency safety

1. **Session isolation**: every job path includes `OPENCODE_SESSION_ID` env. Runner refuses action if missing.
2. **Atomic writes**: output → `<name>.tmp` → `os.replace()` to final name (atomic on POSIX + Windows).
3. **Cross-process lock**: `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) on `job.lock`. Lock stores `{pid, timestamp, session_id}` as JSON.
4. **Stale lock reclaim**: lock > 30min (env: `STALE_LOCK_MINUTES=30`) AND `pid` not alive → safe to reclaim.
5. **Status enum**: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`.
6. **Never trust partial**: `collect` refuses output unless `status.json` says `complete` or `stale_reclaimed`.

### C.5 CLI

```
python -m runner submit --kind read --path <file> --reader flash
python -m runner submit --kind brain --prompt <text> --files <paths...> --reader glm-max-flex
python -m runner status <job_id>
python -m runner collect <job_id>
python -m runner list --session <id>
python -m runner cleanup --stale-minutes 30
```

### C.6 Build steps

1. Stdlib-only `runner.py` (`os, sys, json, hashlib, time, pathlib, argparse, subprocess, msvcrt, urllib.request, urllib.error`)
2. `python -m py_compile` verification
3. Smoke test: submit a read of README.md, poll status, collect result
4. Append `.opencode/parallel/jobs/` to `.gitignore`

---

## Part D — Local Perfume Knowledge Library (NEW BIG INVESTMENT)

### D.1 Problem

No DeepInfra/DeepSeek model has Perfumer's World SKU catalog knowledge. Hallucinated material names cost real material waste (see Agent Failure Registry F5/F11). Need structured local library that models retrieve from.

### D.2 Source data we already have

- `knowledge/perfumersworld_stock.md` — 4036 lines, raw catalogue, US$/gram, SKUs
- `data/materials/_sources/perfumersworld_stock.parsed.json` — parsed (12,026 lines)
- `engine/odor_thresholds.py` ODT_DATA — 210 materials
- `data/materials/*.yaml` — 210 materials
- `engine/ingredient_intelligence.py` _PROFILES — 210 materials
- `material_properties.json` — 210 materials, full MW/VP/logP/ODT
- `inventory.txt` — actual owned stock
- `data/thai_market_sales_2500_15000_thb.md` — Thai retail reference pricing
- `docs/fragrance_families_reference.md` — 22 mapped families
- `engine/reference_contracts.py` — Explorer/Aventus/Prada L'Homme architecture contracts

### D.3 Library to build

`.opencode/library/perfume_kb.jsonl` — one JSON per line, structured for cheap Tier-0 retrieval:

```json
{"id": "pw_sku_5EW07840", "source": "perfumersworld", "base_name": "2 3-Dimethyl Pyrazine", "dilution_pct": 1.0, "solvent": "DPG", "sku": "5EW07840", "price_usd_per_gram": 0.12, "in_local_inventory": false}
{"id": "gs_osmanthus_abs", "source": "goodscents", "name": "Osmanthus Absolute", "cas": "68917-16-2", "constituents": [...], "vp_pa_25c": 0.02, "mw": 212, "logp": 2.5}
{"id": "lit_hong2023_osmanthus", "source": "literature", "ref": "Hong et al. 2023", "topic": "β-ionone dominance in osmanthus GCMS-O", "key_finding": "..." }
{"id": "fam_chypre", "source": "families_reference", "family": "chypre", "anchor_materials": ["oakmoss", "patchouli", "labdanum", "bergamot"], "forbidden": ["vanillin >5%", "hedione >12%"]}
{"id": "ref_explorer_v1", "source": "reference_contracts", "name": "Montblanc Explorer", "marker_groups": [...], "official_source": "..."}
```

### D.4 Retrieval contract

Tier-0 model (DeepSeek-V4-Flash) loads `.opencode/library/perfume_kb.jsonl` (or a chunked subset) and uses embedding-free lexical search:
- `grep` the JSONL for material name → returns matching lines
- Pass matching lines into prompt context as known-good facts
- For chemistry questions, also fetch PubChem CID via existing `pubchem_*` MCP tools (already installed)
- For peer-reviewed findings, also fetch web via `webfetch` (used in this session)

### D.5 Library build phases

**Phase 1 — Perfumer's World ingestion (50% already done in parsed.json)**
1. Read `perfumersworld_stock.parsed.json`, normalize to JSONL
2. Cross-reference `base_name` against `inventory.txt` to flag `in_local_inventory`
3. Cross-reference SKUs against any pubchem CID mappings we have

**Phase 2 — Good Scents + TGSC material properties (fetch)**
1. For each natural in inventory (bergamot, osmanthus, vetiver, etc.), fetch Good Scents entry
2. Extract constituents (CAS, %, odor description), VP, MW, logP
3. Merge into library as `{"source": "goodscents", ...}` entries

**Phase 3 — Literature citations (we already have many in AGENTS.md)**
1. Extract every reference in AGENTS.md "Session Learnings" section
2. Build JSONL entries with `{ref, material, key_finding}` for each
3. Add: Calkin & Jellinek 1994, Carles 1961, Ellena 2011, Sinding 2017, Laing & Francis 1989, Shiseido GCMS, Hong 2023, Guo 2024

**Phase 4 — Reference contracts (we already have 3)**
1. Re-emit existing 3 contracts (Explorer, Aventus, Prada L'Homme) into JSONL
2. Future: add Tom Ford Neroli Portofino, Dior Homme Parfum, etc. as user requests

### D.6 Caching strategy

- `.opencode/library/perfume_kb.jsonl` — append-only, sha256-versioned
- `.opencode/cache/retrieval/<query_hash>.json` — 24h TTL for repeated queries by Tier-0
- `.opencode/cache/pubchem/<cid>.json` — 30d TTL (per AGENTS.md E.1)

---

## Part E — Pipeline Format Unification (Prada Template)

### E.1 The canonical format (`Prada_LHomme_Architecture_Control_30mL_EdT.md`)

```markdown
# <Formula Name> — <size> <style>
**Date:** <YYYY-MM-DD>
**Claim mode:** named_reference | unclaimed
**Reference contract:** <contract_id> | none
**Reference scope:** architecture | quantitative_similarity | sensory_similarity
**Family archetype:** `<key>`
**Reference evidence:** <one-sentence proof of what the reference actually discloses>
**Official source:** <URL>
**Concentration:** <uL concentrate> + <uL ethanol>; <final volume>; <% v/v>
**Status:** <Research control | Pending bench | Released>

## Concept Lock
<1-paragraph north star prose>

## Formula
| # | Ingredient | Dilution | Amount (uL) | Active uL | Active ppm v/v proxy | Specific function |
|---:|---|---|---:|---:|---:|---|

## Summary
... concentrate / top / heart / base / ethanol / active material / solvent-from-dilutions / active-concentration ...
```

### E.2 Pipelines to extend (must NOT require full main pipeline run)

All 6 scripts must parse the metadata block first and refuse to proceed if missing:

| Script | What to add | Why |
|---|---|---|
| `scripts/evaluate_formula.py` | metadata parser block; refuse unless metadata present or `unclaimed` | Quality floor |
| `scripts/oav_headspace_analyze.py` | emit smaller JSON (OAV table + note distribution only); reuse `format_pipeline_analysis.py` formatters | Fast diagnostic |
| `scripts/formula_simulator.py` | temporal evolution only; emit 5-window OAV | #4 from AGENTS.md requirement |
| `scripts/formula_diagnosis.py` | emit deviation report if any named reference detected (reuse my new `build_reference_deviation()`) | Alerts before costly fixes |
| `scripts/formula_recommender.py` | pre-formulation only; must NOT touch main pipeline | Prevents overspending |
| `scripts/opus_v_workbook_pipeline.py` | apply same metadata block requirement | Workbook-style consistency |

### E.3 Hard-block safeguards (anti-waste, anti-oversight)

1. **Refuse to gate any formula missing metadata block** — wrap `_gate_reference_claim_contract` OR explicit `unclaimed`
2. **Refuse to gate if `inventory_stock_contract` FAIL** — already a FAIL; promote to hard-block
3. **Refuse to run expensive pipelines if `quantitative_authority.active_concentrate_ppm_w_w == UNAVAILABLE`** — density fallback yields wrong ppm
4. **Refuse to mix chemically incompatible naturals** (F11 failure) — add `_CHEMICAL_FAMILY_MAP` in `engine/ingredient_intelligence.py`, check pairs before gate
5. **Pre-flight cost ticker** — emit `_ESTIMATED_MATERIAL_COST_THB` BEFORE running gates, warn if exceeds `data/thai_market_sales_2500_15000_thb.md` bracket

### E.4 Pseudocode safeguard wrapper

```python
def pipeline_preflight_guard(formula_path, brief):
    # 1. Metadata block required unless explicit `Reference claim: none`
    meta = parse_formula_metadata(formula_path)
    if not meta.get("claim_mode"):
        return HARD_BLOCK("Missing metadata block. Set `Reference claim: none` or fill Explicit metadata.")

    # 2. Inventory contract check
    if not inventory_stock_contract_ok(formula_path):
        return HARD_BLOCK(f"Inventory contract FAIL: {issues}")

    # 3. Quantitative authority check
    if meta.get("claim_mode") == "named_reference" and meta.get("scope") == "quantitative_similarity":
        if not quantitative_authority_ok(formula_path):
            return HARD_BLOCK("Quantitative scope requires density chain. Refusing to run.")

    # 4. Chemical family compatibility (F11)
    incompatible = check_natural_compatibility(formula_path)
    if incompatible:
        return WARN(f"Risky natural combinations: {incompatible}")

    # 5. Thai market cost ticker
    cost_thb = estimate_material_cost_thb(formula_path)
    if cost_thb > 5000:
        return WARN(f"Material cost ~{cost_thb} THB may exceed mass-market retail bracket")

    return PASS
```

---

## Part F — OpenCode Config Edits (B.1-B.4 carryover)

### F.1 Remaining edits to `opencode.json`

1. ✅ DONE: `model: "deepinfra/zai-org/GLM-5.2"` (set to normal FP4)
2. ✅ DONE: `small_model: "deepinfra/deepseek-v4-flash"` (V4 Flash replaces V3.1 — better perf, $/M same)
3. ✅ DONE: `env-guard.js` forwards 3 API keys + `OPENCODE_SESSION_ID`
4. ⬜ TODO: flip `deepluna_read.enabled: true → false` in `opencode.json`
5. ⬜ TODO: flip `deepluna_fast_read.enabled: true → false` in `opencode.json`
6. ⬜ TODO: flip `_note_overrides` — already added marker comment

### F.2 Codex keeps DeepLuna — verified

- `~/.codex/config.toml` has independent `deepseek_orchestrator` MCP server
- OpenCode disabling its own MCP servers does NOT affect Codex
- No edits to `~/.codex/` required

### F.3 Provider verification curls (execute on orchestrator start)

```powershell
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPINFRA_API_KEY" https://api.deepinfra.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:OPENCODE_GO_API_KEY" https://api.opencode.com/v1/models
```

All three should return 200. If any fail, the routing plan must fall back.

---

## Part G — Cache, Hooks, Skills, Superpowers

### G.1 Cache infrastructure (local, free)

| Cache location | Contents | TTL |
|---|---|---|
| `.opencode/cache/gate_results/<sha256>.json` | Pipeline gate JSON outputs | Invalidate on formula git HEAD change |
| `.opencode/cache/pubchem/<cid>.json` | PubChem compound details | 30 days |
| `.opencode/cache/retrieval/<query_hash>.json` | Local perfume library query results | 24 hours |
| `.opencode/cache/reference_eval/<formula_sha>.json` | Reference contract evaluations | Invalidate on `reference_contracts.py` git HEAD change |

### G.2 Provider cache (paid but cheap)

* DeepSeek-V4-Flash cached tier on DeepInfra: $0.018/Mtok vs $0.09 — 80% discount
* DeepSeek-V4-Pro cached tier on DeepSeek-direct: $0.10/Mtok vs $1.30 — 92% discount
* Pre-pend stable agent instructions in every call (cacheable prefix)

### G.3 Hooks (`env-guard.js` rewrite)

* `tool.execute.before` on `read` of `.env` → deny (already in place)
* `tool.execute.before` on `read` of formula file → check stale gate cache; reuse if `_notes_shown`
* `tool.execute.after` on `write` to formula file → invalidate gate cache for that formula
* `shell.env` — already forwards 3 API keys + session id (done this session)
* Pre-bash hook on `formula_release_gate.py` invocation → refuse if `OPENCODE_SESSION_ID` unset when more than 1 OpenCode window open (check via `tasklist | grep opencode` count)

### G.4 Skills to add

| Skill name | Purpose | Location |
|---|---|---|
| `provider-routing` | Cost-benefit tier decision matrix, loaded at session start | `.agents/skills/provider-routing/SKILL.md` |
| `perfume-library-query` | Stdlib-only JSONL retrieval against local perfume KB | `.opencode/skills/perfume-library-query/SKILL.md` |
| `formula-release-gate` (already exists) | Extend with metadata-block enforcement | `.opencode/skills/formula-gate/SKILL.md` |
| `parallel-reader` | Document the `.opencode/parallel/runner.py` contract | `.opencode/skills/parallel-reader/SKILL.md` |

### G.5 MCP additions

| MCP | Purpose | Cost |
|---|---|---|
| `pubchem` (already installed) | Compound properties by CID | Medium |
| `memory` (already installed) | Persistent knowledge graph | Low-Medium |
| `sequential_thinking` (already installed) | Multi-step reasoning | Medium |
| NEW: `perfume_kb` | Local stdlib-only MCP that exposes `.opencode/library/perfume_kb.jsonl` | Free |

The new `perfume_kb` MCP is just a thin stdlib wrapper exposing `query_material`, `query_family`, `query_literature`, `query_reference_contract` over the local JSONL. Zero external calls.

### G.6 Superpowers (oh-my-opencode plugin integration)

Existing plugins already in `opencode.json`:
- `oh-my-openagent` — agent dispatch
- `@plannotator/opencode` — plan annotation UI
- `opencode-pty` — PTY sessions
- `.opencode/plugins/env-guard.js` — env + hook guards
- `.opencode/plugins/inventory-guard.js` — inventory guards

To add:
- `.opencode/plugins/gate-cache-guard.js` — wraps `formula_release_gate.py` bash invocations to check/invalidate local gate cache
- `.opencode/plugins/parallel-runner-guard.js` — ensures `OPENCODE_SESSION_ID` is unique across running OpenCode windows
- `.opencode/plugins/provider-tier.js` — sets `DEEPINFRA_SERVICE_TIER` env var based on task shape (chat=standard, gate=flex, plan=flex)

---

## Part H — Carryover from v1

Combined with v1's outstanding items:

- [x] Set opencode.json `model` to GLM-5.2 FP4 (DONE)
- [x] Set opencode.json `small_model` to DeepSeek-V4-Flash (DONE — replaced V3.1 with V4-Flash per A.1 analysis)
- [x] Updated env-guard.js to forward 3 API keys + session id (DONE)
- [x] Added `_note_overrides` marker (DONE)
- [⬜] Flip `deepluna_read.enabled → false` in opencode.json (F.1.4)
- [⬜] Flip `deepluna_fast_read.enabled → false` in opencode.json (F.1.5)
- [⬜] Build `.opencode/parallel/runner.py` + README (Part C)
- [⬜] Run Part F.3 provider verification curls
- [⬜] Extend Part E.2 pipelines with metadata-block requirement
- [⬜] Add Part E.3 safeguard hard-blocks (preflight wrapper)
- [⬜] Build Part D perfume library Phase 1 (Perfumer's World → JSONL)
- [⬜] Build Part D Phase 2 (Good Scents fetch)
- [⬜] Build Part G.4 new skills (provider-routing, perfume-library-query, parallel-reader)
- [⬜] Build Part G.5 new `perfume_kb` MCP
- [⬜] Build Part G.6 new plugin hooks (gate-cache-guard, parallel-runner-guard, provider-tier)

---

## Part I — Orchestrator Handoff

### I.1 Recommended hand-off

Hand to **GLM-5.2 max (deepinfra/zai-org/GLM-5.2) at normal FP4 tier**. You explicitly said "you" (me). I'm running on this already.

For final formula gates only, drop to flex tier (Part B.1 Tier 2) — max 1-2 times per session.

### I.2 Execution order (tight)

**Wave 1 (15 min, config lockdown)**:
1. F.1.4 + F.1.5 — disable DeepLuna MCP in opencode.json (2 minutes)
2. F.3 — verify providers via curl (3 minutes)
3. Add `.opencode/parallel/jobs/` and `.opencode/cache/` to `.gitignore` (2 minutes)
4. F.1.6 — fix the `_note_overrides` comment syntax (valid JSON) (2 minutes)

**Wave 2 (45 min, framework build)**:
5. C.5 — write `runner.py` (stdlib only) + README + smoke test (30 minutes)
6. G.6 — write 3 plugin hooks (`gate-cache-guard.js`, `parallel-runner-guard.js`, `provider-tier.js`) (15 minutes)

**Wave 3 (30 min, config finalization)**:
7. G.4 — write 4 new skill files (provider-routing, perfume-library-query, parallel-reader, formula-release-gate extension) (20 minutes)
8. G.5 — write `perfume_kb` MCP (stdlib only) — 10 minutes

**Wave 4 (60-90 min, pipeline unification)**:
9. E.2 — extend 6 pipeline scripts with metadata-block parsing (60 min) — delegate to Tier 1 (DeepSeek-V4-Flash flex)
10. E.3 — add `pipeline_preflight_guard()` wrapper in `scripts/formula_release_gate.py` and `scripts/pipeline_audit.py` (30 min)

**Wave 5 (60+ min, local perfume library)**:
11. D.5 Phase 1 — Perfumer's World `parsed.json` → `perfume_kb.jsonl` normalizer script (20 min)
12. D.5 Phase 3 — literature citations extractor (20 min)
13. D.5 Phase 2 — (DEFER) Good Scents + TGSC fetch — requires network, optional, can be done later when assistant idle

### I.3 Total cost estimate for the build

| Wave | Tier | Tokens (est) | Cost (USD) |
|---|---|---|---|
| 1 | Tier 0 orchestrator (me GLM-5.2 FP4 normal) | 50K in / 10K out | $0.15 |
| 2 | Tier 0 + 1 Tier-2 final review (GLM flex) | 80K / 20K total across waves | $0.40 |
| 3 | Tier 0 + 1 Tier-2 (skill files review) | 60K / 15K | $0.30 |
| 4 | Tier 0 + 3 Tier-1 flex delegations | 200K / 50K | $0.50 |
| 5 | Tier 0 only | 100K / 20K | $0.20 |
| **Total build** | | | **~$1.55** |

### I.4 What this plan does NOT do

- Does NOT change Codex — `~/.codex/config.toml` untouched
- Does NOT install any third-party Python/JS packages — stdlib only
- Does NOT run the full main pipeline on any formula
- Does NOT modify `engine/` scientific modules beyond existing reference_contracts.py extensions from prior v1 work
- Does NOT touch reference_contracts.py again (already extended this session)
- Does NOT fetch Good Scents / TGSC (deferred to Wave 5 Phase 2, optional)
- Does NOT require multimodal models (none on DeepInfra qualify for this project)

---

## Part J — Future-Facing Extensions (LISTED, NOT BUILT YET)

### J.1 Orthogonal perfume testing protocol

When a bench test reveals a formula smells wrong, the corrective loop becomes:

1. Bench-test → user notes "off-character" / "muddy" / "too sharp"
2. Tier-0 orchestrator loads `.opencode/library/perfume_kb.jsonl`
3. Fetch constituent GC-MS data from library
4. Identify which class is overrepresented (e.g. "phenylpropanoid > terpenoid ratio broken")
5. Tier 1 pre-gates: cheap flash model proposes 2-3 minimal fixes
6. Tier 2 GLM-5.2 max final-brain accepts one fix, writes revised formula
7. Re-gate, hand to user for next bench test
8. Append to `formulas/<name>` as version bump

### J.2 Material property auto-fetch

When inventory is updated with a new material:
1. `inventory_parser.py` detects new entry
2. Auto-fire `pubchem_*` calls to get MW/logP/VP/ODT
3. Auto-append to `data/materials/<LETTER>.yaml`, `ingredient_intelligence._PROFILES`, `odor_thresholds.ODT_DATA`
4. Auto-run `scripts/_generate_material_properties.py` to resync `material_properties.json`
5. Auto-emit new entry to `perfume_kb.jsonl`

### J.3 Pre- and post-formulation diagnostic scan

`scripts/scan_formula_history.py` (NEW, not yet built) — scans `formulas/*.md` chronologically:
- Tags each formula with family archetype
- Cross-references Agent Failure Registry (F1-F11 from AGENTS.md)
- Emits JSON report of recurring failure patterns
- Fed back to Tier 0 as extra system prompt context for future sessions

### J.4 Perfumer's World price tracker

`scripts/perfumersworld_price_fetch.py` (NEW, not yet built) — refreshes the catalogue quarterly:
- Reads existing `knowledge/perfumersworld_stock.md`
- User pastes fresh stock list
- Diffs to show price changes
- Updates `perfume_kb.jsonl` entries

### J.5 DeepInfra priority escalation observer

`scripts/deepinfra_tier_audit.py` (NEW, not yet built) — runs daily:
- Reads `deepinfra_metrics` from active sessions
- Flags any session where standard tier TTFT > 5s
- Auto-suggests escalating to priority tier for that model in future similar sessions

---

**END OF PLAN v2 — ready for orchestrator handoff on approval.**
**Cost cap for build: $2 USD. Time: ~3 hours.**
**Ongoing session cost ceiling: $2-4/day.**